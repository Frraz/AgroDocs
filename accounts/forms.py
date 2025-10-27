"""accounts/forms.py"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone
from django.db import transaction
from .models import InviteCode, AccountStatus

User = get_user_model()


class SignupForm(UserCreationForm):
    """
    Formulário de cadastro com validação de código de convite.
    - Mostra erro claro no próprio campo quando o código é inválido/consumido.
    - Marca o convite como utilizado ao salvar o usuário.
    """
    email = forms.EmailField(required=True, label="E-mail")
    invite_code = forms.CharField(
        required=True,
        label="Código de convite",
        help_text="Informe o código que você recebeu."
    )

    class Meta:
        model = User
        # Não inclua invite_code aqui (não é campo do modelo)
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # UX: aplica classes padrão de controle de formulário
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()

        # Se já houver erros (POST inválido), realça o(s) campo(s)
        for name in self.errors:
            if name in self.fields:
                css = self.fields[name].widget.attrs.get("class", "")
                if "is-invalid" not in css:
                    self.fields[name].widget.attrs["class"] = (css + " is-invalid").strip()

    def clean_invite_code(self):
        """
        Valida o código de convite:
        - Precisa existir, estar ativo e ser utilizável agora (is_usable_now()).
        - Mensagem única e amigável: "Código inválido, tente novamente".
        """
        code = (self.cleaned_data.get("invite_code") or "").strip()
        if not code:
            # Campo é required=True; manter mensagem consistente
            raise forms.ValidationError("Código inválido, tente novamente")

        # Busca case-insensitive e apenas códigos ativos
        candidates = InviteCode.objects.filter(code__iexact=code, is_active=True).order_by("-created_at")

        invite = None
        for cand in candidates:
            # Confia na regra de domínio do model
            if getattr(cand, "is_usable_now", None) and cand.is_usable_now():
                invite = cand
                break

        if not invite:
            # Mensagem solicitada
            raise forms.ValidationError("Código inválido, tente novamente")

        # Guarda para uso no save()
        self._invite = invite
        return code

    @transaction.atomic
    def save(self, commit=True):
        """
        Salva o usuário e consome o convite de forma atômica.
        Observações:
        - Incrementa uses (se o campo existir e já tiver valor), em vez de fixar em 1.
        - Define used_by, redeemed_at e desativa o código.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email")

        if commit:
            user.save()

        invite = getattr(self, "_invite", None)
        if invite and (not hasattr(invite, "is_usable_now") or invite.is_usable_now()):
            # Atualiza campos do convite
            # Incrementa uses com segurança (se None, assume 0)
            current_uses = getattr(invite, "uses", 0) or 0
            invite.uses = current_uses + 1

            if hasattr(invite, "used_by"):
                invite.used_by = user
            if hasattr(invite, "redeemed_at"):
                invite.redeemed_at = timezone.now()
            if hasattr(invite, "is_active"):
                invite.is_active = False

            # Define quais campos atualizar, respeitando os existentes
            update_fields = []
            for fname in ("used_by", "redeemed_at", "uses", "is_active", "updated_at"):
                if any(f.name == fname for f in invite._meta.fields):
                    update_fields.append(fname)

            invite.save(update_fields=update_fields or None)

        return user


class LoginForm(AuthenticationForm):
    """
    Login com bloqueio de usuários suspensos (AccountStatus).
    Mensagem genérica sem expor motivo/datas.
    """

    def confirm_login_allowed(self, user):
        try:
            status = user.account_status
        except AccountStatus.DoesNotExist:
            status = None

        if status and getattr(status, "is_suspended_now", False):
            raise forms.ValidationError(
                "Seu acesso está temporariamente bloqueado. Entre em contato com o administrador.",
                code="suspended",
            )
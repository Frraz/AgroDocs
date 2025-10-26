from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone
from .models import InviteCode, AccountStatus

User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True, label='E-mail')
    invite_code = forms.CharField(required=True, label='Código de convite', help_text='Informe o código que você recebeu.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_invite_code(self):
        code = self.cleaned_data.get('invite_code', '').strip()
        if not code:
            raise forms.ValidationError('Informe o código de convite.')

        candidates = InviteCode.objects.filter(code=code, is_active=True).order_by('-created_at')
        invite = None
        for cand in candidates:
            if cand.is_usable_now():
                invite = cand
                break

        if not invite:
            raise forms.ValidationError('Este código de convite é inválido, já foi utilizado ou expirou.')

        self._invite = invite
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        invite = getattr(self, '_invite', None)
        if invite and invite.is_usable_now():
            invite.used_by = user
            invite.redeemed_at = timezone.now()
            invite.uses = 1
            invite.is_active = False
            invite.save(update_fields=['used_by', 'redeemed_at', 'uses', 'is_active', 'updated_at'])
        return user


class LoginForm(AuthenticationForm):
    # Mensagem genérica sem expor data/motivo
    def confirm_login_allowed(self, user):
        try:
            status = user.account_status
        except AccountStatus.DoesNotExist:
            status = None

        if status and status.is_suspended_now:
            raise forms.ValidationError(
                'Seu acesso está temporariamente bloqueado. Entre em contato com o administrador.',
                code='suspended'
            )
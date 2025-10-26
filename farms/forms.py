""" farms/forms.py """

"""
Forms e filtros do app Farms.

Melhorias:
- Helpers utilitários (only_digits, regex E.164).
- Validações robustas de CPF/CNPJ e CAR (com normalização).
- Normalização de WhatsApp para E.164 (assumindo +55 se ausente).
- save() do DocumentForm idempotente e atômico ao sincronizar lembretes.
- UX: placeholders, autocomplete e máscaras preservadas.
- Filtros (fazendas e documentos) com limpeza/normalização.
"""

import re
from typing import Optional

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import Document, DocumentReminder, Farm

User = get_user_model()

# -----------------------------
# Regex e utilitários
# -----------------------------

ONLY_DIGITS_RE = re.compile(r"\D+")
# Aceita qualquer UF (2 letras), 7 dígitos, 32 alfanum maiúsculos
CAR_PATTERN = re.compile(r"^[A-Z]{2}-\d{7}-[A-Z0-9]{32}$")
# E.164: + e até 15 dígitos (sem espaços, sem pontuação)
E164_RE = re.compile(r"^\+?[1-9]\d{1,14}$")


def only_digits(value: str) -> str:
    """Remove tudo que não é dígito."""
    return ONLY_DIGITS_RE.sub("", value or "")


def validate_cpf(digits: str) -> bool:
    """Valida CPF (apenas dígitos)."""
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    nums = list(map(int, digits))
    s1 = sum(a * b for a, b in zip(nums[:9], range(10, 1, -1)))
    d1 = (s1 * 10) % 11
    d1 = 0 if d1 == 10 else d1
    s2 = sum(a * b for a, b in zip(nums[:10], range(11, 1, -1)))
    d2 = (s2 * 10) % 11
    d2 = 0 if d2 == 10 else d2
    return nums[9] == d1 and nums[10] == d2


def validate_cnpj(digits: str) -> bool:
    """Valida CNPJ (apenas dígitos)."""
    if len(digits) != 14 or digits == digits[0] * 14:
        return False
    nums = list(map(int, digits))
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    d1 = 11 - (sum(a * b for a, b in zip(nums[:12], w1)) % 11)
    d1 = 0 if d1 >= 10 else d1
    d2 = 11 - (sum(a * b for a, b in zip(nums[:13], w2)) % 11)
    d2 = 0 if d2 >= 10 else d2
    return nums[12] == d1 and nums[13] == d2


# -----------------------------
# FarmForm
# -----------------------------


class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ["nome", "matricula", "car_recibo", "proprietario_nome", "proprietario_cpf"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "placeholder": "Nome da fazenda",
                    "autocomplete": "off",
                    "class": "form-control",
                }
            ),
            "matricula": forms.TextInput(
                attrs={
                    "placeholder": "Matrícula",
                    "autocomplete": "off",
                    "class": "form-control",
                }
            ),
            "car_recibo": forms.TextInput(
                attrs={
                    "class": "form-control mask-car",
                    "placeholder": "UF-1234567-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                    "style": "text-transform:uppercase;",
                    "autocomplete": "off",
                }
            ),
            "proprietario_nome": forms.TextInput(
                attrs={
                    "placeholder": "Nome do proprietário",
                    "autocomplete": "name",
                    "class": "form-control",
                }
            ),
            "proprietario_cpf": forms.TextInput(
                attrs={
                    "class": "form-control mask-doc",
                    "placeholder": "CPF ou CNPJ",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Permite a máscara completa de CNPJ (18 chars com pontuação)
        self.fields["proprietario_cpf"].widget.attrs["maxlength"] = 18

    # Normalizações leves de string
    def clean_nome(self) -> str:
        return (self.cleaned_data.get("nome") or "").strip()

    def clean_matricula(self) -> str:
        return (self.cleaned_data.get("matricula") or "").strip()

    def clean_proprietario_nome(self) -> str:
        return (self.cleaned_data.get("proprietario_nome") or "").strip()

    def clean_car_recibo(self) -> str:
        raw = (self.cleaned_data.get("car_recibo") or "").strip().upper()
        if not raw:
            return raw
        # Se já está no formato correto, aceite
        if CAR_PATTERN.match(raw):
            return raw
        # Tente normalizar: aceitar sem traços/extras, ex.: PA1506187... => PA-1506187-<32>
        alnum = re.sub(r"[^A-Z0-9]", "", raw)
        # 2 (UF) + 7 (número) + 32 (hash) = 41
        if len(alnum) == 41 and alnum[:2].isalpha() and alnum[2:9].isdigit() and alnum[9:].isalnum():
            formatted = f"{alnum[:2]}-{alnum[2:9]}-{alnum[9:]}"
            if CAR_PATTERN.match(formatted):
                return formatted
        raise forms.ValidationError(
            _("Formato inválido. Exemplo válido: UF-1234567-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        )

    def clean_proprietario_cpf(self) -> str:
        raw = self.cleaned_data.get("proprietario_cpf") or ""
        digits = only_digits(raw)
        if len(digits) == 11:
            if not validate_cpf(digits):
                raise forms.ValidationError(_("CPF inválido."))
        elif len(digits) == 14:
            if not validate_cnpj(digits):
                raise forms.ValidationError(_("CNPJ inválido."))
        else:
            raise forms.ValidationError(_("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos) válido."))
        return digits  # persistimos só dígitos


# -----------------------------
# DocumentForm
# -----------------------------


class DocumentForm(forms.ModelForm):
    # Lembretes (tabela própria associada)
    lembretes = forms.MultipleChoiceField(
        label=_("Lembretes"),
        required=False,
        choices=DocumentReminder.OPTIONS,
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "list-unstyled d-flex flex-wrap gap-3",
            }
        ),
    )

    class Meta:
        model = Document
        fields = [
            "farm",
            "nome",
            "data_emissao",
            "data_vencimento",
            "tipo",
            "notify_email",
            "notify_whatsapp",
        ]
        widgets = {
            "farm": forms.Select(
                attrs={
                    "placeholder": _("Selecione a fazenda"),
                    "class": "form-select",
                    "autocomplete": "off",
                }
            ),
            "nome": forms.TextInput(
                attrs={
                    "placeholder": _("Nome do documento"),
                    "class": "form-control",
                    "autocomplete": "off",
                }
            ),
            "data_emissao": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "data-role": "emissao",
                    "autocomplete": "off",
                },
                format="%Y-%m-%d",
            ),
            "data_vencimento": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "data-role": "vencimento",
                    "data-min-from": "data_emissao",
                    "autocomplete": "off",
                },
                format="%Y-%m-%d",
            ),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "notify_email": forms.EmailInput(
                attrs={
                    "placeholder": "email@exemplo.com",
                    "class": "form-control",
                    "autocomplete": "email",
                }
            ),
            "notify_whatsapp": forms.TextInput(
                attrs={
                    "class": "form-control phone-input",
                    "type": "tel",
                    "placeholder": "(00) 0 0000-0000",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "data-iti-separate": "false",
                    "aria-describedby": "hint-whatsapp",
                }
            ),
        }

    def __init__(self, *args, user: Optional[User] = None, **kwargs) -> None:
        self.user = user
        super().__init__(*args, **kwargs)

        # Limita farms ao owner
        if user:
            self.fields["farm"].queryset = Farm.objects.filter(owner=user)
            if not self.instance.pk:
                self.instance.created_by = user

        # Inicializa lembretes atuais para edição
        if self.instance and self.instance.pk:
            existing = list(self.instance.reminders.values_list("days_before", flat=True))
            self.fields["lembretes"].initial = existing

        # Placeholders curtos
        self.fields["nome"].widget.attrs.setdefault("placeholder", "Ex.: Certidão, Licença, Contrato...")
        self.fields["notify_whatsapp"].widget.attrs.setdefault("placeholder", "(00) 0 0000-0000")

    def clean(self):
        """Validação cruzada amistosa (o model pode ter um clean também)."""
        cleaned = super().clean()
        de = cleaned.get("data_emissao")
        ate = cleaned.get("data_vencimento")
        if de and ate and de > ate:
            raise ValidationError({"data_vencimento": _("A data de vencimento deve ser posterior à emissão.")})
        return cleaned

    def clean_notify_whatsapp(self) -> str:
        raw = (self.cleaned_data.get("notify_whatsapp") or "").strip()
        if not raw:
            return raw
        # Normaliza caracteres comuns de formatação
        raw = re.sub(r"[\s\-\(\)]", "", raw)
        # Se vier nacional (sem +), assume Brasil (+55)
        if not raw.startswith("+"):
            raw = "+55" + raw
        if not E164_RE.match(raw):
            raise forms.ValidationError(_("Informe um número válido (ex.: +5511999999999)."))
        return raw

    @transaction.atomic
    def save(self, commit: bool = True) -> Document:
        doc: Document = super().save(commit=False)
        if self.user and not doc.pk:
            doc.created_by = self.user

        # Valida regras do model
        doc.full_clean()

        if commit:
            doc.save()

        # Sincroniza lembretes de forma idempotente
        selected_days = list(map(int, self.cleaned_data.get("lembretes", [])))
        selected_set = set(selected_days)
        current_set = set(doc.reminders.values_list("days_before", flat=True))

        to_add = selected_set - current_set
        to_remove = current_set - selected_set

        if to_add:
            DocumentReminder.objects.bulk_create(
                [DocumentReminder(document=doc, days_before=d) for d in sorted(to_add)]
            )
        if to_remove:
            doc.reminders.filter(days_before__in=to_remove).delete()

        if commit:
            self.save_m2m()

        return doc


# -----------------------------
# Filtros (Farm e Document)
# -----------------------------


class FarmFilterForm(forms.Form):
    nome = forms.CharField(label=_("Nome"), required=False)
    matricula = forms.CharField(label=_("Matrícula"), required=False)
    car_recibo = forms.CharField(label=_("Recibo CAR"), required=False)
    proprietario_nome = forms.CharField(label=_("Proprietário"), required=False)
    proprietario_cpf = forms.CharField(
        label=_("CPF do proprietário"),
        required=False,
        help_text=_("Aceita com ou sem pontuação"),
    )
    q = forms.CharField(
        label=_("Busca"),
        required=False,
        help_text=_("Busca por nome, matrícula, CAR, proprietário, CPF"),
    )

    def clean_proprietario_cpf(self) -> str:
        v = self.cleaned_data.get("proprietario_cpf", "") or ""
        return only_digits(v)


class DocumentFilterForm(forms.Form):
    # Filtros principais (email e whatsapp REMOVIDOS)
    nome = forms.CharField(label=_("Nome"), required=False)
    fazenda = forms.CharField(label=_("Fazenda (nome)"), required=False)
    tipo = forms.ChoiceField(label=_("Tipo"), required=False, choices=[("", _("Todos"))])

    # Intervalos de datas
    data_emissao_de = forms.DateField(
        label=_("Emissão de"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    data_emissao_ate = forms.DateField(
        label=_("Emissão até"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    data_vencimento_de = forms.DateField(
        label=_("Vencimento de"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    data_vencimento_ate = forms.DateField(
        label=_("Vencimento até"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    q = forms.CharField(
        label=_("Busca"),
        required=False,
        help_text=_("Busca por nome, tipo, fazenda e também por e-mail/WhatsApp se necessário"),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Popular choices dinamicamente a partir do field choices do model (se houver)
        try:
            field = Document._meta.get_field("tipo")
            choices = getattr(field, "choices", None)
            if choices:
                self.fields["tipo"].choices = [("", _("Todos"))] + list(choices)
        except Exception:
            # Em caso de ausência do campo ou de choices, mantemos "Todos"
            pass
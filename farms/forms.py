from django import forms
from django.contrib.auth import get_user_model
from .models import Farm, Document, DocumentReminder
import re

User = get_user_model()

ONLY_DIGITS_RE = re.compile(r'\D+')
# Aceita qualquer UF (2 letras), 7 dígitos, 32 alfanum maiúsculos
CAR_PATTERN = re.compile(r'^[A-Z]{2}-\d{7}-[A-Z0-9]{32}$')
# E.164: + e até 15 dígitos (sem espaços, sem pontuação)
E164_RE = re.compile(r'^\+?[1-9]\d{1,14}$')


def validate_cpf(digits: str) -> bool:
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


class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['nome', 'matricula', 'car_recibo', 'proprietario_nome', 'proprietario_cpf']
        widgets = {
            'nome': forms.TextInput(attrs={
                'placeholder': 'Nome da fazenda',
                'autocomplete': 'off',
                'class': 'form-control',
            }),
            'matricula': forms.TextInput(attrs={
                'placeholder': 'Matrícula',
                'autocomplete': 'off',
                'class': 'form-control',
            }),
            'car_recibo': forms.TextInput(attrs={
                'class': 'form-control mask-car',
                'placeholder': 'UF-1234567-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
                'style': 'text-transform:uppercase;',
                'autocomplete': 'off'
            }),
            'proprietario_nome': forms.TextInput(attrs={
                'placeholder': 'Nome do proprietário',
                'autocomplete': 'name',
                'class': 'form-control',
            }),
            'proprietario_cpf': forms.TextInput(attrs={
                'class': 'form-control mask-doc',
                'placeholder': 'CPF ou CNPJ',
                'inputmode': 'numeric',
                'autocomplete': 'off',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Permite a máscara completa de CNPJ (18 chars com pontuação)
        self.fields['proprietario_cpf'].widget.attrs['maxlength'] = 18

    def clean_car_recibo(self):
        raw = (self.cleaned_data.get('car_recibo') or '').strip().upper()
        if not raw:
            return raw
        # Se já está no formato correto, aceite
        if CAR_PATTERN.match(raw):
            return raw
        # Tente normalizar: aceitar sem traços, ex.: PA1506187410... => PA-1506187-<32>
        alnum = re.sub(r'[^A-Z0-9]', '', raw).upper()
        # Deve ter 2 (UF) + 7 (número) + 32 (hash) = 41 caracteres
        if len(alnum) == 41 and alnum[:2].isalpha() and alnum[2:9].isdigit() and alnum[9:].isalnum():
            formatted = f'{alnum[:2]}-{alnum[2:9]}-{alnum[9:]}'
            if CAR_PATTERN.match(formatted):
                return formatted
        raise forms.ValidationError('Formato inválido. Exemplo válido: UF-1234567-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')

    def clean_proprietario_cpf(self):
        raw = self.cleaned_data.get('proprietario_cpf') or ''
        digits = ONLY_DIGITS_RE.sub('', raw)
        if len(digits) == 11:
            if not validate_cpf(digits):
                raise forms.ValidationError('CPF inválido.')
        elif len(digits) == 14:
            if not validate_cnpj(digits):
                raise forms.ValidationError('CNPJ inválido.')
        else:
            raise forms.ValidationError('Informe um CPF (11 dígitos) ou CNPJ (14 dígitos) válido.')
        return digits


class DocumentForm(forms.ModelForm):
    lembretes = forms.MultipleChoiceField(
        label='Lembretes',
        required=False,
        choices=DocumentReminder.OPTIONS,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'list-unstyled d-flex flex-wrap gap-3',  # compacto horizontal
        })
    )

    class Meta:
        model = Document
        fields = [
            'farm', 'nome', 'data_emissao', 'data_vencimento',
            'tipo', 'notify_email', 'notify_whatsapp',
        ]
        widgets = {
            'farm': forms.Select(attrs={
                'placeholder': 'Selecione a fazenda',
                'class': 'form-select',
            }),
            'nome': forms.TextInput(attrs={
                'placeholder': 'Nome do documento',
                'class': 'form-control',
            }),
            # DateInputs com data-attributes para o JS relacionar min/max
            'data_emissao': forms.DateInput(
                attrs={
                    'class': 'form-control date-picker',
                    'placeholder': 'DD/MM/AAAA',
                    'autocomplete': 'off',
                    'data-role': 'emissao',
                },
                format='%Y-%m-%d'
            ),
            'data_vencimento': forms.DateInput(
                attrs={
                    'class': 'form-control date-picker',
                    'placeholder': 'DD/MM/AAAA',
                    'autocomplete': 'off',
                    'data-role': 'vencimento',
                    'data-min-from': 'data_emissao',  # interpretado no JS
                },
                format='%Y-%m-%d'
            ),
            'tipo': forms.Select(attrs={
                'class': 'form-select',
            }),
            'notify_email': forms.EmailInput(attrs={
                'placeholder': 'email@exemplo.com',
                'class': 'form-control',
            }),
            # Com separateDialCode=false no JS, usar form-control aqui é seguro
            'notify_whatsapp': forms.TextInput(attrs={
                'class': 'form-control phone-input',
                'type': 'tel',
                'placeholder': '(00) 0 0000-0000',
                'autocomplete': 'tel',
                'inputmode': 'tel',
                # dicas para o JS (documentação própria)
                'data-iti-separate': 'false',
                'aria-describedby': 'hint-whatsapp',
            }),
        }

    def __init__(self, *args, user: User = None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user:
            self.fields['farm'].queryset = Farm.objects.filter(owner=user)
            if not self.instance.pk:
                self.instance.created_by = user
        if self.instance and self.instance.pk:
            existing = list(self.instance.reminders.values_list('days_before', flat=True))
            self.fields['lembretes'].initial = existing

        # Placeholders curtos para reduzir altura visual quando o texto quebra
        self.fields['nome'].widget.attrs.setdefault('placeholder', 'Ex.: Certidão, Licença, Contrato...')
        self.fields['notify_whatsapp'].widget.attrs.setdefault('placeholder', '(00) 0 0000-0000')

    def clean_notify_whatsapp(self):
        raw = (self.cleaned_data.get('notify_whatsapp') or '').strip()
        if not raw:
            return raw
        # Normaliza caracteres comuns de formatação
        raw = re.sub(r'[\s\-\(\)]', '', raw)
        # Se vier nacional (sem +), assume Brasil (+55). O JS normalmente envia E.164.
        if not raw.startswith('+'):
            raw = '+55' + raw
        if not E164_RE.match(raw):
            raise forms.ValidationError('Informe um número válido (ex.: +5511999999999).')
        return raw

    def save(self, commit=True):
        doc = super().save(commit=False)
        if self.user and not doc.pk:
            doc.created_by = self.user
        # Valida regras do model (inclusive emissão <= vencimento, se houver)
        doc.full_clean()
        if commit:
            doc.save()

        # Sincroniza lembretes de forma idempotente
        selected = list(map(int, self.cleaned_data.get('lembretes', [])))
        current = set(self.instance.reminders.values_list('days_before', flat=True))
        to_add = set(selected) - current
        to_remove = current - set(selected)
        for d in to_add:
            DocumentReminder.objects.create(document=doc, days_before=d)
        if to_remove:
            self.instance.reminders.filter(days_before__in=to_remove).delete()

        return doc
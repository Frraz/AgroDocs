import secrets
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class InviteCode(models.Model):
    # IMPORTANTE: não é único. Isso permite reusar o MESMO code em novos convites.
    code = models.CharField('Código', max_length=64, db_index=True, blank=True)
    label = models.CharField('Descrição', max_length=200, blank=True)

    # Uso único por registro
    max_uses = models.PositiveIntegerField('Máximo de usos', default=1, help_text='Uso único (1).')
    uses = models.PositiveIntegerField('Usos', default=0)

    # Expira em 24h por padrão (definido automaticamente no save)
    expires_at = models.DateTimeField('Expira em', null=True, blank=True)
    is_active = models.BooleanField('Ativo', default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='created_invites',
        verbose_name='Criado por',
    )
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    # Auditoria de resgate
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='used_invites',
        verbose_name='Usado por',
    )
    redeemed_at = models.DateTimeField('Usado em', null=True, blank=True)

    class Meta:
        verbose_name = 'Convite'
        verbose_name_plural = 'Convites'
        ordering = ['-created_at']

    def __str__(self):
        status = 'ativo' if self.is_active else 'inativo'
        return f'{self.code or "(auto)"} ({status})'

    @property
    def remaining_uses(self):
        return max(self.max_uses - self.uses, 0)

    def is_usable_now(self):
        # Ativo, não usado, e não expirado
        if not self.is_active:
            return False
        if self.uses >= 1:
            return False
        if not self.expires_at:
            return False
        return timezone.now() <= self.expires_at

    def clean(self):
        # Definir defaults para validar corretamente
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        if not self.code:
            self.code = secrets.token_urlsafe(12)

        # Impedir coexistência de mais de um convite "usável" com o MESMO code
        # (evita dois cadastros simultâneos com o mesmo código).
        if self.is_active and self.uses < 1 and self.expires_at and self.code:
            qs = InviteCode.objects.filter(code=self.code, is_active=True, uses__lt=1, expires_at__gt=timezone.now())
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('Já existe um convite ativo e não utilizado com este código. Aguarde o uso/expiração ou desative-o antes de criar outro com o mesmo código.')

    def save(self, *args, **kwargs):
        # Defaults automáticos
        if not self.code:
            self.code = secrets.token_urlsafe(12)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)

        # Se já marcado como usado, sincroniza flags
        if self.used_by_id:
            self.uses = 1
            self.is_active = False
            if not self.redeemed_at:
                self.redeemed_at = timezone.now()

        # Validação de coexistência
        self.full_clean()
        super().save(*args, **kwargs)


class AccountStatus(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='account_status', verbose_name='Usuário')
    suspended_until = models.DateTimeField('Suspenso até', null=True, blank=True)
    reason = models.CharField('Motivo do bloqueio', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Status de Conta'
        verbose_name_plural = 'Status de Contas'

    def __str__(self):
        return f'Status de {self.user}'

    @property
    def is_suspended_now(self):
        return bool(self.suspended_until and timezone.now() < self.suspended_until)
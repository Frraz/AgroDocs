from datetime import timedelta
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import InviteCode, AccountStatus


# Action: desativar e recriar convite com o mesmo código
def regenerar_mesmo_codigo(modeladmin, request, queryset):
    """Desativa o convite atual (se necessário) e cria um novo com o MESMO código (24h, uso único)."""
    criados = 0
    for obj in queryset:
        if obj.is_active and obj.uses < 1 and (not obj.expires_at or obj.expires_at > timezone.now()):
            obj.is_active = False
            obj.expires_at = timezone.now()
            obj.save(update_fields=['is_active', 'expires_at', 'updated_at'])
        InviteCode.objects.create(
            code=obj.code,
            label=obj.label,
            is_active=True,
            max_uses=1,
        )
        criados += 1
    messages.success(request, f'{criados} convite(s) recriado(s) com o mesmo código.')
regenerar_mesmo_codigo.short_description = 'Desativar e recriar com o mesmo código'


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'label', 'is_active', 'uses', 'expires_at',
        'used_by', 'redeemed_at', 'created_by', 'created_at',
    )
    list_filter = ('is_active', 'expires_at', 'redeemed_at')
    search_fields = ('code', 'label', 'used_by__username', 'created_by__username')
    readonly_fields = ('uses', 'redeemed_at', 'created_at', 'updated_at')
    actions = [regenerar_mesmo_codigo]
    fieldsets = (
        (None, {'fields': ('label', 'code')}),
        ('Validade e uso', {'fields': ('expires_at', 'is_active', 'uses')}),
        ('Auditoria', {'fields': ('used_by', 'redeemed_at', 'created_by', 'created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AccountStatus)
class AccountStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'suspended_until', 'reason')
    list_filter = ('suspended_until',)
    search_fields = ('user__username', 'user__email', 'reason')
    fields = ('user', 'suspended_until', 'reason')

    def save_model(self, request, obj, form, change):
        # Impede suspender a si próprio
        if obj.user_id == request.user.id:
            raise ValidationError('Você não pode suspender sua própria conta.')
        # Garante que reste pelo menos um superusuário ativo
        User = get_user_model()
        if obj.suspended_until and obj.user.is_superuser and obj.user.is_active:
            others = User.objects.filter(is_superuser=True, is_active=True).exclude(id=obj.user_id).exists()
            if not others:
                raise ValidationError('Não é permitido suspender o único superusuário ativo.')
        super().save_model(request, obj, form, change)


# Inline para editar bloqueio na página do usuário
class AccountStatusInline(admin.StackedInline):
    model = AccountStatus
    can_delete = False
    fk_name = 'user'
    extra = 0
    verbose_name_plural = 'Status de Conta (bloqueio temporário)'


# Ações rápidas no User admin
def suspender_7_dias(modeladmin, request, queryset):
    until = timezone.now() + timedelta(days=7)
    count = 0
    for user in queryset:
        # Não suspender o próprio admin se for o único superusuário
        if user == request.user:
            continue
        if user.is_superuser and user.is_active:
            User = get_user_model()
            others = User.objects.filter(is_superuser=True, is_active=True).exclude(id=user.id).exists()
            if not others:
                continue
        status, _ = AccountStatus.objects.get_or_create(user=user)
        status.suspended_until = until
        status.reason = status.reason or 'Suspensão administrativa por 7 dias.'
        status.save(update_fields=['suspended_until', 'reason'])
        count += 1
    messages.success(request, f'{count} usuário(s) suspenso(s) por 7 dias.')
suspender_7_dias.short_description = 'Suspender por 7 dias'


def remover_bloqueio(modeladmin, request, queryset):
    count = 0
    for user in queryset:
        updated = AccountStatus.objects.filter(user=user).update(suspended_until=None, reason='')
        count += updated
    messages.success(request, f'Bloqueio removido de {count} usuário(s).')
remover_bloqueio.short_description = 'Remover bloqueio'


# Substitui o UserAdmin padrão para incluir inline e ações
User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [AccountStatusInline]
    actions = [suspender_7_dias, remover_bloqueio]
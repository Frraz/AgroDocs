from django.contrib import admin
from .models import Farm, Document, DocumentReminder, NotificationLog

class DocumentReminderInline(admin.TabularInline):
    model = DocumentReminder
    extra = 0

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('nome', 'matricula', 'owner', 'proprietario_nome', 'proprietario_cpf')
    search_fields = ('nome', 'matricula', 'proprietario_nome', 'proprietario_cpf')
    list_filter = ('owner',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('nome', 'farm', 'created_by', 'tipo', 'data_emissao', 'data_vencimento')
    list_filter = ('tipo', 'data_vencimento')
    search_fields = ('nome', 'farm__nome')
    inlines = [DocumentReminderInline]

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('document', 'days_before', 'sent_on')
    list_filter = ('days_before', 'sent_on')
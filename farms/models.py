from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

PHONE_E164 = RegexValidator(
    regex=r'^\+?[1-9]\d{1,14}$',
    message='Informe o número em formato internacional E.164. Ex: +5511999999999'
)

class Farm(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farms')
    nome = models.CharField(max_length=200)
    matricula = models.CharField(max_length=100)
    car_recibo = models.CharField(max_length=100, blank=True, null=True)
    proprietario_nome = models.CharField(max_length=200)
    # Agora aceita CPF (11) ou CNPJ (14) — salvamos apenas dígitos
    proprietario_cpf = models.CharField('CPF/CNPJ', max_length=14)

    class Meta:
        verbose_name = 'Fazenda'
        verbose_name_plural = 'Fazendas'
        constraints = [
            models.UniqueConstraint(fields=['owner', 'matricula'], name='uniq_owner_matricula')
        ]

    def __str__(self):
        return f'{self.nome} ({self.matricula})'

class Document(models.Model):
    TIPO_CERTIDAO = 'certidao'
    TIPO_CONTRATO = 'contrato'
    TIPO_LICENCA = 'licenca'
    TIPO_OUTRO = 'outro'
    TIPOS = [
        (TIPO_CERTIDAO, 'Certidão'),
        (TIPO_CONTRATO, 'Contrato'),
        (TIPO_LICENCA, 'Licença'),
        (TIPO_OUTRO, 'Outro'),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='documents')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    nome = models.CharField(max_length=200)
    data_emissao = models.DateField()
    data_vencimento = models.DateField(db_index=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    notify_email = models.EmailField()
    notify_whatsapp = models.CharField(max_length=20, validators=[PHONE_E164])

    class Meta:
        ordering = ['data_vencimento', 'nome']
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'

    def clean(self):
        if self.farm_id and self.created_by_id:
            if self.farm.owner_id != self.created_by_id:
                raise ValidationError('Você só pode vincular documentos às suas próprias fazendas.')
        if self.data_emissao and self.data_vencimento and self.data_vencimento < self.data_emissao:
            raise ValidationError('Data de vencimento não pode ser anterior à emissão.')

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'

class DocumentReminder(models.Model):
    OPTIONS = (
        (1, '1 dia antes'),
        (3, '3 dias antes'),
        (7, '7 dias antes'),
        (30, '1 mês antes'),
    )
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='reminders')
    days_before = models.PositiveIntegerField(choices=OPTIONS)

    class Meta:
        unique_together = ('document', 'days_before')
        verbose_name = 'Lembrete'
        verbose_name_plural = 'Lembretes'

    def __str__(self):
        return f'{self.days_before} dia(s) antes de {self.document}'

class NotificationLog(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='notification_logs')
    days_before = models.PositiveIntegerField()
    sent_on = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = ('document', 'days_before', 'sent_on')
        verbose_name = 'Log de Notificação'
        verbose_name_plural = 'Logs de Notificações'

    def __str__(self):
        return f'Notificação {self.days_before}d para {self.document} em {self.sent_on}'
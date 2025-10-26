from django.conf import settings
from django.core.mail import send_mail
from twilio.rest import Client

def send_document_email(document, subject, message):
    recipient = document.notify_email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )

def send_document_whatsapp(document, message):
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        # Twilio não configurado; apenas ignore ou logue em produção
        return
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        from_=settings.TWILIO_WHATSAPP_FROM,
        to=f'whatsapp:{document.notify_whatsapp}' if not document.notify_whatsapp.startswith('whatsapp:') else document.notify_whatsapp,
        body=message
    )

def build_notification_messages(document, days_before):
    subject = f'Lembrete: "{document.nome}" vence em {days_before} dia(s)'
    message = (
        f'Olá,\n\n'
        f'O documento "{document.nome}" ({document.get_tipo_display()}) da fazenda "{document.farm.nome}" '
        f'vence em {days_before} dia(s), na data {document.data_vencimento.strftime("%d/%m/%Y")}.\n\n'
        f'Proprietário: {document.farm.proprietario_nome} (CPF: {document.farm.proprietario_cpf})\n'
        f'Matrícula: {document.farm.matricula}\n\n'
        f'AgroDocs'
    )
    return subject, message

def notify_document(document, days_before):
    subject, message = build_notification_messages(document, days_before)
    send_document_email(document, subject, message)
    send_document_whatsapp(document, message)
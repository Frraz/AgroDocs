""" farms/services/notifications.py """

import logging
import re
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from twilio.rest import Client

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    pass


class NotConfiguredError(NotificationError):
    """Indica que a integração não está configurada (ex.: credenciais do Twilio ausentes)."""


# ==========
# EXISTENTES
# ==========

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
    to = normalize_phone_to_e164(document.notify_whatsapp, default_country_code="+55")
    client.messages.create(
        from_=settings.TWILIO_WHATSAPP_FROM,
        to=f"whatsapp:{to}",
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


# ==========
# NOVOS: NORMALIZAÇÃO E TESTES
# ==========

E164_RE = re.compile(r"^\+?[1-9]\d{1,14}$")


def normalize_phone_to_e164(raw: str, default_country_code: str = "+55") -> str:
    """
    Normaliza um número para E.164:
    - Aceita entradas como 'whatsapp:+55...', '+55...', '94 99208-3253', '(94) 99208-3253'
    - Remove espaços, hífens, parênteses
    - Se não começar com '+', prefixa default_country_code (padrão +55)
    - Valida E.164 final
    Retorna o número em E.164 (ex.: '+5594992083253') ou levanta NotificationError.
    """
    if not raw:
        raise NotificationError("Informe um número WhatsApp.")

    value = str(raw).strip()
    if value.lower().startswith("whatsapp:"):
        value = value.split(":", 1)[1].strip()

    # remove espaços, hífens, parênteses
    value = re.sub(r"[()\s\-]", "", value)

    if not value:
        raise NotificationError("Informe um número WhatsApp.")

    if not value.startswith("+"):
        value = f"{default_country_code}{value}"

    # valida E.164
    if not E164_RE.match(value):
        raise NotificationError("WhatsApp inválido. Use formato E.164, ex.: +5511999999999.")

    return value


def _twilio_client():
    sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    from_whatsapp = getattr(settings, "TWILIO_WHATSAPP_FROM", None)  # ex.: 'whatsapp:+14155238886'
    if not sid or not token or not from_whatsapp:
        raise NotConfiguredError(
            "Twilio não configurado. Defina TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_WHATSAPP_FROM em settings."
        )
    return Client(sid, token), from_whatsapp


def send_test_email(to_email: str, user, subject: Optional[str] = None, body: Optional[str] = None) -> str:
    """
    Envia e-mail de teste. Retorna um identificador simples ex.: 'ok-1'.
    """
    try:
        validate_email(to_email)
    except DjangoValidationError:
        raise NotificationError("E-mail inválido.")

    subject = subject or "Teste de notificação - AgroDocs"
    body = body or f"Olá {user.get_username()}, este é um e-mail de teste de notificação do AgroDocs."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    try:
        sent = send_mail(subject, body, from_email, [to_email], fail_silently=False)
        if sent <= 0:
            raise NotificationError("Falha ao enviar o e-mail de teste.")
        return f"ok-{sent}"
    except Exception as e:
        logger.exception("Falha ao enviar e-mail de teste")
        raise NotificationError(f"Erro ao enviar e-mail: {e}") from e


def send_test_whatsapp(to_value: str, user, body: Optional[str] = None) -> str:
    """
    Envia WhatsApp de teste via Twilio. Aceita '+5511...', 'whatsapp:+5511...', '(11) 9....'
    Retorna o SID da mensagem em caso de sucesso.
    """
    # Normaliza para E.164
    e164 = normalize_phone_to_e164(to_value, default_country_code="+55")

    try:
        client, from_whatsapp = _twilio_client()
    except Exception as e:
        if isinstance(e, NotConfiguredError):
            raise
        logger.exception("Twilio não disponível")
        raise NotConfiguredError("Pacote/configuração Twilio ausente. Instale 'twilio' e configure credenciais.") from e

    body = body or f"Olá {user.get_username()}, esta é uma mensagem de teste WhatsApp do AgroDocs."

    try:
        msg = client.messages.create(body=body, from_=from_whatsapp, to=f"whatsapp:{e164}")
        return msg.sid
    except Exception as e:
        logger.exception("Falha ao enviar WhatsApp de teste")
        raise NotificationError(f"Erro ao enviar WhatsApp: {e}") from e
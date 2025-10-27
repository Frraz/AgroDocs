from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from farms.models import DocumentReminder, NotificationLog
from farms.services.notifications import notify_document

class Command(BaseCommand):
    help = 'Envia notificações de documentos conforme lembretes configurados.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Mostra o que seria enviado, sem enviar de fato.')

    def handle(self, *args, **options):
        today = timezone.localdate()
        dry_run = options['dry_run']
        count = 0

        reminders = DocumentReminder.objects.select_related('document', 'document__farm')
        for reminder in reminders:
            target_date = today + timedelta(days=reminder.days_before)
            doc = reminder.document
            if doc.data_vencimento == target_date:
                # Evita duplicidade no mesmo dia
                log_exists = NotificationLog.objects.filter(
                    document=doc,
                    days_before=reminder.days_before,
                    sent_on=today
                ).exists()
                if log_exists:
                    continue

                if dry_run:
                    self.stdout.write(self.style.NOTICE(
                        f'[DRY-RUN] Enviaria lembrete {reminder.days_before}d para "{doc.nome}" (vence {doc.data_vencimento})'
                    ))
                else:
                    notify_document(doc, reminder.days_before)
                    NotificationLog.objects.create(
                        document=doc,
                        days_before=reminder.days_before,
                        sent_on=today
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'Enviado lembrete {reminder.days_before}d para "{doc.nome}"'
                    ))
                count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY-RUN] Total de notificações simuladas: {count}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Total de notificações enviadas: {count}'))
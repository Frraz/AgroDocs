""" Como usar:
Desbloquear e reativar: python manage.py unsuspend_user --username SEU_USERNAME """

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from accounts.models import AccountStatus

User = get_user_model()

class Command(BaseCommand):
    help = 'Reativa/desbloqueia um usuário. Uso: --username USERNAME (ou --email EMAIL).'

    def add_arguments(self, parser):
        parser.add_argument('--username', help='Username do usuário.')
        parser.add_argument('--email', help='E-mail do usuário.')
        parser.add_argument('--promote', action='store_true', help='Também torna is_staff e is_superuser.')
        parser.add_argument('--just-clear', action='store_true', help='Apenas limpa bloqueio (sem alterar is_active).')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')

        if not username and not email:
            raise CommandError('Informe --username ou --email.')

        try:
            if username:
                user = User.objects.get(username=username)
            else:
                user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError('Usuário não encontrado.')

        # Limpa bloqueio
        AccountStatus.objects.filter(user=user).update(suspended_until=None, reason='')

        if not options['just_clear']:
            user.is_active = True
            if options['promote']:
                user.is_staff = True
                user.is_superuser = True
            user.save()

        msg = f'Usuário {user.username} desbloqueado'
        if not options['just_clear']:
            msg += ' e reativado'
            if options['promote']:
                msg += ' (promovido a staff/superuser)'
        msg += '.'
        self.stdout.write(self.style.SUCCESS(msg))
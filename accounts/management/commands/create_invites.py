import secrets
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import InviteCode


class Command(BaseCommand):
    help = 'Cria código(s) de convite (uso único, expira em 24h por padrão).'

    def add_arguments(self, parser):
        parser.add_argument('--code', help='Código personalizado (opcional). Se não informado, é gerado.')
        parser.add_argument('--label', help='Descrição/nota do(s) convite(s).', default='')
        parser.add_argument('--expires', help='YYYY-MM-DD ou YYYY-MM-DDTHH:MM (opcional).')
        parser.add_argument('--count', type=int, default=1, help='Quantidade de convites (padrão: 1).')

    def handle(self, *args, **options):
        label = options['label'] or ''
        count = options['count'] or 1
        code_fixed = options.get('code')

        expires_at = None
        expires_str = options.get('expires')
        if expires_str:
            try:
                if 'T' in expires_str:
                    expires_at = datetime.fromisoformat(expires_str)
                else:
                    expires_at = datetime.fromisoformat(expires_str + 'T23:59')
                if timezone.is_naive(expires_at):
                    expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
            except ValueError:
                raise CommandError('Formato de --expires inválido. Use YYYY-MM-DD ou YYYY-MM-DDTHH:MM')

        # Regra para evitar dois convites ATIVOS usáveis com o mesmo code:
        # Se --code for informado e existir um convite usável com esse code, bloqueia.
        if code_fixed:
            exists_usable = InviteCode.objects.filter(
                code=code_fixed, is_active=True, uses__lt=1, expires_at__gt=timezone.now()
            ).exists()
            if exists_usable:
                raise CommandError('Já existe um convite ativo e não utilizado com este código. Aguarde uso/expiração ou desative-o antes de criar outro com o mesmo código.')

        codes = []
        for i in range(count):
            code = code_fixed or secrets.token_urlsafe(12)
            invite = InviteCode.objects.create(
                code=code,
                label=label,
                expires_at=expires_at or (timezone.now() + timedelta(hours=24)),
                is_active=True,
                max_uses=1,
            )
            codes.append(invite.code)

        self.stdout.write(self.style.SUCCESS(f'Criados {len(codes)} convite(s):'))
        for c in codes:
            self.stdout.write(f'- {c}')
        self.stdout.write('Obs.: cada convite é de uso único e expira em 24h por padrão. Você pode reutilizar o mesmo código criando um novo convite após o uso/expiração.')
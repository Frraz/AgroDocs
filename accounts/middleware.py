from django.shortcuts import redirect
from django.contrib.auth import logout
from .models import AccountStatus


class SuspendedUserMiddleware:
    """
    Se o usuário estiver autenticado e suspenso, faz logout e redireciona para
    a página de bloqueio com mensagem genérica.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            status = AccountStatus.objects.filter(user=request.user).only('suspended_until').first()
            if status and status.is_suspended_now:
                logout(request)
                return redirect('accounts:blocked')
        return self.get_response(request)
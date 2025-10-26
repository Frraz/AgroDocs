from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Nossas URLs de accounts (inclui login custom com verificação de bloqueio)
    path('accounts/', include('accounts.urls', namespace='accounts')),
    # URLs padrão do auth (logout, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    path('', RedirectView.as_view(pattern_name='farms:farm-list', permanent=False)),
    path('farms/', include('farms.urls', namespace='farms')),
]
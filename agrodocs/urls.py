""" agrodocs/urls.py """

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Autenticação
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("accounts/", include("django.contrib.auth.urls")),

    # App Farms
    path("farms/", include(("farms.urls", "farms"), namespace="farms")),

    # Raiz do site → lista de fazendas
    path("", RedirectView.as_view(pattern_name="farms:farm_list", permanent=False), name="home"),
]

# Em desenvolvimento, serve arquivos de mídia (uploads)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
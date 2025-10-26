""" farms/urls.py """

from django.urls import path
from . import views

app_name = "farms"

urlpatterns = [
    # Fazendas
    path("", views.FarmListView.as_view(), name="farm_list"),
    path("new/", views.FarmCreateView.as_view(), name="farm_create"),
    path("<int:pk>/edit/", views.FarmUpdateView.as_view(), name="farm_update"),
    path("<int:pk>/delete/", views.FarmDeleteView.as_view(), name="farm_delete"),

    # Documentos
    path("documents/", views.DocumentListView.as_view(), name="document_list"),
    path("documents/new/", views.DocumentCreateView.as_view(), name="document_create"),
    path("documents/<int:pk>/edit/", views.DocumentUpdateView.as_view(), name="document_update"),
    path("documents/<int:pk>/delete/", views.DocumentDeleteView.as_view(), name="document_delete"),

    # API de Notificações (teste)
    path("notifications/test/", views.NotificationTestView.as_view(), name="notification_test"),
]
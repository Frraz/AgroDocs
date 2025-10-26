from django.urls import path
from . import views

app_name = 'farms'

urlpatterns = [
    path('', views.FarmListView.as_view(), name='farm-list'),
    path('new/', views.FarmCreateView.as_view(), name='farm-create'),
    path('<int:pk>/edit/', views.FarmUpdateView.as_view(), name='farm-update'),
    path('<int:pk>/delete/', views.FarmDeleteView.as_view(), name='farm-delete'),

    path('documents/', views.DocumentListView.as_view(), name='document-list'),
    path('documents/new/', views.DocumentCreateView.as_view(), name='document-create'),
    path('documents/<int:pk>/edit/', views.DocumentUpdateView.as_view(), name='document-update'),
    path('documents/<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='document-delete'),
]
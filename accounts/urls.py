from django.urls import path
from django.contrib.auth.views import LoginView
from .views import SignupView, BlockedView
from .forms import LoginForm

app_name = 'accounts'

urlpatterns = [
    # Login usando nosso formulário que valida bloqueios
    path('login/', LoginView.as_view(authentication_form=LoginForm), name='login'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('blocked/', BlockedView.as_view(), name='blocked'),
]
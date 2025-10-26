from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from .forms import SignupForm


class SignupView(FormView):
    template_name = 'registration/signup.html'
    form_class = SignupForm
    success_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, 'SIGNUP_ENABLED', True):
            return redirect('login')
        if request.user.is_authenticated:
            return redirect('farms:farm-list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class BlockedView(TemplateView):
    template_name = 'accounts/blocked.html'
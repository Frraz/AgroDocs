from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Farm, Document
from .forms import FarmForm, DocumentForm

# Fazendas
class FarmListView(LoginRequiredMixin, ListView):
    model = Farm
    template_name = 'farms/farm_list.html'
    context_object_name = 'farms'

    def get_queryset(self):
        return Farm.objects.filter(owner=self.request.user).order_by('nome')

class FarmCreateView(LoginRequiredMixin, CreateView):
    model = Farm
    form_class = FarmForm
    template_name = 'farms/farm_form.html'
    success_url = reverse_lazy('farms:farm-list')

    def form_valid(self, form):
        # Garanta que o owner seja o usuário logado e deixe o CreateView salvar/definir self.object
        form.instance.owner = self.request.user
        return super().form_valid(form)

class FarmUpdateView(LoginRequiredMixin, UpdateView):
    model = Farm
    form_class = FarmForm
    template_name = 'farms/farm_form.html'
    success_url = reverse_lazy('farms:farm-list')

    def get_queryset(self):
        return Farm.objects.filter(owner=self.request.user)

class FarmDeleteView(LoginRequiredMixin, DeleteView):
    model = Farm
    template_name = 'farms/farm_confirm_delete.html'
    success_url = reverse_lazy('farms:farm-list')

    def get_queryset(self):
        return Farm.objects.filter(owner=self.request.user)

# Documentos
class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'farms/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return Document.objects.filter(created_by=self.request.user).select_related('farm')

class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'farms/document_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('farms:document-list')

class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'farms/document_form.html'

    def get_queryset(self):
        return Document.objects.filter(created_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('farms:document-list')

class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    template_name = 'farms/document_confirm_delete.html'

    def get_queryset(self):
        return Document.objects.filter(created_by=self.request.user)

    def get_success_url(self):
        return reverse('farms:document-list')
""" farms/views.py """

"""
Views do app Farms com:
- Listagens com filtros e paginação (fazendas e documentos)
- CRUD com escopo por usuário (owner) e mensagens de sucesso
- Otimizações: select_related, ordering dinâmico (sort/dir), querystring no contexto
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Q, Value as V
from django.db.models.functions import Replace
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DocumentFilterForm, DocumentForm, FarmFilterForm, FarmForm
from .models import Document, Farm


# =============================
# Fazendas
# =============================


class FarmListView(LoginRequiredMixin, ListView):
    model = Farm
    template_name = "farms/farm_list.html"
    context_object_name = "farms"
    paginate_by = 20

    # campos permitidos para ordenação: chave -> expressão ORM
    SORT_MAP = {
        "nome": "nome",
        "matricula": "matricula",
    }

    def get_ordering(self):
        sort = (self.request.GET.get("sort") or "nome").strip()
        direction = (self.request.GET.get("dir") or "asc").strip().lower()
        field = self.SORT_MAP.get(sort, "nome")
        return (f"-{field}", "pk") if direction == "desc" else (field, "pk")

    def get_queryset(self):
        qs = Farm.objects.filter(owner=self.request.user)

        # Normaliza CPF do proprietário (remove . - /) para facilitar busca
        qs = qs.annotate(
            cpf_digits=Replace(
                Replace(
                    Replace(F("proprietario_cpf"), V("."), V("")),
                    V("-"),
                    V(""),
                ),
                V("/"),
                V(""),
            )
        )

        form = FarmFilterForm(self.request.GET or None)
        self.filter_form = form  # para o contexto

        if form.is_valid():
            cd = form.cleaned_data

            if cd.get("nome"):
                qs = qs.filter(nome__icontains=cd["nome"])
            if cd.get("matricula"):
                qs = qs.filter(matricula__icontains=cd["matricula"])
            if cd.get("car_recibo"):
                qs = qs.filter(car_recibo__icontains=cd["car_recibo"])
            if cd.get("proprietario_nome"):
                qs = qs.filter(proprietario_nome__icontains=cd["proprietario_nome"])
            if cd.get("proprietario_cpf"):
                qs = qs.filter(cpf_digits__icontains=cd["proprietario_cpf"])

            # Busca global
            q = cd.get("q")
            if q:
                q_digits = "".join(ch for ch in q if ch.isdigit())
                qs = qs.filter(
                    Q(nome__icontains=q)
                    | Q(matricula__icontains=q)
                    | Q(car_recibo__icontains=q)
                    | Q(proprietario_nome__icontains=q)
                    | Q(proprietario_cpf__icontains=q)
                    | Q(cpf_digits__icontains=q_digits)
                )

        return qs.order_by(*self.get_ordering())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = getattr(self, "filter_form", FarmFilterForm())
        # usados nos headers de ordenação
        ctx["current_sort"] = self.request.GET.get("sort") or "nome"
        ctx["current_dir"] = self.request.GET.get("dir") or "asc"
        return ctx


class FarmCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Farm
    form_class = FarmForm
    template_name = "farms/farm_form.html"
    success_url = reverse_lazy("farms:farm_list")
    success_message = "Fazenda criada com sucesso."

    def form_valid(self, form):
        # Garante owner = usuário logado
        form.instance.owner = self.request.user
        return super().form_valid(form)


class FarmUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Farm
    form_class = FarmForm
    template_name = "farms/farm_form.html"
    success_url = reverse_lazy("farms:farm_list")
    success_message = "Fazenda atualizada com sucesso."

    def get_queryset(self):
        return Farm.objects.filter(owner=self.request.user)


class FarmDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Farm
    template_name = "farms/farm_confirm_delete.html"
    success_url = reverse_lazy("farms:farm_list")
    success_message = "Fazenda removida com sucesso."

    def get_queryset(self):
        return Farm.objects.filter(owner=self.request.user)


# =============================
# Documentos
# =============================


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "farms/document_list.html"
    context_object_name = "documents"
    paginate_by = 20

    SORT_MAP = {
        "nome": "nome",
        "fazenda": "farm__nome",
        "data_emissao": "data_emissao",
        "data_vencimento": "data_vencimento",
    }

    def get_ordering(self):
        sort = (self.request.GET.get("sort") or "data_vencimento").strip()
        direction = (self.request.GET.get("dir") or "asc").strip().lower()
        field = self.SORT_MAP.get(sort, "data_vencimento")
        return (f"-{field}", "pk") if direction == "desc" else (field, "pk")

    def get_queryset(self):
        # Restringe por farms do usuário
        qs = Document.objects.filter(farm__owner=self.request.user).select_related("farm")

        form = DocumentFilterForm(self.request.GET or None)
        self.filter_form = form

        if form.is_valid():
            cd = form.cleaned_data

            if cd.get("nome"):
                qs = qs.filter(nome__icontains=cd["nome"])
            if cd.get("fazenda"):
                qs = qs.filter(farm__nome__icontains=cd["fazenda"])
            if cd.get("tipo"):
                qs = qs.filter(tipo=cd["tipo"])

            # Intervalos de data
            de = cd.get("data_emissao_de")
            ate = cd.get("data_emissao_ate")
            if de:
                qs = qs.filter(data_emissao__gte=de)
            if ate:
                qs = qs.filter(data_emissao__lte=ate)

            de = cd.get("data_vencimento_de")
            ate = cd.get("data_vencimento_ate")
            if de:
                qs = qs.filter(data_vencimento__gte=de)
            if ate:
                qs = qs.filter(data_vencimento__lte=ate)

            # Busca global (mantém possibilidade de buscar e-mail/WhatsApp por 'q')
            q = cd.get("q")
            if q:
                qs = qs.filter(
                    Q(nome__icontains=q)
                    | Q(tipo__icontains=q)
                    | Q(farm__nome__icontains=q)
                    | Q(farm__matricula__icontains=q)
                    | Q(notify_email__icontains=q)
                    | Q(notify_whatsapp__icontains=q)
                )

        return qs.order_by(*self.get_ordering())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = getattr(self, "filter_form", DocumentFilterForm())
        # usados nos headers de ordenação
        ctx["current_sort"] = self.request.GET.get("sort") or "data_vencimento"
        ctx["current_dir"] = self.request.GET.get("dir") or "asc"
        return ctx


class DocumentCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "farms/document_form.html"
    success_url = reverse_lazy("farms:document_list")
    success_message = "Documento criado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # DocumentForm limita farms e define created_by
        return kwargs


class DocumentUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = "farms/document_form.html"
    success_url = reverse_lazy("farms:document_list")
    success_message = "Documento atualizado com sucesso."

    def get_queryset(self):
        # Apenas documentos de farms do usuário
        return Document.objects.filter(farm__owner=self.request.user).select_related("farm")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class DocumentDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Document
    template_name = "farms/document_confirm_delete.html"
    success_url = reverse_lazy("farms:document_list")
    success_message = "Documento removido com sucesso."

    def get_queryset(self):
        return Document.objects.filter(farm__owner=self.request.user)
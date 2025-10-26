""" farms/views.py """

"""
Views do app Farms com:
- Listagens com filtros e paginação (fazendas e documentos)
- CRUD com escopo por usuário (owner) e mensagens de sucesso
- Otimizações: select_related, ordering dinâmico (sort/dir), querystring no contexto
- Endpoint para testar notificações (email/whatsapp)
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import F, Q, Value as V
from django.db.models.functions import Replace
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DocumentFilterForm, DocumentForm, FarmFilterForm, FarmForm
from .models import Document, Farm
from .services.notifications import (
    NotificationError,
    NotConfiguredError,
    send_test_email,
    send_test_whatsapp,
)

# =============================
# Fazendas
# =============================


class FarmListView(LoginRequiredMixin, ListView):
    model = Farm
    template_name = "farms/farm_list.html"
    context_object_name = "farms"
    paginate_by = 20

    SORT_MAP = {"nome": "nome", "matricula": "matricula"}

    def get_ordering(self):
        sort = (self.request.GET.get("sort") or "nome").strip()
        direction = (self.request.GET.get("dir") or "asc").strip().lower()
        field = self.SORT_MAP.get(sort, "nome")
        return (f"-{field}", "pk") if direction == "desc" else (field, "pk")

    def get_queryset(self):
        qs = Farm.objects.filter(owner=self.request.user)
        qs = qs.annotate(
            cpf_digits=Replace(
                Replace(Replace(F("proprietario_cpf"), V("."), V("")), V("-"), V("")),
                V("/"),
                V(""),
            )
        )
        form = FarmFilterForm(self.request.GET or None)
        self.filter_form = form
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
        kwargs["user"] = self.request.user
        return kwargs


class DocumentUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = "farms/document_form.html"
    success_url = reverse_lazy("farms:document_list")
    success_message = "Documento atualizado com sucesso."

    def get_queryset(self):
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


# =============================
# API: Teste de Notificações
# =============================

class NotificationTestView(LoginRequiredMixin, View):
    """
    Endpoint para enviar teste de notificação.
    POST JSON: {"channel": "email"|"whatsapp", "value": "<destino>"}
    Throttle: 5 req/min por usuário e canal.
    """
    THROTTLE_LIMIT = 5  # por minuto

    def post(self, request, *args, **kwargs):
        import json

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

        channel = str(payload.get("channel") or "").strip().lower()
        value = str(payload.get("value") or "").strip()

        if channel not in {"email", "whatsapp"}:
            return JsonResponse({"ok": False, "error": "Canal inválido."}, status=400)
        if not value:
            return JsonResponse({"ok": False, "error": "Informe um destino."}, status=400)

        # Throttle por usuário e canal
        key = f"notify_test:{request.user.id}:{channel}"
        count = cache.get(key, 0)
        if count >= self.THROTTLE_LIMIT:
            return JsonResponse({"ok": False, "error": "Muitas tentativas. Tente novamente em instantes."}, status=429)
        cache.set(key, count + 1, timeout=60)  # 1 minuto

        try:
            if channel == "email":
                try:
                    validate_email(value)
                except DjangoValidationError:
                    return JsonResponse({"ok": False, "error": "E-mail inválido."}, status=400)
                ident = send_test_email(value, request.user)
                return JsonResponse({"ok": True, "channel": "email", "sent_to": value, "id": ident})

            else:  # whatsapp
                # Delega a normalização/validação para o serviço, que aceita formatos variados
                sid = send_test_whatsapp(value, request.user)
                return JsonResponse({"ok": True, "channel": "whatsapp", "sent_to": value, "id": sid})

        except NotConfiguredError as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
        except NotificationError as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"ok": False, "error": f"Erro inesperado: {e}"}, status=500)
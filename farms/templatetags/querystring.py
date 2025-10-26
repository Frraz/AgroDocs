""" farms/templatetags/querystring.py """

from django import template
from django.http import QueryDict

register = template.Library()

@register.simple_tag
def querystring(params, **kwargs):
    """
    Retorna a querystring atual substituindo/removendo chaves.
    Uso no template:
      href="?{% querystring request.GET sort='nome' dir='asc' page=None %}"

    Regras:
    - Valores None ou "" removem a chave da querystring.
    - Listas/tuplas são suportadas (ex.: ?tag=a&tag=b).
    - Aceita QueryDict (request.GET) ou dict comum.
    """
    # Converte params para QueryDict mutável
    if isinstance(params, QueryDict):
        q = params.copy()
    else:
        q = QueryDict(mutable=True)
        params = params or {}
        for k, v in params.items():
            if isinstance(v, (list, tuple)):
                for item in v:
                    q.appendlist(k, item)
            else:
                q[k] = v

    # Aplica alterações vindas de kwargs
    for k, v in kwargs.items():
        if v is None or v == "":
            q.pop(k, None)
        elif isinstance(v, (list, tuple)):
            q.setlist(k, list(v))
        else:
            q[k] = v

    return q.urlencode()
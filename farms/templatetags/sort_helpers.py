from django import template

from django import template

register = template.Library()

def _norm(value, default=""):
    if value is None:
        return default
    return str(value).strip()

@register.simple_tag
def next_dir(current_sort, current_dir, column):
    """
    Retorna a próxima direção para a coluna:
    - Se a coluna já está ordenada asc -> desc
    - Caso contrário -> asc
    """
    cs = _norm(current_sort).casefold()
    cd = _norm(current_dir, "asc").casefold()
    col = _norm(column).casefold()
    if cs == col and cd == "asc":
        return "desc"
    return "asc"

@register.simple_tag
def sort_icon(current_sort, current_dir, column):
    """
    Retorna '▲' (asc) ou '▼' (desc) quando a coluna está ativa; vazio se inativa.
    """
    cs = _norm(current_sort).casefold()
    cd = _norm(current_dir, "asc").casefold()
    col = _norm(column).casefold()
    if cs != col:
        return ""
    return "▲" if cd == "asc" else "▼"
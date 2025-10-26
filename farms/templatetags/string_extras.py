from django import template

register = template.Library()

@register.filter
def startswith(value: str, prefix: str) -> bool:
    try:
        return str(value).startswith(prefix)
    except Exception:
        return False

@register.filter
def endswith(value: str, suffix: str) -> bool:
    try:
        return str(value).endswith(suffix)
    except Exception:
        return False

@register.filter
def contains(value: str, needle: str) -> bool:
    try:
        return str(needle) in str(value)
    except Exception:
        return False
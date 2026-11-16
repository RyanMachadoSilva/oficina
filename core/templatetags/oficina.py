from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def brl(valor):
    """Formata como moeda: 1234.5 -> R$ 1.234,50"""
    try:
        v = Decimal(valor or 0)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    txt = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {txt}"


@register.filter
def num(valor):
    """Quantidade sem zeros desnecessários: 1.00 -> 1, 2.50 -> 2,5"""
    try:
        v = Decimal(valor or 0).normalize()
    except (InvalidOperation, TypeError, ValueError):
        return valor
    txt = f"{v:f}"
    return txt.replace(".", ",")

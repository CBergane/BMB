from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template


register = template.Library()
SEK_QUANTUM = Decimal('0.01')


@register.filter
def sek(value):
    """Format a numeric value as Swedish kronor without using float rounding."""
    if value is None:
        value = 0

    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
        if not amount.is_finite():
            amount = Decimal(0)
        amount = amount.quantize(SEK_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal(0).quantize(SEK_QUANTUM)

    return f'{amount:.2f}'.replace('.', ',') + ' kr'

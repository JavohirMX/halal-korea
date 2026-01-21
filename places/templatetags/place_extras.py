from django import template

register = template.Library()

@register.filter
def make_range(value):
    try:
        return range(int(value))
    except (TypeError, ValueError):
        return range(0)


@register.filter
def split(value, sep=','):
    """Split a string by separator and return a list."""
    if value:
        return value.split(sep)
    return [] 
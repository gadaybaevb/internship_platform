from django import template

register = template.Library()

@register.filter
def minutes(value):
    """Возвращает количество минут из общего времени в секундах."""
    return value // 60

@register.filter
def seconds(value):
    """Возвращает количество секунд из общего времени в секундах."""
    return value % 60

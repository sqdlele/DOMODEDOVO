from django import template
from ..utils import format_date_russian, format_time_russian

register = template.Library()

@register.filter(name='russian_date')
def russian_date(value):
    return format_date_russian(value)

@register.filter(name='russian_time')
def russian_time(value):
    return format_time_russian(value)

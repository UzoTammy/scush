from django import template
from django.template.defaultfilters import stringfilter
from ozone.mytools import Month
from datetime import date
import decimal

register = template.Library()

@register.filter(name='zeropadding')
@stringfilter
def zero_padding(value, n):
    try:
        if value.isdigit():
            return value.zfill(n)
    except Exception:
        return None

@register.filter(name='addsep')
@stringfilter
def add_sep(value):
    part1 = value[:3]
    part2 = value[3:7]
    part3 = value[7:]
    return f"{part1}-{part2}-{part3}"

@register.filter(name='abs')
def absolute(value):
    try:
        return abs(value)
    except (ValueError, TypeError):
        return None
    
@register.filter(name='str')
@stringfilter
def convert_to_string(value):
    return str(value)
    
@register.filter()
def replace(value):
    arg = '*'
    value1 = value.split('@')[0]
    value1 = value1.replace(value[0], arg)
    value1 = value1.replace(value1[-1], arg)
    if len(value1) > 5:
        value1 = value1.replace(value1[int(len(value1)/2)], arg)
    return value1 + '@' + value.split('@')[1]

@register.filter(name="last_month_payroll_period")
def payroll_period_last(value):
    last_month = Month.last_month()
    year = date.today().year
    return f"{year}-{str(last_month).zfill(2)}"

@register.filter(name="next_month_payroll_period")
def payroll_period_next(value):
    next_month = Month.next_month()
    year = date.today().year
    return f"{year}-{str(next_month).zfill(2)}"

@register.filter
def join(value, arg):
    return f'{arg}-{value}'

@register.filter(name='div')
def divide(value, arg):
    try:
        return value/arg
    except (ValueError, ZeroDivisionError, decimal.InvalidOperation):
        return None

@register.filter
def minus(value, arg):
    try:
        return value - arg
    except Exception:
        return None

@register.filter
def dividedby(value, arg):
    return value/arg

@register.filter
def myriad(value):
    try:
        if isinstance(value, (decimal.Decimal,)):
                value = float(value)
        if 1e3 <= value < 1e6:
            if isinstance(value, (decimal.Decimal,)):
                value = float(value)
            return f"{round(value/1e3, 2)}K"
        elif 1e6 <= value < 1e9:
            return f"{round(value/1e6, 3)}M"
        elif value >= 1e9:
            return f"{round(value/1e9, 3)}B"
        return round(value, 1)
    except Exception:
        return None

@register.filter
def array(value, arg):
    try:
        return value[arg-1]
    except Exception:
        return None

@register.filter
def multiply(value, arg):
    return value * arg

@register.filter
def array_index(value, index):
    return value[index]

@register.filter
def make_list(value, separator):
    return value.split(separator)


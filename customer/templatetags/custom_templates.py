from django import template
from django.template.defaultfilters import stringfilter
from ozone.mytools import Month
from datetime import date

register = template.Library()


@register.filter(name='zeropadding')
@stringfilter
def zero_padding(value, n):
    if value.isdigit():
        return value.zfill(n)
    return value


@register.filter(name='addsep')
@stringfilter
def add_sep(value):
    part1 = value[:3]
    part2 = value[3:7]
    part3 = value[7:]
    return f"{part1}-{part2}-{part3}"


@register.filter(name='abs')
def absolute(value):
    return abs(value)


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

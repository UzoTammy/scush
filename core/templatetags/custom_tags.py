from django import template
from django.template.defaultfilters import stringfilter
from ozone.mytools import Month
from datetime import date
from djmoney.money import Money
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
    except (ValueError, ZeroDivisionError, TypeError, decimal.InvalidOperation):
        return None

@register.filter
def minus(value, arg):
    try:
        return value - arg
    except Exception:
        return None

@register.filter
def dividedby(value, arg):
    try:
        return value / arg
    except (TypeError, ZeroDivisionError, decimal.InvalidOperation):
        return None

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
        return decimal.Decimal('0.00')

@register.filter
def array(value, arg):
    try:
        return value[arg-1]
    except Exception:
        return None

@register.filter
def multiply(value, arg):
    try:
        return value * arg
    except (TypeError, decimal.InvalidOperation):
        return None

@register.filter
def array_index(value, index):
    try:
        return value[index]
    except IndexError:
        return None

@register.filter
def make_list(value, separator):
    return value.split(separator)


@register.filter
def as_money(value, currency='NGN'):
    """Wrap a plain Decimal/float (e.g. from an annotate/aggregate) as Money, so it
    renders with a currency prefix the same way a real MoneyField value does."""
    try:
        amount = value.amount if hasattr(value, 'amount') else value
        return Money(amount, currency)
    except Exception:
        return value

@register.filter
def money_compact(value):
    """Format a Money or Decimal/float as ₦XM / ₦XB (negative-safe)."""
    try:
        amount = float(value.amount) if hasattr(value, 'amount') else float(value)
    except (TypeError, ValueError, AttributeError):
        return value
    negative = amount < 0
    amount = abs(amount)
    if amount >= 1e9:
        formatted = f'₦{amount / 1e9:.2f}B'
    elif amount >= 1e6:
        formatted = f'₦{amount / 1e6:.2f}M'
    elif amount >= 1e3:
        formatted = f'₦{amount / 1e3:.2f}K'
    else:
        formatted = f'₦{amount:,.2f}'
    return f'-{formatted}' if negative else formatted


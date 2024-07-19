import decimal

from django.db.models.query import QuerySet
from django.db.models import Sum


class QuerySum:
    """
    This is a container class of tools related to queryset and aggregation
    """
    @staticmethod
    def to_currency(queryset:QuerySet, fieldname:str)->decimal.Decimal:
        """This function returns a decimal value being the sum of a field
        :params - queryset and a numeric field.
        The returned result is a decimal value in 2 decimal places"""
        total = queryset.aggregate(Sum(fieldname))[f'{fieldname}__sum'] if queryset.exists() else decimal.Decimal('0')
        return round(total, 2)

    @staticmethod
    def to_number(queryset:QuerySet, fieldname:str)-> decimal.Decimal|int:
        """This function returns a decimal if field is a float or decimal field
        and int if the field is an IntegerField.
        :param - queryset and a numeric field
        The returned result is either a decimal or integer.
        Takes care of whole numbers and no restricted level of precision.
        """
        total = queryset.aggregate(Sum(fieldname))[f'{fieldname}__sum'] if queryset.exists() else decimal.Decimal('0')
        
        return total
import decimal
import os

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
    

def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024), total_size

def count_files_and_directories(directory):
    file_count = 0
    dir_count = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        # Increment the file and directory counts
        file_count += len(filenames)
        dir_count += len(dirnames)
    return file_count, dir_count
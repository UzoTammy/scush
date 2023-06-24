import datetime
from abc import ABC, abstractmethod
# import pytz


class AbstractDateTime(ABC):

    class AbstractClass:
        """
        This is a Date Time abstract class that serves as a base for derived mixin classes.
        this class will be responsible to host reusable date manipulations. This will help
        store knowledge of works done on date and datetime module.
        This is limited to naive datetime. 

        Class-level documentation:
        - The AbstractClass defines a common interface for derived classes.
        - It provides shared functionality and contracts for implementation.

        Method documentation:
        - get_date method(date_string):
            - This method takes a date string in a standard yyyy-mm-dd format
            and return a date object.
            - Parameters:
                - date_string: (string) format: yyyy-mm-dd or yyyy.mm.dd or yyyy/mm/dd or yyyy:mm:dd.
            - Returns: (date object).

        Contract and guidelines:
        - Derived classes must implement get_date.
        - The return value of get_date must be a date object.

        Design decisions and considerations:
        - Decision: Using get_date instead of a generic name.
        - Rationale: It provides a clear and specific purpose for the method.
        - Trade-off: Some developers might need to rename their existing methods.
        """
    
    @abstractmethod
    def get_date(self, date_string:str) -> datetime.date:
        """get date function is based on taking a string
        date in the standard format yyyy-mm-dd and returning a 
        date object.
        """
        raise NotImplementedError("Derived classes must implement get_date.")

    
    @abstractmethod
    def days_apart(self, start_date:str, end_date:str) -> datetime.date:
        pass
    
    @abstractmethod
    def next_month(self, str_date:str) -> datetime.date:
        pass
    
    @abstractmethod
    def next_workday(self, str_date:str) -> datetime.date:
        pass
    
    @abstractmethod
    def readable_date(self, str_date:str) -> datetime.date:
        pass


class DateTimeMixin(AbstractDateTime):
    """Working with date objects"""
    def get_date(self, date_string:str=None):
        """converting date string to date object"""
        if date_string is None:
            return datetime.date.today()
        try:
            if '/' in date_string:
                date_string=date_string.replace('/', '-')
            if '.' in date_string:
                date_string = date_string.replace('.', '-')
            if ':' in date_string:
                date_string = date_string.replace(':', '-')
            return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError as err:
            """Check {date_string} and follow this format yyyy-mm-dd: 
            yyyy must be 4-digits 1970 to 9999, mm ranges 01-12 and dd ranges 01-31"""
            return -1
        except TypeError:
            return -2
        except:
            return -3
        
    def days_apart(self, start_date:str, end_date:str) -> int:
        start_date = self.get_date(start_date)
        end_date = self.get_date(end_date)
        return (end_date - start_date if end_date > start_date else start_date - end_date).days
    
    def next_month(self, str_date:str) -> int:
        date_obj = datetime.datetime.strptime(str_date, '%Y-%m-%d').date()
        if date_obj.month == 12:
            return 1
        return date_obj.month + 1

    def next_workday(self, date_string:str, holidays:list=None) -> datetime.date:
        date_obj = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
        if date_obj.weekday() == 4:
            workday = date_obj + datetime.timedelta(3)
        elif date_obj.weekday() == 5:
            workday = date_obj + datetime.timedelta(2)
        else:
            workday = date_obj + datetime.timedelta(1)
        if holidays is None:
            return workday
        else:
            while (workday.strftime('%Y-%m-%d') in holidays):
                workday += datetime.timedelta(1)
            return workday

    def readable_date(self, date_obj:datetime.date, is_day=False) -> str:
        """Convert a date object to a clear date string in the form
        january 
        """
        if is_day is True:
            """is_day parameter is to return the day of the week: monday, tuesday..."""
            return date_obj.strftime('%a %d %B, %Y')
        return date_obj.strftime('%d %B, %Y')

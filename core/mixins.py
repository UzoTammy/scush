import datetime
# import pytz


class DateTimeMixin:
    """Working with date objects"""
    def get_date(self, date_string=None):
        """converting date string to date object"""
        if date_string is None:
            return datetime.date.today()
        return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
    
    def days_apart(self, start_date, end_date):
        start_date = self.get_date(start_date)
        end_date = self.get_date(end_date)
        return (end_date - start_date if end_date > start_date else start_date - end_date).days
    
    def next_month(self, date_string):
        date_obj = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
        if date_obj.month == 12:
            return 1
        return date_obj.month + 1


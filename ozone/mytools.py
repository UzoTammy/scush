import datetime
import calendar
import csv
import itertools as it
from decimal import Decimal


class DatePeriod:
    """last day of the month"""
    days_in_month = calendar.monthrange(datetime.date.today().year,
                                        datetime.date.today().month)[1]

    days_in_year = (366 if calendar.isleap(datetime.date.today().year) else 365)

    def __init__(self, date_string):
        self.date_string = date_string

    def age_days(self):
        """This function transforms a date string to
        number of days (integer) from that given date.
        The steps are as follows:
        get a date object
        get the current date object
        the difference of both objects is a timedelta
        return the days integer of the timedelta. However
        since leap days are involved, in other to align with
        human calculation, we have to deduct the leap days"""

        date_object = datetime.datetime.strptime(self.date_string, '%d-%m-%Y')
        date_object_days = date_object
        today_days = datetime.datetime.today()
        days = (today_days - date_object_days).days

        # considering human method
        years = divmod(days, 365)[0]
        leap_days = divmod(years, 4)[0]
        return days - leap_days

    def age_tuple(self):
        """It converts a date string to a tuple (years, months, weeks, days).
        use the age_days function to derive days from date string"""
        days = self.age_days()
        days = -days if days < 0 else days  # change -ve to +ve
        age_years = list(divmod(days, 365))  # get the whole and the remainder (in years)
        age_months = divmod(age_years[1], 30)  # get the whole and the remainder (in months)
        age_weeks = divmod(age_months[1], 7)   # get the whole and the remainder (in weeks)

        age_years.pop()
        age_years += list(i for i in age_months)
        age_years.pop()
        age_years += list(i for i in age_weeks)
        return tuple(age_years)

    def year_month_week_day(self):
        """A string output of the years, months, weeks, and days of
        a given date"""
        age_tuple = self.age_tuple()
        # convert tuple to string and consider plurals
        N_str = list()
        time_units = ('year', 'month', 'week', 'day')
        for index, values in enumerate(zip(age_tuple, time_units)):
            if values[0] > 0:
                N_str.append(
                    f"{values[0]}{time_units[index]}" if age_tuple[index] == 1 else f"{values[0]}{time_units[index]}s")
        result = ', '.join(N_str)
        return result

    @staticmethod
    def countdown(date_string, start):
        """This function is to get number of days left between a given date
        and the current date within the same year, with the
        beginning stated"""
        date_object = datetime.datetime.strptime(date_string, '%d-%m-%Y').date()
        current_date = datetime.date.today()
        date_object = datetime.date(current_date.year, date_object.month, date_object.day)
        days_apart = (date_object-current_date).days

        if 0 <= days_apart <= start:
            return days_apart
        return -1

    def working_days(self,):
        return


class Person:
    """dummy data"""
    data = {
        'first_name': 'John',
        'second_name': 'Obi',
        'last_name': 'Mikel',
        'birth_date': '12-04-1990',
        'gender': 'Male',
        'marital_status': 'Married',
        'qualification': 'HND',
        'course': 'Physical Education',
        'mobile': '08012345678',
        'email': 'obimikel@chelsea.com',
        'address': '#10 Downing street, Burkingham, London',
    }

    """last day of the month"""
    days_in_month = calendar.monthrange(datetime.date.today().year,
                                        datetime.date.today().month)[1]

    days_in_year = (366 if calendar.isleap(datetime.date.today().year) else 365)

    def __init__(self, profile):
        self.first_name = profile.get('first_name')
        self.second_name = profile.get('second_name')
        self.last_name = profile.get('last_name')
        self.birth_date = profile.get('birth_date')
        self.gender = profile.get('gender')
        self.marital_status = profile.get('marital_status')
        self.qualification = profile.get('qualification')
        self.course = profile.get('course')
        self.mobile = profile.get('mobile')
        self.email = profile.get('email')
        self.address = profile.get('address')

    def __str__(self):
        return self.first_name

    def fullname(self):
        return f"{self.first_name} {self.second_name} {self.last_name}"

    """Function to transform date string to age. It is decorated with static method
    because its date string argument is external and not an attribute of this class"""
    @staticmethod
    def age_years(date_string):
        """The steps:
        convert date string to date object
        get today's date object
        get years from diff of the two date objects
        get current month
        get date object's month
        compare equality of the two date object's months and
            compare again the days of the objects and
            if they are the same or current day is greater then
            return the years else return years less 1
        again compare non-equality of the object's months and
        if the current month is less than the date object's then
        return years otherwise return years less 1
        """
        date_object = datetime.datetime.strptime(date_string, '%d-%m-%Y')  # 1
        today_date_object = datetime.date.today()
        years = today_date_object.year - date_object.year
        current_month = today_date_object.month
        birthday_month = date_object.month
        if current_month == birthday_month:
            """get the days within equal months and compare them"""
            if today_date_object.day >= date_object.day:   # or current_day > birthday_day:
                return years
            return years - 1
        elif birthday_month > current_month:
            return years - 1
        return years

    """Function to transform a date string into days from current date"""
    @staticmethod
    def age_days(date_string):
        """date_string argument must be presented in this format.
        The steps are as follows
        get a date object
        apply the timedelta to convert to days"""
        date_object = datetime.datetime.strptime(date_string, '%d-%m-%Y')
        date_object_days = date_object
        today_days = datetime.datetime.today()
        return (today_days - date_object_days).days


    @staticmethod
    def age_tuple(date_string):
        days = Person.age_days(date_string)
        years = list(divmod(days, Person.days_in_year))
        months = divmod(years[1], Person.days_in_month)
        weeks = divmod(months[1], 7)
        years.pop()
        years += list(i for i in months)
        years.pop()
        years += list(i for i in weeks)
        return tuple(years)

    @staticmethod
    def year_month_week_day(date_string):
        """"""
        age_tuple = Person.age_tuple(date_string)
        # convert tuple to string and consider plurals
        N_str = list()
        time_units = ('year', 'month', 'week', 'day')
        for index, values in enumerate(zip(age_tuple, time_units)):
            if values[0] > 0:
                N_str.append(f"{values[0]}{time_units[index]}" if age_tuple[index] == 1 else f"{values[0]}{time_units[index]}s")
        result = ', '.join(N_str)
        return result


class CSVtoTuple:
    def __init__(self, filepath):
        self.filepath = filepath
    """The first step is to locate the sheet,
    save it into a csv format. """

    def csv_content(self, **kwargs):
        content = list()
        """fetch the file, remove all empty spaces"""
        with open(self.filepath, 'r') as csv_rf:
            rf_reader = csv.reader(csv_rf)
            next(rf_reader)

            """remove blank spaces in cells"""
            for line in rf_reader:
                refined = list(item.strip() for item in line)
                content.append(refined)

            try:
                """convert string to integer if needed"""
                for i in kwargs['integer']:
                    for line in content:
                            line[i] = int(line[i]) if line[i].isnumeric() else line[i]

                """convert string to float if needed"""
                for i in kwargs['decimal']:
                    for line in content:
                        line[i] = float(line[i]) if line[i].isnumeric() else line[i]
            except KeyError as err:
                pass
            finally:
                return tuple(content)


class Month:
    month = datetime.date.today().month

    @classmethod
    def last_month(cls):
        iters = it.cycle(range(12, 0, -1))
        for i in iters:
            if cls.month == i:
                p_month = next(iters)
                return p_month

    @classmethod
    def next_month(cls):
        iters = it.cycle(range(1, 13, 1))
        for i in iters:
            if cls.month == i:
                n_month = next(iters)
                return n_month

    @classmethod
    def previous_month_letter(cls, month):
        cycle = it.cycle(range(13, 1, -1))
        if list(calendar.month_name).index(month) in cycle:
            result = calendar.month_name[next(cycle)] 
        return result

    @classmethod
    def number_of_working_days(cls, year, month):
        days_in_month = calendar.monthrange(year, month)
        month_range = range(1, days_in_month[1]+1)
        first_day = days_in_month[0]

        if first_day == 0:

            return len(list(i for i in zip(it.cycle(range(7)), month_range) if i[0] != calendar.SUNDAY))
        else:
            week_one = list(range(first_day, 6))
            week_one = list(i for i in zip(week_one, range(1, len(week_one)+1)))
            result = list(i for i in zip(it.cycle(range(7)), range(len(week_one)+1, days_in_month[1])) if i[0] != calendar.SUNDAY)
            return len(week_one + result)


    @staticmethod
    def month_int(month):
        for i in range(1, 13):
            if month == calendar.month_name[i]:
                break
        return i    


class DateRange:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

    @property
    def days(self):
        if self.end_date > self.start_date:
            return self.end_date - self.start_date
        return self.start_date - self.end_date

    @property
    def days_exclusive(self):
        if self.end_date > self.start_date:
            next_date = self.start_date + datetime.timedelta(1)
            previous_date = self.end_date - datetime.timedelta(1)
        else:
            next_date = self.end_date + datetime.timedelta(1)
            previous_date = self.start_date - datetime.timedelta(1)
        return previous_date - next_date

    @property
    def exclude_a_day(self):
        if self.end_date > self.start_date:
            start_date = self.start_date + datetime.timedelta(1)
            return self.end_date - start_date
        else:
            end_date = self.end_date + datetime.timedelta(1)
            return self.start_date - end_date

    def range(self):
        result = list()
        for i in range(self.days.days):
            if self.start_date > self.end_date:
                self.start_date, self.end_date = self.end_date, self.start_date
            result.append(self.start_date + datetime.timedelta(i))
        result.append(self.end_date)
        return result

    def exclude_weekday(self, weekday):
        result = list()
        for i in self.range():
            if i.weekday() != weekday:
                result.append(i)
        return result


class Period:
    full_months = {
        '01': 'January',
        '02': 'February',
        '03': 'March',
        '04': 'April',
        '05': 'May',
        '06': 'June',
        '07': 'July',
        '08': 'August',
        '09': 'September',
        '10': 'October',
        '11': 'November',
        '12': 'December',
    }

    def __init__(self, year, month):
        self.year = year
        self.month = month

    def __str__(self):
        return f"{self.year}-{str(self.month).zfill(2)}"

    def previous(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
            return f"{self.year}-{str(self.month).zfill(2)}"
        return f"{self.year}-{str(self.month-1).zfill(2)}"

    def next(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
            return f"{self.year}-{str(self.month).zfill(2)}"
        return f"{self.year}-{str(self.month+1).zfill(2)}"


class Taxation:
    """Reliefs included transport, leave allowance, rents"""

    @classmethod
    def evaluate(cls, annual_taxable_amount):
        if annual_taxable_amount < 300_000:
            # 1%
            return Decimal(1)/Decimal(100) * annual_taxable_amount
        elif 300_000 <= annual_taxable_amount < 2*300_000:
            # 7% and 11%
            first = 300_000 * Decimal(7)/Decimal(100)
            second = (annual_taxable_amount - 300_000) * Decimal(11)/Decimal(100)
            return first + second
        elif 2*300_000 <= annual_taxable_amount < 2*300_000+500_000:
            # 7%,11% and 15%
            first = 300_000 * Decimal(7)/Decimal(100)
            second = 300_000 * Decimal(11)/Decimal(100)
            third = (annual_taxable_amount - 2 * 300_000) * Decimal(15)/Decimal(100)
            return first + second + third
        elif 2*300_000 + 500_000 <= annual_taxable_amount < 2*(300_000+500_000):
            # 7%, 11%, 15% and 19%
            first = 300_000 * Decimal(7)/Decimal(100)
            second = 300_000 * Decimal(11)/Decimal(100)
            third = 500_000 * Decimal(15)/Decimal(100)
            forth = (annual_taxable_amount - 2*300_000 - 500_000) * Decimal(19)/Decimal(100)
            return first + second + third + forth
        elif 2 * (300_000 + 500_000) <= annual_taxable_amount < 2 * (300_000 + 500_000) + 1_600_000:
            # 7% + 11% + 15% + 19% + 21%
            first = 300_000 * Decimal(7)/Decimal(100)
            second = 300_000 * Decimal(11)/Decimal(100)
            third = 500_000 * Decimal(15)/Decimal(100)
            forth = 500_000 * Decimal(19)/Decimal(100)
            fifth = (annual_taxable_amount - 2*300_000 - 2*500_000) * Decimal(21)/Decimal(100)
            return first + second + third + forth + fifth
        else:
            return annual_taxable_amount * Decimal(24)/Decimal(100)





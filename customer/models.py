import datetime
from django.db import models
from djmoney.models.fields import MoneyField, Money
from django.urls import reverse
from users.models import Profile as UserProfile


class Profile(models.Model):
    business_name = models.CharField(max_length=100)
    business_owner = models.CharField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=120)
    cluster = models.CharField(max_length=3,
                               choices=[('TRF', 'Trade Fair'), ('FES', 'Festac'), ('OMO', 'Omonile'),
                                ('OKO', 'Okoko'), ('BAD', 'Badagry'), ('SAT', 'Satellite'), 
                                ('BAR', 'Barracks'), ('LIS', 'Lagos Island'), ('NC', 'No Cluster')],
                            default='TRF')
    region = models.CharField(max_length=3,
                              choices=[('LOS', 'Lagos'), ('DSP', 'Diaspora'), ('OLS', 'Outside Lagos')],
                              default='LOS')
    mobile = models.CharField(max_length=17)
    second_mobile = models.CharField(max_length=17, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, help_text="<span class='text-danger'>not compulsory</span>")
    classification = models.CharField(max_length=20, choices=[('RTN', 'Returnable'), ('OWP', '1-Way Pack'), 
        ('WIN', 'Wine'), ('ROW', 'Returnable+1-Way'), ('OWW', '1-Way+Wine'), ('ALL', 'All'),
        ('RTW', 'Returnable+Wine')],
    default='OWP'
    )
    contact_person = models.CharField(max_length=50, blank=True, null=True, 
                                        help_text="format: firstname//mobile"
                                        )
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.business_name

    def get_absolute_url(self):
        return reverse('customer-detail', kwargs={'pk': self.pk})


class CustomerCredit(models.Model):
    customerID = models.OneToOneField(Profile, on_delete=models.CASCADE)
    credit_limit = MoneyField(max_digits=14, decimal_places=2)
    current_credit = MoneyField(max_digits=14, decimal_places=2, default=Money(0, 'NGN'))
    date_created = models.DateField(default=datetime.date.today)
    expiry_date = models.DateField()
    approved_by = models.ForeignKey(UserProfile, on_delete=models.DO_NOTHING)
    isPermanent = models.BooleanField(default=True)
    status = models.BooleanField(default=True, choices=[
        (True, 'Active'), (None, 'Blacklist'), (False, 'Disable')],
        null=True, blank=True)

    def __str__(self) -> str:
        return self.customerID.business_name

    
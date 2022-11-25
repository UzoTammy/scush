from django.db import models
from django.urls import reverse


class CustomerProfile(models.Model):
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
    mobile = models.CharField(max_length=13)
    second_mobile = models.CharField(max_length=13, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, help_text="<span class='text-danger'>not compulsory</span>")
    classification = models.CharField(max_length=20, choices=[('RTN', 'Returnable'), ('OWP', '1-Way Pack'), 
        ('WIN', 'Wine'), ('ROW', 'Returnable+1-Way'), ('OWW', '1-Way+Wine'), ('ALL', 'All'),
        ('RTW', 'Returnable+Wine')],
    default='OWP'
    )
    contact_person = models.CharField(max_length=50, blank=True, null=True, help_text="firstname, mobile number")
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.business_name

    def get_absolute_url(self):
        return reverse('customer-detail', kwargs={'pk': self.pk})



from django.db import models
from djmoney.models.fields import MoneyField
from django.shortcuts import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from djmoney.money import Money
from outlet.models import SalesCenter


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Source(models.Model):
    code = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=100, blank=True, default='')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.code


class Product(models.Model):
    name = models.CharField(max_length=20)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    unit_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN', default=0.0)
    pack_type = models.CharField(max_length=20, default='Pack')
    quantity_per_pack = models.IntegerField(default=24)
    unit_type = models.CharField(max_length=20, default='Can')
    product_state = models.CharField(max_length=20, default='Liquid')
    size_value = models.FloatField(default=33, blank=True, null=True)
    size_value_unit = models.CharField(max_length=20, default='CL', blank=True, null=True)
    alcohol_content = models.FloatField(default=0.0)
    vat = models.FloatField(default=7.5, choices=[(7.5, 'Vatable'), (0.0, 'Exempted')])
    image = models.ImageField(default='default.jpg', upload_to='product_pics')
    cost_price = MoneyField(
        max_digits=8, decimal_places=2, default_currency='NGN', 
        validators=[MinValueValidator(Money(1, 'NGN'), 
        message="Cost price can't be NGN0.00")])
    parameter = models.CharField(max_length=20, default='Standard', verbose_name='Flavour, Shape or Size',
                                 help_text='<span class="text-danger">products of the same name but different shape or flavour e.g. maltina: classic, pineaple, vanilla</span>')
    active = models.BooleanField(default=True, choices=[(True, 'Yes'), (False, 'No')], verbose_name='Active?')
    discount = models.FloatField(default=0.0)
    discount_type = models.CharField(max_length=20,
                                     choices=[
                                         ('PP', 'Per Pack'),
                                         ('PERCENT', 'Percent'),
                                         ('VALUE', 'Absolute Value'),
                                         ('RATIO', 'Qty Ratio')
                                     ], default='PP')
    date_modified = models.DateTimeField(default=timezone.now)
    is_stock_valued = models.BooleanField(default=False) #
    watchlist = models.BooleanField(default=False, verbose_name='watchlist')
    velocity = models.IntegerField(default=-1)
    min_stock_level = models.IntegerField(default=0, verbose_name='Minimum Stock Level',
                                          help_text='Minimum stock to hold (in units). 0 = not set')
    max_stock_level = models.IntegerField(default=0, verbose_name='Maximum Stock Level',
                                          help_text='Maximum stock to hold (in units). 0 = not set')
    reorder_point = models.IntegerField(default=0, verbose_name='Reorder Point',
                                        help_text='Trigger reorder when stock falls to/below this. 0 = not set')
    reorder_qty = models.IntegerField(default=0, verbose_name='Reorder Quantity',
                                      help_text='Suggested quantity to reorder. 0 = not set')

    def __str__(self):
        if self.parameter == 'Standard':
            return f"{self.name}~{self.size_value}{self.size_value_unit}x{self.quantity_per_pack}{self.pack_type}"
        return f"{self.name} {self.parameter}~{self.size_value}{self.size_value_unit}x{self.quantity_per_pack}{self.pack_type}"

    def get_absolute_url(self):
        return reverse('product-detail', kwargs={'pk': self.pk})

    def margin(self):
        return self.unit_price - self.cost_price

    def nickname(self):
        return f"{self.name} {int(self.size_value)}{self.size_value_unit},{self.pack_type}"

    def current_stock(self):
        """Quantity from the most recent ProductExtension record, or None if none exist."""
        latest = self.productextension_set.order_by('-date').first()
        return latest.stock_value if latest else None

    def stock_status(self):
        """Returns 'LOW', 'OVER', 'OK' or 'UNSET' based on current stock vs reorder/max levels."""
        if self.reorder_point == 0 and self.max_stock_level == 0:
            return 'UNSET'
        stock = self.current_stock()
        if stock is None:
            return 'UNSET'
        if self.reorder_point and stock <= self.reorder_point:
            return 'LOW'
        if self.max_stock_level and stock >= self.max_stock_level:
            return 'OVER'
        return 'OK'

    def save(self, *args, **kwargs):
        if self.pk:
            previous = Product.objects.filter(pk=self.pk).first()
            if previous is not None:
                changed_by = getattr(self, '_changed_by', None)
                if previous.cost_price != self.cost_price:
                    PriceHistory.objects.create(
                        product=self, price_type='COST',
                        old_price=previous.cost_price, new_price=self.cost_price,
                        changed_by=changed_by,
                    )
                if previous.unit_price != self.unit_price:
                    PriceHistory.objects.create(
                        product=self, price_type='SELLING',
                        old_price=previous.unit_price, new_price=self.unit_price,
                        changed_by=changed_by,
                    )
        super(Product, self).save(*args, **kwargs)


class ProductPerformance(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    outlet = models.ForeignKey(SalesCenter, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    landing_cost = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN', default=0.0)
    selling_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN', default=0.0)
    depletion = models.IntegerField()
    balance = models.IntegerField()
    tag = models.BooleanField(default=True) #focus brand

    def __str__(self):
        return f'{self.product} performance' 

    def get_absolute_url(self):
        return reverse('product-performance-detail', kwargs={'pk':self.pk})
         
class ProductExtension(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cost_price = MoneyField(
        max_digits=8, decimal_places=2, default_currency='NGN',
        default=Money(1000, 'NGN'), 
        validators=[MinValueValidator(Money(1, 'NGN'), 
        message="Cost price can't be NGN0.00")]
    )
    selling_price = MoneyField(
        max_digits=8, decimal_places=2, default_currency='NGN',
        default=Money(1000, 'NGN'), 
        validators=[MinValueValidator(Money(1, 'NGN'), 
        message="Selling price can't be NGN0.00")]
    )
    stock_value = models.IntegerField(default=0, verbose_name='quantity')
    date = models.DateField(default=timezone.now)
    sell_out = models.IntegerField(default=0)
    sales_amount = MoneyField(
        max_digits=12, decimal_places=2, default_currency='NGN',
        default=Money(0, 'NGN'), 
        validators=[MinValueValidator(Money(0, 'NGN'), 
        message="Sales amount can't be negative")]
    )
    active = models.BooleanField(default=True) # can be used to deactivate the product
    
    def __str__(self) -> str:
        return f'{self.product}-{self.date}'

    def get_absolute_url(self):
        return reverse('product-ext-detail', kwargs={'pk':self.pk})
    
    def value_of_stock(self):
        return self.cost_price * self.stock_value

    def save(self, *args, **kwargs):
        if self.cost_price == Money(0, 'NGN') and self.sell_out != Money(0, 'NGN'):
            self.cost_price = self.product.cost_price
        super(ProductExtension, self).save(*args, **kwargs)


class PriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    price_type = models.CharField(max_length=10, choices=[('COST', 'Cost'), ('SELLING', 'Selling')])
    old_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN')
    new_price = MoneyField(max_digits=8, decimal_places=2, default_currency='NGN')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Price histories'

    def __str__(self):
        return f'{self.product} {self.get_price_type_display()} price: {self.old_price} -> {self.new_price}'

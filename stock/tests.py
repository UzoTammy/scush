"""
Stock app tests
===============
Covers the stock-movement ledger (Product.stock_balance/stock_status),
automatic PriceHistory creation on Product.save(), stock count variance,
ProductExtension cost-price backfill, and the Sales-group permission gate
on product/stock-adjustment views.
"""
import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from djmoney.money import Money

from stock.models import (
    Category, Product, ProductExtension, Source, StockCountLine, StockCountSession,
    StockLocation, StockMovement,
)

NGN = 'NGN'


def money(amount):
    return Money(Decimal(str(amount)), NGN)


def make_source(code='NB'):
    return Source.objects.get_or_create(code=code)[0]


def make_category(name='Malt'):
    return Category.objects.get_or_create(name=name)[0]


def make_product(name='Star', cost_price=100, unit_price=150, **overrides):
    defaults = dict(
        name=name, source=make_source(), category=make_category(),
        cost_price=money(cost_price), unit_price=money(unit_price),
    )
    defaults.update(overrides)
    return Product.objects.create(**defaults)


def make_stock_location(name='Main Warehouse'):
    """StockLocation.branch -> outlet.SalesCenter -> staff.Employee -> apply.Applicant,
    mirroring the local-helper pattern used by staff/tests.py."""
    from apply.models import Applicant
    from staff.models import Employee, Position
    from outlet.models import SalesCenter

    applicant = Applicant.objects.create(
        first_name='Loc', second_name='', last_name=f'Manager-{name}',
        birth_date=datetime.date(1990, 1, 1), gender='MALE', marital_status='SINGLE',
        qualification='BSC', mobile='080-0000-0000', state='Applied',
    )
    position, _ = Position.objects.get_or_create(name='Sales')
    employee = Employee.objects.create(
        staff=applicant, date_employed=datetime.date(2022, 1, 1), position=position,
        department='Sales', branch='HQ', banker='GTB', account_number='00000001',
        basic_salary=money(50000), allowance=money(10000), tax_amount=money(5000),
        status=True, is_confirmed=True,
    )
    sales_center = SalesCenter.objects.create(name=name, address='x', staff=employee)
    return StockLocation.objects.create(name=name, branch=sales_center)


# ── Model: Product.stock_balance / stock_status ─────────────────────────────

@pytest.mark.django_db
class TestProductStockBalance:
    def test_stock_balance_empty_ledger_is_zero(self):
        product = make_product()
        assert product.stock_balance() == 0

    def test_stock_balance_aggregates_signed_quantities(self):
        product = make_product()
        StockMovement.objects.create(product=product, movement_type='RECEIPT', quantity=100,
                                      date=datetime.date(2026, 1, 1))
        StockMovement.objects.create(product=product, movement_type='SALE', quantity=-30,
                                      date=datetime.date(2026, 1, 2))
        assert product.stock_balance() == 70

    def test_stock_balance_filters_by_location(self):
        product = make_product()
        loc_a = make_stock_location('Warehouse A')
        loc_b = make_stock_location('Warehouse B')
        StockMovement.objects.create(product=product, movement_type='RECEIPT', quantity=50,
                                      date=datetime.date(2026, 1, 1), location=loc_a)
        StockMovement.objects.create(product=product, movement_type='RECEIPT', quantity=20,
                                      date=datetime.date(2026, 1, 1), location=loc_b)
        assert product.stock_balance(location=loc_a) == 50
        assert product.stock_balance(location=loc_b) == 20
        assert product.stock_balance() == 70


@pytest.mark.django_db
class TestProductStockStatus:
    def test_unset_when_no_thresholds_configured(self):
        product = make_product(reorder_point=0, max_stock_level=0)
        assert product.stock_status() == 'UNSET'

    def test_unset_when_no_current_stock_record(self):
        product = make_product(reorder_point=10, max_stock_level=100)
        assert product.stock_status() == 'UNSET'

    def test_low_when_at_or_below_reorder_point(self):
        product = make_product(reorder_point=10, max_stock_level=100)
        ProductExtension.objects.create(product=product, stock_value=10, date=datetime.date(2026, 1, 1))
        assert product.stock_status() == 'LOW'

    def test_over_when_at_or_above_max_level(self):
        product = make_product(reorder_point=10, max_stock_level=100)
        ProductExtension.objects.create(product=product, stock_value=150, date=datetime.date(2026, 1, 1))
        assert product.stock_status() == 'OVER'

    def test_ok_between_thresholds(self):
        product = make_product(reorder_point=10, max_stock_level=100)
        ProductExtension.objects.create(product=product, stock_value=50, date=datetime.date(2026, 1, 1))
        assert product.stock_status() == 'OK'


# ── Model: Product.save() PriceHistory ──────────────────────────────────────

@pytest.mark.django_db
class TestPriceHistory:
    def test_creation_does_not_create_history(self):
        product = make_product(cost_price=100, unit_price=150)
        assert product.price_history.count() == 0

    def test_cost_price_change_creates_history_entry(self):
        product = make_product(cost_price=100, unit_price=150)
        product.cost_price = money(120)
        product._changed_by = None
        product.save()
        entries = list(product.price_history.all())
        assert len(entries) == 1
        assert entries[0].price_type == 'COST'
        assert entries[0].old_price == money(100)
        assert entries[0].new_price == money(120)

    def test_unit_price_change_creates_history_entry(self):
        product = make_product(cost_price=100, unit_price=150)
        product.unit_price = money(200)
        product.save()
        entries = list(product.price_history.filter(price_type='SELLING'))
        assert len(entries) == 1
        assert entries[0].old_price == money(150)
        assert entries[0].new_price == money(200)

    def test_unchanged_prices_create_no_history(self):
        product = make_product(cost_price=100, unit_price=150)
        product.name = 'Star Renamed'
        product.save()
        assert product.price_history.count() == 0

    def test_both_prices_changing_creates_two_entries(self):
        product = make_product(cost_price=100, unit_price=150)
        product.cost_price = money(110)
        product.unit_price = money(160)
        product.save()
        assert product.price_history.count() == 2


# ── Model: StockCountSession.net_variance / StockCountLine.variance ─────────

@pytest.mark.django_db
class TestStockCount:
    def test_net_variance_sums_positive_and_negative(self):
        session = StockCountSession.objects.create(date=datetime.date(2026, 1, 1))
        p1, p2 = make_product('P1'), make_product('P2')
        StockCountLine.objects.create(session=session, product=p1, system_qty=100, counted_qty=90)
        StockCountLine.objects.create(session=session, product=p2, system_qty=50, counted_qty=55)
        # -10 + 5 = -5
        assert session.net_variance() == -5

    def test_variance_property(self):
        session = StockCountSession.objects.create(date=datetime.date(2026, 1, 1))
        line = StockCountLine.objects.create(session=session, product=make_product(), system_qty=20, counted_qty=25)
        assert line.variance == 5


# ── Model: ProductExtension.save() cost_price backfill ──────────────────────

@pytest.mark.django_db
class TestProductExtensionBackfill:
    def test_backfills_cost_price_from_product_when_zero_and_sold(self):
        product = make_product(cost_price=250)
        ext = ProductExtension(product=product, cost_price=money(0), sell_out=5, date=datetime.date(2026, 1, 1))
        ext.save()
        assert ext.cost_price == money(250)

    def test_no_backfill_when_cost_price_already_set(self):
        product = make_product(cost_price=250)
        ext = ProductExtension(product=product, cost_price=money(80), sell_out=5, date=datetime.date(2026, 1, 1))
        ext.save()
        assert ext.cost_price == money(80)

    def test_no_backfill_when_no_sell_out(self):
        product = make_product(cost_price=250)
        ext = ProductExtension(product=product, cost_price=money(0), sell_out=0, date=datetime.date(2026, 1, 1))
        ext.save()
        assert ext.cost_price == money(0)


# ── Views: Sales-group permission gate ───────────────────────────────────────

@pytest.fixture
def sales_user(db, user_in_group_factory):
    return user_in_group_factory('Sales', username='sales_user')


@pytest.mark.django_db
class TestPermissionGates:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse('product-create'))
        assert response.status_code == 302

    def test_non_sales_user_forbidden(self, client, new_user):
        client.force_login(new_user)
        response = client.get(reverse('product-create'))
        assert response.status_code == 403

    def test_sales_user_allowed(self, client, sales_user):
        client.force_login(sales_user)
        response = client.get(reverse('product-create'))
        assert response.status_code == 200

    def test_stock_transfer_requires_sales_group(self, client, new_user):
        client.force_login(new_user)
        response = client.get(reverse('stock-transfer'))
        assert response.status_code == 403


# ── Views: StockMovementCreateView / StockCountCreateView / StockTransferView

@pytest.mark.django_db
class TestStockMovementViews:
    def test_stock_movement_create_records_signed_quantity(self, client, new_user):
        product = make_product()
        client.force_login(new_user)
        response = client.post(reverse('stock-movement-add', kwargs={'pk': product.pk}), data={
            'movement_type': 'RECEIPT', 'quantity': 25, 'date': '2026-01-01',
            'location': '', 'reference': '', 'note': '',
        })
        assert response.status_code == 302
        assert product.stock_balance() == 25

    def test_stock_count_creates_adjustment_only_when_variance_nonzero(self, client, sales_user):
        product_a = make_product('A')
        product_b = make_product('B')
        StockMovement.objects.create(product=product_a, movement_type='RECEIPT', quantity=10,
                                      date=datetime.date(2026, 1, 1))
        StockMovement.objects.create(product=product_b, movement_type='RECEIPT', quantity=10,
                                      date=datetime.date(2026, 1, 1))
        client.force_login(sales_user)
        response = client.post(reverse('stock-count-new'), data={
            'date': '2026-01-02', 'note': '',
            f'counted_{product_a.pk}': '15',  # variance +5 -> adjustment expected
            f'counted_{product_b.pk}': '10',  # variance 0 -> no adjustment
        })
        assert response.status_code == 302
        assert StockMovement.objects.filter(product=product_a, movement_type='ADJUSTMENT').count() == 1
        assert StockMovement.objects.filter(product=product_b, movement_type='ADJUSTMENT').count() == 0
        assert product_a.stock_balance() == 15
        assert product_b.stock_balance() == 10

    def test_stock_transfer_creates_matched_out_and_in_movements(self, client, sales_user):
        product = make_product()
        loc_a = make_stock_location('From')
        loc_b = make_stock_location('To')
        StockMovement.objects.create(product=product, movement_type='RECEIPT', quantity=50,
                                      date=datetime.date(2026, 1, 1), location=loc_a)
        client.force_login(sales_user)
        response = client.post(reverse('stock-transfer'), data={
            'product': product.pk, 'from_location': loc_a.pk, 'to_location': loc_b.pk,
            'quantity': 20, 'date': '2026-01-02', 'note': '',
        })
        assert response.status_code == 302
        assert product.stock_balance(location=loc_a) == 30
        assert product.stock_balance(location=loc_b) == 20
        assert product.stock_balance() == 50

    def test_stock_transfer_same_location_rejected(self, client, sales_user):
        product = make_product()
        loc = make_stock_location('Only')
        client.force_login(sales_user)
        client.post(reverse('stock-transfer'), data={
            'product': product.pk, 'from_location': loc.pk, 'to_location': loc.pk,
            'quantity': 5, 'date': '2026-01-02', 'note': '',
        })
        assert StockMovement.objects.filter(product=product).count() == 0

    def test_stock_transfer_non_positive_quantity_rejected(self, client, sales_user):
        product = make_product()
        loc_a = make_stock_location('X')
        loc_b = make_stock_location('Y')
        client.force_login(sales_user)
        client.post(reverse('stock-transfer'), data={
            'product': product.pk, 'from_location': loc_a.pk, 'to_location': loc_b.pk,
            'quantity': 0, 'date': '2026-01-02', 'note': '',
        })
        assert StockMovement.objects.filter(product=product).count() == 0


@pytest.mark.django_db
class TestProductLevelAndPriceViews:
    def test_product_level_update_sets_reorder_fields(self, client, sales_user):
        product = make_product()
        client.force_login(sales_user)
        response = client.post(reverse('product-set-levels', kwargs={'pk': product.pk}), data={
            'min_stock_level': '5', 'max_stock_level': '200', 'reorder_point': '20', 'reorder_qty': '50',
        })
        product.refresh_from_db()
        assert response.status_code == 302
        assert (product.min_stock_level, product.max_stock_level,
                product.reorder_point, product.reorder_qty) == (5, 200, 20, 50)

    def test_price_quick_update_rejects_negative_result(self, client, sales_user):
        product = make_product(unit_price=100)
        client.force_login(sales_user)
        client.post(reverse('price-quick-update'), data={
            'product': product.pk, 'amount': '150', 'direction': 'decrease',
        })
        product.refresh_from_db()
        assert product.unit_price == money(100), 'a negative result must be rejected, not applied'

    def test_price_quick_update_applies_positive_result(self, client, sales_user):
        product = make_product(unit_price=100)
        client.force_login(sales_user)
        client.post(reverse('price-quick-update'), data={
            'product': product.pk, 'amount': '25', 'direction': 'increase',
        })
        product.refresh_from_db()
        assert product.unit_price == money(125)

    def test_price_update_with_neither_selling_nor_cost_does_not_crash(self, client, new_user):
        """Regression: PriceUpdate.post() previously referenced an unbound `msg`
        when POST had none of 'selling'/'cost'/'redirect'."""
        product = make_product()
        client.force_login(new_user)
        response = client.post(reverse('price-update', kwargs={'pk': product.pk}), data={})
        assert response.status_code == 302

    def test_price_update_selling_branch(self, client, new_user):
        product = make_product(unit_price=100)
        client.force_login(new_user)
        client.post(reverse('price-update', kwargs={'pk': product.pk}), data={'selling': '175'})
        product.refresh_from_db()
        assert product.unit_price == money(175)

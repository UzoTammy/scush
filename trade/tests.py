"""
Trade app tests
===============
Covers TradeDaily/TradeMonthly/BalanceSheet ratio & balance calculations,
the shared P&L form validation (_validate_pl) and stock-continuity check,
the period-locking / adjustment-approval workflow, and the post_save
email signals.
"""
import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.urls import reverse
from djmoney.money import Money

from core.models import Setting
from trade.forms import TradeDailyForm, TradeMonthlyForm
from trade.models import (
    BalanceSheet, TradeDaily, TradeMonthly, TradeBudget, CashProjection,
    TradeAdjustmentRequest, TradeAuditLog,
)

NGN = 'NGN'


def money(amount):
    return Money(Decimal(str(amount)), NGN)


def money_data(**fields):
    """Build MultiWidget-suffixed POST data (`<field>_0`/`<field>_1`) for MoneyFields."""
    data = {}
    for name, val in fields.items():
        data[f'{name}_0'] = str(val)
        data[f'{name}_1'] = NGN
    return data


def pl_data(date_, sales, purchase, direct_expenses, indirect_expenses,
            opening_value, closing_value, gross_profit,
            direct_income='0', indirect_income='0', confirm_anomaly=False):
    data = {
        'date': date_.isoformat() if hasattr(date_, 'isoformat') else date_,
        'confirm_anomaly': confirm_anomaly,
    }
    data.update(money_data(
        sales=sales, purchase=purchase, direct_expenses=direct_expenses,
        indirect_expenses=indirect_expenses, opening_value=opening_value,
        closing_value=closing_value, gross_profit=gross_profit,
        direct_income=direct_income, indirect_income=indirect_income,
    ))
    return data


def make_daily(date_, sales=1000, purchase=400, direct_expenses=50, indirect_expenses=100,
                opening_value=200, closing_value=300, gross_profit=600):
    return TradeDaily.objects.create(
        date=date_, sales=money(sales), purchase=money(purchase),
        direct_expenses=money(direct_expenses), indirect_expenses=money(indirect_expenses),
        opening_value=money(opening_value), closing_value=money(closing_value),
        gross_profit=money(gross_profit),
    )


def make_balance_sheet(**overrides):
    defaults = dict(
        date=datetime.date(2026, 1, 31),
        profit=money(100), adjusted_profit=money(0), capital=money(1000), liability=money(500),
        loan_liability=money(0), fixed_asset=money(200), current_asset=money(800),
        investment=money(0), suspense=money(0), difference=money(0), sundry_debtor=money(0),
    )
    defaults.update(overrides)
    return BalanceSheet.objects.create(**defaults)


@pytest.fixture
def admin_user(db, user_in_group_factory):
    return user_in_group_factory('Administrator', username='trade_admin')


@pytest.fixture
def superuser_admin(db, user_in_group_factory):
    """Superuser who ALSO belongs to the Administrator group.

    UserPassesTestMixin.test_func() on trade's group-gated views checks
    group membership only — is_superuser does not bypass it. The
    superuser-skips-approval behavior inside form_valid() is only reachable
    once this gate is already passed.
    """
    return user_in_group_factory('Administrator', username='trade_superadmin',
                                  is_superuser=True, is_staff=True)


# ── Model: TradeDaily ratios ────────────────────────────────────────────────

@pytest.mark.django_db
class TestTradeDailyRatios:
    def test_margin_ratio(self):
        daily = make_daily(datetime.date(2026, 1, 1), sales=1000, gross_profit=600, indirect_expenses=100)
        assert daily.margin_ratio() == Decimal('50.00')

    def test_margin_ratio_zero_sales(self):
        daily = make_daily(datetime.date(2026, 1, 1), sales=0, gross_profit=0)
        assert daily.margin_ratio() == Decimal('0')

    def test_delivery_expense_ratio_zero_purchase(self):
        daily = make_daily(datetime.date(2026, 1, 1), purchase=0)
        assert daily.delivery_expense_ratio() == Decimal('0')

    def test_admin_expense_ratio_zero_sales(self):
        daily = make_daily(datetime.date(2026, 1, 1), sales=0, gross_profit=0)
        assert daily.admin_expense_ratio() == Decimal('0')


# ── Model: BalanceSheet ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBalanceSheet:
    def test_is_balanced_within_default_tolerance(self):
        bs = make_balance_sheet(profit=money(100), adjusted_profit=money(0), capital=money(1000),
                                 liability=money(500), fixed_asset=money(200), current_asset=money(800),
                                 investment=money(0), suspense=money(0), difference=money(0))
        # left = 100+0+1000+500=1600; right = 200+800+0+0+0+0=1000 -> not balanced
        assert bs.is_balanced() is False
        assert bs.balance_difference() == money(600)

    def test_is_balanced_exact(self):
        bs = make_balance_sheet(profit=money(0), adjusted_profit=money(0), capital=money(1000),
                                 liability=money(0), fixed_asset=money(1000), current_asset=money(0),
                                 investment=money(0), suspense=money(0), difference=money(0))
        assert bs.balance_difference() == money(0)
        assert bs.is_balanced() is True

    def test_is_balanced_uses_custom_tolerance_setting(self, balance_tolerance_setting):
        balance_tolerance_setting('50')
        bs = make_balance_sheet(profit=money(0), adjusted_profit=money(0), capital=money(1000),
                                 liability=money(0), fixed_asset=money(1030), current_asset=money(0),
                                 investment=money(0), suspense=money(0), difference=money(0))
        # difference = -30, within tolerance of 50
        assert bs.is_balanced() is True

    def test_growth_ratio_zero_capital(self):
        bs = make_balance_sheet(capital=money(0))
        assert bs.growth_ratio() == 0

    def test_growth_ratio(self):
        bs = make_balance_sheet(profit=money(200), capital=money(1000))
        assert bs.growth_ratio() == Decimal('20.00')

    def test_debt_to_equity_ratio_zero_capital(self):
        bs = make_balance_sheet(capital=money(0))
        assert bs.debt_to_equity_ratio() == 0

    def test_current_ratio_zero_liability_returns_none(self):
        bs = make_balance_sheet(liability=money(0))
        assert bs.current_ratio() is None

    def test_current_ratio(self):
        bs = make_balance_sheet(current_asset=money(800), liability=money(400))
        assert bs.current_ratio() == Decimal('2.000')

    def test_quick_ratio_zero_liability_returns_none(self):
        bs = make_balance_sheet(liability=money(0))
        assert bs.quick_ratio() is None

    def test_quick_ratio_uses_matching_daily_closing_value_as_inventory(self):
        make_daily(datetime.date(2026, 1, 31), closing_value=100)
        bs = make_balance_sheet(date=datetime.date(2026, 1, 31), current_asset=money(500),
                                 sundry_debtor=money(50), liability=money(100))
        # (500 - 50 - 100) / 100 = 3.5
        assert bs.quick_ratio() == Decimal('3.500')

    def test_quick_ratio_no_matching_daily_treats_inventory_as_zero(self):
        bs = make_balance_sheet(date=datetime.date(2026, 2, 1), current_asset=money(500),
                                 sundry_debtor=money(0), liability=money(100))
        assert bs.quick_ratio() == Decimal('5.000')


# ── Model: TradeBudget / CashProjection ─────────────────────────────────────

@pytest.mark.django_db
class TestTradeBudgetAndCashProjection:
    def test_utilisation(self):
        budget = TradeBudget.objects.create(
            month='January', year=2026, budgeted_sales=money(1000), budgeted_purchase=money(400),
            budgeted_direct_expenses=money(50), budgeted_indirect_expenses=money(100),
        )
        assert budget.utilisation(500, 1000) == Decimal('50.0')

    def test_utilisation_zero_budgeted_returns_none(self):
        budget = TradeBudget.objects.create(
            month='January', year=2026, budgeted_sales=money(1000), budgeted_purchase=money(400),
            budgeted_direct_expenses=money(50), budgeted_indirect_expenses=money(100),
        )
        assert budget.utilisation(500, 0) is None

    def test_utilisation_none_budgeted_returns_none(self):
        budget = TradeBudget.objects.create(
            month='January', year=2026, budgeted_sales=money(1000), budgeted_purchase=money(400),
            budgeted_direct_expenses=money(50), budgeted_indirect_expenses=money(100),
        )
        assert budget.utilisation(500, None) is None

    def test_cash_projection_signed_amount(self):
        inflow = CashProjection.objects.create(
            description='Sale', amount=money(500), expected_date=datetime.date(2026, 3, 1), flow_type='IN',
        )
        outflow = CashProjection.objects.create(
            description='Rent', amount=money(200), expected_date=datetime.date(2026, 3, 1), flow_type='OUT',
        )
        assert inflow.signed_amount() == money(500)
        assert outflow.signed_amount() == money(-200)


# ── Forms: _validate_pl shared hard blocks ──────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize('field,value', [
    ('sales', 0),
    ('sales', -100),
    ('purchase', -1),
    ('gross_profit', -1),
    ('direct_expenses', -1),
    ('indirect_expenses', -1),
    ('opening_value', -1),
    ('closing_value', -1),
])
def test_daily_form_hard_block(field, value):
    data = pl_data(datetime.date(2026, 1, 1), sales=1000, purchase=400, direct_expenses=50,
                    indirect_expenses=100, opening_value=200, closing_value=300, gross_profit=600)
    data[f'{field}_0'] = str(value)
    form = TradeDailyForm(data=data)
    assert form.is_valid() is False


@pytest.mark.django_db
def test_daily_form_gross_profit_exceeding_sales_blocked():
    data = pl_data(datetime.date(2026, 1, 1), sales=100, purchase=10, direct_expenses=5,
                    indirect_expenses=5, opening_value=0, closing_value=0, gross_profit=200)
    form = TradeDailyForm(data=data)
    assert form.is_valid() is False
    assert 'gross_profit' in form.errors


@pytest.mark.django_db
def test_daily_form_valid_when_all_hard_rules_satisfied_and_no_anomaly():
    data = pl_data(datetime.date(2026, 1, 1), sales=1000, purchase=400, direct_expenses=50,
                    indirect_expenses=100, opening_value=200, closing_value=300, gross_profit=600)
    form = TradeDailyForm(data=data)
    assert form.is_valid() is True


# ── Forms: soft anomalies (require confirm_anomaly) ─────────────────────────

@pytest.mark.django_db
class TestSoftAnomalies:
    def test_purchase_exceeds_sales_blocked_without_confirm(self):
        data = pl_data(datetime.date(2026, 1, 1), sales=100, purchase=200, direct_expenses=5,
                        indirect_expenses=5, opening_value=0, closing_value=0, gross_profit=0)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is False

    def test_purchase_exceeds_sales_passes_with_confirm(self):
        data = pl_data(datetime.date(2026, 1, 1), sales=100, purchase=200, direct_expenses=5,
                        indirect_expenses=5, opening_value=0, closing_value=0, gross_profit=0,
                        confirm_anomaly=True)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is True

    def test_negative_net_profit_blocked_without_confirm(self):
        data = pl_data(datetime.date(2026, 1, 1), sales=1000, purchase=100, direct_expenses=0,
                        indirect_expenses=900, opening_value=0, closing_value=0, gross_profit=900)
        form = TradeDailyForm(data=data)
        # net_profit = 900-900 = 0, not negative; use indirect_expenses > gross_profit for genuine negative
        data = pl_data(datetime.date(2026, 1, 1), sales=1000, purchase=100, direct_expenses=0,
                        indirect_expenses=950, opening_value=0, closing_value=0, gross_profit=900)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is False

    def test_gp_divergence_over_threshold_blocked_without_confirm(self):
        # sales-purchase = 600, gross_profit = 500 -> 16.7% divergence, over 10% threshold
        data = pl_data(datetime.date(2026, 1, 1), sales=1000, purchase=400, direct_expenses=0,
                        indirect_expenses=0, opening_value=0, closing_value=0, gross_profit=500)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is False

    def test_gp_divergence_within_threshold_passes(self):
        # sales-purchase = 600, gross_profit = 570 -> 5% divergence, within threshold
        data = pl_data(datetime.date(2026, 1, 1), sales=1000, purchase=400, direct_expenses=0,
                        indirect_expenses=0, opening_value=0, closing_value=0, gross_profit=570)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is True


# ── Forms: TradeDailyForm stock continuity ──────────────────────────────────

@pytest.mark.django_db
class TestStockContinuity:
    def test_first_ever_record_has_no_prior_check(self):
        data = pl_data(datetime.date(2026, 1, 1), sales=1000, purchase=400, direct_expenses=50,
                        indirect_expenses=100, opening_value=999, closing_value=300, gross_profit=600)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is True

    def test_opening_mismatch_blocked_without_confirm(self):
        make_daily(datetime.date(2026, 1, 1), closing_value=300)
        data = pl_data(datetime.date(2026, 1, 2), sales=1000, purchase=400, direct_expenses=50,
                        indirect_expenses=100, opening_value=999, closing_value=500, gross_profit=600)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is False
        assert 'opening_value' in form.errors

    def test_opening_mismatch_passes_with_confirm(self):
        make_daily(datetime.date(2026, 1, 1), closing_value=300)
        data = pl_data(datetime.date(2026, 1, 2), sales=1000, purchase=400, direct_expenses=50,
                        indirect_expenses=100, opening_value=999, closing_value=500, gross_profit=600,
                        confirm_anomaly=True)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is True

    def test_opening_matches_prior_closing_passes(self):
        make_daily(datetime.date(2026, 1, 1), closing_value=300)
        data = pl_data(datetime.date(2026, 1, 2), sales=1000, purchase=400, direct_expenses=50,
                        indirect_expenses=100, opening_value=300, closing_value=500, gross_profit=600)
        form = TradeDailyForm(data=data)
        assert form.is_valid() is True


# ── Views: permission gates ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestPermissionGates:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse('trade-home'))
        assert response.status_code == 302
        assert '/login' in response.url or 'login' in response.url

    def test_non_administrator_forbidden(self, client, new_user):
        client.force_login(new_user)
        response = client.get(reverse('trade-daily-list'))
        assert response.status_code == 403

    def test_administrator_allowed(self, client, admin_user):
        make_daily(datetime.date(2026, 1, 1))
        client.force_login(admin_user)
        response = client.get(reverse('trade-daily-list'))
        assert response.status_code == 200

    def test_lock_view_requires_superuser_not_just_administrator(self, client, admin_user):
        monthly = TradeMonthly.objects.create(
            month='January', year=2026, sales=money(1000), purchase=money(400),
            direct_expenses=money(50), indirect_expenses=money(100), opening_value=money(0),
            closing_value=money(0), gross_profit=money(600),
        )
        client.force_login(admin_user)
        response = client.post(reverse('trade-period-lock', kwargs={'pk': monthly.pk}))
        assert response.status_code == 403

    def test_adjustment_review_requires_superuser(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse('trade-adjustment-list'))
        assert response.status_code == 403


# ── Views: locking ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPeriodLocking:
    def make_monthly(self, **overrides):
        defaults = dict(
            month='January', year=2026, sales=money(1000), purchase=money(400),
            direct_expenses=money(50), indirect_expenses=money(100), opening_value=money(0),
            closing_value=money(0), gross_profit=money(600),
        )
        defaults.update(overrides)
        return TradeMonthly.objects.create(**defaults)

    def test_superuser_can_toggle_lock(self, client, superuser):
        monthly = self.make_monthly()
        client.force_login(superuser)
        response = client.post(reverse('trade-period-lock', kwargs={'pk': monthly.pk}))
        monthly.refresh_from_db()
        assert response.status_code == 302
        assert monthly.locked is True
        assert monthly.locked_by == superuser
        assert TradeAuditLog.objects.filter(model_name='TradeMonthly', record_id=monthly.pk).exists()

    def test_locked_monthly_blocks_update(self, client, admin_user, superuser):
        monthly = self.make_monthly()
        client.force_login(superuser)
        client.post(reverse('trade-period-lock', kwargs={'pk': monthly.pk}))
        client.force_login(admin_user)
        response = client.get(reverse('trade-update', kwargs={'pk': monthly.pk}))
        assert response.status_code == 302

    def test_locked_matching_daily_blocks_update(self, client, admin_user, superuser):
        monthly = self.make_monthly()
        daily = make_daily(datetime.date(2026, 1, 15))
        client.force_login(superuser)
        client.post(reverse('trade-period-lock', kwargs={'pk': monthly.pk}))
        client.force_login(admin_user)
        response = client.get(reverse('trade-daily-update', kwargs={'pk': daily.pk}))
        assert response.status_code == 302


# ── Views: adjustment-request workflow ──────────────────────────────────────

@pytest.mark.django_db
class TestAdjustmentWorkflow:
    def test_non_superuser_update_creates_adjustment_request_and_does_not_save(self, client, admin_user):
        daily = make_daily(datetime.date(2026, 1, 1), sales=1000)
        client.force_login(admin_user)
        data = pl_data(datetime.date(2026, 1, 1), sales=2000, purchase=400, direct_expenses=50,
                        indirect_expenses=100, opening_value=200, closing_value=300, gross_profit=1600,
                        confirm_anomaly=True)
        client.post(reverse('trade-daily-update', kwargs={'pk': daily.pk}), data=data)

        daily.refresh_from_db()
        assert daily.sales == money(1000), 'record must be untouched until a superuser approves'
        assert TradeAdjustmentRequest.objects.filter(
            model_name='TradeDaily', record_id=daily.pk, status=TradeAdjustmentRequest.STATUS_PENDING,
        ).exists()

    def test_superuser_update_saves_directly_and_logs_audit(self, client, superuser_admin):
        daily = make_daily(datetime.date(2026, 1, 1), sales=1000)
        client.force_login(superuser_admin)
        data = pl_data(datetime.date(2026, 1, 1), sales=2000, purchase=400, direct_expenses=50,
                        indirect_expenses=100, opening_value=200, closing_value=300, gross_profit=1600,
                        confirm_anomaly=True)
        client.post(reverse('trade-daily-update', kwargs={'pk': daily.pk}), data=data)

        daily.refresh_from_db()
        assert daily.sales == money(2000)
        assert TradeAuditLog.objects.filter(model_name='TradeDaily', record_id=daily.pk).exists()
        assert not TradeAdjustmentRequest.objects.filter(model_name='TradeDaily', record_id=daily.pk).exists()

    def test_review_approve_applies_changes(self, client, admin_user, superuser):
        daily = make_daily(datetime.date(2026, 1, 1), sales=1000)
        adj = TradeAdjustmentRequest.objects.create(
            model_name='TradeDaily', record_id=daily.pk, record_str=str(daily), requester=admin_user,
            proposed_changes={'sales': {'old_display': '1000', 'new_display': '2000',
                                         'new_data': {'type': 'money', 'amount': '2000', 'currency': 'NGN'}}},
        )
        client.force_login(superuser)
        response = client.post(reverse('trade-adjustment-review', kwargs={'pk': adj.pk}), data={'action': 'approve'})

        daily.refresh_from_db()
        adj.refresh_from_db()
        assert response.status_code == 302
        assert daily.sales == money(2000)
        assert adj.status == TradeAdjustmentRequest.STATUS_APPROVED
        assert TradeAuditLog.objects.filter(model_name='TradeDaily', record_id=daily.pk).exists()

    def test_review_reject_leaves_record_unchanged(self, client, admin_user, superuser):
        daily = make_daily(datetime.date(2026, 1, 1), sales=1000)
        adj = TradeAdjustmentRequest.objects.create(
            model_name='TradeDaily', record_id=daily.pk, record_str=str(daily), requester=admin_user,
            proposed_changes={'sales': {'old_display': '1000', 'new_display': '2000',
                                         'new_data': {'type': 'money', 'amount': '2000', 'currency': 'NGN'}}},
        )
        client.force_login(superuser)
        client.post(reverse('trade-adjustment-review', kwargs={'pk': adj.pk}), data={'action': 'reject'})

        daily.refresh_from_db()
        adj.refresh_from_db()
        assert daily.sales == money(1000)
        assert adj.status == TradeAdjustmentRequest.STATUS_REJECTED

    def test_already_reviewed_request_short_circuits(self, client, admin_user, superuser):
        daily = make_daily(datetime.date(2026, 1, 1), sales=1000)
        adj = TradeAdjustmentRequest.objects.create(
            model_name='TradeDaily', record_id=daily.pk, record_str=str(daily), requester=admin_user,
            status=TradeAdjustmentRequest.STATUS_APPROVED,
            proposed_changes={'sales': {'old_display': '1000', 'new_display': '2000',
                                         'new_data': {'type': 'money', 'amount': '2000', 'currency': 'NGN'}}},
        )
        client.force_login(superuser)
        client.post(reverse('trade-adjustment-review', kwargs={'pk': adj.pk}), data={'action': 'reject'})

        adj.refresh_from_db()
        assert adj.status == TradeAdjustmentRequest.STATUS_APPROVED, 'reviewing twice must not flip status again'


# ── Signals: email on save ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestEmailSignals:
    def test_trade_daily_create_sends_email(self):
        mail.outbox.clear()
        make_daily(datetime.date(2026, 1, 1))
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ['uzo.nwokoro@ozonefl.com']
        assert mail.outbox[0].cc == ['dickson.abanum@ozonefl.com']

    def test_balance_sheet_create_sends_email(self):
        mail.outbox.clear()
        make_balance_sheet()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ['uzo.nwokoro@ozonefl.com']
        assert mail.outbox[0].cc == ['dickson.abanum@ozonefl.com']

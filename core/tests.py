"""
Core app tests
==============
Covers CompanyProfile singleton enforcement and Setting key/value lookup
(both used cross-app — e.g. trade's balance-tolerance check), the
CompanyProfile edit-permission split (superuser vs HRD group), the
is_staff gate on the dashboard views, and the latest_stock_date context
processor.
"""
import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse
from djmoney.money import Money

from core.context_processors import latest_stock_date
from core.models import CompanyProfile, Setting
from core.views import CompanyProfileDynamicUpdateView, CompanyProfileStaticUpdateView, DashBoardView, DBoardView


# ── Model: CompanyProfile ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCompanyProfile:
    def test_clean_blocks_second_instance_via_full_clean(self):
        CompanyProfile.objects.create(legal_name='First Co')
        second = CompanyProfile(legal_name='Second Co')
        with pytest.raises(ValidationError):
            second.full_clean()

    def test_clean_does_not_block_updating_existing_instance(self):
        profile = CompanyProfile.objects.create(legal_name='First Co')
        profile.legal_name = 'Renamed Co'
        profile.full_clean()  # must not raise

    def test_raw_save_bypassing_clean_is_not_blocked(self):
        """clean() is only invoked via full_clean()/ModelForm.is_valid() — a
        raw .save() has no DB-level uniqueness backing it up. Documented so a
        future refactor doesn't assume the DB enforces the singleton."""
        CompanyProfile.objects.create(legal_name='First Co')
        CompanyProfile.objects.create(legal_name='Second Co')  # does not raise
        assert CompanyProfile.objects.count() == 2

    def test_load_creates_when_absent(self):
        assert CompanyProfile.objects.count() == 0
        profile = CompanyProfile.load()
        assert profile.pk == 1
        assert CompanyProfile.objects.count() == 1

    def test_load_is_idempotent(self):
        first = CompanyProfile.load()
        second = CompanyProfile.load()
        assert first.pk == second.pk
        assert CompanyProfile.objects.count() == 1


# ── Model: Setting ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSetting:
    """Keys here are test-only and deliberately distinct from any key seeded by
    core/migrations/0004_seed_settings.py, which pre-populates rows (including
    'balance_tolerance' and 'branches') in every test run's database."""

    def test_get_value_missing_key_returns_default(self):
        assert Setting.get_value('test_only_missing_key', 'fallback') == 'fallback'

    def test_get_value_returns_stored_text_value(self):
        Setting.objects.create(key='test_only_tolerance', label='Tolerance', category='trade',
                                value_type=Setting.TYPE_NUMBER, text_value='25')
        assert Setting.get_value('test_only_tolerance', '1') == '25'

    def test_get_list_missing_key_returns_empty_list_by_default(self):
        assert Setting.get_list('test_only_missing_list_key') == []

    def test_get_list_missing_key_returns_given_default(self):
        assert Setting.get_list('test_only_missing_list_key', ['HQ']) == ['HQ']

    def test_get_list_returns_stored_list_value(self):
        Setting.objects.create(key='test_only_branches', label='Branches', category='general',
                                value_type=Setting.TYPE_LIST, list_value=['HQ', 'Annex'])
        assert Setting.get_list('test_only_branches') == ['HQ', 'Annex']


# ── Views: CompanyProfile edit permission split ─────────────────────────────

@pytest.mark.django_db
class TestCompanyProfilePermissions:
    def test_static_edit_requires_superuser(self, client, new_user):
        client.force_login(new_user)
        response = client.get(reverse('company-profile-static-edit'))
        assert response.status_code == 403

    def test_static_edit_allows_superuser(self, client, superuser):
        client.force_login(superuser)
        response = client.get(reverse('company-profile-static-edit'))
        assert response.status_code == 200

    def test_dynamic_edit_requires_hrd_group(self, client, new_user):
        client.force_login(new_user)
        response = client.get(reverse('company-profile-dynamic-edit'))
        assert response.status_code == 403

    def test_dynamic_edit_allows_hrd_group(self, client, user_in_group_factory):
        hrd_user = user_in_group_factory('HRD', username='hrd_user')
        client.force_login(hrd_user)
        response = client.get(reverse('company-profile-dynamic-edit'))
        assert response.status_code == 200

    def test_static_edit_view_operates_on_the_singleton(self, client, superuser):
        CompanyProfile.load()
        client.force_login(superuser)
        response = client.get(reverse('company-profile-static-edit'))
        assert response.context['object'].pk == 1


# ── Views: dashboard is_staff gate ───────────────────────────────────────────
# Testing test_func() directly (rather than a full GET) avoids depending on
# the large amount of unrelated fixture data get_context_data() pulls in.

@pytest.mark.django_db
class TestDashboardPermissionGate:
    def _test_func_for(self, view_class, user):
        request = RequestFactory().get('/dummy/')
        request.user = user
        view = view_class()
        view.request = request
        return view.test_func()

    def test_dashboard_denies_non_staff(self, new_user):
        assert self._test_func_for(DashBoardView, new_user) is False

    def test_dashboard_allows_staff(self, new_user):
        new_user.is_staff = True
        new_user.save(update_fields=['is_staff'])
        assert self._test_func_for(DashBoardView, new_user) is True

    def test_dboard_denies_non_staff(self, new_user):
        assert self._test_func_for(DBoardView, new_user) is False

    def test_dboard_allows_staff(self, new_user):
        new_user.is_staff = True
        new_user.save(update_fields=['is_staff'])
        assert self._test_func_for(DBoardView, new_user) is True

    def test_dashboard_anonymous_redirected_to_login(self, client):
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302


# ── Context processor: latest_stock_date ────────────────────────────────────

@pytest.mark.django_db
class TestLatestStockDateContextProcessor:
    def test_returns_none_when_no_records(self):
        assert latest_stock_date(None) == {'latest_stock_date': None}

    def test_returns_most_recent_date(self):
        from stock.models import Category, Product, ProductExtension, Source

        source = Source.objects.create(code='NB')
        category = Category.objects.create(name='Malt')
        product = Product.objects.create(
            name='Star', source=source, category=category,
            cost_price=Money(Decimal('100'), 'NGN'), unit_price=Money(Decimal('150'), 'NGN'),
        )
        ProductExtension.objects.create(product=product, date=datetime.date(2026, 1, 1))
        ProductExtension.objects.create(product=product, date=datetime.date(2026, 3, 15))
        ProductExtension.objects.create(product=product, date=datetime.date(2026, 2, 1))

        assert latest_stock_date(None) == {'latest_stock_date': datetime.date(2026, 3, 15)}

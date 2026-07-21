"""
Payroll Generation Tests
========================
Ensures the GeneratePayroll view never creates duplicate payroll records
for the same staff-period combination, regardless of how many times the
form is submitted.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from djmoney.money import Money

from django.core.exceptions import ValidationError

from apply.models import Applicant
from staff.models import Employee, Payroll, EquityParticipant, EquityShareAllocation, Welfare
from staff import equity


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_applicant(first='Test', last='Staff', n=1):
    """Create a minimal Applicant record."""
    return Applicant.objects.create(
        first_name=first,
        second_name='',
        last_name=f'{last}{n}',
        birth_date=datetime.date(1990, 1, 1),
        gender='MALE',
        marital_status='SINGLE',
        qualification='BSC',
        mobile='080-0000-0000',
        state='Applied',
    )


def make_employee(applicant, n=1):
    """Create an active Employee linked to the given Applicant."""
    return Employee.objects.create(
        staff=applicant,
        date_employed=datetime.date(2022, 1, 1),
        position='Sales',
        department='Sales',
        branch='HQ',
        banker='GTB',
        account_number=f'000000000{n}',
        basic_salary=Money(Decimal('50000.00'), 'NGN'),
        allowance=Money(Decimal('10000.00'), 'NGN'),
        tax_amount=Money(Decimal('5000.00'), 'NGN'),
        status=True,
        is_confirmed=True,
    )


def make_hrd_user():
    """Create a user who belongs to the HRD group."""
    user = User.objects.create_user(
        username='hrd_tester',
        password='testpass123',
    )
    hrd_group, _ = Group.objects.get_or_create(name='HRD')
    user.groups.add(hrd_group)
    return user


# ── Test cases ────────────────────────────────────────────────────────────────

@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class PayrollGenerationTests(TestCase):
    """Tests for the GeneratePayroll view (name='generate-payroll')."""

    def setUp(self):
        self.client = Client()
        self.user = make_hrd_user()
        self.client.login(username='hrd_tester', password='testpass123')

        # Create two active employees
        self.app1 = make_applicant('Alice', 'One', 1)
        self.app2 = make_applicant('Bob',   'Two', 2)
        self.emp1 = make_employee(self.app1, 1)
        self.emp2 = make_employee(self.app2, 2)

        self.period = '2099-01'   # Far-future period — won't collide with real data
        self.url    = reverse('generate-payroll', kwargs={'period': self.period})

    def tearDown(self):
        Payroll.objects.filter(period=self.period).delete()

    # ── Core correctness ──────────────────────────────────────────────────────

    def test_single_post_creates_one_record_per_employee(self):
        """A single POST must create exactly one Payroll row per active employee."""
        response = self.client.post(self.url)

        self.assertIn(response.status_code, [200, 302],
                      'POST should return 200 or redirect 302')

        count = Payroll.objects.filter(period=self.period).count()
        active_staff = Employee.objects.filter(status=True).count()
        self.assertEqual(
            count, active_staff,
            f'Expected {active_staff} payroll records but got {count}'
        )

    def test_single_post_creates_one_record_for_emp1(self):
        """Employee 1 must have exactly one record after one POST."""
        self.client.post(self.url)
        count = Payroll.objects.filter(period=self.period, staff=self.emp1).count()
        self.assertEqual(count, 1, f'emp1 has {count} records instead of 1')

    def test_single_post_creates_one_record_for_emp2(self):
        """Employee 2 must have exactly one record after one POST."""
        self.client.post(self.url)
        count = Payroll.objects.filter(period=self.period, staff=self.emp2).count()
        self.assertEqual(count, 1, f'emp2 has {count} records instead of 1')

    # ── Idempotency (double-submit guard) ─────────────────────────────────────

    def test_second_post_does_not_create_duplicates(self):
        """A second POST to the same period must NOT create extra records."""
        self.client.post(self.url)
        before = Payroll.objects.filter(period=self.period).count()

        self.client.post(self.url)   # second submit
        after = Payroll.objects.filter(period=self.period).count()

        self.assertEqual(before, after,
                         f'Second POST increased records from {before} to {after}')

    def test_five_posts_yield_single_copy_per_employee(self):
        """Simulates 5 rapid submits — still only 1 record per employee."""
        for _ in range(5):
            self.client.post(self.url)

        for emp in [self.emp1, self.emp2]:
            count = Payroll.objects.filter(period=self.period, staff=emp).count()
            self.assertEqual(
                count, 1,
                f'After 5 POSTs, {emp} has {count} records — expected 1'
            )

    def test_total_records_after_five_posts_equals_active_staff(self):
        """Total payroll rows after 5 POSTs == number of active employees."""
        for _ in range(5):
            self.client.post(self.url)

        total      = Payroll.objects.filter(period=self.period).count()
        active     = Employee.objects.filter(status=True).count()
        self.assertEqual(total, active,
                         f'Expected {active} total records, got {total}')

    # ── Redirect (Post-Redirect-Get) ──────────────────────────────────────────

    def test_successful_post_redirects(self):
        """After saving, the view must redirect (302), not re-render the form."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302,
                         'Expected redirect after payroll save')

    def test_second_post_redirects_without_saving(self):
        """A second POST to an existing period redirects immediately."""
        self.client.post(self.url)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302,
                         'Second POST should redirect, not re-render')

    # ── GET behaviour ─────────────────────────────────────────────────────────

    def test_get_shows_generate_form_when_period_is_new(self):
        """GET on a fresh period renders the generated_payroll template."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/payroll/generated_payroll.html')

    def test_get_shows_record_exists_when_period_already_saved(self):
        """After saving, GET on the same period renders the recordexists template."""
        self.client.post(self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/payroll/recordexists.html')

    # ── Net pay calculation sanity ────────────────────────────────────────────

    def test_net_pay_equals_gross_minus_tax(self):
        """For a staff with no credits or debits, net pay = gross pay - tax."""
        self.client.post(self.url)
        record = Payroll.objects.get(period=self.period, staff=self.emp1)

        expected_gross = self.emp1.basic_salary + self.emp1.allowance - self.emp1.tax_amount
        self.assertEqual(
            record.net_pay.amount, expected_gross.amount,
            f'net_pay {record.net_pay} != expected {expected_gross}'
        )

    # ── Unauthorised access ───────────────────────────────────────────────────

    def test_unauthenticated_user_cannot_post(self):
        """An unauthenticated request must be redirected to login."""
        anon_client = Client()
        response = anon_client.post(self.url)
        self.assertIn(response.status_code, [302, 403],
                      'Unauthenticated POST should be denied')

    def test_non_hrd_user_cannot_post(self):
        """A user not in the HRD group must receive 403."""
        User.objects.create_user(username='plain_user', password='pass123')
        non_hrd_client = Client()
        non_hrd_client.login(username='plain_user', password='pass123')
        response = non_hrd_client.post(self.url)
        self.assertEqual(response.status_code, 403,
                         'Non-HRD user should receive 403')


"""
Equity Pool Tests
=================
Vesting math and the guardrails described in SCusH_Equity_Pool_Feature_Plan_v2.md
Sections 4-5: 0/33/66/100% clock, the permanent fully_matured latch, clawback capped
at the unvested balance, and profit-pool credits always using the *locked* share for
the fiscal year the credit belongs to (not whatever share is current now).
"""

from dateutil.relativedelta import relativedelta


def make_participant(months_ago, allocation='900000.00', n=1):
    """Create an EquityParticipant whose grant_date is `months_ago` months before today.
    Eligibility is active employment only (make_employee defaults status=True) — management
    status is deliberately irrelevant here and untouched."""
    applicant = make_applicant('Equity', 'Participant', n)
    employee = make_employee(applicant, n)
    grant_date = datetime.date.today() - relativedelta(months=months_ago)
    participant = EquityParticipant.objects.create(
        staff=employee,
        role_code='TEST',
        initial_capital_allocation=Money(Decimal(allocation), 'NGN'),
        grant_date=grant_date,
    )
    equity.post_grant(participant)
    return participant


class EquityVestingTests(TestCase):
    """Vesting clock: 0% / 33% / 66% / 100% per Policy Sec.6.2, using the doc's own
    worked example (NGN900,000 -> NGN297,000 vested at 18 months)."""

    def test_vesting_pct_before_12_months(self):
        participant = make_participant(6, n=9)
        self.assertEqual(participant.vesting_pct, Decimal('0'))
        self.assertEqual(participant.vested_balance.amount, Decimal('0.00'))

    def test_vesting_pct_at_18_months_matches_worked_example(self):
        participant = make_participant(18, n=2)
        self.assertEqual(participant.vesting_pct, Decimal('33'))
        self.assertEqual(participant.vested_balance.amount, Decimal('297000.00'))

    def test_vesting_pct_at_30_months(self):
        participant = make_participant(30, n=3)
        self.assertEqual(participant.vesting_pct, Decimal('66'))

    def test_vesting_pct_at_40_months_is_fully_vested(self):
        participant = make_participant(40, n=4)
        self.assertEqual(participant.vesting_pct, Decimal('100'))
        self.assertEqual(participant.vested_balance.amount, Decimal('900000.00'))

    def test_fully_matured_latch_set_permanently_past_36_months(self):
        participant = make_participant(40, n=5)
        self.assertFalse(participant.fully_matured)
        self.assertTrue(participant.check_and_latch_maturity())
        participant.refresh_from_db()
        self.assertTrue(participant.fully_matured)

    def test_fully_matured_latch_does_not_revert(self):
        """Once latched, vesting_pct stays 100% even if grant_date math would say otherwise —
        this is the 'safe forever' guarantee from Sec.5."""
        participant = make_participant(40, n=6)
        participant.check_and_latch_maturity()
        # Simulate a future code change that recomputes months incorrectly by moving
        # grant_date to look recent — the stored latch must win regardless.
        participant.grant_date = datetime.date.today()
        participant.save(update_fields=['grant_date'])
        self.assertEqual(participant.vesting_pct, Decimal('100'))


class EquityClawbackTests(TestCase):

    def test_clawback_rejected_when_exceeding_unvested_balance(self):
        participant = make_participant(6, n=7)  # 0% vested -> entire balance is unvested
        with self.assertRaises(ValidationError):
            equity.post_clawback(participant, Decimal('1000000.00'), note='Net-loss year')

    def test_clawback_allowed_within_unvested_balance(self):
        participant = make_participant(6, n=8)
        equity.post_clawback(participant, Decimal('100000.00'), note='Net-loss year, approved by MD')
        self.assertEqual(participant.current_balance.amount, Decimal('800000.00'))

    def test_clawback_requires_note(self):
        participant = make_participant(6, n=9)
        with self.assertRaises(ValidationError):
            equity.post_clawback(participant, Decimal('1000.00'), note='')


class EquityProfitPoolCreditTests(TestCase):
    """A credit posted for fiscal_year N must always use the share locked for year N,
    even after a later reallocation changes that participant's current share (§5)."""

    def test_credit_uses_locked_share_for_its_own_fiscal_year(self):
        participant = make_participant(6, n=1)
        EquityShareAllocation.objects.create(
            participant=participant, fiscal_year='2026',
            pool_share_pct=Decimal('50.00'), effective_from=datetime.date(2026, 1, 1), locked=True,
        )
        EquityShareAllocation.objects.create(
            participant=participant, fiscal_year='2027',
            pool_share_pct=Decimal('20.00'), effective_from=datetime.date(2027, 1, 1), locked=True,
        )

        equity.post_profit_pool_credit_for_year('2026', Decimal('1000000.00'))

        credit = participant.clock_events.get(event_type='profit_pool_credit', fiscal_year='2026')
        self.assertEqual(credit.amount.amount, Decimal('500000.00'),  # 50% of 1,000,000
                         '2026 credit must use the 2026 locked share (50%), not the 2027 share')

    def test_lock_blocked_when_shares_do_not_sum_to_100(self):
        p1 = make_participant(6, n=1)
        p2 = make_participant(6, n=2)
        EquityShareAllocation.objects.create(
            participant=p1, fiscal_year='2028',
            pool_share_pct=Decimal('40.00'), effective_from=datetime.date(2028, 1, 1), locked=False,
        )
        EquityShareAllocation.objects.create(
            participant=p2, fiscal_year='2028',
            pool_share_pct=Decimal('50.00'), effective_from=datetime.date(2028, 1, 1), locked=False,
        )
        with self.assertRaises(ValidationError):
            equity.lock_fiscal_year_allocation('2028')

        # Fix the shortfall and confirm locking then succeeds.
        allocation = EquityShareAllocation.objects.get(participant=p2, fiscal_year='2028')
        allocation.pool_share_pct = Decimal('60.00')
        allocation.save(update_fields=['pool_share_pct'])
        equity.lock_fiscal_year_allocation('2028')
        self.assertTrue(
            EquityShareAllocation.objects.filter(fiscal_year='2028', locked=True).count() == 2
        )


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class EquityPoolEndToEndTests(TestCase):
    """Walks the admin flow (list/detail/reallocate/threshold/PDF) as an HRD user, and
    confirms a linked staff account only ever sees its own Equity Pool data."""

    def setUp(self):
        self.client = Client()
        make_hrd_user()
        self.client.login(username='hrd_tester', password='testpass123')
        self.participant = make_participant(6, n=3)
        # StaffDetailView.get_context_data() does Welfare.objects.latest('date') unconditionally
        # (pre-existing, unrelated to Equity Pool) — seed one row so employee-detail doesn't 500
        # on an otherwise-empty test database.
        Welfare.objects.create(staff=self.participant.staff, description='n/a', amount=Money(Decimal('0'), 'NGN'))

    def test_equity_list_loads(self):
        response = self.client.get(reverse('equity-list'))
        self.assertEqual(response.status_code, 200)

    def test_participant_detail_loads(self):
        response = self.client.get(reverse('equity-participant-detail', kwargs={'pk': self.participant.staff_id}))
        self.assertEqual(response.status_code, 200)

    def test_employee_detail_still_loads_after_gratuity_removal(self):
        response = self.client.get(reverse('employee-detail', kwargs={'pk': self.participant.staff_id}))
        self.assertEqual(response.status_code, 200)

    def test_threshold_list_loads(self):
        response = self.client.get(reverse('equity-threshold-list'))
        self.assertEqual(response.status_code, 200)

    def test_reallocation_view_loads(self):
        response = self.client.get(reverse('equity-reallocate', kwargs={'fiscal_year': '2027'}))
        self.assertEqual(response.status_code, 200)

    def test_single_statement_pdf_generates_and_is_stored(self):
        from staff.models import EquityStatement
        response = self.client.get(
            reverse('pdf-equity-statement', kwargs={'pk': self.participant.staff_id}),
            {'fiscal_year': '2026'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(EquityStatement.objects.filter(participant=self.participant).count(), 1)

    def test_bulk_statement_pdf_generates_for_active_participants(self):
        from staff.models import EquityStatement
        response = self.client.get(reverse('pdf-equity-statement-bulk', kwargs={'fiscal_year': '2026'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EquityStatement.objects.filter(fiscal_year='2026').count(), 1)

    def test_non_hrd_user_gets_403_on_admin_list(self):
        User.objects.create_user(username='plain_equity_user', password='pass123')
        anon_client = Client()
        anon_client.login(username='plain_equity_user', password='pass123')
        response = anon_client.get(reverse('equity-list'))
        self.assertEqual(response.status_code, 403)

    def test_my_equity_pool_shows_only_own_participant_data(self):
        applicant = make_applicant('Linked', 'Staff', 4)
        employee = make_employee(applicant, 4)
        employee.is_management = True
        employee.save(update_fields=['is_management'])
        other_participant = make_participant(6, n=5)

        user = User.objects.create_user(username='linked_user', password='pass123')
        user.profile.staff = other_participant.staff
        user.profile.save()

        linked_client = Client()
        linked_client.login(username='linked_user', password='pass123')
        response = linked_client.get(reverse('my-equity-pool'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['participant'], other_participant)
        self.assertNotEqual(response.context['participant'], self.participant)

    def test_my_equity_pool_shows_not_enrolled_for_non_participant(self):
        user = User.objects.create_user(username='unlinked_user', password='pass123')
        unlinked_client = Client()
        unlinked_client.login(username='unlinked_user', password='pass123')
        response = unlinked_client.get(reverse('my-equity-pool'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['participant'])

    def test_help_page_loads_for_hrd_user(self):
        response = self.client.get(reverse('equity-help'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_hrd'])

    def test_help_page_loads_for_plain_authenticated_user(self):
        User.objects.create_user(username='help_reader', password='pass123')
        reader_client = Client()
        reader_client.login(username='help_reader', password='pass123')
        response = reader_client.get(reverse('equity-help'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_hrd'])


class EquityEligibilityTests(TestCase):
    """Participants are derived from active employment only — never from is_management,
    and nothing in this section writes back to Employee (Sec: 'nothing in this section
    should alter the status of a staff')."""

    def setUp(self):
        from staff.form import EquityParticipantForm

        self.form_class = EquityParticipantForm

        self.active_non_management = make_employee(make_applicant('Active', 'NonMgmt', 1), 1)
        self.active_non_management.is_management = False
        self.active_non_management.save(update_fields=['is_management'])

        self.active_management = make_employee(make_applicant('Active', 'Mgmt', 2), 2)
        self.active_management.is_management = True
        self.active_management.save(update_fields=['is_management'])

        self.terminated_management = make_employee(make_applicant('Terminated', 'Mgmt', 3), 3)
        self.terminated_management.is_management = True
        self.terminated_management.status = False
        self.terminated_management.save(update_fields=['is_management', 'status'])

    def test_active_non_management_staff_is_eligible(self):
        queryset = self.form_class().fields['staff'].queryset
        self.assertIn(self.active_non_management, queryset)

    def test_active_management_staff_is_eligible(self):
        queryset = self.form_class().fields['staff'].queryset
        self.assertIn(self.active_management, queryset)

    def test_terminated_staff_is_excluded_even_if_management(self):
        queryset = self.form_class().fields['staff'].queryset
        self.assertNotIn(self.terminated_management, queryset)

    def test_adding_participant_does_not_alter_employee_is_management(self):
        before = self.active_non_management.is_management
        equity.post_grant(EquityParticipant.objects.create(
            staff=self.active_non_management,
            role_code='TEST',
            initial_capital_allocation=Money(Decimal('1000000.00'), 'NGN'),
            grant_date=datetime.date.today(),
        ))
        self.active_non_management.refresh_from_db()
        self.assertEqual(self.active_non_management.is_management, before)

    def test_adding_participant_does_not_alter_employee_status(self):
        before = self.active_management.status
        equity.post_grant(EquityParticipant.objects.create(
            staff=self.active_management,
            role_code='TEST',
            initial_capital_allocation=Money(Decimal('1000000.00'), 'NGN'),
            grant_date=datetime.date.today(),
        ))
        self.active_management.refresh_from_db()
        self.assertEqual(self.active_management.status, before)

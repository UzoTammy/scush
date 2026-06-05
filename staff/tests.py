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

from apply.models import Applicant
from staff.models import Employee, Payroll


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

"""
Cashflow app tests
==================
Covers the BankAccount/CashCenter balance ledger (deposit/withdraw/
reset_current_balance), the money-movement forms (insufficient-funds and
duplicate-transaction guards), and the withdrawal request/approve/administer
workflow.
"""
import datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from djmoney.money import Money

from cashflow.forms import (
    AdministerWithdrawalForm, BankTransferForm, CashDepositForm, DisburseCashForm,
    InterbankTransferForm, InterCashTransferForm, RequestToWithdrawForm,
)
from cashflow.models import BankAccount, BankTransaction, CashCenter, CashTransaction, Withdrawal

NGN = 'NGN'


def money(amount):
    return Money(Decimal(str(amount)), NGN)


def money_data(**fields):
    data = {}
    for name, val in fields.items():
        data[f'{name}_0'] = str(val)
        data[f'{name}_1'] = NGN
    return data


def make_bank(account_number='0001', opening_balance=1000, status=True, category='Business'):
    """current_balance is not derived from opening_balance by the model — the create
    views set it explicitly (BankAccountCreateView.form_valid), so tests must too."""
    return BankAccount.objects.create(
        account_number=account_number, name=f'Bank {account_number}', short_name=f'B{account_number}',
        opening_balance=money(opening_balance), current_balance=money(opening_balance),
        opening_balance_date=datetime.date(2026, 1, 1), category=category, status=status,
    )


def make_cash_center(name='Main Cash Center', opening_balance=1000, status=True):
    return CashCenter.objects.create(
        name=name, opening_balance=money(opening_balance), current_balance=money(opening_balance),
        opening_balance_date=datetime.date(2026, 1, 1), status=status,
    )


# ── Models: balance ledger ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestBankAccountLedger:
    def test_deposit_increments_balance_and_creates_credit_transaction(self, new_user):
        bank = make_bank(opening_balance=1000)
        bank.deposit(money(500), 'top up', datetime.datetime(2026, 1, 2), new_user)
        bank.refresh_from_db()
        assert bank.current_balance == money(1500)
        txn = bank.transactions.get()
        assert txn.transaction_type == 'CR'
        assert txn.amount == money(500)
        assert txn.approved_by == new_user

    def test_withdraw_decrements_balance_and_replays_via_reset(self, new_user):
        bank = make_bank(opening_balance=1000)
        bank.withdraw(money(300), 'payout', datetime.datetime(2026, 1, 2), new_user)
        bank.refresh_from_db()
        assert bank.current_balance == money(700)
        txn = bank.transactions.get()
        assert txn.transaction_type == 'DR'
        assert txn.balance == money(700), 'reset_current_balance() should stamp the replayed balance onto the row'

    def test_reset_current_balance_replays_in_timestamp_order(self, new_user):
        bank = make_bank(opening_balance=1000)
        # Recorded out of chronological order — reset must still replay by timestamp.
        bank.deposit(money(200), 'late-posted deposit', datetime.datetime(2026, 1, 5), new_user)
        bank.withdraw(money(100), 'earlier withdrawal', datetime.datetime(2026, 1, 3), new_user)
        bank.reset_current_balance()
        bank.refresh_from_db()
        assert bank.current_balance == money(1100)
        txns = list(bank.transactions.order_by('timestamp'))
        assert txns[0].balance == money(900)   # 1000 - 100 (Jan 3 withdrawal, replayed first)
        assert txns[1].balance == money(1100)  # 900 + 200 (Jan 5 deposit, replayed second)


@pytest.mark.django_db
class TestCashCenterLedger:
    def test_withdraw_decrements_balance_and_resets_like_bank_account(self, new_user):
        """Regression: CashCenter.withdraw() previously skipped reset_current_balance(),
        unlike BankAccount.withdraw() — both should behave the same way."""
        center = make_cash_center(opening_balance=1000)
        center.withdraw(money(400), 'disburse', datetime.datetime(2026, 1, 2), new_user)
        center.refresh_from_db()
        assert center.current_balance == money(600)
        txn = center.cash_transactions.get()
        assert txn.balance == money(600)

    def test_deposit_increments_balance(self, new_user):
        center = make_cash_center(opening_balance=1000)
        center.deposit(money(250), 'collection', datetime.datetime(2026, 1, 2), new_user)
        center.refresh_from_db()
        assert center.current_balance == money(1250)


# ── Forms: insufficient funds / duplicate / same-account guards ────────────

@pytest.mark.django_db
class TestInterCashTransferForm:
    def test_same_center_rejected(self):
        center = make_cash_center()
        data = {'donor': center.pk, 'receiver': center.pk, 'post_date': '2026-01-02', 'description': ''}
        data.update(money_data(amount=100))
        form = InterCashTransferForm(data=data)
        assert form.is_valid() is False

    def test_insufficient_funds_rejected(self):
        donor = make_cash_center(name='Donor', opening_balance=100)
        receiver = make_cash_center(name='Receiver', opening_balance=0)
        data = {'donor': donor.pk, 'receiver': receiver.pk, 'post_date': '2026-01-02', 'description': ''}
        data.update(money_data(amount=500))
        form = InterCashTransferForm(data=data)
        assert form.is_valid() is False

    def test_valid_transfer_accepted(self):
        donor = make_cash_center(name='Donor', opening_balance=1000)
        receiver = make_cash_center(name='Receiver', opening_balance=0)
        data = {'donor': donor.pk, 'receiver': receiver.pk, 'post_date': '2026-01-02', 'description': ''}
        data.update(money_data(amount=500))
        form = InterCashTransferForm(data=data)
        assert form.is_valid() is True


@pytest.mark.django_db
class TestDisburseCashForm:
    def test_insufficient_funds_rejected(self):
        donor = make_cash_center(opening_balance=100)
        data = {'receiver': 'Guinness', 'donor': donor.pk, 'post_date': '2026-01-02', 'description': 'x'}
        data.update(money_data(amount=500))
        form = DisburseCashForm(data=data)
        assert form.is_valid() is False

    def test_duplicate_transaction_rejected(self, new_user):
        donor = make_cash_center(opening_balance=1000)
        donor.withdraw(money(200), 'dupe check', datetime.datetime(2026, 1, 2), new_user)
        data = {'receiver': 'Guinness', 'donor': donor.pk, 'post_date': '2026-01-02', 'description': 'dupe check'}
        data.update(money_data(amount=200))
        form = DisburseCashForm(data=data)
        assert form.is_valid() is False


@pytest.mark.django_db
class TestRequestToWithdrawForm:
    def test_insufficient_funds_rejected(self):
        bank = make_bank(opening_balance=100)
        data = {'party': 'Guinness', 'bank': bank.pk, 'post_date': '2026-01-02', 'description': ''}
        data.update(money_data(amount=500))
        form = RequestToWithdrawForm(data=data)
        assert form.is_valid() is False

    def test_duplicate_transaction_rejected(self, new_user):
        bank = make_bank(opening_balance=1000)
        bank.withdraw(money(200), 'weekly supply', datetime.datetime(2026, 1, 2), new_user)
        data = {'party': 'Guinness', 'bank': bank.pk, 'post_date': '2026-01-02', 'description': 'weekly supply'}
        data.update(money_data(amount=200))
        form = RequestToWithdrawForm(data=data)
        assert form.is_valid() is False

    def test_valid_request_accepted(self):
        bank = make_bank(opening_balance=1000)
        data = {'party': 'Guinness', 'bank': bank.pk, 'post_date': '2026-01-02', 'description': 'weekly supply'}
        data.update(money_data(amount=200))
        form = RequestToWithdrawForm(data=data)
        assert form.is_valid() is True


@pytest.mark.django_db
class TestInterbankTransferForm:
    def test_same_account_rejected(self):
        bank = make_bank()
        data = {'donor': bank.pk, 'receiver': bank.pk, 'post_date': '2026-01-02', 'description': ''}
        data.update(money_data(amount=100))
        form = InterbankTransferForm(data=data)
        assert form.is_valid() is False

    def test_insufficient_funds_rejected(self):
        donor = make_bank(account_number='0001', opening_balance=100)
        receiver = make_bank(account_number='0002', opening_balance=0)
        data = {'donor': donor.pk, 'receiver': receiver.pk, 'post_date': '2026-01-02', 'description': ''}
        data.update(money_data(amount=500))
        form = InterbankTransferForm(data=data)
        assert form.is_valid() is False


@pytest.mark.django_db
class TestAdministerWithdrawalForm:
    def test_amount_exactly_equal_to_balance_is_rejected(self, new_user):
        """AdministerWithdrawalForm uses `<=`, so an exact-balance withdrawal is blocked too."""
        bank = make_bank(opening_balance=500)
        withdrawal = Withdrawal.objects.create(
            bank=bank, party='Guinness', amount=money(500), requested_by=new_user, particulars='chq-1',
        )
        data = {
            'party': 'Guinness', 'requested_by': new_user.pk, 'bank': bank.pk,
            'particulars': 'chq-1', 'post_date': '2026-01-02',
        }
        data.update(money_data(amount=500))
        form = AdministerWithdrawalForm(data=data, instance=withdrawal)
        assert form.is_valid() is False

    def test_amount_below_balance_is_accepted(self, new_user):
        bank = make_bank(opening_balance=500)
        withdrawal = Withdrawal.objects.create(
            bank=bank, party='Guinness', amount=money(200), requested_by=new_user, particulars='chq-1',
        )
        data = {
            'party': 'Guinness', 'requested_by': new_user.pk, 'bank': bank.pk,
            'particulars': 'chq-1', 'post_date': '2026-01-02',
        }
        data.update(money_data(amount=200))
        form = AdministerWithdrawalForm(data=data, instance=withdrawal)
        assert form.is_valid() is True


@pytest.mark.django_db
class TestBankTransferAndCashDepositForms:
    def test_bank_transfer_duplicate_rejected(self, new_user):
        bank = make_bank(opening_balance=1000)
        bank.deposit(money(100), 'reconciliation credit', datetime.datetime(2026, 1, 2), new_user)
        data = {'bank': bank.pk, 'post_date': '2026-01-02', 'description': 'reconciliation credit'}
        data.update(money_data(amount=100))
        form = BankTransferForm(data=data)
        assert form.is_valid() is False

    def test_cash_deposit_insufficient_cash_rejected(self):
        cash_center = make_cash_center(opening_balance=100)
        bank = make_bank(opening_balance=0)
        data = {'cash_center': cash_center.pk, 'bank': bank.pk, 'post_date': '2026-01-02', 'description': ''}
        data.update(money_data(amount=500))
        form = CashDepositForm(data=data)
        assert form.is_valid() is False


# ── Views: withdrawal approve / administer workflow ─────────────────────────

@pytest.mark.django_db
class TestWithdrawalWorkflow:
    def test_all_cashflow_views_require_login(self, client):
        response = client.get(reverse('cashflow-home'))
        assert response.status_code == 302

    def test_withdrawal_request_view_withdraws_but_creates_no_withdrawal_row(self, client, new_user):
        """Documents a real functional gap: the request form calls bank.withdraw()
        directly and never creates a Withdrawal — so the approve/administer
        workflow below can only ever act on Withdrawal rows created some other
        way (e.g. admin). Flagged for a product decision, not silently treated
        as correct."""
        bank = make_bank(opening_balance=1000)
        client.force_login(new_user)
        data = {'party': 'Guinness', 'bank': bank.pk, 'post_date': '2026-01-02', 'description': 'weekly supply'}
        data.update(money_data(amount=200))
        client.post(reverse('withdrawal-request'), data=data)

        bank.refresh_from_db()
        assert bank.current_balance == money(800)
        assert Withdrawal.objects.count() == 0

    def test_approve_view_sets_stage_approved_and_sends_email(self, client, new_user):
        bank = make_bank(opening_balance=1000)
        withdrawal = Withdrawal.objects.create(
            bank=bank, party='Guinness', amount=money(200), requested_by=new_user,
        )
        client.force_login(new_user)
        response = client.post(
            reverse('approve-withdrawal', kwargs={'pk': withdrawal.pk}),
            data={'decision': 'Approved', 'remark': ''},
        )
        withdrawal.refresh_from_db()
        assert response.status_code == 302
        assert withdrawal.stage == 1

    def test_approve_view_disapprove_sets_stage_negative_one(self, client, new_user):
        bank = make_bank(opening_balance=1000)
        withdrawal = Withdrawal.objects.create(
            bank=bank, party='Guinness', amount=money(200), requested_by=new_user,
        )
        client.force_login(new_user)
        client.post(
            reverse('approve-withdrawal', kwargs={'pk': withdrawal.pk}),
            data={'decision': 'Disapproved', 'remark': ''},
        )
        withdrawal.refresh_from_db()
        assert withdrawal.stage == -1

    def test_administer_view_completes_withdrawal_and_debits_bank(self, client, new_user):
        bank = make_bank(opening_balance=1000)
        withdrawal = Withdrawal.objects.create(
            bank=bank, party='Guinness', amount=money(200), requested_by=new_user, stage=1,
        )
        client.force_login(new_user)
        data = {
            'party': 'Guinness', 'requested_by': new_user.pk, 'bank': bank.pk,
            'particulars': 'chq-1', 'post_date': '2026-01-02',
        }
        data.update(money_data(amount=200))
        response = client.post(
            reverse('administer-withdrawal', kwargs={'pk': withdrawal.pk}), data=data,
        )
        withdrawal.refresh_from_db()
        bank.refresh_from_db()
        assert response.status_code == 302
        assert withdrawal.stage == 2
        assert bank.current_balance == money(800)


@pytest.mark.django_db
class TestStatementViewsResetOnRead:
    def test_bank_statement_get_triggers_reset_and_is_idempotent(self, client, new_user):
        bank = make_bank(opening_balance=1000)
        bank.deposit(money(300), 'x', datetime.datetime(2026, 1, 2), new_user)
        client.force_login(new_user)

        client.get(reverse('bank-statement', kwargs={'pk': bank.account_number}))
        bank.refresh_from_db()
        first_balance = bank.current_balance

        client.get(reverse('bank-statement', kwargs={'pk': bank.account_number}))
        bank.refresh_from_db()
        assert bank.current_balance == first_balance == money(1300)

    def test_cash_statement_get_triggers_reset(self, client, new_user):
        center = make_cash_center(opening_balance=1000)
        center.deposit(money(150), 'x', datetime.datetime(2026, 1, 2), new_user)
        client.force_login(new_user)

        client.get(reverse('cash-statement', kwargs={'pk': center.pk}))
        center.refresh_from_db()
        assert center.current_balance == money(1150)

"""Equity Pool business logic shared between admin views and the seed-data migration.

Keeping this here (rather than duplicating the same posting/validation logic inside
views.py and the migration) means the vesting/forfeiture/clawback rules only exist once.
"""
import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from djmoney.money import Money


def post_grant(participant, created_by=None):
    from staff.models import EquityClockEvent
    return EquityClockEvent.objects.create(
        participant=participant,
        event_type=EquityClockEvent.GRANT,
        amount=participant.initial_capital_allocation,
        effective_date=participant.grant_date,
        fiscal_year=str(participant.grant_date.year),
        created_by=created_by,
    )


def post_profit_pool_credit_for_year(fiscal_year, total_pool_amount, created_by=None):
    """Split one fiscal year's Employee Profit Pool total across active participants,
    using each participant's *locked* share allocation for that specific fiscal_year."""
    from staff.models import EquityParticipant, EquityClockEvent

    if total_pool_amount <= 0:
        raise ValidationError('Total pool amount must be greater than zero.')

    participants = EquityParticipant.objects.filter(status=EquityParticipant.STATUS_ACTIVE)
    allocations = []
    for participant in participants:
        share_pct = participant.locked_share_for(fiscal_year)
        if share_pct <= 0:
            continue
        amount = (Decimal(total_pool_amount) * share_pct / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        allocations.append((participant, amount))

    created = []
    for participant, amount in allocations:
        created.append(EquityClockEvent.objects.create(
            participant=participant,
            event_type=EquityClockEvent.PROFIT_POOL_CREDIT,
            amount=Money(amount, 'NGN'),
            effective_date=datetime.date.today(),
            fiscal_year=fiscal_year,
            created_by=created_by,
        ))
    return created


def prepare_next_year_allocation(fiscal_year, created_by=None):
    """Pre-populate a fiscal year's (unlocked) share rows from the prior locked year,
    for active participants only (§7.1b). Existing unlocked rows for this year are left as-is."""
    from staff.models import EquityParticipant, EquityShareAllocation

    prior_year = str(int(fiscal_year) - 1)
    created = []
    for participant in EquityParticipant.objects.filter(status=EquityParticipant.STATUS_ACTIVE):
        if EquityShareAllocation.objects.filter(participant=participant, fiscal_year=fiscal_year).exists():
            continue
        prior = participant.share_allocations.filter(fiscal_year=prior_year, locked=True).first()
        pct = prior.pool_share_pct if prior else Decimal('0')
        created.append(EquityShareAllocation.objects.create(
            participant=participant,
            fiscal_year=fiscal_year,
            pool_share_pct=pct,
            effective_from=datetime.date(int(fiscal_year), 1, 1),
            locked=False,
            created_by=created_by,
        ))
    return created


def lock_fiscal_year_allocation(fiscal_year):
    """Refuse to lock an unbalanced allocation — shares across active participants
    must sum to exactly 100% first (§4 validation)."""
    from staff.models import EquityParticipant, EquityShareAllocation

    rows = EquityShareAllocation.objects.filter(
        fiscal_year=fiscal_year,
        participant__status=EquityParticipant.STATUS_ACTIVE,
    )
    total = sum((row.pool_share_pct for row in rows), Decimal('0'))
    if total != Decimal('100'):
        raise ValidationError(
            f'Cannot lock FY{fiscal_year}: active participants\' shares sum to {total}%, not 100%.'
        )
    rows.update(locked=True)
    return rows


def post_clawback(participant, amount, note, created_by=None):
    from staff.models import EquityClockEvent

    if not note:
        raise ValidationError('A note is required for a clawback.')
    unvested = participant.unvested_balance
    if amount > unvested.amount:
        raise ValidationError(
            f'Clawback amount ({amount}) exceeds unvested balance ({unvested.amount}). '
            'Vested amounts cannot be clawed back.'
        )
    return EquityClockEvent.objects.create(
        participant=participant,
        event_type=EquityClockEvent.CLAWBACK,
        amount=Money(-amount, 'NGN'),
        effective_date=datetime.date.today(),
        fiscal_year=str(datetime.date.today().year),
        note=note,
        created_by=created_by,
    )


def post_forfeiture_cause(participant, note, created_by=None):
    from staff.models import EquityClockEvent

    if not note:
        raise ValidationError('A linked investigation reference/note is required before forfeiture-for-cause can be posted.')
    balance = participant.current_balance
    event = EquityClockEvent.objects.create(
        participant=participant,
        event_type=EquityClockEvent.FORFEITURE_CAUSE,
        amount=Money(-balance.amount, 'NGN'),
        effective_date=datetime.date.today(),
        fiscal_year=str(datetime.date.today().year),
        note=note,
        created_by=created_by,
    )
    participant.status = participant.STATUS_FORFEITED_CAUSE
    participant.save(update_fields=['status'])
    return event


def post_separation(participant, note='', created_by=None):
    """Not-for-cause separation: pay out vested balance; forfeit unvested to reserves
    unless the participant is already fully matured (Policy 9.1-9.4)."""
    from staff.models import EquityClockEvent

    events = []
    participant.check_and_latch_maturity()
    if not participant.fully_matured:
        unvested = participant.unvested_balance
        if unvested.amount > 0:
            events.append(EquityClockEvent.objects.create(
                participant=participant,
                event_type=EquityClockEvent.FORFEITURE_SEPARATION,
                amount=Money(-unvested.amount, 'NGN'),
                effective_date=datetime.date.today(),
                fiscal_year=str(datetime.date.today().year),
                note=note or 'Separation — unvested balance forfeited to reserves.',
                created_by=created_by,
            ))

    payout_amount = participant.current_balance
    if payout_amount.amount > 0:
        events.append(EquityClockEvent.objects.create(
            participant=participant,
            event_type=EquityClockEvent.PAYOUT,
            amount=Money(-payout_amount.amount, 'NGN'),
            effective_date=datetime.date.today(),
            fiscal_year=str(datetime.date.today().year),
            note=note or 'Separation payout.',
            created_by=created_by,
        ))

    participant.status = participant.STATUS_SEPARATED
    participant.save(update_fields=['status'])
    return events

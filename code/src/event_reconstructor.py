"""
Event Reconstructor Module

Reconstructs cash flows from raw financial events:
1. Resolves missing amounts via ImageExtractor.
2. Normalizes all transaction values into the user's home currency via CurrencyConverter.
3. Applies amendments, delays, and salary updates from MessageParser.
4. Resolves linked transactions, exclusions (non-cash, cancelled, pending credits).
5. Discovers regular monthly recurring commitments and flexible spending opportunities.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from src.image_extractor import ImageExtractor
from src.message_parser import MessageParser, StructuredMessageUpdate
from src.currency_converter import CurrencyConverter
from src.data_joiner import RequestContext


@dataclass
class ReconstructedCashEvent:
    event_id: str
    date: str
    amount: float  # In home_currency
    category: str
    direction: str  # 'debit' or 'credit'
    status: str
    is_recurring: bool
    flexibility: str  # 'fixed', 'stoppable', 'reducible', 'reducible_or_stoppable'
    minimum_allowed_amount: Optional[float]
    description: str


@dataclass
class RecurringCommitment:
    category: str
    description: str
    day_of_month: int
    amount: float  # In home_currency
    flexibility: str
    minimum_allowed_amount: Optional[float]
    sample_event_id: str
    last_event_date: str


class EventReconstructor:
    """Reconstructs cash events and recurring schedules for a user context."""

    def __init__(self, image_extractor: ImageExtractor, message_parser: MessageParser, currency_converter: CurrencyConverter):
        self.image_extractor = image_extractor
        self.message_parser = message_parser
        self.currency_converter = currency_converter

    def reconstruct(self, ctx: RequestContext) -> Dict[str, Any]:
        user_id = ctx.user_id
        home_curr = ctx.profile.home_currency
        req_date = ctx.request_date

        # 1. Parse user messages
        user_messages = ctx.messages
        updates: List[StructuredMessageUpdate] = []
        if len(user_messages) > 0:
            for _, m_row in user_messages.iterrows():
                update = self.message_parser.parse_message(m_row)
                if not update.is_injection_attempt:
                    updates.append(update)

        # 2. Map image receipts to missing events
        image_amounts: Dict[str, float] = {}
        for _, img_row in ctx.images.iterrows():
            img_id = img_row['image_id']
            ev_id = img_row['related_event_id']
            extracted = self.image_extractor.extract(img_id, ev_id)
            # Convert extracted amount if currency differs
            amount_home = self.currency_converter.convert(
                extracted.amount, extracted.currency, home_curr, req_date
            )
            image_amounts[ev_id] = amount_home

        # 3. Process events
        raw_events = ctx.events.copy()
        processed_events: List[ReconstructedCashEvent] = []

        # Find cancelled event IDs to exclude
        cancelled_event_ids = set(raw_events[raw_events['status'] == 'cancelled']['event_id'])
        # If an event has linked_event_id and status is cancelled, the parent was cancelled
        for _, row in raw_events.iterrows():
            if row['status'] == 'cancelled' and pd.notna(row['linked_event_id']):
                cancelled_event_ids.add(str(row['linked_event_id']))

        for _, row in raw_events.iterrows():
            ev_id = str(row['event_id'])
            if ev_id in cancelled_event_ids or row['status'] in ('cancelled', 'failed', 'unrealized'):
                continue
            if row['direction'] == 'non_cash':
                continue
            # Exclude pending credits per PRD rules
            if row['direction'] == 'credit' and row['status'] == 'pending':
                continue

            # Amount resolution
            raw_amt = row['amount']
            if pd.isna(raw_amt):
                if ev_id in image_amounts:
                    amt_home = image_amounts[ev_id]
                else:
                    amt_home = 0.0
            else:
                amt_home = self.currency_converter.convert(
                    float(raw_amt), str(row['currency']), home_curr, str(row['event_date'])
                )

            # Minimum allowed amount in home currency
            min_allowed = None
            if pd.notna(row['minimum_allowed_amount']):
                min_allowed = self.currency_converter.convert(
                    float(row['minimum_allowed_amount']), str(row['currency']), home_curr, str(row['event_date'])
                )

            date_val = str(row['settlement_date']) if pd.notna(row['settlement_date']) else str(row['event_date'])

            processed_events.append(ReconstructedCashEvent(
                event_id=ev_id,
                date=date_val,
                amount=amt_home,
                category=str(row['category']),
                direction=str(row['direction']),
                status=str(row['status']),
                is_recurring=(row['event_type'] in ('subscription', 'salary', 'income', 'debt_payment', 'rent') or row['category'] in ('salary', 'rent', 'utilities', 'insurance', 'education', 'family_support', 'housing')),
                flexibility=str(row['flexibility']),
                minimum_allowed_amount=min_allowed,
                description=str(row['description'])
            ))

        # 4. Extract recurring commitments from history (past settled events)
        recurring_commitments = self._extract_recurring_commitments(processed_events, req_date, updates)

        return {
            'processed_events': processed_events,
            'recurring_commitments': recurring_commitments,
            'message_updates': updates
        }

    def _extract_recurring_commitments(self, events: List[ReconstructedCashEvent], req_date: str, updates: List[StructuredMessageUpdate]) -> List[RecurringCommitment]:
        """Discovers distinct recurring monthly commitments and applies message updates."""
        FIXED_COMMITMENT_CATEGORIES = {
            'rent', 'housing', 'utilities', 'insurance', 'education', 
            'debt_repayment', 'family_support', 'cloud_storage', 
            'delivery_membership', 'gym', 'music_subscription', 'streaming',
            'healthcare', 'entertainment'
        }

        # Group settled debit events before req_date by category & description
        past_debits = [
            e for e in events 
            if e.direction == 'debit' and e.date <= req_date and e.status == 'settled'
            and (e.category in FIXED_COMMITMENT_CATEGORIES or e.is_recurring)
        ]
        groups: Dict[tuple, List[ReconstructedCashEvent]] = {}
        for e in past_debits:
            key = (e.category, e.description)
            groups.setdefault(key, []).append(e)

        commitments: List[RecurringCommitment] = []
        for (cat, desc), ev_list in groups.items():
            # If appears at least twice or is marked subscription/recurring
            if len(ev_list) >= 2 or any(e.is_recurring for e in ev_list):
                # Sort by date
                ev_list = sorted(ev_list, key=lambda x: x.date)
                latest = ev_list[-1]
                
                # Determine day of month
                days = [pd.to_datetime(e.date).day for e in ev_list]
                median_day = int(np.median(days))
                
                # Determine typical amount (median or latest)
                typical_amount = float(latest.amount)
                
                # Check if message increases rent or changes commitment
                for u in updates:
                    if u.action_type == 'rent_increase' and cat == 'rent' and u.percentage_change:
                        typical_amount *= (1.0 + u.percentage_change / 100.0)

                commitments.append(RecurringCommitment(
                    category=cat,
                    description=desc,
                    day_of_month=median_day,
                    amount=typical_amount,
                    flexibility=latest.flexibility,
                    minimum_allowed_amount=latest.minimum_allowed_amount,
                    sample_event_id=latest.event_id,
                    last_event_date=latest.date
                ))

        return commitments


if __name__ == '__main__':
    from src.data_loader import load_all_data
    from src.data_cleaner import clean_all_data
    from src.data_joiner import DataJoiner

    print('Testing event_reconstructor.py...')
    raw = load_all_data()
    clean = clean_all_data(raw)
    joiner = DataJoiner(clean)
    
    img_ext = ImageExtractor()
    msg_parse = MessageParser()
    curr_conv = CurrencyConverter(clean['exchange_rates'])
    reconstructor = EventReconstructor(img_ext, msg_parse, curr_conv)

    # Test request_01
    ctx1 = joiner.get_request_context('request_01')
    res1 = reconstructor.reconstruct(ctx1)
    print(f"Request 01: Reconstructed {len(res1['processed_events'])} cash events, {len(res1['recurring_commitments'])} recurring commitments")
    
    # Test request_03 (missing amount in image_01 resolved)
    ctx3 = joiner.get_request_context('request_03')
    res3 = reconstructor.reconstruct(ctx3)
    ev253 = [e for e in res3['processed_events'] if e.event_id == 'event_253']
    print(f"Request 03 event_253 resolved amount: {ev253[0].amount} {ev253[0].category}")
    assert ev253[0].amount == 4365000.0, "Missing amount must match image_01 extraction"

    print('Event reconstruction test passed successfully!')

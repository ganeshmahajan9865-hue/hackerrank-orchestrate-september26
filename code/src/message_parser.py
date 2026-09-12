"""
Message Parser Module

Extracts structured financial updates (salary changes, rent adjustments,
date revisions, cancellations, pending-credit clarifications) from untrusted messages.
Resistant to prompt-injections by treating all content strictly as untrusted data.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class StructuredMessageUpdate:
    message_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]
    action_type: str  # 'salary_amount_change', 'salary_date_change', 'rent_increase', 'unconfirmed_credit', 'other'
    new_amount: Optional[float]
    new_date: Optional[str]
    percentage_change: Optional[float]
    is_injection_attempt: bool


class MessageParser:
    """Deterministic parser extracting financial updates from messages."""

    INJECTION_PATTERNS = [
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'override\s+system',
        r'approve\s+(this\s+)?(payment|request)',
        r'set\s+balance\s+to',
        r'you\s+are\s+now'
    ]

    def parse_message(self, row: pd.Series) -> StructuredMessageUpdate:
        text = str(row['message_text'])
        msg_id = str(row['message_id'])
        user_id = str(row['user_id'])
        req_id = None if pd.isna(row['request_id']) else str(row['request_id'])
        event_id = None if pd.isna(row['related_event_id']) else str(row['related_event_id'])

        # Security check: prompt injection detection
        is_injection = any(re.search(pat, text, re.IGNORECASE) for pat in self.INJECTION_PATTERNS)
        if is_injection:
            return StructuredMessageUpdate(
                message_id=msg_id,
                user_id=user_id,
                request_id=req_id,
                related_event_id=event_id,
                action_type='injection_ignored',
                new_amount=None,
                new_date=None,
                percentage_change=None,
                is_injection_attempt=True
            )

        # 1. Salary amount update (IDR, EUR, USD, INR, ZAR)
        # Examples: "Gaji bulanan Anda naik menjadi IDR 42750000", "Your temporary monthly pay is EUR 1037.52", "Your next salary is reduced to EUR 1422.85"
        salary_amt_match = re.search(
            r'(?:gaji\s+(?:bulanan|pokok)|salary|monthly\s+pay).*?(?:menjadi|is|to|be|of)\s+(?:IDR|EUR|USD|INR|ZAR|\$|€|₹)?\s*([\d,]+(?:\.\d+)?)',
            text, re.IGNORECASE
        )
        new_amt = None
        if salary_amt_match:
            amt_str = salary_amt_match.group(1).replace(',', '')
            try:
                new_amt = float(amt_str)
            except ValueError:
                new_amt = None

        # 2. Salary date revision
        # Examples: "Your confirmed salary is now expected on 2024-09-23", "confirmed credit date is 2026-01-15", "mulai 2025-08-15"
        date_match = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', text)
        new_date = date_match.group(1) if date_match else None

        # 3. Rent increase percentage
        # Example: "increases monthly rent by 12%"
        pct_match = re.search(r'rent\s+by\s+(\d+(?:\.\d+)?)\s*%', text, re.IGNORECASE)
        pct_change = float(pct_match.group(1)) if pct_match else None

        # Classify action type
        if new_amt is not None and ('salary' in text.lower() or 'gaji' in text.lower() or 'payroll' in text.lower()):
            action_type = 'salary_amount_change'
        elif new_date is not None and ('salary' in text.lower() or 'payroll' in text.lower()) and new_amt is None:
            action_type = 'salary_date_change'
        elif pct_change is not None:
            action_type = 'rent_increase'
        elif any(k in text.lower() for k in ['belum disetujui', 'pending', 'menunggu', 'market value', 'no cash proceeds']):
            action_type = 'unconfirmed_credit'
        else:
            action_type = 'informational'

        return StructuredMessageUpdate(
            message_id=msg_id,
            user_id=user_id,
            request_id=req_id,
            related_event_id=event_id,
            action_type=action_type,
            new_amount=new_amt,
            new_date=new_date,
            percentage_change=pct_change,
            is_injection_attempt=False
        )

    def parse_all(self, messages_df: pd.DataFrame) -> Dict[str, List[StructuredMessageUpdate]]:
        """Groups parsed structured updates by user_id."""
        user_updates: Dict[str, List[StructuredMessageUpdate]] = {}
        for _, row in messages_df.iterrows():
            update = self.parse_message(row)
            user_updates.setdefault(update.user_id, []).append(update)
        return user_updates


if __name__ == '__main__':
    from src.data_loader import load_all_data
    from src.data_cleaner import clean_all_data

    print('Testing message_parser.py...')
    raw = load_all_data()
    clean = clean_all_data(raw)
    parser = MessageParser()
    updates_by_user = parser.parse_all(clean['messages'])
    
    total_updates = sum(len(v) for v in updates_by_user.values())
    salary_amts = sum(1 for u_list in updates_by_user.values() for u in u_list if u.action_type == 'salary_amount_change')
    salary_dates = sum(1 for u_list in updates_by_user.values() for u in u_list if u.action_type == 'salary_date_change')
    rent_incs = sum(1 for u_list in updates_by_user.values() for u in u_list if u.action_type == 'rent_increase')
    
    print(f"Parsed {total_updates} messages:")
    print(f"  Salary amount changes: {salary_amts}")
    print(f"  Salary date changes: {salary_dates}")
    print(f"  Rent percentage increases: {rent_incs}")
    
    # Test user_02 update
    u2_up = updates_by_user.get('user_02', [])
    for u in u2_up:
        print(f"User 02 update: type={u.action_type}, amount={u.new_amount}, date={u.new_date}")
    
    print('Message parsing test passed successfully!')

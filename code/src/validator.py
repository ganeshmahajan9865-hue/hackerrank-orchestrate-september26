"""
Validator Module

Implements Section 7 and PRD Phase 17 validation checklist.
Ensures every row strictly conforms to the schema, mathematical invariants,
chronological constraints, and payment plan contracts.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import datetime
import pandas as pd

from src.data_joiner import RequestContext, DataJoiner


@dataclass
class ValidationIssue:
    request_id: str
    column: str
    severity: str  # 'ERROR', 'WARNING'
    message: str


class OutputValidator:
    """Validates predicted output rows against ground-truth contracts and financial consistency rules."""

    EXPECTED_COLUMNS = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed',
        'decision_explanation'
    ]

    ALLOWED_STATUSES = {'affordable_now', 'affordable_with_plan', 'affordable_later', 'not_affordable'}
    ALLOWED_METHODS = {'full_payment', 'partial_payment', 'installments', 'wait', 'not_recommended'}

    def __init__(self, joiner: Optional[DataJoiner] = None):
        self.joiner = joiner

    def validate_dataframe(self, df: pd.DataFrame, expected_count: Optional[int] = None) -> List[ValidationIssue]:
        """Runs full validation suite on the prediction DataFrame."""
        issues: List[ValidationIssue] = []

        # 1. Check exact columns and order
        if list(df.columns) != self.EXPECTED_COLUMNS:
            issues.append(ValidationIssue(
                request_id='HEADER',
                column='columns',
                severity='ERROR',
                message=f"Columns mismatch! Expected: {self.EXPECTED_COLUMNS}, got: {list(df.columns)}"
            ))

        # 2. Check row count
        if expected_count is not None and len(df) != expected_count:
            issues.append(ValidationIssue(
                request_id='COUNT',
                column='row_count',
                severity='ERROR',
                message=f"Expected {expected_count} rows, got {len(df)}"
            ))

        # 3. Check duplicate request_ids
        dups = df[df.duplicated(subset=['request_id'])]
        if len(dups) > 0:
            for dup_id in dups['request_id'].unique():
                issues.append(ValidationIssue(
                    request_id=str(dup_id),
                    column='request_id',
                    severity='ERROR',
                    message="Duplicate request_id found in output"
                ))

        # 4. Row-by-row validation
        for _, row in df.iterrows():
            req_id = str(row['request_id'])
            ctx = self.joiner.get_request_context(req_id) if self.joiner else None
            row_issues = self.validate_row(row.to_dict(), ctx)
            issues.extend(row_issues)

        return issues

    def validate_row(self, row: Dict[str, Any], ctx: Optional[RequestContext] = None) -> List[ValidationIssue]:
        """Validates an individual output record."""
        issues: List[ValidationIssue] = []
        req_id = str(row['request_id'])

        # amount_safe_to_pay
        try:
            safe_amt = float(row['amount_safe_to_pay'])
            if safe_amt < 0:
                issues.append(ValidationIssue(req_id, 'amount_safe_to_pay', 'ERROR', f"Negative safe amount: {safe_amt}"))
            if ctx and safe_amt > ctx.requested_amount + 1e-4:
                issues.append(ValidationIssue(req_id, 'amount_safe_to_pay', 'ERROR', f"Safe amount ({safe_amt}) exceeds requested amount ({ctx.requested_amount})"))
        except Exception as ex:
            issues.append(ValidationIssue(req_id, 'amount_safe_to_pay', 'ERROR', f"Invalid numeric amount_safe_to_pay: {ex}"))

        # affordability_status
        status = str(row['affordability_status'])
        if status not in self.ALLOWED_STATUSES:
            issues.append(ValidationIssue(req_id, 'affordability_status', 'ERROR', f"Invalid status: {status}"))

        # recommended_payment_method
        method = str(row['recommended_payment_method'])
        if method not in self.ALLOWED_METHODS:
            issues.append(ValidationIssue(req_id, 'recommended_payment_method', 'ERROR', f"Invalid method: {method}"))

        if ctx and method != 'not_recommended':
            allowed_methods = ctx.profile.payment_methods_user_will_consider
            # 'wait' is allowed if user considers full_payment
            check_method = 'full_payment' if method == 'wait' else method
            if check_method not in allowed_methods:
                issues.append(ValidationIssue(req_id, 'recommended_payment_method', 'ERROR', f"Method {method} not in user considered methods: {allowed_methods}"))

        # earliest_date_for_full_payment
        earliest = row.get('earliest_date_for_full_payment')
        earliest_str = str(earliest) if pd.notna(earliest) and earliest != '' else None

        if status == 'affordable_now':
            if ctx and earliest_str != ctx.request_date:
                issues.append(ValidationIssue(req_id, 'earliest_date_for_full_payment', 'ERROR', f"affordable_now must have earliest_date == request_date ({ctx.request_date}), got {earliest_str}"))
            if method != 'full_payment':
                issues.append(ValidationIssue(req_id, 'recommended_payment_method', 'ERROR', f"affordable_now must use full_payment, got {method}"))

        if method == 'wait':
            if status != 'affordable_later':
                issues.append(ValidationIssue(req_id, 'affordability_status', 'ERROR', f"wait method must have affordable_later status, got {status}"))
            if not earliest_str:
                issues.append(ValidationIssue(req_id, 'earliest_date_for_full_payment', 'ERROR', "wait method requires earliest_date_for_full_payment"))
            elif ctx and earliest_str <= ctx.request_date:
                issues.append(ValidationIssue(req_id, 'earliest_date_for_full_payment', 'ERROR', f"wait method earliest_date ({earliest_str}) must be after request_date ({ctx.request_date})"))

        if method == 'not_recommended':
            if status != 'not_affordable':
                issues.append(ValidationIssue(req_id, 'affordability_status', 'ERROR', f"not_recommended method must have not_affordable status, got {status}"))
            if row.get('payment_plan') != 'none':
                issues.append(ValidationIssue(req_id, 'payment_plan', 'ERROR', f"not_recommended method must have payment_plan 'none', got {row.get('payment_plan')}"))

        # payment_plan format
        plan_str = str(row['payment_plan'])
        if plan_str != 'none':
            parts = plan_str.split('|')
            prev_date = None
            total_plan_amt = 0.0
            for p in parts:
                tokens = p.split(':')
                if len(tokens) != 2:
                    issues.append(ValidationIssue(req_id, 'payment_plan', 'ERROR', f"Malformed plan token: {p}"))
                    continue
                d_val, a_val = tokens[0], tokens[1]
                try:
                    p_date = datetime.date.fromisoformat(d_val)
                    if prev_date and p_date < prev_date:
                        issues.append(ValidationIssue(req_id, 'payment_plan', 'ERROR', f"Plan dates not chronological: {d_val} after {prev_date}"))
                    prev_date = p_date
                except Exception:
                    issues.append(ValidationIssue(req_id, 'payment_plan', 'ERROR', f"Invalid date in plan: {d_val}"))

                try:
                    amt = float(a_val)
                    total_plan_amt += amt
                except Exception:
                    issues.append(ValidationIssue(req_id, 'payment_plan', 'ERROR', f"Invalid amount in plan: {a_val}"))

            if method == 'partial_payment':
                if len(parts) != 2:
                    issues.append(ValidationIssue(req_id, 'payment_plan', 'ERROR', f"partial_payment must have exactly 2 payments, got {len(parts)}"))
                if ctx and abs(total_plan_amt - ctx.requested_amount) > 0.05:
                    issues.append(ValidationIssue(req_id, 'payment_plan', 'ERROR', f"partial_payment total ({total_plan_amt}) does not sum to requested amount ({ctx.requested_amount})"))

        # spending_changes_needed
        changes_str = str(row['spending_changes_needed'])
        if changes_str != 'none':
            changes = changes_str.split('|')
            if len(changes) > 3:
                issues.append(ValidationIssue(req_id, 'spending_changes_needed', 'ERROR', f"More than 3 spending changes: {len(changes)}"))
            stopped_ids = set()
            reduced_ids = set()
            for c in changes:
                c_tokens = c.split(':')
                act = c_tokens[0]
                ev_id = c_tokens[1] if len(c_tokens) > 1 else ''
                if act not in ('stop', 'reduce_to'):
                    issues.append(ValidationIssue(req_id, 'spending_changes_needed', 'ERROR', f"Invalid action: {act}"))
                if act == 'stop':
                    stopped_ids.add(ev_id)
                elif act == 'reduce_to':
                    reduced_ids.add(ev_id)

            collision = stopped_ids.intersection(reduced_ids)
            if collision:
                issues.append(ValidationIssue(req_id, 'spending_changes_needed', 'ERROR', f"Event collision between stop and reduce: {collision}"))

        # decision_explanation
        exp_str = str(row['decision_explanation']).strip()
        if not exp_str or exp_str == 'nan':
            issues.append(ValidationIssue(req_id, 'decision_explanation', 'ERROR', "decision_explanation is empty"))

        return issues

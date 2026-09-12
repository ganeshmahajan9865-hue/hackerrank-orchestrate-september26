"""
Data Joiner Module

Assembles all relevant context (profile, events, payment options,
messages, images) for a specific request into a cohesive RequestContext.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd


@dataclass
class UserProfile:
    user_id: str
    home_currency: str
    current_available_balance: float
    minimum_balance_to_keep: float
    financial_priorities: list
    expense_categories_to_protect: list
    expense_categories_user_is_willing_to_reduce: list
    expense_categories_user_is_willing_to_stop: list
    payment_methods_user_will_consider: list
    max_installment_months: Optional[float]


@dataclass
class RequestContext:
    request_id: str
    user_id: str
    request_date: str
    request_type: str
    requested_amount: float
    desired_completion_date: str
    allows_partial_payment: bool
    request_text: str
    profile: UserProfile
    events: pd.DataFrame
    payment_options: pd.DataFrame
    messages: pd.DataFrame
    images: pd.DataFrame


class DataJoiner:
    """Indexed joins across all cleaned datasets for sub-millisecond context retrieval."""

    def __init__(self, cleaned_data: Dict[str, pd.DataFrame]):
        self.raw_data = cleaned_data
        
        # Combine requests and sample_requests for seamless unified lookup
        all_reqs = []
        if 'requests' in cleaned_data:
            all_reqs.append(cleaned_data['requests'])
        if 'sample_requests' in cleaned_data:
            all_reqs.append(cleaned_data['sample_requests'])
            
        self.requests_df = pd.concat(all_reqs, ignore_index=True).drop_duplicates(subset=['request_id'])
        self.requests_by_id = self.requests_df.set_index('request_id', drop=False)
        
        # Index profiles
        profiles_df = cleaned_data['financial_profiles']
        self.profiles_by_user = profiles_df.set_index('user_id', drop=False)
        
        # Group events by user_id
        events_df = cleaned_data['financial_events']
        self.events_by_user = dict(tuple(events_df.groupby('user_id')))
        
        # Group payment options by request_id
        rpo_df = cleaned_data['request_payment_options']
        self.rpo_by_request = dict(tuple(rpo_df.groupby('request_id')))
        
        # Group messages by user_id
        msg_df = cleaned_data['messages']
        self.msg_by_user = dict(tuple(msg_df.groupby('user_id')))
        
        # Group images by user_id
        img_df = cleaned_data['images']
        self.img_by_user = dict(tuple(img_df.groupby('user_id')))

    def get_user_profile(self, user_id: str) -> UserProfile:
        if user_id not in self.profiles_by_user.index:
            raise KeyError(f'User ID {user_id} not found in financial profiles.')
        row = self.profiles_by_user.loc[user_id]
        return UserProfile(
            user_id=row['user_id'],
            home_currency=row['home_currency'],
            current_available_balance=float(row['current_available_balance']),
            minimum_balance_to_keep=float(row['minimum_balance_to_keep']),
            financial_priorities=row['financial_priorities_list'],
            expense_categories_to_protect=row['expense_categories_to_protect_list'],
            expense_categories_user_is_willing_to_reduce=row['expense_categories_user_is_willing_to_reduce_list'],
            expense_categories_user_is_willing_to_stop=row['expense_categories_user_is_willing_to_stop_list'],
            payment_methods_user_will_consider=row['payment_methods_user_will_consider_list'],
            max_installment_months=None if pd.isna(row['max_installment_months']) else float(row['max_installment_months'])
        )

    def get_request_context(self, request_id: str) -> RequestContext:
        if request_id not in self.requests_by_id.index:
            raise KeyError(f'Request ID {request_id} not found in requests dataset.')
        
        req_row = self.requests_by_id.loc[request_id]
        user_id = req_row['user_id']
        profile = self.get_user_profile(user_id)
        
        # Retrieve user events
        empty_events = self.raw_data['financial_events'].iloc[0:0].copy()
        events = self.events_by_user.get(user_id, empty_events).copy()
        
        # Retrieve payment options for this request
        empty_rpo = self.raw_data['request_payment_options'].iloc[0:0].copy()
        payment_options = self.rpo_by_request.get(request_id, empty_rpo).copy()
        
        # Retrieve user messages (can filter to request or related events)
        empty_msg = self.raw_data['messages'].iloc[0:0].copy()
        messages = self.msg_by_user.get(user_id, empty_msg).copy()
        
        # Retrieve user images
        empty_img = self.raw_data['images'].iloc[0:0].copy()
        images = self.img_by_user.get(user_id, empty_img).copy()
        
        return RequestContext(
            request_id=request_id,
            user_id=user_id,
            request_date=req_row['request_date'],
            request_type=req_row['request_type'],
            requested_amount=float(req_row['requested_amount']),
            desired_completion_date=req_row['desired_completion_date'],
            allows_partial_payment=bool(req_row['allows_partial_payment']),
            request_text=req_row['request_text'],
            profile=profile,
            events=events,
            payment_options=payment_options,
            messages=messages,
            images=images
        )


if __name__ == '__main__':
    from src.data_loader import load_all_data
    from src.data_cleaner import clean_all_data
    
    print('Testing data_joiner.py...')
    raw = load_all_data()
    clean = clean_all_data(raw)
    joiner = DataJoiner(clean)
    
    # Test sample request_01
    ctx = joiner.get_request_context('request_01')
    print(f'Context loaded for {ctx.request_id}:')
    print(f'  User: {ctx.user_id} ({ctx.profile.home_currency})')
    print(f'  Balance: {ctx.profile.current_available_balance:,.2f}, Min balance: {ctx.profile.minimum_balance_to_keep:,.2f}')
    print(f'  Events count: {len(ctx.events)}')
    print(f'  Payment options count: {len(ctx.payment_options)}')
    print(f'  Messages count: {len(ctx.messages)}')
    print(f'  Images count: {len(ctx.images)}')
    
    # Test evaluation request_26
    ctx26 = joiner.get_request_context('request_26')
    print(f'\nContext loaded for {ctx26.request_id}:')
    print(f'  User: {ctx26.user_id} ({ctx26.profile.home_currency})')
    print(f'  Events count: {len(ctx26.events)}')
    print(f'  Payment options count: {len(ctx26.payment_options)}')
    
    print('\nData joining test passed successfully!')

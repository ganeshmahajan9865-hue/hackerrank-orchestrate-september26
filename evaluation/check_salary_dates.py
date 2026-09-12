import sys, os
sys.path.insert(0, '.')
import pandas as pd
import datetime

from src.data_loader import load_all_data
raw = load_all_data()
samples = raw['sample_requests']
events = raw['financial_events']
profiles = raw['financial_profiles']

print(f"{'Req ID':<10} {'Req Date':<11} {'Sal Date':<11} {'Days':>4} {'Diff':>14} {'Diff/Days':>12}")

for _, row in samples.iterrows():
    u_id = row['user_id']
    r_date = datetime.date.fromisoformat(row['request_date'])
    prof = profiles[profiles['user_id'] == u_id].iloc[0]
    headroom = prof['current_available_balance'] - prof['minimum_balance_to_keep']
    diff = headroom - row['amount_safe_to_pay']
    
    # Find next salary date
    u_sal = events[(events['user_id'] == u_id) & (events['category'] == 'salary') & (events['direction'] == 'credit')]
    # find salary day of month
    sal_days = [pd.to_datetime(d).day for d in u_sal['event_date']]
    sal_day = sal_days[0] if sal_days else 15
    
    # Next salary date
    if r_date.day < sal_day:
        next_sal = datetime.date(r_date.year, r_date.month, sal_day)
    else:
        m = r_date.month + 1
        y = r_date.year
        if m > 12:
            m = 1
            y += 1
        next_sal = datetime.date(y, m, sal_day)
        
    days = (next_sal - r_date).days
    rate = diff / days if days > 0 else 0
    print(f"{row['request_id']:<10} {str(r_date):<11} {str(next_sal):<11} {days:>4} {diff:>14,.2f} {rate:>12,.2f}")

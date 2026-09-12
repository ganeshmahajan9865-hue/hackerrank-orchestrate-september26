import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data
raw = load_all_data()
df = raw['financial_events']
profiles = raw['financial_profiles']

diffs = {
    'user_08': 452.0,
    'user_14': 1134.0,
    'user_15': 487.0,
    'user_18': 624.0,
    'user_21': 568.0,
    'user_22': 157.0,
}

for u_id, diff in diffs.items():
    u_events = df[df['user_id'] == u_id]
    u_debits = u_events[u_events['direction'] == 'debit']
    print(f"=== {u_id}: Target Diff = {diff} ===")
    
    # Check pending debits
    pending = u_debits[u_debits['status'] == 'pending']['amount'].sum()
    rem = diff - pending
    print(f"  Pending debits sum: {pending}, Remainder: {rem}")
    
    # Check debits by category in the last complete month
    # Find all combinations of categories or recurring events matching remainder
    cats = u_debits.groupby(['category', 'description'])['amount'].mean().reset_index()
    print("  Distinct categories and average amounts:")
    for _, c_row in cats.iterrows():
        print(f"    {c_row['category']}: {c_row['description']} = {c_row['amount']}")

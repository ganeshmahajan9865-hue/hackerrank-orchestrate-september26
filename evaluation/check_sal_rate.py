import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data

raw = load_all_data()
df = raw['financial_events']

for u_id, daily_rate in [
    ('user_03', 189050.0),
    ('user_07', 3877.5),
    ('user_08', 56.5),
    ('user_18', 78.0),
    ('user_22', 11.4),
    ('user_24', 1875.0),
    ('user_25', 806550.0),
]:
    u_sal = df[(df['user_id'] == u_id) & (df['category'] == 'salary')]
    sal_amt = u_sal['amount'].dropna().iloc[-1]
    print(f"{u_id}: Salary = {sal_amt:,.2f}, Rate*30 = {daily_rate*30:,.2f}")

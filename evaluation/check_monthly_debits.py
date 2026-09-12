import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data

raw = load_all_data()
df = raw['financial_events']
samples = raw['sample_requests']

print(f"{'User':<8} {'Daily Rate':>12} {'Monthly (Rate*30)':>18} {'Avg Monthly Debits':>20}")

for u_id, daily_rate in [
    ('user_03', 189050.0),
    ('user_07', 3877.5),
    ('user_08', 56.5),
    ('user_18', 78.0),
    ('user_22', 11.4),
    ('user_24', 1875.0),
    ('user_25', 806550.0),
]:
    u_events = df[df['user_id'] == u_id]
    u_debits = u_events[(u_events['direction'] == 'debit') & (u_events['status'] == 'settled')]
    # calculate total settled debits
    total_debits = u_debits['amount'].sum()
    # number of months in history (from min date to max date)
    min_date = pd.to_datetime(u_debits['event_date'].min())
    max_date = pd.to_datetime(u_debits['event_date'].max())
    months = (max_date - min_date).days / 30.4375
    avg_m_debits = total_debits / months if months > 0 else 0
    print(f"{u_id:<8} {daily_rate:>12,.2f} {daily_rate * 30:>18,.2f} {avg_m_debits:>20,.2f}")

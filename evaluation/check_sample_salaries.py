import sys, os
sys.path.insert(0, '.')
import pandas as pd
from src.data_loader import load_all_data

raw = load_all_data()
df = raw['financial_events']
samples = raw['sample_requests']

for _, row in samples.iterrows():
    u_id = row['user_id']
    r_date = row['request_date']
    u_ev = df[df['user_id'] == u_id]
    fut_sal = u_ev[(u_ev['category'] == 'salary') & ((u_ev['settlement_date'] >= r_date) | (u_ev['event_date'] >= r_date))]
    print(f"{row['request_id']} ({u_id}) r_date={r_date}: {len(fut_sal)} future salary events")
    for _, s in fut_sal.iterrows():
        print(f"   {s['event_id']}: {s['event_date']} {s['status']} {s['amount']}")

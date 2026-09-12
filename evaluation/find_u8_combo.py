import sys, os
sys.path.insert(0, '.')
import pandas as pd
import itertools

df = pd.read_csv('dataset/financial_events.csv')
u8 = df[df['user_id'] == 'user_08']
debits = u8[u8['direction'] == 'debit']

target = 452.0
# Look at unique amounts in user_08
print("Finding combination for 452.0 in user_08:")
for r in range(1, 6):
    for c in itertools.combinations(debits.to_dict('records'), r):
        if abs(sum(x['amount'] for x in c) - target) < 1e-4:
            print("Found match:", [f"{x['category']}:{x['amount']}" for x in c])
            break

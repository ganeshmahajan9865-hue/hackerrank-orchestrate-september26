import sys, os
sys.path.insert(0, '.')
import datetime
import pandas as pd
from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner

raw = load_all_data()
clean = clean_all_data(raw)
joiner = DataJoiner(clean)
ctx = joiner.get_request_context('request_01')

curr_bal = ctx.profile.current_available_balance
min_bal = ctx.profile.minimum_balance_to_keep
req_amt = ctx.requested_amount
req_date = datetime.date.fromisoformat(ctx.request_date)

# Test daily simulation
daily_deltas = {req_date + datetime.timedelta(days=i): 0.0 for i in range(91)}

# Explicit future events
# event_102: pending debit 567.60 on 2024-03-05
daily_deltas[datetime.date(2024, 3, 5)] -= 567.60
# event_103: scheduled credit 23320 on 2024-03-15
daily_deltas[datetime.date(2024, 3, 15)] += 23320.00
# Future salaries on 2024-04-15 and 2024-05-15
daily_deltas[datetime.date(2024, 4, 15)] += 23320.00
daily_deltas[datetime.date(2024, 5, 15)] += 23320.00

# Commitments:
# utilities day 6: 1507.80
# education day 8: 1821.60
# debt_repayment day 11: 3487.00
# music day 11: 235.40
# delivery day 13: 306.90
# rent day 2 (starts next month April 2, May 2)
for dt in daily_deltas:
    if dt.day == 6 and dt >= req_date:
        daily_deltas[dt] -= 1507.80
    if dt.day == 8 and dt >= req_date:
        daily_deltas[dt] -= 1821.60
    if dt.day == 11 and dt >= req_date:
        daily_deltas[dt] -= (3487.00 + 235.40)
    if dt.day == 13 and dt >= req_date:
        daily_deltas[dt] -= 306.90
    if dt.day == 2 and dt > req_date: # day 2 next month!
        daily_deltas[dt] -= 5148.00

# Simulate with paying 25256 on req_date
b = curr_bal - req_amt
min_seen = b
for dt in sorted(daily_deltas.keys()):
    b += daily_deltas[dt]
    if b < min_seen:
        min_seen = b

print(f"Opening balance after paying full amount: {curr_bal - req_amt:,.2f}")
print(f"Lowest balance seen over 90 days: {min_seen:,.2f}")
print(f"Minimum balance to keep: {min_bal:,.2f}")
print(f"Headroom above min: {min_seen - min_bal:,.2f}")
print(f"Is safe? {min_seen >= min_bal}")

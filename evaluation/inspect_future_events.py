import pandas as pd
samples = pd.read_csv('dataset/sample_requests.csv')
events = pd.read_csv('dataset/financial_events.csv')

for idx, row in samples.iterrows():
    req_id = row['request_id']
    u_id = row['user_id']
    r_date = row['request_date']
    u_ev = events[events['user_id'] == u_id]
    fut_ev = u_ev[(u_ev['settlement_date'] >= r_date) | ((u_ev['settlement_date'].isna()) & (u_ev['event_date'] >= r_date))]
    print(f"{req_id} ({u_id}) r_date={r_date}: {len(fut_ev)} future events")
    for _, fe in fut_ev.iterrows():
        print(f"  {fe['event_id']}: date={fe['event_date']}, sett={fe['settlement_date']}, dir={fe['direction']}, stat={fe['status']}, amt={fe['amount']}, cat={fe['category']}, flex={fe['flexibility']}")

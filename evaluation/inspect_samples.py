import pandas as pd

df = pd.read_csv('dataset/sample_requests.csv')
for idx, row in df.iterrows():
    print(f"{row['request_id']}: safe={row['amount_safe_to_pay']}, status={row['affordability_status']}, method={row['recommended_payment_method']}")
    print(f"  Plan: {row['payment_plan']}")
    print(f"  Earliest: {row['earliest_date_for_full_payment']}")
    print(f"  Changes: {row['spending_changes_needed']}")
    print(f"  Explanation: {row['decision_explanation']}\n")

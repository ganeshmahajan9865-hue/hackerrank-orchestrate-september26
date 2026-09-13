# Modifying Flexible Spending to Enable Purchase Goals

When a requested purchase is unaffordable under current spending trajectories, making disciplined spending adjustments can safely unlock the necessary headroom.

### Permitted Adjustment Actions
- `stop:<event_id>`: Cease an upcoming non-essential recurring subscription or lifestyle service completely.
- `reduce_to:<event_id>:<new_amount>`: Scale down an upcoming discretionary debit to a lower permitted floor.

### Strict Governance Rules
1. User Consent: Adjustments are exclusively permitted in categories the user has explicitly consented to adjust (`expense_categories_user_is_willing_to_stop` and `expense_categories_user_is_willing_to_reduce`).
2. Absolute Floor Protection: No spending category can ever be reduced below its established minimum allowed amount.
3. Limited Action Budget: A maximum of three total spending interventions may be recommended for any single purchase request.

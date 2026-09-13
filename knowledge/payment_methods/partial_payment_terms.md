# Structure and Rules for Partial Payments

A partial payment splits a purchase into two discrete installments: a safe down payment today, followed by the remaining balance on the earliest safe future date.

### Mandatory Conditions for Partial Payments
1. Request Allowance: The seller or request terms must explicitly permit partial payments (`partial_payment_allowed = True`).
2. User Acceptance: The user's preferences must accept partial payments.
3. Strict Two-Payment Structure:
   - Payment 1: Exactly `amount_safe_to_pay` on `request_date`.
   - Payment 2: Exactly `requested_amount - amount_safe_to_pay` on `earliest_date_for_full_payment`.
4. Deadline Adherence: The second payment date must arrive on or before the user's `desired_completion_date`.
5. Sum Integrity: The two payments must strictly sum to the total requested amount.

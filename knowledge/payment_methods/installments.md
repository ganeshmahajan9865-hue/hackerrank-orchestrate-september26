# Managing Installment Payments Responsibly

Installment payment plans spread an expense across multiple billing cycles, lowering the immediate liquidity drain.

### Criteria for Recommending Installments
1. User Willingness: The user's profile must explicitly allow installments (`max_installment_months > 0`).
2. Plan Duration Constraint: The plan duration cannot exceed the user's `max_installment_months`.
3. Cumulative Cash Flow Feasibility: Each scheduled monthly payment must be fully survivable throughout the entire plan horizon without breaching the user's minimum balance threshold.
4. Total Financing Cost: Shorter installment terms with lower aggregate interest/fees are strictly preferred over longer, more expensive options.

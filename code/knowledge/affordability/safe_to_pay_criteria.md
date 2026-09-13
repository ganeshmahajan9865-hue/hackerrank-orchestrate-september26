# Safe-to-Pay Determination Criteria

The `amount_safe_to_pay` represents the maximum cash an individual can part with on the request date without triggering a cash flow shortfall over the next 90 days.

### Core Affordability Standards
- Preservation of Buffer: Balance must never dip below the user's required `minimum_balance_to_keep`.
- Protection of Essentials: Ongoing payments for protected categories (rent, food, utilities, health) must remain 100% funded.
- Upfront Limits: If the requested cost exceeds available headroom, `amount_safe_to_pay` equals the exact constrained headroom (bounded between 0 and the requested total).
- True Affordability: An item is only `affordable_now` if the safe-to-pay amount covers 100% of the requested expense upfront.

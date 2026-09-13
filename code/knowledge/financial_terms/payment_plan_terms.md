# Payment Plan Vocabulary and Formatting Rules

Financial recommendations follow strict semantic conventions to ensure unambiguous execution by banking systems and consumer users.

### Payment Plan Notation
- Format: Chronological sequence of pipe-separated `YYYY-MM-DD:amount` tuples (e.g., `2026-04-06:268.74|2026-05-06:268.74|2026-06-05:268.74`).
- Precision: All monetary figures formatted to exact decimal precision matching the user profile currency.
- Sum Equivalence: The aggregate sum of all payments in the plan must strictly equal the total required payment obligation.
- `none` Value: Used exclusively when no payment is scheduled or when the recommendation is `not_recommended`.

### Earliest Full Payment Date
The first conservative calendar date where a single lump-sum full payment is 100% safe without breaching minimum balance. For `affordable_now`, this is identical to `request_date`. For `not_affordable`, this field is left empty.

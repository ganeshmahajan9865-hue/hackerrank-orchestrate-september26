# HackerRank Orchestrate

Starter repository for the **HackerRank Orchestrate** 24-hour hackathon (September 2026).

## Buy or Wait?

Build an AI-powered financial agent that decides whether a user can safely afford a requested expense.

A user may ask: **"Can I afford this laptop?"**

Answering well takes more than the current balance. The agent must account for recurring expenses, pending payments, essential spending, confirmed income, available payment options, and relevant details buried in messages and images.

For every request, the agent decides whether the user should pay in full, pay partially, use installments, wait, or not proceed. The recommendation must be personalized: two users with the same balance can deserve different answers based on their commitments, priorities, payment preferences, and willingness to adjust flexible expenses.

A recommendation is safe only if the user can complete the full payment plan, cover essential expenses, and stay above their preferred minimum balance throughout the forecast period.

Read [`problem_statement.md`](./problem_statement.md) for the full task spec, input/output schema, allowed values, conflict-resolution rules, and submission format.

---

## Quick Start

Clone the repository and move into the project directory:

```bash
git clone https://github.com/interviewstreet/hackerrank-orchestrate-september26.git
cd hackerrank-orchestrate-september26
```

Build your solution in `code/main.py`, or use another language and document its entry point clearly.

Your solution must:

- Read the input files from `dataset/`
- Generate one prediction for every request
- Write the final predictions to `output.csv` in the repository root

Run the starter Python entry point with:

```bash
python3 code/main.py
```

After running your solution, confirm that `output.csv` exists in the repository root and contains the required columns and one row for every request.

## Important File Locations

```text
dataset/        Input data and the blank output template. Do not modify the input data.
code/           Your solution code.
output.csv      Final generated predictions in the repository root.
code.zip        ZIP file containing your complete solution for submission.
```

The blank template at `dataset/output.csv` is provided as a reference. Your final generated file must be the root-level `output.csv`.

---

## Repository Layout

```text
.
├── AGENTS.md                         # Rules for AI coding tools + transcript logging
├── problem_statement.md              # Full challenge statement
├── README.md                         # You are here
├── code/                             # Your solution code
├── output.csv                        # Final generated predictions
└── dataset/
    ├── requests.csv                  # 250 requests to evaluate — predict these
    ├── output.csv                    # Blank submission template
    ├── sample_requests.csv           # 25 solved examples
    ├── financial_profiles.csv        # Balances, minimum balance, priorities, preferences
    ├── financial_events.csv          # Historical, pending, and confirmed transactions
    ├── request_payment_options.csv   # Payment options available per request
    ├── exchange_rates.csv            # Fixed, dated conversion rates
    ├── messages.csv                  # Messages tied to users, requests, or events
    ├── images.csv                    # Payroll letters, statements, bills, receipts
    └── media/
        └── images/
```

Only `dataset/requests.csv` requires predictions. Everything else is context. Join user records with `user_id`, request records with `request_id`, supporting evidence with `related_event_id`, and exchange rates with the rate date and currency pair.

Amounts are in the user's `home_currency` — the dataset uses INR, ZAR, IDR, USD, and EUR, and every conversion rate you need is in `exchange_rates.csv`. All dates are `YYYY-MM-DD`. Live exchange rates, market data, and banking access are not required.

---

## What You Need to Build

For every row in `dataset/requests.csv`, produce one row in `output.csv` with:

| Column | Meaning |
|---|---|
| `request_id` | The request being answered |
| `amount_safe_to_pay` | Largest amount safe to pay on `request_date` before optional spending changes, after protecting essentials and the minimum balance |
| `affordability_status` | `affordable_now`, `affordable_with_plan`, `affordable_later`, or `not_affordable` |
| `recommended_payment_method` | `full_payment`, `partial_payment`, `installments`, `wait`, or `not_recommended` |
| `payment_plan` | Chronological `<YYYY-MM-DD>:<amount>` entries joined by `\|`, or `none` |
| `earliest_date_for_full_payment` | Earliest date the full amount is forecast safe as one payment; empty if never within the forecast |
| `spending_changes_needed` | Up to three `stop:<event_id>` / `reduce_to:<event_id>:<amount>` changes joined by `\|`, or `none` |
| `decision_explanation` | Short explanation and the financial facts behind it |

`0 <= amount_safe_to_pay <= requested_amount` must always hold. Installment plans must exactly match a supplied payment option, and only recurring expenses marked flexible may be changed.

`affordable_with_plan` means the full request is completed through a partial-payment schedule, installments, or permitted spending changes. Recommend `partial_payment` only when the request allows it, the user accepts it, `0 < amount_safe_to_pay < requested_amount`, and `earliest_date_for_full_payment` is on or before `desired_completion_date`. Use exactly two payments: pay `amount_safe_to_pay` on `request_date`, then pay the remaining amount on `earliest_date_for_full_payment`. The two payments must add up to `requested_amount`. Unlike installments, partial payment does not need to match a supplied payment option.

---

## Suggested Workflow

1. Inspect `dataset/sample_requests.csv` — 25 requests with completed output columns — to understand the expected format and decision style.
2. Reconstruct each user's financial state from `financial_profiles.csv` and `financial_events.csv`: separate recurring expenses from one-time events, reserve pending transactions, count confirmed salary only on its settlement date, and de-duplicate repeated representations of the same event.
3. When an event has a blank `amount`, find its `event_id` as `related_event_id` in `images.csv` and extract the amount from the linked image. Never treat a blank amount as zero. Pull in any other relevant messages, images, and payment options for the request.
4. Forecast forward and generate a plan that keeps the balance above the minimum at every step.
5. Verify deterministically — bounds, plan feasibility, schedule match, flexible-only spending changes — before writing `output.csv`.
6. Score yourself on the solved samples, then run the full dataset.

You may use any language or runtime. Python, JavaScript, and TypeScript are all reasonable choices.

---

## Requirements

Your solution must:

- be runnable from the terminal
- read the provided files from `dataset/`
- produce a valid `output.csv` with the exact required columns in the exact required order
- include one prediction for every `request_id` in `dataset/requests.csv`
- not use organizer-only files or hardcoded labels
- keep behavior deterministic where possible

If you use API keys or secrets, read them from environment variables. Never hardcode secrets in the repo.

---

## Evaluation

Your `output.csv` will be compared against hidden ground-truth values.

The scoring will consider:

- accuracy of `amount_safe_to_pay`
- correctness of `affordability_status`
- correctness of `recommended_payment_method` and `payment_plan`
- accuracy of `earliest_date_for_full_payment`
- validity of `spending_changes_needed`
- usefulness and consistency of `decision_explanation`

### Token Usage And Cost Analysis

Your `code.zip` must include one token-usage file:

```text
evaluation/usage_report.md
```

The report must cover model providers and names, model calls, input and output tokens, total and average tokens per request, estimated total and per-request cost. The reported values must correspond to the final full-dataset run that produced your `output.csv`.

---

## Chat Transcript Logging

This repo includes an [`AGENTS.md`](./AGENTS.md) file for AI coding tools. It asks compatible tools to append conversation summaries to a `log.txt` in the repository root — the same directory as `AGENTS.md`:

| Platform | Path |
|---|---|
| macOS / Linux | `<repo root>/log.txt` |
| Windows | `<repo root>\log.txt` |

The path resolves relative to `AGENTS.md`, so it stays correct across clones, renames, and checkouts. `log.txt` is gitignored — upload it as your chat transcript at submission time. Do not paste secrets into the chat.

In case, the harness you are using is not in the repo root, you can explicitly ask the agent to look for the AGENTS.md in this folder & then continue.

---

## Submission

Submit the following files as instructed by HackerRank:

| File | Description |
|---|---|
| `code.zip` | Full runnable solution, prompts/configuration, README, and the required `evaluation/` folder |
| `output.csv` | Predictions for every row in `dataset/requests.csv` |
| `chat_transcript` | The `log.txt` described above, showing how you developed or used the system |

Before submitting, confirm:

- `output.csv` has one row per row in `dataset/requests.csv` (250 rows plus the header).
- `output.csv` has the exact required columns in the exact required order.
- Every `amount_safe_to_pay` satisfies `0 <= amount_safe_to_pay <= requested_amount`.
- Every installment plan matches a supplied payment option, and every spending change targets a flexible recurring expense.
- Your runnable code, setup instructions, and `evaluation/` folder are included in `code.zip`.

---

## Retrieval-Augmented Generation (RAG) Subsystem

### What is RAG and Why is it Used?
Retrieval-Augmented Generation (RAG) couples domain-specific external knowledge retrieval with text generation. In the "Buy or Wait?" system, RAG is integrated strictly as an **explanation enrichment layer** following the deterministic decision:
1. **Explainability:** Transforms raw figures and statuses into grounded justifications citing financial principles (e.g. the 50/30/20 rule, installment obligation risks, or the strategic value of delaying purchases until confirmed income settles).
2. **Strict Financial Safety:** RAG **never** calculates or overrides financial decisions. The 90-day cash forecast, safe amount calculation, and ranking hierarchy execute purely in deterministic Python.

### RAG Architecture

```text
User Request & Profile
       ↓
Deterministic Financial Engine (90-Day Simulation & Constraint Ranking)
       ↓
Financial Decision (Status, Safe Amount, Plan, Earliest Date, Spending Changes)
       ↓
Decision-Aware RAG Retriever (Routes topic filters & queries based on decision)
       ↓
Local Vector Store (16 Curated Documents / 38 Chunks with Cosine Similarity)
       ↓
Context Builder (Immutable Facts + Sanitized Supporting Guidance)
       ↓
Grounded Explanation Generator (RAG Synthesis with Automatic Fallback)
       ↓
Validator (Checks 8-Column Schema & Mathematical Invariants)
       ↓
output.csv
```

### Knowledge Base Structure (`knowledge/`)
- `budgeting/`: 50/30/20 rule, zero-based cash allocation, 90-day cash flow forecasting.
- `affordability/`: Safe-to-pay criteria, strategic delayed purchases (wait strategy), opportunity cost.
- `payment_methods/`: Responsible installment management, benefits of full upfront payment, partial payment terms.
- `emergency_fund/`: Untouchable minimum balance buffer, accounting for unforeseen variable expenses.
- `spending/`: Protected essentials vs. discretionary spending, reducing flexible expenses, subscription audits.
- `financial_terms/`: Affordability status definitions (`affordable_now`, `affordable_with_plan`, `affordable_later`, `not_affordable`) and payment plan notation.

### Vector Store & Indexing
- **Embedding Engine:** Normalized TF-IDF vectorizer with sublinear term-frequency scaling and L2 normalization (`src/rag/embeddings.py`). Runs 100% offline in milliseconds without external API keys or heavy C-dependencies.
- **Vector Store:** In-memory matrix with cosine similarity search and metadata filtering (`src/rag/vector_store.py`).
- **Persistent Index:** Serialized to `knowledge/index.json` on initial build; automatically reloaded on subsequent runs to prevent redundant re-indexing.

### Decision-Aware Retrieval Routing
Retrieval queries and topic categories are dynamically routed based on the computed decision:
- `affordable_now` → Prioritizes `affordability`, `payment_methods`, and `budgeting` (upfront payment benefits and emergency buffer protection).
- `affordable_with_plan` → Prioritizes `payment_methods`, `spending`, and `financial_terms` (installment obligations and flexible spending adjustments).
- `affordable_later` → Prioritizes `affordability`, `emergency_fund`, and `budgeting` (confirmed salary timing and avoiding financing costs).
- `not_affordable` → Prioritizes `affordability`, `emergency_fund`, and `spending` (overdraft prevention and non-negotiable minimum balance floor).

### Prompt Injection & Security Defense
All external data (messages, transaction memos, and retrieved documents) are treated as untrusted:
- `ContextBuilder.sanitize_text()` neutralizes adversarial prompt directives (e.g. *"ignore previous instructions"* or *"override decision"*).
- Financial fields are passed as typed numeric primitives in an immutable payload.
- System prompt enforces reference-only data interpretation.

### Transparent Fallback Behavior
If RAG is disabled (`use_rag=False`), if the knowledge index is missing, or if any component encounters an exception, the pipeline automatically falls back to deterministic rule-based explanation templates. The financial decision fields remain 100.0% identical in both cases.

### Running the Project with RAG
```bash
# Run full pipeline with RAG enabled (Default)
python code/main.py

# Run RAG test suite (12 tests)
pytest -v tests/test_rag.py

# Verify mathematical invariance (RAG vs Non-RAG across 250 requests)
python scripts/verify_rag_equivalence.py
```

---

## What-If Purchase & Payment Simulator

The What-If Purchase & Payment Simulator (`src/scenario_simulator.py`) allows users, advisors, and automated planning systems to test hypothetical purchase amounts and payment structures (Full Payment, Partial Payment, Installments, Wait) without mutating raw dataset files or altering core decision logic.

### Simulator Architecture
```text
User Input:
  - Base Request ID (e.g. 'request_01' or 'request_52')
  - Hypothetical Purchase Amount(s) (e.g. ₹40,000, ₹60,000, ₹80,000)
  - Simulated Payment Method(s) (full_payment, partial_payment, installments, wait, or specific option ID)
                     ↓
         ScenarioSimulator (src/scenario_simulator.py)
                     ↓
  ┌─────────────────────────────────────────────────────────┐
  │ 1. Ephemeral Context Cloning (In-memory, zero mutation) │
  │ 2. Payment Method & Eligibility Verification            │
  │ 3. Existing ForecastEngine (90-day daily cash flow)     │
  │ 4. Existing DecisionEngine (Candidate plan evaluation)  │
  │ 5. Minimum Projected Balance & Cash Floor Tracking      │
  │ 6. Grounded Natural-Language Explanation (via RAG)      │
  └─────────────────────────────────────────────────────────┘
                     ↓
              ScenarioResult
  (purchase_amount, payment_method, affordability_status,
   amount_safe_to_pay, payment_plan, earliest_date_for_full_payment,
   spending_changes_needed, minimum_projected_balance,
   decision_explanation)
                     ↓
        Multi-Scenario Comparison & Ranking
  (Ranks valid options using PRD Section 4.4 hierarchy to identify Best Scenario)
```

### Key Guarantees
1. **Zero Algorithm Duplication:** Directly reuses `ForecastEngine`, `DecisionEngine`, `PaymentPlanEngine`, `CurrencyConverter`, and `ExplanationGenerator`.
2. **Dataset Immutability:** Uses deep-copied in-memory contexts. Never modifies original CSV files.
3. **Deterministic Evaluation:** Simulation and minimum projected balance calculations execute 100% deterministically in Python. RAG provides grounded natural-language explanations.
4. **Section 4.4 Safe-Plan Ranking:** When comparing multiple scenarios, ranks using the exact PRD hierarchy (deadline compliance, minimal spending changes, minimal cost, earlier start date, fewer payments).

### Running Simulator Tests & Demonstrations
```bash
# Run the 11 simulator test cases (covers small/medium/large amounts, methods, invalid inputs, ranking, immutability)
pytest -v tests/test_scenario_simulator.py

# Run interactive 6-scenario demonstration
python scripts/demo_simulator.py request_01
python scripts/demo_simulator.py request_52
```

### Python API Example
```python
from src.scenario_simulator import ScenarioSimulator, ScenarioSpec

# Initialize simulator with existing engines
simulator = ScenarioSimulator(joiner, reconstructor, forecast_engine, decision_engine, plan_engine, explanation_gen)

# 1. Simulate a single scenario
spec = ScenarioSpec(purchase_amount=60000.0, payment_method='full_payment')
result = simulator.simulate_scenario('request_52', spec)
print(f"Status: {result.affordability_status} | Min Balance: {result.minimum_projected_balance}")

# 2. Compare multiple scenarios
specs = [
    ScenarioSpec(purchase_amount=60000.0, payment_method='full_payment', scenario_label='Full Payment'),
    ScenarioSpec(purchase_amount=60000.0, payment_method='installments', scenario_label='Installments'),
    ScenarioSpec(purchase_amount=60000.0, payment_method='wait', scenario_label='Wait')
]
comparison = simulator.simulate_scenarios('request_52', specs)
print(comparison.to_markdown())
print(f"Best Plan: {comparison.best_scenario.scenario_label}")
```


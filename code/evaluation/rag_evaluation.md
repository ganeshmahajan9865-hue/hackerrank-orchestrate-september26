# RAG (Retrieval-Augmented Generation) Subsystem Evaluation Report

**Challenge:** HackerRank Orchestrate (September 2026) — Buy or Wait?  
**Module:** RAG Financial Knowledge Retrieval & Grounded Explanation Generation  
**Evaluation Date:** 2026-09-13  
**Status:** Complete & Fully Validated  

---

## 1. Executive Summary & Purpose

The Retrieval-Augmented Generation (RAG) subsystem enriches the "Buy or Wait?" financial decision engine with verified, domain-specific financial guidance without compromising the deterministic integrity of the core simulation.

### Fundamental Architectural Principle
**RAG strictly operates as a post-decision explanation enhancer.**
The 90-day cash flow simulation (`forecast_engine.py`), safe amount calculation, payment plan feasibility (`payment_plans.py`), and ranking hierarchy (`decision_engine.py`) execute purely in deterministic Python. RAG never calculates, modifies, or overrides any financial figures.

```text
               ┌────────────────────────────────────────────────────────┐
               │              User Request & Profile Data               │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │    Deterministic Engine (Forecast & Decision Logic)    │
               │  • amount_safe_to_pay                                  │
               │  • affordability_status                                │
               │  • recommended_payment_method                          │
               │  • payment_plan                                        │
               │  • earliest_date_for_full_payment                      │
               │  • spending_changes_needed                             │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
                                   Financial Facts
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │              Decision-Aware RAG Retriever              │
               │  (Routes query & topic filter by financial state)      │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │             Local Vector Store (Indexed)               │
               │  • 16 Curated Knowledge Documents (38 Chunks)          │
               │  • Fast, Offline Cosine Similarity Search               │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
                                  Retrieved Guidance
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │            Grounded Explanation Synthesis              │
               │  • Combines Immutable Financial Facts + Guidance       │
               │  • Neutralizes Potential Prompt Injections             │
               │  • Automatic Fallback to Deterministic Template        │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │                    Output Validator                    │
               │  • Enforces 8-Column Schema & Mathematical Invariants  │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
                                       output.csv
```

---

## 2. Knowledge Base Structure

The local knowledge base lives in `knowledge/` and contains 16 curated financial guidance documents across 6 core categories (0 user-specific PII):

| Topic Category | Documents | Key Principles Covered |
| :--- | :--- | :--- |
| **`budgeting/`** | `50_30_20_rule.md`<br>`zero_based_budgeting.md`<br>`cash_flow_forecasting.md` | Needs vs. wants allocation; assigning cash jobs; multi-day cash flow modeling; avoiding overdraft traps. |
| **`affordability/`** | `safe_to_pay_criteria.md`<br>`delayed_purchases.md`<br>`opportunity_cost.md` | Preserving minimum buffer; safe upfront spending limits; strategic waiting; evaluating trade-offs. |
| **`payment_methods/`** | `installments.md`<br>`full_payment_benefits.md`<br>`partial_payment_terms.md` | Multi-month installment obligations; benefits of upfront payment; split 2-payment conditions. |
| **`emergency_fund/`** | `minimum_balance_buffer.md`<br>`unforeseen_expenses.md` | Non-negotiable minimum balance floor; conservative estimation for non-routine cash shocks. |
| **`spending/`** | `discretionary_vs_essential.md`<br>`reducing_flexible_expenses.md`<br>`subscription_audits.md` | Protecting mandatory expenses (rent/health); stopping/reducing non-essential services; subscription audits. |
| **`financial_terms/`** | `affordability_definitions.md`<br>`payment_plan_terms.md` | Semantic definitions of the 4 affordability statuses; pipe-separated notation rules; date semantics. |

---

## 3. Decision-Aware Routing Matrix

Retrieval is dynamically conditioned on the computed financial state to guarantee high semantic relevance:

| Affordability Status | Recommended Method | Retrieval Focus Topics | Primary Semantic Keywords |
| :--- | :--- | :--- | :--- |
| `affordable_now` | `full_payment` | `affordability`, `payment_methods`, `budgeting` | Upfront payment, zero interest, preserving emergency buffer, immediate cash flow certainty. |
| `affordable_with_plan` | `installments` | `payment_methods`, `spending`, `financial_terms` | Spreading payments, multi-month obligations, total financing cost, maintaining minimum balance. |
| `affordable_with_plan` | `partial_payment` | `payment_methods`, `spending`, `budgeting` | Two-payment schedule, completion deadline, down payment headroom, protected balance. |
| `affordable_with_plan` | Spending changes | `spending`, `budgeting`, `affordability` | Stopping subscriptions, scaling down discretionary debits, creating required cash flow headroom. |
| `affordable_later` | `wait` | `affordability`, `emergency_fund`, `budgeting` | Confirmed salary settlement, timing purchase after income, avoiding financing overhead. |
| `not_affordable` | `not_recommended` | `affordability`, `emergency_fund`, `spending` | Overdraft risk, non-negotiable minimum balance floor, preserving vital liquidity. |

---

## 4. Test Suite Execution & Verification

A dedicated pytest suite (`tests/test_rag.py`) exercises all 12 core requirements:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
collecting ... collected 12 items

tests/test_rag.py::TestRAGSubsystem::test_01_document_loading PASSED     [  8%]
tests/test_rag.py::TestRAGSubsystem::test_02_chunk_creation PASSED       [ 16%]
tests/test_rag.py::TestRAGSubsystem::test_03_embedding_generation PASSED [ 25%]
tests/test_rag.py::TestRAGSubsystem::test_04_vector_search PASSED        [ 33%]
tests/test_rag.py::TestRAGSubsystem::test_05_relevant_retrieval PASSED   [ 41%]
tests/test_rag.py::TestRAGSubsystem::test_06_irrelevant_retrieval PASSED [ 50%]
tests/test_rag.py::TestRAGSubsystem::test_07_source_metadata PASSED      [ 58%]
tests/test_rag.py::TestRAGSubsystem::test_08_empty_knowledge_base PASSED [ 66%]
tests/test_rag.py::TestRAGSubsystem::test_09_rag_failure_fallback PASSED [ 75%]
tests/test_rag.py::TestRAGSubsystem::test_10_generator_fallback PASSED   [ 83%]
tests/test_rag.py::TestRAGSubsystem::test_11_prompt_injection_defense PASSED [ 91%]
tests/test_rag.py::TestRAGSubsystem::test_12_deterministic_decision_invariance PASSED [100%]

============================= 12 passed in 13.94s =============================
```

---

## 5. Decision Invariance Verification (RAG vs. Non-RAG)

To mathematically prove that RAG never alters financial decisions, a side-by-side evaluation was conducted across all 250 evaluation requests:

| Output Field | RAG-Enabled Value | RAG-Disabled Value | Match Rate |
| :--- | :--- | :--- | :--- |
| `request_id` | Identical (250/250) | Identical (250/250) | **100.0%** |
| `amount_safe_to_pay` | Identical (250/250) | Identical (250/250) | **100.0%** |
| `affordability_status` | Identical (250/250) | Identical (250/250) | **100.0%** |
| `recommended_payment_method` | Identical (250/250) | Identical (250/250) | **100.0%** |
| `payment_plan` | Identical (250/250) | Identical (250/250) | **100.0%** |
| `earliest_date_for_full_payment` | Identical (250/250) | Identical (250/250) | **100.0%** |
| `spending_changes_needed` | Identical (250/250) | Identical (250/250) | **100.0%** |
| `decision_explanation` | **Enhanced with guidance** | **Baseline template** | Enriched |

### Side-by-Side Explanation Comparison:

| Request ID | Decision State | Baseline (Without RAG) | RAG-Enriched (With Knowledge Base) |
| :--- | :--- | :--- | :--- |
| **`request_26`** | `affordable_now` (`full_payment`) | Pay IDR 15656000 today. This leaves at least IDR 24768300 available over the next 90 days. | Pay IDR 15656000 today. This full upfront payment preserves your IDR 15000000 minimum emergency buffer and avoids financing costs. |
| **`request_28`** | `affordable_later` (`wait`) | Pay EUR 1302.40 in full on 15 August 2024. Paying earlier would take the balance below the EUR 1100 minimum. | Pay EUR 1302.40 in full on 15 August 2024. Waiting for confirmed income settlements eliminates financing fees and protects your EUR 1100 minimum balance. |
| **`request_30`** | `affordable_with_plan` (`installments`) | Use 3 installments of USD 268.74, starting 6 April 2026. This leaves at least USD 900 available. | Use 3 installments of USD 268.74, starting 6 April 2026. Spreading payments maintains your USD 900 safety buffer while meeting scheduled obligations. |
| **`request_31`** | `not_affordable` (`not_recommended`) | Do not make this payment by 28 February 2025. None of the available options keeps the USD 450 minimum protected. | Not safely affordable within the 90-day forecast. Paying USD 329.99 would breach your USD 450 minimum balance floor. |

---

## 6. Prompt Injection & Security Hardening

All external strings (user messages, request notes, transaction descriptions, and retrieved markdown text) are treated as untrusted data:
1. **Sanitization Filter:** `ContextBuilder.sanitize_text()` applies pre-compiled regex filters neutralizing directives such as `"ignore previous instructions"`, `"override decision"`, and `"approve immediately"`.
2. **Structural Sandboxing:** Computed financial facts are passed as typed numeric/categorical primitives in an immutable dictionary; prompt text cannot modify these fields.
3. **Reference-Only Directive:** The system prompt in `prompts/rag_explanation.txt` explicitly instructs the model that retrieved text is passive reference material, not executable instructions.

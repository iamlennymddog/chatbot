## `bitstalk-deal-buddy`  ·  Generic (classification signal)  ·  now-7d
**Date**: 2026-11-17  |  **Profile**: multi-agent RAG chat (orchestrator + sub-agent, BM25 retrieval, cost tool)  |  **Model**: `claude-sonnet-5-5`, `claude-haiku-5-5`

Customer-facing BitsTalk South Africa deals assistant that delegates catalogue research to a Deals Specialist sub-agent.

| Metric | Value |
|--------|-------|
| Sessions classified | 15 (dd-verify-001 excluded by user) |
| Failures (partial) | 2 |
| Error spans | 0 in the sample (`s1` error session was pre-instrumentation test traffic) |
| Evals configured | 0 (no ongoing quality signal) |

### Findings

- **Promo pricing hedged to the customer** (~50% of failures): the catalogue states the porting promo, but the specialist flagged its derived price as "not verified against a tool result" because `calculate_contract_cost` cannot model promo months; the orchestrator then told the customer the promo only "may" exist.
- **Catalogue has no contract/cancellation terms** (~50% of failures): the agent correctly refused to invent terms and referred the customer to 135; the gap is in the data, not the agent.

### Recommendations

- **Add a promo-aware cost calculation** (`promo_months` + `promo_monthly_price` on `calculate_contract_cost`) and tell the orchestrator to state catalogue promos as facts.
- **Add a general contract-terms section** (early termination, cooling-off, upgrade rules) to `data/bitstalk_deals.txt`.

*Sample: 15 sessions, 2 failures analyzed. Confidence: Low — fewer than 5 failing units; patterns need more traffic to confirm.*

## Classification Signal Summary

**Source**: agent-observability-session-classify  |  **ml_app**: bitstalk-deal-buddy  |  **Signal**: content-only

| Metric | Value |
|--------|-------|
| Traces classified | 15 |
| Failures in corpus (no+partial) | 2 |
| Pass rate | 87% |
| Failure modes | inconsistent_promo_grounding, catalogue_knowledge_gap |

*Root cause analysis is based on per-trace classification verdicts, not automated eval judge reasoning.*

**Open coding**: 2 problematic rows → 2 initial categories: Promo pricing downgraded to uncertainty (1), Unanswerable policy question (1).
**Axial coding**: no merges (each < 3 but distinct and actionable; kept, flagged low-confidence). Final categories:
1. Promo pricing downgraded to uncertainty (1, 50%) — medium
2. Catalogue knowledge gap: contract terms (1, 50%) — low

## Failure Taxonomy

| # | Failure Mode | Traces | % | Severity | Root Cause |
|---|-------------|-------:|:-:|:--------:|-----------|
| 1 | Promo pricing downgraded to uncertainty | 1 | 50% | **Medium** | Tool Gap + System Prompt Deficiency |
| 2 | Catalogue knowledge gap (contract terms) | 1 | 50% | **Low** | Retrieval Failure (missing data) |

## Failure Mode 1: Promo pricing downgraded to uncertainty

**Count**: 1 trace  |  **Severity**: Medium  |  **Root Cause**: Tool Gap + System Prompt Deficiency

`search_deals` returned BT-SIMO-001, whose catalogue text states "First 3 months at HALF PRICE on 30GB and 75GB plans when you port your number". The Deals Specialist reported the promo but computed R199.50 itself and labelled it "not verified against a tool result", because `calculate_contract_cost` only takes `monthly_price`, `months`, `upfront` and `trade_in_credit`. The orchestrator, told to "Never invent prices", turned that caveat into "There may be a promo ... I couldn't confirm that price". In another session (dd-verify-001) the same promo was stated as fact, so customers get inconsistent answers.

**Evidence**

| Trace | Anomaly | Signal |
|---|---|---|
| [6afc628a...f309548c](https://app.datadoghq.com/llm/traces?query=trace_id:6afc628a0000000006239baaf309548c) | specialist: "about R199.50 each, which I have not verified against a tool result" → reply: "There may be a promo" | classification: partial |

**Root cause**: `calculate_contract_cost` (backend/src/tools/dealTools.js) cannot express promo months, so promo totals are always "unverified"; the orchestrator prompt has no rule distinguishing catalogue facts from derived arithmetic.

**Fix**:
  BEFORE (tool): `monthly_price x months + upfront - trade_in_credit`
  AFTER  (tool): add optional `promo_months`, `promo_monthly_price`: `promo_monthly_price x promo_months + monthly_price x (months - promo_months) + upfront - trade_in_credit`
  BEFORE (orchestrator prompt): "- Base your answer only on what the tools return. Never invent prices or deals."
  AFTER:  "- Base your answer only on what the tools return. Never invent prices or deals. Promotions that appear in the catalogue text are facts: state them plainly with their conditions."

**Impact**: Removes the hedge on every promo-priced answer (SIM-only, prepaid app bonus, summer specials).

## Failure Mode 2: Catalogue knowledge gap (contract terms)

**Count**: 1 trace  |  **Severity**: Low  |  **Root Cause**: Retrieval Failure (data not in index)

The customer asked for the cancellation policy of BT-FLAG-001. The specialist ran three `search_deals` queries ("cancellation early termination settlement fee cooling-off period contract", …); none returned contract terms because `data/bitstalk_deals.txt` has none (only "cancel any time with 30 days notice" for SIM-only). The agent behaved correctly: it declined to guess and referred the customer to 135.

**Evidence**

| Trace | Anomaly | Signal |
|---|---|---|
| [6afc0fdc...5f2dd822](https://app.datadoghq.com/llm/traces?query=trace_id:6afc0fdc0000000013952c175f2dd822) | 3 retrievals, none relevant; brief: "The catalogue does not contain a cancellation policy" | classification: partial |

**Root cause**: missing source data, not agent behaviour.

**Fix**: add a `GEN-` section with contract terms (early termination fee rules, cooling-off, upgrade eligibility, what happens to bundled gifts) to `data/bitstalk_deals.txt`.

**Impact**: Makes policy questions answerable; keep the honest-refusal behaviour as a guarded property (evaluator).

## Prioritized Action Plan

| Priority | Action | Confidence | Impact |
|:---:|---|:---:|---|
| 1 | Add promo months to `calculate_contract_cost` and a "catalogue promos are facts" prompt rule | Medium | Consistent promo answers |
| 2 | Add contract-terms section to the catalogue | Medium | Policy questions answerable |
| 3 | Configure at least one evaluator | High | Enables Eval Signal mode for future RCAs — app currently has no ongoing quality signal |

## Limitations & Follow-ups

- Only 2 failing sessions; both patterns need more production traffic to confirm frequency.
- Most sessions are single-turn seed traffic; multi-turn behaviour (context carry-over) is under-sampled.
- Latency (14–29 s per turn, up to 14 tool calls) was not classified as a failure but is worth a latency monitor.

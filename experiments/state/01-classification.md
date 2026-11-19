session: seed-01  verdict: yes  reason: Greeting handled directly without tools, invites budget/brand.  content: io
session: seed-02  verdict: yes  reason: Closest 2GB prepaid options with prices and out-of-bundle warning.  content: io
session: seed-03  verdict: yes  reason: Only iPhone under R800 identified with full cost, next option flagged as over budget.  content: io
session: seed-04  verdict: yes  reason: Coverage confirmed for Soweto and 5G home internet tiers quoted with totals.  content: io
session: seed-05  verdict: yes  reason: UK roaming options compared for a two-week trip with costs.  content: io
session: seed-06  verdict: yes  reason: S26 Ultra vs iPhone 17 Pro 36-month totals compared side by side.  content: io
session: seed-07  verdict: yes  reason: Fibre availability confirmed, follow-up question asked.  content: io
session: seed-08  verdict: yes  reason: Correctly explains free phone and no credit check are mutually exclusive, with alternatives.  content: io
session: seed-09  verdict: partial  reason: Correct cheapest 50GB+ SIM-only plan, but the porting promo is presented as unconfirmed here while another session states it as fact.  content: io
session: seed-10  verdict: yes  reason: Business fleet deal for 8 lines with per-line and total cost.  content: io
session: seed-11  verdict: yes  reason: States no Huawei in catalogue and offers close alternatives.  content: io
session: seed-12  verdict: yes  reason: Youth prepaid deal and eligibility explained.  content: io
session: dd-verify-001  verdict: partial  reason: Turn 2 follow-up ("compare that") lost the prior deal because the request carried no history, so the agent could not resolve the reference.  content: io
session: 19927f27  verdict: yes  reason: Flagship comparison for Sandton with coverage check.  content: io
session: ea1e1082  verdict: yes  reason: Both turns give grounded iPhone vs Samsung guidance with deal IDs.  content: io
session: 38a6504b  verdict: partial  reason: Four turns satisfied, but the cancellation-policy question could not be answered because the catalogue has no such data.  content: io

# Session Classification Summary

**App:** `bitstalk-deal-buddy`  |  **Timeframe:** now-7d → now  |  **Granularity:** session  |  **Sampled:** 16
**Root span kind:** agent  |  **Content source:** io

Excluded as outliers (sanity check): sessions 70a61afd, b366043d, 72c9d2a3 (empty root I/O, emitted by an earlier instrumentation build) and session `s1` (status:error, 0.3-0.6s, filtered by `@status:ok`).

## Verdict Distribution

| Verdict | Count | % |
|---------|------:|:-:|
| yes     | 13    | 81% |
| partial | 3     | 19% |
| no      | 0     | 0% |

## Failure Mode Frequency

| Failure Mode | Count | % of failures |
|-------------|------:|:-------------:|
| catalogue_knowledge_gap | 1 | 33% |
| inconsistent_promo_grounding | 1 | 33% |
| lost_conversation_context | 1 | 33% |

## Per-Unit Details

| Trace/Session ID | Type | Verdict | Failure Mode | Reason | Content source |
|-----------------|------|---------|-------------|--------|----------------|
| [seed-01](https://app.datadoghq.com/llm/traces?query=session_id:seed-01) | session | yes | none | none | io |
| [seed-02](https://app.datadoghq.com/llm/traces?query=session_id:seed-02) | session | yes | none | none | io |
| [seed-03](https://app.datadoghq.com/llm/traces?query=session_id:seed-03) | session | yes | none | none | io |
| [seed-04](https://app.datadoghq.com/llm/traces?query=session_id:seed-04) | session | yes | none | none | io |
| [seed-05](https://app.datadoghq.com/llm/traces?query=session_id:seed-05) | session | yes | none | none | io |
| [seed-06](https://app.datadoghq.com/llm/traces?query=session_id:seed-06) | session | yes | none | none | io |
| [seed-07](https://app.datadoghq.com/llm/traces?query=session_id:seed-07) | session | yes | none | none | io |
| [seed-08](https://app.datadoghq.com/llm/traces?query=session_id:seed-08) | session | yes | none | none | io |
| [seed-09](https://app.datadoghq.com/llm/traces?query=session_id:seed-09) | session | partial | inconsistent_promo_grounding | Porting promo hedged here but stated as fact in another session. | io |
| [seed-10](https://app.datadoghq.com/llm/traces?query=session_id:seed-10) | session | yes | none | none | io |
| [seed-11](https://app.datadoghq.com/llm/traces?query=session_id:seed-11) | session | yes | none | none | io |
| [seed-12](https://app.datadoghq.com/llm/traces?query=session_id:seed-12) | session | yes | none | none | io |
| [dd-verify-001](https://app.datadoghq.com/llm/traces?query=session_id:dd-verify-001) | session | partial | lost_conversation_context | Follow-up reference unresolved; request had no prior turns. | io |
| [19927f27...f17d5d42](https://app.datadoghq.com/llm/traces?query=session_id:19927f27-1b81-4a4e-9601-f8b3f17d5d42) | session | yes | none | none | io |
| [ea1e1082...9adb46ed](https://app.datadoghq.com/llm/traces?query=session_id:ea1e1082-e0a4-4b73-a38a-4c829adb46ed) | session | yes | none | none | io |
| [38a6504b...2c80aa45](https://app.datadoghq.com/llm/traces?query=session_id:38a6504b-aa44-4f67-8b6e-91052c80aa45) | session | partial | catalogue_knowledge_gap | Cancellation policy not in catalogue. | io |

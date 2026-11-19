import json, os, sys, urllib.request, urllib.error

APP = "bitstalk-deal-buddy"
# Spans arrive via OpenTelemetry GenAI (see backend/src/otel.js). The root agent input holds the
# system instructions plus the conversation; the last user message is the current request.
ROOT_FILTER = "@meta.span.kind:agent @name:deal-buddy"
Q = "{{spans[name:deal-buddy].meta.input.value}}"
A = "{{spans[name:deal-buddy].meta.output.value}}"
DOCS = "{{spans[name:search_deals].meta.output.value}}"  # search_deals is an OTel execute_tool span; output = matching catalogue sections
TOOLS = "{{spans[meta.span.kind:tool]}}"
BRIEF = "{{spans[name:deals-specialist].meta.output.value}}"
CTX = "BitsTalk Deal Buddy is a customer-facing assistant for BitsTalk South Africa. It delegates catalogue research to a Deals Specialist sub-agent that uses search_deals (retrieval over the BitsTalk deals catalogue) and calculate_contract_cost; check_network_coverage checks coverage by location."

def boolean(desc):
    return ({"name": "boolean_eval", "strict": True, "schema": {"type": "object", "properties": {
        "boolean_eval": {"type": "boolean", "description": desc},
        "reasoning": {"type": "string", "description": "Explanation for the evaluation"}},
        "required": ["boolean_eval", "reasoning"], "additionalProperties": False}}, {"pass_when": True})

def categorical(cats, passing):
    return ({"name": "categorical_eval", "strict": True, "schema": {"type": "object", "properties": {
        "categorical_eval": {"type": "string", "anyOf": [{"const": k, "description": v} for k, v in cats.items()]},
        "reasoning": {"type": "string", "description": "Explanation for the category chosen"}},
        "required": ["categorical_eval", "reasoning"], "additionalProperties": False}}, {"pass_values": passing})

def score(desc, lo, hi, thr):
    return ({"name": "score_eval", "strict": True, "schema": {"type": "object", "properties": {
        "score_eval": {"type": "number", "description": desc, "minimum": lo, "maximum": hi},
        "reasoning": {"type": "string", "description": "Explanation for the score"}},
        "required": ["score_eval", "reasoning"], "additionalProperties": False}}, {"min_threshold": thr})

EVALS = [
 ("catalogue_promo_stated_as_fact", "trace", ROOT_FILTER,
  f"{CTX}\nYou judge how the final reply handles promotions. A promotion is any special offer in the retrieved catalogue text (e.g. half price for the first months, bonus data, summer specials) that is relevant to what the customer asked. Catalogue text is authoritative: a relevant promo should be stated plainly with its conditions. Choose 'stated' if every relevant promo is stated as fact; 'hedged' if a relevant promo is mentioned but presented as uncertain, unconfirmed or 'may apply'; 'omitted' if a clearly relevant promo is missing; 'not_applicable' if no relevant promo appears in the retrieved text.",
  f"Conversation (the last user message is the customer's current request):\n{Q}\n\nRetrieved catalogue text:\n{DOCS}\n\nFinal reply:\n{A}",
  categorical({"stated": "Relevant promos stated plainly with conditions", "hedged": "A relevant promo is presented as uncertain or unconfirmed",
               "omitted": "A clearly relevant promo is missing from the reply", "not_applicable": "No relevant promo in the retrieved text"}, ["stated", "not_applicable"])),
 ("honest_refusal_on_missing_data", "trace", ROOT_FILTER,
  f"{CTX}\nYou judge behaviour when the retrieved catalogue text does NOT contain the information the customer asked for (e.g. cancellation terms, unlisted brands, unlisted areas). The correct behaviour is to say clearly that the information is not available and point the customer to BitsTalk (call 135, a store or bitstalk.co.za), optionally offering close alternatives that ARE in the catalogue. Choose 'honest_refusal' if the reply does that; 'fabricated' if it states facts, prices, fees or terms that are not in the retrieved text or tool outputs; 'not_applicable' if the retrieved text contains what was asked.",
  f"Conversation (the last user message is the customer's current request):\n{Q}\n\nRetrieved catalogue text:\n{DOCS}\n\nTool calls and results:\n{TOOLS}\n\nFinal reply:\n{A}",
  categorical({"honest_refusal": "Says the information is unavailable and refers the customer on, without inventing facts",
               "fabricated": "States facts, prices or terms not present in retrieved text or tool outputs",
               "not_applicable": "The requested information is present in the retrieved text"}, ["honest_refusal", "not_applicable"])),
 ("price_and_deal_id_grounding", "trace", ROOT_FILTER,
  f"{CTX}\nCheck grounding. Every Rand amount and every deal ID (format like BT-MID-001, GEN-20) in the final reply must appear in the retrieved catalogue text or in a calculate_contract_cost result, or be simple, clearly labelled arithmetic on those numbers. Return true if all prices and deal IDs are grounded, false if any price or ID is invented or contradicts the sources. Replies with no prices or IDs are true.",
  f"Retrieved catalogue text:\n{DOCS}\n\nTool calls and results:\n{TOOLS}\n\nFinal reply:\n{A}",
  boolean("Whether every price and deal ID in the reply is grounded in the sources")),
 ("contract_total_correctness", "trace", ROOT_FILTER,
  f"{CTX}\nCheck arithmetic. For every total contract cost quoted in the final reply, verify total = monthly price x months + upfront - trade-in credit (and, for promos, the discounted months at the promo price). Return true if every quoted total is correct within R1, false if any total is wrong. Replies without totals are true.",
  f"Tool calls and results:\n{TOOLS}\n\nFinal reply:\n{A}",
  boolean("Whether every quoted contract total is arithmetically correct")),
 ("tool_use_correctness", "trace", ROOT_FILTER,
  f"{CTX}\nJudge tool use across the whole trace. Correct use means: (1) consult_deals_specialist is called for any deal, price, device or plan question, with a self-contained task that carries the customer's stated needs (budget, data use, brand, term, location); (2) check_network_coverage is called when the customer gives a location or asks about home internet/5G/fibre; (3) calculate_contract_cost is used when totals are compared; (4) greetings and small talk use no tools. Choose 'correct', 'partially_correct' (minor omissions, e.g. a need missing from the task) or 'incorrect' (wrong or missing tool calls that affect the answer).",
  f"Conversation (the last user message is the customer's current request):\n{Q}\n\nTool calls and results:\n{TOOLS}\n\nFinal reply:\n{A}",
  categorical({"correct": "Right tools with the right arguments", "partially_correct": "Minor omissions in tool use or task content",
               "incorrect": "Wrong or missing tool calls that affect the answer"}, ["correct"])),
 ("goal_completion", "trace", ROOT_FILTER,
  f"{CTX}\nJudge whether this turn fully answered the customer's request. Choose 'complete' if the reply answers what was asked with concrete deal IDs/prices where relevant (or correctly explains what is not available); 'partial' if it answers only part or needs the customer to ask again; 'incomplete' if it fails to address the request.",
  f"Conversation (the last user message is the customer's current request):\n{Q}\n\nAgent steps:\n{TOOLS}\n\nFinal reply:\n{A}",
  categorical({"complete": "Request fully answered", "partial": "Only part of the request answered", "incomplete": "Request not addressed"}, ["complete"])),
 ("session_goal_completion", "session", "@meta.span.kind:agent @name:deal-buddy",
  f"{CTX}\nYou see a whole customer chat session (one trace per customer turn). Judge whether the customer's goals were met across the session. Choose 'completed' if the customer got usable deal recommendations or a clear answer to each question; 'partially_completed' if some goals were left unmet; 'not_completed' if the session ended without the customer's main goal being met.",
  "Per-turn conversation input (the last user message in each is that turn's request):\n{{traces[*].spans[name:deal-buddy].meta.input.value}}\n\nAssistant replies:\n{{traces[*].spans[name:deal-buddy].meta.output.value}}",
  categorical({"completed": "Customer goals met", "partially_completed": "Some goals unmet", "not_completed": "Main goal not met"}, ["completed"])),
 ("multi_turn_context_retention", "session", "@meta.span.kind:agent @name:deal-buddy",
  f"{CTX}\nYou see a whole customer chat session (one trace per turn). Check whether follow-up turns that refer to earlier context (e.g. 'that deal', 'compare it with', 'what about cancellation') are resolved correctly from earlier turns, without asking the customer to repeat themselves or losing the referenced deal. Return true if context is retained or the session has no such follow-ups, false if any follow-up loses context.",
  "Per-turn conversation input (the last user message in each is that turn's request):\n{{traces[*].spans[name:deal-buddy].meta.input.value}}\n\nAssistant replies:\n{{traces[*].spans[name:deal-buddy].meta.output.value}}",
  boolean("Whether follow-up references are resolved from earlier turns")),
 ("brand_voice_and_format", "span", "@meta.span.kind:agent @name:deal-buddy",
  f"{CTX}\nScore the reply's voice and format from 1 to 10. A 10 is: concise short bullet points; prices in Rand with term (e.g. R399 per month x 36 months); deal IDs mentioned; friendly, upbeat South African tone (a little warmth like 'Howzit' or 'lekker' is welcome, not overdone); one short follow-up question when the customer's needs are unclear. Deduct for walls of text, missing deal IDs on recommended deals, prices without Rand or term, or a cold/robotic tone.",
  "Conversation (the last user message is the customer's current request):\n{{meta.input.value}}\n\nReply:\n{{meta.output.value}}",
  score("Voice and format quality from 1 to 10", 1, 10, 7)),
 ("scope_adherence", "span", "@meta.span.kind:agent @name:deal-buddy",
  f"{CTX}\nReturn true if the reply stays within scope: BitsTalk South Africa products, deals, coverage and how to buy them. Return false if it recommends competitor networks, gives financial, legal or medical advice beyond stating BitsTalk terms, discusses unrelated topics at length, or asks for unnecessary personal data (ID numbers, bank details) in chat. Stating documents needed for credit vetting is in scope.",
  "Conversation (the last user message is the customer's current request):\n{{meta.input.value}}\n\nReply:\n{{meta.output.value}}",
  boolean("Whether the reply stays within BitsTalk customer-service scope")),
]

def payload(name, scope, flt, system, user, schema_crit):
    schema, crit = schema_crit
    return {"data": {"type": "evaluator_config", "id": name, "attributes": {
        "eval_name": name, "category": "Custom",
        "llm_provider": {"integration_provider": "anthropic", "model_name": "claude-haiku-5-5"},
        "llm_judge_config": {"inference_params": {"temperature": 0, "max_tokens": 1024},
            "parsing_type": "structured_output", "output_schema": schema, "assessment_criteria": crit,
            "prompt_template": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        "target": {"application_name": APP, "enabled": False, "eval_scope": scope, "filter": flt,
                   "root_spans_only": scope == "span", "sampling_percentage": 100}}}}

def call(method, name, body=None):
    req = urllib.request.Request(f"https://api.datadoghq.com/api/unstable/llm-obs/config/evaluators/custom/{name}",
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"DD-API-KEY": os.environ["DD_API_KEY"], "DD-APPLICATION-KEY": os.environ["DD_APP_KEY"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]

only = sys.argv[1:] 
for e in EVALS:
    if only and e[0] not in only: continue
    st, _ = call("GET", e[0])
    if st == 200:
        print(f"{e[0]}: EXISTS - skipped"); continue
    st, body = call("PUT", e[0], payload(*e))
    print(f"{e[0]}: HTTP {st} {body if st >= 300 else ''}")

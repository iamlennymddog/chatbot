# BitsTalk Deal Buddy – RAG chatbot

## Layout
- `backend/` – Node.js + Express API, multi-agent design using the OpenAI Node.js SDK (Chat Completions + tool calling) against Anthropic's OpenAI-compatible endpoint (`https://api.anthropic.com/v1/`), so Claude remains the model provider. Logs are JSON (pino) and go to stdout and `backend/logs/app.log`.
- `frontend/` – Vue 3 (Composition API, `<script setup>`) + Vite. `/api` is proxied to `localhost:3001`.

## Run
```bash
export ANTHROPIC_API_KEY=sk-ant-...
./start.sh           # backend :3001 + frontend http://localhost:5173
./stop.sh            # stop backend and frontend (or Ctrl+C in the start.sh terminal)
```
Optional overrides: `ANTHROPIC_MODEL`, `SPECIALIST_MODEL`.

## Agent design
```
POST /api/chat
 └─ agent: deal-buddy (orchestrator, ANTHROPIC_MODEL)
     ├─ tool: check_network_coverage        (mock coverage API)
     └─ tool: consult_deals_specialist
         └─ agent: deals-specialist (sub-agent, SPECIALIST_MODEL)
             ├─ retrieval: search_deals      (BM25 over data/bitstalk_deals.txt)
             └─ tool: calculate_contract_cost
```
- `src/agents/runAgent.js` – generic tool-use loop shared by both agents
- `src/agents/orchestrator.js`, `src/agents/dealsSpecialist.js` – prompts + tool sets
- `src/tools/` – tool implementations

The chat response includes `steps` (every tool call per agent), which the UI shows under "Agent activity".

## API
- `GET  /api/health`
- `GET  /api/deals` – list of deal IDs/titles
- `POST /api/chat` – `{ sessionId, messages: [{role, content}] }` → `{ reply, sources, steps, usage }`

## Datadog instrumentation
`./start.sh` reads `DD_API_KEY` with `getSecretKey BITSTALK_DD_API_KEY`, starts a dedicated Agent container (`datadog/agent.sh`, key in the 0600 file `.dd/datadog.env`) and runs the backend with `node --import dd-trace/initialize.mjs`.

| Signal | How |
|---|---|
| APM | service `bitstalk-deals-chatbot-api`, env `pov`. Express, HTTP and the OpenAI SDK are auto-instrumented. |
| LLM Observability | ml_app `bitstalk-deal-buddy`, sent through the Agent. OpenAI SDK calls produce `llm` spans; `src/tracing.js` adds `agent` / `tool` / `retrieval` spans and an agent manifest (instructions, model, tools) on each agent span for the **Execution Graph**. The chat `sessionId` is set on the root `deal-buddy` span only and is inherited by all children. |
| Logs | pino JSON -> `backend/logs/app.log`, tailed by the Agent (`datadog/conf.d/bitstalk-chatbot.d`). `DD_LOGS_INJECTION=true` adds `dd.trace_id`/`dd.span_id`. |
| Runtime metrics | `DD_RUNTIME_METRICS_ENABLED=true` via DogStatsD :8125 |

Execution graph per chat turn:
```
agent: deal-buddy                       (session_id = chat sessionId)
├─ llm: OpenAI.createChatCompletion (claude-sonnet-5-5)
├─ tool: check_network_coverage
└─ tool: consult_deals_specialist
   └─ agent: deals-specialist
      ├─ llm: OpenAI.createChatCompletion (claude-haiku-5-5)
      ├─ retrieval: search_deals
      └─ tool: calculate_contract_cost
```
Stop the Agent with `datadog/agent.sh down`.

## Log format
Each line is JSON with `level` (string), `time` (ISO), `service`, `env`, `version`, `req.id`, `session_id`, plus `agent`, `event` (`agent.start`, `agent.llm_call`, `tool.call`, `rag.retrieve`, `agent.end`, `chat.completed`, `llm.error`) and timing/token fields.

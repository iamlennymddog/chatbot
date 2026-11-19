# BitsTalk Deal Buddy – RAG chatbot

## Layout
- `backend/` – Node.js + Express API, multi-agent design using the OpenAI Node.js SDK (Chat Completions + tool calling) against Anthropic's OpenAI-compatible endpoint (`https://api.anthropic.com/v1/`), so Claude remains the model provider. Logs are JSON (pino) and go to stdout and `backend/logs/app.log`.
- `frontend/` – Vue 3 (Composition API, `<script setup>`) + Vite. `/api` is proxied to `localhost:3001`.

## Run
```bash
export ANTHROPIC_API_KEY=sk-ant-...
./start.sh           # backend :3001 + frontend http://localhost:5173
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

## Log format
Each line is JSON with `level` (string), `time` (ISO), `service`, `req.id`, `session_id`, plus `agent`, `event` (`agent.start`, `agent.llm_call`, `tool.call`, `rag.retrieve`, `agent.end`, `chat.completed`, `llm.error`) and timing/token fields.

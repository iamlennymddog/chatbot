# Regenerates docs/datadog-instrumentation-guide.html from the instrumented source files.
# Usage: python3 docs/build_guide.py
import html, pathlib, sys
ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "datadog-instrumentation-guide.html"

def read(p): return (ROOT / p).read_text()
def between(p, start, end, include_end=True):
    s = read(p); i = s.index(start); j = s.index(end, i)
    return s[i:j + (len(end) if include_end else 0)]
def code(text, lang="js", title=None):
    head = f'<div class="code-title"><span>{html.escape(title)}</span><button class="copy">Copy</button></div>' if title else '<div class="code-title"><span></span><button class="copy">Copy</button></div>'
    return f'<div class="code">{head}<pre><code class="lang-{lang}">{html.escape(text.strip(chr(10)))}</code></pre></div>'
def details(summary, inner):
    return f'<details><summary>{html.escape(summary)}</summary>{inner}</details>'

agent_sh = read("datadog/agent.sh")
conf_yaml = read("datadog/conf.d/bitstalk-chatbot.d/conf.yaml")
otel_js = read("backend/src/otel.js")
tracing_js = read("backend/src/tracing.js")
run_agent = read("backend/src/agents/runAgent.js")
start_dd = between("start.sh", "  # APM + log/trace correlation", "BACKEND_CMD=(node --import dd-trace/initialize.mjs src/server.js)")
logger_base = between("backend/src/logger.js", "export const logger = pino(", "    },\n", True)
server_session = between("backend/src/server.js", "app.post('/api/chat'", "const ctx = { log, sessionId, steps: [], sources: new Map() };")
server_shutdown = between("backend/src/server.js", "// Flush pending OTel spans before exit.", "  });\n}")
agent_span = between("backend/src/agents/runAgent.js", "  return withSpan(\n    `invoke_agent ${name}`", "      links: caller ? [flow(caller.spanContext(), 'input', 'input')] : [],\n    },")
finish_fn = between("backend/src/agents/runAgent.js", "      const finish = (text, iterations) => {", "        return { text, usage, iterations };\n      };")
chat_fn = between("backend/src/agents/runAgent.js", "/** One Chat Completions call", "      return { response, choice, chatSpan: span.spanContext() };\n    },\n  );\n}")
tool_span = between("backend/src/agents/runAgent.js", "  return withSpan(\n    `execute_tool ${toolUse.name}`", "      links: chatSpan ? [flow(chatSpan, 'output', 'input')] : [],\n    },")
loop_links = between("backend/src/agents/runAgent.js", "        convo.push(choice.message);", "        chatInputs = outcomes.map((o) => flow(o.spanContext, 'output', 'input'));")
specialist = between("backend/src/agents/dealsSpecialist.js", "    const result = await runAgent({", "    });")

install = """cd backend
npm install dd-trace \\
  @opentelemetry/api@~1.9.0 \\
  @opentelemetry/sdk-trace-node @opentelemetry/sdk-trace-base \\
  @opentelemetry/resources \\
  @opentelemetry/exporter-trace-otlp-proto @opentelemetry/exporter-trace-otlp-http"""
pkg_script = """\"scripts\": {
  \"start\": \"node --import dd-trace/initialize.mjs src/server.js\"
}"""
server_import = """import 'dotenv/config';
import { otelEnabled, shutdownTracing } from './otel.js';   // first app import: registers the OTel provider
// ... rest of the imports"""
env_manual = """# Credentials
export ANTHROPIC_API_KEY=sk-ant-...            # LLM provider key (unchanged)
export DD_API_KEY=<your Datadog API key>       # Organization Settings > API Keys
export DD_SITE=datadoghq.com                   # your Datadog site (datadoghq.eu, us3.datadoghq.com, ...)

# Unified service tagging (APM + logs)
export DD_SERVICE=bitstalk-deals-chatbot-api
export DD_ENV=pov
export DD_VERSION=1.0.0

./start.sh"""
frontend_session = """// frontend/src/composables/useChat.js — one ID per conversation, sent with every turn
const sessionId = crypto.randomUUID()

fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ sessionId, messages }),
})"""
verify_cmd = """# Agent is up and accepting traces
curl -s http://localhost:8126/info | head -5
datadog/agent.sh status | grep -A3 "bitstalk-chatbot"

# OTLP exports to Datadog succeed (one line per batch)
grep '"event":"otel.export"' backend/logs/app.log | tail -3

# Send a test chat
curl -s -X POST http://localhost:3001/api/chat -H 'content-type: application/json' \\
  -d '{"sessionId":"guide-test-1","messages":[{"role":"user","content":"I live in Sandton, compare Samsung and iPhone contracts"}]}'"""
branch_diff = """git clone https://github.com/iamlennymddog/chatbot.git && cd chatbot
git fetch origin no-instrumentation
git diff origin/no-instrumentation main --stat     # files changed
git diff origin/no-instrumentation main -- backend  # code changes"""
stop_sh = read("stop.sh")
stop_usage = """./stop.sh               # stop backend, frontend and the Datadog Agent
./stop.sh --keep-agent  # stop the app, leave the Agent running"""
import base64
flow_png = base64.b64encode((ROOT / "docs" / "datadog-communication-flow.png").read_bytes()).decode()
prompts_js = read("backend/src/agents/prompts.js")
buddy_prompt = between("backend/src/agents/orchestrator.js", "// Tracked in LLM Observability as prompt", "variables: {} };")
specialist_prompt = between("backend/src/agents/dealsSpecialist.js", "  // Tracked in LLM Observability as prompt", "  const system = renderTemplate(prompt.template, prompt.variables);")
prompt_attr = between("backend/src/agents/runAgent.js", "  // Same prompt metadata on every LLM call", "promptTracking(prompt, messages.at(-1)?.content) : undefined;")
prompt_span = between("backend/src/agents/runAgent.js", "        // Prompt tracking (id, version, template, variables)", "'_dd.ml_obs.prompt_tracking': promptAttr } : {}),")
agent_start = """DD_API_KEY=<your key> DD_SITE=datadoghq.com datadog/agent.sh up
datadog/agent.sh status   # API key valid, APM Agent running, bitstalk-chatbot log source OK"""
flow_diagram = """invoke_agent deal-buddy ─input→ chat(sonnet) ─output→ execute_tool check_network_coverage ─output→ chat(sonnet) ─output→ agent output
                                             └output→ execute_tool consult_deals_specialist ─output→ ┘
                                                        └input→ invoke_agent deals-specialist ─input→ chat(haiku)
                                                                  ─→ execute_tool search_deals ─→ chat(haiku)
                                                                  ─→ execute_tool calculate_contract_cost ─→ chat(haiku)
                                                                  ─output→ agent output ─output→ consult_deals_specialist"""

steps = [
("overview", "How it fits together", f"""
<p>The chatbot is a small multi-agent system: <b>Deal Buddy</b> (orchestrator, Claude Sonnet) delegates research to the <b>Deals Specialist</b> sub-agent (Claude Haiku), which calls tools. Both agents use the <b>OpenAI Node.js SDK</b> pointed at Anthropic's OpenAI-compatible endpoint.</p>
<p>Datadog gets the telemetry through two paths:</p>
<figure class="diagram"><img src="data:image/png;base64,{flow_png}" alt="Telemetry flow from the BitsTalk Deal Buddy backend to Datadog"><figcaption>Full telemetry flow. Editable source: <code>docs/datadog-communication-flow.drawio</code> (open in <a href="https://app.diagrams.net">diagrams.net</a>).</figcaption></figure>
<p>In short:</p>
<table>
<tr><th>Signal</th><th>Sent by</th><th>Lands in</th></tr>
<tr><td>APM traces</td><td><code>dd-trace</code> → Datadog Agent (<code>localhost:8126</code>, HTTP)</td><td>APM, service <code>bitstalk-deals-chatbot-api</code></td></tr>
<tr><td>Runtime metrics (<code>runtime.node.*</code>)</td><td><code>dd-trace</code> → Agent DogStatsD (<code>localhost:8125</code>, UDP)</td><td>Metrics</td></tr>
<tr><td>Container and host metrics (<code>docker.*</code>, <code>system.*</code>)</td><td>collected by the Agent itself (Docker socket, <code>/proc</code>)</td><td>Metrics, Infrastructure</td></tr>
<tr><td>Logs (correlated to traces)</td><td>pino JSON file → Datadog Agent</td><td>Logs</td></tr>
<tr><td>Agent traces, sessions, <b>Execution Graph</b></td><td>OpenTelemetry GenAI → Datadog OTLP intake</td><td>LLM Observability, ml_app <code>bitstalk-deal-buddy</code></td></tr>
</table>
<div class="callout why"><b>Why OpenTelemetry for LLM Observability?</b> The Execution Graph draws its edges from <em>span links</em> between spans of the same trace (<code>{{from: "output", to: "input"}}</code>). The dd-trace Node.js LLM Observability SDK cannot create span links today, so agent, LLM and tool spans are emitted with OpenTelemetry using the GenAI semantic conventions. dd-trace stays in place for APM and logs, with its own LLM Observability switched <b>off</b> to avoid duplicate LLM spans.</div>
"""),
("prereqs", "Prerequisites", f"""
<ul class="check">
<li>Node.js 20+ and npm</li>
<li>Docker (Docker Desktop, colima, or a Linux host) for the Datadog Agent</li>
<li>A Datadog account and an <b>API key</b> (Organization Settings → API Keys). Note your <b>site</b>, e.g. <code>datadoghq.com</code> (US1) or <code>datadoghq.eu</code> (EU1).</li>
<li>Your LLM provider key (here <code>ANTHROPIC_API_KEY</code>)</li>
</ul>
<p>All file paths below are relative to the repository root. The repository has two branches:</p>
<table>
<tr><th>Branch</th><th>Contents</th></tr>
<tr><td><code>no-instrumentation</code></td><td>The same agent with no Datadog code: the starting point.</td></tr>
<tr><td><code>main</code></td><td>The fully instrumented agent described in this guide.</td></tr>
</table>
<p>To see every change this guide makes in one view:</p>
{code(branch_diff, "bash", "Shell")}
"""),
("agent", "Run the Datadog Agent", f"""
<p>The Agent receives APM traces from dd-trace on <code>localhost:8126</code>, DogStatsD metrics on <code>localhost:8125</code>, and tails the backend's log file. The script keeps the API key in a <code>0600</code> env file (<code>.dd/datadog.env</code>, gitignored) instead of the <code>docker run</code> command line.</p>
{code(agent_sh, "bash", "datadog/agent.sh")}
<p>Tell the Agent which log file to collect and how to tag it:</p>
{code(conf_yaml, "yaml", "datadog/conf.d/bitstalk-chatbot.d/conf.yaml")}
{code(agent_start, "bash", "Start and check")}
<div class="callout tip">Container log collection is off (<code>DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=false</code>) so only this app's log file is sent. Turn it on if the app itself runs in containers.</div>
"""),
("install", "Install the libraries", f"""
{code(install, "bash", "backend/")}
<p>Both <code>dd-trace</code> and the OpenTelemetry packages are saved to <code>backend/package.json</code>, so a clean <code>npm ci</code> on deploy includes them.</p>
"""),
("apm", "APM, logs and trace correlation (dd-trace)", f"""
<p>Load dd-trace before any application code with Node's <code>--import</code> flag. No code changes are needed for APM: Express, HTTP and the OpenAI SDK are instrumented automatically.</p>
{code(pkg_script, "json", "backend/package.json")}
<p>Give logs the same <code>service</code> / <code>env</code> / <code>version</code> as APM (unified service tagging). With <code>DD_LOGS_INJECTION=true</code>, dd-trace adds <code>dd.trace_id</code> and <code>dd.span_id</code> to every pino log line, so logs and traces link to each other.</p>
{code(logger_base, "js", "backend/src/logger.js (excerpt)")}
"""),
("otel", "Set up OpenTelemetry for LLM Observability", f"""
<p>Register an OpenTelemetry tracer provider that exports straight to Datadog's OTLP intake. The endpoint and headers come from environment variables (step 10). <code>service.name</code> becomes the LLM Observability <b>ml_app</b>. Export results are logged, because OpenTelemetry silently drops export errors (wrong key or site) by default.</p>
<div class="callout why"><b>One trace ID across LLM Observability, APM and logs.</b> The <code>DatadogTraceIdGenerator</code> gives every new OpenTelemetry trace the 128-bit trace ID of the active dd-trace span (the HTTP request). That is the same ID dd-trace writes into each log line as <code>dd.trace_id</code>, so from an LLM Observability trace you can click <b>View in APM</b> and then open the trace's <b>Logs</b>.</div>
{code(otel_js, "js", "backend/src/otel.js")}
<p>Import it first in the entry point, and flush pending spans on shutdown:</p>
{code(server_import, "js", "backend/src/server.js (top)")}
{code(server_shutdown, "js", "backend/src/server.js (bottom)")}
"""),
("helpers", "Add GenAI span helpers", f"""
<p>Datadog maps the GenAI <code>gen_ai.operation.name</code> attribute to LLM Observability span kinds:</p>
<table>
<tr><th><code>gen_ai.operation.name</code></th><th>LLM Observability span kind</th><th>Used for</th></tr>
<tr><td><code>invoke_agent</code></td><td>agent</td><td>each agent run (orchestrator and sub-agent)</td></tr>
<tr><td><code>chat</code></td><td>llm</td><td>each model call</td></tr>
<tr><td><code>execute_tool</code></td><td>tool</td><td>each tool call, including the sub-agent hand-off tool</td></tr>
</table>
<p>These helpers create spans, build the <code>{{from, to}}</code> link objects, and convert OpenAI chat messages to the GenAI message format (role + typed parts: <code>text</code>, <code>tool_call</code>, <code>tool_call_response</code>).</p>
{code(tracing_js, "js", "backend/src/tracing.js")}
"""),
("loop", "Instrument the agent loop (Execution Graph)", f"""
<p>All agents share one tool-use loop in <code>backend/src/agents/runAgent.js</code>. Instrumenting it once covers the orchestrator, the sub-agent and every tool. The <b>span links</b> describe how data flows, and are what the Execution Graph draws:</p>
<table>
<tr><th>Link</th><th>On span</th><th>Meaning</th></tr>
<tr><td>caller tool <b>input → input</b> agent</td><td>sub-agent <code>invoke_agent</code></td><td>the hand-off tool's input is the sub-agent's input</td></tr>
<tr><td>agent <b>input → input</b> first chat</td><td>first <code>chat</code></td><td>the agent's input feeds its first model call</td></tr>
<tr><td>chat <b>output → input</b> tool</td><td><code>execute_tool</code></td><td>the model's tool call is the tool's input</td></tr>
<tr><td>tool <b>output → input</b> next chat</td><td>next <code>chat</code></td><td>tool results feed the next model call</td></tr>
<tr><td>last chat <b>output → output</b> agent</td><td><code>invoke_agent</code></td><td>the final answer is the agent's output</td></tr>
<tr><td>agent <b>output → output</b> caller tool</td><td>hand-off <code>execute_tool</code></td><td>the sub-agent's answer is the tool's output</td></tr>
</table>
{code(flow_diagram, "text", "Resulting data flow for one chat turn")}
<h4>7a. Agent span</h4>
<p>Wrap each agent run in an <code>invoke_agent</code> span. <code>activeSpan()</code> returns the hand-off tool span when this agent is a sub-agent, so the sub-agent links back to its caller automatically.</p>
{code(agent_span, "js", "backend/src/agents/runAgent.js — invoke_agent")}
<h4>7b. LLM span</h4>
<p>The OpenAI SDK does not emit OpenTelemetry spans itself, so wrap each Chat Completions call in a <code>chat</code> span with the request, response, token usage and messages:</p>
{code(chat_fn, "js", "backend/src/agents/runAgent.js — chat")}
<h4>7c. Tool span</h4>
<p>Wrap each tool call in an <code>execute_tool</code> span, linked to the <code>chat</code> span that requested it:</p>
{code(tool_span, "js", "backend/src/agents/runAgent.js — execute_tool")}
<h4>7d. Wire the links through the loop</h4>
<p>After the tools run, their spans become the inputs of the next model call. When the agent finishes, link its output to the last model call, and to the caller tool for a sub-agent:</p>
{code(loop_links, "js", "backend/src/agents/runAgent.js — loop")}
{code(finish_fn, "js", "backend/src/agents/runAgent.js — finish")}
{details("Show the complete runAgent.js", code(run_agent, "js", "backend/src/agents/runAgent.js"))}
"""),
("subagents", "Describe agents and the session", f"""
<p>Each agent passes a <code>description</code>, recorded as <code>gen_ai.agent.description</code>. Sub-agents need nothing else: calling <code>runAgent</code> from inside a tool handler creates the nested agent and its links.</p>
{code(specialist, "js", "backend/src/agents/dealsSpecialist.js")}
<p>The backend reads a per-conversation <code>sessionId</code> and sets it as <code>gen_ai.conversation.id</code> on every span, so all turns of a chat group into one <b>LLM Observability session</b>:</p>
{code(server_session, "js", "backend/src/server.js")}
{code(frontend_session, "js", "frontend (already in place)")}
"""),
("prompts", "Track prompt versions", f"""
<p><a href="https://docs.datadoghq.com/llm_observability/monitoring/prompt_tracking/">Prompt Tracking</a> links every LLM call to the prompt template and version that produced it. LLM Observability then shows call counts, tokens and latency per prompt version, diffs two versions, filters traces by prompt, and opens any version in the Playground with its variables.</p>
<p>With OpenTelemetry, prompt metadata goes on each LLM (<code>chat</code>) span as the attribute <code>_dd.ml_obs.prompt_tracking</code>: a JSON string with <code>id</code>, <code>version</code>, <code>chat_template</code> (or <code>template</code>) and <code>variables</code>.</p>
{code(prompts_js, "js", "backend/src/agents/prompts.js")}
<p>Each agent defines its system prompt as a versioned template. The Deal Buddy prompt has no variables:</p>
{code(buddy_prompt, "js", "backend/src/agents/orchestrator.js")}
<p>The Deals Specialist prompt takes the catalogue details as variables, so they show up separately from the template:</p>
{code(specialist_prompt, "js", "backend/src/agents/dealsSpecialist.js")}
<p>The agent loop builds the attribute once per agent run (the agent's input becomes <code>user_message</code>) and sets it on every <code>chat</code> span:</p>
{code(prompt_attr, "js", "backend/src/agents/runAgent.js")}
{code(prompt_span, "js", "backend/src/agents/runAgent.js — chat span attributes")}
<div class="callout tip"><b>Versioning:</b> bump <code>version</code> whenever you change a template (for example <code>1.0.0</code> → <code>1.1.0</code>). Calls from before and after the change then appear as two versions of the same prompt, which you can compare side by side.</div>
"""),
("configure", "Configure, start and stop", f"""
<p><code>start.sh</code> starts the Agent, then the backend and frontend. These are the Datadog settings it sets for the backend:</p>
{code(start_dd, "bash", "start.sh (Datadog section)")}
<div class="callout warn"><b>Keep dd-trace's LLM Observability off.</b> If both <code>DD_LLMOBS_ENABLED</code> and the OpenTelemetry exporter are on, every model call appears twice in LLM Observability.</div>
<p>To run it with your own credentials:</p>
{code(env_manual, "bash", "Shell")}
<div class="callout tip">In this repository <code>start.sh</code> reads both keys with a local <code>getSecretKey</code> helper. Replace those two lines with your own secret store, or export <code>ANTHROPIC_API_KEY</code> and <code>DD_API_KEY</code> and remove the <code>getSecretKey</code> calls.</div>
<h4>Stop the stack</h4>
<p><code>stop.sh</code> stops the backend and frontend, then the Datadog Agent container. The backend gets <code>SIGTERM</code> first, so pending OpenTelemetry spans are flushed to Datadog before it exits. Use <code>--keep-agent</code> to stop only the app, which is what Ctrl+C in the <code>start.sh</code> terminal does too.</p>
{code(stop_usage, "bash", "Shell")}
{details("Show stop.sh", code(stop_sh, "bash", "stop.sh"))}
"""),
("verify", "Verify in Datadog", f"""
{code(verify_cmd, "bash", "Local checks")}
<p>Then open Datadog (replace <code>app.datadoghq.com</code> with your site):</p>
<ol class="verify">
<li><b>Execution Graph</b> — <a href="https://app.datadoghq.com/llm/traces?query=%40ml_app%3Abitstalk-deal-buddy">LLM Observability → Traces</a>, filter <code>@ml_app:bitstalk-deal-buddy</code>, open a <code>deal-buddy</code> trace and click <b>Execution Graph</b>. You should see <code>deal-buddy</code> → model calls → <code>check_network_coverage</code> / <code>consult_deals_specialist</code> → <code>deals-specialist</code> → <code>search_deals</code> / <code>calculate_contract_cost</code>.</li>
<li><b>Sessions</b> — the trace header shows the session; <b>View Session</b> lists every turn of the conversation.</li>
<li><b>LLM Observability → APM → Logs</b> — in the same LLM Observability trace, click <b>View in APM</b>. The APM trace opens with the same trace ID; its <b>Logs</b> tab shows every log line of that request (agent steps, tool calls, retrievals).</li>
<li><b>Prompts</b> — <a href="https://app.datadoghq.com/llm/prompts">LLM Observability → Prompts</a>: <code>deal-buddy-system</code> and <code>deals-specialist-system</code>, version <code>1.0.0</code>, with call counts, tokens and latency. In a trace, the LLM spans show the prompt and its variables.</li>
<li><b>APM</b> — <a href="https://app.datadoghq.com/apm/services/bitstalk-deals-chatbot-api">APM → service <code>bitstalk-deals-chatbot-api</code></a>: <code>POST /api/chat</code> with <code>openai.request</code> spans.</li>
<li><b>Logs</b> — <a href="https://app.datadoghq.com/logs?query=service%3Abitstalk-deals-chatbot-api">Logs, <code>service:bitstalk-deals-chatbot-api</code></a>. Open a log line and use the trace link to jump to its APM trace.</li>
</ol>
<div class="callout tip">Traces sent over OTLP can take a minute or two to appear in LLM Observability.</div>
"""),
("troubleshoot", "Troubleshooting", """
<table>
<tr><th>Symptom</th><th>Cause and fix</th></tr>
<tr><td>No traces in LLM Observability</td><td>Check <code>grep otel.export backend/logs/app.log</code>. <code>status: error</code> with 401/403 means a wrong API key or the wrong <code>DD_SITE</code> (the OTLP host is <code>otlp.&lt;site&gt;</code>).</td></tr>
<tr><td>Traces appear but there is no <b>Execution Graph</b> button</td><td>The spans have no links. Make sure LLM Observability comes from OpenTelemetry (steps 5–7), not from dd-trace's <code>DD_LLMOBS_ENABLED</code>.</td></tr>
<tr><td>A prompt does not appear under <b>Prompts</b></td><td><code>_dd.ml_obs.prompt_tracking</code> is read only on LLM spans (<code>gen_ai.operation.name=chat</code>) and must be valid JSON with <code>template</code> or <code>chat_template</code>. Search traces for <code>@meta.input.prompt.id:deal-buddy-system</code> to check that it was indexed.</td></tr>
<tr><td>Every model call appears twice</td><td>Both dd-trace LLM Observability and OpenTelemetry are on. Unset <code>DD_LLMOBS_ENABLED</code>.</td></tr>
<tr><td>Each turn is its own session</td><td>The frontend must reuse one <code>sessionId</code> per conversation; the backend sets it as <code>gen_ai.conversation.id</code>.</td></tr>
<tr><td>No APM traces</td><td>Start the backend with <code>node --import dd-trace/initialize.mjs</code> and check the Agent: <code>curl localhost:8126/info</code>.</td></tr>
<tr><td><b>View in APM</b> finds no trace, or the APM trace has no logs</td><td>The LLM Observability trace ID must equal the dd-trace trace ID. Check that <code>backend/src/otel.js</code> passes <code>idGenerator: new DatadogTraceIdGenerator()</code>, that dd-trace is loaded (<code>--import dd-trace/initialize.mjs</code>), and that <code>otel_trace_id</code> equals <code>dd.trace_id</code> in <code>backend/logs/app.log</code>.</td></tr>
<tr><td>Logs not linked to traces</td><td>Set <code>DD_LOGS_INJECTION=true</code>, and make sure the Agent's log config uses the same <code>service</code> as <code>DD_SERVICE</code>.</td></tr>
</table>
"""),
]

def render(out, title, h1, intro, steps, footer):
    nav = "".join(f'<a href="#{sid}"><span class="n">{i}</span>{html.escape(t)}</a>' for i, (sid, t, _) in enumerate(steps))
    body = "".join(
        f'<section id="{sid}"><h2><span class="n">{i}</span>{html.escape(t)}</h2>{content}</section>'
        for i, (sid, t, content) in enumerate(steps)
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ --ink:#1f2330; --muted:#5b6170; --line:#e3e5ec; --bg:#f7f7fa; --purple:#632ca6; --purple-soft:#f1ebfa; --code:#1e1f29; --ok:#1d7a4f; --warn:#9a5b00; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color:var(--ink); background:#fff; }}
header {{ background:linear-gradient(135deg,#3b1a6b,#632ca6); color:#fff; padding:40px 32px 32px; }}
header h1 {{ margin:0 0 8px; font-size:30px; }}
header p {{ margin:0; max-width:760px; opacity:.9; }}
.layout {{ display:grid; grid-template-columns:260px minmax(0,1fr); max-width:1200px; margin:0 auto; }}
nav {{ position:sticky; top:0; align-self:start; max-height:100vh; overflow:auto; padding:24px 16px; border-right:1px solid var(--line); }}
nav a {{ display:flex; gap:10px; align-items:center; padding:7px 10px; border-radius:6px; color:var(--ink); text-decoration:none; font-size:14px; }}
nav a:hover, nav a.active {{ background:var(--purple-soft); color:var(--purple); }}
.n {{ display:inline-flex; justify-content:center; align-items:center; min-width:24px; height:24px; border-radius:50%; background:var(--purple); color:#fff; font-size:12px; font-weight:600; }}
main {{ padding:8px 40px 80px; min-width:0; }}
section {{ padding-top:28px; border-bottom:1px solid var(--line); padding-bottom:20px; }}
h2 {{ display:flex; gap:12px; align-items:center; font-size:23px; margin:12px 0 14px; }}
h2 .n {{ min-width:32px; height:32px; font-size:15px; }}
h4 {{ margin:26px 0 6px; font-size:17px; }}
code {{ font:13.5px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:var(--bg); padding:1px 5px; border-radius:4px; }}
.code {{ margin:14px 0 18px; border-radius:8px; overflow:hidden; border:1px solid #2c2d3a; }}
.code-title {{ display:flex; justify-content:space-between; align-items:center; background:#2c2d3a; color:#c9cbe0; font:12.5px ui-monospace, Menlo, monospace; padding:6px 12px; }}
.copy {{ background:transparent; border:1px solid #555870; color:#c9cbe0; border-radius:5px; font-size:12px; padding:2px 10px; cursor:pointer; }}
.copy:hover {{ background:#3d3f52; }}
pre {{ margin:0; background:var(--code); color:#e8e9f3; padding:14px 16px; overflow:auto; max-height:560px; }}
pre code {{ background:none; padding:0; color:inherit; font-size:13px; white-space:pre; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0 16px; font-size:14.5px; }}
th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
th {{ background:var(--bg); }}
.callout {{ border-left:4px solid var(--purple); background:var(--purple-soft); padding:12px 16px; border-radius:6px; margin:16px 0; font-size:15px; }}
.callout.warn {{ border-color:var(--warn); background:#fff6e5; }}
.callout.tip {{ border-color:var(--ok); background:#eaf7f0; }}
details {{ margin:14px 0; }}
summary {{ cursor:pointer; color:var(--purple); font-weight:600; }}
ul.check {{ list-style:none; padding-left:0; }}
ul.check li::before {{ content:"✓ "; color:var(--ok); font-weight:700; }}
ol.verify li {{ margin-bottom:8px; }}
a {{ color:var(--purple); }}
.arch {{ display:grid; grid-template-columns:1fr 1.3fr 1fr; gap:14px; align-items:center; margin:18px 0; }}
.arch-col {{ display:flex; flex-direction:column; gap:12px; }}
.arch-box {{ border-radius:10px; padding:14px; text-align:center; font-weight:600; border:2px solid; }}
.arch-box small {{ display:block; font-weight:400; font-size:12.5px; color:var(--muted); margin-top:4px; }}
.arch-box.app {{ border-color:#3a7bd5; background:#eef4fd; }}
.arch-box.agent {{ border-color:#7a7f8f; background:#f3f4f7; }}
.arch-box.dd {{ border-color:var(--purple); background:var(--purple-soft); }}
.arrow {{ position:relative; background:#fafbfc; border:1px dashed #b9bdc9; border-radius:8px; padding:6px 12px 6px 12px; font-size:13px; color:var(--muted); }}
.arrow span {{ display:block; font-weight:700; color:var(--ink); }}
.arrow::after {{ content:"→"; position:absolute; right:-16px; top:50%; transform:translateY(-50%); color:#7a7f8f; font-size:18px; }}
.arrow.otel {{ border-color:var(--purple); }}
.arrow.otel span {{ color:var(--purple); }}
figure.diagram {{ margin:16px 0; }}
figure.diagram img {{ width:100%; border:1px solid var(--line); border-radius:8px; }}
figure.diagram figcaption {{ font-size:13px; color:var(--muted); margin-top:6px; }}
footer {{ color:var(--muted); font-size:13px; padding:24px 40px; }}
@media (max-width:900px) {{ .layout {{ grid-template-columns:1fr; }} nav {{ position:static; max-height:none; border-right:0; border-bottom:1px solid var(--line); }} main {{ padding:8px 18px 60px; }} .arch {{ grid-template-columns:1fr; }} .arrow::after {{ content:"↓"; right:auto; left:50%; top:auto; bottom:-20px; }} }}
</style>
</head>
<body>
<header>
<h1>{html.escape(h1)}</h1>
<p>{intro}</p>
</header>
<div class="layout">
<nav>{nav}</nav>
<main>{body}</main>
</div>
<footer>{footer}</footer>
<script>
document.querySelectorAll('.copy').forEach(function (b) {{
  b.addEventListener('click', function () {{
    var text = b.closest('.code').querySelector('code').innerText;
    navigator.clipboard.writeText(text).then(function () {{ b.textContent = 'Copied'; setTimeout(function () {{ b.textContent = 'Copy'; }}, 1500); }});
  }});
}});
var links = document.querySelectorAll('nav a');
var obs = new IntersectionObserver(function (entries) {{
  entries.forEach(function (e) {{
    if (e.isIntersecting) links.forEach(function (a) {{ a.classList.toggle('active', a.getAttribute('href') === '#' + e.target.id); }});
  }});
}}, {{ rootMargin: '-40% 0px -55% 0px' }});
document.querySelectorAll('section').forEach(function (s) {{ obs.observe(s); }});
</script>
</body>
</html>
"""
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    print(out, len(page))

render(
    OUT,
    "Datadog instrumentation guide — BitsTalk Deal Buddy",
    "Datadog instrumentation guide",
    "Step by step: add APM, logs and LLM Observability — with a working <b>Execution Graph</b> for agents, sub-agents and tools — to the BitsTalk Deal Buddy Node.js agent (OpenAI SDK, Claude models).",
    steps,
    "Code samples are taken from the <code>main</code> branch of this repository. The uninstrumented version is on <code>no-instrumentation</code>.",
)

# ---------------------------------------------------------------------------------------------
# Add-on guide: Execution Graph for an app that already has dd-trace (APM, logs) working.
# ---------------------------------------------------------------------------------------------
EG_OUT = ROOT / "docs" / "execution-graph-addon-guide.html"

eg_start_env = between("start.sh", "  # dd-trace's own LLM Obs stays OFF", '  export OTEL_SERVICE_NAME="${DD_LLMOBS_ML_APP:-bitstalk-deal-buddy}"')
eg_install = """npm install \\
  @opentelemetry/api@~1.9.0 \\
  @opentelemetry/sdk-trace-node @opentelemetry/sdk-trace-base \\
  @opentelemetry/resources \\
  @opentelemetry/exporter-trace-otlp-proto @opentelemetry/exporter-trace-otlp-http"""
eg_skeleton = """import { withSpan, flow, json, genAiMessages, activeSpan, SpanKind } from './tracing.js';

export async function runAgent({ name, model, messages, tools, sessionId }) {
  const caller = activeSpan(); // the hand-off tool's span when this agent runs as a sub-agent

  // 1. Agent span. A sub-agent links its input to the tool that called it.
  return withSpan(`invoke_agent ${name}`, {
    attributes: {
      'gen_ai.operation.name': 'invoke_agent',
      'gen_ai.agent.name': name,
      'gen_ai.conversation.id': sessionId,
      'gen_ai.input.messages': genAiMessages(messages.slice(-1)),
    },
    links: caller ? [flow(caller.spanContext(), 'input', 'input')] : [],
  }, async (agentSpan) => {
    let inputs = [flow(agentSpan.spanContext(), 'input', 'input')]; // first model call reads the agent input

    while (true) {
      // 2. LLM span around YOUR existing model call, linked to whatever fed it.
      const { message, chatSpan } = await withSpan(`chat ${model}`, {
        kind: SpanKind.CLIENT,
        attributes: {
          'gen_ai.operation.name': 'chat',
          'gen_ai.request.model': model,
          'gen_ai.conversation.id': sessionId,
          'gen_ai.input.messages': genAiMessages(messages),
        },
        links: inputs,
      }, async (span) => {
        const response = await callYourModel(messages, tools);           // unchanged
        const message = response.choices[0].message;
        span.setAttributes({
          'gen_ai.usage.input_tokens': response.usage?.prompt_tokens ?? 0,
          'gen_ai.usage.output_tokens': response.usage?.completion_tokens ?? 0,
          'gen_ai.output.messages': genAiMessages([message]),
        });
        return { message, chatSpan: span.spanContext() };
      });

      // 4. Done: the last model call's output is the agent's output (and the caller tool's output).
      if (!message.tool_calls?.length) {
        agentSpan.addLink(flow(chatSpan, 'output', 'output'));
        caller?.addLink(flow(agentSpan.spanContext(), 'output', 'output'));
        agentSpan.setAttribute('gen_ai.output.messages', genAiMessages([message]));
        return message.content;
      }

      // 3. Tool spans, each linked to the model call that requested it.
      messages.push(message);
      const results = await Promise.all(message.tool_calls.map((tc) =>
        withSpan(`execute_tool ${tc.function.name}`, {
          attributes: {
            'gen_ai.operation.name': 'execute_tool',
            'gen_ai.tool.name': tc.function.name,
            'gen_ai.tool.call.id': tc.id,
            'gen_ai.tool.call.arguments': tc.function.arguments,
          },
          links: [flow(chatSpan, 'output', 'input')],
        }, async (span) => {
          const content = await runYourTool(tc);                         // unchanged; may call runAgent()
          span.setAttribute('gen_ai.tool.call.result', json(content));
          return { spanContext: span.spanContext(), reply: { role: 'tool', tool_call_id: tc.id, content } };
        })));

      messages.push(...results.map((r) => r.reply));
      inputs = results.map((r) => flow(r.spanContext, 'output', 'input')); // tool results feed the next call
    }
  });
}"""
eg_server = """// your entry point (server.js / index.js)
import { shutdownTracing } from './otel.js';   // first application import
// ... the rest of your imports and app

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, async () => {
    await shutdownTracing();                    // flush pending LLM Observability spans
    process.exit(0);
  });
}"""
eg_env = """# Keep what you already have for dd-trace (DD_SERVICE, DD_ENV, DD_VERSION, DD_AGENT_HOST, DD_LOGS_INJECTION, ...)

# 1. Switch dd-trace's own LLM Observability off (otherwise every model call appears twice)
unset DD_LLMOBS_ENABLED                          # and remove DD_LLMOBS_ML_APP / DD_LLMOBS_AGENTLESS_ENABLED

# 2. Send OpenTelemetry GenAI spans straight to Datadog's OTLP intake
export DD_SITE=datadoghq.com                     # your site: datadoghq.eu, us3.datadoghq.com, ...
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://otlp.${DD_SITE}/v1/traces"
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL="http/protobuf"
export OTEL_EXPORTER_OTLP_TRACES_HEADERS="dd-api-key=${DD_API_KEY},dd-otlp-source=llmobs,DD-LLMObs-Enabled=true"
export OTEL_SERVICE_NAME="my-agent"              # becomes the LLM Observability ml_app"""
eg_k8s = """# Kubernetes: container env (the API key comes from a Secret; $(DD_API_KEY) expands the variable above it)
env:
  - name: DD_API_KEY
    valueFrom:
      secretKeyRef: { name: datadog-secret, key: api-key }
  - name: OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
    value: "https://otlp.datadoghq.com/v1/traces"
  - name: OTEL_EXPORTER_OTLP_TRACES_PROTOCOL
    value: "http/protobuf"
  - name: OTEL_EXPORTER_OTLP_TRACES_HEADERS
    value: "dd-api-key=$(DD_API_KEY),dd-otlp-source=llmobs,DD-LLMObs-Enabled=true"
  - name: OTEL_SERVICE_NAME
    value: "my-agent"
  # no DD_LLMOBS_ENABLED"""
eg_verify = """# The app logs one line per OTLP export batch (from otel.js)
grep '"event":"otel.export"' <your log file> | tail -3
#   status "ok"     -> spans reached Datadog
#   status "error"  -> 401/403: wrong API key or DD_SITE; network error: no egress to otlp.<site>:443"""

eg_steps = [
("before", "Before you start", f"""
<p>This guide is for a Node.js agent that already sends <b>APM traces and logs</b> to Datadog with <code>dd-trace</code>, but has no <b>Execution Graph</b> in LLM Observability. It adds the graph on top, without touching the APM and log setup.</p>
<table>
<tr><th>Stays as it is</th><th>Changes</th></tr>
<tr><td>
<ul>
<li><code>dd-trace</code>, loaded with <code>--import dd-trace/initialize.mjs</code></li>
<li>The Datadog Agent, APM traces, runtime metrics</li>
<li>Log collection and log/trace correlation</li>
<li>Your LLM client, tools and agent logic</li>
</ul></td><td>
<ul>
<li>dd-trace's own LLM Observability is switched <b>off</b></li>
<li>LLM Observability spans come from <b>OpenTelemetry</b> instead, sent straight to Datadog's OTLP intake</li>
<li>Two small files are added (<code>otel.js</code>, <code>tracing.js</code>)</li>
<li>Your agent loop gets three kinds of spans and the links between them</li>
</ul></td></tr>
</table>
<div class="callout why"><b>Why the switch?</b> The Execution Graph draws its edges from <em>span links</em> between spans of the same trace, each link saying how data flowed (<code>{{from: "output", to: "input"}}</code>). The dd-trace Node.js LLM Observability SDK cannot create span links today; OpenTelemetry can. dd-trace stays in place for everything else. Datadog docs: <a href="https://docs.datadoghq.com/llm_observability/instrument/otel_instrumentation/#span-links">OpenTelemetry Instrumentation → Span links</a>.</div>
<h4>Trade-offs to know about</h4>
<ul>
<li><b>No <code>tracer.llmobs</code> APIs.</b> With dd-trace's LLM Observability off, <code>llmobs.trace()</code>, <code>llmobs.annotate()</code> and prompt management (<code>tracer.llmobs.prompts.getPrompt</code>) can't be used. Prompt <em>tracking</em> still works through an OpenTelemetry attribute (see step 6).</li>
<li><b>LLM spans are created by hand.</b> The OpenAI Node.js SDK emits no OpenTelemetry spans, so each model call is wrapped in a span (step 5). APM's automatic <code>openai.request</code> spans are unaffected.</li>
<li><b>Slower to appear.</b> Spans sent over OTLP took 3–4 minutes to become searchable in LLM Observability in our tests, against about one minute for APM and logs.</li>
</ul>
<p>The working reference is this repository's <code>main</code> branch: <code>backend/src/otel.js</code>, <code>backend/src/tracing.js</code> and <code>backend/src/agents/runAgent.js</code>. The full guide, <code>docs/datadog-instrumentation-guide.html</code>, covers the same code with more detail.</p>
"""),
("llmobs-off", "Switch dd-trace's LLM Observability off", f"""
<p>Remove <code>DD_LLMOBS_ENABLED</code> (and <code>DD_LLMOBS_ML_APP</code>, <code>DD_LLMOBS_AGENTLESS_ENABLED</code>) from the app's environment, wherever it is set: shell scripts, Dockerfile, Helm values, Kubernetes manifests. If both dd-trace and OpenTelemetry send LLM Observability data, every model call appears twice.</p>
<p>If your code calls <code>llmobs.trace()</code>, <code>llmobs.wrap()</code> or <code>llmobs.annotate()</code>, replace those calls with the OpenTelemetry spans from step 5. They are the same places in your code: the agent run, each tool and each model call.</p>
<div class="callout tip">Leave everything else in dd-trace alone. APM, the OpenAI integration's APM spans and <code>DD_LOGS_INJECTION</code> keep working with LLM Observability off.</div>
"""),
("install", "Install OpenTelemetry", f"""
<p>In the app's directory (dd-trace is already installed):</p>
{code(eg_install, "bash", "Shell")}
<p>The packages are saved to <code>package.json</code>, so your normal build (<code>npm ci</code>) picks them up.</p>
<div class="callout warn">Keep <code>@opentelemetry/api</code> inside the range your dd-trace version supports (dd-trace 6.25: <code>&gt;=1.4.1 &lt;1.11.0</code>; this repository uses <code>~1.9.0</code>). Check <code>npm ls @opentelemetry/api</code> if npm reports a peer-dependency conflict.</div>
"""),
("otel", "Add the OpenTelemetry setup", f"""
<p>Copy <code>backend/src/otel.js</code> into your app unchanged. It:</p>
<ul>
<li>registers an OpenTelemetry tracer provider that exports to the OTLP endpoint from the environment (step 7),</li>
<li>gives each LLM Observability trace the <b>same trace ID as the dd-trace request</b>, so <b>View in APM</b> and log correlation work from LLM Observability,</li>
<li>logs every export result, because OpenTelemetry silently drops export errors (wrong key or site) by default.</li>
</ul>
<p>It uses the app's logger (<code>./logger.js</code>). Point that import at your own logger, or replace the <code>logger.info</code> / <code>logger.error</code> calls with <code>console</code>.</p>
{details("Show otel.js", code(otel_js, "js", "backend/src/otel.js"))}
<p>Import it first in your entry point and flush on shutdown, so the last spans are not lost when the process stops:</p>
{code(eg_server, "js", "Your entry point")}
"""),
("helpers", "Add the span helpers", f"""
<p>Copy <code>backend/src/tracing.js</code> unchanged. It provides:</p>
<table>
<tr><th>Helper</th><th>What it does</th></tr>
<tr><td><code>withSpan(name, {{ attributes, links, kind }}, fn)</code></td><td>runs <code>fn</code> inside an active span, records errors, always ends the span</td></tr>
<tr><td><code>flow(spanContext, from, to)</code></td><td>builds an Execution Graph link, e.g. <code>flow(chatSpan, 'output', 'input')</code></td></tr>
<tr><td><code>activeSpan()</code></td><td>the current span: inside a tool handler, that's the tool span</td></tr>
<tr><td><code>genAiMessages(messages)</code></td><td>converts OpenAI chat messages to the GenAI message format LLM Observability displays</td></tr>
<tr><td><code>json(value)</code></td><td>stringifies and truncates long attribute values</td></tr>
</table>
{details("Show tracing.js", code(tracing_js, "js", "backend/src/tracing.js"))}
"""),
("loop", "Instrument the agent loop", f"""
<p>This is the only step that touches your agent code. Datadog maps <code>gen_ai.operation.name</code> to the LLM Observability span kind, so you need three kinds of spans:</p>
<table>
<tr><th>Span</th><th><code>gen_ai.operation.name</code></th><th>Wraps</th></tr>
<tr><td>agent</td><td><code>invoke_agent</code></td><td>one agent run (orchestrator or sub-agent)</td></tr>
<tr><td>llm</td><td><code>chat</code></td><td>one model call</td></tr>
<tr><td>tool</td><td><code>execute_tool</code></td><td>one tool call, including a tool that hands off to a sub-agent</td></tr>
</table>
<p>And these links, which become the graph's edges. Links are drawn only between spans of the <b>same trace</b>, and carry <code>from</code> / <code>to</code> attributes (<a href="https://docs.datadoghq.com/llm_observability/instrument/otel_instrumentation/#span-links">Datadog docs: Span links</a>):</p>
<table>
<tr><th>Link</th><th>Put it on</th></tr>
<tr><td>agent <b>input → input</b> first model call</td><td>the first <code>chat</code> span</td></tr>
<tr><td>model call <b>output → input</b> tool it requested</td><td>each <code>execute_tool</code> span</td></tr>
<tr><td>tool <b>output → input</b> next model call</td><td>the next <code>chat</code> span (one link per tool)</td></tr>
<tr><td>last model call <b>output → output</b> agent</td><td>the <code>invoke_agent</code> span, when the agent finishes</td></tr>
<tr><td>hand-off tool <b>input → input</b> sub-agent, and sub-agent <b>output → output</b> hand-off tool</td><td>the sub-agent's <code>invoke_agent</code> span, and the hand-off tool span</td></tr>
</table>
<p>A typical tool-use loop with all of this in place looks like the sketch below. Only the <code>withSpan</code> wrappers and links are new; <code>callYourModel</code> and <code>runYourTool</code> stand for code you already have.</p>
{code(eg_skeleton, "js", "Sketch: your agent loop with spans and links")}
<div class="callout tip"><b>Sub-agents need no extra code.</b> When a tool handler calls <code>runAgent()</code>, <code>activeSpan()</code> returns that tool's span, so the sub-agent links itself to its caller in both directions. Because <code>withSpan</code> uses active spans, everything stays in one trace.</div>
<p>The complete version in this repository adds model and provider names, the system prompt, tool definitions, token usage on the agent span, error handling and logging:</p>
{details("Show backend/src/agents/runAgent.js", code(run_agent, "js", "backend/src/agents/runAgent.js"))}
"""),
("session", "Sessions and prompts", f"""
<p><b>Sessions.</b> Set <code>gen_ai.conversation.id</code> to one ID per conversation on every agent and model span (the sketch passes <code>sessionId</code> through). All turns of a conversation then group into one LLM Observability session. If you already pass a session ID to <code>llmobs.trace()</code>, reuse that value.</p>
<p><b>Prompt tracking (optional).</b> To see calls, tokens and latency per prompt version, add the attribute <code>_dd.ml_obs.prompt_tracking</code> to each <code>chat</code> span: a JSON string with <code>id</code>, <code>version</code>, <code>template</code> (or <code>chat_template</code>) and <code>variables</code>. This repository builds it with a small helper:</p>
{code(prompts_js, "js", "backend/src/agents/prompts.js")}
<p>Step 9 of the full guide shows how the agents define their versioned prompts.</p>
"""),
("configure", "Configure the deployment", f"""
<p>The OpenTelemetry spans go <b>from the app straight to Datadog</b> over HTTPS, not through the Datadog Agent. The app needs a Datadog API key and outbound access to <code>otlp.&lt;your site&gt;</code> on port 443.</p>
{code(eg_env, "bash", "Environment variables")}
{code(eg_k8s, "yaml", "Kubernetes example")}
<p>For comparison, this is how this repository's <code>start.sh</code> sets them:</p>
{code(eg_start_env, "bash", "start.sh (excerpt)")}
"""),
("verify", "Verify", f"""
{code(eg_verify, "bash", "Local check")}
<p>Send a request that makes the agent call at least one tool, wait 3–4 minutes, then in Datadog (replace <code>app.datadoghq.com</code> with your site):</p>
<ol class="verify">
<li><a href="https://app.datadoghq.com/llm/traces">LLM Observability → Traces</a>, filter <code>@ml_app:&lt;OTEL_SERVICE_NAME&gt;</code>, open a trace and click <b>Execution Graph</b>. You should see the agent, its model calls and tools, and any sub-agent nested under its hand-off tool.</li>
<li>In the same trace, click <b>View in APM</b>. Your existing APM trace for the request opens, and its <b>Logs</b> tab shows the request's logs.</li>
<li>Check that each model call appears <b>once</b>. Two copies mean dd-trace's LLM Observability is still on (step 1).</li>
</ol>
"""),
("troubleshoot", "Troubleshooting", """
<table>
<tr><th>Symptom</th><th>Cause and fix</th></tr>
<tr><td>No traces in LLM Observability</td><td>Wait 3–4 minutes, then check the <code>otel.export</code> log lines. 401/403: wrong API key, or <code>DD_SITE</code> doesn't match your org. Network errors: the app has no egress to <code>otlp.&lt;site&gt;:443</code>.</td></tr>
<tr><td>Traces appear but there is no <b>Execution Graph</b> button</td><td>The spans have no links, or the trace came from dd-trace's LLM Observability. Check that <code>DD_LLMOBS_ENABLED</code> is unset and that every <code>chat</code> and <code>execute_tool</code> span gets its <code>links</code>.</td></tr>
<tr><td>The graph is missing edges, or a sub-agent floats on its own</td><td>A link is missing. Every model call after the first needs one link per tool result; a sub-agent must run inside its hand-off tool's <code>withSpan</code>, so that <code>activeSpan()</code> finds the tool.</td></tr>
<tr><td>Every model call appears twice</td><td>dd-trace's LLM Observability is still on. Remove <code>DD_LLMOBS_ENABLED</code> everywhere it is set.</td></tr>
<tr><td>Agent, model and tool spans are split across several traces</td><td>A span was started outside the active context, for example in a callback that lost the async context. Create spans with <code>withSpan</code> (it uses <code>startActiveSpan</code>) and <code>await</code> inside it.</td></tr>
<tr><td><b>View in APM</b> finds no trace</td><td>The LLM Observability trace ID must equal the dd-trace trace ID. Check that <code>otel.js</code> passes <code>idGenerator: new DatadogTraceIdGenerator()</code>, is imported first, and that the app still starts with <code>--import dd-trace/initialize.mjs</code>.</td></tr>
<tr><td>Each turn is its own session</td><td>Use the same <code>gen_ai.conversation.id</code> for every turn of a conversation.</td></tr>
</table>
"""),
]

render(
    EG_OUT,
    "Add the Execution Graph to a dd-trace Node.js agent",
    "Add the Execution Graph to an existing dd-trace agent",
    "For Node.js agents that already send APM traces and logs to Datadog with <code>dd-trace</code>: keep that setup and add LLM Observability's <b>Execution Graph</b> with OpenTelemetry GenAI spans.",
    eg_steps,
    "Code samples are taken from the <code>main</code> branch of this repository. Full guide: <code>docs/datadog-instrumentation-guide.html</code>.",
)

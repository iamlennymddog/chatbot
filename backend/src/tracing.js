// GenAI semantic-convention spans + span links for the LLM Obs Execution Graph.
// Span kinds come from gen_ai.operation.name: invoke_agent -> agent, execute_tool -> tool,
// chat -> llm. Links carry {from, to} to describe data flow between spans of one trace.
import { trace, context, SpanKind, SpanStatusCode } from '@opentelemetry/api';
import { provider } from './otel.js';

const tracer = provider.getTracer('bitstalk-deal-buddy');
const MAX_ATTR = 8000;

export const flow = (spanContext, from, to) => ({ context: spanContext, attributes: { from, to } });
export const json = (value) => {
  const s = typeof value === 'string' ? value : JSON.stringify(value);
  return s.length > MAX_ATTR ? `${s.slice(0, MAX_ATTR)}…` : s;
};

const parseArgs = (args) => {
  try {
    return args ? JSON.parse(args) : {};
  } catch {
    return args;
  }
};

/** OpenAI chat messages -> GenAI semconv messages (role + typed parts). */
export function genAiMessages(messages) {
  return json(
    messages.map((m) => {
      if (m.role === 'tool') {
        return { role: 'tool', parts: [{ type: 'tool_call_response', id: m.tool_call_id, response: m.content }] };
      }
      const parts = [];
      if (m.content) parts.push({ type: 'text', content: String(m.content) });
      for (const tc of m.tool_calls ?? []) {
        parts.push({ type: 'tool_call', id: tc.id, name: tc.function.name, arguments: parseArgs(tc.function.arguments) });
      }
      return { role: m.role, parts, ...(m.finish_reason ? { finish_reason: m.finish_reason } : {}) };
    }),
  );
}

export const activeSpan = () => trace.getSpan(context.active());

/** Run fn inside an active span; records errors and always ends the span. */
export function withSpan(name, { attributes = {}, links = [], kind = SpanKind.INTERNAL } = {}, fn) {
  return tracer.startActiveSpan(name, { attributes, links, kind }, async (span) => {
    try {
      return await fn(span);
    } catch (err) {
      span.recordException(err);
      span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
      throw err;
    } finally {
      span.end();
    }
  });
}

export { SpanKind, SpanStatusCode };

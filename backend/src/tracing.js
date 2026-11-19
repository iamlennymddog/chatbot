// Thin wrapper around Datadog LLM Observability spans.
// No-op unless the app is started with dd-trace loaded (node --import dd-trace/initialize.mjs)
// and DD_LLMOBS_ENABLED set. Span kinds used: agent, tool, retrieval. The OpenAI integration
// in dd-trace adds the llm spans underneath, giving the Execution Graph:
//   agent(deal-buddy) -> llm / tool(check_network_coverage)
//                     -> tool(consult_deals_specialist) -> agent(deals-specialist)
//                          -> llm / retrieval(search_deals) / tool(calculate_contract_cost)
let llmobs = null;
if (process.env.DD_LLMOBS_ENABLED && !/^(0|false)$/i.test(process.env.DD_LLMOBS_ENABLED)) {
  try {
    llmobs = (await import('dd-trace')).default.llmobs;
  } catch {
    llmobs = null;
  }
}

/**
 * Run fn inside an LLM Obs span.
 * spanOptions: { kind, name, sessionId? }  (sessionId belongs on the root span only;
 *              children inherit it through the async context)
 * annotate(result) returns { inputData, outputData, metadata, metrics, tags } for the span.
 * startAnnotation is applied when the span opens, e.g. { agent: {...} } so the agent
 * manifest is recorded even if the run fails.
 */
export async function traceSpan(spanOptions, fn, annotate, startAnnotation) {
  if (!llmobs) return fn();
  return llmobs.trace(spanOptions, async (span) => {
    if (startAnnotation) {
      try {
        llmobs.annotate(span, startAnnotation);
      } catch {
        /* annotation must never break the request */
      }
    }
    const result = await fn();
    if (annotate) {
      try {
        llmobs.annotate(span, annotate(result));
      } catch {
        /* annotation must never break the request */
      }
    }
    return result;
  });
}

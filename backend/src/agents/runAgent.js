import { openai } from './client.js';
import { withSpan, flow, json, genAiMessages, activeSpan, SpanKind, SpanStatusCode } from '../tracing.js';

const MAX_ITERATIONS = 6;
const PROVIDER = 'anthropic'; // OpenAI SDK -> Anthropic's OpenAI-compatible endpoint

/**
 * Generic tool-use loop on the OpenAI Chat Completions API, traced with OTel GenAI conventions.
 * tools: [{ definition: {name, description, input_schema}, handler: async (input, ctx) => any }]
 * ctx:   { log, sessionId, steps, sources } shared across the whole request (all agents).
 *
 * Execution Graph edges (span links, all in one trace):
 *   caller tool --input->input--> agent --input->input--> first chat
 *   chat --output->input--> each tool it called --output->input--> next chat
 *   last chat --output->output--> agent --output->output--> caller tool
 */
export async function runAgent({ name, description, model, system, messages, tools, ctx, maxTokens = 1024 }) {
  const toolMap = new Map(tools.map((t) => [t.definition.name, t]));
  const caller = activeSpan(); // set when this agent is invoked from a tool (sub-agent)
  const toolDefs = tools.map((t) => ({
    type: 'function',
    function: { name: t.definition.name, description: t.definition.description, parameters: t.definition.input_schema },
  }));
  const systemInstructions = json([{ type: 'text', content: system }]);
  const toolDefinitions = json(
    tools.map((t) => ({
      type: 'function',
      name: t.definition.name,
      description: t.definition.description,
      parameters: t.definition.input_schema,
    })),
  );

  return withSpan(
    `invoke_agent ${name}`,
    {
      attributes: {
        'gen_ai.operation.name': 'invoke_agent',
        'gen_ai.provider.name': PROVIDER,
        'gen_ai.agent.name': name,
        'gen_ai.agent.description': description,
        'gen_ai.request.model': model,
        'gen_ai.request.max_tokens': maxTokens,
        'gen_ai.conversation.id': ctx.sessionId,
        'gen_ai.system_instructions': systemInstructions,
        'gen_ai.tool.definitions': toolDefinitions,
        'gen_ai.input.messages': genAiMessages(messages.slice(-1)),
      },
      links: caller ? [flow(caller.spanContext(), 'input', 'input')] : [],
    },
    async (agentSpan) => {
      const log = ctx.log.child({ agent: name, otel_trace_id: agentSpan.spanContext().traceId });
      const convo = [{ role: 'system', content: system }, ...messages];
      const usage = { input_tokens: 0, output_tokens: 0 };
      log.info({ event: 'agent.start', model }, `Agent ${name} started`);

      // The first LLM call consumes the agent's input; later ones consume the tool results.
      let chatInputs = [flow(agentSpan.spanContext(), 'input', 'input')];
      let lastChat = null;

      const finish = (text, iterations) => {
        if (lastChat) agentSpan.addLink(flow(lastChat, 'output', 'output'));
        if (caller) caller.addLink(flow(agentSpan.spanContext(), 'output', 'output'));
        agentSpan.setAttributes({
          'gen_ai.output.messages': json([{ role: 'assistant', parts: [{ type: 'text', content: text }], finish_reason: 'stop' }]),
          'gen_ai.usage.input_tokens': usage.input_tokens,
          'gen_ai.usage.output_tokens': usage.output_tokens,
        });
        return { text, usage, iterations };
      };

      for (let i = 1; i <= MAX_ITERATIONS; i++) {
        const t0 = Date.now();
        const { response, choice, chatSpan } = await chat({ model, maxTokens, convo, toolDefs, systemInstructions, toolDefinitions, ctx, links: chatInputs });
        lastChat = chatSpan;
        usage.input_tokens += response.usage?.prompt_tokens ?? 0;
        usage.output_tokens += response.usage?.completion_tokens ?? 0;
        log.info(
          {
            event: 'agent.llm_call',
            model: response.model,
            iteration: i,
            llm_ms: Date.now() - t0,
            stop_reason: choice.finish_reason,
            input_tokens: response.usage?.prompt_tokens,
            output_tokens: response.usage?.completion_tokens,
          },
          `Agent ${name} LLM call ${i}`,
        );

        const toolCalls = choice.message.tool_calls ?? [];
        if (choice.finish_reason !== 'tool_calls' || toolCalls.length === 0) {
          const text = choice.message.content ?? '';
          log.info({ event: 'agent.end', iterations: i, ...usage }, `Agent ${name} finished`);
          return finish(text, i);
        }

        convo.push(choice.message);
        const outcomes = await Promise.all(toolCalls.map((tc) => executeTool(tc, toolMap, ctx, log, name, chatSpan)));
        convo.push(...outcomes.map((o) => o.result));
        // Every tool result feeds the next LLM call.
        chatInputs = outcomes.map((o) => flow(o.spanContext, 'output', 'input'));
      }

      log.warn({ event: 'agent.max_iterations', ...usage }, `Agent ${name} hit max iterations`);
      return finish("Sorry, I couldn't complete that request. Please try rephrasing.", MAX_ITERATIONS);
    },
  );
}

/** One Chat Completions call inside a GenAI `chat` span (the OpenAI SDK has no native OTel spans). */
function chat({ model, maxTokens, convo, toolDefs, systemInstructions, toolDefinitions, ctx, links }) {
  return withSpan(
    `chat ${model}`,
    {
      kind: SpanKind.CLIENT,
      attributes: {
        'gen_ai.operation.name': 'chat',
        'gen_ai.provider.name': PROVIDER,
        'gen_ai.request.model': model,
        'gen_ai.request.max_tokens': maxTokens,
        'gen_ai.conversation.id': ctx.sessionId,
        'gen_ai.system_instructions': systemInstructions,
        'gen_ai.tool.definitions': toolDefinitions,
        'gen_ai.input.messages': genAiMessages(convo.filter((m) => m.role !== 'system')),
      },
      links,
    },
    async (span) => {
      const response = await openai.chat.completions.create({ model, max_tokens: maxTokens, messages: convo, tools: toolDefs });
      const choice = response.choices[0];
      span.setAttributes({
        'gen_ai.response.id': response.id,
        'gen_ai.response.model': response.model,
        'gen_ai.response.finish_reasons': [choice.finish_reason],
        'gen_ai.usage.input_tokens': response.usage?.prompt_tokens ?? 0,
        'gen_ai.usage.output_tokens': response.usage?.completion_tokens ?? 0,
        'gen_ai.output.messages': genAiMessages([{ ...choice.message, finish_reason: choice.finish_reason }]),
      });
      return { response, choice, chatSpan: span.spanContext() };
    },
  );
}

async function executeTool(toolCall, toolMap, ctx, log, agentName, chatSpan) {
  const toolUse = { id: toolCall.id, name: toolCall.function.name, input: parseArgs(toolCall.function.arguments) };
  const tool = toolMap.get(toolUse.name);
  const t0 = Date.now();
  ctx.steps.push({ agent: agentName, tool: toolUse.name, input: toolUse.input });

  return withSpan(
    `execute_tool ${toolUse.name}`,
    {
      attributes: {
        'gen_ai.operation.name': 'execute_tool',
        'gen_ai.tool.name': toolUse.name,
        'gen_ai.tool.type': 'function',
        'gen_ai.tool.call.id': toolUse.id,
        'gen_ai.tool.description': tool?.definition.description,
        'gen_ai.tool.call.arguments': json(toolUse.input),
      },
      // The LLM's tool call output is this tool's input.
      links: chatSpan ? [flow(chatSpan, 'output', 'input')] : [],
    },
    async (span) => {
      const spanContext = span.spanContext();
      try {
        if (!tool) throw new Error(`Unknown tool ${toolUse.name}`);
        const output = await tool.handler(toolUse.input, ctx);
        const content = typeof output === 'string' ? output : JSON.stringify(output);
        span.setAttribute('gen_ai.tool.call.result', json(content));
        log.info(
          { event: 'tool.call', tool: toolUse.name, tool_input: toolUse.input, tool_ms: Date.now() - t0, status: 'ok' },
          `Tool ${toolUse.name} executed`,
        );
        return { spanContext, result: { role: 'tool', tool_call_id: toolUse.id, content } };
      } catch (err) {
        // Tool errors go back to the model as text, so record them without failing the request.
        span.recordException(err);
        span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
        log.error({ event: 'tool.call', tool: toolUse.name, tool_input: toolUse.input, status: 'error', err }, `Tool ${toolUse.name} failed`);
        return { spanContext, result: { role: 'tool', tool_call_id: toolUse.id, content: `Error: ${err.message}` } };
      }
    },
  );
}

function parseArgs(args) {
  try {
    return args ? JSON.parse(args) : {};
  } catch {
    return {};
  }
}

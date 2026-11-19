import { openai } from './client.js';

const MAX_ITERATIONS = 6;

/**
 * Generic tool-use loop on the OpenAI Chat Completions API.
 * tools: [{ definition: {name, description, input_schema}, handler: async (input, ctx) => any }]
 * ctx:   { log, steps, sources } shared across the whole request (all agents).
 */
export async function runAgent({ name, model, system, messages, tools, ctx, maxTokens = 1024 }) {
  const toolMap = new Map(tools.map((t) => [t.definition.name, t]));
  const log = ctx.log.child({ agent: name });

  const convo = [{ role: 'system', content: system }, ...messages];
  const toolDefs = tools.map((t) => ({
    type: 'function',
    function: {
      name: t.definition.name,
      description: t.definition.description,
      parameters: t.definition.input_schema,
    },
  }));
  const usage = { input_tokens: 0, output_tokens: 0 };
  log.info({ event: 'agent.start', model }, `Agent ${name} started`);

  for (let i = 1; i <= MAX_ITERATIONS; i++) {
    const t0 = Date.now();
    const response = await openai.chat.completions.create({
      model,
      max_tokens: maxTokens,
      messages: convo,
      tools: toolDefs,
    });
    const choice = response.choices[0];
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
      return { text, usage, iterations: i };
    }

    convo.push(choice.message);
    const results = await Promise.all(toolCalls.map((tc) => executeTool(tc, toolMap, ctx, log, name)));
    convo.push(...results);
  }

  log.warn({ event: 'agent.max_iterations', ...usage }, `Agent ${name} hit max iterations`);
  return { text: "Sorry, I couldn't complete that request. Please try rephrasing.", usage, iterations: MAX_ITERATIONS };
}

async function executeTool(toolCall, toolMap, ctx, log, agentName) {
  const toolUse = { id: toolCall.id, name: toolCall.function.name, input: parseArgs(toolCall.function.arguments) };
  const tool = toolMap.get(toolUse.name);
  const t0 = Date.now();
  ctx.steps.push({ agent: agentName, tool: toolUse.name, input: toolUse.input });
  try {
    if (!tool) throw new Error(`Unknown tool ${toolUse.name}`);
    const output = await tool.handler(toolUse.input, ctx);
    log.info(
      { event: 'tool.call', tool: toolUse.name, tool_input: toolUse.input, tool_ms: Date.now() - t0, status: 'ok' },
      `Tool ${toolUse.name} executed`,
    );
    return {
      role: 'tool',
      tool_call_id: toolUse.id,
      content: typeof output === 'string' ? output : JSON.stringify(output),
    };
  } catch (err) {
    log.error({ event: 'tool.call', tool: toolUse.name, tool_input: toolUse.input, status: 'error', err }, `Tool ${toolUse.name} failed`);
    return { role: 'tool', tool_call_id: toolUse.id, content: `Error: ${err.message}` };
  }
}

function parseArgs(args) {
  try {
    return args ? JSON.parse(args) : {};
  } catch {
    return {};
  }
}

import { runAgent } from './runAgent.js';
import { SPECIALIST_MODEL } from './client.js';
import { createDealTools } from '../tools/dealTools.js';
import { renderTemplate } from './prompts.js';

/** Sub-agent: researches the deals catalogue and returns a factual brief to the orchestrator. */
export function createDealsSpecialist(index) {
  const tools = createDealTools(index);
  // Tracked in LLM Observability as prompt `deals-specialist-system`; catalogue details are variables.
  // Bump the version when the template changes.
  const prompt = {
    id: 'deals-specialist-system',
    version: '1.0.0',
    template: `You are the BitsTalk Deals Specialist, an internal research agent. You do NOT talk to customers directly;
you prepare a factual brief for the customer-facing assistant.

- ALWAYS use search_deals to find facts. Search more than once when comparing categories or brands.
- Use calculate_contract_cost when comparing contracts or when total cost matters.
- Only report facts from tool results. Never invent prices, devices or deals.
- Output a concise brief: the 2-4 best matching deals with deal ID, device/plan, monthly price, term, data, extras, and total cost if calculated. Note anything relevant that is NOT available.

Catalogue: {{catalogue}}
Deals in catalogue: {{deal_ids}}`,
    variables: {
      catalogue: index.preamble.replace(/\n/g, ' '),
      deal_ids: index.chunks.map((c) => c.id).join(', '),
    },
  };
  const system = renderTemplate(prompt.template, prompt.variables);

  return async function consult(task, ctx) {
    const result = await runAgent({
      name: 'deals-specialist',
      description: 'Researches the BitsTalk deals catalogue and calculates contract costs',
      model: SPECIALIST_MODEL,
      system,
      prompt,
      messages: [{ role: 'user', content: task }],
      tools,
      ctx,
    });
    return result.text;
  };
}

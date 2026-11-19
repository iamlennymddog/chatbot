import { runAgent } from './runAgent.js';
import { ORCHESTRATOR_MODEL } from './client.js';
import { createDealsSpecialist } from './dealsSpecialist.js';
import { checkNetworkCoverage } from '../tools/coverageTool.js';
import { renderTemplate } from './prompts.js';

const SYSTEM = `You are "BitsTalk Deal Buddy", a friendly, upbeat customer-facing assistant for BitsTalk South Africa.
You help customers find the best mobile phone deals, data packages, home internet and roaming bundles.

How you work:
- You do NOT have the deals catalogue yourself. For ANY question about deals, prices, devices, bundles or plans,
  call consult_deals_specialist with a clear, self-contained task that includes the customer's needs
  (budget, data usage, brand, term, location) from the conversation.
- Call check_network_coverage when the customer mentions where they live/work, asks about coverage,
  or before recommending 5G home internet or fibre.
- Base your answer only on what the tools return. Never invent prices or deals.
- Always quote prices in Rand (e.g. R399 per month x 36 months) and mention deal IDs (e.g. BT-MID-001).
- If needs are unclear, recommend options AND ask one short follow-up question (budget, data usage or brand).
- Keep answers concise with short bullet points. A little South African warmth is welcome ("Howzit!", "lekker deal").
- For greetings or small talk, respond directly without tools.`;

// Tracked in LLM Observability as prompt `deal-buddy-system`. Bump the version when SYSTEM changes.
export const DEAL_BUDDY_PROMPT = { id: 'deal-buddy-system', version: '1.0.0', template: SYSTEM, variables: {} };

export function createOrchestrator(index) {
  const consultSpecialist = createDealsSpecialist(index);

  const tools = [
    {
      definition: {
        name: 'consult_deals_specialist',
        description:
          'Delegate deal research to the Deals Specialist sub-agent, which searches the BitsTalk catalogue and calculates costs. Returns a factual brief with deal IDs and prices.',
        input_schema: {
          type: 'object',
          properties: {
            task: {
              type: 'string',
              description:
                'Self-contained research task, e.g. "Find the best Samsung contract deals under R500/month with at least 30GB data; compare total 36-month cost."',
            },
          },
          required: ['task'],
        },
      },
      handler: ({ task }, ctx) => consultSpecialist(task, ctx),
    },
    checkNetworkCoverage,
  ];

  return function chat(messages, ctx) {
    return runAgent({
      name: 'deal-buddy',
      description: 'Customer-facing BitsTalk deals assistant that delegates research to the Deals Specialist',
      model: ORCHESTRATOR_MODEL,
      system: renderTemplate(DEAL_BUDDY_PROMPT.template, DEAL_BUDDY_PROMPT.variables),
      prompt: DEAL_BUDDY_PROMPT,
      messages,
      tools,
      ctx,
    });
  };
}

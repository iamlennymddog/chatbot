// Tools available to the Deals Specialist sub-agent.
export function createDealTools(index) {
  const searchDeals = {
    definition: {
      name: 'search_deals',
      description:
        'Search the BitsTalk deals catalogue (phones, contracts, SIM-only, prepaid bundles, home internet, roaming, business, trade-in info). Returns the most relevant catalogue sections with full details. Call multiple times with different queries to compare options.',
      input_schema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Keywords, e.g. "Samsung contract 50GB" or "Europe roaming"' },
          top_k: { type: 'integer', description: 'Number of results (1-6), default 4' },
        },
        required: ['query'],
      },
    },
    handler: async ({ query, top_k = 4 }, ctx) => {
      const hits = index.search(query, Math.min(Math.max(top_k, 1), 6));
      for (const h of hits) ctx.sources.set(h.chunk.id, h.chunk.title);
      ctx.log.info(
        { event: 'rag.retrieve', query, hits: hits.map((h) => ({ id: h.chunk.id, score: Number(h.score.toFixed(3)) })) },
        'Retrieved deal context',
      );
      if (!hits.length) return 'No matching deals found. Try broader keywords.';
      return hits.map((h) => ({ id: h.chunk.id, score: Number(h.score.toFixed(3)), text: h.chunk.text }));
    },
  };

  const calculateContractCost = {
    definition: {
      name: 'calculate_contract_cost',
      description:
        'Calculate the total cost of a contract or plan: monthly price x months + upfront payment, minus any trade-in credit. Use this whenever comparing total cost of ownership between deals.',
      input_schema: {
        type: 'object',
        properties: {
          deal_id: { type: 'string', description: 'Deal ID, e.g. BT-MID-001' },
          monthly_price: { type: 'number', description: 'Monthly price in Rand' },
          months: { type: 'integer', description: 'Contract term in months (e.g. 24 or 36)' },
          upfront: { type: 'number', description: 'Once-off upfront payment in Rand, default 0' },
          trade_in_credit: { type: 'number', description: 'Trade-in credit in Rand, default 0' },
        },
        required: ['monthly_price', 'months'],
      },
    },
    handler: async ({ deal_id, monthly_price, months, upfront = 0, trade_in_credit = 0 }) => {
      const total = monthly_price * months + upfront - trade_in_credit;
      return {
        deal_id,
        total_cost_rand: Math.round(total * 100) / 100,
        effective_monthly_rand: Math.round((total / months) * 100) / 100,
        breakdown: `R${monthly_price} x ${months} + R${upfront} upfront - R${trade_in_credit} trade-in`,
      };
    },
  };

  return [searchDeals, calculateContractCost];
}

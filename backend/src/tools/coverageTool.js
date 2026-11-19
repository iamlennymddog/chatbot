// Mock network coverage lookup used by the orchestrator (no real BitsTalk API).
// Deterministic per area so demos are repeatable.
const METRO = ['johannesburg', 'sandton', 'pretoria', 'cape town', 'durban', 'midrand', 'centurion', 'soweto', 'gqeberha', 'port elizabeth', 'bloemfontein', 'stellenbosch', 'umhlanga', 'randburg', 'rosebank'];

export const checkNetworkCoverage = {
  definition: {
    name: 'check_network_coverage',
    description:
      'Check BitsTalk network coverage (5G, LTE, fibre availability) for a South African suburb, town or city. Use when the customer asks about coverage or before recommending 5G home internet or fibre.',
    input_schema: {
      type: 'object',
      properties: { area: { type: 'string', description: 'Suburb, town or city, e.g. "Sandton" or "Polokwane"' } },
      required: ['area'],
    },
  },
  handler: async ({ area }) => {
    const a = area.toLowerCase().trim();
    const hash = [...a].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
    const metro = METRO.some((m) => a.includes(m));
    await new Promise((r) => setTimeout(r, 150 + (hash % 250))); // simulate an API call
    return {
      area,
      '5g': metro || hash % 3 === 0 ? 'available' : 'not available',
      lte: 'available',
      lte_advanced: metro || hash % 2 === 0 ? 'available' : 'limited',
      fibre: metro ? 'available' : hash % 4 === 0 ? 'available' : 'not available',
      typical_5g_speed_mbps: metro ? 250 + (hash % 300) : 80 + (hash % 120),
    };
  },
};

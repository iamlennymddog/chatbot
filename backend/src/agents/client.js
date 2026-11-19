import OpenAI from 'openai';

// OpenAI SDK pointed at Anthropic's OpenAI-compatible endpoint, so the app talks
// the OpenAI Chat Completions API while Claude stays the model provider.
export const openai = new OpenAI({
  apiKey: process.env.ANTHROPIC_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL || 'https://api.anthropic.com/v1/',
});
export const ORCHESTRATOR_MODEL = process.env.ANTHROPIC_MODEL || 'claude-sonnet-5-5';
export const SPECIALIST_MODEL = process.env.SPECIALIST_MODEL || 'claude-haiku-5-5';

import 'dotenv/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import express from 'express';
import cors from 'cors';
import pinoHttp from 'pino-http';
import { logger } from './logger.js';
import { DealsIndex } from './rag.js';
import { createOrchestrator } from './agents/orchestrator.js';
import { ORCHESTRATOR_MODEL, SPECIALIST_MODEL } from './agents/client.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_FILE = process.env.DEALS_FILE || path.resolve(__dirname, '../data/bitstalk_deals.txt');
const PORT = Number(process.env.PORT || 3001);
const MAX_HISTORY = 12;

if (!process.env.ANTHROPIC_API_KEY) {
  logger.warn('ANTHROPIC_API_KEY is not set - /api/chat will fail');
}

const index = new DealsIndex(DATA_FILE);
const chat = createOrchestrator(index);
const app = express();

app.use(cors());
app.use(express.json({ limit: '100kb' }));
app.use(
  pinoHttp({
    logger,
    genReqId: (req) => req.headers['x-request-id'] || randomUUID(),
    autoLogging: { ignore: (req) => req.url === '/api/health' },
    serializers: {
      req: (req) => ({ id: req.id, method: req.method, url: req.url }),
      res: (res) => ({ statusCode: res.statusCode }),
    },
  }),
);

app.get('/api/health', (_req, res) => res.json({ status: 'ok', models: { orchestrator: ORCHESTRATOR_MODEL, specialist: SPECIALIST_MODEL }, chunks: index.chunks.length }));

app.get('/api/deals', (_req, res) => {
  res.json(index.chunks.map((c) => ({ id: c.id, title: c.title })));
});

app.post('/api/chat', async (req, res) => {
  const { messages } = req.body || {};
  const sessionId = req.body?.sessionId ?? req.headers['x-session-id'] ?? randomUUID();
  const log = req.log.child({ session_id: sessionId });

  if (!Array.isArray(messages) || messages.length === 0 || messages.at(-1)?.role !== 'user') {
    return res.status(400).json({ error: 'messages must be a non-empty array ending with a user message' });
  }

  const history = messages
    .filter((m) => (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string' && m.content.trim())
    .slice(-MAX_HISTORY)
    .map((m) => ({ role: m.role, content: m.content }));
  while (history.length && history[0].role !== 'user') history.shift();

  const ctx = { log, sessionId, steps: [], sources: new Map() };

  try {
    const t0 = Date.now();
    const result = await chat(history, ctx);
    log.info(
      {
        event: 'chat.completed',
        duration_ms: Date.now() - t0,
        tool_calls: ctx.steps.length,
        input_tokens: result.usage.input_tokens,
        output_tokens: result.usage.output_tokens,
      },
      'Chat request completed',
    );

    res.json({
      reply: result.text,
      sources: [...ctx.sources].map(([id, title]) => ({ id, title })),
      steps: ctx.steps,
      usage: result.usage,
    });
  } catch (err) {
    log.error({ event: 'llm.error', err, status: err.status }, 'Chat request failed');
    res.status(err.status && err.status < 500 ? 502 : 500).json({ error: 'Sorry, the assistant is unavailable right now.' });
  }
});

app.listen(PORT, () => logger.info({ port: PORT, orchestrator_model: ORCHESTRATOR_MODEL, specialist_model: SPECIALIST_MODEL }, `BitsTalk Deals chatbot API listening on :${PORT}`));

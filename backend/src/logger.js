import fs from 'node:fs';
import path from 'node:path';
import pino from 'pino';

// JSON logs to stdout + logs/app.log (tailed by the Datadog Agent):
// - string "level" and ISO timestamp
// - service/env/version match DD_SERVICE/DD_ENV/DD_VERSION (unified service tagging)
// With dd-trace loaded and DD_LOGS_INJECTION=true, dd.trace_id / dd.span_id are added to
// every line for trace <-> log correlation.
const logDir = process.env.LOG_DIR || path.resolve(process.cwd(), 'logs');
fs.mkdirSync(logDir, { recursive: true });

const streams = [
  { stream: process.stdout },
  { stream: pino.destination({ dest: path.join(logDir, 'app.log'), sync: false, mkdir: true }) },
];

export const logger = pino(
  {
    level: process.env.LOG_LEVEL || 'info',
    base: {
      service: process.env.DD_SERVICE || 'bitstalk-deals-chatbot-api',
      env: process.env.DD_ENV || 'pov',
      version: process.env.DD_VERSION || '1.0.0',
    },
    timestamp: pino.stdTimeFunctions.isoTime,
    formatters: {
      level: (label) => ({ level: label }),
    },
    redact: ['req.headers.authorization', 'req.headers["x-api-key"]'],
  },
  pino.multistream(streams),
);

import fs from 'node:fs';
import path from 'node:path';
import pino from 'pino';

// JSON logs to stdout + logs/app.log with a string "level" and ISO timestamp.
const logDir = process.env.LOG_DIR || path.resolve(process.cwd(), 'logs');
fs.mkdirSync(logDir, { recursive: true });

const streams = [
  { stream: process.stdout },
  { stream: pino.destination({ dest: path.join(logDir, 'app.log'), sync: false, mkdir: true }) },
];

export const logger = pino(
  {
    level: process.env.LOG_LEVEL || 'info',
    base: { service: 'bitstalk-deals-chatbot-api' },
    timestamp: pino.stdTimeFunctions.isoTime,
    formatters: {
      level: (label) => ({ level: label }),
    },
    redact: ['req.headers.authorization', 'req.headers["x-api-key"]'],
  },
  pino.multistream(streams),
);

import fs from 'node:fs';
import { logger } from './logger.js';

// Lightweight retrieval: split the deals file into sections ("=== ... ===") and
// rank them with BM25 against the user's query. No vector DB needed for a POV.
const STOPWORDS = new Set(
  'a an the and or of to for in on with is are be i me my you your we it this that what which how can do does any some best deal deals please want need get show tell about'.split(' '),
);

const tokenize = (text) =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t && !STOPWORDS.has(t));

export class DealsIndex {
  constructor(filePath) {
    this.filePath = filePath;
    this.load();
  }

  load() {
    const raw = fs.readFileSync(this.filePath, 'utf8');
    const parts = raw.split(/^(?==== )/m);
    this.preamble = parts.shift().trim();
    this.chunks = parts.map((text, i) => {
      const title = text.match(/^=== (.+?) ===/)?.[1] ?? `Section ${i}`;
      const id = title.match(/(BT-[A-Z]+-\d+)/)?.[1] ?? `GEN-${i}`;
      const tokens = tokenize(text);
      const tf = new Map();
      for (const t of tokens) tf.set(t, (tf.get(t) || 0) + 1);
      return { id, title, text: text.trim(), tf, length: tokens.length };
    });
    this.avgLen = this.chunks.reduce((s, c) => s + c.length, 0) / this.chunks.length;
    this.df = new Map();
    for (const c of this.chunks) for (const t of c.tf.keys()) this.df.set(t, (this.df.get(t) || 0) + 1);
    logger.info({ event: 'rag.index.loaded', file: this.filePath, chunks: this.chunks.length }, 'Deals index loaded');
  }

  search(query, k = 5) {
    const qTokens = [...new Set(tokenize(query))];
    const N = this.chunks.length;
    const k1 = 1.5;
    const b = 0.75;
    const scored = this.chunks.map((c) => {
      let score = 0;
      for (const t of qTokens) {
        const f = c.tf.get(t);
        if (!f) continue;
        const df = this.df.get(t);
        const idf = Math.log(1 + (N - df + 0.5) / (df + 0.5));
        score += idf * ((f * (k1 + 1)) / (f + k1 * (1 - b + (b * c.length) / this.avgLen)));
      }
      return { chunk: c, score };
    });
    return scored
      .filter((s) => s.score > 0)
      .sort((a, b2) => b2.score - a.score)
      .slice(0, k);
  }
}

#!/usr/bin/env node
// Fetch AI / LLM / vector-DB provider logos and rasterise them to PNG so AI
// architecture diagrams (RAG, agents, LLM gateway) show real brand icons.
//
// Primary source: @lobehub/icons (the de-facto AI/LLM icon set — has OpenAI,
// Claude, Gemini, DeepSeek, Mistral, Qwen, ... which simpleicons dropped for
// trademark reasons). Fallback: simpleicons. Rasteriser: @resvg/resvg-js
// (Rust resvg — NO native system libs, works on Windows where cairosvg fails).
//
// Usage:  cd tools && npm install && node fetch_ai_logos.mjs
// Writes PNGs (256px tall, transparent) into ../assets/icons/ai/png/<key>.png.
// Re-run any time to add a logo: add an entry to MAP below and run again.

import { Resvg } from '@resvg/resvg-js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEST = path.resolve(__dirname, '..', 'assets', 'icons', 'ai', 'png');
const L = 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons';
const S = 'https://cdn.simpleicons.org';

// key -> source SVG URL. key is what a diagram references as icon "ai/<key>".
const MAP = {
  // LLM providers & models
  openai:      `${L}/openai.svg`,          // mono (lobehub has no -color for openai)
  claude:      `${L}/claude-color.svg`,    // Anthropic
  gemini:      `${L}/gemini-color.svg`,    // Google
  deepseek:    `${L}/deepseek-color.svg`,
  mistral:     `${L}/mistral-color.svg`,
  meta:        `${L}/meta-color.svg`,      // Llama
  qwen:        `${L}/qwen-color.svg`,      // Alibaba
  grok:        `${L}/grok.svg`,            // xAI
  perplexity:  `${L}/perplexity-color.svg`,
  cohere:      `${L}/cohere-color.svg`,
  huggingface: `${L}/huggingface-color.svg`,
  ollama:      `${L}/ollama.svg`,          // local models
  // managed model platforms
  bedrock:     `${L}/bedrock-color.svg`,   // AWS
  azureai:     `${L}/azureai-color.svg`,   // Azure OpenAI / AI Foundry
  vertexai:    `${L}/vertexai-color.svg`,  // GCP
  // AI-app frameworks / orchestration
  langchain:   `${L}/langchain-color.svg`,
  llamaindex:  `${L}/llamaindex-color.svg`,
  dify:        `${L}/dify-color.svg`,
  flowise:     `${L}/flowise.svg`,
  n8n:         `${L}/n8n.svg`,
  // vector databases (simpleicons where lobehub lacks them)
  qdrant:      `${S}/qdrant`,
  milvus:      `${S}/milvus`,
};

fs.mkdirSync(DEST, { recursive: true });
let ok = 0; const fail = [];
for (const [k, u] of Object.entries(MAP)) {
  try {
    const r = await fetch(u);
    if (!r.ok) { fail.push(`${k}(${r.status})`); continue; }
    const svg = Buffer.from(await r.arrayBuffer());
    const png = new Resvg(svg, { fitTo: { mode: 'height', value: 256 }, background: 'rgba(255,255,255,0)' }).render().asPng();
    fs.writeFileSync(path.join(DEST, `${k}.png`), png);
    ok++;
  } catch (e) { fail.push(`${k}(err)`); }
}
console.log(`AI logos converted: ${ok}/${Object.keys(MAP).length} -> ${DEST}`);
if (fail.length) console.log('failed (add an alternate source URL):', fail.join(', '));

#!/usr/bin/env node
// Fetch language / framework / tool logos and rasterise them to PNG for the
// tech-stack tables (every row shows a logo).
//
// Source: devicon (MIT) + simpleicons (CC0). Rasteriser: @resvg/resvg-js
// (Rust resvg — NO native system libs, works on Windows where cairosvg fails).
//
// Usage:
//   cd tools && npm install && node fetch_tech_logos.mjs
// Writes PNGs (256px tall, transparent) into ../assets/icons/data/png/<key>.png.
// Re-run any time to add a logo: add an entry to MAP below and run again.
//
// AWS / Azure / GCP service icons are NOT fetched here — they come from the
// aws/ azure/ gcp/ packs (fetch_icons / vendor architecture-icon sets).

import { Resvg } from '@resvg/resvg-js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEST = path.resolve(__dirname, '..', 'assets', 'icons', 'data', 'png');
const D = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons';

// key -> source SVG URL. key is what a proposal references as "data/<key>".
const MAP = {
  go:`${D}/go/go-original-wordmark.svg`, nodejs:`${D}/nodejs/nodejs-original.svg`,
  nestjs:`${D}/nestjs/nestjs-original.svg`, react:`${D}/react/react-original.svg`,
  flutter:`${D}/flutter/flutter-original.svg`, dart:`${D}/dart/dart-original.svg`,
  typescript:`${D}/typescript/typescript-original.svg`, vite:`${D}/vitejs/vitejs-original.svg`,
  antdesign:`${D}/antdesign/antdesign-original.svg`, opentelemetry:`${D}/opentelemetry/opentelemetry-original.svg`,
  playwright:`${D}/playwright/playwright-original.svg`, vitest:`${D}/vitest/vitest-original.svg`,
  terraform:`${D}/terraform/terraform-original.svg`, githubactions:`${D}/githubactions/githubactions-original.svg`,
  prometheus:`${D}/prometheus/prometheus-original.svg`, grafana:`${D}/grafana/grafana-original.svg`,
  docker:`${D}/docker/docker-original.svg`, apachekafka:`${D}/apachekafka/apachekafka-original.svg`,
  postgresql:`${D}/postgresql/postgresql-original.svg`, redis:`${D}/redis/redis-original.svg`,
  mongodb:`${D}/mongodb/mongodb-original.svg`, kubernetes:`${D}/kubernetes/kubernetes-plain.svg`,
  amazonwebservices:`${D}/amazonwebservices/amazonwebservices-original-wordmark.svg`,
  dotnetcore:`${D}/dotnetcore/dotnetcore-original.svg`, java:`${D}/java/java-original.svg`,
  spring:`${D}/spring/spring-original.svg`, python:`${D}/python/python-original.svg`,
  rust:`${D}/rust/rust-original.svg`, vuejs:`${D}/vuejs/vuejs-original.svg`,
  angular:`${D}/angular/angular-original.svg`, svelte:`${D}/svelte/svelte-original.svg`,
  kotlin:`${D}/kotlin/kotlin-original.svg`, nginx:`${D}/nginx/nginx-original.svg`,
  rabbitmq:`${D}/rabbitmq/rabbitmq-original.svg`, graphql:`${D}/graphql/graphql-plain.svg`,
  mysql:`${D}/mysql/mysql-original.svg`, swift:`${D}/swift/swift-original.svg`,
  helm:`${D}/helm/helm-original.svg`, elasticsearch:`${D}/elasticsearch/elasticsearch-original.svg`,
  i18next:'https://cdn.simpleicons.org/i18next/26A69A',
  // Technologies a recent bid named in its stack table with no logo to show for them.
  // Devicon carries the first three; OpenAPI and Flyway are not in devicon, so they come
  // from simpleicons with the brand colour baked into the URL.
  fastapi:`${D}/fastapi/fastapi-original.svg`, nextjs:`${D}/nextjs/nextjs-original.svg`,
  junit:`${D}/junit/junit-original.svg`,
  openapi:'https://cdn.simpleicons.org/openapiinitiative/6BA539',
  flyway:'https://cdn.simpleicons.org/flyway/CC0000',
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
console.log(`tech logos converted: ${ok}/${Object.keys(MAP).length} -> ${DEST}`);
if (fail.length) console.log('failed (add an alternate source URL):', fail.join(', '));

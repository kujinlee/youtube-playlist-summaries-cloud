# Cloud image — ONE image runs both processes (web = the standalone Next server, worker = job loop).
# Fly.io process groups (fly.toml) pick which command each machine runs. See
# docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md §5.
#
# Node 22 is REQUIRED: the worker's @supabase/supabase-js createClient needs native
# WebSocket, which crashes on Node 20 (docs/local-validation-findings.md). Re-confirmed 2026-07-19 —
# running the bundled worker on Node 20 still fails fast with "Node.js 20 detected without native
# WebSocket support", so this pin is load-bearing, not historical.
#
# MULTI-STAGE (2026-07-19). The previous single-stage image was 3.44 GB because everything the BUILD
# needed stayed in the final layer: the full 684 MB node_modules incl. dev deps, npm's cache in
# /root/.npm, TypeScript + ts-node (the worker ran through ts-node), and a `COPY . .` of the whole
# repo. None of that is needed to RUN the app. The builder stage below produces exactly two
# artifacts — Next's traced standalone server and a single-file worker bundle — and the runtime
# stage copies only those.

# ── Builder ───────────────────────────────────────────────────────────────────
FROM node:22-bookworm-slim AS builder
WORKDIR /app

# Full install (incl. dev deps): `next build` and esbuild both need them. Confined to this stage.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# `next build` emits .next/standalone — a self-contained server carrying ONLY the node_modules files
# @vercel/nft traces as reachable (78 MB, vs 492 MB for the full install). Enabled by
# `output: 'standalone'` in next.config.ts.
# The NODE_OPTIONS heap bump is scoped to this layer: next build's static-generation phase OOMs at
# the default heap for this app's route set (validated 2026-07-17). The build machine needs >4 GB.
RUN NODE_OPTIONS=--max-old-space-size=4096 npm run build

# Bundle the worker to one CJS file, so the runtime needs neither ts-node, TypeScript, nor a
# node_modules of its own. See scripts/build-worker.mjs for the externals rationale.
RUN npm run build:worker

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM node:22-bookworm-slim
WORKDIR /app

# NODE_ENV=production makes releaseGateOpen() return the compile-time const (the money gate stays
# closed until RELEASE_VERIFIED is flipped in source — see docs/reservation-release-live-gate.md).
ENV NODE_ENV=production
ENV PORT=3000
# Browsers land here rather than /root/.cache so the path is stable regardless of the running user.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# The standalone server and its traced node_modules. `server.js` defaults hostname to 0.0.0.0
# (verified in the emitted file), so Fly's external routing works without a HOSTNAME env.
COPY --from=builder /app/.next/standalone ./
# standalone deliberately omits these two — the output.md doc requires copying them explicitly.
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
# Single-file worker. Sits at the standalone root so `require('playwright')` resolves against
# /app/node_modules below.
COPY --from=builder /app/dist/worker.js ./worker.js

# File tracing includes only the playwright RUNTIME entry (a 12 KB index.js stub) — not cli.js, and
# not the .bin symlinks. Overlay the complete packages so the CLI exists, then let Playwright itself
# choose the apt packages via --with-deps. Hardcoding that OS package list would silently drift out
# of sync on every playwright upgrade.
COPY --from=builder /app/node_modules/playwright ./node_modules/playwright
COPY --from=builder /app/node_modules/playwright-core ./node_modules/playwright-core
RUN node node_modules/playwright/cli.js install --with-deps chromium \
    && rm -rf /root/.npm /var/lib/apt/lists/*

EXPOSE 3000

# Default = web. fly.toml's [processes] overrides the command for the worker group.
CMD ["node", "server.js"]

# Cloud image — ONE image runs both processes (web = `next start`, worker = job loop).
# Fly.io process groups (fly.toml) pick which command each machine runs. See
# docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md §5.
#
# Node 22 is REQUIRED: the worker's @supabase/supabase-js createClient needs native
# WebSocket, which crashes on Node 20 (docs/local-validation-findings.md).
FROM node:22-bookworm-slim

WORKDIR /app

# Install ALL dependencies (incl. dev): `next build` needs them, and the worker runs via
# ts-node (`npm run worker`), which needs typescript/ts-node/tsconfig-paths at runtime.
# (Follow-up optimization: compile the worker to JS + prune dev deps for a smaller image.)
COPY package.json package-lock.json ./
RUN npm ci

# Playwright Chromium + its OS libraries — the worker renders PDFs via playwright's chromium
# (lib/pdf/generate-doc-pdf.ts, launched with --no-sandbox). --with-deps installs the apt libs.
RUN npx playwright install --with-deps chromium

# App source + production build of the Next.js web app.
# NODE_OPTIONS heap bump is scoped to THIS layer only: `next build`'s static-generation phase
# OOMs at the default heap for this app's route set (validated 2026-07-17). Runtime processes
# are unaffected (no persistent NODE_OPTIONS). The build machine needs >4 GB RAM available.
COPY . .
RUN NODE_OPTIONS=--max-old-space-size=4096 npm run build

# Runtime env. NODE_ENV=production makes releaseGateOpen() return the compile-time const
# (money gate stays closed until RELEASE_VERIFIED is flipped in source — see live-gate doc).
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# Default = web process. fly.toml's [processes] overrides the command for the worker group.
CMD ["npm", "run", "start"]

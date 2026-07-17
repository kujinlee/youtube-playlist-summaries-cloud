# Deploy Runbook — Fly.io (web + worker) + Supabase

Roadmap M1 (`docs/roadmap-to-launch.md`). Architecture: one image, two Fly process groups sharing the
repo (`docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5). No yt-dlp/ffmpeg
(all YouTube content via Gemini's YouTube-URL ingestion); Chromium is used only for PDF export in the
worker.

## Artifacts in this repo (M1.2 — done)
- `Dockerfile` — Node 22 (worker needs it), installs Playwright Chromium + deps, `next build`.
- `fly.toml` — `web` (`next start`) + `worker` (`npm run worker`) process groups, HTTP on web only,
  `kill_timeout=120s` for graceful worker drain.
- `.dockerignore`.

## Prerequisites (M1.3 — human-gated, needs your accounts)
1. **Fly.io account** + `flyctl` installed and authed (`fly auth login`).
2. **Prod Supabase project** (separate from local dev).
3. **Gemini API key** and **YouTube Data API key**.

## Step 1 — Supabase (prod)
1. Create the project; note the **Project URL**, **anon key**, **service_role key**.
2. Apply migrations `0001`–`0020` to prod (e.g. `supabase link` + `supabase db push`, or run the SQL in
   `supabase/migrations/` in order via the SQL editor / psql).
3. Create the storage bucket **`artifacts`** (the code uses `ARTIFACTS_BUCKET='artifacts'`,
   `lib/supabase/storage-env.ts`).
4. Configure Auth (providers / redirect URLs) to match the deployed web origin.

## Step 2 — Fly app + secrets
```bash
fly apps create <your-app-name>          # then set app = "<your-app-name>" in fly.toml
```
Set secrets (injected into every machine's env — the worker reads them directly; it does NOT load a
`.env` file, per docs/local-validation-findings.md):
```bash
fly secrets set \
  NEXT_PUBLIC_SUPABASE_URL="https://<ref>.supabase.co" \
  NEXT_PUBLIC_SUPABASE_ANON_KEY="<anon-key>" \
  SUPABASE_SERVICE_ROLE_KEY="<service-role-key>" \
  GEMINI_API_KEY="<gemini-key>" \
  YOUTUBE_API_KEY="<youtube-key>" \
  STORAGE_BACKEND="supabase"
```
Optional model / tuning overrides (have sane defaults if unset): `GEMINI_SUMMARY_MODEL`,
`GEMINI_DEEPDIVE_MODEL`, `GEMINI_TRANSCRIBE_MODEL`, `PDF_MAX_CONCURRENCY`, `PREGEN_SUMMARY_HTML`.

> **Do NOT set `CLOUD_GEMINI_RELEASE_VERIFIED` in prod** — it is inert there by design. Class-A release is
> a compile-time gate (`RELEASE_VERIFIED` in `lib/gemini-failure.ts`), flipped only after the live-Gemini
> check (M1.1, `docs/reservation-release-live-gate.md`). Until flipped, failures fail-closed to KEEP (safe).

## Step 3 — Deploy (M1.4)
```bash
fly deploy
fly scale count web=1 worker=1        # ensure exactly one always-on worker machine
fly logs                              # watch both process groups boot
```

## Step 4 — Smoke test (M1.4)
On the live URL: sign in → add a playlist → generate a summary → view it → download (MD + PDF) → share.
Watch `fly logs` for the worker claiming/among completing the job. Fix any cloud-run blockers, then tick
M1.4 in the roadmap.

## Known follow-ups (not blockers)
- **Build memory:** `next build`'s static-generation phase OOMs at Node's default heap for this app's
  route set. The `Dockerfile` scopes `NODE_OPTIONS=--max-old-space-size=4096` to the build layer; the
  build machine needs **>4 GB RAM** (the Fly remote builder qualifies; a local `docker build` needs a
  Docker VM ≥ ~5 GB). Validated locally 2026-07-17 (image builds, 3.44 GB).
- Image size: the worker runs via `ts-node` so the image keeps dev deps + Chromium (3.44 GB). Compiling
  the worker to JS and pruning dev deps is a post-launch optimization.
- Local dev parity: running the worker locally needs env injected explicitly (e.g. `dotenv -e .env.local --
  npm run worker`) — the container gets env from Fly secrets, so this only affects local runs.

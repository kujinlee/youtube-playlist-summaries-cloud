# Deploy Runbook — Fly.io (web + worker) + Supabase

Roadmap M1 (`docs/roadmap-to-launch.md`). Architecture: one image, two Fly process groups sharing the
repo (`docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5). No yt-dlp/ffmpeg
(all YouTube content via Gemini's YouTube-URL ingestion); Chromium is used only for PDF export in the
worker.

## Artifacts in this repo (M1.2 — done)
- `Dockerfile` — **multi-stage** (2026-07-19). Builder: Node 22, full `npm ci`, `next build`
  (`output: 'standalone'`), `npm run build:worker` (esbuild → one CJS file). Runtime: Node 22 +
  Playwright Chromium, carrying **only** the standalone server and the worker bundle.
- `fly.toml` — `web` (`node server.js`) + `worker` (`node worker.js`) process groups, HTTP on web
  only, `kill_timeout=120s` for graceful worker drain. **These are direct `node` invocations, not
  npm scripts** — the runtime image contains neither the `next` CLI nor `ts-node`.
- `.dockerignore`.

## Prerequisites (M1.3 — human-gated, needs your accounts)
1. **Fly.io account** + `flyctl` installed and authed (`fly auth login`).
2. **Prod Supabase project** (separate from local dev).
3. **Gemini API key** and **YouTube Data API key**.

## Step 1 — Supabase (prod)
1. Create the project; note the **Project URL**, **anon key**, **service_role key**.
   **Use the "Legacy anon, service_role API keys" tab, not the newer publishable/secret keys.**
   Every test in this repo (2450 unit, 468 integration, incl. the money path and RLS isolation) ran
   against JWT-format keys, and a lot of behaviour is pinned to exact role grants — `0007` grants
   storage to `service_role`, `0020` grants *only* `select, insert` on `ledger_audit`, and
   `reservation-release.test.ts` asserts an `authenticated` client gets `42501`. Do **not** click
   *"Disable JWT-based API keys"*. See the key-migration item in the roadmap Parking Lot.
2. Apply migrations `0001`–**`0021`** to prod: `supabase login` → `supabase link --project-ref <ref>`
   → **`supabase db push --dry-run`** (read it) → `supabase db push`.
   `0021` drops-then-recreates `merge_video_data` / `persist_summary` / `update_video_annotations`,
   so **verify those RPCs are callable under an authenticated user JWT afterwards** — grants must
   survive the recreate.
   ⚠️ **Never run `supabase db reset` while linked to prod** — it drops everything. `db push` is the
   additive one.
3. ~~Create the storage bucket~~ — **not a manual step.** Migration `0007` creates the private
   `artifacts` bucket *and* both `storage.objects` policies (`artifacts_owner_rw` keyed on
   `split_part(name,'/',1) = auth.uid()`, and `artifacts_service_all`). Just verify they exist after
   the push.
4. Configure Auth to match the deployed web origin. **This app is Google-OAuth-only** — there is no
   email/password path (`app/login/page.tsx` calls `signInWithOAuth({provider:'google'})`), so
   nobody can log in until Google is configured. You need: a Google Cloud OAuth client whose
   authorized redirect URI is `https://<ref>.supabase.co/auth/v1/callback`, its client ID + secret
   pasted into Supabase → Authentication → Providers → Google, and the Site URL / redirect
   allow-list set to the deployed app origin.
5. **Keep the Supabase region and `fly.toml`'s `primary_region` in the same locality.** The worker
   makes many small round trips per job, so a cross-continent split costs ~60–70ms on each.

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
> a compile-time gate (`RELEASE_VERIFIED` in `lib/gemini-failure.ts`), not an env var.
> **Status: the gate is now OPEN** (`= true`, PR #29, 2026-07-19) after the live-Gemini verification —
> so a class-A failure RELEASES its reservation rather than keeping it. Evidence, including which
> parts are measured vs bounded vs inferred, is in `docs/reservation-release-live-gate.md`.

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
  Docker VM ≥ ~5 GB). Validated locally 2026-07-17 (image builds, 3.44 GB single-stage).
- **Image size — reworked 2026-07-19, size NOT yet measured.** ⚠️ The multi-stage rewrite is
  committed and every part that can be checked without a container build has been (see below), but
  `docker build` could not run in that session: Docker Desktop's registry pulls hang on this machine
  (`node:22-bookworm-slim` never resolves, plain `docker pull` included), and no base image was
  cached. **The first `fly deploy` — or any `docker build` on a machine with working registry
  access — is what confirms the number.** Treat the expected size as an estimate until then.
  What the rewrite removes from the runtime layer, all of which the old image carried:
  the full 684 MB `node_modules` incl. dev deps; npm's cache in `/root/.npm`; TypeScript + `ts-node`;
  and the whole-repo `COPY . .`. What it keeps: `.next/standalone` (**measured: 78 MB**, vs 492 MB
  for the full install), `.next/static` + `public` (1.5 MB), the worker bundle (**measured: 2.4 MB**),
  Chromium + its apt libs, and the Node base.
  Separately and independently measured: swapping the `googleapis` umbrella package for
  `@googleapis/youtube` took `node_modules` from **684 MB → 492 MB**.
- **Verified without a build:** standalone emits `server.js` binding `0.0.0.0` by default (so Fly
  needs no `HOSTNAME`); file tracing does include `playwright`/`playwright-core`, but only a 12 KB
  runtime stub — **not** `cli.js` — which is why the Dockerfile overlays the full packages before
  running `playwright install --with-deps`; and the bundled worker boots on Node 22 against local
  Supabase and exits cleanly on SIGTERM in ~1 s (graceful drain preserved). It still fails fast on
  Node 20 with the native-WebSocket error, so the Node 22 pin remains load-bearing.
- Local dev parity: running the worker locally needs env injected explicitly (e.g. `dotenv -e .env.local --
  npm run worker`) — the container gets env from Fly secrets, so this only affects local runs.

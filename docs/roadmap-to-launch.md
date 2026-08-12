# Roadmap to Launch — Cloud App

The path from "all capabilities merged" to "a running, unified product." Created 2026-07-17, after the
reservation-release money-path slice merged (PR #22). This is the **milestone** roadmap (not the
per-feature dev backlog — that's `docs/backlog.md`, which covers local-app style enhancements).

**Where we are:** every cloud capability is built and merged — including **M2a cloud sync (PR #23, 2026-07-19)** — auth, playlist ingest, summary +
deep-dive generation, serving, downloads, sharing, cost guardrails, and the spend_ledger reserve→release
money path. What remains is turning that into a deployed, verified, unified app.

**Three milestones:** M1 Deploy → M2 Sync → M3 Acceptance. Hardening lives in the Parking Lot (post-launch).

---

## M1 — Deploy (the app goes live) 🚀
Turn merged code into a running app a real user can reach. Highest-leverage milestone.

- [x] **1.1 Live-Gemini verification** ✅ **DONE 2026-07-19 — `RELEASE_VERIFIED = true`.**
  Full evidence: `docs/reservation-release-live-gate.md` → *Verification record*. Three live runs via
  `npm run verify:gemini-release` against Tier 1 `gemini-2.5-flash`.
  - **Fact 1 MEASURED, decisive:** 3,193 live rejections, every one a typed
    `GoogleGenerativeAIFetchError status=429`, every one routed to `'release'` by the REAL
    classifier. Zero misclassifications. (A statusless `GoogleGenerativeAIError` was correctly
    kept — the conservative direction.)
  - **Fact 2 BOUNDED, not proven zero:** a controlled pair held successes at ~1,004 while raising
    rejections 197 → 2,996; input tokens moved only 2,013 → 2,714. "Billed like successes" predicted
    8,008 → **excluded by 3×**. Residual bound **≤0.25 input tokens/rejection (~$0.000000075)** vs a
    150¢ reservation. Exact zero is not measurable — the console reported 63K vs 118K output tokens
    for identical success counts.
  - **503 INFERRED, never observed** — a burst can only provoke 429. `RELEASE_STATUSES` still covers
    both; narrowing to `{429}` was considered and rejected because 503 is Gemini's *classic outage*
    response, i.e. the very case this gate exists to fix.
  - **User decision:** accept "bills nothing *material* relative to the reservation" rather than
    "exactly zero" — exact precision is short-lived against vendor pricing that changes. Durable
    answer = periodic recalibration, filed in the Parking Lot.
  - Regression: reservation-release 32/32 **twice with no DB reset**, full integration 65 suites /
    468 tests, 2450 unit, tsc clean.
  - ⚠️ **Still closed:** `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` (`lib/gemini.ts`) — a *different*
    premise (worst-case audio-fallback transcription cost), NOT verified by this session.
- [x] **1.2 Deploy config** *(written + `docker build`-validated 2026-07-17; image builds, 3.44 GB)*.
  `Dockerfile` (Node 22 + Playwright Chromium + `next build`), `.dockerignore`, `fly.toml` (web + worker
  process groups, HTTP on web only, `kill_timeout=120s`), runbook `docs/deploy.md`. Worker **graceful
  drain already existed** (SIGTERM/SIGINT → AbortController → clean loop exit, `worker/main.ts`); Node 22
  pinned per the supabase-js native-WebSocket finding. tsc clean. **Build finding:** `next build`'s
  static-generation phase OOMs at default heap → fixed with a build-layer `NODE_OPTIONS=--max-old-space-size=4096`
  (build machine needs >4 GB; the Fly remote builder does). Follow-up: 3.44 GB image (dev deps + Chromium)
  → compile worker to JS + prune dev deps later. **→ Done 2026-07-19 on branch `chore/shrink-deploy-image`
  (multi-stage + standalone + bundled worker), but the resulting SIZE is still unmeasured — `docker build`
  could not run in that session. See "Shrink the deploy image" under NEXT ACTIONS.**
  *Actual `fly deploy` is 1.3/1.4 (needs your accounts).*
- [x] **1.3 Provision prod infra** — ✅ **DONE 2026-07-21.**
  Prod Supabase project `uykwcybxqgewmbltroxf` (AWS `us-east-1`; **legacy JWT keys**, not
  publishable/secret — see Parking Lot). Secrets go into `fly secrets` at 1.4, not a file.
  - [x] **Migrations 0001–0021 applied + verified** (`supabase db push`; `migration list` shows
    local==remote through 0021). Post-apply checks all passed: the three RPCs `0021` recreates
    (`merge_video_data`/`persist_summary`/`update_video_annotations`) are callable under an
    authenticated JWT (grants survived the drop-recreate); `artifacts` bucket is private with both
    `storage.objects` policies; `exec_sql` is `anon=false authenticated=false service_role=true`.
  - [x] **RLS verified on every table** (`rls_on=true, rls_forced=true` for all 12). This mattered
    because **hosted Supabase auto-grants full DELETE/INSERT/UPDATE on public tables to
    `anon`/`authenticated`** — its standard permissive-grant model — which local `supabase start`
    does NOT do. So the prod grant list looks alarming (`ledger_audit` shows anon/authenticated with
    full privileges) but RLS is the real gate: `ledger_audit`/`spend_ledger` are `rls_forced` with
    `policies=0`, so session clients are denied while `service_role` writes via `BYPASSRLS`. The
    money-path guard test was already written to accept either a permission error OR zero rows, so it
    holds identically under prod's RLS-denial and local's missing-grant. **Anyone re-running the
    grant check and panicking: check RLS, not grants.**
  - [x] **Google OAuth configured 2026-07-21.** Client `yps-supabase`
    (`373870827220-ej77r0ako1q1h4ktvtm459idiu3eak6u`), redirect URI
    `https://uykwcybxqgewmbltroxf.supabase.co/auth/v1/callback`; Supabase Google provider enabled,
    Site URL + `/**` redirect set to `https://youtube-playlist-summaries.fly.dev`. **Nonce checks
    ON** in prod (local keeps them off). Real sign-in only testable once deployed (1.4).
  - Fly app **`youtube-playlist-summaries`** reserved (`fly apps create`); `fly.toml` app name + iad
    region set (PR #30).
- [x] **1.4 Deploy + smoke test** — ✅ **COMPLETE 2026-08-11** (all A + B items; see [`docs/m1.4-finishup-checklist.md`](m1.4-finishup-checklist.md)). **CORE DONE 2026-07-22; APP LIVE at
  https://youtube-playlist-summaries.fly.dev.** Deployed (Fly iad, image 471 MB, web+worker).
  Core journey VERIFIED live: OAuth sign-in → add playlist (`/api/jobs` → durable queue) → worker →
  Gemini → stored → **rendered summary with section timestamps**. Guardrail correctly capped spend
  (prod `daily_cap_cents` was 500¢ at deploy: 3 of 9 queued, 6 blocked — working as designed; **later
  raised to 5000¢, verified live 2026-07-23** so full playlists flow). Owner signup locked
  OFF after account creation. **3 cloud-run blockers found + fixed (PR #31, all build-time-vs-runtime):**
  NEXT_PUBLIC absent at build (→ [build.args] + fail-build guard); OAuth callback → 0.0.0.0:3000
  (→ x-forwarded-host); root page baked static-LocalApp at build (→ force-dynamic).
  **Redeploy 2026-07-29 (release v5):** shipped the share pre-warm fix (backlog #14, PR #37) —
  share-before-view no longer 503s. Post-deploy checks green: image 471 MB, `/dev-login`→404 (gate
  closed), `/login`→200. **Download verified working (user, 2026-07-28).** **Share-before-view
  VERIFIED working live against v5 (user, 2026-07-29)** — the link served once the owner minted it
  with the new code. Caveat surfaced: a tab open *across* the deploy runs stale JS and needed a hard
  refresh → filed backlog #16 (app-wide "new version available" banner); #15 removes the
  share-specific instance.
  **Redeploy 2026-08-11 (release v6) — 45 commits, the largest gap yet.** Shipped the two slices that
  were merged but protecting nothing: **#46 serve-path bounding** (PR #67 — its durability half lives
  in migrations `0024`/`0025`, so the app half alone would have been *worse* than either end state)
  and **PR #42 serial coherence** (whose migration `0023` had gone unapplied since 2026-08-03).
  Migrations pushed first; see *Prod schema reconciliation* below. Post-deploy green: `/login`→200,
  `/dev-login`→404 (gate closed), both machines on one digest, Next.js 16.2.6 booted, worker running,
  zero boot errors. Investigated and cleared: `/api/version`→401 not 404 — **no such route exists**
  (backlog #16 would add it) and the middleware auth-gates `/api/*` before routing can 404, which is
  the fail-closed direction.
  **Still to do in 1.4 → actionable checklist: [`docs/m1.4-finishup-checklist.md`](m1.4-finishup-checklist.md)**
  (a) ~~download~~ ✅ ~~share-before-view~~ ✅ (live, v5); (b) raise prod
  `daily_cap_cents` if the owner wants full playlists; (c) the 5 cloud-sync checks below.
  Original checklist retained:
  → add playlist → generate summary → view → download → share); fix any cloud-run blockers.
  **Cloud-sync verification (M2a) folds in here** — all 46 cloud-sync integration tests run against the
  LOCAL Supabase stack (`supabase/config.toml`: TLS disabled, pooler disabled, no network), so transient
  storage failures essentially never occur there. That is precisely the root-cause class M2a was built to
  survive, so it is untested by construction until a hosted project exists. Run these against real
  Supabase, in this order:
  **➜ These live in [`docs/m1.4-finishup-checklist.md`](m1.4-finishup-checklist.md) §B (B1–B5) and
  nowhere else.** This file used to carry a second, differently-worded copy of all five; it drifted, and
  on 2026-08-11 the copy still showed the serve-doc money item **ticked `[x]` as "CONFIRMED and FIXED"**
  while the checklist's B3 was failing against hosted infra. Two copies of a gate means one of them is
  lying and nobody can tell which. Status as of 2026-08-11: **B1 ✅ B2 ✅ B5 ✅ (by replacement),
  B4 ✅ (decided *tolerate*, then passed — PR #76), B3 ❌ FAILED — a real defect, see the checklist.**

### Prod schema reconciliation — 2026-08-11

**This document said prod was verified "through 0021". Prod was actually at 0022, and three
migrations were unapplied.** Read live via the read-only `claude_ro` role, not inferred from files.

- **`0022` had been applied out-of-band and recorded nowhere.** Harmless in itself — but the same
  blind spot is why **`0023` sat unapplied for eight days** after the serial-coherence slice merged
  (PR #42, 2026-08-03). Prod ran without the phantom-serial fix for that whole window and every
  document here read as "merged, done". **Reconciliation covers git and files; it does not and
  cannot cover live infrastructure.** The only defence is to read the running system, so a migration
  applied by hand must be recorded here *at the moment it is applied*.
- **`0023`/`0024`/`0025` applied 2026-08-11** (`supabase db push --linked`). `migration list` now
  reports local == remote for all 25.
- Safety was established against the live catalog *before* pushing, and re-verified after:
  `claim_video_slot` has **both** the 2-arg wrapper and the 3-arg form with identical return tables
  (so in-flight old instances keep resolving); `guardrail_config_lease_ttl_covers_serve` is present
  and `lease_ttl_seconds` is still **180** — above the 161 floor, so `0024`'s fix-up `UPDATE` was a
  no-op on prod (it was *not* local, which sat at 30 and refused the migration);
  `settle_serve_model(uuid, boolean) → boolean` unchanged, so `create or replace` succeeded.
- Live `guardrail_config` recorded for the next session: `daily_cap_cents=5000`,
  `magazine_est_cents=6`, `max_serve_attempts=5`, `summary_max_attempts=1`, `dig_max_attempts=2`.
- **The push printed a `pgdelta` certificate stack trace and still succeeded** — that is the CLI
  failing to cache its own local catalog snapshot, not a database error. It was treated as
  unproven either way and settled by querying `pg_catalog` directly.

**M1 done = a real URL a user can log into and use.**

---

## M2 — Sync (unify local + cloud, Stage 3) 🔗
The original two-project vision: local and cloud coexist, **newer-wins** reconciliation. Branch
`feat/stage3-cloud-sync` (off the M1 branch; rebase onto master once M1 merges).

**Decomposed (design approved 2026-07-17):**
- **M2a — this slice:** local→cloud push + cloud→local pull of **metadata + docs**, per-video newer-wins
  (`docVersion` → portable `contentGeneratedAt` → `contentHash`), **additive** deletes, Supabase-Auth login,
  local per-playlist sync manifest, manual **Cloud Sync** trigger. Spec:
  `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`.
- **M2b — later slice (own spec):** image/slide-asset backfill (both directions), tombstone delete
  propagation, background/auto-sync, true-conflict loser-preservation.

  **M2b acceptance test (defined 2026-07-24, from a hands-on walk-through):** the concrete "done"
  scenario for the cloud-text → local-assets vision —
  1. **Cloud generates a dig-deeper** (against real or local Supabase). Per `dig-handler.ts:115` it is a
     *text-only slice*: `[[SLIDE:…]]` tokens are preserved **unresolved** (no images) — this is expected.
  2. **Sync carries the dig-deeper doc** cloud→local. **← the M2a gap this slice closes.** Today
     `sync-run.ts:128` copies **only the `summaryMd` blob** ("Keep ONLY artifacts.summaryMd"); the
     `digDeeperMd` blob (the "second artifact kind", deferred finding Claude-R2-M1) does NOT transfer.
     M2b must sync `digDeeperMd` (and other artifact blobs) between replicas, healing the pointer/blob
     split.
  3. **Local backfills slide assets** — resolve `[[SLIDE:…]]` → cropped video frames via ffmpeg
     (`lib/dig/slide-crop.ts`, `slides.ts`). Requires the **source video fetched locally** (backlog #8
     "downloadable video + ffmpeg"). This is the "images" step — they are **slide crops**, not
     AI-generated infographics.
  4. **Assets sync back** local→cloud so the cloud doc gains the images too (backfill *both directions*).
  **Done = a dig-deeper generated text-only on the cloud, synced to local, enriched with slide images
  locally, and those images propagated back to cloud.** The pieces exist in isolation (cloud dig-gen ✅,
  slide-crop code ✅); M2b is the connective tissue — dig-doc blob sync + orchestrated local video-fetch
  → ffmpeg backfill + asset sync-back.

- [x] **2.1 Brainstorm + spec** (M2a) — design user-approved; spec `…2026-07-17-stage3-cloud-sync-design.md`
  **v10 CONVERGED** (two-class model; commit bbc5991). **User-approved 2026-07-17.**
- [x] **2.2 Plan** — `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md` **v6 CONVERGED**
  (dual adversarial review, **6 rounds**, Codex + Claude independent; round 6 both 0 B/H/M; trend
  Blocking 4→0→0→0→0→0, High 3→5→2→1→1→0; commit 16ffb99). 14 TDD tasks. Reviews saved
  `docs/reviews/plan-cloud-sync-m2a-{codex,claude}-r{1..6}.md`.
- [x] **2.3 Implement** (subagent-driven-development) — all 14 TDD tasks committed, each per-task
  dual-reviewed clean. 2421 unit / 245 suites; cloud-sync integration 4 suites.
- [x] **2.3b Whole-branch dual review to convergence** — **CONVERGED at round 7** (both reviewers,
  independent; round 7 was a focused pass on the round-6 delta). Final: `15c32bd` + doc correction.
  Reviews `docs/reviews/whole-branch-cloud-sync{,-v2,-v3,-v4,-v5,-v6}-rereview-{codex,claude}.md` +
  `whole-branch-cloud-sync-v7-focused-{codex,claude}.md`.
  | Round | Findings | Fixed in |
  |---|---|---|
  | R1 | 1 Blocking + 2 High (WB-B1/H1/H2) | `32a164c` |
  | R2 | 2 High + 3 Med (H-R2-2 was a *regression from the R1 fix*) | `1f54c60` |
  | R3 | **1 Blocking** (B1) — Codex said CONVERGED, Claude caught it | `3bc8cc7` |
  | R4 | 3 High (H2 a *regression from the B1 fix*; H1/H3 pre-existing) | `66fe6e5` |
  | R5 | 1 High — found independently by BOTH reviewers — + dead-code removal + 1 Low | `12c850d` |
  | R6 | 1 defect filed High (Codex) / Low (Claude), adjudicated → fixed; 1 Medium | `15c32bd` |
  | R7 | focused pass on the R6 delta — **both reviewers CONVERGED**, 0 Blocking/High | — |
  Trend Blocking 1→0→1→0→0→0→0, High 2→2→0→3→1→1→0. Rounds 1–4 did not converge monotonically —
  each sharper prompt surfaced pre-existing defects earlier rounds walked past — then R5–R7
  converged: R5's single High was found by both reviewers independently, R6's sole defect was a
  severity dispute over a known issue, R7 found nothing. Root cause of
  B1/R4-H1/R4-H3 is one shared shape: *a value meaning "absent" is also what a failure produces*
  (`SupabaseBlobStore.get` swallows every error; `playlist_title ?? null`).
- [x] **2.4 Merge** — ✅ **MERGED to master 2026-07-19, PR #23, merge commit `d2bf143`** (52 commits, 86 files). Branch deleted.

**M2a deferred findings** (carried past the 2.4 gate deliberately — none blocking; revisit alongside the honest-blob-read slice):
- **Claude-R2-M1** — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
  (`sync-run.ts` artifacts deep-merge). Latent until a second artifact kind is populated.
- **Codex-R2-Med** — absent (`undefined`) companion scalars are not explicitly cleared on transfer,
  so a winner lacking `tldr`/`takeaways`/`tags` leaves the loser's stale values in place.
- **Claude-R3-M1** — `build-doc-html` derives `base` from `digDeeperMd` in preference to `summaryMd`,
  so when replica keys diverge (`serialNumber` is replica-local) the dig-deeper view serves the
  pre-sync summary. Stale-but-coherent; fix lives outside sync.
- **M-R7-1** — the companion freshness guard judges a CLOUD receiver against the LOCAL
  `GENERATOR_VERSION`. Correct for `copyToLocal` (local constant IS the receiver's); inert for
  `copyToCloud` under deploy/checkout skew, where the sender may still be shipped and 503 a
  rendering share. NOT a regression (the pre-guard code shipped unconditionally). Closing it needs
  the cloud to expose its effective `GENERATOR_VERSION` (no endpoint today, not carried in any synced
  artifact). Worth evaluating in that slice: the simpler rule *never overwrite a receiver matching the
  winner hash* may strictly dominate, since a sender envelope fresh by the sender's constant is not
  necessarily fresh by the receiver's.
- **L-R6-2** — `noop + shareNeedsOwnerServe: false` under-reports a matching-hash but
  version-skewed receiver model. Same family as M-R7-1: the sync run cannot fully reason about a
  remote serving environment's freshness. Condition predates the sync.

**M2a done = second device hydrates from cloud + local research publishes to the shared portal (minus
slide images); M2 done = full bidirectional incl. images.**

---

## M3 — Acceptance (prove it end-to-end on the deployed app) ✅
- [ ] **3.1 Browser-level Playwright cloud e2e** against the deployed URL — full user journey (not mocks).
- [ ] **3.2 Real-render / regenerate checks**: regenerate `9nh8TQRcYD0` to confirm the summary
  section-timestamp guarantee live; verify cloud dig-serve render.
- [ ] **3.3 Final acceptance sign-off.**

**M3 done = verified the whole journey works in production.**

---

## Process & documentation integrity (added 2026-07-30, PR #38)

Not a feature slice — this is the machinery that stops hard-won lessons from decaying.

- [x] **Phase 6 — per-milestone architecture review** adopted in `docs/dev-process.md`. First run:
  `docs/reviews/architecture-review-2026-07-30.md` — 7 composition findings + 4 verified defects
  (one on the money path). Per-task review is structurally blind to these.
- [x] **Finding #3 — `InMemoryBlobStore`.** The storage seam is now the test surface; the adapter
  models BOTH shipped `promote()` semantics because they genuinely disagree.
- [x] **CI** (`.github/workflows/ci.yml`) — `tsc`, the unit suite, the `service_role` confinement
  guard, and documentation integrity, on Node 22. Free (public repo). First run exposed that
  `npm test` was never hermetic: it silently required `ffmpeg`.
- [x] **Branch + PR is the standard path**, keyed on blast radius, not size.
- [x] **ADR-0005** — the hosted product never downloads YouTube video (ToS). Recorded because the
  decision lived only in a Draft spec and was misread by the very review that reads `docs/adr/`.
- [x] **`scripts/check-docs.py`** — ADR index drift, dangling ADR refs, broken living-doc links;
  advisory list of spec decisions never promoted. Code→ADR references went 0 → 2.
- [ ] **Triage the 19 spec docs** holding decision markers with no ADR (the advisory list).
- [x] **Branch-rule enforcement** — `.claude/hooks/block-default-branch-push.sh` (PR #39). Denies a
  push to the default branch; allows it when no remote exists. 15 verified cases + proved live.
  The first mechanism here that *constrains* rather than reminds.
- [ ] **Backlog #18(b) — give `grill-with-docs` a trigger.** The rule for promoting decisions was
  never missing; the skill that applies it went dormant. **This is the open root cause.**
- [x] **README coverage** — CI, ADRs, roadmap/backlog links and the maintenance scripts (done by hand
  2026-07-30). **The check that keeps it true is NOT built** — see the open item below.
- [ ] **README-coverage check** in `scripts/check-docs.py`: every `scripts/*.py|*.sh` and every
  `.github/workflows/*.yml` must be mentioned in `README.md`. Fixing the content by hand does not
  stop it drifting again; only the check does.
- [x] **Roadmap internal-consistency check** — ✅ **BUILT 2026-08-12** (`scripts/check-roadmap-consistency.py`, in CI, `--self-test` 15/15). Verified against the real defect: run on master's roadmap before the fix it reports 5 findings; the first implementation matched cue and identifier on the SAME line and reported that same file CLEAN, because the sentence wraps — so it now scans paragraph units, with that exact shape pinned as a regression case. *replaces a rejected proposal.* The original idea was
  "fail if `master` moved N commits since the roadmap changed." **That would not have worked:** when
  measured on 2026-07-30 the roadmap *was* being edited regularly (PR #32 on 07-22, all M1 checkboxes
  current) — the rot was a **summary block inside an actively-maintained file**, still naming M1.3 as
  "the single remaining blocker" nine days after its own checkbox was ticked two screens above. A
  recency check reads green throughout. Build the consistency check instead: flag when a step named
  as blocking in *NEXT ACTIONS* has a `[x]` checkbox elsewhere in the file. Lesson: **staleness lives
  inside frequently-edited files; recency is the wrong signal.**
- [ ] **Shrink `docs/dev-process.md`** — it is always loaded via `CLAUDE.md`, and grew **347 → 412
  lines during a single session (2026-07-30)** — the same session that diagnosed *dilution* (rules
  present but unapplied) as its failure mode. `docs/process-rationale.md` already exists for
  evidence, yet 3 inline `**Why:**` narratives remain in the process doc. Move them; leave the
  operative rules scannable. **Guiding principle: every hard-won lesson should become a check, a
  checklist item, or a hook — prose is the fallback, not the default.** Of six mechanisms proposed
  on 2026-07-30, five went unbuilt and the only thing added was prose.

## Dev-infrastructure debt (NOT tied to any feature slice — survives every merge)

**STATUS: two open items (`exec_sql` 2026-07-20; an UNIDENTIFIED unit-suite flake 2026-07-30).**
`middleware-2a` red suite FIXED 2026-07-23 · integration-vs-migrations FIXED 2026-08-04 (PR #46) ·
the two 2026-07-19 items are CLOSED.

- [x] **`npm run test:integration` does not apply pending migrations — the gate fails OPEN.** ✅ **FIXED 2026-08-04.**
  `tests/integration/global-setup.ts` runs `supabase migration up` once per suite (jest `globalSetup`, not
  `setupFiles`, which fires per test file). A no-op costs ~4.6 s against a ~160 s suite. If anything WAS
  pending it warns loudly, because that means every earlier run on that machine tested the wrong schema.
  If migrations cannot be applied it **refuses to run** rather than reporting a green suite that proves
  nothing — verified by mutation (0 tests execute). Original entry below for the record.
  **Found 2026-08-03 on `fix/serial-coherence-sync`.** The branch adds `0023`, but the local DB still
  had only the pre-0023 schema, so the whole integration suite had been running against the OLD
  `claim_video_slot` and reporting green. Applying it by hand (`npx supabase migration up`) turned up
  **two real failures immediately** — one test pinning the very phantom-serial bug 0023 fixes, one
  stale key assertion (see A7 in the serial-coherence slice).
  This is the dangerous shape: not a red suite someone learns to ignore, but a **green** one that is
  not testing the code under review. A migration is exactly when the suite matters most, and exactly
  when it silently stops applying.
  **Fix:** run `supabase migration up` (or a `db reset`) in the integration global-setup
  (`tests/integration/setup.ts`), so the schema under test always matches the branch. Cheap; the only
  question is reset-vs-up given suite runtime (~170 s) and the idempotency requirement.
  **Until then:** apply migrations by hand before trusting a green integration run on any branch that
  adds one.

- [ ] ⚠️ **One unit test failed once, then passed 4× in a row — identity UNKNOWN (2026-07-30).**
  Observed while gating the D5–D7 batch: `npm test -- --ci` reported `1 failed, 251 passed / 1 failed,
  2516 passed` on the first run, then **4 consecutive fully-green runs** (252 suites / 2517 tests).
  **The failing test's name was not captured** — the run was piped to `tail`, which discarded the
  failure block, and it has not reproduced since. That is a process error worth naming: *always
  capture the full log when a suite may fail.*
  **Why this is recorded rather than waved off:** `docs/dev-process.md` makes the full-suite step
  satisfiable only while every red suite is **explicitly named**. This one cannot be named, so the
  gate is met on the 4 green runs but the debt is real — an intermittent failure is exactly what
  makes "confirm no regressions" unfalsifiable later.
  **Trigger:** the next time any unit run goes red, capture `> /tmp/run.log 2>&1` in full and grep
  for `✕`/`●` before doing anything else. If it recurs and names itself, promote to a real entry.

- [x] **`middleware-2a.test.ts` — 2 OAuth-callback tests were RED on `master`.** ✅ **FIXED 2026-07-23.**
  Was pre-existing since `1c96e62` (PR #31 OAuth `x-forwarded-host` fix): `publicOrigin` reads
  `request.headers.get('x-forwarded-host')`, but the test's `callbackReq()` mock built a request with
  no `headers` (hidden by an `as never` cast) → `Cannot read properties of undefined (reading 'get')`.
  Test-only (real OAuth was verified live in M1.4). Fix: `callbackReq()` now supplies a real `Headers`
  (with optional entries), **plus** a new regression test covering the behind-a-proxy branch — the exact
  `0.0.0.0:3000` incident PR #31 fixed, which previously had ZERO coverage (mutation-checked: it goes red
  if `publicOrigin` ignores `x-forwarded-host`). Full integration suite now **469 pass / 0 fail**, tsc clean.

- [ ] **`exec_sql(sql text)` is a test-only helper that ships to production.**
  **TRIGGER: before the app is reachable by anyone but the owner (i.e. before M1.4 opens sign-ups).**
  Migration `0004` creates a `security definer` function that executes arbitrary interpolated SQL,
  granted to `service_role` only and correctly denied to anon/authenticated (verified in prod:
  `anon=false authenticated=false service_role=true`). It has **zero production callers** — only 8
  integration test files use it. Residual risk: anyone holding the `service_role` key can run
  arbitrary SQL as the function owner, including statement injection past the wrapper
  (`select 1) t; drop …; --`) — an *escalation* beyond service_role's already-broad access, on a
  money-handling DB. Accepted for now (user, 2026-07-20 — option (c)): no deploy, no users, no data
  yet, and the exposure requires an already-compromised service_role key. **The fix** is a new migration
  (`0022` is now taken by `dig_max_attempts` → use `0023`+)
  that drops `exec_sql`, plus moving its creation into integration-test setup so it never exists in
  prod. Touches 8 test files' setup, so it wants its own PR + review, not a mid-deploy rush.

Filed separately on purpose: these were previously buried in the M2a deferred list, which becomes
historical the moment M2a merges. They are neither M2a findings nor blocked by it.

**Every item carries a TRIGGER — the event that will actually surface it.** A debt list without
triggers is a wish list: nothing in the workflow reads a prose section, so items rot there
indefinitely (the Parking Lot below is the standing evidence). A trigger ties the item to something
that fires anyway, so it resurfaces without anyone remembering it exists.

- [x] **`tests/integration/reservation-release.test.ts` fails on a clean tree.** ✅ **FIXED 2026-07-19**
  (branch `fix/reservation-release-self-poisoning`, commit `c8be696`).
  **The recorded root cause was wrong, and the wrong diagnosis is why it sat unfixed.** This entry
  used to read "local Supabase state pollution — leftover rows from other suites … needs a DB reset
  between runs", which framed it as an *infrastructure* chore nobody owned. In fact the suite
  **poisons itself**: it writes rows it never cleans up, then asserts on them with globally-scoped
  queries. Proven by double-run on a freshly reset DB with no code change between — run 1 32/32
  green, run 2 three failures. That makes it a *test-correctness bug in one file*, which is a small
  permanent fix rather than an ops burden. Two mechanisms, two different fixes:
  - `spend_ledger` / `jobs`: it was the only money-path suite asserting on these global day-keyed
    tables **without** a `beforeEach` wipe (it had only `beforeAll(ensureGuardrailHeadroom)`, a
    config guard that deletes no rows). Added the wipe every other money suite already uses. Also
    fixes behavior 23, which claims by a **fixed literal** `p_video_id` and so received a leftover
    queued job from an earlier run.
  - `ledger_audit`: **cannot be wiped, and must not be.** Migration `0020:22` grants service_role
    only `select, insert` — it is a money-path audit log and Task 1 exists to prove that lockdown.
    A delete there does not error, it silently affects zero rows. *The append-only property under
    test is exactly why the suite cannot clean up after itself.* Both assertions were instead
    **scoped** to a per-run discriminator (a fresh uuid note; the `'fail_job '||job_id` note the RPC
    already stamps), making them indifferent to accumulated rows.
  **Why it survived review:** it passes on every *first* run, including CI on a fresh container.
  Red-only-on-a-second-run looks environmental from inside CI and looks like someone else's mess
  from the developer's chair — neither vantage point sees the accumulation.
  **Verified** (no DB reset between any of these): suite ×3 consecutive on a deliberately polluted
  DB → 32/32 each; **full integration ×2 back-to-back → 65 suites / 468 tests each**; unit 245/2450;
  `tsc` clean. The full integration suite is now **idempotent across runs**, which also confirms this
  was the only self-poisoning file.
- [x] **`scripts/codex-frontier-model.py` can select an unrunnable model.** ✅ **FIXED 2026-07-19**
  — `scripts/codex-review.py`, converged over **5 adversarial rounds** (reviews
  `docs/reviews/codex-dispatch-wrapper-codex{,-v2..v5}.md`; round 5: 0 Blocking/High/Medium).
  The picker is unchanged and unchangeable — re-verified that the cache carries no
  minimum-client-version field across every key of all 7 models — so the fix lives at the point of
  use: the wrapper walks all candidates (`gpt-5.6-sol → -terra → -luna → gpt-5.5` today) and exits
  **non-zero** if none produces a review, so the caller learns the gate did not run.
  **Success is decided solely by whether `codex exec -o/--output-last-message` wrote a substantive
  final-message file** — not the exit code, not stdout.
  Three things worth remembering, each found by a review round rather than by reasoning:
  - **The documented exit-0 claim was wrong.** A direct `codex exec` on a rejected model exits **1**;
    the exit-0 report comes from the plugin's background-task path. `docs/plugins.md` is corrected.
  - **The first design was unwinnable and was abandoned, not patched.** Parsing stdout cannot work:
    `codex exec` multiplexes banner, echoed prompt, tool transcript, and reply onto one stream, so a
    review that *quoted* an error was indistinguishable from a run that *hit* one, and every regex
    fix grew a mirror bug on another channel (one extracted "review" reached 308 KB of transcript).
  - **`ABORT` was deleted rather than fixed.** Rounds 3 and 4 found the same false-abort through two
    different matchers; removing the early-exit branch removed the class, at the cost of a few
    fast-failing attempts. stdout can now influence what the wrapper *says*, never what it *does*.
  Original description of the defect, kept for context:
  **TRIGGER: every adversarial review.** Mitigation is already enforced in `docs/plugins.md` (FAIL
  OPEN — read the output FILE, never the exit code), so the gate cannot silently no-op today. What
  remains is the permanent fix. Note the picker *cannot* be made smarter from the cache alone: it
  already filters `visibility == "list"` and `supported_in_api`, and the cache carries no
  minimum-client-version field. So the fix belongs at the point of use — a dispatch wrapper that
  detects the HTTP 400 / findings-free output and retries with the next candidate by priority,
  exiting non-zero if no candidate produces a real review. It ranks by `priority`
  without filtering on what the pinned Codex CLI supports; on 2026-07-18 it returned `gpt-5.6-sol`
  → HTTP 400 → a review file containing only an error, with **exit code 0**. The adversarial gate
  can therefore silently no-op. Filter by client-version support, and/or fail loudly on an empty
  review. Interim workaround: `codex exec -m gpt-5.5`, and always read the output FILE (see the
  FAIL OPEN note in `docs/plugins.md`).

---

## Serial coherence in cloud-sync — ✅ MERGED (PR #42, `f8703bc`, 2026-08-03)

**Why it exists:** tracing architecture-review finding #2 surfaced a **live data-loss bug**. `base` =
`<serial>_<slug>` addresses every derived blob (`models/<base>.json`,
`dig/<base>/<sectionId>.r<V>.md`) and dig content is **paid Gemini output**. Sync recomputed
`serialNumber` on the receiver while copying the sender's `summaryMd` KEY verbatim, so rows said
`serialNumber: 9` beside a file named `003_alpha.md` and the paid blobs were silently orphaned — no
error, no report, no cleanup. Divergence was routine, not hypothetical: both replicas allocate
`max + 1` in their own ingestion order and no migration constrains uniqueness.

**Status: implemented, dual review in progress (round 3 dispatched). NOT merged. No PR yet.**

- [x] **A0** behaviors table (33 rows) + Codex review of the table
- [x] **A4** `copy` at the `BlobStore` seam — ONE shared `copyBlob`, all three adapters delegate.
      Deviation from plan: `copy`, not `rename` — Supabase `move()` is copy+delete and non-atomic,
      and nothing is atomic across N objects, so a destructive rename bakes an unrecoverable
      ordering into the seam.
- [x] **A1** receiver adopts the sender's serial (`claimVideoSlot(p, id, desiredSerial?)`, migration
      0023); a collision **aborts and reports** that video. Fixed two phantom-serial bugs on the way,
      one per adapter — both returned a COMPUTED serial rather than the persisted one.
- [x] **A2** stop overwriting `playlistIndex` with a storage row ordinal
- [x] **A3** `lib/cloud-sync/reconcile-serial.ts` — repair an already-diverged base before
      `transferClassA` writes the winner's key onto the loser. Deviation from plan: reconciles the
      full **base**, not only the serial (the slug diverges on its own), and does NOT reuse
      `serial-migrate.ts`, which solves backfill rather than relocation and never touches digs.
- [x] **A5** regression guard: derive the base from the row after a sync, and the paid dig is there
- [x] **A-review** — **5 rounds done.** Round 5 found (a) a relocation branch with ZERO unit
      coverage, caught by mutation — replacing `describeDivergence`'s no-local-MD fallback with
      "never diverged" left all 2582 unit tests GREEN; 4 tests added, mutant now kills 2; and
      (b) one High, **deferred by explicit decision** to `docs/backlog.md` #17 (fence the worker
      persist). Trail: `docs/reviews/task-A-serial-coherence-branch{,-v2,-v3,-v4,-v5}-*.md`.
      R1: 3 Codex (2H/1M) + 2 coordinator. R2: 1H/1M/1L Codex + 2 coordinator. R3: 1H/1M/1L.
      R4: 1H/2M. Zero Blocking in any round. **Convergence = a full round with no new
      Blocking/High.** Every fix is mutation-checked, and 4 separate mutations found guards that
      no test covered — each became a test.
      Reviews: `docs/reviews/task-A-serial-coherence-branch{,-v2,-v3,-v4}-rereview-codex.md`,
      each with a coordinator adjudication section (2 findings were downgraded on evidence, 1
      suggested fix was replaced with a stricter one, 1 suggestion was declined with reasons).
      **Known gap, named not hidden — sync has no mutual exclusion against the WORKER.** Every sync
      metadata write is unconditional (no compare-and-swap), so a concurrent writer's change can be
      lost or overwritten.
      **The primary trigger is not a second sync.** `runSync` has exactly one caller —
      `scripts/cloud-sync.ts` (`npm run cloud-sync`), a manual CLI with no lock — so two *syncs*
      colliding needs two machines on one cloud account, deliberately, with the overlap landing
      inside one video's copy phase. Thin on its own. The reachable collision is
      **`lib/job-queue/summary-handler.ts:156-157`**, which writes *both* `serialNumber` and
      `summaryMd` when a summary job completes: one sync + an ordinary cloud ingest or re-summarize
      running in the worker, no second device and no deliberate action.
      *(Corrected 2026-08-02 — the original entry named two concurrent syncs as the trigger and
      undersold reachability.)*
      Adjudicated **pre-existing and not A3-specific**: `transferClassA` (`sync-run.ts:427`) and
      `copyAdditiveVideo` (`:281`) carry the identical exposure against the same rows, independently
      verified by Codex in round 4. A3's pre-write freshness re-read covers the common direction
      (worker writes during A3's copy phase ⇒ refuse, delete nothing); the reverse order and the
      lost-update case remain. No path destroys blobs — A3 deletes only after a verified write — but
      a row can end pointing where neither writer intended.
      **Fix must cover the whole sync write path, not A3 alone. Under discussion (2026-08-02):
      queue-based serialization vs conditional writes. Needs a decision before filing.**
      **Round 5 (2026-08-03) sharpened the CONSEQUENCE — same root cause, worse outcome.** Codex
      produced a concrete interleaving, confirmed by reading the code: `summary-handler.ts:95-96`
      pins `baseName` from the serial it reserved, then spends MINUTES in transcription + Gemini
      before persisting at `:156`. `persist_summary` resolves the key as
      `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')` (`0021:135`) — the **payload wins** —
      while `serialNumber` is restored from the existing row by step (2). So a stale worker persist
      landing after A3 leaves `serialNumber 3` beside `summaryMd 007_alpha.md`, with the paid digs
      at `dig/003_alpha/` and `dig/007_alpha/*` already deleted by A3's cleanup: **the dig content
      is orphaned**, not merely mis-pointed. Because A3 *moves and then deletes*, a lost update on
      this path costs paid content rather than a wrong pointer.
      **Codex's proposed fix does not work and was rejected with reasons** (see
      `docs/reviews/task-A-serial-coherence-branch-v5-rereview-review.md`): it suggests widening
      A3's pre-write freshness check to compare `serialNumber`, but the worker has written nothing
      at that moment — the write lands strictly after. Only fencing closes it, which is the decision
      above.
      **DECIDED 2026-08-03 (human): merge the serial-coherence branch now, fence as its own slice.**
      Rationale: the gap predates the branch, and the branch is strictly better than the status quo
      even with it open — it removes the divergence that was being written on *every* sync. Filed as
      `docs/backlog.md` **#17** (needs its own design-spec → plan → SDD; must cover the whole sync
      write path, not A3).
- [x] **A7 — integration suite restored to green against 0023** (2026-08-03). Two failures, both
      real, both invisible until the migration was actually applied to the local DB
      (`npx supabase migration up` — it was NOT applied, so the suite had been passing against the
      pre-0023 schema).
      1. `tests/integration/metadata-store.test.ts` test 10 asserted the **phantom serial as the
         contract**: a re-claim returning `{position: 1, serialNumber: 2}`, values computed from
         `MAX(...)` before the `ON CONFLICT` check and never stored. 0023 fixed that; the test was
         pinning the bug the branch removes. Now guards the fix.
      2. `tests/integration/cloud-sync/e2e.int.test.ts` **M-R2-2** hard-coded the pre-A3 key.
         Proven branch-caused (passes on `master`, fails on the branch, same `-t` filter, same DB)
         and then proven **correct**: on master that fixture ended `serialNumber 1` beside
         `<videoId>.md` — a row whose serial and filename disagree, the exact orphaning condition.
         On the branch both replicas end at `001_<videoId>.md` with `report.errors` empty.
         Re-asserted as an invariant (replicas agree; the key encodes the row's serial).
      **Process gap this exposed:** `npm run test:integration` does not apply pending migrations, so
      a new migration silently leaves the suite testing the old schema — a gate that fails OPEN.
      Recorded under *Dev-infrastructure debt*.
- [ ] **A6 — RE-SCOPED 2026-08-03: `position` is NOT vestigial.** The premise was wrong. The
      *return-value field* of `claimVideoSlot` has zero consumers after A2, but the **column** is
      load-bearing: `supabase-metadata-store.ts:43` orders every `readIndex` by it. Splits into:
      - [x] **A6a DONE** (`93631da`) — `position` dropped from the `claimVideoSlot` return type
        across the interface + both adapters. Payoff is defect-prevention, not tidiness: A2's bug was
        literally `playlistIndex = slot.position + 1`, and removing the field makes that unwriteable.
        Proven by the compiler — the only remaining use failed `TS2339` on removal. No SQL. Test
        assertions were **moved to where the guarantee is observable**, not dropped: the concurrency
        test now reads the `position` COLUMN and asserts `0..N-1`, because position is protected by
        `videos_playlist_position_uniq` while `serialNumber` lives in jsonb with no constraint —
        the row-lock is the only thing preventing a duplicate serial.
      - **A6b** (defer — own slice) drop the column + `videos_playlist_position_uniq` + the dead
        `reorder_videos` (0005, zero production callers). Needs a replacement `ORDER BY`, and the
        obvious candidate is a trap: `serialNumber` lives in the `data` jsonb, so
        `.order('data->>serialNumber')` sorts as TEXT (`"10"` before `"2"`) without a generated
        column. Would also be the **third** `claim_video_slot` signature change (0007 → 0023 → this)
        and would change the shape of 0023's rolling-deploy wrapper. Likely dissolved by ADR-0006.
- [x] **PR + merge** — ✅ **MERGED to master** (PR #42, squash `f8703bc`, 2026-08-03). CI green,
      branch deleted. Merged with backlog #17 knowingly open: the worker-vs-sync gap predates this
      branch, and the branch is strictly better than the status quo — it stops divergence being
      written on every sync.

**Sequenced behind A** (each needs its own spec + merge gate): **B** stable section identity,
**C** authority + divergence detection, **D** cloud rebuild parity. See
`docs/superpowers/plans/2026-07-31-serial-coherence-sync.md` and `~/.claude/plans/`.

## Stable blob addressing / manifest — ⏸ **PARKED 2026-08-11 (user decision)**

**⏸ STATUS — PARKED, not abandoned, and not blocked.** Design is done and merged: **ADR-0006**,
**ADR-0007** (`efee284`) and the coordination implementation (`1a7c076`), behind seventeen adversarial
review rounds. What is *not* done is the migration: **the schema has never run and holds zero rows** —
`video_artifacts`/`video_generations` appear in no migration (prod and master both end at `0025`), and
it lives only at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/`.

*Why park:* everything it currently fixes is a defect **in itself**, not in the running product, and
the roadmap's stated goal is M3 acceptance. The remaining risk sits entirely in first contact with
real data, which deserves a deliberate slice rather than a continuation. Every parked piece carries
its own trigger — task #44 (T5 code preconditions), task #45 (`doc_key` re-key ⟷ `inflight_uq`
coupling), backlog #25 (render addressing), #26 (attempt ceiling), #27 (GC retention).

**⚠ UNPARK TRIGGER:** when backlog #17/#19 (CAS conditional-write on `persist_summary`) becomes the
next slice, or when a real caller is about to reach `record_artifact` for a paid kind. **Backlog #26
must be closed FIRST** in that case — ADR-0007 deleted the only per-kind attempt bound on the money
path, so shipping without that decision silently promotes a summary from 1 paid attempt to 5.

**Why it exists:** every hard defect of the last three weeks reduces to one sentence — *the blob
address is derived from mutable data* (`base = <serial>_<slug>`, and both halves move). Spec:
`docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md`; decision recorded in
**ADR-0006**, which supersedes ADR-0002's rejection of video-level shared summaries.

**Gate status (§15 of the spec):**

- [x] **Re-verify §3 ground truth against live code** — ✅ 2026-08-05. 16 facts, **13 verbatim, 3
      citations corrected, 0 facts false**. All three were stale *line numbers* pushed down by PRs
      #45 and #38 — so the spec now cites symbols, not lines.
- [x] **Walk each §9 concurrency row** — ✅ 2026-08-05, and it earned its cost: **3 of 4 rows did not
      survive**, each invalidated by a *later section of the same spec*. Row 1 answers a **scalar**
      race with a **blob** fix (this is Q8, concretely), row 3 rests on the sufficiency claim §5.1
      retracted, row 4 sells team concurrency §11.1 disclaims.
- [x] **Q4 — retention + GC trigger** — ✅ 2026-08-05. *Not current ⇒ delete, except paid, retained
      **90 days**.* Scheduled sweep. A duration not a generation count, because a count evicts by
      activity and bursts of activity are when mistakes happen. Explicit delete outranks retention.
      **Surfaced while closing it:** removing `<playlistKey>` from the path breaks `Principal.indexKey`,
      so playlist hard-delete (a prefix sweep) must become manifest-driven enumeration — uncosted work
      on the delete path whose worst failure mode is silent.
- [x] **Q8 — scalar coherence** — ✅ 2026-08-05. **The card joins the generation** (§5.2). Refined the
      same day: the card is *not homogeneous* — document facts (`tldr`, `docVersion`, …) travel with the
      body, video judgments (`ratings`, `overallScore`, `tags`, …) stay on the video and are stable
      across regenerations. Also added §5.2.2: a generation is not publishable until corrections are
      applied — **depends on backlog #23**.
- [x] **Q3 — overlap threshold + section-merge ambiguity** — ✅ 2026-08-05. *When ambiguous, leave
      unattached; never guess.* Attach only when unambiguous in **both** directions (exactly one
      section overlaps the dig, and exactly one dig claims that section); threshold **0.8** of the
      dig's own span, tunable upward only. **Exposed a gap in §6:** the section-**split** case was
      never named and is ambiguous from the dig's side, not the section's.
      **All three prerequisites are now closed.** Remaining §14 questions (Q1 generationId form,
      Q5 offline local generation, Q6 cross-playlist dedup, Q7 seam-bypassing writers) are not
      prerequisites and can be settled during the review.
- [x] **`grill-with-docs` terminology pass** — ✅ 2026-08-06. Nine terms in `CONTEXT.md`. Found four
      collisions with established vocabulary (*slot* = `claim_video_slot`; *rendering* = summary→HTML/PDF,
      **renamed to display name**; *tenant* was already the gloss for **Owner**; *authoritative* vs
      *source-of-truth*), one six-hour-old self-contradiction (§2 `Card` vs §5.2.1), and it renamed the
      path segment **`tenantId` → `workspaceId`** after establishing that a name for *who may access* is
      unfit for an address. §11 rewritten: membership-not-identity, atomic creation, and §11.1's
      teams-are-expensive claim withdrawn as wrong.
- [ ] **Dual adversarial review to convergence** — mandatory (schema + identity + money path).
      **Deliberately sequenced last:** running it while 3 prerequisite forks are open would burn a
      round re-reporting "these are open."
      **Rounds 1–6 done, NOT CONVERGED** (7 → 8 → 10 → 6 → 7 → 8 Blocking). Trail:
      `docs/reviews/spec-blob-addressing-r{1..6}-*.md` — ✅ **MERGED (PR #51)**. Round 6's
      security/mechanical half is applied; four design items are handed off in `…-r6-handoff.md`.

      **Handoff item 1 (`detached` fencing) — ✅ DONE (PR #52).** Sequenced first because it is
      self-contained and its three sub-parts had to be cross-derived as one change. Outcome: of the
      four measured bypasses, **two were fixed, one was closed by a constraint, and one was not a
      defect** — H1's `P9` rested entirely on §6.2's "a detached dig is never deleted", which
      contradicted §8's 90-day retention rule decided the day before. **User retired the §6.2 promise
      2026-08-06**, and the finding dissolved without a code change. Third finding in that section in
      three rounds, so `dev-process.md`'s recurrence trigger applied: the rule was a choice wearing the
      costume of a constraint. New `detached_at` column carries the clock. 48 → 57 assertions,
      **7/7 new guards mutation-checked RED**; the mutation harness is now committed
      (`…/mutate-schema.py`) rather than rebuilt ad-hoc each round.
      **Mutation found two defects in the round's own tests** — a two-guard fixture (round 5 H1's
      masking shape, recurring) and a vacuous clock assertion (`now()` is transaction-stable, so it
      compared `now()` with `now()` and could never fail). Both were invisible to reading and to a
      green suite.
      **Handoff item 2 (corrections representation) — ✅ DONE (PR #53, stacked on #52).** The
      roadmap's "blocked by backlog #23" turned out to be **two claims, only one true**: §5.2.2's
      publishability rule genuinely needs #23 (it is about the *cost* of re-applying corrections),
      but the hash representation does not — provided "no corrections" is a **defined** constant
      rather than one derived from the corrections shape. That distinction unblocked the slice.
      Fixes a measured money-path defect (rung 1 stale for the whole corpus ⇒ `copyToCloud` on every
      sync, forever). `corrections_hash` is now NOT NULL — the nullable column conflated "no
      corrections" with "never computed", which is *why* 2903 wrong rows were invisible — and a
      trigger keeps the denormalized copy from drifting, which is the half B4 did not ask for.
      Reverses round 5's C2. 57 → 63 assertions, **13/13 mutations behaved as expected**.
      **One mutation is documented as expected-GREEN:** rung 1's `=` carries no guard of its own
      while NOT NULL holds, and saying so beats letting a tightened-looking comparison read as a fix.
      Three defects found by running it, none visible to reading — a `distinct` that would violate the
      PK for a video in two playlists, and *twice* an unqualified name that resolved everywhere except
      inside the `security definer set search_path = ''` trigger (`no_corrections_hash`, then
      pgcrypto's `digest`, which Supabase installs in `extensions`).
      **Handoff item 4 (the reservation protocol) — ✅ DONE (PR #54).** The reclaim added in round 5
      was not a protocol: an untyped return that conflated absent with zero, a terminal bound that was
      resettable because reclaim and reserve were two round trips, and no way for a reclaimed writer
      to learn it lost. Replaced by `reserve_artifact_slot` / `renew_artifact_lease` /
      `record_artifact`, modelled on `reserve_serve_model` (0014), already in production doing this.
      **The reviewer's proposed fix was declined on purpose:** H5 wanted a token that VETOES the
      record, but in the measured race both Gemini calls are already paid for by then, so rejecting
      one discards bought content without preventing the charge. **User decision 2026-08-07: the
      reservation guards SPENDING, not recording.** Renewal — token-fenced, ceiling-bounded — fixes
      the actual defect (a lease expiring under a live worker) and tells the loser *while it is still
      working*. 63 → 73 assertions, **22/22 mutations as expected**.
      **`search_path` swept across the whole schema** after the same class of bug appeared four times
      in one day, the last reached from a definer function *through a CHECK constraint*. Every
      function now pins its path except `assert_raises`, labelled as the deliberate exception.
      **Handoff item 3 (the generation-write API) — ✅ DONE (PR #55).** Sequenced last on purpose,
      because it had been specified-before-the-table-changed **twice** (round 2 N-B3, round 5) and the
      table only settled across the three merges above. **Measured, and worse than the handoff
      described:** after items 1/2/4 landed, a cloud summarize could not reserve a summary slot *at
      all* — reserving with no generation row raised `[23503]` on the artifact's FK, and creating that
      row from what is knowable before the paid call raised `[23514] gen_card_complete`. Both doors
      locked, with the Gemini call between them. §10.0 exists to prevent exactly this and predicted a
      failure *after* payment; the real one was *before* it — safer, but a dead feature rather than an
      expensive one, and all 73 assertions missed it because every fixture hand-inserts a **complete**
      generation, the one thing no producer can do.
      **The premise that failed:** *"a generation row is only ever complete"* — restated as **a
      generation must be complete when something RECORDED points at it**. `video_generations` gets
      `state` (`pending|complete`, defaulting to **complete**, which is the fail-*closed* default), the
      four summary CHECKs gate on it, and an artifact-side trigger forbids recording against a pending
      generation — that trigger, not the gate, is what keeps the relaxation from being a bypass.
      `record_artifact` gained `md_hash` / `card` / `doc_version_major` / `produced_at` and completes
      the generation in the same transaction. **73 → 89 assertions, 35/35 mutations as expected.**
      **Task #25 dissolved without a schema change** — `digDeeper` was never bound to one generation;
      the FK is on `(ws, video, generation_id, KIND)`, so it points at a *digDeeper* generation minted
      per rewrite. Third time a finding came from reasoning about a **name** rather than reading the
      constraints (round 2's `kind='summary'`, item 1's `P9`, this).
      **Item 1's deferred `INSERT`-path `detached_at` gap is closed here rather than carried to round
      7**, by bounding the clock to the artifact's real lifetime — and doing so found an illegal value
      inside a *passing* fixture (a dig detached in 2020 from a generation produced in 2026).
      **The mutation harness needed a fourth verdict.** Item 3's guards are triggers, and a trigger's
      `raise exception` matched neither the assertion nor the constraint pattern — so three *working*
      guards were reported `INVALID` ("the mutation broke the SQL"). That is the harness making the
      mistake its own docstring warns about, one layer up; `RED(trigger)` now names it.

- [ ] **Round 14 — the escalation rule fires a SECOND time, and the slice is SPLIT (2026-08-09).**
      **NOT CONVERGED: 4 Blocking, 4 High, 5 Medium, 1 Low.** Reviews:
      `docs/reviews/spec-blob-addressing-r14-{codex,claude,coordinator}.md`. PR #65 (`c16d44a`).
      Aimed at **round 13's own fixes**, and the aim was right: **every Blocking was in a change made
      the day before**, and two of them were round-13 fixes that contradicted each other.
      **B2, the deepest:** round 13 named staged-write ordering as the GC-floor successor *and* carved
      `model` out as the standing exception — but `model-store.ts:51` writes the model with a plain
      `put`, and its docblock says staged→promote *"is NOT used for the model"* **deliberately** (a
      regenerated model must overwrite). So a `model` generation would be collectable while its paid
      Gemini call is in flight — round 9's B1 resurrected. The successor is now stated **per kind**.
      **B3 (MEASURED):** `on delete restrict` on the new provenance table aborts the cascade
      `profiles → workspaces → workspace_videos → video_generations`, so **account deletion broke**.
      Now cascade.
      **B4:** `render_id` reached the column but never the **address**, so renders stayed overwritable
      — N rows on one key, N−1 pointing at bytes that no longer exist. *A render was not ADDRESSED by
      the hash; it was IDENTIFIED by it while remaining ADDRESSED by an unchanged key.*
      **B1 was my own editing error** — two copies of the central table, the second being the refuted
      version, at equal authority. `check-docs.py` now has a **mutation-verified duplicate-heading
      gate**; it had passed the file because it checked links, frontmatter and budgets but never asked
      whether a normative document contradicts itself.
      **The coordinator made the same class of error twice**, in the fixes for the round that named
      it. Round 13's B1 was *"a true lemma about writes read as a conclusion about money"*; round 14
      found (a) a true rule about **spend** read as a conclusion about **availability** (`SUM` on
      `attempt_count` → `attempts_exhausted` → a 503 with no stale fallback; now
      `least(sum, max-1)`), and (b) *"production already does content addressing"* citing a file that
      hashes the renderer's **input** and carries a separate hand-maintained version segment
      *precisely because the hash does not subsume it*. **All three citations RESOLVE. Resolving is
      not supporting.**
      A **57-tag `[VERIFIED:]` audit** found 1 wrong, 1 partial-wrong, 3 off-by-N, 1 claim-vs-code
      mismatch — all corrected.
      **⟳ SCOPE SPLIT (user decision):** render addressing failed design review **twice in two
      rounds**, meeting the escalation criterion in its own right, so it is **not patched a third
      time**. It moves to [`docs/superpowers/specs/2026-08-09-render-addressing-brief.md`](superpowers/specs/2026-08-09-render-addressing-brief.md)
      + backlog #25, awaiting Phase 1 brainstorming — which **neither previous attempt ever had**
      (each was one paragraph written while fixing something else; that is the root cause, not
      difficulty). **ADR-0007 is now scoped to COORDINATION only**, and states honestly that the
      `generation_id IS NULL` conflation it was drafted to dissolve is **still open**.
      **The core decision has now survived TWO design reviews** — neither reviewer could break the
      disjointness claim in either round.

- [ ] **Round 13 — the FIRST DESIGN REVIEW, and the escalation rule's first firing (2026-08-09).**
      **NOT CONVERGED: 2 Blocking, 4 High, 6 Medium, 1 Low.** Reviews:
      `docs/reviews/spec-blob-addressing-r13-{codex,claude,coordinator}.md`. ADR-0007 revised in
      answer; **round 14 mandatory**.
      Triggered by the stop condition armed in PR #64 — two consecutive rounds whose findings were
      caused by the previous round's fixes ⇒ escalate from **fix** to **redesign**, and review the
      redesign's *premises* instead of hunting defects in the mechanism it deletes. It fired correctly
      and paid immediately: **both Blockings are about the ADR's justification, and neither argues for
      restoring the reservation protocol.** The decision to delete it survived review; twelve defect
      hunts could not have reached either finding, because neither is a bug in any line of SQL.
      **B1 — a paid producer with no job.** The magazine `model` is generated by an HTTP GET
      (`lib/html-doc/serve-doc.ts:112`), arbitrated by a *third* coordination vocabulary the ADR never
      named (`serve_model_charge`), whose `doc_key` still carries `playlist_id` while the artifact slot
      does not. One video in N playlists ⇒ N leases on one slot, no lease expiry needed — the spec
      measured this as round-1 H5 and specced the re-key at `:2464`/`:2753`, never implemented.
      **The sharpest sentence of the series:** the load-bearing claim (*writes land on different keys*)
      is **true**, and round 5 measured that its truth is precisely the *mechanism* of the double
      spend. The contended resource was never the key — it was the money. **The ADR proved the wrong
      lemma and read it as the conclusion.**
      **B2 — generation-derived render addresses break GC.** §8 requires the paid/free split to be
      readable *"from the KEY ALONE"*; the discriminator is path segment 4. Uniform addressing erases
      it. MEASURED: both escape routes are closed by constraints the ADR listed as *"Kept, unchanged"*.
      **Decision (user, 2026-08-09): Option A** — re-key `doc_key` to `(workspace_id, video_id)` in the
      same slice as the deletion, and name `serve_model_charge` in the concern table as a **standing
      structural exception**. Routing `model` through `jobs` was evaluated and rejected as a *product*
      change (first-view latency, the read-only share path, six earned serve outcomes incl.
      serve-stale-over-budget, G1's separate fairness cap) — recorded with a trigger for revisiting.
      `attempt_count` merges by **SUM** on migration, per the serve path's own rule *"over-count is
      safe, under-count is the bug"*.
      **Renders switch to `sha256(rendered bytes)`** under the existing `renders/` prefix, with
      provenance in a `video_artifact_sources` join table — settling the "Open design question" the ADR
      had deferred while saying it must not be discovered during implementation. Both reviewers
      recommended it independently; it is already what production PDFs do.
      **The reviewers SPLIT on the reclaim path and the split was adjudicated by reading code:** Codex
      said two producers append two rows, Claude showed the heartbeat-abort prevents the append. Both
      partly right — the rows are prevented, the *charge* is not, and that residual is pre-existing and
      tracked to 1D. Fourth split in this project's history; the standing lesson held.
      **A gate built one day earlier cannot see the collision it was built for.**
      `check-vocabulary-collisions.py` scans only the spec schema dir, so `serve_model_charge` — the
      largest live duplicate of `jobs`' vocabulary — is outside its glob, and it prints
      *"✅ no unjustified duplicate mechanism"*. Same shape as round 12's *"every guard classified"*.
      Widening its glob to `supabase/migrations/` is open follow-up.
      ⚠ **Rounds 9–12 are NOT recorded in this list** — they live in
      `docs/reviews/spec-blob-addressing-r{9,10,12}-*.md` and the 2026-08-09 retrospective. Recorded
      here as a known gap rather than backfilled, so nobody reads the jump from 8 to 13 as rounds that
      never happened.

- [ ] **Round 7 — NOT CONVERGED (2 Blocking, 3 High, 5 Medium), fixes on `fix/blob-addressing-r7-findings` (PR #56).**
      Called for one purpose: the four items had each been reviewed against *itself* and none against
      the others. **Every Blocking and High was an interaction between two of them and a defect in
      none individually** — round 6's cross-derivation verdict, reproduced under the same condition.
      Both reviewers independently **confirmed** the 89/89 and 35/35 claims as true; every finding was
      something neither instrument could see.
      **B1 silently revoked a user decision.** `record_artifact`'s append was blind, so a worker that
      merely *restarted* and forgot its token collided with its own pending row (`[23505]`, no race).
      The 2026-08-07 decision — *the reservation guards spending, not recording* — was restored as a
      rejection by item 3's freeze trigger, written a day later **in a different file**. A rule can be
      overturned by a change that never mentions it.
      **B2:** nothing bounded `produced_at`, a caller-supplied **ranking rung**; a future value made
      §6.2's detach permanently impossible. **H2:** the generation completion was fenced on nothing,
      so a caller could complete another writer's generation and lock the real owner out of its paid
      work forever. **H3:** a denied reservation littered an unreachable `pending` generation.
      **89 → 98 assertions, 35 → 41 mutations, all as expected.**
      Two physical rules learned from the fixes: **a CHECK is evaluated on the proposed tuple before
      conflict resolution** (so `excluded.*` cannot repair itself), and **the span belongs to the slot
      while provenance belongs to the generation**.
      **The Codex gate had been running at half strength.** Two independent sandboxes: disabling
      Claude Code's does nothing to the one `codex exec` applies to itself, so the reviewer could not
      reach Docker and reviewed by *reading* — `0/35 … SQL did not run`. Fixed with
      `-s danger-full-access`; recorded in `docs/plugins.md`. The prior memory note covered the
      **outer** sandbox only, which is shape #10 in the tooling rather than the schema.
- [ ] **Round 8 opening — the GUARD CLASSIFICATION pass (PR #57).** Ran *before* the review round, and
      it found two defects seven adversarial rounds had missed. Every guard on the two tables was
      labelled **SHAPE** (is this row well-formed? a violation is a caller bug → **reject**) or
      **SEQUENCE** (who got here first? a violation is concurrency, and the caller may already have
      spent money → **reconcile**, never a raw rejection).
      **32 guards: 26 SHAPE, 6 SEQUENCE.** Every CHECK and FK is SHAPE and correct. Three of the six
      were already reconcilers — including `video_artifacts_inflight_uq`, the one predicted broken —
      one is a deliberate ownership fence, and **two were rejecters**:
      **(1) The free-render path had no working writer.** `free_uq` promises renders are
      "overwritable"; measured, the first render of a slot worked and every re-render failed with a
      raw `23505`. One INSERT takes one conflict arbiter and `record_artifact`'s was the **paid**
      partial index, which a NULL generation can never match. Same shape as handoff item 3 — a whole
      *kind* of write unreachable — surviving because every fixture writes a free render **once**.
      **(2) §8's retention sweep could never run.** `forbid_collecting_current` raised, so a batch
      collect died on the first current generation and rolled back the rest; retrying could not help
      because a current generation is *permanently* current. A guard that made its own purpose
      unreachable. Fixed by moving the currency test into `video_generations_collectable`, which the
      sweeper selects **through**, with the trigger kept as a backstop — deliberately **not** by
      silently suppressing the update (shape #5, on the one path with no undo).
      **98 → 102 assertions, 41 → 44 mutations.**
      **Why review missed both: each guard is *plainly correct*.** The pass does not ask whether a
      guard is right, it asks what it does when the caller is merely **second** — a question nobody
      asks of a constraint they agree with. Depth and coverage are different axes; seven deep rounds
      lost to one shallow total sweep.
- [ ] **Round 8** — mandatory: a round returning new Blocking/High is proof the loop is still earning
      its cost. Standing agenda: the inert `pending` generation left by a crashed summary worker (§8
      has no sweep for it), `persist_summary`'s merge semantics (backlog #17's residue), and the one
      SEQUENCE item the classification could **not** measure — `reserve_artifact_slot` guards
      `paid_uq` with a check-then-act, so a concurrent recorder between the read and the write yields
      a raw `23505` instead of the typed `already_recorded`. Proving it needs real concurrency, which
      the rollback harness cannot produce.

      **Round 6's headline is a correction to round 5's own report.** `assert_raises` caught
      `when others`, so six negatives were passing on a `[42601]` arity error instead of the
      constraint they named — round 5's Blocking B1 and High H5 shipped **unverified** while the suite
      printed green and exited 0. **The instrument was converting failures into passes**, which no
      amount of further testing could have found. Any "verified" claim from round 5 or earlier
      predates `3fb6970` and is not trustworthy. Two live security holes were also MEASURED, both
      created by round 5's fixes: `anon` deleted another tenant's reservation through a definer
      function with default `PUBLIC EXECUTE`, and `anon` TRUNCATEd the paid manifest — TRUNCATE sees
      neither RLS nor a row trigger. 48 assertions now, each naming the guard that rejected it.

      **The artifact changed medium at round 4→5, and that is the headline.** Roughly half of round
      4's Blocking were *"the SQL in this prose block does not execute"* — compile errors being found
      by human review, the most expensive possible way to find them. The schema moved out of prose
      into **executable, verified DDL** (`…/2026-08-03-stable-blob-addressing/schema/`, run by
      `verify-schema.sh` against the live local Postgres inside a rollback). It paid on the first run
      and has paid every round since. **13 → 37 behavioural assertions, every guard mutation-checked.**

      **Round 5 found three defects that no amount of reading had found in four rounds**, each
      MEASURED: a **cross-tenant leak** (a view runs as its owner, so it bypasses RLS — and the
      *missing* grant is what makes the leak look like a fix), an **empty card winning the ranking**
      (`?&` tests key existence, and the resulting SQL NULLs made a placeholder outrank a real paid
      generation), and a **double charge** (two writers reserving one slot, because round 4's
      append-only fix removed the mutual exclusion round 3's money guard was standing on).

      **Standing count: shape #9 — "a fix that moved or reintroduced a defect" — now at seven**, three
      of them caused by this review's own fixes. That is the argument for the cross-derivation step
      (`docs/dev-process.md`), which found five conflicts *between* round-5 findings before any were
      written, four of them between different reviewers.

**Blocks:** backlog #17 / task #19 (the CAS conditional-write slice is deferred pending this), and
task #18 (A6b `position` drop, likely dissolved by ADR-0006).

**Blocked by:** **backlog #23** — corrections as deterministic `{from, to}` pairs. §5.2.2 requires a
generation to carry the user's corrections; today re-applying them costs a whole-document Gemini round
trip, which is why the code silently does not do it *and stamps a hash claiming it did*. The rule is
correct either way, but sequence #23 first or it ships as a per-generation LLM call on a document whose
headings are an identity anchor.

## Honest-blob-read slice (`BlobRead`) — own spec + merge gate

**Why it exists:** Stage 3 cloud-sync produced 1 Blocking + 3 High that were all one shape — a value
meaning *absent* is also what a *failure* produces. `SupabaseBlobStore.get` is `if (error) return null`
(swallows 404, 5xx, timeout, RLS) while `LocalFsBlobStore.get` nulls only on ENOENT. The branch fixed
its own call sites with the `BlobStore.provesAbsence` flag — a side-channel callers must remember to
consult. The durable fix is to make the type honest so the compiler enforces it at every call site:

```ts
type BlobRead =
  | { ok: true;  bytes: Buffer }
  | { ok: false; reason: 'absent' }
  | { ok: false; reason: 'unreadable'; cause: unknown };
```

**The money-path instance it was named for is now FIXED** (`fix/serve-model-unreadable-no-recharge`,
2026-07-19): `resolveMagazineModel` probes the new `BlobStore.tryGet` before `reserve_serve_model` and
returns `busy` on an unreadable read instead of paying. Confirmed empirically first — 6¢ → 12¢ with a
simulated transient failure — so this is no longer an inference. That closes the **billable** path only;
the rest of the slice below still stands, and `provesAbsence` cannot retire until it lands.

**Scope:** `lib/storage/blob-store.ts` + both impls; then every caller — `serve-doc.ts`,
`serve-summary-core.ts`, `read-model.ts`, `model-store.ts`, `rerender.ts`, `generate.ts`,
`build-doc-html.ts`, `dig-handler.ts`, `load-dig-for-serve.ts`, `app/api/pdf/[id]/route.ts`. Each
caller must state which `reason` it means; `unreadable` must never trigger a spend or a delete. Retire
`provesAbsence` once the type carries the information.

**Second, smaller item in the same slice:** delete the `setPlaylistMeta` footgun — omitting the
optional title writes `playlist_title: meta.playlistTitle ?? null`, i.e. **erases** it (this was H3).
Split into `setPlaylistUrl` + the never-clobber `setPlaylistTitleIfNull`, which *already existed* and
was simply not called — proof that offering a safe alternative is not enough while the unsafe one is
callable.

**Sequencing:** after M2a merges (touches merged serving/sharing/dig read paths, so it must not ride
along on the sync branch). Needs its own spec + review + human merge gate like any other slice.

---

## Parking Lot — post-launch hardening (does NOT block launch)

*Same rule as Dev-infrastructure debt: each item needs a **trigger**, or it rots here. Items without
one are honest wishes, not plans — mark them so rather than pretending they are scheduled.*

- **Cloud dev/staging Supabase project** *(user proposal, 2026-07-24)* — today the only hosted Supabase
  is **prod** (`uykwcybxqgewmbltroxf`); there is **no cloud environment to develop/test against without
  touching prod**. Local Docker Supabase (#2) covers most dev/test, but the *hosted-infra* dimension
  (pooler/TLS/network, real Storage RLS + legacy-key grants, transient failures) can currently only be
  exercised against prod — which is exactly why the M1.4 **B1–B5** checks were framed against prod.
  **Fix:** stand up a **separate staging Supabase project** (or use Supabase branching), apply the same
  migrations `0001–00NN`, and point the B-group + any future hosted-sync testing at *staging*. **TRIGGER:**
  before running any hosted-infra sync/acceptance test (B-group, M2b, M3) — run it against staging, not
  prod. Rule of thumb: **prod is never a development target.**
- **Real-cost settle slice** (spec §10): replace the keep/release *heuristic* with real `actual_cents`
  from `usageMetadata`; closes the §2.4a/b/**4c** residuals + the crash residual (billable-phase marker).
  Natural sequel to the reservation slice. **MEASURED MOTIVATION (2026-07-22):** actual per-video cost
  on flash ≈ **8¢** (summary ~6.5¢ + dig ~1.5¢, from `lib/gemini-cost.ts`), but each job RESERVES 150¢
  — ~37× over. So the daily cap governs reservations, not spend: at $5 it fits ~3 videos though real
  spend allows ~60. Settling to actual is what lets the cap track real money. Do NOT fix this by
  lowering the 150¢ reservation — it is a proven worst-case bound (a 30-min all-retries video ≈ $1.15).
  See the [[cost-per-video-analysis]] memory.
  - **Also revisit `summary_max_attempts` here (found 2026-07-23).** It's pinned at 1 because
    cap-soundness requires `summary_est_cents ≥ ceil(worst) × attempts`, and with worst=115¢ /
    est=150¢ there's only room for 1 attempt — bumping to 2 today would force est→230¢ (a 53% larger
    reservation, ~33→~21 jobs/day at the 5000¢ cap). Once settling recalibrates est to *actual* cost,
    `2 × small` is cheap, so summary gets its transient-failure retry for free. **`dig_max_attempts`
    was already raised 1→2 in migration `0022`** — dig worst=23¢ vs est=150¢ had ample headroom
    (150 ≥ 23×2), so it needed no est change. This entry = do the same for summary after settle.
- **Serve-lease heartbeat / expiry sweep** (spec §10, §2.3/H5): closes the bounded 6¢ serve residual.
- **Migrate off legacy JWT API keys.** Prod was provisioned on Supabase's *legacy* `anon` /
  `service_role` JWT keys, deliberately: every test in this repo ran against that format, and a lot
  of behaviour is pinned to exact role grants (`0007` storage → `service_role`; `0020` grants only
  `select, insert` on `ledger_audit`; `reservation-release.test.ts` asserts `authenticated` gets
  `42501`). Supabase now steers toward publishable/secret keys and both legacy entries in the
  dashboard say "Prefer using … instead", so this is a real migration, just not one to do on the
  first deploy. **TRIGGER:** any Supabase notice about legacy-key removal, or any work touching the
  auth/role layer. Whoever does it must re-run the RLS isolation + money suites against the new key
  format, not assume equivalence.
- **Subscription / billing tier** *(user vision, 2026-07-21)* — the app already ships a free tier
  with limits (`quota_allowance` per anon/authenticated, `guardrail_config` daily cap + max_free_users).
  The missing piece is a **credit-card subscription that lifts those limits** — no billing layer maps
  a paying user to a raised allowance. **TRIGGER:** when free-tier limits become the thing users hit
  and ask to pay past. Design note: this is a raise-the-allowance feature on top of existing
  guardrails, not a new limits system. See the access-tiers memory.
- **Open public signup safely** *(2026-07-21)* — `Allow new users to sign up` should stay OFF after
  the M1.4 smoke test (bootstrapping: sign in once to create the owner account, then lock). Before
  ever opening it publicly, **verify the PROD `guardrail_config` defaults** (`daily_cap_cents`,
  `max_free_users`) — those, not the signup toggle, are what cap a stranger's spend. They came from
  migration defaults and may be generous. **TRIGGER:** any decision to let people other than the
  owner sign in. Pairs with the `exec_sql` debt item under the same "before sign-ups open" trigger.
- **Periodic cost recalibration** *(user proposal, 2026-07-19)* — the cost constants in this repo
  (`summary_est_cents`, `dig_est_cents`, and the per-token reasoning behind the M1.1 gate) are
  snapshots of vendor pricing that changes. Rather than re-deriving exact figures by hand, add a
  job that periodically re-measures actual cost-per-operation from `usageMetadata` and current
  published pricing, and flags drift beyond a threshold. **Trigger:** any future "is this cost
  number still right?" question — including the next live-gate style verification, which should
  read the recalibrated number instead of re-litigating token arithmetic. Rationale: small factors
  should be ignored, not chased; what matters is catching an order-of-magnitude change.
  **First pass done 2026-07-22:** confirmed the 150¢ reservation is ~37× the ~8¢ real flash cost, and
  that dev billing ($15.18 June) is Pro-dominated dev digs prod never makes. Recurring half still open:
  the `PRICE_*_PER_1M_CENTS` constants in `lib/gemini-cost.ts` are dated (gemini-2.5-flash, 2026-07) and
  want periodic refresh against live pricing.
- **Committed integration test** for the cloud dig **serve** path (currently uncovered).
- **Deploy verification** of cloud summary-PDF (needs a live container — folds into 1.4/3.1).

---

## Serve-path absence defect — backlog #34 — ✅ RESOLVED 2026-08-11 (PR #78)

> ⚠️ **This section was written when the defect was believed live, and stayed that way after it was
> fixed.** Filed by PR #77, resolved by PR #78 — and this heading still said *"NOT started"* until
> 2026-08-12. `dev-process.md` requires the status to move in the same PR as the work; it was updated
> in `backlog.md` and the M1.4 checklist and missed here. Recorded rather than silently corrected,
> because it is the third instance of this exact shape in one week.

**What gate B3 measured, and what it did not.** `tryGet → absent` is not proof of absence on Supabase:
an RLS-denied read returns a 404 byte-identical to a genuine miss. Driving `resolveMagazineModel`
directly with the owner policy dropped re-reserved and re-generated — **6¢ → 12¢** with a second live
Gemini call. **But that state is not reachable through the application.** The only caller goes through
`loadSummaryForServe`, which reads the summary markdown with the same store and principal and fails
closed at `409 "repair needed"`, so a permissions fault ends the request before any reserve. The B3
harness had read the markdown with `service_role` to isolate the model read, constructing a state the
app cannot enter. **The charge was real; the route to it was not.**

**What was genuinely wrong, and is fixed (PR #78).** The blob store's comment asserted a 404 *"IS
provable absence"* and listed RLS denial as producing something else — both false, and it quoted the
very error string that disproves it. And the protection was **accidental**: no signature, comment or
test carried it, and `mdBody` was optional, so a new caller could reach the charging code having never
done the read. `mdBody` is now required, and
`tests/integration/serve-md-unreadable-no-charge.test.ts` pins the short-circuit — mutation-verified.

**Acceptance did not need hosted infrastructure after all.** Gate B3's money clause tested an
unreachable state, so it is replaced by that test, which runs in CI on every change instead of by hand
against a live project. The staging project `neeufoxdbgbpkjukzzuc` was consequently deleted
2026-08-12; prod was verified untouched and serving afterwards.

---

## The `explain-diff` skill — an EXPERIMENT, not a process change (2026-08-12)

A skill that builds a self-contained HTML explanation of a change, aimed at **behaviour and decisions**
rather than a line-by-line walkthrough. Design note: [`explainer-spec.md`](explainer-spec.md).
Skill: `.agents/skills/explain-diff/`. Output: `~/explainers/` (outside the repo — no `.gitignore`
entry, nothing to commit by accident).

**Nothing is enforced. This is deliberate, and it is what two review rounds bought.** It began as a
mandatory pre-merge gate with a PR-body record, an independently-authored quiz, a CI check and a
renderer. Round 1 returned 26 findings, 5 Blocking — **every Blocking and High landed on the
enforcement layer; the explainer itself drew none.** Round 2 on the stripped-down version returned 20
more, and killed the remaining process machinery: `process-checklists.md` is not `@`-included by
`CLAUDE.md`, and its read-trigger is *"when you are working a gate"*, so a rule routed there for a
thing that is **not** a gate has no activation path. Reviews:
`docs/reviews/understanding-gate-spec-v2-{codex,claude}.md`,
`docs/reviews/explainer-spec-v3-r2-{codex,claude}.md`.

**The founding premise is UNMEASURED** — PR #67 being 39 commits over 7 rounds shows the model was
absent, not that the absence cost anything — so the experiment is the attempt to measure it.

- [ ] **Re-examine after 5 explainers or on 2026-09-30, whichever comes first.** Count them with
      `ls ~/explainers | wc -l`. **RETIRE the skill** unless at least one has produced: a boundary
      nobody had written down, a decision that became an ADR, a corrected belief, or a defect the dual
      review missed. **FAILS IF** the date passes with none of the four and the skill is still installed.
      **VERIFIED AGAINST:** the explainers in `~/explainers/` at that date.

**Run 1 (PR #78, `5cbedcf`) produced one: [ADR-0008](adr/0008-serve-money-guard-depends-on-storage-grant-granularity.md)** — the serve
path's money guard depends on migration `0007`'s grant being on the owner path segment, and `0007`
says nothing about it. Narrow that grant and the guard dies silently (6¢ → 12¢, every test green).
Filed as **backlog #35** for the migration-side anchor, which is blocked on one unverified question:
whether editing an already-applied migration is safe here.

- [ ] **backlog #35 — annotate `0007`'s policy with a pointer to ADR-0008** (or add a check that fails
      when the `split_part` clause changes without ADR-0008 being revisited). **FAILS IF** the policy's
      granularity can be changed with nothing in the migration, and no gate, referring to ADR-0008.

---

## Sequence & status
**M1 → M2 → M3**, Parking Lot after. Within M1: 1.2 + 1.3 can proceed in parallel with 1.1; 1.4 needs all
three. **M2 Sync is COMPLETE (PR #23 + #24, 2026-07-19).** **M1.1 is now DONE (2026-07-19).**
Current: **M1 IS COMPLETE — the app is LIVE and every first-class path has been exercised against
real infra.** 1.1 ✅ 1.2 ✅ 1.3 ✅ (2026-07-21), 1.4 core ✅ (2026-07-22, PR #32), **1.4 finish-up ✅
(2026-08-11)** — all of A1–A3 and B1–B5 closed; see
[`docs/m1.4-finishup-checklist.md`](m1.4-finishup-checklist.md) for the evidence and the release each
item was verified against.

**Next: M3 Acceptance** (browser-level Playwright e2e against the deployed URL). M2 Sync completed
2026-07-19.

### ▶ NEXT ACTIONS (**refreshed 2026-08-12** — read this first on a fresh session)

**Reconcile this block against `git log` AND against live infrastructure every time.** The
2026-07-30 version of it was stale within days, and the entries below it still are — treat the
numbered engineering list as a *candidate pool*, not a current plan, and check each against
`git log` before picking one up. **Also read the running system**, not just the repo: on 2026-08-11
this file claimed prod was at migration `0021` when it was at `0022`, which is how `0023` came to sit
unapplied for eight days while every document read "merged, done".

**Current state (2026-08-12):**
- **`master` = the merge of PR #84**, clean, tsc clean, **2690 unit / 267 suites** and **491
  integration** green (counts re-run 2026-08-12).
  *No commit SHA here, deliberately, and* ***the PR that edits this line names ITSELF***. The field
  held a SHA once: false the moment it was written, because the PR editing this block is the PR whose
  merge moves `master` past whatever SHA it names. Replacing the SHA with a PR number did not fix it
  either — **PR #81 wrote "#80"**, the previous number, so the field was wrong again on the very
  first merge. [`dev-process.md`](dev-process.md) already says *"do not chase the squash SHA — the PR
  number exists as soon as the PR does"*: open the PR, then write its own number here.
  Enforced by `scripts/check-roadmap-consistency.py`, which compares this against the PR in `HEAD`'s
  merge subject. ⚠ That comparison only has something to compare **on `master`**, so it catches the
  mistake on the first CI run after merge — it does not block the PR that makes it.
- **Deployed: release v6, 2026-08-11 15:47Z** (`fly status`: web + worker both v6).
  ⚠ **`master` has moved past the deployed release.** Nothing outstanding is deploy-urgent — the
  behaviour changes are the share tolerating version skew and the serve-path precondition — but
  **the app is not running `master`**. No PR range is listed here on purpose: it needs re-editing on
  every merge, which is the same defect as the SHA. Read `git log` and `fly status`, not this line.
- **Prod schema == master, verified by enumeration 2026-08-12: 25 applied, `0001` … `0025`, and the
  set diffed against `supabase/migrations/*.sql` is IDENTICAL** — no missing migration, no extra.
  Latest three: `0025 settle_is_observable`, `0024 lease_covers_serve`,
  `0023 claim_video_slot_desired_serial`. `guardrail_config.daily_cap_cents = 5000` (gate A3).

  **Re-run it with no login and no token:**
  ```
  psql "$CLAUDE_RO_DATABASE_URL" -At \
    -c "select version from supabase_migrations.schema_migrations order by version;"
  ```
  Diff that against `ls supabase/migrations/*.sql`. **Count and max are not enough** — they agree
  while a middle migration is missing; diff the sets.

  *This became possible on 2026-08-12.* `supabase migration list --linked` needs a platform login,
  and `claude_ro` was denied on the `supabase_migrations` schema — so the one question that once went
  eight days unanswered here ("is prod on the schema we think?") was unanswerable by the very role
  built to answer it. Two grants fixed it permanently:
  `grant usage on schema supabase_migrations to claude_ro;` and
  `grant select on supabase_migrations.schema_migrations to claude_ro;`

  ⚠ **What this reads is the migration LEDGER, not the schema.** It answers "does prod think it ran
  `0025`?" A partial or hand-edited migration can leave the ledger saying yes. The stronger evidence
  is still to probe for an object the migration creates — e.g. `ledger_audit_kind_note_idx` from
  `0025`, which is present. The cheap check does not retire the real one.
- **The blob-addressing schema is ⏸ PARKED by user decision** — see that section for the unpark
  trigger. Do not resume it by momentum.

**Blocked on the human:** nothing.

**⭐ M1 IS COMPLETE (2026-08-11).** M1.4 closed with all of A1–A3 and B1–B5 ticked — see
[`docs/m1.4-finishup-checklist.md`](m1.4-finishup-checklist.md) for the evidence and the release each
item was verified against. M2 Sync completed 2026-07-19.

**The actual next step: M3 Acceptance** — browser-level Playwright e2e against the deployed URL.
⚠ **It needs a design pass before it can start:** M3.1/3.2/3.3 are the only three items the
gate-falsifiability ratchet still flags, because none of them says what observation would make it
FAIL. Write them as gates first; that exercise is what turned the version-skew item from a six-week
"experiment" into an hour of work.

> **Convention for this block:** name only work that is still open. Past items belong in the sections
> below, because `scripts/check-roadmap-consistency.py` reads an identifier inside a forward-looking
> sentence as a claim that it is pending — and that strictness is the point.

**Two things from closing M1.4 that change how to run M3:**
1. **Ask what caller reaches the state you are testing.** Gate B3 "failed" against a situation the
   application cannot enter — the harness had used `service_role` to bypass the app's own
   short-circuit. The mechanism was real; the scenario was manufactured.
2. **For "logged out", fetch with no cookie jar** (`curl`), not an incognito window. Stronger
   guarantee, and it avoids the trap that made the 2026-07-22 A2 attempt inconclusive.

*(The throwaway staging project has been deleted — see the serve-path absence section.)*

**Older candidate pool below — VERIFY BEFORE STARTING. Several of these predate three merged
slices.**

**Unblocked — engineering, in recommended order:**
0. **Finding #2 — CONFIRMED DEFECT (2026-07-30).** A re-dug section silently keeps its OLD body
   on the cloud path: `writeDigSectionBlob` calls `promote()`, which is create-if-absent on
   Supabase, so the regenerated content is discarded — and that writer stamps no metadata, so
   nothing records it. Proven by `tests/lib/dig/write-dig-section-blob-promote.test.ts`
   (currently RED **on purpose** — it is the bug report; branch `test/promote-divergence-finding-2`,
   not merged). **Reachability not yet traced:** does the dig path allow re-digging an already-dug
   section at the same `DIG_GENERATOR_VERSION`? Answer that first — it sets severity vs D2.
1. **D2 — no reaper for `serve_model_charge`** (money path, fails silently). Nothing cron-shaped
   exists in the migrations and `sweep_expired_leases` never touches `reserved_cents`, so a process
   death between reserve and settle appears to strand the reservation permanently.
   See `docs/reviews/architecture-review-2026-07-30.md` → *Defects*.
2. **Architecture-review findings #1, #2, #4–#7** — same document. #2 (route the five artifact
   writers through `writeArtifact`) is the natural next one; the new `InMemoryBlobStore` makes it
   testable.
   - **Acceptance criteria are defined and measurable:**
     [`docs/reviews/architecture-findings-acceptance.md`](reviews/architecture-findings-acceptance.md).
     Current state any time via `python3 scripts/check-arch-findings.py` (**2/18 criteria met** as
     of 2026-07-30 — the 2 are finding #3). It runs in CI as a **ratchet**: it fails the build if
     any metric gets *worse* than its 2026-07-30 baseline, which is the only thing that would
     notice a 13th route file copy-pasting the `STORAGE_BACKEND` fork.
   - **SCOPE CORRECTION 2026-07-30.** Finding #2 covers FIVE writers. The trace below graded only
     **W2 (the dig writer)** and an earlier revision of this line wrongly labelled the whole finding
     LOW on that one sample. Live `promote()` callers still assuming uniformity:
     `summary-handler.ts:178` (W1), `write-dig-section-blob.ts:50` (W2, traced),
     `sync-run.ts:210` (W3). W1 and W3 are **untraced**.
   - ⚠️ **W1 (summary) CONFIRMED DEFECT 2026-07-30 → finding #2 is a BUG FIX, not a refactor.**
     Proven by `tests/lib/job-queue/summary-handler-promote-divergence.test.ts` (drives the REAL
     `makeSummaryHandler`; RED **on purpose**, branch `test/promote-divergence-finding-2`):
     local `overwrite` → REGENERATED body ✅, Supabase `create-if-absent` → **ORIGINAL body** ❌.
     The dig key embeds `.r{V}` so a bump can't collide; the summary key has no version at all
     (`baseName = padSerial(serial) + slugify(title)`, and `reserve_video_slot` returns the
     **existing** serial for a known video — `0009…sql:88`), so it is stable for the life of the
     video. Path, all designed behaviour: `CURRENT_DOC_VERSION` bump + deploy → **a user
     re-submits the same playlist URL** to `POST /api/jobs` (the ONLY cloud summary-job trigger;
     `videos/[id]/regenerate` is local-only and enqueues nothing) → new `jobs_idem_active` slot
     → jobs for **every** video in that playlist → the skip at `summary-handler.ts:85-91`
     doesn't fire on a version mismatch → full charged summarize → `promote()` onto the occupied
     key → Supabase **skips** → old body survives while `persistSummary(..., 'promoted')` stamps
     the NEW docVersion. **Unlike the dig case the two bodies are SUPPOSED to differ.** Local
     unaffected. **Not automatic on deploy** — it needs the re-submit (corrected 2026-07-30).
     **Viewing a stale doc is NOT a trigger:** a bump makes the *rendered HTML* stale
     (`eligibility.ts:12`) and that re-renders from the existing markdown without running the
     handler. ⚠️ **But if lazy per-video regeneration-on-view is ever built, this defect starts
     firing on view** — fix #2 before building it. **W3 (`sync-run.ts:210`) still untraced.**
   - **W2 (dig) reachability TRACED 2026-07-30 → severity LOW.** The writer-level
     divergence is proven (`tests/lib/dig/write-dig-section-blob-promote.test.ts`, RED **on purpose**
     — it is the bug report; branch `test/promote-divergence-finding-2`, unmerged). But the
     user-initiated re-dig is blocked by the trigger's blob dedupe (`enqueue-dig-core.ts:39`),
     concurrent triggers by `jobs_idem_active`, and a version bump can't collide at all because
     `.r{V}` is *in* the key. The only open route is same-job re-execution after `complete()` fails
     (`worker-runner.ts:59` → `sweep`, `0008_jobs_queue.sql:173`), where **both bodies are valid
     digs** — the user sees the first generation, not wrong content. Keep the fix (divergence +
     silent discard are real), but it is not urgent. Full trace + the one bad conjunction
     (terminally-`failed` job outside the idem index + an `exists()` false-negative → paid,
     discarded, untraced) in `docs/reviews/architecture-review-2026-07-30.md`.
3. **D1, D3, D4** — cloud dug-section ordering, the YAML newline that silently drops a paid dig
   section, and the write-only dig generator meta.
4. **D5, D6, D7 — filed 2026-07-30**, all found while tracing #2. See
   `docs/reviews/architecture-review-2026-07-30.md` → *Defects*.
   - **D5** — a **style-only (MINOR) doc-version bump re-summarizes the whole playlist on
     cloud**. `needsResummarize()` encodes the documented MAJOR/MINOR rule and has exactly one
     caller (the local path); the cloud skip compares the flattened `"major.minor"` string. Local
     and cloud-serve cost **0** Gemini calls for the same bump; cloud ingest pays in full, and
     W1 then discards the result. Fix: cloud calls `needsResummarize`; stop flattening the job
     version.
   - **D6** — the **magazine model's drift guard is a title proxy**. `isFresh()` checks titles +
     `GENERATOR_VERSION` and never `sourceMdHash`, which *is* written into every envelope. A
     prose-only MD change with stable titles is served as fresh forever — and `fixSummary` pins
     headings **on purpose**, so that is the designed shape of a corrections regenerate, not a
     coincidence. Already documented in the wrong module (`companion.ts:43-45`). Fix: read
     `sourceMdHash` in `isFresh`.
   - **D7** — **section identity is answered three ways, two of them the title string.** Model ↔
     section is positional+title; dig ↔ section is `startSec` with a title fallback. `startSec` is
     minted inside `generateSummary` and lives only in the MD's `▶` line, so it is unique within a
     generation but **not stable across** one. A re-summarize always breaks the numeric match, and
     if it also rewords a heading, **paid dug content orphans**. One retitled heading also nulls
     every section's gist. Fix direction: a **stable, persisted `sectionId`** minted once and
     carried through regenerations — the concept the codebase keeps approximating.
   - Proof for D6/D7: `tests/lib/html-doc/section-identity-after-resummarize.test.ts` (5 passing
     characterization tests — they encode current behaviour, so they are a regression baseline for
     any stable-sectionId work).
4. **Backlog #18(b)** — give `grill-with-docs` a trigger. It is the documentation-integrity skill
   (ships `ADR-FORMAT.md` + `CONTEXT-FORMAT.md`, captures decisions *as they crystallise*) and has
   been dormant since 2026-07-12. Its dormancy is why ADR-0005 sat unpromoted for four weeks.
5. **`PreCompact`/`SessionEnd` snapshot** of mechanical session state (branch, unpushed commits,
   dirty files, open tasks). Designed 2026-07-30, **not built**. Honest limit: a `PreCompact`
   *command* hook cannot read the conversation (`prompt`/`agent` hook types are tool-events only),
   so it captures mechanical state — **not decisions**, and is no substitute for (4).
   *(The push guard from this pair IS built — PR #39, `.claude/hooks/block-default-branch-push.sh`.)*
6. **Two unbuilt checks** for `scripts/check-docs.py` — README coverage, and roadmap
   internal-consistency. Both recorded under *Process & documentation integrity* above.

**Unblocked — can be picked up now, in recommended order:**
1. ~~Fix the red `reservation-release` suite~~ ✅ **MERGED to master 2026-07-19** (PR #25, merge commit `bbc82c9`).
   Root cause was a self-poisoning suite, not the "state pollution from other suites" this
   roadmap previously recorded — see *Dev-infrastructure debt*. "Full suite green" is a
   falsifiable gate again and the known-red list is empty.
2. ~~Shrink the deploy image~~ ✅ **MERGED 2026-07-19 (PR #26).** The multi-stage Dockerfile is on
   `master` (`FROM node:22-bookworm-slim AS builder`) and the app has since deployed and served
   traffic, so `fly deploy` supplied the confirmation the local `docker build` could not.
   *(This entry read "CODE DONE, SIZE UNMEASURED, branch unmerged" for 11 days after that branch
   was merged and deleted.)*
3. ~~Codex dispatch wrapper~~ ✅ **DONE 2026-07-19** — `scripts/codex-review.py`, converged over 5
   adversarial rounds. Use it for every Codex review: `python3 scripts/codex-review.py --out
   docs/reviews/<name>-codex.md "<prompt>"`. Exit 1 means the gate did not run → fall back to Claude.
   *(This line claimed the dev-infrastructure debt list was EMPTY. It is not — see that
   section: `exec_sql` is open, added 2026-07-20, one day after this line was written.)*
4. **Full honest-blob-read slice** — the remaining ~10 `blob.get` callers, retiring `provesAbsence`.
   Own spec + review + merge gate. The billable path is already closed (PR #24), so this is no longer
   urgent. *(Note: the `ledger_audit` wipe that silently affected zero rows during the fix above is
   the same swallow-the-error shape this slice exists to fix — it is not confined to `BlobStore`.)*
5. **Locally-fixable M2a deferred findings** — most notably Claude-R3-M1 (`build-doc-html` derives
   `base` from `digDeeperMd`, so a diverged replica key makes the dig view serve the pre-sync summary).

**Loose end:** ~~uncommitted local modifications to `docs/local-validation-findings.md` and
`supabase/config.toml`~~ — **stale, verified 2026-07-30:** `git status` reports no modifications
to either file.

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
- [~] **1.4 Deploy + smoke test** — **CORE DONE 2026-07-22; APP LIVE at
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
  - [ ] **Round-trip.** Local-only video → sync → present in cloud; cloud-only video → sync → hydrated
    locally with a readable MD body. Confirm blob paths are `<ownerId>/<playlistKey>/<key>` under a real
    user JWT — the Task 12 review caught a literal `{ id: 'cloud' }` principal that Storage RLS rejects.
  - [ ] **B1 guard, live.** Make a cloud MD blob unreadable mid-sync (revoke the Storage policy briefly,
    or point at a key the policy denies) and confirm: the error surfaces in `report.errors`, the other
    replica's bytes are byte-preserved, `docVersion` is not downgraded, and **no manifest baseline is
    written** — then re-run and confirm it heals. This is the check local cannot produce.
  - [x] **serve-doc money finding — CONFIRMED and FIXED before launch (2026-07-19).** No prod infra was
    needed: the repo already had fault-injecting blob-store wrappers and `spend_ledger` assertions, and
    the `null` a transient error produces is byte-identical to a 404's. Measured before the fix
    `spend 6→12, gemini_calls=1, attempt_count=2` — a real double-charge for a model already in the
    bucket; after, `status=busy, spend 6→6, gemini_calls=0`. Regression test:
    `tests/integration/serve-model-unreadable.test.ts`. **Still worth re-running against hosted
    Supabase at deploy** to confirm a real 5xx (not a simulated one) carries a non-404 `statusCode`.
  - [ ] **M-R7-1 skew.** Deploy an image whose `GENERATOR_VERSION` differs from the local checkout, run a
    `copyToCloud` transfer where both sides hold a model for the same body, and check whether a rendering
    share starts returning 503.
  - [ ] **No service-role on the sync path** in the deployed config (`scripts/check-service-confinement.ts`
    passes against the real environment, not just local).

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
- [ ] **Roadmap internal-consistency check** — *replaces a rejected proposal.* The original idea was
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

**STATUS: one open item (`exec_sql`, 2026-07-20). `middleware-2a` red suite FIXED 2026-07-23. The two
2026-07-19 items are CLOSED.**

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

## Serial coherence in cloud-sync — branch `fix/serial-coherence-sync` (2026-07-31)

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
- [ ] **A-review** — 4 rounds done, **not converged**; round 5 is the next step.
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
- [ ] **A6** delete the vestigial `position` column — separable, deliberately last
- [ ] **PR + merge** (human gate)

**Sequenced behind A** (each needs its own spec + merge gate): **B** stable section identity,
**C** authority + divergence detection, **D** cloud rebuild parity. See
`docs/superpowers/plans/2026-07-31-serial-coherence-sync.md` and `~/.claude/plans/`.

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

## Sequence & status
**M1 → M2 → M3**, Parking Lot after. Within M1: 1.2 + 1.3 can proceed in parallel with 1.1; 1.4 needs all
three. **M2 Sync is COMPLETE (PR #23 + #24, 2026-07-19).** **M1.1 is now DONE (2026-07-19).**
Current: **M1 core is DONE — the app is LIVE.** 1.1 ✅ 1.2 ✅ 1.3 ✅ (2026-07-21), 1.4 core ✅
(2026-07-22, PR #32); 1.4 finish-up items remain in [`docs/m1.4-finishup-checklist.md`](m1.4-finishup-checklist.md).
Update the checkboxes as steps land.

### ▶ NEXT ACTIONS (as of 2026-07-30 — read this first on a fresh session)

**The deploy blockers are GONE.** M1.1–M1.3 are done and the app is live; the previous version of
this block still named M1.3 as "the single remaining blocker" nine days after it shipped — it
contradicted the checkboxes directly above it. Reconcile this block against `git log` and the
merged-PR list every time, per *Session Resume*.

**Blocked on the human:** nothing. PR #38 (`04984af`) and PR #39 (`622e793`) are both merged;
`master` is green.

**Unblocked — engineering, in recommended order:**
1. **D2 — no reaper for `serve_model_charge`** (money path, fails silently). Nothing cron-shaped
   exists in the migrations and `sweep_expired_leases` never touches `reserved_cents`, so a process
   death between reserve and settle appears to strand the reservation permanently.
   See `docs/reviews/architecture-review-2026-07-30.md` → *Defects*.
2. **Architecture-review findings #1, #2, #4–#7** — same document. #2 (route the five artifact
   writers through `writeArtifact`) is the natural next one; the new `InMemoryBlobStore` makes it
   testable.
3. **D1, D3, D4** — cloud dug-section ordering, the YAML newline that silently drops a paid dig
   section, and the write-only dig generator meta.
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

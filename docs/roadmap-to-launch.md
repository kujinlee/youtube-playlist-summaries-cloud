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
  (prod `daily_cap_cents`=500¢: 3 of 9 queued, 6 blocked — working as designed). Owner signup locked
  OFF after account creation. **3 cloud-run blockers found + fixed (PR #31, all build-time-vs-runtime):**
  NEXT_PUBLIC absent at build (→ [build.args] + fail-build guard); OAuth callback → 0.0.0.0:3000
  (→ x-forwarded-host); root page baked static-LocalApp at build (→ force-dynamic).
  **Still to do in 1.4:** (a) download + share paths — not yet exercised; (b) raise prod
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

## Dev-infrastructure debt (NOT tied to any feature slice — survives every merge)

**STATUS: one open item (added 2026-07-20). The two 2026-07-19 items are CLOSED.**

- [ ] **`exec_sql(sql text)` is a test-only helper that ships to production.**
  **TRIGGER: before the app is reachable by anyone but the owner (i.e. before M1.4 opens sign-ups).**
  Migration `0004` creates a `security definer` function that executes arbitrary interpolated SQL,
  granted to `service_role` only and correctly denied to anon/authenticated (verified in prod:
  `anon=false authenticated=false service_role=true`). It has **zero production callers** — only 8
  integration test files use it. Residual risk: anyone holding the `service_role` key can run
  arbitrary SQL as the function owner, including statement injection past the wrapper
  (`select 1) t; drop …; --`) — an *escalation* beyond service_role's already-broad access, on a
  money-handling DB. Accepted for now (user, 2026-07-20 — option (c)): no deploy, no users, no data
  yet, and the exposure requires an already-compromised service_role key. **The fix** is a `0022`
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

- **Real-cost settle slice** (spec §10): replace the keep/release *heuristic* with real `actual_cents`
  from `usageMetadata`; closes the §2.4a/b/**4c** residuals + the crash residual (billable-phase marker).
  Natural sequel to the reservation slice. **MEASURED MOTIVATION (2026-07-22):** actual per-video cost
  on flash ≈ **8¢** (summary ~6.5¢ + dig ~1.5¢, from `lib/gemini-cost.ts`), but each job RESERVES 150¢
  — ~37× over. So the daily cap governs reservations, not spend: at $5 it fits ~3 videos though real
  spend allows ~60. Settling to actual is what lets the cap track real money. Do NOT fix this by
  lowering the 150¢ reservation — it is a proven worst-case bound (a 30-min all-retries video ≈ $1.15).
  See the [[cost-per-video-analysis]] memory.
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
Current: **M1 — 1.3 prod infra is the only remaining human-gated blocker; then 1.4 deploy.**
Update the checkboxes as steps land.

### ▶ NEXT ACTIONS (as of 2026-07-19 — read this first on a fresh session)

**Blocked on the human (credentials only, no engineering left):**
1. ~~M1.1~~ ✅ **DONE 2026-07-19** — gate verified and opened (`RELEASE_VERIFIED = true`).
2. **M1.3** — provision the prod Supabase project, secrets, buckets; apply migrations **0001–0021**.
   **This is now the single remaining blocker to a deploy.**

Then M1.4 (deploy + smoke test + the 5 cloud-sync checks above) and M3 follow.

**Unblocked — can be picked up now, in recommended order:**
1. ~~Fix the red `reservation-release` suite~~ ✅ **MERGED to master 2026-07-19** (PR #25, merge commit `bbc82c9`).
   Root cause was a self-poisoning suite, not the "state pollution from other suites" this
   roadmap previously recorded — see *Dev-infrastructure debt*. "Full suite green" is a
   falsifiable gate again and the known-red list is empty.
2. **Shrink the deploy image** — ⚠️ **CODE DONE 2026-07-19, SIZE UNMEASURED** (branch
   `chore/shrink-deploy-image`, unmerged). Multi-stage Dockerfile: builder does
   `npm ci` + `next build` (`output: 'standalone'`) + an esbuild worker bundle; the runtime layer
   carries only those two artifacts + Chromium, dropping the full 684 MB `node_modules`, npm's
   cache, TypeScript/`ts-node`, and the whole-repo `COPY . .`. Also swapped the `googleapis`
   umbrella (194 MB, used for a single `youtube.v3` call) for `@googleapis/youtube` (1.8 MB).
   **`docker build` could not run** — Docker Desktop registry pulls hang on this machine and no base
   image was cached — so the resulting size is an ESTIMATE, not a measurement. Measured pieces:
   `node_modules` 684 → 492 MB; `.next/standalone` 78 MB (vs 492 MB full install); worker bundle
   2.4 MB. **The first `docker build` on a machine with registry access, or `fly deploy` itself,
   is the confirmation step — fold it into 1.4.** Verified without a build: standalone `server.js`
   binds `0.0.0.0`; the bundled worker boots on Node 22 and drains cleanly on SIGTERM in ~1 s;
   2450 unit tests + tsc green. Note `fly.toml`'s process commands changed to direct `node`
   invocations, since neither the `next` CLI nor `ts-node` exists in the runtime image any more.
3. ~~Codex dispatch wrapper~~ ✅ **DONE 2026-07-19** — `scripts/codex-review.py`, converged over 5
   adversarial rounds. Use it for every Codex review: `python3 scripts/codex-review.py --out
   docs/reviews/<name>-codex.md "<prompt>"`. Exit 1 means the gate did not run → fall back to Claude.
   **The dev-infrastructure debt list is now EMPTY.**
4. **Full honest-blob-read slice** — the remaining ~10 `blob.get` callers, retiring `provesAbsence`.
   Own spec + review + merge gate. The billable path is already closed (PR #24), so this is no longer
   urgent. *(Note: the `ledger_audit` wipe that silently affected zero rows during the fix above is
   the same swallow-the-error shape this slice exists to fix — it is not confined to `BlobStore`.)*
5. **Locally-fixable M2a deferred findings** — most notably Claude-R3-M1 (`build-doc-html` derives
   `base` from `digDeeperMd`, so a diverged replica key makes the dig view serve the pre-sync summary).

**Loose end:** `docs/local-validation-findings.md` and `supabase/config.toml` have uncommitted local
modifications predating 2026-07-18; never reviewed, deliberately excluded from PRs #23/#24.

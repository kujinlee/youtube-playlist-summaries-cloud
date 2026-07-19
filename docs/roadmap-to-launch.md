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

- [ ] **1.1 Live-Gemini verification** *(human-gated: needs a live Gemini key + billing dashboard)*.
  Procedure in `docs/reservation-release-live-gate.md`. Verify the two facts: (a) an overloaded/
  rate-limited call throws `GoogleGenerativeAIFetchError` with `.status ∈ {429,503}`, and (b) those
  statuses bill $0. If both hold, flip `RELEASE_VERIFIED = true` in `lib/gemini-failure.ts` and re-run
  `npm run test:integration -- reservation-release`. Same live session also confirms the Stage 1D
  transcript fallback (`CLOUD_TRANSCRIBE_FALLBACK_VERIFIED`, `lib/gemini.ts`). Record evidence in
  `docs/local-validation-findings.md`. *Until flipped, release is fail-closed to KEEP — safe but leaves
  the outage residual, so this is what makes the deploy actually solve the self-DoS.*
  → **Harness ready (2026-07-17):** `npm run verify:gemini-release` (`scripts/verify-gemini-release.ts`)
  drives the REAL classifier against live 429/503s and prints the billing-dashboard window to check.
  Just needs you to run it with a live key. *Verification itself still pending — this step stays open.*
- [x] **1.2 Deploy config** *(written + `docker build`-validated 2026-07-17; image builds, 3.44 GB)*.
  `Dockerfile` (Node 22 + Playwright Chromium + `next build`), `.dockerignore`, `fly.toml` (web + worker
  process groups, HTTP on web only, `kill_timeout=120s`), runbook `docs/deploy.md`. Worker **graceful
  drain already existed** (SIGTERM/SIGINT → AbortController → clean loop exit, `worker/main.ts`); Node 22
  pinned per the supabase-js native-WebSocket finding. tsc clean. **Build finding:** `next build`'s
  static-generation phase OOMs at default heap → fixed with a build-layer `NODE_OPTIONS=--max-old-space-size=4096`
  (build machine needs >4 GB; the Fly remote builder does). Follow-up: 3.44 GB image (dev deps + Chromium)
  → compile worker to JS + prune dev deps later. *Actual `fly deploy` is 1.3/1.4 (needs your accounts).*
- [ ] **1.3 Provision prod infra**. Prod Supabase project; secrets (Gemini key, Supabase URL/anon/service
  keys, any OAuth); storage buckets; apply migrations **0001–0021** to prod (0021 is the cloud-sync signals migration from PR #23 — it drops-then-recreates `merge_video_data`/`persist_summary`/`update_video_annotations`, so grants must survive; verify the RPCs are callable under an authenticated user JWT after applying).
- [ ] **1.4 Deploy + smoke test**. Deploy app + worker; smoke-test the live container end-to-end (sign in
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
- [ ] **`scripts/codex-frontier-model.py` can select an unrunnable model.**
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
  Natural sequel to the reservation slice.
- **Serve-lease heartbeat / expiry sweep** (spec §10, §2.3/H5): closes the bounded 6¢ serve residual.
- **Committed integration test** for the cloud dig **serve** path (currently uncovered).
- **Deploy verification** of cloud summary-PDF (needs a live container — folds into 1.4/3.1).

---

## Sequence & status
**M1 → M2 → M3**, Parking Lot after. Within M1: 1.2 + 1.3 can proceed in parallel with 1.1; 1.4 needs all
three. **M2 Sync is COMPLETE (PR #23 + #24, 2026-07-19).** Current: **M1 — waiting on credentials.**
Update the checkboxes as steps land.

### ▶ NEXT ACTIONS (as of 2026-07-19 — read this first on a fresh session)

**Blocked on the human (credentials only, no engineering left):**
1. **M1.1** — run `npm run verify:gemini-release` with a live Gemini key + billing dashboard open.
2. **M1.3** — provision the prod Supabase project, secrets, buckets; apply migrations **0001–0021**.

Then M1.4 (deploy + smoke test + the 5 cloud-sync checks above) and M3 follow.

**Unblocked — can be picked up now, in recommended order:**
1. ~~Fix the red `reservation-release` suite~~ ✅ **DONE 2026-07-19** (`c8be696`, branch
   `fix/reservation-release-self-poisoning` — **unmerged, awaiting the human push/PR gate**).
   "Full suite green" is a falsifiable gate again and the known-red list is empty.
2. **Shrink the deploy image** (3.44 GB — prune dev deps, compile the worker to JS). On M1.4's critical
   path; you feel it on every deploy. See the M1.2 notes.
3. **Codex dispatch wrapper** — see *Dev-infrastructure debt*; stops the review gate failing open.
   **Now the sole remaining dev-infrastructure debt item.**
4. **Full honest-blob-read slice** — the remaining ~10 `blob.get` callers, retiring `provesAbsence`.
   Own spec + review + merge gate. The billable path is already closed (PR #24), so this is no longer
   urgent. *(Note: the `ledger_audit` wipe that silently affected zero rows during the fix above is
   the same swallow-the-error shape this slice exists to fix — it is not confined to `BlobStore`.)*
5. **Locally-fixable M2a deferred findings** — most notably Claude-R3-M1 (`build-doc-html` derives
   `base` from `digDeeperMd`, so a diverged replica key makes the dig view serve the pre-sync summary).

**Loose end:** `docs/local-validation-findings.md` and `supabase/config.toml` have uncommitted local
modifications predating 2026-07-18; never reviewed, deliberately excluded from PRs #23/#24.

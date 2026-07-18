# Roadmap to Launch — Cloud App

The path from "all capabilities merged" to "a running, unified product." Created 2026-07-17, after the
reservation-release money-path slice merged (PR #22). This is the **milestone** roadmap (not the
per-feature dev backlog — that's `docs/backlog.md`, which covers local-app style enhancements).

**Where we are:** every cloud capability is built and merged — auth, playlist ingest, summary +
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
  keys, any OAuth); storage buckets; apply migrations 0001–0020 to prod.
- [ ] **1.4 Deploy + smoke test**. Deploy app + worker; smoke-test the live container end-to-end (sign in
  → add playlist → generate summary → view → download → share); fix any cloud-run blockers.

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
- [ ] **2.3b Whole-branch dual review to convergence** — **← IN PROGRESS, not yet converged.**
  Reviews `docs/reviews/whole-branch-cloud-sync{,-v2,-v3,-v4}-rereview-{codex,claude}.md`.
  | Round | Findings | Fixed in |
  |---|---|---|
  | R1 | 1 Blocking + 2 High (WB-B1/H1/H2) | `32a164c` |
  | R2 | 2 High + 3 Med (H-R2-2 was a *regression from the R1 fix*) | `1f54c60` |
  | R3 | **1 Blocking** (B1) — Codex said CONVERGED, Claude caught it | `3bc8cc7` |
  | R4 | 3 High (H2 a *regression from the B1 fix*; H1/H3 pre-existing) | in progress |
  Trend Blocking 1→0→1→0, High 2→2→0→3. **Not converging monotonically** — each round's
  sharper prompt surfaces pre-existing defects the earlier rounds walked past. Root cause of
  B1/R4-H1/R4-H3 is one shared shape: *a value meaning "absent" is also what a failure produces*
  (`SupabaseBlobStore.get` swallows every error; `playlist_title ?? null`).
- [ ] **2.4 Merge** *(human gate)*.

**M2a deferred findings** (recorded, none blocking merge on their own — decide at the 2.4 gate):
- **Claude-R2-M1** — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
  (`sync-run.ts` artifacts deep-merge). Latent until a second artifact kind is populated.
- **Codex-R2-Med** — absent (`undefined`) companion scalars are not explicitly cleared on transfer,
  so a winner lacking `tldr`/`takeaways`/`tags` leaves the loser's stale values in place.
- **Claude-R3-M1** — `build-doc-html` derives `base` from `digDeeperMd` in preference to `summaryMd`,
  so when replica keys diverge (`serialNumber` is replica-local) the dig-deeper view serves the
  pre-sync summary. Stale-but-coherent; fix lives outside sync.
- **Pre-existing, unrelated:** `tests/integration/reservation-release.test.ts` fails identically on a
  clean tree (local Supabase state pollution — leftover `ledger_audit` rows + stale queued job).
  Needs a DB reset or per-test isolation; not caused by this branch.
- **Tooling:** `scripts/codex-frontier-model.py` returned `gpt-5.6-sol`, which the pinned Codex CLI
  (0.142.5) cannot run (HTTP 400) — it ranks by `priority` without filtering on client-version
  support, so the adversarial gate can silently no-op. Pin/filter needed.

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

## Parking Lot — post-launch hardening (does NOT block launch)
- **Real-cost settle slice** (spec §10): replace the keep/release *heuristic* with real `actual_cents`
  from `usageMetadata`; closes the §2.4a/b/**4c** residuals + the crash residual (billable-phase marker).
  Natural sequel to the reservation slice.
- **Serve-lease heartbeat / expiry sweep** (spec §10, §2.3/H5): closes the bounded 6¢ serve residual.
- **Committed integration test** for the cloud dig **serve** path (currently uncovered).
- **Deploy verification** of cloud summary-PDF (needs a live container — folds into 1.4/3.1).

---

## Sequence & status
**M1 → M2 → M3**, Parking Lot after. Within M1: 1.2 + 1.3 can proceed in parallel with 1.1; 1.4 needs all
three. Current: **M1 starting.** Update the checkboxes as steps land.

# Whole-Branch Review — Cloud Dig-Deeper Generation (`bce5b48..032ca10`)

Dual final review at the merge gate. Branch `feat/cloud-dig-generation`, 7 tasks, 37 files, +3251/−34.
Reviewers: Codex adversarial (gpt-5.5) + Claude final reviewer (opus). Both tasked with cross-task coherence + triage of the deferred findings.

## Convergent verdict (both reviewers agree)

**All cross-task money/auth invariants hold** — independently confirmed by both:
- **One-charge end-to-end:** exactly one charge point (atomic INSERT-or-JOIN in `enqueue_job`; quota debit + `spend_ledger` reserve on INSERT only; JOIN = no charge). Dedup 200 returns before preflight/enqueue (no charge-on-noop). Worker never charges. Retry re-charge blocked three ways: `dig_max_attempts=1`, version guard, `PermanentTranscriptError→NonRetryableError`.
- **Dedup-key ↔ write-key agreement (the one place a divergence silently re-charges every trigger):** trigger and worker both derive `base` from the **same** `videos.data` jsonb via the **same** `artifacts.summaryMd.key ?? summaryMd` fallback + `assertCloudSummaryMdKey` guard + `.replace(/\.md$/,'')`. Structurally impossible to diverge. H1 genuinely closed.
- **Version coherence:** enqueue `version`, `jobs_idem_active` slot, worker guard, blob `.r{V}` all key off `DIG_GENERATOR_VERSION` — a bump moves all four together.
- **Two-client split:** no service-role tenant read anywhere; confinement allowlist minimally scoped to the dig route.
- **Summary/ingest path non-regression:** `makeJobHandler` is a pure router; enqueuer payload widening is a jsonb passthrough (RPC body byte-identical).

**Genuine strengths:** per-section-blob model eliminates the lost-update race by construction; §9.2 completed-row re-check prevents a phantom 202; fail-closed anon gate + "prove the anon is real" test discipline are correct for a money path.

## Divergent verdict — the ONE open decision (human gate)

**Codex: BLOCKING — dig spend bound is not mechanically provable.**
`generateDig` (`lib/dig/generate.ts`) defaults to `gemini-2.5-pro` (unpriced vs the summary path's `PRICED_MODEL`), sends **no `maxOutputTokens`**, and its internal retry-once can issue **two** billable completions in one job (`dig_max_attempts=1` caps job executions, not model calls). So `dig_est_cents=150` is asserted, not proven. Worst-case (uncapped 64K-token output × retry-doubling + byte-capped input) ≈ $1.6–1.7 > $1.50. The summary path, by contrast, has a mechanical guard (`SUMMARY_MODEL===PRICED_MODEL` fail-fast + token caps making `perRunWorstCents` computable). Codex verdict: **not mergeable as-is**; must add an output cap, price the actual model (or fail-fast if it differs), account for the retry, and add a cost-guard test proving `dig_est_cents ≥ worst-case`.

**Claude opus: acceptable-deferral / mergeable as-is.**
Argues 150¢ is a sound worst-case (single-section output bounded by the model's own ~64K max ≈ $0.64; input now byte-capped; `max_attempts=1` bounds retries; missing abort-signal is the known summary-parity limitation).

**Controller assessment:** Codex's arithmetic is the sounder one — Claude opus's "$0.64 < $1.50" undercounts the retry-doubling (two billable completions) and the input cost. Without a `maxOutputTokens` cap, 150¢ is not a provable ceiling. The **global daily `spend_ledger` cap still bounds total runaway spend** (system-level protection holds), but the **per-job** charge-once bound is not mechanically provable — a gap against this project's established provable-spend-bound standard.

### Compounding (Codex Medium, related)
- **`ctx.signal` not threaded into `generateDig`** (`dig-handler.ts` checks `aborted` only *after* the call returns) — an abort burns the paid generation then discards it → a charged job with no blob. Part of the same `generate.ts` hardening. (Summary path has the same known limitation.)

### Not blocking (both reviewers agree — genuine deferrals)
- **§9.2 `409 repair` has no in-slice recovery path** — but unreachable in normal operation (promote precedes `completed`; `max_attempts=1` → a crash yields `failed`/`dead_letter`, not `completed`); needs *external* blob loss to reach. Deferred to the GC slice (plan L6). Document as manual/operator repair.
- **503 omits `Retry-After`** (429 has it) — no client yet; documented simplification.
- yamlScalar `\n`/`\r` (single-line heading titles), base-guard duplication (each individually correct), CLOUD_CAPS hand-copy (values can't drift — same imported constants; export `buildCloudCaps()` as fast follow-up), enqueue() payload union (runtime backstops; tighten at 3rd job_kind), T7 `as any`/setup mutations (load-bearing inserts already `{error}`-checked) — all acceptable deferrals.

## Merge decision → HUMAN
The branch is functionally correct and all isolation/one-charge/key-agreement invariants hold. The single open question is whether the **non-provable per-job dig cost bound** must be hardened before merge (Codex) or is an acceptable deferral given the daily-cap backstop (Claude opus). Because this (a) is a money invariant, (b) has reviewer non-convergence, and (c) any hardening touches `lib/dig/generate.ts` — which the spec designated UNTOUCHABLE ("Local path … UNTOUCHED") — and may require recalibrating `dig_est_cents` or the output cap, it is a spec-level decision reserved for the human. See the two options presented at escalation.

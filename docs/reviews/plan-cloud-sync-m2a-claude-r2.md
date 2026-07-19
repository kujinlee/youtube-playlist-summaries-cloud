# Adversarial Plan Re-Review (Round 2) — Stage 3 Cloud Sync M2a (Claude)

Re-reviewed v2 (commit e411393) against v10 spec + real source. Every reconcile row and round-1 finding traced against the new code.

## Mandate A — Round-1 closure audit
- ① mdHash from key not body: CLOSED — `deriveClassASignals(video, mdBody)` hashes mdBody; `readMdBody` on both sides.
- ② / B1 regenerate stamping: CLOSED (primary) — T4(b) extends real updateVideoFields; write & compare share `mdHash`. Residual N5.
- ③ T7 equal-hash skip: CLOSED — skips only both-current or both-stale+same-major; 11 rows traced.
- ④ / B2 RPC overload PGRST203: CLOSED — 0021 drops old signatures first; sole call site updated in T4.
- ⑤ sourceMdHash never written: NOT CLOSED → re-filed N1 (hashes filename).
- ⑦ / H1 T12 placeholder: PARTIALLY → re-filed N2 (presence NPE).
- M1 persist_summary guard: CLOSED — shown as diff, copy-verbatim instruction.
- M2 confinement: CLOSED. M3 harness: CLOSED. M4 local updateVideoFields test: CLOSED.
- M5 equal-value conflict: CLOSED (but see round-2 H1 from Codex — the fix regressed timestamp propagation).
- L1 archived empty {}: CLOSED. L2 one-sided needsRegen: CLOSED. L3 dedup playlistKey: CLOSED. L4 additive-cache test: PARTIALLY → N-note (helper still copies whole Video).

## Mandate B — New findings

### HIGH
**N1 — `sourceMdHash` stamps `mdHash(filename)` not `mdHash(body)`; every synced companion deleted → re-charge (round-1 ⑤ still open).** In `lib/html-doc/generate.ts` the MD body is `md` (line 33: `mdBytes.toString('utf-8')`); `sourceMd`/`video.summaryMd` is the blob key (lines 36, 50). T4(c) says `sourceMdHash: mdHash(sourceMd)` → hashes "001_title.md". `decideCompanion` compares `mdHash(body)` vs `mdHash(filename)` → never equal → deleteReceiverModel for every synced video. The T4 step-4b test `expect(env.sourceMdHash).toBe(mdHash(env.sourceMd))` passes on the buggy code, locking it in. Fix: `sourceMdHash: mdHash(md)`; test against the real BODY, never `mdHash(env.sourceMd)`.

**N2 — T12 presence/delete branch still `// ...` and reconcile derefs `lv!`/`cv!` → NPE on one-sided (money-create/delete) videos (round-1 ⑦ partial).** For a cloud-only video `lv` is null; `deriveHumanSnapshot(null)` derefs `video.updatedAt` → TypeError. The one-sided videos are exactly the additive-create/delete cases. Fix: render the presence/delete branch as real code that `continue`s before any `lv!/cv!` use; Behavior #2 → "every two-sided video."

### MEDIUM
**N3 — local `updateVideoAnnotations` allowlist excludes `corrections` → silent drop.** `local-metadata-store.ts` `allow = Set(['personalScore','personalNote','archived'])`. `applyClassBWinners` writes corrections to a local loser via `updateVideoAnnotations`. Fix: add 'corrections' to the Set + test.

**N4 — `buildBaseline`/manifest advance underspecified for `skip` and Class-B-only.** For `skip` there is no winner and `winnerMdHash` is null, yet a baseline must advance (seen-before for delete inference). Fix: advance from agreed-current signals; make buildBaseline take reconciled current signals.

**N5 — bare regenerate (no corrections param) stamps `mdHash('')` while stored corrections unchanged → fresh MD mis-marked stale.** Fix: stamp hash of the corrections actually baked in (stored value when param absent).

### LOW
- N6 — persist_summary grant under `authenticated` unverified (plan flags it as must-verify — good; confirm early in T12).
- N7 — equal-mdHash + one-current + different-major can downgrade major on an identical body — degenerate/unreachable; note only.
- N8 — `merge_video_data_bulk` not updated for conditional restamp — benign (non-Class-B path); document exclusion.

## Money-safety: holds (no producer/spend_ledger touch). Rename `summaryMd`→`summaryMdKey`: clean (all consumers updated).

**Verdict: NOT CONVERGED** — 2 new High (N1 sourceMdHash filename = round-1 ⑤ not closed; N2 presence NPE = round-1 ⑦ partial) + 2 Medium. Fix N1, N2, re-run dual review.

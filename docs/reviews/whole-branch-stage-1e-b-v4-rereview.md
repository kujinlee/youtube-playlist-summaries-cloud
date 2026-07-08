# Stage 1E-b Whole-Branch — Re-Review Round 4 (of fix `23bb78d`) — CONVERGED

**Target:** round-4 fix diff `cd6c91e..23bb78d` (persist_summary preserves existing summary fields on a status-only write via re-apply layer). **Date:** 2026-07-08.
**Reviewers:** Codex (`gpt-5.5`) + Claude Opus (instructed to be exhaustive after under-reviewing rounds 2-3).

## Both reviewers: CONVERGED
- **Codex:** status-only regression genuinely fixed; 0 Blocking/High/Medium/Low. `converged`.
- **Claude Opus (exhaustive):** GENUINELY-FIXED. **Proved it empirically** — applied the round-3 function to the live DB, confirmed the new test FAILS (`language` undefined, `ratings/overallScore/docVersion` dropped), restored round-4 → passes (negative control proving the test is a real guard). Traced all 4 field-resolution scenarios (first-time / concurrent-metadata-change / status-only / keyed re-persist) — all correct. Cross-checked the layer-3 whitelist against `SummaryCoreGeminiFields` (8) + handler-added (`summaryMd, docVersion, processedAt`) = **exactly 11** summary-owned fields; no metadata field wrongly included, no summary field omitted. Key-scoped monotonic / Task-2 lost-update / 0-row raise / owner scoping all intact. **No new Critical/Important.** `CONVERGED`.

## The final persist_summary merge (converged form)
```
data = (p_video - 'artifacts')                     -- (1) payload defaults — first-time bare row fill
     || (v.data - 'artifacts')                       -- (2) ALL existing win: no metadata clobber, no summary drop
     || strip_nulls({language,ratings,overallScore,processedAt,videoType,audience,tags,tldr,takeaways,docVersion FROM p_video})  -- (3) re-apply summary-owned (present-wins)
     || strip_nulls({summaryMd: coalesce(p_video, existing)})   -- (4)
     || {artifacts: existing || {summaryMd:{key, KEY-SCOPED monotonic status}}}   -- (5)
```

## Accepted Minor observations (pre-existing, not round-4 regressions; deferred with owners)
- L1 can resurrect a non-summary key a concurrent writer DELETED from `v.data` (first-time-fill mechanism; handler's payload carries a fixed metadata set that concurrent writers update, not delete — not reachable/harmful).
- No way to explicitly null-out a summary field (strip_nulls) — by design; handler never emits null summary fields.
- Deferred (from the whole-branch review, unchanged): full lease-fencing of persist_summary (residual stale write is idempotent + non-corrupting after the whitelist; double-Gemini-charge on reclaim → 1D); dead_letter orphan GC → 1H; SIGTERM burns a retry attempt (cooperative model); staged-blob leak → 1C/1D; runtime VideoSchema.parse on write (parity w/ local).

## Convergence trail (iterate-to-convergence — big/critical branch: schema/identity/concurrency/RLS)
| Round | Artifact | Blocking/High found | Outcome |
|---|---|---|---|
| WB-1 | whole branch | Codex 2B+2H / Opus 2 Important | fix (8 changes) |
| WB-2 | fixes v1 | Codex 2B+2H (metadata clobber under-fixed) / Opus converged | fix (whitelist) |
| WB-3 | fixes v2 | Codex 1H (status-only drop) / Opus converged | fix (re-apply layer) |
| WB-4 | fixes v3 | **Codex 0 / Opus 0** | **CONVERGED** |

Each round found strictly narrower defects, all confined to the intricate `persist_summary` two-precedence-group merge. Rounds 2 and 3 each caught a real defect the fixes introduced/left — the loop earned its cost. WB-4 is the gate: a full dual round with no new Blocking/High. **Ready to finish the branch + PR.**

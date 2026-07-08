# Stage 1E-b Whole-Branch — Re-Review Round 3 (of fix `cd6c91e`) + Round-4 fix

**Target:** round-3 fix diff `51a5d8a..cd6c91e` (persist_summary whitelist merge + key-scoped monotonic + guarded delete). **Date:** 2026-07-08.

## Round-3 verdicts (DISAGREED again — Codex more rigorous on the SQL)
- **Codex: revise-again.** Confirmed all three round-2 findings genuinely fixed (metadata clobber, key-scoped monotonic, guarded delete). But NEW High: **a status-only persist now DROPS existing summary metadata.** The whitelist removed the summary keys from `v.data`; if `p_video` also omits them (a status-only call: `{id,title}`), `language/ratings/overallScore/processedAt/docVersion` are deleted. Erasing `docVersion` defeats the idempotency skip.
- **Claude Opus: CONVERGED.** Verified the three round-2 fixes, but only checked `summaryMd` on the status-only path (which IS re-set via the coalesce layer) and the existing test (whose `p_video` never populated `language/ratings`), so it missed the other summary fields being dropped.

## Adjudication — Codex right; not reachable in the handler, but a real RPC regression
Traced it: a status-only persist on a fully-populated row (`(p_video - artifacts) || (v.data - artifacts - summary_keys) || …`) removes `summary_keys` from `v.data` and, since `p_video` lacks them, they vanish. The handler ALWAYS sends the full `Video` (both committed and promoted persists), so it is **not reachable in production** — but `persist_summary` is a primitive whose pre-whitelist behavior supported status-only writes, and dropping `docVersion` is a genuine trap. Fix it.

## Round-4 fix (commit below)
Rewrote the merge to preserve ALL existing fields, then re-apply ONLY the summary-owned fields `p_video` actually provides:
```
data = (p_video - 'artifacts')                     -- (1) payload defaults for a first-time bare row
     || (v.data - 'artifacts')                       -- (2) ALL existing win back: no metadata clobber AND no
                                                     --     dropped summary fields on a status-only persist
     || jsonb_strip_nulls({11 summary-owned fields FROM p_video})  -- (3) present ones win; absent → existing kept
     || jsonb_strip_nulls({summaryMd: coalesce(p_video, existing)})
     || {artifacts: existing || {summaryMd:{key, KEY-SCOPED monotonic status}}}
```
This is the canonical `base || existing-wins || re-apply-owned-subset` form. Verified against all cases: first-time (metadata+summary from payload), re-persist with concurrent metadata change (all non-summary preserved, summary updated), status-only (existing summary preserved), keyed persist (summary updated).
- New test: full persist then status-only persist preserves `language/ratings/overallScore/docVersion` (the exact Codex scenario).
- **Verified:** full guard GREEN — integration 117 (+1), unit 1588, tsc 0, confinement OK, `db reset` clean; all 25 worker-persistence + summary-handler tests pass (incl. the round-2/3 metadata-preservation, key-scoped-monotonic, archived-preservation, and Task-2 lost-update/artifact-merge/owner-mismatch tests).

## Convergence
Round 3 returned a High → round-4 re-review (dual) mandatory. Each round has found a strictly narrower issue confined to the `persist_summary` merge (genuinely intricate: two field-groups with opposite precedence). See `-v4-rereview.md`.

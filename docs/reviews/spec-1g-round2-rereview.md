# Stage 1G spec — Round-2 dual re-review (CONVERGED)

**Date:** 2026-07-10 · Spec v2 → v3. Both passes: **0 new Blocking/High; round-1 fixes verified genuine. Convergence gate met.**

## Claude (opus) — CONVERGED
Part A (fixes genuine):
- **Blocking/H2 (definer):** GENUINE. §6/D3 mandate full `security definer set search_path = public` verbatim + restated grants + no `drop function`; P17 asserts `prosecdef` + `proconfig search_path` + anon/auth executable-with-writes-succeeding (a true end-to-end proof — fails if it silently reverts to INVOKER).
- **High/H1 (positional mis-pair):** GENUINE, gate closes completely. `sameTitles` true ⟹ `parsed.sections[i].title === envelope.sourceSections[i]` ⟹ `model.sections[i]` belongs to the correct heading. Titles-drifted → 503 (P6b); can never reach the positional renderer with a stale model.
- **Reorder money-safety:** SAFE. Steps 4/5a/5b share one `begin…exception…end` savepoint (0012:57-95); an under-budget owner in a global-full window has the 5a `serve_owner_budget` increment rolled back on the 5b PJ004 raise — no per-owner phantom spend (mirror-leak absent).

Part B (new-defect hunt): savepoint scoping correct on either PJ004/PJ005; `sameTitles` read stays pure (never-charge intact); null/empty model impossible (zod requires non-optional model; corrupt → null → 503); sameTitles-true-but-count-differs cannot mis-pair (identical to a fresh serve). Consistency clean across D3/§4/§7/table. Only 2 Low wording notes (P4b could name the serve_owner_budget rollback; titles-match ≠ prose-match) — both addressed in v3.

## Codex (gpt-5.5) — no new Blocking/High
Round-1 fixes genuine (definer header + P17; D5 titles-gate; per-owner-first reorder money-safe — all verified against 0012). Part B: P4/P4b/P5/P6/P6b/P15/P16/P17 internally consistent with per-owner-5a-before-global-5b; serve-stale is a pure blob read (no gemini/reserve/write); `sameTitles` computable from parsed titles + envelope `sourceSections`. One **Low**: "version-only staleness" overstates — the gate is title-equality, which doesn't prove body prose unchanged under matching titles. Addressed in v3 (D5/P5 reworded to "title-stable staleness" with the precise positional-coherence-not-content-identity guarantee).

## Disposition
Round-2 returned only Low wording (both passes) → **convergence**. v3 applies the wording clarifications (D5/P5/P4b/R4). No design change. Ready for user spec-approval.

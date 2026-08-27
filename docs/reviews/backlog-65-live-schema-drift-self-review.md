# Backlog 65 — drift detection in `check-live-schema.py`: the AUTHOR'S SELF-REVIEW

> ⚠ **THIS IS NOT THE CLAUDE HALF, AND ITS ORIGINAL FILENAME SAID IT WAS.** It was
> `…-claude.md` — the exact convention a genuine independent half uses — with the
> disclaimer only inside. That is *"the absence of a reviewer looks exactly like the
> presence of a clean one"*, the sentence `check-review-rounds.py` exists to enforce,
> reproduced in the artifact warning about it. Renamed 2026-08-27.
>
> The real independent half is
> [`backlog-65-live-schema-drift-claude.md`](backlog-65-live-schema-drift-claude.md).
> It found **1 High, 3 Medium, 4 Low — NOT CONVERGED**, including a High that neither
> Codex nor this self-review found. Kept as evidence of what a self-review does and
> does not catch.

**Date** 2026-08-27 · **Subject** `scripts/check-live-schema.py`, `scripts/mutate-live-schema-check.sh`
**Codex half** [`backlog-65-live-schema-drift-codex.md`](backlog-65-live-schema-drift-codex.md) — 1 High, 1 Medium, 1 Low, all accepted and fixed.

REVIEW GAP: claude — not invoked as an independent fresh-context reviewer. This session is under a
standing instruction not to spawn subagents, so this half was written by the **implementing agent**.
That is materially weaker than the process requires: an author reviewing their own work shares every
blind spot that produced it, which is the exact failure `dual-review-halves-are-not-redundant`
records. **Re-run this half with a fresh subagent before treating the round as converged.** What
follows is therefore evidence, not an independent verdict.

---

## 1. What was verified BY EXECUTION, not by reading

| Claim | How it was falsified |
|---|---|
| The guard is load-bearing | Reverted `unexpected()` to `HEAD`, kept the harness → **exactly 1 of 48** assertions went red, and the `✅ every mutation caught` banner disappeared. Harness `exit "$fail"` → 1 |
| The red is caused by the mutation, not the clone | `green → add column → red → drop column → green`. A red on a scratch clone alone proves nothing |
| Drift-only failures actually print something | Ran `main()` with one injected column: exit 1, object named, remedy printed |
| Both refusal branches work | Injected a dotted identifier → exit 2; stripped `table:`/`view:` from the manifest → exit 2. Baseline unchanged at exit 0 |
| The bound probes really landed | Desynced the index name from its postcondition → `DID NOT LAND (got '0', wanted 1) — treat this bound as NOT RUN`, harness exit 1 |
| Prod is unaffected | `--prod --expect-present` exit 0 before and after; 161 objects; anon surface still 10 |

## 2. Defects found in my own work, by executing rather than reading

**M1 — the drift report opened with a dangling conjunction.** With drift as the only failure the
first line read `⛔ AND 1 object(s) …`, continuing a sentence nothing had started, because the block
was written to follow the missing/redefined reports. Fixed with a joiner conditional on prior output;
both branches asserted. **A self-test proves the verdict, never the message.**

**M2 — the empty set passes.** `unexpected()` returns `set()` when `owned_relations()` is empty, so a
manifest that parses but names no table or view would report CLEAN over any database at all. This is
the same defect class `load_manifest` already guards one level up (r4 B2), reappearing in the new
code — *the guarantee was carried across in one direction only*, which is this file's own r5 B1
lesson. `main` now refuses with exit 2, and two self-test cases pin it.

**M3 — a failed probe reddened its neighbour.** Found while falsifying `landed`: the misnamed index
left `drop index m4_mut_idx` to abort its block under `ON_ERROR_STOP`, so the removed-column
assertion reported MUTATION SURVIVED for an unrelated reason. Cleanup is now `if exists`. Failing
loudly is right; failing loudly in the *wrong* assertion sends the next reader to the wrong defect.

## 3. Codex's findings — adjudicated by re-derivation, not accepted on sight

**High + Medium share one root cause, and it is not a parser bug.** `CATALOG_SQL` builds
`relname || '.' || objectname` unquoted, so `col:workspaces.audit.seen` is *genuinely* both a column
on `"workspaces.audit"` and a column `"audit.seen"` on `workspaces`. `split` yields Codex's false
positive; `rsplit` yields its false negative. **Choosing either is choosing which error to make**, so
the gate refuses (exit 2) instead. Measured on both subjects first: prod and local hold 391 objects
each and **0** ambiguous ones, so the refusal is unreachable today — which is why it must exist
before something makes it reachable.

**Low accepted as written**, and it was the sharpest of the three: two bound probes asserted the gate
*passes*, so if their SQL never landed they would have certified a bound nothing tested.

## 4. Bounds — stated, and asserted as PASSING cases so widening them turns a test red

- **Indexes.** `idx:` carries no relation name; a bare `create unique index` on an M4 table is still
  invisible. Closing it means changing the catalog rendering and regenerating all 161 manifest
  entries — its own slice.
- **The 27 manifest objects on 4 FOREIGN relations** (`videos`, `playlists`, `jobs`, `profiles`).
  Not M4's to bound: a future migration adding a column to `videos` is legitimate.
- **`fn:` and `type:`** attach to no relation. Added functions are `check-anon-exposure.py`'s subject.
- `verdict()` does **not** enforce its own preconditions — `main` does. A future direct caller of
  `verdict()` bypasses both refusals. Recorded in its docstring; not fixed, because raising from a
  pure predicate would complicate every existing caller for a hypothetical one.

## 5. Verdict

**CONVERGED on the evidence available — but the round is NOT converged procedurally**, because the
independent half named above never ran. Nothing here is blocking; the residual risk is that an author
who missed a defect once will miss it twice.

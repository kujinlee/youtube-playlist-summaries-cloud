# Round 8 — `plan-586-redesign` — coordinator — Codex NOT CONVERGED: two BLOCKERs on the final tree; the DEFER bet is refuted and the ladder is spent

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the FINAL TREE of the plan at 98606433, reviewed by Codex at
`docs/reviews/codex/plan-586-redesign-r8-codex.md` (2 BLOCKER). Both were built as running code on the extracted
Task 7.2/7.3 blocks, each with a control (25 assertions).

```yaml
round: 8
fixes_nontrivial: false
subject: plan-586-redesign
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: B1, severity: High, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: filed}
  - {id: B2, severity: High, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: filed}
```

## What held

The r7 fold held on everything it touched. Malformed headers, a runner clock more than an hour off, the exact
+31-day boundary and in-progress runs do not establish finality. The guard's rebuild refuses inserted, removed and
altered observations. A part-way failure publishes nothing.

## B1: a final observation freezes evidence that absorb discarded

Absorb keeps the existing row when it is already a `miss`. It still records the report's identity and its final
observation. A legal attempt 2 that adds a second miss (`y.py`) is therefore absorbed without that miss. After an
owner reset archives the ledger, `settled` is True for the run, and `y.py` is never compared again.

## B2: the report listing is capped too, and truncation hides tightening evidence

`list_reports` walks the `shadow-compare.yml` run listing, which is capped at 1,000 results like the CI listing in
backlog #595. `runs_from_listing` discards `total_count`. A 1,001st run carrying an unabsorbed miss is never listed,
and the guard accepts the unchanged ledger. Truncation here OPENS rather than closes, unlike #595.

## Not fix-induced, and still one component

Neither finding came from the r7 fold. Both are older paths that r2–r7 did not reach. They are the same shape
as the thrashing: evidence that a run's state is complete is taken from a source that is not complete (a capped
listing, an absorb that keeps the first row). They are marked `fix_induced: false`.

## Disposition: the owner decides

The defer row (r7) bet that r8 would find no BLOCKER. It is refuted. Every route on the ladder (accrete,
redesign, split, defer) has been used, so the next step is the owner's. Both findings stay `deferred` until the owner
answers. The defer row's outcome is left open until then.

## Owner decision

2026-11-10, selection card A: the plan is SPLIT. Slices 1-5 go forward in the plan PR and get built; slices 6-8 return
to a spec revision before they are planned again. B1 is filed as backlog #597, B2 as backlog #598, and the spec
revision as backlog #599 (inputs: #592-#596, #597, #598; trigger: slice 4's first master runs, Task 4.3).

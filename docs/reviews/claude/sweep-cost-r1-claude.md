Reviewed head: bf1545272bf0a030af3275fde116d2d0b52bf260

# sweep-cost — round 1, Claude half (adversarial, mandate: REFUTE)

Subject: `git diff origin/master...HEAD` (origin/master = `f7ff7eb0`). The branch touches
`scripts/gen-backlog-page.py` (it puts `functools.lru_cache` on `layout_body` and memoises `_drifted`),
`docs/backlog.md` (rows 559 and 560) and `docs/dashboard-entries.md` (one entry).

## What I ran

| Check | Result |
|---|---|
| `python3 scripts/gen-backlog-page.py --self-test` in the worktree, timed | 247/247 passed, rc=0, real 24.9 s |
| The same in a scratch `git clone` of HEAD (the control for the mutants) | 247/247, rc=0, real 32.3 s |
| Do all 77 `scripts/mutations/gen-backlog-page.json` anchors still bind exactly once at HEAD? | yes, 0 bad (28 of them are inside `layout_body` or its callees) |
| master's suite (`f7ff7eb0` file) under cProfile, in the clone | 247/247. `layout_body` cumulative 159.2 s of 270.6 s = **58.8%**, 21,040 calls. The comment's "~60% of the suite's CPU" holds |
| `check-docs.py`, `check-dashboard-entry.py` | both rc=0 |
| Manifest entry counts derived from git: `756c41fa` (last master commit of 2026-09-15) / `c3d85c6d` / HEAD | 643 / 4,093 / 4,093. Row 559's numbers hold |

The mutants were applied to `scripts/gen-backlog-page.py` inside a scratch `git clone` of HEAD, never
to the worktree. Each one was restored in a `finally` block, and afterwards `git status` in the clone
was clean.

| Mutant (my own, not in the manifest) | Where | Result |
|---|---|---|
| M1: `layout_body` drops its last block (`merged[:-1]`) | `layout_body` return | **RED**, 227/247 |
| M2: `layout_body` loses the `prov` class (always `"seg"`) | `layout_body` return | **RED**, 243/247: four provenance cases |
| M4: `_enum_cuts` needs a run of 3 (`len(run) >= 3`) | callee | **RED**, 244/247: `unlaid_rows` ×2, `(1) (2) run` |
| M5: `_label_cuts` also takes a label ending in `.` | callee | **RED**, 246/247: `bare marker` case |
| M3: `cuts = [c for c in cuts if c >= ps]` (was `pe`) | `layout_body` | green, 247/247. **Equivalent, not masked:** `_prov_span` returns None if a `<strong>` lies inside the span, and the glyph/marker carry stops at the span's closing `.`, so no label cut can fall in `[ps, pe)`. The same mutant is green on master. This branch did not cause it, so it is not a finding |

## The four questions

1. **Is `layout_body` pure?** Yes, as far as this suite exercises it. It and its callees (`_layout_text0`,
   `_layout_depth0`, `_label_cuts`, `_visible_before`, `_prov_span`, `visible_text`, `_enum_cuts`,
   `_enum_run_ok`, `_layout_block`) read only their argument and the module-level `_LAYOUT_*` compiled
   regexes and constants. They read no environment variable, file or clock. The suite rebinds module
   names in exactly four places: `BACKLOG` and `attach_history` at :3396–3397, `HOME` at :3408, `GROUPS`
   at :3806 and :3826, and `LEGEND_SCHEMAS` at :4283. **None of them is read by `layout_body` or a
   callee.** No case rebinds a `_LAYOUT_*` name, `LAYOUT_MIN_CHARS` or a layout helper. Its only value
   is `str`, which is immutable, and an exception is not cached.
2. **Can the cache let a mutant survive?** It cannot here. Under `--mutate`, each mutant's suite runs as
   a fresh `python3 <copy> --self-test` subprocess, and that matches how I ran it. So the cache is
   filled by the mutated function. Four constructed mutants went red, and so did every manifest
   anchor's binding. The only way a memo can mask a mutant is if the same process changes the function's
   inputs between calls, and question 1 rules that out today. See R1-F2 for the part that rests on
   convention.
3. **Hashable and keyed on everything?** `lru_cache` takes a single `str` argument, which is hashable.
   `_drifted` is keyed on `tuple(unread)`. Its other inputs are `_gnum`, which is fixed in the closure,
   `BACKLOG.read_text()` and `GROUPS`/`DEPENDS`. All 7 calls (:3300, :3340, :3342–3343, :3348–3349)
   run consecutively, **before** the first swap of `BACKLOG` (:3396) or `GROUPS` (:3806). So the key
   covers every input that varies across those calls. `build` treats `unread` as a read-only `Sequence`.
   The memo is also per-call-of-`_self_test_body`, so it cannot leak across runs.
4. **Anything stated as MEASURED that was not?** I verified the counts I could derive locally. They are
   643 → 4,093 entries, 77 entries for this target, a mean of 53.2 s (4,098/77), 20.4% (4,098/20,076),
   about 60% CPU, and a suite time of about 25–30 s. I did **not** re-derive the CI-run figures, because
   the brief says not to touch GitHub. Those are run 42432742676's 20,076 s and per-target table, and
   the "2 real survivor reds in 200 runs". They cite a run ID, so they have provenance. One claim cites
   none: see R1-F1.

## Findings

### R1-F1 — Low — "77 entries all still killed" is stated with no run behind it
`docs/dashboard-entries.md` (the 2026-11-07 entry, `<!--tech-->` paragraph):
*"247/247 cases, 77 entries all still killed; no entry, case or pin changed."*
- **Scenario:** a reader takes "all still killed" as a measurement of this branch's file. Every other
  number in the paragraph names its source: a CI run, a commit or a timing triple. This one does not.
  I could not verify it within the brief's 270 s bound, since 77 × about 27 s is about 35 min.
- **Repro:** look in the entry for a command, a run ID or a log for the per-entry result. There is none.
  `--only scripts/gen-backlog-page.py` would produce one.
- **Fix:** cite the source, e.g. "(`check-plan-code.py --mutate . --only scripts/gen-backlog-page.py`,
  77/77 killed)" or this PR's CI sweep run ID. If neither was run, say "anchors verified; per-entry
  verdict from this PR's sweep". Doc-only.

### R1-F2 — Low — the cache's soundness rests on a convention no guard observes
`scripts/gen-backlog-page.py:1070–1075` (the comment above `@functools.lru_cache`).
- **Scenario:** a future self-test case rebinds a layout input in-process, e.g.
  `globals()["_LAYOUT_PROV_WORDS"] = 5`, the same pattern the suite already uses for `GROUPS`. It then
  asserts on `layout_body(x)` for an `x` that an earlier case or page build already laid out. The cache
  returns the unpatched answer. That case passes vacuously, and a mutant that its assertion should kill
  survives. The comment argues only "each mutant is its own process". It does not name this
  same-process hazard, which is the one that can actually bite.
- **Repro (hypothetical, nothing does it today):** add a case that sets
  `_LAYOUT_PROV_WORDS = 0`, calls `layout_body` on a row already rendered by `_built`, and asserts the
  provenance is not split. The memo returns the earlier split HTML.
- **Fix:** add one sentence to the comment: *"⚠ any case that rebinds a `_LAYOUT_*` name or a layout
  helper must call `layout_body.cache_clear()` before and after"*. Optionally, call `cache_clear()` at
  the top of `_self_test_body`. A guard is not warranted at this size. File it rather than fold it if the
  round cap applies.

Neither finding blocks or changes coverage. The change does what it claims. I found no input the cache
answers stale, and no constructed mutant inside `layout_body` or its callees survived because of it.

VERDICT: CONVERGED

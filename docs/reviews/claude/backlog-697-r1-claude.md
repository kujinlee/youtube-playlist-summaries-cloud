Reviewed head: aac34e33398dec90489f57584a0f90384d9b464f

# backlog-697 (PR #621) round 1, Claude half

Scope: `git diff origin/master..HEAD` (base d0db35d3), 5 commits. Adversarial: each claim below was attacked with an input I built and ran.

## The acceptance test (backlog row 697, Fails if): HOLDS at this head

- `python3 scripts/build-shipped-corpus.py --out <scratch>` built 180 files, PASS. I compared it with the recall package's
  `installed_files` that sit under `docs/memory/` and `docs/marketplace/shipped-corpus/` (179), matching by basename:
  **built minus package = `MEMORY.md` only; package minus built = none; byte differences = none.** The six paraphrases in the
  package are byte-identical to what the builder emits.
- None of the 16 A–C names appear in the package. No raw D source does either: the real-repo case `decision5_gaps(real recall) == []` passes, and in a
  full clone `--closure` printed `0 gaps`, rc 0.

## Claims checked

| Claim | Result |
|---|---|
| `memory-corpus` lists 179 files = 173 + 6, with 23 exclusions | Measured: 179 files, 23 `docs/memory/` exclusions, no overlap. The only tracked file in either directory that is in neither list is `shipped-corpus/sources.json`, and `--map` is rc 0, so it is covered elsewhere |
| `--closure` reads decision 5 through the builder's `groups`/`_canon_sha`, and an unreadable table is rc 2 | When the table is missing: rc 2, `CANNOT RUN: decision 5 cannot be read` (that case passes). When a NAME moves: rc 1 with a traceback (finding M2) |
| Self-test 140→149, mutations 195→201, edge 361→362 | `--self-test` 149/149 (87 s). The manifest has 201 entries and `expected_mutations.py` says 201. The edge pin case passes. **The dashboard entry says 140 -> 148** (N1) |
| Each new mutation dies on its named case | Verified in a FULL `git clone` at aac34e33, 3 of 6: NAME clause (#1) → its named case red, plus 3 others; plugin skip (#4) → its named case red, only that one; table→`{}` (#6) → its named case red, only that one |
| CI's non-self-test `check-*` steps | 36 run on this worktree: 35 rc 0; `check-inventory` rc 3, which CI prints and passes. `check-review-rounds` rc 1 **only because this half was not yet written**. `check-selftest-counts --changed` flags `check-plan-code.py --self-test` red on 3 `node_modules/typescript` cases: the worktree has no `node_modules`. That is environmental and this PR did not cause it. **Treat `check-plan-code` self-test as NOT RUN here** |

## Attack results

- **Renamed path, CRLF, trailing whitespace** (`_canon_sha` = `splitlines`, `rstrip` per line, trailing blank lines dropped): an exact
  or whitespace-only copy under any name is caught. An altered frontmatter line, a BOM or a one-character edit passes. That
  matches the docstring's stated BOUND and is outside the Fails-if, which says "bytes equal".
- **A–C file with a changed byte under its own name**: caught by the NAME clause, whatever its bytes (the case passes).
- **Every package kind**: `CHANNELS = ("plugin", "reusable-workflow")`, and both are run through `decision5_gaps`, before the SKIPPED line for
  reusable-workflow. A directory entry (`docs/memory`) in a reusable-workflow component gives CANNOT RUN rc 2, and a glob
  gives REFUSED rc 1, both from the map loader, so neither can slip past the `is_file()` skip.
- **Recall at the install site (attacks 2 and 3)**: `scripts/recall-llm.py:417` `memory_dir()` reads only
  `~/.claude/projects/<slug>/memory`, and `memory_files()` (line 432) drops `MEMORY.md`. So the recall code never reads the installed
  `docs/memory/` or `shipped-corpus/` at the install site, with or without the index. The spec already says so: §C5 row,
  r6 CLAUDE M7, "a stranger gets the corpus as documents and no working recall". It is not a defect of this PR and it is
  not against decision 5, which says nothing about the index. See M1 for the cost of the divergence.

## Findings

### M1 MINOR (corpus-declaration): the package is the built corpus minus its index, and the paraphrases are not under `docs/memory/`
- `docs/marketplace/components.json:681` (memory-corpus notes), plus the `docs/memory/MEMORY.md` exclusion at :1044.
- Input: build `--out` and diff it against the package (above).
- Observed: the builder emits a FILTERED `MEMORY.md`. I checked it: it links no A–C file and has no dangling link. The package drops the index instead. The
  stated reason, "a tracked-file stager cannot" ship a transformed file, is the same problem the D paraphrases solved by
  committing their output under `shipped-corpus/`. The backlog Fix said "repoint at the BUILT corpus". The dashboard's
  plain-language line says the index "links the excluded files", which is true of the raw index and not of the built one.
  Separately, the six D lessons install at `docs/marketplace/shipped-corpus/<name>`. A user who copies the installed
  `docs/memory/` into their harness memory directory (the only place `recall-llm` looks) therefore gets 173 lessons, no D lessons and no index.
- Expected: the package equals the builder's output, or the divergence is stated as a decision.
- Fix: commit the builder's filtered index as `shipped-corpus/MEMORY.md`, have the builder keep it fresh, and list it. Or record "the index does not ship" as a
  decision with its reason corrected. Either way, say in the plan note that the D files install outside `docs/memory/`.

### M2 MINOR (closure-guard): a moved builder name is rc 1 with a traceback, not CANNOT RUN rc 2
- `scripts/check-shipping-sets.py` `_corpus_builder` / `decision5` (the `try` catches only `OSError, b.CannotRun`, and the
  load sits outside the `try`).
- Input, run in a full clone: (a) rename `def groups(` in `build-shipped-corpus.py`; (b) rename `def _canon_sha(`; (c) remove
  the builder file.
- Observed: in all three, `--closure` exits rc 1 with `AttributeError` or `FileNotFoundError`. rc 1 is this script's "gaps
  found". It is loud, so it does not fail open, but the brief claims CANNOT RUN, and PR #620 (backlog #698) is rewriting that
  file now.
- Expected: rc 2 `CANNOT RUN: decision 5 cannot be read: build-shipped-corpus.py has no groups`.
- Fix: put the load and the attribute lookups inside the `try`, catch `AttributeError` and `ImportError` too (or check with `hasattr`), and add one
  case where the builder lacks a name and the result is rc 2.

### M3 MINOR (mutations): canonical matching is not witnessed at the call site
- `scripts/check-shipping-sets.py` `decision5` (the `sources` dict) and `decision5_gaps` (`hit = …`).
- Input: replace `_canon_sha` with the builder's raw `_sha` at BOTH sites.
- Observed: **149/149 pass, so the mutant survives.** No case ships a source copy with CRLF or trailing whitespace, so
  the docstring's "CANONICAL hash … under any name" is untested here. The builder's own suite tests `_canon_sha`, but
  coverage does not compose across a call site. Replacing only ONE site does die, because the hash domains no longer match.
- Fix: add a case where a D source copy with CRLF endings and a trailing space, under another name, is a gap, and add a mutation (raw `_sha` at both sites) that dies on it.

### N1 NIT (docs): the case counts disagree
- `docs/dashboard-entries.md` (the 2026-11-23 tech block) says "Self-test 140 -> 148". The suite prints 149, and the
  docstring and the brief's pin say 149. The brief's "8 new cases" is also 9: 4 unit, 3 CLI, the identity case and the real-repo case.
- Fix: change it to 149 (+9).

VERDICT: CONVERGED

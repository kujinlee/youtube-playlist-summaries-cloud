Reviewed head: e89789ff30031be039db06da2690f3c850397a9a

# Round 3 — 586-slice1 — claude

Subject: PR #557, branch `586-slice-1-strace`, head `e89789ff`; the round-2 fold is `ea13a38a..e89789ff`.
Mandate: REFUTE. All experiments ran on a COPY outside the repo: a probe that imports `scripts/strace-measure.py` and
feeds `analyse_log` constructed logs, and a mutation runner that rewrites a copy of the script (in a scratch tree with
`fixture_git.py` and `fixtures/strace-lines/` beside it) and runs its `--self-test`. The control (unmutated copy) passes
54/54.

## Gates run (on the worktree, head e89789ff)

| check | result |
|---|---|
| `python3 scripts/strace-measure.py --self-test` | 54/54 passed |
| `python3 scripts/check-fixture-variation.py` | OK (2 unrelated `⭐ codex-review.py … now varies` notes) |
| `python3 scripts/check-ratchet-contract.py` | ratchet contract OK |
| `python3 scripts/check-fixture-git-isolation.py` | ok — 98 scripts isolated, 0 exempt |
| the doc's figures vs the three JSONs | match (see Q4 below) |
| a live strace run | NOT RUN — macOS host, no strace; every reader claim below is from constructed lines through `analyse_log` |

## Findings

### F1 — High — a removal through a symlink (or `..` after one) is resolved LEXICALLY, so it can go entirely unlisted

`scripts/strace-measure.py:168` (`resolve` → `os.path.normpath`) and `:278` (`inside`). Docstring `:23-24` says every
removal "whose path resolves outside the copy is LISTED"; the doc (`2026-11-10-strace-on-runner.md:98`) says every
successful removal outside the copy "is listed".

Inputs run (copy root `/t`):

| input | result |
|---|---|
| `1 symlink("/home/runner", "/t/ln") = 0` / `1 unlink("/t/ln/.gitconfig") = 0` | `external_removals` **[]**, `unresolved_removal_count` 0 — the real `~/.gitconfig` is deleted and nothing lists it |
| `1 unlink("/t/ln/../x") = 0` (`ln` a symlink out of the copy) | **[]** — `normpath` collapses `ln/..` to `/t`, the kernel does not |

`-yy` decorates file descriptors, never path STRING arguments, so an absolute or dirfd-relative path string that
traverses a symlink is never physically resolved. The staged copy starts symlink-free (`stage_tree` uses `copytree`
without `symlinks=True`), but suites create symlinks at run time: `symlink` is in 31 of 92 targets (run 42893595762,
MEASURED in the doc), and e.g. `scripts/check-review-recorded.py:2796` symlinks the real `scripts/` into a temp dir and
`scripts/compaction-state.py:1865` does `os.symlink(outside, …)`. Whether any of run 42915171820's removals took this
path CANNOT be read from the committed JSON (no lines are kept for paths judged inside the copy).

Answer to the brief's Q1: **yes, a successful removal of a path outside the copy can still go unlisted.**

Fix: record every symlink the log creates (`symlink`, `symlinkat`, with the resolved link path); a removal whose
lexical path has a created symlink as a proper prefix component, or contains `..` after any component not known to be
a real directory, is UNRESOLVED (counted, sampled), never judged inside. State "lexical" in the docstring and the
doc's removal row, and say slice 2's parser must resolve symlinks (it already must follow cwd, `:107-111` of the doc).
A self-test case per input above. FIX-INDUCED: **no** (lexical resolution predates r2), but the fold's new claims at
doc `:98` and `:101-102` ("can no longer hide one") are refuted by it.

### F2 — Medium — "under a created DIRECTORY ⇒ created" annotates a pre-existing file reached through a symlink as created, and nothing lists it as not-created

`scripts/strace-measure.py:265-270` (`kind_of`), used at `:327`.

| input | result |
|---|---|
| `mkdir("/external/d")` / `symlink("/home/runner", "/external/d/s")` / `unlink("/external/d/s/.gitconfig")` | `[("/external/d/s/.gitconfig", created_in_log=True)]`, counts `{created: 1, not_created: 0}` |
| `mkdir("/tmp/d")` / `symlinkat("/home/runner", 3</tmp/d>, "s")` / `unlinkat(3</tmp/d>, "s/.gitconfig", 0)` | `[("/tmp/d/s/.gitconfig", True)]`, `not_created: 0` |

The r1 case "under a created SYMLINK it is not" covers a symlink AT THE TOP; a symlink INSIDE a created directory
inherits the directory's "created". On the runner every `mkdtemp` is a successful `mkdir`, so every temp dir is a
"created directory" — exactly where suites put their symlinks. The headline "**0** annotated not-created" therefore
cannot exclude a pre-existing file deleted through such a link; and the doc's sentence that a wrong annotation
"mislabels a removal and can no longer hide one" (doc `:101-102`) is true of the LIST but false of the
not-created COUNT, which is the figure the doc leads with and slice 2 "decides its refusal rule from".

(Related, acceptable: a pre-existing directory renamed INTO a created one — `mkdir /tmp/d; rename /home/runner/data
/tmp/d/data; unlink /tmp/d/data/f` — annotates `f` created, but the rename's SOURCE is listed not-created, so the
loss is still in the not-created bucket. `RENAME_EXCHANGE` probes annotated correctly.)

Fix: track created symlinks with kind `"symlink"`; `kind_of(p)` returns None when any component between the created
directory and `p` is a created symlink (or a path that arrived by a rename from a not-created source). Cases for both
inputs. FIX-INDUCED: **no** for the rule (r1), **yes** for the doc claim that leans on it.

### F3 — Medium — three r2 fold behaviours survive mutation; one case is satisfied by the constant its own fixture supplies

Mutations run on a copy of the script, each against the full self-test (control 54/54):

| mutation | targets | self-test |
|---|---|---|
| `forget` drops only the exact path, not its subtree (`:274`, `if c == p`) | the docstring's "CLEAR the evidence for that path **and its subtree**" | **54/54 — survives** |
| `per[note] = max(...)` → sum over seeds (`:559`) | the per-target removal count feeding the 63,720 total | **54/54 — survives** |
| `targets_with_not_created` → `len(removal_counts)` (`:608`) | the doc's "in 0 of 92 targets" | **54/54 — survives** |

The third is the *constant-from-the-fixture* shape: case `r2 X1 merge totals the removals by annotation` (`:876-878`)
has ONE target, and that target has a not-created removal, so "targets with not-created" and "targets" are both 1.
On run 42915171820 they are 0 vs 92 — the mutation would have published "in 92 of 92 targets". The second: every
`_shard` has one seed (`"seeds": [0]`), so max and sum coincide. The first: no case creates a path BELOW the one
being cleared (e.g. `mkdir d; mkdir d/e; rmdir`-or-`rename d …; rename /pre /…/d; unlink d/e/f`).

Killed as claimed (verified): no forget (4 red), no exit orphaning (2), `killed` not orphaned (1), unpaired null
condition (2), totals null condition (1), re-exempting created (6), annotation from the dict only (4), and the two
`check-fixture-variation` exemptions' named mutations — sample store no-insert (1 red), wrong owner (1 red), merge
reads only the last directory (2 red). **Both exemptions are earned.**

Fix: a two-target merge case where only ONE target has not-created removals (want `targets_with_not_created: 1`);
a two-seed record with different counts (want the max); a subtree-clearing reader case. Low-priority survivors in the
same pass: `KEEP_REMOVALS` bound `<=`→`<` and the merge's created-path `[:20]` → `[:1]` both survive (no case
exceeds a cap). FIX-INDUCED: **yes**.

### F4 — Low — FAILED removals are listed and counted, but the doc says "every successful"; the merge drops `ok`

`:320-331` lists and counts a removal whatever `ok` is (`unlink("/home/runner/absent") = -1 ENOENT` → listed,
`not_created_in_log: 1`). `by_note` does not split by `ok`, and `merge` (`:549-552`) keeps only the path, so the
63,720 cannot be split into removals that happened and attempts that failed. Listing failures is conservative (an
over-report), but doc `:98` claims "every successful … is listed", and the COUNT is presented as removals.
Fix: count `by_note` per `ok` (or exclude failures from the counts and keep them listed), carry it into the merge,
and word the doc row to match. FIX-INDUCED: **yes** (the counts are new in r2).

### F5 — Low — the doc's removal and ratio figures from run 42915171820 omit two facts about how they were made

1. **63,720** is the SUM over targets of the MAX over the two seeds (`:559`, `:606`), not the number of removals
   observed; the row does not say so (and F3 shows the aggregation is unpinned).
2. Run 42915171820's `not_green` is `scripts/regen-pages.py` **traced, both seeds** (MEASURED, run3 JSON) — and that
   red traced run (seed 0, 146.04 s) is this run's TRACE_FACTOR witness in the doc's table (`:55`). The ratio of a
   suite that failed under strace is not a healthy traced duration. It does not move the committed 20, but the row
   should say the witness was red (and `merge` arguably should exclude non-green records from `ratios`).

FIX-INDUCED: **yes** (run 42915171820's figures were added by the fold).

### F6 — Low — the r2 "null unless every record measured it" rule was applied to two fields, not the class

The fold (r2 Codex X2) made `unpaired_halves` and `external_removal_totals` null unless every record carries the
field. The same `tr.get(...)`-defaults-to-empty pattern remains for `unresolved_removals` (`:560`),
`refusal_triggers` (`family_counts`), `deleted_labels` and `at_fdcwd_decorated`; and a record with
`log_missing: True` (`:484`) is read by nothing in `merge`, so a traced run with no log contributes "no refusal
trigger" silently (a red traced run still appears in `not_green`, which limits the damage). Not observed in the three
committed runs (`external_removal_coverage` and `unpaired_halves_coverage` are 184/184 in run 42915171820).
Fix: one coverage count over the analysed fields (records with the analyse output vs records), and null the derived
tables when it is short; surface `log_missing`. FIX-INDUCED: **no** (instance-not-class of the fold).

## Q2 — exit orphaning, multi-threaded

`+++ exited`/`+++ killed` are per TID under `strace -f`, and `pending` is keyed by that TID, so a sibling's
`exit_group` does not orphan another thread's pending half. Probe: `7 unlinkat(3</external>, <unfinished ...>` /
`8 exit_group(0) = ?` / `7 <... unlinkat resumed>"v", 0) = 0` / `7 +++ exited` / `8 +++ exited` → `/external/v` listed,
0 unpaired. Correct. An `execve` from a non-leader thread prints `+++ superseded by execve in pid N +++`, which
`EXITED` does not match and `LINE` cannot parse: it lands in `unparsed_lines` and the halves are counted unpaired —
noisy, never a hidden removal. No finding.

## Q4 — doc vs the three JSONs

Every checked figure matches its run id: run ids/shas in each header; 118 syscalls and the same 7 ioctl tokens in all
three; `AT_FDCWD` decorated in 92; TRACE_FACTOR 20 / 12 / 15 with the stated witnesses; refusal triggers
(`io_uring_setup` only) and the 28 unresolved-removal targets IDENTICAL as sets between 42893595762 and 42915171820;
run 42915171820: `created_in_log` 63,720, `not_created_in_log` 0, `targets_with_not_created` 0, records 184,
coverage 184/184, `check-rc-contract.py` 9,622, `batch-ci.py` 6,316. Whether "0 not created" is what slice 2 needs:
the figure is true of what this reader can see, and is bounded by F1 (lexically-inside removals are never examined),
F2 (symlinks under temp dirs annotate as created) and the 28 unresolved targets the doc already caveats. The doc
should state the first two bounds beside the 0, as it already does the third.

## Count

High 1 (F1), Medium 2 (F2, F3), Low 3 (F4, F5, F6). Fix-induced: 3 (F3, F4, F5); F2's doc claim is fix-induced,
its rule is not.

VERDICT: NOT CONVERGED

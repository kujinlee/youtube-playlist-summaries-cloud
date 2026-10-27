# diff-coverage — round 1, Claude half (adversarial)

Subject: PR #411, branch `diff-coverage`, head `772e0ab8`, reviewed as `git diff origin/master...HEAD`
(origin/master = `4aaa6ed7`). Every experiment ran in fresh copies under
`scratchpad/dcr1.VnRP/` (clones `repo`, `br`, `p4`, `sh`), never in the worktree. Python 3.14.4 locally,
plus 3.12 (the CI pin) where noted.

## What holds (executed)

- `check-diff-coverage.py --self-test`: 23/23 on 3.14 and on `/usr/local/bin/python3.12`.
- `check-plan-code.py --mutate . --only scripts/check-diff-coverage.py` (full clone, `node_modules` with
  typescript): **10 mutations, 10 killed, 10 attributed to the case each names, 0 survivors**.
- `check-merge-ready.py --self-test`: **211/211**. It includes "the derivation finds exactly the FIVE
  steps ci.yml gates today" over the real workflow, and the stray-mention ratchet accepts the new
  `if: github.event_name == 'pull_request'` line at its new allowance of 5. Verdict logic is untouched:
  merge-ready still *invokes* only dashboard-entry, review-recorded and review-rounds. The new step,
  like namespaces and doc-citations, reaches the verdict only through `gh pr checks`. So its verdicts
  are unchanged.
- These were all green on the branch: `check-selftest-counts` (61 scripts verified), its `--self-test`
  (18/18), `check-fixture-variation` and its `--self-test` (67/67), `check-ratchet-contract` (it
  discovers the new guard), `check-main-drivable`, `check-rc-contract`, `check-docs`,
  `check-dashboard-entry --base origin/master`, `check-reference-namespace`, `check-doc-citations`.
- CANNOT RUN coverage:
  - An unknown base gives rc 2 (self-test).
  - A non-repository gives rc 2 (self-test).
  - **Shallow clone, executed:** `git clone --depth 1` plus a depth-1 fetch of master printed
    `CANNOT RUN — ... no merge base`, rc 2.
  - Refused manifests give rc 2 (self-test, with the real loader).
- Diff parsing, executed by probe:
  - `+N,0` deletion hunks add nothing.
  - `+++ /dev/null` is ignored.
  - `\ No newline` lines are ignored, because nothing matches them.
  - A rename shows only its changed lines, because three-dot diff keeps rename detection on.
  - Multi-line `if`/`elif`/`while` tests flag every test line. An `elif` chain flags each arm.
    `raise SystemExit(...)`, module-level `sys.exit(main())` and an `if __name__` test are all flagged.
- The headline claim holds. On master, `check-hook-commands.py:80` mutated to `if True:` leaves that
  suite **22/22 green**, so the warning on that line on `hooks-absolute-path` is a genuine survivor.
  `hooks-absolute-path` against `origin/master` reproduces **29** warnings exactly.
- Same-text-elsewhere (attack 2): the harness refuses any anchor whose count ≠ 1 (`check-plan-code.py:2412`,
  `:2672`). Over all 2,160 real entries, **0** edits have an anchor count ≠ 1 in the delivered source. So
  "every occurrence" in `anchor_lines` cannot over-clear today; mutating it to first-occurrence-only survives
  as an equivalent mutant. A different over-clear does exist (finding 3).

## Findings

### 1. MEDIUM: decision changes on continuation lines, in ternaries and in comprehension filters are invisible, and the summary then says "every one is reached"

**Where:** `scripts/check-diff-coverage.py:124-125` (`Return`/`Raise`/`Assert`/`ExceptHandler` add
`node.lineno` only) and `:191-192` (the all-clear wording).

**Evidence (executed).**
- In clone `p4` I committed two one-line decision changes to manifested scripts:
  - `check-merge-ready.py:642`: dropped `and not is_comment(l[1:])` from the filter on the continuation
    line of a multi-line `return [... for l in hk\n if ...]`;
  - `check-diff-coverage.py:317`: `sys.stderr if code == 2` became `code == 1`.
- `run_check(root, "HEAD~1")` printed:
  `diff coverage: 0 changed decision line(s) with no anchor, across 2 manifested script(s) changed against HEAD~1 — every one is reached`.
- Neither line is anchored. The output is a false all-clear: "every one is reached" says an anchor
  reached them, and none did.
- **Measured over every manifested script:** 400 multi-line `return`/`raise`/`assert` statements carry
  **2,191 continuation lines** the check cannot see. The manifested scripts also hold 789 `IfExp` and
  483 comprehension `if` filters. Those counts include `self_test` bodies, so read them as an upper bound.
- Probe (`dcr1-probes/p1.py`) results:
  - `rc = 1 if a else 0`: not a decision line.
  - `bad = [x for x in xs if x.broken]`: not a decision line.
  - `match`: not a decision line. There are 0 `match` statements in manifested scripts today, so this
    one is latent.
  - `os._exit` and `quit`: not decision lines.
  - `except (A,\n B)`: only the first line counts.

**Fix.**
- Use the full statement span (`lineno..end_lineno`) for `Return`/`Raise`/`Assert`, and the `type` span
  for `ExceptHandler`.
- Treat `IfExp.test` and `comprehension.ifs` spans as decision lines.
- Reword the summary to what was measured: "N changed decision line(s) found, M with no anchor". It
  should never say "every one is reached" about lines the rule never classified.

### 2. MEDIUM: deleting a decision line, the PR #364 "severing" class, produces no warning and is reported as 0 scripts changed

**Where:** `scripts/check-diff-coverage.py:64-79` (`changed_lines` keeps only new-side lines and drops
files with none), `:182` (`n_files`).

**Evidence (executed).**
- In clone `p4` at master I deleted `if not isinstance(groups, list):` and its `raise Malformed(...)`
  from `check-hook-commands.py`, then committed.
- That script's suite stayed **22/22 green**. The check printed `diff coverage: 0 changed decision
  line(s) with no anchor, across 0 manifested script(s) changed against HEAD~1 — every one is reached`.
- So a branch that removes a guard's decision is reported as having changed no manifested script at all.
- The sweep catches this only when the deleted line was anchored (the anchor goes NOT FOUND). An
  unanchored decision line can be deleted with every instrument green. The dashboard text says it
  "points at each changed line that makes a decision", and a deleted one is a changed one.

**Fix.**
- Also parse the old side: the `-a,b` part of the header, plus `git show <merge-base>:<path>`.
- WARN on each deleted line that was a decision line in the base source: "a decision line was removed".
- Count files from the headers, not from non-empty added-line sets.
- At minimum, state the bound in the docstring, the PR body and the backlog row.

### 3. MEDIUM: an anchor's unchanged context lines clear decision lines the mutation never edits, 21% of anchor coverage

**Where:** `scripts/check-diff-coverage.py:134-145` (`anchor_lines` covers every line of `edits[*][0]`)
and `:179` (only `edit[0]` is read; `edit[1]` is discarded).

**Evidence (executed, `dcr1-probes/p2.py`).**
- Over all 2,160 entries and 5,485 non-exempt decision lines in manifested scripts, 1,283 lines are
  reached by anchor text. **269 of them (21%) are reached only as unchanged context.** The `find` and
  `repl` lines are identical there, so no mutation alters them.
- Example: `check-arch-findings.py:148` `return "REGRESSED"`. The anchor is
  `if cur > self.baseline:\n return "REGRESSED"` and the replacement changes only `>` to `>=`. The
  `return` line counts as covered, and changing it to `return "OPEN"` would draw no warning.
- More examples from the same run:
  - `begin-plan.py:412` `if session:`;
  - `check-ci-watched.py:362` `except (OSError, subprocess.SubprocessError):`;
  - `check-dashboard-entry.py:594`.
- The docstring's caveat is that "an anchor reaching a line is not proof the mutation tests it". The
  case here is stronger: the mutation does not even edit the line.

**Fix.** Cover only the lines of `find` that differ in `repl`. A `difflib.SequenceMatcher` over the two
line lists works, and `p2.py` does exactly that. Add a case with a two-line anchor whose second line is
unchanged context.

### 4. MEDIUM: in CI the warnings have no reader

**Where:** `.github/workflows/ci.yml:909-911`; `scripts/check-diff-coverage.py:187`.

**Evidence (executed).**
- The step prints plain `WARN ...` lines to stdout and exits 0. In Actions that is a green step whose
  log stays collapsed. Nothing reaches the PR conversation, the checks summary or the diff.
- The repo already uses `::warning::` annotations (`ci.yml:175`, `:189`, `:225`, `:285`, `:295`), so the
  channel exists.
- Volume, measured: the PR's own diff gives 36 warnings. `session-state` gives 59 at `1eb2e8b2`/`f9c8fe80`
  and 51 at `d24832e6`. `hooks-absolute-path` gives 29. With a cap of 12 per file, most of this lands as
  "… and N more" in a log nobody opens. This is the *gate's channel is weaker than the gate* failure
  the project has recorded before.

**Fix.**
- When `GITHUB_ACTIONS` is set, emit `::warning file=<path>,line=<n>::<msg>` for the capped lines. The
  annotation then shows on the PR diff at that line, and the instrument gets a reader.
- ⚠ On `pull_request`, HEAD is the merge commit, so line numbers are merge-side. They can drift from
  the PR head's numbers when master touched the same file. UNVERIFIED how often.

### 5. LOW: the loader-exception CANNOT RUN path and four documented behaviours have no case

**Where:** `scripts/check-diff-coverage.py:173-174`, `:124`, `:123`, `:186`.

**Evidence (executed, `dcr1-probes/mut.py`, each mutant applied to a copy and `--self-test` run).**

| Mutant | Location | Self-test |
|---|---|---|
| `return 2` → `return 0` in the loader `except Exception` arm | `:174` | 23/23 green |
| `ast.ExceptHandler` dropped from the decision tuple | `:124` | green |
| multi-line if test reduced to its first line only | `:123` | green |
| `CAP` never truncates | `:186` | green |
| `base...HEAD` → `base..HEAD` | `:165` | green |

The first mutant SURVIVED. Attack 4 asked about exactly this path, a loader import failure. Its rc 2 is
asserted by nothing; the one CANNOT RUN case it resembles uses the *refusal* path, `:175`. The other
four are also survivors.

**Fix.** Add these cases, each with a matching manifest entry:
- a root whose `check-plan-code.py` raises on import, expecting rc 2;
- a changed `except` line that is warned;
- a changed second line of a multi-line `if` that is warned;
- `CAP+1` warnings producing the "… and 1 more" line.

### 6. LOW: the docstring/import/literal-pin exemptions never change the output, so mutation 4 guards inert code and the "never warn" claims are vacuous

**Where:** `scripts/check-diff-coverage.py:95-98`, `:101-107`; mutation "a literal module pin counts
as behaviour".

**Evidence (executed, `dcr1-probes/p3.py`).**
- Across every manifested script, `decision_lines ∩ non_behaviour` = 810 lines. 800 are `self_test`
  bodies and 10 are blank or comment lines inside multi-line tests. **0** come from the docstring,
  import or literal-pin rules.
- That is structural, not chance: an `Expr` string, an `Import` or a literal `Assign` can never contain
  an `If`/`Return`/`Raise`/`Assert`/`ExceptHandler`/`exit` call.
- Mutating `for node in tree.body` to `ast.walk(tree)` survives.
- The PR body, the backlog row and the dashboard all say these "never warn", which is true of lines the
  rule could never flag anyway.

**Fix.** Delete the three inert exemptions, along with mutation 4 and its case, or move the case onto
`uncovered`'s output so it can fail. Rewrite the prose to say *only `self_test` bodies and comment
lines inside a test are exempt*.

### 7. LOW: the CI step is inserted between check-review-recorded and that step's own comment block, and a CANNOT RUN would skip that gate

**Where:** `.github/workflows/ci.yml:891-911`.

**Evidence (executed by reading the hunk).**
- The block "⛔ THE ZERO-ROUND CASE ... WRITES ITS OWN BODY FILE ... EDITING THE PR BODY DOES NOT
  RE-ARM THIS STEP" describes `check-review-recorded`. It now sits directly above the diff-coverage step.
- That step's `if: github.event_name == 'pull_request'` carries no status function, so it carries an
  implicit `success() &&` (GitHub's documented semantics; not executed in Actions). An rc 2 from
  diff-coverage would therefore **skip check-review-recorded**. The verify job is red either way, but
  the review gate's own message would not be printed.

**Fix.** Move the new step and its comment *after* `check-review-recorded`.

### 8. LOW: the "48" in the PR body, backlog row and dashboard cannot be reproduced; the 163/71 figures are UNVERIFIED

**Evidence (executed).**
- The current tool, run against `origin/master` on `session-state`, gives 59 at `1eb2e8b2`, 59 at
  `f9c8fe80` and 51 at `d24832e6`. None is 48.
- `hooks-absolute-path` gives 29, which matches.
- The 163/71 figures came from an earlier, broader rule that is not in the tree, so I could not run them.

**Fix.** Name the commit and base each figure was measured on, or restate the figures from a rerun.

### 9. LOW: exit code 1 does exist, and the self-test prints a stray "CANNOT RUN" on a green run

**Where:** `scripts/check-diff-coverage.py:32-33`, `:180`, `:296`.

**Evidence (executed).**
- I committed a latin-1 byte into a manifested script. The check raised `UnicodeDecodeError` and exited
  **rc=1**, though the docstring says "There is no 1". This is low-likelihood, because such a script
  fails its own import anyway.
- `--self-test` prints `CANNOT RUN — git diff no-such-ref-xyz...HEAD failed ...` to stderr as its first
  line on a 23/23 pass. The call at `:296` does not redirect stderr; the call at `:300` does.

**Fix.**
- Wrap the source reads and the parse in the CANNOT RUN arm, or amend the docstring.
- Redirect stderr at `:296` the way `:300` does.

## PR body, backlog #251 row, dashboard entry

These parts are true as executed:
- the mechanism;
- the reuse of `load_manifests`;
- the CI shape;
- merge-ready going from 4 to 5;
- 23 cases;
- 10 mutations, each killed by the case it names;
- line 80 being the real survivor;
- the 29.

These parts are not:
- "Comments, docstrings, imports, literal module pins ... never warn" is vacuous (finding 6).
- "points at each changed line that makes a decision" omits deleted lines, continuation lines, ternaries
  and comprehension filters (findings 1 and 2).
- "48" is unreproduced (finding 8).
- The "Bounds" list omits the deletion blind spot and the context-line over-clear (findings 2 and 3).

Usefulness (attack 8): there is a signal. On `hooks-absolute-path`, 1 of 29 warnings was confirmed as a
live survivor, and I did not test the others. But the signal reaches no reader (finding 4), and the
all-clear message overstates what was checked (findings 1 and 2).

VERDICT: NOT CONVERGED

# Phase 6 architecture review — `ci_flaky_contract` in `scripts/sweep-red-alert.py` (backlog #629)

- Subject: `ci_flaky_contract`, merged by PR #573 (backlog #617 part 1), read at master `9263dfc5`.
- Armed by THRASHING: rounds 2, 3 and 4 of PR #573 each carried a finding caused by the previous round's fix, all in
  the component `contract-parser` (`docs/reviews/coordinator/617-bind-ci-r2-coordinator.md` to `...-r4-coordinator.md`).
- Read first: `CONTEXT.md` (the guard vocabulary: guard, cannot-run, falsifier), `docs/adr/` (ADR-0014 is the only one
  that touches this path; nothing here re-opens it), backlog #617, backlog #619, backlog #629, the nine round documents
  of subject `617-bind-ci`, and `docs/reviews/architecture-review-2026-11-12-495-sweep-flaky-filing.md` (the review
  that proposed R1, the per-shard record).
- No tracked code was changed. Every probe ran against in-memory or scratch copies. The probe scripts are quoted by
  name in *Bound of this review*.
- Every claim below is tagged **[M]** (measured in this review: a command was run and its output read) or **[I]**
  (inferred: reasoned from text or documentation, not run). The closing table separates them.

## Verdict

1. **The thrashing is a mechanism defect, not a prose floor.** The contract answers a question about what the runner
   does by reading the text of two nested languages (YAML, and bash inside it) with line patterns. It must be right in
   both directions at once, and no case can tell it when it is wrong.
2. **Backlog #619 R1 retires the contract wholly**, on one condition that backlog #619 does not yet state: the reader
   identifies a record by its content, and the record's shard index and total are the values the harness sliced by.
3. **Recommendation: RETIRE it in the same change that lands backlog #619, and FREEZE it until then.** Do not fold the
   contract edges filed in rounds 1, 3 and 4. Do not delete it early: its cases are, by accident, the only thing
   that makes a drift of the `grep` marker red today.

## 1. What structure made each fix produce the next round's findings

### The record, replayed

The same ten edits to `ci.yml`, run against the contract as it stood at each head the reviewers saw. Five truly break
the hand-over (the file `read_flaky` expects is not written). Five change nothing the runner does. `✗` marks a wrong
answer. **[M]**

| Edit to `ci.yml` | Breaks the hand-over? | r1 head `fb0c31f6` | r2 head `f40a45e5` | r3 head `a2c28a43` | r4 head `ded10459` | master |
|---|---|---|---|---|---|---|
| a comment names the file, the real redirect is renamed | yes | ok ✗ | RED | RED | RED | RED |
| `SHARD_INDEX=$SHARD_TOTAL` before the write | yes | ok ✗ | ok ✗ | RED | RED | RED |
| `((SHARD_INDEX++))` | yes | ok ✗ | ok ✗ | ok ✗ | RED | RED |
| `unset -v "${!SHARD_@}"` then `: "${SHARD_INDEX=38}"` (r4 Codex) | yes | ok ✗ | ok ✗ | RED | **ok ✗** | ok ✗ |
| `printf -v "$(compgen -v SHARD_I)" 38` (new in this review) | yes | ok ✗ | ok ✗ | ok ✗ | ok ✗ | ok ✗ |
| `env:` written below `run:` | no | ok | **RED ✗** | ok | ok | ok |
| `echo "SHARD_INDEX=$SHARD_INDEX"` | no | ok | ok | **RED ✗** | RED ✗ | RED ✗ |
| a `- ` line inside a heredoc in the step | no | ok | **RED ✗** | RED ✗ | ok | ok |
| `merge-multiple: true  # comment` | no | RED ✗ | ok | ok | ok | ok |
| `${{ strategy['job-index'] }}` (new in this review) | no | RED ✗ | RED ✗ | RED ✗ | RED ✗ | RED ✗ |
| **wrong answers of 10** | | 7 | 6 | 5 | 4 | 4 |

Three things in that table are the finding:

- **Every fold added at least one wrong answer that the head before it did not have** (the bold cells). The r1 fold
  added two false reds. The r2 fold added one. The r3 fold turned a correct RED into a false ok. **[M]**
- **The total falls by one a round** (7, 6, 5, 4), so each fold was a real improvement. This is not a team going in
  circles. It is a model converging on a target it cannot reach. **[M]** for the counts, **[I]** for "cannot reach".
- **Two rows are wrong at every head, and I wrote both in a few minutes.** One escape never spells the variable's
  name, so no rule about how the name is mentioned can see it. `eval "$(printf %s_%s=38 SHARD INDEX)"` is a third.
  Under bash each makes shard 0 write `shard-38.txt`. **[M]** (bash 3.2 locally; the runner's bash is newer, **[I]**
  that it agrees).

### The four causes

**S1. The contract's subject is the runner; what it opens is text.** The fact it wants is "shard *i* writes
`shard-i.txt` into the directory the alert step reads". What it reads is `ci.yml`, with `_uncomment`, `_indent`,
`_children` and four regular expressions standing in for a YAML parser and for bash. Each round's finding is a place
where the language means something the patterns do not model:

| Round | What the patterns did not model | Language |
|---|---|---|
| r1 | a `#` comment is not a command; a key under `env:` is not a key under `with:` | bash, YAML |
| r2 | a variable can be reassigned after `env:` sets it; key order inside a step is free | bash, YAML |
| r3 | assignment has more spellings than `=`; a `- ` inside a block scalar is not a step | bash, YAML |
| r4 | an expansion can assign (`${V=…}`), and indirection can name a variable without spelling it | bash |

The supply of such places has no end that a pattern list can reach. The r3 allow-list was meant to stop the list
growing, and r4 plus the two new rows above show it did not. **[M]** for each row (the round documents and the replay),
**[I]** for "no end".

**S2. One predicate carries two opposite duties.** It must never say ok over a broken hand-over (the reviewers'
criterion a), and it must never go red over a harmless edit (criterion b). The second duty exists only because of
where the call sits: `main` runs `ci_flaky_contract(workflow)` before `read_flaky`, so a false red withholds names
that are present and readable. Measured: with all 38 shard files in place and one FLAKY name among them, `main` opens
one issue under the real workflow; under the workflow with the debug `echo` it raises `ValueError` and makes no issue
call at all. **[M]**

A tightening for duty (a) spends duty (b), and the reverse:

| Fold | Direction | The next round's finding it caused |
|---|---|---|
| r1 Claude m3: read the variable from the writing step only | tighten | r2 Codex m3 (`env:` below `run:` is a false red); r3 Claude m3 (a heredoc `- ` line is a false red) |
| r2 Codex M1: any `VAR=` in the step raises | tighten | r3 Claude m2 (the debug `echo` is a false red) |
| r3 Claude M1: allow only `$V`, `${V` and the `V:` key | tighten, with `${V` left open so `${V}` passes | r4 Codex M1 (`${V=38}` is a false ok, and the head before refused it) |

**[M]**: each pair is in the round documents and reproduces in the replay table.

**S3. Nothing in the suite can tell the contract it is wrong.** Its cases are text edits of the real `ci.yml` that the
author thought of. At every reviewed head the self-test was fully green (40/40, 46/46, 49/49, 52/52) and every mutant
was killed by its named case (28, 34, 37, 39), and at every one of those heads a reviewer reproduced an escape. The
mutation tally proves each clause is load-bearing. It cannot prove the model of bash is complete, and no case runs a
shell. **[M]** for the counts (quoted from the round documents; 52/52 re-run here), **[I]** for the general statement.

**S4. The two links it guards already fail closed without it; the one link that fails open it does not guard.**

- With the contract call removed, the files as a `$SHARD_TOTAL` drift would leave them make `main` raise *"lacks 38 of
  38 shard files"*. The files as `merge-multiple: false` would leave them do the same. **[M]**
- With the contract present and r4's escape applied, the outcome is that same red. So each round's MAJOR was about
  *when* a drift is seen (the PR's self-test, not the first master sweep), never about *whether*. **[M]**
- The marker literal in the shard step's `grep -F` is the link that fails open (F1 of the 2026-11-12 review). Replace
  its em dash with a hyphen: `ci_flaky_contract` says ok, and with every shard file present and empty `main` prints
  "no FLAKY mutation in this sweep" and exits 0. **[M]**
- ⚠ **A correction to backlog #619's row.** It says a drift of that literal leaves the self-test green. That was true
  on 2026-11-12 (33/33). On master it is 49 passed, 3 FAILED. The three cases are r2 Codex M1, r3 Claude M1 and the r3
  allow-list case, whose fixtures happen to anchor on the text `grep -F 'mutation FLAKY — '`. No case names the
  marker; the labels that go red talk about reassigning the index. It is a pin by accident, on a prefix of one line.
  **[M]**

Four rounds of review went into the links that were already loud. That is where the cost of S1 to S3 landed.

### Thrashing or prose floor?

`docs/review-method.md` gives one test: *can a redesign remove it?* **Yes.** Section 2 runs the drifts against a reader
of per-shard records, and the two links the contract guards stop bearing any load. The findings do not survive the
reshaping, so they are mechanism defects and the redesign is owed. They are not branch-coverage gaps: the code the
contract "governs but does not own" is bash itself.

One precedent in this repository went the same way. The 2026-11-08 sweep-deadline review replaced a `ci.yml` parser
that "r1-r3 kept finding holes in" (the words are in `sweep_limit_pin`'s docstring, `scripts/check-plan-code.py`) with
a value the runner evaluates and hands over in `env:`. What it kept is a static pin that is strict (an unknown shape is
a problem) and that the run-time guarantee does not rest on. `ci_flaky_contract` is the opposite on both counts: it
tries to be tolerant, and it sits in `main`. **[M]** that the docstring says this; **[I]** that the analogy holds.

## 2. Does backlog #619 R1 remove the need for the contract?

**Wholly, for both links, given two conditions.** I wrote a 30-line sketch of R1's reader (`read_records`: every
`*.json` under the directory, at any depth; identity from each record's own `shard` and `total`; refuse a duplicate, an
out-of-range index, a missing index, a disagreeing total, an incomplete record, or no record at all) and drove the
drifts from PR #573's rounds against it. It reads no file name and no `ci.yml`. **[M]** for every row; the sketch is
not the implementation, so **[I]** that the implementation will match.

| | Situation | Today, without the contract | R1 reader |
|---|---|---|---|
| A | every shard writes its own file, merged into one directory | green | green, 1 FLAKY read |
| B | `merge-multiple: false` (one subdirectory per artifact) | red, 38 of 38 missing | **green**, 1 FLAKY read |
| C | every shard names its file by a constant (r2 M1, r3 M1, r4 M1, the new escapes), not merged | red, 38 of 38 missing | **green**, 1 FLAKY read |
| D | the same constant name, merged into one directory | red | red: "37 of 38 shards wrote no record" |
| E | R1 as the 2026-11-12 review sketched it: every shard writes `shard.json`, and `merge-multiple: true` is kept | (n/a) | **red on every master sweep**: "37 of 38" |
| F | the index handed to the harness is a constant | (n/a today: the file name carries it) | red: "duplicate shard 0", 37 missing |
| G | a 39th job (an `include:` entry) | **silent**: `shard-38.txt` never read (r3 Claude m4, F2) | green, all 39 read |
| H | one shard killed before it writes | red, 1 missing | red, names shard 7 |
| I | one shard stopped on its budget | green over a partial log (F3) | red: "shard 7 incomplete" |
| J | nothing downloaded | red | red: count unknown, NOT RUN |

What this shows:

- **The file-name link is gone (B, C).** The name of the file no longer says which shard it is, so no variable in the
  shell has to be proved equal to `strategy.job-index`. The whole of S1's bash side has nothing left to model.
- **The `merge-multiple` link is gone (B).** Either setting is read.
- **Rows F and G are closed by content.** They are the two that a text contract either cannot see or sees wrongly.
- **Row E is a defect in R1's sketch, found here.** The 2026-11-12 review says the shard step writes
  `sweep-record/shard.json` and that the download "may keep `merge-multiple: true` or drop it". With both, 38 files of
  one name land in one directory and one survives. It fails closed, and it would be red on every master sweep from the
  first one. **[M]** for the reader's verdict on one surviving file; **[I]** that `download-artifact` lets the last
  writer win (its documentation, not run).

**Condition 1 — the record carries the values the harness sliced by.** The shard step already passes
`--shard0 "$SHARD_INDEX/$SHARD_TOTAL"`, and `parse_shard("38/38", zero_based=True)` already answers CANNOT RUN. **[M]**
The record's `shard` and `total` must be the parsed result of that flag, never a second read of the environment. Then
the set of records proves coverage by its own arithmetic: if the indices 0 to total-1 are all present, complete and
agree on total, every mutant was in exactly one slice, whatever the shell did to its variables on the way. **[I]**

**Condition 2 — one record per artifact, and no merge.** Drop `merge-multiple` and read at any depth. The artifact
name is `sweep-flaky-${{ strategy.job-index }}`, an expression the runner evaluates outside any shell (**[M]**: it is
in the upload step's `with:`, not in a `run:`). Two shards then cannot collide whatever the file is called, and row E
cannot happen.

### What would still need guarding, and how

| Residual | Fails | Guard that fits it |
|---|---|---|
| The joins nobody parses: the `--record` path, the upload `path:`, the artifact `name:` against the download `pattern:`, the download `path:` against the alert step's directory | closed: no record, NOT RUN | **Exercise it, do not parse it.** Today the upload, download and alert steps are skipped on `pull_request` (**[M]**), so these joins first run on master, after the merge. Run the upload, the download and the reader in a validate-only mode on pull requests too (read and check the records; file nothing). The PR that breaks a join is then red on its own run. This replaces what the contract was for, with a measurement in place of a proof. |
| A red alert step on master that nobody sees | open, to a person | Already filed: backlog #617 part 3 (a NOT RUN scan opens no issue and no session lists it). Unchanged by R1, and now the only thing between a broken join and silence if the pull-request exercise is declined. |
| The record's `complete` flag is the harness's own claim | open only if the harness writes `true` wrongly | A case in the harness's suite: a budget stop and a `NotMeasured` each write `false`. R1 already asks for this. |
| The harness side of the producer-consumer tie | open | R1's own case: the real harness `main` writes a record from a fixture that goes FLAKY, and the reader reads that file. No hand-written record stands in. |

None of these is a property of `ci.yml`'s text. There is nothing left for `ci_flaky_contract`, `_uncomment`, `_indent`
or `_children` to do.

## 3. Recommendation

**RETIRE with backlog #619. FREEZE until then.**

| Option | What happens | Consequence |
|---|---|---|
| **A. Retire in the change that lands backlog #619 (recommended)** | Delete `ci_flaky_contract`, `_uncomment`, `_indent`, `_children`, `SHARD_FILE`, `DOWNLOAD_STEP`, their cases and mutants, with `shard_count`, `flaky_names` and the `grep` block that R1 already deletes. | The 19 cases and 16 mutants PR #573 added go (33 to 52, 23 to 39; **[M]** for 52 and 39, the earlier figures are the 2026-11-12 review's). The contract edges filed in backlog #617 (r1: `- if:` before `name:`, `${SHARD_INDEX:-0}`, the order point, the duplicated block walk; r3: the second matrix axis) and in backlog #629 (r4) close as retired, unfixed. Pull-request-time detection of a broken join moves from a text proof to the validate-only run. |
| B. Freeze until then (recommended, with A) | No further rule is added to the contract. The r4 escape and the two new ones stay open. | Each is fail-closed on the first master sweep (**[M]**, S4). The exposure is a deliberately obscure edit to the shard step, in the window before backlog #619 lands. The self-test still reds the ordinary drifts on the PR. The debug-`echo` false red stays, and reaches master only if a PR is merged over a red self-test (**[I]**: I did not check which checks are required). |
| C. Retire now, before backlog #619 | Delete the contract and its cases today. | Loses pull-request-time detection of the two drifts (they are still red on master, but that red opens no issue: backlog #617 part 3). ⚠ And it **reopens F1 silently**: the three cases that redden a marker drift by accident go with it (**[M]**). Not recommended. |
| D. Keep and continue (fold r4, then whatever r5 finds) | Model `${V=…}`, `${!…}`, `printf -v`, `eval`. | S1 says the list does not end; the replay says each fold costs a new wrong answer. A fifth round on the same component. Not recommended. |
| E. Redesign in place: a strict, exact-text pin of the shard step, run by the self-test only, out of `main` | Any edit to the step is red until the pin is updated. Cannot fail open on a text change. | A copy of the step with a pin on it, false-red by design on every edit to the step (5 commits touched those lines in the last 31 days, of 39 to `ci.yml`; **[M]**). All of it deleted when backlog #619 lands. Not worth building for the interval. |

**Why not fold the cheap interim fix** (move the contract call to after the read, so a false red cannot withhold
names; r1 Claude m2)? It is sound, and small. But the call in `main` re-checks the same file the PR's self-test
already checked, so the loss needs a merge over a red check; and the fold would rework the `main` mutant for code that
backlog #619 deletes. Freeze is the cheaper honest state. If backlog #619 slips past a week or two, take this fold
then.

### What goes to the backlog (same commit)

- **backlog #619, amended.** It retires `ci_flaky_contract` in the same change; conditions 1 and 2; the validate-only
  run on pull requests; its row's claim about the self-test under a marker drift is corrected; one more FAILS IF.
- **backlog #629, closed** with a pointer to this document.
- **backlog #617, amended.** Part (1)'s filed contract edges are not to be folded. Parts (2) and (3) stand; part (3)
  matters more under R1, as the table above says.

No new row. Everything here is a change to how backlog #619 is built.

## Checked and found sound

- `python3 scripts/sweep-red-alert.py --self-test`: **52/52** at `9263dfc5`. **[M]**
- The contract is right about today's `ci.yml`: it returns ok at all five heads replayed. **[M]**
- Codex r4's claim that the head before `ded10459` refused `${SHARD_INDEX=38}`: reproduced (RED at `a2c28a43`, ok at
  `ded10459`). **[M]**
- The coordinator's r4 judgement, *not a BLOCKER, the missing-file red still reports it*: reproduced. **[M]**
- The alert-first order in `main` (the red alert before anything about FLAKY) is untouched by any of this.
- The 2026-11-12 review rejected R2 (each shard files its own names) for a token-scope reason and a race. Nothing here
  changes that; R2 would also retire the contract, at the price that review named.

## Bound of this review

- Static reading plus the probes. No CI run was triggered and no workflow was executed on a runner.
- The shell probes ran under bash 3.2 (macOS). `printf -v`, `compgen -v`, `${!prefix@}` and `${V=word}` all exist in
  the runner's bash as well; that they behave the same there is inferred.
- `read_records` is a sketch written for this review. It was not reviewed by anyone else, and R1's real reader may meet
  cases it does not.
- The harmlessness of `${{ strategy['job-index'] }}` rests on Actions' documented index syntax, not on a run.
- Probe scripts, in this session's scratchpad under `p629/`: `probe.py` (the escapes, `main` with and without the
  contract, the marker drift), `history.py` (the replay table), `r1_proto.py` (rows A to J).

## Measured and inferred, separated

| # | Claim | Status | How |
|---|---|---|---|
| 1 | The self-test is 52/52 on master `9263dfc5` | MEASURED | ran it |
| 2 | Wrong answers of ten drifts per head: 7, 6, 5, 4, 4 | MEASURED | `history.py` over `fb0c31f6`, `f40a45e5`, `a2c28a43`, `ded10459`, master |
| 3 | Every fold introduced at least one wrong answer the previous head did not have | MEASURED | the same table, bold cells |
| 4 | Three escapes pass the contract on master while bash writes `shard-38.txt` for shard 0 | MEASURED | `probe.py`, bash 3.2 |
| 5 | `strategy['job-index']` and the debug `echo` are red on master | MEASURED | `probe.py` |
| 6 | A false red in `main` files nothing, where the real workflow files one issue from the same files | MEASURED | `probe.py`, `gh` replaced by a recorder |
| 7 | Without the contract, both guarded drifts end in "lacks 38 of 38 shard files" | MEASURED | `probe.py`, contract replaced by a no-op |
| 8 | With the contract, r4's escape ends in that same red | MEASURED | `probe.py` |
| 9 | A marker drift: contract ok, `main` exits 0 with "no FLAKY mutation" | MEASURED | `probe.py` |
| 10 | A marker drift makes the self-test 49 passed, 3 FAILED, through fixture anchors | MEASURED | a `git archive` copy with the one literal changed |
| 11 | The R1 reader's verdict on rows A to J | MEASURED | `r1_proto.py` (a sketch) |
| 12 | The harness refuses `--shard0 38/38` as CANNOT RUN | MEASURED | called `parse_shard` |
| 13 | The upload, download and alert steps are skipped on `pull_request`; the artifact name is a runner expression | MEASURED | read `ci.yml` (the three `if:` lines, the upload's `with: name:`) |
| 14 | 39 commits touched `ci.yml` in 31 days, 5 of them the shard step's lines | MEASURED | `git log --since=2026-10-13`, with `-L` for the step |
| 15 | Self-test and mutation counts per round (40/46/49, 28/34/37) | QUOTED | the round documents; not re-run at those heads |
| 16 | The supply of bash and YAML spellings a pattern list must model has no reachable end | INFERRED | from 2 to 4 and from the languages; not provable by probes |
| 17 | `download-artifact` with `merge-multiple: true` lets the last same-named file win (row E's cause) | INFERRED | its documentation; not run |
| 18 | The runner's bash agrees with bash 3.2 on the three escapes | INFERRED | Codex confirmed r4's on its own shell; the other two not run elsewhere |
| 19 | With conditions 1 and 2, a complete set of records proves every mutant was in exactly one slice | INFERRED | from `--shard0`'s round-robin slicing; no record writer exists yet |
| 20 | R1's real reader will behave as the sketch | INFERRED | the sketch is 30 lines, unreviewed |
| 21 | A false red reaches master only by a merge over a red self-test | INFERRED | `check-selftest-counts` runs on pull requests and lists this script; whether it is a required check was not read |
| 22 | The validate-only run on pull requests is cheap (38 small artifacts a run) | INFERRED | not measured |
| 23 | The sweep-deadline precedent is the same class | INFERRED | from `sweep_limit_pin`'s docstring |

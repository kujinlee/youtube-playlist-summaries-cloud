# Phase 6 architecture review — the slice-3 cross-run view in `scripts/strace_reads.py` (backlog #626)

- Subject: `_named`, `_cwd_pass`, `_resolve`, `record_from_log` and `cross_run` in `scripts/strace_reads.py`, merged
  by PR #567 (backlog #586 slice 3, commit `fc5e0380`), read at master `2c691771`. The file is unchanged between
  the two.
- Armed by THRASHING (conservative reading): rounds 2 and 3 of PR #567 each found a check that the SHADOW argument
  skipped, in the component `cross-run-record` (`docs/reviews/coordinator/586-slice3-r2-coordinator.md`,
  `docs/reviews/coordinator/586-slice3-r3-coordinator.md`).
- Read first: `CONTEXT.md` (it has no entry for this module), `docs/adr/` (no ADR touches this path; nothing here
  re-opens one), backlog #586, backlog #626, backlog #622, the seven round documents of subject `586-slice3`, and
  spec §2 of `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md`.
- No tracked code was changed. Two prototypes were applied to the worktree file, measured and reverted; every other
  probe ran against scratch copies taken with `git show`.
- Every claim is tagged **[M]** (measured in this review: a command was run and its output read) or **[I]**
  (inferred from reading). The table at the end separates them.

Terms. A **labelled open** is a successful `open`/`openat` whose return value strace decorates with the path the
kernel resolved (`= 3</t/docs/b.md>`). Its **SHADOW argument** is the path text the call itself typed, which the
round-1 fold started keeping for the cross-run comparison. An **unlabelled path** is any other path a call typed,
for example the argument of a failed open. The **cross view** is `_resolve(..., cross=True)`; the **read view** is
`cross=False`.

## Verdict

1. **The thrashing is a mechanism defect, and a small one.** The path tag `from_label` has three values, and every
   check was written `from_label is False`. A new third value therefore skipped every check by default, in a module
   whose rule is to refuse by default. The checks sit in two functions, and each fold repaired the function its
   reviewer named.
2. **A redesign removes the class, and it costs about 11 lines.** One predicate decides "this path is a name, check
   it" at all three sites. One differential self-test case states the property the three rounds were circling: a
   path text that refuses when unlabelled also refuses as a SHADOW argument. Replayed against the round-1 fold, that
   one case shows 19 violations at once, so it would have folded rounds 2 and 3 into one.
3. **Recommendation: build both before slice 4 edits the resolver (backlog #633), and keep the read view until
   slice 4 has used it as a measuring tool, then delete it (backlog #634).** Master is not fail-open today: 0
   violations in 27 forms.

## 1. What structure made each fix produce the next round's findings

### The record, replayed

One harness, `diff_harness.py`, builds each of 27 path forms twice: once as a failed open (unlabelled) and once as a
labelled open of the same text. It asks for `record_from_log(...).trace` on both. A **violation** is a form where
the unlabelled twin refuses and the labelled twin is `complete`. 25 of the 27 forms refuse when unlabelled; they
cover eight refusal reasons. The two others are controls. [M]

| Head | What it is | Violations of 27 | Which reasons were exempt |
|---|---|---|---|
| `42ba603d` | round-1 reviewed head; the argument of a labelled open is dropped | 22 | all seven that a path can earn |
| `e2fe1d29` | after the round-1 fold; SHADOW exists | 19 | `..` (4), `/proc` and `/dev/fd` (5), runtime link (7), pre-existing link (3) |
| `aa5c4d78` | after the round-2 fold | 10 | runtime link (7), pre-existing link (3) |
| `fc5e0380` | after the round-3 fold; master | 0 | none |

All four rows are [M]. Three things follow.

- Round 2's finding (`..`, `/proc`) and round 3's (both link checks) are the same 19 rows. Round 2 fixed nine and
  left ten. [M]
- Neither reviewer saw the other ten because each was shown, and each reported, one input. The coordinator's rule
  ("a fresh fold agent first turns every reviewer input into a failing self-test case") produced instance cases:
  two for round 2, three for round 3. No case states the property. [M: the case names at
  `scripts/strace_reads.py:1994`, `:1998`, `:2016`, `:2018`, `:2020`]
- Strictly, R3-1 was caused by round 1's fix, not round 2's. The coordinator said so and armed on the conservative
  reading. This review agrees with that reading: round 2's fix is what declared the class closed while leaving ten
  of its rows open. [I]

### The three causes

**Cause 1: a third tag value fell on the exempt side of every check.** Slice 2 had two kinds of path: the kernel's
label (trusted, `True`) and a typed name (`False`). Its bound is correct for the label
(`scripts/strace_reads.py:77`): "A successful open's label is the kernel's resolution AT THAT MOMENT, so none of the
link rules apply to it." The round-1 fold added `SHADOW`, a typed name that is kept for comparison and left out of
the read view. It is untrusted text, exactly like `False`. But the checks read `from_label is False`
(`scripts/strace_reads.py:639`, `:641`, and `:743` before round 3), so `SHADOW` inherited the label's exemption.
The round-1 coordinator document records this as a decision: "it skips the label-replaced checks (`..`, `/proc`,
links)". The tag carries two independent facts in one value: *is this text trusted* and *does it enter the read
view*. `SHADOW` needed "no" for both and got "yes" for the first. [M for the quoted lines; I for the reading]

**Cause 2: the checks an unlabelled path gets are not listed anywhere, and they sit in two passes.** `..` and
`/proc` are refused in `_cwd_pass` (`:639`–`:643`). The two link checks are in `_resolve` (`:753`–`:758`). Round 2's
reviewer found the gap through `..`, so the fold mirrored `_cwd_pass`'s two checks into `_resolve` and stopped.
Round 3's reviewer listed the exemption by group and found the rest. [M for the locations; I for the cause]

**Cause 3: a second mode kept the fix out of the place it belonged.** The round-2 coordinator document: "A first
attempt applied the refusal in `_cwd_pass` for every caller, and it broke two slice-2 cases". Hence the `cross`
flag. The read view those cases protect has no production caller: outside its own self-test, nothing imports
`resolve_log`, `resolve_calls` or `record_from_log` yet, and `record_from_log` passes `cross=True`. [M: `grep` over
`scripts/` and `.github/`; only `check-fixture-variation.py`, `check-selftest-counts.py`, `check-plan-code.py` and
`ci.yml` name the module, none calls it]

### Thrashing or prose floor?

The test in `docs/review-method.md` is *can a redesign remove it?* Yes. With one predicate at every gate, the
round-2 and round-3 findings are not two findings; they cannot be written (section 2, prototype E2). It is a
mechanism defect. It is not the kind that needs a new design for the module: the resolution itself is done once,
in one loop, and was never the problem. What was doubled was the gate. [M for E2; I for the classification]

### The two questions backlog #626 asks

**Do `_cwd_pass` and `_named` still treat "kept for comparison" paths differently?** `_named` only tags
(`:547`). `_cwd_pass` still exempts SHADOW from both of its checks (`:639`, `:641`), and `_resolve` re-implements
them for SHADOW at `:748`–`:752`. The two copies already differ in text: `_cwd_pass` refuses a magic link when
`follow or len(p) > magic.end()`, the copy refuses on any `PROC.match(p)`. For an open the two agree, because an
open always follows its final component. So the answer is yes, by duplication, and behaviour is equal today. [M:
0 violations at `fc5e0380`, including the two final-component `/proc` forms]

The round-3 coordinator document says "A check added to that branch later applies to SHADOW automatically, so there
is no exemption left to fix piecemeal." That holds for `_resolve`'s branch only. A probe added one hypothetical rule
to `_cwd_pass`, written the way its neighbours are written (`if from_label is False and ...`): the unlabelled twin
refused and the SHADOW twin was `complete`. The same rule written in prototype E2's style refused both. [M]

**Should the cross-run sets come from paths resolved ONCE?** They already do: one `_named`, one loop in `_resolve`,
two lists out of it (`kept`, `every`). No path is resolved twice. The other paths that reach the sets were checked
against backlog #626's failure condition:

| Path kind | Tag | Checked as a name? |
|---|---|---|
| a typed path of a call that is not a labelled open | `False` | yes, both passes |
| a SHADOW argument | `SHADOW` | yes under `cross` [M] |
| a socket `sun_path` | `False` | yes (`_named`, the `sun_path` branch) |
| the kernel's label of a return value or a descriptor operand | `True` | no, by slice 2's bound; it is the kernel's own resolution |

Backlog #626's failure condition ("a path compared by text in `cross_run` reaches the sets without going through a
check that an unlabelled path in the same position gets") is not met at master. [M for the 27 forms; I beyond them]

## 2. Can a redesign remove the class, and at what cost?

Three shapes were considered. Two were built and measured.

**E2: one predicate, three sites.** A helper `_is_name(from_label, cross)` returns
`from_label is False or (cross and from_label is SHADOW)`. `_cwd_pass` takes `cross` and uses the helper at `:639`
and `:641`; `_resolve` uses it at `:743`; lines `:748`–`:752` are deleted. Measured on the worktree, then reverted:

- 11 lines added, 10 removed. [M: `git diff --stat`]
- Self-test 288/288, unchanged. Differential harness 0 violations of 27. [M]
- 5 of 207 mutation anchors lose their text and need re-binding: "a `..` is accepted", "a magic /proc path is
  accepted", and the three SHADOW mutations. The two SHADOW `..` and `/proc` mutations then duplicate the first two
  and one new mutation is owed (the helper without its `cross` clause), so the pin moves from 207 to about 206. [M
  for the 5; I for the final pin]

**E1: delete the read view (`cross` always True).** Three of 288 cases fail: "a successful .. open is resolved by
its label", "a successful /proc/\*/fd open is resolved by its label", and "a successful open via a since-deleted
temp link gives its staged name". [M] Those three describe behaviour that no production path has, because
`record_from_log` already refuses all three inputs. This is the cleanest end state: the tag becomes a plain boolean
plus "not in the read view", and there is one mode. It is not recommended yet, for the reason in section 3.

**Not built: resolve the SHADOW text instead of refusing it.** The trace does not record which links the kernel
walked, so a text with `..` or a link in it cannot be turned into the real path from the log alone. Refusal is the
only sound answer, and round 1's rule ("prefer refusing to modelling") stands. [I]

**The part that matters more than the shape: a case that states the property.** Either shape still rests on a
convention unless a case goes red when it is broken. The differential case is a hand-written table of path forms
(an independent list, never derived from the code under test), each run as both twins, with two assertions: no
violation, and the set of refusal reasons the unlabelled twins produce equals a written list, so the table cannot
shrink in silence. The harness in this review is that case in draft: 27 forms, eight reasons. [M that it reddens
the three older heads; I that it would have been written in round 1 had the rule asked for a property]

## 3. Recommendation

**Build E2 and the differential case in one small PR, before slice 4 touches `_cwd_pass` or `_resolve` (backlog
#633). Keep `cross=False` until slice 4 has measured with it, then delete it (backlog #634).**

Each consequence, named:

- **Master stays as it is until then.** It is not fail-open in the 27 forms. The risk carried is that an edit to
  `_cwd_pass` in the meantime adds a check SHADOW skips. Nothing is scheduled to edit it before slice 4. [I]
- **E2 costs one review round's worth of mutation work**: 5 anchors re-bound, the pin changed, one mutation added.
- **The read view survives one more slice, on purpose.** The refusal reason for a SHADOW `..` is the same string as
  for an unlabelled one, so a count of reasons cannot tell slice 4 how many guards are refused only because of the
  cross view. Running both views over the same log can: a log that resolves in the read view and refuses in the
  cross view was refused by a SHADOW argument. After that count is recorded, the mode has no remaining use.
- **The three slice-2 cases that E1 fails then change meaning**: they will assert a refusal. That is a visible
  change to slice 2's stated behaviour and belongs in slice 4's review, with the count beside it.
- **Nothing here closes the `_meets` breadth question** the round-1 coordinator flagged ("at, below or above").
  That is still slice 4's first real-corpus count.

### What slice 4 of backlog #586 must do or avoid

1. **Build every `Record` through `record_from_log`.** Never take reads from `resolve_log` and the cross-run sets
   from `record_from_log`: the two can disagree about whether the same log is complete. [M: E1's three cases]
2. **Parse while the copy and the directories around it still exist, on the machine that ran the trace.** Spec §2
   already says "resolved at parse time, before the copy is removed". Round 3 made every labelled open depend on it,
   and nothing notices when it cannot run. The round-3 input B gives `through a pre-existing link` with the link in
   place, and `complete` after the link, or the whole tree, is removed. [M] Slice 4's caller should refuse a record
   whose `ctx.copy` is not an existing directory at parse time. The module cannot do it: its own cases use `/t`.
3. **Count cross-only refusals on the real corpus before trusting the selection numbers.** The two recorded whole
   logs resolve `complete` in both views, with 284 labelled opens, none holding `..` or a `/proc` path. [M] Two logs
   are not the corpus: 0 in 284 opens says nothing about a guard that imports through `..`. [I]
4. **Do not add a check to either pass written `from_label is False`.** Until backlog #633 lands this is a
   convention. After it, the differential case enforces it.
5. **Backlog #622 still applies** (record with `UV_USE_IO_URING=0`).

### What goes to the backlog (same commit)

- Backlog #626: closed, with this verdict.
- Backlog #633 (new): E2 plus the differential case.
- Backlog #634 (new): slice 4's obligations 1 to 3, and the deletion of `cross=False` afterwards.

## Checked and found sound

- Every round-1, round-2 and round-3 reviewer input, re-expressed as a form in the harness, refuses at master. [M]
- A socket path is tagged `False` and gets every check; the round-3 "taken for a shadow" mutation still names a
  case. [M: manifest entry "a socket path is taken for a shadow"]
- `cross_run`, `_meets` and `merge_seeds` hold no path logic of their own beyond prefix comparison; they cannot
  re-open the exemption. [I]
- Self-test at master: 288/288. [M]

## Bound of this review

- The harness's lines are hand-written in strace's format, not substituted into the recorded samples the module's
  own cases use. They parse and classify (25 refuse for path reasons, none for `log did not parse`).
- 27 forms is a sample. It covers every refusal reason an open's path can earn; it does not cover other calls
  (`stat`, `rename`, `execve`), which have no SHADOW.
- The pre-existing-link forms ran on macOS's filesystem under a temp directory. `os.path.realpath` behaving the same
  on the runner is inferred.
- The mutation sweep on E2 stopped at the five unbound anchors, as the harness is built to. The other 202 were not
  run against E2.
- No CI run was triggered for the prototypes.
- Probe files, in this session's scratchpad under `p6/`: `diff_harness.py`, `e2.diff`, `e2-sweep.out`, and the four
  historical copies `v-<sha>/`.

## Measured and inferred, separated

| # | Claim | Status | How |
|---|---|---|---|
| 1 | The self-test is 288/288 at master `2c691771` | MEASURED | ran it |
| 2 | Violations per head: 22, 19, 10, 0 of 27 | MEASURED | `diff_harness.py` against `git show` copies of `42ba603d`, `e2fe1d29`, `aa5c4d78`, `fc5e0380` |
| 3 | Round 2 fixed 9 of the 19 and round 3 the other 10 | MEASURED | the per-form rows of the same runs |
| 4 | Only instance cases exist for the class (2 for round 2, 3 for round 3) | MEASURED | the case names in the file |
| 5 | Nothing outside the module calls `resolve_log`, `resolve_calls` or `record_from_log` | MEASURED | `grep` over `scripts/` and `.github/` |
| 6 | A new `from_label is False` check in `_cwd_pass` exempts SHADOW at master, and does not under E2 | MEASURED | one hypothetical rule patched into in-memory copies of both |
| 7 | E2 is +11/−10 lines, 288/288, 0 violations | MEASURED | applied to the worktree, ran, reverted |
| 8 | E2 unbinds 5 of 207 mutation anchors | MEASURED | `check-plan-code.py --mutate . --only scripts/strace_reads.py` on E2 |
| 9 | E1 (no read view) fails exactly 3 of 288 cases | MEASURED | both `cross` defaults flipped, ran, reverted |
| 10 | The pre-existing-link refusal disappears when the link is gone at parse time | MEASURED | the round-3 input B, parsed three times |
| 11 | Both recorded whole logs are `complete` in both views; 284 labelled opens, 0 with `..` or `/proc` | MEASURED | a script over `scripts/fixtures/strace-lines/whole-*.log` |
| 12 | The exemption came from carrying slice 2's rule for the label over to the argument | INFERRED | the bound at `:77` and the round-1 coordinator's sentence |
| 13 | A property case would have been written in round 1 had the fold rule asked for one | INFERRED | counterfactual |
| 14 | The final pin under E2 is about 206 | INFERRED | 5 unbound, 2 become duplicates, 1 owed |
| 15 | No edit to `_cwd_pass` is scheduled before slice 4 | INFERRED | backlog #586's row; no open PR was checked for it |
| 16 | The real corpus has guards whose labelled opens hold `..` | NOT KNOWN | slice 4's count answers it |
| 17 | `cross_run`, `_meets` and `merge_seeds` cannot re-open the exemption | INFERRED | reading |

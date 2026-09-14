# record-review-topology — round 14, Claude half

**NOT CONVERGED.** One High, one Medium, one Low. The High is **not** in the repair the round was
convened to review — the repair is sound and I verified its load-bearing properties by execution.
It is in `check-review-recorded.py`, the gate this branch ships, which **fails open**: a rename that
pairs a guarded source with a prose destination makes a deleted code file invisible to both of the
gate's questions, and the run exits 0 saying *"no guarded path changed"*. Measured end to end, with
a control proving the cause.

Round 13's Claude half said ~1,800 lines of review had gone into the instrument rather than into the
gate. I tested that claim rather than inheriting it, and it is **correct**: the defect below sits in
two lines this branch edited, and is an instance of a class the file's own docstring names.

Subject: worktree `.yps-worktrees/review-topology`, HEAD `dc9fe107` + the uncommitted delta.
All work done in an isolated copy (`rsync --exclude=.git`, git reachability asserted absent); no
mutating git anywhere; nothing written under `docs/reviews/`.

---

## Baseline — measured on this tree, in the isolated copy

```
codex-review          --self-test   85/85   rc=0     check-review-recorded --self-test  117/117 rc=0
check-plan-code       --self-test  128/128  rc=0     check-ratchet-contract --self-test  41/41  rc=0
check-fixture-variation  511 params, 50 files        check-selftest-counts  38 scripts, all verified
check-review-rounds   233 parsed, 0 silent gaps      check-guard-coverage / check-docs / check-anchors  rc=0
```

---

## H1 — the shipped gate reports "no guarded path changed" over a DELETED code file

**Claim.** `changed_paths` (`scripts/check-review-recorded.py:657`) and `added_paths` (`:675`) run
`git diff --name-only` with git's **default rename detection ON**, while the sibling
`_changed_since` (`:499`) this branch added passes `--no-renames`. When a guarded file is paired by
rename detection with a prose destination, `--name-only` prints **only the destination**, so the
guarded source disappears from the gate's view of the diff and `guarded_changes` returns empty.

**Failure scenario, measured.** Scenario 1 — a branch moves `lib/x.ts` into `docs/` with a small
edit and records no review at all:

```
$ git diff --name-status --no-renames master-base HEAD      # ground truth
A       docs/x.ts
D       lib/x.ts

$ python3 scripts/check-review-recorded.py --base master-base
ok — no guarded path changed — a review round is not required
rc=0
```

A code file left the tree, no review document, no `NO-REVIEW:` declaration, exit 0. This is the exact
outcome the file's `WHY THIS EXISTS` section was written against.

**It defeats the SECOND question too, and that half is this branch's own code.** `tail_candidates`
(`:326`) computes `(set(after) | set(reviewed)) & set(branch_delta)`. `after` comes from
`_changed_since` (`--no-renames`, so it *does* contain the renamed-away path) and `branch_delta`
comes from `changed_paths` (rename-detected, so it does *not*). The intersection silently drops the
path, and the round is credited with having seen it. Scenario 2 — same rename, plus a genuine fix
that a round's verdict does cover:

```
$ git diff --name-status --no-renames master-base HEAD
A  docs/reviews/codex/subject-r1-codex.md
A  docs/reviews/verdicts/subject-r1-codex.verdict.json
A  docs/x.ts
D  lib/x.ts
M  lib/y.ts

$ python3 scripts/check-review-recorded.py --base master-base
ok — review recorded in this range: docs/reviews/codex/subject-r1-codex.md
ok — the final tree was in the tree handed to subject-r1-codex.verdict.json
rc=0
```

`lib/x.ts` is deleted by the merge, appears in no verdict's `dirty` map, and the gate says the final
tree was handed to the reviewer.

**Control — the flag is the cause, not something else.** Adding `--no-renames` to `changed_paths`
and `added_paths` in a copy of the same two repositories, changing nothing else:

```
scenario 1 -> FAILED — 1 guarded path(s) changed and no review round was recorded:
                  lib/x.ts                                                        rc=1
scenario 2 -> FAILED — 1 round(s) ran and guarded code was committed after every one of them.
                  The closest (subject-r1-codex.verdict.json) never saw: lib/x.ts  rc=1
```

**The rename policy was measured, not assumed** (git 2.49.0, `diff.renames` unset → default true):

```
git diff --name-only              master HEAD  ->  docs/x.ts
git diff --name-only --no-renames master HEAD  ->  docs/x.ts + lib/x.ts
```

**Provenance, stated honestly.** The rename policy in those two functions is **inherited from
`origin/master`** (PR #285) — `grep -c no-renames` on `origin/master:scripts/check-review-recorded.py`
is `0`. What is new here is that this branch (a) edited both of those exact lines for the r11 `-z`
repair, (b) wrote `_changed_since` **with** `--no-renames` at the same time, and (c) built
`tail_candidates` to intersect the two lists, which is what turns a latent inconsistency into a
second live fail-open. The `-z` docstring at `:638-644` says the sibling fix was *"fixed there as an
INSTANCE, not searched for as a class, which is this project's own recorded failure shape."* The
same sentence is true of `--no-renames`, one flag over, in the same three functions, written in the
same round.

**Fix.** Add `--no-renames` to both subprocess calls. `codex-review.py:375` already passes it on
`diff-index`, so this makes producer and consumer agree rather than inventing a policy. It needs a
case (`split_nul` is already the pure seam; the rename policy is not currently reachable from one)
and a manifest entry — deleting the flag must go red via a named case, or the repair repeats r13's H1
in a different file.

---

## M1 — "the obvious manifest entry is IMPOSSIBLE" is false, and it is asserted in three places

**Claim.** `check-plan-code.py:3101-3107`, the r13 coordinator document (§*The obvious manifest entry
is IMPOSSIBLE*) and the design of the repair all state that a mutation reverting `case_line` to
`got={got!r}` **cannot be attributed**. It can. I wrote two such entries and the real harness reports
`attributed=True` for both.

**Refuted by execution**, driving `check_plan_code.run_mutations` over a staged `HARNESS_TREE`:

```
CANDIDATE A: case_line reverts to the broken `got={got!r}` shape        caught=True  attributed=True
CANDIDATE B: same revert, attributed via a boolean case's garbled name  caught=True  attributed=True
CANDIDATE C: same revert, expect = the real case name                   caught=True  attributed=False
```

Candidate C is the control: with the *undamaged* case name as `expect` the entry is indeed
unattributable, which is the observation the claim was built on. But attribution is exact equality
against whatever `parse_fail_names` returns, and the mutant's output is deterministic, so the garbled
name is a writable string. Candidate B's `expect` is the short, stable one:

```
"the line keeps the canonical shape the harness documents: got=False"
```

That is a boolean case, so the tail is a literal `: got=False` under any revert of the `": got "`
delimiter — it does not embed a list repr and does not move with the fixture values. The coordinator
computed the ugly long-form variant (candidate A) and, having seen it, wrote **impossible**. The
short form was available and was not looked for.

**Why this is Medium and not Low.** The regression itself *is* caught — `--self-test` goes
`80/85`, rc=1 — so nothing is unguarded today. The defect is the assertion. This branch's stated
signature failure is *a comment asserting a property the code lacks*; r13's M1 was exactly that, and
the repair for it introduced a new false claim of the same shape in the same commit block. An
"impossible" written into a guard's source is a durable instruction to future authors not to try.

**Fix.** Either add candidate B as a twelfth entry (`EXPECTED_MUTATIONS` 11 → 12, declared total
620 → 621), or keep the entry count and rewrite the claim to what was actually measured: *the
detecting case's name is garbled, so an attributable entry must name the garbled form; we judged
that too brittle to ship.* The second is a legitimate engineering choice. **Impossible** is not.

---

## M2 — a review document that arrives by RENAME is invisible to `review_added`

**Claim.** Same root cause as H1, opposite direction. `added_paths` uses `--diff-filter=A` with
rename detection on, so a review document *moved* into `docs/reviews/` is classified `R` and never
reaches `review_added`.

**Measured.** A branch performing the `docs/reviews/<writer>/` relocation this project actually did
(backlog #92, and `docs/plugins.md` now mandates that layout), plus one code change:

```
$ git diff --name-status --no-renames master-base HEAD
A  docs/reviews/codex/subject-r1-codex.md
D  docs/reviews/subject-r1-codex.md
M  lib/y.ts

$ python3 scripts/check-review-recorded.py --base master-base
FAILED — 1 guarded path(s) changed and no review round was recorded:
    lib/y.ts
rc=1
```

```
git diff --name-only --diff-filter=A              master HEAD  ->  (nothing)
git diff --name-only --diff-filter=A --no-renames master HEAD  ->  docs/x.ts
```

This is a false FAIL, so it is Medium rather than High — but it is the *kind* of false FAIL this
file itself cites backlog #56 about: a gate that fires on a branch doing the right thing is a gate
that gets switched off. Fixed by the same one-flag change as H1; listed separately so a fixer does
not patch `changed_paths` and leave `added_paths`.

---

## L1 — `case_line`'s `(reason)` tail is safe, but only as a fact about today's data

**Claim.** The repair's safety argument is *"no `reason` contains `': got '`"* (`codex-review.py`
`case_line` docstring, and the comment at the classifier printer). I verified it — 14 reason tails
across the suite, **0** containing the delimiter — but nothing enforces it. A future classifier
reason containing `": got "` silently garbles the name of every classifier case that fails.

`parse_fail_names`' own docstring already records the same hazard for case *names* (*"Zero of the
live case names contain it today. This function is where that fact is visible."*), so the posture is
consistent with the repo's. Recorded rather than filed as a defect; closing it is a one-line
assertion over `REASONS`, which is a new rule and therefore another round.

---

## What I verified and found CLEAN

Stated positively, because a review that only lists problems hides how much was actually measured.

1. **`case_line` is the single shape.** `grep` over `scripts/codex-review.py` finds exactly one
   `[PASS]`/`[FAIL]` emitter (`:865`), reached from exactly two `print` sites. No third path.
   It is not byte-identical to either old printer, deliberately — both old shapes were the broken
   `got=` form the repair exists to delete.

2. **Every one of the 85 cases is attributable — proved by forcing all of them red.** I replaced
   `case_line` with a wrapper that forces `ok=False` while keeping each case's real `got`/`want`,
   captured the output at the `print` boundary, and parsed it with the harness's own
   `parse_fail_names`:

   ```
   printed lines: 86 | [FAIL] lines: 85 | parsed: 85
   suspicious lines: 0        duplicate parsed names: none
   ```

   Every line carries exactly one `": got "`, every parsed name is the case's real name, and no two
   cases share a name. This is the class question — *can any case in this file be attributed to?* —
   answered by executing rather than by reading printers, which is how it was missed twice.

3. **The two literal-shape cases assert BOOLEANS for a real reason.** Under the `tail = ""` mutation
   (manifest entry 10) the boolean form parses back to
   `the line keeps the canonical shape the harness documents` — readable, and the manifest's `expect`
   matches it. Had the case compared the line strings directly, the `want` repr would put a second
   `": got "` in the output and the name would truncate mid-repr. The recorded rationale is correct.

4. **Counts, all recounted independently, none trusted from a tally.**
   `EXPECTED_MUTATIONS`: 44 files, sum **620**; manifest entries on disk: 44 files, sum **620**;
   zero per-file mismatches. `codex-review.py`: `len(cases)=17` + 68 `chk` call sites = **85**,
   equal to the docstring's declaration and the printed denominator. The only surviving
   `extra += <literal>` in the file is the `extra += 1` inside `chk` (`:971`) — the two others
   `grep` finds are inside the comment that explains their removal. `check-selftest-counts.py`
   independently verifies 38 declared counts by running them.

5. **Every `expect` in both changed manifests resolves to a real case name.** AST cross-check over
   all 44 manifests: in `check-review-recorded.json` (35 entries) and `codex-review.json`
   (11 entries) every `expect` is a literal case name in its target, except two that are
   f-string-generated (`f"{_p} is guarded"` / `is prose`, `:773`/`:776`) and therefore legitimately
   absent from the literal set.

6. **Importing `parse_fail_names` from `check-plan-code.py` is safe.** No cycle (that file never
   imports `codex-review`). Cost **≈0.08 s** per suite run (0.13 s module exec vs 0.05 s bare
   interpreter), against 11 spawned runs — unmeasurable next to the harness. No stray output:
   `--self-test` writes 87 stdout lines and **0** to stderr, none outside the `[PASS]`/`[FAIL]`/tally
   grammar, so nothing the parser could mistake for a case. `if __name__ == "__main__"` is guarded
   and the module name is `_cpc`, so `main` cannot fire. Its one module-level side effect is
   `sys.path.insert(0, scripts/)` — which `codex-review.py:62` already does itself, so it is a
   no-op, and no file in `scripts/` has an importable name that shadows a stdlib module.
   **When `check-plan-code.py` is itself the mutated target, nothing changes**: `run_suite_parts`
   (`:487`) runs `[sys.executable, <the mutated file>, "--self-test"]`, so only the mutated file's
   own suite runs. Cross-file mutation contamination is structurally impossible here.
   It works under the staged tree with a redirected `$HOME` — probes 1 and 3 above ran through
   `stage_tree` + `child_env` and the control was green (`85/85`).

7. **Regression — nothing r13 reviewed has moved.** AST-level comparison against `HEAD:` (comments
   ignored): in `codex-review.py` the only functions that differ are `case_line`,
   `_load_fail_parser`, `chk` and `self_test`; `reviewed_state`, `unredirected`, `verdict_record`,
   `classify`, `watched_dirs` and `main` are byte-identical. In `check-plan-code.py` only `_self_test`
   differs — `load_manifests` is **AST-identical**, confirming its change is comment-only as the
   diff claims. `check-review-recorded.py` is untouched by the delta, so `tail_candidates`,
   `classify_verdict` and `second_question` are unchanged since r13 read them.

8. **The branch's own gate, run against itself**, correctly reports `rc=1` / *"10 round(s) ran and
   guarded code was committed after every one of them"* — because r11–r13's verdicts are still
   untracked. That is the expected state of a branch holding its fixes uncommitted, not a defect,
   and it is what the r14 Codex run exists to clear.

---

## On the frame — the question round 13 raised and round 14 asked me to test

The claim I was asked not to inherit was that the rounds have been re-deriving by hand properties the
mechanism could hold, and that the attention went to the instrument rather than to the gate.

**Tested, and it holds — with evidence rather than assent.** The repair under review is good work:
two printers became one, the contract is asserted against its real reader, and I could not break any
of the 85 cases' attributability under forcing. But the defect I found is in `check-review-recorded.py`,
in two `subprocess.run` lines that thirteen rounds read past, and it is the *same class* as a finding
one of those rounds filed about the *same two lines* — `-z` was added to both in r11 and
`--no-renames` was not, while the function written in that same round has it. Thirteen rounds of
attacking the mutation harness did not look at whether the gate's own `git diff` is the diff it
reasons about.

That is not an argument for a fourteenth round of instrument review. It is the concrete form of
*"after fixing, SEARCH for the class"*: the r11 repair searched for `-z` across three call sites and
stopped at the flag it was thinking about.

**A note on my own method, stated so it can be checked.** Every claim above that says *measured* was
produced by running code in an isolated copy, and the two behavioural claims carry controls
(candidate C for M1; the `--no-renames` patch for H1/M2). Three claims are reading, not execution,
and are labelled as such: the provenance of the rename policy on `origin/master` (a `grep -c`), the
realism of a guarded→prose rename, and the judgement that candidate B is "stable enough to ship".

---

## Verdict

**NOT CONVERGED.** H1 is a measured fail-open in the gate this branch exists to add, in lines the
branch edited, and it should not merge without the flag and a case that can fail for its absence.
M1 is a false claim in a durable comment, of the class this branch was convened to remove, and is a
five-minute fix in either of two acceptable directions. M2 rides on H1's one-line change and is
listed separately so it is not left behind.

VERDICT: NOT CONVERGED

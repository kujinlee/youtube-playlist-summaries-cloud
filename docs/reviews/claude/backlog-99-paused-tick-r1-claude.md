# Code review r1 — `backlog-99-paused-tick` (673b4a8b) — CLAUDE half

Base `origin/master` = `aea0994b`. Diff reviewed: `git diff origin/master...HEAD` (10 files,
+621/−28). Independent half — no Codex output was read.

**Verdict: NOT CONVERGED.** 0 Blocking · 1 High · 3 Medium · 8 Low.

Method: every premise below was executed, not read. Both suites were run; all 17 new mutations were
applied to temp copies and their red-case sets recorded; the branch's own scripts were driven
against a throwaway repo root and compared side-by-side with an `origin/master` control.

---

## What I verified as CORRECT (stated so it is not re-litigated)

These are the things the brief asked me to attack and which held up under execution.

**The `{0, 3}` allow-list is not a fail-open.** I injected each failure shape into a copy and read
the exit code:

| shape | exit | hook verdict |
|---|---|---|
| runtime exception inside `decide()` | 1 | BLOCK (`block-idle-stop.sh:99`) |
| `SyntaxError` in the module | 1 | BLOCK |
| unknown flag (argparse) | 2 | BLOCK |
| script file missing | 2 | BLOCK |
| SIGTERM | 143 | BLOCK |
| paused with steps outstanding | 3 | allow + exit 1 (stderr shown) |

`WARN` is returned at exactly four sites (`check-plan-progress.py:160`, `:169`, `:186` — and only
`:186` is the non-cannot-run one), every one of them guarded by `paused is not None`. There is no
new path that allows a stop the base blocked. **Caveat, pre-existing:** invoked with *no* action
flag the script exits 0 (`:426-436` falls through). The hook always passes `--decide`, and base
behaves the same, so this is context, not a branch finding.

**`strip_field` and `parse_sentinel` agree.** I ran a differential oracle over the brief's awkward
inputs plus a 20,000-case identity fuzz over the alphabet `ab: \n\r\t\x0b\x0c\x85#-`:

- CRLF, no-final-newline, `  paused: x`, `\tpaused : x`, colon-less `paused`, `plan: paused.md`,
  `paused:` with an empty value, `Paused:` (case), doubled `paused:` — **all agree**, 0 divergences.
- `strip_field(t, absent_key) == t` for all 20,000 fuzz inputs — 0 failures.

Both use the same `str.splitlines()`, so their line partitions cannot disagree by construction, and
`"".join(splitlines(keepends=True))` is exactly identity. The `if "paused" in fields` guard at
`:149` also correctly keeps an *empty* pause reason (`paused:`) distinguishable from an absent one.

**The anti-nag is untouched.** All three WARN returns pass `None` as the third element, so
`run_decide:257` (`elif unticked is not None`) never writes `STATE` on a paused turn. I traced
(pause → resume → stop → stop): identical to base, because the anti-nag also requires
`stop_hook_active`, which is false on the first stop after a resume. `None` is correct on every new
path. *(The justification comment at `:182-185` is stronger than the facts — see L4.)*

**All 17 mutations are caught via the case they name.** Measured, per entry, on temp copies:
`begin-plan.json` 7/7, `check-plan-progress.json` 10/10, every `expect` resolving to a red case that
is present in the measured red set. `EXPECTED_MUTATIONS` sums to 203 and the manifests on disk
contain 203. `MANIFEST_BASELINE = 21` matches what `check-ratchet-contract.py` actually prints.
`check-selftest-counts.py` verifies 31 and 42 by running them. `check-plan-code.py --self-test`
189/189, `check-docs.py` OK, `check-dashboard-entry.py` OK.

⚠ **NOT RUN BY ME:** `check-plan-code.py --mutate .` over all 203. The dashboard entry and backlog
row both claim *"203 mutations, 0 survivors"*. I verified the 17 new ones directly and left the
other 186 to CI. **Treat the full-suite figure as unverified by this review.**

**Item 7 (other consumers of the `case()` output format).** Searched `scripts/*.py`,
`.claude/hooks/*.sh`, `.github/workflows/*.yml` for `FAIL`. The only parser is
`check-plan-code.py:887` (`l.strip().startswith("[FAIL] ")`), and the two changed suites now match
it. `check-selftest-counts.py` reads the `N/N self-test cases passed` line, which is unchanged.
Nothing else parses either suite. **No consumer breaks.**

---

## H1 — High: a PAUSED sentinel with every step ticked is now DELETED, silently, and the human's pause reason with it

`check-plan-progress.py:173-179` moves `unticked == 0` **above** the paused branch, and
`run_decide:254-256` unlinks the sentinel on `unticked == 0`. Combined with the ALLOW path's stdout
routing at `:267`, a paused plan whose boxes are all ticked is destroyed with **zero visible
output**.

MEASURED, both directions, same fixture:

```
sentinel: plan: .claude/plans/p.md / armed: x / paused: waiting on CI before opening the PR
plan:     2 of 2 ticked

origin/master  →  exit 0, sentinel PRESERVED
HEAD           →  exit 0, message on STDOUT, sentinel DELETED
```

The message that is lost is `"✅ every step in ... is ticked (2/2). Clearing ..."`. It goes to
**stdout**, and this commit's own comment at `check-plan-progress.py:260-265` is the authority for
what that means: *"`block-idle-stop.sh` surfaces a hook's STDERR to the human on exit 1 and swallows
its stdout"*. `PROGRESS_RC` is 0 here, so `block-idle-stop.sh:121` is false and the hook exits 0 —
nothing is shown at all.

**It is reachable by the ordinary path, not a contrived one.** Driven end to end:

```
$ begin-plan.py --pause "waiting on CI before the PR"        # plan already 2/2
paused: waiting on CI before the PR
⚠ WHEN THE WORK RESUMES, run `scripts/begin-plan.py --resume` FIRST. …          [exit 0]

$ check-plan-progress.py --decide                            # the very next Stop
✅ every step in `.claude/plans/p.md` is ticked (2/2). Clearing …               [exit 0, stdout]

$ begin-plan.py --resume
refusing: nothing is armed, so there is nothing to resume.                      [exit 1]
```

`cmd_pause` (`begin-plan.py:388-398`) does not refuse a fully-ticked plan, and the measured #99
incident was itself a checkpoint pause (`paused: T1+T2 committed and pushed`). So `--pause` promises
`--resume`, and one turn later `--resume` says the thing it promised does not exist. The promise is
made by code this branch added (`:396-398`); the contradiction is created by code this branch added
(`:173-179`).

**Why this is not just a tidy-up.** Three separate house rules land on it:

1. The branch's own thesis, stated at `:139-142`: *"from here on it is never SILENT"*. This is the
   one paused outcome that is not merely silent but destructive, and it is the one exempted.
2. *A guard's own OUTPUT is part of its contract.* The only notice of a deletion is emitted on the
   stream this same commit documents as reaching nobody — the exact failure CLAUDE.md records
   against `begin-plan.py`'s banner.
3. Backlog #94 widened `paused:` to mean *blocked on in-flight work*. For that reading, "every box
   ticked" does not mean "over"; it means "waiting". The sentinel and the free text saying **what**
   it waits on are both discarded, and `--resume` cannot bring them back.

The self-test case `"paused with EVERY step ticked -> allow and CLEAR the sentinel"`
(`:359-361`) asserts the clearing and asserts nothing about anyone being told. The comment at
`:174-175` argues the case for clearing but never confronts the silence.

**Fix, smallest form:** on that branch, when `paused is not None`, return `WARN` with a message that
names the pause reason being discarded, and keep `unticked = 0` so the clear still happens. That
satisfies both rules at once — it is exactly the combination `:152-155` already reasons its way to
on the cannot-run arms. **What would make this Blocking:** a case where the plan is not in fact
finished (`--pause` at a checkpoint on a plan whose remaining work is tracked outside the checkbox
list) — then the guard is disarmed permanently with no recoverable record.

---

## M1 — Medium: `block-idle-stop.sh` cites five `check-plan-progress.py` line numbers that were EXACT on base and are all wrong on HEAD — in the comment block this commit edits

`.claude/hooks/block-idle-stop.sh:74-84` is the corrected-2026-09-05 paragraph. This commit inserts
a new paragraph directly beneath it at `:86-96` and leaves the citations pointing into a file it
grew by ~60 lines. Measured, `sed -n Np` on both refs:

| cited | claim | `origin/master` | HEAD | correct now |
|---|---|---|---|---|
| `:105` | plan-file-missing block | `if plan_text is None:` ✅ | `return "".join(kept)` | **161** |
| `:109` | *"Fix the path or delete …"* | that line ✅ | a docstring | **158** |
| `:113` | zero-checkboxes block | `if total == 0:` ✅ | blank | **170** |
| `:130` | the anti-nag | the anti-nag line ✅ | `stop_hook_active: bool,` | **204** |
| `:183` | `elif unticked is not None` | that line ✅ | a prose comment | **257** |

Five for five exact before, zero for five after. This is the third recorded correction to that same
comment block (`:8-16`, `:74-84`), and the file's own history is the argument for why it matters: it
exists because *"the r1 fold checked WHERE this comment sat and never re-read WHAT it claimed."*

*(Separately and pre-existing: the header at `:11-12` cites the three invocations as `:48`, `:56`,
`:67`; on base they were `:62`, `:82`, `:93` and on HEAD they are `:65`, `:97`, `:110`. Already
wrong before this branch — noted so it is not mistaken for collateral, but it is now wronger.)*

## M2 — Medium: `check-plan-progress.py:94` cites `check-banner-armed.py:499`, and the same commit moved that line by six

`strip_field`'s docstring (`:94`) and the self-test comment (`:372`) both cite
`check-banner-armed.py:499` for *"a colon-less `paused` line is a key to one parser and not the
other"*. On `origin/master`, `:499` was inside that paragraph. This commit inserts a six-line
`⟳ 2026-09-06` paragraph at `check-banner-armed.py:497-502`, so:

- HEAD `:499` = `outstanding. That is a change to what it SAYS, not to whether it allows, …` — the
  **new** paragraph, which is about something else.
- The cited near-miss now lives at `:503-508`.

Both the citation and the line it broke were written in this same commit. Same class as M1, hence
the same severity; listed separately because it is a different file and a different edit.

## M3 — Medium: `--pause` accepts a multi-line reason, and `--resume` reports success while leaving the residue behind

`cmd_pause` (`begin-plan.py:395`) writes `f"\npaused: {why.strip()}\n"` with no rejection of, or
escaping for, embedded newlines. `strip_field` — correctly, since it mirrors `parse_sentinel` —
removes only the line that *is* the `paused` field. The continuation lines survive, and if any of
them has `key: value` shape it becomes a live sentinel field. Driven for real:

```
$ begin-plan.py --pause $'waiting on review\nplan: .claude/plans/other.md'
$ cat .claude/executing-plan
plan: .claude/plans/p.md
armed: x
paused: waiting on review
plan: .claude/plans/other.md          ← injected; parse_sentinel is last-wins

$ begin-plan.py --resume
resumed: the Stop guard is armed again and will refuse a stop with steps outstanding.   [exit 0]

$ cat .claude/executing-plan          ← the injected line survives the "resume"
plan: .claude/plans/p.md
armed: x
plan: .claude/plans/other.md

$ check-plan-progress.py --status
.claude/plans/other.md: 0/1 steps ticked, 1 remaining      ← guard now supervises the WRONG plan
```

`--pause` is pre-existing; `--resume` and its "resumed:" assertion are this branch's. The branch's
own framing (`strip_field` docstring, `:92-98`) is that one owner answers *"which line is the paused
line"* — that is true and holds, but it presumes the pause **is** one line, and nothing enforces
that. `cmd_pause` should refuse or collapse a `why` containing a newline. One line, at the writer.

---

## Low

**L1 — the WARN message's `--resume` guidance has no dedicated mutation, while its `cmd_tick`
counterpart does.** `begin-plan.json` has *"the tick refusal stops naming the only command that
clears the pause"*, isolating that case (measured: 1 red case). `check-plan-progress.json` has no
equivalent: the case `"the warning names the command that re-arms the guard"` (`:344-345`) goes red
under exactly one mutation — the blunderbuss *"paused short-circuits to a silent ALLOW again"*,
which reddens **7 cases at once**. So the only text telling a human how to leave the paused state on
the Stop path is guarded only incidentally. The manifest comment at `check-plan-code.py:612-616`
lists what the ten mutations weigh — *"dropping the count, dropping the human's pause reason"* — and
does not notice that the third element of the same message is unweighted. Same class, one end
covered.

**L2 — `"the refused tick leaves the plan BYTE-IDENTICAL on disk"` is never the sole red.** Measured
red sets for the two mutations that touch it:

- *"--tick stops consulting the pause"* → 5 red, including `"cmd_tick REFUSES on a paused plan"`.
- *"--tick warns about the pause but ticks anyway"* → 3 red, also including that case.

The harness's rule (each `expect` must resolve to exactly one red case) is satisfied, and the case
does reach the branch it claims — it genuinely reddens when the tick writes. But no mutation
isolates it, so it is not independently proven load-bearing. A mutation that keeps `return REFUSED`
and moves the write above it would.

**L3 — `"cmd_resume leaves the plan itself untouched"` is not about `cmd_resume`.** Measured: it
goes red under *"--tick warns about the pause but ticks anyway"*, a mutation of `cmd_tick`, and
under no mutation of `cmd_resume`. It re-reads the same `before` snapshot as L2's case
(`begin-plan.py:571`, `:600`), so it reddens whenever *any* earlier command in the sequence wrote
the plan. The name attributes an observation to the wrong subject.

**L4 — the `None`-not-`unticked` justification at `check-plan-progress.py:182-185` is stronger than
the facts.** It says a count written while paused *"would satisfy `unticked >= prev_unticked` on the
first stop AFTER the resume, allowing it"*. The anti-nag at `:204` also requires `stop_hook_active`,
which is false on a first stop in a fresh turn. The behaviour is right and conservative; the stated
reason omits a conjunct, and the self-test comment at `:348-351` repeats it verbatim.

**L5 — `"WARN is not BLOCK — the pause escape still works"` (`:340`) goes red under none of the ten
mutations.** It is strictly implied by `:352-353` (`WARN not in (ALLOW, BLOCK, 1)`), which does have
an isolating mutation. Redundant rather than vacuous — a `WARN = 2` mutation would separate them —
but nothing exercises it, so it currently asserts nothing the suite does not already assert.

**L6 — `--banner` renders a paused plan identically to a running one.** Measured on a paused 1/2
plan: `## ▶ STEP 2 of 2 — Step 2 … (plan: … — 1/2 ticked. --tick when this step is done.)`, with no
mention of the pause. `--status` *does* print `PAUSED: waiting on CI` (pre-existing, correct). The
banner is the command the actor runs *before* doing the work, and the tick refusal only fires
*after*, so the wasted-work window #99 describes is narrowed but not closed. Scope call, not a
defect in what shipped.

**L7 — `cmd_tick` reads and parses the sentinel twice.** `_armed_plan()` (`:258-266`) already does
`SENTINEL.read_text()` + `parse_sentinel()` and discards the fields; `:351-352` re-reads and
re-parses, and calls `_load_plan_progress()` a second time (re-executing the whole
`check-plan-progress.py` module body). Answering the brief's item 5 directly: `_armed_plan()`
succeeding and the second read failing requires the sentinel to be deleted between the two calls,
which raises an uncaught `FileNotFoundError` — traceback, exit 1, which happens to equal `REFUSED`,
so the exit code is right for the wrong reason. Not a real hazard (single-process, no concurrency),
but returning the fields from `_armed_plan()` removes the question entirely.

**L8 — `paused = fields.get("paused") if "paused" in fields else None` (`:149`) is exactly
`fields.get("paused")`.** `parse_sentinel` only ever stores `str` values, so `.get` returns `None`
iff the key is absent. The conditional reads as if it defends the empty-reason case; it does not
defend anything, because there is nothing to defend. Harmless, and arguably self-documenting — but
no mutation can distinguish the two forms, so it is untested by construction.

**L9 (pre-existing, newly surfaced) — an unreadable plan file is reported as "does not exist".**
`_read` (`:232-236`) catches `OSError` and returns `None`; `:156` then says *"which does not
exist"*. Measured with `chmod 000` on the plan: the paused path prints
`⏸ PAUSED (waiting) — and CANNOT RUN: … which does not exist.` Not a regression — base allowed
silently — but this branch is what puts that sentence in front of a human for the first time on the
paused path.

---

## Dispositions requested

- **H1** — needs a decision, not just an edit: clear-and-say-so (WARN) vs. refuse-to-clear-while-
  paused. I recommend clear-and-say-so; it keeps the stale-sentinel property the branch wanted and
  costs one `return WARN`.
- **M1, M2** — mechanical; repoint the ten citations.
- **M3** — one line in `cmd_pause`.
- **L1** — one manifest entry; it closes the asymmetry the branch itself identified on the other half.
- **L2–L9** — record dispositions; none blocks a merge on its own.

**NOT CONVERGED.**

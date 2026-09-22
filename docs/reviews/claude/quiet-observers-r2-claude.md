# quiet-observers — round 2, Claude half

Subject: `131c94b7` on `quiet-stop-observers-wt`.

REVIEW GAP: codex — rounds 2+ ALTERNATE by design; the Codex half ran as round 1

**Method.** Everything below was RUN. Nothing was mutated in either working tree: `scripts/` was
copied to a scratchpad staging directory and mutated there, with `$HOME` redirected to a fake home
for every child process, and the staged copy restored from the worktree between probes (the control
was re-proved green after the last restore). The two end-to-end drives used a throwaway repo root
inside that staging directory, so `begin-plan.py`'s `ROOT = Path(__file__).parent.parent` resolved
to the copy and never to a real checkout. No mutating `git` command was run. `check-plan-code.py
--mutate .` was **not** re-run — round 1 recorded 890/890 killed / 0 survivors and an instance was
already running in the other tree; a second 35-minute sweep would have measured the same manifest.
Instead I measured what a manifest-driven sweep structurally cannot: decision points with **no
manifest entry**, by hand-mutating them and watching the suite stay green.

Controls: every "this goes quiet" claim below is preceded by the same input proved LOUD first.

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | Medium | The `no_pr` decision at its CALL SITE has no falsifier, and neither does the handler that sets its fail direction — 3 mutations, suite green on all 3 |
| 2 | Medium | `cmd_pause`'s unreadable-plan handler is unfalsifiable, and removing it makes `--pause` crash without recording the pause — the escape hatch, trapped |
| 3 | Medium | A second `--pause` re-baselines the stamp and permanently erases an already-firing #99 warning. This is the case round 1 declared sound, and it happened twice in this worktree's live sentinel |
| 4 | Low | The stamp comparison is pinned on one side only: `<` → `<=` dies, `<` → `!=` survives |
| 5 | Low | Three live sites restate the exit-3 / paused contract this commit changed. All three are now false — 3 of 3, population enumerated |
| 6 | Low | The three-row decision table in the docstring and the commit message overclaims its middle row. This is the half of round 1's Medium that IS foldable here |

### 1 — Medium: the `no_pr` decision is unfalsifiable at the call site, and so is its fail direction

The branch's primary deliverable is *no PR → quiet, GitHub unreachable → loud*. The pure rule that
decides which of those it is (`_NO_PR in (p.stderr or "")`) is well covered. Everything the rule
feeds is not.

Control first, then five probes against a staged copy:

```
CONTROL                                                       rc=0

C1 — the CALL SITE: delete run_decide's 'if no_pr: return QUIET'
  suite: rc=0        <- SURVIVES

C2 — the CALL SITE inverted: QUIET on EVERY gh outcome
  suite: rc=0        <- SURVIVES

C3 — the gh command itself: ask for the wrong field
  suite: rc=0        <- survives (PRE-EXISTING: `_run`'s argv was never asserted either)

C4 — _pr_checks_raw swallows a gh CRASH as 'no PR' (silence on OSError)
  suite: rc=0        <- SURVIVES

C5 (reference, a branch that DOES have a falsifier) — the _NO_PR sentence is emptied
  suite: rc=1        <- killed
restored control                                              rc=0
```

The mutations, verbatim:

* **C1** `    if no_pr:` → `    if False:` — restores the every-stop `CANNOT RUN` this whole branch
  exists to remove. 28/28 still pass.
* **C2** `    raw, no_pr = _pr_checks_raw()` → `…; no_pr = True` — the observer goes silent on every
  branch, forever, including one with a pending check and no watcher armed. 28/28 still pass.
* **C4** in `_pr_checks_raw`, `except (OSError, subprocess.SubprocessError): return None, False`
  → `return None, True` — `gh` not installed, `gh` timing out, or `gh` crashing all become
  **silence**. The function's own docstring promises the opposite: *"a REWORD falls back to CANNOT
  RUN — noisy, not silent, which is the direction this guard must fail in."* 28/28 still pass.

`scripts/mutations/check-ci-watched.json` gained exactly two entries in `5018606b`, and both target
the return expression inside `_pr_checks_raw`. Nothing in the manifest reaches `run_decide`. So
round 1's *"890/890 killed, 0 survivors"* is true and says nothing about C1, C2 or C4 — a sweep
measures the manifest, not the code, and the three decision points added here that most need a
falsifier are the three that got none. This is the repo's recorded *unit coverage does not compose
— mutate the CALL SITE*, and the guard at issue is the one that fails open.

C3 I am **not** counting against this branch: `_run(["gh", …])` was equally unasserted before, so
the argv hole is pre-existing, not introduced.

### 2 — Medium: `--pause`'s unreadable-plan handler cannot fail, and its absence traps the human

`cmd_pause` now does plan I/O it never did before:

```python
_armed = _armed_plan()
if _armed is not None:
    try:
        _done, _total = _load_plan_progress().count_steps(_armed[0].read_text())
        if _total:
            _stamp = f"paused_unticked: {_total - _done}\n"
    except (OSError, UnicodeDecodeError):
        _stamp = ""     # unreadable plan -> no stamp, and the reader treats that as "cannot tell"
```

The delivered behaviour is **correct**, and I checked that rather than assuming it. With the plan
file deleted, and separately with the plan file holding undecodable bytes:

```
=== A. DELIVERED code: plan file DELETED, then --pause ===
paused: parked while the plan is missing
  rc=0
  sentinel:
    plan: .claude/plans/demo.md
    armed: 2026-09-22T14:14:31-07:00
    by: scripts/begin-plan.py
    paused: parked while the plan is missing        <- pause recorded, no stamp. Correct.
  --decide:
    ⏸ PAUSED (parked while the plan is missing) — and CANNOT RUN: … TREAT THIS AS NOT RUN …
    rc=3                                            <- loud. Correct.

=== B. DELIVERED code: plan file with UNDECODABLE bytes, then --pause ===
  rc=0, pause recorded, no stamp                    <- correct
```

Two mutations, both **survive** a green 53/53 control:

* **M3** the handler writes a wrong value — `_stamp = ""` → `_stamp = "paused_unticked: 0\n"`.
  A hand-editable-looking `0` stamp makes every subsequent stop read as progress. 53/53 pass.
* **M4** the handler stops catching — `except (OSError, UnicodeDecodeError):` →
  `except (KeyboardInterrupt,):`. 53/53 pass. The real consequence, driven on the same input as A:

```
=== C. M4-MUTATED (handler removed): same input as A ===
    FileNotFoundError: [Errno 2] No such file or directory: '…/.claude/plans/demo.md'
  sentinel after the crash:
    paused lines: 0
```

`--pause` dies before the `SENTINEL.write_text` on the line below, so the pause is **never
recorded**. The Stop guard then goes on blocking a human who has explicitly said "I am parking
this" — `--pause` is the documented escape hatch, and this branch gave it a new way to fail with no
case watching. `.claude/plans/` is gitignored (`.gitignore:96`), so a branch switch cannot remove a
plan; `git clean -xfd`, a removed worktree, or a hand deletion can.

### 3 — Medium: a second `--pause` silently erases an already-firing #99 warning

Round 1 listed *"Double `--pause` with a readable plan is last-key-wins and `--resume` strips all
copies via `strip_field`"* under what it attacked and found sound. The parsing claim is true — I
re-derived it independently, see *Attacked, and found sound*. But round 1 checked what the readers
**select** and never asked what the second write **means**. It means the baseline moves.

Driven end to end against the real `begin-plan.py` and `check-plan-progress.py` in a throwaway
repo, control first:

```
### 3. --pause
sentinel now:
    plan: .claude/plans/demo.md
    paused: waiting on CI
    paused_unticked: 2

### 4. CONTROL — hand-tick one step while paused (#99's own defect), then --decide
⏸ PAUSED, BUT 1 STEP(S) WERE TICKED SINCE — the guard has been stood down while the work carried on (backlog #99).
   Paused because: waiting on CI
   → `scripts/begin-plan.py --resume` re-arms it.
  rc=3  <-- the mechanism works

### 5. THE CLAIM — a SECOND --pause, with no --resume in between
sentinel now:
    paused: waiting on CI
    paused_unticked: 2
    paused: now waiting on the review
    paused_unticked: 1          <- re-baselined

--decide:
  rc=0  <-- silent. The resumed-work signal is gone, and it does not come back.
```

Not hypothetical. The live sentinel in this worktree carries **two** `paused:` lines and **two**
`paused_unticked:` lines, written by two different `--pause` calls in one session:

```
paused: thread B: Codex half dispatched (task byt0uqpd1) on 84131ec0; then the Claude half as round 2, fold, PR. …
paused_unticked: 2
paused: HANDING BACK — see .remember/remember.md in the main tree. …
paused_unticked: 2
```

Both stamps happen to read 2 here, so nothing was lost this time. The route is ordinary: park,
hand-tick something (`--tick` refuses on a paused plan, so a hand edit is the only way, which is
also round 1's scenario), park again with a fresher reason. The warning that was owed is discarded
by a command that never mentions it.

The tell is an asymmetry the code itself argues for elsewhere. `cmd_resume` REFUSES when the plan
is not paused — its own self-test case reads *"cmd_resume REFUSES when the plan is not paused — it
never invents a state."* `cmd_pause` accepts when the plan **is** paused, appends a second pair, and
overwrites the baseline. One of the two commands guards its precondition.

⚠ **This one is separable from backlog #100 and foldable inside this slice.** The repair is a
refusal or a strip-before-append in `cmd_pause`, i.e. command behaviour — it does not add, remove or
reinterpret a sentinel field, which is what the brief rules out of scope. Which repair is right I am
deliberately not deciding: a bare refusal would strand someone who legitimately needs to restate the
reason, and a proposed fix is a hypothesis.

### 4 — Low: the stamp comparison is pinned on one side only

```
M1 — '<' becomes '!=' (a plan that GREW while paused now warns)
  suite: rc=0        <- SURVIVES
M2 — '<' becomes '<=' (equal counts now warn)
  suite: rc=1        <- killed
```

The suite's two stamped fixtures are `_WAIT` (began 2, unticked 2) and `_MOVED` (began 4, unticked
2). There is **no case anywhere with `unticked > began`**, so the upper half of the comparison is
untested by construction. In the `!=` world, a plan that grew while paused takes the WARN branch and
prints `⏸ PAUSED, BUT -1 STEP(S) WERE TICKED SINCE`, and 42/42 still pass.

The same gap has a live consequence in the unmutated code, which is why it is listed here rather
than only as a coverage note. If the plan **shrinks** while paused, the loud branch reports a number
that cannot be true:

```
B. the plan SHRANK while paused (steps deleted): stamp 10, only 6 steps exist
   -> WARN   '⏸ PAUSED, BUT 8 STEP(S) WERE TICKED SINCE — …'
   (6 steps exist in total; the message asserts 8 were ticked)
```

### 5 — Low: 3 of 3 live restatements of the exit-3 contract are now false

Population derived by grep over `scripts/`, `.claude/`, `docs/dev-process.md`,
`docs/process-checklists.md` and `docs/backlog.md` for sites restating what exit 3 / a paused
verdict means, excluding `check-plan-progress.py` itself (the owner) and `docs/reviews/` (history,
correctly frozen). Three live sites; all three assert the pre-`5018606b` meaning:

| Site | Says | Now |
|---|---|---|
| `.claude/hooks/block-idle-stop.sh:33` | "returning 3 — a paused plan with steps outstanding. It is the only case where the blocking check declines to block and still has something to say" | that state returns **0, silently**, in the common case |
| `.claude/hooks/block-idle-stop.sh:119` | "the blocking check can now also return 3 = WARN: a paused plan that still has steps outstanding" | same |
| `scripts/check-banner-armed.py:505` | "decide() now returns WARN (3) rather than a silent ALLOW when a paused plan still has steps outstanding" | same |

Measured against the live sentinel in this worktree — paused, 2 of 3 outstanding, which is exactly
"a paused plan with steps outstanding":

```
decide -> 0 '' None
```

The third site is the one that matters, because it is not a comment about a number — it is a
reconciliation contract between two guards. It continues: *"Do not read a WARN over there as a
divergence from `not armed` over here — they are the same verdict, differently voiced."* The
conclusion still holds; the premise it is derived from is now false, which is the shape that gets a
future reader to trust a derivation whose input moved.

Noted because the irony is load-bearing rather than decorative: `block-idle-stop.sh:25`, eight lines
above the first stale site, reads *"a second copy is what drifted, and citing the source is the
whole fix."* This commit added a fourth drift to that same comment block's history.

### 6 — Low: the decision table's middle row claims more than the mechanism supports

`check-plan-progress.py`'s module docstring, the `decide()` comment, and the commit message all
carry this table:

```
fewer outstanding than at pause time  -> WARN: work resumed without `--resume` (the defect)
the same                              -> ALLOW, silent: genuinely waiting, most of a pause
no stamp (a hand-edited pause)        -> WARN, one line: cannot tell
```

Row 2's gloss is wrong, and round 1 proved it: "the same" does not mean *genuinely waiting*, it
means *the net count did not fall*, which round 1's repro shows includes work that demonstrably
resumed. The table reads as an exhaustive three-way decision, and row 3 explicitly names the
undecidable case — so a reader takes rows 1 and 2 as decidable. The honest version of row 2 is
*undecidable, treated as waiting*, and the file already knows how to say that: row 3 does it.

This is the half of round 1's Medium that **is** foldable inside this slice, because it is a
sentence, not a grammar. It costs one line in three places and removes the overclaim that the
grammar fix (backlog #100) would otherwise be the only way to retire.

## Round 1's Medium, adjudicated

**Is it real as stated? Yes.** Round 1's repro, re-run verbatim in this worktree:

```
=== ROUND 1's REPRO, VERBATIM ===
(2, 4)
(0, '', None)
```

`(0, '', None)` is ALLOW with an empty message — a silent stand-down over a plan where one step was
ticked and one added while paused. Round 1 drove it rather than arguing it, and it reproduces.

**Is the class wider than the instance? Yes, and it is wider than the one clause round 1 gave it.**
Round 1 noted in passing that *"a similar stale-stamp case with more outstanding than pause time
also goes quiet."* Rather than extend that by eye, I enumerated the whole space: for a paused plan
of 6 steps, every `(began, unticked)` pair with both in 0–4, with the plan text **built** so
`count_steps` really returns the intended pair, and the verdict taken from the delivered `decide()`:

```
total steps in every plan below = 6

began \ unticked |       0       1       2       3       4
----------------------------------------------------------
               0 |    WARN  silent  silent  silent  silent
               1 |    WARN  silent  silent  silent  silent
               2 |    WARN    WARN  silent  silent  silent
               3 |    WARN    WARN    WARN  silent  silent
               4 |    WARN    WARN    WARN    WARN  silent

       no stamp at all -> WARN
    non-numeric 'soon' -> WARN
         negative '-1' -> WARN
              empty '' -> WARN
```

(The `unticked = 0` column is WARN from the earlier all-ticked branch, not from the stamp.)

The class stated exactly: **the guard fires only on a strict decrease of a scalar, so every plan
edit that does not lower the outstanding count is invisible** — the entire triangle where
`unticked >= began > 0`. Round 1's instance is the diagonal. Three further members, each run:

* **Steps added and none ticked** (`unticked > began`) — silent, *and* untested by construction
  (finding 4).
* **The plan is repointed while paused** — the stamp came from plan A, the count is taken over plan
  B. Driven: `plan: other.md` with a stamp of 2 against a 5-outstanding plan → `ALLOW, ''`.
* **The plan shrinks while paused** — the loud branch survives but prints an impossible number
  (finding 4).

**Does it block the PR? No.** Three reasons, in order of weight:

1. The pre-change behaviour for round 1's exact input was WARN-on-every-stop, so the residual is a
   **narrowing** of an alarm that was firing on everything — and by backlog #56's measured verdict a
   gate that nags gets switched off, and a switched-off gate covers nothing. Net coverage against
   the state #99 cares about is better after this branch than before it, not worse.
2. Reaching it needs a hand-edited plan that both ticks and adds while paused. `--tick` refuses on a
   paused plan, so no supported command produces this state.
3. The repair is the sentinel's grammar — store the done count too, or fingerprint the checkbox
   lines — which is `docs/backlog.md` #100's own subject: *"`.claude/executing-plan` is a structured
   state file with no schema, no enumerated state set, and TWO de-facto owners of its grammar."*
   **I confirm that it cannot be fixed inside this slice**, and I have not designed it here.

What should not ship unchanged is the **claim** about the hole, not the hole: finding 6.

## Attacked, and found sound

* **`gh`'s exact sentence — the single most load-bearing measured claim on the branch.** Run live
  against `gh version 2.88.1 (2026-03-12)`, on two branches:
  ```
  returncode: 1   stdout: ''
  stderr: 'no pull requests found for branch "quiet-stop-observers-wt"'
  stderr: 'no pull requests found for branch "banner-work-without-banner"'
  _NO_PR in stderr -> True
  ```
  The commit message's measurement reproduces exactly, including the branch name it quotes.

* **The fix works end to end, and not for an ambient reason.** This worktree's branch has no
  upstream, so `_skip_reason` short-circuits and a naive `--decide` would be quiet for the wrong
  reason. Forcing the gh path, with the pre-fix behaviour as a control:
  ```
  1. _skip_reason() -> 'branch quiet-stop-observers-wt has no upstream — nothing was pushed'
  2. forced gh path:  run_decide() -> 0   (QUIET)
  3. CONTROL, no_pr signal removed (pre-fix): run_decide() -> 2   <- the every-stop noise
  ```

* **A stray `paused_unticked:` with no `paused:` line does not stand the guard down** (round 1's
  claim). Driven: `-> BLOCK  '⛔ DO NOT STOP — 2 of 6 steps are untic…'`. The paused branch is keyed
  on `paused`, as claimed.

* **Duplicate-key reader agreement — the brief's lead, independently verified and widened.** The
  reader population was derived mechanically, not by eye: grep for `.claude/executing-plan` across
  the repo returns 23 files, of which exactly **3** parse it (`check-plan-progress.py`,
  `check-banner-armed.py`, `begin-plan.py`); `block-idle-stop.sh` names the path in prose only and
  delegates. Run against the live doubled sentinel:
  ```
  raw copies in the file:  paused=2  paused_unticked=2
    paused           FIRST copy = 'thread B: Codex half dispatched (task byt0uqp'
    paused           LAST  copy = 'HANDING BACK — see .remember/remember.md in t'   <- parse_sentinel
    paused_unticked  FIRST = '2'   LAST = '2'
  reader 1  check-plan-progress.parse_sentinel  -> LAST-wins (dict assignment)
  reader 2  check-banner-armed._armed_from_text -> FIRST-match, returns False
                                                   (presence of `paused` only; never reads the stamp)
  reader 3  begin-plan._armed_plan              -> borrows reader 1, so LAST-wins
  strip_field: paused lines left: 0   paused_unticked left: 0
  ```
  So the two rules **do** differ — first-match vs last-wins — and they still cannot disagree here,
  because the only question reader 2 asks of `paused` is presence, and every copy is the key. Reader
  2 never reads `paused_unticked` at all, so the new field has exactly one reader. The one place the
  two rules genuinely can disagree is `plan`, and `begin-plan.py:414` already documents that and
  defends it with the multi-line-reason refusal. Round 1's claim holds; `strip_field` removing every
  copy is what keeps it holding.

* **The declared mutation arithmetic is real, not merely self-consistent.** `check-plan-code.py
  --self-test` asserts `sum(EXPECTED_MUTATIONS.values()) == 890`; that is the dict agreeing with a
  literal. Checked against the JSON on disk instead:
  ```
  declared sum: 890 over 52 entries
  on-disk  sum: 890 over 52 files
  DISAGREEMENTS (declared, on-disk): none
    scripts/check-ci-watched.py            declared=11 on-disk=11
    scripts/begin-plan.py                  declared=12 on-disk=12
    scripts/check-plan-progress.py         declared=16 on-disk=16
  ```
  The commit's `881 → 890, +9` decomposes as +2 / +3 / +4 across the three manifests. ✓

* **Verification run requested by the brief**, all at their declared counts:
  ```sh
  python3 scripts/check-ci-watched.py --self-test      # 28/28 self-test cases passed   rc=0
  python3 scripts/check-plan-progress.py --self-test   # 42/42 self-test cases passed   rc=0
  python3 scripts/begin-plan.py --self-test            # 53/53 self-test cases passed   rc=0
  python3 scripts/check-plan-code.py --self-test       # 128/128 passed                 rc=0
  ```
  Docstrings updated to match in the same commit (23→28, 35→42, 50→53), and
  `check-selftest-counts.py` verifies all 45 declaring scripts by running them.

* **Branch gates, all green:**
  ```
  check-dashboard-entry      rc=0  ok — an entry block was added
  check-review-rounds        rc=0
  check-docs                 rc=0  Documentation integrity OK
  check-selftest-counts      rc=0  45 script(s) declare a count, every one verified by running it
  check-ratchet-contract     rc=0  ratchet contract OK
  ```

* **`check-plan-code.py --mutate .` was NOT re-run.** ~35 minutes, and an instance was running in
  the other tree; round 1 recorded 890/890 killed / 0 survivors against this same HEAD's code. I
  treat that as round 1's evidence and it is not in dispute. What findings 1, 2 and 4 show is that
  the number is bounded by the manifest: four of this branch's new decision points have no entry, so
  a 0-survivor sweep is silent about them.

**VERDICT: NOT CONVERGED**

Nothing here is Blocking and nothing here is a correctness defect in the delivered behaviour —
every delivered path I drove behaved as documented. The three Mediums are all the same shape, which
is the shape this repo's ratchet contract exists to prevent: **new decision points shipped with
falsifiers for their pure rules and none for their wiring or their fail direction**, in two guards
whose entire purpose is to fail loud rather than silent. All three are fixable inside this slice
without touching the sentinel grammar.

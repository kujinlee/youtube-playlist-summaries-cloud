<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None found.

## High

- **H1 — A legitimate checkpoint pause is declared finished.** `scripts/check-plan-progress.py:413–420` maps every fully ticked plan to STALE, calls its pause reason “historical,” and instructs `--finish`. Reproduced with `paused: waiting on CI`: `decide` correctly preserves the sentinel because external work remains; session start declares the work finished. Following its instruction deletes the waiting reason and continuation pointer.

  **The channel-only claim survives narrowly as “no new input predicate.” It does not survive as “the same verdict on another channel.”** This is a coarser classification with a different remedy. Preserve the paused/unpaused distinction and make finishing conditional on confirming the external work ended.

- **H2 — Runner failures become silent success.** `.claude/hooks/report-plan-state.sh:22–23` discards stderr and unconditionally exits 0. Reproduced with an invalid UTF-8 plan: Python raises before printing a verdict; the hook returns **0, empty stdout, empty stderr**. Missing Python or a broken import has the same delivery problem. The documented exception depends on emitting failure text; this path emits none. Catch runner failures and deliver a CANNOT RUN diagnostic on stdout before exiting 0.

## Medium

- **M1 — Total rewriting corrupts examples and literal code.** `scripts/begin-plan.py:219` substitutes across the entire document. With one real checkbox, both prose containing `**Step 1 of 9** — example` and the same text inside a fenced block become `of 2` after append. `_STEP_PREFIX_RE` owns a prefix of a parsed checkbox description; `_TOTAL_RE` is unanchored and owns substantially more. Restrict rewriting to actual step prefixes outside fenced examples.

- **M2 — Auto-creation can overwrite the previous plan.** `scripts/begin-plan.py:451–453` derives the filename from the title and delegates to `cmd_begin`, which overwrites it. Reproduced on both interpreters: an unarmed `--add "repeat"` replaces an existing completed `.claude/plans/repeat.md`, losing its contents. Use a collision-safe filename or refuse the collision explicitly.

- **M3 — Valid task titles fail when unarmed.** `--add "Review src/api|inspect|needed"` raises an uncaught `ValueError` because its title is passed through filename-slug validation. The same title can be appended when armed. Auto-creation needs to generate a safe filename independently of the task title.

- **M4 — Another existing discriminator disappears.** With `paused_unticked: 2`, one ticked box and one outstanding box, `decide` reports “PAUSED, BUT 1 STEP(S) WERE TICKED SINCE.” Session start merely reports PARKED and says resume “when the work restarts,” although it already restarted. This is a third coverage hole beyond timing and unrecorded promises: **recorded evidence of progress under a pause is omitted from the assistant-facing verdict.**

## Low

- **L1 — “Session start fires ONCE” is inaccurate.** The hook has no matcher restriction. Claude Code documents SessionStart on startup, resume, clear, and automatic/manual compaction. It can therefore observe a sentinel that becomes stale during a session at a later compaction boundary. Coverage remains intermittent, but “never during it” overstates the limitation. [Official hook lifecycle](https://code.claude.com/docs/en/hooks#sessionstart).

- **L2 — Delivery tests prove less than their names claim.** `scripts/check-plan-progress.py:774` checks nonempty stdout without capturing or asserting empty stderr. The runner cases also read the live repository rather than constructed failure states, and never exercise the shell wrapper. The distinct-label case checks constants, not whether the state machine collapses classifications. These are coverage weaknesses, not additional unconditional tautologies.

## Checked and found SOUND

- **The documented delivery premise is correct:** exit-0 SessionStart plain-text stdout reaches Claude’s context; nonzero failures and their stderr reach the user instead. Keeping exit 0 for an explicitly printed CANNOT RUN verdict is defensible. H2 concerns failures that print no verdict. [Official exit-code contract](https://code.claude.com/docs/en/hooks#exit-code-output).
- **Read-only behavior reproduced on both interpreters:** fully ticked paused/unpaused plans, missing plan files, and zero-checkbox plans preserve sentinel bytes and state-file bytes.
- **Appending while paused preserves the reason and count stamp.** Recording additional work alone is not evidence of progress; keeping the pause is defensible. Auto-creating a one-step plan after an explicit declaration of future work is also defensible, subject to M2/M3.
- **Counts re-derived:**

  | Measurement | Base → commit |
  |---|---:|
  | begin-plan self-tests | 63 → 78 |
  | plan-progress self-tests | 43 → 66 |
  | plan-code self-tests | 178 |
  | begin-plan mutations | 18 → 21 |
  | plan-progress mutations | 17 → 19 |
  | Declared mutation sum | 1408 → 1413 |

  Commit self-tests passed **78/78, 66/66, 178/178 on both Python versions**.
- **Five new mutations reproduced:** five uniquely binding anchors, none duplicated in prose; **0 survivors, 5/5 killed through their named cases**, on each interpreter, with green initial controls and restored controls after every entry. FAIL detection stripped leading whitespace.
- The new behavioral cases contain adjacent stale/live/parked negatives. No additional unconditional tautology found; their green results do not invalidate the counterexamples above.

## CANNOT RUN

- The broader sweep timed out on bare `check-selftest-counts.py` and `check-main-drivable.py` at 55 seconds: **treat this as NOT RUN**, a verification failure, not a pass. Their self-tests completed successfully.
- The author’s exact “48 RAN, 0 red” measurement was therefore not independently established.
- Full mutation sweep, Jest-result count check, and PR-only gates remain **NOT RUN**, as already disclosed. No finding for that disclosure.
- `check-memory-link.py` reporting an absent corpus is **not a measurement**.

## Instruments

Read the commit message and complete diff. Used Python **3.14.4** and **3.12.9**, with stdin closed on every guard. Mutations and execution fixtures ran in a `tar` copy excluding `.venv`/`node_modules`, with `node_modules` restored by symlink.

The broader sweep attempted 53 unique single-line Python CI commands: 51 exited 0, two timed out; the absent-corpus result is excluded from evidence. Harness conclusions above use official documentation, not an end-to-end Claude session experiment. No review file was written; worktree Git status remained clean.

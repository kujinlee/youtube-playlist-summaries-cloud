<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established. **Not converged: 2 High / 2 Medium.**

## High

**H1 — Wording #6 is false. Remove the structural narration; do not write wording #7.**  
`scripts/check-plan-code.py:3059–3063`

The disclosure says any line led by OTHER whitespace “ENDS that run and is quoted here.” The loop at `:650` instead consumes every whitespace-only line:

```python
not lines[i].strip() or lines[i].startswith((" ", "\t"))
```

A real child writing:

```python
'  File "f"\n\u3000\nEND\n'
```

produces a rendered report quoting **END**, alongside the disclosure asserting that the U+3000-led line ends the run and is quoted. That whitespace-only line does neither. A blank line likewise remains inside the purported “run of SPACE-or-TAB-indented lines,” despite having no such indentation.

The other clauses have narrower support:

- SPACE/TAB identifies the nonblank run start; blanks of any whitespace are subsequently consumed.
- At least one member matches the correctly quoted `^[ \t]+File "` pattern.
- Extracted lines retain stderr order and undergo `.strip()`.
- Nonblank U+3000, form-feed, vertical-tab and `\x1c` prefixes terminate the run and disappear from quotations.
- BOM and NUL terminate the run but remain in quotations; neither is whitespace.
- Real-child `\r` and CRLF undergo subprocess newline normalization before extraction. The report narrates the normalized stream.
- Split stderr writes with intervening stdout writes preserved **ONE · TWO**; stdout did not enter extraction.

**The sentence should cease to exist in this form.** Delete its run/position narration and disclosure, retaining only the evidence quotation and necessary uncertainty statement. Six attempts have reproduced the same failure pattern. No new predicate or seventh structural explanation is warranted.

**H2 — The new falsifier still tests presence, not truth.**  
`scripts/check-plan-code.py:3923–3924`

On an isolated, complete `HARNESS_TREE`:

| Experiment | Result |
|---|---|
| Control | 297/297 |
| Replace sentence with the refuted claims | 296/297; exactly the new case fails |
| Same false replacement, retaining `SPACE-or-TAB-indented` | **297/297** |
| Restore committed source | 297/297 |

The green false replacement was:

```text
SPACE-or-TAB-indented: CPython SAID THE FOLLOWING KILLED THE CHILD,
in reverse order, each one a VALIDATED exception class
```

Thus causal attribution, reversed order and exception validation can all return while the new case passes.

The current fixture’s diagnostic tail **does not contain the phrase**, so the previous raw-stderr trap is absent for this fixture. Position **734/1547** also genuinely dies through its named case: **1 killed / 1 attributed / 0 survivors**. These establish presence coverage, not semantic coverage. Remove the unsupported narration and retire coverage whose sole subject is its presence.

## Medium

**M1 — A fifth piece of debris preserves the withdrawn column-zero claim.**  
`scripts/check-plan-code.py:567`, `:615`, `:659–664`

The docstring still opens:

> Every line `stderr` printed at COLUMN ZERO after a frame block

It later defines a heading as returning to column zero, and the implementation comment repeats that claim. A real child’s `\u3000END` is extracted as `END`, refuting this documentation by the same witness that refuted wording #5.

Delete these surviving assertions with their withdrawn subject. The function name also retains the misleading positional description.

**M2 — #270 still draws the count-to-load conclusion.**  
`docs/backlog.md:285`

The fold corrects the earlier equal-count inference, but preserves:

> The second green carried ONE MORE mutation entry … which counts against the load story rather than for it.

That remains a load inference from an entry count, immediately after explaining why counts support none. Delete that sentence. **UNDIAGNOSED remains correct**; this finding does not diagnose the cancellation.

## Low

None established.

## Checked and found SOUND

- Reviewed committed **`2c33738c`**, its commit message, both round-15 halves, and `ce8c2cbf..2c33738c`.
- Self-test: **297/297**. Binding: **1555 anchors / 1547 entries, 0 unbound**.
- All **62 manifests** agree with `EXPECTED_MUTATIONS` in both directions; total **1547**, this file **145**. The declared-sum case pins **1547**.
- Nothing retired to fund this rise: all **144 previous entries remain unchanged**, plus one new entry. Cases add one and rename the surviving atexit case.
- The four specified debris sites were corrected: orphaned constant comment, historical tuple result, surviving “verbatim,” and “by the same label.”
- Rows **#279/#280** explicitly distinguish the original accounting as historical record from the later accounting.
- Replayed **all 21 published invocations**, stdin closed: **21 green / 0 red**.
- Independently counted **46 guards on disk / 34 distinct guards referenced in `ci.yml`**.
- The commit explicitly denies CI equivalence; its invocation-set claim does not imply it.
- Worktree remains clean. No review file written.

## CANNOT RUN

**These are verification failures, not passes:**

- Full local `--mutate .`: excluded by the supplied constraint. One scoped mutation does not verify the population.
- Fresh CI replay: not performed.
- Historical 4s→6s magnitude under its original conditions: not reproduced.

## Instruments

Prepared `.venv/bin/python` **3.12.9**, venv-first mutation `PATH`; production `run_mutations` with real children and inspection of rendered reports; complete isolated `HARNESS_TREE` with green control/sever/false-replacement/restoration; scoped mutation attribution; AST case comparison; manifest comparison in both directions; named 21-command replay.

One accounting helper initially assumed a dictionary-shaped manifest and raised `TypeError`; corrected and rerun against the actual list format. No red correctness control was accepted.

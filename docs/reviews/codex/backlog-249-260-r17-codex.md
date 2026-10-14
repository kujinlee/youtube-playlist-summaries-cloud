<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established. **Not converged: 1 High / 4 Medium / 1 Low.**

## High

**H1 — The new case tests tokens, not refusals. Both the shape argument and child-unproducibility premise are refuted.**  
`scripts/check-plan-code.py:3946–3960`

Removing **only `NOT`** from:

```text
THIS HARNESS DOES NOT CLAIM ANY OF THEM IS THE EXCEPTION
```

makes the report assert exception-hood while retaining every tested substring.

| Experiment | Result |
|---|---|
| Committed control | 297/297 |
| Delete `NOT` | **297/297** |
| Restore | 297/297 |

A refusal is a speech act with scope and polarity. Its tokens can survive after its force is reversed. The assertion/refusal distinction therefore does **not** justify this substring oracle.

The child-unproducibility premise also fails **without changing the shipped `_q` child’s bytes**. Run that child beneath a directory named:

```text
ANY OF THEM IS THE EXCEPTION | NOR THAT IT KILLED THE CHILD |
NOR THAT CPYTHON WROTE ANY OF IT |
NOR ANYTHING ABOUT WHERE IN THE STREAM THEY APPEARED
```

Its traceback prints the filename containing those tokens. `diagnostic_tail` then supplies all four to the case.

Measured in the complete isolated tree:

| Experiment | Result |
|---|---|
| Committed control | 297/297 |
| Replace disclaimer with `CPython SAID THESE VALIDATED EXCEPTIONS KILLED THE CHILD`, ordinary fixture directory | 296/297; exactly the refusal case fails |
| Same false report, unchanged child bytes, token-bearing fixture directory | **297/297** |
| Restore | 297/297 |

A separately constructed child emitting the tokens directly produced the same false acceptance.

**Remedy:** withdraw the “correctness IS its presence” argument. The refusal oracle must reject token-preserving negation and diagnostic-tail substitution, and must distinguish harness-authored refusal text from child evidence. This requires no new structural narration.

All four shipped entries **734–737** nevertheless reproduced **1 killed / 1 attributed through their named refusal case / 0 survivors**, with green controls and re-controls. Those deletion mutations establish token sensitivity, not refusal correctness.

## Medium

**M1 — Structural prose remains false after the summary’s deletion.**  
`scripts/check-plan-code.py:569–571`, `:620–621`

The withdrawal note says a line led by **ANY other whitespace** is returned. The shipped function disproves that:

```python
lines_after_frame_runs('  File "f"\n\u3000\n') == []
```

The U+3000-only line is consumed, not returned.

The restored definition—“the first line that ENDS a run of indented frame lines”—also describes the consumed run too narrowly:

```python
lines_after_frame_runs(
    '  File "f"\n  PROSE\n\u3000\nEND\n'
) == ['END']
```

The run includes arbitrary indented prose and wholly strippable whitespace. It is not a run consisting of frame lines. The restored sentence fixes the grammar but preserves the earlier structural overclaim.

**Remedy:** delete these overbroad explanations; do not write another stream description.

The fold’s contract-location justification is also inaccurate: `:546–556` contains historical discussion and “nothing decides any more,” not the run contract. `:666–674` omits the frame-marker requirement and blank-consuming rule. A reader can recover the exact behavior from the implementation at `:650–676`, but neither cited prose range states it completely.

**M2 — “No function CLASSIFIES a line any more” is false.**  
`docs/backlog.md:294–295`; `docs/roadmap-to-launch.md:3084`; `scripts/check-plan-code.py:553`

**Direct answer: yes, `FRAME_LINE` performs classification.**

```python
bool(FRAME_LINE.match('  File "f"')) == True
bool(FRAME_LINE.match('  prose')) == False
```

`lines_after_frame_runs` uses that classification to decide whether a run qualifies for extraction. The live attribution path also uses `parse_fail_names` to classify output lines as named failures.

Deleting the two exception-name validators establishes their absence. It does not establish the absence of classification. The living documents assert this claim without a qualification; the commit’s description of it as “scoped and dated” does not supply one.

**Remedy:** delete the general classification claims, retaining the concrete deletion facts.

**M3 — The completed vocabulary sweep missed two living assertions.**  
`docs/backlog.md:294–295`

Both closure paragraphs still assert:

> the report claims only that the child printed those lines at column zero after a frame block — which it did

That is the retired positional claim, stated as current fact. It also misdescribes the current report, whose disclaimer refuses stream-position attribution.

The committed-tree grep covered **all three spellings**. Classification:

- Script occurrences at `:569`, `:572`, `:622`, `:672`, `:3076`, `:3942`: withdrawal/history quotations. Their separate explanatory overclaim is M1.
- Historical rename references in both backlog rows and roadmap `:3085`: legitimate history.
- Roadmap `:3087–3088`: withdrawal explanation.
- Backlog `:294` and `:295`, quoted above: **live assertions**.
- The two hyphenated remedy references in row #280 belong to its explicitly superseded proposal and subsequent critique.
- No spelling survives in `scripts/mutations/check-plan-code.json`.
- Frozen review testimony was excluded from the live-assertion population.

**Remedy:** delete the two surviving positional assertions. No replacement narration is needed.

**M4 — “Read no line it could quote” upgrades selection failure into inability.**  
`scripts/check-plan-code.py:3096`

A real mutated child with:

```python
sys.tracebacklimit = 0
raise RuntimeError("QUOTABLE")
```

produces this same report:

```text
this harness read no line it could quote ...
    RuntimeError: QUOTABLE
```

The else-arm is reachable while a readable, quotable line exists—and the diagnostic window actually quotes it. What was measured is an empty extractor result. The unqualified inability claim goes further.

**Remedy:** delete “this harness read no line it could quote, so”; retain the instruction to read the window and the existing bound. This is a deletion, not a seventh structural wording.

## Low

**L1 — The newly dated “18 at this commit” pin is wrong.**  
`docs/backlog.md:285`; commit `5fb42985`

Re-derived using sorted manifests and `muts[index-1::total]`:

| Revision | Total entries | Shard 7/8: `check-plan-code` | Shard 8/8: `check-plan-code` |
|---|---:|---:|---:|
| `2c33738c` | 1547 | **19** | 18 |
| `5fb42985` | 1550 | **19** | 19 |

The historical **19** reproduces. **18 at HEAD does not.** Adding the four refusal entries changed the partition again.

Correct or delete the HEAD pin. This arithmetic establishes no load conclusion.

## Checked and found SOUND

- Reviewed committed **`5fb42985`**, the fold and testimony commits, both round-15 and round-16 reviews, and the branch changes relevant to these claims.
- The new docstring **summary** is sound: it delegates selection to the implementation, preserves decoded-stream order, and remains pure. Universal-newline translation does not reverse that order.
- Real-child carriage-return witness:

  ```text
  bytes:   b'  File "f"\rONE\r  File "g"\rTWO\n'
  decoded: '  File "f"\nONE\n  File "g"\nTWO\n'
  quoted:  ['ONE', 'TWO']
  report:  ONE · TWO
  ```

  One LF-delimited child-written line becomes two quoted elements. The normalization note’s demonstrated claim and the narrowed order clause survive.
- Requested extraction boundaries reproduced: no-frame runs, blank-only runs and EOF after frames return `[]`; a frame run at the start returns its terminating nonblank line; nested indentation does not create separate runs; separated qualifying runs preserve order; entirely strippable whitespace is consumed.
- Counts reproduce: **296 → 297 cases**, **144 → 148 entries** for this file, **1546 → 1550 total entries**.
- All **62 manifests** match all **62 `EXPECTED_MUTATIONS` keys** in both directions, with zero per-file mismatches.
- Binding reproduces: **1558 anchors / 1550 entries**, every anchor resolving exactly once, **0 unbound**.
- No duplicate mutation names or complete anchor tuples exist **within a manifest**, which is the actual refusal scope. Cross-manifest repeated names and individual anchors shared by different tuples are not that predicate.
- Four entries were added; two existing entries were renamed/retargeted. No case was retired to fund the increase.
- Six scoped invocations—**720, 721, 734, 735, 736, 737**, each over denominator **1550**—all reproduced their named attribution, with green control and re-control.
- Historical sever at **`e3a61e93`** reproduced in its complete tree: **296/296 control → 296/296 false replacement → 296/296 restoration**.
- The explicitly named guard set below returned **53 exit-code zeros**, and both explicit base checks returned zero. The memory-link exception is **NOT RUN**, as recorded below.
- Independently reproduced **46 guards on disk / 34 distinct guards referenced in `ci.yml`**.

## CANNOT RUN

**These are verification failures; treat each as NOT RUN, never as a pass.**

- Full local `--mutate .` and the eight-shard population matrix. Six single-entry runs do not verify the population.
- `check-test-counts.py` against a real `jest-results.json`.
- PR-event forms of the PR-only guards and a fresh CI replay.
- Default `check-memory-link.py`: its corpus is absent despite exit code 0. Its self-test ran; its live subject did not.
- Original timing/cancellation conditions and the historical “297/297 phrase retained” experiment were not independently replayed here.

The known review-recorded debt and possible missing round-17 Claude half are not filed as defects.

## Instruments

Venv-first `PATH`, **Python 3.12.9**, stdin closed for every guard; complete isolated committed-tree archives; production `run_mutations` and real children; rendered-report inspection; green control/sever/restoration sequences; filename-token and direct-stderr attacks; AST/JSON accounting; committed-tree grep of all three spellings.

**The 53-command invocation SET:** every name below means `python3 scripts/<name>.py`, with the indicated arguments.

```text
Default (25):
check-python-pin, check-docs, check-backlog-closure,
check-arch-findings, check-gate-falsifiability,
check-roadmap-consistency, check-review-rounds, check-anchors,
check-memory-link, check-rc-contract, check-surface-recall,
check-features, check-ratchet-contract, check-explainer-delivery,
check-plan-task-order, check-plan-file-tags,
check-theme-token-coverage, check-selftest-counts,
check-fixture-variation, check-main-drivable,
check-storage-independence, check-group-claims,
check-producer-enumeration, check-storage-grant-pin,
check-function-revokes

--self-test (25):
check-python-pin, check-test-counts, check-backlog-closure,
check-review-recorded, check-withdrawal, check-provenance,
check-review-rounds, check-anchors, check-memory-link,
check-rc-contract, check-surface-recall, check-features,
check-plan-file-tags, check-guard-coverage,
check-vocabulary-collisions, check-banner-armed,
check-theme-token-coverage, check-selftest-counts,
check-fixture-variation, check-main-drivable,
check-storage-independence, check-group-claims,
check-function-revokes, check-dashboard-entry, check-plan-code

Additional three:
check-provenance
check-withdrawal
check-plan-code --binding

Plus:
check-provenance --base origin/master
check-withdrawal --base origin/master
```

An initial in-memory module clone lacked `__file__` and raised; it supplied no finding. The corrected instrument reproduced the child-token attack.

**Worktree clean; HEAD unchanged. No review file written, commit made, push performed or merge attempted.**

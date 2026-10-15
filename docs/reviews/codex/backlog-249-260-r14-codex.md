<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — “Nothing decides what a line MEANS” is false: child-controlled text is still attributed to CPython.**

At `scripts/check-plan-code.py:618–638,3008–3013`, the surviving `intro.startswith(IGNORED_AT_SHUTDOWN)` decides that a block was labelled by CPython. A real child:

```python
raise RuntimeError(
    'real\nException ignored in FORGED\n'
    '  File "fake", line 1\nPLAIN_TEXT'
)
```

produces:

```python
[("RuntimeError: real", False), ("PLAIN_TEXT", True)]
```

Through real `run_mutations`, the report says:

```text
PLAIN_TEXT [after a block CPython labelled 'Exception ignored in']
```

CPython did not label that block. The exception’s message supplied both the label and the frame-shaped text. The frame regex also establishes only **frame-shaped text**, not an authentic traceback frame block.

The redesign removed exception-name classification, but retained a semantic attribution and publishes it as provenance. **Round 14 refutes the removal claim again.** Remove that attribution, or describe the observed child-written prefix literally. Do not introduce another validator.

## Medium

**M1 — The replacement “VERBATIM” positional claim is false.**

At `scripts/check-plan-code.py:610–638`, `.strip()` both filters and changes the quoted lines.

Measured with real children:

| Child output after a frame-shaped line | Reported quotation |
|---|---|
| `RuntimeError: X  \n` | `RuntimeError: X` |
| `\fFF_MARKER\n` | `FF_MARKER` |
| `\u3000\nAFTER\n` | `AFTER`; the column-zero whitespace line disappears |

The first example is an ordinary `raise RuntimeError("X  ")`, reproduced through real `run_mutations`. The report’s **VERBATIM** assertion is therefore false without any exotic exception class.

The third example also disproves an unrestricted “every column-zero line” claim: whitespace-only lines are consumed as part of the preceding run.

State the actual selection and normalization, or remove those claims. Adding another character predicate would continue the narrowing sequence.

**M2 — #281’s “MECHANISM graded as BRANCH-COVERAGE five times” diagnosis contradicts its cited record.**

`docs/backlog.md:296` and the new roadmap section attribute the delay to applying the test per finding.

But `docs/reviews/coordinator/backlog-249-260-r11-thrashing.md` explicitly grades **r11 Claude H1 as MECHANISM**, answers the redesign test **YES**, and prescribes:

> Stop attributing: name every heading, claim none.

Thus at least one finding in the stated sequence was correctly classified even under the per-finding application. The record supports a failure to carry the broader redesign into the owner’s decision; it does not support five consecutive misclassifications or establish that per-finding application caused them.

The **round-11 opportunity** is supported. Correct the diagnosis and enumeration rather than treating them as measured facts.

## Low

**L1 — Both closure rows publish the wrong final case count.**

`docs/backlog.md:294–295` says **291 → 295**. The committed suite runs **298/298**, agreeing with the commit message and roadmap. Update both rows.

**L2 — The redesign’s code comment retains the explicitly rejected historical bound.**

`scripts/check-plan-code.py:537` says **“Five consecutive review rounds (9–13)”**. The enumerated examples cover rounds **11–13**, and #281 explicitly says rounds 9–10 concern a different component. Distinguish five examples from three rounds and retain the witnessed bound.

## Checked and found SOUND

- Independently reproduced **298/298 cases**, **146 manifest entries for this file**, **1548 loaded entries**, declared sum **1548**, and binding **1556 anchors / 1548 entries**.
- Structural manifest comparison by subject found **two retired validator mutations, four retargeted mutations, and one added predicate-reintroduction mutation**. The net **147 → 146** fall is retirement with the deleted subject. Four classifier cases were likewise retired; renamed and inverted cases were distinguished from retirements.
- All five current touched entries passed scoped mutation runs:

  | In-file index | Zero-based population position | Killed | Attributed | Survivors |
  |---:|---:|---:|---:|---:|
  | 131 | 721 | 1 | 1 | 0 |
  | 135 | 725 | 1 | 1 | 0 |
  | 141 | 731 | 1 | 1 | 0 |
  | 142 | 732 | 1 | 1 | 0 |
  | 145 | 735 | 1 | 1 | 0 |

- Separate staged runs confirmed the first four mutations each fail **only their named expectation**. Predicate reintroduction fails its named `bad-name` case plus the tally, marker, and non-identifier-module cases. **No second unobservable-expect or ambient-attribution instance established among these five.**
- The inverted tally case asserts the exact result `[("0/0 passed", False)]`. Predicate reintroduction makes it fail.
- The `bad-name` case directly observes extraction and fails when classification returns. The separate report case asserts **` · `**; removing that separator fails exactly that case. Raw diagnostic-tail markers cannot satisfy this assertion.
- A **fifth producer** was reproduced through real `run_mutations`: a running case executes an assertion, then calls `sys.exit(1)` before reporting. It yields `caught=True`, `fails=[]`, `attributed=False`, `measured=True`. **This is not a completeness finding**, because the message expressly disclaims completeness.
- Ordinary `SystemExit("ORDINARY_EXIT")` is omitted from extracted lines, as are zero-frame `RuntimeError` and `ExceptionGroup`. These fit the stated no-frame/no-column-zero bounds; their omission alone is not a new finding. Chained exceptions, bare `KeyboardInterrupt`, and a thread’s `ValueError` were extracted.
- Position probes covered tabs, form feed, CR/CRLF, NUL, BOM, split writes, interleaved streams, and one-/eight-space frame-shaped lines. CR is normalized by subprocess text decoding; raw-string probes were not mistaken for production-path measurements.
- Re-derived shard assignment from sorted manifest loading and `muts[index - 1::total]`: this file’s eight shard counts are **18,18,18,18,18,18,19,19**. Shards 7 and 8 do carry the same **count**, 19.
- GitHub job metadata independently confirms shards 1–7 succeeded and shard 8 was cancelled, **23:14:57 → 23:45:16 = 30m19s**. This is cancellation, not a survivor. [Recorded run](https://github.com/kujinlee/youtube-playlist-summaries-cloud/actions/runs/38483050947)

## CANNOT RUN

**Treat these as NOT RUN, not passes.**

- Full local `--mutate .` sweep: excluded by the supplied timeout constraint. Five scoped entries do not establish population-wide coverage.
- Independent CI replay: NOT RUN. Existing job metadata was inspected; no workflow was rerun.
- Historical **4s → 6s** timing comparison: not independently reproduced under the original measurement conditions. **+50%** and approximately **38s for 19 entries** follow arithmetically from those supplied timings, but do not validate them.

## Instruments

Prepared `.venv/bin/python` **3.12.9**, venv-first mutation `PATH`; commit message read first; both round-13 reviews; redesign and wider diffs; structural JSON and AST inspection; real subprocesses; production `run_mutations` probes; five population-stride mutation runs; staged failing-case inspection; shard arithmetic; GitHub job metadata.

Reviewed committed HEAD **`c5660227`**. Worktree remained clean. **No review file written.**

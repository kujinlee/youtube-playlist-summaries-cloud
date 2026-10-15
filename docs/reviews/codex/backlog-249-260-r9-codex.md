<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — Walk-back loses the list container when the span opens after the item’s first line.** `scripts/check-withdrawal.py:598–603` stops before the list-marker line, then derives `cont=0` from its continuation:

```markdown
  - first
    second the count was `wrong:
    # h
    holds 1,414 anchors today`
```

Both GFM parsers render a heading boundary and no inline code span. The mask whitens that boundary; `history_marker()` returns `'was '`, silently exempting the live figure.

Interleaved containers also fail through this path:

```markdown
> - > - - first
>   >     the count was `wrong:
>   >     # h
>   >     holds 1,414 anchors today`
```

Both parsers confirm the boundary; the guard again returns `'was '`. Claim 4 is refuted. Recover the enclosing list state independently of where this paragraph starts, and pin both witnesses.

**H2 — `list_content_column()` counts characters rather than tab-expanded columns.** At `scripts/check-withdrawal.py:519`, `m.end() - i` undercounts tabbed markers. This witness uses a literal tab after the first dash and eight spaces before subsequent content:

```text
"-\t- the count was `wrong:\n        # h\n        holds 1,414 anchors today`"
```

Both GFM parsers render the heading boundary. The mask absorbs it and returns history marker `'was '`. Claim 1 is refuted independently of H1. Calculate indentation using Markdown tab stops and add a regression case.

## Medium

**M1 — A lenient regression in the new ordered-marker rule survives 157/157.** Changing only `LIST_MARKER` from `\d{1,9}[.)]` to `\d{1,1}[.)]` leaves the suite green. On:

```markdown
999) the count was `wrong:
     # h
     holds 1,414 anchors today`
```

Both parsers confirm a boundary. Baseline preserves it; the mutant whitens it. Add coverage and an attributed mutation for wider ordered markers.

**M2 — The measurement explanation falsely says the index defect cannot produce false CLEAN results.** `scripts/check-withdrawal.py:380–381` and backlog #267 repeat this assertion. I found **14 r7 shapes** whose genuine lenient result becomes **OK** at the old index. One is:

```text
"> intro\nlazy `a\n~~~\nb` x"
```

All three oracle answers indicate a boundary. The r7 mask preserves the document’s first newline but whitens the span’s newline. The corrected counts reproduce; this explanation does not.

**M3 — “Both dialects agreeing over 1,620 shapes” omits exclusions.** The generator excludes **four parser disagreements**, leaving **1,616 adjudicated grid shapes**. Corrected GFM-only evaluation retains those four disagreements. Disclose that denominator and exclusion policy beside the table.

## Low

**L1 — Backlog #269’s measured denominator is inaccurate.** HEAD’s `verify` job contains **69 step entries, 66 with `run`**, rather than 64 steps. State the counting convention and recompute the coverage comparison.

## Checked and found SOUND

- Python 3.12 suites passed: withdrawal **157/157**, plan-code **237/237**, features, docs, and review-rounds.
- Binding passed: **1,556 anchors across 1,548 entries**.
- Scoped attribution passed: **49 entries, zero problems**, including all five additions and the retargeted anchor. Each exact named expectation occurred once.
- Reconstructing the intended historical variants reproduced **228 lenient / 88 noisy** for r7, **0 / 34** after both fence clauses, and **0 / 34**, with **0 list disagreements**, after the list fix.
- Independently checked all **34 residual shapes**: all noisy.
- Backlog #267’s area correction, #268’s R1–R3/R4W distinction, and all three rows’ observational `FAILS IF` clauses checked sound.

## CANNOT RUN

The supplied **unmodified measurement replay failed** with `NameError: scan`: it reads current HEAD, removes the walk-back, and leaves the new `scan` reference behind. **Treat that replay as NOT RUN, not passed.**

The supplied oracle also still uses literal `<pre>` stripping. A Ruby-info fence yields `(False, True, True)` there; corrected stripping yields `(True, True)`. Historical reconstruction and corrected-oracle checks completed separately.

## Instruments

Python **3.12.9** throughout; `cmarkgfm` and `MarkdownIt("gfm-like").disable("linkify")`; corrected `<pre\b[^>]*>` stripping; supplied attribution harness; temporary `/tmp` probes and in-memory mutation.

No repository edits or review file. High findings remain; convergence remains **0 of 2**.

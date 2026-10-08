<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — The new paragraph rule can re-pair a genuine span’s closer and hide live prose.**

File: `scripts/check-withdrawal.py`, `PARA_END` and `mask_inline_code`:

```python
r"|\n {0,3}(?:[-*+][ \t]|1[.)][ \t]|#{1,6}[ \t]|>)"
```

```python
if PARA_END.search(text[e:cs]):
    i += 1
    continue
```

The rule mistakes both a continuation of an existing block quote and an empty list marker for paragraph interruption. Rejecting the genuine span leaves its closer available as another opener.

Two concrete inputs, written here as Python string literals:

```python
"> intro `a\n> b` the count was wrong:\nholds 1,414 anchors today`"
"intro `a\n* \nb` the count was wrong:\nholds 1,414 anchors today`"
```

Both cmarkgfm and markdown-it-py parse the first backtick pair as inline code. The subsequent `holds 1,414 anchors today` is prose. HEAD instead pairs the genuine closer with the final unmatched backtick, masking the colon/newline boundary and extending `'was '` into the figure’s sentence.

**Executed:** Python 3.12 loaded both `aee7dd8e` and HEAD implementations and drove their real `main(["--strict", "--base", base], root=...)` over temporary Git repositories. In each repository, `docs/src.md` corrected `holds 1,414 anchors today` to `holds 1,416 anchors today`; `docs/copy.md` retained one witness above.

For **both witnesses**:

- Parent: **rc=1**, reports the stale figure as a survivor.
- HEAD: **rc=0**, reports no survivor and `suppressed as history: 1 hit(s) — 'was 'x1`.

This is a regression introduced within the reviewed fold. The hypothesis that remaining defects are exclusively older is refuted.

## Medium

None separately established. Without the later unmatched backtick, the same empty-item error produces a false survivor instead; this is another consequence of H1.

## Low

**L1 — The new parser-derivation comment falsely clears `---`.**

File: `scripts/check-withdrawal.py`, comment above `PARA_END`:

> “both parsers keep the code span across all of those”

The listed exclusions include `---`. For:

```python
"the count was `wrong:\n---\nholds 1,414 anchors today`"
```

both parsers produce a setext heading followed by a separate paragraph, with **no inline code span**. HEAD masks the intervening whitespace and returns history marker `'was '`.

**Executed:** Python 3.12 parser rendering, `mask_inline_code`, and `history_marker`. The broader differential comparison also checked the parent implementation: this runtime defect is inherited, so this finding concerns the fold’s new, incorrect clearance claim—not a new production regression.

## Checked and found SOUND

All executions used **Python 3.12**.

- Clean tracked worktree at `54625c75`; diff reproduced **6 files, 297 insertions, 68 deletions**.
- All five `--self-test` runs returned rc=0: find-claim **86/86**, withdrawal **121/121**, provenance **155/155**, plan-code **237/237**, frontier-model **51/51**.
- AST extraction and JSON enumeration reproduced **1,531 mutations across 62 manifests**, with every per-file count matching.
- `check-plan-code.py --binding`: rc=0, **1,539 anchors / 1,531 entries**.
- Temporary-copy attribution through the repository’s `run_mutations` and child environment reproduced **99 entries, 99 caught, 99 attributed, 0 problems** across the four requested files. Controls passed before and after; every replacement parsed and changed its source.
- All **1,531** replacement texts parsed successfully. This clears syntax failures, not runtime attribution.
- The value-key memo probe returned `(True, True, True)`; restoring the old id key in an isolated namespace returned `(False, False, True)`. On a 1.2-million-character document, cold masking took approximately **35.5 ms** and 10,000 warm lookups **1.7 ms**.
- Both parsers confirmed the flipped `1)` expectation, the contrasting `2)` case, and escaped-opener truncation.
- Provenance checks ran Git on **matched spans**: `HEAD~?` and `HEAD~!` matched `HEAD~`; both resolved successfully.
- `_drive_span_window` previously had only `trailing_span=True` callers; removal retained both verdict controls.
- A **162-input** marker/indent differential had zero disagreements between the two parser oracles. HEAD disagreed on **56** inputs; **16 disagreements were newly introduced**, while the fold fixed **32** parent disagreements.
- `gh run list` and `gh run view` confirmed all eight mutation shards plus completion passed at `e70aa551`. The separate verify job failed at “Review rounds have both halves.” [CI run](https://github.com/kujinlee/youtube-playlist-summaries-cloud/actions/runs/37788537409)

## CANNOT RUN

**Full-repository runtime attribution remains unverified — failed run, not a pass.** I attempted eight native shards in temporary trees, but my wrapper incorrectly accessed `.mutations` on `NotMeasured`. I terminated that attempt and its active children; no full tally is claimed. A subsequent standalone `check-main-drivable` control passed **438/438** in **53.6 seconds**.

`scratchpad/r6/attrib.py` is absent, so that exact command could not run. The independent four-file execution above reproduced its stated 99-entry result.

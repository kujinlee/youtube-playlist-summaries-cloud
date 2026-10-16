<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None.

## High

### H1 — Git transformations still separate the diff from the document

**The fourth route is reproduced.** `--no-ext-diff` does not disable textconv or working-tree encoding.

Command: `python3 /tmp/r4seams.py`

Observed:

```text
CASE plain
rc 1 ⛔ 1 drifted citation(s) added:

CASE textconv DIFF ''
rc 0 doc citations OK — every `path:line` added under docs/ resolves to a real line

CASE encoding
rc 0 doc citations OK — every `path:line` added under docs/ resolves to a real line
```

All fixtures append `see lib/a.ts:2 here`, where line 2 is blank.

- **Textconv:** `.gitattributes` contains `docs/** diff=mask`; `diff.mask.textconv` is `sed '/lib\/a.ts/d'`. Git sees identical converted documents and emits no hunks. The reader sees the actual document. The guard passes.
- **Encoding:** `.gitattributes` contains `docs/** working-tree-encoding=UTF-16`; the document is written with Python’s UTF-16 encoding. Git emits `@@ -1,0 +2 @@` and the citation as UTF-8 text. `_reader` decodes the UTF-16 bytes as UTF-8 with replacement, leaving interleaved NULs that prevent citation matching. The guard passes.

The plain UTF-8 control returns rc=1. These are additional routes, not repetitions of Claude’s binary or symlink findings. The source comment claiming textconv cannot break this design is false.

### H2 — The line-rule fold leaves lone carriage returns broken

This is an **incomplete fold of H1**, not a new filing of its original `splitlines()` finding. Changing the split operation does not prevent `read_text()` from translating lone `\r` into `\n` first.

Command: `python3 /tmp/r4seams.py`

Fixture bytes:

```python
b'intro\rmore\nsee `lib/a.ts:2` here\n'
```

Observed:

```text
CASE cr
rc 0 doc citations OK — every `path:line` added under docs/ resolves to a real line
```

Git numbers two document lines; `_reader` produces three nonempty lines. The added range examines `intro` and `more`, missing the drifted citation. The plain control returns rc=1.

The form-feed witness passes while this explicitly claimed part of the fix remains broken.

## Medium

### M1 — The new “hunkless” refusal rejects ordinary deletion-only patches

Command: `python3 /tmp/r4refusals.py`

Change:

```text
keep
remove
```

becomes:

```text
keep
```

Observed diff and result:

```text
@@ -2 +1,0 @@ keep
-remove

deletion rc 2 CANNOT RUN — a diff with no hunk headers and 1 line(s) this rule does not understand: '-remove'
```

There **is** a hunk header. `out` is empty because the hunk adds zero lines. `if not out and unexplained` incorrectly equates “no additions” with “no headers.”

This also exposes the next ambient coverage gap: both deletion tests supply a bare header without the removed content that triggers the refusal. The intended adjacent fixture is a real deletion patch.

The historical replay reaches this defect too:

Command: `python3 /tmp/r4measure.py`

```text
history 40 10 0.25 errors ["a diff with no hunk headers and 672 line(s) this rule does not understand: '-'"]
```

Diagnostic control, changing only the refusal to distinguish actual absence of headers:

Command: `python3 /tmp/r4measure-control.py`

```text
history 40 10 0.25 errors []
```

The ten-firing figure reproduces; a clean historical run does not reproduce with the shipped refusal.

### M2 — The document-symlink refusal also rejects legitimate cited code symlinks

Command: `python3 /tmp/r4refusals.py`

Fixture:

```text
lib/link.ts -> a.ts
docs/x.md: see `lib/link.ts:1`
```

`lib/a.ts:1` contains `one`. The document is regular.

Observed:

```text
symlink-target rc 2 CANNOT RUN — lib/link.ts is a symlink; git diffs the link text and this would read its target, so the two would not describe the same document
```

Git is numbering `docs/x.md`, not `lib/link.ts`. Following the cited code symlink introduces no disagreement between document hunk numbers and document lines. The shared `_reader` applies the new refusal beyond the condition it was introduced to defend.

### M3 — Forced Git color makes legitimate patches CANNOT RUN

Command: `python3 /tmp/r4refusals.py`

Configuration:

```sh
git config color.ui always
```

Observed:

```text
color rc 2 CANNOT RUN — a diff with no hunk headers and 6 line(s) this rule does not understand: '\x1b[1mdiff --git a/docs/x.md b/docs/x.md\x1b[m'
```

The same ordinary citation patch returns rc=1 without forced color. The new allow-list refuses Git’s decorated output because the invocation does not enforce `--no-color`.

## Low

No additional finding filed.

## What I could not break

- Required checks:
  
  | Command | Observed |
  |---|---|
  | `python3 scripts/check-doc-citations.py --self-test` | `74/74 passed`, rc=0 |
  | `python3 scripts/check-doc-citations.py` | `doc citations OK …`, rc=0 |
  | `python3 scripts/check-fixture-variation.py` | `fixture variation OK …`, rc=0 |
  | `python3 scripts/check-review-decision.py` | `ARCHITECTURE_REVIEW — thrashing: 'diff-extraction' carried fix-induced findings in r2 and r3`, rc=1 |

- **Manifest:** applied all 33 edits independently and ran each full suite. Every mutant returned rc=1. A second targeted execution verified that every mutation reddens every case listed in its `expect`; none kills only a neighbour. All 33 anchors bind once; names and anchors are unique. All 74 case names are unique.
- **Split clauses:** both rename-path mutations and both upper-bound mutations die through their named cases. I found no behavioral regression from the splits.
- **Declared counts:** importing `check-plan-code.py` gives citation mutations **33**, total **1452**.
- **Six exemption recipes:** `python3 /tmp/r4rows.py` reproduces **2, 2, 7, 7, 6, 6** failures for `argv`, `root`, `fetch_changed`, `fetch_tracked`, `make_reader`, and `fetch_file_diff`, respectively. Their named cases fail.
- **Witnesses:** measured results are `(1, 1)`, `("CANNOT RUN", "CANNOT RUN", 1)`, `("CANNOT RUN", 1)`, `(1, 1, 1, 0)`, and `(0, 1)`. Those controls distinguish a guard returning no findings. Contrary to the brief, `_ext_diff_witness` returns scalar **1**, not a tuple; its manifest mutation nevertheless fails its named case.
- **Numbers, imported grammar:** **26,395/27,290 = 96.7%**, **111/895 = 12.4%**, **369/895** ranges, fenced **41/879** balanced and **56/895** overall. Review counts moved by 20; the other figures reproduce exactly.
- CRLF, `core.autocrlf=true`, UTF-8 BOM, no final newline, and hard links still detect the bad citation. Pure rename, mode-only change, and empty-file addition pass.
- `assume-unchanged` and `skip-worktree` conceal unstaged edits from Git and produce rc=0; I did not file that as a fold-induced defect. Sparse checkout, submodules, and case-collision constructions remain unverified.

No review file or tracked source file was written.

VERDICT: NOT CONVERGED

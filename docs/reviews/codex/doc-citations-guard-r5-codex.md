<!-- codex-review: model=gpt-6-astra -->

Reviewed `9e5a5ddc`, including both Claude fold commits. No tracked files were modified.

## Blocking

None.

## High

### H1 — Carriage returns in document filenames still produce a fail-open

`changed_files()` requests NUL-delimited output but reads it with `text=True`. Python translates carriage returns **inside filenames** into newlines. The subsequent blob lookup uses the wrong path, returns `None`, and the guard treats the staged document as deleted.

Command:

```sh
python3 /tmp/r5-paths.py
```

Observed, with every document newly citing nonexistent `lib/missing.ts:2`:

```text
'plain.md' changed (('docs/plain.md', None),) result (1, '⛔ 1 drifted citation(s) added:')
'a\rb.md' changed (('docs/a\nb.md', None),) result (0, 'doc citations OK — every `path:line` newly cited in a STAGED docs/ change resolves to a real line')
'a\r\nb.md' changed (('docs/a\nb.md', None),) result (0, 'doc citations OK — every `path:line` newly cited in a STAGED docs/ change resolves to a real line')
'a\nb.md' changed (('docs/a\nb.md', None),) result (1, '⛔ 1 drifted citation(s) added:')
```

This is distinct from round 4’s carriage returns **in document content**. The comparison uses one content oracle, but path decoding changes which object it asks that oracle for.

Read the pathname stream as bytes and decode without newline translation. The witness needs both CR and CRLF filenames, beside the newline-only control.

### H2 — Another live retirement remains: rejecting legitimate cited symlinks survives 75/75

The Claude review treated the retired `r4-codex M2` entry as covered by the directory-reader mutation. Those properties differ: accepting an ordinary cited symlink is not tested by refusing a directory.

I reapplied the original retired edit, inserting this before `is_file()`:

```python
if target.is_symlink():
    raise RuntimeError(f"{path} is a symlink")
```

Command:

```sh
python3 /tmp/r5-retired.py
```

Observed:

```text
retired cited-symlink mutation 0 75/75 passed

shipped linked citation (0, 'doc citations OK — every `path:line` newly cited in a STAGED docs/ change resolves to a real line')
mutant linked citation 2 CANNOT RUN — lib/link.ts is a symlink
```

The fixture cites `lib/link.ts:1`, where `lib/link.ts -> a.ts` and line 1 contains `one`.

**The shipped behavior is correct. The coverage loss is real.** This is another surviving retirement of a property that previously prevented a shipped false refusal. Restore the mutation and a real, valid in-root symlink citation witness.

## Medium

### M1 — Deleting a legacy binary-encoded document is still CANNOT RUN

`findings_for()` reads the pre-image before determining whether the post-image exists. Consequently, deleting a UTF-16LE Markdown file encounters the pre-image’s NUL refusal before reaching the deleted-document clause.

Command:

```sh
python3 /tmp/r5-refusals.py
```

Observed:

```text
utf16 False delete (0, 'doc citations OK — every `path:line` newly cited in a STAGED docs/ change resolves to a real line')
utf16 True delete (2, 'CANNOT RUN — HEAD:docs/x.md holds NUL bytes once decoded as UTF-8 — git does not treat this as text, so its citations cannot be read reliably')
```

The change is an ordinary staged deletion; another tracked file remains. No document survives to gain citations.

This is a rebuild defect left uncovered by the fold’s new deletion witness, which supplies only a readable text pre-image. Read the post-image first and return immediately when it is absent.

### M2 — Two new witness controls do not establish what their comments claim

Command:

```sh
python3 /tmp/r5-controls.py
```

Observed:

```text
containment shipped (None, 1)
containment refuses everything (None, 1)
rename shipped (0, 0)
rename no-op guard (0, 0)
```

For containment, I replaced `_reader` with a reader returning `None` for **every** path. The witness still passes: its in-root blank-line citation produces one finding whether the reader successfully reads the blank line or refuses the file entirely. The comment explicitly claims that “refuses everything” cannot satisfy this control; it can.

For rename configuration, replacing `findings_for` with a function returning `[]` leaves both elements correct. Both fixtures are pure renames, so neither establishes that the configured pipeline still examines newly gained citations.

These are witness-specific failures, not claims that the entire suite tolerates either replacement. Use a valid in-root citation for the containment control, and an additional bad citation in the rename control.

## Low

No additional finding filed.

## Verification and retirement audit

All required checks passed:

| Command | Observed |
|---|---|
| `python3 scripts/check-doc-citations.py --self-test` | `75/75 passed`, rc=0 |
| `python3 scripts/check-doc-citations.py` | `doc citations OK …`, rc=0 |
| `python3 scripts/check-fixture-variation.py` | 855 parameters across 67 files, rc=0 |
| `python3 scripts/check-selftest-counts.py` | 53 declaring scripts verified, rc=0 |

**Manifest:** `python3 /tmp/r5-mutations.py` independently applied all 34 entries. Every anchor bound once; all 34 mutations returned rc=1 through every named `expect`. Names and anchors were unique; all 75 case names were unique. A separate corrected module import confirmed **34** declared mutations and sum **1453**. The audit script’s initial count-import attempt failed because it omitted registration in `sys.modules`; that did not affect the completed mutation runs.

I audited the 24 name-based retirements identified by Claude:

| Retired subjects | Assessment |
|---|---|
| Five hunk parsing/arithmetic entries | Consumers removed |
| Four per-file diff flags | Consumers removed |
| Three hunkless/no-content refusal entries | Consumers removed |
| Document/diff line-count agreement | Boundary removed |
| Document symlink refusal | Replaced by the explicitly documented link-text policy |
| Empty-added-set shortcut | Removing it is now behaviorally equivalent |
| Cited-file split, decode, NUL; `ValueError` handling | Restored |
| Both cited-file upper bounds | Covered by replacement entries |
| Rename-source scope | Covered by replacement entry |
| Unreadable document | Responsibility moved to blob reading; the unwitnessed `cat-file -p` branch is already Claude M4, not re-filed |
| Acceptance of cited code symlinks | **Still live and unmeasured — H2** |

## Figures independently reproduced

Command:

```sh
python3 /tmp/r5-figures.py
```

The replay used a temporary `GIT_INDEX_FILE`, loaded each commit with `read-tree`, and called the imported guard with its parent as base and the actual index as post-image.

```text
HISTORY 40 9 3 0.23 OLD 10 4 0.25
```

| Commit | New rule | Old rule |
|---|---:|---:|
| `5128b99b` | 7 | 7 |
| `2e55c89d` | 1 | 1 |
| `b2e10e39` | 0 | 1 |
| `71a32378` | 1 | 1 |

The nine findings comprise seven blank lines, the 70-line `development-velocity.md` tombstone cited at line 262, and unresolved `dist/index.mjs:145`. The removed firing is the repeated `check-ci-watched.py:183` citation at `b2e10e39`; its introduction still fires at `71a32378`.

Imported-grammar corpus measurements:

- Reviews: **26,422/27,317 = 96.7%**; absolute counts moved as documented.
- Living corpus: **111/895 = 12.4%**.
- Ranges: **369/895**.
- Fenced citations: **56/895** overall; **41/879** in fence-balanced documents.

The figure supporting the scope decision holds.

## What I could not break

- The phantom-element fix correctly handles empty files, one-line files without a newline, newline-only files, and whitespace-only final lines.
- Containment correctly handles in-root symlinks and a symlinked repository root, including macOS temporary-directory resolution.
- Ordinary and bracket-named conflicted documents return rc=2; resolving and staging the bad citation returns rc=1.
- A symlinked document contributes exactly its link text, as documented.
- The declared mutation counts, attribution, and historical firing figures hold.

I did not exhaust rebase/cherry-pick states, submodule conflicts, shallow clones, or stash transitions. I found no new multiset defect.

VERDICT: NOT CONVERGED

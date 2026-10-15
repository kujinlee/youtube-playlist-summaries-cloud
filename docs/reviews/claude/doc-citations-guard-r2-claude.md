# doc-citations-guard — round 2, Claude half

**NOT CONVERGED — 1 Blocking, 1 High, 3 Medium, 1 Low.**

Round 2's subject was the round-1 fixes, not the original work. That weighting was correct: **four of
the six findings below are defects in the fold itself**, and the Blocking one is a line written to
*describe* a round-1 finding.

Branch `doc-citations-guard` at `6e5a7a89`, reviewed against `origin/master`.

---

## Blocking — the branch is RED against its own gate

`docs/dashboard-entries.md:15116` was added by this branch and contains `(lib/a.ts:2)` — prose
describing the paren false positive that round 1 fixed. After that fix only the first path segment
is restricted, so the bracket is correctly *not* captured and the citation `lib/a.ts:2` is extracted
intact. It resolves to nothing, because `lib/a.ts` is a fixture path that exists only inside the
self-test's in-memory world.

```
$ python3 scripts/check-doc-citations.py --base origin/master
⛔ 1 drifted citation(s) added:

  docs/dashboard-entries.md: `lib/a.ts:2` does not resolve — no such file, and no tracked file ends with it
rc=1
```

CI runs this step on pull requests without suppressing failure, so the pull request cannot go green
as it stands. The parent's earlier green run predates the final dashboard edit.

**Fix:** write the example so it is not a citation — e.g. `` `(lib/a.ts:2)` `` rendered as
``(lib/a.ts<!---->:2)``, or drop the line number, or name a path that resolves. Then re-run the gate
against `origin/master` and confirm `rc=0` before opening the pull request.

⚠ Note the shape: a guard whose documentation cannot be written without tripping it will keep doing
this. Worth a deliberate convention for example citations in prose.

---

## High — removing a `---` horizontal rule disables the guard for the rest of the hunk

`scripts/check-doc-citations.py:201` clears scope on any line beginning `---`:

```python
        if line.startswith("---") or line.startswith("diff --git"):
            current = None   # a file boundary clears scope rather than inheriting it
```

A **removed** line is emitted as `-` plus its content, so removing a markdown horizontal rule `---`
emits `----`, which matches. Scope is cleared mid-hunk and every citation added after it is skipped.
This repository's documents use `---` rules constantly, so the trigger is ordinary editing.

Reproduced with a real repository and a real `git diff` — not a constructed diff string:

```
$ git diff --unified=0 --cached
--- a/docs/x.md
+++ b/docs/x.md
@@ -3 +3 @@ intro
----
+`lib/a.ts:999`

$ python3 scripts/check-doc-citations.py --base HEAD --root $T
doc citations OK — every `path:line` added under docs/ resolves to a real line
rc=0
```

Control — the same citation added *without* removing the rule:

```
$ python3 scripts/check-doc-citations.py --base HEAD --root $T
⛔ 1 drifted citation(s) added:
  docs/x.md: `lib/a.ts:999` is outside the file (1 lines)
rc=1
```

The citation is 998 lines past the end of a one-line file and the guard reports OK. This is a
fail-open, and it was **introduced by round 1's own boundary fix** — the branch that fix added is
the branch that carries the defect.

**Fix:** a file-boundary header is `--- a/...`, `--- /dev/null` or exactly `---` followed by
whitespace/EOL in the header position; a removed content line is none of those. Match `"--- "` and
bare `"---"` only when a `+++` has not yet been consumed for the current file, or more simply drive
scope from `diff --git` / `+++` alone and never clear on `---`. Add a case whose diff removes a
`---` rule and asserts the following citation still fires.

---

## Medium — a file that exists but cannot be read crashes out of a function documented as PURE

`scripts/check-doc-citations.py:252-260`: `_reader` returns `None` when `is_file()` is false, but
calls `read_text` unguarded otherwise. A file that exists and is unreadable raises out of
`violations()` — documented at `:185` as *"PURE — no git, no filesystem"* — and `violations()` is
called at `:465`, **outside** the `try` that produces CANNOT RUN at `:457-462`.

```
$ python3 -c '<drive violations() with _reader over a chmod 000 file>'
⛔ RAISED out of a 'PURE' function: PermissionError: [Errno 13] Permission denied: .../lib/secret.ts
```

Round 1's M1 fixed the *missing* branch and left its sibling. The promised contract is rc=2 CANNOT
RUN; the behaviour is a traceback.

**Fix:** catch `OSError` in `_reader` and return `None`, or raise a distinguished error that `main`
converts to rc=2. Decide deliberately which it should be — an unreadable file is arguably CANNOT RUN
rather than a finding — and add a case.

## Medium — a case added to fix the ambient-pass defect is itself ambient

`scripts/check-doc-citations.py:356`, *"a second +++ header RE-SCOPES, so a following citation is
judged under the new file"*, asserts `== []`. It passes when re-scoping works **and** when header
handling is removed entirely, because with no header handling `current` is never set and the result
is also empty.

```
headers ignored -> 20 fails; RE-SCOPES among them? NO — it passes ambiently
```

This is the exact class r1-codex M3 raised, reappearing in a case written to answer it.

**Fix:** assert the positive. Put the citation under a *second* header that IS in scope and a first
that is not, so the case fails if re-scoping stops happening.

## Medium — all three documents' figures are off by one, and the cause is structural

Re-derived by importing the shipped module:

| figure | claimed | re-derived |
|---|---|---|
| reviews share | 26,344 / 27,239 = 96.7% | 26,344 / **27,240** = 96.7% |
| living corpus | 111 / 895 = 12.4% | **112 / 896** = 12.5% |
| PR window | 10 / 40 = 0.25 | 10 / 40 = 0.25 ✓ |

The docstring, `docs/backlog.md` and `docs/dashboard-entries.md` agree with each other and all three
disagree with the tree. The cause is that commit `6e5a7a89` — the commit that *recorded* the figures
— itself added citations to the corpus being measured:

```
docs/backlog.md: added citation `helpers/cloud.ts:132`
docs/dashboard-entries.md: added citation `lib/a.ts:2`
```

This is the fourth time these numbers have been wrong. The first three had a fixable cause; this one
does not, while a document reporting a corpus measurement lives inside that corpus.

**Fix:** state the figures against a named commit (`measured at <sha>`), or exclude the reporting
documents, or round so the claim survives its own recording. The docstring's instruction to
re-derive is right and should say which revision it was taken at.

## Low — `_header_path` contradicts its own docstring on undecodable bytes

`:177-180` promises *"undecodable: no scope rather than the WRONG scope"*, but `errors="replace"`
means invalid UTF-8 never raises:

```
  invalid utf-8 bytes   "b/docs/\377\377.md"  -> 'docs/��.md'
```

A replacement-char path is returned rather than `None`. It will almost always fall out of
`in_scope`, so the direction is safe, but the comment describes behaviour the code does not have.

**Fix:** either `errors="strict"` so the `except` is reachable, or correct the comment.

---

## What I could not break

Stated because a review that only lists findings overstates its own coverage.

- **`--root` plumbing is correct.** All three consumers receive it — `fetch_diff(args.base, root)`,
  `fetch_tracked(root)`, `make_reader(root)` at `:459-465`. No path honours it in one and not another.
- **`_header_path` survives** a literal backslash (`a\\b.md` → `a\b.md`), an escaped quote, a trailing
  tab, an unquoted space, and `/dev/null` → `None`.
- **The URL lookbehind and the first-segment restriction each have an isolating witness** — removing
  either produces exactly one failing case, the one named.
- **C-quote decoding has an isolating witness**: removing it fails exactly *"a C-quoted unicode header
  decodes and its citations are examined"*, 37/38.
- **Boundary clearing has an isolating witness**: removing it fails exactly one case.
- **`violations()` is genuinely pure** of git and filesystem; the only impurity reaches it through the
  injected `read`, which is Medium 1 above.
- **6 of 7 mutation `expect`s isolate correctly.** The seventh, the blank-line clause, fails 20 cases
  — broad, but its named case is among them.

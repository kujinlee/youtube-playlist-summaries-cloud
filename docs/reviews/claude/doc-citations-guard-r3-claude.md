# doc-citations-guard — round 3, Claude half

**NOT CONVERGED — 1 High, 1 Medium.**

Subject: the redesign in `6c1d5e4e`, which deleted `_header_path()` and the boundary clause and made
`violations()` take the path as a parameter. The claim under test is that header misparsing and
scope leaking are now **impossible by construction**.

**That claim holds.** I could not break it, and I tried the whole class that produced the previous
three fail-opens. What I did break is the *new* load-bearing mechanism — and the way I broke it is
that nothing in the suite is watching it.

---

## High — `-z` is the entire premise of the redesign and has no witness; removing it silently disables the guard

`changed_files` at `scripts/check-doc-citations.py:211` passes `-z` so git emits paths
NUL-delimited and never quoted. Every safety property the redesign claims rests on that one flag.

**No case fails when it is removed.** Mutation applied in memory, then `self_test()`:

```text
control failures: none (green)
-z dropped from changed_files    -> 0 case(s): []
```

For comparison, every other mutation I tried isolates to exactly one case:

```text
git CANNOT RUN -> 0        -> 1 case: '⛔ main() returns 2 — CANNOT RUN — when git cannot be reached, never 0'
read CANNOT RUN -> 0       -> 1 case: '⛔ main() returns 2 when a cited file exists but cannot be READ'
in_scope filter dropped    -> 1 case: '...and an out-of-scope changed file is never diffed at all'
in_scope .md clause dropped-> 1 case: 'a generated .html page is out of scope'
```

**The failure mode is total, not partial.** Without `-z`, `r.stdout.split("\0")` returns ONE element
containing every path separated by newlines and a trailing `\n`, so `in_scope` rejects it and the
scoped list is empty. Measured in a scratch repo containing one bad citation:

```text
shipped (-z)     changed=["'docs/bad.md'"]
                 scoped=['docs/bad.md']  rc=1
mutant (no -z)   changed=["'docs/bad.md\\n'"]
                 scoped=[]  rc=0
```

The guard passes everything and says so cheerfully. That is a fourth fail-open in this component —
not live, but undefended.

⭐ **And the case that looks like the witness is not one.** `scripts/check-doc-citations.py:321`
reads:

```python
case("a unicode docs path IS in scope — git hands it over unquoted via -z",
     in_scope("docs/é\t.md"), True)
```

The name claims something about git and `-z`; the assertion calls `in_scope` on a Python string and
touches neither. It is the same defect r1-codex raised as M3 — *"the header case contains no
citation that could trigger a finding"* — in a case written after that finding. It is also
duplicative: it exercises exactly the clauses `a nested docs .md IS in scope` already covers, which
is why no mutation distinguishes them.

**Fix:** a case that drives `changed_files` against a real scratch repo whose changed set only `-z`
survives — two scoped docs, or one whose name carries a space or newline — asserting the returned
tuple has the right *length* and no trailing whitespace. Add a mutation removing `-z` and name that
case. The current `:321` case should either be deleted as duplicative or rewritten to assert what
its name claims.

---

## Medium — glob metacharacters in a scoped filename make the pathspec over-match, so findings are misattributed and duplicated

`file_diff` at `scripts/check-doc-citations.py:220` passes the path as a git **pathspec**. Pathspecs
honour glob magic (`*`, `?`, `[...]`) even after `--`. Git matches the literal file *and* anything
the glob expands to, so one `file_diff` call can return a second, unrelated file's diff.

Scratch repo with `docs/[id].md` (citing `lib/a.ts:999`) and `docs/i.md` (citing `lib/a.ts:777`):

```text
pathspec 'docs/[id].md' matches:
    docs/[id].md
    docs/i.md
```

The guard then reports, `REAL rc=1`:

```text
⛔ 5 drifted citation(s) added:
  docs/[id].md: `lib/a.ts:999` is outside the file (1 lines)
  docs/[id].md: `lib/a.ts:777` is outside the file (1 lines)   <-- lives in docs/i.md
  docs/i.md:    `lib/a.ts:777` is outside the file (1 lines)   <-- same finding, again
  docs/q?mark.md: ...
  docs/star*name.md: ...
```

`lib/a.ts:777` is not in `docs/[id].md`. A guard whose purpose is to stop readers being sent to the
wrong place names the wrong file in its own message, and reports the same defect twice.

**It is fail-CLOSED and latent, which is why this is Medium and not High.** It over-reports rather
than misses, and the repository has no such document today:

```text
docs paths with glob chars: 0
```

The convention exists elsewhere, though — `app/api/html/[id]/route.ts` and siblings — so a doc named
in that style is plausible rather than exotic.

**Fix:** `--literal-pathspecs` on the `file_diff` invocation, or prefix the pathspec with
`:(literal)`. Verified:

```text
git --literal-pathspecs diff --name-only -z HEAD -- 'docs/[id].md'
    docs/[id].md
```

Add a case with a glob-named scoped file asserting exactly one finding attributed to it.

---

## What I could not break, stated so the coverage is not overstated

The redesign's central claim survived every attack I made on it.

* **`-z` itself is sound.** A filename containing a newline round-trips intact:
  `changed_files` returns `['docs/new\nline.md']` and the finding names it correctly.
* **`core.quotePath` both ways.** The r2-codex reproduction — a document named with a combining
  accent and a tab — now fires under `true` and `false` alike, `rc=1` both times, correctly named.
  That fail-open is genuinely closed, not relocated.
* **Deletions** (`rc=0`), **renames** (`rc=0`) and an **empty diff** (`rc=0`) are all clean in
  isolated repos; no crash, no invented finding.
* **`violations()` is genuinely pure.** Its AST references no `subprocess`, `open`, `pathlib`,
  `Path`, `read_text`, `is_file` or `os`; the only calls it makes are `int`, `len` and `resolve`.
* **Both CANNOT RUN witnesses isolate** to exactly one case each, as shown above.
* **All three figures reproduce and the three documents agree.** Re-derived through the new path
  (file list → per-file diff → `violations`): reviews share `26360/27255 = 96.7%`; living corpus
  `111/895 = 12.4%`; PR window `10/40 = 0.25/commit`. The docstring, `docs/backlog.md` row 49 and
  `docs/dashboard-entries.md` all carry `~26,350 of ~27,250`, `~111/~895` and `10 / 0.25`.
* **The branch passes its own gate** — `python3 scripts/check-doc-citations.py --base origin/master`
  returns `rc=0`.
* **The per-file cost is acceptable.** Over the last 40 commits the scoped changed-file count is
  median 2, mean 7.2, max 158; the live invocation takes 0.22s. One subprocess per scoped file is
  not a problem at this repository's scale.

## Ambient-case hunt

The directive asked for a fourth ambient case after three were found in earlier rounds. There is
one, and it is `:321` above — it is folded into the High because it is that finding's cause rather
than a separate defect. I found no others: every other mutation I constructed isolated to exactly
one case, and the `in_scope` cases, while they assert a predicate directly, are each distinguished
by at least one mutation.

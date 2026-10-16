# Round 5 — `doc-citations-guard` (backlog #49 / #291) — Claude half

Subject: `scripts/check-doc-citations.py` as rebuilt in `353dcef1`, on branch `doc-citations-guard`
at HEAD `b0914b58`. Also examined: `scripts/mutations/check-doc-citations.json`,
`scripts/check-plan-code.py`'s `EXPECTED_MUTATIONS`, `scripts/check-fixture-variation.py`,
`.github/workflows/ci.yml:567`.

Every fixture below was built in a throwaway repository under a scratch directory with
`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `GIT_CONFIG_NOSYSTEM=1` and
`HOME=/nonexistent`. No tracked file was modified except this one. Mutants were written to temp
copies and executed with `cwd` at the repository root, never by editing `scripts/`.

Baseline:

```
$ python3 scripts/check-doc-citations.py --self-test   ->  67/67 passed      rc=0
$ python3 scripts/check-doc-citations.py               ->  doc citations OK  rc=0
$ python3 scripts/check-fixture-variation.py           ->  855 parameters / 67 files  rc=0
```

---

## THE CLAIM UNDER TEST, and where it survived

> Citations are extracted from the PRE-image and the POST-image as a MULTISET of `(path, line)`
> and the guard checks what the document GAINED. Both images come from git, so there is ONE
> oracle, no line number crosses any boundary, and no diff is parsed.

**The half of that claim about the DOCUMENT holds, and I could not break it.** All five routes
through the round-4 seam now fire correctly, measured one at a time against a bad citation in a
scoped document (`rc=1` in every case):

| route | fixture | result |
|---|---|---|
| baseline | plain document | rc=1 |
| r4 H1 | form feed in the document | rc=1 |
| r4 H2 | `docs/** -diff` in a committed `.gitattributes` | rc=1 |
| r4 C1 | `diff.external` pointing at a script that prints `nothing` | rc=1 |
| r4-codex XH1 | `diff.strip.textconv` deleting the cited line + `docs/** diff=strip` | rc=1 |
| r4-codex XH1 route 5 | `docs/x.md working-tree-encoding=UTF-16LE` | rc=1 |
| — | `core.autocrlf=true` with a CRLF document | rc=1 |

The structural reason is sound and I verified it rather than assumed it: `citations()` runs a regex
over the whole blob, so nothing in the guard depends on where a line break falls in the document.
The three git settings the commit message calls "simply irrelevant" are irrelevant.

**The MULTISET holds.** I could not produce a count error. Twelve constructions, each checked by
importing the module: nested paths, the same citation reached bare and backticked, whitespace
inserted mid-citation, adjacent citations with no separator, a citation inside a longer path, a
range, `:10` alongside `:10-20`, a count that falls on one key while rising on another, `..`
prefixes, and Next.js route groups. `finditer` is leftmost-longest and non-overlapping, and
`post - pre` keeps counts correctly in all of them.

**THE FIGURES ALL REPRODUCE — including the one the scope decision rests on.** Re-derived by
importing `CITE`, `in_scope`, `resolve`, `citations`, `added_citations` and `violations`, never by
copying the grammar:

| figure | docstring | re-derived | verdict |
|---|---|---|---|
| 40-commit window, #291 rule | 9 firings, 0.23/commit, 3 commits | **9, 0.23, 3** | exact |
| ...under `--no-merges` | — | 9, 0.23, 3 | stable |
| ...under `--first-parent` | — | 9, 0.23, 3 | stable |
| 40-commit window, OLD rule | 10 firings, 0.25/commit, 4 commits | **10, 0.25, 4** | exact |
| the lost firing | `b2e10e39`, a citation its author never introduced | `b2e10e39`, `check-ci-watched.py:183`, present once in the pre-image and once in the post | exact |
| `b2e10e39` detail | old examined 6, four already in the pre-image; new examines 3 | **6, four already present; 3** | exact |
| reviews exclusion | 26,375 of 27,270 = 96.7% | 26,399 of 27,294 = **96.7%** | ratio exact; absolutes moved by 24, which is the stated structural caveat |
| living corpus | 111 of 895 = 12.4% | **111 of 895 = 12.4%** | exact |
| ranges | 369 of 895 = 41.2% | **369 of 895 = 41.2%** | exact |
| fenced, all living | 56 of 895 = 6.3% | **56 of 895 = 6.3%** | exact |
| fenced, fence-balanced | 41 of 879 = 4.7% | **41 of 879 = 4.7%**, 2 odd-fence documents | exact |

The lost firing is not a lost defect: the same citation is caught at `71a32378`, the older commit
that actually introduced it, under both rules. The narrowing is real and the argument for it is
correct.

**THE MANIFEST HOLDS.** I applied all 24 edits myself to temp copies. Every anchor binds **exactly
once**; no duplicate names; no duplicate anchor text; every `expect` names a real case; every
mutation goes red **through the case it names**; zero survivors.
`EXPECTED_MUTATIONS['scripts/check-doc-citations.py'] = 24` matches the manifest, and
`sum(EXPECTED_MUTATIONS.values())` read by importing `check-plan-code.py` is **1443**, as declared.

So the findings below are not about the comparison. They are about **what the rebuild stopped
witnessing, what it tells the reader, and three inputs on which it answers wrongly.**

---

# Blocking

None.

---

# High

## H1 — Four of round 4's own fixes still protect live fail-opens, and NOTHING witnesses any of them: each mutates to a measured rc=0 with the suite at 67/67

This is round 4's starred shape — *coverage decayed as a side effect of work nearby* — repeated at a
larger scale, and it is the finding of this round.

The retirement was audited directly rather than from the commit message. Of the 24 entries retired
from the manifest, **six name an anchor string that is still present in the shipped file**:

```
$ git show 353dcef1^:scripts/mutations/check-doc-citations.json > /tmp/old-man.json
# then, by importing json and reading scripts/check-doc-citations.py:
⛔ STILL PRESENT (1x): the empty-added-set short circuit is removed...
   anchor: '    if not added:\n'
⛔ STILL PRESENT (1x): ⛔ main() stops catching ValueError...
   anchor: '    except (RuntimeError, OSError, ValueError) as exc:...'
⛔ STILL PRESENT (1x): ⛔ r4 H1 — the document is split with Python's line rule (`splitlines()`)...
   anchor: '        return raw.split("\\n")\n'
⛔ STILL PRESENT (1x): ⛔ r4-codex M2 — the symlink refusal is moved back into the shared reader...
   anchor: '        if not target.is_file():\n            return None\n'
⛔ STILL PRESENT (1x): ⛔ r4-codex H2 — the document is read with `read_text()`...
   anchor: '        raw = target.read_bytes().decode("utf-8", errors="replace")\n'
⛔ STILL PRESENT (1x): ⛔ r4-codex H1 route 5 — the NUL refusal is removed...
   anchor: '        if "\\x00" in raw:\n'
retired entries whose anchor text is still in the file: 6
```

Two of those six are fine and I say so: `if not added:` is a pure short-circuit with no behavioural
property (removing it leaves 67/67 **and** changes no verdict, correctly), and `is_file()` is
re-covered by new entry 13. **The other four are live defences with no witness at all.** Each was
mutated on a temp copy; in every case the suite stayed at **67/67** and the real behaviour changed:

**(a) `split("\n")` → `splitlines()` — FAIL-OPEN.** The cited file counts lines Python's way, not
the way git, `sed` and the reader's editor do.

```
$ printf 'alpha\n\x0cbeta\n\ngamma\n' > lib/a.ts     # a form feed inside the CITED file
$ sed -n 3p lib/a.ts                                  #   -> empty: line 3 is blank
$ printf 'cite `lib/a.ts:3` here\n' > docs/x.md && git add -A
$ python3 <shipped> --root . --base HEAD      -> rc=1  "`lib/a.ts:3` is a blank line"
$ python3 <splitlines mutant> --root . --base HEAD -> rc=0  "doc citations OK"
$ python3 <splitlines mutant> --self-test     -> 67/67 passed
```

**(b) `read_bytes().decode()` → `read_text()` — FAIL-OPEN.** Universal newlines translate a lone
`\r` before any split can help. This is exactly r4-codex H2, which that round shipped *incomplete*.

```
$ printf 'intro\rmore\n\ntail\n' > lib/a.ts   # sed -n 2p -> empty
$ printf 'cite `lib/a.ts:2`\n' > docs/x.md && git add -A
$ python3 <shipped> --root . --base HEAD      -> rc=1
$ python3 <read_text mutant> --root . --base HEAD -> rc=0
$ python3 <read_text mutant> --self-test      -> 67/67 passed
```

**(c) the `_reader` NUL refusal — CANNOT RUN collapses to a pass.**

```
$ python3 -c "open('lib/a.ts','wb').write('const a=1\n\nexport default a\n'.encode('utf-16'))"
$ printf 'cite `lib/a.ts:2`\n' > docs/x.md && git add -A
$ python3 <shipped> --root . --base HEAD -> rc=2  "lib/a.ts holds NUL bytes once decoded as UTF-8"
$ python3 <NUL-removed mutant> ...       -> rc=0  "doc citations OK"
$ python3 <NUL-removed mutant> --self-test -> 67/67 passed
```

**(d) `main()`'s OSError arm — the declared `FAILS IF` has no case.** The module docstring lists
*"`git` cannot be run … which is CANNOT RUN (rc=2), never a pass"*. Removing `OSError` from the
first handler leaves 67/67:

```
$ env -i PATH=<dir containing only python3> python3 <shipped> --root . --base HEAD
    rc=2    CANNOT RUN — [Errno 2] No such file or directory: 'git'
$ env -i PATH=<same> python3 <OSError-dropped mutant> --root . --base HEAD
    rc=1    Traceback (most recent call last): ... raise SystemExit(main(sys.argv[1:]))
$ python3 <OSError-dropped mutant> --self-test -> 67/67 passed
```

**Why this is High rather than Low.** Three of the four are the fixes round 4 bought with three
Highs, and the file documents each at length — (a) and (b) carry a combined 25 lines of comment
explaining that they are "TWO INDEPENDENT HALVES and each needs its own mutation anchor". Both
anchors were then removed. The subjects did not move: the retirement reasoning appears to have
followed the *document* leaving the reader (which is true) rather than the clause's remaining
caller (cited files, where the property is identical and still reachable). ⚠ Note that the shipped
code is **correct** in all four cases; what is gone is any means of noticing if it stops being.

**The brief's question — "check that nothing was retired whose property still exists" — answers
NO for four entries.**

## H2 — An unmerged path reads as DELETED, so the guard reports rc=0 over a conflicted scoped document: a THIRD answer collapsing into the ordinary one

`blob()` is built around a distinction it states twice — *"A MISSING PATH AND A BAD REF ARE
DIFFERENT ANSWERS AND MUST NOT COLLAPSE"* (`scripts/check-doc-citations.py:334`). There is a third
answer it does not consider: **in the index, but not at stage 0.**

```
$ git merge other
CONFLICT (content): Merge conflict in docs/x.md
$ git ls-files -u
100644 ab5aaf38... 1   docs/x.md
100644 d453a097... 2   docs/x.md
100644 b3478560... 3   docs/x.md
$ git diff --cached --name-status -z -M HEAD | tr '\0' '\n'
U
docs/x.md
$ git cat-file -e :docs/x.md
fatal: path 'docs/x.md' is in the index, but not at stage 0
$ python3 scripts/check-doc-citations.py --root . --base HEAD
doc citations OK — every `path:line` newly cited in a STAGED docs/ change resolves to a real line
  rc=0
```

Adjacent control — the **same bytes**, one `git add` apart:

```
$ printf 'intro\nother side `lib/a.ts:2`\n' > docs/x.md && git add docs/x.md
$ python3 scripts/check-doc-citations.py --root . --base HEAD
⛔ 1 drifted citation(s) added:
  docs/x.md: `lib/a.ts:2` is a blank line — a reader following it lands on nothing
  rc=1
```

`changed_files` reports the path with status `U`, the generic two-field arm pairs it as
`(path, None)`, `blob(":docs/x.md")` gets a non-zero `cat-file -e`, the ref half is empty so no
`rev-parse` happens, and `None` is returned — which `findings_for` reads through the comment
*"deleted from the index: it has no citations to gain"* (`:380`). The document is not deleted; it is
unreadable at the path asked for, and per `CLAUDE.md` an unreachable subject is a FAILURE, never a
pass.

⚠ **The exit code cannot distinguish these, and the file is right to refuse prose matching.** Both
answers are `rc=128`:

```
$ git cat-file -e :docs/nosuch.md ; echo rc=$?
fatal: path 'docs/nosuch.md' does not exist (neither on disk nor in the index)
rc=128
$ git cat-file -e :docs/x.md ; echo rc=$?
fatal: path 'docs/x.md' is in the index, but not at stage 0
rc=128
```

So the structural question is `git ls-files -u -- <path>` (or `--stage`), not a message test.
⚠ **Bound, stated rather than hidden:** not reachable in CI, where the index equals `HEAD`. The
cost is a local green that the success message explains wrongly — it says *"unstaged edits are not
examined — `git add` and re-run"*, and here the file is staged, three times over.

---

# Medium

## M1 — The out-of-range message overstates every file's length by one, and the case that claims to pin the boundary "from both sides" cannot see it. TWELFTH AMBIENT CASE.

`_reader` returns `raw.split("\n")`, which leaves a trailing empty element on every
newline-terminated file. `violations` then uses `last_line = len(lines)`.

```
$ printf 'alpha\nbeta\ngamma\n' > lib/a.ts          # THREE lines
$ _reader('lib/a.ts') -> ['alpha', 'beta', 'gamma', '']   len = 4
$ cite :4  -> rc=1  "`lib/a.ts:4` is a blank line — a reader following it lands on nothing"
$ cite :5  -> rc=1  "`lib/a.ts:5` is outside the file (4 lines)"
```

The file has three lines. The reader is told four. And `:4` — *"a file that lost its last line …
the single commonest drift there is"*, in the manifest's own words — is reported as a blank line
rather than as out of range.

**The ambient case.** `scripts/check-doc-citations.py:1017` is named *"⛔ the line immediately past
the end fires, not only one far past it"* and its partner *"...and the last line itself does not, so
the boundary is pinned from both sides"*. Both run against the injected `world` at `:839`, whose
`lib/a.ts` is `["const a = 1", "", "export default a"]` — **three elements, no phantom**. Measured
side by side:

```
SUITE world  lib/a.ts = ['const a = 1', '', 'export default a']        len = 3
  :4 -> ['docs/x.md: `lib/a.ts:4` is outside the file (3 lines)']
PROD  reader lib/a.ts = ['const a = 1', '', 'export default a', '']    len = 4
  :4 -> ['docs/x.md: `lib/a.ts:4` is a blank line — a reader following it lands on nothing']
  :5 -> ['docs/x.md: `lib/a.ts:5` is outside the file (4 lines)']
```

The case asserts the out-of-range branch at `:4`; production never reaches it there. The name
describes a mechanism the body does not exercise — the tell this repository's own memory records.
This is the twelfth ambient case on this file, and the first one the #291 rebuild created: the
comment at `:467` that licensed the phantom —

> ⚠ The trailing phantom element `split("\n")` leaves on a newline-terminated file is never read:
> `violations` indexes only members of `added`, which git numbers.

— **was true of the old rule and is false of this one.** `added` no longer comes from git's line
numbers; it comes from citation text, which is arbitrary author input, so the phantom is reachable
by writing `:N+1`. The file warns *"⛔ Do not re-derive the old reason — it is no longer true of this
code"* about a different comment, 300 lines earlier, and leaves this one standing.

Net verdict is still a finding in both cases, so this is not a fail-open. It is a wrong number in
reader-facing output, a documented justification that the rebuild invalidated, and an unfalsifiable
boundary case.

## M2 — `-M` prevents six false refusals under `diff.renames=false`, and the fixtures cannot witness it

Removing `-M` from `changed_files` leaves **67/67**. It is nonetheless load-bearing:

```
# pure rename of a document carrying six copies of a bad citation
$ git config diff.renames false
$ git diff --name-status HEAD~1 HEAD
A   docs/new.md
D   docs/old.md
$ python3 <shipped> --root . --base HEAD~1   -> rc=0   (correct: a rename adds nothing)
$ python3 <no -M mutant> --root . --base HEAD~1 -> rc=1  "⛔ 6 drifted citation(s) added:"
```

With `diff.renames` unset both answer rc=0, because git has defaulted rename detection on since
2.9 — which is why the three rename witnesses pass either way. They are *structurally* unable to
see this: each sets `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`, so no fixture can
ever present `diff.renames=false`. The direction is a **false refusal**, which backlog #56 measures
as the fatal one.

## M3 — The deleted-document clause has no case, and deletion is the shape round 4 shipped a false refusal on

```
$ git rm -q docs/gone.md       # the document carried a bad citation
$ python3 <shipped> --root . --base HEAD            -> rc=0  "doc citations OK"   (correct)
$ python3 <clause-removed mutant> --root . --base HEAD -> rc=1  Traceback (TypeError out of citations)
$ python3 <clause-removed mutant> --self-test        -> 67/67 passed
```

`if post is None: return []` (`:379-382`) is the only thing standing between an ordinary `git rm` of
a scoped document and an uncaught `TypeError` — `TypeError` is not in `main()`'s
`(RuntimeError, OSError, ValueError)` tuple, so it escapes as a traceback rather than CANNOT RUN.
No case in the suite ever hands `findings_for` a `None` post-image: `drive()` always supplies one.
r4-codex XM1 was *"a DELETION-ONLY edit to any scoped document returned rc=2"*; the rebuild answers
deletion correctly and witnesses it nowhere.

## M4 — `blob()`'s `cat-file -p` refusal has no case, and its own docstring says it must be CANNOT RUN

`blob()` raises when `-p` fails after `-e` succeeded (`:352-353`), with the stated reason that *"an
unreadable repository is CANNOT RUN, never an empty document, because an empty document would read
as 'this file had no citations before' and turn every citation in it into a new one."* Replacing
that `raise` with `return None` leaves **67/67**. `_blob_witness` varies the ref and the root but
never produces a path that exists and cannot be printed.

## M5 — `--base <base tip>` charges a branch for citations the BASE deleted

```
# feature branch adds prose only; master then deletes the line carrying an old citation
$ git merge-base master feature -> 8d1853bc      master tip -> 8f6263a3
$ python3 scripts/check-doc-citations.py --root . --base master
⛔ 1 drifted citation(s) added:
  docs/x.md: `lib/a.ts:2` is a blank line — a reader following it lands on nothing
  rc=1
$ python3 scripts/check-doc-citations.py --root . --base "$(git merge-base master feature)"
doc citations OK
  rc=0
```

The branch gained nothing. The base lost something, so the branch's unchanged copy reads as new.
⚠ **Two honest qualifications.** (1) **Pre-existing, not fix-induced** — the pre-`#291` guard fires
on the same fixture (`rc=1`), because the same line appears as an addition in a tip-relative diff.
(2) Not reachable in the CI step: `ci.yml:49` checks out with `fetch-depth: 0` on the synthesised
merge ref, so `HEAD` already contains the base's deletion. It *is* reachable in the invocation
`ci.yml:550`'s sibling comment recommends — *"locally runnable with `--base origin/master` for the
author who writes the line"* — on any branch that is behind. It is not filed in rounds 1–4.

## M6 — `_reader` resolves a citation OUTSIDE the repository root

`read()` is `root / path` with no containment, and `CITE` matches a leading `../`:

```
$ citations("cite ../outside.ts:2 here")  ->  {('../outside.ts', 2): 1}
# ../outside.ts lives ABOVE the checkout and is tracked by nothing
$ git ls-files -> docs/seed.md docs/x.md
$ cite ../outside.ts:2  -> rc=0   "doc citations OK"
$ cite ../nothere.ts:2  -> rc=1   (control: the outside path does not exist)
$ cite ../outside.ts:9  -> rc=1   (control: out of range in the outside file)
```

Making the filesystem the existence oracle was deliberate (r1 H1), and its argument was about
untracked files *inside* the repository, such as `.claude/skills/shared/explainer-delivery.md`.
Escaping the root makes the verdict depend on the checkout's parent directory, which differs between
a developer's machine and a runner. `FAILS IF` says the guard fires when a citation *"resolves to no
tracked file"*; here it resolves to no file in the repository at all and passes.

## M7 — The declared case count is wrong by 3, and the repo's own count guard is structurally blind to it

```
$ grep -c '^    case(' scripts/check-doc-citations.py   -> 67
$ python3 scripts/check-doc-citations.py --self-test    -> 67/67 passed
$ sed -n '165p;812p' scripts/check-doc-citations.py
  --self-test  runs 64 cases. Most are over DOCUMENTS this file builds with an injected
    """64 cases. The count is declared in the module docstring and verified by running this."""
```

The docstring says the count is "verified by running this". It is not: `check-selftest-counts.py`
exits 0 over 52 scripts and this file is not among them, because `count_drift`
(`scripts/check-plan-code.py:2132`) matches `--self-test\s+#\s*(\d+) cases` and this declaration has
no `#`. The guard's inverse rule — *"declares a count but is not in POPULATION, so nothing checks
it"* — never fires, because the non-canonical form is not recognised as a declaration either. The
commit message reconciles it as *"64 cases plus 3 variation cases = 67"*; there is no second suite —
all 67 are `case()` calls inside `self_test()`, and the "variation" cases at `:1122-1133` are four
ordinary ones. This is the fourth declared-count drift `docs/dev-process.md` records for this
repository, and the first that no machine can see.

## M8 — The stated retirement arithmetic is wrong by two in both directions

The commit message and the round's brief say *"21 manifest entries RETIRED WITH THEIR SUBJECTS … and
7 added … one more retired as SUPERSEDED"* — 22 retired, 7 added. Measured against
`353dcef1^:scripts/mutations/check-doc-citations.json`:

```
old entries: 39   new entries: 24
by NAME:  retired=24  added=9
by EDITS: retired=26  added=11   kept-same-edits=13
entries whose EDITS are unchanged but whose NAME changed (would double-count): (none)
```

**24 retired and 9 added**, not 22 and 7. No entry was merely renamed, so renaming does not explain
the gap. The error cancels — `39 − 22 + 7` and `39 − 24 + 9` both give 24 — which is why the total,
`EXPECTED_MUTATIONS = 24` and the declared sum 1443 are all correct while the account of how they
got there is not. ⚠ Two of the 24 are the entries H1 shows should not have been retired at all, so
this is not only a tally: the sum FELL by 15 for this file, and 4 of those were live properties.

---

# Low

**L1 — a comment asserts a guard clause that is not in the code.** `scripts/check-doc-citations.py:453`:

> ⚠ `is_symlink()` BEFORE `is_file()`, because `is_file()` follows the link and answers True.

There is no `is_symlink()` call anywhere in the file (`grep -n is_symlink` returns that comment and
nothing else), and `_reader` reads straight through a link:

```
$ ln -s real.ts lib/alias.ts          # real.ts has 4 lines
$ _reader('.')('lib/alias.ts') -> ['one', '', 'three', 'four', '']
$ _reader('.')('lib/real.ts')  -> ['one', '', 'three', 'four', '']
```

The *behaviour* is right — r4-codex M2 found that refusing a cited code symlink was a false refusal —
and the whole 11-line comment block at `:448-455` describes the removed document-reading flow. A
comment claiming a defence that does not exist is the shape this repository has paid for before.

**L2 — `--no-color` now protects nothing, and its comment says otherwise.** `:401-404` claims the
flag is needed *"on BOTH invocations"* because decoration *"would corrupt \[the NUL-delimited paths]
in a quieter way"*. There is only one invocation left, and measured:

```
$ git config color.ui always
$ python3 <shipped> --root . --base HEAD          -> rc=1
$ python3 <--no-color removed mutant> ... --base HEAD -> rc=1
```

The verdict is identical. Keep the flag if you like; the comment's claim is not reproducible, and
the allow-list it protected was deleted.

**L3 — `--literal-pathspecs` has outlived its consumer.** Its only subject was `file_diff`'s
per-file `-- <paths>`, deleted in this commit. `changed_files` now passes no pathspec at all
(`grep -n '"--"'` finds none) and `blob` uses `<ref>:<path>`, which is not a pathspec. Removing the
flag leaves 67/67, and correctly so.

**L4 — two manifest entries are attributed to one case whose name does not mention the property.**
Entries 20 (the `rev-parse --verify` refusal) and 21 (the NUL refusal in `blob`) both `expect` *"⛔ a
missing pre-image is None while a broken ref or root is CANNOT RUN — never confused"*. Both are
killed, so there is no survivor — but `_blob_witness` is a five-element conjunction, and the case
name says nothing about NUL, so entry 21's red line names a property it did not break.

**L5 — `_blob_witness`'s annotation and docstring are a 4-tuple; it returns 5.** `:711-715` —
`-> "tuple[object, object, object, object]"` and *"How `blob()` answers four questions"*, immediately
above a docstring listing five names and a body returning five elements.

**L6 — dead helper with a docstring contradicting its neighbour.** `body()` at `:847-849` is defined
and never called (`grep -n 'body('` returns only the definition), and its docstring reads *"for
driving `main()`, which still sees a diff"* — while `drive()`'s docstring 200 lines later states
*"There is no diff text in this suite at all any more, which is the change this rebuild is for."*

**L7 — three more stale sentences in the module docstring's `--self-test` paragraph** (`:165-168`):
*"the hunk-header reader is exercised on diff texts"* (there is no hunk-header reader), *"four cases
build a throwaway git repository"* (seven witnesses do, called by seven cases), and the 64 of M7.

**L8 — a `clean` filter breaks the "one oracle" claim, with a stated bound.** Both images coming from
git makes them consistent with *each other*, not with what the reader reads:

```
$ cat .gitattributes            -> docs/*.md filter=lfsish
$ git config filter.lfsish.clean  <script replacing the citation with PLACEHOLDER>
$ sed -n 2p docs/x.md                      -> bad lib/a.ts:2 here     (what a reader reads)
$ git cat-file -p :docs/x.md | sed -n 2p   -> bad PLACEHOLDER here    (what the guard reads)
$ python3 scripts/check-doc-citations.py --root . --base HEAD -> rc=0
$ # control: same worktree bytes, filter attribute removed      -> rc=1
```

⚠ Bound: the `.gitattributes` half is committable but `filter.*.clean` lives in `.git/config`, so
unlike `docs/** -diff` (r4 H2) this is not author-committable, and in CI the filter is absent. Worth
one clause in the blind-spot list, not a fix.

**L9 — a >4300-digit line number is CANNOT RUN.** `int(match.group(2))` over an unbounded `\d+`:

```
$ python3 -c "open('docs/x.md','w').write('cite lib/a.ts:' + '1'*4400 + '\n')"
$ python3 scripts/check-doc-citations.py --root . --base HEAD
CANNOT RUN — Exceeds the limit (4300 digits) for integer string conversion
  rc=2
```

This is the live subject of the `ValueError` arm whose retired entry cited the deleted hunk-header
parser. The input is contrived; the direction is a false refusal of a document that is otherwise
fine, and CANNOT RUN blocks CI.

**L10 — a wrong-case citation passes on a case-insensitive filesystem.** `LIB/a.ts:1` resolves
through macOS's APFS to `lib/a.ts` and passes; on a case-sensitive runner no tracked file ends with
`/LIB/a.ts` and it fires. The divergence runs in the safe direction (CI is the stricter oracle), so
I record it rather than file it as a defect.

---

## Already found in earlier rounds and still live — not re-filed, but still true

`ci.yml:562-565` still carries the **first** generation of figures: *"the living corpus fires 175
times on 838 pathed citations (20.9%), while ADDED lines fire 6 times over 40 commits
(0.15/commit)."* r1's Claude half filed both numbers as wrong and r2's Codex half quoted these exact
two lines. Four rounds later they are a fourth set of figures in a third location, and this slice
re-measured everything else. The module docstring's own warning — *"these numbers have now been
wrong TWICE for the same reason"* — applies to the comment that wires the guard up.

## What I could not break

* **The document comparison.** All five round-4 seam routes fire; `diff.external`, `color.ui`,
  `core.autocrlf`, `docs/** -diff`, `textconv` and `working-tree-encoding` on the document all
  produce the correct verdict. The claim that no line number crosses a boundary is true of the
  document, and the regex-over-the-whole-blob design is why.
* **The multiset.** Twelve constructions, no count error.
* **Every figure.** Four exact, one ratio-exact with the stated structural drift of 24, plus the
  40-commit number re-derived three ways and the `b2e10e39` 6/4/3 breakdown reproduced exactly.
* **The manifest.** 24 entries, each anchor binding once, each mutation red through the case it
  names, zero survivors, `EXPECTED_MUTATIONS` and the 1443 sum both correct.
* **`--base` handling.** A tag, `HEAD^{tree}`, an empty string, `:` and a nonexistent ref all give
  the right answer (rc=1, rc=1, rc=2, rc=2, rc=2). The `rev-parse --verify` separation works; I
  could not make a bad base read as an empty pre-image.
* **The stated symlink blind spot is exactly as documented.** `docs/link.md -> ../notes-target.md`
  with the target out of scope: the blob holds `../notes-target.md`, rc=0. The docstring neither
  overstates nor understates it.
* **`git add -N`** leaves the path out of `diff --cached` entirely, so an intent-to-add document is
  not examined — local only, and within what the success message already says.

## On thrashing

Of the 20 findings above (2 High, 8 Medium, 10 Low), **two are fix-induced** (M1's phantom justification and H1's four
retirements are consequences of this slice's own rebuild). The other eighteen are either
pre-existing, newly measurable, or instrument defects the rebuild created by deletion rather than by
patching. The component that produced three consecutive fix-induced rounds — the diff/document seam
— **is gone and did not reappear**. The defect weight has moved wholesale from the deliverable to
the instrument, which is a different and better problem.

VERDICT: NOT CONVERGED

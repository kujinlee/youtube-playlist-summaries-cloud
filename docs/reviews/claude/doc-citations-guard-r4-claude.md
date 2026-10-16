# Round 4 — `doc-citations-guard` — Claude half

Subject: `cce97501` on `doc-citations-guard`. Primary file `scripts/check-doc-citations.py`.
Baseline before anything else: `--self-test` → `58/58 passed` rc=0; the guard over the real repo
→ rc=0; `check-fixture-variation.py` → rc=0; `check-review-decision.py` →
`ARCHITECTURE_REVIEW — thrashing: 'diff-extraction' carried fix-induced findings in r2 and r3`.
Python 3.14.4, git 2.49.0. Every fixture below is a throwaway repository under a temp directory;
no tracked file was modified.

## The claim under test, and the verdict on it

> No content and no identity is inferred from diff text any more. … the ONLY thing read out of a
> diff is `@@` hunk headers, and that is safe because every content line in a unified diff carries
> a one-character prefix, so no content line can begin at column 0 with `@@`.

**The structural half is TRUE and I could not break it.** The inference drawn from it is not.

Reading only `@@` headers is safe *as diff parsing*. It is not sufficient for the guard, because
the headers carry **line numbers into a document that is read from somewhere else** — git numbers
lines, `_reader` numbers lines, and nothing checks that the two are numbering the same object.
That seam did not exist before this round: `violations()` used to take its content from the same
bytes the numbers came from, so the two could not disagree. Three of the findings below are the
same new seam reached by three different routes, and all three are **fail-open**, which is the
direction all four previous Highs failed in.

So the defect family did not end. It **moved** — out of diff *parsing*, which the redesign made
structurally safe, and into diff/document *agreement*, which the redesign created and did not
witness.

---

## Blocking

None.

---

## High

### H1 — `_reader` splits lines on seven characters git does not, so the guard reads the wrong line. Both directions reproduced.

`scripts/check-doc-citations.py:370` reads the document with
`read_text(...).splitlines()`. Python's `str.splitlines()` breaks on `\v \f \x1c \x1d \x1e \x85
U+2028 U+2029` and a lone `\r`; git ends a line only at `\n`. Any one of those characters anywhere
in a document shifts every later line number by one, so `doc_lines[n - 1]` at `:264` is **not the
line git said was added**.

Measured, by import, not by assertion:

```
  \f form feed     splitlines -> 2 entries   git lines -> 1
  \v vert tab      splitlines -> 2 entries   git lines -> 1
  \x85 NEL         splitlines -> 2 entries   git lines -> 1
  U+2028           splitlines -> 2 entries   git lines -> 1
  U+2029           splitlines -> 2 entries   git lines -> 1
  \r lone CR       splitlines -> 2 entries   git lines -> 1
```

**Direction 1 — a drifted citation on an added line passes (fail-open).** Base commit holds one
git line `intro<FF>more`; the author then appends a line carrying `lib/a.ts:2`, which is blank in
`lib/a.ts`.

```
$ git -C $REPO --literal-pathspecs diff --unified=0 -M HEAD -- docs/x.md | tail -2
@@ -1,0 +2 @@ intro^Lmore
+see `lib/a.ts:2` here
$ python3 scripts/check-doc-citations.py --root $REPO --base HEAD
doc citations OK — every `path:line` added under docs/ resolves to a real line        rc=0
```

Control, the identical document with the form feed replaced by a space:

```
⛔ 1 drifted citation(s) added:
  docs/x.md: `lib/a.ts:2` is a blank line — a reader following it lands on nothing    rc=1
```

**Direction 2 — a commit that added no citation at all is blocked (false positive).** Base holds
`intro<U+2028>more` on git line 1 and a year-old `lib/a.ts:2` on git line 2. The author appends
one innocent sentence and changes nothing else:

```
$ git ... diff --unified=0 -M HEAD -- docs/x.md | tail -2
@@ -2,0 +3 @@ old stale `lib/a.ts:2` from last year
+harmless new sentence
$ python3 scripts/check-doc-citations.py --root $REPO --base HEAD
⛔ 1 drifted citation(s) added:
  docs/x.md: `lib/a.ts:2` is a blank line — a reader following it lands on nothing    rc=1
```

That second direction breaks the **added-lines-only contract** the whole scope argument rests on —
the 96.7% exclusion and the 12.4% living rate are justified by "ADDED LINES ONLY", and here a
citation from last year is attributed to this commit.

**Live population, measured over the repository rather than imagined.** 4 tracked `.md` files
already disagree with git's line count today:

```
docs/reviews/architecture-review-2026-09-22-observer-family.md   splitlines 858  git 856
docs/reviews/claude/backlog-99-paused-tick-r2-claude.md          splitlines 289  git 286
docs/reviews/claude/observer-log-owner-r1-claude.md              splitlines 404  git 402
docs/reviews/claude/retire-plan-mode-r1-claude.md                splitlines 166  git 164
```

All four are under `docs/reviews/` and therefore out of scope **today** — so this is latent, not
live, and I am not overstating it. But the producer of those characters (U+2028/U+2029) is this
project's own review-writing agents, and the only thing between them and the scoped corpus is the
`docs/reviews/` exclusion; the moment such text is quoted into `docs/backlog.md` or a dashboard
entry — which these guards' own documents do constantly — it is in scope.

**No case can tell the difference.** In my sweep, `splitlines()` → `split("\n")` left the suite at
**58/58 passed** (survivor list below). `split("\n")` is also the fix: it matches git's rule
exactly, and its only side effect is one phantom trailing element, which `violations` never reads
because it only indexes members of `added`.

### H2 — a scoped document git calls binary is skipped entirely, rc=0, and the document need not contain a single odd byte.

`added_lines()` finds no `@@` in a binary diff, so it returns `()`, and `findings_for`
(`scripts/check-doc-citations.py:292`) reads that as nothing to check:

```python
    added = added_lines(fetch_file_diff(base, root, path, source))
    if not added:
        return []
```

The round-3 document named the malformed-header direction as the one new fail-open. This is the
*other* exit from the same function, and it was not named.

**Route A — a NUL byte anywhere in the document.**

```
$ printf 'see `lib/a.ts:2` here\nbinary\000marker\n' > $REPO/docs/nul.md && git -C $REPO add -A
$ git -C $REPO --literal-pathspecs diff --unified=0 -M HEAD -- docs/nul.md | tail -1
Binary files /dev/null and b/docs/nul.md differ
$ python3 scripts/check-doc-citations.py --root $REPO --base HEAD
doc citations OK — …                                                                  rc=0
```

**Route B — a tracked `.gitattributes`, on a plain-ASCII document.** This one needs no unusual
content at all, only a line anybody can commit, and it is the realistic route:

```
.gitattributes: 'docs/** -diff'   diff tail: Binary files /dev/null and b/docs/plain.md differ
    SHIPPED: doc citations OK — …                                                     rc=0
.gitattributes: 'docs/** binary'  diff tail: Binary files /dev/null and b/docs/plain.md differ
    SHIPPED: doc citations OK — …                                                     rc=0
.gitattributes: 'docs/** text'    diff tail: +see `lib/a.ts:2` here        <- CONTROL
    SHIPPED: ⛔ 1 drifted citation(s) added:                                           rc=1
```

Same document bytes in all three; the only difference is the attribute. The third row is the
adjacent control, so this is not a claim about an absurd fixture.

Per `CLAUDE.md` — *"cannot run" is a FAILURE, never a pass* — a diff with no hunk headers over a
file git reports as **changed** is a CANNOT RUN, not an empty change set. The guard already draws
that distinction correctly two lines later for an unreadable document; it does not draw it here.

### H3 — for a symlinked document the diff numbers the link and the reader numbers the target.

Third route into the same seam, and it needs no exotic characters or attributes.

```
$ ln -s target.md $REPO/docs/link.md && git -C $REPO add -A
$ git -C $REPO --literal-pathspecs diff --name-status -z -M HEAD | tr '\0' '|'
A|docs/link.md|
$ git -C $REPO --literal-pathspecs diff --unified=0 -M HEAD -- docs/link.md | tail -1
\ No newline at end of file
$ python3 scripts/check-doc-citations.py --root $REPO --base HEAD
doc citations OK — …                                                                  rc=0
```

git's hunk header describes the **link text** (one line, `target.md`). `_reader` at
`scripts/check-doc-citations.py:368` tests `target.is_file()`, which follows the link, so
`doc_lines` is the **target's** four lines. `added` is `(1,)`, the guard examines `"line1"`, and
the drifted `lib/a.ts:2` on line 4 of what `docs/link.md` now resolves to is never read — even
though `docs/link.md` is a brand-new scoped path whose every line is new.

The adjacent survivor from the sweep is `is_file -> exists`, which also left the suite at 58/58:
nothing in the suite distinguishes the reader's treatment of a non-regular file at all.

---

## Medium

### M1 — a document ENTERS the scoped corpus by rename and is never examined, by any run, past or future.

`file_diff` puts the rename source in the pathspec (`scripts/check-doc-citations.py:340`) so git
pairs the halves and a rename adds nothing. That is r3-codex CM1's fix, and it is right for an
in-scope rename. It is wrong when the pre-image was **never in scope**, because then no run ever
checked those lines and no run ever will:

```
reviewsintodocs:  docs/reviews/old.md -> docs/promoted.md   R100   rc=0
scriptsintodocs:  scripts/notes.md    -> docs/notes.md      R100   rc=0
txtintomd:        docs/notes.txt      -> docs/notes.md      R100   rc=0
```

Each source document carries `lib/a.ts:2` (blank). Each destination is in scope. All three pass.

The distinguishing test, which is what makes this a finding rather than a restatement of the
contract: for an ordinary in-scope rename an earlier run **did** check those lines when they were
added, so skipping them is correct. For these three, `in_scope(source)` is False in every case —
the `.md` test, the `docs/` prefix test and the `docs/reviews/` exclusion respectively — so the
lines have never been seen and, being "not added" forever after, never will be. This is
fix-induced from round 3, which is the thrashing pattern continuing.

### M2 — no case parses a hunk header carrying a function-context suffix, which is the shape git emits for nearly every real hunk.

`HUNK` is applied with `.match`, not `.fullmatch`, which is what lets real output parse. Pinning
the end of the pattern leaves the suite completely green:

```
mutant: HUNK pattern gains a trailing `$`   ->  58/58 passed, rc=0
```

and turns the guard into CANNOT RUN on an ordinary diff:

```
$ git ... diff --unified=0 -M HEAD -- docs/x.md | tail -2
@@ -5,0 +6 @@ ctx5
+harmless appended line
$ [mutant] python3 g.py --root $REPO --base HEAD
CANNOT RUN — unparsable hunk header: '@@ -5,0 +6 @@ ctx5'                              rc=2
```

Every `added_lines` case uses a bare header (`"@@ -1,0 +2,3 @@"`, `"@@ -1 +2 @@"`, …), and of the
three repository witnesses `_nul_witness` never calls `file_diff`, `_pathspec_witness` diffs a
**new** file (no funcname), and `_rename_witness` produces no hunks at all. So the suite cannot
tell a parser that handles git's real output from one that refuses all of it — and refusing all of
it is rc=2 on every PR, which is loud, but the suite is not what would have told you.

### M3 — `--unified=0` is load-bearing and has zero cases.

```
mutant: --unified=0 dropped from file_diff   ->  58/58 passed, rc=0
```

At the default `-U3` the hunk header's `+c,d` range spans the context lines, so `added` contains
lines the author did not touch:

```
DEFAULT -U3 hunk header: @@ -2,3 +2,4 @@ ctx1          (start 2, count 4 -> lines 2,3,4,5)
  [shipped  --unified=0] rc=0  doc citations OK
  [mutant   --unified=0 dropped] rc=1
       docs/x.md: `lib/a.ts:2` is a blank line — a reader following it lands on nothing
```

The author appended one line; the mutant blames a citation three lines above it. Note this is the
**same observable symptom as H1's direction 2** — two independent routes to breaking the
added-lines-only contract, and the live one is H1.

### M4 — three of the six new `main.*` exemption rows state a measurement that does not hold.

`check-fixture-variation.py`'s own precedent, which the round brief quotes: an exemption resting on
something untrue is worse than none. I performed each stated substitution — insert the module
default for the injected parameter immediately after `args = parser.parse_args(argv)` — and ran the
suite. **All four stated counts reproduce exactly.** Three rows name a case that does not redden.

| row | claimed | measured | named case reddens? |
|---|---|---|---|
| `main.fetch_changed` | 7 red, incl. "main() returns 0 over a clean world" | **7 red** | ✅ YES |
| `main.fetch_tracked` | 7 red, incl. "main() returns 1 when a citation has drifted" | **7 red** | ✅ YES |
| `main.root` | reddens both `--root` cases | 2 red | ✅ YES, under the strong reading (see below) |
| `main.argv` | `parse_args(argv)` → `parse_args([])` reddens 2 named cases | **0 red, rc=2, the suite never runs** | ❌ NO |
| `main.make_reader` | 6 red, "**including both CANNOT RUN cases**" | 6 red | ❌ NO — no CANNOT RUN case is among them |
| `main.fetch_file_diff` | 6 red, incl. "main() returns 2 when a hunk header does not parse, never 0" | 6 red | ❌ NO |

* **`main.argv`** — the row specifies the substitution literally, and performing it removes
  `--self-test` from the parsed arguments, so `main()` runs the real check instead of the suite:
  `rc=2`, stdout empty, **zero** red cases. "Zero red" is exactly how an exemption reads as *not
  load-bearing*, which is the dangerous direction. The row's conclusion is nonetheless sound: the
  nearest runnable variant (keep `--self-test` reachable, ignore the rest of `argv`) gives
  `56/58 passed` with both named cases red. So the fix is to the recorded recipe, not the row.
* **`main.root`** — under my first reading (insert `root = ROOT`, leaving the `--root` flag
  handling in place) only `"...and without --root it is the root main() was handed"` reddens, since
  the other case tests the flag, not the parameter. Under the stronger reading (`root = ROOT` after
  the override too) both redden: `56/58 passed`. Verified, no finding; recorded here so the next
  reader does not repeat my weaker experiment.
* **`main.make_reader`** — the six red cases are `main() returns 0 over a clean world`,
  `main() returns 1 when a citation has drifted`, and the four `--base`/`--root` cases. No CANNOT
  RUN case appears, and none *can*: both of the two reach rc=2 before the injected reader matters
  (the hunk-header case raises inside `added_lines`; the unreadable-document case raises because
  the real `_reader` also returns None for a path that does not exist), so each still asserts
  `== 2` and still passes. The clause is false under every reading, not just mine.
* **`main.fetch_file_diff`** — same shape: substituting the real `file_diff` makes git fail against
  the fixture's `/nonexistent` root, which is *also* rc=2, so the named case passes for a different
  reason than the one it names.

### M5 — AMBIENT CASE (the eighth on this file): the bare-filename case uses the one stem length for which its own property is an equivalent mutation.

`scripts/check-doc-citations.py:668`:

```python
    case("a bare filename with no directory is NOT a citation",
         lambda: violations("docs/x.md", (1,), ["`a.ts:2`"], tracked, read) == [])
```

The named property is the directory-separator requirement in `CITE`. Making that separator optional
survives at **58/58**. The reason is the fixture, not the rule — with a one-letter stem the first
character class consumes the `a` and nothing is left before the extension dot, so the mutant cannot
match either. Every stem of two or more characters separates them:

```
input              shipped            separator-optional mutant
'`a.ts:2`'         []                 []                 <- the case's fixture
'`ab.ts:2`'        []                 ['ab.ts']
'`route.ts:2`'     []                 ['route.ts']
'`ensure.ts:66`'   []                 ['ensure.ts']
```

The file's own docstring at `:143-144` argues this rule with `route.ts:12` and the measurement
"1,266 occurrences in living docs". The docstring picked the input that distinguishes; the case
picked the one that does not.

### M6 — AMBIENT CASE (the ninth): the `tracked_files` case names the empty-tree refusal and exercises the git-failure raise.

`scripts/check-doc-citations.py:746` — *"⛔ `tracked_files` on a path that is no repository RAISES
**rather than passing over nothing**"*. `tracked_files` has two raises (`:355` git failed, `:358`
refusing to pass over an empty tree). The fixture reaches the first:

```
  Path('/nonexistent')              -> git ls-files failed: fatal: cannot change to '/nonexistent'
  a freshly `git init`ed repo       -> git ls-files returned nothing — refusing to pass over an empty tree
```

The second raise has a reachable witness — the second line above — and zero cases, confirmed by
the sweep: `tracked_files: an empty tree passes` left the suite at **58/58**. The clause the
docstring argues for ("an empty list would pass about nothing") is the one with no case, and the
case that claims it is satisfied by the other branch.

### M7 — the out-of-range boundary is untested on the under-reporting side, and the manifest pins only the other side.

```
mutant: raw_line > len(lines) + 1   ->  58/58 passed, rc=0
```

The case is `"a line past EOF fires"` with `lib/a.ts:99` against a 3-line file — 96 lines past the
boundary. Measured over the shipped code:

```
  :3   over a 3-line file -> 0 finding(s)
  :4   over a 3-line file -> 1 finding(s)      <- the boundary, untested
  :99  over a 3-line file -> 1 finding(s)      <- what the case uses
```

`:4` is the single commonest drift there is: a file that lost its last line. Manifest entry 2 pins
the *over*-reporting direction (`>` becomes `>=`, caught by "line 3 (last line) is in range"), so
this exact line was considered and only one side of it was covered. Negatives have to be adjacent
to be falsifiable.

---

## Low

### L1 — the rename case cannot tell the destination from the source.

```
mutant: changed_files yields (fields[i+1], fields[i+2]) instead of (fields[i+2], fields[i+1])
    ->  58/58 passed, rc=0
```

Measured directly on the witness's own fixture:

```
changed_files gives (path='docs/new.md', source='docs/old.md')
  findings_for(correct orientation) = []
  findings_for(SWAPPED orientation) = []
  in_scope(dest)=True  in_scope(source)=True
```

`_rename_witness` asserts `== 0`, which both orientations produce, and both paths are in scope, so
the case named *"a pure rename of a document with a BAD citation adds nothing"* is blind to the
pairing it depends on. Low rather than Medium because an inverted pairing is loud in production —
a rename-with-modification would audit the deleted path, `read` returns None and `findings_for`
raises to rc=2 — but the case is not what would tell you.

### L2 — the historical figure's recorded method does not reproduce its own number.

The figure itself is **exact**: injecting both the `git show <commit>:<path>` reader *and* a
two-ref diff gives **10 firings over 40 commits = 0.25/commit across 4 commits**, with the
composition the docstring hand-classifies (eight blank lines, `development-velocity.md:262`
now a 70-line tombstone, `dist/index.mjs:145`). Reproduced identically under `rev-list -n 40`,
`--no-merges` and `--first-parent`.

But the docstring (`:40-42`) records the method as *"injecting a `git show <commit>:<path>`
reader — no checkout"*. Injecting only that reader and calling the shipped `file_diff` gives
**6 firings across 2 commits and 78 `RuntimeError`s**, because `file_diff` and `changed_files`
take a single `base` and always diff it against the **worktree**, never commit-to-parent. So the
recipe as written under-reports by 4 and silently converts most of the corpus to CANNOT RUN. The
second injection is mandatory and unrecorded.

This is also the honest answer to the brief's "loss of the ability to read a historical patch":
it is not merely that a blob reader is needed, it is that **the diff must be injected too**,
because the shipped functions cannot express a two-ref diff at all.

### L3 — seven clauses that survive the whole suite; each is correct in the shipped code and witnessed by nothing.

From the sweep (53 mutants over the shipped file, control green at 58/58, 3 anchors unbound and
excluded, **15 survivors**). H1, H3, M2, M3, M7 and L1 above are survivors already filed. The rest:

| survivor | what it means |
|---|---|
| `HUNK`: drop the `^` anchor | doubly redundant — `line.startswith("@@")` gates, and `.match` anchors at 0 |
| `changed_files`: drop `-M` | measured redundant: rename detection is on by default, so the rename case stays green |
| `file_diff`: drop `-M` | same |
| `changed_files`: drop `--literal-pathspecs` | that call carries no pathspec, so the flag does nothing there |
| `file_diff`: git failure returns `""` instead of raising | a CANNOT RUN direction with no case. Reachable in principle (`file_diff("HEAD", ".", "docs/../../etc/x.md")` → RuntimeError) but not from a path `--name-status` can emit, so the handler is correct and merely unwitnessed |
| `_reader`: `is_file` → `exists` | no case distinguishes a non-regular file; adjacent to H3 |
| `resolve`: `f.endswith(path)` instead of `f.endswith("/" + path)` | the suffix match's **segment boundary** has no case: without the slash a citation of `c/ensure.ts` resolves to `lib/html-doc/ensure.ts` |
| `CITE`: drop the `\b` after the line number | no case; without it `lib/a.ts:12abc` becomes a citation of `:12` |

---

## Was this the right redesign? (brief item 5)

**Yes as far as it went, and there is a shape that removes more of the class. I prototyped it
rather than arguing it.**

What the redesign genuinely bought, stated first because it is real: the four header defects of
r1–r3 are gone *by construction*, not patched, and I could not reconstruct any of them. The
property it rests on is true (see "could not break"). The r1 L2 fence exemption did become
reachable. The manifest and the figures are in better shape than any previous round's.

What it cost: the **numbers** now cross a boundary the **bytes** used to stay inside. H1, H2 and
H3 are one defect — *the diff and the document are two oracles and nothing checks they describe
the same object* — reached three ways. Patching them individually (use `split("\n")`; treat a
hunkless diff of a changed file as CANNOT RUN; refuse a non-regular file) is correct and I would
take all three. But a fourth route is likely, because the seam remains.

**The shape that removes the seam: compare citation STRINGS, not line numbers.** Read the
pre-image document (`git show <base>:<source or path>`) and the post-image document (the
worktree), extract `CITE` matches from each, and check the multiset difference. No line numbers
cross the boundary; no diff text is parsed at all; `added_lines`, `HUNK`, `--unified=0` and the
hunk-header CANNOT RUN all cease to exist.

Measured — a 40-line prototype against every fixture in this review, beside the shipped guard:

| fixture | shipped | prototype |
|---|---|---|
| H2 route A — NUL byte in the document | **rc=0 (misses)** | rc=1, finds it |
| H2 route B — `docs/** -diff` attribute | **rc=0 (misses)** | rc=1, finds it |
| H1 direction 1 — form feed, drifted citation added | **rc=0 (misses)** | rc=1, finds it |
| H1 direction 2 — U+2028, innocent append | **rc=1 (false positive)** | rc=0, correct |
| M3 — `-U3` context window over a stale citation | rc=0 | rc=0 (the dependency is gone) |
| pure rename of a document with a bad citation | rc=0 | rc=0 |
| rename+recreate (a real added citation) | rc=1 | rc=1 |
| the real repository, branch vs `origin/master` | rc=0 | rc=0 |

It also strengthens what "added" means in the direction the guard wants: a citation that merely
*moved* is not re-examined, and a citation that is genuinely new is caught however the file was
reformatted around it. M1 becomes a policy choice (pass `base:source` or not) instead of an
accident.

**Two honest caveats.** (1) It is a **scope change**, not a redesign: "on an added line" becomes
"a citation string new to this document", which is exactly the ground on which the fence exemption
was deferred this round. So this is a FILING with the measurement as its argument, in the same
shape as r1 L2 — not something to land inside round 4. (2) The firing rate would have to be
re-measured; the string-difference rule is slightly wider than the line rule (a reformatted
paragraph re-presents its citations), and 0.25/commit does not transfer.

**On cost, since the brief asks: N+1 is real and small, and it is not a reason to change
anything.** Measured on the real repository against `origin/master`: 26 changed paths, 7 scoped,
`1 (name-status) + 1 (ls-files) + 7 (per-file) = 9` git subprocesses, the per-file diffs taking
0.17s against 0.06s for a single `git diff -- docs/`. The prototype is the same order (1+N
`git show`, batchable through `git cat-file --batch`). Nothing here argues for or against either
shape.

---

## What I could NOT break — stated plainly, so the coverage is not overstated

* **The structural `@@` property itself.** I looked for a unified-diff line beginning at column 0
  with `@@` that is not a hunk header, and for a hunk header off column 0. Tried: function-context
  suffixes (`@@ -5,0 +6 @@ ctx5`, and one whose funcname contains a form feed), `\ No newline at
  end of file`, a `----` markdown rule, `+@@ -9,0 +99 @@` as added content, a document whose first
  line begins `@@`, mode-change-only entries, binary `Binary files … differ`, an empty diff, a
  symlink entry, `--literal-pathspecs` with glob-shaped names, and a document with CRLF. Found
  none. The claim's structural half holds for `git diff --unified=0 -M --literal-pathspecs` as
  invoked. What fails is the inference, not the property.
* **`added_lines`' arithmetic and its raise.** Count-of-3, omitted count, `+c,0` deletion hunk,
  multi-hunk accumulation, and the ValueError-to-rc=2 path all survived every attack, and each has
  a case that reddens when flipped.
* **The 20-entry mutation manifest, verified by applying every edit myself**: 20 anchors all bind
  exactly once, no duplicate names, no duplicate anchors, every `expect` name exists in the suite,
  and **20 killed / 20 attributed to every case they name**, matching the commit message exactly.
  `EXPECTED_MUTATIONS['scripts/check-doc-citations.py'] = 20`; declared sum **1439**; no file's
  manifest length disagrees with its row; no manifest on disk lacks a row.
* **All seven stated figures, re-derived by importing the module.** 26,375 of 27,270 (**96.7%**);
  111 of 895 (**12.4%**); 369 of 895 ranges (**41.2%**); 41 of 879 fenced over fence-balanced
  documents (**4.7%**) and 56 of 895 over all (**6.3%**, reproducible only under the reading that
  an odd trailing fence opens a block to EOF — the qualifier the docstring flags is doing real
  work); 10 firings over 40 commits at **0.25/commit**; **58** self-test cases. The one method
  problem is L2, and it does not touch any number.
* **The `EXAMINED_KEYS` pin is the real set** — 23 pinned, 23 examined, empty difference in *both*
  directions. Worth noting that `check-fixture-variation.py:1234-1240` only checks
  `pinned - keys`, so the agreement is a fact about this commit rather than something enforced.
* **Two of the six exemption rows (`fetch_changed`, `fetch_tracked`) are exactly right**, and
  `main.root` is right under the stronger reading. All four stated counts reproduce.
* **`--base` pointing at an unrelated ref** (an orphan branch) is conservative: the whole document
  reads as added and the guard fires. Not a fail-open.
* **Staged-but-not-committed changes** do not create a disagreement: `git diff <base>` and
  `_reader` both see the worktree, so H1's class is not reachable this way.
* **Mode-change-only entries, deletions, and `--root`** behaved correctly in every fixture.

---

## Were rounds 2 and 3's defects actually dissolved?

Checked individually, because "dissolved" is the claim that justifies the redesign.

| prior finding | dissolved? |
|---|---|
| r3-codex CH1 — `++` discarded as a header | **Yes.** No body parser exists; `"++ `lib/a.ts:99`"` is examined like any line |
| r3 H1 — `-z` has no witness | **Yes**, and the witness runs git: dropping `-z` reddens its case |
| r3 M1 — glob pathspec over-match | **Yes** for `file_diff`; the `changed_files` copy of the flag is redundant (L3) |
| r3 CM1 — rename reports new citations | **Yes** for in-scope renames — and the fix opened M1 |
| r2 H1 — `---` boundary matched `----` | **Yes.** `added_lines` has no boundary concept |
| r2-codex CH1 / r1-codex H1 — C-quoted / UTF-8 paths | **Yes.** The path comes from `--name-status -z` |
| r2 M2 — the fix's own case was ambient | **No, as a class.** Two more ambient cases this round (M5, M6), making eight and nine on this file |

---

VERDICT: NOT CONVERGED

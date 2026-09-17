# Round 3 — Claude adversarial half, `schema-gates-always-reports` (backlog #137)

## Subject, confirmed by execution

```
$ git log --oneline -8
2ec4d072 r3 codex: 2 Lows, both prose — the thrashing question answered with evidence
20b88211 r2 claude: 1 High + 5 Medium + 3 Low, and the High was in the predicate this file exists for
3e25d630 r2: a child vouched for its parent, and CI caught a crash this machine could not
99f4da56 Dashboard: what round 1 cost and what it caught (backlog #137)
a5a50d8f r1 High 2: make under-coverage LOUD, since measurement says it cannot be made SOUND
b3052e11 r1 Blocking: three mutations shared one anchor and the whole 719-entry harness went dark
3a2fc5e3 Round 1 found the fail-open this branch had only declared, and the fix is a class fix (backlog #137)
839bc738 Fifteen schema gates reported red into a void, and the filter protecting them was buying nothing (backlog #137)

$ git rev-parse HEAD
2ec4d0720d2d76ff533d9afe654b55fcc13c0a3c
$ git branch --show-current
schema-gates-always-reports
$ git status --porcelain
(clean)
$ git diff --stat master...HEAD | tail -1
 17 files changed, 2609 insertions(+), 183 deletions(-)
```

Reviewed commit **`2ec4d072`**, base `93c815c8` (PR #315). Mutation evidence was taken against a
copy of the tracked tree at `/tmp/rr3/repo` (`git ls-files -z | xargs -0 tar cf - | tar xf -`, a
COPY so `ROOT` resolves to the copy); measurements of the real corpus were taken read-only against
the working tree. No tracked file was modified except this document.

---

## Verdict and shape — read this before the count

**NOT CONVERGED** — 1 High, 4 Medium, 3 Low.

**The branch is SAFE TO MERGE on the code.** Not one finding below makes the shipped gate return a
wrong answer. The High and two of the Mediums are in the **review record and the backlog**, not in
`scripts/check-review-recorded.py`; the code findings are a falsifiability gap on a CANNOT-RUN
guard, an unpinned constant, and three inert clauses.

**The High is the one the round was convened to look for, and it is not where anyone expected.**
The asymmetry that three coordinator documents — and my own r2 half — state as measured is **false**,
and it has been concealing **two r1 findings inside the `#137` workflow change that are still open at
`HEAD`**.

**On the process question: the THRASHING DETERMINATION STANDS, and its stated REASON does not.**
Round 3 carries six fix-induced findings, not two, and only two of those are prose. The
determination survives a stricter test than the one the coordinator applied — *can a redesign remove
it?* — under which **none of the six is a mechanism defect**. That is a different and better
argument than "both findings are prose", and the difference is actionable: the prose-floor label
prescribes *stop reviewing and go build*, while the correct labels (branch-coverage and stale
cross-reference) prescribe *fix, plus an exhaustiveness pass*. Section
[⟳ Thrashing](#-thrashing-my-own-determination-not-an-inheritance) carries the per-finding evidence.

**Three things the branch gets right, verified rather than assumed:**

1. **The `antidrift_verdict` extraction is behaviour-preserving.** I compared the extracted function
   against the **pre-extraction inline sequence in `main`** (`3e25d630`) — not against `HEAD~1`,
   which carries the drift codex found — across six states, by RUNNING `main` with the derivation
   patched. Exit codes and message text are **byte-identical in five of six**; the sixth difference
   is the intended r2 Medium 2 fix. Codex's r3 Low 1 was real and is closed.
2. **The broadened `is_gate_data` has no false positive today, and I found its plausible near-future
   one and executed it.** The outcome is loud, and the remedy the failure message prescribes
   actually works — contrary to my first reading of it. Evidence in *no finding*, item 1.
3. **The manifest's identity holds independently.** 61 entries, 61 unique names, 61 unique anchor
   tuples, 61 unique `old` anchors, every anchor occurring **exactly once** in the delivered file,
   every entry carrying an `expect`, and `EXPECTED_MUTATIONS` pinned at 61 == the accepted
   population. The r1 Blocking cannot recur from this file.

---

## HIGH 1 — the asymmetry the retreat rests on is FALSE, and two r1 findings inside the `#137` change are still open at `HEAD`

**VERIFIED.** `docs/reviews/coordinator/schema-gates-always-reports-r3-coordinator.md` ("The
asymmetry that has held for all six halves"), the same claim in
`…-r2-coordinator.md`, and — I have to own this — in my own r2 half.
**ORIGIN: (b) pre-existing.** First written in the r2 coordinator document, carried unchanged into
r3. **NOT fix-induced**, so it does not meet this round's stated trigger. Its severity therefore has
no bearing on whether the retreat fires, which is why I can grade it on merit without gaming
anything.

The claim, verbatim:

> **The actual #137 change — the deleted `paths:` filters — has produced ZERO findings.** Codex
> checked it directly this round and reported none. Every finding in three rounds has been in the
> collateral derivation […]

**Three separate things are wrong with that, and the third is the expensive one.**

### (a) The r1 claude half filed two findings in the workflow change, and its own Summary table names them

```
$ grep -n "^## \(MEDIUM 10\|LOW 14\)" docs/reviews/claude/schema-gates-always-reports-r1-claude.md
411:## MEDIUM 10 — the workflow's justification for requiring the context rests on a false premise, and the counterexample has ZERO slack (VERIFIED)
519:## LOW 14 — removing the `push:` filter lets a docs-only merge cancel a code merge's gate run
```

Low 14's subject is **the deletion itself** — not the derivation, not collateral prose. So the claim
is refuted even under the narrowest possible reading of "the deleted `paths:` filters". Medium 10's
subject is `.github/workflows/schema-gates.yml:58-60`, prose this branch's first commit **wrote**.

### (b) Both are still open at `HEAD`, and nothing since r1 says otherwise

```
$ grep -n "expected to transfer" .github/workflows/schema-gates.yml
60:# expected to transfer.

$ sed -n '58,60p' .github/workflows/schema-gates.yml
# docs-only PRs by construction, so it is evidence and not proof. The job's verdict does not depend
# on the diff (it rebuilds the same database from the same migrations), which is why the record is
# expected to transfer.

$ grep -n "WHAT IS LOST" .github/workflows/schema-gates.yml
74:# ⚠ WHAT IS LOST, SAID PLAINLY: the log no longer distinguishes "this PR could not have broken a
```

The false premise is verbatim. `WHAT IS LOST` still does not mention the push-run cancellation.
Neither appears in the r1, r2 or r3 fix lists.

**And the premise is still false at `HEAD`** — I re-derived it rather than inheriting r1's
measurement, because this branch **edited one of the two files it turns on**:

```
$ grep -n -A3 "^LINE_BUDGETS" scripts/check-docs.py
191:LINE_BUDGETS = {
192:    "docs/dev-process.md": 220,   # the spine: what must be true, in what order, who decides
193:    "docs/plugins.md": 260,       # plugin governance + tool gates

$ wc -l docs/dev-process.md docs/plugins.md
     220 docs/dev-process.md
     260 docs/plugins.md
```

**220/220 and 260/260 — zero slack on both.** `check-docs.py` is gate 6 of the fifteen, so a
docs-only diff appending one line to either file turns `schema-gates` **red**. "The job's verdict
does not depend on the diff" is false for gates 3, 6 and 15.

### (c) The r3 "independent confirmation" is attributed to a reviewer that did not report the check

The r3 coordinator document says *"Codex checked it directly this round and reported none."* Codex's
r3 half lists what it ran, and the workflow is not in it:

```
$ sed -n '/Checks I ran that did not produce findings/,$p' docs/reviews/codex/schema-gates-always-reports-r3-codex.md | grep -n "^\$\|^derived\|^bound\|^entries\|^tracked"
check-review-recorded.py --self-test      178/178
check-plan-code.py --self-test            128/128
check-plan-code.py --mutate .             732 killed
derive real gate dirs and bound docs paths
manifest identity
tracked docs path length
```

Six checks, none of which opens `.github/workflows/schema-gates.yml`. A confirmation credited to a
reviewer who did not report performing it is the shape this repository refuses everywhere else —
*"a script beats a claim only when it reads the thing the claim is about"*, and *"'Cannot run' is a
FAILURE, never a pass"*. It is worse than an unsourced claim, because it reads as corroboration.

**Why HIGH rather than Medium**, stated so it can be argued with. r1's Medium 10 (a false premise in
a workflow comment) and Medium 11 (wrong numbers in a backlog row) are the comparable claim defects
on this branch and both are Medium. This one escalates on three counts: it is the **load-bearing
premise of a pre-committed retreat** and of a process-gate determination; it **caused a second
reviewer to repeat it** without re-deriving (me, r2 — the corroboration was worthless, because what
I actually tested was the deletion's *trigger semantics*, and I then carried the coordinator's "zero
findings" phrasing rather than checking it against r1's own summary table); and it has kept **two
filed findings invisible for two rounds**, which is a consequence no wrong sentence in a comment has.

**What this does NOT do:** it does not change the retreat. Corrected, the asymmetry is still
strongly in the same direction — 11 of r1-claude's 14 findings, all 9 of r2-claude's, codex's
1+1+2, and all 7 of mine below in the derivation, against 2 in the workflow change. "Reverting the
derivation" remains the right retreat. The sentence "every finding" and the word "ZERO" are what
must go, together with the invented confirmation.

**Observation that proves it fixed:** the asymmetry is restated with the two exceptions named and
their status (open / fixed), the r3 "Codex checked it directly" sentence is removed or replaced by a
check someone actually ran, and r1's Medium 10 and Low 14 are either closed or explicitly carried.

---

## MEDIUM 2 — the empty-derivation CANNOT-RUN guard has no falsifier: its case passes for an ambient reason

**VERIFIED.** `scripts/check-review-recorded.py:586` (`if not derived:`), case at `:1385-1386`.
**ORIGIN: (a) fix-induced** — by the r2 Medium 6 fix. The clause pre-existed in `main`; the
extraction into `antidrift_verdict` and the case written to cover it are both new in `20b88211`, and
the case cannot see the clause.

The extraction was done because I measured, in r2, that the ordering and the call sites were
undrivable. It closed that: the order mutation goes red, and two of the three exit codes are pinned.
**The third is not.** Delete the guard and the suite stays green:

```
$ # /tmp/rr3/repo, sole edit: `if not derived:` -> `if False:`
CONTROL:  (0, '178/178 passed')
  antidrift: empty-derivation guard removed  -> SURVIVED (suite green)  [178/178 passed]
```

Because the case asserts only the exit code, and the **completeness prong returns the same code**:

```
REAL           antidrift_verdict([], CODE_UNDER_PROSE)[0] = 2   <- the SHIPPED case asserts 2
               antidrift_verdict([], ())[0]               = 2
GUARD DELETED  antidrift_verdict([], CODE_UNDER_PROSE)[0] = 2   <- passes anyway
               antidrift_verdict([], ())[0]               = 0   <- a falsifier that DISTINGUISHES
```

With the guard gone, `declared_not_derived([], CODE_UNDER_PROSE)` reports both declared directories
missing and returns 2 by a different route. The case's own name — *"an empty derivation is CANNOT RUN
**before either question is asked**"* — names precisely the property it cannot observe.

**Concrete failure scenario.** The guard is load-bearing exactly when the declaration is empty, and
that state is reachable: both exempted spec directories are finished work (`m4` merged, the
stable-blob spec **parked**), so archiving them and emptying `CODE_UNDER_PROSE` is an ordinary future
edit. With the guard silently removed at some earlier point, `derived == []` and `declared == ()`
then yields **rc 0** — the gate reporting a pass over a derivation that found nothing, which is the
"a zero over nothing is not a finding" fail-open the guard's own comment is about.

**Observation that proves it fixed:** `case("...and it refuses even with nothing declared, so the
empty-derivation guard is not standing on the completeness prong", antidrift_verdict([], ())[0], 2)`,
plus a manifest entry on `if not derived:` — there is none today, so `--mutate .` is blind to it too.

---

## MEDIUM 3 — `docs/backlog.md` row 137 ships stale counts for the THIRD time on this branch

**VERIFIED.** `docs/backlog.md`, row 137.
**ORIGIN: (a) fix-induced** — the r1 Medium 11 fix wrote numbers that the r2 and r3 fixes then moved
past, twice, without touching the row.

The row states, as the branch's outcome:

> **manifest 43→52, total 714→723** […] **Self-test 139→157.**

Shipped truth at `HEAD`:

```
$ python3 scripts/check-review-recorded.py --self-test | tail -1
178/178 passed
$ python3 -c "import json;print(len(json.load(open('scripts/mutations/check-review-recorded.json'))))"
61
$ grep -n 'case("the declared counts are the real ones"' scripts/check-plan-code.py
3237:    case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 732)
```

**61 / 732 / 178**, against the row's 52 / 723 / 157. The chain of this exact defect on this branch:

| Round | Row said | Shipped | Status |
|---|---|---|---|
| r1 Medium 11 | 43→47 / 714→718 / 139→148 | 50 / 721 / 153 | filed, fixed |
| r2 (not filed) | 43→52 / 714→723 / 139→157 | 56 / 727 / 166 | went stale again, unnoticed |
| **r3 (here)** | 43→52 / 714→723 / 139→157 | **61 / 732 / 178** | stale by 9 / 9 / 21 |

`check-selftest-counts.py` reads only `scripts/*.py`, so no gate sees a count in a Markdown row —
the blind spot `docs/plugins.md` records against itself (*"a count with no owner drifts again, and
the only durable fix is to have one copy, in the place a gate can run"*). The r1 fix updated the
numbers; it did not give them an owner, which is why they went stale twice more.

**Observation that proves it fixed:** the row's counts either match the shipped values, or — better,
and what the plugins.md lesson actually prescribes — are **deleted** from the row in favour of
pointing at the pinned `EXPECTED_MUTATIONS` and the script's own declared count, both of which a
gate already checks. (`check-selftest-counts` rc=0 and `check-test-counts` rc=0 today; they simply
cannot see this row.)

---

## MEDIUM 4 — the severity-trajectory table that carries the determination misstates three of its cells, including my own half's

**VERIFIED.** `docs/reviews/coordinator/schema-gates-always-reports-r3-coordinator.md`, *"The
trajectory, measured rather than asserted"*.
**ORIGIN: new in round 3** — a bookkeeping defect in the r3 coordinator document, not caused by a
code fix.

Re-derived from the review documents' own headings and verdict lines:

```
$ grep -c "^## \(BLOCKING\|HIGH\|MEDIUM\|LOW\) " docs/reviews/claude/schema-gates-always-reports-r1-claude.md
14
$ grep -n "^## LOW" docs/reviews/claude/schema-gates-always-reports-r1-claude.md
471:## LOW 12 …   501:## LOW 13 …   519:## LOW 14 …
$ grep -n "NOT CONVERGED —" docs/reviews/claude/schema-gates-always-reports-r2-claude.md
33:**NOT CONVERGED** — 1 High, 5 Medium, 3 Low.
572:**NOT CONVERGED** — 1 High, 5 Medium, 3 Low.
```

| half | table says | documents say | wrong cells |
|---|---|---|---|
| r1 claude | 1 / 4 / 6 / **4** | 1 / 4 / 6 / **3** (1+4+6+3 = 14 ✓, and its Summary table lists 14) | 1 |
| r2 claude | 0 / **2** / **6** / 3 | 0 / **1** / **5** / 3 (its own verdict line, stated twice) | 2 |
| r1 codex | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 ✓ | — |
| r2 codex | 0 / 0 / 1 / 0 | ✓ | — |
| r3 codex | 0 / 0 / 0 / 2 | ✓ | — |

The table also disagrees with the **coordinator's own r3 dispatch brief** to me, which says
*"1 Blocking, 6 High, 12 Medium, 3 Low across four halves"*. Summing the corrected rows gives
Blocking 1 ✓, High 6 ✓, Medium 12 ✓ — the brief matches the documents and the table does not — while
Low is **6**, so the brief is wrong on Low too and in the other direction.

**This does NOT change the verdict, and that is worth stating plainly.** Corrected, High runs
4 → 1 → 1 and Blocking 1 → 0 → 0: still a monotonic decline, still prose-only on the codex half. The
finding is that a table introduced with the words *"measured rather than asserted"* was asserted, in
the document whose job is to justify a process decision — the *"never write a cost table from memory:
DERIVE, don't store"* shape, applied to a review record.

**Observation that proves it fixed:** the table's cells equal the counts in the documents it
summarises, and the brief's Low total is corrected to 6.

---

## MEDIUM 5 — `PATH_LIMIT`'s VALUE is unfalsified across a 4,545-byte window, and 1024 is itself too generous by `len(ROOT)+1`

**VERIFIED (both halves, executed).** `scripts/check-review-recorded.py:288` (`PATH_LIMIT = 1024`),
clause at `:517`, cases at `:1442-1445`.
**ORIGIN: (a) fix-induced** — this constant IS the r2 Medium 4 fix.

### (a) The two cases bracket the bound so loosely that Linux's PATH_MAX survives

```
$ # /tmp/rr3/repo, sole edit: the value of PATH_LIMIT
CONTROL:                  (0, '178/178 passed')
  PATH_LIMIT = 4096    -> SURVIVED  [178/178 passed]
  PATH_LIMIT = 2048    -> SURVIVED  [178/178 passed]
  PATH_LIMIT = 1025    -> SURVIVED  [178/178 passed]
  PATH_LIMIT = 100000  -> killed    [FAIL] a path over the TOTAL byte limit is rejected…

the two shipped cases' inputs, in bytes:
  reject-case: len('docs/' + '/'.join(['a'*100]*50)) = 5054
  accept-case: len('docs/' + '/'.join(['a'*100]*5))  =  509
```

509 < bound < 5054 is all that is pinned. **4096 — Linux's `PATH_MAX`, i.e. precisely the wrong
value for the platform this finding was about — leaves the suite at 178/178.** `COMPONENT_LIMIT` in
the same function is the model this one failed to follow: its cases are 256 bytes (reject) and 255
bytes (accept), so its value is pinned exactly, and its own comment explains that it exists as a
separate NAME so the width rule and the limit carry separate anchors. The manifest has an entry
deleting the `PATH_LIMIT` clause (killed) and none pinning its value.

### (b) The guard bounds `rel`; the OS receives `ROOT/rel`

`main:1253` injects `is_file=lambda rel: (ROOT / rel).is_file()`, so the string handed to `stat()` is
`len(str(ROOT)) + 1` bytes longer than the string `looks_like_path` measured. Executed on both
interpreters, on a path `looks_like_path` **accepts**:

```
=== 3.14 ===  len(str(ROOT)) = 69   PATH_MAX(os.pathconf) = 1024
  rel= 1014B  abs= 1084B  looks_like_path=PASS -> is_file: returned False
=== 3.12 ===  len(str(ROOT)) = 69   PATH_MAX(os.pathconf) = 1024
  rel=  913B  abs=  983B  looks_like_path=PASS -> is_file: returned False
  rel= 1014B  abs= 1084B  looks_like_path=PASS -> is_file: RAISED OSError errno=63
                                                  [Errno 63] File name too long
```

So on macOS with Python ≤3.12 there is a live band — `rel` between **955 and 1024 bytes** — that the
shape guard admits and that raises `ENAMETOOLONG` inside the case-list build: the unattributable-kill
crash this branch's headline r2 defect was, one platform over. The constant's comment calls 1024 a
*"Conservative bound"*; it is conservative for Linux and **negative by 70 bytes** for the platform
the number was taken from.

**Reachability: REASONED, and it is not live.** CI is Linux (`PATH_MAX` 4096), so 1084 bytes is safe
there. Over the real corpus:

```
longest bound docs/ string:                           152B (rejected — contains whitespace)
longest bound docs/ string reaching is_file:           77B
widest whitespace-free TOKEN containing docs/ anywhere: 108B  (run-schema-assertions.sh)
gap band: rel in (954, 1024] bytes
```

846 bytes of headroom. The finding is the pair of claims, not a live crash: a bound whose value no
case can distinguish from the wrong one, described as conservative when it is not.

**Observation that proves it fixed:** two cases bracketing the bound tightly —
`looks_like_path("docs/" + "/".join(["a"*100]*10))` (1010 B) is True and a 1030-byte path is False —
plus either a `PATH_LIMIT` that accounts for the prefix, or an `is_file` injection that answers False
on `OSError` (which is what 3.13+ already does), or the word "conservative" narrowed to "conservative
on Linux; on macOS the effective bound is `PATH_LIMIT - len(str(ROOT)) - 1`".

---

## LOW 6 — r2 Low 7 is reported fixed and is not, and the fallback that masks it is unfalsified too

**VERIFIED.** `scripts/check-review-recorded.py:149` (`PROSE_FILES`), `:216-217`, `:221`.
**ORIGIN: (b) pre-existing code, plus a claim defect in the r3 fix report** (the dispatch brief says
"all nine of your r2 findings" were fixed).

r2 Low 7 asked for one case: `guarded_changes([".gitignore"]) == []`. It was not added —
`.gitignore` still appears exactly once in the whole file, in the constant:

```
$ grep -n "gitignore" scripts/check-review-recorded.py
149:PROSE_FILES = ("README.md", "CLAUDE.md", "AGENTS.md", "CONTEXT.md", ".gitignore")
```

and both halves of the pair survive individually while being killed only together — a textbook
mutual mask:

```
CONTROL:                                              (0, '178/178 passed')
  is_prose: PROSE_FILES branch deleted             -> SURVIVED  [178/178]
  is_prose: root-.md fallback -> False             -> SURVIVED  [178/178]
  PROSE_FILES loses `.gitignore` only              -> SURVIVED  [178/178]
  BOTH prose branches deleted at once              -> killed    [175/178]
      [FAIL] README.md is prose: got ['README.md'] want []
      [FAIL] CLAUDE.md is prose: got ['CLAUDE.md'] want []
      [FAIL] AGENTS.md is prose: got ['AGENTS.md'] want []
```

The five `PROSE_FILES` cases all use root `.md` files, so they pass via the fallback; the fallback
has no case of its own because every input it would need is in `PROSE_FILES`. Each clause is
defended only by the other's inputs. The **root-`.md`-fallback half is a new observation** — r2 Low 7
named only the tuple — and the manifest's entry for the fallback mutates it to `return True`
(killed), never to `return False`.

Direction of failure is noisy in both directions (a `.gitignore` one-liner, or a new root
`CHANGELOG.md`, would demand a review round), which is why this stays Low.

**Observation that proves it fixed:** `guarded_changes([".gitignore"]) == []` (isolates the tuple)
and `guarded_changes(["NOTICE.md"]) == []` for a root `.md` outside the tuple (isolates the
fallback).

---

## LOW 7 — `antidrift_verdict`'s `declared` parameter governs only one of its two prongs

**VERIFIED.** `scripts/check-review-recorded.py:578`, `:239`.
**ORIGIN: (a) fix-induced** — the parameter is new with the r2 Medium 6 extraction.

```
signatures:
   antidrift_verdict      (derived, declared) -> (int, str)
   declared_not_derived   (derived, declared) -> list[str]
   prose_exceptions_cover (gate_dirs)         -> list[str]      <- NO declared parameter

--- `declared` held FIXED; only the module global CODE_UNDER_PROSE moves ---
  CODE_UNDER_PROSE=2 entries -> antidrift_verdict(D, declared=<fixed>) rc=1
  CODE_UNDER_PROSE=3 entries -> antidrift_verdict(D, declared=<fixed>) rc=0
```

The completeness prong takes `declared`; the coverage prong reads the module constant. A future case
written as `antidrift_verdict(dirs, ("docs/x/",))` to drive the coverage rule would be exercising the
real tuple instead — the "a case can pass for an AMBIENT reason" shape, pre-installed in the fix
written to remove it.

**Why only Low, and the correction to my own first read of it.** I initially took the docstring's
`PURE` label as falsified by the global read. It is not: this file uses `PURE` to mean *no
filesystem, no git, a case can call it directly*, and `is_prose`, `guarded_changes` and
`review_added` all read module constants under the same label. The residual is narrower — an
**inconsistency between two sibling rules in one function**, where one takes the tuple and the other
closes over it, which reads as an oversight rather than a decision and will mislead the next
case-writer.

**Observation that proves it fixed:** `prose_exceptions_cover(gate_dirs, declared)` takes the tuple
and `antidrift_verdict` threads its own parameter into both prongs — after which a case can drive
the coverage rule with a synthetic declaration; or a sentence saying the coverage prong is
deliberately global and why.

---

## LOW 8 — three clauses that cannot receive their intended input any more, and none has a case or a mutation

**VERIFIED.** `ORIGIN: (b) pre-existing` — all three date from `839bc738`, the original `#137`
commit, where two of them were re-pointed from globs to derived directories and not re-examined.

```
CONTROL:                                                    (0, '178/178 passed')
  prose_exceptions_cover: drop glob-star split            -> SURVIVED  [178/178]
  declared_not_derived: rstrip on derived removed         -> SURVIVED  [178/178]
  gate_code_dirs: spec_dirs dot-filter dropped            -> SURVIVED  [178/178]
```

1. **`prefix = g.split("*")[0]`** (`:243`). The docstring says the rule *"still accepts a glob's `*`
   prefix"* — but `gate_code_dirs` can no longer produce one: prong 1's regex is `[\w./-]+`, which
   excludes `*`, and prong 2 requires the path to EXIST as a file. The authority it was written for
   (`schema-gates.yml`'s globs) is what this branch deleted. Dead since `839bc738`.
2. **`stems = {x.rstrip("/") for x in derived}`** (`:566`). Derived directories come from
   `rsplit("/", 1)[0]`, so they never carry a trailing slash. The **declared**-side `rstrip` IS
   load-bearing, and I confirmed it rather than assuming: removing it goes red via two cases
   (`173/178`, `[FAIL] ...and the derivation FINDS every directory already declared as gate code`).
3. **`if "." not in p.rsplit("/", 1)[-1]`** in `spec_dirs` (`:428`). The runner binds exactly one
   `docs/` path today and it has no dot, so the filter never excludes anything. Its direction if it
   ever mattered is noisy — bogus `$SPEC`-joined directories would be reported as uncovered.

Low because all three are inert and two of the three fail noisy. Filed because this file's own r1
Low 12 was the same audit and these three were not in it, and because a clause whose justification
names a deleted authority is the *stale cross-reference* shape `review-method.md:213` prescribes a
grep for.

**Observation that proves it fixed:** each clause gets a case and a manifest entry, or is deleted, or
carries a sentence saying it is prospective and cannot currently fire.

---

## Is the branch SAFE TO MERGE, and is `schema-gates` SAFE TO MAKE REQUIRED?

**Both yes, in that order, and the order is not optional.** Stated separately from the convergence
verdict, because the two are different questions.

**Safe to merge — the code.** No finding above changes an answer the shipped gate gives. Every repo
gate is green against the working tree:

```
check-docs               rc=0      check-anchors            rc=0
check-plan-file-tags     rc=0      check-selftest-counts    rc=0
check-ratchet-contract   rc=0      check-guard-coverage     rc=0
check-backlog-closure    rc=0      check-test-counts        rc=0
check-review-recorded --self-test  178/178 rc=0
check-review-rounds      rc=1  <-- for ONE reason: "round 3: only codex — claude neither ran nor
                                   recorded a REVIEW GAP:", which this document closes
```

**Safe to require `schema-gates` — and the workflow's own stated reason for this is the false one.**
The right answer, which is r1's and is written down nowhere in the shipped file:

| Red on a docs-only PR | Newly blocking once required? |
|---|---|
| gate 6 `check-docs.py` — **the only tree-reading gate a docs-only diff can flip**, and its two line budgets have ZERO slack (220/220, 260/260) | **No.** `ci.yml:109` runs the same script inside `verify`, which has no path filter and IS required. Such a PR is already blocked today |
| gate 3 `check-guard-coverage.py`, gate 15 `check-paid-caller-arrival.py` | No — a docs-only diff cannot flip either |
| gates 1-2, 4-5, 7-14 | No — they rebuild the database from migrations and do not read the diff |
| **infrastructure**: the 0.34 GB Postgres image pull, `npm ci`, docker | **Yes — this is the whole of the new exposure**, and the file states it honestly |

So nothing is *wrongly* blocked. What is wrongly *stated* is the justification: "the job's verdict
does not depend on the diff" is false for three of fifteen gates, and the true argument is the
narrower one — *the only tree-reading gate a docs-only diff can flip is gate 6, which `verify`
already requires.*

**The ordering constraint holds and I re-verified it:** `prod-drift` is gated
`if: github.event_name == 'schedule' || … 'workflow_dispatch'` (`:206`), so no fork PR reaches
`CLAUDE_RO_DATABASE_URL`; `schema-gates` is gated `!= 'schedule'` (`:164`) so the context reports on
every PR, which is the point; `concurrency` still carries `github.event_name`; `permissions: contents:
read` unchanged. Adding the context **before** this merges blocks every docs-only PR.

---

## What I tried that produced NO finding

1. **The broadened `is_gate_data`, attacked directly — and its plausible near-future case
   EXECUTED.** No false positive today:

   ```
   every bound docs/ path over the 13 real gate sources, classified:
     GATEDATA   docs/superpowers/specs/m4/live-manifest.txt                       (43B)
     GATEDATA   .../stable-blob-addressing/schema/05_assert.sql                   (77B)
     GATEDATA   docs/superpowers/specs/m4/seed-assertion-corpus.sql               (51B)
     notfile    docs/adr, docs/reviews/, docs/superpowers/, .../schema, ...       (directories)
     prose/.md  docs/backlog.md, docs/dev-process.md, docs/plugins.md, ...
     noshape    'docs/...-render-addressing-brief.md, backlog #25).\n  Do NOT...'  (152B, whitespace)
   derived: 3 dirs   uncovered: []   undiscovered: []   antidrift rc=0
   ```

   There are **zero** tracked extension-less files under `docs/`, so the r2 Medium 3 deletion admits
   nothing new today. The only `docs/` directories holding a tracked non-`.md` file outside the two
   exemptions are `docs` itself (4 files) and `docs/reviews/verdicts`. I then built the near-future
   case: gate 6 — **already in the runner** — gaining one line binding the generated architecture
   page, which is exactly how a documentation-integrity gate grows:

   ```
   + ARCH = ROOT / "docs/architecture.html"

   derived: ['docs', '.../stable-blob-addressing', '.../schema', '.../m4']
   uncovered: ['docs']
   antidrift rc=1  FAILED — the schema gates treat 1 `docs/` director(ies) as gate machinery
                   that this gate still classifies as PROSE:  docs
   ```

   So one line in an existing gate reds `check-review-recorded` repo-wide. **That is the r2 Medium 2
   fix working as designed** (loud, not silent), and — correcting my own first reading of it — the
   remedy the message prescribes actually works and is not destructive:

   ```
   CODE_UNDER_PROSE + 'docs'  -> antidrift rc=0, uncovered=[]
       is_prose('docs/backlog.md')=True   is_prose('docs/reviews/claude/x.md')=True
       is_prose('docs/architecture.html')=False   is_prose('docs/available-skills.pdf')=False
   ```

   The `.md` carve-out keeps the whole prose tree prose; only non-`.md` files under `docs/` become
   guarded, which is the correct outcome. **No finding.** (My first run of this appeared to show the
   remedy failing; that was my harness passing a `declared` argument while `prose_exceptions_cover`
   read the global — which is Low 7, not a defect in the remedy.)

2. **The `antidrift_verdict` extraction, re-verified against the PRE-EXTRACTION subject.** Codex
   compared against `HEAD~1`, which is the commit carrying the drift; the equivalence question is
   against `3e25d630`, where the sequence was still inline in `main`. Executed by running `main`
   itself with `_gate_sources` and `gate_code_dirs` patched, comparing exit code AND stderr byte for
   byte:

   ```
   empty          pre rc=2 cur rc=2  rc_same=True  msg_IDENTICAL=True
   undiscovered   pre rc=2 cur rc=2  rc_same=True  msg_IDENTICAL=True
   uncovered      pre rc=1 cur rc=1  rc_same=True  msg_IDENTICAL=True
   both           pre rc=2 cur rc=2  rc_same=True  msg_IDENTICAL=True
   ok            (proceeds past antidrift in BOTH, to the same next stage)  IDENTICAL
   bare-docs      pre rc=2 cur rc=1  rc_same=False <- the INTENDED r2 Medium 2 fix
   STATES DIFFERING: 1
   ```

   Five of six byte-identical; the sixth is the fix. The restored `— measured twice on this branch.`
   suffix is present. **Codex's r3 Low 1 is genuinely closed, not reworded.**

3. **The manifest, independently.** 61 entries / 61 unique names / 61 unique anchor tuples / 61
   unique `old` anchors / `anchors NOT occurring exactly once in the delivered file: []` / every
   entry has an `expect` / `EXPECTED_MUTATIONS` pin 61 == 61. I also swept **every** manifest in
   `scripts/mutations/` for cross-file `(file, anchor)` collisions and found one —
   `check-plan-file-tags.json`, two entries sharing the `FILE_TAG` anchor. **Not a finding, and I
   chased it to the end rather than reporting it:** `load_manifests` keys its refusal on the
   **tuple** of anchors (`:1047`), those two entries have one and two edits respectively, so the
   tuples differ; and the file is untouched by this branch (`git diff --stat master...HEAD` on it is
   empty). That loose keying is already filed as this file's own r12 Low.

4. **An exhaustive clause sweep of the r3 fix surface.** 35 generated mutations across
   `is_gate_data`, `looks_like_path`, `prose_exceptions_cover`, `declared_not_derived`,
   `antidrift_verdict`, `gate_code_dirs`, `is_prose` and `review_added` — forcing each `if` to both
   constants, neutralising each `and`/`or` operand, deleting each clause, widening each constant.
   **Six survivors, all reported above** (Medium 2, Medium 5, Low 6 ×2, Low 8 ×3 — counting the
   PATH_LIMIT value separately). Everything r3 was meant to fix is killed via its named case:

   ```
   review_added: drop REVIEW_DIR clause (my r2 High 1)      -> killed  [176/178]
   is_gate_data: prose rule -> always False                 -> killed  [176/178]
   is_gate_data: extension-less rule restored (entry 57)    -> killed
   prose_exceptions_cover: drop the bare-docs disjunct      -> killed  [177/178]
   looks_like_path: drop PATH_LIMIT clause                  -> killed  [177/178]
   antidrift: swap order (coverage before completeness)     -> killed  [176/178]
   antidrift: undiscovered rc 2->1 / uncovered rc 1->0 /
              empty rc 2->0                                 -> all killed
   ```

   **My r2 High 1 is properly closed** — `review_added(["docs/notes.md"]) == []` isolates the
   `REVIEW_DIR` clause, and a second case carries it through `verdict`.

5. **`PATH_LIMIT` as a too-strict gatekeeper** (the silent direction the coordinator flagged). No
   live false rejection: the longest string reaching `is_file` over the real corpus is 77 bytes and
   the widest whitespace-free `docs/` token anywhere in the 13 gate sources is 108 bytes, so nothing
   is within 846 bytes of the bound. Codex's *"tracked docs files 1465, long offenders []"* is
   confirmed; the finding at this site (Medium 5) is about the bound's value and its prefix, not
   about under-coverage.

6. **`docs/backlog.md` row 138 — my r2 Medium 5.** Properly fixed, and fixed in the direction I
   asked for rather than reworded: the row now reads *"A content rule DOES separate them, and the
   first version of this row said otherwise"*, records the non-recursive 6-of-7 result and
   `docs/superpowers`' zero direct children, and gives the honest deferral reason —
   *"FRAGILITY, NOT IMPOSSIBILITY"*. My r2 Low 8 (the mutation-name attribution) and Low 9 (the
   count narrative in `check-plan-code.py`) are likewise properly closed; the narrative now carries
   the full chain `43 → 47 → 49 → 52 → 56 → 61` beside the pinned 732.

7. **`--mutate .`** — see the note at the end of this document.

---

## ⟳ Thrashing — my own determination, not an inheritance

**I agree with the verdict and reject the reasoning.** Round 3 is **not** thrashing, the architecture
review should **not** arm, and the retreat should **not** fire — but not for the stated reason, and
the coordinator's own pre-commitment plus the documented rule both point the other way until the
right test is applied.

### The coordinator's reason does not survive round 3's full result

The r3 document rests on: *"Both are prose. Codex says so itself."* That is true **of the codex
half**. It is not true of the round. Origins, per finding:

| Finding | Sev | Fix-induced? | Which fix | Prose? |
|---|---|---|---|---|
| r3 codex Low 1 (message drift) | Low | **yes** | r2 fix 5 | yes |
| r3 codex Low 2 (stale docstring) | Low | **yes** | r2 fix 2 | yes |
| **Medium 2** (empty-derivation ambient case) | Medium | **yes** | r2 Medium 6 | **no — code** |
| **Medium 3** (backlog row stale, 3rd time) | Medium | **yes** | r1 Medium 11 | yes |
| **Medium 5** (`PATH_LIMIT` value + prefix) | Medium | **yes** | r2 Medium 4 | **no — code** |
| **Low 7** (`declared` governs one prong) | Low | **yes** | r2 Medium 6 | **no — code** |
| High 1 (the asymmetry claim) | High | no — pre-existing (r2 coordinator doc) | — | yes |
| Low 6 (`PROSE_FILES` mask) | Low | no — pre-existing | — | no |
| Medium 4 (trajectory table) | Medium | no — new in r3 | — | yes |

**Six of nine round-3 findings are fix-induced**, three of them in code, and all six are in **one
component** — the gate-code derivation and its anti-drift pair. `dev-process.md`'s own words are
*"did the previous fix cause this? If yes for a meaningful share of the round, it is thrashing and
the count is irrelevant"* (`review-method.md:483`). Six of nine is a meaningful share. **On that
sentence alone, round 3 is the second consecutive such round and the condition is met.**

### The test that actually decides it, quoted rather than characterised

`review-method.md:198-202`:

> **⚠ THE SYMPTOM LIST IS A PROMPT, NOT THE TEST. There is one test, and it is this:**
> ### Can a redesign remove it?

Applied per fix-induced finding:

| Finding | Can a redesign remove it? | Class per `review-method.md` |
|---|---|---|
| Medium 2 — ambient case on the empty-derivation branch | **No.** Any shape with two refusals that both return 2 has this mask unless a case distinguishes them. Remedy is one case | **branch-coverage** → fix + exhaustiveness pass |
| Medium 5 — `PATH_LIMIT` value unpinned, bound off by `len(ROOT)` | **No.** Any implementation needs a bound and a case pinning it; the remedy is two cases and one constant | **branch-coverage** |
| Low 7 — `declared` threaded into one prong | **No.** A local parameterisation omission; the fix is one argument | **branch-coverage** (the `promoteIfAbsent` precedent at `:209` — "one stale signature reference; the fix is six words", judged editorial) |
| Medium 3 — backlog counts stale a third time | **No.** A count in prose beside a count a gate checks regenerates forever until a gate owns it | **stale cross-reference** (`:213`) — remedy is a grep, explicitly neither mechanism nor branch-coverage |
| r3 codex Lows 1 and 2 | **No** | **stale cross-reference** |

**Zero mechanism defects. No redesign is owed, so the architecture review does not arm and the
retreat does not fire.** That conclusion is stronger than the coordinator's, because it survives the
three code findings the prose-floor argument does not cover.

### Two corrections to the record that follow from this

1. **"Prose floor" is the wrong label, and the mislabel has a cost.** The prose-floor row in
   `review-method.md:466` prescribes *"Stop reviewing prose. Write the code or the plan, and review
   THAT"* — which is meaningless here: the subject already executes, and round 3's findings were
   found by RUNNING it. The correct labels are **branch-coverage** and **stale cross-reference**,
   whose prescriptions are *"FIX, plus an exhaustiveness pass"* and *"grep for every place that
   stated the old one"*. Both are owed and neither is "stop". The exhaustiveness pass is exactly
   what would have found Medium 2, Medium 5 and Low 6 — three ambient-reason cases that three rounds
   of hunting reached one at a time.
2. **My own r2 hypothesis was half right and I am marking it.** I wrote: *"if round 3's findings are
   'this fix is correct and nothing would notice it breaking', that is evidence for the prose-floor
   reading […] If round 3 finds a repair that produces a wrong answer, that is thrashing."* Round 3's
   findings are the first kind and none produces a wrong answer, so the direction held — but I got
   the *label* wrong in the same way the coordinator did. An unfalsifiable clause is not prose; it
   is branch-coverage, and the difference is whether an exhaustiveness pass is owed. It is.

### The ambient-reason class, counted

The coordinator asked for a case that passes for an ambient reason, noting six had been found on this
branch. I found **three more**: the empty-derivation case (Medium 2), the `PATH_LIMIT` value pair
(Medium 5), and the `PROSE_FILES`/root-`.md` mutual mask (Low 6). That is **nine on one file across
three rounds**, every one found by mutating a clause and watching the suite stay green, and never by
reading. This is the strongest argument in the round for the exhaustiveness pass above: the class is
not converging by sampling.

---

## Verdict

**NOT CONVERGED** — 1 High, 4 Medium, 3 Low.

**THE BRANCH IS SAFE TO MERGE.** Every finding is in a written claim or in a falsifiability gap; none
changes an answer the shipped gate gives, and every repo gate is green except `check-review-rounds`,
which is red only for this document's absence. `schema-gates` is safe to make required **after** this
merges, and the only genuinely new exposure is an infrastructure failure on a docs-only PR.

**What I would not merge without: HIGH 1.** Not because the code is wrong, but because two filed r1
findings inside the `#137` change are open at `HEAD` and a sentence in the review record says they do
not exist — and one of the two things cited to support that sentence is a check no reviewer reported
running. Mediums 3 and 4 are numbers in the repository that are not what was measured; both are a
few minutes. Medium 2 is one case plus one manifest entry, Medium 5 is two cases plus one constant,
and the Lows are cheap. The derivation itself is in better shape than the record describing it.

---

### `--mutate .`, run to completion on this machine

```
$ python3 scripts/check-plan-code.py --mutate .
[47/47] re-control scripts/peer-sites.py
OK — delivered scripts mutated: 47 file(s), 732 mutation(s), 732 killed, 732 attributed to the
     case each names, 0 survivor(s)
rc=0
```

Independently reproduces codex's r3 figure at this commit, on Python 3.14 where codex's run was its
own. ⚠ **What that green does NOT cover, which is the point of Medium 2 and Medium 5:** `--mutate .`
measures only the 61 entries the manifest declares. `if not derived:` has **no entry**, and
`PATH_LIMIT`'s **value** has none either (the one entry there deletes the clause). A 732/732 result
is evidence about the manifest, not about the file — the 35-mutation clause sweep in item 4 is what
reads the file, and it is where the six survivors came from.

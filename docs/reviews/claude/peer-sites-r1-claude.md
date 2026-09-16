# peer-sites — round 1, Claude half

**Subject:** branch `peer-sites`, commit `52010914` (`git diff master...peer-sites`, 7 files, +614/-2).
**Verdict: NOT CONVERGED.** 1 Blocking, 4 High, 4 Medium, 5 Low.

**The central claim is false in both directions, and I measured both.** The docstring
(`scripts/peer-sites.py:29-33`) and the commit message both assert that asking for *peers within a
bounded container* has **no false positives by construction** and therefore *"prints 2-4 lines"*.

Replayed over the last **200 master commits** (138 with python changes, 362 python file-diffs):

| measured | value |
|---|---|
| containers emitted | **73** — 61 `exits`, 12 `branches`, **0 `except`** |
| of the 12 `branches`, the `if ok: … else: print("[FAIL]")` false positive | **4** |
| commits emitting nothing at all | 96 of 138 (70%) |
| loudest commit | **32 lines** (against a claim of "2-4") |
| containers whose own output block is ≥ 9 lines | 10 |
| partially-touched containers where the edit landed in an arm **body** | **79 silent**, 5 spoken |

So: the false positives are real and systematic (H3), the volume claim is wrong by an order of
magnitude at the tail (L1), and the detector is blind to the commonest edit shape there is — a fix
*inside* one arm — because a member is recorded as a *line* and not a *range* (H1). The `except`
shape, one of the three the design is built on, fired **zero** times in 362 file-diffs.

The volume result, in fairness, **supports** the design: 70% of python-touching commits produce
nothing, which is the property that makes an always-on advisory readable. It is the claims around
it that need to come down to what was measured.

⚠ **PROCESS — THE TREE MOVED UNDER THIS REVIEW.** `git status --short` was empty at start. By the
time I finished measuring, `scripts/peer-sites.py` (447 → 520 lines) and
`scripts/check-fixture-variation.py` were modified in the working tree with comments citing
`r1 BLOCKING` / `r1 High` / `r1 Medium`, and `docs/reviews/verdicts/peer-sites-r1-codex.verdict.json`
had appeared. Every measurement below was therefore **re-run against a pinned copy of the committed
blob** (`git show 52010914:scripts/peer-sites.py`, md5 `e4d70ddbc9a1c55cf5a4c87f9905368b`, 447
lines, 32/32). This is `review-method.md:54-55` — *neither half is committed until both finish* — with
the fixes taking the place of the commit: the first half's grade leaked into the tree the second
half was reading. See P1.

---

## Blocking

### B1 · `else:` + a nested `if` is fused into the enclosing chain, so a member is offered that is not a peer — the exact thing "bounded by construction" forbids

`scripts/peer-sites.py:117-131` (`_if_chain`) walks `orelse[0] is If` as an `elif`. An `elif` and an
`else:` containing an indented `if` produce the **same AST**, so the two are indistinguishable
without reading `col_offset`.

Measured against the pinned blob:

```
 2: def f(x, y):
 3:     if x:
 4:         return 1
 5:     else:
 6:         if y == 1:          <- a container of its own, not an arm of line 3's chain
 7:             return 2
 8:         elif y == 2:
 9:             return 3

report(src, touched={8}) ->
  if/elif chain: you changed 1 of 3 branches
      :3      if x:            <- NOT a peer of line 8
      :6      if y == 1:
    > :8      elif y == 2:
```

This is Blocking not because of the miscount but because of what it costs: the design's whole
licence to print unconditionally is *every member is legitimately in scope*. A fused container has
a member that is not, and the reader has no way to tell which output is which.

**Falsifier:** `containers` reports two separate `branches` entries — `[3]` (dropped, one arm) and
`[6, 8]` — for the source above.

**Siblings — searched.** I asked whether the same AST ambiguity appears anywhere else in the file.
It does not: `_if_chain` is the only place an `orelse` is interpreted, and the `elifs` set at
`:82-84` uses the *same* predicate, so both are wrong together and a single `col_offset` test fixes
both.

**Reach, measured, because severity should not rest on my imagination: 0 occurrences** of `else:` +
a lone nested `if` across all 117 python files in the repo today. So this has never fired and
cannot fire on the current tree. **I am still filing it Blocking, and the reason is the claim, not
the reach** — `:29-33` licenses printing unconditionally *because* membership is decidable, and a
counterexample to decidability is a counterexample to the licence whether or not the corpus
contains one. If the project prefers severity to track reach, downgrade it to High; the fix is the
same either way and it is one line.

(The working tree already contains a `_is_elif` fix labelled `r1 BLOCKING`. I reached this
independently — see the PROCESS note — and the reach measurement is the part I would add to it.)

---

## High

### H1 · A member is a LINE, not a RANGE — so the tool is silent whenever the edit lands anywhere but the member's head line

`scripts/peer-sites.py:91` records `n.lineno` for a return; `:95` records `h.lineno` for a handler;
`:125-130` records the arm's head line. `report:194` then tests `m in touched` — exact equality.
Every real edit that lands on the line *below* the head is invisible.

Measured on the pinned blob:

| shape | edit lands on | result |
|---|---|---|
| `except OSError:` / `except ValueError:` | the handler **body** | `report(...) -> []` |
| 4-arm `if/elif/elif/else` | an arm **body** | `report(...) -> []` |
| `return (\n  "the value you edit"\n)` | the **value** line | `report(...) -> []` (touching `return` speaks) |

Replayed over real history, counting only containers that were *partially* touched in an arm body:

```
                                               60 commits   200 commits
peer-sites SPEAKS  (head line also touched):        1             5
peer-sites SILENT  (body only):                    31            79    (77 branches, 2 except)
```

One of the silent ones is `307423f1 scripts/check-plan-code.py` — **3 of 6 arms of a six-arm `elif`
chain edited, nothing said.** That is the tool's own advertised job.

The corpus for the multi-line-return half: **136 multi-line value-returns across 34 scripts** in
`scripts/` alone (`check-banner-armed.py` 16, `gen-dashboard.py` 13, `gen-backlog-page.py` 12,
`explainer-serve.py` 11). This is why the `except` shape reported **zero** containers in 362 python
file-diffs while `exits` reported 61: a `return` edit usually touches the `return` line, a handler
fix never touches the `except X:` line.

**Falsifier:** membership becomes a `(start, end)` span and `hit` becomes range intersection; the
three cases above then speak.

⚠ **The in-flight fix in the working tree is right about `_span` and wrong about the arm bodies,
and the wrong half is stated as measured.** The uncommitted `_if_chain` docstring says a whole-arm
member would mean *"any edit anywhere inside it would mark every member touched, so the
partially-touched filter could never fire."* Arms are **disjoint** ranges, so that does not follow.
Measured over the same 119 file-diffs with whole-arm membership: **16 partially touched, 44 fully
touched** — the filter fires 16 times where the shipped rule fires 1, so *"could never fire"* is
false. The 44 are a real cost and worth weighing; the sentence as written is not a measurement.

**Siblings — searched, and this IS the sibling finding.** I found it first on `except` handlers,
then asked the branch's own question — *another SITE doing the same job?* — and checked the other
two shapes. All three record a head line. The root cause is one line (`m in touched` at `:194`),
not three. I then asked *another LEVEL?* and found the multi-line-return case, which is the same
defect one nesting down.

### H2 · `--diff REF` is a two-dot diff, so it attributes master's changes to the branch

`scripts/peer-sites.py:228` (`git diff --name-only <ref>`) and `:173` (`git diff -U0 <ref> -- path`)
both compare **ref against the working tree**, not against the merge base. The usage line at `:4`
says *"peers of everything a branch touched"*, and the output says **"you changed"**.

Measured in a throwaway git repo outside the review tree (`scratchpad/ps/sandbox`), with the pinned
blob as `scripts/peer-sites.py`:

```
branch `feature` touched ONLY other.py;  master then edited app.py

$ python3 scripts/peer-sites.py --diff master
── app.py ───
handle(): you changed 1 of 3 exits
    :3      return "one"
  > :5      return "two"          <- changed by MASTER; this branch never touched it
    :6      return "other"

$ git diff master...feature --name-only
other.py
```

This is the repo's own recorded failure shape — *a green check says nothing about the branch BASE*.

**Siblings — searched, by grepping every `subprocess` git-diff call in `scripts/`.** Two other
guards do exactly this job and **both already use three-dot**:
`scripts/check-dashboard-entry.py:1277-1279` (`f"{base}...HEAD"`, both the name list and the `-U0`
patch) and `scripts/check-review-decision.py:622` (`f"{args.base}...HEAD"`). `peer-sites.py` is the
only two-dot caller in the directory, so this is not an open question in this repo — the neighbours
answer it.

**Falsifier:** the sandbox invocation above prints nothing.

### H3 · False positives exist, are systematic, and recur — the "no such thing as a false positive" claim is refuted

Of the **12** `branches` containers emitted over 200 commits, **4 are one idiom** (and all 4 are in
the 60-commit window too, so the class is current, not historical):

```
d29898c6  scripts/check-paid-caller-arrival.py     scripts/check-roadmap-consistency.py
d29898c6  scripts/check-test-counts.py             756c41fa  scripts/explainer-serve.py

if/elif chain: you changed 1 of 2 branches
    :495    if want == got:                 <- the peer offered
  > :498    print(f"  [FAIL] {name}: …")    <- what was actually changed
```

The commit changed the failure-diagnostic format in eleven guards. The "peer" is the *success*
branch of a two-arm self-test helper. There is no version of that review question a reader answers
with anything but "no". It is not incidental — it is the single most common two-arm shape in this
codebase, and it fired four times in one sample.

**Rate, stated honestly because it is sample-dependent: 4 of 12 `branches` containers (33%), 4 of
73 containers overall (5.5%).** The rate is the weaker half of the finding. The strong half is that
the class is *systematic* — it is the single most common two-arm shape in this codebase, it fired
four times in four different guard files, and no reader will ever answer its question with anything
but "no". A claim of *zero by construction* is refuted by one instance; this is four, reproducible.

**Falsifier:** run the replay over 200 commits and get zero `1 of 2 branches` reports whose touched
member is a `[FAIL]` print.

**Siblings — searched.** I asked whether the same class exists in the `exits` shape, since that is
where 61 of the 73 containers came from. Over the 200-commit corpus I found **none** of the shape I
expected (a small container whose only untouched peer is a `CANNOT RUN` / `--self-test` / bare-`rc`
guard clause): 0 of the 21 containers with ≤3 members. On the 60-commit dump two are arguable
(`_hook_awk`'s `CANNOT RUN` return, `_timeout_on_the_mutated_run`'s stub return) but I would not
call either a false positive. **The `exits` shape is sound; the `branches` shape is where the
noise is**, which matters for the fix: narrowing `_if_chain` costs nothing the experiment measured.

### H4 · The two new `EXEMPT` entries rest on a premise I measured to be false

`scripts/check-fixture-variation.py:542-553` exempts `changed_lines.ref` and `changed_lines.path`
(reason block `:542-549`, entries `:550-553`) because *"exercising it with VARIED refs and paths
would require a real `.git`, which the mutation harness's staged tree does not have."*

The sub-claim about the harness tree is **true** — `HARNESS_TREE` (`check-plan-code.py:168`) stages
`scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`, `.github/…`, and no
`.git`. The premise built on it is **false**, because this guard compares **argument source text**,
which its own docstring says at `:56-58`.

Measured — one extra case, in a directory with no `.git` at all:

```python
case("a second bad ref, a different path — still CANNOT RUN",
     changed_lines("HEAD~999999", "scripts/does-not-exist.py"), None)
```

```
analyse(shipped_src,  exempt={}) -> 2 findings  (changed_lines.ref, changed_lines.path)
analyse(src + case,   exempt={}) -> 0 findings  (the exemptions are NOT needed)
run in a temp tree, .git present? False  ->  33/33 passed, rc=0
```

The commit message repeats the same false premise: *"no case could vary the parameters without a
real .git — which the harness tree deliberately lacks."* The **split** of `parse_hunks` out of
`changed_lines` was a good change for its own reasons; the reason recorded for it is not the reason.
By the branch's own standard — an exemption resting on a false premise is worse than none.

**Siblings — searched.** I parsed every reason string in the `EXEMPT` dict looking for others that
lean on an absent world (`.git`, harness, temp, ambient, filesystem, network). Exactly one other:
`check-plan-code.py:run_suite_parts.d`, whose reason is *"a second directory would test the tempfile
module, not this function"* — a different and sound argument. No sibling defect.

### H5 · The branch commits its own headline defect: the ratcheted `len(rets) > 1` has two unratcheted siblings, and the tool is silent about them

The author found that `len(rets) > 1 → > 0` was invisible through `report` (a one-member container
is fully touched by definition), moved the claim to `containers`, and shipped manifest entry 1 for
it. The identical expression appears twice more in the same function, eight lines apart:

```
scripts/peer-sites.py:92    if len(rets) > 1:                                    <- ratcheted
scripts/peer-sites.py:94    if isinstance(node, ast.Try) and len(node.handlers) > 1:   <- NOT
scripts/peer-sites.py:98    if len(chain) > 1:                                   <- NOT
```

Measured by mutating a copy of the pinned blob (control 32/32):

```
SURVIVED   containers: a try with ONE handler becomes a container      32/32 passed
SURVIVED   containers: a chain of ONE arm becomes a container          32/32 passed
```

And the point that matters: **asked about its own line 92, `peer-sites.py` says nothing.**

```
report(peer-sites_src, touched={92})    -> SILENT
report(peer-sites_src, touched={92,93}) -> SILENT
```

Three sequential `if` statements are not one of the three shapes, so the mechanism built to stop
*fix the instance, miss the sibling* does not see the instance of that failure in its own source.
That is not an argument against shipping it — it is an argument that the docstring's *"3 of 6 are
mechanical"* is the ceiling for a hand-picked sample, not a rate.

**Siblings — searched, and this finding IS a sibling sweep.** I ran 13 hand-written mutations
against a copy of the pinned blob. **6 survived** the 32-case suite:

| survivor | why it matters |
|---|---|
| `len(node.handlers) > 1 → > 0` | sibling of manifest entry 1 |
| `len(chain) > 1 → > 0` | sibling of manifest entry 1 |
| bare `return` counts as a value-returning exit | the "value-returning" word in the contract |
| `report`'s `seen` dedupe removed | see M1 — it is dead code |
| `-U0 → -U3` in `changed_lines` | see M2 |
| `main --diff` CANNOT RUN path → `return 0` | see M3 — the project's cardinal rule |

Reproduce: `scratchpad/ps` mutation probe, control proved green first, each mutation applied to a
copy outside the repo.

---

## Medium

### M1 · `report`'s `seen` dedupe is dead code, and `_if_chain`'s docstring credits it with a job it does not do

`scripts/peer-sites.py:205-208` keys on `(kind, tuple(members))`. `_if_chain`'s docstring
(`:121-123`) says nested arms are *"filtered by the dedupe in `report`"* — they are not: a nested
arm's member tuple is a **subset**, therefore a different key, therefore not deduped. The thing that
actually filters them is the `elifs` set at `:82-86`, which the same file explains correctly at
`:78-81` (*"Deduping on the member tuple does not help — the tuples genuinely differ"*). Two
adjacent comments in one file give opposite accounts of the same mechanism.

Measured: across **117 python files / 869 containers**, duplicate `(kind, members)` keys: **0**. The
mutation that removes the dedupe survives 32/32.

**Falsifier:** a source file where two distinct containers of the same kind have identical member
lists. I could not construct one that `containers` can emit.

**Siblings — searched.** I grepped the file for other claims about a mechanism's effect and checked
each against a mutation: the `elifs` skip (`:82`) is real (manifest entry 5 kills it), the two
`report` guards are real (entries 3 and 4), the `_own_nodes` scope skip is real (entry 2). `seen` is
the only one whose stated effect is unmeasured, and the only one whose removal is invisible.

### M2 · `parse_hunks` is documented as a reusable pure rule but is only correct for `-U0`, and answers confidently on a shape it cannot read

`scripts/peer-sites.py:134-160` derives touched lines from the **header range** alone. Measured on
the pinned blob:

```
"@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n"     -> {1, 2, 3}    (one line changed; two are context)
"@@@ -1,2 -1,2 +9,2 @@@\n"              -> {9, 10}      (a combined diff, a different grammar)
```

The sole caller passes `-U0` (`:173`), so the live path is right today. But the docstring at
`:136-142` frames this as the **RULE separated from the FETCH** precisely so it is reusable, and
six of the thirty-two cases exist to test it in isolation. A pure rule whose contract holds only for
its current caller's flags is the landmine the split was meant to remove. The `@@@` case is worse
than wrong: it is a plausible number for a shape the parser has no grammar for, where silence is the
correct answer.

The other edges I probed are **fine** and I am recording them so the next reviewer does not repeat
the work: `@@-1 +7 @@` (no space) → `{7}`; CRLF → `{7}`; a section heading containing `+` after the
second `@@` → correct; `--- /dev/null` preamble → correct; `@@ -1 +0,0 @@` → `set()`; an *added*
content line that itself looks like a hunk header (`+@@ -1 +999 @@`) → correctly ignored.

**Falsifier:** `parse_hunks("@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n") == {2}`.

**Siblings — searched.** I asked whether any other pure rule in this file has a contract narrower
than its docstring claims. `containers` and `report` are genuinely world-free (asserted by the two
`_src_of` cases at `:432-435`). `changed_lines` is the shell and is honest about it. No sibling.

### M3 · `main --diff` prints CANNOT RUN and then exits 0, and nothing proves otherwise

`scripts/peer-sites.py:240-244`: when `changed_lines` returns `None` for a file, the loop prints
`CANNOT RUN — … NOT CHECKED.` to stderr and **continues**; `:255` returns 0 regardless. A caller
reading the exit code sees a clean advisory run over a file set that was partly not examined.

The `--diff` entry point's own refusal path (`:231-233`, `return 2`) is **unratcheted**: replacing
it with `return 0` survives 32/32. No case in the suite drives `main` at all, which is also why
`check-fixture-variation` does not examine `main`'s parameters — the repo has been here before
(`check-fixture-variation.py:79-81`, r7 B1: *"this file JOINED its own population once `main`'s
verdict path was cased"*).

The docstring's *"always exits 0 on a well-formed run"* is a fair defence for the advisory design.
A run in which git could not answer for some files is not a well-formed run.

**Falsifier:** `--diff` over a tree where one changed `.py` file cannot be diffed returns 0.

**Siblings — searched.** The `--site` path (`:257-265`) *does* return 2 on bad input, and that is
also uncased. Both entry points are uncovered; one is silently wrong, one is right by luck.

### M4 · The stated BOUNDS are incomplete, in the one section whose whole claim is that they are stated

`scripts/peer-sites.py:35-38` is headed *"WHAT IT CANNOT SEE, STATED RATHER THAN DISCOVERED LATER"*
and names exactly two blind spots: prose clauses and encoding levels. Three more, measured:

1. **Anything that is not Python.** `main` filters `p.endswith(".py")` (`:234`). This repo's product
   is 21,923 lines of `.ts`/`.tsx` under `lib app components worker`. (In fairness: **0 of the last
   60 master commits** touched a `.ts`/`.tsx` file — 39 touched `.py`, 21 touched neither — so the
   scope is defensible for current work. It is the *silence* about it I am filing.)
2. **An edit inside an arm body** (H1).
3. **An edit to a multi-line return's value** (H1).

The two cases at `:423-425` assert the two stated blind spots, which is good practice; there is no
case asserting the unstated three, because they were not known.

**Falsifier:** the section names non-Python source, arm bodies, and multi-line values.

**Siblings — searched.** I checked the same claim where it is repeated: the commit message
(*"IT CATCHES 3 OF 6 AND THE DOCSTRING SAYS SO"*), `docs/review-method.md:66-72`, and
`docs/dashboard-entries.md:9548`. All three carry the same two-item list, so a fix must land in four
places. `docs/review-method.md:69-70` is the one that matters most — it tells reviewers what the script
covers.

---

## Low

- **L1 · `:31` "prints 2-4 lines" is false.** Measured over 200 commits: 96 of 138 python-touching
  commits silent, and the non-silent tail runs 3 … 19, 20, 21, 30, **32** lines. **10 containers
  print a block of 9+ lines on their own** (`do_GET()` with 13 exits printed 14). The claim is the
  load-bearing justification for *"can be read every time"*; the real distribution still supports
  that conclusion, so fix the number, not the design.
  *Siblings:* the same figure is in the commit message; not in `review-method.md`.
- **L2 · `try/except/else/finally`: `else` and `finally` are never members**, and a `try` with one
  handler plus an `else` is not a container at all. Defensible, but unstated. **`match`/`case` is
  not a shape** — a `match` whose arms do not return yields `containers(...) == []`. Measured: **0
  `match` statements in the repo today**, so this is latent, not live. The docstring's stated reason
  for the short list (*"a shape whose membership is a judgement call"*) does not cover `match`,
  whose arms are syntactically enumerated — so the omission has no recorded reason.
  *Siblings:* I enumerated the AST statement types that bound an enumerable set — `If`, `Try`,
  `Match`, `FunctionDef` exits — and `Match` is the only one absent.
- **L3 · the `else` arm is reported at its first statement, not at `else:`.** `_if_chain:130`
  appends `cur.orelse[0].lineno`. In the suite's own fixture the chain is `[3, 5, 7, 10]` where
  `else:` is line 9 and `d()` is line 10, so the printed body text for that member is `d()`.
  *Siblings:* the `except` shape uses `h.lineno`, which *is* the `except` keyword line — so the two
  shapes disagree about what a member's line means.
- **L4 · the footer count is wrong for deleted files.** `:251-252` prints
  `"… in {len(paths)} changed python file(s)"`, but `:238-239` skips paths that no longer exist.
  A branch that deletes a `.py` file overstates what was examined.
- **L5 · manifest entry 7's attribution is only true outside the harness.** `"a git failure is
  spelled the same way as a clean diff"` is killed by the case *"a bad ref reports CANNOT RUN"* —
  but in the staged tree (no `.git`) the branch is reached because there is **no repository**, not
  because the ref is bad. The kill is real; the case name describes a cause that does not obtain
  where it is measured. This is the same fact as H4, seen from the other side.
  *Siblings:* I read all seven entries. The other six are honest — each names the mechanism it
  removes and the case it reddens, and I confirmed each anchor exists verbatim in the pinned blob.

---

## `containers()` — what I probed and found CORRECT, recorded so round 2 does not repeat it

All against the pinned blob. Each of these is a shape the brief asked me to attack; each behaves.

| shape | result |
|---|---|
| `async def` | `('exits', 'a()', …)` — `AsyncFunctionDef` is handled at `:88` |
| decorated function | member lines are the returns, not the decorators — `lineno` is the `def` |
| lambda inside a function | the lambda's body is excluded from the enclosing exits (`_own_nodes:109`) |
| comprehension | no spurious container; it cannot hold a `return` |
| walrus in `if`/`elif` tests | chain read correctly; the `exits` container compensates for the body-blindness here |
| nested `try` (inner 2 handlers, outer 1) | only the inner is a container — correct |
| class method | `m()` is its own exits container |
| `try` nested inside an `if` arm | three containers, all correctly scoped |
| `parse_hunks` edges | no-space `@@`, CRLF, a `+` in the section heading, `--- /dev/null`, `@@ -1 +0,0 @@`, and an *added* content line that looks like a hunk header — all correct (see M2 for the two that are not) |
| the two stated blind spots | asserted by cases at `:423-425`, and both hold |

The `_own_nodes` nested-scope skip and the `elifs` head-dedupe — the two recent repairs the brief
singled out — are **both correct and both ratcheted**. My only finding against them is B1, which is
a third case neither was written for.

---

## The seven manifest entries (brief item 5) — all honest, verified independently

Against a copy of the pinned blob in a directory with no `.git` (control **32/32**, proved green
first), each entry: anchor occurs **exactly once**, mutation goes **red**, and the red arrives
**via the case the entry names**.

```
RED anchor=1 via-named-case=True   a single exit is treated as an enumerable set
RED anchor=1 via-named-case=True   a nested scope's exits are counted as the outer function's
RED anchor=1 via-named-case=True   a container the diff touched ENTIRELY is advised on anyway
RED anchor=1 via-named-case=True   a container the diff never touched is advised on anyway
RED anchor=1 via-named-case=True   one if/elif chain is reported once per arm
RED anchor=1 via-named-case=True   unparseable source raises instead of refusing
RED anchor=1 via-named-case=True   a git failure is spelled the same way as a clean diff
```

The only attribution I would qualify is the last one (L5). What the manifest does **not** cover is
in H5: six further mutations that survive, two of them siblings of entry 1.

---

## The `review-method.md` step (brief item 6)

**It is actionable, and it is the best part of the branch.** `docs/review-method.md:59-76` gives a
reviewer three concrete questions (LEVEL / SITE / COPY), an explicit example of an acceptable
answer, and — the part that makes it work — *"not searched is an acceptable answer; silence is
not"*, which converts an unbounded obligation into a one-line statement. I applied it to myself
throughout this review and it changed the output: H1, H5 and M4 each started as a single instance
and became a class only because the step forced the second question.

Two observations rather than findings:

- **Nothing enforces it.** `scripts/check-review-rounds.py` checks that both halves exist; no guard
  reads a round document for per-finding sibling statements. That is probably correct — the check
  would be a keyword search over prose — but it means the step is in the same category as the
  2026-08-27 memory rule the branch says was "spent".
- **`:69-70` tells reviewers the script "answers those three mechanically."** Per H1 and H2 it answers
  them on a narrower set than that sentence implies, and per H2 it can answer with a line the branch
  did not change. The sentence should survive the fixes, but it should not ship ahead of them.

---

## Process

### P1 · The branch's own review protocol was broken while this review ran (High, process)

`review-method.md:54-55` — *"Neither half is committed until both finish — a committed first half
leaks its grade to the second through `git log` and the diff."* The fixes were not committed, but they
were **written into the working tree** that the second half reads, carrying `r1 BLOCKING` /
`r1 High` / `r1 Medium` labels. I discovered this only because a `grep -n` returned line 473 of a
file I had read as 447 lines. Any reviewer that had not pinned the blob would have measured a mix.

The rule's falsifier should be the **tree**, not the commit: no writes to the subject while a half
is in flight. This is the same shape as the `docs/reviews/` no-legitimate-writes zone already
recorded in `docs/plugins.md`.

*Consequence for this review:* every number above is against the pinned blob. I did **not** review
the working-tree changes, except to note in H1 that one of their stated rationales is measurably
false — which is the kind of thing this rule exists to let a reviewer say before it is committed.

### P2 · Nothing runs `peer-sites.py` (High)

`grep -rn peer-sites` over the whole repo returns: the script, its manifest, three ratchet
registrations (`check-plan-code.py`, `check-fixture-variation.py`, `check-selftest-counts.py`), and
two prose mentions (`review-method.md:69`, `dashboard-entries.md:9548`). **No hook, no CI step, no
gate, no skill invokes it.** `check-ratchet-contract.py` does not cover it — it discovers 36 guards,
all named `check-*.py`, and correctly excludes this one because it is not a gate.

The branch's premise is *"having the rule did not help, so this is the attempt at a mechanism."* A
script a reviewer must remember to run is a rule with an executable attached. The cheapest real fix
is one line in whatever already runs at review time; the honest alternative is to stop calling it a
mechanism.

*Falsifier:* a caller exists in `.claude/hooks/`, `.github/workflows/`, or a skill.

### P3 · `--mutate .` against the review subject: CANNOT RUN from the repo

Per *"cannot run is a FAILURE, never a pass"*: I started `python3 scripts/check-plan-code.py
--mutate .` at the top of this review, and the tree changed underneath it (P1), so its result
describes neither `52010914` nor any coherent tree. I therefore built a clean export
(`git archive 52010914` + `node_modules/typescript` + `.claude/hooks`, verified
`md5(scripts/peer-sites.py) == e4d70ddbc9a1c55cf5a4c87f9905368b`, no `.git`) and ran
`--mutate <export>` against it. **Result recorded below.**

```
$ python3 <export>/scripts/check-plan-code.py --mutate <export>
OK — delivered scripts mutated: 47 file(s), 696 mutation(s), 696 killed,
     696 attributed to the case each names, 0 survivor(s)
EXIT=0
```

**696/696/696/0 against the committed tree — matches the commit message's claim.** (The run I
started from the repo also reported 696/696/696/0, but it straddled the working-tree edits, so I am
citing the export.) ⚠ A green sweep here is not evidence against H5: the harness proves every
*declared* mutation kills via its named case, and H5 is about six mutations that were never
declared.

Green against the committed tree, run individually and confirmed:

| check | result |
|---|---|
| `peer-sites.py --self-test` | **32/32**, rc=0 |
| `check-fixture-variation.py` | OK — 538 parameters / 52 files; rc=0 · `--self-test` **67/67** |
| `check-selftest-counts.py` | 40 scripts, every count verified by running it; rc=0 · `--self-test` **18/18** |
| `check-docs.py` | Documentation integrity OK; rc=0 · `--self-test` **13/13** |
| `check-ratchet-contract.py` | 36 guards, contract OK; rc=0 · `--self-test` **41/41** |

---

## What I did not attack

- `gen-dashboard.py --self-test` — not run; the dashboard entry itself I read and quote in M4.
- The working-tree r1 fixes — out of scope by design (P1), except the one rationale in H1.
- The Codex half — not read; `docs/reviews/verdicts/peer-sites-r1-codex.verdict.json` exists but I
  did not open the review, so any overlap above was reached independently.

## Verdict

**NOT CONVERGED.** B1 and H1 together mean the two claims the design rests on — *no false positives*
and *the containers are complete* — are both measurably wrong on this tree, and H2 means the entry
point can report a change the branch did not make. H5 is the one I would not want lost: the branch
built to stop *fix the instance, miss the sibling* shipped that exact defect in the function that
defines its three shapes, and its own tool is silent about it.

None of this argues against the idea. The volume measurement **supports** it: 96 of 138
python-touching commits produce nothing at all, which is the property that makes an always-on
advisory readable, and the `exits` shape — 61 of the 73 containers — I could not fault. The claims
around it are what need to come down to what was measured, and the `branches` shape is where the
work is.

---
---

# ADDENDUM — subject versions, and a re-measurement on the moving tree

The coordinator flagged mid-review that the tree had moved twice. It moved a **third** time while I
was answering. Everything above and below is now pinned to a named, hashed subject.

## The three subjects

| tag | what | `scripts/peer-sites.py` | suite | manifest |
|---|---|---|---|---|
| **`52010914`** | HEAD, committed, pre-fix | md5 `e4d70ddbc9a1c55cf5a4c87f9905368b`, 447 ln | 32/32 | 7 |
| **`T1000`** | working tree as of my first snapshot | md5 `85d5926b9107ed0fe422d977efeb2cb4`, 593 ln | 42/42 | 9 |
| **`T1015`** | working tree now (= live at time of writing) | md5 `c867c86ef445bf923b5f49da3a3ef237`, 793 ln | 53/53 | 16 |

Nothing is committed; HEAD is still `52010914`. Copies of all three are outside the repo; every
number below names which one it came from.

## Per-finding subject and current status

| # | measured against | status on **T1015** |
|---|---|---|
| B1 `_is_elif` | `52010914` | **CLOSED** — fixed *and* ratcheted (dies 40/42 via its named case). Independently reproduced by me before I saw your note. |
| H1 `_span` / range intersection | `52010914` | **HALF CLOSED.** The multi-line-exit half is fixed and ratcheted. The **arm-body half is open** — see N6. |
| H2 two-dot `--diff` | `52010914` | **CLOSED** — `_merge_base`, and the comment now states why two-dot-against-the-base is right here and three-dot is not. I agree with that reasoning. |
| H3 false positives | `52010914`, re-measured on `T1000` | **CLOSED as a claim** — docstring now carries the measured numbers. The 4 `[FAIL]`-idiom containers still fire (unchanged on T1000 and T1015); that is now a stated cost, not a false claim. |
| H4 `EXEMPT` false premise | `52010914` | **CLOSED** — both entries deleted, parameters varied. ⚠ but the fix opened **N7**. |
| H5 unratcheted siblings | `52010914`, re-probed on `T1000` and `T1015` | **CLOSED** — `len(handlers) > 1`, `len(chain) > 1` and bare-`return` all now die via named cases on T1015. |
| M1 dead `seen` dedupe | `52010914`, re-measured on `T1000` | **CLOSED** — deleted. See Q2. |
| M2 `parse_hunks` `-U3` / `@@@` | `52010914` | **CLOSED** — body-parsing + `@@@` refusal, both ratcheted (`-U0→-U3` now dies 41/42). ⚠ but the rewrite hollowed out an older falsifier — **N3**. |
| M3 `--diff` returns 0 after CANNOT RUN | `52010914` | **CLOSED** — unchecked files are remembered, not just printed. |
| M4 unstated bounds | `52010914` | **PARTLY** — the two numeric claims are corrected; non-Python, arm bodies and the else's 2nd statement are still unstated. |
| L1 "2-4 lines" | `52010914`, re-measured on `T1000` | **CLOSED** — replaced with the measured distribution. |
| L2 `match` / `try-else-finally` | `52010914`, re-checked on `T1015` | **OPEN** — `ast.Match` occurs 0 times in the script; 0 `match` statements in the repo, so still latent. |
| L3 else-arm line semantics | `52010914` | **SUPERSEDED by Q1** — it is now a span, which makes it a design question rather than a cosmetic one. |
| L4 footer file count | `52010914` | **CLOSED** — `examined` is now counted separately from `len(paths)`. |
| L5 manifest attribution | `52010914` | **MOOT** — the EXEMPT it mirrored is gone. |

## Your two open questions

### Q1 — `_if_chain`'s `else` arm as `_span(cur.orelse[0])`: **it re-creates the tiling problem, for exactly one arm.** Measured on T1015.

```
 3:     if x == 1:            members: [(3,3), (6,9)]
 4:         a()
 5:     else:
 6:         result = compute(
 7:             alpha,
 8:             beta,
 9:         )
10:         cleanup()

 touch  3  (the `if` TEST)              -> SPEAKS
 touch  4  (INSIDE the if arm)          -> SILENT
 touch  6  (the else's 1st stmt head)   -> SPEAKS
 touch  7  (INSIDE the else's 1st stmt) -> SPEAKS     <- the if arm's body is silent here
 touch 10  (the else's 2nd statement)   -> SILENT     <- and the else's own body is silent here
```

**Three different rules for "I edited this arm" in one container.** An `if`/`elif` arm is its test;
the `else` arm is its first statement *whole*; the else's later statements are nothing at all. The
docstring justifies the condition-only choice by saying whole arms would tile — and then makes one
arm whole. That arm is the one with no test, so it is also the one that most often holds a big
statement.

**Your own fixture, and it is worse than a miscount.** Touching line 8 (`elif y == 2:`, the *inner*
chain's test) produces two reports, and the outer one is:

```
if/elif chain: you changed 1 of 2 branches
    :3        if x:
  > :6-9      if y == 1:          <- marked touched; prints a line the user did not change
```

That is **B1 arriving through the range instead of through the AST**: the outer `if x:` is offered
as a peer of an edit that belongs entirely to the nested chain, which is the exact advice `_is_elif`
was written to stop. The printed body text is the member's *first* line, so the reader is shown
`if y == 1:` for an edit to `elif y == 2:`.

**And it can silence the outer container.** Touching `{3, 6}` — the outer test plus the inner test:

```
outer chain members [(3,3), (6,9)]  ->  line 6 falls inside 6-9, so BOTH read as touched
                                    ->  filtered as "fully touched", the outer report VANISHES
```

The docstring's stated fear ("the partially-touched filter could never fire") is realised, confined
to the else arm. **Not correct as it stands.** Options, in my order of preference: (a) represent the
`else` by its **head keyword line** only, restoring symmetry with the tests — which also makes the
member a line the reader can point at; (b) represent *every* arm by its full body and accept that
"all arms touched" means "you rewrote the statement" (measured on `52010914`: that gives 16
partially-touched vs 1, at the cost of 44 silences); (c) keep the span and state the asymmetry in
the docstring. What is not defensible is the current combination of doing (b) for one arm while the
docstring argues against it.

**Siblings — searched.** The same "member = a whole statement" choice exists for `exits` (a return's
span) where it is right — a return *is* the thing you edit — and for `except` where the head-only
choice was made deliberately (N2). So the three shapes now make three different choices, and only
`exits` has a case that pins its choice.

### Q2 — `report()`'s `seen` dedupe: **you deleted it, and the deletion is right.** Measured before it went, on T1000:

```
corpus: 59 files, 437 containers
pairs the dedupe CATCHES (identical member tuple, same kind):        0
pairs it CANNOT catch    (same kind, overlapping but unequal):       0
```

So with ranges it neither fired nor gained a job: equality cannot see overlap, and the corpus has
neither. Removing it survived 42/42 on T1000. Confirmed closed — no further action.

## Confirming what you asked me to confirm

**The B1 and H1 fixes originally shipped with no falsifying case — independently reproduced.** On
`T1000` I mutated `_is_elif` to `return True` and `_span` to `(node.lineno, node.lineno)`; both now
die **40/42 via the case each names**, so the gap is closed. I also probed the *other* direction,
which your note did not mention: `_is_elif → return False` (a genuine `elif` chain split into
singletons) also dies 40/42. Both directions are covered.

## NEW — findings that survive the fixes, all measured on T1015 (control 53/53)

### N1 (Blocking, current tree) · `check-fixture-variation.py` is RED right now, and the H4 fix caused it

```
$ python3 scripts/check-fixture-variation.py        # live tree, md5 c867c86e…
rc=1
✗ peer-sites.py: `main(argv=…)` is passed the SAME value at every call site in the suite
  (1x `['--diff', 'master']`).
```

Deleting the two EXEMPT entries meant adding a case that drives `main`, which pulled `main` into the
guard's field of view for the first time — and its one call site passes one value. Pinned: on
`52010914` `analyse()` reports the two `changed_lines` findings and **does not examine `main` at
all**; on T1015 it examines `main` and reports `main.argv`. The branch does not currently pass its
own gates.
*Siblings — searched:* I re-ran `analyse()` over the pinned T1000 and T1015 sources. `main.argv` is
the only newly-examined parameter, so there is one instance, not a class.

### N2 (High) · the `except` shape still fires zero times, and the decision that causes it has no case

`containers` records a handler as `(h.lineno, _span(h.type)[1])` — the head, deliberately
(`"the handler HEAD, not its body: same tiling problem as an if-arm"`). Mutating it to the
handler's full body **survives 53/53**. So the decision is unfalsifiable in either direction, and it
is the reason the shape is inert: replayed over 200 master commits (362 python file-diffs),
`except` produced **0** containers on `52010914`, **0** on T1000, **0** on T1015, while `exits`
produced 61 → 67 → 67. A handler fix lands in the handler body; it never touches `except X:`.
*Falsifier:* one real commit in 200 where the shape speaks. There is none.
*Siblings — searched:* this is the same root as Q1 and the arm-body half of H1 — three shapes, three
different answers to "what counts as touching a member", and only `exits` has a case pinning its
answer.

### N3 (Medium) · the `parse_hunks` rewrite hollowed out the deletion-guard's falsifier

`cursor = int(start) if (int(count) if sep else 1) else 0` — the `else 0` is the descendant of the
`max(n, 1)` bug the commit message lists as one of the five defects building this found. Mutating it
away **survives 53/53**, and it is now dead by construction: under body-parsing a deletion hunk has
no `+` lines, so it contributes nothing whether or not the cursor is armed.

```
'@@ -4,2 +3,0 @@\n'          -> []
'@@ -4,2 +3,0 @@\n-a\n-b\n'  -> []      (same with the guard removed)
```

The case *"a deletion-only hunk claims no new lines"* still passes, but it can no longer fail for
the reason it names. This is this repo's own *removing a signal hollows out its falsifier*.
*Siblings — searched:* I re-probed every guard inside the rewritten `parse_hunks`. The `-`-line and
context-line rules and the `@@@` refusal all die (41/42 on T1000). The zero-count guard and the
malformed-header reset (N4) are the two that do not.

### N4 (Medium) · a malformed hunk header leaves the cursor armed — real, and unfalsified

`except (IndexError, ValueError): cursor = 0` → `pass` **survives 53/53**, because the only
malformed-header case has no body lines after it. With a preceding valid hunk it is a live
misattribution:

```
'@@ -1,0 +10,2 @@\n+a\n+b\n@@ garbage @@\n+c\n+d\n'
shipped            -> [10, 11]              correct
with the mutation  -> [10, 11, 12, 13]      +c/+d claimed as lines 12,13 of the old hunk
```

*Falsifier:* the two-hunk fixture above as a case.

### N5 (Medium) · `report`'s `>` marker can disagree with its own header

`mark = "  >" if m in hit` → `if m[0] in touched` **survives 53/53**. The shipped behaviour is
right; nothing proves it. Under the mutation, the very shape the H1 fix exists for prints a header
claiming a touched member and marks none:

```
f(): you changed 1 of 2 exits
    :4-6      return (            <- no `>`, though this is the member that was hit
    :7        return "other"
```

*Siblings — searched:* the rest of the output line (the `span` suffix, the 82-char truncation, the
`{len(hit)} of {len(members)}` counts) — the counts die, the marker and the span suffix do not.

### N6 (High, carried) · the arm-body half of H1 is unchanged by the fixes

Re-measured on T1015 exactly as on `52010914`, over 200 master commits:

```
                          52010914   T1000   T1015
arm-BODY edits: SPEAKS         1        5       5
                SILENT        31       79      79      (24 of them 3+-arm chains)
```

The `_span` fix recovered 6 containers, all in `exits` (61 → 67). `branches` is unchanged at 12
because the arms are still their *tests*. `307423f1` editing 3 of 6 arms of a six-arm chain is still
silent. This is the design question behind Q1, not a separate defect — I list it so the count is
not lost.

### N7 (Low) · `_span`'s `None` fallback is unfalsifiable *and* unreachable

`getattr(node, "end_lineno", None) or node.lineno` → dropping the `or node.lineno` **survives
53/53**. Measured over the corpus: `end_lineno` is `None` on **0 of 128,887** stmt/expr nodes in 59
files. The comment claims it prevents a `TypeError` in `report`'s `range()`; the reachable form of
that risk was `h.type` being `None`, which the `if h.type else` already handles. Keep it as
belt-and-braces if you like, but the comment should not present an unreachable branch as a measured
save.

## Verdict on T1015

**NOT CONVERGED**, on N1 alone — the tree is red. Beyond that the substantive open item is one
question, not seven: **what does it mean to touch a member?** `exits` says the whole statement,
`except` says the head, `branches` says the test for three arms and the whole first statement for
the fourth. Q1, N2 and N6 are that one question seen from three sides, and the fix for it should be
a single decision applied to all three shapes, with a case per shape pinning it.

Everything else I filed in round 1 is closed, and I verified the closures rather than taking them.

---

## Late re-check — the tree moved a FOURTH time while this addendum was being written

**`T1030`** = `scripts/peer-sites.py` md5 `cd72ee4fa28a334896a551c20720fe5d`, 836 lines, **59/59**,
16 manifest entries. Plus `.claude/hooks/peer-sites-advisory.sh` (new) and edits to
`docs/review-method.md`, `docs/dashboard-entries.md`, `.claude/settings.json`.

- **N1 is CLOSED on T1030.** `check-fixture-variation.py` now exits **0**. It was genuinely red on
  T1015 (`md5 c867c86e…`, rc=1, `main.argv`) and I stand by the finding against that subject; it was
  fixed while I was writing. Recording both halves because a finding that quietly evaporates is
  indistinguishable from one that was wrong.
- **P2 looks addressed** by `.claude/hooks/peer-sites-advisory.sh`. I have not reviewed that hook —
  it arrived after I finished measuring, and reviewing it would be reviewing a fifth subject.
- **Everything else still stands.** Re-probed against T1030, control 59/59:

```
SURVIVED   N2  except-handler span -> the handler's FULL body            59/59
SURVIVED   N3  parse_hunks zero-count guard removed                     59/59
SURVIVED   N4  malformed header leaves the cursor armed                 59/59
SURVIVED   N5  the `>` marker reverts to exact-line equality            59/59
SURVIVED   Q1  the else arm becomes its head LINE, not its span         59/59
SURVIVED   N7  `_span`'s None fallback removed                          59/59
```

Q1's asymmetry is byte-for-byte unchanged on T1030: the `if` arm's body is SILENT, the else's first
statement is SPEAKS, the else's second statement is SILENT. The outer chain is still filtered away
as "fully touched" when the inner test is edited — only the inner chain reports.

**⚠ A PROCESS NOTE THAT IS WORTH MORE THAN ANY OF THE ABOVE.** Four subjects in one review round,
none committed, each fixing the previous round's findings before the round finished. That is
`review-method.md:54-55` defeated by the working tree rather than by `git log`, and it has a cost
this addendum can measure: **six findings have now survived four consecutive fix passes**, and all
six are the same kind — a *decision* with no case, rather than a bug. Fixes land where a reviewer
pointed; the unfalsifiable choices next to them do not get touched, because nothing red is pointing
at them. A round that ends before the fixes start is what would catch those.

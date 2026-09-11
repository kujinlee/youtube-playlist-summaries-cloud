# Adversarial review — `harness-progress-output` round 5 (Claude half)

**Verdict: NOT CONVERGED.**

**Subject:** `d6f55881` alone. **Scope:** coverage, per the human's explicit decision. I accept the
scoping and did not work outside it — see *On the scoping* at the end.

| | finding | measured |
|---|---|---|
| **B1** | `diagnostic_tail` need not take the TAIL of stdout — no case, no entry | `out[:out_keep]` → **124/124 passed** |
| **H1** | the floor's spare-budget term may read the wrong stream | `window - len(err)` → **124/124 passed** |
| **M1** | the report's stream ORDER is unpinned at three sites | 3 edits, each **124/124 passed** |
| **M2** | six more edges have a case and no manifest entry | each dies in the suite, none in CI's manifest |
| **M3** | a refuted principle is still stated as a rule; two clauses rest on it | both dead — `458/458/458`, asked not assumed |
| **L1–L3** | trailing-space entry; a want that pins length not side; a guard restored by association | — |

**The commit's own numbers all verify** — `--mutate .` re-run: 38 files, 458 mutations, 458 killed,
458 attributed, 0 survivors, exit 0. Every finding is something that run cannot see.

**One sentence, if you read nothing else:** `"S" * 5000` is a stronger-*looking* fixture than the one
r4 replaced and pins strictly less, because a homogeneous string cannot distinguish a head from a
tail — and that is B1.

---

## Proof of subject

```
$ git log --oneline origin/master..HEAD
d6f55881 Round 4: an input far inside the boundary pins nothing, a third time   <-- SUBJECT
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes

$ git rev-parse HEAD
d6f55881b6d21f1943ef88891e4bead6f1424c02

$ git show --stat d6f55881
 docs/dashboard-entries.md                                        |  32 +-
 docs/reviews/claude/harness-progress-r4-claude.md                | 571 +++++
 docs/reviews/coordinator/harness-progress-r4-codex.md            | 104 ++
 docs/reviews/coordinator/harness-progress-r4-codex.verdict.json  |  20 +
 scripts/check-plan-code.py                                       |  67 +-
 scripts/mutations/check-plan-code.json                           |  82 +-
 6 files changed, 863 insertions(+), 13 deletions(-)
```

Executable subject: `scripts/check-plan-code.py`, `scripts/mutations/check-plan-code.json`.
Manifest holds **63** entries for `check-plan-code.py`; `EXPECTED_MUTATIONS` declares **63**; the
declared sum is **458**. Suite declares and runs **124**.

## Method, and the control

Every verdict below is a **measured suite run over a control proved green first**.

- **Control, green:** `python3 scripts/check-plan-code.py --self-test` → `124/124 passed`, rc 0, 3.3 s.
- **Staged control, green:** the probe harness copies `scripts/` into a temp dir, symlinks the other
  four `HARNESS_TREE` members (`supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`),
  redirects `$HOME` into the temp dir, and runs from the tree root. A **no-op edit** through that
  harness gives `rc 0, 124/124 passed`.
  ⚠ My first attempt staged `scripts/` alone and the control came back **red on 3 cases**
  (`every HARNESS_TREE entry is present in the tree this file lives in`, …). Every verdict over that
  tree would have been an artefact — the brief's warning is real and it fired on me.
- Probe harness: `/Users/kujinlee/.claude-tmp/r5-claude-scratch/probe.py`. It refuses any anchor
  that does not occur **exactly once**, so no probe can silently edit two sites or none.
- Attribution rule used throughout is the code's own (`scripts/check-plan-code.py:1138-1139`):
  `[(w, [f for f in fails if w == f]) for w in wants]`, then `len(m) != 1` is *unattributed* —
  exact equality, exactly one red case.

## ⚠ The working tree moved under me, and the findings were re-verified against git

Late in the review `git status` showed `scripts/check-plan-code.py` and
`scripts/mutations/check-plan-code.json` **modified in the working tree** — declaring `126 cases`
and `70` mutations, and citing "r5 H2" and "r5 L2" in new comments. Someone is fixing this review's
findings while it is being written.

Every measurement above was taken before those edits landed (my control was `124/124`, the manifest
63 entries, the declared sum 458, and both full runs reported 458 mutations). But *"a reviewer can
review the wrong subject"* is a failure this project has already paid for, so I did not rely on
that. **I re-ran the three headline probes against the subject commit's bytes taken directly from
git** (`git show d6f55881:scripts/…`), with the working tree's other scripts staged around them:

```
subject d6f55881: check-plan-code.py = 194923 B, manifest = 26655 B
CONTROL — subject commit, unmodified (must be 124/124)   rc=0  124/124 passed
B1 — out[:out_keep] (head of stdout)                     rc=0  124/124 passed
H1 — window - len(err)                                   rc=0  124/124 passed
M3 — max(room - 1, 0) floor deleted                      rc=0  124/124 passed
```

**B1, H1 and M3 reproduce on `d6f55881` exactly.** This review describes that commit, not the
working tree; if the in-flight edits close some of these, that is the next round's evidence, not
this one's.

## Not a re-file

I read all four filed rounds. The closest prior finding to B1/M1 is **r3 H1** (*"M1's swap
RE-CREATES r1 F7's harm for 28 of 38 suites"*), which is about the **concatenation order of the two
streams** and was closed by replacing the concatenation with `diagnostic_tail`. B1 and M1 are about
properties of the *replacement function* — the direction of its stdout slice, and the order of its
own halves and arguments — none of which existed as code when r3 H1 was written. Nothing in rounds
1–4 names a slice direction, an argument order, or the `window - len(out)` operand. I checked the
r1/r2/r3/r4 Claude halves and the four coordinator halves.

---

# Blocking

## B1 — `diagnostic_tail` does not have to take the TAIL of stdout. No case, no mutation, and the harm is the one four rounds were spent on.

`scripts/check-plan-code.py:432-433`:

```python
    return "\n".join(p for p in (err[-err_keep:] if err_keep else "",
                                 out[-out_keep:] if out_keep else "") if p)
```

**Measured.** Change `out[-out_keep:]` to `out[:out_keep]` — the head of stdout instead of the tail —
and the suite is **`rc 0, 124/124 passed`**. Nothing goes red. There is also no manifest entry for
it: I enumerated all 63 entries for this file and not one touches either slice's direction.

The stderr half is *not* in this state, which is what makes the gap legible rather than arguable.
Flipping `err[-err_keep:]` alone gives `122/124`, red via two cases:

```
[FAIL] a CANNOT RUN report says WHY the control died, not just that it did: got (False, False) want (False, True)
[FAIL] a suite that crashes AFTER 800 B of stdout still shows its traceback: got (1, False) want (1, True)
```

Both of those are stderr-content assertions. **Every case in the file that exercises the stdout half
feeds it a string whose head and tail are indistinguishable**, so none of them can see the direction:

| case | stdout fixture | why it cannot see the direction |
|---|---|---|
| `a flooded stderr cannot evict stdout's failure from the window` | `"[FAIL] the one that matters"` (27 B) | fits entirely; `out[:27] == out[-27:]` |
| `...and a flooded stdout cannot evict stderr's traceback` | `"S" * 5000` | homogeneous |
| `both streams flooded, …the stderr half is exactly half the window` | `"S" * 5000` | homogeneous |
| `...and the window never exceeds its budget…` | `"S" * 5000` | homogeneous (asserts a LENGTH) |
| `...and a quiet stderr gives its whole half back to stdout` | `"S" * 5000` | homogeneous (asserts a LENGTH) |
| `...and a whitespace-only stream is dropped…` | `"done\n"` | fits entirely |
| `a suite that crashes AFTER 800 B of stdout…` (`late.py`) | `"S" * 800` | homogeneous |
| `600 B of child stderr cannot push the failure out…` (`flooder.py`) | `"  [FAIL] the value is one"` | fits entirely |

**The harm, measured against the real corpus rather than a fixture.** Using the suite the commit
message itself cites:

```
REAL SUITE check-paid-caller-arrival.py --self-test: rc=0 stdout=16701 B stderr=0 B
simulated RED stdout = 16727 B, stderr = 0 B     (its last line replaced by a [FAIL] line)

--- SHIPPED  out[-out_keep:] ---
  "…✓ an empty ledger is CANNOT RUN, not dormant\n\n  [FAIL] the population is the filesystem: got 14 want 24"
  contains the [FAIL] line?  True

--- MUTANT   out[:out_keep] ---
  'subject: `record_artifact` · production dirs lib/app/worker/… \n         production callers: 0   (commen'
  contains the [FAIL] line?  False
```

And on the crash-after-printing shape with a real traceback (stdout 16,701 B, stderr 166 B):
shipped keeps the tail of stdout (`True`); the mutant does not (`False`), handing the reader
`'DORMAN…'` — the run's banner.

So the mutant deletes the failure from the only diagnostic the harness prints when a control dies,
over **28 of the 38 real suites** (the branch's own figure for suites exceeding 400 B of stdout on a
green run). That is r1 F7's harm restored in full, and the suite reports `124/124 passed`.

**This is the class the round exists for, in the function the round was about.** It is r3 B1 and
r4 B1's diagnosis one step further out: r4 B1 was a fixture whose *magnitude* sat inside the
boundary (41 characters proving a 41-character property for an 84-character corpus); this is a
fixture whose *shape* — a homogeneous run of one character — makes the property undetectable at any
magnitude. Tenth instance. `"S" * 5000` is a stronger-looking input than `"S" * 800` and pins
strictly less than a 30-byte string with a distinguishable end.

**Fix — and I RAN it, over the control, rather than proposing a hypothesis.** One case beside the
existing quiet-stderr case at `:2602`, with a fixture whose head and tail differ:

```python
    _tailed = diagnostic_tail("HEAD" + "S" * 5000 + "THE-TAIL", "")
    case("...and what it keeps is the END of stdout, not the beginning",
         (len(_tailed), _tailed.endswith("THE-TAIL"), _tailed.startswith("HEAD")),
         (400, True, False))
```

Measured, both directions, through the same staged harness:

```
PROPOSED FIX on SHIPPED code (must be GREEN)          rc=0  125/125 passed
PROPOSED FIX + the B1 mutation (must be RED)          rc=1  124/125 passed
   [FAIL] ...and what it keeps is the END of stdout, not the beginning: got (400, False, True) want (400, True, False)
```

**Exactly one** red case, so an `expect` naming it satisfies the harness's real attribution rule
(`w == f`, `len(m) == 1`). The matching manifest entry is still needed — the edge currently has
neither a case nor an entry — and `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` goes 63 → 64,
the declared sum 458 → 459, and the docstring count 124 → 125.

---

# High

## H1 — the floor's spare-budget term may read the wrong stream: `window - len(out)` → `window - len(err)` is green, and the mirror of an existing case is missing.

`scripts/check-plan-code.py:416`:

```python
    err_keep = min(len(err), max(half, window - len(out)))
```

**Measured:** replacing `window - len(out)` with `window - len(err)` leaves the suite at
**`rc 0, 124/124 passed`**. No manifest entry moves this operand either.

The docstring two paragraphs up states the contract this operand *is*: *"whatever a quiet stream does
not use goes to the other."* The mutant breaks exactly half of it. Concretely, a suite that raises at
import — no stdout, a traceback on stderr, a shape the file itself uses as a fixture at
`:2541-2549`:

| input | shipped | mutant | lost |
|---|---|---|---|
| `("", "E" * 5000)` — raises at import: no stdout, 5000 B traceback | 400 | 200 | **200** |
| `("s" * 50, "E" * 5000)` — short stdout, long traceback | 401 | 251 | **150** |
| `("S" * 5000, "")` — quiet stderr, **the direction that IS cased** | 400 | 400 | 0 |

(Run side by side, not arithmetic.) The reader gets half the traceback, and up to 200 characters of
the 400-byte budget are simply discarded — for the failure shape where the traceback is the *only*
evidence there is. The third row is why nothing notices: the one input the suite tries is the one
input on which the two agree.

**Why nothing sees it.** I enumerated all eight `diagnostic_tail(` call sites in the suite:

```
2537  diagnostic_tail(_nso, _nse)                  (flooder.py — real child)
2557  diagnostic_tail(_lso, _lse)                  (late.py — real child)
2566  diagnostic_tail("[FAIL] the one that matters", "E" * 5000)
2569  diagnostic_tail("S" * 5000, "RuntimeError: boom")
2585  diagnostic_tail("S" * 5000, "E" * 5000)
2593  diagnostic_tail("S" * 5000, "E" * 5000)
2598  diagnostic_tail("done\n", "  \n")
2602  diagnostic_tail("S" * 5000, "")              <-- the ONLY quiet-stream case
```

`:2602` is `...and a quiet stderr gives its whole half back to stdout`, want `400`. There is **no
`diagnostic_tail("", "E" * 5000)`** anywhere. The give-back property — the sentence the operand
implements — is cased in one direction only. That asymmetry is the whole of this finding.

**Fix — RUN, not proposed.** The missing case is a one-line mirror of `:2602`:

```python
    case("...and a quiet STDOUT gives its whole half back to stderr",
         len(diagnostic_tail("", "E" * 5000)), 400)
```

```
H1 FIX on SHIPPED code (must be GREEN)        rc=0  125/125 passed
H1 FIX + the H1 mutation (must be RED)        rc=1  124/125 passed
   [FAIL] ...and a quiet STDOUT gives its whole half back to stderr: got 200 want 400
```

One red case, so it is attributable. Plus a manifest entry moving `len(out)` → `len(err)`.

# Medium

## M1 — the report's stream ORDER is unpinned in three independent places, while the same property in `merged_output` has a docstring, two review rounds and a manifest entry.

Three separate edits, each staged alone, each **`rc 0, 124/124 passed`**:

| # | edit | site |
|---|---|---|
| a | the return tuple's two halves swapped — stdout emitted first | `:432-433` |
| b | `diagnostic_tail(so, se)` → `diagnostic_tail(se, so)` at the BEFORE-control site | `:974` |
| c | `diagnostic_tail(so, se)` → `diagnostic_tail(se, so)` at the AFTER-control site | `:1007` |

(b) and (c) are the two call sites the commit's H1 fix was about — the pair the commit found by
"after fixing, SEARCH for the class". The class search found the *slicing expression* at both sites
and stopped; the *argument order* at both sites is uncovered.

**Honest limit — and I measured it rather than asserting it.** 20,000 random `(stdout, stderr)`
pairs with lengths drawn from `{0, 1, 5, 50, 199, 200, 201, 300, 399, 400, 401, 800, 5000}` — every
boundary of this function — comparing `diagnostic_tail(a, b)` against `diagnostic_tail(b, a)`:

```
identical: 3012   reordered only: 16988   CONTENT differs: 0
```

**Not one input loses content to the swap.** `diagnostic_tail` is symmetric under argument exchange
except for the order of the two halves in the output, so (b) and (c) reorder the report rather than
truncating it, and I am not going to dress that up as a data-loss bug. The strongest case I
can make is (a)+(b)+(c) together: the reader of a CANNOT RUN report gets stdout first and the
traceback second, which is the arrangement `merged_output`'s docstring at `:437-452` spends a
paragraph rejecting and which manifest entry 49 exists to prevent **for the other function**. One
rule, two functions, enforced in one of them.

## M2 — the exhaustiveness pass covered the edges on its list; the *class* it was supposed to sweep still has six uncovered members.

The commit's claim is the strong one: *"Every numeric edge this branch introduced or touched now has
a case AT its boundary with a LITERAL want, and a mutation that moves the constant and dies"*, and
its headline is finding an eighth edge that *"had cases and NO manifest entry, so nothing in CI held
it — r4 L2's shape, one row over"*.

I enumerated every integer literal, comparison and slice in the production code this branch touches,
independently of the commit's list. **Six more are in exactly that state — a case that fails, and
no manifest entry**:

| edge | site | probe | red via |
|---|---|---|---|
| `room - 1` (the ellipsis's own character) | `:1288` | `room - 1` → `room` | `122/124` — 2 cases |
| `min(len(err), …)` (the stderr cap) | `:416` | cap deleted | `123/124` — 1 case |
| `if p` (drops an empty half from the join) | `:432` | filter deleted | `122/124` — 2 cases |
| `enumerate(targets, 1)` BEFORE-control | `:961` | start → 0 | `122/124` — 2 cases |
| `enumerate(muts, 1)` | `:1038` | start → 0 | `121/124` — 3 cases |
| `enumerate(targets, 1)` re-control | `:993` | `position + 1` | `122/124` — 2 cases |

None of the 63 manifest entries moves any of these. By the commit's own standard for the eighth edge
— *cases but no entry* — these are six more instances of the row it congratulated itself on
finding. The row was fixed; the question was not asked of the other rows on the same lines.

I rate this Medium rather than High because a case failing does stop `--mutate .` at its control
step, so CI is not blind to these today; what is missing is the proof that the code is
load-bearing, which is the manifest's job and the reason the eighth edge was filed at all.

## M3 — the principle r4 L1 refuted is still stated as a general rule, and two clauses rest on it. Both are dead — asked and answered, not assumed.

Two clauses on this branch are green when deleted:

| clause | site | suite when deleted |
|---|---|---|
| `max(room - 1, 0)` — the floor | `:1288` | `rc 0, 124/124 passed` |
| `min(len(out), …)` — the cap | `:417` | `rc 0, 124/124 passed` |

The stated justification for the first having no case is `progress_line`'s docstring at `:1280-1282`:

> That branch is unreachable anyway — it needs a `done`/`total` pair of some 76 digits — **and a
> clause no input can reach is a clause no case can kill.**

**That last clause is the general principle `d6f55881` itself refuted, 860 lines earlier in the same
file** (`:418-431`): *"'no input can reach this clause' is not the same as 'nothing can' …
Reachability has to be asked of the mutation space too."* The lesson was recorded at the site where
it was learned, and the site that states its opposite **as a rule** was left standing. This file's
own convention is to mark a reversal with `⟳` at *every* site it governs; it does that in a dozen
places.

**So I asked the question rather than assuming either answer.** Three instruments, in increasing
order of authority (Measurements §2–§3):

1. **Input-space sweep** — 60,000 random `(stdout, stderr)` pairs across every boundary for the cap;
   324 `(done, total, label-length, PROGRESS_WIDTH)` combinations for the floor. **Differs on 0.**
2. **Mutation-space enumeration** — the floor binds only when `len(head) > 78`, i.e. a `done`/`total`
   pair of **more than 74 digits**. No entry moves `head` or `PROGRESS_WIDTH` that way (#38 shortens
   `head`; #48 widens `PROGRESS_WIDTH` to 200, which makes `room` *larger*).
3. **The full `--mutate .`** — the instrument that refuted r4 L1, and the only one that counts. Floor
   deleted, over a staged tree, with entry #45's anchor retargeted so the run can complete:
   **`38 file(s), 458 mutation(s), 458 killed, 458 attributed, 0 survivor(s), EXIT=0`** — identical
   to the baseline. Contrast r4 L1's twin clause, where the same experiment gave **457 attributed**.

**The floor is dead in the mutation space too.** r4 L1's question, asked of the second clause and
answered: *no*.

### ⭐ The first attempt at that run produced something better than the number

Deleting the floor *without* touching the manifest gave:

```
✗ mutation 'the label is emitted unbounded again, …': anchor NOT FOUND — it was not applied,
  so its 'caught' verdict would be meaningless
NOT MEASURED — the mutation harness produced no coverage verdict (457 of 458 declared
  mutation(s) produced a verdict). Treat this as NOT CHECKED.
```

`ok = False` at `:1068` → `main` returns `1` at `:2897` → **CI goes red.** Entry #45's anchor is the
literal text `    return head + label[:max(room - 1, 0)] + "…"`, so *any* edit to that line breaks it.

⚠ **That is a CANNOT RUN, and I am recording it as a failed experiment, not as a pass.** It is also
the more interesting result: **the floor is protected after all — accidentally, and by the wrong
mechanism.** Not by a case, and not by a mutation dying; by an anchor that happens to quote it. That
is the *"a refactor ORPHANS the mutation guarding it"* class seen from the other side — the same
brittleness that destroys coverage under a legitimate refactor is here the only thing between this
clause and silent deletion, and what it reports is *"the manifest is broken"*, never *"this guard is
load-bearing"*.

**Why Medium and not High:** the harm is nil, measured three ways, and CI does go red. What is wrong
is that the file states a refuted principle as a live rule at the exact place it is relied on, and a
reader who acts on it gets a green suite followed by a red that names the wrong thing.

**Fix:** amend `:1282` with the `⟳` this file uses everywhere else — *"⟳ asked of the MUTATION space
too (r5): 458/458/458, dead; and held in CI only by entry #45's text anchor, which is not coverage"*.
That is a different artefact from an unexamined assertion of unreachability, and it is the artefact
r4 L1 proves is needed.

**And the cap is half-swept.** The commit's edge list names `min(len(out), window - err_keep)` as
swept with *"a mutation that moves the constant and dies"*. The entry it means is #53, which moves
`window - err_keep` → `window`. That covers the **subtraction**, not the **cap**. The row reads as
whole and is not.

---

# Low

## L1 — `head = f"[{done}/{total}] "`: the trailing space is load-bearing and cased eight times over, with no entry.

Removing it gives `116/124` — 8 red cases, the largest blast radius of any probe I ran. It is
thoroughly cased and has no manifest entry. Listed for completeness of the enumeration, not as work
worth doing: an edge eight cases deep is not the shape that goes silently vacuous.

## L2 — the split-point case asserts a length, not a side.

```python
case("both streams flooded, and the stderr half is exactly half the window",
     len(diagnostic_tail("S" * 5000, "E" * 5000).split("\n")[0]), 200)
```

The want is the literal 200, which is right and is the round's B1 fix. But `.split("\n")[0]` is
asserted only for its **length** — and `"S"` and `"E"` are both available in the value. The case
would pass identically if the first line were the *stdout* half (this is M1(a), measured green).
Asserting `diagnostic_tail("S" * 5000, "E" * 5000).split("\n")[0] == "E" * 200` costs nothing and
closes M1(a) in the same line.

## L3 — the restored guards were restored as a pair; only one of them was measured.

`:432-433` — the commit's comment says *"THE `if err_keep else ""` GUARDS STAY"* and gives the
measurement for **`err_keep`** only: entry #52 (`max(half, …)` → `max(0, …)`) drives `err_keep` to 0
with `err` non-empty. Nothing in the comment, and nothing I found in the manifest, drives
**`out_keep`** to 0 with `out` non-empty: that needs `window - err_keep == 0`, i.e. `err_keep == 400`,
which needs `len(out) == 0`. The twin guard is asserted to be load-bearing by association.

This is small, and I did not run the mutation-space experiment for it — but it is the same
association that made r4 L1 wrong in the first place ("the guards cannot matter", reasoned once and
applied to both).

---

## The enumeration (brief item 2), done from the code

AST-walked every `ast.Constant(int)`, `ast.Compare`, `ast.Subscript` and `min`/`max` call in the
functions this branch introduced or edited, then hand-added the loop/call-site edges in
`mutate_delivered`, `run_mutations` and `main`. **29 edges.** Each probed individually through the
staged harness over the green control.

| # | site | edge | case? | entry? | probe verdict |
|---|---|---|---|---|---|
| 1 | `:391` | `DIAGNOSTIC_WINDOW = 400` | ✅ 3 literal wants | ✅ #62 | `399`→`121/124`, `401`→`122/124` |
| 2 | `:415` | `half = window // 2` — the `2` | ✅ literal 200 | ✅ #57 #58 | `//2+1`→`123/124` |
| 3 | `:416` | `max(half, …)` floor | ✅ | ✅ #52 | covered |
| 4 | `:416` | `window - len(out)` operand | ❌ | ❌ | **GREEN 124/124 → H1** |
| 5 | `:416` | `min(len(err), …)` cap | ✅ | ❌ | `123/124` → M2 |
| 6 | `:417` | `window - err_keep` | ✅ | ✅ #53 | `-1`→`120/124` |
| 7 | `:417` | `min(len(out), …)` cap | ❌ | ❌ | GREEN 124/124 → M3 |
| 8 | `:432` | `err[-err_keep:]` **direction** | ✅ | ❌ | `122/124` |
| 9 | `:433` | `out[-out_keep:]` **direction** | ❌ | ❌ | **GREEN 124/124 → B1** |
| 10 | `:432` | `if err_keep else ""` | deliberate | ✅ #52 (mutation space) | r4 L1 |
| 11 | `:433` | `if out_keep else ""` | deliberate | ❌ | → L3 |
| 12 | `:432` | `"\n"` separator | ✅ literal 401 | ✅ #59 | covered |
| 13 | `:432-433` | tuple ORDER — err half first | ❌ | ❌ | **GREEN → M1(a)** |
| 14 | `:432` | `if p` filter (drops an empty half) | ✅ | ❌ | `122/124` → M2 |
| 15 | `:437-453` | `merged_output` order | ✅ | ✅ #30 #49 | covered |
| 16 | `:468` | `return 2` on timeout | ✅ | ✅ #0 | covered |
| 17 | `:961` | `enumerate(targets, 1)` start | ✅ | ❌ | `122/124` → M2 |
| 18 | `:967` | `out.split("\n")[-1]` | ✅ | ✅ #56 | covered |
| 19 | `:974` | `diagnostic_tail(so, se)` arg order | ❌ | ❌ | **GREEN → M1(b)** |
| 20 | `:993` | `enumerate(targets, 1)` start | ✅ | ❌ | `122/124` → M2 |
| 21 | `:1007` | `diagnostic_tail(so, se)` arg order | ❌ | ❌ | **GREEN → M1(c)** |
| 22 | `:1038` | `enumerate(muts, 1)` start | ✅ | ❌ | `121/124` → M2 |
| 23 | `:1256` | `PROGRESS_WIDTH = 79` | ✅ literal 79 | ✅ #48 | `78`→`121/124`, `80`→`122/124` |
| 24 | `:1285` | `head`'s trailing space | ✅ ×8 | ❌ | `116/124` → L1 |
| 25 | `:1286` | `len(label) <= room` | ✅ at 69/70 | ✅ #50 #51 | covered |
| 26 | `:1288` | `room - 1` — the ellipsis's own column | ✅ | ❌ | `122/124` → M2 |
| 27 | `:1288` | `max(…, 0)` floor | ❌ | ❌ | **GREEN → M3** |
| 28 | `:1288` | `label[:…]` direction (head, correctly) | ✅ | ✅ #45 | covered |
| 29 | `:97` | `SUITE_TIMEOUT = 120` | pre-existing, consumed by `run_suite_parts` | — | out of scope |

**Seven rows are green when mutated — 4, 7, 9, 13, 19, 21, 27 — which is five distinct findings**
(B1, H1, M1 a/b/c, and M3's two clauses). Six of the seven are not integer literals at all. That is the answer to "what did I miss": the sweep was organised around *constants*,
and a constant is the one kind of edge it already had a habit of checking.

### ⭐ And here is the mechanism that let the sweep mark them green — measured, not guessed

I re-read the manifest programmatically, asking of each uncovered edge: *does any entry's edit text
contain this expression, and does any entry actually CHANGE it?*

```
slice direction out      -> NO ENTRY MENTIONS IT
`if p` filter            -> NO ENTRY MENTIONS IT
slice direction err      -> [(59, 'only ANCHORS on it')]
window - len(out)        -> [(52, 'only ANCHORS on it'), (54, 'only ANCHORS on it')]
min(len(err),            -> [(52, 'only ANCHORS on it')]
min(len(out),            -> [(53, 'only ANCHORS on it'), (54, 'only ANCHORS on it')]
enumerate(targets, 1)    -> NO ENTRY MENTIONS IT
enumerate(muts, 1)       -> NO ENTRY MENTIONS IT
```

**Six of the seven green rows sit inside the ANCHOR TEXT of an entry that does not move them** —
every one except B1's, which no entry mentions at all.
`window - len(out)` appears verbatim in entries 52 and 54; `min(len(out), …)` in 53 and 54. An
audit that asks "is there a manifest entry for this line?" — which is what a sweep organised around
lines does — gets a hit and moves on. The entry is real, it dies, it names a case; it just is not
about the sub-expression the auditor was checking.

⚠ This is the same failure as **r4 L2 / the eighth edge**, one level down. r4 L2 was *"the row has
cases and no entry"*. This is *"the row has an entry, and the entry is not about this part of the
row"* — and it is harder to see, because the grep succeeds. The question that separates them is not
*"is this line in the manifest?"* but *"does any entry's `find` differ from its `repl` AT this
sub-expression?"*, which is a three-line script over the manifest and is how I produced the table
above.

Two entries are listed in the table as covering an edge on a technicality and should not be read as
coverage: entry **45** (`return head + label[:max(room - 1, 0)] + "…"` → `return head + label`)
deletes the truncation wholesale rather than moving the `- 1` or the `0`; entry **38**
(`f"[{done}/{total}] "` → `f"[{done}] "`) removes `/{total}` and keeps the trailing space. Neither
moves the edge it appears to cover.

---

## Answers to the brief's seven questions

**1. Are the new boundary cases genuinely at the boundary?** Yes — I probed all four numeric
constants at ±1 and every one dies at the tight boundary, via a literal want:

| constant | −1 | +1 |
|---|---|---|
| `PROGRESS_WIDTH = 79` | `121/124` | `122/124` |
| `DIAGNOSTIC_WINDOW = 400` | `121/124` | `122/124` |
| `half = window // 2` (200) | *n/a* (`window // 4` is entry 57) | `+1` → `123/124` |
| `out_keep` budget | `− 1` → `120/124` | — |

This is a real improvement and I could not break it. The smallest edits that survive are not edits
to the constants at all — they are the *directions and operands* around them (B1, H1, M1).

**2. Is the exhaustiveness pass exhaustive?** No — M2 (six more edges with cases and no entry) and,
more seriously, B1 and H1, which have neither. The enumeration is in M2's table plus B1/H1; it was
done from the code, walking `diagnostic_tail`, `merged_output`, `run_suite_parts`, `run_suite`,
`progress_line`, `stderr_progress`, both control loops, `run_mutations` and the `main` wiring.

**3. Are the restored guards uncovered on purpose, correctly?** Yes — the reasoning is right and the
harness proved it. But the same question was not asked of the other two clauses in that position
(M3) or of the guard's own twin (L3). I asked it of M3's floor: a full `--mutate .` says
**458/458/458 — dead**, so the author's instinct was right; what is missing is that they did not ask,
and the docstring at `:1282` still states the refuted principle as a general rule.

**4. Did the H1 fixture change weaken anything it already served?** I found no weakening. The fixture
at `:2124-2140` still drives `rc=1` so `control_is_green` is unaffected; `a tree that goes bad DURING
the sequence invalidates the run` asserts on `"no longer green AFTER the sequence"`, which the
change does not touch; and dropping `": got "` from the fixture's `[FAIL]` line is an *improvement*
against the truncation hazard the file documents at `:2521-2530`.

**5. Does `--mutate .` still report 458/458/458/0?** **Yes, exactly** — re-run, 7m25s:
`38 file(s), 458 mutation(s), 458 killed, 458 attributed, 0 survivor(s)`, exit 0. The nested
self-test writes 0 B to stderr and the reporter fires 534 times (`458 + 38 + 38`). *Measurements §1.*

**6. Cases against entries; recomputation.** `d6f55881` adds **3 cases** and **6 entries**
(121→124, 452→458) — the healthy direction of the ratio the file's own comment at `:2658-2665` warns
about. I found **no** case that rebuilds a production value: the new split-point case re-splits on
`"\n"`, but the separator is independently pinned by the `== 401` case, so the two do not derive from
each other. L2 is the one place a want is weaker than it needs to be, and that is a missing
assertion, not a recomputation.

**7. What did the author not measure?** The *direction* of a slice, the *operand* of a subtraction,
and the *order* of two arguments — three kinds of edge that are invisible to a sweep organised
around integer literals. Every finding above is one of those three. The commit's sweep was
"every numeric edge"; the defects live one category out from "numeric".

---

## On the scoping

I think the coverage scoping is right, and the evidence for it got stronger this round rather than
weaker. B1, H1 and M1 are in three different functions and two different files' worth of call sites,
and all three are the same method failure: **a fixture that cannot distinguish the property it
claims to pin.** A redesign of the diagnostic subsystem would carry `"S" * 5000` along with it.

But I would name the method failure more precisely than "an input far inside the boundary", because
that phrasing has now produced four rounds of fixes that each move an input closer to *one* boundary
and miss the next axis:

> **A fixture must differ from itself along the axis the property is about.** `"S" * 5000` is at the
> boundary of *magnitude* and has no *position*, so it pins length and cannot pin direction.
> `"E" * 5000` vs `"S" * 5000` have identity but the want throws it away (L2). r4 asked "is the
> input at the edge?"; the question that catches B1 is "**what two inputs would this case have to
> tell apart, and can it?**"

That is a checklist item, not a redesign, and per the brief's rule I am not proposing to restructure
anything — I could not show a redesign removes a defect rather than moving it.

---

## What I did NOT measure

- **The full `--mutate .` for M1, M2, M3.** I measured those with the suite only. A mutation-space
  run could show one of them is load-bearing in the way r4 L1's guards were; I only ran that
  experiment for M3's floor, where the question is the whole finding. L3 in particular is unrun.
- **Any non-`check-plan-code.py` target.** The other 37 files in `EXPECTED_MUTATIONS` are untouched
  by this commit and I did not review them.
- **The docs half of the commit** (`docs/dashboard-entries.md`, the two filed r4 reviews) beyond
  reading the r4 findings to avoid re-filing them.
- **Whether the commit's three deliberate deferrals are right** (**r4's** L3 — not mine —
  `parse_fail_names`'s asymmetry, and the generic "±1 and ×2 on every integer literal" sweep). The
  commit says the filing decision is the human's and I agree. I note only how that sweep would have
  scored against this round: it would have caught **M2's `room - 1` and the three `enumerate(…, 1)`
  starts, and M3's `0` floor** — and **not B1, H1 or M1**, none of which is an integer literal. It is
  worth more than the commit implies and still misses the Blocking.
- **Concurrency.** B1's and M3's probes — the two that matter — ran with nothing else in flight.
  Several later probes (M1's three, M3's cap) ran alongside a full `--mutate .`. Each probe is a
  single ~3 s suite against a 120 s `SUITE_TIMEOUT` on 12 cores, so a contention-induced timeout is
  implausible; and every one of those returned **green**, which is the safe direction — contention
  makes runs fail, not pass. I did not re-run them in isolation.
- **`if out_keep else ""`** (L3) in the mutation space. That is the one experiment of this shape I
  left unrun.

---

## Measurements

### 1. The baseline `--mutate .` — brief item 5. **The commit's claim verifies exactly.**

```
$ python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 38 file(s), 458 mutation(s), 458 killed,
     458 attributed to the case each names, 0 survivor(s)
EXIT=0
real 7m25.466s   user 4m41.326s   sys 2m12.902s
```

Claimed 38 / 458 / 458 / 458 / 0 — **got 38 / 458 / 458 / 458 / 0.** No discrepancy.

Two subsidiary claims also check out:

- **nested self-test stderr = 0 B.** `python3 scripts/check-plan-code.py --self-test 2>err` →
  `0` bytes. The r1 H1/H2 fix holds.
- **the reporter fires in every phase.** stderr carried **534** progress lines:
  `458 mutations + 38 controls + 38 re-controls = 534`, exactly. First line
  `[1/38] control scripts/begin-plan.py`, last `[38/38] re-control scripts/page_markup.py`.
  The docstring's "510 lines over the run" figure is from the 434-mutation era and is now stale by
  24 lines — cosmetic, not filed.

**So every number in the commit message is true.** The findings above are all things the run cannot
see: `--mutate .` measures the mutations someone thought to write, and B1/H1/M1/M3 are mutations
nobody wrote. The commit says this itself, in its deferral list. It is worth stating plainly that a
`458/458/458/0` is fully consistent with a Blocking coverage hole — that is the *definition* of this
class, not a surprise.

### 2. The M3 mutation-space experiment — asking r4 L1's question of the second clause

**Attempt 1 — CANNOT RUN, recorded as a failure.** Staged tree, `max(room - 1, 0)` → `room - 1`,
manifest untouched:

```
✗ mutation 'the label is emitted unbounded again, …': anchor NOT FOUND — it was not applied,
  so its 'caught' verdict would be meaningless
NOT MEASURED — the mutation harness produced no coverage verdict (457 of 458 declared
  mutation(s) produced a verdict). Treat this as NOT CHECKED.
```

Entry #45's anchor quotes the edited line verbatim. This is not a result about the floor; it is the
harness refusing to produce one — and it is the substance of M3's ⭐ note.

**Attempt 2 — the real measurement.** Same edit, with entry #45's anchor retargeted to the new text
(the single manifest change; nothing else moved):

```
$ python3 scripts/check-plan-code.py --mutate .          # staged tree, floor deleted
OK — delivered scripts mutated: 38 file(s), 458 mutation(s), 458 killed,
     458 attributed to the case each names, 0 survivor(s)
EXIT=0
```

**Identical to the baseline.** Where r4 L1's twin clause gave `458 killed, 457 attributed`, this one
gives 458/458. The floor is dead in the mutation space.

### 3. Input-space sweeps for M1 and M3

```
diagnostic_tail(a,b) vs diagnostic_tail(b,a)   20,000 pairs   content differs on 0  (M1 b/c)
min(len(out), …) cap present vs deleted        60,000 pairs   differs on 0          (M3)
max(room - 1, 0) vs room - 1                      324 combos  differs on 0          (M3)
```

Length pools covered every boundary of these functions:
`{0, 1, 2, 5, 50, 100, 199, 200, 201, 299, 300, 399, 400, 401, 800, 5000}`, including
whitespace-only strings; and `PROGRESS_WIDTH ∈ {79, 200}`, 200 being the only value any manifest
entry produces.

### 4. Both proposed fixes, run over the control

| fix | on shipped code | with its mutation | red cases |
|---|---|---|---|
| B1's tail case | `125/125 passed` | `124/125 passed` | exactly 1 — the new case |
| H1's mirror case | `125/125 passed` | `124/125 passed` | exactly 1 — the new case |

Both are attributable under the real rule (`w == f`, exactly one match), so neither is a hypothesis.

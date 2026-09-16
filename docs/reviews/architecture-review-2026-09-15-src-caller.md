# Architecture review — `src-caller`, 2026-09-15

**Armed by the thrashing rule, not scheduled.** `docs/dev-process.md` fires a Phase 6 review when
**two consecutive rounds carry findings caused by the previous round's own fix, in one component.**
Round 2's Claude half found that had happened in `src-caller` on branch `ship-src-root-alone` and
said so plainly, including the recommendation *not* to take another patch. This is that review.

⚠ **Scope is the component, not the codebase.** The arming condition is component-scoped and so is
this document. `CONTEXT.md` and `docs/adr/` were read; nothing here re-litigates an ADR.

---

## The verdict, first

**Four consecutive attempts to guard one property were each half-covering, and the cause is common
to all four rather than particular to any.** They tried to prove a NEGATIVE — *"nothing else
consults the world"* — by **intercepting the world at runtime**. Interception must enumerate the
surfaces through which the world is reachable, and that set is **open**. Every attempt was defeated
by the next member of it.

| # | Attempt | Where | Defeated by | Found by |
|---|---|---|---|---|
| 1 | `_Forbidden` v1 — `get` only | PR #295 r4 | `dict()`, `len()`, `for k in` | #295 r4 reviewer |
| 2 | `_Counting` v1 — `get` only | r1 here | `SRC_ROOT_ENV in os.environ` | Codex r2 |
| 3 | `_Counting` v2 — eight surfaces | r2 here | `setdefault`, `pop`, `repr()`, `==`, `len()` | coordinator |
| 4 | stub `src_root` + `_Forbidden` | r2 here | **a second `src_root()` call**, and `os.environb` | Claude r2 |

Attempt 4 is the instructive one. Stubbing `src_root` made the *env* unreachable — and in the same
move made **calling the stub twice free**, retiring the coverage attempt 2 had bought. The comment
shipped with it asserted the deleted cases were redundant. That sentence was false and one
two-line mutation falsified it:

```
root = observed.root   ->   root = src_root().root
```

**working tree: 142/142 SURVIVES** · at commit `78100320`: **KILLED**, by exactly the two cases
attempt 4 deleted. Verified independently by the coordinator.

⭐ **This is not four careless mistakes. It is the predictable behaviour of a denylist over an open
set**, and the right response is to change what question is asked, not to enumerate harder.

## The redesign — ask it a second way, where the set is CLOSED

The property is about a **bounded region of code we own**: ten lines of `do_GET`. "Does this region
call `src_root()` more than once, or name an environment API at all?" is **decidable by reading it**.
There is no open set of runtime surfaces to enumerate — only the names appearing in a region where
anything new is, by definition, a change under review.

**Two checks that answer different questions, composed:**

| | Question | Catches | Blind to |
|---|---|---|---|
| **STATIC** — source of the `/src/` branch | *is this region written correctly?* | a second `src_root()`; any env spelling **including `os.environb`** | a helper that cheats |
| **DYNAMIC** — `_Forbidden` over `os.environ` | *does anything it calls cheat?* | env reads through any callee at runtime | spellings outside `os.environ` |

⚠ **Why this is not the duplicate-vocabulary shape `check-vocabulary-collisions.py` catches**, asked
because attempt 3 *was* that shape (a second env-interception class beside `_Forbidden`): the two
halves **have no shared fact to disagree about.** One is a statement about syntax in a named region;
the other is a statement about runtime reachability. A drift between them is not possible in the way
`_Counting` and `_Forbidden` could drift, because neither is a copy of the other's rule.

**The static half is not a new instrument for this file.** `_rev_branch_src` (`:1417`) already
asserts a call-site property by slicing source, and its comment gives this exact reason: *assert the
MECHANISM, not a hardcoded answer.* The redesign extends an existing idiom rather than importing one.

### Measured — the two escapes that defeated interception, against the redesign

Control `150/150`, mutations applied to the delivered file, restored by `cp`, never git:

| Mutation | Before (attempt 4) | After |
|---|---|---|
| `root = src_root().root` — a second observation | **142/142 SURVIVES** | **148/150 KILLED** |
| re-read via `os.environb.get(...)` | **142/142 SURVIVES** | **147/150 KILLED** |
| re-read via `SRC_ROOT_ENV in os.environ` | 136/142 killed | 142/150 killed |
| re-read via `os.getenv` | 136/142 killed | 142/150 killed |
| master's broken `<dir>` 404 text | killed | 147/150 killed |
| `safe_path` bypassed at the caller | killed | 146/150 killed |

Both previously-invisible escapes now die, and nothing that was caught stopped being caught.

## What the review also changed, and why each is part of the design rather than a patch

- **The vacuity ratchet runs in BOTH directions.** r2 L2 asked for the surface list to be *derived*
  from `_Forbidden` rather than hand-typed, because a hand-typed copy drifts — correct, and
  deriving it alone **introduced the opposite hole**: deleting `__iter__` from the class deleted its
  case too, and the suite reported **148/148 passed**, a guard losing a surface reading as a clean
  run. Measured. A derived population needs a **floor**, and the floor must be a literal — deriving
  it from the same walk would make it agree by construction. Now: added-but-unexercisable → red
  (149/151); removed → red (148/149).
- **`_Forbidden` takes `by=`** (r2 L1). Its message hardcoded `src_root_help`, true while that was
  its only user; attempt 4 gave it a second, and every failure from the new site sent the reader to
  the wrong function. That is this file's own rule — *the reason for a failure was inferred rather
  than carried* — committed inside the guard written for it. Verified: the renderer site still says
  `src_root_help`, the caller site now says `do_GET`.
- **The `/src/` reach comment gained one clause** (r2 L3). It said no CORS header is emitted *"so a
  cross-origin page cannot read the response"*. True of the **body**; status is observable
  cross-origin, and this route answers 200-vs-404 by file existence — measured — which over the true
  reach is a file-existence oracle for the checkout. Still not judged worth blocking on (paths, not
  contents, on a loopback dev server), but the sentence now says what is true, because round 1's
  defect on this same paragraph was a security judgement resting on an unchecked claim.

## Stated limits — what this design does NOT guarantee

- The static half reads a **source slice** between two markers. A marker that moves raises inside
  the case thunk (r4's rule), so it reports as `[FAIL]` rather than aborting the suite — but it is
  still a slice, and a refactor that moves the `/src/` branch must re-check it.
- The static half cannot see into helpers; that is the dynamic half's job, and the dynamic half
  cannot see spellings outside `os.environ`. **Neither is complete alone. The claim is about the
  pair**, and that is the first time this component has stated its boundary rather than implying
  coverage it did not have.
- `scripts/explainer-serve.py` still has **no mutation manifest** (backlog **#122**), so every
  measurement above was run by hand — the exact complaint #122 makes. Unchanged by this work.

## The question no tool can see — *what did we decide that isn't written down?*

**That an instrument may be redesigned mid-branch when its defect is structural, without the
deliverable being touched.** Every finding in rounds 1 and 2 except one comment clause was aimed at
the *instrument*; `/src/` itself has taken no finding since round 4 of PR #295 and serves correctly,
verified live. `review-method.md`'s Q4 would read that as *stop reviewing and go build* — and
against that, the thrashing rule said *stop patching and redesign*. **Both fired, and they point
opposite ways.** The resolution taken here: the thrashing rule wins when the repeated defect is a
guard **reporting a pass it has not earned**, because "go build" on top of a guard that cannot fail
is how the four-day outage happened in the first place — a green suite over a dead subsystem. That
reasoning is recorded here because it is a judgement, not a rule either document contains, and the
next person to hit the collision deserves the argument rather than the outcome.

## Filed, not fixed here

**A Codex review invoked with a generic `--out` stem overwrites a committed verdict belonging to
unrelated merged work.** Measured on this branch, twice: `--out …/r1-codex.md` made the wrapper
write `docs/reviews/verdicts/r1-codex.verdict.json`, clobbering the committed verdict for
`bb265c08` — **not an ancestor of this branch**. Both restored here; the branch now uses
branch-specific stems. The *cause* is in `scripts/codex-review.py`, which derives the verdict path
from the caller's `--out` stem with no allocator — this project's recorded *"a guard's evidence path
is a namespace with no allocator"*, now at its third occurrence. Fixing it is a tooling change with
a policy call in it (who owns that namespace), so it is a backlog row, not a smuggled edit.

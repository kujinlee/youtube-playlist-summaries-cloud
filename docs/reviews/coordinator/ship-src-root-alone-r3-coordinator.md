# Round 3 — `ship-src-root-alone` — coordinator

```yaml
round: 3
fixes_nontrivial: false
subject: ship-src-root-alone
halves:
  claude: ran
  codex: ran
findings:
  - {id: B1, severity: Blocking, aim: instrument, fix_induced: true, component: src-caller, disposition: retreat}
  - {id: B2, severity: Blocking, aim: instrument, fix_induced: true, component: src-caller, disposition: retreat}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: recorded-evidence, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: recorded-evidence, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: recorded-evidence, disposition: refuted}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: src-caller, disposition: moot}
  - {id: L2, severity: Low, aim: instrument, fix_induced: true, component: forbidden-ratchet, disposition: fixed}
deliverable_findings: 0
stopping_rule: triggered_and_executed
```

## The pre-committed retreat triggered, and was executed

Round 2's coordinator document said, **before this round ran**:

> if round 3 finds another fix-induced defect in `src-caller` … the answer is **not** a sixth
> attempt. It is to **delete the "consulted the world exactly once" property from this suite
> entirely**, state in the comment that it is unguarded and why, and let the behavioural cases stand
> alone.

Round 3's Claude half found **two Blocking, both fix-induced, both in `src-caller`**, and the
architecture review's central claim was refuted:

- **B1** — the static case was `count("src_root()") == 1`, a **literal substring count**. `_probe =
  src_root` in-region defeats it, and the dynamic half could not help because `_drive_src` still
  **stubbed** `src_root` — the mechanism the architecture review itself identified as attempt 4's
  fatal flaw and did not remove. **A regression, on the strongest evidence available**: killed at the
  parent commit `78100320`, survives at the child. Confirmed a real production defect, not a test
  artefact — driving `do_GET` unstubbed with a counting wrapper gave **2** real reads of
  `EXPLAINER_DOCS_ROOT` against a pristine **1**.
- **B2** — *"NO ENVIRONMENT API IN THE REGION, IN ANY SPELLING"* was four literal tokens. Four
  genuine second reads placed **in the region, in plain sight** passed the whole suite: an aliased
  `from os import environ as _ENV`, `posix.environ`, an import-time cache, and a module-level helper
  using `os.environb`. Two of those need no helper, so this document's own stated limit did not
  cover them.

⭐ **The claim that asking the question STATICALLY makes the set CLOSED was wrong.** The *region* is
bounded; the set of ways to name the environment from inside it is not. It was **attempt 5 of the
identical shape** — a denylist over an open set — relocated from runtime surfaces to source text.

⚠ **And the argument that would have stopped me was already in hand.** I argued the open-set problem
*inductively*, from four failures, which could have been four coincidences. Round 2's reviewer had
already given the *structural* reason: `os.environb` and a subprocess inheriting the environment read
the **C-level environ** beneath `os.environ`, which no Python object swap can reach. I weighted my own
induction over their mechanism. **Pre-committing the retreat is the only reason this did not become a
sixth attempt** — by the time the evidence arrived, the decision had already been made, so there was
nothing left to rationalise.

## What the retreat actually is

`scripts/explainer-serve.py` no longer claims the property. It states, in terms:

| | |
|---|---|
| **GUARDED** | a second read spelled through the `os.environ` **object** at request time — `_drive_src` swaps it for `_Forbidden`, so every behavioural case is also asserting this |
| **NOT GUARDED** | a name bound before the swap (`from os import environ as _ENV`), `posix.environ`, `os.environb`, an import-time cache, a subprocess inheriting the env, and a second `src_root()` call however spelled |

⭐⭐ **THE HONESTY STATEMENT WAS VERIFIED BY MUTATION, BOTH LISTS, BY THE CODEX HALF** — which is the
one thing that had to be true, because a false entry in the *guarded* column would have been the
sixth false coverage claim on this component:

> guarded examples all died at `138/144`; the named unguarded escapes all survived at `144/144`,
> including pre-bound `environ`, `posix.environ`, `os.environb`, import-time cache, subprocess
> inheritance, and a second `src_root()` call.

It also confirmed the deletion took nothing it should not have: fallback removed `139/144`, master's
`<dir>` text `143/144`, `safe_path` bypass `141/144`, `expanduser` deleted `143/144`, either `[FAIL] `
report site `143/144`.

**An unguarded property that says so is worth more than a guard reporting a pass it has not earned.**
That is this branch's own lesson — the four-day outage was a green suite over a dead subsystem.

## M1, M2 — my recorded numbers were wrong, and the cause is one habit

**M1 (Claude):** every figure in the architecture review's mutation table was **one too low**. The
raw runs were made at **149** cases; a floor case was then added (149 → 150) and I updated the
**denominators by hand without re-running**, leaving the numerators. Adding an always-passing case
increments both. No verdict changes — every row is still killed. This is *never write a cost table
from memory — derive, don't store*, broken by editing a measurement to match a changed world instead
of taking it again.

**M2 (Codex):** my *correction* to the round-1 document said "re-measured cleanly: 133 → 131". Wrong
as well. Measured with the context named:

| where `78100320` runs | control | mutant |
|---|---|---|
| in-tree | 133/133 | 132/133 |
| out-of-tree | 132/133 | 131/133 |

⭐ **An out-of-tree run of this suite carries one pre-existing red** — a case asserting a declared
source is a real file in the repo, which cannot pass outside it. "133 → 131" is a pair occurring in
neither context: it took the in-tree control and the out-of-tree mutant. **A measurement needs its
CONTEXT recorded, not just its value** — and the absence of that habit produced a wrong correction
*inside a correction about wrong measurements*, which is this repo's *the corrections fail too*.

## M3 — REFUTED, and the disagreement is the lesson

Codex filed the architecture review's *other* correction sentence as also one low. It is not. That
sentence names its context — **out-of-tree**, control 149/150, mutant 148/150 — and Codex measured
**in-tree**, 150/150 → 149/150. Both are right for their context; re-verified by the coordinator.
Recorded rather than quietly dropped, because a refuted finding that is never written down gets
re-filed — and because it is the same context-labelling defect as M2, seen from the other side.

## L1 — moot, L2 — fixed

- **L1** the static slice's *second* marker failed **silently** (switching `resolve_page(path, ROOT)`
  to keyword arguments widened the region from 18 to 27 lines at 150/150) while the stated limit
  claimed both markers fail loud. Moot: the static check is gone with the retreat.
- **L2** `_EXERCISE` bound a surface name to its probe **by convention** — repointing the
  `setdefault` and `pop` probes at `_fb.get("X")` passed 150/150, so two cases claiming to exercise
  those surfaces re-proved `get`. Probes are now dispatched by `getattr(_fb, n)`, which cannot be
  pointed elsewhere. ⚠ **The remaining bound is stated in the code rather than implied**: rewriting
  the dispatch line itself still passes. That is accepted, not chased — chasing it is the
  enumerate-harder trap this file has just retreated from, relocated one level further in.

## Q4 — convergence, and why NO round 4

**The deliverable has taken zero findings in three rounds**, and round 3's Claude half examined it
**directly** rather than inheriting that verdict — `SrcRoot`, `src_root`, `src_root_help`,
`_gone_checkout_help` and the `/src/` branch — and confirmed the carried-observation design is
correct, with pre-existing coverage intact rather than hollowed by the redesign.

**Round 3's remaining work was two sentences in review documents.** No code changed after the Codex
half audited it, so `fixes_nontrivial: false` and the tree that merges **is** the tree that was
reviewed — Q4(b)'s question is answered without spending a round on it.

⚠ **Stated rather than hidden: the two `⟳ CORRECTED` blocks in
`ship-src-root-alone-r1-coordinator.md` and the architecture review were edited AFTER round 3's Codex
half ran.** They are documentation of measurements, contain no code, and one of them exists *because*
that half filed M2. Running a fourth dual round to re-read two corrected paragraphs is the cost this
project measured on PR #302 — *two needless rounds* — and `review-method.md:309` says one round is
enough for a small contained change.

**Q5 — thrashing:** armed at round 2, acted on at round 3 **by retreating**. It cannot re-arm,
because there is no longer a guard in `src-caller` to induce a defect in: the component's remaining
cases are behavioural, and all of them are mutation-proved.

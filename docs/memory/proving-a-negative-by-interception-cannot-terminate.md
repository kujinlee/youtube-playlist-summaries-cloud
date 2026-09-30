---
name: proving-a-negative-by-interception-cannot-terminate
description: "FIRES-WHEN: about to claim a guard proves an absence by intercepting calls — ⭐⭐ FIVE guards for one property each reported a pass they had not earned — intercepting an OPEN set. The retreat, pre-committed before the round that triggered it, is what stopped a sixth"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 227fd546-5a6f-429b-bcf1-09fc12283325
  modified: 2026-09-16T00:44:37.085Z
---

One property — *"the `/src/` caller consults the world exactly once"* — took **five** guards on
PR #310, and **every one reported a pass it had not earned**:

| attempt | defeated by |
|---|---|
| refuse env reads via `get` | `dict()`, `len()`, `for k in` |
| count env reads via `get` | `SRC_ROOT_ENV in os.environ` |
| count via eight surfaces | `setdefault`, `pop`, `repr()`, `==`, `len()` |
| stub the probe, forbid the env outright | calling the stubbed probe **twice**; `os.environb` |
| **static** source check, "never names an env API in any spelling" | `_probe = src_root`; `from os import environ as _ENV`; `posix.environ`; an import-time cache |

**Why:** each tried to prove a NEGATIVE by INTERCEPTING the world, which requires enumerating the
surfaces it is reachable through — an **open** set. ⛔ **And two members can never be closed:**
`os.environb` and a subprocess reading the inherited env go to the **C-level environ**, beneath
anything a Python object swap can reach.

⚠ **Attempt 5 is the one that settles it, because I wrote an architecture review arguing it was
structurally different** — asking statically over "a bounded region of code we own" makes the set
closed. **Wrong.** The *region* is bounded; the set of ways to NAME the environment from inside it is
not. It was the same denylist-over-an-open-set, relocated to source text, and it fell in one round.

**Why:** the argument that would have stopped me was already in hand — a reviewer had given the
C-level-environ mechanism a round earlier. I weighted my own induction from four failures over their
mechanism. A conclusion reached twice by different routes beats one you argued for.

**How to apply:**
- Before writing a guard that proves *"nothing else does X"*, ask **is the set of ways to do X
  closed?** If you are enumerating, it is not, and you are on attempt 1 of N.
- ⭐ **PRE-COMMIT THE RETREAT IN WRITING, IN THE ROUND DOCUMENT, BEFORE THE ROUND THAT MIGHT TRIGGER
  IT RUNS.** That is the only reason the sixth attempt did not happen — by the time the evidence
  arrived the decision was made, so there was nothing left to rationalise. I *would* have argued.
- The retreat is not a loss: **state what IS guarded and what is NOT, and verify BOTH lists by
  mutation.** An unguarded property that says so beats a guard reporting an unearned pass — a false
  entry in the *guarded* column is just the next false coverage claim. The opposite reviewer
  confirmed both lists: guarded examples died, every named escape survived.
- A whitelist over a region *would* be closed ("may name only these tokens") — the one option not
  tried. Recorded, not planned.

See [[a-second-implementation-of-one-rule-drifts]], [[assert-the-property-not-the-mechanism]],
[[a-framing-widened-to-fit-is-no-longer-a-claim]], [[gates-detect-defects-not-design]],
[[a-filed-finding-s-proposed-fix-is-a-hypothesis]].

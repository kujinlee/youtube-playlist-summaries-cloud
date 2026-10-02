# Architecture review — 2026-10-01 — the wiring class, scoped

**Armed by THRASHING, not a count.** `dev-process.md`: two consecutive rounds carrying findings
caused by the previous round's own fix, in one component. Round 8's Blocking was in a file round 7's
fold created; round 9's Blocking is in the call site round 8's fix created. Every other part of the
`semantic-recall-replication` fold converged. Put to the human as a selection card; they chose a
scoped review over folding per-instance.

**Scope: one question — why does each fix create the next instance?** Not a code review.

Independent read by a spawned agent with a REFUTE mandate, told in advance that the conclusion it
was most likely to reach (#213's AST guard) was already written down and therefore proved nothing.
Its brief: `<scratchpad>/arch-review-brief.md`; its full return: `<scratchpad>/arch-review-rest.md`.

⛔ **Every load-bearing claim below was re-derived by the coordinator. Two were wrong.** See
*Corrections*.

---

## The mechanism

> Every `main()` resolves its world from **module globals**, so `main` is the one function in a
> guard that no case can drive over a world it built. The repair this fold keeps applying — extract
> the rule into a function so its internals become testable — is applied to the **callee**. It
> shrinks the globals-coupled region but can never empty it, because the last act of `main` is to
> build the world and hand it over, and that act is below nobody. Each correct repair relocates one
> statement from *coverable by a case* into *the residue*, and the residue is exactly what no case
> reaches.
>
> **The class regenerates because the repair's direction is downward and the defect's home is
> upward.**

✅ **VERIFIED.** Every `main` in the three guards takes `argv` and nothing else, while reading 2–4
module globals. The fossil record is in the code's own docstrings, two generations deep:
`check-ratchet-contract.py:219` *"EXTRACTED FOR THE WIRING, not for tidiness"*, then one level out
at `:990` *"EXTRACTED TO MAKE THE WIRING TESTABLE — round 8's two Blockings"*. Two correct repairs,
each creating the next instance, each documented as a fix.

## The second mechanism, which is the harder half

**The fix was already in this repo, in a docstring, and did not travel.**
`scripts/check-ci-watched.py:860` — ✅ verified verbatim:

```python
def main(argv: "list[str] | None" = None, stream=None) -> int:
    """... Extracting `payload_from` was only half the repair; the line that CALLS it was still
    unreachable, which is the same "unit coverage does not compose — mutate the CALL SITE" lesson
    this file already records, at the next layer out again.
```

That is this entire review's mechanism, written before round 1 of this fold, by someone who hit it
in another file and fixed it structurally. Nine rounds then re-derived fragments of it in prose.
**So the honest framing of the recommendation is *finish propagating a fix you already made*, not
*adopt a new architecture*.** It is also the one guard of 36 built this way, and the class has never
touched it — n=1, and the right n=1.

## Why #213's AST guard is the wrong instrument — measured, not argued

The agent implemented #213 as its row specifies and ran it. 11 entries demanded across the three
files (4 exist); **108 repo-wide**, 208 if widened — +9%/+18% on a 42-minute sweep.

| # | objection | measurement |
|---|---|---|
| 1 | **Its scope is the region the repair empties** | `check-ratchet-contract.py`: 2 demanded entries in `main`, **16 whole-file**. Round 8's extraction moved three consumptions into `assess`, where instance ⑹ now sits at `:1006` — outside the detector's subject. **It loses reach at exactly the rate the repair proceeds.** This is the objection that decides |
| 2 | **It misses the newest instance three ways** | `_env` is in `observe()` not `main`, is a comprehension not a call, and flows to `subprocess.run(env=…)` not a verdict. Read literally it also misses ⑶, a for-iterator |
| 3 | **At least one demanded entry is unkillable** | severing `ratchets = discover_guards(…)` → rc 1 both ways; `evaluate` re-derives it. The harness refuses survivors, so the author is pushed into a contrived case or an escape |
| 4 | **Its subject is absent in 7 of 43 guards** | no `main()`; and #196 already puts `recall-llm.py` — which defines the rc constants both guards read — outside the population |

**Rejected alternatives, both argued from this repo's own prior measurements:**

- **Registry (N call sites → 1).** `check-ratchet-contract.py:159` already settled it: *"a registry
  is evadable by simply not registering… The filesystem cannot be evaded by omission."* An
  unregistered rule is a one-line deletion no case sees; restoring visibility needs a completeness
  check, which is #213 relocated.
- **Verdict-takes-functions.** `verdict(coverage_fn=lambda *_: [])` is exactly as invisible as
  `problems = []`. Nine of eleven instances are a result computed and not read; the one
  dropped-argument instance was only droppable because of a parameter default, already banned at
  `check-rc-contract.py:385`. It also re-merges the fetch into the rule, inverting the rule
  `check-ratchet-contract.py:317` paid for. *(Argued, not executed — labelled as such.)*

## Recommendation — D1 + D2

**D1 — give `main` its world as a defaulted parameter.** `def main(argv, root=ROOT)`; `__main__`
binds the real repo, a case binds a constructed one; behaviour unchanged. Built and measured for
`check-ratchet-contract.py`: four edits plus two cases reusing the world `ASSESS_WIRING_CASES`
already builds.

| severance | suite |
|---|---|
| none (control) | 54/54 green, live rc 0 |
| **round 9's Blocking** — `violations = []` | **52/54**, both cases named `[FAIL]` |
| `if len(other_v) > BASELINE:` → `if False:` | **53/54**, named `[FAIL]` |
| `discover_guards` result discarded | 54/54 — correctly green, measured benign |

⭐ **Row 3 is what decides between D1 and #213.** That statement is **not a call**, so #213 demands
no entry for it, and nine rounds of severance never touched it. The end-to-end case catches it
anyway. **A case that drives `main` covers the residue; a detector covers the shapes someone thought
to enumerate.**

D1 does **not** reduce the number of obligations — four rule results still need four assertions. It
changes their **kind**: a `case(...)` line written by reflex with feedback in seconds, instead of a
manifest entry authored blind against a 42-minute loop (#208).

**D2 — replace #213's 108-bit per-call-site subject with one bit per guard:** *does this guard's
`--self-test` invoke `main()` over a world the case constructed?* Ships as a pinned debt set like
`WIDENED_MANIFEST_DEBT`, not a baseline-0 ratchet. **Nothing moves `main`** — its subject is the one
region a correct repair cannot empty.

---

## ⛔ Corrections — the coordinator's hand-verification found two errors

**1. The population counts are wrong, and the error is in D2's favour.** Independently derived over
`scripts/check-*.py`:

| claim | review said | re-derived | verdict |
|---|---|---|---|
| guards | 43 | **43** | ✅ |
| with a `main()` | 36 | **36** | ✅ |
| `main` takes its world as a parameter | 1 (`check-ci-watched.py`) | **1**, same file | ✅ |
| suite drives `main()` | 5 | **7** | ❌ |
| `main` unreachable by any case | **31** | **29** | ❌ |

The review's own breakdown also double-counts: `check-ci-watched.py` both takes a parameter **and**
rebinds globals (6 sites), so its *"1 param + 5 rebinding"* exceeds its *"5 driving"*.

**2. D2's sub-condition 2 would FALSE-POSITIVE on the best-tested `main` in the repo — and this is
the serious one.** `check-fixture-variation.py` drives `main()` **fourteen times from
`_self_test()`**, each over a constructed path: `main([str(_f)])`, `main([str(_clean)])`,
`main([str(_fl)])`, `main([str(_nf)])`, … It points `main` at a built world **through `argv`
itself** — needing neither an extra parameter nor a global rebind, which are the only two routes
sub-condition 2 admits.

⭐ **So the recommendation's own detector would refuse the repo's best worked example of the
recommendation.** D2 must admit a third route — *the suite passes `main` an `argv` that names a
constructed path* — before it is written. Unamended, it ships with a known false positive on the
file that should be its exemplar.

⚠ Both errors point the same way: the exposure is **smaller** than stated (29, not 31) and more of
the repo already does the right thing than the review credits. The recommendation survives; its
costing does not.

**3. One live defect, verified.** `scripts/check-surface-recall.py:686` assigns `_saved_m =
globals()["MATCHER"]`. ✅ `grep -n "_saved_m"` returns **exactly one line** — assigned, never read.
The comment immediately above asserts a defence (*"the matcher is STAGED, so `defined =
_defined_codes()` cannot be severed to a literal dict and still pass"*) that the code does not
implement; round 9's H1a measured the consequence at 58/58 green. **Nothing in this repo checks
whether a comment's claim is true.**

---

## Decided but never written down

1. **`main` is exempt from the guard contract.** R1–R4 each name a **file**; none names a
   **region**. Consequence, measured: 29 of 36 `main`s no case has ever executed.
2. **A structural lesson is published by writing it in the docstring of the file that learned it.**
   Three lessons, three files, no file has all three — no-defaulted-parameters (missing from
   surface-recall, which re-derived it from scratch at `:588`, 400 lines from where it was already
   written), the ambient-environment case (missing from rc-contract — *that absence is instance
   #10*), a case that drives `main` (missing from ratchet-contract — *that absence is round 9's
   Blocking*).
3. **The verification stack is governed by nothing.** All 13 ADRs govern the product. None governs
   the verification stack — so there is no venue where *"a guard's `main` must be drivable"* could
   be **decided** rather than discovered (which is why `check-ci-watched.py` solved it privately),
   and none where a decision is protected from re-litigation. CONTEXT.md's Verification Stack
   section, created by architecture review #7 for the adjacent failure, carries **vocabulary only**.
4. **The three guards are a family and nothing says so** — one contract over one rc vocabulary,
   `_defined_codes` importing `defined_codes` by `spec_from_file_location`. No name, no shared
   fixture, no reconciler beyond two cases each written *after* a drift defect.
5. **"Wiring" is load-bearing and undefined.** Eleven instances, four review rounds, #213, this
   document — and no CONTEXT.md glossary entry. Architecture review #7's own finding was that an
   unnamed distinction recurs because no round can say it.

## Falsifiers

- **D1:** a later instance whose severed statement lives in the `main` of a guard that *already has*
  an end-to-end case driving `main` over a constructed world. Instances in guards without one
  confirm rather than refute and must not be counted against it.
- **D2:** a guard that **passes** R5 and still carries a live wiring defect found by severance; or
  the ranking failing to predict — sever one `main` consumption in ten guards, five from the 29 and
  five from the 7, and if survival rates do not differ sharply the bit measures nothing.
- **The propagation half:** if the three-lesson gap fills in without anyone building a channel, then
  *"there is no channel, only attention"* is wrong and the remedy is not structural.
- **The prediction offered for judgement:** fold r9's four findings per-instance without adding a
  `main`-driving case to `check-ratchet-contract.py`, and a twelfth instance appears in one of these
  three files within two rounds.

## Not measured

`--mutate .` not re-run by the reviewer (taken from the r9 documents). The unkillable fraction of
#213's 108 is unknown — one proved, a structural tell (callee re-derived downstream) screens 13 of
108, but n=1, the tell conflates "callee appears downstream" with "this value is recomputed"
(4 of its 13 hits are one generic `_run` helper), and completeness is unknown. D2's discrimination
test not run. D1 costed only for `check-ratchet-contract.py`; surface-recall expected larger because
three defaulted parameters must come out first. `.claude/settings.json` is deliberately outside
`HARNESS_TREE`, so production reachability of the hook is inherited from the r9 Codex half, not
reproduced.

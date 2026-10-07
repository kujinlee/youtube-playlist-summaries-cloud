# Architecture review — 2026-10-06 — the contrast/palette layer, scoped

**Armed by THRASHING, not a count.** `docs/dev-process.md`: two consecutive rounds carrying findings
caused by the previous round's own fix, in one component. Rounds 3 and 4 of PR #364 did that in the
contrast guard and its wiring — five of round 4's six Medium-or-above findings were defects in round
3's fixes. The per-finding evidence is
[`coordinator/unify-explainer-style-r4-coordinator.md`](coordinator/unify-explainer-style-r4-coordinator.md).
Folding was stopped by the repository owner in favour of this review.

**Scope: three questions.** Not a code review. Subject: `scripts/check-page-contrast.py`, its probe,
and its wiring into `scripts/page_chrome.py`.

⛔ **Every claim below that carries a number was produced by running something, and the command is
given.** Where I reasoned to a conclusion without executing it, it is labelled UNVERIFIED. Two of my
own intermediate measurements were wrong and are recorded in *Corrections to my own work* — both
were caught by checking a known positive, not by re-reading.

Worktree `wt-364`, branch `unify-explainer-style` at `e489a5ea`. Interpreter `/usr/local/bin/python3.12`
(3.12.9), matching CI's pin. All mutation work was done on **copies** under
`<scratchpad>/q1rep/`, never in the worktree — `an-instrument-that-edits-the-repo-corrupts-its-peers`.

---

## Q1 — Can `check-page-contrast.py`'s `main()` be driven by a case that BINDS WITHOUT A BROWSER?

### VERDICT: YES — and it costs TWO production lines. `MAIN_DEBT` is the honest state *today*, so the un-pin is unearned as it stands; but the repair is cheaper than the pin, so FIX IT rather than re-pin. ⛔ And backlog #239 MUST NOT be applied on its own: measured, it destroys the only binding the case has.

### The four-world table, reproduced

Severance applied to the single line `main()` resolves its corpus with:

```
-        pages = corpus(root / "docs" / "explainers")
+        pages = corpus(ROOT / "docs" / "explainers")
```

| world | result |
|---|---|
| control + browser | `94/94` rc=0 |
| severed + browser | `92/94` rc=1 — **KILLED** |
| control + no node | `94/94` rc=0 |
| **severed + no node** | **`94/94` rc=0 — SURVIVED** |

Command, per tree: `python3.12 scripts/check-page-contrast.py --self-test`, with the no-node worlds
run under `env -i PATH="<shim>:/usr/bin:/bin"` where the shim directory contains only a `python3.12`
symlink. Backlog #240's measurement is confirmed exactly.

### ⭐ A FIFTH WORLD, WHICH IS THE ONE CI ACTUALLY HAS — and #240 names the wrong one

`ci.yml:53-57` runs `actions/setup-node@v4` with `node-version: '22'`, and `ci.yml:394` runs
`python3 scripts/check-page-contrast.py --self-test`. **So CI has node and lacks Chromium.** That is
neither of the two worlds #240 measured, and its `FAILS IF` clause — *"leaves the suite green with
node absent from `PATH`"* — describes an environment the gate never runs in.

Measured by setting `PLAYWRIGHT_BROWSERS_PATH` to an empty directory (node present, no browser):

| world | result |
|---|---|
| control + node, no Chromium | `94/94` rc=0 |
| **severed + node, no Chromium** | **`94/94` rc=0 — SURVIVED** |

**#240's conclusion is right and its mechanism is wrong.** The mutant survives in CI for a different
reason than #240 gives: not `node is not on PATH`, but `the light browser run exited 1`. Both are
`CannotRun`, both return `2`, and the case asserts only the integer. The row needs amending so its
falsifier names the world the gate is in; as written, someone could satisfy it by installing node.

### Why the case cannot bind: `2` is a four-way overload

`main()` funnels every `CannotRun` into one `return 2`. The causes reachable here are *probe missing*,
*no pages to measure*, *node not on PATH*, *the browser run exited non-zero*, *zero elements*, and
*timeout* — plus an unreadable baseline. The case asserts `2`. So any severance that swaps one cause
for another is invisible.

The **reason strings already differ**, and `main()` already prints them. Captured via
`contextlib.redirect_stdout` around `main([], root=<constructed world>)`:

| tree | world | printed refusal |
|---|---|---|
| control | no node | `FAILED: no pages to measure — an empty corpus is not a clean result…` |
| severed | no node | `FAILED: node is not on PATH ([Errno 2] …)` |
| control | node, no Chromium | `FAILED: no pages to measure …` |
| severed | node, no Chromium | `FAILED: the light browser run exited 1: } /  / Node.js v20.18.2.` |

So **asserting the refusal REASON instead of the bare code binds in every world, with ZERO production
lines changed.** That is the cheapest repair available and it is worth stating because it bounds the
cost of everything else: nothing here needs a rewrite.

⚠ **Refutation of that cheap option.** It asserts a prose substring, which this repo's own
`assert-the-property-not-the-mechanism` lesson warns about — a reworded refusal breaks the case for a
reason unrelated to the property. I therefore do **not** recommend it as the final design, only as
evidence that a browserless binding exists.

### ⛔ Backlog #239 applied alone makes the case bind LESS — round 4's refutation, confirmed and stronger

#239 asks for `root=root` at the `measure()` call. Applied by itself:

```
-        samples = measure(pages, extra_css=extra)
+        samples = measure(pages, extra_css=extra, root=root)
```

| tree | world | rc | printed refusal |
|---|---|---|---|
| #239 + control | **full browser** | 2 | `FAILED: page-contrast-probe.mjs is missing…` |
| #239 + severed | **full browser** | 2 | `FAILED: page-contrast-probe.mjs is missing…` |

`94/94` in **both**. The probe refusal now fires before the corpus path, so control and severed
produce an **identical rc and an identical message even with a browser present** — the one world in
which the mutant previously died. Round 4 said this; it is stronger than it was stated, because the
loss is not confined to the browserless case.

**This is a live trap in the backlog.** #239 is filed 🟠 / size S with no cross-reference warning, and
anyone who picks it up as a one-line fix regresses the guard. It must be fixed *with* #240 or not at
all.

### The design that works: make the measurement injectable — 2 lines

```python
-def main(argv: list[str], root: Path = ROOT) -> int:
+def main(argv: list[str], root: Path = ROOT, measure_fn=measure) -> int:
...
-        samples = measure(pages, extra_css=extra)
+        samples = measure_fn(pages, extra_css=extra, root=root)
```

The defaults keep behaviour identical — verified: the shipped suite is `94/94` with the seam applied.
The second line also closes #239, and the parameter is what lets a case reach past the browser.

**Call-site cost, enumerated as the brief requires.** `main` has exactly one production caller, the
`__main__` guard at `:912`. `measure` has exactly one caller, the line above. The only other module
that imports this guard is `scripts/explainer-serve.py:1754`, and it imports the **pure** `contrast()`
only (`:1761`), never `main` or `measure`. **Zero external call sites change.**

Cases this enables — written, and run with **no node and no browser**
(`env -i PATH="<shim>:/usr/bin:/bin"`):

| case | asserts | killed by |
|---|---|---|
| C1 | `main()` measures exactly the pages in the constructed world | corpus severance |
| C1b | …and hands that same world to the probe launcher | **#239's defect** |
| C2 | the success line names the fraction of baseline measured | Q2's verdict revert |
| C3 | a partial run says `NOT A WHOLE-CORPUS PASS` | Q2's emptied branch |
| C4 | an unusable baseline is not reported as a clean pass | **red on shipped code — #242** |

Measured, each mutant against the five cases, all browserless:

| tree | cases passed | which failed |
|---|---|---|
| seam, control | 4/5 | C4 — *this is #242, a real open defect* |
| seam + corpus severed | 3/5 | **C1** + C4 |
| seam + verdict reverted | 4/5 | **C2** |
| seam + warning emptied | 3/5 | **C3** + C4 |
| seam, `root=` removed again | 4/5 | **C1b** |

C1's failure output lists the 58 real pages it wrongly reached, which is as legible as a failure gets.

⚠ **The bound on this, stated rather than hidden.** A `measure_fn` double covers `main()`'s
**decision** path — corpus resolution, palette selection, verdict rendering, refusal routing. It does
**not** cover the probe, and `a-mocked-boundary-tests-the-contract-you-imagined` is the reason to say
so plainly. The probe is already untested by the suite in CI (no Chromium), so this adds coverage
without removing any; it must not be described as testing the measurement. C1 is deliberately a
**recorder**, not a stub — it asserts the real page list `main()` computed, so the binding is to the
production value, not to a fixture.

### ⭐ The deeper finding: ADR-0014's enforcement is SHAPE-only, so "complies" asserts less than it reads

`check-main-drivable.py`'s D2 rule is a pure AST rule over source text. Run on three variants:

```
SHIPPED (worktree)     complies=True  route='param'  calls=2
SEVERED (root->ROOT)   complies=True  route='param'  calls=2
#239 THREADED          complies=True  route='param'  calls=2
```

**D2 reports full compliance for the severed file.** It can see *that* a case passes a constructed
world to `main`; it cannot see *whether the case can fail*. #240 is precisely the defect class the
shape rule admits — the same acknowledged limit as `enforce-selection-card.sh` ("SHAPE ONLY").

Population, from the guard's **own** entry point (`python3.12 scripts/check-main-drivable.py`):

```
45 guards on disk · 7 without main() · 38 in population
  11 drive main() over a constructed world — param 4, argv 3, rebind 9, subproc 1
  27 pinned as ADR-0014 identity debt
D2 OK
```

So **11 guards are recorded compliant, and that record is a shape claim about all of them.** Within
that population `check-page-contrast.py` is the only guard whose route is `param` alone, confirming
#240's note — derived as a subset: a 55-file superset glob showed exactly one `param`-only guard, and
the guard's 38-file population is a subset of it.

⛔ **This does NOT re-litigate ADR-0014, and it does not trigger its falsifier.** The ADR's falsifier
is *a severed statement inside the `main` of a guard that already has a case driving `main` over a
constructed world* — which would show the end-to-end case does not cover the residue. Here the case
**does** reach the statement; what fails is the **assertion's resolution**. That is a gap the
falsifier does not name, and it belongs in the ADR's *Consequences* as a note, not as a reversal.

### Recommendation and cost

1. Land the seam (**2 production lines**) + C1/C1b/C2/C3 (**~45 suite lines**) in one commit. Closes
   #239, #240, #241 and gives #242 its falsifier.
2. **Keep `check-page-contrast.py` out of `MAIN_DEBT` only if that lands in the same commit.** If the
   seam is deferred, re-pin it — on today's code the un-pin is unearned and #240 is correct.
3. Amend #240's `FAILS IF` to name CI's world (node present, Chromium absent), not a no-node runner.
4. Amend #239 with a ⛔ *do not fix alone* note referencing the measured regression above.

---

## Q2 — Is a verdict LINE a testable surface at all?

### VERDICT: YES, but NOT by extracting the verdict into a value. The decision is ALREADY a value — `coverage()` is pure and has 9 cases. What is untestable is the RENDERING, and the thing blocking a case is the browser between `main()` and its own output. The same two-line seam from Q1 fixes it. ⛔ A dataclass/structured-result rewrite is the WRONG answer here, and I can say why by measurement.

### Both #241 claims reproduced

| mutation | suite |
|---|---|
| verdict sentence reverted to its pre-fold wording (drops `{_cov}`) | `94/94` rc=0 |
| `if _missed:` → `if False:`, so `NOT A WHOLE-CORPUS PASS` never prints | `94/94` rc=0 |

And the manifest is blind to both. `scripts/mutations/check-page-contrast.json` holds **12** entries;
none of their `edits` touch `OK over`, `_cov`, `coverage(`, `NOT A WHOLE-CORPUS` or `_missed`:

```
python3.12 -c "import json; d=json.load(open('scripts/mutations/check-page-contrast.json')); ..."
  -> entries: 12 ; entries touching the verdict line: none
```

### Why the structural rewrite is the wrong answer

The obvious reading of "make the verdict a value a case can read" is to introduce a result object. But
the decision is **already** separated and already covered:

- `coverage()` is pure, returns `(measured, total, missed)`, and the suite has **9** cases on it,
  6 mutations / 6 killed (per #241's own note).
- `verdict()` is pure and cased.
- `population_notes()` is pure and cased.

The defect is not that the verdict is a string instead of a value. It is that **`main()` computes
`_cov` and prints it, and no case reaches `main()`'s `--against` branch** — because reaching it
requires `samples`, and `samples` comes from a browser. That is the *same residue* as Q1, which is why
#240 and #241 were filed as two findings and are **one defect wearing two severities**.

Measured proof that the seam alone suffices, no new types: with `measure_fn` injected and canned
samples, the verdict branch becomes reachable and both mutations die (C2, C3 above) — browserless.

⚠ **Refutation of my own recommendation.** What would make the seam the wrong choice? If the
`--against` block held *decision* logic that deserved its own pure function, the seam would be
covering a smell rather than removing it. I checked: between `load_baseline` and `return 0`, `main()`
contains no decision of its own — it calls `population_notes`, `verdict`, `coverage` and formats their
results. There is one conditional, `if _missed:`, which is a rendering choice. So there is nothing to
extract, and extracting a `(rc, lines)` reporter would *also* work but would catch **less**: it would
not catch Q1's corpus severance, because that happens before the baseline is loaded. The seam catches
both with fewer lines. That is the whole argument.

### #242 reproduced live, and it is the same residue again

Driving `main(["--against", <baseline>], root=<one-page world>)` with a real browser:

| baseline | rc | output |
|---|---|---|
| `{"samples": {}, "summary": {}}` | **0** | `OK over no baseline — no element crossed below AA…` |
| `{"summary": {}}` (samples absent) | **0** | `OK over no baseline — no element crossed below AA…` |

No advisory, no warning, exit 0. The guard measured 428 sites on one page and reported a clean pass
over a baseline it compared **nothing** against. This is the coverage fold's own failure mode in its
most extreme form, and C4 above is the falsifier it lacks — C4 is **red on the shipped code**, which
is the correct state for an open defect and means it must land with the fix, not before it.

### Recommendation and cost

The seam from Q1, unchanged — **no additional production lines for Q2**. Then #242's fix: make the
zero-coverage case say so. One branch in the rendering path (`_total == 0` with a baseline present →
advisory + non-zero, or an explicit `NOTHING COMPARED` line), ~4 lines, with C4 as its falsifier.

⚠ Whether #242 should exit non-zero or exit 0 with a loud advisory is a **decision, not a mechanical
choice** — `--against` an unusable baseline on a fresh clone is plausible, and `population_notes`'
docstring records that failing on a legitimately-absent derived page is how backlog #56's gate got
switched off. I have not chosen it. The advisory-plus-rc-0 form is the one consistent with the
existing design; the row should say which.

---

## Q3 — Is standard-palette-injection the right unification mechanism?

### VERDICT: INJECTION IS RIGHT — KEEP IT. ⛔ A REFUSAL IS REFUTED BY MEASUREMENT: it would be red on 58 of 58 pages on day one, which is backlog #56's measured switch-off. But the premise that aliasing "cannot close" is WRONG as stated, and the measurement that shows it is the most consequential thing in this review: the corpus contains **11 private colour vocabularies, not 91 loose names**, and the three names covering **45 of 58 pages** are declared in **one tracked file the standard has never been compared against**.

### The row's figures, reproduced from the guard's own `corpus()`

```python
pages = corpus(Path("docs/explainers"))          # the guard's rule, not a hand-rolled glob
private = {name for "--x:" decl in page} - set(page_chrome.STANDARD_LIGHT)
```

| measurement | value |
|---|---|
| `STANDARD_LIGHT` / `STANDARD_DARK` token names | 40 / 40, **key sets identical** |
| served pages (guard's `corpus()`) | **58** |
| pages declaring ≥1 token outside the standard set | **58 / 58** |
| distinct such names | **91** |

#238's authoritative figures confirmed exactly. `standard_palette_css()` emits the four selector forms
as documented (`:root`, the `prefers-color-scheme` media block, and both `data-theme` forms).

### The refusal mechanism, refuted

A refusal — *no served page may declare a colour token outside the set* — fails on every page today.
Scoping it to colour-valued declarations barely helps:

| measurement | value |
|---|---|
| private names carrying a colour value | **84 of 91** |
| pages declaring ≥1 colour-valued private token | **58 / 58** |
| private names that are NOT colours | 7 — `--emph --head --mono --prose --sans --serif` (+ a regex artefact) |

So a colour-scoped refusal is still **58/58 red on day one**. `docs/backlog.md` #56's measured verdict
is that such a gate gets switched off. **A blanket refusal is not available**, and this is the
measurement that settles it rather than an argument about it.

### ⭐ The distribution is bimodal, and that refutes "an open-ended chase"

| private colour tokens per page | pages |
|---|---|
| 2 | 1 |
| **3** | **47** |
| 4 / 7 / 8 / 12 / 13 / 19 | 1 each |
| 25 | 4 |

Aliasing the three most widespread names collapses the problem:

| names aliased | pages still declaring a private colour token |
|---|---|
| 0 | 58 |
| 2 | 58 |
| **3** | **13** |
| 30 | 7 |
| 84 | 0 |

45 of 58 pages are **fully** covered by three names. And grouping pages by their private-colour
vocabulary as a set:

| pages | names | vocabulary |
|---|---|---|
| **45** | 3 | `--em`, `--raise`, `--verified-br` |
| **4** | 25 | `--amber*`, `--c-com/-fn/-key/-num/-str/-typ`, `--code-*`, `--crim*`, `--indigo…` — **byte-identical across all four** |
| 1 each | 2–19 | nine further bespoke vocabularies, incl. the 19-name `--st-*` set |

**11 distinct vocabularies, not 91 independent divergences.** The unit of divergence is the
producing template, not the token name and not the page. That is why `page_chrome.py:85` records the
aliases being *"discovered one review at a time"*: the discovery channel was review findings on
rendered pages, where the population looks like 91 names across 58 files.

### ⭐⭐ And the dominant vocabulary has a tracked source the standard was never diffed against

`docs/explainers/_explainer-style.css` — **tracked**, 6,724 bytes:

| measurement | value |
|---|---|
| tokens it declares | 33 |
| of those, inside `STANDARD_LIGHT` | 28 |
| **outside the standard set** | **5 — `--em`, `--mono`, `--raise`, `--sans`, `--verified-br`** |

`--mono` and `--sans` are font stacks (values read: `ui-monospace,SFMono-Regular,…` and
`-apple-system,BlinkMacSystemFont,…`), so the **colour** gap is exactly **three names: `--em`,
`--raise`, `--verified-br`** — the same three that cover 45 of 58 pages.

**The closer nobody wrote**, run against the live tree:

```
assert colour-valued tokens of _explainer-style.css  ⊆  set(page_chrome.STANDARD_LIGHT)
  -> RESULT: FAIL
  -> names the shared stylesheet declares that the standard does not control:
     --em, --mono, --raise, --sans, --verified-br
  -> would it have caught all three dominant names at once? -> True
```

It is pure, needs no browser, reads two files already in the repo, and **goes red today**. It would
have produced all three names in one run; they were instead found across three review rounds, one
spelling at a time — the shape `page_chrome.py:85` already confesses to for the faint-ink role.

⚠ **Refutation of my own proposal, and an honest bound.** What would make this check the wrong
mechanism? If the 45 pages did not actually get those tokens from that stylesheet. They do not get
them *live*: the file is referenced only by `scripts/bootstrap-explainers.sh`, and the three names
carry **13, 6 and 4 distinct values** across the corpus — so pages hold **copies**, not a link. The
consequence is precise and must not be overstated: **the superset check is a LEADING gate governing
future pages; it does not retroactively unify the 45.** Those are unified by the palette absorbing
the three names, which is a separate change (below).

### The `--st-*` page: the thesis is still false for it, by construction

`2026-10-02-brief-project-status.html` still declares its full private vocabulary — **18 `--st-*`
names** (`--st-ink`, `--st-ink2`, `--st-ink3`, `--st-ground`, `--st-rule`, `--st-bad`, `--st-ok`, …).
The round-3 fold corrected one **value** (`--st-ink3` #6B7585 → #5E6878). It did not reconnect the
page to the layer. So PR #364's claim — *"one layer decides the common look and feel"* — remains
false for this page, and the repair that was applied was the kind that has to be repeated per page
per failure. This is the single clearest demonstration that the mechanism is sound and its
**enforcement at authoring time does not exist**.

### A real, unguarded near-miss

`page_chrome.py` records that the corrected faint ink *"clears all 18 grounds the palette now
defines, worst 4.53"*. `--em` and `--raise` are page-local **grounds** the palette does **not** define,
so they were never in that set. Measured with the guard's own `contrast()`:

| scheme | ink | ground | ratio |
|---|---|---|---|
| light | `--fg3` #5c6777 | `--em` #eae6de | **4.61:1** |
| light | `--fg3` #5c6777 | `--raise` #f0ebe3 | 4.83:1 |
| dark | `--fg3` #8892a2 | `--raise` #272523 | 4.86:1 |
| dark | `--fg3` #8892a2 | `--em` #26241f | 4.93:1 |

All pass. **The margin is 0.11 on the worst pair, and nothing checks it.** The palette's own claim is
true and silent about the grounds it does not define — which is the same shape as the claim this
review's Q1 is about. If the standard absorbs `--em` and `--raise` as grounds, this pair enters the
guarded set and the near-miss stops being luck.

### Recommendation and cost

1. **Keep injection.** It is the only mechanism that unifies values without editing 58 pages' rules,
   and the two alternatives are measured out: a refusal is 58/58 red (above), and a build step cannot
   reach pages already on disk, which is the `explainer-serve` send-time precedent #221 chose.
2. **Add the superset check** — colour-valued tokens of every shared token source ⊆ the standard set.
   ~15 lines with a `--self-test`; red today naming 3 colour names. This is the mechanical closer for
   the class `page_chrome.py:85` describes.
3. **Absorb `--em`, `--raise`, `--verified-br` into the palette** — 3 entries × 2 palettes = 6 lines.
   ⛔ **Values must be chosen by measurement, not by copying the stylesheet's**, using
   `--extra-css` against the baseline, which exists for exactly this. I have **not** run that
   comparison (it needs a value proposal first), so the contrast effect of this step is **UNVERIFIED**
   and it must not ship on the strength of this document.
4. **Pin the 11 vocabularies as a declared debt set**, in the established `MAIN_DEBT` /
   `WIDENED_MANIFEST_DEBT` form: the set may shrink, never grow. That gives the refusal's *value* —
   a new page cannot invent a twelfth `--st-*` vocabulary silently — without the day-one red that
   #56 measured getting switched off. The 4×25 vocabulary is one entry, not four.
5. ⚠ **#238's conclusion stands and is not weakened:** the live gate is still run by nothing, and
   none of the above changes that. Aliasing closing 45 pages reduces the *surface*; only running the
   gate *measures* it.

---

## What is not written down

Asked by `docs/dev-process.md` — the failure no tool can see. **No ADR governs this component**, and
the absence is load-bearing: four review rounds re-derived the same structural choices because there
was no venue in which they had been decided. These are the decisions I found living only in comments,
or nowhere:

1. **The palette unifies VALUES, not usage — pages keep deciding WHERE colour goes.** This is the
   whole reason the approach is tractable rather than a 62-page rewrite, it is the thing that
   distinguishes it from the 2026-10-02 failure, and it exists only as prose in `page_chrome.py:64-78`
   and backlog #221. It is exactly the kind of choice a later round re-opens.
2. **There are TWO sources of truth for the token vocabulary** — `page_chrome.STANDARD_LIGHT` (40) and
   `docs/explainers/_explainer-style.css` (33) — **and no rule relates them.** Nobody wrote down that
   the second exists as a style source; the measured consequence is 3 names across 45 pages and three
   review rounds of one-at-a-time discovery. *This is the single most consequential thing I found.*
3. **`rc=2` is deliberately overloaded across at least four CANNOT-RUN causes.** As a *contract* this
   is good and the docstring defends it. Its *testability* cost — that no case can distinguish the
   causes, which is the whole of #240 — was never recorded as a trade-off anyone accepted.
4. **The live gate is unwired on purpose.** The docstring says so honestly (*"Until something runs it,
   this guard protects nothing on its own"*), but a docstring is not a decision, and #238 is the row
   that exists because the choice was never put anywhere a reader would look for it.
5. **ADR-0014 compliance is a SHAPE claim.** "11 guards drive `main()` over a constructed world" does
   not mean 11 guards have cases that can fail, and D2 cannot tell the difference — proved above by
   it passing the severed file. The ADR's *Consequences* should say so; its decision is untouched.
6. **The corpus's divergence is per-TEMPLATE, 11 vocabularies.** Every document about #221 describes
   the problem as "62 pages, 139 token names". Nobody wrote that it is ~11 producers, two of which
   account for 49 of 58 pages — and the mechanism you choose depends entirely on which of those two
   framings you hold.

**Recommended venue.** One ADR for this component, carrying (1) and (2) with its falsifier being the
superset check, plus a *Consequences* note on ADR-0014 for (5). Items (3), (4) and (6) are findings
for the backlog, below. I have deliberately not drafted the ADR — per `dev-process.md` the spec is the
human gate, and (1) is a design decision the human already settled in different words ("current
standard is backlog style … for now having unified style"), so it needs recording, not deciding.

---

## Corrections to my own work

⛔ Recorded because `an-inference-stated-as-measured` is this repo's most expensive recurring defect
and the corrections for it have their own failure rate.

1. **My first "no node" world had node on it.** `PATH=/usr/local/bin:/usr/bin:/bin` still resolves
   `/usr/local/bin/node`. The run I would have reported as *severed + no node* was actually
   *severed + browser*, and it printed `92/94 rc=1` — which would have read as **"the case binds,
   #240 is wrong"**, the exact opposite of the truth, and it fails toward good news. Caught by
   checking the known positive (`command -v node`) before trusting the negative, not by re-reading.
   All browserless runs above use a shim directory containing only `python3.12`.
2. **My first guard population was the wrong set.** I globbed `scripts/*.py` and got *55 in
   population, 15 compliant*; the guard's own entry point reports *45 on disk, 38 in population, 11
   compliant*. I was measuring a different population with a second implementation of the guard's own
   rule — `a-second-implementation-of-one-rule-drifts`, which this repo has measured 17 times. Every
   population figure above is the guard's own output. The one inference I kept from the superset run
   is labelled as subset reasoning where it appears.

---

## Findings that should become work

⚠ Proposed wording only — `docs/backlog.md` is **not** edited by this review, per the brief.

**NEW — the seam (supersedes the repair path of #239, #240, #241; gives #242 its falsifier).**
🔴 *`main()`'s measurement is not injectable, so four open rows share one root cause and two of them
cannot be fixed independently.* Measured: adding `measure_fn=measure` to `main()`'s signature and
calling `measure_fn(pages, extra_css=extra, root=root)` — **2 production lines, zero external call
sites** (`main` has one caller at `:912`; `measure` has one; `explainer-serve.py:1754` imports only
the pure `contrast()`) — makes five cases bind with **no node and no browser**, killing the corpus
severance, #239's defect, the verdict revert and the emptied warning branch. Shipped suite stays
`94/94` with the seam applied. **FAILS IF:** any severance on a line `main()`'s `root` reaches, or on
the verdict line, leaves the suite green with node absent from `PATH` **and** with Chromium absent
while node is present. Files: `scripts/check-page-contrast.py`. Size: S–M.

**AMEND #240** — its `FAILS IF` names *"node absent from `PATH`"*, which is **not CI's environment**:
`ci.yml:53-57` installs node 22 and `ci.yml:394` runs the suite, so the gate world is *node present,
Chromium absent*. Measured in that world: control `94/94` rc=0, severed `94/94` rc=0 — still
SURVIVED, via `the light browser run exited 1` rather than `node is not on PATH`. The conclusion is
unchanged; the falsifier must name the world the gate is in, or it could be satisfied by installing
node.

**AMEND #239** — add ⛔ *DO NOT FIX ALONE*. Measured: applied by itself, control and severed both
return 2 with the **identical** message `page-contrast-probe.mjs is missing`, **with a full browser**
— `94/94` both. It removes the only world in which #240's mutant currently dies. It must land with
the seam.

**NEW — the two token sources are never compared.** 🔴 *`docs/explainers/_explainer-style.css` is a
tracked style source declaring 5 tokens the standard palette does not control, and nothing relates
the two sets.* Measured: it declares 33 tokens, 28 inside `STANDARD_LIGHT`, 5 outside — `--em`,
`--mono`, `--raise`, `--verified-br` (colour), `--mono`/`--sans` (font stacks). The three colour names
are declared by **45 of 58 served pages**, with 13, 6 and 4 distinct values respectively, and were
found across three review rounds one at a time. A pure superset check over the two files is ~15 lines,
needs no browser, and is **red today**. **FAILS IF:** a shared token source declares a colour token
outside the standard set and no check reports it. Files: `scripts/page_chrome.py`,
`docs/explainers/_explainer-style.css`. Size: S.

**NEW — the corpus has 11 private vocabularies, and the alias list was sized against the wrong
population.** 🟠 *"91 names across 58 pages" describes the symptom; the structure is 11 vocabularies,
two of which cover 49 of 58 pages.* Measured: 47 pages declare exactly 3 private colour tokens; the
3-name vocabulary covers 45 pages; a 25-name vocabulary is **byte-identical across 4 pages**; the
other 9 are one page each. Aliasing 3 names takes pages-with-private-colour-tokens from 58 to 13.
Proposed mechanism: pin the 11 vocabularies as a declared debt set that may shrink and never grow —
the refusal's value without the 58/58 day-one red that #56 measured getting switched off. **FAILS
IF:** a twelfth private vocabulary reaches `docs/explainers/` with nothing reporting it. Files:
`scripts/page_chrome.py`, `scripts/check-page-contrast.py`. Size: M.

**NEW — the standard's faint ink is unguarded on two grounds it does not define.** 🟡 Measured:
`--fg3` #5c6777 on `--em` #eae6de is **4.61:1** against a 4.5 floor — a 0.11 margin — and on
`--raise` #f0ebe3 is 4.83:1; dark is 4.93 and 4.86. All pass. `page_chrome.py` claims the value
*"clears all 18 grounds the palette now defines"*, which is true and silent about these two, because
they are page-local. Absorbing `--em`/`--raise` into the palette moves them into the guarded set.
**FAILS IF:** a palette ink lands on a ground declared by ≥40 served pages that no case checks.
Files: `scripts/page_chrome.py`. Size: S.

**NEW — `--st-*` page still bypasses the layer.** 🟠 `2026-10-02-brief-project-status.html` declares
**18 `--st-*` token names** and is unchanged structurally; round 3 corrected one value
(`--st-ink3` #6B7585 → #5E6878). PR #364's thesis is false for this page by construction, and the
repair applied is the per-page-per-failure kind. **FAILS IF:** a served page declares a wholly private
colour vocabulary and reaches `docs/explainers/` with nothing reporting it. Files:
`docs/explainers/2026-10-02-brief-project-status.html`, `scripts/page_chrome.py`. Size: S–M.

**NEW — ADR-0014 compliance is shape-only; add it to Consequences.** 🟡 Measured: `classify()` returns
`complies=True, route='param', calls=2` for the shipped file, the `root→ROOT`-severed file **and** the
#239-threaded file. D2 sees that a case passes a constructed world, never that the case can fail. The
guard's own population is 38 with **11 compliant**, so the ledger's "11" is a shape claim about 11
guards. Not a refutation of the ADR and **not** its stated falsifier (the case here does reach the
statement; its assertion is too coarse). **FAILS IF:** ADR-0014's Consequences claim or imply that D2
compliance means a case can fail. Files: `docs/adr/0014-a-guards-main-is-drivable.md`,
`scripts/check-main-drivable.py`. Size: S (documentation).

**#243 — two of its four claims independently confirmed.** The grounds predicate
(`explainer-serve.py:1759-1761`) iterates **13** grounds, not "18 light / 16 dark", and
`set(STANDARD_LIGHT) == set(STANDARD_DARK)` is `True`, so a light/dark split of that claim is
impossible. Backlog **#220 is absent** from `docs/backlog.md` (rows 215-219 and 221-225 are present;
220 is the only gap in the sequence) while `check-page-contrast.py:9` cites it. ⚠ Precision: #221
states it *supersedes* #220, so this is a **deleted row with no tombstone**, not an invented
citation — the fix is to retarget the docstring to #221, not to re-file #220.

---

## Method notes

- Mutations were applied to **copies** under `<scratchpad>/q1rep/{control,severed,thr-*,seam*,q2a,q2b}`,
  each a tree of `scripts/{check-page-contrast.py,page_chrome.py,page-contrast-probe.mjs}` plus
  `docs/explainers/` and a `node_modules` symlink. The worktree was never mutated.
- Browserless runs: `env -i PATH="<shim>:/usr/bin:/bin" HOME="$HOME"`, shim containing only a
  `python3.12` symlink, with `command -v node` confirmed ABSENT **and** the guard confirmed to print
  `node is not on PATH` before any conclusion was drawn from that world.
- CI-shaped runs: `PLAYWRIGHT_BROWSERS_PATH=<empty dir>` with node present.
- `check-plan-code.py --mutate .` was **NOT** run (1,407 entries, ~29 min), per the brief. **So no
  claim here is backed by the repo's own mutation sweep**, and the new cases proposed above have not
  been through it. The 12 existing manifest entries for this file were read, not executed.
- Corpus and token measurements call `check_page_contrast.corpus()` and `page_chrome.STANDARD_LIGHT`
  directly, never a hand-rolled filename or token rule — #238 records the coordinator paying for
  exactly that substitution (58/91 vs 59/95, the delta being `frag-plan-mode-question.html`).

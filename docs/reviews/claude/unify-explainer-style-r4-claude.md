# Round 4 — Claude adversarial half · PR #364 `unify-explainer-style` (backlog #221)

**Subject:** round 3's FOLDS, at `c0200f60` plus the uncommitted `check-main-drivable.py` docstring
fix and the uncommitted `docs/backlog.md` #238 amendment.
**Interpreter:** `/usr/local/bin/python3.12` (CI's pin) throughout.
**Mandate:** refute, not confirm. Codex's round-4 half reported no deliverable findings; this half
set out to break the folds and did.

---

## The one question this round had to answer

Round 3's HIGH 1 was *a green that did not state its coverage*. The fold is two `print` statements
in `main()`. **So the only question that matters is whether anything can now tell those two
statements from the sentence they replaced** — and the answer is no, measured.

```
CONTROL  delivered, 3.12                                         94/94  rc=0
MUTANT   verdict line reverted VERBATIM to the pre-fold sentence  94/94  rc=0   *** SURVIVED ***
MUTANT   `if _missed:` -> `if False:` (warning deleted)           94/94  rc=0   *** SURVIVED ***
```

Nine cases were added for this fold. All nine land on the helper beside the change, not on the
change. Against `coverage()` itself the coverage is genuinely good — six mutations, six killed:

```
KILLED  len(total & seen) -> len(total)     "…reports partial coverage", "…reports zero coverage"
KILLED  len(total) -> len(seen)             "…reports partial coverage"
KILLED  sorted(total - seen) -> []          4 cases, incl. the pre-existing VANISHED advisory
KILLED  total & seen -> total | seen        2 cases
KILLED  seen = {…} -> seen = set()          6 cases
KILLED  (0, 0, []) -> (0, 1, [])            "coverage with no baseline … claims nothing"
```

That is the shape this repository has already paid for and written down: *unit coverage does not
compose — mutate the CALL SITE.* The helper is pinned; the behaviour the High asked for is not.

---

## Findings

### HIGH 1 — the HIGH 1 fold can be reverted verbatim with the suite green and the mutation sweep silent. DELIVERABLE (`scripts/check-page-contrast.py`)

**Claim.** The deliverable behaviour of round 3's HIGH 1 fix is `scripts/check-page-contrast.py:882`
(the coverage-carrying success line) and `:883-885` (the `⚠ NOT A WHOLE-CORPUS PASS` line). Neither
is asserted by any case, in this file or anywhere in the repository, and neither has a mutation-
manifest entry. Reverting `:882` to its exact pre-fold text leaves `94/94`; deleting the warning
leaves `94/94`.

**Evidence.**
- `scripts/check-page-contrast.py:882`, `:883-885` — the two prints.
- `scripts/check-page-contrast.py:735-764` — the seven new cases, every one against `coverage()`.
- `scripts/check-page-contrast.py:766-781` — the two remaining new cases are the D2 `main()` pair
  (see HIGH 2) and assert an integer, not output.
- `scripts/mutations/check-page-contrast.json` — 12 entries; `grep -n 'OK over\|WHOLE-CORPUS\|coverage'`
  over it returns **nothing**. The fold commit `c0200f60` does not touch the manifest (last three
  commits touching it are `de1b66eb`, `30e5b1b9`, `ad4885a1`), so `--mutate .` cannot see the fold
  either.
- `grep -rn "OK over\|WHOLE-CORPUS"` across `*.py *.mjs *.ts *.json *.yml` outside `docs/reviews/`
  finds only the two producing lines themselves.
- Mutation runs above, each against a proved-green control in the same environment.

**Why this is High and not a note.** The round-3 finding was not "`coverage()` does not exist" — it
was "the verdict omits its denominator, and a verdict that omits its denominator is read as
whole-corpus by every reader including the one who wrote it". A fix whose own falsifier is absent
restores the state before the finding on the next refactor that touches `main()`, and the suite will
say 94/94 while it happens. The repository's rule is *what observation would make this FAIL?* — for
this fold, none.

**Proposed fix — HYPOTHESIS.** Extract the sentence, then case it:
`def verdict_line(measured: int, total: int) -> str` and
`def shortfall_line(n_missed: int) -> str | None`, both PURE, called from `:882-885`; cases for
`(35420, 65370)`, `(2, 2)`, and the `total == 0` path (see MEDIUM 1), plus manifest entries naming
each. That also removes the `_total == 0` hole and the stdout noise in LOW 1 with the same change.

---

### HIGH 2 — the case that un-pinned this guard from `MAIN_DEBT` is unfalsifiable in CI, which is the only place the suite runs as a gate. DELIVERABLE (`scripts/check-page-contrast.py`, `scripts/check-main-drivable.py`)

**Claim.** `main([], root=_rootA) == 2` and `main(["--raw"], root=_rootB) == 2` (`:777`, `:781`) are
killed by severing `root` **only when a Playwright browser happens to be installed on the machine
running the suite.** In a CI-shaped environment — node present, no browser, which `ci.yml:385-386`
states is the runner — the severance survives with the suite green. The cases assert the integer
`2`, and `2` is the return of at least four distinct CANNOT-RUN paths, so the assertion cannot
distinguish which world `main()` read.

**Evidence.** Severance applied to `scripts/check-page-contrast.py:811`
(`corpus(root / "docs" / "explainers")` → `corpus(ROOT / …)`), run over a world whose `ROOT` holds
the real `docs/` and `scripts/` by symlink:

```
CONTROL   delivered, browser present                       94/94  rc=0   refusal: "no pages to measure"
SEVERED   browser present                                  92/94  rc=1   both D2 cases FAIL   (killed)
SEVERED   no browser (probe exits 1, as on the CI runner)  94/94  rc=0   *** SURVIVED ***
CONTROL   no browser                                       94/94  rc=0   refusal: "no pages to measure"
```

The severed no-browser run's refusal text changes to `the light browser run exited 1: …` — the rc
does not, and the rc is all the case reads.

**And this guard has no second route.** Re-running `check-main-drivable.classify` over the
population: `check-page-contrast.py` is the **only** D2-compliant file whose route set is `['param']`
alone. Every other compliant guard carries `rebind` and/or `argv` as well — routes that substitute a
module global and therefore honour the constructed world regardless of ambient capability. So this
guard's entire D2 compliance rests on the pair measured above.

- `scripts/check-main-drivable.py:131-139` — the un-pin comment, whose load-bearing sentence is
  *"over an EMPTY constructed world `main()` returns 2 … with no node and no browser."* That
  sentence is **true**, and it is not the same claim as *the case binds `root`*.
- `scripts/check-main-drivable.py:81` and `.github/workflows/ci.yml:405` — now state 27 of 38 / 11
  driving, a figure produced by this case. `D2 OK` is reported from source text, so it stays green
  in CI either way; what is vacuous there is the compliance it certifies, not the gate.

**⛔ Round 3's still-open MEDIUM 1 is NOT the fix for this, and applying it makes the case worse.**
I measured the obvious repair (`samples = measure(pages, extra_css=extra, root=root)` at `:825`):

```
MEDIUM-1 fix, NOT severed, no browser   94/94  rc=0   refusal: "page-contrast-probe.mjs is missing"
MEDIUM-1 fix, SEVERED,    no browser    94/94  rc=0   *** SURVIVED ***
```

With `root` threaded, the refusal fires from `measure`'s probe check (`:366-367`) before the pages
check is ever reached — so the case stops exercising the corpus path at all while still asserting
`2` and still reporting green. **Fixing the parameter does not fix the assertion.**

**Proposed fix — HYPOTHESIS.** Assert the refusal *sentence*, not the code: capture stdout
(`contextlib.redirect_stdout`) around both calls and assert the message contains
`no pages to measure` for world A. That is falsified by the severance in every environment, and it
also removes LOW 1. Thread `root` into `measure()` as well (round 3's MEDIUM 1) — but after the
assertion changes, not instead of it, and with the case's expected sentence updated to whichever
refusal the new order produces.

**Codex's round-4 half concluded this case "proves the corpus root path is read, but correctly does
not claim to cover the severance."** The first half of that is what fails: it does not prove the
corpus root path is read in the environment that runs it. Codex ran
`check-page-contrast.py --self-test` on this machine, where a browser is installed; the no-browser
leg is the one nobody ran, and it is CI.

---

### MEDIUM 1 — `--against` a baseline with no usable `samples` prints `OK over no baseline` and exits 0, with no advisory. DELIVERABLE (`scripts/check-page-contrast.py:880`)

**Claim.** `_cov = … if _total else "no baseline"` turns a zero-site comparison into a reassuring
pass. `load_baseline` (`:303-315`) performs no validation, `population_notes` returns `[]` because
nothing vanished, and `verdict` flags only sites below their own threshold — so over a clean corpus
the gate reports `OK` having compared nothing. The phrase is also false: a baseline *was* given and
read.

**Evidence.** Live runs over a constructed world (one served page, stub probe, both schemes clean):

```
real baseline      ->  OK over 100.0% of baseline (2 of 2 site(s)) …                   rc=0
{"samples":{}}     ->  OK over no baseline — no element crossed below AA …             rc=0
{"hello":"world"}  ->  OK over no baseline — no element crossed below AA …             rc=0
```

This is the fold's own failure mode in its worst form — 0% coverage, the word `OK`, and the
`⚠ NOT A WHOLE-CORPUS PASS` line silent because `_missed` is empty when `_total` is empty. The
file already applies the opposite rule to its own inputs in `measure`: *"a zero over
a non-empty corpus is a probe that did not work"* (`:389-392`).

**Reachability, stated as a bound not a vibe:** it needs a baseline with no usable `samples` **and**
a corpus with no new below-AA sites. `--write-baseline` cannot produce the first unless every site
is gradient-backed; the realistic route is `--against` pointed at the wrong gzipped JSON, or a
format change. Medium, not High, on that bound.

**Proposed fix — HYPOTHESIS.** `if _total == 0: print("FAILED: baseline <path> contains zero
comparable sites. TREAT THIS AS NOT RUN."); return 2` — the file's own CANNOT-RUN contract, which
`check-rc-contract.py` and `check-surface-recall.py` already govern for this script (both green
today, 6 codes declared).

---

### MEDIUM 2 — the fold's own comment states a MEASURED total and percentage that the baseline in the repository refutes, and that the code two lines below contradicts. DELIVERABLE prose (`scripts/check-page-contrast.py:871-872`)

**Claim.** The new comment reads *"29,950 of **66,732** baselined sites were not measured.
MEASURED: that green covered **55.1%** of its own baseline."* Both figures are wrong.

**Evidence.** `docs/contrast-baseline.json.gz` in this tree holds **65,370** sample keys (its own
`summary.scored` is 65,370; `summary.elements` 65,508). So the figure is 35,420 of 65,370 = **54.2%**
— which is what `c0200f60`'s commit message says, what the line at `:882` computes, and what the
live gate prints. 66,732 is not the baseline's size, nor `elements`, nor `scored`.

**Why it is worth a finding.** The fold's own stated principle is *one computation, two readers*
(`:194-196`). The comment and the code are two readers of the same number and they disagree, inside
the fix for a finding about exactly that. It changes no behaviour, which is why it is Medium rather
than High; it is the `an-inference-stated-as-measured` shape, and the next reader to quote 55.1% has
no way to know which figure was derived.

**Proposed fix — HYPOTHESIS.** Replace both numbers with 29,950 of 65,370 and 54.2%, and name the
ref (`c0200f60`) and the artefact (`docs/contrast-baseline.json.gz`, `summary.scored`) the figures
come from.

---

### MEDIUM 3 — the uncommitted #238 amendment attributes to "a different tree state" a discrepancy that reproduces deterministically from this tree, and the method it canonises is the one this guard's own mutation manifest forbids. DELIVERABLE prose (`docs/backlog.md:265`, uncommitted)

**Claim.** The amendment says *"ROUND 3 RE-DERIVED 58 PAGES / 91 NAMES AND I CANNOT REPRODUCE THAT
FROM THIS TREE … most likely a different tree state during the round."* Both figures reproduce
from `c0200f60`, with no tree difference. They are two different **population rules**:

```
*.html minus *.fragment.html   (the row's stated recipe)  ->  59 pages, 95 distinct private names
check-page-contrast.corpus()   (the guard's own rule)     ->  58 pages, 91 distinct private names
difference: exactly one file — frag-plan-mode-question.html
names only that file contributes: --bad, --bad-bg, --measured, --ok-bg   (4 -> 95 vs 91)
```

`frag-plan-mode-question.html` has no `name="viewport"`, so `is_served_page` (`:439`) excludes it.
The row's recipe is a **filename rule**, and this guard's docstring records that rule being measured
wrong on this exact file: *"A FILENAME rule was first and missed `frag-plan-mode-question.html` … which
promptly turned up as the corpus's worst result at 1.00:1 because a chromeless fragment has no
palette"* (`:428-431`). `scripts/mutations/check-page-contrast.json` carries an entry named *"the
corpus rule accepts fragments, so chromeless files with no palette are measured"* — the manifest
guards against precisely the misclassification the row now publishes as its measurement.

**Why this matters more than the 4-name delta.** The row was amended specifically to add provenance,
and the amendment closes an open discrepancy with an invented cause ("a different tree state") in a
paragraph headed **MEASURED**. A future reader has no reason to re-open it. The conclusion (aliasing
cannot close) is unaffected at either figure, as the row says.

**Proposed fix — HYPOTHESIS.** Replace the "cannot reproduce" sentence with the two rules and the
one file, and state the guard's `corpus()` figure (58 / 91) as the primary, since that is the
population the gate actually measures.

---

### MEDIUM 4 — "FILED, NOT FOLDED" is true of one of seven deferrals. NOT deliverable (process)

**Claim.** `c0200f60`'s message says round 3's MEDIUM 1 and six Lows were filed. The freeze's
disposition rule is *everything else files as a backlog row*. Only LOW 5 reached the backlog (the
#238 amendment). No row exists for MEDIUM 1 or Lows 1, 2, 3, 4, 6.

**Evidence.** `docs/backlog.md` max row id is **238**; the only row this PR touched after round 3 is
#238. Greps over `docs/backlog.md`: `threaded into` 0, `measure(pages` 0, `18 grounds` 0,
`hex STRING` 0, `14 keys` 0, `#220 does not` 0.

**Mitigated, not lost:** all seven are written up in the committed
`docs/reviews/claude/unify-explainer-style-r3-claude.md:101-267`. Nothing in the repository reads a
review doc for unclosed findings, which is what the backlog row is for — and HIGH 2 above shows
MEDIUM 1 is no longer only a docstring overclaim.

**Proposed fix — HYPOTHESIS.** One row covering MEDIUM 1 + HIGH 2 together (the `root`/assertion pair
in `check-page-contrast.main`), and one row batching Lows 1–4 and 6 as prose-accuracy items with
their `file:line`.

---

### LOW 1 — the "pure rules only" self-test now opens with two `FAILED:` lines. DELIVERABLE (`scripts/check-page-contrast.py:771-781`)

`python3 scripts/check-page-contrast.py --self-test` now prints, as lines 1 and 2 of its output,
`FAILED: no pages to measure — … TREAT THIS AS NOT RUN.` twice; `94/94 self-test cases passed` is
line 4. The CI step is named *"Contrast harness self-test (pure rules only — NOTHING runs the live
gate)"* (`.github/workflows/ci.yml:393`). Nothing greps the step for `FAILED`, so this is cosmetic —
but the repository's own position is that a channel can be weaker than the gate, and a green step
whose log opens `FAILED:` twice teaches the reader to skim past the word. **HYPOTHESIS:** the
stdout capture proposed in HIGH 2 silences it as a side effect.

### LOW 2 — the shortfall line prescribes one remedy for every cause. DELIVERABLE (`scripts/check-page-contrast.py:884-885`)

`⚠ NOT A WHOLE-CORPUS PASS: N baselined site(s) were not measured … Regenerate the derived pages and
re-run.` A missed site can also be a deleted page, a renamed selector, or a shifted sibling ordinal
— for those the instruction is wrong and the ADVISORY two lines above (which names the pages) is the
part that tells the truth. **HYPOTHESIS:** "…were not measured (see the ADVISORY above for which
pages). If they are the gitignored derived pages, regenerate them and re-run."

---

## Round 3's still-open items — disposition checked

| Item | Verdict |
|---|---|
| MEDIUM 1 — `root` not threaded into `measure()` (`:825`) | **Correctly deferred under the freeze, but escalate.** Still live; and HIGH 2 measures that the obvious fix leaves the D2 case *less* bound, not more. It is now half of a High, not a standalone docstring overclaim. |
| LOW 1 — "18 grounds light / 16 dark" | Correctly deferred (Low, prose). Unchanged. |
| LOW 2 — two `--fg2 > --fg` cases compare hex strings | Correctly deferred. Unchanged. |
| LOW 3 — "14 keys" vs a 21-tuple | Correctly deferred (pre-existing, instrument). Unchanged. |
| LOW 4 — `check-page-contrast.py:9` cites backlog #220 | Correctly deferred. ⚠ Note `docs/backlog.md:248` (row #221) *also* cites #220 as a row it supersedes, so the dangling citation is in two places, not one. |
| LOW 5 — #238's population figure | Folded into the #238 amendment — **and the fold is MEDIUM 3 above.** |
| LOW 6 — the `NO-ENTRY:` reason | PR body; not re-checked (outside the tree). |

## Checked and clean — stated so the next round need not repeat it

- **The `coverage()` refactor is behaviour-preserving for `population_notes`.** Differential test,
  old implementation vs delivered, 4,000 randomised inputs (dict baselines, `None` baselines,
  baselines with no `samples` key, 0–12 samples, 0–25 baseline keys, seed 7): **0 disagreements** —
  ordering, the `by_page` top-5 selection, the empty-baseline path and the zero-sample path all
  identical. The one input shape that diverges is `baseline["samples"]` as a **list with a repeated
  key** (old counts it twice, new once); `baseline_payload` (`:290`) builds a dict and cannot produce
  it, and the new behaviour is the correct one. Not a finding.
- **The denominator at `:880` is the right one for the sentence it is in.** `measured = |total ∩ seen|`
  over `total = |baseline samples|` is "the fraction of the baseline this run compared", which is
  what the words say. Sites *not* in the baseline are checked at full strength by `verdict`'s
  new-element branch, so the line understates the run's reach rather than overstating it. 54.2% =
  35,420 / 65,370 reproduces against the baseline file.
- **`--write-baseline` never reaches the new line** (`main` returns at `:850`), and the live run
  confirms no `OK over` line on that path. `--raw --against` reaches it with the same arithmetic;
  the raw view is strictly worse than the palette view (112 vs 7 below-AA pairs per round 3), so
  it fails rather than greens. I did **not** run `--raw --against` over the real corpus.
- **The fixture variation is real where it can be.** `check-fixture-variation` green (841 parameters,
  64 files). For `coverage`, severing `samples` to `set()` kills six cases, so the parameter is
  load-bearing, not merely varied. For `main`, `root` is varied across two distinct worlds and
  `check-fixture-variation` is satisfied — **which is the limit of that guard: it enforces that call
  sites vary a parameter, and cannot see that the assertion cannot distinguish the variation.**
  That is HIGH 2.
- **The declared counts agree with the runs.** `check-page-contrast.py --self-test` 94/94 under 3.12
  and the docstring says 94; `check-selftest-counts.py` green over 52 scripts. `MAIN_DEBT` holds
  exactly 27 names, `check-page-contrast.py` is absent from it, and `check-main-drivable.py` reports
  `45 on disk · 7 without main() · 38 in population · 11 driving · 27 pinned · D2 OK` — matching the
  uncommitted docstring fix (38 / "one of the 11") and `ci.yml:405`. Codex's round-4 Low is correctly
  fixed; I searched the class and found no other stale 37/10 figure in `scripts/` or `.github/`.
- `check-rc-contract.py` and `check-surface-recall.py` both green.

## Not done

- `check-plan-code.py --mutate .` unsharded (1,407 entries) — out of budget per the brief. The
  manifest gap in HIGH 1 was established by reading the manifest and grepping it, not by running the
  sweep.
- The live `--against` gate over the real corpus with the derived pages regenerated. Round 3
  measured that path (exit 1, ten new below-AA); I did not re-run it, and HIGH 1/HIGH 2 do not
  depend on it.
- LOW 6 (PR body text) — outside this tree.

---

## NOT CONVERGED

Two Highs in the deliverable, both introduced by round 3's own folds, both measured rather than
argued:

1. the HIGH 1 fold has no falsifier anywhere — reverting it verbatim leaves 94/94 green and the
   mutation manifest has no entry for it;
2. the case that un-pinned this guard from `MAIN_DEBT` survives severance of the very parameter it
   exists to bind, in the no-browser environment that is the only one where the suite runs as a
   gate — and round 3's still-open MEDIUM 1, applied as written, makes it bind less.

Both fold under the freeze. The two Highs share one repair (assert the sentence, not the integer,
with stdout captured), which also closes LOW 1. MEDIUM 1–4 and LOW 2 file as backlog rows.

⚠ **This is the second consecutive round whose findings are defects in the previous round's fixes**
(round 3's two findings were defects in decisions made earlier the same session; round 4's two Highs
are defects in round 3's folds, in the same component). That is one round short of the thrashing
arming condition in `docs/dev-process.md` — if round 5's findings are again caused by round 4's
fixes in `check-page-contrast.main`, answer *thrashing or prose floor?* in that round's document
with per-finding evidence rather than opening round 6.

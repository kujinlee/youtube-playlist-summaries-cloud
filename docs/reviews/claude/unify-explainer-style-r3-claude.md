# unify-explainer-style — round 3, Claude adversarial half

Worktree `wt-364`, branch `unify-explainer-style` at `a0a434b6` (⚠ **unpushed** — `origin/unify-explainer-style`
is at `7009896a`). Every python invocation `/usr/local/bin/python3.12`. No tracked file modified; the four
gitignored derived pages were regenerated with explicit `--out` for one measurement and then deleted
(`git status --porcelain` empty, before and after). `docs/explainers/questions.md` not touched.

**1 High · 2 Medium · 6 Low.** Three are in the DELIVERABLE at Medium or above.

The High is not a defect the palette introduced — I exonerated the palette by measurement. It is that the
single piece of evidence this PR rests on was taken over 54% of its own baseline, and on the full corpus at
`HEAD` the same command exits **1**.

---

## What I attacked, and what survived

| Target from the handoff | Verdict |
|---|---|
| 1. "assume I got a third merge resolution wrong" | **No third wrong resolution.** All 7 union files checked; see *Merge audit* below |
| 2. `questions.md` untracked | **Correct.** `.gitignore:176` already ignores it; the only readers name `~/explainers/questions.md` (the symlink), never a tracked path |
| 3. the `MAIN_DEBT` pin | **REFUTED — Medium 2.** `main([], root=<constructed world>)` returns 2 with no node and no browser |
| 4. the fold (`--st-ink3` → `#5E6878`) | **SOUND.** Reproduces (5.26/4.97); dark half was already clear; no token missed. See *The fold* below |
| 5. #238's measurement | **Conclusion stands, figure does not re-derive — Low 5.** I get 58 pages / 91 tokens, not 59 / 95 |
| 6. declared sums 1407 / 38 / 28 | **Confirmed from the tools' own output.** `check-main-drivable.py`: "38 in population … 28 pinned"; `check-plan-code.py --self-test` 178/178 |

---

## Findings

### HIGH 1 — the gate's only green verdict was measured over 54% of its own baseline, and on the full corpus at `HEAD` it exits 1. DELIVERABLE (`scripts/check-page-contrast.py`)

**Claim.** `check-page-contrast.py:802` prints `OK — no element crossed below AA and none already failing got
worse` unconditionally, immediately after `population_notes` (`:190-215`, reached at `:792-793`) has reported
that almost half of the baselined sites were never measured. That OK line is the PR's central evidence, in
the commit message (*"the live gate exits **0**"*) and in the PR body (*"Clean-clone gate · **rc=0**"*). It is
true only of a 58-page subset.

**Evidence — both runs, same command, same commit.**

Run as a clean tree gives (`scripts/check-page-contrast.py:792`, `:802`):

```
contrast: 36920 measured site(s) … across 58 page(s)
  below AA: 90 of 36782 scored   worst: 2.06:1
  ⚠ ADVISORY — 29950 baselined site(s) were not measured this run
    (backlog-table.html x21252, dashboard.html x5678, goals.html x1602, features.html x1418).
  OK — no element crossed below AA and none already failing got worse        rc=0
```

29,950 of the baseline's 65,370 keys = **45.8% unmeasured**; `backlog-table.html` alone is **32.5%**. The four
absent pages are the four DERIVED, gitignored ones — the dashboard, the backlog, the goals view, the features
view: the pages a reader opens by bookmark.

Regenerate those four into the worktree (`gen-backlog-page.py --out …`, and the three siblings) and the
*identical* command exits **1**:

```
contrast: 69420 measured site(s) … across 62 page(s)
  below AA: 165 of 69282 scored
  ⚠ ADVISORY — 2 baselined site(s) were not measured this run (goals.html x2).
FAILED — 10 contrast regression(s):
  ✗ NEW element below AA: 4.14:1 (needs 4.5) [light] backlog-table.html :: 'a design conversation'   (x3)
  ✗ NEW element below AA: 4.10:1 (needs 4.5) [light] backlog-table.html :: '⚠ see status'            (x7)
                                                                                             rc=1
```

The advisory dropping from 29,950 to 2 is itself the proof that the baseline *was* written with those pages
present — so the clean-tree blindness is a property of the environment every reviewer and every clean clone
has, not of a stale baseline.

**⚠ THE PALETTE IS EXONERATED, and I want this on the record rather than left for a later round to discover.**
The failing pair is `#A8690B` on `#F7F6F3` (4.14) and on `#FDF4E3` (4.10). `#A8690B` is not a palette token
(`--warn` is `#7c6426`, `--accent` `#8a5a2b`); it is a literal in `gen-backlog-page.py`. I re-ran the probe on
that page with `CONTRAST_EXTRA_CSS` **unset** and the same pairs fail at the same ratios, because the page's
own `--bg` is already `#F7F6F3`. Raw, that page has **112** below-AA light sites; with the palette injected, 7
distinct failing pairs. The palette *improves* the page substantially and causes none of the 10. What is
defective is the instrument's silence, and the PR's reliance on it.

**Why High and not Medium.** This gate is the only safety mechanism for a change that restyles sixty already-
published pages; its own docstring (`:40-42`) makes "not a pass when it cannot run" a stated contract and sets
rc=2 for *no* pages, while a run that measured 54% of its subject prints an unqualified OK. CLAUDE.md's rule
is that a check which cannot reach what it measures must fail loudly — partial reach is the same failure with
a number attached. The PR body does disclose the 29,950 figure, which is why this is not Blocking: the hole is
named, but it is named as a *result* (`rc=0`) rather than as a limit on what that result covers, and no row in
the verification table reports the gate on the full corpus at `HEAD`. Mine is the first such run.

**HYPOTHESIS.** Two parts, the first cheap and sufficient on its own:
1. Make the success line carry its coverage — `OK — … (35,420 of 65,370 baselined sites measured; 45.8% NOT
   MEASURED, see advisory above)` — so the sentence cannot be quoted without its hole.
2. Add `--require-coverage FRACTION` (or a default bound) under which an unmeasured majority is **rc=2
   CANNOT RUN**, not rc=0. Round 2's B1 was right that *failing* on absent derived pages makes the gate red on
   every clean clone (#56); reporting the gap in the verdict line costs nothing and keeps it green.
3. The durable half belongs in **#238**, whose shape should widen: not only *nothing runs the live gate*, but
   *and when a human does run it, it cannot see 45.8% of what it baselined* — because `corpus()` globs
   `docs/explainers/*.html` while `gen-*.py` defaults to `~/explainers` and the four outputs are gitignored.
   The 10 real AA failures on `backlog-table.html` are live today and nothing in this repository can see them.

---

### MEDIUM 1 — `main()`'s `root` parameter does not reach `measure()`, so the docstring asserts a property the code does not have. DELIVERABLE (`scripts/check-page-contrast.py`)

**Claim.** `check-page-contrast.py:724` says *"⛔ `root` IS DEFAULTED SO A CASE CAN DRIVE THIS OVER A WORLD IT
BUILT — ADR-0014."* `root` reaches `corpus()` at `:744` and stops there. `:758` is `measure(pages, extra_css=extra)`
— no `root=` — so `measure` falls back to the module global for the probe path (`:347`) and the subprocess
`cwd` (`:360`). The `page_chrome` import at `:756` resolves through the module-level `sys.path.insert` at `:58`,
also the real tree.

**Evidence — measured, not read.** Driving `main(root=<tmpdir holding one viewport page and an empty
`scripts/`>)` with `subprocess.run` instrumented:

```
module ROOT = …/wt-364
rc = 2
  node cmd[1] = …/wt-364/scripts/page-contrast-probe.mjs     ← the REAL repo's probe
  cwd         = …/wt-364                                     ← the REAL repo's cwd
```

The constructed world contained no probe, and `measure` never noticed: the `probe.is_file()` refusal at
`:348-349` is **unreachable through `main()`** in any tree where the real probe exists, which is every tree.
This is ADR-0014's own defect shape — `main` resolving its world from module globals — half-repaired, and a
comment asserting a universal the code does not satisfy, which is what six of this PR's own corrected findings
already were.

**HYPOTHESIS.** `measure(pages, extra_css=extra, root=root)` at `:758`, and resolve `page_chrome` from
`root / "scripts"` at `:756` rather than from the import-time path. Then add a case that drives `main` over a
world whose `scripts/` is empty and assert the message names the missing probe — which is the falsifier the
`:348` refusal currently has none of.

---

### MEDIUM 2 — the `MAIN_DEBT` pin on `check-page-contrast.py` is removable today, and both limbs of its stated reason are false. DELIVERABLE (`scripts/check-main-drivable.py:131-139`)

**Claim.** The pin's comment says route (a) *"is not available rather than merely harder"*, because `main()`'s
live path needs node and a browser, so *"a case driving `main()` would either need Chromium in CI or would be
driving a path that cannot measure anything."* Measured, the first limb is false and the second mislabels the
file's own advertised contract as nothing.

**Evidence.** With `scripts/` and `docs/explainers/` both constructed and empty:

```
main([],                 root=<empty world>) -> 2
main(["--raw"],          root=<empty world>) -> 2
main(["--against", …],   root=<empty world>) -> 2
FAILED: no pages to measure — an empty corpus is not a clean result, it is a measurement
        that did not happen. TREAT THIS AS NOT RUN.
```

No node, no browser, no network. That is exactly the `param` route `check-main-drivable.py:34-36` admits
(`main([], root=_r)`), and it drives argparse, `corpus()`, both of `measure()`'s guard clauses and the
`except CannotRun → return 2` arm at `:759-761` — i.e. the *"NOT A PASS WHEN IT CANNOT RUN"* contract the
docstring states at `:40-42`. A path that returns the file's own documented refusal is not "a path that cannot
measure anything"; it is the one region of this guard whose failure mode is a silent green.

ADR-0014's rule D2 pays the debt set **down** one guard at a time; this PR adds to it, taking the population
37 → 38 and the pin set 27 → 28.

**⚠ And the pin is not neutral — it defers the case that would have exposed Medium 1.** `check-main-drivable.py`
cannot catch a half-threaded `root` itself: it reads call-site *source text* and says so at `:63-67` (*"it never
proves the case ASSERTS anything useful once there"*). A case that actually drove `main(root=…)` and asserted
on the message would have hit the leak immediately.

**HYPOTHESIS.** Fix Medium 1, then add to `check-page-contrast.py`'s suite:
`case("an empty world is CANNOT RUN, not a clean corpus", main([], root=_built), 2)` plus one asserting the
missing-probe message, and delete `"scripts/check-page-contrast.py"` from `MAIN_DEBT`. The reconciliation is
already enforced in both directions (`check-main-drivable.py:5125` — *"no pinned name complies"*), so leaving
the pin after adding the case goes red on its own.

---

### LOW 1 — "18 grounds in light, 16 in dark" cannot both be counts of palette-defined grounds, and the delivered predicate checks 13. DELIVERABLE prose + PR body

`page_chrome.py`'s light `--fg3` comment: *"#5c6777 clears all 18 grounds the palette now defines, worst 4.53"*;
the dark comment: *"already clears its 16"*; the PR body: *"measuring every ground the token actually lands on
(18 in light, 16 in dark)"*.

`set(STANDARD_LIGHT) == set(STANDARD_DARK)` — I verified it, and so does this PR's own case in
`explainer-serve.py` (*"light and dark define exactly the same role set"*). Any name-based count of
palette-defined grounds is therefore **identical** in the two schemes, so 18 ≠ 16 is impossible as stated.

The delivered predicate `_aa_over_own_grounds` (`scripts/explainer-serve.py`, `grounds = [k for k in pal if
k.endswith("-bg") or k in (…)]`) iterates **13** in each scheme. Its light worst is **4.53** on `--code`/`--pill`
— matching the comment's figure exactly, so the measurement was taken over 13 and reported as 18. Dark's worst
over those 13 is **4.61**, not the 4.52 the comment gives; 4.52 is `#163020`, a page-local corpus ground, not a
palette one. Two populations (palette grounds, corpus grounds) are being reported in one sentence.

**HYPOTHESIS.** Say both: *"clears AA on all 13 grounds the palette defines (worst 4.53 light, 4.61 dark), and
on every ground it lands on across the corpus (worst 4.52, on `#163020`)."*

---

### LOW 2 — the two `--fg2` vs `--fg` cases compare hex STRINGS, not lightness. DELIVERABLE (`scripts/explainer-serve.py`)

```python
case("in light, --fg2 is lighter than --fg — emphasis reads as a change of tone",
     lambda: page_chrome.STANDARD_LIGHT["--fg2"] > page_chrome.STANDARD_LIGHT["--fg"])
case("...and in dark, --fg2 is DIMMER than --fg, which is the same property inverted",
     lambda: page_chrome.STANDARD_DARK["--fg2"] < page_chrome.STANDARD_DARK["--fg"])
```

The values are hex strings, so these are lexicographic comparisons. They pass on today's neutral greys by
coincidence of the red channel. Falsifiers, both of which pass the shipped cases while violating the named
property:

| scheme | `--fg2` | `--fg` | case says | luminance |
|---|---|---|---|---|
| light | `#ff0000` | `#808080` | passes | 0.2126 **<** 0.2159 — fg2 is DARKER |
| dark | `#0000ff` | `#404040` | passes | 0.0722 **>** 0.0513 — fg2 is BRIGHTER |

The comment above them calls this *"the one a future palette edit could silently lose"*; a string comparison
cannot see that loss. `luminance()` is already reachable in this suite — `_aa_over_own_grounds`, twenty lines
up, imports `check-page-contrast.py` for exactly this kind of arithmetic.

**HYPOTHESIS.** Compare `_m.luminance(_rgb(pal["--fg2"]))` against `_m.luminance(_rgb(pal["--fg"]))`.

---

### LOW 3 — `check-fixture-variation.py`'s pin comment declares 14 keys; the delivered tuple has 21. NOT deliverable (instrument), pre-existing

The comment reads *"Twelve keys over seven pure functions"* with a follow-up *"+2 keys for `dump_baseline`"* —
14. The `EXAMINED_KEYS["check-page-contrast.py"]` tuple below it lists **21** keys over **13** functions
(`baseline_payload`, `collapse`, `composite`, `contrast`, `dump_baseline`, `is_served_page`, `load_baseline`,
`luminance`, `parse_color`, `population_notes`, `sample_key`, `summarise`, `threshold_for`).

**⚠ NOT a merge-resolution defect** — I checked `de1b66eb`, where the comment already said the same thing, so
the blanket "keep both sides" did not cause it. The guard reconciles the tuple against its own `analyse()` and
exits 0, so the DATA is right and only the stated count is wrong. Low because nothing downstream reads it.

---

### LOW 4 — `check-page-contrast.py:9` cites backlog **#220** as the record of the hole, and #220 does not exist in `docs/backlog.md`. DELIVERABLE prose

*"NOTHING IN THIS REPOSITORY MEASURED CONTRAST. Backlog #220 is that hole; #221 is the unification this guard
exists to make safe."* There is no `| 220 |` row in `docs/backlog.md` on this branch or on `master`; row #221
says *"Supersedes **#220**, which was filed as 'softer bold' and is a SYMPTOM"*. So the id is dangling **and**
mischaracterised — by #221's own account #220 was the symptom request, not the measurement hole. The hole is
#221's own content.

**HYPOTHESIS.** *"Nothing in this repository measured contrast — which is backlog #221's own first paragraph.
(#220 was the superseded 'softer bold' request and no longer has a row.)"*

---

### LOW 5 — #238's population measurement does not re-derive, and the figure is environment-dependent. Instrument/prose

`a0a434b6`'s message and backlog #238 state: *"59 served pages declare 95 DISTINCT token names outside the
standard set, and 59 of 59 declare at least one."* Re-derived in this worktree over `corpus()` and
`set(STANDARD_LIGHT) | set(STANDARD_DARK)` (40 names):

```
served pages (corpus()): 58
distinct token names declared, all: 129
distinct OUTSIDE the standard:       91
pages declaring >=1 outside token:   58 of 58   (zero pages with none)
```

**The conclusion is unaffected and I am not disputing it** — 58 of 58 is as decisive as 59 of 59, and the alias
route cannot close. What is wrong is that the figure moves with which gitignored derived pages happen to exist
(the same cause as High 1: `corpus()` sees 58 here and the baseline holds 60), and the row states it as a flat
count. A later reader re-deriving it will get a third number and have no way to tell which was right.

**HYPOTHESIS.** State it as *"every one of the 58 served pages present in a clean tree (62 when the four
derived pages are generated)"* and name the token set it was taken against.

---

### LOW 6 — the `NO-ENTRY:` reason contradicts itself inside one sentence. PR body

> `NO-ENTRY: no product behaviour change. This alters how already-published explainer pages render when served;
> the product pipeline is untouched.`

The second clause is a behaviour change, on the surface the human reads most. `check-dashboard-entry.py` passes
on it (I confirmed the line is in the PR body at line 78, so my local rc=1 is a no-PR-body artifact, not a CI
red) and the dashboard then **displays** this reason to the reader who was away. "No product behaviour change"
is the half they will see first.

**HYPOTHESIS.** *"NO-ENTRY: no change to the summarisation pipeline. Sixty already-published explainer pages do
change how they render when served — the entry for that is #221's own backlog row."*

---

## Merge audit — handoff item 1, a null result with its method stated

Seven files differ from **both** parents of `7009896a` (merge base `7f7a1577`), not five:
`.github/workflows/ci.yml`, `docs/backlog.md`, `docs/roadmap-to-launch.md`, `scripts/check-fixture-variation.py`,
`scripts/check-main-drivable.py`, `scripts/check-plan-code.py`, `scripts/check-selftest-counts.py`.

| File | Checked how | Verdict |
|---|---|---|
| `check-selftest-counts.py` | both `POPULATION` entries present (`check-page-contrast.py`, `check-main-drivable.py`); `frozenset`, so order is not semantics | ok, guard green both modes |
| `ci.yml` | both step blocks present; `27 of 37` → `28 of 38` applied once. ⚠ the blank line between the probe self-test step and the ADR-0014 comment was lost, so that comment hangs under a `run:` — YAML-valid, `schema-gates` passes in CI | ok (cosmetic) |
| `check-main-drivable.py` | master's 5,141-line file plus the 11-line pin only | ok, 438/438 + live run `D2 OK` |
| `check-fixture-variation.py` | both key blocks present; the `),` repair held | ok, green both modes (see Low 3 for its comment) |
| `check-plan-code.py` | declared sum **1407** once, not twice | ok, `--self-test` 178/178 |
| `docs/backlog.md` | ids **221-238 contiguous, no duplicates**; `uniq -d` empty across the whole table | ok (220 absent by design — Low 4) |
| `docs/roadmap-to-launch.md` | `28 of 38` present and reconciled | ok |

**No third wrong resolution.** Every guard in `ci.yml` that takes no external service runs green under 3.12
(53 unique invocations; the only non-greens are `check-dashboard-entry.py` — needs the PR body, which has the
line — `check-test-counts.py` — needs `jest-results.json` — and `check-review-rounds.py`, which is red for the
missing round-3 Claude half **this document is**).

## The fold — handoff item 4, and it holds

`--st-ink3` `#6B7585` → `#5E6878`, in both the page and its `.fragment.html`. Recomputed independently:

| fg | `--st-ground` | `--st-surface` | `--st-sunk` | `--st-struct-bg` | `--st-ok-bg` | `--st-bad-bg` | `--st-unknown-bg` |
|---|---|---|---|---|---|---|---|
| `#5E6878` (new, light) | **5.26** | 5.63 | **4.97** | 4.86 | 4.89 | 4.81 | 4.99 |
| `#6B7585` (old, light) | 4.35 | 4.66 | 4.11 | 4.02 | 4.04 | 3.97 | 4.12 |
| `#8A94A3` (dark, unchanged) | 6.01 | 5.63 | 5.15 | 4.99 | 5.02 | 5.52 | 5.14 |

The commit's 4.34→5.26 and 4.11→4.97 reproduce (4.35 vs 4.34 is rounding). **The dark half needed nothing** —
`#8A94A3` clears 4.5 on all seven dark grounds, worst 4.99, so changing only the light declaration was correct
rather than a missed half. `--st-ink2` (8.25–9.56) and `--st-low` (5.10–5.98) are clear, and I found no eighth
`--st-*` token below AA. Not aliasing `--st-ink3` into the standard set was the right call and #238 is the
right place for the residue.

## What I checked that found nothing

- **Higher-specificity theme overrides.** If any page redefined tokens at specificity above the palette's
  `(0,2,0)`, unification would silently fail there. Three candidates in the corpus, all `:root[data-theme="dark"]
  .diff del/ins` element rules, none a `:root`-level token redefinition. The specificity story in
  `standard_palette_css()` holds.
- **Injection-point divergence.** The server appends the palette after `</body>` (`explainer-serve.py:1224`);
  the probe injects via `addStyleTag`, which appends to `<head>`. These differ only if a page declares `:root`
  tokens in a `<style>` *after* its head. No served page does — I checked all 62 for a `<style>` past `</head>`
  or past 50% of the document; zero. ⚠ It is an unstated assumption, not a current defect: the 20 fragments
  carry body-level `<style>` and would diverge, but `is_served_page` excludes them from the corpus.
- **Was the baseline re-written after the palette, making the ratchet self-referential?** It was rewritten at
  `129b882b`, `30e5b1b9` and `de1b66eb`, all at or after the palette. But each rewrite was forced by a key-schema
  change (sibling ordinals, gradient exclusion, gzip), and the headline comparison in `129b882b`
  (486 → 100 over 6,664 sites) is same-basis — raw versus palette-injected under one schema, not pre- versus
  post-schema. `4,192 → 155` in the PR body is the same comparison under the post-split schema. The claim is
  internally consistent and I could not break it.
- **The class I most feared in a change that restyles sixty published pages: a dark-mode regression the gate
  cannot see.** It cannot happen for this harness — `measure()` runs both schemes by default (`:330`) and
  `sample_key` includes the scheme (`:164`), with a case pinning that two schemes are two keys. I verified the
  baseline holds exactly 32,685 light and 32,685 dark keys. Dark is measured symmetrically throughout. What
  the gate is blind to is not a *scheme*, it is four *pages* — which is High 1.

---

## Verdict

**NOT CONVERGED.**

Reason: High 1 is in the deliverable and is unaddressed in any form — the gate prints an unqualified pass over
an unmeasured majority of its own baseline, and that pass is the evidence the PR's safety claim rests on. Under
the freeze (*Blocking/High in the DELIVERABLE folds*) it is a fold, and the cheap half of the fix is one
f-string. Medium 1 and Medium 2 interlock with it and with each other: `root` is advertised and half-threaded,
and the pin added to `MAIN_DEBT` defers precisely the case that would have caught it. The six Lows are prose
and one test predicate; none blocks.

What a convergent round 4 needs to show: the success line carries its coverage; `measure` receives `root`; and
either the pin is removed with a case that drives `main()` over a constructed world, or the pin's comment states
the real reason rather than the refuted one.

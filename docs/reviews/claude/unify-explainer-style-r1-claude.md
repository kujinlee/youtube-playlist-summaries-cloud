# `unify-explainer-style` — round 1, Claude adversarial half

**Subject:** `git diff master...HEAD`, base `master` = `2413b003`, two commits `ad4885a1` (contrast
harness) and `129b882b` (unification).
**HEAD at start:** `129b882b5b8958153621a2c87d3b3c5a372aabb9`
**HEAD at end:** `129b882b5b8958153621a2c87d3b3c5a372aabb9` — unchanged, the round stands.
**Mandate:** refute. No git mutations were made; every mutation below was applied to a copy under a
scratch directory.

---

## Lead: the headline survived, and I tried hard to break it

**486 → 100 is real.** It is not an artefact of the probe change. I re-derived it from scratch with
the *current* probe on *both* sides, which is the comparison the mid-stream probe edit could have
corrupted:

```
$ python3 scripts/check-page-contrast.py --write-baseline $S/run-raw.json --raw
contrast: 6664 text element(s) across 60 page(s), both schemes
  below AA: 486   worst: 1.11:1

$ python3 scripts/check-page-contrast.py --write-baseline $S/run-palette.json
contrast: 6664 text element(s) across 60 page(s), both schemes
  below AA: 100   worst: 1.11:1
```

Same probe, same key schema, same 6,664-key population on both sides — `set(raw) == set(palette)`
is `True`. The committed baseline reproduces exactly: **0 of 6,664 keys differ in ratio** from my
independent run, and `--against docs/contrast-baseline.json` exits 0.

The probe-change hazard was real but does not reach this number. The *commit-1* baseline is
unusable for the comparison — it has a different key schema (`page|scheme|fg|bg|px|weight`), 3,534
keys, and `below_aa: 423` — so the author could not have derived 486 from it, and did not: 486 is
the `--raw` figure under the current code, which is the honest comparison. **Claim 1 survives.**

So does the cascade claim (§4), and so does the `--fg3` deviation (§5). Details in *What survived*.

What did not survive: the regression count, the reason given for the regressions, the baseline's
own integrity on a clean clone, and a documented safety property of `collapse`.

---

## Blocking

### B1 — The remaining regressions are **23, not 14**, and the stated reason they are unavoidable is false. `--ink3` is a token, not a literal

**Premise**, `129b882b` commit body:

> ```
> already-failing, worsened    14   (4.34 -> 4.15)
> ```
> The 14 are page-local LITERAL colours on the standard's `--bg`. No token override
> […] can reach them.

**Measurement.** The real gate, run with the branch's own code, `--raw` baseline as "before":

```
$ python3 scripts/check-page-contrast.py --against $S/run-raw.json
contrast: 6664 text element(s) across 60 page(s), both schemes
  below AA: 100   worst: 1.11:1

FAILED — 23 contrast regression(s):
  ✗ WORSENED while already below AA: 4.34 -> 4.15 [light] …sidebar-refresh-after-ingest… :: '→'
  ✗ WORSENED while already below AA: 4.34 -> 4.15 [light] …verify-counts-delete-anchor… :: 'PR #91'
  … (23 lines, all 4.34 -> 4.15, all light, across 4 pages)
rc=1
```

Both halves of the claim fail.

**The count is 23.** Not 14 — a 64% understatement of the branch's only acknowledged cost. All 23
are the same pair (4.34 → 4.15), light scheme, on four pages:
`2026-08-12-explanation-sidebar-refresh-after-ingest-49045e5.html`,
`2026-08-12-explanation-verify-counts-delete-anchor-995d7e4.html`,
`2026-08-13-explanation-m3-1-cloud-e2e-70f7ab1.html`,
`2026-08-13-explanation-money-guard-review-a45e375.html`.

**They are not literals.** The foreground is `rgb(125, 118, 108)` = `#7d766c`, and the rule that
sets it is:

```
docs/explainers/2026-08-13-explanation-money-guard-review-a45e375.html
  figcaption{…;color:var(--ink3);…}
```

— and all four pages declare `--ink3:#7d766c`:

```
$ for F in <the four pages>; do grep -o -E '\-\-ink3:[^;}]*' $F | head -1; done
--ink3:#7d766c
--ink3:#7d766c
--ink3:#7d766c
--ink3:#7d766c
```

`--ink3` is simply **not in `STANDARD_LIGHT`/`STANDARD_DARK`**. It is reachable by exactly the
mechanism this commit is built on; it was missed, not ruled out. Across the whole corpus the same
token accounts for the plurality of what remains:

```
failures below AA, by (fg, bg), top 4 of 100:
   23  fg=rgb(125, 118, 108)  bg=rgb(247, 246, 243)
   15  fg=rgb(125, 118, 108)  bg=rgb(255, 255, 255)
   11  fg=rgb(178, 106, 18)   bg=rgb(253, 243, 227)
   11  fg=rgb(125, 118, 108)  bg=rgb(246, 243, 237)
```

**49 of the 100 remaining failures are `#7d766c`.**

**Severity reasoning — Blocking.** This is not a wording slip. The sentence "no token override can
reach them" is the argument for shipping the regressions, and it is false; adding one token both
removes the 23 regressions *and* unifies four pages the branch currently leaves un-unified, which
is the branch's stated goal. A human reading the commit decides to merge on a cost of 14
unavoidable; the true cost is 23 avoidable. This is the repo's own
`an-inference-stated-as-measured` shape, in the commit whose subject is measuring carefully.

**Fix.** Add `"--ink3": "#616c7c"` to `STANDARD_LIGHT` and `"--ink3": "#8892a2"` to
`STANDARD_DARK` (matching `--fg3`/`--ink-faint`, which is what the token means on those pages), then
re-measure. Separately, eight pages hardcode `--ink-3` rather than chaining it
(`--ink-3:#7a8494` ×4, `--ink-3:#6b7686` ×4, versus `--ink-3: var(--ink-faint, #7a8695)` ×40) —
same class, worth the same sweep. Then correct the commit body to the re-measured number.

**Structural.**

---

### B2 — The committed baseline holds 496 keys from four pages that are **not in git**, and `verdict()` never notices a key that disappears

**Premise**, `scripts/check-page-contrast.py:170` (`verdict`):

> ```python
> prior = {k: v for k, v in baseline.get("samples", {}).items()}
> for s in samples:
> ```

The loop is over `samples` — the current run. Nothing ever iterates `prior`. A baseline key with no
counterpart in the run is not compared, not reported, and not counted.

**Measurement — the rule.** Pure, no browser:

```
baseline has 2 sites. Run returns NONE of them:
  verdict([], baseline) = []          <- SILENT
run returns only one of them:
  verdict([one], baseline) = []       <- SILENT about the other
```

**Measurement — the live instance.** The corpus is `docs/explainers/*.html` filtered by
`is_served_page`. 60 pages are measured; **four of them are untracked**:

```
$ git ls-files 'docs/explainers/*.html' | wc -l        →  72
$ ls docs/explainers/*.html | wc -l                    →  80
served pages measured: 60   UNTRACKED among them: 4
    backlog-table.html
    dashboard.html
    features.html
    goals.html
baseline keys contributed by untracked pages: 496
of which below AA: 7
```

**496 of 6,664 committed baseline keys (7.4%) describe pages that do not exist in the repository.**
One of them is `backlog-table.html` — the page the commit names as *the standard*. On a clean
clone those 496 sites are absent, `verdict` says nothing about any of them, and the gate exits 0.

The Codex half reached the same place from the other direction and measured the consequence
end-to-end: a `git archive HEAD` tree gives `418 → 93` over `6168` samples / `56` pages, and
`--against docs/contrast-baseline.json` still exits 0 there. I note the agreement rather than claim
it twice; I reached the untracked-corpus fact independently (the `72 vs 80` count above) before
seeing their file.

**Severity reasoning — Blocking.** `measure()` does refuse a *total* wipeout (`CannotRun` on zero
rows, and on an empty corpus) — so the catastrophic case is covered. What is not covered is the
partial case, which is the one that actually happens: a page renamed, a generated page absent, a
selector reshuffled. This is the ratchet's whole job, the harness was explicitly built *before* the
change so it could do that job going forward, and today it would pass a tree in which 7.4% of its
subject had vanished. A ratchet that cannot tell "clean" from "not measured" is backlog #56's
failure mode and this file's own opening confession, one level up.

**Fix.** Two parts, both small:
1. In `verdict`, after the `samples` loop, iterate `prior` for keys absent from the run and emit a
   `MISSING` line. Make it rc=2 (CANNOT RUN) rather than rc=1 when the missing fraction exceeds a
   written threshold — a vanished population is not a regression, it is a measurement that did not
   happen.
2. Decide what the four standing pages are. Either track them, or exclude them from the corpus and
   the baseline. Leaving a generated, untracked page in a committed baseline makes the baseline
   machine-specific — which is also why the author's `--raw` figure and a clean tree's disagree.

**Structural.**

---

## High

### H1 — `collapse`'s documented guarantee — "it can over-report a regression, never hide one" — is false, and the masking surface is two-thirds of the corpus

**Premise**, `scripts/check-page-contrast.py:150-152` (`sample_key` docstring):

> ⚠ Two sites can share a key and differ in colour (the same selector path inside a verified
> box and a defect box). `collapse` keeps the WORST ratio for a key, which is conservative in
> the only direction that matters: **it can over-report a regression, never hide one.**

and `:157-159` (`collapse`):

> ⛔ WORST, NOT FIRST OR MEAN. […] Over-reporting a regression costs a reader one line; hiding
> one costs the thing this harness exists for.

**Measurement.** Runnable counterexample, nothing deleted, both sites present throughout:

```
before: A=3.00 (already below AA), B=8.00 (passing). collapsed baseline = 3.0
after:  A=9.00 (fixed),            B=3.50 (CROSSED below AA). collapsed = 3.5
verdict = []   <-- SILENT; B crossed 8.00 -> 3.50 and nothing reports it
```

The minimum is monotone in the *group*, not in its members. Any member may degrade arbitrarily —
including from passing to failing — and stay invisible as long as the group minimum does not fall.
Here the group minimum *rose*, so the run reads as an improvement.

This is not a corner. Over the real corpus:

```
collapsed sites: 6664
sites standing for >1 element: 4410 (66.2%)
total elements behind them: 63258
largest single site stands for: 2212 elements
```

**66.2% of tracked sites are groups**, and the largest tracks the worst of 2,212 elements. For
every one of those groups the guarantee quoted above does not hold.

**Severity reasoning — High, not Blocking.** The *direction* the author worried about (a
first-or-mean baseline letting the worst degrade) is genuinely fixed by taking the minimum, and the
palette change itself is verified by the absolute `below_aa` count, which is immune to this. What
is wrong is the stated safety property, and a false safety property in a guard's docstring is how
the next person skips a check. It does not invalidate 486 → 100.

**Fix.** Cheapest honest option: delete the claim and say what is true — *a site records the worst
of its group; a regression confined to a non-worst member is not detected.* Better: store the full
ratio multiset per key (or a `(min, count, sorted-ratios-hash)`) so a member-level change is
visible. Note the baseline format is `{key: ratio}`, so this is a baseline-schema change and should
ride with B2's rewrite rather than be done twice.

**Structural.**

---

### H2 — The probe is blind to `background-image`, so the corpus's worst reported ratio is fiction and text on gradients cannot regress

**Premise**, `scripts/page-contrast-probe.mjs:30-32`:

> ```js
> // The background a reader actually sees behind this text: the nearest ancestor that is opaque.
> // ⚠ NOT the element's own background — most text sits on a transparent element inside a card,
> // and scoring against `transparent` is how a contrast probe reports fiction.
> ```

`bgOf` (`:33-54`) consults `getComputedStyle(n).backgroundColor` only. `background-image` — every
gradient — is never read.

**Measurement.** The worst result in the whole corpus, from my palette run:

```
 1.11 [light] 2026-08-12-explanation-sidebar-refresh-after-ingest-…  div.lane>div.bar>div.seg
      fg=rgb(255, 255, 255)  bg=rgb(246, 243, 237)  'create'
```

Driving the same element directly:

```json
{"cls":"seg s-gh","text":"create","color":"rgb(255, 255, 255)",
 "bgColor":"rgba(0, 0, 0, 0)",
 "bgImage":"repeating-linear-gradient(45deg, rgb(178, 106, 18), rgb(178, 106, 18) 5px, rgb(207, 138, 4…",
 "parentBgColor":"rgb(246, 243, 237)"}
```

The text sits on a solid amber hatch of `rgb(178, 106, 18)`. White on that is ≈3.5:1 — below AA, so
there *is* a real defect here, but nothing like 1.11:1. The probe walked past the gradient, found
the parent's cream, and scored white-on-cream.

`worst: 1.107` is the headline figure in `docs/contrast-baseline.json`'s own `summary` block, and in
both the before and after summaries quoted in this review. It describes a rendering nobody sees.

The ratchet consequence is the serious half: because the measured ratio is computed from a colour
the gradient does not affect, **changing the gradient cannot move the number.** Any future
regression to text on a gradient or image background is invisible to this gate, permanently and
silently — the precise failure mode the file's opening confession is about.

**Severity reasoning — High.** It corrupts a published headline number, and it carves a whole class
of element out of a guard that reports no gap. It is not Blocking because the class is small in this
corpus and the palette change does not touch gradients, so 486 → 100 is unaffected.

**Fix.** In `bgOf`, when no opaque `backgroundColor` is found on the chain but some ancestor has
`backgroundImage !== 'none'`, do not fall through to the canvas. Return a sentinel and have
`measure()` record the sample as **EXCLUDED, reason: painted background not readable from computed
style** — counted and reported, never silently scored. (Sampling the painted pixel via
`page.screenshot` + a clip box is the thorough version and is a bigger change; refusing is correct
and cheap, and matches this file's `CannotRun` discipline.) The same change should be reflected in
the `summary`, so `worst` stops naming an element the probe cannot see.

**Structural.**

---

### H3 — The probe's comment says it decides nothing; it holds seven decision rules, none of them testable by anything in the repository

**Premise**, `scripts/page-contrast-probe.mjs:12-14`:

> ⛔ IT DECIDES NOTHING. No contrast maths, no thresholds, no verdict — those are pure Python and
> cased without a browser. This file only reports what the page computed: colour, background,
> size, weight. **Putting a rule here would put it where no self-test can reach it.**

and `scripts/check-page-contrast.py:238-240`:

> ⚠ THE PROBE DECIDES NOTHING. It reports computed colour, background, size and weight; every
> threshold and every verdict is pure Python above, cased without a browser.

**Measurement.** Rules living in that file:

```
:28  return parts.length < 4 || parseFloat(parts[3]) >= 0.999;    ← what counts as opaque
:53  return dark ? 'rgb(18, 18, 18)' : 'rgb(255, 255, 255)';      ← the UA-canvas fallback (NEW in 129b882b)
:58  for (let i = 0; n && i < 3; i++, n = n.parentElement)        ← selector depth = the KEY's identity
:86  if (cs.clip === 'rect(0px, 0px, 0px, 0px)') continue;        ← what is "visually hidden"
:87  if (cs.clipPath && /inset\(\s*(50%|100%)/.test(cs.clipPath)) continue;
:89  if (r.width <= 2 || r.height <= 2) continue;                 ← the off-by-one the comment itself confesses
:91  if (r.bottom < -2000 || r.right < -2000) continue;
```

Every one of these decides whether an element is measured at all, or against what. `:58` is
load-bearing for *identity*: the three-level depth is two of the five components of `sample_key`,
so changing it silently reshapes the entire baseline. `:53` was added in commit 2 and, by the
author's own note, moved 316 sites — it changed the numbers this review is about.

And nothing tests any of it:

```
$ grep -rln 'page-contrast-probe' --include='*.py' --include='*.json' --include='*.yml' --include='*.mjs' .
scripts/check-page-contrast.py          # invokes it
scripts/page-contrast-probe.mjs         # itself
$ grep -rln 'page-contrast-probe' scripts/mutations/
  (no match — NO MUTATION MANIFEST COVERS THE PROBE)
```

No self-test, no mutation entry, no CI step. The comment's own conditional — *"putting a rule here
would put it where no self-test can reach it"* — is satisfied, and the conclusion drawn from it is
the opposite of the truth. This is backlog #216's class (a comment asserting a property the code
does not have), filed one day before this branch.

**Severity reasoning — High.** The rule/fetch split is the file's central design claim and the
reason its 64 pure cases are trusted. The split is real for the *arithmetic* and false for
*population selection*, which is the half that decides what the arithmetic is applied to — and the
repo has paid for exactly that distinction before (`a-measurement-is-only-as-good-as-its-corpus`).

**Fix.** Either (a) move the filters into Python — have the probe emit `clip`, `clipPath`, `rect`,
`backgroundImage` and the full ancestor background chain, and let a pure, cased
`is_measurable(raw)` / `resolve_bg(raw)` decide — which makes H2's fix free and restores the claim
honestly; or (b) keep them in JS and give the `.mjs` a `node --test` suite plus a mutation manifest,
and rewrite the comment to say the probe decides *which elements are measured* and is cased
separately. (a) is better and is the one the file's own architecture already argues for.

**Structural.**

---

## Medium

### M1 — The CI comment cites a `docs/dev-process.md` entry that does not exist, and nothing anywhere runs the live gate

The CI *step name* is honest, and I want to credit that before the finding — `.github/workflows/ci.yml:388`
reads `Contrast harness self-test (pure rules; the live run is local)`, which cannot be mistaken for
enforcement. Attack §7's main worry does not land.

**Premise**, `.github/workflows/ci.yml:385-387`:

> Contrast against the committed baseline is a LOCAL pre-merge gate, **listed with the other two in
> docs/dev-process.md**. Saying so is the point: a contrast gate that silently does not run in CI,
> while a CI step bearing its name goes green, is worse than no gate at all.

**Measurement.**

```
$ grep -n -i 'contrast\|page-contrast' docs/dev-process.md
  (no output — NO MENTION AT ALL)

$ sed -n '170,171p' docs/dev-process.md
**Not yet in CI:** `test:integration` and `test:e2e` (need a live Supabase stack); run them locally
before a merge. ⟳ 2026-09-13 the schema gates LEFT this list — CI builds their Postgres in 14s.
```

The list the comment points at has two entries and this is not one of them. And no caller exists
anywhere for the measuring half:

```
$ grep -rn 'check-page-contrast' --include='*.py' --include='*.yml' --include='*.sh' --include='*.md' .
.github/workflows/ci.yml:391   → --self-test
scripts/check-fixture-variation.py:308, scripts/check-selftest-counts.py:87,
scripts/check-plan-code.py:1381,3035                     → registry entries
scripts/page_chrome.py:76,92                             → prose
$ grep -n 'contrast' scripts/check-merge-ready.py
  (check-merge-ready does NOT run it)
```

`--against` is invoked by nobody: not CI, not `check-merge-ready.py`, not a hook. `check-ratchet-contract.py`
passes the file because the CI `--self-test` satisfies its caller requirement — so the contract is
discharged by the pure half while the half that measures contrast is orphaned.

**Severity reasoning — Medium.** The comment is the only place the local-gate protocol is written
down, and it is wrong about where it is written down, which means it is written down nowhere. The
guard works; it just has no appointed moment to run. Transitional in the sense that both halves are
one-line additions — but the class (a comment asserting documentation that does not exist) is the
same one the repo filed as #216.

**Fix.** Add `check-page-contrast.py --against docs/contrast-baseline.json` to the "Not yet in CI"
line in `docs/dev-process.md`, and add it to `scripts/check-merge-ready.py` so the pre-merge moment
is mechanical rather than remembered. Then the CI comment becomes true.

**Transitional.**

---

### M2 — Commit 2's two load-bearing logic changes gained no mutation-manifest entries, and `EXPECTED_MUTATIONS` did not move

**Premise.** `129b882b` rewrote `sample_key` (colour-keyed → selector-keyed) and added the
worst-keeping branch to `collapse`.

**Measurement.**

```
$ git diff --stat ad4885a1 129b882b -- scripts/mutations/check-page-contrast.json
  (empty — unchanged)
$ grep -n 'check-page-contrast.py"' scripts/check-plan-code.py
1381:    "scripts/check-page-contrast.py": 8,
```

The 8 anchors are commit 1's. None touches `return f"{s['page']}|{s['scheme']}|{s['selector']}|…"`
or `if r["ratio"] < hit["ratio"]:`; the nearest, `hit["instances"] += 1`, severs the adjacent line.
`worsened` has no anchor either (only `crossed` does).

**I expected this to mean the new logic was unfalsifiable, and measurement refuted that.** Severing
each on a copy under a scratch directory, against a control proved green first (`64/64`):

```
M1: collapse stops keeping the WORST ratio   → rc=1  63/64   ** killed **
M2: sample_key drops the SELECTOR            → rc=1  62/64   ** killed **
M3: the WORSENED branch never fires          → rc=1  62/64   ** killed **
M4: the CROSSED comparison is severed        → rc=1  63/64   ** killed **
```

The cases exist and they bite. What is missing is only the *ratchet* — nothing pins those cases, so
a later refactor can delete them and `EXPECTED_MUTATIONS: 8` will still agree with itself.

**Severity reasoning — Medium, downgraded from my initial read.** No live hole. The repo's whole
mutation discipline exists because "the case exists today" and "the case cannot be removed
unnoticed" are different properties, and commit 2 added logic with only the first.

**Fix.** Add three entries to `scripts/mutations/check-page-contrast.json` with the anchors above
and the case names they kill, and raise `EXPECTED_MUTATIONS["scripts/check-page-contrast.py"]` to
11. The declared-sum bookkeeping in `check-plan-code.py` moves with it.

**Transitional.**

---

### M3 — Unification is partial, and the pages are not unified on the tokens a reader most notices

The commit's own route — *13 tokens defined by ≥90% and all in the standard* — is accurate, and the
palette covers 18. But a token used by 80% of pages is not covered, and those are the accent colours.

**Measurement.** Resolved in Chromium with the palette injected, over all 60 served pages:

```
tokens USED by pages but NOT in the standard palette (colour-bearing, by page count):
  --accent      49/60      --warn        48/60      --code        48/60
  --warn-br     47/60      --warn-bg     47/60      --code-fg     45/60
  --danger      45/60      --danger-bg   45/60      --pill        45/60
  --hair        45/60      --h           45/60      --strong      45/60

distinct resolved values across the corpus, light / dark:
  --code 5/5    --accent 4/6    --warn 4/4    --strong 2/2    --h 2/2    --pill 2/2    --hair 2/2
```

So after this branch, headings (`--h`), emphasis (`--strong`), code (`--code`), accents and warning
colours still come in 2–6 variants across the corpus. Ground, ink and rules are unified; the
semantic palette is not.

**Severity reasoning — Medium.** The human's instruction was *"For now having unified style"*, and
this is a real and substantial step toward it — I am not claiming the branch fails its goal. But the
commit's framing (*"only WHAT the colours are becomes uniform"*) reads as complete, and §B1's
`--ink3` shows the gap is not merely cosmetic: it is where the residual contrast failures live. The
six pages the backlog row says are "out of reach by construction" are reported; these 45–49-page
tokens are not mentioned at all.

**Fix.** No code change required for merge. State the residual in the commit body or the backlog row
— which tokens remain per-page and how many values each has — so the next pass has a target rather
than rediscovering it. The `--accent`/`--code`/`--warn` families are the obvious second slice.

**Transitional.**

---

## Low

### L1 — "6,664 sites × 2 schemes" double-counts the corpus

Commit body: `RESULT, measured over 6,664 sites x 2 schemes`. The 6,664 figure *already* spans both
schemes — `scheme` is the second component of `sample_key`, and the 100 failures split
`light 88 / dark 12` within that total. The phrasing implies 13,328. Say *6,664 sites across both
schemes*. **Structural** (it is a claim), trivial to fix.

### L2 — `--report` is a declared, documented, no-op flag

`scripts/check-page-contrast.py:515` declares `--report`; `main()` never reads `args.report`. The
usage block at `:30` documents it as `measure and print, no verdict` — which is what the *default*
no-flag path already does (`:542-544` print the summary unconditionally, then fall to `return 0`).
Harmless, but a documented flag that does nothing is a small trap. Delete it, or make the default
path require it. **Transitional.**

### L3 — Two small inaccuracies in the `--fg3` deviation comments; neither changes the chosen value

(a) `scripts/page_chrome.py` dark block says *"lightened by 14 to clear the worst (#163020)"*, but
`#163020` is not among the six grounds the comment enumerates, and of the grounds it does list the
worst is `rgb(38,36,44)`/`#26242c`:

```
chosen #8892a2 on #26242c: 4.516     on #163020: 4.520
```

The chosen value clears both, so the decision is right and only the named witness is wrong.
(b) `sample_key` formats `px` as `.1f`, so two sizes 0.05px apart can share a key while
`threshold_for` gives them different thresholds (e.g. 23.96 → 4.5 vs 24.04 → 3.0), and `collapse`
keeps the first row's threshold. Latent only — measured over the corpus, **0 keys whose members
disagree on threshold**, and 20 sites sit on the boundary at exactly `px=24.0`. Worth a comment, not
a change. **Transitional.**

---

## What survived refutation

I attacked these and failed; recording them so a later round does not re-spend the time.

**§1 — 486 → 100 is real.** Re-derived independently with the current probe on both sides. The
committed baseline reproduces with 0 of 6,664 ratios differing, and `--against docs/contrast-baseline.json`
is rc=0. **0 crossed below AA** confirmed. The probe-change hazard was the right thing to worry
about and does not reach this number. ⚠ The 486 is specific to *this workspace's* 60-page corpus;
see B2 for why a clean tree gives a different pair.

**§4 — the injected palette wins the cascade, everywhere, in all four states.** Chromium,
all 60 served pages, reading every one of the 18 standard tokens on both `document.documentElement`
and `document.body`:

```
scheme=light data-theme=none  :: 60 pages → standard tokens NOT resolving to the standard: NONE
scheme=dark  data-theme=none  :: 60 pages → NONE
scheme=light data-theme=dark  :: 60 pages → NONE
scheme=dark  data-theme=light :: 60 pages → NONE
```

Zero exceptions, including under the explicit theme toggle in both directions. I specifically
hunted for tokens redeclared on `body` (which would beat a `:root` override for the whole subtree)
and found none. The four-selector-form reasoning is correct and the `:not([data-theme="light"])`
specificity arithmetic (0,2,0) checks out.

**§5 — the `--fg3` deviation is honest and minimal.** Every number re-derived:

```
standard #6b7686 on --bg #f7f6f3 : 4.261   (claim 4.26)  ✓ under AA
chosen   #616c7c worst ground #f7ebd9 : 4.523            ✓ (claim 4.52)
standard #7a8494 on --bg #101318 : 4.924   (claim 4.92)  ✓
MINIMAL uniform darkening clearing 4.5 on every listed light ground: d=10 → #616c7c
MINIMAL uniform lightening clearing 4.5 on every listed dark  ground: d=14 → #8892a2
```

Both chosen values are the *smallest* uniform step that clears AA on every ground — not merely a
step that works. I then asked the question the brief asked: is there a value closer to the standard
that is also AA-clean? By raw RGB distance, yes: `#666a84` (dist² 173 vs 300). **Perceptually, no** —
in CIE Lab it is nearly twice as far:

```
dE76 from #6b7686:   chosen #616c7c = 4.01     RGB-nearest #666a84 = 7.88
```

`#666a84` buys its proximity by shifting hue; the chosen value preserves it. And of the 100
remaining failures, **0 have the standard `--fg3` as foreground** — the "chosen against every
ground the token lands on" claim holds under direct measurement.

**Declared self-tests, all at their declared counts:**

```
check-page-contrast.py --self-test     64/64
explainer-serve.py --self-test        211/211
check-plan-code.py --self-test        131/131
check-selftest-counts.py              OK — 51 scripts declare a count, every one verified by running it
check-ratchet-contract.py             OK — 44 guards discovered
check-fixture-variation.py            OK — 766 parameters across 63 files
```

The `explainer-serve` wiring cases are the right shape: `_wire_of` drives the real `do_GET` with a
`BytesIO` on `wfile` and asserts the palette bytes are on the wire, not merely defined. I severed
the injection line on a copy and the suite goes red, as its manifest entry claims.

---

## Could Not Measure

**`check-plan-code.py --mutate .`** — the full sweep (1,187 mutations over 58 guards) was started and
had reached 275/1187 when this document was written. It is the repo's own measured cost problem
(backlog #217). **Treat the full sweep as NOT RUN by this round.** What I did run instead, and what
it does and does not cover: the control for `check-page-contrast.py` is green (64/64), the manifest
parses and its 8 anchors all resolve against the delivered file, and I hand-severed the four
commit-2 logic changes against that control (M2 above) — so the *new* code is covered by direct
measurement. What remains unmeasured is whether commit 2 orphaned an anchor in one of the other 57
guards' manifests; `check-ratchet-contract.py` passing is weak evidence against that, not proof.

---

## Verdict

**NOT CONVERGED: 2 Blocking · 3 High · 3 Medium · 3 Low**

The headline measurement is sound and I could not shake it, and the two claims most likely to be
hand-waved — the cascade and the colour deviation — are the best-evidenced things in the branch.
What fails is bookkeeping about the *residual*: the regression count is 23 not 14, the reason given
for those regressions is false and a one-token fix removes them, and the baseline that is supposed
to hold all of this still cannot tell a clean tree from a tree where 7.4% of its subject is missing.

**HEAD at end: `129b882b5b8958153621a2c87d3b3c5a372aabb9`** — matches the start.

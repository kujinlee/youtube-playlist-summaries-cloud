# `unify-explainer-style` — round 2, Claude adversarial half

**Subject:** `git diff 129b882b..HEAD` — one commit, `30e5b1b9`, the fold of round 1's
`2 Blocking · 3 High · 3 Medium · 3 Low`.
**HEAD at start:** `30e5b1b98f83b03efa77c1b03309c84d62e79bc1`
**HEAD at end:** `30e5b1b98f83b03efa77c1b03309c84d62e79bc1` — unchanged, the round stands.
**Mandate:** refute. No git mutations. Every mutation below was applied to a copy under
`$SCRATCH/r2/`; the repository was read, never written, except for this file.

---

## Lead: the headline is exact, the cascade survived doubling, and **`ordinal` is stable** — and
## the fold is still where the bug is

Asked first, because the brief asked it first:

> **Is `ordinal` stable? YES.** Two full corpus runs, identical inputs, back to back:
> `set(A) == set(B)` is `True`, `A-B = 0`, `B-A = 0`, and **0 of 65,508 keys differ in ratio**.
> Under the change the gate exists to measure — raw vs. injected palette — the key sets are
> *also* identical: `A-RAW = 0`, `RAW-A = 0`. The downstream fear in the brief (ordinals shift →
> every key shifts → `VANISHED` fires spuriously) **does not occur**, and it cannot occur by
> insertion either: ordinals are a dense prefix `0..n-1`, so adding a sibling *extends* the key
> set rather than displacing it. I could not make it move. See *What survived*, and L1 for the
> residual that is real but small.

What I did find is that **four of the fold's nine fixes re-commit, inside the fix, the defect
class they were closing** — which is the prior the brief told me to assume, and it held:

| Round 1 finding | The fold's fix | What round 2 measured |
|---|---|---|
| **B2** baseline silently passes when keys vanish | report `VANISHED` | the gate is now **permanently rc=1 on every clean clone**, and the exposure went **7.4% → 45.7%** |
| **H3** probe header claims a property the code lacks | add a 10-case self-test | the self-test tests a **duplicate** of the predicate; severing the real one leaves it **10/10 green** |
| **H2** gradient sites scored against fiction | exclude them from scoring | a baselined site that becomes gradient-backed can **crash 8.0 → 2.0 in total silence** |
| **B1** a value justified against a ground set that had moved | add `--ink3`/`--ink-3`, 37 tokens | the fold adds **two new grounds** and does not re-derive — **53 of its own 211 residuals** are that collision |

---

## Blocking

### B1 — The gate is now **permanently red on every clean clone**, the comment saying it is not is false, and round 1's B2 exposure grew 6×

**Premise**, `scripts/check-page-contrast.py:205-210`:

> ```
> # ⚠ REPORTED, NOT SILENTLY TOLERATED, and deliberately not fatal on its own: the four pages
> # are derived artefacts a fresh clone legitimately lacks. The caller decides; what is
> # forbidden is not knowing.
> ```

**Measurement — there is no "caller decides".** `verdict()` returns one undifferentiated
`list[str]`, and `scripts/check-page-contrast.py:711-717`:

```python
        problems = verdict(samples, base)
        if problems:
            print(f"\nFAILED — {len(problems)} contrast regression(s):")
            …
            return 1
```

`VANISHED` is appended to the same list as `CROSSED` and is exactly as fatal. No flag, no
threshold, no separate channel exists. The comment names a mechanism that is not in the file.

**Measurement — the live consequence,** `git archive HEAD` into a scratch tree:

```
$ git archive HEAD | tar -x -C $S/clean && cd $S/clean
$ python3 scripts/check-page-contrast.py --against docs/contrast-baseline.json.gz
contrast: 35558 measured site(s) (page x scheme x element) across 56 page(s)
  below AA: 146 of 35420 scored   worst: 2.06:1   ⚠ 138 NOT SCORED (…)

FAILED — 1 contrast regression(s):
  ✗ VANISHED — 29950 baselined site(s) were not measured this run (backlog-table.html x21252,
    dashboard.html x5678, goals.html x1602, features.html x1418). …
rc=1
```

**Measurement — the exposure grew.** Round 1 measured 496 of 6,664 keys (7.4%) from the four
gitignored standing pages. Removing `collapse`'s merge multiplied the baseline ten-fold, and the
standing pages are the largest contributors:

```
committed baseline: 65508 keys, 60 pages
  backlog-table.html  21252
  dashboard.html       5678
  goals.html           1602
  features.html        1418
  ── gitignored total  29950   =  45.7%   (round 1: 7.4%)
```

`.gitignore:147-161` states why these are untracked and regenerated: they are derived from
`docs/backlog.md` and rebuilt by the `regen-*` hooks. `backlog-table.html` alone — *the page the
commit names as the standard* — is **32.4% of the committed baseline**.

**Severity reasoning — Blocking.** Round 1's B2 was Blocking because the gate could not tell
"clean" from "not measured". It can now, and the repair traded a silent pass for a gate that
**cannot be kept green by anyone who does not have this workspace's untracked artefacts**. The
only documented invocation, in the only tree a reviewer can reproduce, is red forever and prints
`FAILED — 1 contrast regression(s)` about something the same message explains is not a
regression. Backlog #56's measured verdict is that a gate red from birth gets switched off; this
one is red from birth in every environment but one. The false comment is the Blocking half: a
reader who hits the red will look for the "caller decides" mechanism and not find it.

**Fix.** Three parts, all small, and the first is the one that matters:
1. Make the claim true or delete it. Separate `verdict()`'s return into regressions and
   measurement gaps, and give `main()` a rule: `VANISHED` alone is **rc=2 CANNOT RUN** (a
   measurement that did not happen is not a regression, which the message already says),
   `CROSSED`/`WORSENED` is rc=1.
2. Decide what the standing pages are. Either exclude the four from `corpus()` *and* from the
   baseline, or have `--against` regenerate them first. Leaving 45.7% of a committed baseline
   pointing at untracked derived files makes it machine-specific, which is the half of B2 the
   fold did not touch.
3. Reword the `FAILED — n contrast regression(s)` header so a vanishing count is not called a
   regression count.

**Structural.**

---

### B2 — The probe's new self-test exercises a **copy** of the predicate the browser runs. Severing the real one leaves it 10/10 green, and round 1's H3 is reported fixed while being inert

**Premise**, `scripts/page-contrast-probe.mjs:19-21`:

> ```
> // ⛔ WHAT IS DONE ABOUT IT: `--self-test` below exercises the pure predicates (`opaque`, the
> // selector builder) with no browser, and `check-page-contrast.py` runs it.
> ```

Three claims. **All three are false.**

**Measurement 1 — it does not exercise `opaque`.** `opaque` lives at `:30-36` *inside* `PROBE`,
which is serialised into the browser by `page.evaluate(PROBE)` at `:172` and therefore cannot
reference module scope. `isOpaque` at `:129-135` is a **verbatim duplicate** of it. The self-test
calls `isOpaque` ten times and `opaque` zero times. Severing the browser-side one on a copy,
against a control proved green first:

```
=== CONTROL ===
10/10 probe self-test cases passed

=== MUTATION: `return parts.length < 4 || parseFloat(parts[3]) >= 0.999;`  ->  `return false;`
    (the in-PROBE opaque(), the line every self-test case is written about) ===
10/10 probe self-test cases passed
```

The mutation is live on the real path — same page, pristine then severed:

```
{"selector":"body>div.wrap>h1",…,"bg":"rgb(247, 246, 243)",…}   ← pristine
{"selector":"body>div.wrap>h1",…,"bg":"rgb(255, 255, 255)",…}   ← severed: every background
                                                                   on every page is now wrong
```

Every background on every page in the corpus changes, every ratio with it, and the guard
installed to catch exactly this reports a clean 10/10.

**Measurement 2 — the selector builder is not tested at all.** `sel` (`:77-89`) is neither
exported nor referenced by any case. It is two of the six components of `sample_key`.

**Measurement 3 — `check-page-contrast.py` does not run it.**

```
$ grep -n 'self-test\|self_test' scripts/check-page-contrast.py | grep -i 'probe\|mjs'
(no output)
```

CI *does* (`.github/workflows/ci.yml:396-397`, in the required `verify` job) — the comment names
the wrong caller.

**Measurement 4 — nothing ratchets any of it.** No mutation manifest
(`ls scripts/mutations/ | grep -i probe` → empty), and both ratchets glob Python only:
`check-ratchet-contract.py:191-194` and `check-selftest-counts.py:299` take
`scripts/*.py` / `*.sh`. The probe declares no case count anywhere. Nine of the ten cases could
be deleted and every guard in the repo would stay green.

There is also a **third** copy of the rule: `OPAQUE_RE` at `:128` is exported and consumed by
nothing in the repository.

And the sentence round 1 H3 quoted *second* survives verbatim:

```
$ grep -rn 'PROBE DECIDES NOTHING' --include='*.py' --include='*.mjs' .
scripts/check-page-contrast.py:308:    ⚠ THE PROBE DECIDES NOTHING. It reports computed colour, …
```

**Severity reasoning — Blocking.** H3's defect was *a comment asserting a property the code does
not have*. The fold's remedy is a comment asserting a property the code does not have, over a
test that cannot fail, on a file outside every ratchet — and it marks H3 closed. This is the
repo's `a-second-implementation-of-one-rule-drifts` (17×) and `a-test-that-cannot-fail` landing
together on one fix. It is Blocking rather than High because the branch's reviewable claim is now
"the probe's rules are tested", a reader has no cheap way to discover it is not, and the next
change to `opaque` will be made in the belief that something is watching.

**Fix.**
1. Delete `isOpaque` and `OPAQUE_RE`. Define `opaque` **once** at module scope and pass it into
   the page — `page.evaluate(([src]) => { const opaque = eval(src); … }, [opaque.toString()])`,
   or move `PROBE` to a string assembled from the exported functions. One rule, one place.
2. Export and case `sel`, or stop claiming it is covered.
3. Add `scripts/mutations/page-contrast-probe.json` and teach `check-ratchet-contract.py` /
   `check-selftest-counts.py` to see `scripts/*.mjs` — otherwise the next `.mjs` guard repeats
   this exactly.
4. Fix `check-page-contrast.py:308` — it is the other half of the finding being closed.
5. Correct `:19-21` to name CI as the caller.

**Structural.**

---

## High

### H1 — The gradient exclusion is a **silent escape hatch for a real regression**, and the comment claiming it is not describes the wrong protection

**Premise**, `scripts/check-page-contrast.py:210-212`:

> ```
> # ⚠ A SITE WHOSE BACKGROUND IS A GRADIENT IS NOT SCORED — its ratio is not a fact about
> # what a reader sees. It still counts as MEASURED for the vanishing check, so excluding it
> # cannot be used to make a baselined site disappear quietly.
> ```

**Measurement**, driving the delivered `verdict()`:

```
A) baselined at 8.0, now 2.0, ORDINARY background:
    ['CROSSED below AA: 8.00 -> 2.00 (needs 4.5) [light] p.html :: \'t\'']
B) baselined at 8.0, now 2.0, and the background became a GRADIENT:
    []

C) already-failing and getting WORSE:
   ordinary : ['WORSENED while already below AA: 2.50 -> 1.20 [light] p.html :: \'t\'']
   gradient : []
```

The sentence is true about `VANISHED` — `seen` is computed at `:216` *before* the filter at
`:217`, so the key does not vanish — and it is the wrong protection. The site does not vanish; it
is **dropped from the verdict entirely**, reporting nothing, rc=0. Turning a background into a
gradient is an ordinary style change, and this gate exists to guard style changes.

The self-test locks in only the half that holds:

```python
case("a site that becomes gradient-backed does NOT read as vanished",
     any("VANISHED" in x for x in verdict([g(8.0)], _b)), False)
```

`g(8.0)` is a **passing** site. There is no case for a gradient-backed site that crossed —
`fixing-a-premise-is-not-covering-the-branch`.

**Scale.** 138 sites are already unmeasurable today, across four pages, and they are permanently
unscored:

```
unmeasurable (gradient-backed) sites: 138; nominal ratio below threshold: 2
  [('…sidebar-refresh-after-ingest…', 38), ('…verify-counts-delete-anchor…', 34),
   ('…m3-1-cloud-e2e…', 34), ('…money-guard-review…', 32)]
```

**Severity reasoning — High, not Blocking.** It needs a background to *become* an image, so it
does not fire on this branch's own change (verified: raw → palette is rc=0 with zero
regressions). But it is a standing hole in the ratchet with a comment over it saying the hole is
covered, and the hole's size grows with every gradient anyone adds.

**Fix.** Report, do not drop. When a baselined key is present in the run but unscorable, emit
`UNSCORABLE — <key> was <prior> and can no longer be measured (background became an image)` and
treat it with the same rule as `VANISHED` under B1's fix. Then add the missing case: a
gradient-backed site whose prior was passing and whose nominal ratio crossed **must** produce a
line.

**Structural.**

---

### H2 — The fold's **two new tokens collide with each other**, and 53 of its own 211 residual failures are that collision. The justification comment enumerates a ground list that predates it

**Premise**, `scripts/page_chrome.py:94-99` — the derivation of the faint-ink value, quoted as
the reason `#616c7c` is right:

> ```
> # chosen by measuring EVERY background this token actually lands on across the corpus:
> #     rgb(255,255,255) x4432   rgb(247,246,243) x1321   rgb(244,241,234) x96
> #     rgb(238,246,242) x20     rgb(247,235,217) x20     rgb(243,241,237) x18
> # and clearing the WORST of them (#f7ebd9) at 4.52:1, chosen against 5,907 real sites.
> ```

and the fold's own additions at `:142` / `:146`: `"--code": "#e9e4db"`, `"--pill": "#e9e4db"`.

**Measurement — the grounds the token lands on *now*, with the palette this commit ships:**

```
grounds --fg3/--ink3 ACTUALLY lands on (top 10 of 22):
    2866  #ffffff   5.32:1
     983  #f7f6f3   4.93:1
      53  #e9e4db   4.20:1 <-- BELOW AA, and NOT in the list at page_chrome.py:96-99
      37  #f6f3ed   4.81:1
      18  #f3f1ed   4.72:1
      17  #f2efe9   4.64:1
      10  #eef6f2   4.84:1
      10  #f7ebd9   4.52:1   ← the "worst" the comment clears
```

`#e9e4db` is the fold's own `--code`/`--pill`. It is absent from the enumerated list because it
was not a standard token when that list was measured. It is now **the only ground the faint ink
fails**, and it is the single largest group in the residual:

```
top (fg,bg) pairs among the 211 remaining failures:
    53  fg=rgb(97, 108, 124)  bg=rgb(233, 228, 219)      ← #616c7c on #e9e4db, 25.1% of the 211
    35  fg=rgb(168, 105, 11)  bg=rgb(247, 246, 243)
    28  fg=rgb(168, 105, 11)  bg=rgb(253, 244, 227)
…
e.g. 2026-09-23-topic-pr-336-338.html  div.box>p.sub>code  4.205:1 needs 4.5  '6a0974b3'
```

A pure derivation over all 22 live grounds:

```
minimal uniform darkening of #616c7c that clears 4.5 on ALL 22 grounds: d=5 -> #5c6777
```

**Five RGB points on one token the commit already edits removes 25% of its own residual.**

**It is not a regression.** Their raw (unstyled) ratios were `min 3.255 max 3.283`, so the palette
improved them; `--against` the raw baseline is `OK`, rc=0. That is why this is High and not
Blocking, and it is the honest half of the story.

**Severity reasoning — High.** This is round 1's B1 recurring inside B1's fix: *a value justified
against a measured ground set, where the set then moved and nothing was re-derived*. The comment
is now a **false provenance** — it presents a six-ground enumeration as the basis for a choice
made against twenty-two, and the two grounds it omits are ones the same commit introduced. A
reader checking the claim will find the token clears every ground listed, and miss that the list
is stale.

**Fix.** `--fg3`/`--ink-faint`/`--ink3`/`--ink-3` → `#5c6777` in `STANDARD_LIGHT`, re-measure, and
replace the hand-written ground enumeration with the derived one. Then add the invariant that
would have caught it, which is pure, browser-free and cheap — in `explainer-serve.py`'s palette
block beside the parity case:

```python
case("every ink token clears AA on every ground token in the same palette", …)
```

**Structural.**

---

### H3 — A **fifth, sixth and seventh spelling**. The new case hard-codes one role's four names, so it cannot see any of them — and the commit quotes the memory it is about to violate

**Premise**, `scripts/page_chrome.py:150-153`:

> ```
> # ⚠ The recall hook fired `a-shim-can-fail-in-both-directions — fixing only the one name you
> # noticed` at the exact step this palette was written, and I quoted it in the step banner.
> ```

and the case the fold added, `scripts/explainer-serve.py:1729-1735`:

```python
case("every spelling of the faint-ink role carries ONE value, in light",
     lambda: len({page_chrome.STANDARD_LIGHT[t]
                  for t in ("--fg3", "--ink-faint", "--ink3", "--ink-3")}) == 1)
```

**Measurement — every ink-role spelling defined anywhere in the corpus, and whether the palette
covers it:**

```
  --ink        YES   #12161c
  --ink-soft   YES   #39424f
  --ink-faint  YES   #616c7c
  --ink2       *** NO ***
  --ink-2      *** NO ***
  --ink3       YES   #616c7c
  --ink-3      YES   #616c7c
  --muted      *** NO ***
  --fg / --fg2 / --fg3   YES
```

```
--ink2  #4a4640  on 4 pages (sidebar-refresh, money-guard-review, verify-counts, m3-1-cloud-e2e)
--ink-2 #39424f  on backlog-table.html  ← THE PAGE THE COMMIT NAMES AS THE STANDARD
--muted #78716c  on 2026-08-24-findings-slice-a-file-or-not.html
```

The **mid-ink role** (`--fg2` = `--ink-soft` = `#39424f`) has two further spellings, exactly the
shape B1 cost 23 regressions on, one role over. `--ink-2` happens to agree with the standard by
coincidence; `--ink2`'s `#4a4640` does not, so four pages keep a private mid-ink after a commit
whose purpose is that they should not. `--muted` is a seventh.

The new case is a **hard-coded 4-tuple for one role**. It cannot see `--ink2`, `--ink-2` or
`--muted`, and it would not notice a fifth spelling of the *faint* role either. It is a test of
the instance, not the class — and the class is precisely what the quoted memory is about.
`scripts/check-theme-token-coverage.py` does not cover this: it compares `gen-dashboard`'s light
palette against `brief-compose`'s OS-dark shim, a different set difference entirely.

**Severity reasoning — High.** Not a contrast failure — `#4a4640` and `#39424f` both clear AA — so
the readability headline is unaffected. It is a **goal** failure: the branch's stated purpose is
"single layer that decides common look and feel", and after it four pages still decide their own
mid-ink. And the guard written to prevent recurrence is itself instance-shaped.

**Fix.** Derive the spelling set rather than typing it. Grep `--[a-z0-9-]+\s*:` across
`docs/explainers/*.html`, group by resolved role, and assert every spelling of a covered role is
in the palette with the role's value — failing on an *uncovered* spelling of a covered role. Add
`--ink2`, `--ink-2` and `--muted` in the same pass.

**Structural.**

---

## Medium

### M1 — `--report`, the fix for L2, reprints verbatim the one number H2 was filed to remove

**Measurement.** The whole of `--report`'s first screen:

```
contrast: 65508 measured site(s) (page x scheme x element) across 60 page(s)
  below AA: 211 of 65370 scored   worst: 2.06:1   ⚠ 138 NOT SCORED (text over a gradient or
  image — no single background colour exists, so any ratio would be fiction)

  worst sites (ratio, threshold, scheme, page, text):
  ✗   1.11 / 4.5  [light] 2026-08-12-explanation-sidebar-refresh-after-i   'create'
  ✗   2.06 / 4.5  [dark ] 2026-08-13-explanation-m3-1-cloud-e2e-70f7ab1.   '★'
```

The `1.11` / `'create'` row is **round 1 H2's own example** — the `.seg` on a
`repeating-linear-gradient`, the number the fold's commentary calls "a number no reader could
ever experience". It is the top line of the new report, flagged `✗`, two lines under a summary
that says `worst: 2.06:1` and `138 NOT SCORED`.

`summarise`'s docstring, `scripts/check-page-contrast.py:276`:

> `"""PURE. -> the headline numbers, so a report cannot disagree with its own detail."""`

`scripts/check-page-contrast.py:725` sorts `samples`, not `scored`.

**Severity reasoning — Medium.** No verdict is affected; it misleads a human reading the one
output the flag exists to produce, and it is the exact fiction the same commit removed from
`summary`.

**Fix.** `worst = sorted((s for s in samples if not s.get("bg_uncertain")), …)`, and list the
unmeasurable ones separately under their own heading with a distinct glyph — they are worth
seeing, they are just not failures.

**Transitional.**

---

### M2 — The only documented invocation names a file this commit deleted

**Measurement.** `scripts/check-page-contrast.py:28-29`, unchanged by the fold:

```
    python3 scripts/check-page-contrast.py --write-baseline docs/contrast-baseline.json
    python3 scripts/check-page-contrast.py --against docs/contrast-baseline.json
```

```
$ ls docs/contrast-baseline.json
ls: docs/contrast-baseline.json: No such file or directory
$ ls docs/contrast-baseline.json.gz
-rw-r--r--  210502  docs/contrast-baseline.json.gz
```

Those two lines are the **only** references to the gate's baseline anywhere outside review
documents. `--against` on the documented path is rc=2 CANNOT RUN; `--write-baseline` on it
succeeds and writes **gzip bytes under a `.json` name** (verified: first bytes `b'\x1f\x8b'`),
leaving the committed `.json.gz` orphaned and a liar of a file beside it.

**Severity reasoning — Medium.** The gate is run by a human typing a command, and the only place
that command is written down is wrong. Round 1's M1 was the same class (a comment pointing at a
`dev-process.md` entry that did not exist); the fold corrected M1's *comment* and did not search
for the class in the file it was editing.

**Fix.** `.json` → `.json.gz` on both usage lines. Optionally have `dump_baseline` refuse a path
not ending `.gz`, so the name cannot lie.

**Transitional.**

---

### M3 — A new mutation entry's **name is false**, and the consequence it misses is the worse one

**Premise**, `scripts/mutations/check-page-contrast.json`:

```json
"name": "siblings are merged again, so a passing one can cross below AA behind a failing one",
"edits": [["        counter[base] = n + 1", "        counter[base] = n"]],
"expect": "...and are numbered in document order, so the numbering is reproducible"
```

and `scripts/check-plan-code.py:1375-1378`, three lines above the count this fold raises:

> `An entry whose NAME is wrong is a false claim with a green tick.`

**Measurement**, running the mutation:

```
under the mutation, collapse([Copy 2.221, Close 5.492]) ->
   samples returned: 2 | ratios: [2.221, 5.492] | ordinals: [0, 0]
   -> NOT merged: both samples survive, both carry their own ratio.

the masking scenario the name asserts — Close crashes 5.492 -> 3.0 behind a failing Copy:
   verdict: ["CROSSED below AA: 5.49 -> 2.22 … 'Copy'", "CROSSED below AA: 5.49 -> 3.00 … 'Close'"]
   -> the crossing IS reported. The mutation does not restore the masking its name claims.

what it ACTUALLY does, on the baseline write path:
   {'p.html|light|div>div>button|13.1|400|0': 5.492}
   -> one key, LAST sibling's ratio (5.492) wins. The WORSE one (2.221) is lost.
```

So the real consequence is a silent ten-fold baseline shrink that records the **best** sibling
rather than the worst — strictly worse than the named one, and unrecorded.

**Severity reasoning — Medium.** The entry does go red via its named case (all 10 do, measured
below), so the ratchet works. What is wrong is the only written statement of *what the ordinal
protects*, in the file future readers will consult to find out.

**Fix.** Rename to what it severs, e.g. *"every sibling is numbered 0, so the written baseline
collapses to one key per group and keeps the LAST sibling's ratio, not the worst"*.

**Transitional.**

---

## Low

### L1 — `ordinal` is stable, and the residual is misattribution rather than vanishing — bounded at 6.1%

Recording the shape, because the brief asked and because the number is worth having next time.
96.6% of sites are now discriminated by a positional counter, over groups up to 2,212 members:

```
distinct base keys: 6664 of 65508 sites
sites in a group of >1: 63254 (96.6%)
largest:  2212  backlog-table.html|dark|details>div.prose>code|12.9|400
```

An insertion cannot produce `VANISHED` (the key set is a dense prefix, measured: inserting one
direct-child `<code>` into `backlog-table.html` gave `VANISHED: 0  NEW: 1`). It can silently
re-point a key at a neighbour. That only matters where a group is heterogeneous:

```
groups with >1 member: 4410;  heterogeneous in ratio: 302 (6.8%)
sites living in a heterogeneous group: 4018 of 65508 (6.1%)
keys whose ratio would change if one sibling were inserted at the FRONT of its group: 1176
```

A *deletion* shrinks a group and does fire `VANISHED` for its last ordinal — which, on four
pages regenerated from `docs/backlog.md` on every row change, will be routine. Worth a sentence
in the docstring (which currently says only "shifts only for siblings AFTER an insertion" —
true, and silent about what the shift does). **Transitional.**

### L2 — `hasImage` and `bgOf` disagree about `<html>`

`hasImage` (`:45-54`) loops `while (n && n !== document.documentElement)`, so the root element is
never examined for a background image; `bgOf` (`:64-65`) explicitly checks
`document.documentElement`'s background colour. A page-level gradient on `html` would therefore
be scored against the root's colour and reported as measurable. Latent only — measured, 0 pages
in this corpus do it. One line: hoist the check above the loop. **Transitional.**

### L3 — `OPAQUE_RE` is exported and consumed by nothing

`scripts/page-contrast-probe.mjs:128`. A third copy of a rule that should have one. Delete it
with B2's fix. **Transitional.**

---

## What survived refutation

Recorded so round 3 does not re-spend the time.

**The headline is exact, and the population is the same on both sides.**

```
raw      : 65508 measured site(s) across 60 page(s)   below AA: 4192 of 65370   worst 2.06:1
palette  : 65508 measured site(s) across 60 page(s)   below AA:  211 of 65370   worst 2.06:1
set(raw keys) == set(palette keys) : True   (RAW-A = 0, A-RAW = 0)
```

**`ordinal` is stable.** Two identical back-to-back runs: `set(A)==set(B)` `True`, 0 of 65,508
ratios differ. Insertion extends rather than displaces. See L1 for the bounded residual.

**Round 1's B1 is genuinely closed.** `--against` the raw baseline:
`OK — no element crossed below AA and none already failing got worse`, rc=0. The 23 worsened
sites are **0**. The four pages' `--ink3` now resolves to the standard, and the 53 that remain
below AA (H2) were 3.26:1 before and are 4.21:1 now — improved, not regressed.

**The cascade holds for all 37 tokens, doubled from the 18 round 1 verified.** Chromium, every
served page, both schemes, both forced themes, reading each token on `documentElement` and
`body`:

```
scheme=light data-theme=none :: 60 pages x 37 tokens -> deviations: 0
scheme=dark  data-theme=none :: 60 pages x 37 tokens -> deviations: 0
scheme=light data-theme=dark :: 60 pages x 37 tokens -> deviations: 0
scheme=dark  data-theme=light:: 60 pages x 37 tokens -> deviations: 0
TOTAL: 0
```

**Light/dark parity holds.** `set(STANDARD_LIGHT) == set(STANDARD_DARK)` is `True`, 37 each, no
role defined in one scheme only — and the fold added the case that asserts it. Every foreground
token clears AA on its own semantic ground in both schemes (`--warn` on `--warn-bg` 5.07/7.35,
`--danger` on `--danger-bg` 6.09/6.16, `--code-fg` on `--code` 7.15/7.59, `--accent` on
`--accent-bg` 5.01/6.35, `--good` on `--verified-bg` 5.24/8.01). The one exception is H2.

**The ΔE adjudication is correctly recorded.** `page_chrome.py:99-105` withdraws "imperceptible"
and states the right thing: `#666a84` is nearer in RGB (13.15 vs 17.32) and nearly twice as far
perceptually (ΔE 7.88 vs 4.01). Round 1's M-finding is discharged honestly, including the part
that was against the author.

**All ten mutation entries resolve and go red via the case they name**, hand-run on a temp copy
against a control proved green first:

```
CONTROL: 75/75 self-test cases passed  rc=0
10/10 entries: anchor resolves exactly once, suite goes RED, the NAMED case is the one that fires
```

(M3 is about one entry's *name*, not its mechanism.)

**The `worst: 1.107` fiction is gone from the summary** — `worst` is now 2.06 over `scored`, and
`unmeasurable` is reported rather than hidden. M1 is about the new `--report` path only.

**Declared counts, all verified by running:**

```
check-page-contrast.py --self-test        75/75
page-contrast-probe.mjs --self-test       10/10      (inert — see B2)
explainer-serve.py --self-test          215/215
check-plan-code.py --self-test          131/131
check-selftest-counts.py                OK — 51 scripts, every count verified by running it
check-ratchet-contract.py               OK — 44 guards
check-fixture-variation.py              OK — 769 parameters / 63 files, 117 ratcheted, 7 exempt
```

The CI step claimed by H3's fix **is** present and in the required `verify` job
(`.github/workflows/ci.yml:396-397`). It runs; it measures a duplicate.

---

## Could Not Measure

**`python3 scripts/check-plan-code.py --mutate .`** — the full sweep, 1,189 mutations over 58
guards, backlog #217's known cost problem. Round 1 reached 275/1187 and stopped. I did not start
it: a Codex reviewer is running concurrently in this tree and 1,189 spawned suites would contend
with it for the whole machine, which is the `concurrent-agents-go-wrong` hazard. **Treat the full
sweep as NOT RUN by this round.**

What I ran instead, and its exact scope: all **10** entries of
`scripts/mutations/check-page-contrast.json` applied one at a time to a copy of the delivered
file under a scratch directory, against a control proved green first — every anchor resolved
exactly once, every mutation went red, and in every case the failing case was the one the entry
names. That is stronger than the sweep for *this file* and says nothing about whether the fold
orphaned an anchor in one of the other 57 manifests. `check-ratchet-contract.py` passing and
`check-plan-code.py --self-test` agreeing at 131/131 with `EXPECTED_MUTATIONS` summing to 1,189
are weak evidence against that, not proof.

---

## Verdict

**NOT CONVERGED: 2 Blocking · 3 High · 3 Medium · 3 Low**

The measurement at the centre of this branch is sound and I could not shake it: the headline is
exact over an identical population, the 37-token cascade wins on every page in every state,
`ordinal` is stable, and round 1's B1 regressions are genuinely zero. The fold did real work.

What fails is the same thing that failed in round 1, one layer in: **four of the fixes reproduce
the defect class they close.** The vanishing fix makes the gate unkeepable and documents a
"caller decides" mechanism that is not in the file; the probe's new self-test cannot fail and
says it covers two things it does not; the gradient exclusion closes a fiction and opens a silent
path for a real crossing; and the palette adds two grounds without re-deriving the value whose
justification enumerates the old ones. Each is small to fix. None of them is a wording slip.

**HEAD at end: `30e5b1b98f83b03efa77c1b03309c84d62e79bc1`** — matches the start.

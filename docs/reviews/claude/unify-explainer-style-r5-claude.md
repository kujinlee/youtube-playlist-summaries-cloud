# `unify-explainer-style` round 5 — Claude half, standing in for Codex

**VERDICT: NOT CONVERGED.**

**Does the deliverable carry a Blocking or High?** **YES — one High (H1), in `scripts/check-page-contrast.py` itself**, repeated in `docs/backlog.md` #241 and in the `docs/dashboard-entries.md` entry. No Blocking.

Subject: commit `2025da34` on branch `unify-explainer-style` (PR #364), diff `470f4ba5..2025da34`, five files.

Everything below was produced by running commands. Where I could not run something I say so in *what I could not check*.

---

## Summary table

| # | Severity | Subject | Where |
|---|---|---|---|
| H1 | **High** | The stated BOUND is false on one of its four named components — **palette selection is not covered**, and `extra_css` is not even checked for being forwarded. Four severances of that path, all green at 104/104 | `scripts/check-page-contrast.py:893-901`, `docs/backlog.md` #241, `docs/dashboard-entries.md` |
| M1 | Medium | The production comment names the **wrong missing dependency**: survival is attributed to "Chromium absent", measured to be `playwright` the npm **package** absent at module resolution. Installing Chromium changes nothing | `scripts/check-page-contrast.py:786-795`, `:888-891` |
| L1 | Low | #245's `⭐ SUB-SECOND` headline cites a 4.0s whole-run figure as its evidence. The claim is true (measured: 91 ms) but its provenance measures a different thing | `docs/backlog.md` #245 |
| L2 | Low | No manifest entry severs the seam's **own default** `measure_fn=measure` — the one line production uses. The suite does kill it; `--mutate .` cannot see that it still does | `scripts/mutations/check-page-contrast.json` |
| L3 | Low | `docs/backlog.md` #236 still says "every one of the **1,394** mutation entries" in the present tense; the figure is now 1,411 | `docs/backlog.md:263` |
| L4 | Low | The `⚠ BOUND` clause is on #241 only; #239 and #240 carry a byte-identical closure paragraph without it | `docs/backlog.md` #239, #240 |
| L5 | Low | `(tmp / "scripts").mkdir()` in `_world` is dead, while the identical line in the D2 setup is now load-bearing | `scripts/check-page-contrast.py:801` |

Claims that survived refutation are in **§ Confirmed** — including one where my own suspicion was the thing refuted.

---

## H1 (High) — the BOUND is stated as four components and measures three

### The claim attacked

`scripts/check-page-contrast.py:893-901`, the `main()` docstring:

```
    ⚠ THE BOUND, STATED RATHER THAN HIDDEN. A `measure_fn` double covers this function's
    DECISION path — corpus resolution, palette selection, verdict rendering, refusal routing.
```

Restated verbatim in `docs/backlog.md` #241's closure (`⚠ BOUND, STATED RATHER THAN HIDDEN: the seam covers main()'s DECISION path — corpus resolution, palette selection, verdict rendering, refusal routing`) and in the dashboard entry (`⚠ BOUND: the seam covers main()'s DECISION path — corpus resolution, palette selection, verdict rendering, refusal routing`).

The palette-selection path is `scripts/check-page-contrast.py:932-939`:

```python
        if args.extra_css:
            extra = Path(args.extra_css).read_text(encoding="utf-8")
        elif args.raw:
            extra = ""
        else:
            import page_chrome
            extra = re.sub(r"</?style>", "", page_chrome.standard_palette_css())
```

### What I ran

Four severances of exactly that path, applied one at a time to a copy of the delivered file inside a browserless staged tree, each followed by the full suite:

```
PALETTE SELECTION severed: the standard palette is never applied (extra = '')
  rc=0  104/104 self-test cases passed
  reds: NONE  <-- SURVIVED

PALETTE SELECTION inverted: --raw now gets the palette, the default gets nothing
  rc=0  104/104 self-test cases passed
  reds: NONE  <-- SURVIVED

--extra-css branch severed: a caller-supplied stylesheet is ignored
  rc=0  104/104 self-test cases passed
  reds: NONE  <-- SURVIVED

extra_css is no longer FORWARDED to the measurement at all
  rc=0  104/104 self-test cases passed
  reds: NONE  <-- SURVIVED
```

For contrast, the same procedure over the four entries the commit *does* add kills every one (see § Confirmed, claim 5), and over the seam's default kills two cases (L2). So the harness is working; this path is simply not reached by any case.

### Why that refutes the claim

Measured, the four named components are **3 of 4**:

| Component | Covered? | Evidence |
|---|---|---|
| corpus resolution | ✅ | manifest entry 13 → 2 reds, both named |
| verdict rendering | ✅ | entries 15, 16 → 2 reds each, both named |
| refusal routing | ✅ | the D2 pair reds when the default is severed (L2) |
| **palette selection** | ❌ | four severances, 104/104 green, zero reds |

Three things make this High rather than Medium:

1. **The uncovered branch is the one the file exists for.** The comment directly above it, `:926-928`, says: *"THE STANDARD PALETTE BY DEFAULT, BECAUSE THAT IS WHAT A READER SEES. The pages on disk do not carry it — `explainer-serve` injects it at send time, so a harness that measured the bare files would be measuring a view nobody has. Backlog #221."* My first severance makes the gate measure the bare files — reinstating #221's original defect — and the suite reports 104/104.

2. **It reproduces #239's own defect shape inside the fix for #239.** #239 is *one argument threaded, its sibling not*. The recorder is `scripts/check-page-contrast.py:812-819`:

   ```python
       def _recorder(samples: list[dict]):
           seen: dict = {"pages": None, "root": None}

           def fn(pages, extra_css: str = "", root=None, **kw):
               seen["pages"] = sorted(q.name for q in pages)
               seen["root"] = root
               return samples
           return fn, seen
   ```

   `root=None` is a deliberate sentinel and is asserted. `extra_css: str = ""` is the same opportunity **not** taken — the parameter is accepted into a default and never recorded, so dropping `extra_css=extra` from the call site is invisible. `**kw` extends that silence to any argument added later.

3. **The capability is already there; it is the claim that is wrong, not the design.** I drove the real default-palette branch through the seam and captured what a case could have asserted:

   ```
   rc: 0 pages: ['a.html']
   extra_css len: 2825 | has --bg token: True | has <style>: False
   first 80: :root{--bg:#f7f6f3;--bg2:#ffffff;--card:#ffffff;--panel:#ffffff;--ground:#f7f6f3
   ```

   So the fix is small (record `extra_css`, two cases over the `--raw` / default pair, one manifest entry). What cannot stand is a paragraph headed *"STATED RATHER THAN HIDDEN"* that hides one quarter of its own subject — this repository's `a-framing-widened-to-fit-is-no-longer-a-claim` and `assert-the-property-not-the-mechanism` shape, and the honesty mechanism is the thing that is wrong.

**Either fix is acceptable:** add the palette cases + entry, or delete `palette selection` from all three bound statements. What is not acceptable is leaving the sentence as it is.

---

## M1 (Medium) — the comment names the wrong missing dependency

### The claim attacked

`scripts/check-page-contrast.py:786-795` and, in near-identical words, the `main()` docstring at `:888-891`:

```
    # MEASURED: that mutant is killed only where a browser exists, and SURVIVES in the world
    # CI actually has — node present, Chromium absent (`ci.yml:53-57` installs node 22; nothing
    # installs Chromium).
```

### What I ran

The citation itself is correct — `.github/workflows/ci.yml:53-57` is `uses: actions/setup-node@v4` … `node-version: '22'`, and `grep -rn playwright .github/workflows/` returns nothing, so no job installs browsers.

But the world the mutant actually runs in is the **staged tree**, and there the probe never reaches Chromium:

```
$ node scripts/page-contrast-probe.mjs light docs/explainers/<page>.html     # staged/pruned tree
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'playwright' imported from
  .../pruned/scripts/page-contrast-probe.mjs
PROBE RC=1
```

The same severance, run through the harness in that tree, refuses with:

```
FAILED: the light browser run exited 1: } /  / Node.js v20.18.2. TREAT THIS AS NOT RUN.
94/94 self-test cases passed
PRE-SEAM SEVERED browserless RC=0
```

— i.e. the `CannotRun` is `measure`'s *"the {scheme} browser run exited {returncode}"* arm (`:388-390`) raised by an **ESM resolution failure**, not by a browser.

And this machine **has** Chromium: `~/Library/Caches/ms-playwright/chromium-1223` exists, and the same probe run in the real worktree emits rows (`{"selector":"body>div.wrap>h1",…}`). So Chromium being present did not prevent the survival in the staged tree.

### Why that refutes the claim

`HARNESS_TREE` (`scripts/check-plan-code.py:199-207`) is `("scripts", "supabase", "docs", "node_modules/typescript", ".claude/hooks", ".github/workflows")`. The `playwright` **package** is never staged, so the mutant survives in every staged tree regardless of what browsers the runner has. Installing Chromium in CI — the action the sentence invites — would change nothing.

The correct mechanism *is* written down, in `docs/backlog.md` #239/#240/#241 and the dashboard entry: *"`HARNESS_TREE` stages `node_modules/typescript` ONLY … so `measure()` can NEVER succeed inside a staged tree"*. The two **code** sites carry the weaker, misattributing version instead. This is the third pass over the same sentence: #240's original falsifier named a no-node runner, Phase 6 corrected it to Chromium-absent, and the operative dependency is a layer further down again (`true-about-the-name-silent-about-the-layer`). The repair is to replace "Chromium absent" with the `HARNESS_TREE` sentence the backlog already has.

---

## L1 (Low) — #245's sub-second headline is evidenced by a figure for something else

`docs/backlog.md` #245:

> ⭐ **THE FIX IS A SUB-SECOND EAGER PASS:** every `edits` find-string in every manifest either occurs in its target or the run refuses, BEFORE any tree is staged or any suite runs. Reproduced at 4.0s on a one-manifest tree versus 15 minutes in CI.

4.0s is the wall time of a complete 16-mutation run on a one-manifest tree (I reproduced it: `22:10:41 → 22:10:45`). It is not a measurement of an eager anchor-binding pass, which does not exist yet, and 4.0s is not sub-second. The comparison also sets 16 entries against a 176-entry CI shard.

I measured the actual thing, over the real repo:

```
eager anchor-binding pass over ALL manifests: 1411 entries, 1419 find-strings, 59 targets read -> 91 ms
unbound: 0
```

So the claim is **true** — and now has provenance. The row's own evidence sentence did not supply it. (The dashboard entry is careful here: it says only *"The class wants a sub-second eager anchor-binding pass"*. The backlog row is the overclaiming copy.)

---

## L2 (Low) — the seam's own default has no manifest entry

`def main(argv, root=ROOT, measure_fn=measure)` — the default is the **only** path production uses (`:1031-1032`, `sys.exit(main(sys.argv[1:]))`). No entry in `scripts/mutations/check-page-contrast.json` severs it.

Measured — the suite does catch it today:

```
default severed to a no-op (the seam's own default is the ONLY production path)
  rc=1  102/104  reds: ['main() over an EMPTY constructed world refuses with the CANNOT-RUN code',
                        '...and --raw over a DIFFERENT empty world refuses identically']
default severed to a stub returning one fabricated sample
  rc=1  102/104  reds: [same two]
```

So this is a ratchet gap, not a coverage gap: `--mutate .` cannot tell if that protection ever stops holding. One entry naming those two cases closes it. (That measurement also refutes the worry in the brief that the D2 pair is now vacuous — see § Confirmed.)

---

## L3 (Low) — a stale present-tense figure in a file this commit edits

`docs/backlog.md:263` (#236): *"so every one of the **1,394** mutation entries is measured by a check with no authority"*. Derived count today: **1,411** (my pass above; `sum(EXPECTED_MUTATIONS.values())` asserted at `scripts/check-plan-code.py:4948`). The staleness predates this commit (it was 1,407 at `470f4ba5`) and widens with it. Every other 1,394/1,407 occurrence I found is a past-tense `⟳` trail entry and correctly historical:

```
scripts/check-plan-code.py:4926  ⚠ 1394 is the GUARD'S OWN FIGURE, read from `got 1394 want 1211`
scripts/check-plan-code.py:4939  ⚠ 1407 is the GUARD'S OWN FIGURE, read from `got 1407 want 1394`
scripts/check-plan-code.py:4947  ⚠ 1411 is the GUARD'S OWN FIGURE, read from `got 1411 want 1407`
```

No stale `94 cases` site survives anywhere (`check-selftest-counts.py` → rc=0, *"52 script(s) declare a count, every one verified by running it"*).

---

## L4 (Low) — the bound is on one of the three closure rows

#239, #240 and #241 carry a byte-identical closure paragraph (structurally-browserless + negative control + D2 reclassification). Only #241 then adds `⚠ BOUND, STATED RATHER THAN HIDDEN`. A reader arriving at #239 or #240 gets the closure without the limitation. Given H1 the sentence has to be revisited at every site anyway; put the corrected version on all three.

---

## L5 (Low) — one `mkdir` is dead and its twin is load-bearing

`_world` (`:798-805`, the `mkdir` at `:801`) does `(tmp / "scripts").mkdir()`, which nothing reads: the recorder replaces `measure`, so the probe path is never taken in any of the four new worlds. The identical line in the D2 setup (`:775-777`) **became** load-bearing with this commit — it is what makes the probe missing under the constructed root, which is why those two cases now print `page-contrast-probe.mjs is missing` instead of `no pages to measure`. The two lines look interchangeable and are not.

---

## Confirmed — claims I attacked and could not break

**Claim 1 — "zero external call sites change".** Holds. `measure` has exactly one call site, the seam default. `main` has one production caller (`:1032`) and six suite call sites. The only module that loads this file is `scripts/explainer-serve.py:1754`, which takes the pure `contrast()` (`_m.contrast(fg, _rgb(pal[k]))`); `grep -rn "check-page-contrast.py"` over `scripts/ .claude/ tests/` returns only that, plus guards reading it as *data* (`check-selftest-counts`, `check-fixture-variation`, `check-plan-code`, `check-main-drivable`). `measure_fn=measure` as a def-time default is not a hazard here: nothing monkeypatches the module attribute, and the default binds the same object a mutation would rewrite.

**Claim 1b — the D2 refusal message change is NOT a further weakening; my suspicion was the thing refuted.** Pre-seam the two D2 cases refused with `no pages to measure` (reproduced: `CONTROL(pre-seam, browser present) RC=0`, 94/94, that message twice). Post-seam they refuse with `page-contrast-probe.mjs is missing` — in CI too (`verify` log, 05:06:40: the message twice, then `104/104 self-test cases passed`). I expected the pair to be left asserting nothing. They are not: they are now the only thing binding the seam's **default** (L2). Net, the pair measures something it did not measure before.

**Claim 2 — "16 killed, 16 attributed, 0 survivors in a browserless world".** Reproduced exactly, in 4 seconds:

```
OK — delivered scripts mutated: 1 file(s), 16 mutation(s), 16 killed,
16 attributed to the case each names, 0 survivor(s) — measured over the WHOLE manifest
```

On whether editing `EXPECTED_MUTATIONS` in the copy invalidates it: **no, with one stated caveat.** The dict is read only by the whole-manifest drift gate (`scripts/check-plan-code.py:1801-1811`) which must balance before execution begins; per-mutation verdicts are computed downstream and never consult it. Making it `{"scripts/check-page-contrast.py": 16}` is therefore *necessary* to run a pruned tree at all, not a loosening of the verdict. The caveat is that the pruned run proves nothing about the repo's declared sum — which I verified independently two ways: `check-plan-code.py --self-test` → `178/178 passed` (its case at `:4948` asserts 1411), and my own count over all 59 manifests → `1411 entries, 1419 find-strings`.

**Claim 3 — "the harness is structurally browserless".** Confirmed directly (M1's probe run). `HARNESS_TREE` read, not guessed — six entries, `node_modules/typescript` the only `node_modules` member. `scripts/page-contrast-probe.mjs:28` is `import { chromium } from 'playwright';`, as cited.

**The question the brief asked me to add — are there manifest entries anywhere whose kill depends on `measure()` running?** I checked all 59 manifests. `grep -ln page-contrast-probe scripts/mutations/*.json` returns nothing (the probe `.mjs` has no manifest at all), and `scripts/mutations/check-page-contrast.json` is the only manifest naming this file. All 16 of its entries kill in a browserless tree (claim 2). Nothing else in the repo runs the live gate either: `grep -rn "check-page-contrast" .github/workflows/` finds only `--self-test`, and the comment at `ci.yml:385-392` says so in writing. **No finding.**

**Claim 4 — the negative control.** Reproduced with the exact numbers, and extended to the four-world matrix myself rather than taken on report:

| World | Result |
|---|---|
| pre-seam control, browser present | `94/94 self-test cases passed`, rc=0 |
| pre-seam **severed**, browser present | `92/94`, rc=1 — **killed**, reds are the two D2 cases |
| pre-seam control, browserless staged tree | `94/94`, rc=0 |
| pre-seam **severed**, browserless staged tree | `94/94`, rc=0 — **SURVIVED** |
| pre-seam severed through the harness, one-entry manifest | `FAILED — 1 file(s), 1 mutation(s), 0 killed, 0 attributed, 1 survivor(s)` |
| post-seam, full manifest, same tree | `16 mutation(s), 16 killed, 16 attributed, 0 survivor(s)` |

Is the control equivalent apart from the seam? Yes — same `HARNESS_TREE`, same tree construction, same single severance text (`pages = corpus(root / …)` → `corpus(ROOT / …)`, which occurs once in both versions), only the two production lines differ. Could it have survived for an unrelated reason? It survives for exactly one reason, which I traced to the message: every `CannotRun` funnels into `main`'s single `return 2` (`:946-948`), the severed run hits the browser-run arm, and the D2 cases assert the integer. That is the stated cause, not a coincidence. The one correction is M1: the *dependency* that is missing is `playwright`, not Chromium.

**Claim 5 — the four entries and ten cases.**
- *Do all 20 expect-strings resolve?* Yes. 19 resolve by static equality against the 104 case names (`ast`, first argument of every `case`/`close`/`refuses` call; 104 calls, 0 non-constant, 0 duplicate names). The 20th, `"an unparseable colour REFUSES rather than guessing — returned instead of refusing"`, is a pre-existing entry resolving against the `refuses` helper's appended suffix (`:485`, `print(f"[FAIL] {name} — returned instead of refusing")`) over the case at `:500`. Attribution is exact equality on `parse_fail_names` output (`scripts/check-plan-code.py:2040-2062`, `unnamed = [(w, m) ... if len(m) != 1]` at `:2054-2055`), and this suite's `[FAIL]` format contains no `": got "`, so no name is truncated.
- *Killable for the wrong reason / collateral reds?* No. Each new entry produces exactly two reds, both named, zero collateral:

  | Entry | reds | named | collateral |
  |---|---|---|---|
  | 13 corpus from MODULE root | 2 | 2 | 0 |
  | 14 root no longer forwarded | 2 | 2 | 0 |
  | 15 success line loses its denominator | 2 | 2 | 0 |
  | 16 `if _missed:` → `if not _missed:` | 2 | 2 | 0 |

  (Note the harness's attribution rule is per-`expect` cardinality, not set equality, so it would have tolerated collateral; measured, there is none.)
- *Recorders or fixture constants?* Recorders. The got-side of `"main() measures exactly the pages of the world it was GIVEN"` is `sorted(q.name for q in pages)` taken from the list `corpus()` actually produced; two distinct worlds yield two distinct lists. Deleting the corpus call entirely (`pages = []`) reds both page-list cases, which a fixture-constant assertion could not do. `check-fixture-variation.py` → rc=0, *842 parameter(s) examined across 64 file(s)*, with this file's ratchet list untouched by the commit.
- *Can `root=None` be satisfied accidentally?* No. `seen` initialises both keys to `None`, so a `main()` that returns before reaching `measure_fn` fails the page-list case as well; the want side is a unique `TemporaryDirectory` `Path` that cannot compare equal to `None`; and the call site passes `root` by keyword, so there is no positional route that satisfies it by accident. Entry 14 is the falsifier and it reds exactly the two root cases.

**Claim 6 — the retargeted anchor.** Meaning preserved, not inverted: `population_notes` (`:211-235`) returns `[]` early when `vanished` is empty, so replacing `if not vanished:\n        return []` with `return []` silences the advisory **unconditionally** — which is what the renamed entry now says, and the old wording ("silenced") is the one that was imprecise. Unique: the two-line text occurs once (`"if not vanished:"` once; bare `"        return []"` twice, so uniqueness rests on the pair — the harness refuses ambiguous anchors and did not). Durable? **No more than its predecessor** — it is two short lines of an early-return idiom and any reflow orphans it. That is #245's class, which this commit files; I am not double-counting it as a finding. CI now agrees the retarget binds: `mutation-sweep (4)` is **pass** on `2025da34`, having been **failure** on `470f4ba5`.

**Claim 7 — counts.** Every one verified by running:

| Figure | Claimed | Measured |
|---|---|---|
| suite cases | 94 → 104 | `104/104 self-test cases passed`; pre-seam file `94/94` |
| docstring | `# 104 cases` | matches; `check-selftest-counts.py` rc=0 |
| manifest entries | 12 → 16 | `len(json)` = 16; diff shows 12 before |
| `EXPECTED_MUTATIONS[file]` | 12 → 16 | diff `scripts/check-plan-code.py:1440` |
| declared sum | 1407 → 1411 | `--self-test` 178/178 (asserts 1411); independent count 1411 |

Other sites: one stale (L3). Guards run, all rc=0: `check-docs`, `check-anchors`, `check-ratchet-contract`, `check-main-drivable`, `check-selftest-counts`, `check-fixture-variation`, `check-review-rounds`, `check-dashboard-entry`, `check-gate-falsifiability`, `check-group-claims`, `check-backlog-closure` (WARN-only, 3 stale rows, 0 orphans).

**Claim 8 — #245's narrative.** Verified against git and the CI logs, not taken on report.
- Anchor line across the branch's own ancestry: `de1b66eb` **1**, `a0a434b6` **1**, `c0200f60` **0**, `e489a5ea` **0**, `470f4ba5` **0**. "Present at `de1b66eb`, 0 occurrences from `c0200f60` onward" — accurate.
- `mutation-sweep (4)` on `470f4ba5` (job `112628405116`): `startedAt 04:16:48`, `completedAt 04:31:46` → **14m58s**. Exact.
- Its log, quoted: `✗ mutation 'the VANISHED advisory is silenced, so a baselined page absent from a run says nothing': anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless` / `NOT MEASURED — the mutation harness produced no coverage verdict (175 of 176 declared mutation(s) produced a verdict). Treat this as NOT CHECKED. — measured over shard 4 of 8 (round-robin)`. Exact.
- One understatement worth noting rather than filing: the row says *"176 entries bought no coverage verdict"*. True of that shard; the aggregator also failed, so the whole 1,407-entry sweep bought none.
- *Does the closure text overclaim the bound?* Yes — that is H1, and L4 for its distribution.

**D2 reclassification.** Taken from the guard's own function rather than asserted:

```
NEW: Verdict(path='<memory>', routes=frozenset({'param', 'argv'}), calls=6, has_main=True, error=None)
OLD: Verdict(path='<memory>', routes=frozenset({'param'}),          calls=2, has_main=True, error=None)
```

Matches "routes `{param}` → `{argv, param}`, call sites 2 → 6" exactly.

**CI state of the deliverable, stated because it is a fact about this commit.** `verify` is **red** on `2025da34`, and the dashboard entry discloses this honestly. The cause is `check-review-recorded.py`, quoted from the job log: `FAILED — 4 round(s) ran and guarded code was committed after every one of them. / The closest (unify-explainer-style-r4-codex.verdict.json) never saw: scripts/check-main-drivable.py, scripts/check-page-contrast.py, scripts/check-plan-code.py, scripts/mutations/check-page-contrast.json`. That is the gate asking for *this* round, not a defect in the five files; the contrast suite itself passes in CI at `104/104`. At the time of writing `mutation-sweep` shards 1, 2, 4, 6, 7 pass and 3, 5, 8 are still pending.

---

## ⚠ CODEX GAP

**REVIEW GAP:** codex — no frontier model is resolvable (both cached models are `visibility: "hide"`); Claude ran in its place per `docs/plugins.md`

**The Codex half of round 5 could not run.** `scripts/codex-frontier-model.py` exits 1 with:

```
error: no visible, API-supported model with a priority found in cache
```

The cache (`~/.codex/models_cache.json`, fetched 2026-10-06 19:42) holds exactly two models — `gpt-5.5` (priority 13) and `codex-auto-review` (priority 43) — and **both carry `visibility: "hide"`**, while the resolver requires `visibility == "list"`. The Codex CLI itself is installed (0.142.5), so this is a model-visibility condition, not a missing tool.

Per `docs/plugins.md`, a Codex-unavailable-for-any-reason condition falls back to a rigorous **Claude** adversarial review in its place, which this document is: written with an explicit refuting mandate, with every load-bearing claim re-measured rather than read. **The Codex-specific pass should be re-attempted before merge if access returns** — the gap is recorded here so it can be.

---

## What I could not check

- **The full `--mutate .` sweep** (1,411 entries). Out of bounds by the brief, and the three CI shards that would answer it (3, 5, 8) were still pending when I finished. My evidence is a pruned 16-entry run plus the four-world matrix; it says nothing about whether the other 1,395 entries still bind under this commit — though no manifest but this one names a changed file, and `check-plan-code.py --self-test` (178/178) covers the whole-manifest invariants.
- **Whether `measure()` succeeds in CI's non-staged `verify` checkout.** I measured three worlds — the real worktree (succeeds), a staged/pruned tree (fails at ESM resolution), and the repo's own self-test (never calls it). I did not run a browser on a GitHub runner, so "CI has no Chromium" rests on `grep -rn playwright .github/workflows/` returning nothing plus the `ci.yml:385-392` comment, not on an observed launch failure. M1 does not depend on that: it is established by the staged tree alone.
- **Anything requiring a write to git.** No `git add`, commit, push, or `check-merge-ready.py` run (it reads the committed diff and the PR). Its PR-only gates are unmeasured here.
- **The Codex half**, as above.
- **Whether `page-contrast-probe.mjs`'s own DOM walks (`sel`, `bgOf`, `hasImage`, the visibility filters) are correct.** Unchanged by this commit, and the file says in its own header that only a corpus run touches them. Out of scope, stated so it is not read as covered.

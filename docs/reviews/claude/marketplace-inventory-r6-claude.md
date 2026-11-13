# Round 6 — Claude half: the fold's root-file predicate still misses the class, and the figure the fold corrected in the spec is still wrong on both pages it ships

**Subject:** the r6 FOLD — uncommitted working tree plus `ae12bb3f..HEAD` — on
`marketplace-inventory` (PR #376). Reviewed in the worktree `wt-marketplace`.

**NOT CONVERGED: 1 High, 6 Medium, 2 Low.** No Blocking. Nothing was changed; no git write command
was run.

⛔ **AND MY VERDICT ON THE SECOND QUESTION DISAGREES WITH THE FOLD'S.** `root_level_cites()` meets
the architecture-review arming condition **as `dev-process.md` states it** — two consecutive rounds
whose findings came from the previous round's own fix, in one component — and the one test in
`review-method.md:199` answers **yes, a redesign removes it**. Section 2 argues this with the
definition quoted verbatim rather than paraphrased.

---

## HIGH

### H1 — The fold corrected "157" in the spec at three sites and left it at FOUR sites on the two pages the branch ships. The figure is wrong by 2 at the commit it ships in, and undated.

**Files/lines:**
`docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.html:515` and `:610`;
`docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html:438` and `:533`.

**The observation that makes it fail.** The fold rewrote the memory-corpus count in the spec at
`:258`, `:309` and `:1060`, replacing bare `157` with a producer and `159 at HEAD, 157 on master`.
Both pages still carry the pre-fold sentence verbatim — including, at `:610`/`:533`, the *exact*
clause the spec changed:

| site | text |
|---|---|
| spec `:309` (after the fold) | `the corpus (effort (1)'s memory files — count derived by the §3 producer, **159** at HEAD)` |
| page `:610`, fragment `:533` | `the corpus — effort (1)'s **157 memory files**` |
| page `:515`, fragment `:438` | `check-surface-recall.py, its hook, and **157 memory files**` |

```
$ git grep -c "157 memory files" HEAD -- docs/explainers/
HEAD:docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html:2
HEAD:docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.html:2

$ git ls-tree -r --name-only HEAD -- docs/memory | grep -c '\.md$'
159
```

**Four aggravating facts, each measured:**

1. **The pages are NEW ON THIS BRANCH** — `git ls-tree master -- docs/explainers/ | grep -c
   marketplace-inventory-walkthrough` → `0`. The stale figure is not inherited; it ships with
   PR #376.
2. **The pages were edited INSIDE the reviewed range, by the commit whose subject is this exact
   defect class.** `git log --oneline ae12bb3f..HEAD -- docs/explainers/` → `4d07ee59` ("The corpus
   pass (#295) found two live figures five review rounds never reached") and `d06da80c`. `4d07ee59`
   dated five figures on these two pages (`a4f6d4b5`, `262 → 248 files` with a named producer, the
   `11,642` re-measurement) **and walked past `157 memory files` twice in each file.**
3. **The spec's own rule, at `:124`, is that this form is forbidden:** *"a dated figure is the only
   form that stays true, which is this section's own rule"*. All four page occurrences are undated
   and carry no producer.
4. **No guard can see this, and the guard says so itself.** `check-claim-propagation.py` registers
   exactly two `DERIVED` keys — `spec-path` and `spec-lines` — and prints on every production run:
   *"this gate no longer checks prose at all … Whether the page's words agree with the spec's words
   is ADR-0015's subject and is **enforced by review, not here**"*. ADR-0015 accepted that with
   *"backlog #297's three live drifted claims are the measured price"*. **This round is the review
   that was supposed to be the mechanism, and it is the last one.**

**Why High and not Medium.** r5 CLAUDE H3 was the same shape — a live false figure on a
reader-facing page — and was rated High. This one is worse in one respect: the fold corrected the
same sentence 100 lines away in the spec on the same day, so the two sites now disagree inside one
deliverable.

**Fix.** Replace all four with the dated/producer form the spec now uses, or regenerate the pages
from the spec. ⚠ If the count is carried over, use **158**, not 159 — see M7.

---

## MEDIUM

### M2 — `root_level_cites()` v3 still lets the parent-roundtrip class through for any NESTED target. Reproduced: clean predicate, clean live `audit()`, RED staged control — the exact failure the function exists to prevent.

**File/lines:** `scripts/check-canonical-source.py:306–322`.

The fold's fixture pins `"../" + ROOT.name + "/CONTEXT.md"` — the **root-level** instance r6 CODEX
named. A parent roundtrip to a **nested** file resolves back under the root, so `landed.parent !=
base` and `base in landed.parents`, and the entry is returned clean. Three distinct spellings
escape:

```
'../wt-marketplace/docs/plugins.md'                        predicate=clean  consumer_is_file=True
'docs/../../wt-marketplace/docs/plugins.md'                predicate=clean  consumer_is_file=True
'../../scratchpad/wt-marketplace/docs/plugins.md'          predicate=clean  consumer_is_file=True
```

**The full consumer round-trip, run with production `stage_tree()` and a real `CANONS` entry
rewritten to that spelling:**

```
original cite : .agents/skills/handoff/SKILL.md
rewritten to  : ../wt-marketplace/.agents/skills/handoff/SKILL.md
predicate on the rewritten table : []
LIVE audit() with it             : [] (clean)
stage_tree problems: none
STAGED audit() hits for this cite: ['../wt-marketplace/.agents/skills/handoff/SKILL.md is declared
                                     a citing site but does not exist']
STAGED audit() total problems    : 1
```

That is the docstring's own stated harm, verbatim — *"reddens this guard's own CONTROL inside the
staged tree and turns every mutation shard into NOT MEASURED. Measured live in CI 2026-10-17: 6 of
8"* — surviving the fix written to prevent it.

**Why the two arms cannot catch it.** Arm 2 (`landed.parent == base`) fires only when the target
sits directly in the root; arm 1 (`landed != base and base not in landed.parents`) fires only when
resolution ends outside. A parent roundtrip to a nested file satisfies neither, because
`resolve()` has already erased the `..` that makes the string nonportable. **The property the
predicate needs is lexical (is this registration portable?), and v3 measures a post-resolution
filesystem fact instead.** r6 CODEX asked for both halves — *"Classify paths against the consumer's
root **and reject nonportable registrations**"* — and the fold implemented the first.

**Bound on the blast radius, stated rather than left to inference.** `root_level_cites` has only
self-test callers (`:593` live table, `:624` fixture — `grep -rn root_level_cites`), so a bad
registration passes `--self-test` and surfaces as a red *control* during `--mutate .`, i.e. as
NOT MEASURED rather than as a named failure. No live entry uses such a spelling today
(`root_level_cites(CANONS)` → `[]`), so nothing is broken right now; this is a latent trap in the
guard whose job is to refuse exactly that trap.

### M3 — The converse direction: the predicate REFUSES `node_modules/typescript/…`, a path `HARNESS_TREE` stages, because `resolve()` follows a symlink. The verdict is environment-dependent.

**File/lines:** `scripts/check-canonical-source.py:314` (`landed = (base / c).resolve()`) and `:318`.

Sweeping one real file under each `HARNESS_TREE` directory:

```
  ok       scripts/__pycache__/check-canonical-source.cpython-314.pyc
  ok       supabase/.gitignore
  ok       docs/ADR.md
  REFUSED  node_modules/typescript/LICENSE.txt
  ok       .claude/hooks/block-default-branch-push.sh
  ok       .github/workflows/ci.yml
  ok       .agents/skills/brief/SKILL.md
```

Cause, measured:

```
$ ls -ld node_modules
lrwxr-xr-x  node_modules -> /Users/kujinlee/code/.../youtube-playlist-summaries-cloud/node_modules
$ python3 -c "...(b/'node_modules/typescript/LICENSE.txt').resolve()..."
-> /Users/kujinlee/code/.../node_modules/typescript/LICENSE.txt   under_root=False
```

`node_modules/typescript` is `HARNESS_TREE[3]`, and `stage_tree` copies it with
`shutil.copytree(src, dst, ignore=…)` — default `symlinks=False`, so the symlink is **followed and
the contents copied**. The path is therefore perfectly stageable and the predicate refuses it.

**Why this is worse than a dormant false positive: the same table gets different verdicts on
different machines.** Here `node_modules` is a worktree convenience symlink; in CI `ci.yml:123` and
`:774` run `npm ci`, which produces a real directory, so the identical registration would pass.
A predicate called on the live `CANONS` on every run is not a pure function of the registration —
`measure-the-population-the-code-actually-sees`. Nothing in the live table triggers it today, which
is why `--self-test` is 29/29 here.

### M4 — The arithmetic trail does not close. The shown derivation says 1476; the assertion says 1478. Two folds each added a trail line and neither re-derived the sum.

**File/lines:** `scripts/check-plan-code.py:5187`, `:5197–5201`, `:5203`.

The block's stated purpose is *"a sum whose derivation is not shown is the same defect"*. The
derivation is shown, and it is now wrong by 2:

```
:5198   # Net 1489 - 17 + 1 + 3 + 1 = 1477 ... which is NOT 1476, so one of those is wrong and
:5201   # trail from 1489 is -17 + 3 + 1 = 1476.
:5203   case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 1478)
```

The itemised trail lists **seven** steps; the summing expression accounts for **four**. The correct
derivation over all seven is `1489 − 17 + 3 + 1 + 1 + 1 = 1478`.

**Attributed by execution, not by reading:**

```
$ for r in ae12bb3f 4d07ee59; do git show $r:scripts/check-plan-code.py | grep -o '...values()), [0-9]*'; done
ae12bb3f: ... 1476      # trail concluded 1476 — IT CLOSED
4d07ee59: ... 1477      # r5 CLAUDE added the "7 -> 8" line, left the expression  -> off by 1
worktree: ... 1478      # r6 fold added the "8 -> 9" line, left the expression    -> off by 2
```

Two further wrong numbers in the same block: the header at `:5187` still reads *"1489 -> 1472, then
-> **1476** after round 5"*, and `:5198`'s *"which is NOT 1476"* now compares against a figure that
is no longer the assertion — the whole paragraph is a frozen snapshot of the `ae12bb3f` state.

⚠ **The executable side is entirely correct and I verified it**: declared sum 1478 equals the sum of
actual on-disk manifest lengths (1478), with **zero** per-file mismatches across all 60 manifests.
Only the audit trail is wrong — which is precisely r6 CODEX's Low, one clause to the left, fixed in
the clause the reviewer pointed at and not in the clause that does the arithmetic.

### M5 — The "three extensions" sentence was corrected in `ci.yml` and left standing in `check-canonical-source.py`'s own docstring — the guard against second copies is now the drifted second copy.

**File/lines:** `scripts/check-canonical-source.py:25–26` (vs the fold's `.github/workflows/ci.yml:335`).

```
$ grep -rn "three extensions\|FOUR extensions" --include=*.py --include=*.yml . | grep -v node_modules
docs/reviews/architecture-review-2026-10-14-canonical-source.md:72:  and three extensions.
docs/reviews/claude/plugins-handoff-citations-r6-claude.md:172:### H4 — ... three extensions. ...
.github/workflows/ci.yml:335:      # SYMBOL (oracle: a token substring over four directories and FOUR extensions — `*.md`,

$ sed -n '24,26p' scripts/check-canonical-source.py
  * this one forbids a SYMBOL, so its oracle is a token substring over four directories and three
    extensions.

$ python3 -c "...; print(m.SEARCHED)"
('*.md', '*.py', '*.sh', '*.html')
```

Four, not three. The two review documents are dated records that were true when written
(`architecture-review-2026-10-14` predates ADR-0015's widening) and need no change — I checked that
before listing them, so this is one live site, not three. The live site is the docstring of the file
whose opening line is *"A mechanism described in more than one place drifts. This refuses the second
copy."* The coordinator doc records this fold as *"Same class as M1 last round: the rename was
corrected, the paragraph around it was not"* — and the fold reproduced it one file over.

### M6 — `ci.yml:330` names the wrong guard, which r6 CODEX reported and the fold neither folded nor recorded as deferred.

**File/lines:** `.github/workflows/ci.yml:330–335`.

`:330` reads *"⛔ NOT a generalisation of **the step above**"* and the contrast it then draws is
entirely with `check-explainer-delivery.py` — *"a fenced code block, scoped to
`.agents/skills/*/SKILL.md`"*, *"enumeration completeness over its `PAGE_SKILLS`"*. Measured
ownership:

```
$ grep -c PAGE_SKILLS scripts/check-claim-propagation.py   -> 0
$ grep -c PAGE_SKILLS scripts/check-explainer-delivery.py  -> 6
$ grep -n "explainer-delivery\|claim-propagation\|canonical-source" .github/workflows/ci.yml
299:  run: python3 scripts/check-explainer-delivery.py
325:  run: python3 scripts/check-claim-propagation.py
328:  run: python3 scripts/check-claim-propagation.py --self-test
344:  run: python3 scripts/check-canonical-source.py
```

"The step above" resolves to `claim-propagation` at `:325`/`:328`. The guard being contrasted is
four steps up at `:299`. The canon file states the referent correctly and by name
(`check-canonical-source.py:21`: *"IT DOES NOT GENERALISE `check-explainer-delivery.py`"*), so this
is the positional half of a two-site claim pointing somewhere else — `a-positional-read-needs-a-
verified-shape`.

⭐ **The part that matters for the record:** r6 CODEX reported this — *"Older comments at
`.github/workflows/ci.yml:330–335` still misidentify the preceding guard and say three searched
extensions instead of four"* — one sentence, two clauses. The fold took the second clause and
dropped the first, and the coordinator's "Also folded — found by the reviewer outside its two
findings" section reads as if that paragraph was swept.

### M7 — The §3 producer counts `MEMORY.md`, so the spec's 159 disagrees by one with the component's OWN producer; and "ALREADY PUBLISHED" omits that `memory_dir()` cannot reach the tracked corpus from a clone.

**File/lines:** `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md:258`, `:309`,
`:1060`; against `scripts/recall-llm.py:417–426` and `:429–431`.

⭐ **First, every clause the mandate asked me to treat as potentially Blocking is TRUE.** I tried to
refute each and could not:

```
$ git ls-tree -r --name-only HEAD   -- docs/memory | grep -c '\.md$'   -> 159   ✓ "159 at HEAD"
$ git ls-tree -r --name-only master -- docs/memory | grep -c '\.md$'   -> 157   ✓ "157 on master"
$ git ls-tree -r --name-only HEAD   -- docs/memory | grep -vc '\.md$'  -> 0     (no non-.md noise)
$ gh repo view --json visibility,isPrivate   -> {"isPrivate":false,"visibility":"PUBLIC"}   ✓ PUBLIC
$ gh api .../contents/docs/memory?ref=master --jq length  -> 157        ✓ reachable on the remote default branch
$ curl -o /dev/null -w "%{http_code}" .../raw/master/docs/memory/MEMORY.md  -> 200          ✓ served publicly
```

And the `docs/memory/`-is-the-corpus clause survives the hardest attack available — `recall-llm.py`
builds a path *outside* the repo, so I expected the fold to have replaced a true cell with a false
one. It has not:

```
$ ls -ld /Users/kujinlee/.claude/projects/-Users-...-cloud/memory
lrwxr-xr-x ... memory -> /Users/kujinlee/code/.../youtube-playlist-summaries-cloud/docs/memory
harness dir .md: 159      docs/memory .md: 159
```

**The row is right. Two defects remain in it.**

**(a) The named producer is not the component's producer, and they differ by one.**

```
$ python3 -c "...; print(len(rl.memory_files(Path('docs/memory').resolve())))"
158
```

`scripts/recall-llm.py:429-431` — *"`MEMORY.md` is the INDEX, not an entry, and is excluded"*. The
spec's §3 cell counts it, so the figure a reader takes as "the corpus" is **159** while the number
of entries effort (1) actually reads is **158**. The row exists to name *the* producer; it names a
`git ls-tree` pipeline that no component runs.

**(b) `memory_dir()` returns `None` for anything but the one checkout with the hand-made symlink.**

```
  cwd=.../scratchpad/wt-marketplace                             -> None
  cwd=/Users/kujinlee/code/.../youtube-playlist-summaries-cloud -> /Users/.../memory
  cwd=/tmp/a-fresh-clone                                        -> None
```

The symlink is a local filesystem fact created 2026-09-30; it is not in the repo. So "TRACKED …
ALREADY PUBLISHED" is true about the bytes and silent about the fact that a clone cannot read them —
which `docs/backlog.md:222` (#194) already records as an open obstacle (*"any in-repo home needs a
symlink or a bootstrap step"*). The cell is the one a human reads to grade C1/C2 and decide C5, and
it now reads as though the corpus ships.

⚠ **And the claim the fold retired survives at three further live sites**, which is H1's class
again: `scripts/recall-llm.py:420` (*"The corpus lives OUTSIDE the repository"* — plus *"a worktree
or a clone at another path still finds its own corpus"*, refuted by the `None` above),
`docs/explainers/2026-09-27-topic-memory-recall-taxonomy.html:665,667` and its `.fragment.html:588,590`.
These are on `master` and not touched by this branch, so they are **not** fix-induced — but the
fold's correction is what put the spec in disagreement with them.

---

## LOW

### L8 — The coordinator's per-file `+N` figures are diffstat changed-line totals, not insertions; they sum to 140, not to its own headline 123.

**File:** `docs/reviews/coordinator/marketplace-inventory-r6-coordinator.md`, the scoping table.

```
$ for f in <the six>; do git diff --numstat ae12bb3f..HEAD -- "$f" | cut -f1; done
  +43 check-canonical-source.py   (table: +45)
  +34 check-claim-propagation.py  (table: +42)
  +13 mutations/check-canonical-source.json   (table: +13)
   +4 mutations/check-claim-propagation.json  (table:  +6)
  +14 check-plan-code.py          (table: +16)
  +15 ci.yml                      (table: +18)
  ---
  123 insertions                  table sum: 140
```

The headline "123 lines of guard code" is correct (it is `git diff --stat`'s insertion total). The
per-file numbers were read off the bar-chart column, which is insertions **+** deletions
(123 + 17 = 140). Under a column headed *"unreviewed lines"* with a `+` sign, five of six are
inflated. Scoping arithmetic in the record, not a rule — hence Low.

### L9 — The clause the fold corrected still says "four directories" where the population is four directories PLUS the repo root, which the same guard's comments count as the fifth.

**File/lines:** `.github/workflows/ci.yml:335` vs `scripts/check-canonical-source.py:269` and `:390–395`.

```
$ sed -n '389,396p' scripts/check-canonical-source.py
    for pat in ROOT_GLOBS:                     # ('*.md',)  — top level only
        out += sorted(root.glob(pat))
    for sub in (".agents", ".claude", "docs", "scripts"):
        for pat in SEARCHED:                   # ('*.md','*.py','*.sh','*.html')
            out += sorted(d.rglob(pat))
```

The oracle is `root × {md}` ∪ `4 dirs × {md,py,sh,html}`. `check-canonical-source.py:269` says *"any
directory outside the **five** below"*, and `:256` calls omitting the root *"the WORST MISS (r6
CLAUDE H4)"*. The corrected `ci.yml` clause says four directories and four extensions, which is
right about the extensions and drops the root and the asymmetry — the third correction to one
sentence that still does not match its subject.

---

## 1. Is this CONVERGED?

**No.** One High, six Medium, two Low. H1 and M2 are the two I would not ship: H1 is a live wrong
figure on a page that is new on this branch, and M2 is the guard failing at the job its own
docstring describes.

### What I EXECUTED rather than read

| | Executed | Result |
|---|---|---|
| **A** | `root_level_cites` probed over 18 spellings (parent roundtrip root/nested/double, absolute root/nested, `''`, `.`, `~`, trailing `/`, `.//`, NUL, newline, case-collision root/nested, `node_modules`); full consumer round-trip through production `stage_tree()` + `audit()` on live and staged trees; symlink census of the repo; non-strict `resolve()` over missing parents and missing root files | **M2, M3** |
| **B** | All **9** manifest entries applied one at a time to a staged copy under a redirected `$HOME`, green control first (`29/29`), each checked against the case it names; both arms' witnesses isolated by set difference | **clean — the fold's claim reproduces** |
| **C** | Six independent verifications of the §3 row (ls-tree at HEAD/master/origin-master, non-`.md` residue, `gh repo view`, `gh api contents`, `curl` on raw), the harness-path symlink, `memory_files()`, `memory_dir()` from three cwds, plus a grep sweep for every surviving `157`/"outside this repo" | **H1, M7 — every clause the mandate flagged as Blocking-if-wrong is TRUE** |
| **D** | `SEARCHED` and `ROOT_GLOBS` read out of the loaded module; the walk read; `PAGE_SKILLS` ownership counted in both guards; ci.yml step order enumerated | **M5, M6, L9** |
| **E** | Coordinator's numbers re-derived (`--numstat` per file, `HARNESS_TREE` length, filed-capture byte count); full `ae12bb3f..HEAD` file list; page-edit commits attributed; page provenance stamps compared per commit; eight production document guards run | **L8** |
| **F** | Declared sum vs sum of on-disk manifest lengths across all 60 manifests; the asserted constant at `ae12bb3f`, `4d07ee59` and the worktree; canonical manifest length at each | **M4** |

**Verified clean, and worth as much as the findings:**

- **B is genuinely clean.** 9 entries / `EXPECTED_MUTATIONS` 9 / declared sum 1478 / on-disk sum
  1478 / 0 per-file mismatches. All nine mutations die by the case they name. The two arms have
  **disjoint witnesses** — disabling the absolute arm loses only `<ROOT>/docs/plugins.md`, disabling
  the escapes arm loses only `../elsewhere/outside.md`, neither mutation spuriously catches anything.
  The coordinator's `exercise-the-producer-at-two-distinct-inputs` repair is correct, and I
  reproduced it rather than taking it.
- `check-docs`, `check-canonical-source`, `check-claim-propagation`, `check-plan-file-tags`,
  `check-anchors`, `check-selftest-counts` (54 declared counts, each verified by running it),
  `check-explainer-delivery`: **all rc=0**. Self-tests 29/29, 178/178, 58/58.
- `check-review-rounds.py` is rc=1 solely on *"marketplace-inventory round 6: only codex — claude
  neither ran nor recorded a `REVIEW GAP:` line"*. **This file is that half**; it goes green when
  this lands. Not a finding.
- The page provenance stamps are honest, which I checked before filing a finding I expected to find:
  each `chrome-when` names the commit the page was generated *from* plus "uncommitted changes", then
  ships one commit later. Correct, not stale.
- `''`, `.`, `~/x.md` and newline-bearing spellings pass the predicate but fail `audit()` **in both
  worlds**, so they cannot produce the silent staged-only asymmetry M2 is about. Not filed.

---

## 2. Thrashing or prose floor?

**`docs/review-method.md:522–526`, quoted verbatim:**

> | Shape | Tell | What it means | Do |
> |---|---|---|---|
> | **Thrashing** | findings are **introduced by the previous round's own fix**; severity stays put | the design is fighting itself — a real architecture problem | **the architecture review.** This is the shape the trigger was bought for, and since 2026-09-14 it is the ARMING CONDITION itself |
> | **Prose floor** | findings shift from *"this cannot work"* to *"this is under-specified"*; each round is right and the artifact keeps improving | the review has reached the limit of what can be settled **without an executable subject** | **Stop reviewing prose. Write the code or the plan, and review THAT** |

**And the one test, `docs/review-method.md:199–203`, verbatim:**

> ### Can a redesign remove it?
>
> If a different shape would dissolve the finding, it is a mechanism defect and the redesign is owed.
> If the same finding would survive every reasonable reshaping — because it lives in code the design
> merely *governs*, or because it is a sentence that outlived the decision it described — it is not.

### Per finding

| # | Fix-induced? | By which fix |
|---|---|---|
| **H1** | **No** — pre-existing on the pages. ⚠ But the r6 fold *created the disagreement* by correcting the spec half only, and `4d07ee59` is the in-range commit that edited these pages for this class and missed it | — |
| **M2** | **YES** | the r6 fold's own `root_level_cites` v3 (uncommitted) |
| **M3** | **YES** | the r6 fold — `resolve()` is what v3 introduced; v1/v2 were string tests and could not false-fire this way |
| **M4** | **YES**, and twice over | `4d07ee59` (r5 CLAUDE, off by 1) then the r6 fold (off by 2) |
| **M5** | **YES** | the r6 fold corrected the `ci.yml` copy and not the docstring copy |
| **M6** | **No** (the comment predates the range) — but the fold **received this finding from r6 CODEX and dropped half of it** |
| **M7** | **No** — `recall-llm.py` is on `master`. The fold put the spec into disagreement with it |
| **L8** | **No** — written with the coordinator doc |
| **L9** | **YES** | the r6 fold's correction of that clause |

### ⛔ My verdict: THRASHING in one component, and the fold's reasoning for the opposite conclusion has a gap

The coordinator concluded *"severity **fell** (2 High → 0 High), and `review-method.md:525` requires
'severity stays put' for thrashing"*, and r6 CODEX agreed with *"Severity has fallen, so this pass
alone does not establish the full 'severity stays put' pattern"*. **Both reasoned over the ROUND.
`dev-process.md`'s arming condition is per-component:**

> two consecutive rounds whose findings came from the previous round's own fix, **in one component**

Taking `root_level_cites()` as the component — one function, rewritten three times in two days:

| round | finding | severity | caused by |
|---|---|---|---|
| r5 CLAUDE | H2 — `"/" not in c` pins a spelling | High | v1 |
| r6 CODEX | Medium — `normpath` cannot remove a leading `..` | Medium | **v2, the r5 fix** |
| r6 CLAUDE | **M2** — resolution erases the `..`, so the nested class escapes | Medium | **v3, the r6 fix** |

Fix-induced in two consecutive rounds, in one component, **and severity stays put across those
two** (Medium → Medium). Both clauses of the tell are satisfied. M3 is a *fourth* defect from the
same fix, in the opposite direction.

**And the test at `:199` answers yes.** A different shape dissolves M2 *and* M3 together: refuse a
registration that is not a **relative path with no `..` component** and does not sit under one of
`HARNESS_TREE`'s staged prefixes. That is a lexical predicate over the declared string, so (a) a
parent roundtrip is refused at any depth, and (b) `node_modules/typescript/LICENSE.txt` passes on a
prefix test and never touches the filesystem, which removes the symlink dependence and the
machine-to-machine disagreement. Each of v1, v2 and v3 answered the instance a reviewer named;
a fourth arm would be the fourth instance of that, which is what `review-method.md` calls the design
fighting itself.

**It is not a prose floor.** The subject executes — I ran every claim in this section — and the
findings are not *"this is under-specified"*; M2 is *"this does not do what its docstring says"*,
reproduced end to end through the real consumer.

⚠ **What I am NOT claiming.** M4, M5, M6, L9 **are** branch-coverage and stale-cross-reference, as
the fold said — comments and sentences, dissolved by no reshaping. The architecture-review case
rests on `root_level_cites` alone. And this is a judgement the owner's pre-commitment may simply
overrule: the pre-commitment binds the number of review rounds, not what the fold does with a
finding. My recommendation is narrow — **fold M2/M3 as the lexical redesign rather than as a third
arm**, because the arm-at-a-time pattern is what three rounds have now cost, and if that is not
done, name `root_level_cites` explicitly in the `NO-REVIEW:` line.

---

## 3. ⭐ Given this is the last pass: what ships unreviewed

Written so the `NO-REVIEW:` line can say this rather than imply completeness.

**What I examined:** the uncommitted fold in all five files; `root_level_cites` to destruction;
all nine canonical mutations; the `EXPECTED_MUTATIONS` arithmetic and all 60 manifests' lengths;
the three spec cells the fold changed and every surviving `157`/"outside this repo" in `docs/` and
the two pages; the `ci.yml` comment block; the coordinator doc's numeric claims; eight production
document guards.

**What NO review half has examined — name these:**

1. ⭐ **`scripts/check-claim-propagation.py`'s +34 lines and the `_VOID_EXPECTED` mechanism.** It is
   half the r6 scope. r6 CODEX executed it hard (14 members independently, the 57/57→56/56
   unsoundness reproduction, every expectation red) and I deliberately did **not** re-run that
   ground, because the mandate sent me at the fold and re-deriving a verified result is not where
   the remaining risk was. **So that file has exactly ONE reviewer, and the branch's own record is
   that the two halves produce zero overlapping findings.** This is the largest single thing shipping
   on one pass.
2. **Everything in `ae12bb3f..HEAD` outside the six scoped files, 749 of 872 insertions** —
   `docs/dashboard-entries.md` (+53), `docs/roadmap-to-launch.md` (+19), `docs/backlog.md`,
   `docs/adr/0015-*.md` (+14), `docs/memory/` (two new entries, +59 and the `MEMORY.md` row), and the
   two r5 review documents (+587). Records rather than rules, per the pre-commitment — but the
   **page edits at `4d07ee59`/`d06da80c` are in this excluded set and are NOT records**, and H1 is
   what was sitting in them. ⛔ **The coordinator's stated justification — *"the substantive document
   changes were examined by the r5 Claude half at `ae12bb3f`"* — does not hold for these two pages:
   they were changed at `d06da80c` and `4d07ee59`, both after `ae12bb3f`.** Nobody has reviewed those
   edits. I swept them for the corpus figure and found H1; I did **not** verify the other five
   figures `4d07ee59` dated (`a4f6d4b5` line counts, `248 files`, `11,642`, `665`).
3. **`scripts/recall-llm.py`, `check-surface-recall.py`, `surface-recall.sh` — effort (1) itself.**
   I read only `memory_dir`/`memory_files`. M7(b) means the component as inventoried **cannot read
   its corpus from a clone**; I verified that one path and graded nothing else. The spec's C1–C3
   grades for effort (1) rest on no review.
4. **The spec outside the three cells the fold touched** — ~1,060 lines, including every other
   component row, every other criterion grade, and the `11,624`/`11,642`/`665`/`248` figures. r5
   CLAUDE swept it at `ae12bb3f`; nothing since.
5. **The remaining ADR-0015 bound, unguarded by design and now unreviewed too.** Both guards state
   it: agreement between a canon and its citing sites *"is enforced by review and by nothing else"*,
   and `check-canonical-source.py:62` adds that the guard *"cannot detect a restatement that cites
   the canon and CONTRADICTS it"* (backlog #289). H1 is an instance of exactly that, found by
   sweeping. **After this round no mechanism covers that class on this branch.**
6. **Not run by me:** `check-plan-code.py --mutate .` (full, unscoped), `npm test`, `tsc --noEmit`,
   the integration/e2e suites, the schema gates, and `check-merge-ready.py`. The last of these is
   the one that reads the committed diff and the PR-only gates — ⚠ **it has not been run against
   this fold at all, and the repo's own record is that skipping it put two PRs red.**
7. **Unverified historical figures I quoted from the fold rather than measured:** *"Measured live in
   CI 2026-10-17: 6 of 8"* (`check-canonical-source.py:283`), the *"34 non-exempt sites"* in
   `explainer-serve.py`, and r6 CODEX's scoped `26 mutations / 26 killed`.

**One sentence for the PR body, if it helps:** *`NO-REVIEW:` covers
`scripts/check-claim-propagation.py`'s `_VOID_EXPECTED` work (one reviewer only),
`scripts/recall-llm.py` and the rest of effort (1), the non-code half of `ae12bb3f..HEAD` —
including the two explainer-page edits at `d06da80c`/`4d07ee59`, which no half examined — and the
ADR-0015 canon-vs-citing-site agreement class, which no guard covers.*

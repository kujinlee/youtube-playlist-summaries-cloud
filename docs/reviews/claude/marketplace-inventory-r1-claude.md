# Marketplace inventory spec — round 1, CLAUDE half

**Verdict: NOT CONVERGED** — 3 Blocking, 6 High, 6 Medium, 2 Low.

Subject: `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md` (213 lines) and
`docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.{html,fragment.html}`, plus the
`docs/anchors.md`, `docs/features.md`, `docs/backlog.md` edits, on `marketplace-inventory` at
**`a3fbb197`**. Measured in a worktree at that commit.

Every number below was re-derived by command. Commands and raw output are quoted. Anything I did not
run is marked **NOT VERIFIED** with the reason, in the final section.

---

## Blocking

### B1 — Effort (1)'s component list omits the only recall component that passes C1, and it is on `master`

**The claim.** §3, Effort (1): *"`scripts/check-surface-recall.py` + `.claude/hooks/surface-recall.sh`,
**157** memory files, and two unmerged branches: `c5-recall-matcher` (6 commits) and
`backlog-117-parser-substrate` (10)."* Immediately below, the same section says: *"⭐ The measured
result that must drive this effort's verdict, because it inverted … Whatever ships here, it cannot be
the lexical matcher."*

**The failing case.** The component list contains only the lexical matcher and its hook. The
mechanism that replaced it is absent from the spec entirely:

```
$ grep -in 'recall-llm\|semantic' docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md
(no output)
$ grep -ic 'recall-llm' docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html
0
$ wc -l scripts/recall-llm.py scripts/check-surface-recall.py .claude/hooks/surface-recall.sh
    2550 scripts/recall-llm.py
     820 scripts/check-surface-recall.py
     113 .claude/hooks/surface-recall.sh
$ git ls-tree master --name-only scripts/ | grep -i recall
scripts/check-surface-recall.py
scripts/recall-llm.py
```

`scripts/recall-llm.py` is **2,550 lines, on `master`** — not on an unmerged branch — and it is the
mechanism the §3 result endorses. Its callers and manifest are also on `master`
(`grep -rln recall-llm .claude/ scripts/` → `.claude/hooks/surface-recall.sh`, `check-plan-code.py`,
`check-rc-contract.py`, `bootstrap-memory.sh`, `check-fixture-variation.py`, `check-memory-link.py`,
`check-selftest-counts.py`, `check-surface-recall.py`, `scripts/mutations/recall-llm.json`).

So the inventory, run against §3's scope as written, scores the mechanism that scored 3/20 and never
sees the one that scored 20/20. §3's own instruction ("it cannot be the lexical matcher") is
unexecutable against §3's own component list — the thing it says to ship is not in scope.

I initially assumed this file was on the unmerged `semantic-recall-replication` branch, as the
memory record states. That branch no longer exists (`git rev-parse` → unknown revision); the work
folded into `master`. The omission is therefore of landed code, not of a parked branch.

**Direction.** Add `scripts/recall-llm.py` + `scripts/mutations/recall-llm.json` to effort (1)'s
components, and state which of the three recall mechanisms the verdict is *about*. Re-derive the
addend (see M1).

### B2 — §6's pass condition is satisfiable by a degenerate success, which makes §5's falsifier unreachable for the one component the spec calls the main killer

**The claim.** §6: *"Pass condition, stated so it can fail: a page is **produced and served**, and the
reader can ask a question inside it, from that repository."* And §5: *"any blocker the install
experiment hits on a component the scan scored clean is a **scanner defect**."*

**The failing case, constructed.** In the throwaway repo (§6: *"no `scripts/check-*`"*), run `brief`.
Its step 1 is the ground-truth block at `.agents/skills/brief/SKILL.md:40-62`. Every item in it
resolves to nothing in a stranger's repo. The skill explicitly licenses that outcome:

```
$ sed -n '42p;168,170p' .agents/skills/brief/SKILL.md
Run these; do not skip any. Report the ones that returned nothing.
- **The ground-truth command list is hardcoded** and will drift as the repo changes. Per
  `hardcode-only-what-fails-loudly`: a missing file fails loudly, a *renamed* one fails silently by
  returning nothing. Report empty results rather than skipping them.
```

Page production does not depend on step 1 — it runs through `brief-compose.py` and
`explainer-serve.py`. So the sequence is: all nine ground-truth items return nothing, the skill says
to report that rather than stop, a page is composed, the server starts, Ask works. **§6's pass
condition is MET.** The page has no roadmap layer, no backlog, no ratchet exit codes and no git
reasoning — i.e. `brief`'s entire content — and the verdict recorded is `SHIP`.

The experiment hit no *blocker*; it hit a hollow page. §5's falsifier is keyed on "any blocker the
experiment hits", so it does not fire, the scan is never declared defective, and C4 is recorded as
satisfied for the component §4 names as the expected main killer.

**Direction.** The pass condition has to assert content, not mechanism — e.g. *the page's
ground-truth footer carries a non-empty result for every item in step 1, or the run is a failure* —
and §5's falsifier has to cover "produced a degraded result", not only "blocked".

### B3 — §5 requires a per-component declared shipping set; nothing in §7 produces one, and I have a measured case of a set that resolves WRONG rather than CANNOT RUN

**The claim.** §5: *"**cross-repo dependencies** — invocations of files outside **the component's
declared shipping set**"* and *"⛔ **It must report CANNOT RUN rather than a clean score when it cannot
resolve a component's shipping set.** A zero over a set it failed to build is this repository's single
most-measured failure."*

**The failing case, part 1 — the artifact does not exist.** §7's nine deliverables contain no
artifact that declares, per component, what its shipping set is. §10 does not exclude one either. So
at build time the scan has two options: report CANNOT RUN for all 24 components, which empties
deliverable 4 (*"The inventory — every component … with `SHIP` / `NEEDS-WORK` / `DON'T-SHIP`"*), or
infer the set — which is the condition §5 warns about, with no gate on the inference.

**The failing case, part 2 — measured: the set resolves, and is wrong.** §3 names the component path
as `.claude/skills/shared/`. That path is real, readable and non-empty, so nothing triggers CANNOT
RUN. But its entries are symlinks:

```
$ git ls-files -s .claude/skills | head -3
120000 8eed2db9ee4ec96e1a14c24a1b564e2a72c1fc6d 0	.claude/skills/brief
120000 9016aac96778797f95e5b797649514b98d05dec4 0	.claude/skills/caveman
120000 a1733a24bcd7ecaf810b89961e7dfdba30bdf27a 0	.claude/skills/dashboard
$ ls -l .claude/skills/brief
lrwxr-xr-x  brief -> ../../.agents/skills/brief
```

With a known positive confirmed first (the real path matches), a directory walk over the path §3
names finds **nothing**:

```
$ grep -rc 'check-' .agents/skills/brief/SKILL.md     # KNOWN POSITIVE
.agents/skills/brief/SKILL.md:4
$ grep -rl 'check-' .claude/skills/ | wc -l
0
$ grep -rl 'check-' .agents/skills/ | wc -l
6
```

Mode `120000` is a symlink, and `grep -r` does not follow symlinks met during a walk (it does follow
one named explicitly, which is why the per-file probe above succeeds). So a scan built from §3's own
component paths reports **zero project-specific references and zero cross-repo dependencies** over a
component set it silently truncated to empty — a clean score, not CANNOT RUN. This is the exact
failure shape §5 cites as the repository's most-measured, reproduced against the spec's own stated
paths before the scan is written.

**Direction.** §7 needs a tenth deliverable: the shipping-set declaration, per component, as data the
scan reads. And §5's CANNOT-RUN rule needs a companion: the scan must assert a **non-zero expected
file count** per component and fail when the resolved set is empty or smaller than declared —
a zero over a resolvable-but-empty set is indistinguishable from a clean component.

---

## High

### H1 — The spec's headline corrective finding is a cross-corpus comparison; the figure it attacks was accurate when written

**The claim.** §3: *"⛔ **A FINDING BEFORE THE WORK STARTS: the D2 index undercounts its own subject by
roughly 3×.** `docs/portable-practices.md` describes the suite as *"9 files / 3,599 lines"*. The Python
machinery alone is **10,373 lines across six files**, before 604 lines of skills. That figure has been
quoted as settled since 2026-09-07."* The page renders this as its only chart: `index claims 3,599`
against `measured 10,977`.

**What I checked.** `10,373` reproduces exactly over the six files §3 names. But `3,599` was never a
count of those six files. `portable-practices.md:13-16` enumerates its nine: four skills, the shared
delivery contract, `brief-compose.py`, `explainer-serve.py`, `page_chrome.py`, `page_markup.py`.
`gen-dashboard.py` (3,546) and `gen-goals-page.py` (1,252) — **4,798 lines, 46% of the 10,373** — are
not in it. Measured at the commit that introduced the figure:

```
$ git log --format=%H -S '3,599' --all -- docs/portable-practices.md | tail -1
100cf498e0d62a7dc4ef8d7f5f29a8543e7e6079
$ git log -1 --format='%ad %s' 100cf498
Mon Sep 7 17:00:30 2026 -0700  The comprehensibility suite is a declared deliverable… (#248)
# the nine files it names, at that commit:
158 explain-diff  193 brief  156 explain-findings  95 explain-topic  243 explainer-delivery
536 brief-compose  1468 explainer-serve  450 page_chrome  438 page_markup   = 3,737
```

**3,599 against 3,737 — accurate within 3.7% when written.** The same nine files today:

```
$ wc -l <those nine> | tail -1
    6525 total
```

So the three ratios are: cross-set, as the spec states it, 10,977/3,599 = **3.05×**; same-set,
2026-09-07, **0.96×** (i.e. correct); same-set, today, 6,525/3,599 = **1.81×**.

**Why this is High, not Low.** The spec does not merely get a ratio wrong. It draws a *lesson* from
the case and wires that lesson into three downstream places: §3 calls it *"the first evidence that an
inventory was needed rather than a **recollection**"*; §8's risk row reads *"The inventory is written
**from recall** and drifts, like the 9-files figure"*; §7 item 7 commits PR 1 to correcting it. But
the figure was not written from recall — `portable-practices.md:17` says *"Enumerated in
`docs/backlog.md` row 89, not recalled"*, and row 89 does contain that enumeration. It was derived,
correct, dated, and then its subject grew 1.75×. The actual failure mode is **a dated count decaying**
— which §3's own banner (*"a dated measurement, not a live number"*) already handles — so §8 is
mitigating against a failure this case is not an instance of, and the correction §7 produces will
record the wrong reason.

Separately: this is itself a correct measurement over the wrong corpus, placed in the finding whose
purpose is to shame that defect.

**Direction.** State the ratio same-set (1.81×), date both ends, and re-diagnose: the index figure
decayed, it was not recalled. If §8 wants a recall-drift risk it needs a different exhibit — and the
spec has a real one available (see M2).

### H2 — §6 requires creating the artifact §10 forbids creating

**The claims.** §6: *"A throwaway repository **outside** this one … The suite is added as a **local
marketplace** and installed the way a stranger would."* §10: *"Out of scope … **creating the
marketplace repository**."* §2: *"A marketplace is a git repo carrying
`.claude-plugin/marketplace.json`."*

**The failing case.** By §2's own definition the thing §6 must build *is* a marketplace repo. §10
forbids building one. Nothing in either section distinguishes the throwaway from the published one —
no adjective, no "the *published* marketplace repository". Phase 3 runs autonomously on this text; an
implementer hitting the contradiction has to pick a reading, and both readings are defensible.

I verified the definition holds on this machine — all three installed marketplaces carry that file:

```
$ for d in ~/.claude/plugins/marketplaces/*/; do ls "$d/.claude-plugin/"; done
marketplace.json          # claude-plugins-official
marketplace.json plugin.json   # omc
marketplace.json          # openai-codex
```

**Direction.** One word in §10: *"creating the **published** marketplace repository"*, and one in §6:
*"a throwaway local marketplace, which is not the published repo §10 defers"*.

### H3 — C3's known-killer example is false in form and mostly invisible to the scanner it is meant to calibrate

**The claim.** §4: *"`brief/SKILL.md`'s ground-truth command list calls `scripts/check-*` — guards that
are part of *this* repo's process."* §7: *"including `brief/SKILL.md`'s **nine** known references."*
Repeated in the new `docs/features.md` node: *"9 project-specific references in `brief/SKILL.md`'s
ground-truth command list alone, and that list invokes `scripts/check-*` guards"*.

**What I checked.** The literal form does not occur anywhere in the file:

```
$ grep -o 'scripts/check-[a-z0-9-]*' .agents/skills/brief/SKILL.md | wc -l
0
$ sed -n '44,62p' .agents/skills/brief/SKILL.md | grep -o 'scripts/[a-z0-9./-]*' | wc -l
0
```

The `9` *does* reproduce, but as nine repo-specific **items**, only four of which are checks and none
of which is a path:

```
$ sed -n '44,62p' .agents/skills/brief/SKILL.md | grep -o 'docs/[a-z0-9./-]*\|TaskList\|check-[a-z-]*' | sort -u | nl
     1	check-docs
     2	check-producer-enumeration
     3	check-roadmap-consistency
     4	check-test-counts
     5	docs/backlog.md
     6	docs/reviews/
     7	docs/roadmap-to-launch.md
     8	docs/superpowers/
     9	TaskList
```

**Why it matters downstream.** §5's two detectors are (1) *"matches against a derived vocabulary
(`supabase`, `gemini`, `fly`, `youtube-playlist`, **repo-rooted paths**)"* and (2) *"**invocations of
files** outside the component's declared shipping set"*. Of the nine: items 5-8 are repo-rooted paths
and would be caught by detector 1; items 1-4 are bare tokens, not files, and item 9 is a tool name —
**five of the nine are invisible to both detectors.** So the scan scores at most 4/9 on the single
component the spec elects as its known main killer, and D4's claim that *"the experiment calibrates
the scan"* rests on a calibration example the scan can only partly see. Compounding it, B2 shows the
experiment need not exercise step 1 at all.

**Direction.** Correct the characterisation at all three sites (it is 9 repo-specific items: 4 bare
guard names, 4 document paths, 1 tool name — not 9 `scripts/check-*` invocations). Then add a third
detector for bare tool and guard *names*, and state in §5 how the scan recognises a reference that is
not a path.

### H4 — C2 and C3 are called "mechanically countable"; both directions of wrong answer are present in the suite today, measured

**The claim.** §4's table: C2 and C3 *"mechanically countable"*. §4 also: *"A fourth verdict —
'unknown' — is not permitted; a component that cannot be assessed is `NEEDS-WORK` whose named defect
is 'no way to assess it'."*

**Clean count, unusable component — `scripts/page_chrome.py`:**

```
$ grep -ioc 'supabase\|gemini\|youtube-playlist' scripts/page_chrome.py     # C2
0
$ grep -c 'argparse' scripts/page_chrome.py ; grep -c '__main__' scripts/page_chrome.py
0
1
$ grep -c 'self.test\|--self-test' scripts/page_chrome.py                   # C1
6
```

Zero project vocabulary, a self-test, and its only outgoing import is `page_markup`, which is also
shipping — so C1 ✅, C2 ✅, C3 ✅. It scores as cleanly as anything in the suite. **It has no argparse
and no CLI**: a stranger cannot invoke it at all. It is a library whose value is entirely as a
dependency of `brief-compose.py` / `explainer-serve.py`, and §4's unit of assessment is the component,
with no notion of a component that is not independently usable.

Then the no-"unknown" rule bites: C4 for `page_chrome.py` cannot be assessed per component (the
experiment installs the *suite*, not components), so §4 forces `NEEDS-WORK` with defect *"no way to
assess it"* — and §7 item 5 converts every `NEEDS-WORK` into *"a `docs/backlog.md` row per
`NEEDS-WORK` component"*. The spec therefore manufactures backlog rows for components that have no
defect. **That is the misleading label the three-verdict rule forces.**

**Dirty count, fine component — `scripts/page_markup.py`:**

```
$ grep -ion 'supabase\|gemini\|youtube-playlist' scripts/page_markup.py
304:supabase
305:supabase
$ sed -n '304,305p' scripts/page_markup.py
    case("code: a path glob survives", r("`supabase/migrations/*persist_summary*`"),
         "<code>supabase/migrations/*persist_summary*</code>")
```

Both hits are inside a **self-test fixture** — a case asserting that a path glob survives markup
rendering. The component is fully project-independent; the vocabulary appears only in a test string.
§5 item 1 says matches are *"against a derived vocabulary … not a hand-written list"* and says nothing
about excluding test fixtures, so the scan reports a C2 violation on the suite's most portable file.

**Direction.** Add a fourth category to the verdict set or a stated **role** per component
(`entry-point` vs `library`), so a non-invocable dependency is not scored as if a stranger runs it;
make C4 assessable per *installed unit* rather than per component; and state in §5 whether self-test
fixtures and comments are in or out of the scanned region, since that choice alone flips a verdict
here.

### H5 — "the problem is concentrated in one file" is mislocated; the suite's real C3 blocker sits in the file the spec certifies as clean, and §5's granularity is unstated

**The claim.** §4 and the page both carry `portable-practices.md`'s measurement: *"`explainer-delivery.md`
**0** project references, `explain-topic` and `explain-findings` **1** each, `brief/SKILL.md` **9**"*,
with *"The problem is concentrated in one file"*.

**What I checked.** The `0` reproduces under the vocabulary detector — and misses the three hardest
dependencies in the suite:

```
$ grep -ioc 'supabase\|gemini\|youtube-playlist' .agents/skills/shared/explainer-delivery.md
0
$ grep -n 'python3 scripts/' .agents/skills/shared/explainer-delivery.md
118:python3 scripts/brief-compose.py --content <fragment.html> --slug <slug> --title "<title>"
141:python3 scripts/explainer-serve.py     # idempotent; a no-op if already up
218:3. **what to do when that URL does not load** — `python3 scripts/explainer-serve.py`, safe to run
```

These are **repo-relative paths resolved from the caller's CWD**, and they are the shared delivery
contract that *all four* page-producing skills route through. In a stranger's repo `scripts/` is their
own directory or absent, so the invocation resolves to nothing — or to an unrelated neighbour's
`scripts/`. That is a C3/C4 blocker for every component of effort (3), not a `brief`-only problem, and
it lives in the file both the spec and the page present as the good news.

**And §5's granularity flips the verdict on it.** §5 measures *"invocations of files outside **the
component's declared shipping set**"*. `brief-compose.py` and `explainer-serve.py` are both in §3's
component list. So: shipping set read **per component** → `explainer-delivery.md` scores dirty (both
invocations are outside its own set); read **per suite** → it scores clean. §5 never says which, and
nothing else in the spec does.

**Direction.** Say whether a shipping set is per component or per publishable unit (this is the same
missing artifact as B3). Then re-state the coupling finding: the measurement that exists is C2-only,
as §4 correctly notes — but the conclusion drawn from it ("concentrated in one file") is a C3 claim
that the C2 measurement cannot support, and is false.

### H6 — The page's only effort-(2) evidence figure is a number no run has produced, and a prior review half already filed it

**The claim.** Page §3 table, effort (2) row: *"Sharding shipped and worked — the sweep went **1,758s
→ 346s**."*

**What I checked.** `ci.yml` records 353s, twice:

```
$ grep -n '1758\|346\|353' .github/workflows/ci.yml
621:    # measured speedup at N=8 is 5.0x (1758s -> 353s) rather than 8x: see the matrix.
664:        #   unsharded `--mutate .`          1758s   (29.3 min — the thing being replaced)
668:        #   shard 1 of 8, measured           353s   (150/150 killed, 150 attributed)
```

`346` appears nowhere in `ci.yml`, nowhere in `docs/velocity-evidence-2026-09-24.md`, and nowhere in
`scripts/`. It appears in exactly one prior place — a Claude review half that **filed it as a
defect**:

```
$ sed -n '73,77p' docs/reviews/claude/shard-mutation-sweep-r9-claude.md
Same artifact, same class, smaller: the PR **title** asserts *"1,758s becomes 346s"* and `ci.yml`
records `353 s`. Both are local figures from one machine. CI's eight shards at this commit took
**172–239 s**. Nothing is overstated in the favourable direction, but the squash subject will
permanently carry a number no CI run has produced, and it is the only number most readers will see.
```

So the three candidate values are: `353s` (local, in `ci.yml`), `172–239s` (what CI actually ran), and
`346s` (produced by nothing). The page reinstates the third into the Phase 1 gate artifact, as the
single piece of evidence offered for effort (2)'s verdict. Round 9 filed it Medium on a squash
subject; on the gate page a human reads to make a scope decision, it is worse.

Method note: I confirmed the search finds a known positive before trusting the negative —
`grep -rln '353s'` returns `ci.yml` and `shard-mutation-sweep-r1-claude.md`, so the method works and
the absence of `346s` is a real absence.

**Direction.** Use `172–239s` with "CI, 8 shards" as the label, or `353s` labelled "one machine,
shard 1 of 8". Not 346.

---

## Medium

### M1 — `24 = 17 + 3 + 4` does not reproduce from §3's own enumeration; two of the three addends are unobtainable

**The claim.** §2: *"a surface question over **24 components** (17 + 3 + 4, enumerated in §3 — derived
2026-10-15, not estimated)."* §9b: *"'~13 components' was invented. The derived figure is **24** (17 +
3 + 4)."* The page: *"17 comprehensibility, 3 velocity, 4 recall."*

**What I checked.** Effort (3) reproduces exactly. Counting its table rows at the granularity the rows
themselves use:

```
4 (explain-diff/brief/explain-findings/explain-topic) + 3 (shared/) + 1 + 1 + 2 + 2 + 4 (hooks) = 17 ✅
```

Effort (2)'s prose enumerates five items — `ci.yml` sharding, `check-plan-code.py`, and three velocity
documents, all three of which exist:

```
$ ls docs/superpowers/specs/*velocity* docs/superpowers/plans/*velocity* docs/velocity-evidence-2026-09-24.md
docs/superpowers/plans/2026-09-25-development-velocity-RECONSTRUCTED-plan.md
docs/superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md
docs/velocity-evidence-2026-09-24.md
```

1 + 1 + 3 = **5**, not 3. Effort (1)'s prose enumerates: script, hook, 157 memory files, two branches
= **5**, not 4. Item-by-item the total is **17 + 5 + 5 = 27**.

The addends 3 and 4 are obtainable only by grouping — counting three velocity documents as one
component, and two branches as one — and that grouping contradicts effort (3)'s granularity, where
four SKILL.md files, three shared files and four hook scripts are each counted individually. Pushed
the other way, effort (3)'s one-file-one-component rule applied to effort (1) makes **157 memory
files 157 components**, and effort (1) alone exceeds 160.

So the central scope number is not reproducible from its own text, in the document whose §9b
apologises for an invented component count and whose §8 lists this exact drift as a risk. The `17`
is sound; the `24` is not derived, it is composed.

**Direction.** State the counting rule once (what is one component?), apply it to all three efforts,
and publish the per-effort enumeration as a list rather than prose. B1's omission changes effort (1)'s
addend regardless.

### M2 — The recall result does not reproduce: lexical is 3/20, the "19–20/20" range merges two different experiments, and the stated bound is dropped

**The claim.** §3: *"lexical scoring scored **2/20**; the same paraphrases read by an LLM scored
**19–20/20**, with 0 false fires in 60."* Repeated on the page.

**What I checked** — the measurement record,
`~/.claude/projects/…/memory/backlog-191-semantic-recall-replicated.md`:

| arm | must-fire | negatives | false-fire |
|---|---|---|---|
| lexical top-1 | **3/20** | 53/60 | **11.7%** |
| semantic, 2 runs (33) | 20/20 | 13/13 | 0% |
| semantic, isolated (80 mixed) | **20/20** | **60/60** | **0%** |

Three discrepancies:

1. **Lexical is 3/20, not 2/20.** The error is one case, and it runs in the direction that strengthens
   the spec's "it inverted" argument — the signature this project has recorded repeatedly for a figure
   that was reasoned rather than read.
2. **"19–20/20" merges two experiments.** The headline isolated run is a flat **20/20**. The `19`
   comes from a different probe — nested corpora at sizes 300/600/1000 scoring 20/20, **19/20**, 20/20
   — whose point in the record is that *recall is non-monotonic in corpus size*. Presenting it as a
   range on the headline result reads as measurement noise on one experiment when it is one point from
   another.
3. **The bound is dropped.** The record states it explicitly: *"⚠ **The bound is 5.0%, not zero**
   (rule of three, 0 in 60)."* The spec and the page both say "0 false fires in 60" with no bound.
   This repository keeps a memory rule for exactly this (*state the BOUND … never "no false
   positives"*), and the spec is the document that will be quoted downstream.

Also unreported: the record's three live caveats (paraphraser and matcher share a model family;
labels are the original author's; deployment ratio nearer 50:1 than 3:1). For a verdict that §6 says
must rest on *"C1–C3 plus argument"*, C1's evidence arriving without its caveats is the weakest link
in the weakest-evidenced effort.

**Direction.** 3/20 lexical, 20/20 semantic (isolated, 80 mixed), 0/60 false fires with a 5.0% upper
bound; cite the corpus-size probe separately if it is wanted.

### M3 — "604 lines of skills" omits 630 lines of skills that §3's own table enumerates

**The claim.** §3: *"**10,373 lines across six files**, before 604 lines of skills."* The page totals
this as `measured 10,977`.

**What I checked.** 604 reproduces exactly — as the four `SKILL.md` files only:

```
$ cat .agents/skills/{explain-diff,brief,explain-findings,explain-topic}/SKILL.md | wc -l
604
$ wc -l .agents/skills/shared/*.md
      73 corpus-search.md
     346 explainer-delivery.md
     211 handoff-path.md
     630 total
```

§3's table lists all three `shared/` files as components of the suite (row 2). They are **630 lines**
— slightly more than the 604 counted. So the spec's replacement total, and the page's chart, undercount
the spec's own enumerated component set by 630 lines (10,977 → 11,607). §8's row *"~11,000 lines is
too much to assess per line"* inherits it.

This is the same class as H1 at smaller scale, and it is in the corrected figure rather than the one
being corrected. Note that `explainer-delivery.md` is *also* one of `portable-practices.md`'s nine, so
for the comparison in H1 it must be on both sides.

**Direction.** State the total as `10,373 Python + 604 skills + 630 shared contracts = 11,607`, or
drop `shared/` from the component table — but not both ways at once.

### M4 — D4's load-bearing justification compares unlike units

**The claim.** §2: *"This repository has measured that *review is the wrong instrument for a surface*:
six review rounds produced roughly seven edge cases where a single corpus run produced 5,287."*

**What I checked.** `5,287` reproduces as a figure — `docs/reviews/claude/closing-table-r5-claude.md:82`
gives `| **total** | **5,287** | **456** | **1** | **1** |`, and `docs/dashboard-entries.md:10902`
reads *"5,287 commands in total. It flagged 456 and got two apparently wrong."* So 5,287 is the
**corpus size** — inputs examined. What it *produced* was **456 fires and 2 discrepancies**.

As §2 is written, the corpus run "produced 5,287" of the same kind of thing the six review rounds
produced seven of. It did not: seven findings against 456 fires, or against 2 real discrepancies, is
the comparison. The argument for D4 survives either way — 456 ≫ 7 — so this is Medium, not High. But
it is the sentence that justifies the method over judgement, in a spec about deriving numbers
honestly, and it inflates by ~11×.

**Direction.** *"six rounds produced roughly seven edge cases; one corpus run over 5,287 inputs
produced 456 fires and surfaced two real defects."*

### M5 — D3's "proven on this machine" proves the route, not that this artifact can travel it

**The claim.** §2: *"**Why D3 is safe to commit to:** the route is proven on this machine, not
theorised — `~/.claude/plugins/marketplaces/` holds `omc`, a third-party self-published marketplace,
alongside the official one."*

**What I checked.** The directory holds **three** marketplaces, two of them third-party — `omc`,
`openai-codex`, `claude-plugins-official` — each with `.claude-plugin/marketplace.json`. `omc` is
structured as a plugin from the root (`"source": "./"`, with `agents/`, `commands/`, `hooks/`,
`skills/`).

What that establishes: `/plugin marketplace add` works for a repo **authored in plugin shape**. What
it does not establish, and what the spec never asks anywhere: whether a plugin can carry **10,373
lines of Python living in `scripts/`**, and if so, where that lands on a stranger's disk and how a
`SKILL.md` names it. The suite's delivery contract invokes `python3 scripts/brief-compose.py` from the
caller's CWD (H5). An installed plugin does not put `scripts/` at the user's repo root. So the entire
effort-(3) mechanism depends on a path-resolution story that D3 does not supply and §6 would discover
only after the scan is built — at which point §9's third falsifier (*"if the install experiment cannot
be made to run at all, D4 is unachievable"*) is the one that fires, and the milestone's method has to
be re-decided with the owner.

This is the answer to "what must a reader take on trust": **that the artifact fits the route.**
Everything else in the spec is downstream of it, and §7 orders the scan (item 2) before the experiment
(item 3), so the cheapest possible refutation is scheduled second.

**Direction.** Either add a two-hour spike — one skill, one script, installed from a local marketplace,
invoked from elsewhere — as §7 item 0, before the scan; or state explicitly in D3 that packaging
feasibility is assumed and name it in §9 as the assumption whose failure invalidates D4.

### M6 — "15 document guards … 0 failing" names a denominator that exists nowhere

**The claim.** Page, state block: *"15 document guards run on the branch, 0 failing (volatile — a
guard result decays in minutes)."*

**What I checked.** No enumeration of fifteen document guards exists in the repo:

```
$ grep -rn '15 document guards\|15 guards' docs/ --include=*.md   # excluding the page itself
(no output)
```

The page correctly labels the result volatile, so the decay is disclosed. The unreproducible part is
the **set**: a reader cannot tell which fifteen, so "0 failing" cannot be re-run, and a sixteenth
guard going red would not change the sentence. `scripts/check-schema-gates.sh` bundles thirteen (now
fifteen) *schema* gates, which is a different population and may be where the number came from.

I did verify the two guards the page names individually, and both reproduce verbatim:

```
$ python3 scripts/check-anchors.py   # rc=0
anchors: 14 registered, all claimed; every spec/plan dated >= 2026-08-25 declares one; floor 22 held
$ python3 scripts/check-features.py  # rc=0
feature map: 27 nodes (24 built, 3 declared absent); 14 anchors and 21 backlog areas all claimed exactly once
```

**Direction.** Either name the fifteen (a `for g in …; do` list in the dashboard entry would do), or
say "the document guards this branch touches" and name those.

---

## Low

### L1 — The page's gate claims were measured on a tree two commits behind the page

The page states *"branch `marketplace-inventory` at `e1cd5b8a`"*; HEAD is `a3fbb197`, and `e1cd5b8a`
is two commits back — the page's own commit (`a3fbb197`) and the one before it postdate the figure.
A page cannot cite its own SHA, so this is structural rather than careless, and the page labels guard
results volatile. Worth a line because "0 failing" was measured on a tree that did not contain the
741-line page or the fragment, and `check-docs.py` reads `docs/`.

**Direction.** Stamp the footer with the SHA *and* note "guards measured at `<sha>`, before this
page landed", or re-run after committing and amend.

### L2 — One of the four regen hooks is not executable, unlike its three siblings

```
$ ls -la .claude/hooks/regen-*.sh
-rwxr-xr-x  regen-backlog-page.sh
-rw-r--r--  regen-dashboard.sh      <-- 644
-rwxr-xr-x  regen-features-page.sh
-rwxr-xr-x  regen-goals-page.sh
```

`.claude/settings.json` invokes hooks as `bash <path>`, so it works in this repo and this is not a
live defect. It is a C4 detail for a stranger who wires the hook any other way, and §5's third
report (*"presence of a self-test and of user-facing documentation"*) would not surface it. Noted
because the four hooks are counted as four components and this one differs from the other three in a
way the scan as specified cannot see.

**Direction.** `chmod +x`, or note in the inventory that hook components are invoked via `bash` and
the mode is not load-bearing.

---

## What I checked and could NOT fault

These reproduced exactly, by command, and are stated correctly in the spec:

| Claim | Command | Result |
|---|---|---|
| SKILL.md lines `158 / 195 / 156 / 95` | `wc -l` on the four | exact, all four |
| `10,373 lines across six files` | `wc -l` on the six named | `10373 total` — exact |
| `604 lines of skills` | `cat` four SKILL.md \| `wc -l` | `604` — exact (see M3 for what it omits) |
| anchors `13` before, `14` after | `git show master:docs/anchors.md` vs HEAD, table rows | 13 → 14 — exact |
| `check-anchors` passes with the new name | `python3 scripts/check-anchors.py` | rc=0, *"14 registered, all claimed"* |
| `check-features reports 27 nodes — 24 built, 3 declared absent — 14 anchors and 21 backlog areas all claimed exactly once` | `python3 scripts/check-features.py` | rc=0, **verbatim** |
| `157` memory files | `ls …/memory/*.md \| wc -l` | `157` — exact¹ |
| `c5-recall-matcher` (6 commits), `backlog-117-parser-substrate` (10) | `git rev-list --count master..<b>` | 6 and 10 — exact, both branches exist |
| `39 references in ci.yml` | `grep -c shard .github/workflows/ci.yml` | `39` — reproduces case-sensitively² |
| three velocity documents | `ls` | all three present |
| a marketplace is a git repo with `.claude-plugin/marketplace.json` | `ls` on all three installed | holds (see M5 for what it does not prove) |
| `5,287` | `closing-table-r5-claude.md:82` | reproduces as a figure (see M4 for the unit) |
| effort (3) = 17 components | row-by-row tally of §3's table | `4+3+1+1+2+2+4 = 17` — exact |
| `Q0 is designed in form and not built` | — | NOT VERIFIED, see below |

¹ The 157 includes `MEMORY.md`, which is the index, not a memory — 156 actual memories, and
`MEMORY.md`'s own index carries 139 rows while its header says 133 arrive per session. The spec's
figure is right for what it says ("157 memory files"); flagging only because effort (1)'s addend
(M1) depends on how this corpus is counted, and because a 157-file corpus of the author's private
notes being scored `SHIP`/`DON'T-SHIP` as one "component" is a scope question §3 does not address.

² Case-insensitively it is **47**; non-comment lines are **10**. So 39 is reproducible but
definition-dependent, and the definition that yields it excludes the eight `SHARD_INDEX` /
`SHARD_TOTAL` lines that do the actual sharding. 37 of the 47 are prose comments, so the figure
measures documentation volume more than mechanism. Not filed as a finding — it is honest and roughly
right — but the derivation should be recorded beside it per §8's own mitigation.

**And things that are structurally right, which I tried to break and could not:**

- **The anchor/claimant mechanism.** Row 290 named three candidates and this spec is candidate (a);
  `check-anchors` R4 would have refused the name without a claiming document, and it passes. The
  backlog row's new status is scrupulous about not over-claiming — *"Row closes when that spec's PR
  merges; it is **NOT** closed by the spec existing."* I looked for a premature `✅` and there is none.
- **`docs/features.md`'s split.** The anchor sits on `process-harness` (built) and the absent child
  `harness-installs-elsewhere` names only the gap, because `check-features` refuses an anchor on an
  absent node. That is the honest shape, and the page's §6 records the gate as having had the better
  rule. (The node's `expected-because` text carries H3's defect, but the structure is right.)
- **The page as a gate artifact.** It states what approving commits the reader to and, explicitly,
  what it does not — *"Nothing is installable at the end of this milestone … If you expected something
  shippable from this milestone, say so now — it is a different plan, not a tweak to this one."* Every
  decision carries a case against it and a stated condition under which the alternative wins; it
  names where the plan is weakest in its own §5; it discloses the invented `~13`; and its four
  questions are real forks, not confirmations. Its question 4 (does "publishable" need a support
  policy first?) identifies a genuine spec gap — D1 commits to a public bar and §7 produces no
  support-policy deliverable, with §10 not excluding one either. **The page is more candid about the
  spec's weaknesses than the spec is**, which is the right direction for this gate; the findings
  above against the page are inherited figures (H1, H6, M2, M6), not omissions of substance.
- **§9b.** Recording the invented `~13` rather than silently fixing it is the correct handling, and it
  is what made H1 and M1 findable. The practice works; it just has to be applied to the replacement
  figures too.

---

## NOT VERIFIED

- **`Q0 is designed in form and not built` and `one of two items check-roadmap-consistency still
  reports open`** (§3) — I did not run `check-roadmap-consistency`. Reason: it was not needed for any
  finding and I did not want to spend the run; the claim is plausible and locally checkable. Treat as
  unmeasured, not as confirmed.
- **Whether `/plugin marketplace add <local path>` actually succeeds** — no install was attempted.
  This is the subject of M5 and is, by §6, PR 1's job. I verified only that three marketplaces are
  installed and carry the manifest file.
- **The 5,287 run's `456 fires / 2 discrepancies` breakdown** beyond the two sites I quoted
  (`closing-table-r5-claude.md:82`, `dashboard-entries.md:10902`) — I did not re-run the corpus.
- **Whether `grep -r`'s symlink behaviour (B3) is the behaviour the unwritten scanner will have** —
  B3's measurement is of `grep -r`, which is what `.agents/skills`-walking guards in this repo use;
  a scanner written with `Path.rglob` or `os.walk(followlinks=True)` would not truncate the same way.
  The finding stands as *a reachable path to a wrong-corpus clean score over the paths §3 names*, and
  as the argument for an expected-file-count assertion — not as a claim about code that does not
  exist yet.
- **`scripts/check-plan-code.py`, `scripts/check-surface-recall.py` and `scripts/recall-llm.py` were
  measured by line count and caller only.** I did not assess their C1-C4 standing; that is the
  milestone's work, not this review's.
- **Disclosure on independence:** I did not read the Codex half
  (`docs/reviews/codex/marketplace-inventory-r1-codex.md`). One line of it surfaced incidentally in a
  repo-wide `grep` for `346`, which told me it had marked the 5,287 / 15-guards / 1,758→346 figures as
  not independently replayed. I had already derived H6 and M4 at that point; I did not open the file.
  All findings above are from my own measurements.

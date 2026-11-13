# Marketplace inventory spec — round 2, CLAUDE half

**NOT CONVERGED.**

| | Blocking | High | Medium | Low | total |
|---|---|---|---|---|---|
| CLAUDE r2 | 2 | 7 | 10 | 2 | **21** |

**Attribution — the input the thrashing trigger needs:**

| Attribution | Findings | Count |
|---|---|---|
| **INTRODUCED BY ROUND 2'S FIX** | B1, B2, H1, H2, H3, H4, H5, H7, M1, M3, M4, M5, M7, M8 | **14** |
| introduced by round 1's fix, retained through round 2 | M2, M6 | 2 |
| present before; not closed by either fold | H6, M9, M10, L1 | 4 |
| process, not the document | L2 | 1 |

⛔ **THE ARCHITECTURE REVIEW FIRES.** Round 2 was the first round carrying fix-induced findings
(4 of 10). This is the second, at **14 of 21**, in the same component — the §§3–7 fold and the
walkthrough page. My answer to *thrashing or prose floor?* is in the closing section, with
per-finding evidence, and it is **neither**: there is one mechanism behind almost all fourteen, it
is already named in this branch's own record, and a redesign removes it.

---

## ⚠ The subject moved under this review — read the attributions with this in mind

My brief named `bea19c78`. At **14:57:51** a new commit `5fa1155f` ("Three places still called 24 a
total after round 2 made it a floor, and a markdown bold leaked into the page") landed on the branch
while I was reading, taking the spec from **663 to 669 lines**.

```bash
git reflog -3          # 5fa1155f HEAD@{0}, bea19c78 HEAD@{1}
git diff --stat bea19c78 HEAD   # 3 files, 42 insertions, 16 deletions
```

Two consequences, stated rather than hidden:

- Two of my early reads showed text I could not later find. That was the subject changing, not a
  misread, and I confirmed it by `md5`, `wc -l` and `git diff --quiet HEAD` before concluding
  anything. I report it because a reviewer who had not noticed would have filed findings against a
  tree nobody else could see.
- **Every finding below was re-verified at `5fa1155f`, not at `bea19c78`.** I ran each probe at both
  commits. All 21 stand at the tip; `5fa1155f` closed only the three flat-`24` statements it names,
  and I confirm that closure in *what I could not fault*.

---

## Blocking

### B1 — The page still asserts rules the folded spec rejects. Round 2's Blocking was declared FIXED and has recurred, by the same mechanism, in the same artifact

**INTRODUCED BY ROUND 2'S FIX.**

Round 2's finding 1 was *"The gate page still presents rules the folded spec explicitly rejects"*.
The coordinator recorded: **FIXED — page contract rebuilt from the folded spec, not patched.
Verified by execution: 0 `countable` pills, claim gone, 9 new elements render.**

That verification checked the **three strings that were fixed** and the **nine elements that were
added**. It never asked whether the rest of the page still disagrees with the spec. Four
contradictions survive, each verified present at both `bea19c78` and `5fa1155f`:

**(a) D5 is presented as both settled and undecided, on one page.** The upper block reads
*"D5 · Your decision, now settled — verdict and evidence are two axes … It is a decision of record
now, not a recommendation"*. Lower down the same page still argues the case:

> *"But I would not add a fourth verdict, and here is the distinction that decides it."*
> *"What is left is the part I deliberately did not decide for you."*

**(b) The page still states round 1's inheritance rule, which round 2 refuted and the spec replaced
with five rules:**

> *"a `library` inherits its support verdict from the entry-points that import it"*

Round 2's finding 3 is precisely that this sentence is undefined for more than one importer and
silently wrong for none. §4 now carries the aggregation, orphan, cycle, dual-role and provenance
rules. The page carries the refuted version **and** the replacement (`inherited — a library, via
named entry-point scenarios`), with nothing marking which governs.

**(c) The page still flatly states the rule D5 overrode:**

> *"'Unknown' is not permitted — a component that cannot be assessed is `NEEDS-WORK` whose named
> defect is 'no way to assess it'."*

Under §4b a component merely unreached by the experiment is **`argued`, not `NEEDS-WORK`, and files
no backlog row**. The page's own D5 block says so, eleven lines earlier.

**(d) The page asserts the attribution round 2 refuted.** Its comparison table reads:

> *"Same nine files, at **the commit that wrote the figure** (`100cf498`, 2026-09-07): 3,599 vs
> 3,737 — accurate within 3.7%"*

and the prose beneath it: *"The figure was derived, enumerated, dated and **correct when written**"*.

Round 2's finding 9 established that `100cf498` is **not** the commit that wrote the figure —
`cacbac17`, four days earlier, is — and that at `100cf498` it was **already 3.7% stale**, i.e. not
correct when written. The spec's three-stage table says exactly this. The page says the opposite,
and round 2's single most-emphasised transferable finding (*a republished figure inherits staleness
and loses the fact that it is inherited*) appears on the page **zero times**.

**What I checked.** Detagged both artifacts and grepped source at both commits:

```bash
python3 -c "...strip tags from fragment..."       # 394 text lines
for c in bea19c78 5fa1155f; do
  git show $c:docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html \
    | grep -c 'would not add a fourth verdict'        # 1, 1
  ... 'did not decide for you'                        # 1, 1
  ... 'support verdict from the'                      # 1, 1
  ... 'commit that wrote the figure'                  # 1, 1
  ... 'cacbac17\|republish'                           # 0, 0
done
```
Both `.html` and `.fragment.html` carry (a)–(d) identically, so this is not a stale-fragment
artifact.

**Direction.** The repair that was applied — rebuild the contract paragraphs — is the right one and
was applied to too little of the page. Before the gate, diff the page's *claim set* against the
spec's, not its paragraphs: enumerate every rule the spec states and confirm the page states that
rule and no superseded variant of it. ⛔ And verify by **absence of the refuted claim**, which is
what the round-2 verification omitted; counting added elements cannot detect a surviving
contradiction.

---

### B2 — The artifact the human approves misdescribes its own subject: a "213-line spec" that is 669 lines, stamped at two commits, neither of them the subject

**INTRODUCED BY ROUND 2'S FIX** (the page was recomposed and the state block was not re-derived).
Round 1 filed this as L1, it was recorded **FIXED — state block re-stamped**, and it has recurred
larger.

**Claim**, from the page's "Read this first — what state everything is in" block:

> *"Nothing is implemented. What exists is a **213-line spec**, an allocated anchor, and a feature-map
> node."* … *"As of 2026-10-16 ~13:30 PDT, branch `marketplace-inventory` at **`a3fbb197`** plus the
> round-1 fold."*

and the page header:

> *"Spec `2026-10-15-marketplace-inventory-design.md` · branch `marketplace-inventory` at
> **`e1cd5b8a`** · PR 376"*

**Failing case.** The reader is asked to approve a document whose length the page understates by
**3.2x**, on a page that names **two different commits, neither of which is the subject**, while its
body describes round 2's machinery. A reader deciding how much scrutiny the gate deserves — a
213-line spec reads as an afternoon's work, 669 lines does not — is being given a number that was
true two folds ago.

**What I checked.**

```bash
wc -l docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md     # 669 (663 at bea19c78)
grep -c '213-line' ...fragment.html                                        # 1 at both commits
grep -o 'e1cd5b8a\|a3fbb197\|b748812e\|8a19f4ce\|bea19c78' ...fragment.html \
  | sort | uniq -c                           # 2x e1cd5b8a, 1x a3fbb197, 0 of the three folds
git rev-parse HEAD                           # 5fa1155f
```
`e1cd5b8a` is the dashboard-entry commit, three commits before the r1 fold. Neither fold commit
appears anywhere on the page.

**Direction.** Derive the three provenance facts — spec line count, branch, commit — by command at
compose time, and fail composition if they are absent, rather than writing them by hand. The page
already argues against hand-written figures in its own §3; it is the one place on the page that does
not follow its own rule. ⚠ The deeper point: this defect has now been filed, fixed and recurred
within two rounds, which makes it a **compose-time gap, not an authoring slip**.

---

## High

### H1 — §5 asserts that §7 item 2 names who derives the shipping-set declaration and what validates it. §7 item 2 names neither

**INTRODUCED BY ROUND 2'S FIX** (finding 4's fold edited §5 and left §7 item 2 unchanged).

**Claim**, §5:

> *"**§7 item 2 therefore names who derives the declaration and what validates it against the
> installed layout and the dependency closure** — an oracle written from the output it is meant to
> check is not an oracle"*

**Failing case.** §7 item 2, in full, at the tip:

> *"2. ⭐ **The shipping-set declaration (added by r1 CLAUDE B3, r1 CODEX 2)** — per publishable unit,
> as **data the scan reads**, listing member files with symlinks resolved and an expected file count
> per component. ⛔ Nothing in the original nine deliverables produced this, so the scan had only two
> options at build time: CANNOT RUN for all 24 components, which empties deliverable 5, or infer the
> set — the condition §5 warns about, with no gate on the inference."*

It specifies the declaration's **format and location**. It names no deriver, no validator, no
installed-layout check and no dependency-closure check. So round 2's finding 4 — *"an oracle written
from the output it is meant to check is not an oracle"* — is closed by a **cross-reference to a
section that does not contain the answer**. The builder of PR 1 following §5 to §7 finds nothing,
and the honest reading is that the oracle problem is still open while the spec records it as solved.

This is the question the brief put as *"who validates the validator"*. The answer is: **nobody is
named, and the spec says somebody is.**

**What I checked.** Read both sections at both commits:

```bash
sed -n '/^2\. ⭐ \*\*The shipping-set declaration/,/^3\./p' <spec>    # the text quoted above
sed -n '/^## 7\./,/^## 8\./p' <spec> | grep -n 'derive\|validat\|closure\|who'   # no hits
```

**Direction.** Either name the deriver and the validator in §7 item 2 — my suggestion: the
declaration is derived from the **installed** package tree after §7 item 0's spike, by a step that
never reads the scan's output, and is validated by a third check that walks the dependency closure
from each declared entry-point and fails on any reachable file absent from the declaration — or
delete §5's claim that §7 does so and re-file the oracle problem as open. ⛔ A cross-reference that
asserts its target's content is worse than a gap, because it closes the finding in the reader's mind.

---

### H2 — §6's declared baseline and capture mechanism have no producing deliverable. This is round 1's Blocking B3, one round later, in the same pair of sections

**INTRODUCED BY ROUND 2'S FIX** (finding 7). ⛔ **This is the single most important datum for the
thrashing question.**

Round 1's Blocking B3/F2 was: *"§5 requires a per-component declared shipping set; nothing in §7
produces one."* It was fixed by adding §7 item 2. Round 2's finding 7 then required a baseline and a
capture mechanism in §6. That fix added the requirements to §6 **and added nothing to §7** — so the
branch now has the identical defect, one section over.

**Claim**, §6:

> *"⭐ **a DECLARED BASELINE, because a fresh `HOME` is not isolation (r2 CODEX 7, High …)** … **The
> baseline names what a stranger is ASSUMED to have** — interpreter version, package set, available
> commands, network policy — and every deviation from it is recorded as a prerequisite"*
> *"⭐ **a capture MECHANISM, and its stated limits.** … So: name the mechanism (process/filesystem
> tracing, or an allow-listed environment), and **state what it cannot see**."*

**Failing case.** §7 enumerates eleven deliverables (0–10). **None produces the baseline, and none
produces the capture mechanism.** Item 4 is *"The install-experiment record: failures found, which
the scan predicted, and every resource the run touched (§6)"* — that is the resource record, which
is the **output** of the capture mechanism, not the mechanism or the baseline. So PR 1 reaches the
install experiment with a requirement to have declared a baseline and no artifact in which to have
declared it, and the experiment's isolation claim rests on an undocumented environment — exactly the
condition round 2's finding 7 reported.

Worse, §6 *names the failure it is reproducing*: *"an exhaustive-observation requirement with no
implementation is not evidence of isolation, it is an aspiration."* The fix turned one aspiration
(the resource record) into two (baseline, mechanism) and left both unowned.

**What I checked.**

```bash
sed -n '/^## 7\./,/^## 8\./p' <spec> | grep -n 'baseline\|capture\|tracing\|prerequisite'
#   -> NONE in §7, at both bea19c78 and 5fa1155f
```
Confirmed against a known positive: the same grep over §6 returns the two bulleted requirements, so
the zero over §7 is a real zero.

**Direction.** Add a §7 deliverable: *the baseline document and the capture mechanism, written
before §7 item 0's spike runs, naming interpreter, package set, available commands, network policy,
and what the mechanism cannot observe.* It must precede the spike, because the spike is the first
thing that runs in the isolated environment and is therefore the first thing whose isolation needs a
baseline to be measured against. ⛔ **And add the general rule this branch has now paid for twice: a
requirement stated in §§4–6 is not folded until a §7 item produces it.** That rule is the class fix;
item 2 and this item are the two instances.

---

### H3 — §6's "one documented RECOVERY scenario" has no subject: the shipped suite documents no recovery, and authoring one collides with §7's no-repair rule

**INTRODUCED BY ROUND 2'S FIX** (finding 8).

**Claim**, §6 pass condition item 4:

> *"4. ⭐ **one documented RECOVERY scenario succeeds**, because C4 says *"recover from failure without
> the author"* and no part of the original method tested recovery at all"*

**Failing case.** There is no documented recovery scenario in anything that ships. Over all seven
shipped skill and contract files, the pattern returns **zero**:

```bash
grep -rcE 'safe to run twice|will not load|recover from' \
  .agents/skills/{brief,explain-diff,explain-findings,explain-topic}/SKILL.md \
  .agents/skills/shared/{explainer-delivery,corpus-search,handoff-path}.md
#   -> 0 for all seven
```

⛔ **Known positive confirmed before trusting that zero:** the same pattern returns **1** against the
walkthrough page, which carries *"If the URL will not load, run `python3 scripts/explainer-serve.py`
— safe to run twice."* So the suite's only recovery instruction lives in a **hand-authored page about
this spec**, not in any file a stranger would install. A broader sweep for
`recover|troubleshoot|if it fails` over the same seven files finds one hit, and it is a historical
note about a page lost to a crash (`explainer-delivery.md:64`, backlog #259) — not a procedure.

So item 4 is unsatisfiable as written: the experiment is required to run a documented recovery
scenario, and there is no documentation to run. The two escapes both fail:

- **Author the documentation during the experiment** — then §7's *"What PR 1 explicitly does NOT do:
  … fix any coupling"* is violated, and the owner's option A (evaluation independent of repair) is
  the thing it violates.
- **Treat the absence as the finding** — correct, and then item 4 is not a *pass condition* but a
  guaranteed `NEEDS-WORK` on every entry-point, which makes the install experiment's C4 verdict
  known before it runs. A pass condition whose outcome is determined in advance is the shape §9c
  records as *"a measurement that cannot come back wrong"*, inverted.

**Direction.** Split item 4 in two: a **gate** (*does the suite document any recovery procedure at
all?* — answerable today, answer: no, and that is a C4 finding for the inventory to carry) and a
**conditional pass condition** (*where a procedure is documented, it succeeds under isolation*). The
second then has a population, possibly empty, and says so. ⚠ As written, item 4 reads as though
recovery documentation exists; nobody in three halves checked whether it does.

---

### H4 — The inheritance rules and D5's grade axis do not compose: a library under an unexercised entry-point is `inherited` by one rule and `none` by another, and `inherited` launders `argued` upward

**INTRODUCED BY ROUND 2'S FIX** — specifically by the *composition* of round 2's finding-3 fold
(the five inheritance rules, §4) with the owner's D5 decision (the grade axis, §4b). The two were
authored for different findings and are not reconciled.

**Claims.** §4's aggregation table:

> *"| imported by entry-points that **all** pass | inherits the pass, grade `inherited` |"*

§4's provenance rule, same section:

> *"**AND AN INHERITED PASS MUST NAME THE SCENARIO THAT EXERCISED IT.** … **An `inherited` grade
> therefore records which successful scenario exercised the component**, and a library no scenario
> exercised is `none`, not `inherited`."*

§6 pass condition item 5:

> *"an unexercised entry-point is `argued`, never `measured` (§4b)."*

**The failing case, measured not hypothesised.** `scripts/page_markup.py` (438 lines, a listed
component) is imported by `explainer-serve.py`, `gen-dashboard.py`, `gen-goals-page.py`,
`gen-backlog-page.py` and `gen-features-page.py` — and **not** by `brief-compose.py`:

```bash
python3 - <<'PY'   # ast.walk over Import/ImportFrom, local = scripts/*.py stems
brief-compose.py   LOCAL imports: ['page_chrome']
explainer-serve.py LOCAL imports: ['page_chrome', 'page_markup']
gen-dashboard.py   LOCAL imports: ['page_chrome', 'page_markup']
PY
```

§6's experiment covers effort (3) and elects `brief` as the calibration component. Suppose it
exercises the `brief` path and the server, and never runs the dashboard or goals generators — which
§6 item 5 explicitly permits, requiring only that the coverage matrix record it. Then:

- The aggregation rule asks *did its importing entry-points pass?* Those not exercised are `argued`
  (§6 item 5), and an `argued` entry-point is not a *failure*, so the row *"imported by entry-points
  that all pass"* matches → **`inherited`**.
- The provenance rule asks *which successful scenario exercised it?* If the brief path never calls
  into `page_markup`, none did → **`none`**.

**Two rules in the same section give different grades for the same component, and the spec states no
precedence.** The brief asked me to construct the component whose grade is ambiguous; this is one,
and it is a real file, not a constructed one.

⛔ **And the direction of the error is the dangerous one.** The aggregation rule lets a library
inherit `inherited` from a parent whose own grade is only `argued`. `inherited` is defined as *"a
`library`, passing via named entry-point scenarios"* — a stronger claim than `argued` — so the
composition **upgrades evidence as it propagates downward**. That is the laundering §4's own warning
names: *"Without that, `inherited` launders exactly the component most likely to be at fault."* The
rules were written to close laundering through *unexercised branches*; D5 then opened it through
*unexercised entry-points*, and neither section mentions the other.

**Direction.** Make the provenance rule the sole gate and the aggregation rule subordinate to it:
`inherited` requires at least one **named `measured` scenario** that exercised the component; a
library all of whose importers are `argued` is itself `argued`, not `inherited` and not `none`
(`none` overstates — something *was* established about it, by argument). State precedence
explicitly. ⚠ Note that this needs a fifth cell in the grade axis or an explicit rule that a
library may carry `argued`; §4b currently reserves `argued` for *"C1–C3 plus reasoning"* without
saying whether a library may hold it.

---

### H5 — "Mixed inherits the FAILURE" has no implication test, so it reinstates the phantom backlog row that D5 exists to remove — on `page_chrome.py`, the component the role table was added to rescue

**INTRODUCED BY ROUND 2'S FIX** (finding 3). This is the over-refusal the brief asked me to look for,
and it has a measured instance.

**Claim**, §4:

> *"| imported by a **mix** of passing and failing entry-points | **inherits the FAILURE.** A library
> implicated in any entry-point's failure is not carried by the others |"*

Note the asymmetry: the **pass** side must *"name the scenario that exercised it"*; the **failure**
side requires no showing that the library was implicated at all. The row's own prose says
*"implicated"*, and the rule it states does not test implication.

**The failing case, with both halves measured.** `scripts/page_chrome.py` is imported by
`brief-compose.py` **and** by `gen-dashboard.py` (AST scan above). And `gen-dashboard.py` is
guaranteed to fail under §6's isolation, for a reason that has nothing to do with `page_chrome.py`:

```bash
grep -nE '"gh"' scripts/gen-dashboard.py
# 521:        r = subprocess.run(["gh"] + args, cwd=ROOT, capture_output=True,
```

`gh` is an external, **authenticated** prerequisite. §6 mandates a fresh `HOME` with *"its own
`.claude/` config"* and no inherited credentials, so `gh` is unauthenticated by construction in the
experiment. `gen-dashboard.py` therefore degrades or fails; `brief-compose.py` passes. A mix.

By the rule as written, `page_chrome.py` — 450 lines, zero project vocabulary, a self-test, one
shipping-only import — **inherits the FAILURE**. Then §7 item 6 and §4b apply: `NEEDS-WORK` is
*"reserved for a named defect"*, and a row *"means a defect someone can act on"*. What is the named
defect in `page_chrome.py`? *"Imported by a generator that could not reach an authenticated GitHub
CLI"* is not a defect in `page_chrome.py`, and nobody can act on it there.

⛔ **So the fold regenerates, on the very same file, the defect that D5 was decided to eliminate.**
§4b's opening states the problem it exists to fix: *"because §7 files a `docs/backlog.md` row per
`NEEDS-WORK`, a component with no defect generated a filed defect"* — and names
`page_chrome.py` as the instance. Round 1's role table rescued it; round 2's aggregation rule puts it
straight back, through a different door.

**Direction.** Add the missing implication test, symmetric with the provenance rule the pass side
already has: a library inherits a failure only when the failure is **attributed to code in that
library** — the entry-point's failure trace reaches it. A failure attributed elsewhere (a missing
external executable, an absent credential, a defect in the entry-point's own code) leaves the
library's grade determined by its passing importers. ⚠ And `gh` deserves its own line in the
inventory regardless: it is a real detector-6 subject that exists in a listed component, and §4's
C2 vocabulary (`supabase`, `gemini`, `fly`, `youtube-playlist`) does not contain it, so a C2
vocabulary scan scores `gen-dashboard.py` clean on a hard external prerequisite.

---

### H6 — All six detectors look outward from the component. An INBOUND registration dependency is invisible to every one of them, and 5 of 24 components have one

**PRESENT BEFORE; not closed by detector 6.** This is the dependency form the brief asked me to
construct, and it is structural rather than an omission.

**Claim**, §5, the six detectors: (1) project-specific references, (2) invocations of files outside
the shipping set, (3) presence of a self-test and documentation, (4) bare-name references,
(5) prose-declared skill dependencies, (6) runtime prerequisites — *"imports, required executables,
and environment/configuration reads"*.

**Failing case.** Every one of the six examines **what the component references**. A component can
instead require that **something else reference it** — and nothing in the component's own text
records that. The four regen hooks are components under §3's counting rule, and each is completely
inert unless the host's `.claude/settings.json` wires it:

```bash
grep -o '"command": "[^"]*regen[^"]*"' .claude/settings.json
# "command": "bash .claude/hooks/regen-backlog-page.sh"
# "command": "bash .claude/hooks/regen-goals-page.sh"
# "command": "bash .claude/hooks/regen-features-page.sh"
# "command": "bash .claude/hooks/regen-dashboard.sh"
```

A stranger installs the plugin, receives four hook scripts, and gets no page regeneration — with
**every detector reporting clean**, because each script's own references are fine. Detector 6 is the
near miss: it covers *configuration reads*, and the hook does not **read** `settings.json`; it must
be **named in** it. The dependency runs the other way.

Population: the 4 regen hooks plus `.claude/hooks/surface-recall.sh` in effort (1) — **5 of 24
components**, and the spec already notices the symptom for one of them without diagnosing the class:
*"Recall's hook likewise needs the plan-transition mechanism and its hook registration, neither
inventoried nor excluded."* That is filed as a §3 *mapping* gap. It is also a §5 *detector* gap, and
only the mapping half was fixed.

⚠ **And this class is unfalsifiable by §5's falsifier for two of the five.** The falsifier is *a
blocker or degraded result the experiment hits on a component the scan scored clean* — and §6's
experiment covers effort (3) only, so `surface-recall.sh` has no falsifier at all, as §5 itself
concedes for efforts (1) and (2).

**Direction.** Add a seventh detector, or restate detector 6 as bidirectional: for each component,
does it require an entry in host configuration, a hook registration, a `PATH` entry, or a plugin
manifest stanza in order to do anything? The check is cheap — a component with no importer, no
caller, and no registration in the shipping set's own manifest is either orphaned or inbound-wired,
and §4's orphan rule already asks that question for libraries. Extend it to hooks.

---

### H7 — The three required mutations guard only the file-set half. Detectors 3–6 — including detector 6, added as the thing that "breaks a stranger's run first" — carry no mutation at all

**INTRODUCED BY ROUND 2'S FIX.** Findings 4 (identity + three mutations) and 6 (detector 6) were
folded in the same round, into the same section, and neither accounts for the other.

**Claims.** §5's contract: *"It carries the usual contract: `--self-test` with a declared count
verified by running it, a mutation manifest, a caller, and no fail-open handler."* Then, precisely:

> *"**carry three mutations**, each dying via the case it names: one that **empties** a component's
> set, one that **substitutes** a member while preserving cardinality, and one that **omits** a
> dependency and writes the count to match."*

And §7 item 3: *"including the empty-set mutation §5 requires."*

**Failing case.** All three mutations operate on a component's **declared file set**. Detector 1
(vocabulary), 3 (self-test/docs presence), 4 (bare names), 5 (prose-declared skills) and 6 (imports,
executables, config reads) have **no required mutation**, so each can ship inert and the manifest
still passes — which is this repository's most-paid-for defect class, with `check-ratchet-contract.py`
and `check-plan-code.py --mutate .` existing precisely to prevent it.

Detector 6 is the sharpest instance, because §5 argues for it in the strongest terms available —
*"it is exactly what breaks a stranger's run first"* — and gives it no falsifier. **And its import
clause has no positive instance in the corpus to build one from.** Measured across all eleven
scripts of the three efforts:

```bash
python3 - <<'PY'   # ast imports, classified against sys.stdlib_module_names and scripts/*.py stems
--- no third-party imports in: brief-compose.py, explainer-serve.py, page_chrome.py,
    page_markup.py, gen-dashboard.py, gen-goals-page.py, gen-backlog-page.py,
    gen-features-page.py, recall-llm.py, check-surface-recall.py, check-plan-code.py
PY
```

**Zero third-party imports anywhere.** So detector 6's import half cannot be tested against a known
positive drawn from this repo at all; its live subjects are the executables (`gh`, `git`) and the
config reads. A detector whose headline justification has an empty population, and no mutation, is
an assertion in script form — the thing §5's own falsifier paragraph forbids.

**Direction.** Require one mutation per detector, each dying via the case it names, and say so in
§7 item 3 rather than naming only the empty-set mutation. For detector 6 specifically, the known
positive must be **constructed in the self-test fixture** (a fixture component that imports a
package the baseline excludes, and one that invokes `gh`) because the shipped corpus supplies none —
and that construction is itself the evidence that the detector fires.

---

## Medium

### M1 — The corrected decay paragraph attaches the wrong ratio to its own arrow, and the page states it correctly, so spec and page now disagree

**INTRODUCED BY ROUND 2'S FIX.** Third successive correction to this paragraph; wrong a third time,
in a new way, in a paragraph about number provenance.

**Claim**, §3:

> *"The count decayed (**3,599 → 6,525, 1.75x growth**)."*

**Failing case.** That arrow is **1.813x**, not 1.75x. 1.75x is the growth from **3,737** — the
true value at republication — to 6,525. The paragraph pairs the one arrow with the other arrow's
ratio. §3's own table twelve lines above gives `1.81x` for `3,599 → 6,525`, so the document
contradicts itself within one section; line 166 repeats it (*"its subject then grew 1.75x"*,
following a sentence about the 3,599 figure).

The **page gets this right** — *"was accurate within 3.7% on the day it was written — its subject
then grew 1.75×"*, where the antecedent is 3,737. So the artifact and its spec disagree on which
baseline 1.75x measures.

**What I checked.**

```bash
python3 -c "print(6525/3599, 6525/3737)"   # 1.8130  1.7461
grep -n '1.75x\|1.81x' <spec>              # 130:1.81x  146:1.81x  149:1.75x  166:1.75x  650:1.81x
```

**Direction.** Write both ratios with their baselines explicit — *"1.81x against the published
figure, 1.75x against what the figure should have said"* — since the whole point of the three-stage
history is that those are two different numbers. ⚠ The denominator of "3.7%" is also unstated and
the two readings differ (138/3737 = 3.693%, 138/3599 = 3.834%); the tables use the former.

### M2 — The forensic bullet mis-describes the corpus it exists to document

**INTRODUCED BY ROUND 1'S FIX; retained and duplicated by round 2.**

**Claim**, §3:

> *"The first version of this paragraph compared 3,599 against **10,977** — a set of its own
> construction that adds `gen-dashboard.py` and `gen-goals-page.py` (**4,798 lines, 46% of the Python
> total**), neither of which is among the nine."*

**Failing case.** The set described — the nine plus those two generators — totals **11,323**, not
10,977. The actual composition of 10,977 is **the six Python files plus the four skills**
(10,373 + 604), a set which also **drops `explainer-delivery.md` (346 lines)**, one of the nine, and
the other two shared contracts. So the bullet is wrong in both directions about what was measured:
it names the addition and misses the subtraction.

```bash
python3 -c "print(10373+604, 10373+604+630)"        # 10977  11607
# nine + gen-dashboard + gen-goals-page at a3fbb197: 11323
git show a3fbb197:<spec> | sed -n '71,74p'
#   "The Python machinery alone is 10,373 lines across six files, before 604 lines of skills."
```
The original paragraph never wrote 10,977 as a figure at all; it wrote `10,373 … before 604`.
10,977 is round 1's reconstruction, and round 1 mis-stated its membership.

**Direction.** State the set by enumeration, as the paragraph demands of everyone else: *"the six
Python files plus the four skills — a set that adds the two generators and omits the shared
contracts"*. ⚠ A paragraph whose subject is *"a measurement is only as good as its corpus"* is the
one place a corpus description cannot be approximate.

### M3 — A verbatim duplicated bullet, introduced by round 2's fold

**INTRODUCED BY ROUND 2'S FIX.** The M2 bullet appears **twice**, identical, three lines each, at
§3 lines 156–158 and 159–161.

```bash
for c in b748812e 8a19f4ce bea19c78 5fa1155f; do
  git show $c:<spec> | grep -c 'The first version of this paragraph compared'; done
#   1  1  2  2
git log --oneline -S'The first version of this paragraph compared' -- <spec>
#   bea19c78 (the r2 fold)   b748812e (the r1 fold)
```
Introduced by `bea19c78`, the round-2 fold, and surviving `5fa1155f`. **Direction:** delete one.
A duplicated paragraph is weak evidence on its own; it matters here as the simplest visible instance
of the fold mechanism behind the fourteen — an edit applied to a copy of a passage rather than to the
passage.

### M4 — D5's stated falsifier is unobservable, while a checkable one sits in the same section unused

**INTRODUCED BY ROUND 2'S FIX** (D5 was settled and folded during round 2).

**Claim**, §4b:

> *"**That is this decision's falsifier:** if the inventory is read and acted on as though `argued`
> meant `measured`, the two-axis scheme has failed"*

**Failing case.** Nothing can witness that. "Read and acted on as though" is a claim about a
reader's cognition; no artifact records how the inventory was read, and the spec names no instrument,
no log and no later check. Under this project's own gate rule — *state the observation that would
make it FAIL* — this is a decision wearing a falsifier, not a falsifiable decision.

A **checkable** falsifier exists eight lines above and is not the one nominated: *"A verdict without
a grade is an incomplete row, and deliverable 5 is not done until every row has one"*, plus §4b's
rendering requirement (*grade beside the verdict, never in a footnote*). Both are mechanically
decidable against the produced inventory.

**Direction.** Nominate the decidable one as the falsifier — *every `SHIP` row carries a grade, in
the same visual unit as the verdict, and every `inherited` grade names a scenario* — and keep the
mis-skim risk as a **stated cost**, which is what §4b's preceding sentence already does well. ⚠ The
distinction matters because a gate with an unobservable falsifier reports success forever.

### M5 — The `data` role has no determinable grade, so a listed component cannot satisfy §4b's own completeness rule

**INTRODUCED BY ROUND 2'S FIX** — the composition of round 1's role table with D5's grade axis.

**Claims.** §4's role table: *"| `data` | supplies content (e.g. the memory corpus) | not applicable;
C4 is recorded as `n/a` |"*. §4b: *"**Every component in the inventory carries both fields.** A
verdict without a grade is an incomplete row, and deliverable 5 is not done until every row has
one."* The grade axis offers exactly four values: `measured`, `inherited`, `argued`, `none`.

**Failing case.** The memory corpus is a listed component of effort (1) (157 files). Its C4 is
`n/a`. Which of the four grades does it carry? `n/a` is not among them. `none` means *"nothing was
established"* — false and actively misleading, since what happened is that the criterion does not
apply, not that evidence is absent. `argued` means *"C1–C3 plus reasoning"*, which presumes C4 was
reasoned about. So the row is either incomplete (violating §4b) or mislabelled in a direction that
reads as a failure.

The brief asked whether every component in §3 gets a determinable grade. **It does not: the `data`
role cannot.** This is the one component class where the two axes were never crossed.

**Direction.** Either admit `n/a` as a fifth grade restricted to `data` components, or state that a
`data` component's grade is scoped to the criteria that apply to it (C1–C3) with C4 struck rather
than graded. Say which in §4b, where the completeness rule lives.

### M6 — §6's hollow-page worked example overstates its own case

**INTRODUCED BY ROUND 1'S FIX; retained by round 2.**

**Claim**, §6:

> *"In a repo with no `scripts/check-*`, **all nine** of `brief`'s ground-truth items return nothing.
> … a page carrying no roadmap, no backlog, no ratchet results and **no git reasoning**: `brief`'s
> entire content."*

**Failing case.** Two overstatements, both measured:

- The nine are *4 bare guard names, 4 document paths, 1 tool name* (§4, verified below). The tool
  name is **`TaskList`** — a harness tool, present in any Claude Code session, not a repo artifact.
  It does not "return nothing" in a stranger's repo; its capability is intact. So 8 of 9 at best.
- `brief`'s step 1 opens with **five `git` commands** (`git log --oneline -15`, `git status --short`,
  `git branch --show-current`, `git rev-list --count …`, `git diff --stat …`). These run in any git
  repository, and the skill states that *"git log messages … in this repo carry the reasoning"*. In
  the **seeded** repository §6 now mandates, they return the seeded facts. "No git reasoning" is
  wrong by construction of §6's own replacement design.

**What I checked**, with the known positive first:

```bash
grep -c 'check-' .agents/skills/brief/SKILL.md          # 4   <- known positive
grep -c 'scripts/check-' .agents/skills/brief/SKILL.md  # 0   <- so the zero is real
grep -n 'check-docs\|check-producer-enumeration\|check-roadmap-consistency\|check-test-counts\|TaskList' \
  .agents/skills/brief/SKILL.md     # 55: TaskList, 62: all four guard names, 66: one repeat
sed -n '40,60p' .agents/skills/brief/SKILL.md           # step 1: five git commands, then the four docs
```
`brief/SKILL.md:42` is indeed *"Run these; do not skip any. Report the ones that returned nothing."*,
exactly as §6 cites it.

**Direction.** Correct the example to what it supports — *the eight repo-specific items return
nothing; the git half and the task-list tool still work, so the page is hollow in its judgement
layer and populated in its mechanical one* — which if anything **sharpens** the argument, because a
partially-populated page is more likely to pass a human skim than an empty one. ⚠ As written, the
paragraph is a correct conclusion resting on an overstated premise, inside the section that exists
because a premise was overstated.

### M7 — Detector 6 has a measured false positive and no required/optional rule, repeating the positional-matching defect detector 1 was just repaired for

**INTRODUCED BY ROUND 2'S FIX.**

**Claim**, §5: *"Detector 6 covers imports, required executables, and environment/configuration
reads."* Note that *required* qualifies only *executables*; the config clause is unqualified. §5's
neighbouring rule for fixtures is explicitly behavioural — *"Fixtures are exempted by BEHAVIOUR, not
positionally"* — and detector 6 gets no equivalent.

**Failing case — the false positive the brief asked for.** `scripts/explainer-serve.py:543`:

```python
v = os.environ.get(SRC_ROOT_ENV, "").strip()      # SRC_ROOT_ENV = "EXPLAINER_DOCS_ROOT" (:279)
```

An **optional** override with a default. Detector 6 as specified reports a configuration read, i.e.
a runtime prerequisite, on the suite's principal entry-point — for a variable a stranger never needs
to set. Precisely:

```bash
python3 - <<'PY'   # ast: environ.get/getenv arity, environ[...] subscripts
explainer-serve.py: get/getenv WITH default = 1, WITHOUT default = 2, environ[...] = 4
env var names referenced: ['HOME', SRC_ROOT_ENV]
PY
```

One genuine false positive (`EXPLAINER_DOCS_ROOT`, defaulted) and one true positive (`HOME`, which
§6 controls deliberately). So the detector's precision on its own config clause is 1-in-2 on the
only component where it has subjects.

**Direction.** Give detector 6 the behavioural rule detector 1 now has: a configuration read is a
prerequisite only when the component **fails or degrades** without it — i.e. no default, or a
default that leads to an error path. Report defaulted reads as mention candidates. ⚠ I did not
classify all four `environ[...]` subscripts; several are plainly self-test setup, which is itself an
instance of the fixture-versus-dependency question one detector over.

### M8 — "A mention candidate never alone decides a verdict" is advice, and the spec presents it as a rule

**INTRODUCED BY ROUND 2'S FIX** (finding 6).

**Claim**, §5: *"Mention candidates are **reported separately** from dependency findings and never
alone decide a verdict."*

**Failing case.** The scan **reports**; the verdict is written by a person into deliverable 5. The
first half is enforceable (the script can emit two lists, and a mutation can prove it does). The
second half constrains the human author of the inventory, and nothing observes it: no artifact
records *which* reported lines a verdict rested on. A verdict of `DON'T-SHIP` justified entirely by
mention candidates is indistinguishable, in the produced inventory, from one justified by
dependencies.

**Direction.** Make it checkable or label it as guidance. The cheap mechanical version: require each
non-`SHIP` verdict to cite the dependency finding ids it rests on, and have the scan refuse to
emit a dependency-finding id for a mention candidate. Then "never alone decides a verdict" has a
falsifier — a verdict citing only mention ids — instead of relying on the author's discipline.

### M9 — F18's severity premise was never established by anyone: all four regen hooks are invoked as `bash <path>`, so the mode difference breaks nothing

**PRESENT BEFORE.** Three parties have now examined this finding and none asked what fails.

**History, all of it verified by me.** Round 1 filed F18 as *"`regen-features-page.sh` is not
executable, unlike its three siblings"*. Round 2 checked that file at three commits, found `100755`,
and directed **withdrawal**. The coordinator checked the *claim* rather than the *file*, found
`regen-dashboard.sh` at `100644`, and ruled *"the finding stands; only its subject was wrong"*.

**The coordinator is right about the mode, and I confirm it at four commits:**

```bash
for c in a3fbb197 b748812e 8a19f4ce bea19c78; do git ls-tree $c .claude/hooks/ | grep regen; done
#   100755 regen-backlog-page.sh   100644 regen-dashboard.sh
#   100755 regen-features-page.sh  100755 regen-goals-page.sh      <- identical at all four
```

**The failing case is one level further out.** Nobody asked what the executable bit does here:

```bash
grep -o '"command": "[^"]*regen[^"]*"' .claude/settings.json
#   all four are:  "command": "bash .claude/hooks/regen-<name>.sh"
```

All four are invoked **through `bash`**, which does not consult the execute bit. So the mode
difference is a cosmetic inconsistency with **no failing observation** — and r1's F18, r2's
withdrawal direction, and the coordinator's reinstatement all turn on a premise none of the three
tested.

⛔ **And this reproduces §4b's own founding defect one level up.** D5 exists because *"a component
with no defect generated a filed defect"*. F18 is a filed defect, mandated for the inventory to
carry (*"a finding the inventory must carry"*), against a component with no functional defect. The
general fix did not reach the specific instance already on the record.

**Direction.** Keep it as what it is — an **inconsistency** worth normalising, not a defect worth a
row — and record the observation that would make it a defect (*any hook invoked directly rather than
through `bash`*), which is currently false for all four. ⚠ Severity here is deliberately Medium
rather than Low: the error is not the mode, it is that a finding reached its third review without
anyone stating its falsifier, and the inventory is instructed to carry it.

### M10 — Nobody has asked whether the code may be redistributed. There is no LICENSE file, and the spec mentions licensing zero times, under D1's public-stranger bar

**PRESENT BEFORE.** This is the defect class the brief asked for — the next one of round 2's
*"nobody had looked"* shape. Round 2 opened exactly this question for the **memory corpus** and the
coordinator promoted it onto the page; **the code's own licence was never asked by any half.**

**Claim.** D1: *"**Audience: public strangers, full support bar.** Works in any repo, documented for
a newcomer, failure modes handled without the author"*, and D3 ships via a self-published
marketplace repo. §4's release criteria are C1–C4: measured, project-independent, self-contained,
supportable.

**Failing case.** None of C1–C4 asks whether the project has the right to distribute the artifact,
or grants a stranger the right to use it. Measured:

```bash
ls LICENSE* COPYING*                        # no such file
grep -ci 'licen' <spec>                     # 0
grep -rli 'license' package.json README.md .claude-plugin/   # no hits
```

Published with no licence, the suite reaches strangers under default exclusive copyright: they may
install it and have no granted right to use, modify or redistribute it. For a milestone whose
deliverable is *"can a stranger use this?"*, that is a release criterion, and it is absent from the
criteria list, the risk table and the falsifiers.

⚠ **Bounded honestly, because the adjacent claim would be wrong.** I checked whether the
marketplace mechanism requires licence metadata, and it does not:

```bash
python3 -c "...json.load each ~/.claude/plugins/marketplaces/*/.claude-plugin/marketplace.json..."
#   openai-codex          plugin[0] keys: name description version author source        license: False
#   omc                   plugin[0] keys: name description version author source category homepage tags
#   claude-plugins-official  plugin[0] keys: name description author category source homepage
```
None of the three installed marketplaces carries a `license` key, so this is **not** a packaging
blocker and I make no claim that `marketplace.json` needs one. The gap is in the spec's criteria,
not in the route.

**Direction.** Add a fifth criterion or an explicit release gate — *may this be redistributed, and
under what grant?* — covering the code **and** the corpus round 2 raised, since they have different
answers: the code needs a licence chosen by the owner, the corpus needs a content review. ⚠ Both are
owner decisions, not engineering, so they belong at this Phase 1 gate rather than in PR 1.

---

## Low

### L1 — F18's corrected form has no durable home in the deliverables

**PRESENT BEFORE.** Round 1 wrote *"It is therefore a finding the inventory must carry, and if the
inventory does not mention it, that is a defect in the inventory."* The coordinator agreed, *"now
with the right filename"*. But §7 item 5 enumerates what the inventory contains — role, verdict,
evidence — and says nothing about carrying deferred review findings; the spec mentions
`regen-dashboard`, `100644`, `executable` and `chmod` **zero times**.

```bash
grep -n 'regen-dashboard\|100644\|chmod' <spec>     # no hits for the hook or the mode
grep -n 'regen-dashboard' docs/features.md docs/dashboard-entries.md
#   dashboard-entries.md:15217  (the round-2 narrative entry)
```
Its only durable record is a round-2 narrative row in `dashboard-entries.md` — a record *of the
review*, not an input *to the inventory*. **Direction:** add the deferred findings to §7 item 5's
contents, or drop the claim that the inventory must carry them. An obligation with no deliverable is
the same shape as H1 and H2, at Low cost.

### L2 — Method: the subject moved mid-review

Recorded as a finding because it bears on how this document should be read, not on the spec. See the
banner at the top. `5fa1155f` landed during the review; every finding was re-verified at it. ⛔ The
project's own rule — *a live agent's file is not static* — applies to review subjects too: a half
dispatched against a named commit should be reviewing a worktree nobody else writes to, or should be
told the subject will advance.

---

## What I checked and could NOT fault

Recorded because it is how a thorough round is told from a shallow one, and because several of these
were the obvious places to look for a defect.

- **The three-stage history of the 3,599 figure is correct, and this is the first version of it that
  is.** I re-derived all of it. All nine files resolve at **identical paths** at all three commits,
  so *"the same nine files"* is the same nine; membership is unchanged.
  ```bash
  git log --all --format='%h %ad %s' --date=short -S'3,599' -- docs/backlog.md docs/portable-practices.md
  #   100cf498 2026-09-07 · 87ea0001 2026-09-03 · cacbac17 2026-09-03
  git show cacbac17^:docs/backlog.md | grep -c '3,599'   # 0  <- cacbac17 introduced it
  python3 - <<'PY'   # len(bytes.splitlines()) over the nine, per commit
  cacbac17 TOTAL 3599   100cf498 TOTAL 3737   HEAD TOTAL 6525
  PY
  ```
  **3,599 exactly** at `cacbac17`, **3,737** at `100cf498`, **6,525** today. 6525/3599 = **1.813**.
  ⚠ One detail neither round mentions and which does not change the conclusion: a **third** commit,
  `87ea0001` (2026-09-03, four hours after `cacbac17` and not its descendant), also matches the `-S`
  search — a parallel branch carrying an older draft of row 89 (*"Group B, hook-regenerated (3)"*
  against `cacbac17`'s four). `cacbac17` is still where the figure originated, since its parent has
  zero occurrences.
- **`10,373 + 604 + 630 = 11,607` reproduces exactly**, and the six per-file Python counts in §3's
  table are each exact at HEAD.
- **The F18 subject correction is right.** `regen-dashboard.sh` is `100644` and
  `regen-features-page.sh` is `100755` at all four branch commits, with the coordinator's reading of
  the claim-versus-file error correct. My M9 extends it rather than refuting it.
- **The `scripts/check-*` refutation holds, with a known positive.** `check-` → 4 in
  `brief/SKILL.md`, `scripts/check-` → 0. The nine items are where §4 says: four bare guard names on
  one line (`:62`), four document paths and `TaskList` in step 1, and `brief/SKILL.md:42` is the
  cited "report the ones that returned nothing" line.
- **The symlink/B3 machinery's premise holds.** §3's table now names `.agents/skills/shared/`, the
  real directory, so the measured failure cannot be reached from §3 as written — as §5 claims.
- **Imports are genuinely clean.** AST scan over all eleven scripts: local imports confined to
  `page_chrome` and `page_markup`, both listed components; no third-party imports anywhere. The
  dependency graph §4's inheritance rules operate over is real and small.
- **D3's "proven on this machine" holds.** All three installed marketplaces parse and carry
  `.claude-plugin/marketplace.json`, including the third-party `omc`. §2's careful separation of
  *the route exists* from *this artifact can travel it* survives — and §7 item 0 plus §9's third
  falsifier do discharge it, which is a clean fix.
- **`gen-dashboard.py`'s `gh` wrapper is well built**, and I went looking for a silent-failure
  defect and did not find one: `_gh_json` returns `(None, error)` and its docstring states the rule
  explicitly — *"Never a bare [] on failure — 'nothing' and 'could not ask' must not look alike."*
  ⚠ It is the quality of this code that generates H5, not a defect in it.
- **`5fa1155f`'s own self-audit is correct.** I verified all three sites it claims to have fixed:
  §2's *"at least 24 components"*, §3's *"THE ARITHMETIC IS UNCHANGED AT 24 … 24 is a floor"*, and
  the page's opening *"at least 24"*. The §7 item 6 extension to cover `argued` is also correct and
  closes a real gap. ⚠ It did not close any of the 21 findings above; I checked each at both commits.
- **The local-versus-published marketplace distinction** (r1 H2/CODEX 7) holds in both directions —
  §6, §7 item 0 and §10 now agree, and §10 carries the explicit "⚠ *not* the throwaway local
  marketplace" clause.
- **D5's reasoning for rejecting a fourth verdict is sound** and I tried to break it. The argument
  that `CANNOT-ASSESS` re-opens the escape hatch *and* still cannot separate *proved it* from
  *argued it* is correct; the two-axis scheme is the right shape. My findings M4 and M5 are about its
  edges, not its design.

---

## NOT VERIFIED — with the reason, because an inference stated as a measurement is itself a failure here

- **No scanner, packaging spike, seeded repository or install experiment exists.** Every finding
  against §§5–7 tests the **written contract** by constructing a case, not by executing anything.
  H3's zero-recovery-documentation finding and H6's registration finding are measured against the
  shipped files; the detector findings are specification counterexamples.
- **I did not execute the page in a browser.** B1 and B2 are from the committed source of both
  `.html` and `.fragment.html` and a detagged text extraction. I did not test the Ask channel, and I
  cannot confirm or deny the coordinator's report that both reader questions round-tripped, nor its
  claim that `5fa1155f` left *"zero residual asterisk pairs"* — I did not check the markdown-bold
  sweep at all.
- **I did not run `recall-llm.py --self-test`, the mutation harness, or any guard.** The 201/96
  figures and the recall measurements are taken from prior rounds' records, not re-derived. The
  recall inversion table (3/20, 20/20, 19/20, 5.0% bound) I did **not** re-derive from
  `dashboard-entries.md`.
- **I did not assess the memory corpus's contents.** M10 is about the absence of a licence and of a
  redistribution criterion. I make **no claim** about whether private content or credentials are
  present in the 157 files — that remains, as round 2 said, an unexamined criterion.
- **I did not observe `gen-dashboard.py` degrading under an unauthenticated `gh`.** H5's failure
  half is read from `_gh_json`'s code and from §6's isolation requirements; that `gh` will be
  unauthenticated under a fresh `HOME` is an inference from §6's text, not a measurement.
- **I did not classify all four `os.environ[...]` subscripts** in `explainer-serve.py` (M7); several
  are visibly self-test setup.
- **The `87ea0001` commit's role** I established only far enough to confirm it does not displace
  `cacbac17` as the figure's origin. I did not work out why a parallel branch carried an older draft.

---

## ⛔ Thrashing or prose floor? — the answer this round is required to supply

The trigger is **two consecutive rounds whose findings came from the previous round's fix, in one
component.** Round 2 was the first, at 4 of 10. This is the second, at **14 of 21**, in the same
component. **The architecture review fires.** My answer, with per-finding evidence, is that this is
**neither thrashing nor a prose floor** — and the distinction matters, because the two have opposite
remedies and the correct one is cheap.

**It is not a prose floor.** A prose floor produces findings that are refinements of each other, and
a redesign cannot remove them. These are not that. Thirteen of the fourteen share **one mechanism**,
and it is already named in this branch's own record — the coordinator wrote it against itself after
round 2: *"I folded the spec thoroughly and the page partially — so the fix created a contradiction
between two artifacts that neither artifact contained before."*

**The mechanism is that a rule is stated in more than one place, and the fold updates the site the
finding named.** Per finding:

| Finding | A claim stated at two sites | The site the fold updated | The site it did not |
|---|---|---|---|
| B1 (a)–(d) | D5, inheritance, the no-unknown rule, the figure's history | the spec | the page |
| B2 | the spec's length and commit | the spec (it grew) | the page's state block |
| H1 | who derives and validates the declaration | §5 (asserts it) | §7 item 2 (contains it) |
| H2 | baseline and capture mechanism | §6 (requires them) | §7 (produces them) |
| H4 | how a library's grade is determined | §4's aggregation row | §4's provenance rule, and §4b |
| H5 | when a library is implicated | §4's failure row | §4b's named-defect rule, §7 item 6 |
| H7 | what the mutations must cover | the three file-set mutations | detectors 3–6, §7 item 3 |
| M1 | the decay ratio | §3's table (1.81x) | §3's prose (1.75x), which the page gets right |
| M3 | the forensic bullet | — | it was duplicated rather than edited |
| M4, M5, M8 | grade completeness, `data`, mention candidates | §4b / §5's new rules | the rules they must compose with |

**That is not a document at its floor; it is a document with redundant statements of its own rules.**
The remedy is this project's own `one-rule-one-place`: each rule stated once, every other site a
cross-reference. The spec currently restates its rules across §§3, 4, 4b, 5, 6, 7 and 9, plus two
page artifacts, and `check-docs.py` enforces a line budget on `dev-process.md` for exactly this
reason. **A redesign removes the class**, which is the test the method doc sets — so the arming
condition is satisfied and the finding is actionable rather than terminal.

**It is also not classic thrashing**, because the fixes are not oscillating: no finding below
reverses an earlier fix, and the substance of each round's repairs has held. The three-stage history
is right on its third attempt. The role table, D5, the seeded repository, detector 6, the identity
comparison and the packaging spike are all genuine improvements that survive attack. What has not
held is **propagation**.

⛔ **So the architecture review's subject should be the document's structure, not the marketplace
method.** The question to put to it is the one `dev-process.md` Phase 6 asks: *what did we decide
this milestone that isn't written down?* — and the answer visible from here is that nobody has
decided **where each rule lives**, which is why four rounds of folds have each updated a subset of
the sites that state it. Two concrete follow-ons, both cheap:

1. **A fold checklist, mechanical:** for each folded finding, list every site stating the claim
   (`grep` the claim's distinctive tokens across the spec *and* both page artifacts) and show each
   updated. H1, H2, M1 and all of B1 die to this.
2. **A page-derives-from-spec rule.** The page's provenance block and its rule statements should be
   generated or checked against the spec, not re-authored. B2 has now been filed, fixed and recurred
   within two rounds, which is the signature of an authoring convention standing in for a
   compose-time check.

⚠ **One thing I want to say plainly, because the attribution table reads worse than the branch is.**
Fourteen fix-induced findings is a bad ratio and the trigger should fire on it. But the spec is also
**much** better than it was two rounds ago: round 1 found four Blocking defects in a 213-line
document that had shipped with no review at all, and the four are genuinely closed. The failure now
is not in the thinking; it is that a 669-line document states each of its rules three times and the
folds have been editing one copy. That is a structural problem with a known, cheap fix — and it is
worth fixing before the human gate, because B1 and B2 mean the artifact the owner is being asked to
approve currently disagrees with the document it is approving.

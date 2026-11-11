<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED

Reviewed `ae581e1f83ce28900060c4540c9ff5a286fe1b70`. **The spec still asserts a false measured result and is not fit for approval as the Phase 1 human gate.** No repository files were changed.

References below:

- **S:** `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md`
- **P:** `docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html`
- **H:** its `.html` sibling
- **G:** `scripts/check-claim-propagation.py`

### B1 — Blocking: the newly “measured” wrong-neighbour execution does not happen

**Sites:** S §6, finding 2, approximately lines 793–796; P line 813 and the corresponding H table; commit `e4249da9`.

**Claim:** Both third-party repositories have `scripts/`, so the three delivery invocations “silently run the wrong neighbour’s file.”

**Refutation:** Neither repository contains either target filename. The three invocations comprise one `brief-compose.py` invocation and two `explainer-serve.py` invocations. A directory existing does not make its absent children executable.

I inspected both installed repositories and ran:

```text
python3 scripts/brief-compose.py --help
python3 scripts/explainer-serve.py --help
```

from each repository. **All four returned exit 2 with “can’t open file … [Errno 2] No such file or directory.”**

The inspected revisions were:

- `omc`: `679b418f32409e6d0edecf5038fd2de460cfce04`
- `openai-codex`: `807e03ac9d5aa23bc395fdec8c3767500a86b3cf`

**Sibling search:** Read `e4249da9`, `99667119`, the delivery contract’s three commands, and both walkthrough sources. The false result propagates into the unique-name comparison and the description of the known remedy. Wrong-neighbour execution is a possible failure class; it was not measured here.

### B2 — Blocking: the spec describes retired index text as the index’s current assertion

**Sites:** S §3, lines 134–175 and 187–190; P lines 325–334; S §7 item 8/D8.

**Claim:** `portable-practices.md` currently describes the suite as “9 files / 3,599 lines,” still prints that figure as its count, registers ten anchors, and says a second anchor is owed.

**Refutation:** Reading the current `docs/portable-practices.md`, lines 13–36, shows:

- its current headline is **“~11,000 lines”**;
- “9 files / 3,599 lines” appears inside an explicitly dated correction;
- it reports **13** current anchors, with the fourteenth allocated on this branch;
- it explicitly says the second anchor now exists and strikes the old assertion.

That index still contains errors worth repairing, including the cross-corpus “roughly 3x” correction and “concentrated in one file.” But those are different current defects from the three current assertions this spec says it discovered.

**Checked:** Read the index against every matching figure and anchor assertion in S and P. The historical arithmetic reproduces; the claimed present state does not. D8 needs to identify the actual remaining corrections before promising their delivery.

### H1 — High: deleting a registered document produces a successful audit

**Sites:** G lines 329–341, 353–354, 373–376 and the derived-check missing-path branch.

**Claim:** Live claims reach every registered site; unavailable evidence cannot pass.

**Refutation:** I ran `audit()` against an in-memory filesystem containing the unchanged real spec but no fragment. It returned:

```text
problems: []
note: registered path absent, not audited: …walkthrough.fragment.html
```

`main()` therefore takes its success path. Deleting the page removes it from both the live-claim denominator and the derived-figure check.

**Sibling search:** Examined all missing-path branches. Complete absence raises `CannotRun`; partial absence is explicitly skipped. The empty-tree self-test does not cover this bypass.

### H2 — High: all 31 cases pass with partial propagation detection disabled

**Sites:** G lines 377–382; fixture construction at 537–580; `scripts/mutations/check-claim-propagation.json`.

**Claim:** The guard mechanically refuses a fold updating only some sites, with mutation-tested coverage.

**Refutation:** In memory, I replaced:

```python
if absent and len(absent) < len(auditable):
```

with:

```python
if False:
```

The result remained **31/31 self-test cases passed**.

The purported live-claim test removes `LIVE[0]`, which is registered only at S. It tests **absent everywhere**, not **present at one required site and absent at another**. `page_for()` supplies every page token in the positive fixtures; the remaining negative page fixtures assert unrelated derived-figure errors.

**Sibling search:** Inspected all ten manifest entries and executed each mutation in memory. All ten kill their named cases, but **none targets partial propagation**. The fixture repair restores a green control without proving the guard’s central distinguishing behavior.

### H3 — High: the served walkthrough is outside the audited population

**Sites:** G lines 68–70, registry `sites`, `DERIVED`, and lines 329–330.

**Claim:** The guard protects the reader-facing walkthrough from disagreement with the spec.

**Refutation:** `PAGE_HTML` is defined and written by the synthetic fixture, but never enters the audited path set. I supplied the unchanged S and P alongside an H containing `213-line spec`. `audit()` returned no problems.

**Sibling search:** Searched G and CI registrations for `PAGE_HTML` and fragment handling. CI runs this guard, but this guard never reads H. No independent fragment-to-served-page equivalence check was established.

### H4 — High: adding ordinary inline markup hides a registered retired claim

**Sites:** G `_html_occurrences()`, lines 280–292.

**Claim:** Registered retired assertions are refused in HTML.

**Refutation:** Direct calls returned:

```text
<p>A library inherits its support verdict from the entry-points.</p>
→ (asserted=1, quoted=0)

<p>A library inherits its <em>support verdict</em> from the entry-points.</p>
→ (asserted=0, quoted=0)
```

These render the same words. Detection operates on individual text nodes, so a formatting edit makes the assertion disappear.

**Sibling search:** Inspected live and retired matching. Live matching has the corresponding raw-substring sensitivity to markup and wrapping. This example is not an unregistered paraphrase; it is the registered wording with emphasis.

### M1 — Medium: D9’s stated falsifier does not cover D9’s promise, and cannot gate PR 1

**Sites:** S §4d, lines 524–558; §9’s D9 bullet; P lines 943–994.

**Claim:** Tags and changelog entries are the “whole promise”; C4 is graded against D9; D9 is a gate.

**Refutation by constructed cases:**

1. Release `1.2.0` has a tag and changelog but introduces a breaking change. D9’s table requires a major bump; its stated failing observations do not fire.
2. A package has compliant versioning but recovery instructions say “contact the author.” It passes D9’s release observations and fails C4.
3. A package has working independent recovery but no version tag. It passes the artifact’s C4 requirement and fails D9.

Thus **best-effort response timing does not inherently weaken C4**—independent recovery remains gradeable—but D9 cannot serve as C4’s grading predicate.

Furthermore, §10 excludes every release artifact needed to observe D9’s falsifier. **Within PR 1, D9 is a deferred publication requirement, not an executable milestone gate.** The scope bound acknowledges this; the gate language does not.

**Sibling search:** Compared the criterion row, §4d, §9, §10 and both page occurrences. The incomplete “whole promise” assertion appears in both documents.

### M2 — Medium: the repaired data-role rule excludes the criterion introduced specifically for the corpus

**Sites:** S §4 role table, line 312; C5 discussion, lines 253–295; §4b completeness rule.

**Claim:** A `data` component is graded against **“C1–C3 only”**, with C4 struck.

**Refutation:** Construct a memory corpus that passes C1–C3 but contains material that cannot be redistributed. The role row permits evaluation without C5; the C5 rule vetoes `SHIP` until its content review passes.

The exemption should strike C4 while retaining C5. It currently excludes both.

**Sibling search:** Compared the role table, C5’s corpus-specific requirement, D5 and effort-(1) bounds. “C1–C3 plus argument” also survives at other sites without explaining C5’s mandatory evidence.

### M3 — Medium: the inheritance repair still leaves a reachable population without an aggregation rule

**Sites:** S §4 inheritance table, approximately lines 324–330; named-scenario requirement immediately below it.

**Claim:** The table supplies aggregation, coverage and provenance rules.

**Refutation:** Construct a library imported by two measured entry-points that both fail:

- one fails inside the library;
- the other fails before reaching it.

The table covers all passing, mixed passing/failing, only argued, no importer and cycles. It does **not** cover all failing. Meanwhile, `inherited` is defined through successful named scenarios, which this population has none of.

The inventory can reasonably record a measured attributed failure, but the contract does not define that aggregation. Applying the successful-scenario requirement literally can instead produce `none` despite measured fault evidence.

**Checked:** Read the complete table against D5’s four grades and constructed the case above. This is a written-contract counterexample, not an executed install experiment.

### M4 — Medium: detector 7’s proposed predicate does not establish registration completeness

**Sites:** S §5 detector 7, lines 582–588.

**Claim:** Inbound registration is checked cheaply by requiring a registration declaration for a component with no importer and no invoker.

**Refutation:**

- **False negative:** A hook is invoked by its self-test or another script but lacks its production hook registration. It has an invoker, so the stated predicate does not demand the missing registration.
- **False positive:** A documented standalone CLI has no repository importer or invoker because its caller is the user. It need not require host registration.

Invocation existence and required registration are separate properties.

**Sibling search:** Compared detectors 2, 6 and 7 and the existing hook-registration example. No production-versus-test invoker qualification or registration applicability rule resolves these cases.

### M5 — Medium: the walkthrough still asserts superseded fixes beside their replacements

**Sites:** P lines 503–510, 590, 598 and 931–935; corresponding H sections.

**Claims still presented as current:**

- the code licence remains a choice for the owner;
- there are **six** detectors;
- the experiment requires “one recovery scenario”;
- the spec does not price any ongoing support obligation.

**Refutation:** S and later page sections respectively say MIT is settled, add detector 7, make recovery conditional because none is documented, and record D9’s support policy.

I read these sites against their replacements. They are not consistently marked as retired assertions. The guard remains green because its tokens require presence somewhere, rather than agreement at every substantive restatement.

**Sibling search:** Searched both HTML sources for licence, detector, recovery and support assertions. Both carry the same contradictions. Appending the retired claim “The missing licence blocks approval of this milestone” to P also produced no guard problems: **D7 registers live `MIT`, but does not register the retired blocking claim.**

### M6 — Medium: §7 restores the exhaustive resource requirement §6 explicitly retired

**Sites:** S §6 capture-mechanism paragraph, lines 723–727; §7 item 4, lines 852–853.

**Claim:** §6 permits a capture mechanism with explicit observational limits. §7 nevertheless requires a record of **“every resource the run touched.”**

**Refutation:** Select the expressly permitted mechanism that has declared unobservable accesses. Its record satisfies §6, but cannot establish §7’s exhaustive requirement.

**Checked:** Compared the two clauses and the baseline-producing item 0b. The producer exists now; the remaining defect is incompatible acceptance criteria, not its previous absence.

**Sibling search:** Searched S and P for baseline, capture and resource-record requirements. P follows the bounded §6 formulation.

### what I checked and could not refute

- **Historical counts and arithmetic:** Re-enumerated the same nine files with `git show`, using historical `.claude/skills/` paths where applicable. Totals reproduce as **3,599**, **3,737**, **6,525**. Ratios are **1.8130**, **1.7461**; `138/3737 × 100 = 3.6928%`. The spec/page arithmetic agrees. **Falsifier:** different same-set totals or incorrectly associated denominators. B2 concerns the current index assertion, not this arithmetic.

- **The old guard’s five failures:** Executed the exact `2bca9fe5` source in memory, equivalently to the requested temporary-file invocation. It reports **5 of 31 failed**, for the stated clean-page-fixture reason. Current committed self-tests report **31/31**, and the real-tree audit passes. **Falsifier:** the old source passing or failures attributable to a different cause.

- **Ten scoped mutations:** Applied all ten manifest edits individually in memory and ran each resulting self-test. **All ten fail every named expected case.** No further case-name mismatch was found. **Falsifier:** a surviving mutation or missing named failure. **UNVERIFIED:** the full harness sweep was deliberately not run. The scoped result does not establish the whole-manifest ratchet, unrelated controls or integration checks.

- **Masked-fixture sweep:** The repaired HTML glyph fixture has one marker. The Markdown quotation fixture still has both `⟳` and `SUPERSEDED`; its separate glyph-only case protects glyph behavior. Removing each retirement marker individually leaves ten removals green; only removing `⟳` reddens the suite. There are **11 markers in this commit**, not twelve. **Falsifier:** dedicated coverage reddening for those other removals. This establishes coverage limits, not ten demonstrated production defects.

- **Plugin-root spelling and existing usage:** Read `omc/hooks/hooks.json` and `openai-codex/plugins/codex/hooks/hooks.json`. Both use **`CLAUDE_PLUGIN_ROOT`** and retain package `scripts/` directories. **Falsifier:** different spelling, absent references or paths still rooted in CWD. **UNVERIFIED:** runtime substitution in this suite’s future skill packaging; no isolated package exists, and hook examples alone do not execute that integration.

- **D6’s independent harvest field:** I could not construct a contradiction from `DON’T-SHIP / argued / harvest: practice` when the named measured practice entry exists. Evidence for a transferable practice need not prove installability. **Falsifier:** any rule upgrading the shipping verdict because of harvest, or granting `practice` without its required entry. None was found.

- **Detector contracts 1–6:** Read their triggers and negative boundaries. Their specified positive/negative examples are respectively: project-service action/harmless literal; outside-set invocation/packaged resolved invocation; missing/present tests and documentation; required bare capability/historical mention; required skill load/incidental mention; absent runtime prerequisite/working optional default. **Falsifier:** these pairs receiving indistinguishable treatment. **UNVERIFIED:** actual detector behavior—`check-publishability.py` has not been built. Detector 7 has the contract counterexamples in M4.

- **Baseline and oracle independence:** Item 0b now explicitly produces a baseline before the spike. Item 2 forbids deriving the shipping declaration from scanner output and requires a separate closure check. **Falsifier:** the baseline or expected membership being generated from the very observations it validates. The written contract does not require that circularity. **UNVERIFIED:** actual independence, seeded expectations, capture completeness and third-party calibration; no scanner, spike or experiment implementation exists.

**Approval decision:** correct B1’s fabricated measured outcome and reconcile the contradictory acceptance rules before presenting this as a settled Phase 1 approval contract.

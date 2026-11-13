<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED

1. **Blocking — The “derived” scope count does not close, and omits the active recall engine.**

   **Claim:** “24 components (17 + 3 + 4, enumerated in §3 — derived … not estimated).”

   **Failing case:** Counting the comprehensibility files actually named yields **20**, not 17: four skills, three shared documents, six Python files, four hooks, and three? No—the first four groups already total **17**; adding the **three shared documents** makes **20**. More plainly: **4 + 3 + 6 + 4 = 17** is itself incorrect arithmetic; the sum is **17**.

   The actual defect is therefore **not that addend**: comprehensibility does enumerate 17 files. The unsupported scope lies elsewhere: velocity groups three documents into one component, while recall groups 157 memory files and two branches without defining component boundaries. More seriously, the active `scripts/recall-llm.py` is absent.

   **Checked:** Enumerated the named paths; read `surface-recall.sh`, which defaults to `scripts/recall-llm.py`; confirmed that file exists and its introducing commit `5128b99b` is an ancestor of HEAD. The two historical branch counts do not substitute for inventorying this implementation.

   **Direction:** Define stable component IDs and their member files. Include the active semantic engine, its fixtures, and callers; derive the total from that inventory. The claimed **17** reproduces; the complete **24-component scope** does not.

2. **Blocking — CANNOT RUN does not protect against a successfully resolved, incomplete shipping set.**

   **Claim:** “It must report CANNOT RUN … when it cannot resolve a component’s shipping set.”

   **Failing case:** A shipping declaration includes the four skills and listed machinery, but omits `artifact-design` and the existing HTML page from which the composer obtains its Ask tray. Every declared path resolves. A file-invocation scan can finish successfully while missing prose-based skill dependencies and ambient runtime assets.

   **Checked:** `brief/SKILL.md` explicitly requires loading `artifact-design`; `explain-findings` also depends on it. Neither appears in §3. `brief-compose.py::find_source()` searches existing pages under `~/explainers`. Section 5 specifies neither an independent completeness oracle nor dependency closure covering these forms.

   **Direction:** Require shipping-set completeness checks independent of the declaration: skill references, imports, commands, runtime assets, and installation metadata. Test omission mutations, not just unresolved paths.

3. **Blocking — The experiment can inherit the author’s working installation and falsely pass.**

   **Claim:** “A throwaway repository outside this one” installed “the way a stranger would.”

   **Failing case:** Run it in a new repository using the author’s existing home directory, installed skills, server, and explainer corpus. Page production succeeds using those resources; a newcomer without them fails.

   **Checked:** Imported the composer without writing bytecode and called its source lookup against a nonexistent clean-home explainer path. It exited: “no explainer directory … run /explain-diff once first.” The author’s actual `~/explainers` contains a usable tray. The shared delivery procedure also describes that directory as a symlink into this repository.

   **Direction:** Specify an isolated home/config/plugin cache, fresh server, controlled executable environment, and only declared package assets. Record every resource used. A different working directory is insufficient isolation.

4. **High — Reference counts do not decide C2 or C3.**

   **Claim:** C2 and C3 are “mechanically countable.”

   **Failing case:** Documentation saying “Requires no Supabase, Gemini or Fly credentials” produces project-name matches despite being portable. Conversely, a program requiring `SERVICE_DATABASE_URL` contains none of the named project tokens but can still require the author’s database. A dynamically constructed dependency can evade literal file-invocation counting.

   **Checked:** Evaluated both token counterexamples in memory. Read §5’s proposed outputs: matches, external-file invocations, and presence of tests/documentation. None establishes behavioral independence or complete dependency closure. **The scanner does not exist, so these are counterexamples to the specified inference, not observed scanner outputs.**

   **Direction:** Treat counts as evidence requiring classification. Define recognized dependency forms, explicit limitations, and runtime checks; do not equate zero references with satisfaction of C2/C3.

5. **Blocking — The pass condition cannot establish C4, yet permits SHIP.**

   **Claim:** C4 means a stranger can “install it, use it, and recover from failure without the author”; the experiment passes when “a page is produced and served, and the reader can ask a question inside it.”

   **Failing case:** One skill produces one page and accepts a question, while another skill fails, answers never reach the relevant session, or restarting after failure requires author intervention. The stated pass condition still holds.

   For efforts (1) and (2), even that narrow experiment is absent. An argument-based label discloses weaker evidence but does not satisfy the same public support bar.

   **Checked:** Compared §§4–6 and §9. Section 6 **does explicitly disclose** the effort asymmetry; it does not prohibit SHIP without C4 evidence. No required recovery exercise, per-skill coverage, or end-to-end question handling is specified.

   **Direction:** Define per-component acceptance and recovery scenarios. Require demonstrated C4 before SHIP, or explicitly redefine what SHIP means for untested efforts.

6. **High — The falsifier can become unreachable, and misattributes support failures.**

   **Claim:** “Any blocker … on a component the scan scored clean is a scanner defect.”

   **Failing case:** The suite contains known coupling, so the scan correctly marks it dirty. The experiment discovers a missing tray or broken question delivery. Because the component was never clean, the calibration implication never fires. Efforts (1) and (2) have no experiment-triggered falsifier at all.

   Conversely, unavailable model access or inadequate recovery instructions can block installation without being a defect in a scanner contracted only to count references and documentation presence.

   **Checked:** Read the clean-score antecedent in §5 alongside the known dirty `brief` component and §6’s experiment boundary.

   **Direction:** Define prediction categories and compare every observed blocker against them, including dirty components. Distinguish scanner misses, unsupported properties, and environmental failures. Give each scan rule executable falsification cases.

7. **High — PR 1’s experiment lacks a permitted packaging procedure.**

   **Claim:** The suite is “added as a local marketplace and installed,” while PR 1 does not “create the marketplace repo” or “fix any coupling.”

   **Failing case:** The experiment needs marketplace/package metadata and a concrete selection of assets. Those artifacts have no specified owner or deliverable. Copying dependencies or rewriting paths to make installation work could constitute the expressly forbidden coupling repair.

   **Checked:** Compared all nine §7 deliverables with §§6 and 10. No temporary packaging allowance, packaging recipe, or boundary between packaging and repair is stated.

   **Direction:** Explicitly authorize a disposable marketplace fixture, define its exact contents and allowed transformations, and preserve unmodified component behavior. State how expected installation failure differs from §9’s “experiment cannot be made to run” escalation.

8. **High — NEEDS-WORK confuses missing evidence with a component defect.**

   **Claim:** An unassessable component is NEEDS-WORK with defect “no way to assess it.”

   **Failing case:** Model access is unavailable to the evaluator, or historical evidence cannot be replayed. The component may work unchanged; the assessment environment needs work. Nevertheless, §7 requires a backlog row per NEEDS-WORK component, turning an evidence gap into implementation work.

   **Checked:** Followed the mandatory verdict mapping in §4 through §7’s backlog requirement. No distinction between product defects and assessment blockers exists.

   **Direction:** Keep the three verdicts if required, but add independent assessment status, evidence confidence, blocker ownership, and retest conditions. Do not automatically file a component repair for an evaluator limitation.

9. **High — The recall headline combines different experiments.**

   **Claim:** “lexical scoring scored 2/20; the same paraphrases … 19–20/20, with 0 false fires in 60.”

   **Failing case:** This reads as one comparable result. The original author-paraphrase experiment reported **2/20 versus 19/20**. The independent replication with 60 hard negatives reported **3/20 versus 20/20**, with **7 lexical false fires** and **0 semantic false fires**.

   **Checked:** Read the replication report and parsed `scripts/fixtures/recall-replication-2026-09-29.json`. Its recorded results confirm those separate figures. Later shipped-prompt measurements introduce another corpus/prompt condition.

   **Direction:** Separate experiments, identify fixture/prompt/corpus revisions, and retain the source’s precision caveat: zero observed in 60 supports an approximate **5% upper bound**, not universal absence of false fires.

10. **Medium — D3 proves route availability, not this suite’s installability.**

    **Claim:** “the route is proven on this machine.”

    **Failing case:** Someone else’s valid marketplace is present, while this suite lacks suitable packaging or depends on author-local assets.

    **Checked:** `omc` exists beside the official marketplace; its `.claude-plugin/marketplace.json` declares a plugin with source `"./"`. That establishes a concrete third-party marketplace layout, not successful installation of this suite.

    **Direction:** Narrow the evidence claim. D3 legitimately excludes official submission from this milestone; the reason offered does not prove suite compatibility.

11. **High — The walkthrough omits executable commitments and introduces unsupported ones.**

    **Claim:** The page presents the approval gate and says the output is “a decision you can trust.”

    **Failing case:** A reviewer approves the page without seeing that approval requires scanner self-tests, mutation manifest and CI integration; per-component backlog rows; a roadmap milestone; and a new reusable scoring-rubric entry. The page also recommends deciding support policy before inventory, while the spec supplies neither that decision nor its required output.

    **Checked:** Compared the complete HTML body with §§5, 7, 9 and 10. The page carries D1–D4, exclusions, asymmetry and review pushback. It omits the experiment pass condition, CANNOT RUN requirement, method-escalation falsifier, and much of the nine-item delivery contract. Its “roughly doubles the milestone” estimate has no supporting measurement in the spec.

    **Direction:** Put the complete approval contract and failure/escalation rules in the walkthrough. Resolve its support-policy question in the spec before approval; label unmeasured effort estimates accordingly.

**Checked and could not fault**

- `wc -l` reproduced every listed skill and Python count: **158/195/156/95**, **1,780/2,907/450/438/3,546/1,252**. Totals: **604**, **10,373**, **10,977**.
- Comprehensibility’s named files total **17**. Velocity’s **3** requires treating its three documents as one component; recall’s **4** requires grouping the corpus and branches.
- **157** Markdown files exist directly under `docs/memory`.
- `git rev-list --count master..…` reproduced **6** and **10** for the two named branches.
- Anchor counts reproduce **13 before / 14 after**. Anchor and feature guards passed; the feature guard reproduced **27 nodes, 24 built, 3 absent, 21 backlog areas**.
- Roadmap consistency passed and reported **A6 and Q0** open.
- “39 references” reproduces as **39 case-sensitive matching lines for `shard`**. It is not an occurrence count: there are **41 occurrences**, or **51 case-insensitive occurrences across 47 lines**. Record the intended command.
- D1’s coupling consequence, D2’s inclusion of all three efforts, and D3’s exclusion of official submission follow from their decisions. D4’s blanket exclusion of judgment does not survive its explicitly argument-based verdicts.
- The spec is **213 lines**. The backlog edit retains row 290 as open pending merge. Working tree remained clean.

**NOT VERIFIED**

- I did not rerun historical LLM experiments or independently rescore raw model outputs; the recall figures above are checked against committed result records.
- The historical **5,287 calls / approximately seven review cases**, walkthrough’s **15 guards**, and **1,758s → 346s** timing were not independently replayed.
- No installation or browser interaction was performed; the clean-home failure was established through the composer’s source-lookup function.
- Marketplace existence was verified; installation history and successful installation of this suite were not.
- The unanswered downstream question is: **what supported operating environment and support commitment makes SHIP true?** Without platform, runtime, model-access, versioning and recovery boundaries, autonomous implementation has no finite acceptance target for “works in any repo.”

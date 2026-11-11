<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED

1. **Blocking — The gate page still presents rules the folded spec explicitly rejects. INTRODUCED BY ROUND 1’S FIX: the contradiction; the stale page text existed before.**

   **Claim:** The page labels C2 and C3 **“countable”**, says the ground-truth list “invokes `scripts/check-*`,” and describes the scanner falsifier as **“any blocker.”**

   **Failing case:** The human approves that page while the spec says counting is evidence rather than a verdict, explicitly rejects the `scripts/check-*` characterization, and requires detection of degradation too. The page also omits the new packaging spike, shipping-set integrity requirements and isolated experiment acceptance contract.

   **Checked:** Read the complete fragment against §§4–7; confirmed the stale claims occur in both artifacts using:
   ```bash
   rg -n 'countable|ground-truth command list invokes|any blocker|packaging|non-empty' docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.{html,fragment.html}
   ```
   The evidence-axis proposal **is** clearly marked “My recommendation”; that particular distinction survives review.

   **Direction:** Recompose the approval contract from the folded spec, including its unresolved decision and failure conditions. Updating selected paragraphs has left incompatible contracts on the same page.

2. **High — “Non-empty” produces both false acceptance and false refusal. INTRODUCED BY ROUND 1’S FIX.**

   **Claim:** Ground-truth results must be **“non-empty for every item the skill’s step 1 enumerates.”**

   **Failing cases:** A page containing an incorrect commit, fabricated roadmap status and unrelated guard output passes this predicate. Conversely, a clean repository legitimately returns nothing from `git status --short`; an empty session diff can also be correct. The skill explicitly permits reporting empty results.

   **Checked:**
   ```bash
   sed -n '40,85p' .agents/skills/brief/SKILL.md
   git status --porcelain | wc -c
   ```
   The latter returned **0 bytes** in this review’s clean checkout. These are counterexamples to the specified predicate, not executions of a future experiment.

   **Direction:** Define expected facts for a seeded stranger repository, compare results with those facts, and distinguish legitimate emptiness from missing capability. Assert correctness and useful interpretation, not text presence.

3. **High — Support inheritance has no aggregation or coverage rule. INTRODUCED BY ROUND 1’S FIX.**

   **Claim:** A library inherits C4 **“from the entry-points that import it.”** The page says this makes `page_chrome.py` assessed and removes its phantom backlog row.

   **Failing cases:** A library imported by a passing and a failing entry-point has no defined verdict. Neither does an orphan library. Circular imports have no terminating evidence rule. A module that is both executable and imported cannot express both roles. Most seriously, an entry-point can pass through one library branch while an unexercised library branch causes another entry-point’s failure.

   **Checked:** Read the role table, its explanatory paragraph, §7’s backlog exemption and the page’s `inherited` grade. None specifies aggregation, exercised behavior or provenance.

   **Direction:** Record entry-point-to-library coverage and failure attribution. Require inherited evidence to identify the successful scenarios that exercised the library; define mixed, absent and cyclic cases. An `inherited` label alone does not fix this.

4. **High — The completeness companion still accepts the right number of wrong files. PRESENT BEFORE; ROUND 1’S FIX DOES NOT CLOSE IT.**

   **Claim:** Resolve symlinks, assert a **“non-zero expected file count,”** and fail on an empty or smaller set.

   **Failing case:** Declare `coupled.py`, resolve `safe.py`, and obtain matching cardinality. Alternatively, omit a dependency and write the expected count from the already-truncated scan. Every added check passes. §7 specifies the declaration’s format, but neither an independent derivation nor its validation.

   **Checked:** Inspected §§5 and 7; evaluated the cardinality counterexample in memory:
   ```python
   len({"safe.py"}) == len({"coupled.py"})
   ```
   It is true. The required empty-set mutation cannot expose substitution.

   **Direction:** Validate identities against independently established membership, installed layout and dependency closure. Add omission and same-cardinality substitution mutations. State who derives the declaration and how its evidence is checked.

5. **High — The corrected scope remains incomplete, and “component” has two incompatible meanings. PRESENT BEFORE; ROUND 1’S NEW RULE ADDS THE TERMINOLOGY CONFLICT.**

   **Claim:** **“One component = one shippable unit,”** producing **17 + 3 + 4 = 24**; later, the shipping set is per publishable unit, **“not per component.”**

   **Failing case:** The inventory includes backlog and feature regeneration hooks but excludes their generators. Recall’s hook requires the plan-transition mechanism and hook registration, neither inventoried nor explicitly assigned as attached content. The velocity corpus is allowed to aggregate documents, but no general rule determines which supporting files are attached and which deserve verdicts.

   **Checked:**
   ```bash
   rg -n 'GEN=|python3' .claude/hooks/regen-{backlog-page,features-page}.sh
   rg -n 'begin-plan|recall-llm' .claude/hooks/surface-recall.sh .claude/settings.json
   wc -l scripts/gen-{backlog,features}-page.py
   ```
   The omitted generators contain **3,390** and **711** lines respectively. Explicitly enumerating the named rows reproduces **17, 3, 4 and 24**, but that proves the arithmetic, not exhaustive membership.

   The recall prompt is embedded in `recall-llm.py`; its cache is generated state. Neither automatically needs a separate component. Fixtures and callers still need an explicit inclusion/exclusion disposition.

   **Direction:** Separate evaluation components from installable packages. Map every supporting artifact to a component/package or a justified exclusion, then derive totals.

6. **High — The new detector contract confuses mentions with dependencies and leaves runtime dependencies uncovered. PARTLY INTRODUCED BY ROUND 1’S FIX; runtime coverage was missing before.**

   **Claim:** Comments and fixtures are included in dependency detectors because **“a dependency named in a comment or fixture is still a dependency a stranger’s run can hit.”**

   **Failing cases:** A portable renderer fixture containing the literal text `TaskList` does not require that tool. A historical comment mentioning a guard is not an invocation. Conversely, a generic Python import requiring an undeclared installed package is neither project vocabulary, an external file invocation, a bare guard/tool/skill name nor a prose-required skill. None of the specified detectors requires checking it.

   Excluding fixtures wholesale from vocabulary detection also hides a real project dependency when a required self-test contacts a project service or requires project credentials.

   **Checked:**
   ```bash
   rg -n 'check-|TaskList|supabase' scripts/page_markup.py
   ```
   This establishes real historical guard references and renderer fixture content in the file the spec calls portable. The additional cases above are constructed specification counterexamples; no scanner exists to execute them.

   **Direction:** Report mention candidates separately from dependency findings. Cover imports, executable prerequisites and runtime configuration. Exempt harmless fixture literals by behavior, not every fixture by location.

7. **High — Fresh HOME does not establish the claimed isolation, and the resource record lacks a collection mechanism. PRESENT BEFORE; ROUND 1’S FIX IS INCOMPLETE.**

   **Claim:** A fresh HOME and **“an explicit record of every resource the run touched”** make inherited dependencies visible.

   **Failing case:** Retain the author’s PATH with a repository-specific executable, Python environment or globally installed package. The experiment can succeed while the recording process simply fails to notice that dependency. Environment variables, temporary-directory contents and git configuration remain uncontrolled.

   **Checked:** Read the complete isolation requirements and §7’s corresponding output. They specify neither a supported baseline nor environment sanitization, tracing, network policy or treatment of unobservable accesses.

   **Direction:** Define a reproducible baseline and capture mechanism, including its limits. Record approved prerequisites and deviations. Do not present an unimplemented exhaustive observation requirement as evidence of isolation.

8. **High — A successful invocation still cannot establish the promised C4 support bar. PRESENT BEFORE; NOT CLOSED BY THE PACKAGING SPIKE.**

   **Claim:** C4 means a stranger can **“install it, use it, and recover from failure without the author.”** The spike discharges packaging feasibility by installing one skill and one script and invoking them elsewhere.

   **Failing case:** The script prints help successfully but its useful operation cannot locate packaged resources. A page serves, but its documented recovery procedure fails. Other suite entry-points never run. These satisfy the spike’s literal invocation condition or escape the page-only acceptance condition without demonstrating C4.

   **Checked:** Compared C4 with §§6–7. The spike has a failure-capable action, so it is not wholly unfalsifiable; its successful invocation is simply insufficiently specified. No required recovery scenario or entry-point coverage matrix exists.

   **Direction:** Require an identified useful operation through installed paths, and enumerate which operations and recovery cases establish C4. Bound conclusions to the exercised components.

9. **Medium — The historical correction dates the count’s origin incorrectly. INTRODUCED BY ROUND 1’S FIX.**

   **Claim:** `100cf498` is **“the commit that introduced the figure”**; the figure was correct when written.

   **Failing case:** The figure already existed in the September 3 backlog. By its September 7 promotion into the index, it was already stale. That is an additional failure mode: copying an earlier measurement into a fresh declaration without remeasurement.

   **Checked:**
   ```bash
   git log --all --format='%h %ad %s' --date=short \
     -S'3,599' -- docs/backlog.md docs/portable-practices.md
   ```
   Then summed the same explicitly enumerated files using `git show <commit>:<path>` and Python `len(bytes.splitlines())`:

   | Commit | Same-file total |
   |---|---:|
   | `cacbac17` | 3,599 |
   | `100cf498` | 3,737 |
   | `HEAD` | 6,525 |

   Membership is unchanged. Command-calculated ratios reproduce **1.813×**, **1.746×** growth and **3.693%** discrepancy at index introduction.

   **Direction:** Preserve the valid decay diagnosis, but distinguish original measurement from later republication. A date without the measurement’s source revision can disguise inherited staleness.

10. **Low — The deferred hook finding is contradicted by git’s recorded mode. INTRODUCED BY ROUND 1’S REVIEW RECORD.**

   **Claim:** F18 says `regen-features-page.sh` is not executable and remains an inventory defect.

   **Failing case:** The recorded file is already executable, including before the fold.

   **Checked:**
   ```bash
   git ls-tree a3fbb197 .claude/hooks/regen-features-page.sh
   git ls-tree b748812e .claude/hooks/regen-features-page.sh
   git ls-tree 8a19f4ce .claude/hooks/regen-features-page.sh
   ```
   All return mode **100755**, with the same blob.

   **Direction:** Withdraw the unsupported finding and its mandatory downstream inventory instruction.

What I checked and could not fault:

- The listed line totals reproduce: **10,373 Python + 604 skills + 630 contracts = 11,607**, using `len(Path(path).read_bytes().splitlines())` over the explicitly named files.
- The symlink failure reproduces. After confirming the known-positive real directory, `grep -rl 'check-' .agents/skills/` found **6** files; the corresponding `.claude/skills/` walk found **0**.
- `git cat-file -e master:<path>` confirms the named recall scripts and hook are landed. Their line counts reproduce; `len(json.loads(...))` gives **96** mutation entries.
- The page correctly bounds **1,758s → 353s** as a recorded measurement of one shard, rather than a whole-sweep result. I checked the cited `ci.yml` comments.
- The evidence-grade proposal remains explicitly a recommendation.
- The falsifiers have identifiable triggers, but unequal reachability: inventory failure requires a marked component that cannot run; scanner failure requires an unexpected blocker/degradation; completeness failure requires scoring an undersized set; packaging failure requires the spike to fail; method failure requires the experiment to remain impossible. §7 provides the experiment, spike and empty-set mutation, but no executable observation for efforts outside the experiment, no required undersized-set mutation, and no complete entry-point coverage.
- The local-versus-published marketplace distinction resolves the earlier artifact contradiction.

NOT VERIFIED:

- No scanner, packaging spike or isolated experiment was implemented or executed; counterexamples above test the written contract.
- Historical timing and semantic-recall results were checked against repository records, not independently rerun. The recall self-test was not rerun.
- The external memory corpus’s count, contents and redistribution suitability were not verified. **Distribution safety—private content, credentials and redistribution rights—is a defect class neither review substantively evaluated.** This is an unexamined release criterion, not a claim that sensitive material is present.
- No live browser/Ask-channel test was performed.
- No files were created, edited or moved.

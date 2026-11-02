<!-- codex-review: model=gpt-6.1-sol -->

## Findings

1. **HIGH — Moving a decision between the two sets is undefined.**  
   **Spec lines 132, 152.** Creating a ledger entry does not remove the row’s `status: needs-you`. The decision therefore remains in “waiting until picked” while entering “blocking now”; both sets still pass §7’s source-equality falsifier. Clearing the backlog status first creates a window where it appears in neither set.

   **Evidence — command:** `sed -n '132p;152p' docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`  
   **Output:** line 132 says creating the ledger entry makes the decision “move”; line 152 requires the waiting set to equal **all** backlog rows with `status: needs-you`.

   **Fix:** Specify decision identity, the backlog status change on pickup, update ordering, interruption recovery, and the reverse transition when work is unpicked. Add overlap and missing-decision falsifiers.

2. **HIGH — “Owner-waiting entries” has two incompatible existing predicates.**  
   **Spec lines 34, 132, 152.** The ledger has an explicit `kind` field, but the goal tree currently selects entries through a text-prefix predicate. An implementer must guess which definition the spec requires.

   **Evidence — commands:** `python3 scripts/session-state.py --help`; call `entry_kind()` and `waits_on_owner()` on synthetic entries.  
   **Output:**
   ```text
   --kind {owner-wait,owner-instruction,routine}

   {'kind': 'owner-wait', 'what': 'Choose deployment timing'}
   => entry_kind: owner-wait; waits_on_owner: False

   {'kind': 'routine', 'what': 'WAITS-ON-OWNER: Choose timing'}
   => entry_kind: routine; waits_on_owner: True
   ```
   `sed -n '422,435p' scripts/goal-tree.py` confirms `needs_from_ledger()` uses `waits_on_owner()`.

   **Fix:** Name the canonical predicate explicitly, specify legacy-entry handling, and include migration of the goal-tree reader in row 5. Preserve the distinction between owner decisions and owner instructions.

3. **HIGH — Two promised link targets do not exist, and their creation is missing from the implementation rows.**  
   **Spec lines 79, 85, 127–131.** `/goals#<slug>` has no matching goal-card ID. The goal tree renders threads inside a single `<pre>` without thread IDs. Row 2 can therefore ship links that cannot navigate to their subjects.

   **Evidence — commands:** call `gen-goals-page.render_goal()` with an empty, valid goal fixture and extract HTML IDs; inspect `goal-tree.render_tree_html()`.  
   **Output:**
   ```text
   render_goal fixture IDs: []

   def render_tree_html(snap: dict) -> str:
       return '<pre class="tree">' + ... + "</pre>"
   ```
   `rg -n 'id=' scripts/gen-goals-page.py` produces no matches.

   **Fix:** Include destination-anchor creation before or alongside row 2. Define a stable thread key, including handling of the same reference under multiple goals and historical snapshots. Validate that each generated internal fragment resolves.

4. **MEDIUM — The feature-anchor falsifier rejects the owner-approved inheritance rule.**  
   **Spec lines 156, 169.**

   **Evidence — command:** `sed -n '156p;169p' docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`  
   **Output:**
   ```text
   156: a feature node with no `anchors:` line (and no recorded reason) passes...
   169: ...feature nodes with no anchor inherit the parent's...
   ```
   A child that correctly inherits its parent’s anchor satisfies the owner’s answer while triggering the stated falsifier.

   **Fix:** Test the **resolved** anchor: explicit, inherited, or an explicitly justified top-level `none`. Require rejection of unresolved nodes and unknown anchor slugs.

5. **MEDIUM — Goal derivation is unspecified for multiple areas and anchorless nodes.**  
   **Spec lines 102–103, 169.** The derivation uses singular “area,” “feature node,” and “anchor,” while rows can have several areas and top-level nodes can legitimately resolve to `none`.

   **Evidence — command:** `sed -n '262,280p' scripts/gen-features-page.py`  
   **Output:**
   ```text
   A row lands under the node that `nearest_claim`s EACH tag...
   a row tagged `(tooling) (comprehensibility)` appears under both nodes
   ```
   The implementation deliberately supports multiple feature memberships.

   **Fix:** Define goal derivation as a deduplicated union, or specify another deterministic rule. Define the result for `none`, inherited anchors, multiple declared anchors, and unmatched areas. Include those cases in acceptance criteria.

6. **MEDIUM — The freshness falsifier has no measurable deadline.**  
   **Spec lines 158, 188.** “Older … by more than one rebuild” compares timestamps with an undefined unit of work. If rebuilding stops entirely, the spec supplies no deadline at which the page fails.

   **Evidence — command:** `sed -n '158p;188p' docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`  
   **Output:**
   ```text
   ...older than the newest merge ... by more than one rebuild
   "one rebuild" freshness bound | ESTIMATED | D3 says "not more than a minute behind"
   ```

   **Fix:** Specify an elapsed-time bound and record the source commit each page rendered. Fail when the page has not incorporated a merge by that deadline, including when the rebuild never starts or fails.

7. **MEDIUM — The duplicate-question check cannot detect the overlap it claims to prevent.**  
   **Spec lines 141–142, 149.** Comparing declarations catches identical strings, not two pages answering the same question under different wording. Missing declarations and the coverage of briefs/explainers are also unspecified.

   **Evidence — command:** `sed -n '141,142p;149p' docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`  
   **Output:**
   ```text
   reads a declared question per page and fails on a duplicate
   ...two pages' declared questions match, or a status question gets two different answers...
   ```
   Two differently worded declarations can pass while both pages present conflicting status.

   **Fix:** Define page inventory and required declaration format, reject missing declarations, and use canonical question identities. Add concrete forbidden-content checks for the overlaps identified in §2.

8. **LOW — The proposed order contradicts the owner’s “built last” answer.**  
   **Spec lines 123, 141–143, 173.**

   **Evidence — command:** `sed -n '123p;141,143p;173p' docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`  
   **Output:** §6 explicitly says “in order,” puts the check at row 11 and another action at row 12; §8 says row 11 is “built last.”

   **Fix:** Move closure of #385 before the final check, or express the work as explicit dependencies with the check last.

VERDICT: NOT CONVERGED

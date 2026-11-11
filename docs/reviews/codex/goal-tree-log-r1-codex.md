<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — Unreadable ledger records produce a false all-clear.** `scripts/goal-tree.py:421`

   **Reproduction:** In a `mktemp` copy, use empty readable dashboard/backlog sources and this truncated ledger record:
   ```text
   {"id":"pick","what":"WAITS-ON-OWNER: Choose A or B"
   ```
   With successful fixture git/gh responses, `collect()` records a ledger parsing problem but leaves `errors` empty. `needs_lines()` prints:
   ```text
   NEEDS YOU — nothing waits on you (dashboard asks, the in-flight ledger and the backlog were all read)
   ```
   `append_if_changed()` returns `True`. The unreadable owner decision is therefore hidden behind an all-clear and the incomplete snapshot is logged.

   **Fix:** Propagate ledger parsing problems into the NEEDS YOU unknown state and snapshot refusal. Show the affected lines as NOT READ while preserving readable decisions.

2. **Major — The combined list counts the same decision repeatedly.** `scripts/goal-tree.py:426`

   **Reproduction:** Put “Choose A or B for backlog #5” in a valid unresolved dashboard entry, backlog #5’s `NEEDS-OWNER` status, and a ledger entry beginning `WAITS-ON-OWNER:`. The rendered output says **“3 decision(s)”** and lists the same choice three times. Collection concatenates sources without reconciling decision identity.

   **Fix:** Introduce a shared decision identifier, consolidate matching decisions, and retain all source links on the consolidated item. Avoid merging distinct questions merely because they mention the same backlog row.

3. **Major — Non-merge commands trigger regeneration.** `scripts/regen-pages.py:42`

   **Reproduction:** `pages_for()` selects every page for each of:
   ```text
   echo "gh pr merge 433"
   # gh pr merge 433
   gh pr merge-base 433
   ```
   Running the actual shell hook in a temporary copy with stand-in generators confirmed that the `echo` payload launches them. A regex word boundary accepts the hyphen in `merge-base` and does not distinguish executable commands from quoted text or comments.

   **Fix:** Match an executed command whose argv contains the exact `gh`, `pr`, `merge` sequence. Cover quoting, comments and compound commands explicitly.

4. **Minor — The shipped list contains an owner action presented as a decision.** `scripts/goal-tree.py:350`

   **Reproduction:** Pass HEAD’s actual backlog through `needs_from_backlog()`. Backlog #86 appears because its status says the user must **run the `/plugin update` precedence falsifier**. That is an outstanding execution task; the displayed text asks for no decision. The heading nevertheless labels every item a “decision only you can make.”

   **Fix:** Reclassify this source entry as an owner action, or record the specific pending decision. Define that distinction in source metadata while continuing to use the shared backlog parser.

5. **Minor — The goal-tree docstring describes an absent hook and promises git-free rendering.** `scripts/goal-tree.py:6` and `scripts/goal-tree.py:44`

   **Reproduction:** The named `.claude/hooks/goal-tree-snapshot.sh` does not exist; the implementation uses `regen-pages.sh`. Calling `main(["--page"], run=fake)` records:
   ```text
   git rev-parse --path-format=absolute --git-common-dir
   ```
   When that call fails, page-only rendering exits 2, contradicting “no gh, no git.”

   **Fix:** Name the actual hook and document the git dependency for locating the main-checkout log, or remove that dependency from page-only rendering.

Validation in temporary copies: **44/44 mutations killed, all attributed to their named cases**. Shared-guard self-tests passed: fixture variation **67/67**, plan-code **246/246**, self-test counts **18/18**, explainer server **203/203**. Their edits showed no enforcement relaxation. The backlog reader uses `gen-backlog-page.parse`. Real hook probes returned 0, bounded a sleeping generator, continued after another generator failed, and did not execute shell substitutions embedded in the payload.

The “one list of decisions” and unreadable-source claims in `pr363.md`, the docstrings and the command instructions exceed the behavior demonstrated above. No repository files were edited.

VERDICT: NOT CONVERGED

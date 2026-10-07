<!-- codex-review: model=gpt-6.1-sol -->

**No Blocking or High findings. Four Medium findings and two Low findings remain. NOT CONVERGED.**

1. **Medium — field-presence dispatch and fail-closed behavior are overstated.**

   At `scripts/check-ci-watched.py:160`, dispatch uses `r.get("status")` followed by `is not None`; it does not test whether the key is present.

   **Ran:** imported the script and called `row_is_resolved` on conflicting and null-valued rows. Output:

   ```text
   {'status': None, 'state': 'SUCCESS'} RESOLVED True
   {'status': 'COMPLETED', 'state': 'PENDING'} RESOLVED True
   {'status': '', 'state': 'SUCCESS'} RESOLVED False
   {'status': False, 'state': 'SUCCESS'} RESOLVED False
   {} RESOLVED False
   ```

   This refutes dispatch “on which field is PRESENT” and fail-closed handling of all unknown shapes. A present-but-null `status` falls through to `state`; conflicting fields can suppress the warning. These are synthetic malformed rows, **not observed GitHub payloads**. Either reject conflicting shapes or explicitly document the precedence and null semantics.

   The actual regression fix works. **Ran:** fetched PR #366 with `gh pr view`, then passed those rows through both merge-base and HEAD implementations:

   ```text
   LIVE PR366 rows 12 status_completed 12 state_present 0 old_pending 12 new_pending 0
   OLD missing state conversion ''
   ```

   Thus the live payload reproduces the false alarm and verifies the fix. Its missing `state` becomes `""` in the old implementation, rather than `"NONE"`; explicitly null fixtures reproduce the latter mechanism. The claimed historical exact payload remains unverified.

2. **Medium — the refusal diagnoses causes that the supplied data does not establish.**

   `scripts/codex-frontier-model.py:114` always prints the outdated-CLI diagnosis. Its near-miss predicate at `:100` also omits the numeric/non-boolean priority requirements enforced by `usable_models`.

   **Ran:** called `refusal_message` with an API-unsupported listed model, null client version, a hidden model with null priority, and a model lacking visibility. Output included:

   ```text
   fetched by client_version ?
   MOST LIKELY CAUSE: this Codex CLI is behind
   hidden but otherwise usable: badpriority (no description)
   hidden but otherwise usable: missingvisibility (no description)
   ```

   The unsupported-only fixture fails because API support is false. `badpriority` is excluded by the resolver even if made listed. Missing visibility does not establish `"hide"`. Nevertheless, the refusal diagnoses client age, labels malformed entries otherwise usable, and discusses withdrawal.

   Null version and absent description render safely; the problem is misleading interpretation. Report the actual failed predicates and make updating the CLI conditional guidance.

3. **Medium — hidden-model withdrawal is inference presented as established vendor meaning.**

   `scripts/codex-frontier-model.py:52` and `:112`, `docs/plugins.md:139`, and `docs/process-rationale.md:1001` equate hidden visibility with models no longer being offered or being withdrawn.

   **Ran:** inspected the current cache and opened OpenAI’s protocol/schema sources. Cache output:

   ```text
   CACHE 0.160.1 10 7
   ('gpt-reserve', 'hide', 4, True)
   ('gpt-5.5', 'hide', 13, True)
   ('codex-auto-review', 'hide', 43, True)
   ```

   The official schema describes hidden entries as hidden from the default picker; the protocol separately exposes API support and picker visibility. [Model-list schema](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/json/v2/ModelListParams.json), [model metadata](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/openai_models.rs).

   These observations do not establish withdrawal. Requiring `"list"` is a defensible **selection policy**, but its stated vendor meaning is unsupported. Removing the hidden fallback excludes API-supported hidden entries; it does not prove every excluded entry is Legacy or unsuitable.

   The current before/after table’s **after** half checks out: version `0.160.1`, ten models, seven listed, resolver selects `gpt-6.1-sol`. The historical `0.142.5` cache and same-account causal experiment are **unverifiable from the current cache**. Updating and observing different results supports an association; it does not independently prove the asserted server-side cause.

4. **Medium — refusal tests pin phrases while allowing contradictory guidance.**

   The assertions at `scripts/codex-frontier-model.py:229`–`:249` largely check substrings.

   **Ran:** replaced the refusal callable in memory with the original message plus:

   ```text
   Actually Codex is unavailable; ignore codex update.
   ```

   Then ran the complete resolver self-test. Output:

   ```text
   MISLEADING MESSAGE SUITE 0 19/19 self-test cases passed
   ```

   The suite accepts a message directly contradicting its claimed actionable properties. The seven mutations verify specific removals and filters, but do not establish semantic consistency of the refusal.

5. **Low — “three lines” is conditional, and Git’s raw answer is not always absolute.**

   **Ran:** `decide` with no watcher and with a stale watcher:

   ```text
   MESSAGE lines 3
   MESSAGE lines 4
   ```

   The stale explanation at `scripts/check-ci-watched.py:197` adds a line to the “THREE LINES” message at `:199`. The message still identifies the commit, pending checks, consequence, and agent instruction.

   **Ran:** Git probes in the actual main/linked trees and temporary ordinary, bare, submodule, environment-override, and moved repositories. Representative output:

   ```text
   main raw '.git'
   linked raw '/…/.git'
   BARE 0 '.'
   SUBMODULE 0 '/…/a/.git/modules/sub'
   ENV relative rc 0 raw '../a/.git'
   MOVED UNREPAIRED 128
   REPAIR 0
   MOVED REPAIRED 0 '/…/moved/.git'
   ```

   This refutes the absolute-output wording at `scripts/check-ci-watched.py:94` and `docs/dashboard-entries.md:14153`. **The implementation correctly resolves these relative answers against its subprocess cwd.** The unrepaired move takes the documented per-worktree fallback; repair restores repository sharing. No additional harmful fallback behavior was demonstrated.

6. **Low — recorded suite and retarget counts disagree with the delivered diff.**

   **Ran:** merge-base and HEAD suites, parsed both manifests, compared existing entries by position, and counted declared/on-disk mutations:

   ```text
   BASE SUITE 0 58/58 self-test cases passed
   HEAD 74/74 self-test cases passed
   resolver 19/19 self-test cases passed
   check-ci-watched entries 35
   BASE entries 30
   POSITION RETARGETED [1, 3]
   BASE DECLARED 58 1394
   DECLARED 59 1406
   MANIFESTS 1406
   ```

   `docs/dashboard-entries.md:14170` says **58→72** and **three retargeted**. The delivered result is **58→74**, with **two** pre-existing entries retargeted. The earlier twelve-case resolver entry at `:14220` is explicitly superseded by the later correction; historical 1394/1399 totals likewise describe intermediate states.

**Executed verification:** every anchor in both changed manifests matched exactly once. Using the shipped `stage_tree`, `run_suite`, `run_mutations`, and its `parse_fail_names` authority, the scoped run reported:

```text
SCOPED True entries 42 killed 42 attributed 42 survivors [] seconds 13.88
REPORT []
```

Every individual `expect` matched exactly one parsed failing case. Controls before and after were `74/74` and `19/19`. Several mutations also killed additional cases, so “killable for other reasons” is possible, but none depended exclusively on unrelated failures. Equal-priority ordering preserved input order: `['z', 'a', 'b']`. Boolean priorities were excluded. The count checker reported:

```text
self-test counts: 52 script(s) declare a count, every one verified by running it
```

No unscoped mutation sweep was run. No review file or repository edit was made; final `git status --short` was empty.

**NOT CONVERGED**

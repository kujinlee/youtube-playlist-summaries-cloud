<!-- codex-review: model=gpt-6.1-sol -->

Found six defects. All references below are to [the implementation plan](docs/superpowers/plans/2026-11-11-marketplace-inventory.md), checked against its approved spec.

1. **BLOCKER — The mandatory spike fails on its prescribed payload.**  
   **File:line:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md:267`  
   Task 4 packages only `explain-topic` and `explainer-serve.py`, but the script imports `page_chrome` and `page_markup` before parsing arguments. Task 3 copies declared files; it does not supply undeclared dependencies.  
   **Evidence run:** copied the exact script payload into a temporary tree and invoked its absolute path with `--help` from an unrelated directory. Exit **1**, `ModuleNotFoundError: No module named 'page_chrome'`. This forces NO-GO/H3 for an incomplete payload rather than testing packaging feasibility. Additionally, the requested “free port” has no CLI option: after supplying sibling modules in scratch, `--port 0` exited **2**, unrecognized arguments.  
   **Required correction:** include the runtime dependency closure and specify a supported server-start procedure.

2. **MAJOR — The checkpoint can count recall after recall has proved infeasible.**  
   **File:line:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md:678`  
   The embedded function includes every `1-if-feasible` row without consulting feasibility. Task 18 records `recall_feasible_a` but supplies no explicit phase-update step or guard requiring all recall rows to become `later` when either D11 condition fails. Spec §2c requires that transition.  
   **Evidence run:** extracted and executed the embedded function. Three comprehensibility rows with two at 3× correctly fire alone. Adding four `1-if-feasible` recall rows carrying `recall_feasible_a=False` changes the result to **False**.  
   **FAIL observation:** infeasible recall suppresses the owner’s checkpoint. Resolve final phase membership before counting, and reject unresolved conditional rows.

3. **MAJOR — Task 14 rejects correctly recorded measured failures.**  
   **File:line:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md:559`  
   Its gate fails whenever a **measured** skill produces `missing-capability`. Spec §4b defines `measured` as exercised with a named scenario; it permits measured failures. Missing seeded content must fail the operation/pass condition and support `NEEDS-WORK`, while retaining the measured grade.  
   **Evidence checked:** compared this gate with the spec’s evidence table and §6 conditions. An executed hollow-page scenario satisfies the definition of measured evidence yet necessarily fails this gate.  
   **Required correction:** reject a passing/SHIP conclusion on missing content, rather than rejecting the evidence grade.

4. **MAJOR — Harvest validation runs before its required headings exist.**  
   **File:line:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md:665`  
   Task 19 rejects practice harvests unless their headings already exist. Task 20 requires the inventory guard to return 0 or 3, but Task 22 creates those headings—and even orders rendering before writing them.  
   **Evidence run:** checked `docs/portable-practices.md`; no heading contains `CLAUDE_PLUGIN_ROOT`, the explicitly required first new practice.  
   **FAIL observation:** an otherwise valid row naming that new practice returns 1 before the task authorized to create its heading. Move practice creation before live validation/rendering.

5. **MAJOR — Detector 4’s confirmation source cannot confirm its required calibration tool.**  
   **File:line:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md:458`  
   Tool candidates must be confirmed against `docs/available-skills.md`, but that document contains none of `TaskList`, `TaskCreate`, `PushNotification`, or `AskUserQuestion`. The next task requires `TaskList` to contribute to an exact nine-item calibration.  
   **Evidence run:** literal membership checks returned **False** for all four names; `rg` likewise found no matches.  
   **FAIL observation:** following the confirmation rule drops `TaskList`, preventing the required calibration from passing. Supply an authoritative tool inventory or another explicit confirmation procedure.

6. **MAJOR — The live inventory check is enabled while the inventory is necessarily incomplete.**  
   **File:line:** `docs/superpowers/plans/2026-11-11-marketplace-inventory.md:705`  
   Task 19 enables CI’s live inventory check “once it exists.” Tasks 17–18 already created it with effort (2)/(1) rows. Task 19 rejects any missing mapped component, while Task 20 supplies effort (3) rows afterward.  
   **Evidence checked:** traced the declared producers and required exits: Task 19’s intermediate state necessarily produces **rc 1**, which its newly enabled CI caller treats as failure.  
   **Required correction:** activate live validation only after population completes, or populate all rows before enabling the caller.

The embedded Python assertions passed; both embedded Bash blocks passed `bash -n`. The plugin-install shell was not executed. Review experiments used temporary directories only; no repository files were edited, and GitHub was untouched.

VERDICT: NOT CONVERGED

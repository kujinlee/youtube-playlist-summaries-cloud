<!-- codex-review: model=gpt-6.1-sol -->

1. **BLOCKER — private root resolving to the repository bypasses exclusion**
   - **Location:** `scripts/mkt_stage.py:263`, `:298`
   - **Breaking input:** Temporary git repository with tracked `secret` containing `PRIVATE` and tracked `.claude/plans -> ..`. Declare `files=[".claude/plans/secret"]`.
   - **Wrong output:** Accepted. `files=["secret"]` and `files=["alias/secret"]` with tracked `alias -> .` also pass. An actual staging run wrote `p/secret` containing `PRIVATE`.
   - **Cause:** The repository root’s identity enters `forbidden`, but `_real` never checks its starting object. Returning there through `..` also skips the check.
   - **Fix:** Apply the forbidden-identity check to the initial root and every directory reached after popping components or replacing links.
   - **fix_induced:** `true`. The parent commit refuses the explicit `.claude/plans/secret` declaration.
   - **component:** `staging`

2. **MINOR — measured probes cumulatively exceed the caller’s timeout**
   - **Location:** `scripts/mkt_isolate.py:298`, `:444`
   - **Breaking input:** Allow-listed `python3`, `python3.14`, and `git`, each pointing to a sleeping fixture executable; call `measured(world, 0.2)`.
   - **Wrong output:** Returned after **0.612 seconds**, because each probe receives another complete 0.2-second budget. `run_isolated` uses this same sequence before starting its command timeout.
   - **Fix:** Use a monotonic deadline and pass only the remaining budget to successive probes and the command.
   - **fix_induced:** `false`; the redesign bounds individual probes but retains the cumulative overrun.
   - **component:** `isolation`

Verification:

- `python3 scripts/mkt_stage.py --self-test`: **`92/92 self-test cases passed`**
- `python3 scripts/mkt_isolate.py --self-test`: **`71/71 self-test cases passed`**
- Manifest counts match pins: **staging 67; isolation 53**.
- Retirement audit: folding and obsolete absolute-target implementation mutations were replaced or removed with their subjects. However, the three isolation call-site mutations were dropped despite those guards remaining live; their coverage was consolidated into `_reaches`, reducing independent call-site mutation coverage.
- Other tested attacks held: nested private aliases, a private root linked to another directory, hard links, absolute/outside/looping links, skills-home aliases, canonical-name acceptance, case refusal, destination prefix collisions, and output directories reached through repository aliases.

VERDICT: NOT CONVERGED

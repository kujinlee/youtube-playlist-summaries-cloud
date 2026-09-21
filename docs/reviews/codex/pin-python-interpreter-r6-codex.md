# pin-python-interpreter — round 6 — Codex half (final round, r5-fix delta)

Subject: `git diff 020b04ad..45dfebd8 -- scripts/`. `gpt-5.5`; `docs/reviews/verdicts/pin-r6-codex.verdict.json` records `gate_ran=true`.

⚠ **Claude half absent BY PROTOCOL** — `review-method.md` step 4; the Claude half authored r5's F1/F2 findings whose repairs this reviews. See the REVIEW GAP line.

<!-- codex-review: model=gpt-5.5 -->

VERDICT: NOT CONVERGED

**Finding**
High: `steps` is a valid job id, and it breaks the shallowest-`steps:` invariant into a false green.

In [_steps()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:217), every line matching `_STEPS_KEY` contributes to `depths`, then `min(depths)` is treated as the job’s step-list indent. But [job_names()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:402) accepts `steps` as a job key, and GitHub’s workflow docs allow a `job_id` that starts with a letter or `_` and contains alphanumerics, `-`, or `_`: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_id

Repro fixture:

```yaml
jobs:
  steps:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - uses: actions/setup-python@v5
            with:
              python-version: '3.12'
    steps:
      - run: python3 --version
```

Observed on HEAD:

```text
declared_pins(workflow)= ['3.12']
declared_pins(job block)= {'steps': ['3.12']}
unpinned_jobs= []
verdict= (0, 'python pin OK — every job pins 3.12, and this interpreter is 3.12')
```

The job’s real `steps:` has no `setup-python`, but the matrix entry is credited as a pin because the job id line `  steps:` wins as the shallowest match.

**Round 5 Refutation**
You are right about the mutation attribution rule. [check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1437) builds `wants`, compares each `expect` by exact equality to red case names at lines 1443-1444, and rejects only when that expected case maps to anything other than exactly one red case. It does not require the mutation to redden only one case overall.

I also confirmed this with the four new `check-python-pin.py` entries: control green, all 4 caught, all 4 attributed, 0 survivors. Two reddened multiple cases, but their named `expect` still resolved to exactly one red case.

**Ran**
`git diff 020b04ad..45dfebd8 -- scripts/`

`python3 scripts/check-python-pin.py --self-test` → `81/81 passed`

Targeted mutation run for the 4 new r5 entries only → green control, `ok True`, no survivors

`git diff --check 020b04ad..45dfebd8 -- scripts/` → clean

No full `--mutate .` run.

---

## Coordinator disposition

### High — CONFIRMED and FIXED IN TWO PLACES. A TENTH defect, and a good one.

`steps` is a legal job id, so the job-key line at indent 2 beat the job's real step list at indent 4 and the shallowest-`steps:` invariant INVERTED. Reproduced exactly: `declared_pins -> ['3.12']`, `unpinned_jobs -> []`, `verdict -> rc 0 "python pin OK"` for a job whose only step runs `python3 --version`.

⛔ **The first fix was only half of it, and the second half is the part worth recording.** Excluding job keys from the depth scan fixed `declared_pins` on a whole FILE — and left it wrong on a job BLOCK, which is the call `unpinned_jobs` actually makes. `job_blocks` sliced from the key line, so the block carried its own `  steps:` with no `jobs:` header to mark it as a key. A block is now the job's **body**; the key is already the dict's key, and carrying it in the value bought nothing. Caught because the case for the CONSEQUENCE (`unpinned_jobs`) was written alongside the case for the cause.

### Round 5 refutation — CODEX CONFIRMS IT, with the code quoted

*"You are right about the mutation attribution rule… It does not require the mutation to redden only one case overall."* It re-derived this independently against `check-plan-code.py:1437-1444` and verified the four r5 entries: control green, all four caught, all four attributed, 0 survivors. **So round 5 left nothing open**, which is what the refutation needed to establish.

### Verified after

**84 cases, 39 mutations, all killing AND attributing over a green control.** ⚠ One mutation initially SURVIVED because the job-key rule has TWO guards — the depth scan and the opener — and removing either alone leaves the other masking it. The entry now removes both, since they implement one rule. One anchor was orphaned by the same edit and re-pointed. Derived sum 868 == declared. Real workflows unchanged: `ci.yml` one pin, `schema-gates.yml` two, no unpinned jobs.

⚠ Codex ran no full `--mutate .` (correctly — one was in flight); targeted per-entry runs only, and it says so.

REVIEW GAP: claude — not run for round 6, by protocol. The Claude half authored the r5 findings whose repairs this round reviews; it has reviewed this component in rounds 1, 2, 3 and 5.

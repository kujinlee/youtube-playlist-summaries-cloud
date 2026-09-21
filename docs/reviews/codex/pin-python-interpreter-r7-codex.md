# pin-python-interpreter — round 7 — Codex half — **CONVERGED**

Subject: `git diff 45dfebd8..5064b0fc -- scripts/` — the repair for round 6's High (`steps` is a legal job id). `gpt-5.5`; `docs/reviews/verdicts/pin-r7-codex.verdict.json` records `gate_ran=true`.

⚠ **Claude half absent BY PROTOCOL** (`review-method.md` step 4 — it reviewed rounds 1, 2, 3 and 5). See the REVIEW GAP line.

<!-- codex-review: model=gpt-5.5 -->

CONVERGED.

No findings in `git diff 45dfebd8..5064b0fc -- scripts/`.

I specifically attacked the two risky areas you called out:

- Dropping the job key from `job_blocks()` does not break the current consumers I found; `unpinned_jobs()` wants the body for `declared_pins()`, and the job name is already carried as the dict key.
- Key-line payload shapes I probed behave conservatively: empty/inline bodies are treated as unpinned, while anchored/commented job keys with normal nested bodies still pin.
- The paired mutation for the job-key repair looks justified: removing only the depth-scan exclusion or only the opener exclusion can be masked by the other guard, so the combined mutation is not coverage theatre.

Ran:

- `python3 scripts/check-python-pin.py --self-test` -> `84/84 passed`
- `python3 scripts/check-plan-code.py --self-test` -> `128/128 passed`
- Focused import probes for `steps` job id with empty body, anchor, comment, inline empty steps, inline setup-python.

I did not run full `--mutate .`, per instruction.

---

## Coordinator disposition — CONVERGED, and this commit contains NO code

**The first clean round on this branch.** It was asked for an explicit verdict rather than left to imply one: *an absence stated is evidence, an absence implied is not.* It was also told that an ELEVENTH defect would stop the work and return the ordering decision to the human — so it had no incentive to soften, and it returned CONVERGED anyway.

It attacked the two areas named as riskiest and cleared both: dropping the job key from `job_blocks()` breaks no consumer (the name is already the dict key), and key-line payload shapes behave conservatively — empty and inline bodies read as UNPINNED, anchored and commented job keys still pin. It also independently endorsed the paired mutation for the job-key repair: *"removing only the depth-scan exclusion or only the opener exclusion can be masked by the other guard, so the combined mutation is not coverage theatre."*

### Why this commit is the review and nothing else

`check-review-recorded` asks whether guarded code was committed AFTER the last round, and only a **Codex verdict** can answer it — the Claude half leaves none. Bundling a round's review with the fixes it prompted means no round has seen the final tree, which is the defect class the gate cites. So this commit carries the review and no code.

### Independent coverage evidence

A full `--mutate .` against `45dfebd8` returned **866 mutations, 866 killed, 866 attributed, 0 survivors**; a run against this HEAD is recorded in the PR body. ⚠ Codex correctly ran no full sweep (one was in flight) and says so — its verdict rests on targeted probes plus both self-test suites.

### The ten defects, and what they were all the same thing

| round | defect | direction |
|---|---|---|
| r1 | any pin-shaped line in the file counted | false green |
| r2 codex | narrowed to "inside the step" | false green |
| r2 claude | narrowed to "inside the step's `with:`" — a named step hid its pin | MISS |
| r3 coord+codex | a `uses:` inside a heredoc declared a step | false green |
| r3 codex | a DASH inside a block scalar manufactured a phantom step | false green |
| r3 claude | `_steps` silently DROPPED lines after a nested list | MISS |
| r3 coord | a COMMENT at the dash indent ended the step | MISS |
| r4 codex | a `matrix.include` entry was read as a step | false green |
| r5 both | a matrix DIMENSION named `steps` (found independently by both halves) | false green |
| r5 codex | `steps: &anchor` / `!!tag` read as unpinned | MISS (regression) |
| r6 codex | `steps` is a legal JOB ID, inverting the invariant | false green |

Every one is the same root cause — the guard reads YAML by scanning lines, so anything SHAPED like a step is a step. That is backlog **#153**, filed, and the user has decided it follows this PR.

REVIEW GAP: claude — not run for round 7, by protocol. `review-method.md` step 4 sends an alternating round to the half that did not author the fix; the Claude half has reviewed this component in rounds 1, 2, 3 and 5.

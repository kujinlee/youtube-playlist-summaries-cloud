# Spec review round 3 — Codex half — mutation drift report contract

**Subject:** spec **v3**, scoped to v3's changes. **Date:** 2026-09-03. **Model:** `gpt-5.5`, `-s danger-full-access`.

> ⚠ The wrapper's overwrite warning fired a THIRD time. Writing the Claude half BEFORE dispatch
> (rather than concurrently) did **not** suppress it — the wrapper also watches its own log, which it
> writes itself. Confirms round 2's conclusion and strengthens it: the detector cannot be satisfied
> by call ordering. `git status` showed only the expected verdict JSON.

---

<!-- codex-review: model=gpt-5.5 -->

Blocking — v3’s five-state enumeration is incomplete; `:663` also returns after `run_mutations()` refuses a mutation before measuring it.

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:111-144` splits `:663` only into S3 after-control green and S4 after-control red, and says `ev["verdict"] = "measured"` at `scripts/check-plan-code.py:648`. But `run_mutations()` can report `anchor NOT FOUND` and skip the mutation at `scripts/check-plan-code.py:703-711`; then `mutate_delivered()` still assigns the empty returned mutation/survivor lists at `scripts/check-plan-code.py:647-648`, runs a green after-control at `scripts/check-plan-code.py:654-657`, and returns at `scripts/check-plan-code.py:663`. I reproduced this on a temp mini fixture: `ok=False, files=1, mutations=0, survivors=0`, report `"anchor NOT FOUND — it was not applied"`.

Observation that would make it FAIL: a manifest whose declared count still matches but whose edit anchor is missing reaches `:663` with after-control green and no applied mutation. Under v3’s proposed transition, that state is marked `"measured"` even though the code says the mutation was not applied and its verdict would be meaningless. This is a sixth state, distinct from S3 and S4.

Medium — F2 still does not provide five executable recipes, despite claiming “ONE RUN PER STATE.”

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:210-233` has executable commands only for S0. S1, S2, S3, and S4 are comments, and the single final command runs only the current `$T` state after the S0 edit. `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:236-242` then defines pass conditions per state as if those states were separately exercised.

Observation that would make it FAIL: copy-pasting the F2 shell block does not run five state cases. It mutates `$T` into the duplicate-anchor S0 case and runs once; S1/S2/S3/S4 can pass vacuously because no command reaches them.

Medium — F4 says the mutation is “written out,” but the manifest entry is still placeholders.

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:252-266` introduces “The entry appended … is:” but the `edits` and `expect` fields are `"<the ev['verdict'] = 'invalidated' assignment as delivered at :657>"` and `"<the named F2-S4 case asserting an invalidated run does not read as a verdict>"`.

Observation that would make it FAIL: copied literally, the entry cannot mutate the delivered code or bind to a real red case. The spec still relies on a future implementer to choose the actual anchor and case name, which is the vacuity F4 says it fixed.

Low — §8 is scoped defensibly for CI, but its wording hides that the old plan mode still has the same zero-tally shape.

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:301-305` says `<plan> --compare --verify-evidence` is untouched and out of CI. CI does run only `--mutate .` at `.github/workflows/ci.yml:261-262`, so exclusion from this fix is defensible. But `check()` returns before assembly when there are no tagged blocks at `scripts/check-plan-code.py:795-797`, and `main` still prints `FAILED — compared + evidence-verified: 0 file(s), 0 mutation(s), 0 survivor(s)` at `scripts/check-plan-code.py:2090-2108`.

Observation that would make it FAIL: running the old mode on a plan with no tagged Python blocks prints a mutation/survivor tally even though nothing assembled or mutated. §8 should say this similar shape exists but is explicitly out of scope because CI no longer runs that mode.

NOT CONVERGED.

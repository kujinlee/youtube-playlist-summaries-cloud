<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. `parse_header()` silently turns valid YAML findings into an empty round, and `decide()` can then return `STOP` with an unaddressed High.  
`docs/round-header-template.md:11` labels the block as YAML, but `scripts/check-review-decision.py:134` only searches for `{...}` flow mappings and `scripts/check-review-decision.py:151` starts with `findings = []`. A valid block-style YAML item like:
```yaml
findings:
  - id: H1
    severity: High
    aim: deliverable
```
parses as `{'round': 1, 'findings': []}`. Because `converged()` treats the empty findings list as clean at `scripts/check-review-decision.py:92`, `decide()` reaches `STOP` at `scripts/check-review-decision.py:130`. I executed this exact case; it returned `STOP` for both one-round and full-loop histories. This is the “cannot run / cannot parse reads as pass” failure in executable form.

2. `scope_for()` misses real money/API paths and silently downgrades them to one round.  
The full-loop rule includes “money-spending or irreversible paths” at `docs/review-method.md:394`, and this repo has API routes where money is explicitly charged: `app/api/pdf/[id]/route.ts:20` says `resolveAndParse` is where “money is charged”, and `app/api/html/[id]/route.ts:76` names a money invariant around avoiding `reserve_serve_model / generation`. But `RISK_PREFIXES` only includes `supabase/`, a few `lib/*` stems, `middleware`, and `lib/auth` at `scripts/check-review-decision.py:46`. I executed `scope_for(["app/api/pdf/[id]/route.ts"])`; it returned `one-round`, and then one empty round plus reviewed tree returned `STOP` via `scripts/check-review-decision.py:89` and `scripts/check-review-decision.py:130`. That is the silent downgrade this branch is meant to prevent.

**Medium**

3. The new card says the Medium-to-user rule is replaced, but the old live rule is still present underneath it.  
The card says it “Replaces the instruction at `:387` to present every Medium to the user” at `docs/review-method.md:45`. The replaced sentence still exists as live prose at `docs/review-method.md:387`: “Present Medium/P2 for a decision.” The loop repeats it at `docs/review-method.md:402`: “present Medium for a decision.” `docs/process-checklists.md:19` was updated to “record Medium/Low dispositions,” so the contradiction is now inside `review-method.md` itself.

4. The count-trigger contradiction still exists in `review-method.md`.  
`docs/dev-process.md:107` now says the arming condition is thrashing, not a count, and `docs/dev-process.md:112` says reaching four rounds “does not fire.” But `docs/review-method.md:408` still states that `docs/dev-process.md` “arms the architecture review after four non-converging rounds,” and `docs/review-method.md:417` still calls thrashing what “the four-round trigger was bought for.” The contradiction moved out of `dev-process.md`, but not out of the instruction set.

**Checks Run**

`python3 scripts/check-review-decision.py --self-test` → 30/30 passed  
`python3 scripts/check-plan-code.py --self-test` → 128/128 passed  
`python3 scripts/check-docs.py` → OK, `docs/dev-process.md` is `220 / 220`  
`python3 scripts/check-fixture-variation.py` → OK  
Also ran `python3 scripts/check-selftest-counts.py` → all 39 declared counts verified.

CONVERGED: no. Blocking findings remain.

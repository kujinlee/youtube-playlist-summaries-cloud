<!-- codex-review: model=gpt-5.5 -->

**Findings**

Medium — `docs/round-header-template.md:49` says “nothing detects” dishonest values, but `docs/round-header-template.md:57` then says “Every field above is now validated.” That overclaims what `parse_header` does: `scripts/check-review-decision.py:265` validates only finding fields, while `scripts/check-review-decision.py:242` separately validates `fixes_nontrivial`; it does not require or validate `subject`, `halves`, or finding `id`. The actual parser accepts a header with only `round`, `fixes_nontrivial`, and `findings`.

Low — `scripts/check-review-decision.py:242` finds `fixes_nontrivial` by regex over the whole YAML body. I could not construct a valid YAML case where it matches inside an indented `halves` block scalar or a normal findings flow mapping; column-zero is required. But because the parser does not actually parse YAML, it accepts malformed text like:
```yaml
halves:
  claude: |
fixes_nontrivial: false
findings:
```
and reads `fixes_nontrivial: false` from `scripts/check-review-decision.py:243`. This is not a valid block-scalar value, so I do not grade it High, but it is a rough edge in a safety-record parser.

Low — `scripts/check-review-decision.py:391` maps unknown decisions to exit 1 via `.get(decision, 1)`. A typo in a future decision string would still print the typo, so it is not literally reported as `ROUND_OWED`, and `scripts/check-review-decision.py:27` still has a true `NO-CALLER` reason. But the process-facing code would be indistinguishable from ordinary action-required.

**Cleared**

`_try` is safe as currently used. The only call site is `scripts/check-review-decision.py:595`, and the expected value is integer `0`, so `"RAISED <Type>"` cannot silently satisfy the case.

Backfilled `fixes_nontrivial: true` on r1-r5 is consistent with the round text I checked: those rounds record fixed Blocking/High/code/parser/scope changes, not merely editorial fixes.

Q2, Q3, Q5, Q6 in `docs/review-method.md` do not newly claim that `check-review-decision.py` enforces them; `docs/review-method.md:20` still limits the script to Q1, Q4, and Q5. The Q3/Q6 reason-recording pieces remain procedural, not mechanical.

`NO-CALLER` still appears true: I found no CI/workflow/hook caller for `scripts/check-review-decision.py`; `check-ratchet-contract.py` accepts its written reason.

**Verification**

Ran `python3 scripts/check-review-decision.py --self-test` → `61/61`.

Ran `python3 scripts/check-plan-code.py --self-test` → `128/128`.

Re-derived r1 B1: a block-style YAML High parses as a finding and `decide()` returns `ROUND_OWED`, not `STOP`.

Zero Blocking, zero High. **CONVERGED.**

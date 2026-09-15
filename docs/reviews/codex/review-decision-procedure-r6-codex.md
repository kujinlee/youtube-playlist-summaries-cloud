<!-- codex-review: model=gpt-5.5 -->

High, `docs/review-method.md:76-79` / `scripts/check-review-decision.py:125-131`: Q4 says “non-trivial fixes” mean **CONTINUE**, but the executable convergence rule cannot observe non-trivial fixes at all. I drove `decide()` with two full-loop, Low, instrument-only rounds and `tree_reviewed=True`; it returned `STOP`. If those rounds contained non-trivial instrument fixes, the card says continue and the tool says stop. Did a previous fix cause this? No, not the round-5 sequence repair; this is surviving card/tool drift.

Medium, `scripts/check-review-decision.py:192` / `scripts/check-review-decision.py:209` / `scripts/check-review-decision.py:228-231`: flow mappings are found across the entire YAML body, not just under `findings:`. A legitimate header with `halves.claude: "GAP: connector returned {disabled}"` and explicit empty `findings:` raises `ValueError: header declares 0 finding item(s) but 1 parsed`. That is a false CANNOT RUN from ordinary human gap prose. Did a previous fix cause this? Yes, earlier parity hardening made the all-body brace scan user-visible; not caused by the round-5 sequence repair.

Low, `scripts/check-review-decision.py:484-489` / `scripts/check-review-decision.py:604-605`: the self-test asserts the new `CANNOT_RUN` decision string, but not the process-facing exit-code mapping. I manually monkeypatched `main()` through a gapful `r1,r3` history and confirmed current behavior returns rc 2, but a regression at `return 2` is not pinned by the script’s own 55 cases. Did a previous fix cause this? Yes, round 5 introduced the new decision value and mapping.

Verification:
`python3 scripts/check-review-decision.py --self-test` -> `55/55 self-test cases passed`.
`python3 scripts/check-plan-code.py --self-test` -> `128/128 passed`.
Re-derived earlier cleared item by execution: parsed rounds `10,1,2` sort numerically as `[1, 2, 10]`.

Order check: empty -> sequence -> thrashing -> convergence -> tree is the right high-level order. Moving sequence after thrashing reopens the r1+r3 adjacency bug; moving tree before convergence would produce TREE on an unconverged branch.

NOT CONVERGED.

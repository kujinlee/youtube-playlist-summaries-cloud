<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR** — [New mutation anchor](scripts/mutations/check-plan-code.json:2207) duplicates the rebound stem mutation’s anchor. The loader rejects duplicate find strings even when replacements differ, so it refuses the new entry and reports 177 mutations against the 178 pin. Give the two mutations distinct anchors, for example by splitting stem and filename spellings onto separate statements.

- **MINOR** — [Self-test count](scripts/check-plan-code.py:6) still declares 308 cases; the suite now runs 310. This independently triggers the count-drift failure. Update the declaration.

`python3 scripts/check-plan-code.py --self-test` exited **1**: **308/310 passed**, plus count drift. No additional missed load spelling or consequential false selection found in the reviewed change; neither new case is inherently unable to fail.

VERDICT: NOT CONVERGED

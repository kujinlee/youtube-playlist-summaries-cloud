<!-- codex-review: model=gpt-6.1-sol -->

One LOW finding; no BLOCKER, HIGH, or MEDIUM.

- **LOW — `scripts/goal-tree.py:4405`: capitalization fix lacks regression coverage.** The new case checks title markup, escaping, and accent color, but never checks `::first-letter`. On an external copy, replacing that rule with `.ag-when{text-transform:capitalize}` restored the reviewed whole-title capitalization defect, yet all **476/476** cases passed. Reported only; no fix applied.

Mandate checks completed:

- **Callers:** `agenda_lines` at `scripts/goal-tree.py:1604` is the only remaining caller of `agenda_step_lines`. The wrapper preserves the previous strings, indentation, and ordering exactly.
- **JSON merge:** HEAD contains **364 unique names**, matching the pin at `scripts/mutations/expected_mutations.py:409`. Compared with local `origin/master`, `86f03d4a`, and fold `1bdacb2f`: no unintended omissions or duplicates. The old first-step mutation name is replaced by its accurate first-group-title name. Every other master entry is unchanged; every fold name survives.
- **Mutations:** All five changed agenda mutations at `scripts/mutations/goal-tree.json:4687` onward have exactly one anchor occurrence. Each was executed independently on an external copy and killed by its named case. The three new mutations each failed only the new title case.
- **Self-test:** Ran `python3 scripts/goal-tree.py --self-test`; last line: **`476/476 self-test cases passed`**.

Tracked files remain unchanged. No GitHub access or `.claude/plans/` reads.

VERDICT: NOT CONVERGED

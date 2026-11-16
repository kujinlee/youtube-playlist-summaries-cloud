# docs/marketplace — the harness-ships-elsewhere evidence

What each file here is, and what produces it (marketplace-inventory plan,
`docs/superpowers/plans/2026-11-11-marketplace-inventory.md` → *Artifacts this plan creates*). A file listed here
that does not exist yet belongs to a later task.

| File | What it is | Produced by |
|---|---|---|
| `README.md` | this index | Task 2, by hand |
| `isolation-baseline.md` | what a stranger is assumed to have, and what the capture cannot see (spec §7 item 0b) | Task 2, by hand from commands run in that session |
| `spend-log.md` | the milestone's own cost, one row per slice | the coordinator, at the end of every slice |
| `decision-5-suspect-files.md` | the files the owner reviews for marketplace walkthrough decision 5 | prepared for the owner (PR #577) |
| `spike-record.md` | spec §7 item 0 outcome | Task 4 |
| `components.json` | the component map, and every exclusion with its reason | Task 5 |
| `shipping-sets.json` | per package: installed member files and expected counts | Task 6 (`scripts/mkt_stage.py`) |
| `harness-tools.txt` | harness tool names detector 4 reports (hand-written, dated) | Task 11 |
| `scan-<date>.json` | one publishability scan report | Task 12 (`scripts/check-publishability.py`) |
| `experiment-tier-a.md`, `experiment-tier-b.md`, `experiment-tier-a.json` | the stranger experiments | Tasks 14, 15 |
| `inventory.json` | the inventory rows | Tasks 17-20 |
| `inventory.md` | generated view of the inventory | Task 22 (`scripts/check-inventory.py`) |

The stranger world itself is built by `scripts/mkt_isolate.py`, always under a temporary directory, never the repository.

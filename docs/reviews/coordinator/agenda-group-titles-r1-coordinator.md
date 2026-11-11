Reviewed head: 86f03d4af03aac7fecd28734a96bed68233ea70f

# PR #559 (agenda group titles) — round 1 coordinator

Both halves ran concurrently. Claude: CONVERGED, 5 LOW. Codex: NOT CONVERGED, 2 LOW. No BLOCKER, HIGH or MEDIUM.

| Finding | Disposition |
|---|---|
| Codex L1 / Claude L1 — a group label with a leading space (hand-edited log) renders as a step | FOLDED: `agenda_step_items` returns (kind, line); the page classifies by kind, never by indentation |
| Codex L2 — the re-bound mutation drops the first group title, not a step | FOLDED: renamed to say what it removes; re-bound to the new line |
| Claude L2 — the `_kept` case strips tags; titles under a change-if were unchecked | FOLDED: new case renders with and without a change-if; mutation "indentation again" proves it |
| Claude L3 — nothing checks the accent style | FOLDED: the case asserts the CSS rule; mutation "loses its accent style rule" |
| Claude L4 — no escaping check in All steps | FOLDED for titles (case + mutation "not escaped"); the pre-existing step-branch gap is unchanged |
| Claude L5 — `text-transform:capitalize` capitalises every word, links too | FOLDED: only the first letter is uppercased (`::first-letter`) |
| Codex — the `_kept` prefix lost markup sensitivity | Accepted: the case checks content order; the new title case carries the markup assertion |

Self-test 440/440; the goal-tree mutation slice killed 340/340, each attributed to the case it names.

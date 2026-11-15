# goal-wait-derive (PR #592, backlog #650) — round 4, coordinator

REVIEW GAP: codex — alternation (round 4 is the Claude half; rounds 2+ alternate, `docs/review-method.md` → *Round topology*).

Claude round 4 (`docs/reviews/claude/goal-wait-derive-r4-claude.md`), at `fd1afef1`, reviewing the Phase 6 redesign
(`docs/reviews/coordinator/architecture-review-2026-11-15-goal-wait-derive.md`): **CONVERGED**, 0 BLOCKER, 0 MAJOR, 4 MINOR.

| # | Severity | Finding | fix_induced | Disposition |
|---|---|---|---|---|
| F1 | MINOR | a done prerequisite alarms while another declared one is still open | false | FILED backlog #654 (round cap) |
| F2 | MINOR | a ref that does not exist reads `state not read` forever, hiding an idle item | false | FILED backlog #654 |
| F3 | MINOR | three live-corpus counts in the prose are wrong (6→4 thread lines; 8 ledger waits / 3 dated → 3 / 1) | false | FILED backlog #654 |
| F4 | MINOR | the dashboard entry over-claims the session-start list | false | FILED backlog #654 |

**The redesign held:** no finding is caused by it, so the thrashing that armed Phase 6 is not continuing. Self-tests
goal-tree 536/536, session-state 144/144; anchor resolve `manifests=96 entries=5232 problems=0`; 10 new mutations
hand-applied, all red on their named case.

Outcome: stopped. The stream closes at round 4 (round cap, `docs/review-method.md` §0 Q4c); findings are filed, not folded.

## The merge gate's HOLD (check-merge-ready, 7 flagged lines in `scripts/session-state.py`), verified line by line by the coordinator

Every flagged line, read in `git diff origin/master...HEAD`:
- `552f8a67e4b2` (`:53`): the usage line now names `--after` as required. Stricter.
- `10c519088e11`, `cd83edd00295`, `91a65f397563` (`:1183`–`:1185`): the backlog #514 (c) case's calls gain `--after none`, so they still reach the goal/thread refusal now that `--after` is required. The case still asserts exit 2.
- `08e25662ec2a` (`:1582`): the stray-flag tuple gains `--after` outside `--add`, a new refusal. Stricter.
- `526b5dab06a1` (`:1589`): the "using <ledger>" note now also prints for `--set-after`. A message only, no gate.
- `f4b740628901` (`:1609`): `--add` now passes `parse_after(args.after)`, which raises on a malformed list. Stricter.

## Loosening answers
LOOSENING-CHECK 552f8a67e4b2: not a loosening
LOOSENING-CHECK 10c519088e11: not a loosening
LOOSENING-CHECK cd83edd00295: not a loosening
LOOSENING-CHECK 91a65f397563: not a loosening
LOOSENING-CHECK 08e25662ec2a: not a loosening
LOOSENING-CHECK 526b5dab06a1: not a loosening
LOOSENING-CHECK f4b740628901: not a loosening

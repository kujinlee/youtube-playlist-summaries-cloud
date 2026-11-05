<!-- codex-review: model=gpt-6.1-sol -->

Found three issues in `d3fe1235`:

1. **High — malformed frozen states crash snapshot/print and page rendering.** At `scripts/goal-tree.py:1200`, `{"n": [], "state": "merged"}` passes `_agenda_records()` but crashes `agenda_history()` with an unhashable-list `TypeError`. I reproduced this through fixture-backed `main(["--snapshot", "--print"])`; its handler catches only `Malformed`. Separately, `{"n": 1, "state": {"bad": 1}}` survives history construction but crashes `agenda_html()` through `step_glyph()`. Missing states safely become `cannot`; malformed entries do not.

2. **Medium — same-minute agenda replacements produce false step transitions.** At `scripts/goal-tree.py:535`, `changes()` compares `at`, ignoring agenda identity. My probe replaced agenda ID 1 with ID 2 at the same timestamp, changing step 1 from backlog #1 to backlog #2. It emitted:
   ```
   agenda step 1: next → ✅ merged — B
   ```
   These are different steps in different agendas. Agenda identity must gate state comparisons.

3. **Medium — older snapshots assert unsupported absence.** At `scripts/goal-tree.py:1474`, an absent `agenda` key renders **“AGENDA — none recorded.”** I replayed a pre-agenda snapshot successfully, but its missing field establishes only that agenda information was not captured. Distinguish unavailable information from an explicitly empty agenda.

Verification completed:

- Self-test: **305/305**; docstring says **305**.
- Manifest: **191** entries, matching the pin.
- Every mutation anchor occurs exactly once.
- All **39** mutations named with “backlog #499” fail their named cases on a temporary scripts copy, without tracebacks.
- Escaping/link probes, shared-ref tags, free/malformed exclusions, and past-snapshot tags passed.
- Both older snapshot formats render without crashing.

Tracked files remain unchanged. Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED

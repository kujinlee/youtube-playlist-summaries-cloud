# Round 1 — `sweep-pin-select` (PR #526, backlog #533) — coordinator — NOT CONVERGED (Claude half); one Medium and two Lows FIXED

Codex half: `docs/reviews/codex/sweep-pin-select-r1-codex.md` (CONVERGED, no findings). Claude half:
`docs/reviews/claude/sweep-pin-select-r1-claude.md` (NOT CONVERGED). Both reviewed `b5396580`.

```yaml
round: 1
fixes_nontrivial: true
subject: sweep-pin-select
halves:
  codex: ran
  claude: ran
findings:
  - {id: C-F1, severity: Medium, aim: deliverable, fix_induced: false, component: merge-ready-pins, disposition: fixed}
  - {id: C-F2, severity: Low, aim: deliverable, fix_induced: false, component: plan-code-pins, disposition: fixed}
  - {id: C-F3, severity: Low, aim: deliverable, fix_induced: false, component: selftest-counts, disposition: fixed}
```

**C-F1 — FIXED, fail-closed.** After the move, `check-merge-ready` read the pins at its own constant `PINS_FILE`,
while the harness enforced whatever ITS `PINS_FILE` named. The reviewer's scenario passed as READY: the head harness was
repointed at a new `pins_v2.py` holding a lowered pin, and the stale `expected_mutations.py` was left in place. Before
the move, the same rebinding was CANNOT RUN. Now `pin_pair` reads HEAD's `check-plan-code.py` from the head tree,
using `ast` and never executing it, whenever HEAD keeps its pins in `PINS_FILE`. `harness_binding_problems` (pure)
requires the following, at module level:
- exactly one write of `PINS_FILE`, and it is the same literal this script reads;
- exactly one write of `EXPECTED_MUTATIONS`, and it is exactly `read_pins(own_pins_path())[0]`.

Anything else raises `PinsUnreadable`, which is CANNOT RUN. Cases:
- **the reviewer's exact scenario**, built on the REAL harness and the REAL pins file: CANNOT RUN;
- the real harness binds (the adjacent negative);
- seven rebindings refused: another source, `{}`, `or {}`, a second module write, a `global` write in a function,
  a second `PINS_FILE`, and a `del`;
- four bad `PINS_FILE`s refused: a different literal, a computed one, `None`, and a harness that does not parse;
- a binding nested under `if` is not at module level.

Three mutations, each red via its named case on a temp copy with `HOME` redirected:
- the check skipped in `pin_pair`;
- `!= 1` relaxed to `< 1`;
- the module-level test dropped.

The `main()` fixture `_fake` now answers the harness path with a bound harness.

⚠ BOUND, stated in the code:
- the BODIES of `own_pins_path` and `read_pins` are trusted, like any harness code the same PR can edit;
- a head with NO harness is not checked here, because deleting the mutation gate is not a pin falling.

**C-F2 — FIXED by giving the reason a consumer, not by retiring the mutation.** `own_pin_problems` reread the file
itself and ignored `read_pins`'s reason. It now delegates to the new `pin_file_problems(path, effective)`, which calls
`read_pins`, reports its reason when there is one, and otherwise compares key by key (`pin_differences`, extracted
from `pin_display_problems`). The second read is gone.
- New case: an unreadable or missing pins file, against `effective={}` (what an import holds then), is REPORTED with
  the reason; a readable one is compared key by key (the adjacent negatives).
- The mutation `return {}, None` now also names that case and the `--mutate` refusal case, so its name no longer
  claims a consumer that did not exist.
- The existing "reads as AGREEMENT" mutation is RE-BOUND to the new code (`return [why]` → `return []`) and also names
  the new case.

Both are red via every case they name.

**C-F3 — FIXED.** The `check-selftest-counts.reached` docstring no longer says `check-plan-code.py` holds every
script's path. It says the pins moved to `scripts/mutations/expected_mutations.py`, which is not a `scripts/*.py`
source there, so that over-selection cost shrank.

**Also in this commit (owner input 2026-11-06 09:46):** the backlog #534 row records that "skip shards whose inputs are
unchanged since a green run" was considered and REJECTED for PR CI, with three reasons:
- the whole-tree key saves almost nothing;
- the per-shard key rests on a dependency model with known holes;
- the batch sweep already adapts the cadence.

Self-tests: `check-merge-ready` 259 → 264, `check-plan-code` 321 → 323. Pin: `scripts/check-merge-ready.py` 99 → 102
in `scripts/mutations/expected_mutations.py`. `check-plan-code.py`'s pin is unchanged at 182: one entry was renamed,
one re-bound, and none was added.

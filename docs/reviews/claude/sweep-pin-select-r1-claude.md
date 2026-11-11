Reviewed head: b5396580e948be238c887927047b9195a9bd62d3

# sweep-pin-select (PR #526, backlog #533) — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` in worktree `.claude/worktrees/sps`. The change moves the
mutation pins out of `scripts/check-plan-code.py` into `scripts/mutations/expected_mutations.py`, so
a pins-only diff is selected like any other change instead of forcing the FULL sweep.
`check-merge-ready.py` reads the new file and falls back to the old dict when the new file is absent.

## What was run (evidence)

| Check | Result |
|---|---|
| `python3 scripts/check-plan-code.py --self-test` | `321/321 passed`, rc=0 |
| `python3 scripts/check-merge-ready.py --self-test` | `259/259 self-test cases passed`, rc=0 |
| Real-tree `select_manifests` (imported, `sweep_sources` + `module_sources` of this tree): pins-only diff | `diff-scoped: 12 of 88`: canonical-source, diff-coverage, docs, fixture-git-isolation, fixture-variation, main-drivable, **merge-ready**, page-links, ratchet-contract, selftest-counts, storage-independence, gates-for-pr |
| ...pins + `scripts/mutations/check-plan-code.json` | 13 (the 12 + `check-plan-code.py` via rule 6). The changed manifest's target is not skipped |
| Each NEW or EDITED mutation (2 edited + 2 new in `check-merge-ready.json`, 4 new in `check-plan-code.json`) applied to a fresh `git archive HEAD` copy, then the target's `--self-test` run | **8/8 red via every case each entry names** (expected-hit 1/1, 1/1, 2/2, 1/1, 2/2, 1/1, 1/1, 2/2). The extra `node_modules/typescript` reds are an artifact of my copy, which has no `node_modules` |
| Grep of `scripts/`, `.github/`, `.githooks/` for code reading `EXPECTED_MUTATIONS` / `declared_total` / `pin_drift` / the pins | Code readers are only `check-plan-code.py` and `check-merge-ready.py`. Other hits are comments (`check-ratchet-contract.py:309,449`, `check-selftest-counts.py:190,628`, `ci.yml:870`, which was updated). Living docs (`process-checklists.md`, `portable-practices.md`) name `EXPECTED_MUTATIONS` without a location. Backlog, memory and explainer hits are history |
| `check-ratchet-contract`, `check-guard-coverage`, `check-canonical-source`, `check-docs`, `check-fixture-git-isolation` on the head | all rc=0 (the new `.py` under `scripts/mutations/` trips no walker) |
| Python 3.12 (the CI pin): `ast.parse` of a source with a NUL byte | `SyntaxError`, which `pin_display` catches. A NUL byte in the pins file is therefore refused, not an import crash |

Attempts that did NOT break it:
- **Pin values.** A wrong pin in the pins file is refused by `pin_drift` over the real manifests (case at
  `check-plan-code.py` ~5512). The self-test step runs unconditionally in `verify`, whatever the selection.
- **Empty or malformed display.** An `EXPECTED_MUTATIONS = {}` display gives `own_pin_problems` [] and
  `pin_drift` "no declared pin" for every manifest, so it is red. In `check-merge-ready` it reads as every
  pin removed, a HOLD.
- **Unreadable display.** A display that is not a dict, has a duplicate key or a `**` splat, or does not
  parse is refused by `pin_display`. That is CANNOT RUN at both readers.
- **The base or head layout changing across the move**, in all four combinations:
  - pre/pre: the old file at both revisions;
  - pre-base/post-head: HELD (new case);
  - post-base/post-head: the pins file;
  - post-base with a head that deletes the pins file: CANNOT RUN (new case). A head that restores a
    harness display is read from that display.
- **The working directory.** `check-merge-ready._run` uses `cwd=ROOT`, so `ls-tree`'s cwd-relative
  pathspec is anchored.

## Findings

### F1 — Medium — the loosening detector reads a FILE NAME, and nothing ties it to the pins the harness enforces

- **Where.** `scripts/check-merge-ready.py:1000` hard-codes `PINS_FILE`, and `pins_home` (:1022) chooses
  the file. `scripts/check-plan-code.py:1428` (`PINS_FILE`), :1431 (`own_pins_path`) and :1450
  (`EXPECTED_MUTATIONS = read_pins(own_pins_path())[0]`) decide what is enforced.
- **What changed.** Before the move, `check-merge-ready` read the display inside the harness that
  executed it. Any rebinding of `EXPECTED_MUTATIONS` (to a loader, another file, or a computed value)
  stopped being a single literal display, so `pin_display` refused it (CANNOT RUN). Now `check-merge-ready`
  reads whatever sits at its own constant path. The harness reads whatever ITS constant names.
  `own_pin_problems` compares the harness's dict with the harness's file, so the two always agree with
  each other. Nothing asserts that the harness's file is the one `check-merge-ready` read.
- **Failure scenario (constructed and run).**
  1. Copy this head's `scripts/` into a fresh git repo and commit it as `base`.
  2. On the head:
     - set `PINS_FILE = "scripts/mutations/pins_v2.py"` in `check-plan-code.py`;
     - add `pins_v2.py` as a copy of the pins file with `check-anchors.py` lowered 5 -> 4;
     - delete one entry from `check-anchors.json`;
     - leave `expected_mutations.py` untouched.
  3. Results:
     - `check-merge-ready.pin_pair` + `pin_falls`: `[]`;
     - `hold_reasons(files, diff, …)`: `[]`. This is **READY**, with no HOLD;
     - the head harness: `own_pin_problems()` gives `[]` and `EXPECTED_MUTATIONS["scripts/check-anchors.py"]`
       gives `4`;
     - `pin_drift` over the head manifests: `[]`.

  The FULL sweep this harness edit triggers would be green. The coverage of `check-anchors.py` shrank
  5 -> 4, and the gate built to HOLD exactly that (backlog #359) reports READY. Whether the stale
  `expected_mutations.py` is kept on purpose or left behind by a rename, the result is the same.
- **Why Medium, not Blocking.** It needs an edit to the harness. That edit is visible in the diff, and a
  rename that DELETES the old file is still caught (CANNOT RUN, new case). This is a regression against
  the pre-move structure, not a hole that already existed.
- **Possible fixes.**
  - Make `check-merge-ready` read HEAD's harness `PINS_FILE` literal (via `ast`, like `pin_display`) and
    refuse when it differs from its own `PINS_FILE`. Also refuse when the head harness's
    `EXPECTED_MUTATIONS` binding is not exactly `read_pins(own_pins_path())[0]`.
  - Or HOLD any diff line in `check-plan-code.py` that touches `PINS_FILE`, `own_pins_path` or
    `EXPECTED_MUTATIONS =`.
  - Either fix needs a case built from the scenario above.

### F2 — Low — `read_pins`'s "reason" has no production consumer, so its case and mutation guard output nobody reads

- **Where.** `scripts/check-plan-code.py:1436-1447` (`read_pins` returns `({}, WHY)`) and :1450, which
  keeps only `[0]`. The mutation is "backlog #533: an unreadable pins file is a silent {}, with no reason
  for the consumer to report" (`scripts/mutations/check-plan-code.json`, last entry).
- **Evidence.** `grep -n "read_pins(" scripts/*.py`: the only call outside the self-test is :1450, and it
  discards `[1]`. The refusal that actually protects `--mutate` and `--self-test` is
  `own_pin_problems` (:1453), which REREADS the file itself.
- **Failure scenario.** Apply the mutation (`return {}, None`). Only the two `read_pins` unit cases go red.
  Every consumer still refuses correctly, because none of them reads the reason. The mutation's name
  claims "the consumer" loses a reason it never received.
- **Not unsound.** The guard holds. But the entry pins a contract with no consumer, and that can mislead
  the next editor into thinking the reason is load-bearing.
- **Fix.** Either have `own_pin_problems` use `read_pins(own_pins_path())[1]`, which removes the second
  read and gives the reason a consumer. Or drop the tuple and the mutation's claim.

### F3 — Low — stale comment in `check-selftest-counts.reached` about the dict this PR moved

- **Where.** `scripts/check-selftest-counts.py:628-630`: "`check-plan-code.py` holds every script's path as
  a dictionary KEY (`EXPECTED_MUTATIONS`), so a change to any of them reaches it". After this PR the keys
  live in `scripts/mutations/expected_mutations.py`. That file is not a `scripts/*.py` source in `reached`.
- **Effect.** The over-selection the docstring describes as the accepted cost is now partly gone. The
  comment explains a mechanism that no longer exists. The behaviour is not unsafe:
  - the scope is local only (backlog #402), and CI runs every self-test;
  - `check-plan-code.py` still quotes `expected_mutations.py`, so a pins change still reaches it.
- **Line 190** (`check-plan-code.EXPECTED_MUTATIONS`) still names a real module attribute and is fine.

## Verdict

F1 is a real regression in the merge-time loosening detector, and it was demonstrated end to end.
The selection, `pin_drift`, the fallback across the move, and the fail-closed paths all held under
the inputs I built. The new cases and mutations are each killed by the cases they name.

VERDICT: NOT CONVERGED

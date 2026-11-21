# Round 4 — `marketplace-task16` — coordinator — NOT CONVERGED; §6 STOP → owner

Both halves ran r4 on 7f54a324 (the Phase 6 build b3051290 and its rescan), as §6 of
`docs/reviews/architecture-review-2026-11-21-publishability-install-root.md` requires, each briefed to REFUTE §4.1.
Codex: `docs/reviews/codex/marketplace-task16-r4-codex.md` (one MAJOR, NOT CONVERGED). Claude:
`docs/reviews/claude/marketplace-task16-r4-claude.md` (B1, M1, M2, m1, NOT CONVERGED).

**B1 is a silent hand-on CAUSED BY THE BUILD — verified by the coordinator, not taken from the review.** Fresh copies of
`scripts/check-publishability.py` (+ `check-shipping-sets.py`) from `git show` at b79d4bad and HEAD, run through
`_install_root_uses(tree, parent, 2, ...)`:

| Input | b79d4bad | 7f54a324 |
|---|---|---|
| `SCRIPT_DIR = Path(__file__).resolve().parent; REPO = SCRIPT_DIR.parent`; `def main(argv): SCRIPT_DIR = ...`; `cwd=REPO` | `[(7, '.')]` | `[]` |
| the same with `def load(SCRIPT_DIR=SCRIPT_DIR)` | `[(7, '.')]` | `[]` |
| control: no reuse | `[(5, '.')]` | `[(5, '.')]` |

That is §6's observation 3: **stop, do not fold a second time on this rule, and take it to the owner with the input.**
No code changed this round. The PR is not merged while the owner's answer is outstanding.

Every other finding was silent before the build too (each reviewer re-ran it at b79d4bad), so none is a regression; from
r4 non-BLOCKER findings are filed (round cap), and all four are one mechanism with B1, filed together as backlog #692.

```yaml
round: 4
fixes_nontrivial: false
subject: marketplace-task16
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocker, aim: deliverable, fix_induced: true, component: publishability-install-root, disposition: deferred}
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: filed}
  - {id: M1, severity: Major, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: filed}
  - {id: M2, severity: Major, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: filed}
  - {id: m1, severity: Minor, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: filed}
```

X1 is Codex's MAJOR (`os.chdir(Path(__file__).parent.joinpath(x).parent)`). B1 is deferred to the owner, not to a later
round: the remaining option §6 names is (a0)'s direction for the affected form (report the mention itself), and r4
Claude proposes one rule that would close B1, X1, M1 and M2 together (report a stop below the install depth as
unjudged) — both change the rule, which is the owner's call.

# Round 1 — `610-read-at-origin` (PR #561, backlog #610) — coordinator — both NOT CONVERGED; the design was WITHDRAWN

```yaml
round: 1
fixes_nontrivial: true
subject: 610-read-at-origin
halves:
  claude: ran
  codex: ran
findings:
  - {id: CL1, severity: High, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: CL2, severity: High, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: CL4, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
  - {id: X5, severity: High, aim: deliverable, fix_induced: false, component: goal-tree-collect, disposition: fixed}
```

Claude (`docs/reviews/claude/610-read-at-origin-r1-claude.md`) and Codex (`docs/reviews/codex/610-read-at-origin-r1-codex.md`).

**CL1 refuted the premise.** Every build path of the served page (the Refresh button, `/goal-tree`, the edit hook)
runs `regen-pages.py`, which builds in a private clone at a fresh `origin/master` (backlog #408). Inside it the
`git show origin/master:` reads equal the disk reads and the lag is always 0. Verified by hand: `regen-pages.py`
`launch` runs the generator with `cwd=tree`; `.claude/commands/goal-tree.md` and `.claude/hooks/regen-goals-page.sh`
both go through it. The 14:58 stale page came from a BARE `python3 scripts/goal-tree.py`, run by the coordinator after
recording an agenda, whose default `--out` is the served `~/explainers/goal-tree.html`. (The 18:48 symptom was the
agenda: `.claude/agenda-log.jsonl` agenda #10 named neither PR #559 nor PR #560; agenda #11 at 18:50 did.)

**The design is withdrawn, so every finding against it is closed by removal:** CL2/X3 (threads and link rows read
from a different tree than the backlog), CL3/X4 (lossy decoding of `git show`), CL4/X2 (the `--ff-only` advice),
X1 (a narrowed refspec leaves `origin/master` stale), X5 (the dashboard read was unpinned). `scripts/goal-tree.py`
`collect` is back to `origin/master`'s.

**The replacement** (a redesign, so the round count restarts under the rule PR #553 added; this branch is PR #561): `main` refuses `--page` to the default `--out`
when `REGEN_MAIN_CHECKOUT` (set only by `regen-pages.py launch`) is absent — CANNOT RUN, rc 2, before anything is
logged. Five cases, three mutations (each red against its named case, run by hand), pin 364 -> 367. A new round 1
reviews it under review id `610-served-page`.

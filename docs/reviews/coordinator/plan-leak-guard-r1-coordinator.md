# Round 1 — `plan-leak-guard` (PR #443, backlog #393) — coordinator — NOT CONVERGED (Codex); a redesign, with ACCRETE skipped

REVIEW GAP: claude — the Codex half's eight Blocking findings share one cause that a redesign removes, so the Claude half reviews the redesigned guard in round 2 rather than the mechanism being replaced.

```yaml
round: 1
fixes_nontrivial: true
subject: plan-leak-guard
halves:
  codex: ran
  claude: "GAP: redesign before review; the Claude half reviews the redesigned guard in round 2"
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: false, component: push-detection, disposition: fixed}
  - {id: X2, severity: Blocking, aim: deliverable, fix_induced: false, component: push-detection, disposition: fixed}
  - {id: X3, severity: Blocking, aim: deliverable, fix_induced: false, component: push-detection, disposition: fixed}
  - {id: X4, severity: Blocking, aim: deliverable, fix_induced: false, component: push-detection, disposition: fixed}
  - {id: X5, severity: Blocking, aim: deliverable, fix_induced: false, component: diff-reader, disposition: fixed}
  - {id: X6, severity: Blocking, aim: deliverable, fix_induced: false, component: diff-reader, disposition: fixed}
  - {id: X7, severity: Blocking, aim: deliverable, fix_induced: false, component: public-filter, disposition: fixed}
  - {id: X8, severity: Blocking, aim: deliverable, fix_induced: false, component: plan-discovery, disposition: fixed}
  - {id: X9, severity: High, aim: deliverable, fix_induced: false, component: diff-reader, disposition: fixed}
  - {id: X10, severity: High, aim: deliverable, fix_induced: false, component: public-filter, disposition: fixed}
  - {id: X11, severity: High, aim: deliverable, fix_induced: false, component: output-channel, disposition: fixed}
  - {id: X12, severity: Low, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
```

Codex reviewed `125a9d78` and found eight Blocking defects; it used synthetic plans only. Four of them (X1–X4) share ONE cause: the guard infers from a shell COMMAND'S TEXT what a push will send. Command text cannot settle that:
- what is pushed is history, not the endpoint tree (X1);
- the refs pushed are not HEAD (X2);
- `git -C`, `-c`, aliases and `cd &&` forms bypass detection (X3);
- a comment can trigger the escape (X4).

This is the class this repository calls the wall: a check that infers a property of arbitrary input which the input can defeat.

**Redesign: git's own `pre-push` hook.** Git invokes it for every push, whatever the command, alias or directory, and tells it on stdin exactly which local and remote objects each ref update sends. The guard scans every commit in `remote_sha..local_sha` for each ref (all refs and tags, and history rather than the endpoint), with `--text` (X6) and unquoted paths (X5). "Public" means present at the REMOTE's sha that git reports, not a local `origin/master` (X7). A plan-discovery failure blocks (X8). Consecutive added lines in a hunk are joined before windowing (X9), and the public filter uses the same normalisation as the matcher (X10). The output names `path:line` and the plan file only. The phrase is shown only by a separate `--show` command the owner runs by hand (X11). Git-option forms get cases (X12). The Claude Code PreToolUse hook is REMOVED, so one mechanism owns the decision. The hook directory is tracked and enabled with `core.hooksPath`.

**ACCRETE is skipped, with a reason** (see the decision log): patching the command parser cannot close X1 or X2 at all, because the information is not in the command.

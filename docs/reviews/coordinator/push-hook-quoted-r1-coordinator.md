# Round 1 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — NOT CONVERGED (both halves)

```yaml
round: 1
fixes_nontrivial: true
subject: push-hook-quoted
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-F1, severity: High, aim: deliverable, fix_induced: false, component: detector-regex, disposition: fixed}
  - {id: X-F2, severity: High, aim: adjacent, fix_induced: false, component: destinations, disposition: split}
  - {id: X-F3, severity: Medium, aim: adjacent, fix_induced: false, component: destinations, disposition: fixed}
  - {id: X-F4, severity: Low, aim: adjacent, fix_induced: false, component: input, disposition: fixed}
  - {id: C-F1, severity: High, aim: deliverable, fix_induced: false, component: normalise, disposition: fixed}
  - {id: C-F2, severity: Medium, aim: deliverable, fix_induced: false, component: segments, disposition: fixed}
  - {id: C-F3, severity: Medium, aim: deliverable, fix_induced: false, component: settings-filter, disposition: fixed}
  - {id: C-F4, severity: High, aim: adjacent, fix_induced: false, component: destinations, disposition: fixed}
  - {id: C-F5, severity: Medium, aim: adjacent, fix_induced: false, component: destinations, disposition: fixed}
  - {id: C-F6, severity: Low, aim: adjacent, fix_induced: false, component: destinations, disposition: filed}
  - {id: C-F7, severity: Low, aim: adjacent, fix_induced: false, component: input, disposition: fixed}
  - {id: C-F8, severity: Low, aim: deliverable, fix_induced: false, component: latency, disposition: fixed}
```

Codex (`docs/reviews/codex/push-hook-quoted-r1-codex.md`) and Claude (`docs/reviews/claude/push-hook-quoted-r1-claude.md`)
both reviewed `ed8e0ac4`.

**Held, per both halves:**
- the quoted, `-c`, `sh -c`, `eval`, `env`, `-C` and `GIT_DIR=` forms are refused;
- `--force`, `--no-verify`, hooksPath and ALLOW_PLAN_LEAK are intact;
- a missing detector refuses;
- the coordinator's real push line is allowed;
- the mutations hand-checked red.

**Fixed in the round 1 fold:**
- the backtracking hang (X-F1): bounded scanning plus an internal deadline that refuses;
- the backslash line continuation (C-F1);
- the new over-refusal (C-F2): only real `git … push` segments are read, and `git stash push` is not a push. The documented cost is restated to match;
- the `Bash(*push*)` settings filter (C-F3): measured, then widened or bounded;
- closing shell syntax in a destination (X-F3, C-F5): unresolved shell syntax is refused;
- `HEAD`, `@` and `+master` on the default branch (C-F4, part of X-F2);
- malformed input and a missing `jq` (X-F4, C-F7): both fail closed;
- the hook's own self-test is added to CI (C-F7);
- latency (C-F8): lazy imports.

**Filed as backlog #574** (X-F2's remainder and C-F6): `--all`, `--mirror` and configured destinations
(`push.default`, `remote.<r>.push`). These need the repository's config, not the command text. They predate this
branch and lie outside backlog #428.

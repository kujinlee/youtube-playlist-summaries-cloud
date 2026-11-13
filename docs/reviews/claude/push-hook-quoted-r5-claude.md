Reviewed head: 822fccb8cac707ceaf9528d01bcdddcd5d635a8d

# Round 5 — `push-hook-quoted` (PR #542, backlog #428) — Claude half

Codex skipped this round by alternation. This round is past the round cap, so only a BLOCKER is folded. The
BLOCKER definition is (a) a command the branch ALLOWS that master's hook (`origin/master`) refuses, or (b) one that
reaches the default branch, `--force`, `--no-verify`, `core.hooksPath` or `ALLOW_PLAN_LEAK` without a refusal.

**Mandate.** Refute the r4 fold by finding the NEXT member of each r4 class: the reader (X-F1), a branch change
(X-F2) and an option value (X-F3).

**Method.** Every repro below was fed as crafted JSON on stdin to this worktree's hook and to master's hook
(`git show origin/master:.claude/hooks/block-default-branch-push.sh`). Both ran with their cwd set to a scratch
fixture clone: `origin/HEAD` is `master`, the current branch is `feat/x`, and `GIT_CONFIG_GLOBAL=/dev/null`.
Reader candidates were run through the check's own `_bash_runs` / `_oracle_patterns` (`/bin/bash` 3.2). Git
side effects were confirmed in the fixture only when they did not involve a push: an editor runs, an alias,
`A+=1` and `nice` each change the branch, and `xargs` builds the argv. No `git push` was run. Where a finding rests
on git's push semantics, the documentation is quoted and the behaviour is NOT executed.

**Gates run at head:**
- `python3 scripts/push-command.py --self-test`: **325/325**.
- `bash .claude/hooks/block-default-branch-push.sh --self-test`: **59/59**.
- Mutations hand-checked one at a time, each in a `check-plan-code.stage_tree` copy with its edit applied:
  - `git stash branch` is not a mover: rc 1, one FAIL, the named case.
  - `-C` does not make the current branch unknown: rc 1, four FAILs, the named case among them once.
  - a push-option value beginning with `-` is not refused: rc 1, one FAIL, the named case.

**Result.** The r4 fold fixed exactly its three repros. Every class has a next member, and eight of them are
BLOCKERs under the definition above.

---

### R5-F1 — Blocking — A redirection target hides `master`, `--force`, `-f` and `--no-verify`, which master refused (class: option values)

**Location:** `scripts/push-command.py:186-187` (a redirection target is dropped, never judged) and `:251`.

**Repros (cwd on `feat/x`):**

| command | master | branch |
|---|---|---|
| `git push origin feat/x > master` | DENY | **ALLOW** |
| `git push origin feat/x 2> master` | DENY | **ALLOW** |
| `git push origin feat/x >> master` | DENY | **ALLOW** |
| `git push origin feat/x < master` | DENY | **ALLOW** |
| `git push origin feat/x > --force` | DENY | **ALLOW** |
| `git push origin feat/x > -f` | DENY | **ALLOW** |
| `git push origin feat/x > --no-verify` | DENY | **ALLOW** |
| `git push origin feat/x -o x > master` | DENY | **ALLOW** |
| `git push origin feat/x --push-option=x > master` | DENY | **ALLOW** |

Master reads every whitespace-separated token after `push` up to `;&|` as a flag or a refspec, so a spaced target
is a token there. The branch drops it.

**Why it is a BLOCKER.** It costs no safety, because the push itself is a feature push. But it is the literal
X-F3 shape: the branch allows what master refused. Clause (a) binds it, and so do the loosening answers.

**Fix:** keep each redirection target of a `git push` command. Refuse it, as master did, when it names the
default branch or begins with `-` (unless `ALLOW_DANGEROUS_PUSH=1`). Add the repros as cases.

### R5-F2 — Blocking — A `-c` value or an assignment prefix that git RUNS is exempt on an inert subcommand (class: option values / reader)

**Location:** `scripts/push-command.py:393-394`. `if sub in INERT_SUB: return None` runs before the `pushy` test,
so the push words inside a `-c` value never count. The assignment prefixes skipped at `:358` are never read at all.

**Repros:**

| command | master | branch |
|---|---|---|
| `git -c core.editor='git push origin master ' commit` | DENY | **ALLOW** |
| `git -c core.pager='git push origin HEAD:master;:' log` | DENY | **ALLOW** |
| `GIT_EDITOR='git push origin HEAD:master;:' git commit --allow-empty` | ALLOW | **ALLOW** |
| `GIT_EXTERNAL_DIFF='git push origin HEAD:master;:' git diff` | ALLOW | ALLOW |

- **The `GIT_EDITOR` prefix form really runs.** In the fixture,
  `GIT_EDITOR="echo EDITOR-RAN > marker; :" git commit --allow-empty` wrote the marker. Git runs the editor through
  the shell, so the `;` ends the push's arguments and `git push origin HEAD:master` runs. That is clause (b).
- **The `-c core.editor` form is clause (a).** It is also live wherever `GIT_EDITOR` is unset. In this session's
  environment `GIT_EDITOR=true` overrides it, and with `env -u GIT_EDITOR` the config editor ran too.
- `core.pager` runs only on a tty.

**Fix:** a git command whose `-c` / `--config-env` values, or whose assignment prefixes, hold a push word refuses,
whatever its subcommand (`code-runner`). `git commit -m "…push…"` stays allowed, because the push word there is in
a positional argument.

### R5-F3 — Blocking — `xargs` / `parallel` take their argv from stdin, so `echo push origin HEAD:master | xargs git` passes (class: reader / code runner)

**Location:** `scripts/push-command.py:399-406`. `xargs git` has no push word, no unknown word, no `-c`/`-e`/`-`,
and `xargs` is not in `STDIN_CODE`, so it returns None.

**Repros:**

| command | master | branch |
|---|---|---|
| `echo push origin HEAD:master \| xargs git` | ALLOW | **ALLOW** |
| `printf 'push origin HEAD:master' \| xargs git` | ALLOW | **ALLOW** |
| `echo push origin master \| xargs git` | ALLOW | **ALLOW** |
| `echo push origin master \| parallel git` | ALLOW | **ALLOW** |

The text mentions push, so it reaches the judge, and the push reaches `master` without a refusal (clause (b)).
`echo p1 o2 H:m | xargs printf '[%s]'` printed `[p1][o2][H:m]`, so xargs appends the stdin words as arguments.

**Fix:** in a text that mentions push, `xargs` and `parallel` refuse unconditionally, because their argv is not in
the text. Put them in `STDIN_CODE` semantics regardless of positionals.

### R5-F4 — Blocking — A branch mover behind a wrapper or an alias is not recognised (class: branch change)

**Location:** `scripts/push-command.py:414-426`. `_moves` reads only `name == "git"` with a subcommand in a closed
MOVER list, so the fold enumerated movers and did not refuse non-movers.

**Repros:**

| command | master | branch |
|---|---|---|
| `nice git checkout master && git push origin HEAD` | ALLOW | **ALLOW** |
| `command git checkout master && git push origin HEAD` | ALLOW | **ALLOW** |
| `env git switch master && git push` | ALLOW | **ALLOW** |
| `timeout 9 git switch master && git push` | ALLOW | **ALLOW** |
| `nohup git switch master && git push` | ALLOW | **ALLOW** |
| `time git switch master && git push` | ALLOW | **ALLOW** |
| `git -c alias.co=checkout co master && git push origin HEAD` | ALLOW | **ALLOW** |
| `git -c alias.sw=switch sw master && git push` | ALLOW | **ALLOW** |
| `git co master && git push origin HEAD` (a configured alias) | ALLOW | ALLOW |

In the fixture, `git -c alias.co=checkout co -q master` and `nice git switch -q master` each left HEAD on `master`.
The push that follows is judged against `feat/x` and pushes `master` (clause (b)).

**Fix:** invert the rule. In a text with a git push, refuse:
- any git invocation whose subcommand is not in a closed NON-moving list (`push`, `status`, `log`, `diff`,
  `add`, `commit`, `fetch`, …); an alias is then refused because it is not on the list;
- any code runner or wrapper whose arguments name `git`.

### R5-F5 — Blocking — `A+=1` is an assignment to bash, a command word to the reader (class: reader)

**Location:** `scripts/push-command.py:116` (`ASSIGN` matches `NAME=` only, not `NAME+=`).

The check's own oracle, run on `A+=1 git push o m`:
- the lexer reports the command `['A+=1', 'git', 'push', 'o', 'm']`;
- bash runs `git push o m`;
- the result is **UNSAFE**.

The direct push is still refused (`A+=1` is an unknown command holding a push word). But the disagreement reaches
a discard: the R5-F4 rule never sees the git command behind it.

| command | master | branch |
|---|---|---|
| `A+=1 git checkout master && git push origin HEAD` | ALLOW | **ALLOW** |
| `A+=1 git switch master && git push` | ALLOW | **ALLOW** |

In the fixture, `A+=1 git checkout -q master` moved HEAD to `master`.

**Fix:** `ASSIGN = r"[A-Za-z_][A-Za-z0-9_]*\+?="`. Add `A+=1 git push o m` to `ORACLE_INPUTS` and `"A+=1"` to
`ORACLE_ATOMS`. The seeded corpus has no `+=` atom, which is why it stayed green.

### R5-F6 — Blocking — The destination is reconfigured in the same text (class: branch change, the `remote.<name>.push` / `push.default` question)

**Location:** `scripts/push-command.py:331-349`. `_judge_push` reads only the command-line refspec. A `-c` value
(`:371-374`), a `git config` write (not inert, but not pushy, so None at `:397`) and `GIT_CONFIG_*` prefixes are
never read.

**Repros (all ALLOW on master and on the branch, cwd on `feat/x`):**
- `git -c remote.origin.push=HEAD:master push`
- `git -c remote.origin.push=HEAD:master push origin`
- `git -c remote.origin.push=refs/heads/feat/x:refs/heads/master push origin feat/x`
- `git config remote.origin.push HEAD:master && git push`
- `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.push GIT_CONFIG_VALUE_0=HEAD:master git push`
- `git -c push.default=matching push`
- `git -c remote.origin.mirror=true push origin`
- `git config push.default matching && git push origin`
- `git branch -u origin/master && git -c push.default=upstream push`

The git documentation (`git-push.adoc` 69-74, git 2.49) says:

> "If `git push [<repository>]` without any `<refspec>` argument is set to update some ref at the destination
> with `<src>` with `remote.<repository>.push` configuration variable, `:<dst>` part can be omitted--such a push
> will update a ref that `<src>` normally updates without any `<refspec>` on the command line."

So a named refspec does NOT fix the destination when `remote.<name>.push` maps it. The `matching`, `mirror` and
`upstream` lines come from git's config documentation and were not executed here.

**Fix:** in a text with a push, refuse any git config write (`-c`, `--config-env`, `GIT_CONFIG_COUNT`/`KEY`/
`VALUE`, `git config <key> <value>`, `git branch -u` / `--set-upstream-to`) except a closed allowlist
(`user.name`, `user.email`, …).

### R5-F7 — Blocking — The matching refspec `:` and glob refspecs push `master` (class: option values / judge)

**Location:** `scripts/push-command.py:334-344`. The destination is the text after the last `:`, so the empty
destination of `:` and the `*` destination of a glob never equal `master`.

**Repros (all ALLOW on master and on the branch):**
- `git push origin :`
- `git push origin 'refs/heads/*:refs/heads/*'`
- `git push origin 'refs/heads/m*:refs/heads/m*'`

`git-push.adoc` 142-145 says:

> "The special refspec `:` (or `+:` …) directs Git to push "matching" branches: for every branch that exists on
> the local side, the remote side is updated if a branch of the same name already exists on the remote side."

That includes `master` (clause (b)). The architecture review's own refusal of `--all`/`--mirror` names the same
effect.

**Fix:** refuse a refspec whose destination is empty, or whose source or destination holds `*`.

### R5-F8 — Blocking — `export GIT_DIR=…` changes the repository; only the prefix form was handled (class: branch change)

**Location:** `scripts/push-command.py:388-390`. `REPO_ENV` is read only from the assignment prefix of the same
git command.

**Repros:**

| command | master | branch |
|---|---|---|
| `export GIT_DIR=/elsewhere/.git && git push origin HEAD` | ALLOW | **ALLOW** |
| `export GIT_DIR=/elsewhere/.git; git push` | ALLOW | **ALLOW** |
| `declare -x GIT_DIR=/elsewhere/.git; git push` | ALLOW | **ALLOW** |
| control: `GIT_DIR=/elsewhere/.git git push` | ALLOW | DENY (the fold's case) |

The realistic `/elsewhere` is the main checkout of this same repository (`…/youtube-playlist-summaries-cloud/.git`),
whose HEAD may be `master`. Then `HEAD` pushes `master` (clause (b)).

**Fix:** treat `export` / `declare` / `typeset` / `local` / `readonly` naming `GIT_DIR`, `GIT_WORK_TREE` or any
`GIT_*` in a text with a push like a `cd`: the current branch becomes UNKNOWN. A simpler fix is to refuse
`export` beside a push.

### R5-F9 — Medium (FILE) — Naming the branch after `cd` does not make the destination independent of the cwd

The fold allows `cd X && git push origin feat/x` (ALLOW on both hooks). By the `git-push.adoc` 69-74 text quoted in
R5-F6, X's own `remote.origin.push` remaps a `<src>`-only refspec. X's `origin` may also be another repository,
whose default branch the gate never resolved. So a protected push to `main` there is `cd X && git push origin main`.

Only `src:refs/heads/<dst>` fixes the destination. This relies on configuration that is NOT in the text, and the
same is true of the current repository's own config, which neither hook reads. So it is not a BLOCKER under this
round's definition.

**File:** under `cd` / `-C`, allow only a fully qualified `src:refs/heads/<dst>` refspec, or refuse.

Also in this pre-existing, outside-the-text class, ALLOW on both hooks:
- a configured alias (`git co master && git push origin HEAD`, covered by the R5-F4 inversion);
- `hub checkout master && …`;
- `git bisect start …`;
- a script that checks out (`./x.sh && git push`).

### Failure paths (checked; no finding)

Each of the following refuses, NOT CHECKED: a detector that is missing, crashes, or exits non-zero; empty or
malformed output; an unknown rule (`[ -n "$rule" ] || deny`, the `*)` arm); deadline expiry (rc 142); jq missing;
an invalid, null or non-string payload.

An unresolved default branch disables rule 1 (`rule1 = … bool(default)`), exactly as master's
`[ -n "$default_branch" ] || allow` does, so it is not a loosening.

## Loosening answers
LOOSENING-CHECK f090c90de19b: not a loosening
LOOSENING-CHECK 2d51171ccc52: not a loosening
LOOSENING-CHECK a37789af0a0d: finding: git push origin feat/x > --force (and > -f) is now allowed but master refused it (R5-F1)
LOOSENING-CHECK 19e3cb6a182b: finding: git push origin feat/x > --force (and > -f) is now allowed but master refused it (R5-F1)
LOOSENING-CHECK 6a9e243ccfd4: not a loosening
LOOSENING-CHECK e6c86a86ce2e: not a loosening
LOOSENING-CHECK 30d52ad23ac7: not a loosening
LOOSENING-CHECK 4a4c20c73163: not a loosening
LOOSENING-CHECK e886704a5c48: not a loosening
LOOSENING-CHECK 727e65f884c9: not a loosening
LOOSENING-CHECK 484e60231961: not a loosening
LOOSENING-CHECK 2fec52dc562d: not a loosening
LOOSENING-CHECK c361c21aa22d: not a loosening
LOOSENING-CHECK 1c483d300bca: finding: git push origin feat/x > --no-verify is now allowed but master refused it (R5-F1)
LOOSENING-CHECK 0639175f96f3: finding: git push origin feat/x > --no-verify is now allowed but master refused it (R5-F1)
LOOSENING-CHECK 6ed1cdc83491: finding: git push origin feat/x > master and git -c core.editor='git push origin master ' commit are now allowed but master refused them (R5-F1, R5-F2)
LOOSENING-CHECK 475f8e419a00: finding: git push origin feat/x > master and git -c core.editor='git push origin master ' commit are now allowed but master refused them (R5-F1, R5-F2)
LOOSENING-CHECK b4c2d38505b1: finding: git push origin feat/x > master and git -c core.editor='git push origin master ' commit are now allowed but master refused them (R5-F1, R5-F2)
VERDICT: NOT CONVERGED

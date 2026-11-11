# hooks-absolute-path — round 1, Claude half (adversarial)

Subject: PR #409, branch `hooks-absolute-path`, head `3f861b99`, reviewed as `git diff origin/master...HEAD`.
Every experiment ran in a `mktemp -d` copy (`/var/folders/tg/.../tmp.O9NTd5XDd8/wt`). I replaced that copy's `.git`
file with a standalone `git init` so that no git command could touch the shared worktree's gitdir. I edited nothing
in the reviewed worktree.

## What holds (executed)

- **The fix launches.** I simulated the harness with `printf "$IN" | /bin/sh -c "$cmd"` from `scripts/`, and ran the
  same thing under `/bin/bash` and `/bin/zsh`. The input was `git push origin master`.
  - Old form: rc 127, `No such file or directory`, in all 6 combinations.
  - New form with `CLAUDE_PROJECT_DIR` set: rc 0 and `"permissionDecision":"deny"`, under all 3 shells.
  - New form with the variable unset: rc 127 from `scripts/` and rc 0 from the root. That is the old behaviour, so
    this is not a regression.
  - The new form also works when the project path contains a space (`.../sp ace/wt`): it denies.
- **The harness sets the variable.** I read this in the 2.1.308 binary (`strings`): the hook spawn env is
  `fo={...inherited..., CLAUDE_PROJECT_DIR:Kt(Bn)}` with `shell:true` and `cwd` set to the session cwd. The harness
  sets the variable itself, after the inherited env, so an ambient value cannot override it. The `:-.` arm is
  therefore unreachable under this harness. It is harmless.
- **Linked worktree, with `CLAUDE_PROJECT_DIR` set to a different checkout than the cwd.** I set
  `CLAUDE_PROJECT_DIR` to the main copy, with cwd at `<linked worktree>/scripts` on branch `feat`.
  - `git push origin master`: denied.
  - `git push origin feat` and a bare `git push`: allowed.
  - The hook script now comes from the project dir, but its `git` calls run in the cwd, so the branch it reads is
    the worktree's.
  - ⚠ Behavioural note, not a finding. Previously, a session whose cwd was exactly a linked worktree's root ran
    that worktree's copy of each hook, and `REPO_ROOT` (from `BASH_SOURCE`) resolved to the worktree. Now it always
    resolves to the project dir. This affects `regen-*` pages, the plan-gate sentinel and `block-idle-stop`'s
    `.claude/executing-plan`. The new behaviour is consistent with where the harness loads settings from (and with
    backlog #301), so I do not count it as a regression.
- **The mutations.** `check-plan-code.py --mutate . --only scripts/check-hook-commands.py` (in the copy) killed all 6
  mutations, each attributed to the case it names, with the control green before and after.
- **The neighbouring guards.** `check-ratchet-contract.py`, `check-selftest-counts.py`, `check-fixture-variation.py`,
  `check-main-drivable.py` and `check-guard-coverage.py` all gave rc 0 on the copy. The live
  `check-hook-commands.py` gave rc 0 ("13 hook command(s), every one anchored"), and `--self-test` passed 19/19.

## Findings

### M1 — Medium — `scripts/check-hook-commands.py:89-100`: commands that cannot launch from a subdirectory still pass the guard

The guard splits each command with `shlex.split` and judges tokens one at a time. `shlex` is not a shell parser, so
these constructs hide the relative path. I ran each through `problems()` with the real repo as the world. For the
second column I ran each from `scripts/` with `CLAUDE_PROJECT_DIR` set.

| command | `problems()` findings | from `scripts/` |
|---|---|---|
| `sh -c 'bash .claude/hooks/block-default-branch-push.sh'` | 0 | rc 127, no deny |
| `bash -c "bash .claude/hooks/…"` | 0 | rc 127 |
| `cd .claude/hooks && bash block-default-branch-push.sh` | 0 | rc 1, no deny |
| `FOO=.claude/hooks/… bash $FOO` | 0 | rc 127 |
| `bash $PWD/.claude/hooks/…` (also `"$PWD"/…`) | 0 | rc 127 |
| `bash .claude/hooks/….sh;` (`;` attached) | 0 | rc 127 |
| `bash .claude/hooks/….sh&&true` / `…sh\|\|true` | 0 | `\|\|true`: **rc 0, no deny** — silently green |
| `bash <.claude/hooks/…` (redirect attached) | 0 | rc 1 |
| `bash "$CLAUDE_PROJECT_DIRX/.claude/hooks/…"` (misspelt variable) | 0 | rc 127 |

For comparison, the guard does refuse the plain form and these variants: `./`, `.//`, `a//b`, `../` inside the
path, `< file` with a space, and `source file`.

`$PWD/` is the most likely of these to be pasted, because it looks anchored. `…||true` is the most dangerous,
because the launch failure becomes rc 0. `$CLAUDE_PROJECT_DIRX` passes because `ANCHORS` matches with
`str.startswith`, so `"$CLAUDE_PROJECT_DIR"` also covers any longer variable name.

**Fix:** the population is 13 commands that all have one shape. Invert the rule: accept only a positive grammar,
for example `^(bash|sh|python3) "\$\{CLAUDE_PROJECT_DIR:-\.\}"/<repo path>( <plain args>)*$`, or
`"$CLAUDE_PROJECT_DIR"` / `${CLAUDE_PROJECT_DIR}` with an exact variable boundary. Refuse everything else with a
message naming the accepted shape. That closes this whole class, rather than one token form at a time.

### M2 — Medium — `docs/backlog.md:249` (the backlog #223 row): the "R3 half … is now covered" claim is false

The row says: *"The R3 half of the proposal is now covered from the other side: a hook file `check-ratchet-contract`
counts as a caller is one this guard proved launchable."*

`check-ratchet-contract.py:192` globs `.claude/hooks/*` whole as caller evidence. The new guard reads only the
`command` strings registered in `.claude/settings.json`. These two sets differ by one file today:

- `ls .claude/hooks/` lists 14 scripts; `settings.json` registers 13.
- `check-memory-index-budget.sh` is counted by R3 and is never examined by this guard. `ci.yml:402-407` says it in
  so many words: *"A leading caller EXISTS AS A SCRIPT AND IS NOT REGISTERED."*

So "a hook file R3 counts is one this guard proved launchable" is wrong for 1 of 14 files. It happens not to cause
an escape today, because `check-memory-index-budget.py` also has a CI caller. But the row closes ✅ on a property
nothing enforces, and the row's own "where" column names "`check-ratchet-contract.py` R3's caller rule" as part of
the work.

**Fix:** one of these.
- (a) Delete the sentence, and file the R3 half as still open.
- (b) Make the new guard assert that every `.claude/hooks/*.sh` is either registered or carries a written
  `NOT-REGISTERED:` reason. That makes the claim true and is roughly a two-case addition.

### L1 — Low — `scripts/check-hook-commands.py:18-20,45,96-100`: the docstring promises an existence check that only one spelling gets

The docstring says it refuses *"an anchored path whose file does NOT exist"*, and defines anchored as starting with
`/`, `$CLAUDE_PROJECT_DIR` or `${CLAUDE_PROJECT_DIR`. In the code, existence is checked only when `anchored_rel()`
recognises one of three exact prefixes. Executed:

- `bash /.claude/hooks/block-default-branch-push.sh` (nonexistent absolute path): 0 findings.
- `bash "${CLAUDE_PROJECT_DIR:-scripts}"/.claude/hooks/…`: 0 findings.
- `bash "$CLAUDE_PROJECT_DIRX/…"`: 0 findings.
- `bash ~/.claude/hooks/…`: 0 findings, and it does not exist under `$HOME`.

All four launch nothing.

**Fix:** check existence for every absolute path. Treat any other `$`-prefixed or `~` token as unrecognised and
refuse it. That is the same remedy as M1's positive grammar.

### L2 — Low — `scripts/check-hook-commands.py:100`: false positive on a working shape

`cd "$CLAUDE_PROJECT_DIR" && bash .claude/hooks/block-default-branch-push.sh` gets 1 finding ("RELATIVE path"),
but from `scripts/` it launches and denies (rc 0, deny=1). This is the shape the harness's own schema text
recommends for plugin monitors (*"prefix with `cd "${CLAUDE_PLUGIN_ROOT}" && `"*).

Separately, any argument that merely mentions a repo file is refused as a relative path, for example a grep pattern
such as `grep -q docs/backlog.md`. Nothing in the repo uses either shape today.

**Fix:** if M1's positive grammar is adopted, either allow a leading `cd "$CLAUDE_PROJECT_DIR" &&` explicitly, or
state in the refusal message that the shape is deliberately not accepted.

### L3 — Low — `scripts/check-hook-commands.py:139,145` and others: two cases pass for an ambient reason, and 7 branches have no witness

These hand-applied mutants (in the copy) each left `--self-test` at **19/19**:

1. `ANCHORS` without `"/"`. The case "an absolute path passes" uses `/opt/hooks/z.sh`, which the `has` world does
   not contain, so the case passes whether or not `/` is an anchor. Its name claims the anchor; its body never
   reaches it. In the real check, an absolute path to an existing repo hook would be reported as RELATIVE.
2. `anchored_rel` reduced to the `:-.` prefix only. Existence is then not checked for `$CLAUDE_PROJECT_DIR/…` or
   `${CLAUDE_PROJECT_DIR}/…`. The case "the bare $CLAUDE_PROJECT_DIR form passes" is a positive only, so it cannot
   redden.
3. The `tok.startswith("-")` skip removed.
4. The `"/" not in tok` skip removed. Untested, and it also means that a repo-root script named without a slash,
   such as `python3 setup.py`, is never examined.
5. `h.get("type") == "command"` replaced by `True`. The ZERO case still returns 2, but via `Malformed` (the prompt
   hook has no `command`), not via the zero-command branch its name describes.
6. `isinstance(cmd, str)` replaced by `False`.
7. `isinstance(settings, dict)` replaced by `False`. A top-level JSON array would then raise an uncaught
   `AttributeError` (exit 1, which reads as a finding) instead of exiting 2 (CANNOT RUN).

**Fix:** add these cases:
- an absolute path under a world where it exists, which must give 0;
- `"$CLAUDE_PROJECT_DIR/…/missing.sh"` and `"${CLAUDE_PROJECT_DIR}/…/missing.sh"`, which must give 1;
- a non-command hook *next to* a command hook (count = 1);
- a JSON array as the settings file, which must give 2;
- a non-string `command`, which must give 2.

Then add mutations for 1, 2 and 7 at least.

### L4 — Low — `.claude/hooks/surface-recall.sh:47-48`: a stale quotation of the old command form

The comment says *"`.claude/settings.json:57` invokes this file as `bash .claude/hooks/surface-recall.sh` and passes
NO argument"*. Line 57 now reads `bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/surface-recall.sh`. The argument
still holds (no `$1` is passed), but the quoted text is now the exact form this PR's guard refuses.

**Fix:** update the quotation in the same PR.

### L5 — Low — PR #409 body and the backlog #223 row: the provenance wording is overstated, and the row has no PR number

- **The PR body overstates what can't be tested.** It says *"The session reads the main checkout's settings, so this
  branch can't show that before it merges."* A `claude` session started with cwd at the worktree loads the
  worktree's `.claude/settings.json`, and `CLAUDE_PROJECT_DIR` is then the worktree. So the live falsifier can be
  run before merge, e.g. `claude -p` from the worktree, then `cd scripts`, then a push attempt. I did not run a live
  session: UNVERIFIED that the harness then refuses. The harness-equivalent simulation above did deny.
- **The row never names the PR.** It says *"FIXED 2026-10-26 (branch `hooks-absolute-path`)"* without PR #409.
  `dev-process.md` Phase 5 asks for the merge tick to carry the PR number, which exists as soon as the PR does.

**Fix:** reword the PR body sentence, and add "PR #409" to the row.

### Accuracy check (question 5), apart from the findings above

- **PR body.** "13 hooks", "19 cases, 6 mutations (2138 → 2144)", the launch test and the bound are all accurate
  (executed or counted). "All 2157 manifest anchors still bind once" is UNVERIFIED: I did not run the full anchor
  pre-check.
- **Dashboard entry** (`docs/dashboard-entries.md`, 2026-10-26). These are accurate: 13 commands, the guard's two
  refusals, the CANNOT RUN set, 19 cases, 6 mutations (2138 → 2144), CI runs both, and the `main.argv` EXEMPT
  ("three main([]) cases" — there are three). It does not repeat the R3 claim.
- **Backlog #223 row.** Accurate except for M2 and L5.

VERDICT: NOT CONVERGED

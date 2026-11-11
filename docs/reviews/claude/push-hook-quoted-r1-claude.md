Reviewed head: ed8e0ac456a19038c2019b1d44a640aad9abf681

# push-hook-quoted — round 1, Claude half (adversarial, mandate: REFUTE)

Subject: `git diff origin/master...HEAD`, one commit `ed8e0ac4` (backlog #428, PR #542).

## What was run

| Check | Result |
|---|---|
| `bash .claude/hooks/block-default-branch-push.sh --self-test` | 33/33 pass (19 s) |
| `python3 scripts/push-command.py --self-test` | 39/39 pass (25 s) |
| 65 bypass probes: crafted hook JSON on stdin, fixture clone (`origin/HEAD` = master), cwd on `feat/x` | listed per finding below |
| The same 65 against `origin/master`'s hook (`git show origin/master:.claude/hooks/block-default-branch-push.sh`) | used to mark each bypass NEW or PRE-EXISTING |
| 21 over-refusal probes, cwd on `feat/x` and cwd on `master`, new and old hook | listed in R1-F2 |
| Failure paths: `python3` absent from `PATH`; `jq` absent from `PATH`; detector absent (the suite's own case) | R1-F7 |
| Mutations: anchor uniqueness for all 18; hand-applied #6 (`if segs:`) and #12 (segment runs past a separator) in a temp copy of `scripts/` + `.claude/hooks/` | all 18 anchors occur exactly once; both mutants rc 1 and each names its `expect` case as `[FAIL] <name>:` |
| Latency, 15 runs each, median | R1-F8 |

No `git push` was run. Every probe fed JSON to the hook over a local fixture.

## What holds

- **The #428 subject is fixed.** `git "push" origin master`, `git 'push' origin HEAD:master`, `git p"u"sh origin master`,
  `git pu\sh origin master`, `git push origin ma""ster`, `sh -c "git push origin master"`, `bash -c '…'`, `eval "…"`,
  `env`/`command`/`exec`/`time`/`nohup git push origin master`, `git -C ../main push …`, `GIT_DIR=… git push …`,
  `git --git-dir=… push …` are all DENIED. The old hook allowed nine of them.
- **Rules 2 and 3 are intact.** `--force`, `-f`, `--force` after the refspec, `--no-verify`, `-c core.hooksPath=…`
  and `ALLOW_PLAN_LEAK=1` are denied; `--force-with-lease` is allowed.
- **The detector fails closed.** If `python3` is missing (rc 127), the hook DENIES with "NOT CHECKED". A missing detector
  file also denies; the suite tests this. Empty output with rc 0 gives mode `''`, which reaches the `*)` deny.
- **The coordinator's real push line is ALLOWED.** The line is
  `python3 <scan> . | tail -1 | grep -q 'hits: 0' && python3 scripts/check-plan-leak.py | tail -1 | grep -q 'hits 0' && git push -q origin HEAD:<branch>`.
  It passes with cwd on a feature branch and with cwd on master, with or without a leading `cd ../wt &&`. So does
  `git -C ../wt push -q origin HEAD:feat/x`. The explicit `HEAD:<branch>` refspec makes the current branch irrelevant.
- **The mutations pin their names.** All 18 anchors are unique. Each of the two hand-checked mutants names its expected case.

---

### R1-F1 — High — A backslash-newline continuation hides the push's arguments from every rule (NEW CLASS, in scope)

`scripts/push-command.py:71-73` (`normalize`) and `:68` (`PUSH_SEG`, which stops at `\n`).

Bash joins `\<newline>` into one line. `normalize` deletes the backslash but keeps the newline. The segment then stops at
that newline, so the arguments on the continuation line are never read. This is a bash/hook parser differential on
escaping, the same class as #428's quotes. Agents also use this multi-line form for long commands.

Repro (cwd on `feat/x`; every row below was ALLOWED):

```
git push \
  origin master                      # pushes master          -> allow
git push \
  --force origin feat/x              # bare force push        -> allow
git push \
  --no-verify origin feat/x          # skips pre-push hooks   -> allow
git push origin \
  HEAD:master                        # pushes master          -> allow
```

(The old hook allowed these too, so they are not a regression. #428 claims to close quote and escape differentials,
and this is one it leaves open.)

**Fix:** in `normalize`, replace each `\\\n` with a space BEFORE deleting backslashes, e.g.
`cmd = cmd.replace("\\\n", " ")`. Add a strict-mode case and a hook case (`git push \<nl> origin master` → deny), plus a
mutation that drops the replace.

### R1-F2 — Medium — Over-refusal goes beyond the stated bound: any word `push` is a segment, even in strict mode and even after a non-push git subcommand

`scripts/push-command.py:79` (every `push` word becomes a segment), and `:22-31` (the bound).

The docstring promises two bounds. On a feature branch, only text reading `git push <remote> <default>` is refused. On
the default branch, segments with fewer than two arguments are refused. The measured behaviour is wider than both.

| Command | cwd `feat/x` | cwd `master` | old hook |
|---|---|---|---|
| `git commit -m "push the fix, not master" && git push origin feat/x` | **DENY** | DENY | allow |
| `git commit -m "fix: push gate refuses quoted master" && git push origin feat/x` | **DENY** | DENY | allow |
| `git push origin feat/x && gh pr create --title "Do not push to master" --body-file b` | **DENY** | DENY | allow |
| `git stash push -m "before master merge"` | **DENY** | DENY | allow |
| `git log --oneline --grep "push to master"` | **DENY** | DENY | allow |
| `git stash push -m wip` | allow | **DENY** | allow |
| `echo push; git status` | allow | **DENY** | allow |

On ANY branch, `push` followed later in its segment by the word `master` is enough to refuse. The segment does not
need to read `git push <remote> master`. Rule 2 is wider in the same way: `git push origin feat/x && echo "never push -f"`
reads the `-f`. The old code read only the `git … push` invocation's own segment in these rows.

`git stash push` is an ordinary git subcommand. On the default branch it is refused under the fail-closed rule, and the
stated bound does not name it.

**Fix (pick one, then restate the bound to match what the tests measure):**
(a) In `strict` mode, take segments only from STRICT matches, as the old code did. Keep "every `push` word" for `loose`
mode only. The compound case `git push origin feat/x && /usr/bin/git push origin master` still needs both segments, so
union the STRICT segments with any `push` word whose own `;&|\n` chunk contains a git word.
(b) Exclude `git stash push` (and `git remote … --push`) from LOOSE. Either way, the docstring's bound must list what it
actually refuses. Add `git commit -m "push … master"` on a feature branch as a measured bound case, or as an allow case
if (a) is taken.

### R1-F3 — Medium — The `if: Bash(*push*)` filter never invokes the hook for `git p"u"sh` or `git pu\sh`; the self-test asserts the detector, not the delivered path (in scope, UNMEASURED)

`.claude/settings.json:9` (`"if": "Bash(*push*)"`); `scripts/push-command.py:157` (case "a backslash does not hide
push").

Neither `git p"u"sh origin master` nor `git pu\sh origin master` contains the substring `push` as raw text. If Claude
Code matches `*push*` against the raw command, the hook never runs for them. The detector's success on these inputs is
then unreachable, and the self-test case "a backslash does not hide push" asserts a guarantee production does not
deliver. The hook header records that the filter was MEASURED against raw text (2.1.309). I did not measure the harness
for these two inputs, so this finding is a lead, not a measurement.

This is #428's own class ("bash deletes the quotes, the hook did not"), moved one layer up, into the filter.

**Fix:** measure it with the marker-hook method in the hook header. If it reproduces, choose one of two options. Widen
the filter (for example `Bash(*git*)`, or no filter; the measured cost unfiltered was 31 ms on a non-push call). Or name
`p"u"sh` / `pu\sh` in the OUT-OF-SCOPE list, next to `$'\x70ush'`, and delete or relabel the self-test claim.

### R1-F4 — High (PRE-EXISTING, not #428) — `git push origin HEAD` from the default branch is allowed

`.claude/hooks/block-default-branch-push.sh:295-303`.

With two or more plain tokens, each refspec's destination is compared to the default branch literally. `HEAD` and `@`
resolve to the current branch, and nothing resolves them.

Repro, cwd on `master` (new and old hook both ALLOW):

```
git push origin HEAD
git push -u origin HEAD
git push origin @
```

Each of these pushes master. `git push -u origin HEAD` is one of the most common push forms.

**Fix:** if a destination (or a refspec without a colon) is `HEAD` or `@`, replace it with `$current_branch` before the
comparison. File it if it is not fixed here.

### R1-F5 — Medium (PRE-EXISTING) — Tokens glued to `)`, `` ` ``, `>` or `<` are not refspecs, and a `+` refspec escapes both rules

`scripts/push-command.py:68` (the segment stops only at `;&|\n`) and `.claude/hooks/block-default-branch-push.sh:300`.

Allowed with cwd on `feat/x`, by both the new and the old hook:

```
(cd . && git push origin master)       # token `master)`
$(git push origin master)
`git push origin master`
git push origin master>/dev/null
git push origin 'HEAD:master'2>&1      # token `HEAD:master2>`
git push origin +master                # dest `+master`; also a FORCE push
git push origin +feat/x                # a force push, not refused by rule 2
```

The subshell form `(cd x && git push …)` is a natural shape for an accident.

**Fix:** end a segment at `` ` ``, `(`, `)`, `<`, `>` (and `{`/`}` as words), or strip redirections from tokens. Strip a
leading `+` before the destination compare. Treat a `+`-prefixed refspec as a force push under rule 2.

### R1-F6 — Low (PRE-EXISTING) — `--all`, `--mirror`, `--repo=<r>` and DWIM destinations

Allowed with cwd on `feat/x`, by both the new and the old hook: `git push --all origin`, `git push --mirror origin`,
`git push --repo=origin master` (`--repo=origin` is dropped as a flag, so `master` is read as the remote), and
`git push origin HEAD:heads/master` (git DWIMs this to `refs/heads/master`). `--all` and `--mirror` push the local
default branch. `--mirror` is also a force push of every ref.

**Fix:** treat `--all`/`--mirror` as targeting the default branch, and `--mirror` as force. Strip a `heads/` prefix as
well as `refs/heads/`. Treat `--repo=` as consuming the remote. File it if it is not fixed here.

### R1-F7 — Low (PRE-EXISTING) — No `jq` means a silent ALLOW; the hook's own `--self-test` runs nowhere in CI

`.claude/hooks/block-default-branch-push.sh:148`; `.github/workflows/ci.yml:419-422`.

With `PATH` stripped of `jq` (python3 present), `git push origin master` gives rc 0 and EMPTY stdout, which means allow.
`cmd` falls back to `""`, and `deny()` cannot print without `jq` either. Every rule fails open. The detector's
fail-closed refusal does not help, because it never sees the command.

Separately, `git grep` finds no runner for `block-default-branch-push.sh --self-test`: not in CI, and not in any
`scripts/` gate. This commit's 7 new hook cases are therefore not enforced, although the 13 hook-driven cases in
`push-command.py --self-test` are, through `ci.yml:422`. Rules 2 and 3 (force, no-verify, hookspath) are asserted only
in the hook's suite, so a regression in them would not turn CI red.

**Fix:** `command -v jq >/dev/null || { printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"push gate: jq missing — NOT CHECKED"}}'; exit 0; }`.
Add a CI step: `bash .claude/hooks/block-default-branch-push.sh --self-test`.

### R1-F8 — Low — The added latency is real and partly avoidable

Median of 15 runs, in the fixture, on a loaded machine:

| Command | new | old |
|---|---|---|
| `git push origin feat/x` | 220 ms | 123 ms |
| `echo push` | 115 ms | 25 ms |

A bare `python3 scripts/push-command.py segments` takes about 70 ms. Of that, `-X importtime` attributes about 12 ms to
`tempfile` and 9 ms to `subprocess`. Both are needed only by `--self-test`.

The `if: Bash(*push*)` filter already skips commands without the substring `push`, so a bash-side "skip unless `push`"
check saves nothing extra. A bash-side "skip unless the de-quoted text has a `git` word" check would only skip harmless
text such as `echo push`.

**Fix (cheap):** move `json`/`subprocess`/`tempfile`/`Path` imports into the self-test functions, and invoke with
`python3 -S` if `sitecustomize` is not needed. That saves roughly 20-30 ms per call. The remaining Python start-up is
the price of a mutable detector, and the commit already states it.

---

## Scope summary

| Finding | Class | In #428 scope? | Regression vs `origin/master`? |
|---|---|---|---|
| R1-F1 backslash-newline | escaping differential | yes (same class) | no (old also allowed) |
| R1-F2 over-refusal | new behaviour | yes | **yes**: 7 rows newly refused |
| R1-F3 filter vs `p"u"sh` | quoting differential, one layer up | yes | no (unmeasured) |
| R1-F4 `HEAD`/`@` dest | refspec resolution | no | no |
| R1-F5 glued `)`/redirect/`+` | tokenisation | adjacent | no |
| R1-F6 `--all`/`--mirror`/DWIM | refspec semantics | no | no |
| R1-F7 jq fail-open, hook suite not in CI | failure path | adjacent | no |
| R1-F8 latency | cost | yes | +~95 ms (stated) |

NOT CONVERGED: R1-F1 is a cheap in-scope bypass of all three rules. R1-F2 is a measured regression, and the docstring's
stated bound understates it.

VERDICT: NOT CONVERGED

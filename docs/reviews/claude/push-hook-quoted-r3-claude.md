Reviewed head: 8e5e3d69050961e2b860125964b17657ab58d1cc

# Round 3, Claude half: `push-hook-quoted` (PR #542, backlog #428)

Mandate: REFUTE. I read the r1 and r2 coordinator documents, the r2 Codex review and the fold `8e5e3d69`.
Then I ran three hooks side by side over crafted JSON on stdin, in a fixture clone whose default branch is
`master`. The hooks were HEAD (`8e5e3d69`), r1-fold (`8e5e3d69^`) and `origin/master` (`b15e4f96`). The
fixture was checked out on `feat/x`, or on `master` where stated. No real `git push` was run.

I checked what bash does with a shell function standing in for `git` (`git(){ echo "RAN: git $*"; }`, then
`eval` of the exact command). Every bypass below printed `RAN: git push …` with the destination or flag shown.

**Self-tests:** `push-command.py --self-test` 112/112; the hook's `--self-test` 56/56.

## Summary

| id | severity | tag | what gets through |
|---|---|---|---|
| R3-F1 | High | **FOLD-INDUCED** | a quote inside a heredoc BODY makes the detector see the real push as an argument of `git stash`/`git commit`, so it is exempt. Mode `none` lets through a push to master, `--force`, `--no-verify`, `core.hooksPath` and `ALLOW_PLAN_LEAK`. r1 and master both DENY these. |
| R3-F2 | Medium | PRE-EXISTING (lead 1, reproduced) | `git --attr-source stash push origin master`: git takes `stash` as the option's value; the detector takes it as the subcommand and exempts it |
| R3-F3 | Medium | PRE-EXISTING (lead 2, reproduced) | brace expansion: `git push origin {master,}`, `git {push,origin,master}`, `git push {--force,origin} feat/x`; a glob as the command word (`/usr/bin/gi? push origin master`) |
| R3-F4 | Medium | PRE-EXISTING | `$"…"` (bash locale string): `git push origin $"master"` is read as `$master` |
| R3-F5 | Medium | PRE-EXISTING | rule 2 misses short-option bundles (`-uf`, `-fu`) and abbreviated long options (`--no-veri`) |
| R3-F6 | Low | PRE-EXISTING | destinations the text never shows: `echo master \| xargs git push origin`; and `HEAD:heads/master` (inferred, not executed) |
| R3-F7 | Low | FOLD-INDUCED (prose) | the bound says a push argument holding a quoted `<` or `>` is refused; `--push-option='>'` is allowed |

---

### R3-F1 — High — A heredoc body's quote makes a real push into a `git stash`/`git commit` argument, and so exempt (FOLD-INDUCED)

**File:line:** `scripts/push-command.py:185-189` (a quote opens wherever `q is None`, including a heredoc body),
`scripts/push-command.py:241-242` (the exemption returns `[]`), `scripts/push-command.py:266` (→ `none`), and
`.claude/hooks/block-default-branch-push.sh:262` (`0:none) allow`, BEFORE rules 2 and 3).

**Cause.** `lex` does not model heredocs. It treats `<<EOF` as a redirection, drops `EOF`, and then lexes the
BODY as command lines. Bash reads the body as DATA, where `'` and `"` are literal. So a quote in the body opens
a quote for the detector but not for bash. If that body line reads `git stash … '`, the detector puts
everything up to the next `'` into the stash command's arguments. That includes real command lines after
`EOF`. `_judge` then exempts the stash command, and the push vanishes.

To make bash run the push, the closing quote just has to be somewhere bash ignores: a `#` comment (inside the
detector's quote, `#` is literal) or a second heredoc body.

**Repro** (feature branch `feat/x`, default branch `master`):

```
cat <<EOF
git stash list '
EOF
git push origin master # '
```

| input (abbreviated) | HEAD | r1-fold | master | bash runs |
|---|---|---|---|---|
| above | **allow** (`none`) | DENY | DENY | `git push origin master` |
| same, with the push line `git push --force origin feat/x` and a 2nd heredoc `cat <<EOF` / `'` / `EOF` closing the quote | **allow** | DENY | DENY | `git push --force origin feat/x` |
| `cat <<EOF` / `git commit -m '` / `EOF` / `ALLOW_PLAN_LEAK=1 git -c core.hooksPath=/dev/null push --no-verify origin master # '` | **allow** | DENY | DENY | that push, every gate off |
| `cat <<'EOF'` / `git stash list "` / `EOF` / `git push origin HEAD:master # "` | **allow** | DENY | DENY | `git push origin HEAD:master` |
| each of `-c core.hooksPath=/dev/null`, `ALLOW_PLAN_LEAK=1`, `--no-verify` alone behind the same heredoc | **allow** | DENY | DENY | — |

**Why it is FOLD-INDUCED.** Round 1 deleted quotes before splitting at newlines, so the body's `'` could not
swallow the next line, and r1 denies every row above. The r2 fold made quotes span newlines, and there is no
heredoc model. Master denies because it reads the raw text.

**Same class as round 2?** Yes. Round 2's three Highs were "the detector's lexing differs from bash's, and a
differential that ends in a SUBTRACTION (exemption, dropped word, dropped segment) lets a push through". The r2
fold reversed the direction of the differential (quote-blind became quote-aware) and kept the subtractions, so
the opposite differential now leaks. R3-F4 (`$"…"`) is the same class, in a construct neither version models.

**Fix (patch):** an unquoted `<<` or `<<-` (not `<<<`) in a command holding `git` and `push` is `unresolved`.
This costs the documented `git commit -F - <<EOF` style, which the bound already steers to `-F <file>`.

**Fix (removes the class), recommended:** make the detector MONOTONE. It may only remove a push word from
consideration (stash/commit exemption, comment, redirection target, `bare` drop in strict mode) when BOTH of
these readings agree that the word is inert:
- the quote-aware lexer (r2);
- a quote-BLIND split of the raw text at every `;`, `&`, `|` and newline (essentially r1's reading).

Disagreement means REFUSE. Each reading's blind spot was exactly the other reading's strength:
- r1 denies everything in this table;
- r2 denies X-F1, X-F2 and X-F3 of round 2.

So "deny if either reading denies" closes both, and any future construct where bash's quote state is not
modelled (heredoc, `$"`, `${…'…}`, `case` patterns) becomes a false refusal rather than a pass. The price is
round 1's false refusals coming back for quoted separators beside a stash/commit (for example
`git stash push -m "a; git push origin master"`). The bound must say so. Add every row above as a hook case.

### R3-F2 — Medium — `--attr-source <tree-ish>` puts the exempt word where the detector reads the subcommand (PRE-EXISTING; coordinator lead 1, REPRODUCED)

**File:line:** `scripts/push-command.py:96-97` (`VALUE_OPTS` lacks `--attr-source`), `:211-216` (`_subcommand`
skips any other `-flag` alone), `:241-242` (exempt).

**Measured on git 2.49.0** (`git help git` lists `--attr-source=<tree-ish>`):
- `git --attr-source stash log --oneline -1` ran `log` (rc 0), so git consumed `stash` as the option's value;
- `git --attr-source stash version` printed the version.

So `git --attr-source stash push origin master` runs `push`. Its detector output is `none`, and all three hooks
allow it. `git --attr-source commit push --force origin feat/x` and `… stash push --no-verify …` are allowed
too. Control: `git --attr-source HEAD push origin master` gives `loose` and is DENIED on HEAD, so only the
exemption path leaks.

Other options I checked, none of which reproduced:
- `--config-env stash` → `fatal: invalid config format`, so it takes only the `=` form;
- `--super-prefix` → `unknown option` on 2.49;
- `--list-cmds=…` lists and exits.

**Tag:** master and r1 allow it as well. The exemption is this PR's (r1, C-F2), but master never saw the push
either, so it is not a regression.

**Fix:** add `--attr-source` to `VALUE_OPTS`. More importantly, take the lead's rule: exempt only when every
word between `git` and the subcommand is a RECOGNISED global option (a closed list; the `=` forms parsed). Any
unrecognised `-word` makes the command loose. Pin `git --attr-source stash push origin master` → deny.

### R3-F3 — Medium — Brace expansion and globs rewrite the words after the hook has read them (PRE-EXISTING; coordinator lead 2, REPRODUCED)

**File:line:** `scripts/push-command.py:122-200` (`lex` keeps `{`, `,`, `*`, `?` and `[` as literal word
characters), and the hook at `:402-410` (it compares the literal word).

| input (on `feat/x`) | HEAD / r1 / master | bash runs |
|---|---|---|
| `git push origin {master,}` | allow / allow / allow | `git push origin master` |
| `git push origin HEAD:{master,}` | allow ×3 | `… HEAD:master` |
| `git {push,origin,master}` | allow ×3 (loose segment `push ,origin,master}`) | `git push origin master` |
| `git push {--force,origin} feat/x` | allow ×3 | `git push --force origin feat/x` |
| `/usr/bin/gi? push origin master` | allow ×3 (`none`: no word `git`) | `/usr/bin/git push origin master` |
| `git push origin feat/x; /usr/bin/g?t push origin master` | allow ×3 | both pushes |
| `git push origin mas[t]er`, `maste?`, `m*r` | allow ×3 | expands only if a file named `master` is in cwd |

**Fix:** in `lex`, an UNQUOTED `{` holding a `,` or `..` before its matching `}`, or an unquoted `*`, `?` or `[`,
is `unresolved` when the command holds `push`. The word `git` cannot be required, because the glob case has no
literal `git`. So a glob in a command word with `push` present should be enough. The quote state is already
there to keep `"{a,b}"` and `'*'` literal.

### R3-F4 — Medium — `$"…"` is read as `$` plus a double-quoted string (PRE-EXISTING; same class as R3-F1)

**File:line:** `scripts/push-command.py:173-174` handles `$'` only, so `$"` falls through to `:194` (keeps the `$`)
and then to `:185` (opens the quote).

**Repro:** `git push origin $"master"` gives detector `strict | push origin $master`, and all three hooks allow
it. Bash runs `git push origin master`, because `$"…"` is a locale-translated string and is identical with no
catalogue. `git push $"master" origin` is allowed the same way. (`git $"push" origin master` is denied, but only
because the loose layer catches it.)

**Fix:** treat an unquoted `$"` as `"` (drop the `$`), or as `unresolved` like `$'`. Add a mutation and a case.

### R3-F5 — Medium — Rule 2 misses short-flag bundles and abbreviated long options (PRE-EXISTING)

**File:line:** `.claude/hooks/block-default-branch-push.sh:300` and `:343`.

**Repro:**
- `git push -uf origin feat/x` and `git push -fu origin feat/x` are allowed by all three hooks. Git's
  parse-options bundles short flags, so `-uf` means `-u -f`, a FORCE push.
- `git push --no-veri origin feat/x` is allowed by all three. On this machine `git commit --no-veri --dry-run`
  is accepted (no `unknown option`; the control `--no-verifyx` IS rejected). Commit and push share
  parse-options, so a unique prefix of `--no-verify` is accepted. For push this is INFERRED, not executed.

**Fix:**
- for short flags, match any single-dash bundle containing `f`. `-o`/`--push-option` and `--repo` take values,
  so only bundles of flag letters count, for example `-[a-zA-Z]*f`.
- for long options, refuse any `--no-ver…` prefix of `--no-verify`, `--for` / `--forc` (not `--force-with-lease`
  / `--force-if-includes`), and `--no-verify`'s abbreviations.

### R3-F6 — Low — Destinations the command text does not contain (PRE-EXISTING)

- `git push origin feat/x; echo master | xargs git push origin`: allowed by all three hooks. Bash runs
  `git push origin master`. This is the same out-of-scope family as `$var`, but `xargs` is not listed in the
  docstring's out-of-scope paragraph. Either list it, or make `xargs` a code-running wrapper beside `eval` /
  `sh -c`.
- `git push origin HEAD:heads/master`: allowed by all three. Git resolves an unqualified destination against the
  remote's refs by `ref_rev_parse_rules` (`refs/%s`), so I expect `refs/heads/master`. **Inferred, not
  executed** (that needs a real push).

  Fix: a destination equal to `heads/<default>`, or ending `/<default>`, is the default branch.

### R3-F7 — Low — The bound overstates the quoted-`<`/`>` refusal (FOLD-INDUCED, prose)

**File:line:** `scripts/push-command.py:56-57`, hook `:236-237`.

The bound says "a push argument holding `(`, `)`, a backtick, `$(`, `<` or `>` even QUOTED is REFUSED". This
holds only for NON-option arguments:
- `git push origin feat/x -o '>'` is DENIED;
- `git push origin feat/x --push-option='>'` is ALLOWED on both branches, because the hook drops `-`-prefixed
  tokens before that check.

The behaviour is fine; the sentence is wrong. Fix it to say "a non-option push argument".

---

## Item 2: failure paths and the 5 flipped cases

**Failure paths.** In the hook's `case "$detect_rc:$mode"` (`:261-279`), only `0:none` allows. Everything else
refuses:
- `0:unresolved` and `142:*` refuse;
- any other rc or mode refuses, including rc 0 with an empty or unknown mode, a Python exception (rc 1) and
  missing python (127).

I also confirmed:
- `REDIRECT_OP.match` cannot return `None` on the `<>` / `&>` branch, so there is no crash path in `lex`;
- the jq-missing and unreadable-payload paths refuse with NOT CHECKED (hook self-test).

**Sound, except R3-F1:** a FAILURE path never allows. R3-F1's allow is `0:none`, a "successful" wrong answer.

**The 5 flips, each checked in place.** All are right:
- `git -C "my dir" push …`: loose → strict, which is correct, since one lexed word is right;
- `echo "git push later"`: strict → loose, also correct. `echo` is the command word, and the hook reads loose
  and strict segments by the same rules, so the refusal on the default branch is kept. I measured it: DENY on
  master, allow on feat/x;
- two `$(` cases: loose → unresolved, which is stricter;
- the hook's unbalanced quote: allow → deny, which is stricter, and bash would refuse the line anyway.

## Item 3: the false-refusal bound against behaviour

I ran every example the bound names, on `feat/x` and on `master`:

| example | `feat/x` | `master` |
|---|---|---|
| default-branch examples (`git log --grep push`, `echo "git push later"`, `echo push; git status`) | allow | DENY |
| any-branch loose-text examples (`gh pr create --title "git push origin master"`, `git log --oneline --grep "push to master"`, `git log --grep "push --force"`) | DENY | DENY |
| unresolved examples (subshell, unbalanced quote, `bash -c`) | DENY | DENY |
| `git push origin 'feat/(x)'` | DENY | DENY |
| heredoc body `Don't` beside a feature push | DENY | DENY |

The ALLOWED list matches on both branches:
- `git commit -m "push the fix, not master" && git push origin feat/x`;
- `git stash push -m "git push origin master"`;
- a feature push followed by `--title "Do not push to master"`;
- `git push -u origin feat/x 2>&1`.

`/usr/bin/git stash push -m wip` is loose, as stated: DENY on master, allow on feat/x.

**The one mismatch is R3-F7.** The bound is not a full list of false refusals. For example,
`git status && gh pr create --title "do not push to master"` is refused on any branch. It falls under the
"text reading `push <x> <default-branch>`" clause, so it is covered.

## Item 4: three mutations, hand-checked one at a time

Each mutation was run in a `check-plan-code.stage_tree` copy, with the single manifest entry's edits applied
(anchor count 1), then `push-command.py --self-test`:

| manifest entry | result |
|---|---|
| #33 `r2 X-F2: a QUOTED < or > is a redirection that eats the next word` | rc 1; 6 FAILs including the named `X-F2 r2 … --force` case and the hook case |
| #37 `r2: a # INSIDE a word starts a comment` | rc 1; 1 FAIL, the named case (`got ('none', [])`) |
| #41 `r2 UNRESOLVED: an ANSI-C string is read as $ and a plain quote` | rc 1; 1 FAIL, the named case (`got strict … $master`) |

All three are sound. No mutation covers heredocs or `$"`. That is expected, since neither is modelled
(R3-F1, R3-F4).

## Item 5: the four rules on plain input

On plain input, all four rules are intact (hook self-test 56/56, and my probes):
- `--force` / `-f` / `+refspec` deny, while `--force-with-lease` is allowed;
- `--no-verify` denies;
- `-c core.hooksPath=…`, `--config-env`, `GIT_CONFIG_*` and the quoted and backslash forms deny;
- `ALLOW_PLAN_LEAK` in any form denies, unless `ALLOW_DANGEROUS_PUSH=1` is given.

**However, all four are switched off by R3-F1's heredoc form** (measured; master denies each). Rule 2 and rule 3
sit behind `0:none) allow`, so a wrong `none` skips them all. R3-F5's bundles and abbreviations predate this PR.

## Thrashing judgement

**THRASHING: yes.**
- Round 2's findings (X-F1..X-F3) were caused by round 1's fold.
- Round 3's R3-F1 is caused by round 2's fold: r1 denies every R3-F1 row, and the r2 fold's quote-aware lexer
  without a heredoc model is what lets them through.

That is two consecutive rounds, in ONE component (`detector-tokenizer`), whose findings came from the previous
round's own fix. Phase 6 arms.

**Can a redesign remove the class? Yes.** Every leak has the same shape. A lexing differential with bash meets
a SUBTRACTION step (exempt, comment, redirection target, `bare` drop, a literal word compared against the
default branch), and the subtraction allows. Patching each construct (heredoc, `$"`, brace, glob,
`--attr-source`) is an open-ended list, the "wall" that PR #443 already recorded for rule 3.

The structural fix is the monotone rule in R3-F1: a subtraction counts only when the quote-blind and
quote-aware readings agree, and otherwise the hook refuses. Expansion characters (`{`, `*`, `?`, `[`, `$"`) in a
command with `push` are `unresolved`. The exemption requires a fully recognised git prefix. Then a construct the
lexer does not model can only cost a false refusal, never a pass.

## Loosening answers
LOOSENING-CHECK f090c90de19b: not a loosening
LOOSENING-CHECK 2d51171ccc52: not a loosening
LOOSENING-CHECK a37789af0a0d: finding: a heredoc body line `git stash list '` closed by a later `# '` makes the detector exempt the real push as stash arguments, so `git push --force origin feat/x` after it is allowed where master refused it
LOOSENING-CHECK 19e3cb6a182b: finding: a heredoc body line `git stash list '` closed by a later `# '` makes the detector exempt the real push as stash arguments, so `git push --force origin feat/x` after it is allowed where master refused it
LOOSENING-CHECK 4a4c20c73163: finding: the same heredoc-quote form lets `git -c core.hooksPath=/dev/null push origin feat/x` through, which master refused
LOOSENING-CHECK 2fec52dc562d: finding: the same heredoc-quote form lets `ALLOW_PLAN_LEAK=1 git push origin feat/x` through, which master refused

VERDICT: NOT CONVERGED

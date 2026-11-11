# Architecture review (Phase 6, narrow): the push detector's tokenizer — 2026-11-08

**Subject:** `scripts/push-command.py` + `.claude/hooks/block-default-branch-push.sh` on branch `push-hook-quoted`
(PR #542, backlog #428), head `02012177`. **Armed by THRASHING** (round 3 coordinator): round 2's three Highs came
from round 1's fold, and round 3's C-F1 came from round 2's fold, all in one component, the detector's tokenizer.

**Read first:** `CONTEXT.md` (the *Structural line* and *Soundness check* entries are the precedent this review
lands on), `docs/adr/` (no ADR covers the push gate, so nothing here re-litigates one), `docs/review-method.md` →
*The arming condition — full account*, the three coordinator records, the r1–r3 Codex and Claude reviews, and both
files at head and on `origin/master`.

**Method.** Every option was RUN, not argued:
- a **case matrix** of 67 inputs (every r1–r3 repro, expected DENY; the documented ALLOWED list and four extra
  allowed idioms, expected ALLOW) through master's hook, round 1's hook (`5dcc8759`), head's hook, option (a) (the
  union of r1 and head) and a prototype of option (b), in fixture clones on `feat/x` and on `master`;
- a **corpus** of every Bash `command` in this project's transcripts that holds the words `git` and `push`
  (quote-blind), run through the same hooks and the prototype;
- a **differential oracle**: random command strings lexed by the prototype and executed by `/bin/bash` with shell
  functions standing in for `git`/`echo`/`gh`, checking that bash never runs an invocation the lexer did not report.

No real `git push` was run. The scratch work is in the session scratchpad (`arch-pd/`), not in the repository.

---

## 1. The class, stated once

Every leak in three rounds has one shape:

> the detector's reading of the command differs from bash's, **and** the difference reaches a step that
> **discards** a push word (an exemption, a dropped word, a dropped segment, an early `none → allow`).

Round 1 read quote-BLIND and discarded on that reading, so quoted text became syntax (r2 X-F1..F3). Round 2 read
quote-AWARE without modelling heredocs, and discarded on THAT reading (r3 C-F1). Rounds 1–3 also each reproduced
constructs NEITHER reading models: brace expansion and globs (C-F3), `$"…"` (C-F4), git's own option grammar
(`--attr-source`, C-F2; `-uf` and `--no-veri`, C-F5). Each fold patched the constructs in front of it, and the
list of constructs bash has is longer than the list any round can patch. That is the "wall" PR #443 already
recorded for rule 3.

The term for this already exists in `CONTEXT.md` (*Structural line*, backlog #154): *"The terminating move is
therefore not a wider pattern but a soundness check: refuse what cannot be classified."* and (*Soundness check*):
*"a hand-rolled parser CANNOT be made correct. It CAN be made unable to be silently wrong."* The push detector
is the same problem in a different language, and it has not had that move applied.

**What would remove the class:** a design in which a construct the detector does not read EXACTLY can only cost a
false refusal, never a pass. Concretely, there must be no discard step that runs on an inexact reading.

---

## 2. The options, measured

### 2.1 The case matrix (67 inputs; MEASURED)

| reading | false PASS (of 52 expected-deny) | false REFUSAL (of 15 expected-allow) |
|---|---|---|
| master hook | **35** | 0 |
| round 1 hook (`5dcc8759`) | **32** | 4 (`git stash push -m "git push origin master"` ×2 branches; `git log --grep push` and `echo "git push later"` on master) |
| head hook (`02012177`) | **24** | 3 (`git log --grep push`, `echo "git push later"` on master; a `$(cat <<'EOF' …)` commit beside a feature push) |
| **(a)** union of r1 and head | **19** | 5 (both sets) |
| **(b)** prototype, closed language (level 3, §2.3) | **0** | **0** |

The 19 that (a) still passes are every C-F2, C-F3, C-F4, C-F5 and C-F6 repro and `--all` / `--mirror`: constructs
that NEITHER reading models. That is the measured form of "two wrong lexers are not a right one".

### 2.2 The transcript corpus (MEASURED)

Source: `~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/`, every
`tool_use` named `Bash` whose `command` holds the words `git` and `push` after quotes and backslashes are deleted.

| set | files | unique commands | occurrences |
|---|---|---|---|
| top-level `*.jsonl` (the main sessions) | 185 | 1,168 | 1,319 |
| subagent transcripts (`**/*.jsonl` below it) | 624 | 466 | 475 |
| **total** | 809 | **1,634** | **1,794** |

Head's detector classifies them: `unresolved` **1,142**, `strict` **435**, `loose` 50, `none` 7. So 70% of the
real commands that mention git and push already sit in head's fail-closed bucket. The corpus is mostly from
sessions that ran under master's hook, so these are commands agents actually wrote, not commands written around
head's rules.

**Every corpus command through each hook (MEASURED, 9,804 runs: 3 hooks × 2 fixtures × 1,634):**

| reading | refused on `feat/x` (unique / occurrences) | refused on `master` |
|---|---|---|
| master hook | 26 / 26 | 107 / 108 |
| round 1 hook | 227 / 247 | 395 / 425 |
| **head hook** | **1,166 / 1,292** | 1,184 / 1,310 |
| (a) union of r1 and head | 1,166 / 1,292 (r1's refusals are a subset of head's on `feat/x`) | 1,192 / 1,318 |
| (b) level 1 | 1,241 / 1,374 (77 new vs head, 2 relieved) | 1,249 / 1,382 (71 new, 6 relieved) |
| (b) level 3 | **776 / 866** (69 new vs head, **459 relieved**) | 835 / 926 (64 new, 413 relieved) |

Head ALREADY refuses 71% of these commands on a feature branch, against master's 1.6%. Round 2's fail-closed
`unresolved` rule is where that cost came from, and it was paid without being measured. Level 1's 77 new
refusals are `${S:?}`-style `$` forms (21), a backslash inside double quotes (19), heredocs (9), `[ … ]` (7),
`python3`/`ruby`/`sed` given code (9), and a handful of `\`, `{`, `*`, `~`.

### 2.3 The option (b) prototype and its levels (MEASURED)

`arch-pd/bprime.py` and `bprime2.py` implement option (b) as one rule: **a command holding the word `push` is read
by a lexer that is exact over a CLOSED LANGUAGE, and anything outside the language is refused.** The language is
widened in levels, each one a construct the lexer reads exactly or refuses:

| level | adds to the language | corpus refusals on `feat/x` (unique / 1,634) | on `master` |
|---|---|---|---|
| 0 | plain words `[A-Za-z0-9_./:=@+,%^-]`, single and double quotes (no `$`, backtick or backslash inside), `;` `&` `|` newline, `<` `>` `>>` `N>&M` redirections | 1,436 | 1,440 |
| 1 | + simple parameter expansions `$NAME`, `${NAME}`, `$?` `$$` `$!` `$#` `$0`–`$9`, as words of UNKNOWN value | 1,241 | 1,249 |
| 2 | + heredocs `<<W` / `<<-W` (a quoted delimiter's body is data; an unquoted one's body must hold no `$`, backtick or backslash) | 961 | 1,003 |
| 3 | + command substitution `$( … )`, lexed recursively under the same rules; its commands are judged like any other | **776** | 835 |

Judging, at every level (no exemption runs on an inexact reading, because there is no inexact reading):
- `git` with global options from a CLOSED table (`-C`, `-c`, `--git-dir`, `--work-tree`, `--namespace`,
  `--config-env`, `--super-prefix`, `--attr-source` take a value; a closed list of flags; `=` forms). An
  unrecognised option in a command holding a push word is refused.
- subcommand `push`: options from a CLOSED allowlist (`-u`, `--set-upstream`, `--force-with-lease[=…]`,
  `--force-if-includes`, `-n`/`--dry-run`, `-v`, `-q`, `--porcelain`, `--progress`, `--tags`, `--follow-tags`,
  `--atomic`, `-d`/`--delete`, `-o`/`--push-option`, `--signed`, `-4`/`-6`); any other `-word` is refused. That
  refuses `-f`, `--force`, `-uf`, `-fu`, `--no-veri`, `--no-verify`, `--all`, `--mirror`, `--prune`, `--repo`.
  A `+refspec` is refused. The destination is the text after the last `:`, minus `refs/heads/` or `heads/`, with
  `HEAD`/`@` read as the current branch; the default branch is refused. Fewer than two positionals on the default
  branch is refused.
- a subcommand in a closed INERT list (`commit`, `stash`, `log`, `show`, `diff`, `grep`, `status`, …): its words
  are text. Any other git subcommand holding a push word is refused.
- a command word in a closed TEXT list (`echo`, `printf`, `grep`, `rg`, `gh`, `cat`, `cd`, …): its words are text.
- a CODE RUNNER (`bash`, `sh`, `eval`, `xargs`, `env`, `python3`, `timeout`, …) whose words hold a push word, or
  that takes code from the text (`-c`, `-e`, `-`, or no script argument), is refused.
- any other command holding a push word is refused. A word of unknown value (level 1+) in a git command holding a
  push word is refused unless it is the value of `-C`; an unknown command word holding a push word is refused.
- rule 3 (`hookspath`, `allow_plan_leak`) is a quote-blind substring test over the whole text, run BEFORE lexing
  and never behind an allow.

Of the 435 real pushes (head `strict`) in the corpus, level 3 refuses 53 on `feat/x`: pushes composed with a
construct outside the language (`${S:?}`, `\|` inside double quotes, `[ -L … ]`, `@{u}`, a backslash
continuation, `python3 -c`). The remedy the refusal must print is the one head prints today: run the push as its
own plain command.

### 2.4 The differential oracle (MEASURED) — and why it is part of the design, not a test nicety

The oracle (`arch-pd/fuzz.py`, `fuzz2.py`) generates random command strings over the language's characters
**plus** the characters it must refuse, lexes each, and for each one the lexer ACCEPTS, runs it under `/bin/bash`
(GNU bash 3.2.57, the shell this session's Bash tool runs) with `git`, `echo` and `gh` replaced by functions that
log their argv. Property: **every invocation bash runs must appear, argv identical, in the lexer's command list**
(an unknown-valued word matches any one argument).

- **It found two real differentials in my own level-0 prototype in its first 3,000 strings**: `>& -u` (bash
  reads `>&-` as "close the descriptor" and `u` as an ARGUMENT; the prototype dropped `-u` as the target). That is
  exactly the class this review is about, in a lexer written ten minutes earlier by someone looking for it. The
  fix closed the grammar (`>&`/`<&` must be followed by digits, else OUTSIDE).
- After the fix: level 0, seeds 1–3 × 3,000: **0 unsafe** of 1,843 accepted strings. Level 3, seeds 1–4 (3,000
  each; seed 1 re-run at 4,000 with an extra atom): **0 unsafe** of ~3,500 accepted strings.
- **Mutation controls** (each a one-line change to the level-3 lexer, oracle re-run):
  | mutation | unsafe found |
  |---|---|
  | a `$( … )`'s commands are not reported | **128** / 3,000 |
  | `<<-` does not strip tabs before comparing the delimiter | **1** / 6,000 |
  | an unquoted heredoc body may hold `$` | **0** / 6,000 with the original atoms; **66** / 4,000 after adding the atom `<<E` / `$(git push u)` / `E` |
- **The last row is the bound on this instrument:** the oracle's power is its generator's. A construct admitted to
  the language needs an atom that exercises its DANGEROUS direction (the lexer under-reporting), and a mutation
  proving the atom bites. Without that it is a green check over the wrong subject.

### 2.5 Option (c): ask bash itself (MEASURED where possible)

- `/bin/bash --pretty-print` → `invalid option` (bash 3.2.57; no newer bash is installed).
- `bash -n` on round 3's C-F1 bypass exits **0**: the bypass is valid syntax, and `-n` returns no reading to judge.
- `bashlex` and `tree_sitter_bash`: **not installed** (`ModuleNotFoundError`). Adopting one adds a dependency to a
  gate that must refuse when it is missing, and a third-party parser is a third reading with its own
  differentials (INFERRED; not measured here).
- `xtrace`/`set -x` needs execution, which a hook must never do. Wrapping the text in a function definition and
  printing it with `declare -f` executes the surrounding text if it closes the brace (INFERRED from bash grammar;
  not run).
- Even an exact parse is not an expansion: brace, glob, `$"…"` and parameter values are applied AFTER parsing, so
  a parser alone would still leak C-F3 and C-F4 (INFERRED).
- **What (c) gets right is the oracle.** Bash cannot be the gate's reader, but it is the only authority on what
  bash does, so it belongs in the TEST: §2.4. CI runs Linux bash 5.x; this machine runs 3.2.57. The language must
  be the intersection, so the oracle runs under whichever `/bin/bash` the suite finds, and both are exercised
  (local and CI).

### 2.6 Option (d): move the guard to where the push is concrete

`git push --help` (MEASURED, git 2.49.0): *"With --no-verify, the hook is bypassed completely."* `githooks(5)`:
pre-push receives `<local-ref> <local-object-name> <remote-ref> <remote-object-name>` on stdin, after git has
resolved every refspec. In this clone `core.hooksPath` is set to the main checkout's `.githooks` (MEASURED).

| rule | can it live in `pre-push`? |
|---|---|
| 1, default branch | **Yes, completely.** The remote ref is concrete: `--all`, `--mirror`, `push.default`, `remote.<r>.push`, aliases, `xargs`, variables, scripts — all resolved by git. That is backlog #574 by construction. A `(delete)` line is visible too. |
| 2a, `--force` / `+refspec` | **Partly.** A non-fast-forward update is detectable (`git merge-base --is-ancestor <remote> <local>`), but `--force-with-lease`, which the policy ALLOWS, is the same update at the hook (INFERRED from the stdin format; not run, because running it needs a real push). |
| 2b, `--no-verify` | **No.** It skips the hook. |
| 3, `core.hooksPath` / `ALLOW_PLAN_LEAK` | **No** for hooksPath (the hook is never found). ALLOW_PLAN_LEAK is the plan-leak gate's own escape; a default-branch check there could ignore it, but the plan-leak check cannot. |

And the server already backs part of rule 1 and rule 2 (MEASURED, `gh api …/branches/master/protection`, GET):
`master` is protected, `enforce_admins: true`, `allow_force_pushes: false`, `allow_deletions: false`, required
checks `verify`, `schema-gates`, `mutation-sweep-complete`, no pull-request requirement. So a force push or delete of
master is refused server-side. A direct push of a commit that has already passed the three checks is NOT (INFERRED
from GitHub's documented semantics; not run).

**What (d) cannot do is the part that hurts most.** Round 3's C-F1 heredoc form turned off `--no-verify`,
`core.hooksPath` and `ALLOW_PLAN_LEAK` in one command. Those three rules exist to stop the agent from disabling
`pre-push`, so they cannot live in `pre-push`, and detecting them in text still needs an exact reading (`--no-veri`,
`--no-v{e,}rify`). (d) shrinks what the text gate is responsible for; it does not remove the text gate.

### 2.7 Summary by option

| option | r1–r3 findings removed BY CONSTRUCTION | false-refusal cost | cannot cover |
|---|---|---|---|
| **(a)** dual reading, refuse on union | r3 C-F1 (r1's reading refuses it), r2 X-F1..F3 (head's reading refuses them). Nothing else: 19 of 52 bypasses still pass (C-F2..C-F6, `--all`, `--mirror`). | the UNION of both readings' false refusals: 5 of 15 allowed cases; corpus: 1,166 unique on `feat/x`, identical to head (r1 adds nothing there), 1,192 on `master` | every construct neither reading models; the next construct both mis-read; two lexers and two mutation sets to maintain |
| **(b)** closed language, exact or refuse | **All of them** in text: r2 X-F1..F3, r3 C-F1, C-F2, C-F3, C-F4, C-F5, C-F6's `xargs` and `heads/`, r1's `--all`/`--mirror`. 0 of 52 pass. | level 3: 776 unique corpus commands on `feat/x` vs head's 1,166 (459 relieved, 69 new); level 1: 1,241 (77 new, 2 relieved); level 1: 1,241. 0 of 15 allowed cases. | values not in the text: aliases and functions, git aliases (`git p` has no push word, so nothing triggers), config destinations, scripts run from files, a `core.hooksPath` set by an EARLIER call, `$'\x70ush'` (the `Bash(*push*)` launch filter never fires) |
| **(c)** ask bash | none: no parse is obtainable on this machine without executing, and a parse is not an expansion | n/a | everything after parsing; adds a dependency |
| **(d)** `pre-push` | rule 1 completely, including backlog #574 (config destinations, `--all`, `--mirror`), aliases, variables and scripts | none from text | `--no-verify`, `core.hooksPath`, `ALLOW_PLAN_LEAK` (they disable the hook itself); bare `--force` vs `--force-with-lease`; a clone without `scripts/install-git-hooks.sh` |

---

## 3. Recommendation: (b), a closed language read exactly or refused, at LEVEL 1, with bash as the test oracle

**Why (b):** it is the only option that removes the class rather than its instances. Its invariant is checkable:
*no step discards a push word on a reading that is not exact*, and *exact* is defined by a language small enough
that bash performs nothing on it but quote removal (level 0) or yields an unknown-valued word (level 1). A
construct the language does not admit can only produce a false refusal. The oracle turns "exact" from a claim
into a measurement, and its own controls show it bites. It also folds the hook's rule 1 and rule 2 into ONE
reader: today rule 2 is a regex in bash over the detector's segments (where C-F5 lives), and rule 1 is a second
token loop in bash (where `heads/` lives). Two readers of one command is the class again, in miniature.

**Why level 1 for THIS fold, not level 3:** level 1 is the smallest language that removes the class. ⚠ It is NOT
free: on the corpus it refuses 1,241 unique commands on `feat/x` against head's 1,166, so **6.4% more**, with 77
new refusals and 2 relieved. I expected "no worse than head" and the measurement refutes it. The cost is bought
deliberately: every one of the 77 is a command outside the language, refused with a one-line remedy, and none is
a pass. Levels 2 and 3 add heredoc and substitution handling, the two
constructs where bash 3.2 and bash 5 are most likely to differ and where the oracle's generator needs targeted
atoms (§2.4, last control). They lower the cost substantially (1,241 → 776 unique corpus commands), so they are
worth doing, but as their own change, each with its atoms and controls, not inside a fold that is at round 3 of a
capped loop. **Filed, not built** (see the fold specification).

**Why not (a):** measured 19 of 52 bypasses still pass, and its false refusals are the union of both readings'.

**Why not (d) now:** it is the right home for rule 1's config-dependent half (backlog #574), and it needs no text
reading at all. But it cannot host the three rules that switch it off, so it does not end the tokenizer's job. It
is complementary: re-scope backlog #574 to "rule 1 in `pre-push`".

---

## Fold specification

**Goal of the fold:** replace the detector's reading and the hook's two bash-side readers with ONE function,
`decide(command, current_branch, default_branch, has_remote)`, in `scripts/push-command.py`, which reads the
command exactly over the level-1 closed language or refuses. The hook becomes an adapter.

### F1. Delete

In `scripts/push-command.py`:
- `normalize` as a reader. Keep only a quote-blind VIEW for the trigger (below), named for that.
- `lex` (the r2 quote-aware lexer), `_command_word`, `_subcommand`, `_runs_code`, `_segment`, `_judge`, `segments`,
  `GIT_WORD`, `SEPARATORS`, `SHELL_C`, `NON_PUSH_SUBCOMMANDS`, `VALUE_OPTS`, and the four modes `none` / `strict` /
  `loose` / `unresolved`. The loose layer and its `git`/`bare` kinds go entirely: there is no loose reading.
- The docstring's bound and falsifier sections; they are rewritten (F4).

In `.claude/hooks/block-default-branch-push.sh`:
- `case "$detect_rc:$mode"` with its `0:none) allow` (the early allow that put rules 2 and 3 behind a wrong `none`).
- Rule 2's `grep -qE '(^|[[:space:]])((--force|-f)…'` and `--no-verify` regexes over segments.
- Rule 1's token loop (`toks`, `n`, `dest`, `unresolved`, `targets_default`).
- Keep: jq-missing and unreadable-payload refusals, the escape-hatch prefixes, the default-branch and
  current-branch resolution (pass them to `decide`), the `142:*` deadline refusal and the `*)` fail-closed path.

### F2. Build (level 1)

`decide` returns `allow` or `deny <rule> <reason>` on stdout, exit 0; any other exit or output refuses in the hook.
1. **Trigger.** The word `push` (`PUSH_WORD`, unchanged) in ANY of: the raw text; the text with quotes and
   backslashes deleted and a backslash-newline joined to NOTHING; the same joined to a space. (Head joins with a
   space only, so `git pu\<newline>sh` is joined differently from bash in the trigger path; measured in the case
   matrix as `428-cont2`.) No trigger → `allow`.
2. **Rule 3 first.** Unless `ALLOW_DANGEROUS_PUSH=1` appears: `hookspath` or `allow_plan_leak` in the lower-cased
   quote-blind views → deny. Never behind an allow.
3. **Lex the level-1 language exactly, else deny (`OUTSIDE: <what>`).** Unquoted: `[A-Za-z0-9_./:=@+,%^-]`,
   blanks, newline, `;` `&` `|` (and their doubles), redirections `<`, `>`, `>>`, `>|`, `&>`, `&>>` with a target
   word, `N>&M`/`N<&M` only with digits. Refused: `<<`, `<<<`, `<>`, `>&` without digits (incl. `>&-`), two
   redirections in a row, a redirection with no target, and any unquoted `` ` `` `\` `#` `{` `}` `*` `?` `[` `]`
   `~` `!` `(` `)` or non-ASCII. Single quotes: anything. Double quotes: anything but a backtick or backslash; `$`
   inside them only as a level-1 parameter. `$` only as `$NAME`, `${NAME}`, `$?` `$$` `$!` `$#` `$0`–`$9`
   (unknown-valued word); `$'`, `$"`, `$(`, `$((`, `${…op…}` refused. An unbalanced quote refused.
4. **Judge every command** with the closed tables of §2.3: git global options, the push-option allowlist, `+`,
   destination normalisation (`refs/heads/`, `heads/`, `HEAD`, `@`), <2 positionals on the default branch, the
   INERT git subcommands, the TEXT commands, the CODE RUNNERS, and "anything else holding a push word". Every
   refusal names its rule and the word that caused it.
5. **Deadline:** keep `DEADLINE_S` and SIGALRM exactly as now.
6. **Refusal text** for every `OUTSIDE`: *"run the push as its own plain command: `git push -u origin <branch>`"*.

### F3. Cases and mutations

**Cases (keep every one, re-expressed against `decide` and the hook):**
- all 52 expected-deny rows of the case matrix (every r1–r3 repro, on the branch the repro names), and the 15
  expected-allow rows. The prototype's matrix is `arch-pd/cases.py` plus four extras (`echo '…' | bash`; a
  `$(cat <<'EOF' …)` commit beside a feature push, which level 1 REFUSES — record it as the documented cost; a
  `$S` path in `cd`; `python3 scripts/x.py && git push …`);
- round 1's `'HEAD:master'2>&1` row's expectation is **wrong in the r1 review** (bash's word is `HEAD:master2`,
  then `>&1`): pin it as ALLOW with that reason, or drop it;
- the existing hook self-test rows for the escape hatches, jq-missing, unreadable payload, detector exit codes
  127/137/139/142/143, and detached HEAD.

**The oracle goes in `--self-test`:** fixed seeds, a bounded N (about 1,000 strings, under 10 s), `/bin/bash`
with logging shims, the property of §2.4. Its generator must include, for every construct the language admits, an
atom exercising the under-report direction. It must report NOT RUN (a failure) if `/bin/bash` is missing.

**Mutations (`scripts/mutations/push-command.json`, 47 today, every one anchored in code F1 deletes):**
- **Retire all 47**; their anchors cannot bind. (Lowering the ratchet is deliberate and written in the same
  commit, per `CONTEXT.md` → *Ratchet*.)
- **Add one per decision branch** of the new reader, each naming the case it reddens:
  1. the trigger reads only the raw text (`git p"u"sh origin master` allowed);
  2. rule 3 runs after the lexer (a heredoc / outside-language form with `-c core.hooksPath` then reports OUTSIDE,
     not rule 3 — pin the rule NAME in that case);
  3. one per OUTSIDE class: `<<` accepted; `{`/`}` accepted; `*`/`?`/`[` accepted; `#` accepted; backslash
     accepted; `$"`/`$'` accepted; a backtick inside double quotes accepted; `>&` with a non-digit accepted;
  4. the quote state is ignored for separators (a quoted `;` splits);
  5. a redirection's target is kept as a word;
  6. an unknown git global option is skipped instead of refused (`--attr-source stash push`);
  7. an unknown push option is skipped instead of refused (`-uf`, `--no-veri`, `--all`);
  8. `+refspec` is ignored;
  9. `heads/` (and separately `HEAD`/`@`) is not normalised;
  10. `push` is in the INERT list (or the INERT check runs before the option parse);
  11. the CODE RUNNER rule is dropped (`xargs git push origin`, `echo … | bash`);
  12. an unknown-valued word is allowed as a destination (`git push origin $B`);
  13. the deadline is not armed / SIGALRM ignored (keep the two existing deadline mutations' intent).
- **The oracle needs its own controls**, run once by hand and recorded in the fold's commit message: the three of
  §2.4 (substitution unreported is moot at level 1; use "a redirection's target is not dropped" and "`>&-` is
  accepted" instead), each showing the oracle reddens.

### F4. The bound, rewritten

Replace the bound with this sentence and its measurement: *a command holding the word `push` is refused unless it
is written in the level-1 closed language and every command in it is judged allowed.* State the corpus cost
measured here (1,241 unique / 1,374 occurrences on `feat/x`, against head's 1,166 / 1,292 on `feat/x`), name the common refusals (a heredoc or `$(` beside a push; `${S:?}`;
`[ … ]`; `@{u}`; a backslash continuation), and the remedy (a separate, plain push command). State OUT OF SCOPE
plainly: values not in the text (aliases, functions, git aliases with no push word, config destinations, scripts
run from files, a `core.hooksPath` set by an earlier call) and `$'\x70ush'`, which the launch filter never sees.

### F5. Disposition of round 3's findings

| finding | disposition under this fold |
|---|---|
| C-F1 (High) heredoc body makes a real push a `git stash` argument | **FIXED BY CONSTRUCTION**: `<<` is outside the level-1 language → deny |
| C-F2 `--attr-source stash` as subcommand | **FIXED BY CONSTRUCTION**: closed global-option table (`--attr-source` takes a value; any unknown option with a push word → deny) |
| C-F3 brace expansion, globs | **FIXED BY CONSTRUCTION**: unquoted `{ } * ? [ ]` outside the language |
| C-F4 `$"…"` | **FIXED BY CONSTRUCTION**: only level-1 parameters are admitted after `$` |
| C-F5 `-uf`, `--no-veri` | **FIXED BY CONSTRUCTION**: push-option allowlist |
| C-F6 `xargs`, `HEAD:heads/master` | **FILED to backlog #574**, as the coordinator ruled. The fold's tables refuse both incidentally (the CODE RUNNER rule; `heads/` in the destination normalisation) and the case matrix pins them, so #574's TEXT half closes; its remainder is the config half |
| C-F7 the bound overstates the quoted `<`/`>` refusal | **FIXED BY DELETION**: the sentence goes with the bound (F4) |

### F6. Filed, not built

- **Widen the closed language to level 2 (heredocs) and level 3 (`$( … )`)**, each with oracle atoms for its
  under-report direction and a red control. Measured gain: corpus refusals on `feat/x` 1,241 → 961 → 776 unique.
  Its falsifier: the oracle reports an unsafe string, or a control does not redden.
- **Re-scope backlog #574 to option (d):** rule 1 in `.githooks/pre-push` over the concrete refs, which closes
  config destinations, git aliases, variables and scripts. The three hook-disabling rules stay in the text gate.

---

## Measured vs inferred

| claim | status | how |
|---|---|---|
| master/r1/head/(a)/(b) false-pass and false-refusal counts over 67 cases | MEASURED | each hook run over JSON stdin in fixture clones on `feat/x` and `master`; (a) = deny if r1 or head denies |
| corpus: 1,634 unique / 1,794 occurrences; head modes 1,142/435/50/7 | MEASURED | `arch-pd/extract.py` over 809 transcript files; head's `segments()` imported |
| corpus refusals by hook version | MEASURED | `arch-pd/runhooks.py`, every command through each hook in both fixtures |
| (b) refusals per level (1,436 / 1,241 / 961 / 776 on `feat/x`); level 1 is +77 / −2 against head, level 3 +69 / −459 | MEASURED | `arch-pd/bprime2.py` over the corpus |
| level 3 refuses 53 of 435 head-`strict` pushes on `feat/x` | MEASURED | same run, cross-tabulated with head's mode |
| the oracle found `>&-` differentials in the level-0 prototype; 0 unsafe after the fix (L0 1,843; L3 ~3,500 accepted strings) | MEASURED | `arch-pd/fuzz.py`, `fuzz2.py`, `/bin/bash` 3.2.57 with logging shims |
| oracle controls: 128 / 1 / 0→66 unsafe | MEASURED | one-line mutations of `bprime2.py`, oracle re-run |
| the prototype decides the corpus in 1.9 s total, worst 13 ms; a 300,000-character command in 209 ms | MEASURED | timed in-process (interpreter start not included) |
| `--pretty-print` unavailable; `bash -n` exits 0 on the C-F1 bypass; bashlex / tree-sitter-bash absent | MEASURED | run on this machine |
| `--no-verify` bypasses pre-push; pre-push stdin carries resolved refs | MEASURED (documentation) | `git push --help`, `man githooks`, git 2.49.0 |
| `core.hooksPath` is set in this clone | MEASURED | `git config --get core.hooksPath` |
| master protection: admins enforced, no force, no delete, three required checks, no PR requirement | MEASURED | `gh api …/branches/master/protection` (GET) |
| pre-push cannot tell `--force-with-lease` from `--force` | INFERRED | from the stdin format; a real push would be needed |
| GitHub refuses a direct push of an unchecked commit to master, but not of an already-green one | INFERRED | GitHub's documented required-check semantics; not run |
| a third-party parser would bring its own differentials; a parse still leaves expansions | INFERRED | not measured |
| bash 3.2 and 5.x differ most around heredocs inside `$( … )` | INFERRED | not measured here; the reason level 2/3 are deferred and the oracle runs under both shells |
| level 1 alone (the recommended fold) passes the 67-row matrix | MEASURED: 0 false passes of 52; 1 false refusal of 15 (the `$(cat <<'EOF' …)` commit, which head also refuses) | |

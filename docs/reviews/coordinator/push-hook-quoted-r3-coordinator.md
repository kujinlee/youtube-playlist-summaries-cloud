# Round 3 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — NOT CONVERGED; THRASHING → Phase 6

REVIEW GAP: codex — alternation

```yaml
round: 3
fixes_nontrivial: true
subject: push-hook-quoted
halves:
  codex: gap
  claude: ran
findings:
  - {id: C-F1, severity: High, aim: deliverable, fix_induced: true, component: detector-tokenizer, disposition: fixed}
  - {id: C-F2, severity: Medium, aim: adjacent, fix_induced: false, component: detector-tokenizer, disposition: fixed}
  - {id: C-F3, severity: Medium, aim: adjacent, fix_induced: false, component: detector-tokenizer, disposition: fixed}
  - {id: C-F4, severity: Medium, aim: adjacent, fix_induced: false, component: detector-tokenizer, disposition: fixed}
  - {id: C-F5, severity: Medium, aim: adjacent, fix_induced: false, component: flag-rules, disposition: fixed}
  - {id: C-F6, severity: Low, aim: adjacent, fix_induced: false, component: destinations, disposition: filed}
  - {id: C-F7, severity: Low, aim: deliverable, fix_induced: true, component: bound-prose, disposition: fixed}
```

Claude (`docs/reviews/claude/push-hook-quoted-r3-claude.md`) reviewed `8e5e3d69`. It ran every probe against head, the
round 1 version and master's hook, using a shell function standing in for `git` to see what bash actually runs.

**C-F1 (High, FOLD-INDUCED).** The r2 lexer reads a heredoc BODY as commands. A quote in the body opens a quote that
bash never sees, the real push after `EOF` lands inside a `git stash` command's arguments, it is exempted, and the
detector reports `none`. That one form gets past the default-branch rule, `--force`, `--no-verify`, core.hooksPath
and ALLOW_PLAN_LEAK. Master and round 1 both refuse it.

**C-F2 and C-F3 (Medium) reproduce the two leads from the automated security review:**
- C-F2: `--attr-source stash` reads `stash` as the subcommand.
- C-F3: brace expansion and globs (`{master,}`, `/usr/bin/gi? push`).

**C-F4:** `$"…"` is handled as if it were `$…`.

**C-F5:** bundled short flags (`-uf`) and abbreviated long flags (`--no-veri`) slip past the flag rules.

**THRASHING.** Round 2's Highs came from round 1's fold, and C-F1 comes from round 2's fold. That is two consecutive
rounds in ONE component, the detector's tokenizer. Phase 6 is armed: a narrow architecture review,
`docs/reviews/architecture-review-2026-11-08-push-detector.md`. The fold follows its verdict.

**The reviewer's proposal, for Phase 6 to judge.** Each round so far has been the same class: the detector lexes
differently from bash, and the difference reaches a step that DISCARDS a push word. The reviewer suggests:
- discard a push word only when BOTH the quote-blind reading (round 1's) and the quote-aware reading (round 2's) say
  it is harmless, so that refusal is the union of both;
- treat unquoted expansions in a `push` command as unresolved;
- exempt a command only when every word before its subcommand is a recognised option.

**C-F6 (Low):** `xargs`, and `HEAD:heads/master`. This joins backlog #574, which already covers destinations the
command text never shows.

---

## Phase 6 outcome

**Chosen: design (b) at level 1** (`docs/reviews/architecture-review-2026-11-08-push-detector.md`, *Fold
specification*). One function, `decide`, in `scripts/push-command.py` reads the command exactly over a closed
language or refuses it, runs rule 3 before lexing, and judges every command from closed tables. The hook is an
adapter: it resolves the branches and prints the refusal for the rule `decide` names.

**Why (b).** It is the only option the review measured that removes the class (a reading that differs from bash's,
reaching a step that discards a push word) rather than its instances. Inside the language bash does nothing but
split words, remove quotes and substitute parameters, so there is no inexact reading for a discard to run on, and
anything outside it can only cost a false refusal. Option (a), refusing on the union of the round 1 and round 2
readings, still passed 19 of the 52 bypass repros. Option (c), asking bash, yields no parse without executing.
Option (d), `pre-push`, cannot host the three rules that switch it off; it takes rule 1's config half instead.

**Why level 1, not level 3.** Heredocs and `$( … )` are where bash 3.2 and bash 5 most likely differ (INFERRED in
the review), and each needs its own agreement atoms and controls. That is too much to add inside a capped loop at
round 3, so levels 2 and 3 are filed (backlog #579).

**Measured costs:**

| measure | value | how |
|---|---|---|
| r1–r3 bypass repros that pass | **0 of 52** | the review's case matrix, re-expressed as `--self-test` rows `matrix …` against `decide` |
| expected-allow rows refused | 1 of 15, the documented cost: a `$(cat <<'EOF' …)` commit beside a feature push (`matrix x-2`) | same |
| corpus refusals, review prototype (level 1) | 1,241 unique / 1,374 occurrences on `feat/x`, against round 2's hook at 1,166 / 1,292: **6.4% more (77 new, 2 relieved)** | the review's run |
| corpus refusals, this fold | **1,250 / 1,383 on `feat/x`: 7.2% more than round 2's hook (86 new, 2 relieved)**; on `master`, 1,258 / 1,391 (80 new, 6 relieved) | `decide` in-process over the same 1,634 commands, against round 2's recorded hook results |
| what the 9 beyond the prototype are | a parameter as a command word (6) or before a git subcommand (3): `$PY x.py`, `git -C $W push …` | same run, diffed against the prototype |
| bash-agreement check | 0 unsafe of 240 accepted strings (1,018 run: 18 fixed per-construct inputs and 2 seeds × 500), `/bin/bash` 3.2.57; each of 6 broken-lexer controls reddens it (7 to 69 unsafe) | `--self-test` |
| `decide` time, corpus | 1.1 s for 1,634 commands, worst 4 ms | in-process |

**Where the fold departs from the specification, and why:**
- **`&>>` is OUTSIDE.** The specification admitted it. The agreement check's per-construct input failed: bash
  3.2.57 refuses `&>>` as a syntax error while bash 4+ reads it as an append. The language has to be what both
  shells read the same way, so `&>>` is refused.
- **An UNQUOTED parameter has an unknown word COUNT, not just an unknown value.** Bash splits `$X`, so
  `X="x push origin master"; git -C $X` runs `git -C x push origin master` with the value in the text (INFERRED from
  bash's word splitting; not run, since it would push).
  An unquoted parameter is marked separately (`SPLIT`). A double-quoted one (`UNKNOWN`) is always exactly one word.
  On top of the specification's rule (an unknown word in a git command holding a push word is refused, except the
  `-C` value):
  - a parameter as a command word is refused (`$X` with `X="git push origin master"`);
  - so is one at or before a git subcommand (`git $P origin master`), and an unquoted `-C` value;
  - so is one given to a runner of its arguments (`env $C`, `xargs $C`, `timeout 5 $C`).

  That costs the 9 extra corpus refusals above. A script runner given a parameter (`python3 "$S/x.py"`) is not
  refused: it runs a file, which is out of scope. Restricting the rule this way removed 98 refusals measured in a
  first cut.
- **`--verify` joins the push-option allowlist.** It is the default and is harmless.
- **Detector exit codes 127 / 137 / 139 / 143 and detached HEAD.** The specification called these existing rows;
  they were not on the branch. They are added to `--self-test` through the delivered hook, together with an empty
  output, a bare `deny` and an unknown verdict, each REFUSED with NOT CHECKED.
- **The agreement check runs ONE bash process**, which `eval`s each string in a subshell with `wait`. The
  alternative was one `bash -c` per string. All 1,018 strings now take about 5 s locally.

**Round 3 findings:**

| finding | disposition |
|---|---|
| C-F1 heredoc body | FIXED BY CONSTRUCTION: `<<` is outside → refused (`matrix r3-F1a..e`, hook `C-F1 r3`) |
| C-F2 `--attr-source stash` | FIXED BY CONSTRUCTION: closed global-option table (`matrix r3-F2a..c`) |
| C-F3 brace expansion, globs | FIXED BY CONSTRUCTION: unquoted `{ } * ? [ ]` outside (`matrix r3-F3a..g`) |
| C-F4 `$"…"` | FIXED BY CONSTRUCTION: only simple parameters after `$` (`matrix r3-F4a..b`) |
| C-F5 `-uf`, `--no-veri` | FIXED BY CONSTRUCTION: push-option allowlist (`matrix r3-F5a..c`) |
| C-F6 `xargs`, `heads/` | FILED → backlog #574 (amended: C-F6 joins; re-scoped to rule 1 in `.githooks/pre-push`). The fold refuses both incidentally (`matrix r3-F6a..b`), so #574's TEXT half is closed; the config half remains |
| C-F7 the bound overstated the quoted `<`/`>` refusal | FIXED BY DELETION: the bound is rewritten (docstring *THE BOUND*) |

**Filed:**
- **backlog #579 (new):** widen the closed language to level 2 (heredocs) and level 3 (`$( … )`), each with its own
  agreement atoms and a control that reddens.
- **backlog #574 (amended):** C-F6 joins it, and it is re-scoped to rule 1 in `.githooks/pre-push` over the resolved
  refs: config destinations and git aliases.

**Mutations:** the 47 in `push-command.json` are retired, since every anchor sat in code the fold deletes. 79 new
ones were added, one per decision branch, with the pin arithmetic in `expected_mutations.py`: 47 − 47 + 79 = 79.
Each was hand-checked one at a time in a `stage_tree` copy. The decision-log row is `route: redesign`,
`skipped: ["accrete"]`, `outcome: null`, `rounds_at_termination: 3`, with a falsifiable prediction for round 4.

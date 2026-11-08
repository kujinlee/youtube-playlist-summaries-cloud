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

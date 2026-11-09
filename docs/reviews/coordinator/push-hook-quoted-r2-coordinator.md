# Round 2 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — NOT CONVERGED; fold removes the CAUSE

REVIEW GAP: claude — alternation

```yaml
round: 2
fixes_nontrivial: true
subject: push-hook-quoted
halves:
  codex: ran
  claude: gap
findings:
  - {id: X-F1, severity: High, aim: deliverable, fix_induced: true, component: detector-tokenizer, disposition: fixed}
  - {id: X-F2, severity: High, aim: deliverable, fix_induced: true, component: detector-tokenizer, disposition: fixed}
  - {id: X-F3, severity: High, aim: deliverable, fix_induced: true, component: detector-tokenizer, disposition: fixed}
  - {id: X-F4, severity: Low, aim: deliverable, fix_induced: true, component: bound-prose, disposition: fixed}
```

Codex (`docs/reviews/codex/push-hook-quoted-r2-codex.md`) reviewed `9045d5dc`.

**Held:** every failure exit refuses (127, 137, 139, 142, 143), all 32 mutations are sound, and a detached `HEAD`
gives no bypass.

**All three Highs came from the round 1 fold, and they share ONE cause.** The fold DELETES quotes and backslashes
BEFORE it splits the command, so quoted text becomes shell syntax:
- **X-F2:** a quoted `'>'` becomes a redirection that eats the next flag or the destination.
- **X-F3:** a quoted `';git stash'` becomes a separate `git stash` chunk, which exempts the real push.
- **X-F1:** a quoted `;` splits one invocation. Separately, a strict match in a chunk suppresses every other push in
  that chunk, including a real one before a `#`.

Patching each repro would leave the cause in place, so the fold REPLACES the tokenizer:
- Lex the command the way the shell does (`shlex.shlex(posix=True, punctuation_chars=True)`, or an equivalent
  quote-aware scanner), keeping the knowledge of which characters were quoted.
- Separators and redirections count only when UNQUOTED.
- Commands are split only at unquoted separators.
- A command's subcommand is the first non-option word after `git` and its global options, so `-c k=v` and `-C dir`
  are consumed with their values.
- Every invocation is judged. No strict match suppresses another.
- An unquoted `#` at a word start begins a comment, as in bash. A push inside the comment is text, not a push. But
  the case `/usr/bin/git push origin master # …` must judge the real push before the `#`.
- Lexing failure (an unbalanced quote) and any construct the lexer cannot resolve (`$(`, backticks, `eval`,
  `sh -c`, subshells) keep the existing fail-closed rule: if `git` and `push` both appear, REFUSE.

**X-F4 (Low):** restate the false-refusal bound to include dangerous flags in loose text (`git log --grep "push
--force"`) and the stash exceptions, with cases.

**Seen live on 2026-11-08 at 14:35:** this branch's own detector, run as the session's hook from this worktree,
refused the coordinator's `git add` of this file, because the heredoc carrying this text held backticks. That is the
documented fail-closed bound working (a command containing both words, with shell syntax it cannot resolve). It was
worked around by writing the file directly.

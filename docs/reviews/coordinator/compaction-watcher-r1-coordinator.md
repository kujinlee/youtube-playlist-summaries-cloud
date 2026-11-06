# Round 1 — `compaction-watcher` — coordinator — ⟳ NOT CONVERGED (both halves); RESTRUCTURE (denylist → allowlist)

```yaml
round: 1
fixes_nontrivial: true
subject: compaction-watcher
halves:
  codex: ran
  claude: ran
findings:
  - {id: R1, severity: High, aim: deliverable, fix_induced: false, component: question-watcher-rule, disposition: fixed}
  - {id: R2, severity: High, aim: deliverable, fix_induced: false, component: question-watcher-rule, disposition: fixed}
  - {id: R3, severity: High, aim: deliverable, fix_induced: false, component: question-watcher-rule, disposition: fixed}
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: question-watcher-rule, disposition: fixed}
  - {id: F2, severity: Low, aim: instrument, fix_induced: false, component: question-watcher-tests, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: docstring, disposition: fixed}
```

**Subject:** `git diff origin/master...HEAD` on `compaction-watcher` (PR #527, backlog #537), both halves on `2d69761c`.
**Halves:** `codex/compaction-watcher-r1-codex.md` (3 High, `gate_ran=true`, model `gpt-6.1-sol`) ·
`claude/compaction-watcher-r1-claude.md` (F1, F2 minor; F3 nit; verdict JSON `gate_ran=true`).

**One root, both halves.** `question_watcher()` was a DENYLIST: a regex for the first stage, then a search for `;`,
`&&`, `||`, `$(` and a backtick after a regex strip of `'...'`. Every finding but F3 is a shape the list did not name,
or a strip that disagreed with bash about where a quote is. Adding more denied tokens would leave the class open, so the
rule is now an ALLOWLIST over a real tokenizer.

**The new rule** (`scripts/check-compaction-boundary.py`, `question_watcher`, `_watch_stage`,
`_substitution_outside_single_quotes`):
- refuse a newline, and any `$`, backtick, `<(` or `>(` outside single quotes (a quote-aware scan: a backslash escapes
  outside single quotes, a `'` inside double quotes is literal);
- tokenize with `shlex.shlex(posix=True, punctuation_chars="();<>|&")`, `whitespace_split=True`, `commenters=""`
  (bash reads `a#b` as one word; shlex's default would drop everything after the `#`); an unparsable command is refused;
- stage 1 is `tail` with `-F`, an optional `-n N`/`-nN`, exactly ONE path equal to or ending in
  `/explainers/questions.md`, and optionally `2>/dev/null` or `2>&1`;
- every later stage is split on `|` alone, starts with a filter (`awk grep sed cut head tr cat`), and holds no
  operator token.

**Dispositions.**
- **R1 (Codex High) — fixed.** `| gh run watch 123`, `| tee`, `| xargs … gh`, `| sh` are refused by the filter
  allowlist; `|&` (with work or with `cat`) by the operator rule.
- **R2 (Codex High) — fixed.** `cat <(…)`, `cat >(…)`, `tee >(…)` are refused twice over: shlex makes `<(` an operator
  token, and the scan refuses it. A `<(` inside double quotes (inert in bash) is refused by the scan alone, so that
  clause has its own case.
- **R3 (Codex High) — fixed.** `echo \' ; gh run watch 123 # '` and `cat \' ; …` are refused: shlex reads `\'` as an
  escaped quote and yields a real `;` token. A backtick after `\'`, which shlex reads as a plain word, is refused by the
  scan, and that is the case that kills the "backslash no longer escapes" mutation. The newline half of R3 is F1's.
- **F1 (Claude minor) — fixed.** The same defect as R1-R3. Background `&`, newline, `>(`, a `'` inside double quotes
  hiding a `;`, and `|&` are each a refused case. The docstring no longer claims "nothing chained outside quotes"; it
  states the allowlist, plus one new BOUND: the allowlist judges the SHELL, not the filters' own languages (awk's
  `system()` or a sed `e` inside single quotes is not seen). The 2 live `2>&1` shapes stay matched, which was the caution.
- **F2 (Claude minor) — fixed.** Every clause now has a case that ONLY it answers, and a mutation killed by that case:
  `||`, `;`, `&&`, `&`, `|&` (operator rule); `$(` and a backtick inside double quotes, `${`, a double-quoted `<(` (the
  scan, whose shlex twin cannot see them); the "greedy strip" became "a single-quoted region ends at the NEXT quote";
  `.search` vs `.match` became a first-stage case, `less -F ~/explainers/questions.md`. Two clauses were found masked
  while writing the mutations, and both were deleted, not pinned. The stage-1 operator check was redundant, because any
  operator token there is a second path and the one-path rule refuses it. The `\r` refusal guarded nothing, because bash
  reads CR as an ordinary character.
- **F3 (Claude nit) — fixed.** The log has 4 `block-monitor` rows for the session (11:00:34, 11:01:53, 11:04:48,
  11:07:37; ctx 237,702-247,039), and the docstring now says so.

**Measured, not recalled.**
- **Corpus.** Every Monitor `tool_use` in `~/.claude/projects/-Users-kujinlee-…-cloud/*.jsonl` (assistant and
  `api-request-blob` records; 22 files, 356 commands). The new rule matches **141 of 141** `questions.md` commands and
  **0 of 215** others. No real watcher stops matching. Bound: top-level transcripts only, as in round 1.
- **Suite.** `--self-test` went from 87 to 99 cases. Seven of the new cases were RED on `2d69761c` before the rule
  changed.
- **Mutations.** 5 regex-anchored entries were retired and 18 added, one per clause, so the pin moves 55 → 68. The
  `check-plan-code.py --mutate . --only scripts/check-compaction-boundary.py` (with the main checkout's `node_modules`
  linked in for the run): **68 mutations, 68 killed, 68 attributed to the case each names, 0 survivors**.

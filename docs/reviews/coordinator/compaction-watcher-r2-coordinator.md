# Round 2 — `compaction-watcher` — coordinator — ⟳ NOT CONVERGED (Codex half); RESTRUCTURE (token allowlist → exact templates)

```yaml
round: 2
fixes_nontrivial: true
subject: compaction-watcher
halves:
  codex: ran
  claude: skipped
findings:
  - {id: R2-1, severity: High, aim: deliverable, fix_induced: false, component: question-watcher-rule, disposition: fixed}
  - {id: R2-2, severity: High, aim: deliverable, fix_induced: true, component: question-watcher-rule, disposition: fixed}
  - {id: R2-3, severity: Medium, aim: deliverable, fix_induced: false, component: question-watcher-rule, disposition: fixed}
```

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

**Subject:** `git diff origin/master...HEAD` on `compaction-watcher` (PR #527, backlog #537), Codex half on `2a92ecbf`.
**Half:** `codex/compaction-watcher-r2-codex.md` (2 High, 1 Medium, `gate_ran=true`, model `gpt-6.1-sol`).

**One root again, and it is the rule's SHAPE.** Round 0's regex denylist and round 1's shlex allowlist each judged the
command in terms of shell features, and each was widened by a feature it did not name: in round 2, a filter's FILE
argument (R2-1), a redirect whose adjacency or quoting shlex threw away (R2-2, caused by round 1's own tokenizer) and
brace or glob expansion (R2-3). Patching the three would leave the next feature open. So the design question was
measured first: how many distinct watcher commands exist?

**Measured.** Every Monitor `tool_use` in `~/.claude/projects/-Users-kujinlee-…-cloud/*.jsonl` (assistant and
`api-request-blob` records; 22 files, 356 commands, the same corpus as round 1). Of the 141 that name `questions.md`,
normalizing ONLY the path and the `-n` number leaves **5 distinct shapes**:

| | count | after `tail -n N -F <path>` |
|---|---|---|
| S1 | 136 | ` 2>/dev/null \| awk '…printf "%s \| quoted: %s \| %s\n"…'` — explainer-delivery.md §5 |
| S2 | 2 | ` \| grep --line-buffered -v '^\s*$'` (written `-n0`) |
| S3 | 1 | ` 2>&1 \| awk '…printf "ASK \| %s \| quoted: %s \| %s\n"…'` |
| S4 | 1 | ` 2>/dev/null \| grep --line-buffered -E '^## 20\|^\*\*[0-9]+ ·\|^   Q:'` |
| S5 | 1 | ` 2>&1 \| grep -E --line-buffered 'Q:\|^## \|question\|asked\|ERROR\|No such file'` (an absolute path) |

Paths: `~/explainers/questions.md` 140×, one absolute path 1×. Five is small, so the rule is now **EXACT TEMPLATES**.

**The new rule** (`scripts/check-compaction-boundary.py`, `question_watcher`, `WATCHER_PATH`, `WATCHER_HEAD`,
`WATCHER_SHAPES`, `WATCHER_TEMPLATES`): `re.fullmatch` of `tail -n ?[0-9]+ -F <path>` followed by one of the 5 shapes,
each `re.escape`d from the transcript VERBATIM. The path is `~` or `/…` of `[A-Za-z0-9._/-]`, ending
`/explainers/questions.md`. Nothing else varies. `shlex`, the substitution scan, the filter list and the redirect list
are deleted. A rule that names no shell feature cannot be widened by one, so R2-1, R2-2 and R2-3 close as a class.
⚠ **COST, stated in the docstring:** a watcher written in a NEW shape is not matched and blocks compaction up to the
ceiling until its shape is added. That fails SAFE: it is the behaviour before backlog #537.

**Dispositions.**
- **R2-1 (Codex High) — fixed.** `QB | cat /tmp/ci-events.fifo` (Codex's input), the §5 watcher with a trailing awk FILE
  argument, and S4 with a trailing grep FILE argument are each refused: the template ends where the real program ends.
- **R2-2 (Codex High, fix-induced) — fixed.** `2 >&1`, `'2'>&1`, `2 >/dev/null` and `"2">/dev/null` are refused: the
  redirect is part of the literal, so a byte added or a quote around `2` is another command.
- **R2-3 (Codex Medium) — fixed.** `/tmp/{questions,ci}/…`, `/tmp/*/…`, `/tmp/c?/…`, `/tmp/[cq]i/…` and `~/{a,b}/…`
  are refused by the path's character class.

**Red first.** The three R2 cases went in before the rule changed: on `2a92ecbf` all 12 inputs returned True
(`99/102`). After the change: `105/105`.

**Cases.** Round 1's negatives are all kept. Changed: the "REAL watcher shapes" case is now the 5 transcript commands
byte for byte (checked against the corpus), plus the path and N varied; round 1's synthetic positives (a bare
`tail -F`, a five-filter chain, a shortened awk) are not real shapes, so they moved to a negative case that states the
BOUND. Round 1's "single-quoted program text is inert" positive is now a negative in that case too, because it is not
a real shape. New: START anchor, END anchor (after a newline too), and ADJACENT (no `-F`, a non-digit N, a directory
that only ends in `explainers`). The non-string case is now lazy, so a mutant that raises prints its `[FAIL]` instead
of stopping the suite.

**Mutations.** The 18 entries for the shlex rule's clauses are retired (those clauses no longer exist); 14 are added,
one per template clause: the end anchor, the start anchor, the path's character class, its directory boundary, the
`~` alternative, N as digits, `-F` required, `re.escape`, the `str` check, and each of the 5 shapes. Pin 68 → 64. Each
anchor was asserted to occur exactly once in the source when the entries were written.

**Corpus re-measured on the new rule:** **141 of 141** watchers match, **0 of 215** others.

**Added in round 3 (counts):** "141 of 141" and "0 of 215" count transcript RECORDS; an `api-request-blob` repeats the `tool_use` id of an assistant record. By distinct call: **106/106** watcher calls, **0/193** others, **5 distinct watcher commands**.

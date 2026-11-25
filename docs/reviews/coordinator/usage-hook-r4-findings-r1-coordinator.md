# Round 1 — `usage-hook-r4-findings` (PR #634, backlog #688 X2) — coordinator — Codex CONVERGED, Claude CONVERGED with 3 MINOR

Codex half: `docs/reviews/codex/usage-hook-r4-findings-r1-codex.md`. Claude half:
`docs/reviews/claude/usage-hook-r4-findings-r1-claude.md`. Both reviewed `c89ce07f`.

```yaml
round: 1
fixes_nontrivial: true
subject: usage-hook-r4-findings
halves:
  codex: ran
  claude: ran
findings:
  - {id: MINOR1, severity: Low, aim: instrument, fix_induced: false, component: x1-record, disposition: fixed}
  - {id: MINOR2, severity: Low, aim: instrument, fix_induced: false, component: check-run-hook, disposition: fixed}
  - {id: MINOR3, severity: Low, aim: instrument, fix_induced: false, component: check-run-hook, disposition: fixed}
```

**Both halves confirmed:** both pre-root exits give a usage hook's fixed NOT RUN JSON with exit 0; every non-usage hook
stays exit 1 with an empty stdout; X1 staying FILED is right. Codex found nothing. The launcher
(`.claude/hooks/run-hook.sh`) is unchanged by this fold.

| Finding | Verified against the code | Fold |
|---|---|---|
| **MINOR1** — X1's written reason generalises from one prototype | True. Row 688 and the dashboard entry said fixing X1 "would also stop the guard running inside submodules". Only one pin was ever run over the suite (to `CLAUDE_PROJECT_DIR`'s common dir). | The dashboard sentence and row 688 now say the ONE pin tried made 12 cases red. Row 688's **Fix** names the reviewer's narrower check (the session's `--show-toplevel` must appear in `git -C "$main" worktree list --porcelain`) as the candidate to measure first. It is marked **NOT RUN over the suite**. X1 stays FILED. |
| **MINOR2** — no unreadable-cwd case for the prompt hook | True. OUT_PROMPT existed; the deleted-cwd exit had only GONE_USAGE (the systemMessage channel). | New case GONE_PROMPT (`usage-pace-prompt.sh`, `vanish=True`, want PROMPT_JSON, exit 0), added to mutant pr688b's kill set. CONTROL: the branch's checker over **origin/master's** `run-hook.sh` turns GONE_PROMPT red, `got (1, None, True, '')`, alongside OUT_USAGE, GONE_USAGE and OUT_PROMPT. |
| **MINOR3** — "X2" named two findings in one file | True. The new rows were `X2 #688 …`; the backlog #513 r1 rows `NL`/`NLCD` are `X2 a worktree …`/`X2 a commondir …`. | The new cases are labelled `PREROOT #688 …` (unused in the file before), and mutants x2a–x2d are now pr688a–pr688d. The docstring, row 688 and the dashboard entry follow. No `scripts/mutations/*.json` named them (grep found none). The #513 `X2` rows and their manifest anchors are untouched. |

**`fixes_nontrivial: true`, and why:** MINOR2 adds a world case, which is test code that no reviewer has seen. MINOR1
writes a new claim about a candidate fix. Both are small, but neither is purely editorial.

**Gates after the fold:** `check-run-hook.py` 91/91 worlds; `--self-test` 173/173 (pr688a–pr688d each killed);
`check-docs.py` OK; `gen-backlog-page.py --self-test` 250/250; `check-reference-namespace.py --base origin/master` OK;
the all-manifest anchor resolve shows 6738 anchors, 0 not found exactly once.

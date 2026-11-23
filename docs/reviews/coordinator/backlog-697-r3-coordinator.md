# Round 3 — `backlog-697` — coordinator — CONVERGED; two fail-closed crashes filed, one doc nit fixed

```yaml
round: 3
fixes_nontrivial: false
subject: backlog-697
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: Minor, aim: deliverable, fix_induced: false, component: closure-guard, disposition: filed}
  - {id: F2, severity: Nit, aim: deliverable, fix_induced: false, component: closure-guard, disposition: filed}
  - {id: F3, severity: Nit, aim: deliverable, fix_induced: true, component: docs, disposition: accepted}
```

The Claude half reviewed 36a03112, the round-2 fold: [`claude/backlog-697-r3-claude.md`](../claude/backlog-697-r3-claude.md). **VERDICT: CONVERGED.**

REVIEW GAP: codex — alternation (round 3)

**What held:**
- Attempts to ship a quote as a dotfile, behind a binary prefix, through a symlink, and in a reusable-workflow file each came back as a gap.
- A declared file the repository lacks is refused.
- Genuine clean builder output is read as clean, including zero group-D sources, very large counts, paths with spaces and duplicate basenames.
- The paraphrased comment in `scripts/gen-backlog-page.py` keeps its meaning, and the original wording appears nowhere in the tree.
- The real tree's `--closure` gives 0 gaps.
- 4 new mutations, each run in its own full clone, turned their named case red.
- Self-tests: check-shipping-sets 170/170, gen-backlog-page 250/250, build-shipped-corpus 31/31.

## Dispositions

- **F1 (MINOR, not fix-induced): a `dup-N` basename collides with the scratch copy's own collision route, and an uncaught `FileExistsError` exits rc 1. FILED as backlog #709.** It fails closed, and no real shipped file has that shape. The copy loop is round 1's code.
- **F2 (NIT, not fix-induced): a shipped name containing `: ` splits the hit-line parse, so the result is CANNOT RUN, not a gap. FILED in backlog #709.** It fails closed, and the regex is round 1's.
- **F3 (NIT, fix-induced, docs): the dashboard entry said the contract requires one `<source>: <n> quotes` line per group-D source. ACCEPT.** **Fixed in this commit:** it now says "any number of", which is what `_not_clean` accepts.

## Thrashing watch

**Not thrashing.** The only fix-induced finding (F3) is in docs, not closure-guard. Neither closure-guard finding was caused by the round-2 fold. The redesign bet is WON, and the decision-log row records it as stopped at round 3.

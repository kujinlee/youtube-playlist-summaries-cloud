# Round 1 — coordinator: PR #558 (goal-tree Ask tray + collapsed answers + goal bindings)

**Subject:** `goal-tree-ask` at `f21e4798`. Both halves ran (round 1). Both NOT CONVERGED.

| id | sev | both? | finding | route |
|---|---|---|---|---|
| A (Codex M1 = Claude F1) | MEDIUM | both | a malformed `docs/goal-tree-answers.json` (`answers: null`/`5`, non-string `asked`) raises outside the `try`, so the page is NOT written — breaks the PR's own claim | fold |
| B (Codex L1 = Claude F3) | MEDIUM | both | escaping of answer text, `asked`, the Older-questions key and `answers_error`, and the `_has_tray(written)` file check, are unpinned: removing each leaves 458/458 green | fold: one case per escape and one for the file-side check, each red on its mutation |
| C (Claude F2) | LOW | Claude | a thread's 💬 marker can land inside a closed older fold, invisible | fold: thread markers placed outside folds, as goal markers are |
| D (Claude F5) | LOW | Claude | PR #558 is declared under dev-speed-first; it serves comprehensibility-suite | fold: move the line. PR #557 under two goals is INTENDED (dev speed + harness safety, owner 11-11 06:38) |
| E (Codex M = Claude F6) | MEDIUM | both, pre-existing (95ec78a2) | `_ledger_numbers` drops the ref kind and reads bare `#N` in prose: `PR #558` matches `backlog #558`; `#586` in a ledger `what` attaches to merged siblings | fold: match on (kind, number) from the `thread` refs only. Exposed here, and the PR's own page shows it wrong |
| F (Claude F4) | LOW | Claude | answers show only after merge (tracked file, built from origin/master); the file is not a stale-banner source | fold: list it as a source; say it in the PR body |
| G (Claude, inferred) | LOW | Claude | 40 s compose timeout inside a 60 s Refresh limit leaves ~10 s for the snapshot | fold: measure the snapshot time and set the compose timeout so the sum fits, with the arithmetic in a comment |

Decision log: route `accrete` (first round; findings are local, none caused by an earlier fix).

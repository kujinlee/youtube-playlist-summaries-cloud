# Round 4 — `625` (backlog #625, the Ask answerer) — coordinator — NOT CONVERGED; the round cap: no BLOCKER, three filed, the loop stops

```yaml
round: 4
fixes_nontrivial: false
subject: 625
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: watcher-lifecycle, disposition: filed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: documents, disposition: filed}
  - {id: X3, severity: Low, aim: instrument, fix_induced: true, component: spend-accounting, disposition: filed}
```

REVIEW GAP: claude — alternation (owner 2026-10-28: rounds 2+ run ONE half).

Reviewed `ba7025ac7c76ea0c90a56d94b422172a3b91b196` (the Codex half only, `docs/reviews/codex/625-r4-codex.md`,
model gpt-6.1-sol). Codex numbers the findings 1–3; they are X1–X3 here. No code changed after this round. The
commit after `ba7025ac` is a merge of `origin/master` whose two conflicts were in `docs/backlog.md` and
`docs/dashboard-entries.md`; both sides were kept.

## The round cap

`docs/review-method.md` §0 Q4c: from round 4 a finding is FILED unless it is a BLOCKER. The prompt asked the
reviewer to say for each finding whether it is one, with the definition (wrong answers shown as right, data
loss, spend with no bound, a write outside the page, an action taken on a reader's text). The reviewer says
"Not BLOCKER" for all three and gives a reason for each. The coordinator agrees:

| # | Finding | Severity | Why it is not a BLOCKER | Filed as |
|---|---|---|---|---|
| X1 | A second `--stop`, typed while the first waits for the ledger lock inside `acknowledge_death`, reads the first as a live watcher and sends SIGTERM to the stale pid. Measured: an unrelated `sleep` got signal 15 | HIGH | It needs an unclean end, that pid given to another process, and two stops at once. No reader's text can cause it; no page, ledger or spend is affected. The harm is one SIGTERM to one process of the owner | backlog #638 (widened, raised to 🟠) |
| X2 | §6b says a question that FAILED is answered by the next start. Measured: it stays failed; `--retry` is the remedy | LOW | The failure stays loud on the page. The sentence is wrong, the code is as designed | backlog #640 |
| X3 | The round-3 case for "usage NOT reported" asserts the page stamp and not the log line | LOW | A gap in a case. The code under it is correct at this head | backlog #640 |

## Thrashing or prose floor?

**Thrashing, in one component, and no longer in doubt.**

| Round | Finding | Caused by | Component |
|---|---|---|---|
| 2 | X3 — a stop after a crash changed nothing | the round-1 fold | `watcher-lifecycle` |
| 3 | C1, C2 — a stop after a crash lost the waiting questions; it could remove a live watcher's pid file | the round-2 fold | `watcher-lifecycle` |
| 4 | X1 — the function that fixed C2 holds the lock that means "a watcher is alive" | the round-3 fold | `watcher-lifecycle` |

Three rounds in a row, each finding caused by the fix before it, each in the code around `answerer.pid` and
`watch.lock`. It is not a prose floor: every one was reproduced by running code, and none is about wording.

The round-3 document said the redesign in that fold was the author's and not an independent review. Round 4
confirms the reason for saying so. `acknowledge_death` reused `watch.lock` to mean "nobody else may remove the
pid file", and that lock already meant "a watcher is alive" to every reader. One record carrying two meanings is
the defect class of all three rounds.

**What stops the loop:** the round cap, and backlog #639, the Phase 6 review of the watcher lifecycle. A fourth
fix by the same author in the same component is what the thrashing rule exists to prevent. X1 is recorded in
backlog #638, which #639 names as part of its subject.

Everything outside the lifecycle held from round 3 on. Round 3 re-attacked 14 line separators, 10 usage shapes
and 20 Origin/Host shapes. Round 4 re-attacked the round-3 fixes with two waiting questions, a session claim, a
recorded failure and a question after the stop: both waiting questions stayed NOT ANSWERED and were answered by
the restart, the claim survived, the later question was skipped, and a stop on a root that was never started
created no `.ask/`.

## What the owner should know before starting it

- After the answerer dies, type `--stop` ONCE and wait for it to print. Two stops at the same moment can signal a
  process that is not the answerer (backlog #638).
- A question that failed is not retried by a restart. `python3 scripts/ask_answerer.py --retry ID` does that.

## Decision-log row

`docs/reviews/decision-scheme/decision-log.jsonl`, subject `625`, outcome `stopped`, 4 rounds, retroactive.

# Round 3 — `625` (backlog #625, the Ask answerer) — coordinator — NOT CONVERGED; four folded, one filed; THRASHING armed in `watcher-lifecycle`

```yaml
round: 3
fixes_nontrivial: true
subject: 625
halves:
  codex: skipped
  claude: ran
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: true, component: watcher-lifecycle, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: true, component: watcher-lifecycle, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: watcher-lifecycle, disposition: filed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: spend-accounting, disposition: fixed}
  - {id: C5, severity: Low, aim: instrument, fix_induced: true, component: post-guard, disposition: fixed}
```

REVIEW GAP: codex — alternation (owner 2026-10-28: rounds 2+ run ONE half).

Reviewed `b471cb87426b2fbe17859a939a0691eea5519951` (the Claude half only, a new subagent,
`docs/reviews/claude/625-r3-claude.md`). The review numbers its findings 1–5; they are C1–C5 here.

## Thrashing: armed, in one component

The rule: two consecutive rounds whose findings were caused by the previous round's fix, in one component.

| Round | Finding | Caused by | Component |
|---|---|---|---|
| 2 | X3 — a `--stop` after a crash left the pid file, so the stop changed nothing | the round-1 fold (a crash leaves the pid file) | `watcher-lifecycle` |
| 3 | C1 — a `--stop` after a crash removed the pid file, and with it the page's NOT ANSWERED line and the next start's reason not to skip | the round-2 fold (the fix for X3) | `watcher-lifecycle` |
| 3 | C2 — that removal could delete a LIVE watcher's pid file when a start ran at the same moment | the round-2 fold | `watcher-lifecycle` |

That is the armed condition. C5 is also caused by the round-2 fold, in another component (`post-guard`) and in a
test's name only, so it does not add to it.

### What the three defects have in common

`answerer.pid` carries three meanings: which process to signal, whether the last end was clean, and whether the
next start may skip what was asked meanwhile. Round 1 gave it the second and third meanings. Each later fix
changed who writes or removes the file for ONE of the meanings and broke another.

### Can a redesign remove it?

Partly, and that part is in this fold. The rest is filed.

- **In this fold:** one function, `acknowledge_death`, is now the only place that removes the pid file after
  an unclean end. It holds the watch lock (so no watcher is alive or starting), and it writes a `retry` line
  for each waiting question BEFORE the file goes. The fact the file stood for is in the ledger first. `retry`
  already meant "never skipped by a start, NOT ANSWERED on the page while the answerer is off", so no new
  state was added.
- **Not in this fold:** the file still carries the three meanings. Separating them (the lock for liveness, a
  ledger event for the kind of end, the pid file as an address only) is a change to every lifecycle function,
  and the author of three lifecycle fixes is the wrong reviewer of a fourth design. **Filed as backlog #639, a
  Phase 6 review of the watcher lifecycle.** C3 (backlog #638) belongs to the same review.

Precedent for filing the Phase 6 review as a row and merging: PR #573, backlog #629.

## Disposition, per finding

| # | Finding | Severity | What the fold does | Case that goes red without it |
|---|---|---|---|---|
| C1 | Crash, a question asked, `--stop`, `--start`: the question is skipped and its NOT ANSWERED line disappears | MEDIUM | `acknowledge_death` records each waiting question as to-be-tried-again before it removes the pid file. The page keeps its NOT ANSWERED line; the next start answers it; a question asked after the stop is skipped | `r3: …and a question asked BEFORE that stop is kept…` |
| C2 | `--stop` racing `--start` removes the live watcher's pid file | LOW | The removal happens only while holding `watch.lock` exclusively and non-blocking. `stop` then re-reads the pid, so a watcher that started meanwhile is stopped, not reported as absent | `r3: a death is acknowledged only when no watcher holds the lock…` |
| C3 | `--stop` can send SIGTERM to a stale pid while a new watcher is starting | LOW | FILED, backlog #638. Not caused by a fold; the window is a few statements wide and needs a stop and a start typed together | — |
| C4 | An answered run that reported no usage is stamped "0 tokens" on the page and in the log | LOW | Both say "usage NOT reported". The cap already counted it as 250,000 | `r3: an answer whose run reported no usage says so on the page…` |
| C5 | The case named "the refusal comes BEFORE the body" cannot see a guard that reads the body and then refuses | LOW | The case is renamed to what it shows: the refusal comes before the body is PARSED. No code change | — (a name) |

## Bounds this fold adds

- A `--stop` after an unclean end keeps EVERY question with no ledger line at that moment, however old the
  death. Each costs a run at the next start, up to the daily caps.
- C2's case holds the lock from the suite's own process. It shows that a held lock prevents the removal; it
  does not run a real second watcher.
- C5: nothing asserts that the server refuses before READING the body. A foreign POST with a large body is
  read (up to the existing size limit) and then refused.

## Evidence

Self-tests: `ask_answerer.py` 123/123 (was 120), `explainer-serve.py` 291/291. Mutation manifests:
`ask_answerer.json` 49 → 52 (three new entries; the round-2 stop entry re-bound to the new call site),
`explainer-serve.json` 123 (one `expect` renamed). Sweep on a temp copy outside the repository:
`ask_answerer.py` 52 of 52 killed and attributed; `explainer-serve.py` entries 113–123, 11 of 11.

## What a check caught that the coordinator missed

`check-fixture-variation.py` refused `acknowledge_death(root=…)`, passed one value at every call site. A
second root (no pid file, so nothing to acknowledge) was added to the case.

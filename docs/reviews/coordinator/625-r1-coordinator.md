# Round 1 — `625` (backlog #625, the Ask answerer) — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: 625
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: watch-loop, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: spend-accounting, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: question-entry, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-lock, disposition: fixed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: watcher-lifecycle, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: watcher-lifecycle, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: post-guard, disposition: fixed}
  - {id: C5, severity: Medium, aim: deliverable, fix_induced: false, component: documents, disposition: fixed}
  - {id: C6, severity: Medium, aim: deliverable, fix_induced: false, component: documents, disposition: fixed}
  - {id: C7, severity: Low, aim: deliverable, fix_induced: false, component: caps, disposition: fixed}
  - {id: C9, severity: Low, aim: instrument, fix_induced: false, component: suite-guard, disposition: declined}
```

X1–X4 are Codex 1–4 and C1–C9 are Claude 1–9 in the table below. Claude 3 is X2 and Claude 8 is X3.

Both halves reviewed commit 953d5e6c concurrently. Both end NOT CONVERGED.

- Codex: `docs/reviews/codex/625-r1-codex.md` — 4 findings (3 HIGH, 1 MEDIUM). Loosening questions: none.
- Claude: `docs/reviews/claude/625-r1-claude.md` — 9 findings (1 HIGH, 5 MEDIUM, 3 LOW).

Two findings were raised by both halves (the killed run, the forged entry), so there are 11 distinct ones.
All 11 are answered in this fold: 9 in code with a case and a mutation, 2 in the documents.

## Disposition, per finding

| # | Finding | Severity | What the fold does | Case that goes red without it |
|---|---|---|---|---|
| Codex 1 | A question that arrives while another is being answered waits until the file changes again | HIGH | `watch` keeps the signature taken BEFORE the pass, so the next tick sees the difference | `r1: a question that arrives WHILE another is being answered…` |
| Codex 2 = Claude 3 | A killed run records 0 tokens, so the daily token cap never sees it | HIGH / MEDIUM | Output printed before the kill is parsed for its usage. A run that reported none is recorded `unmeasured` and counts as `UNMEASURED_RUN_TOKENS` (250,000, an assumption the spend line states). The same holds for a stop or a crash during a run | `r1: a killed run is never free…` |
| Codex 3 = Claude 8 | A reader's text holding `---`, a blank line and an entry header is read as a second question on another page | HIGH / LOW | `format_question_entry` (the one writer) rewrites a `---` line and holds the page name to one line | two cases in `explainer-serve.py`, `⛔ #625 r1: a reader's text cannot forge…` |
| Codex 4 | `--retry` and `--answered` judge a state, then append outside the lock | MEDIUM | Read, judge and append under one `ledger_lock` | none — see *Not tested* |
| Claude 1 | A NOT ANSWERED question is skipped by the next `--start`, the remedy the page names | HIGH | A start never skips a question the ledger has a line about; a start that finds the previous watcher's pid file skips nothing; a retried question shows NOT ANSWERED while the answerer is off; `--status` lists skipped questions and a session may `--claim` one | `r1: a start after an UNCLEAN end…`, `r1: a RETRIED question is never skipped…`, `r1: a skipped question is listed…` |
| Claude 2 | A crashed watcher deletes its pid file, so the page reads it as stopped on purpose | MEDIUM | The pid file is removed only on a clean return or a stop signal; a crash is logged as CRASHED and re-raised | `r1: a watcher that CRASHES leaves its pid file…` |
| Claude 4 | Any web page the owner has open can POST a question, and a question now costs a run | MEDIUM | `cross_site(origin, host)`: `do_POST` answers 403 when `Origin` or `Host` is not this machine, on both routes, before the body is read | `⛔ #625 r1: a POST from ANOTHER site is refused 403…` and two `cross_site` cases |
| Claude 5 | The answer block copies the question into tracked pages of a public repository | MEDIUM | No code change. §6 of the delivery document already makes the page's Q&A the artifact, for a session's answers too. The `.gitignore` comment and §6b now say that the block quotes the question and that a committed page is public | — (a document) |
| Claude 6 | The session's path (§5, §6) never meets the claim rule | MEDIUM | §5 and §6 of `explainer-delivery.md` now carry it | — (a document) |
| Claude 7 | A budget under $0.005 is sent to the CLI as `0.00` | LOW | `ASK_ANSWERER_BUDGET_USD` below 0.01 is refused | `r1: a per-question budget the CLI would be given as 0.00 is refused…` |
| Claude 9 | The suite's guard against the real `claude` does not reach the `--start` child process | LOW | Stated as a bound in the script's docstring. Not closed: the one case that starts a child passes `ASK_ANSWERER_CLAUDE`, and the closure the review suggests (a rule keyed on the temp folder's name) would be a second guard to maintain | — |

## Not tested, and why

Codex 4 has no case. The window is between two statements of one process, and a case could open it only by
replacing the lock or the reader with a double, which would test the double. The change is three lines
under an existing lock whose exclusion already has a case (`claim: two processes at once…`).

## One defect the fold itself found

The server sweep on 953d5e6c killed the mutation *the served page no longer carries its questions' state*
through a crash (`.index()` raised `ValueError`), which the harness does not attribute. The case now uses
`.find()` in one chained comparison, so it goes red by value.

## One defect the fold itself made, and closed

Leaving the pid file on any unclean end (Claude 2) made Ctrl-C on a foreground `--watch` read as a death:
`KeyboardInterrupt` is not an `Exception`, so nothing marked the exit clean, and the next start would have
skipped no baseline. SIGINT now raises the same `Stopped` as SIGTERM. Case: `r1: Ctrl-C is a stop on purpose…`.

## Bounds this fold adds

- `UNMEASURED_RUN_TOKENS` is an assumption (250,000), set above the two real runs measured for this row
  (31,687 and 39,902 tokens). It makes the token cap refuse sooner than the true spend would.
- `cross_site` lets through a client that sends neither header (curl, a local script). Such a client can
  append to `questions.md` directly.
- A start after an unclean end answers every question asked since the watcher died, up to the daily caps.

## Evidence

Self-tests: `ask_answerer.py` 118/118 (was 108), `explainer-serve.py` 288/288 (was 283). Mutation manifests:
`ask_answerer.json` 35 → 46, `explainer-serve.json` 116 → 120; four existing anchors moved with the fold and
were re-bound. The sweep results are in the round-2 document, which reviews the folded tree.

## One clerical edit to a filed review

The Claude half named its head in its text (`953d5e6c`) and not as the first line
`record-review-verdict.py` requires. The coordinator added that line (`Reviewed head: <full sha>`) and
changed nothing else in the file.

# Round 2 — `625` (backlog #625, the Ask answerer) — coordinator — NOT CONVERGED; all five folded

```yaml
round: 2
fixes_nontrivial: true
subject: 625
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: question-entry, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: spend-accounting, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: watcher-lifecycle, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: post-guard, disposition: fixed}
  - {id: X5, severity: Low, aim: instrument, fix_induced: false, component: post-guard, disposition: fixed}
```

REVIEW GAP: claude — alternation (owner 2026-10-28: rounds 2+ run ONE half).

Reviewed `118056fd` (the Codex half only, `docs/reviews/codex/625-r2-codex.md`, model gpt-6.1-sol). Codex numbers
the findings 1–5; they are X1–X5 here.

## Fix-induced? One of five

- **X3 is caused by the round-1 fold.** Round 1 (Claude 2) made a crash leave the pid file, and a start that finds
  one skips nothing. `--stop` was not taught about that file, so a stop typed after a crash changed nothing.
- X1, X2 and X4 are instances of a round-1 class that the round-1 fix missed: the forged entry through a carriage
  return, the unmeasured run that printed a result object, the cross-site POST from another port of this machine.
  None was created by the fold. Each round-1 case was satisfied by the one input its fixture supplied.
- X5 is a gap in a round-1 case, not a defect in the code.

Round 1 had no fix-induced finding, so thrashing (two consecutive rounds with fix-induced findings in one
component) is not armed. If round 3 finds a defect in `watcher-lifecycle` that this fold caused, it is.

## Disposition, per finding

| Id | Finding | Severity | What the fold does | Case that goes red without it |
|---|---|---|---|---|
| X1 | A reader's text using carriage returns still read as a second question on another page. The file's reader opens it in text mode, which turns `\r` into a line break after the `---` rewrite has run | HIGH | `format_question_entry` turns `\r\n` and `\r` into `\n` before anything else. The reader's words are otherwise unchanged | `⛔ #625 r2: nor with carriage returns, bare or paired…` — it writes the entry as bytes and reads it back the way `read_questions` does |
| X2 | A run that printed a result object with no `usage` was recorded as 0 tokens and measured. Three such timeouts gave `spent() == (3, 0)` | HIGH | `parse_result` marks every `Run` whose usage sums to zero `unmeasured`. An `answered` event records the flag too, and `unmeasured()` counts answered and failed events | `r2: a result that reports NO usage is unmeasured too…` — an answered run and a killed run, and four direct `parse_result` inputs, one of which reports usage and must stay measured |
| X3 | `--stop` after a crash printed `not running`, left the pid file, and the next start answered a question asked after that stop | MEDIUM | `stop` on a dead watcher removes the pid file, logs it and says the watcher had ended unexpectedly. The next start then records its baseline | `r2: a --stop after an unclean end is a stop on purpose…` |
| X4 | `Origin: http://localhost:8000` with `Host: 127.0.0.1:7391` passed, so a page served by another local site could post | MEDIUM | `cross_site` requires an `Origin` to name the `Host` it posts to, port included | `#625 r2 cross_site: ANOTHER local site is cross-site…` |
| X5 | The 403 case could not tell whether the refusal came before the body was parsed | LOW | A case posts a body that is not JSON: the foreign one must get 403 and the page's own 400 | `⛔ #625 r2: …and the refusal comes BEFORE the body…` |

## Bounds this fold adds or moves

- **X3 trades one bound for another.** After a crash and a `--stop`, questions asked between the crash and the
  stop are skipped by the next start. The page said NOT ANSWERED about them (the panel reads the dead watcher),
  `--status` lists them, and `--retry ID` hands one back. Without the `--stop` nothing changes from round 1.
- **X4 refuses a page opened under one spelling that posts to another** (`localhost:7391` to `127.0.0.1:7391`).
  The tray posts to a relative URL, so the page's own POST always names its own host. Codex's X4 is labelled
  inference in its review: no browser request was made. The refusal is on the header shape alone.
- **X2 counts a run that truly used zero tokens as 250,000.** No real run has reported zero.
- X1 changes a reader's bare `\r` to `\n` in the stored text. Nothing else in the text is changed.

## Round 1's sweep, owed by its document

On the folded tree `118056fd`, on a temp copy outside the repository: `ask_answerer.json` 46 of 46 killed and
attributed (45 in one run, the last entry alone in a second), `explainer-serve.json` entries 113–120 8 of 8.

## Evidence for this fold

Self-tests: `ask_answerer.py` 120/120 (was 118), `explainer-serve.py` 291/291 (was 288). Manifests:
`ask_answerer.json` 46 → 49, `explainer-serve.json` 120 → 123. On a temp copy of the folded tree, outside the
repository: 49 of 49 answerer mutations killed and attributed, and server entries 113–123 11 of 11.

`check-fixture-variation.py` then refused the new stop case: `stop(root)` was called with one root. The case now
also stops a root that never had a watcher, which must print plain `not running`. The stop mutation was swept
again alone after that change: killed and attributed.

The other local checks from `.github/workflows/ci.yml` pass, except `check-decision-scheme.py`, which says
`trigger 1 NOT FED: 625` until the decision-log row is written with the last round.

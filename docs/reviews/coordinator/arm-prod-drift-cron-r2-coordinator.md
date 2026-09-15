# Round 2 — `arm-prod-drift-cron` (PR #308) — coordinator

```yaml
round: 2
fixes_nontrivial: false
subject: arm-prod-drift-cron
halves:
  codex: ran
  claude: "GAP: round 1's Claude half reviewed this branch and returned no Blocking or High; round 2's subject is three sentences of prose it had itself proposed, so a second opinion on its own wording buys nothing a re-read does not. The Codex half checked each claim against GitHub's documentation and the code."
findings:
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: cron-comment, disposition: fixed}
```

REVIEW GAP: claude — round 1's Claude half reviewed this branch in full and returned no Blocking or High; round 2's subject is three sentences of prose that half proposed itself, so a second opinion on its own wording is not an independent check. The Codex half tested each sentence against GitHub's documentation and against `check-live-schema.py`, which is the check that mattered — and it found the overclaim.

## Verdict: CONVERGED on the code — one Low in the prose, fixed

**No new Blocking or High.** Round 2 existed because the tree-identity gate refused: round 1's
verdict was taken before its own three Low fixes landed, so no round had seen the file that ships.
That is the gate PR #299 built working exactly as designed.

## L1 — an overclaim in a gate comment → **FIXED**

The comment said the notification channel was *"undocumented"*. It is not: GitHub documents that
scheduled-workflow failures go to the user who last modified the cron syntax
(*Actions → events-that-trigger-workflows → schedule*).

⭐ **Worth more than its severity, because of where it sat.** An overclaim inside the comment that
justifies arming a nightly alarm is the thing this repository has been correcting all session — a
sentence asserting more than was checked, in the one place people go to find out what is true. It
came from round 1's own reviewer and I carried it in without verifying the word.

What survives the correction is narrower and real, and is kept: the recipient **transfers silently**
to whoever next edits the cron line, and a scheduled failure appears on **no pull request's check
list** — so nobody meets it while reviewing, which is the only moment anyone is reliably looking.

## What round 2 verified, rather than assumed

Each of round 1's three folded-in claims was checked against its source, not its wording:

| claim | checked against |
|---|---|
| public repos have scheduled workflows disabled after 60 days of inactivity | GitHub's documentation; repo confirmed `PUBLIC` |
| scheduled failures notify the last editor of the cron | GitHub's documentation — **this one refuted the wording** |
| `manifest <= live` has no accept-list in that direction | `check-live-schema.py`, read |

Also re-verified: the YAML parses, `schedule` remains a sibling of `workflow_dispatch` under `on:`,
the comments do not comment out a live key, the merge of master left `docs/dashboard-entries.md`
well-formed, and this branch's own entry has its `## YYYY-MM-DD` header — which had been dropped by a
conflict resolution and restored.

## Why the Claude half is a declared GAP rather than a run

Round 1's Claude half reviewed this branch in full and returned no Blocking or High. Round 2's
subject is three sentences of prose **it proposed itself**; a second opinion on its own wording is
not an independent check. The Codex half tested each sentence against the documentation and the
code, which is the check that mattered — and it found the overclaim. Recorded as a GAP with its
reason rather than omitted, per `docs/plugins.md`.

---
name: merge-ready-slice-merged-324
description: "FIRES-WHEN: about to open, check or merge a PR; about to call a branch ready — PR #324 MERGED (af4d9033) — check-merge-ready.py built, line budget warns before it blocks; 3 dual rounds, each found a silent-miss in the SAME parser"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3f96656-ed42-4afa-9402-df62a7de7d83
  modified: 2026-09-21T00:03:46.917Z
---

**MERGED 2026-09-20** — PR #324, squash `af4d9033`, branch `budget-slack-warning` deleted both sides.
`+1846 −18` across 19 files, 12 of them the three rounds' own review docs and verdicts.

## What shipped

- **`scripts/check-merge-ready.py`** (NEW, 724 lines) — runs every gate CI will run, *including the
  two pull-request-only steps* that a local run structurally cannot reach (dashboard-entry ratchet,
  `check-review-recorded`). It derives that PR-only list from `ci.yml` rather than hard-coding it,
  and a ratchet (`ACCOUNTED_MENTIONS`) refuses any unaccounted `pull_request` / `github.event_name`
  mention in any workflow. Verdict line is `READY` / not — **relay it verbatim, never paraphrase**.
- **`scripts/check-docs.py`** — the line budget now WARNS before it blocks. The PR subject is the
  lesson: *"the line budget reported ok at 100%, so the wall could only be found by hitting it."*
  A binary threshold gives no gradient; 99% and 10% printed the same word.

## ⭐ The shape worth remembering: three rounds, one parser, three silent misses

Every round's finding was in the **same component** — the thing that decides which workflow lines are
pull-request-only — and every one was a **silent miss**, not a crash:

| Round | Miss |
|---|---|
| r1 | file scope was hand-written inside a derivation that congratulated itself on being derived |
| r2 | the soundness check was **weaker than the parser it audited**, so it certified a parse it could not itself perform |
| r3 Codex | PR-only-ness can be expressed **by exclusion** (`!= 'schedule'`), so scanning for the word `pull_request` missed it |
| r3 Claude | the fix for r1 parsed every file but left the **`*.yml` pattern** hand-written — `.yaml` is a workflow too |

Note r3-Claude: **fixing the filename and leaving the file PATTERN is instance-not-class**, one level
down from r1's own finding. See [[after-fixing-search-for-the-class]] and
[[a-second-implementation-of-one-rule-drifts]] (r2 is a textbook stand-in-weaker-than-its-subject).

The fourth rewrite **refuses** rather than guessing. Two bounds are stated in comments rather than
mechanised, deliberately: an indirect gate (`startsWith(github.ref, 'refs/pull/')`, `github.head_ref`)
would escape — measured 2026-09-20, neither workflow contains one; and an allow-list *reason* can go
false without its key changing (delete `schema-gates.yml`'s `push` trigger and
`if: github.event_name != 'schedule'` silently becomes a PR-only gate). See
[[a-stated-bound-outlives-its-hole]].

## Gotcha that cost a tick

`scripts/begin-plan.py --tick` **refuses while `.claude/executing-plan` carries a `paused:` line** —
you must `--resume` first. Correct: the Stop guard stands down while paused, so allowing a tick there
would lose both protections to one un-modelled transition.

---

## ⟳ 2026-09-26 — I SKIPPED IT AND PUT TWO PRs RED, having built it for exactly that reason

**Measured.** PRs #351 and #352 both reached CI **red on the dashboard-entry ratchet**. Cause: I ran an
ad-hoc gate subset — `check-docs`, `check-backlog-closure`, `check-anchors` — and inferred readiness. The
script's own output is the rebuttal, printed back at me:

> *"A local gate sweep cannot answer the pull-request-only checks above. **That is why this script exists
> and why 'all my gates are green' is a different claim.**"*

⛔ **RULE, and it is not "run more gates" — it is run THE ONE:** before opening or merging any PR,
`python3 scripts/check-merge-ready.py --pr <N>`. A hand-picked subset cannot reach the PR-only steps
(`check-dashboard-entry`, `check-review-recorded`), because those read the **pull-request body and the
committed diff against the base**, not the working tree.

⚠ **TWO GATES, TWO ESCAPE TOKENS, AND I USED ONE FOR BOTH.** They are not interchangeable:

| gate | escape | means |
|---|---|---|
| `check-dashboard-entry` | **`NO-ENTRY: <reason>`** | this branch needs no dashboard entry |
| `check-review-recorded` | **`NO-REVIEW: <reason>`** | this branch needs no review round |

I wrote `NO-REVIEW:` in both PR bodies. `check-review-recorded` duly passed; the dashboard ratchet failed,
because nothing had answered *it*. ⭐ **And usually the right move is the entry, not the escape** — both of
those branches genuinely warranted one (a false claim withdrawn from `master`; a filed proposal with a
decision attached).

⛔ **AND THE GATE READS THE COMMITTED DIFF, so an uncommitted entry looks like no entry** — `rc=0` on a
branch with **no commits yet** is vacuous, not a pass. Commit, then run it. ⚠ Its own message adds the
other half: *editing the PR body alone will not clear it — CI reads the body from the frozen event
payload, so you must then push something.*

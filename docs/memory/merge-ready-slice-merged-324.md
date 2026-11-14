---
name: merge-ready-slice-merged-324
description: "FIRES-WHEN: about to open, check or merge a PR; about to call a branch ready — run check-merge-ready.py --pr N, never a gate subset; NO-ENTRY vs NO-REVIEW are different escapes. PR #324 (af4d9033) built it; 3 rounds each found a silent miss in the SAME parser"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3f96656-ed42-4afa-9402-df62a7de7d83
  modified: 2026-09-21T00:03:46.917Z
---

## The rule (current)

⛔ **Before opening or merging any PR: `python3 scripts/check-merge-ready.py --pr <N>` — THE ONE, not "more gates".**
A hand-picked local subset cannot reach the PR-only steps (`check-dashboard-entry`, `check-review-recorded`), which
read the PR body and the committed diff against the base. Relay its verdict line (`READY` / not) verbatim.

- **Two gates, two escape tokens — not interchangeable:**

  | gate | escape | means |
  |---|---|---|
  | `check-dashboard-entry` | `NO-ENTRY: <reason>` | this branch needs no dashboard entry |
  | `check-review-recorded` | `NO-REVIEW: <reason>` | this branch needs no review round |

  ⭐ Usually the right move is the entry, not the escape.
- **It reads the COMMITTED diff:** an uncommitted entry looks like no entry, and `rc=0` on a branch with no commits is
  vacuous. Commit, then run it. Editing the PR body alone will not clear it — CI reads the body from the frozen event
  payload, so push something after.
- `scripts/begin-plan.py --tick` refuses while `.claude/executing-plan` carries a `paused:` line — `--resume` first.

**Why:** 2026-09-26, PRs #351 and #352 both reached CI red on the dashboard-entry ratchet: I ran `check-docs`,
`check-backlog-closure`, `check-anchors` and inferred readiness, and wrote `NO-REVIEW:` in both bodies where the
dashboard gate needed an entry. The script's own output: *"A local gate sweep cannot answer the pull-request-only
checks above. That is why this script exists and why 'all my gates are green' is a different claim."*

## History — PR #324, MERGED 2026-09-20 (squash `af4d9033`)

`+1846 −18` across 19 files. Shipped `scripts/check-merge-ready.py` (derives the PR-only list from `ci.yml`; a
ratchet, `ACCOUNTED_MENTIONS`, refuses an unaccounted `pull_request` / `github.event_name` mention) and made
`check-docs.py`'s line budget WARN before it blocks — *"the line budget reported ok at 100%, so the wall could only be
found by hitting it."*

⭐ **Three rounds, one parser, all silent misses:**

| Round | Miss |
|---|---|
| r1 | file scope hand-written inside a derivation that congratulated itself on being derived |
| r2 | the soundness check was weaker than the parser it audited |
| r3 Codex | PR-only-ness expressed by exclusion (`!= 'schedule'`) escaped a scan for `pull_request` |
| r3 Claude | the r1 fix left the `*.yml` pattern hand-written — `.yaml` is a workflow too |

Fixing the filename and leaving the PATTERN is instance-not-class ([[after-fixing-search-for-the-class]],
[[a-second-implementation-of-one-rule-drifts]]). The fourth rewrite refuses rather than guesses. Two bounds stated in
comments, not mechanised: an indirect gate (`startsWith(github.ref, 'refs/pull/')`, `github.head_ref`) would escape —
neither workflow had one on 2026-09-20; and an allow-list reason can go false without its key changing
([[a-stated-bound-outlives-its-hole]]).

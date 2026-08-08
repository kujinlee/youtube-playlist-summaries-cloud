# Development Process

Gate-based workflow. This file is the **spine**: what must be true, in what order, and who decides.
It lives in the project repo so the process is reproducible by anyone who clones it.

**It is deliberately short, and there is a budget** — see *Keeping this file short* at the end.
Detail lives in four places, each with a different read-trigger:

| File | Read when |
|---|---|
| [`docs/process-checklists.md`](process-checklists.md) | you are working a gate — per-task list, post-plan gate, TDD policy, spec contents |
| [`docs/review-method.md`](review-method.md) | a review round is starting — adversarial review, convergence, the classification passes |
| [`docs/process-rationale.md`](process-rationale.md) | a rule here looks arbitrary, expensive or wrong |
| [`docs/plugins.md`](plugins.md) | choosing a skill, or a tool gate misbehaves |

---

## Human-in-the-Loop Policy — Conditional AFK

The **spec is the human gate.** Design, terminology, and goal decisions are settled *with* the human
in Phase 1. Once `docs/design-spec.md` is approved the goal is fixed, and **plan (Phase 2) and
implementation (Phase 3) proceed autonomously** — dual adversarial review to convergence is the
quality gate, not a human sign-off. At convergence the coordinator *notifies* and continues.

Pull the human back in only for an **unexpected situation**:

- a genuine ambiguity or fork the spec did not settle (a real decision, not a mechanical choice);
- an adversarial-review round that **cannot converge**. This collides with *Iterative Re-Review*,
  which says keep going. The rule is **notify and continue**. Stop and wait only if (a) the human
  replies, (b) the next action is outward-facing or irreversible, or (c) the fix is not clearly
  specified — i.e. you would be guessing at intent. Continuing while a notification is outstanding is
  correct; going silent is not;
- a **blocker**: missing access/credentials, an external dependency down, a gate that will not go green;
- anything that would **move the goal** (change the spec) rather than approach it;
- an **outward-facing or hard-to-reverse action** — push, merge, deploy, delete, spend.

**Notification is mandatory whenever you actually need the human** (`PushNotification` — one line,
lead with the decision needed). Silently "waiting" without notifying wastes their time. Do **not**
notify for routine progress, or for anything you can decide yourself.

---

## Session Resume

Verify progress from ground truth before acting — never from a context summary, which is a
compressed snapshot and can be stale after `/compact`:

1. `git log --oneline` — which tasks are committed
2. `ls tests/lib/ docs/reviews/` — what work exists on disk
3. Cross-reference `docs/implementation-plan.md` — find the first uncommitted task

---

## Roadmap & Task List — Always Maintained

There is **always** a current answer to "what's left, and what's next", kept in three layers that
must stay in sync — updated proactively, without being asked.

| Layer | File / tool | Horizon |
|---|---|---|
| **Roadmap** | `docs/roadmap-to-launch.md` | whole project; survives compaction |
| **Task list** | `TaskCreate`/`TaskUpdate` | current milestone |
| **SDD ledger** | `.superpowers/sdd/progress.md` | current slice |

- A roadmap step is not done until its checkbox is ticked **and** its task entry is `completed`.
- A **discovered** step (a review finding that becomes work, a blocker, a follow-up) goes into the
  roadmap **and** the task list in the same turn — a discovery living only in chat is lost at `/compact`.
- At a **milestone boundary**: update the roadmap status line, tick the step, close the task, record
  the outcome in memory.
- **At session start, reconcile all three against git.** The checkboxes are a claim; `git` is the truth.
- The roadmap is the compaction-proof source; the task list can be rebuilt from it. If none exists for
  a multi-milestone effort, **create one before starting work**.

---

## Phases

| # | Phase | Artifact | Gate |
|---|---|---|---|
| 0 | Setup | `git init`, `docs/` | — |
| 1 | **Brainstorming** | `docs/design-spec.md` | grill-with-docs + adversarial review + **user approval**. Spec contents: checklists doc |
| 2 | **Writing Plans** | `docs/implementation-plan.md` | dual adversarial review **to convergence**; then notify and proceed. Post-Plan Gate: checklists doc |
| 3 | **Implementation** | code + tests | per-task two-stage review to convergence, autonomous. Per-Task Checklist: checklists doc |
| 4 | **Verification** | evidence | enumerate every UX case as a task list *before* clicking anything; screenshots to `.screenshots/` (gitignored) |
| 5 | **Final Review + Finish** | PR | full review → commit → push → PR. **Merging is a human gate** |
| 6 | **Architecture Review** | `docs/reviews/architecture-review-<date>.md` | per **milestone**, not per task |

**Phase 3 execution default (set 2026-06-09):** `superpowers:subagent-driven-development` — a fresh
subagent per task. Proceed automatically; do not ask the user to choose each time.

**Phase 5 — branch + PR is the standard path (set 2026-07-30). The axis is blast radius, not size.**
A one-line change can be the most dangerous thing in the repo.

| Change | Path |
|---|---|
| `lib/` `app/` `components/` `worker/` `supabase/` `scripts/` `tests/`, or any config | **Branch + PR, always.** No size exemption |
| Docs | Branch + PR, **batched** |
| Repo has no remote (a PR is impossible) | Direct commit |

- **Batch to kill the friction — the fix is fewer PRs, not more direct pushes.** Roadmap/backlog
  status ticks ride in the **same PR** as the work they describe. Standalone doc edits accumulate.
- **Write the merge tick BEFORE opening the PR**, and do not chase the squash SHA — the PR number
  exists as soon as the PR does.
- Merging stays a **human gate**: open the PR, notify, do not merge.

**Phase 6 — why it is per-milestone:** per-task review is structurally blind to composition defects.
It only ever sees one change, and every change can be individually correct while the structure they
add up to degrades. Read `CONTEXT.md` + `docs/adr/` first; ADRs must not be re-litigated. Agent output
is a **lead, not a finding** — verify every load-bearing claim by hand. Findings that become work go to
`docs/backlog.md` **and** the roadmap in the same turn. Also ask: *"what did we decide this milestone
that isn't written down?"* — the one failure no tool can see.

---

## What is mechanically enforced

**The script is the truth. These lines are pointers, not restatements** — a restatement is a second
copy that drifts.

| Check | Enforces |
|---|---|
| `.claude/hooks/block-default-branch-push.sh` | no push to the default branch (escape: `ALLOW_DEFAULT_BRANCH_PUSH=1`) |
| `.claude/hooks/check-plan-gate.sh` | the Post-Plan Gate before dispatching subagents |
| `.claude/hooks/check-schema-gates.sh` | after editing schema, the gates must run before reporting done |
| `scripts/check-schema-gates.sh` | **one command for all four schema gates** — run this, not the pieces |
| `scripts/check-guard-coverage.py` | every guard classified SHAPE/SEQUENCE; every SEQUENCE guard reconciles and is mutated |
| `scripts/check-docs.py` | documentation integrity |
| `scripts/check-arch-findings.py` | ratchet on architecture-review findings |
| `.github/workflows/ci.yml` | `tsc --noEmit`, unit suite, `service_role` confinement, on Node 22 |

**Not yet in CI:** `test:integration` and `test:e2e` (need a live Supabase stack), and the schema
gates (need a live Postgres — wiring them in belongs to the promotion slice). Run these locally
before asking for a merge.

**Anything longer than a line goes in a FILE, never a shell argument** — `--body-file`,
`git commit -F`, `--prompt-file`. Any backtick inside a double-quoted bash string is command
substitution, and it has silently skipped a review gate. *(Physical, not a preference.)*

---

## Tools

| Tool | Phase |
|---|---|
| `superpowers:brainstorming` | 1 |
| `mattpocock:grill-with-docs` | 1 |
| `codex:rescue` | 1, 2 (docs), 3 (code) |
| `superpowers:writing-plans` | 2 |
| `superpowers:test-driven-development` | 3 |
| `superpowers:requesting-code-review` | 3 |
| `TaskCreate` / `TaskUpdate` | 3 |
| `superpowers:verification-before-completion` | 4 |
| `superpowers:finishing-a-development-branch` | 5 |
| `improve-codebase-architecture` | 6 |

---

## Project-Specific

**Sub-projects.** 1 — Backend (types, lib, API routes, pipelines). 2 — Frontend (React, SSE, Obsidian
URI, PDF viewer). *(⚠ flagged: the original "2 does not begin until 1 is fully verified and merged"
now looks obsolete — see Rules flagged for review.)*

**Mocking boundaries.** `lib/gemini.ts` — all Gemini calls. `lib/youtube.ts` — YouTube Data API +
transcript fetching. E2E mocks at the **API route** level, not the lib boundary.

---

## Keeping this file short

This document reached **576 lines**, of which ~28% was added in two days. Every addition was justified
by a measured defect; the aggregate was unreadable — the *"individually thoughtful, fail as a set"*
verdict these reviews keep producing, applied to their own documentation. An unread rule is worse than
no rule, because it creates a belief that something is covered.

> **Before adding a rule here, ask whether it can be a script.** If it can, write the script and add a
> pointer row above. If it cannot, it belongs in the checklists, method, or rationale doc — not the
> spine. **`scripts/check-docs.py` enforces the line budget.**

### Rules flagged for review, not retired

Surfaced by running this project's own **P / I / H** classification (see `review-method.md`) on the
process itself. Flagged rather than removed — retiring a rule is the user's call.

| Rule | Why flagged |
|---|---|
| Sub-project 2 waits for 1 to be "fully verified and merged" | The frontend shipped; both now proceed in parallel. Looks superseded by events |
| `gh` two-remotes footgun | Marked **RESOLVED 2026-08-04** — the remote was removed. Now history occupying spine space; the story belongs in rationale |
| `subagent-driven-development` as the execution default | Set 2026-06-09, never re-examined; this session ran largely inline |
| "Currently known-red: none" | That is **state**, not policy. Belongs in the roadmap's dev-infrastructure debt section |

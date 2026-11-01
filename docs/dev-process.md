# Development Process

Gate-based workflow. This file is the **spine**: what must be true, in what order, and who decides.
It lives in the project repo so the process is reproducible by anyone who clones it.

**It is deliberately short, and there is a budget** — see *Keeping this file short* at the end.
Detail lives in four places, each with a different read-trigger:

| File | Read when |
|---|---|
| [`docs/process-checklists.md`](process-checklists.md) | you are working a gate — per-task list, post-plan gate, TDD policy, spec contents, **qualifying numbers in prose**, **the six round-cost rules** |
| [`docs/review-method.md`](review-method.md) | a review round is starting — adversarial review, convergence, the classification passes |
| [`docs/process-rationale.md`](process-rationale.md) | a rule here looks arbitrary, expensive or wrong |
| [`docs/plugins.md`](plugins.md) | choosing a skill, or a tool gate misbehaves |
| [`docs/portable-practices.md`](portable-practices.md) | **starting a NEW project** — the measured, project-independent subset of everything here |

---

## Human-in-the-Loop Policy — Conditional AFK

The **spec is the human gate.** Design, terminology, and goal decisions are settled *with* the human
in Phase 1. Once `docs/design-spec.md` is approved the goal is fixed, and **plan (Phase 2) and
implementation (Phase 3) proceed autonomously** — dual adversarial review to convergence, bounded by
the round cap ([`review-method.md`](review-method.md) §0 Q4c), is the quality gate, not a human sign-off. At convergence the coordinator *notifies* and continues.

Pull the human back in only for an **unexpected situation**:

- a genuine ambiguity or fork the spec did not settle (a real decision, not a mechanical choice);
- an adversarial-review round that **cannot converge** — ⟳ 2026-10-31 the **round cap** governs: from r4 findings are
  FILED unless a BLOCKER ([`review-method.md`](review-method.md) §0 Q4c). **Notify and continue**; wait only if (a) the human
  replies, (b) the next action is outward-facing or irreversible, or (c) the fix is not clearly
  specified — i.e. you would be guessing at intent. Continuing while a notification is outstanding is
  correct; going silent is not;
- a **blocker**: missing access/credentials, an external dependency down, a gate that will not go green;
- anything that would **move the goal** (change the spec) rather than approach it;
- an **outward-facing or hard-to-reverse action** — deploy, delete, spend, and a merge the house
  rule HOLDS. ⟳ **2026-10-25, the owner: MERGE WHEN READY** — `check-merge-ready.py --pr N` (run
  from the PR's worktree) READY ⇒ squash, `--match-head-commit` pinned; **exit 3 HOLD** (loosens a
  gate, needs a deploy, `NO-REVIEW:`, or app code without local tests) ⇒ do NOT merge, notify.
  ⟳ 2026-09-30: `push` REMOVED; a PR is still not opened for NOT CONVERGED work —
  [`process-rationale.md`](process-rationale.md) → *The rule that asked for permission a hook already enforced*.

**Notification is mandatory whenever you actually need the human** (`PushNotification` — one line,
lead with the decision needed). Silently "waiting" without notifying wastes their time. Do **not**
notify for routine progress, or for anything you can decide yourself.

---

## Session Resume

Verify from ground truth before acting, never a context summary — it can go stale after `/compact`:

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
  ⤳ If you are about to WORK it now rather than file it, it is a **side job** and gets a name first
  (slug + branch) — sized, switched and announced per the checklists doc; `unheralded` is its guard.
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
| 2 | **Writing Plans** | `docs/implementation-plan.md` | dual adversarial review **to convergence or the round cap**; then notify and proceed. Post-Plan Gate: checklists doc |
| 3 | **Implementation** | code + tests | per-task two-stage review to convergence or the round cap, autonomous. Per-Task Checklist: checklists doc |
| 4 | **Verification** | evidence | enumerate every UX case as a task list *before* clicking anything; screenshots to `.screenshots/` (gitignored) |
| 5 | **Final Review + Finish** | PR | full review → commit → push → PR → **merge when READY; a HOLD goes to the human** |
| 6 | **Architecture Review** | `docs/reviews/architecture-review-<date>.md` | per **milestone** — **or on THRASHING: two consecutive rounds whose findings came from the previous round's fix** |

**Phase 3 execution default (set 2026-06-09):** `superpowers:subagent-driven-development` — a NEW subagent per
task, fold and review round, never a reused or parked one (⟳ 2026-10-30, measured: [checklists](process-checklists.md) → *Agent lifetime*). Proceed; do not ask. Exception: *Who writes a review fold*.

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
- **Merge when READY** (house rule, 2026-10-25, above); a **HOLD** is the human's — do not merge, notify.

**⟳ THE ARMING CONDITION IS THRASHING, NOT A COUNT.** Phase 6 fires when **two consecutive rounds
carry findings caused by the previous round's own fix, in one component** — never on a round count.
⚠ **Reaching four rounds OBLIGES ASKING, and does not fire** — and is the round cap (§0 Q4c): answer *thrashing or prose floor?* in the
round document, with per-finding evidence. The component a convened review examines is ranked by TOTAL
appearances (`check-review-decision.py:review_scope`), a ranker, never a trigger. Full account, both
shapes, *can a redesign remove it?* and the stop condition: [`review-method.md`](review-method.md) →
*The arming condition — full account*.

**The architecture review — why it is per-milestone:** per-task review is structurally blind to composition defects.
It only ever sees one change, and every change can be individually correct while the structure they
add up to degrades. Read `CONTEXT.md` + `docs/adr/` first; ADRs must not be re-litigated. Agent output
is a **lead, not a finding** — verify every load-bearing claim by hand. Findings that become work go to
`docs/backlog.md` **and** the roadmap in the same turn. Also ask: *"what did we decide this milestone
that isn't written down?"* — the one failure no tool can see.

---

## What is mechanically enforced

**The script is the truth. These lines are pointers, not restatements** — a restatement is a second
copy that drifts. One line per row; each row's measurements and history are in
[`process-checklists.md`](process-checklists.md) → *Mechanically enforced checks — the full rows*.

| Check | Enforces |
|---|---|
| `.claude/hooks/block-default-branch-push.sh` | no push to the default branch (`ALLOW_DEFAULT_BRANCH_PUSH=1`); no bare `--force`/`-f` or `--no-verify` anywhere (`ALLOW_DANGEROUS_PUSH=1`; `--force-with-lease` allowed); an agent push mentioning `hookspath`/`ALLOW_PLAN_LEAK` refused. Plan leaks: `.githooks/pre-push` → `scripts/check-plan-leak.py` |
| `.claude/hooks/enforce-selection-card.sh` + `scripts/check-selection-card.py` | an option list follows `portable-practices` §19 — SHAPE only, it cannot see two options that are the same work |
| `.claude/hooks/check-plan-gate.sh` | the Post-Plan Gate before dispatching subagents |
| `.claude/hooks/regen-goals-page.sh` | the goals view is rebuilt from its sources, never hand-edited (`/goals`; ADR-0010) |
| `.claude/hooks/check-schema-gates.sh` | after editing schema, the gates must run before reporting done |
| `.claude/hooks/enforce-handoff-path.sh` + `scripts/check-handoff-path.py` | a session handoff is written where the SessionStart hook reads it |
| `scripts/check-schema-gates.sh` | **one command for all the schema gates** — run this, not the pieces |
| `scripts/check-guard-coverage.py` | every guard classified SHAPE/SEQUENCE; every SEQUENCE guard reconciles and is mutated |
| `scripts/check-sentinel-meanings.py` | every nullable column means exactly ONE thing |
| `scripts/check-vocabulary-collisions.py` | one mechanism per concern — duplicate coordination vocabulary shadows a duplicate protocol |
| `scripts/check-producer-enumeration.py` | every guarded value's producer count matches its defining expression |
| `scripts/check-ratchet-contract.py` | every guard on disk has a `--self-test`, no fail-open handler, and a caller or a `NO-CALLER:` reason |
| `scripts/check-paid-caller-arrival.py` | fires when a non-test caller reaches `record_artifact` (backlog 26's trigger) |
| `scripts/check-function-revokes.py` | every new `public` function revokes PUBLIC in its own migration |
| `scripts/check-python-pin.py` | every CI job pins Python, the pins agree, and in CI the pin took effect |
| `scripts/check-docs.py` | documentation integrity, including this file's line budget |
| `scripts/check-memory-index-budget.py` | the always-loaded memory index fits the harness's injection budget (characters) |
| `scripts/check-backlog-closure.py` | warns when a merged subject closes a backlog row that lacks `✅` (warn-only) |
| `scripts/check-review-rounds.py` | a review round has BOTH halves, or a written `REVIEW GAP:` reason |
| `scripts/check-anchors.py` | every living spec/plan declares the GOAL it belongs to (ADR-0010; `docs/anchors.md`) |
| `scripts/check-explainer-delivery.py` | the explainer delivery loop is described in ONE place; skills cite it |
| `scripts/check-test-counts.py` | the roadmap's stated test counts equal the suite's actual counts |
| `scripts/check-arch-findings.py` | ratchet on architecture-review findings |
| `scripts/check-dashboard-entry.py` | a branch that changes tracked files records a dashboard entry, or declares `NO-ENTRY: <reason>` |
| `scripts/gen-dashboard.py` | the dashboard page is derived, never hand-edited |
| `scripts/check-plan-code.py` | `--mutate .`: every mutation in `scripts/mutations/*.json` goes red via the case it names. FULL sweep is CI's; locally PARTIAL (`--only <script>`) — open a DRAFT PR at slice start |
| `scripts/check-plan-file-tags.py` | no document under `docs/` embeds code through a retired plan-mode tag |
| `.github/workflows/ci.yml` | `tsc --noEmit`, unit suite, `service_role` confinement, on Node 22 |
| `.github/workflows/schema-gates.yml` | the schema gates in CI on every PR (no path filter, so it can be required); `prod-drift` is the scheduled gate |

**Not yet in CI:** `test:integration` and `test:e2e` (need a live Supabase stack); run them locally
before a merge. ⟳ 2026-09-13 the schema gates LEFT this list — CI builds their Postgres in 14s.

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
URI, PDF viewer). They proceed **in parallel** — the original "2 does not begin until 1 is fully
verified and merged" was retired 2026-09-20, superseded by events (the frontend shipped).

**Mocking boundaries.** `lib/gemini.ts` — all Gemini calls. `lib/youtube.ts` — YouTube Data API +
transcript fetching. E2E mocks at the **API route** level, not the lib boundary.

---

## Keeping this file short

Why this file is budgeted, and what it once grew to: [`process-rationale.md`](process-rationale.md) → *Why the spine is short — history
moved out of the always-loaded files*.

> **Before adding a rule here, ask whether it can be a script.** If it can, write the script and add a
> pointer row above. If it cannot, it belongs in the checklists, method, or rationale doc — not the
> spine. **`scripts/check-docs.py` enforces the line budget.**

`check-docs.py` WARNS before a budget blocks.

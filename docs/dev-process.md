# Development Process

Gate-based workflow. This file is the canonical source for the workflow. It lives in the project repo so the process is reproducible by anyone who clones it.

---

## Human-in-the-Loop Policy — Conditional AFK

The **spec is the human gate.** Design, terminology, and goal decisions are settled *with* the human in Phase 1. Once `docs/design-spec.md` is approved the goal is fixed, and **plan (Phase 2) and implementation (Phase 3) proceed autonomously** — dual adversarial review to convergence is the quality gate, not a human sign-off. At convergence the coordinator *notifies* the human and continues; it does not sit and wait for an ack.

Pull the human back in only for an **unexpected situation** — something the automated loop cannot resolve on its own:
- a genuine ambiguity or fork the spec did not settle (a real decision, not a mechanical choice with an obvious default);
- an adversarial-review round that **cannot reach convergence** — a Blocking/High that resists fixing, or fixes that keep surfacing new Blocking/High. **Resolution of the apparent conflict with "Iterative Re-Review" (added 2026-07-18):** that section says to *keep going* on a new Blocking/High; this section says to *pull the human in*. Both fire at the same trigger, so the rule is: **notify and continue.** Stop and wait only if (a) the human replies, (b) the next action is outward-facing or irreversible, or (c) the fix is not clearly specified — i.e. you would be guessing at intent. Continuing while a notification is outstanding is correct; going silent is not;
- a **blocker**: missing access/credentials, an external dependency down, a gate that will not go green;
- anything that would **move the goal** (change the spec) rather than approach it;
- an **outward-facing or hard-to-reverse action** — push, merge, deploy, delete, spend. These stay human gates regardless (see Phase 5).

If none of those apply, keep going. Routine gates (plan approval, per-task review) do **not** require a human stop — carrying the work forward through trial-and-error toward a fixed goal is the point; a human ack there rarely changes the outcome and costs a round-trip.

**Notification is mandatory whenever you actually need the human.** When an unexpected situation above arises, or a long autonomous run has completed and only a human gate (e.g. merge) remains, send a phone notification (`PushNotification` — one line, lead with the decision needed). Silently "waiting" without notifying wastes the human's time: they cannot act on a request they never saw. Do **not** notify for routine progress or for something you can decide yourself.

---

## Session Resume

At session start, verify progress from ground-truth sources before acting:
1. `git log --oneline` — which tasks are committed
2. `ls tests/lib/ docs/reviews/` — what work exists on disk
3. Cross-reference `docs/implementation-plan.md` — find first uncommitted task

Never rely on context summary alone — it is a compressed snapshot and can be stale after `/compact`.

---

## Roadmap & Task List — Always Maintained

There is **always** a current, coherent answer to "what's left to the goal, and what's next" — kept in three layers that must stay in sync. This holds whether work is proceeding autonomously (AFK) or through chat; the roadmap is updated **proactively, without being asked**.

| Layer | File / tool | Scope | Horizon |
|---|---|---|---|
| **Roadmap** | `docs/roadmap-to-launch.md` | Milestones → steps to the **final goal** (the running app), with gating deps + status checkboxes | Whole project; survives compaction |
| **Task list** | `TaskCreate`/`TaskUpdate` | The live, actionable near-term steps (one per roadmap step in flight) | Current milestone |
| **SDD ledger** | `.superpowers/sdd/progress.md` | Per-task execution record **within** a single slice | Current slice |

**Coherence rules:**
- A roadmap step is not done until its checkbox is ticked **and** its task list entry is `completed`. Never mark one without the other.
- When you **discover** a new step (a review finding that becomes work, a blocker, a follow-up), add it to the roadmap **and** the task list in the same turn — a discovery that lives only in chat is lost at the next `/compact`.
- At a **milestone/slice boundary** (merge, convergence, deploy): update the roadmap status line, tick the step, close the task, and record the outcome in memory.
- **Session start (extends Session Resume):** reconcile all three against git ground truth (`git log`, merged PRs, files on disk) before acting — the roadmap's checkboxes are a claim, `git` is the truth. If they disagree, fix the roadmap.
- The roadmap is the **compaction-proof source**; the task list can always be rebuilt from it. If no roadmap exists for a multi-milestone effort, **create one before starting work** (like the Post-Plan Gate for plans).

**When to (re)build the roadmap:** any time the work spans more than one slice/merge to reach the goal, or the user asks "what's next / what's left." A single self-contained slice does not need its own roadmap — the SDD ledger suffices.

---

## Reference Docs (Read On Demand)

These files are not @-included — read them when the trigger condition is met.

| Doc | Read when |
|---|---|
| `docs/roadmap-to-launch.md` | "What's left / what's next" to the final app; session start (reconcile vs git); any milestone/step boundary — keep it current (see Roadmap & Task List) |
| `docs/implementation-plan.md` | Session resume (find next uncommitted task); start of each task |
| `docs/design-spec.md` | Phase 4 verification checklist; any spec ambiguity during implementation |
| `docs/process-rationale.md` | A rule here looks arbitrary, expensive or wrong; you are about to skip or "simplify" one; a review finding resembles something the process claims to prevent |
| `docs/available-skills.md` | Unsure which skill to use or how to invoke it; after installing or updating plugins. Say **"sync docs"** or run `/sync-docs` (`sync-docs` skill) to regenerate. |

---

## Phases

0. **Project Setup** (before Phase 1)
   - `git init` + initial commit
   - Create `docs/` folder

1. **Brainstorming** → `docs/design-spec.md`
   - Dialogue → spec → `grill-with-docs` (terminology + CONTEXT.md) → Codex adversarial review
   - Gate: grill-with-docs + adversarial review + user approval — for big/critical specs, **iterate the review to convergence** (see Adversarial Review → Iterative Re-Review)
   - **For projects with a frontend:** brainstorming includes wireframe + design tokens. `docs/design-spec.md` must contain a `## UI Design` section (ASCII wireframe, token table, badge/component specs) before any Tailwind or styling code is written. The gate is unchanged — user approves the full spec, which now includes the UI section.
   - **For projects that write files:** `docs/design-spec.md` must contain a `## Output File Format` section with: filename convention (with example), required frontmatter/header fields, and an annotated sample file body. No pipeline or file-writing task begins until this section is approved.
   - **For projects with a list/table UI:** `docs/design-spec.md` must enumerate every sort, filter, and grouping operation the user needs — column, direction semantics, and what undefined/missing values do. Discovering missing operations after implementation counts as a spec gap.
   - **For any UI component that triggers an async operation (fetch, ingest, AI generation):** The spec must answer before any component task begins: (1) Blocking or non-blocking? (overlay vs. status bar vs. inline indicator) — default to non-blocking unless the user cannot do anything useful during the operation. (2) What does the user need to see/do while the operation runs? (3) What triggers dismissal? A full-screen blocking overlay requires explicit justification in the spec; "simpler to build" is not justification. Use the brainstorming Visual Companion to show a non-blocking alternative before deciding.
   - **For tasks that include UI components generating URLs or containing modals/overlays:** `docs/design-spec.md` must contain a `## URL Contracts` table (`Component | Link text | Full URL with all params`) — one row per distinct link — and a `## Overlay Dismissal` table (`Component | Mechanism | Expected result`) — one row per dismissal path. Gate: user approves both tables before any component task begins.

2. **Writing Plans** → `docs/implementation-plan.md`
   - Dual adversarial review (Codex + Claude, independent)
   - Gate (Conditional AFK): **dual adversarial review to convergence** (see Adversarial Review → Iterative Re-Review) *is* the gate. On convergence — a full re-review round with no new Blocking/High — **notify the human and proceed** to implementation without waiting. Stop for the human only on non-convergence or a goal-affecting ambiguity (per Human-in-the-Loop Policy).
   - **Required:** immediately after saving the plan, create a Post-Plan Gate checklist (see below) — do not dispatch any implementation subagent until the gate is satisfied (convergence, or human decision when one was needed)

3. **Implementation** (per task)
   - **Execution method default (set 2026-06-09):** use **`superpowers:subagent-driven-development`** — a fresh subagent per task with two-stage review between tasks. Proceed with this method automatically; do **not** ask the user to choose between subagent-driven and inline execution each time. (Under Conditional AFK the plan gate is satisfied by convergence; this default governs only *how* the plan is executed.)
   - Per-task two-stage review to convergence is autonomous. Surface a task to the human only on an unexpected situation (Human-in-the-Loop Policy): a blocker, a genuine ambiguity, or a plan/spec contradiction the review loop cannot resolve.
   - At task start: create a TaskCreate checklist (see Per-Task Checklist below) — do not write any code until the list exists
   - Write failing tests → implement → Claude code review → Codex adversarial review → address → mark done
   - Save each review to `docs/reviews/task-N-<name>-review.md` (Claude) and `docs/reviews/task-N-<name>-codex.md` (Codex)
   - TDD: tests written before implementation; must be failing first

4. **Verification**
   - Before clicking anything: enumerate ALL UX test cases as a `TaskCreate` list — one task per scenario (happy path, each error state, each dismissal path, each disabled state). No ad-hoc clicking before the list exists.
   - Work through the list in order; mark each `completed` with `TaskUpdate` immediately after verifying it. Do not batch.
   - Run actual app; step through `docs/design-spec.md` checklist with evidence
   - Tool: `verification-before-completion`
   - **Screenshots:** always save to `.screenshots/<name>.png` — never to the project root. The `.screenshots/` folder is gitignored; delete its contents after verification is complete.

5. **Final Review + Finish**
   - Full code review → commit → push → PR
   - Tool: `finishing-a-development-branch`

---

## Tools

| Tool | Phase |
|---|---|
| `superpowers:brainstorming` | 1 — design dialogue |
| `mattpocock:grill-with-docs` | 1 — terminology stress-test → CONTEXT.md |
| `codex:rescue` | 1, 2 — doc adversarial review; 3 — code adversarial review |
| `superpowers:writing-plans` | 2 — task breakdown |
| `superpowers:test-driven-development` | 3 — TDD (behaviors specified upfront) |
| `superpowers:requesting-code-review` | 3 — Claude code review |
| `TaskCreate` / `TaskUpdate` | 3 — per-task checklist (create at task start, mark each step done) |
| `superpowers:verification-before-completion` | 4 — evidence collection |
| `superpowers:finishing-a-development-branch` | 5 — commit + PR |

---

## Post-Plan Gate Checklist

Immediately after saving the plan document, create these items with `TaskCreate`. Do not dispatch any implementation subagent until the gate is satisfied.

```
[ ] Run the dual adversarial review of the plan (Codex + Claude, independent)
[ ] Save each round to docs/reviews/plan-<feature>-*.md; iterate to convergence
[ ] Address all Blocking/High; record Medium/Low dispositions in the review doc
[ ] Convergence reached — a full re-review round with no new Blocking/High?
      YES → notify the human (PushNotification) and PROCEED to implementation.
      NO, or a goal-affecting ambiguity surfaced → notify the human and WAIT for a decision.
[ ] Clear sentinel: rm .claude/plan-gate-pending  (if sentinel exists from the write hook)
```

**Rule (Conditional AFK):** the plan gate is **convergence**, not a human ack. When the dual review converges with no unresolved Blocking/High and no goal-affecting ambiguity, notify the human and proceed to implementation without waiting for a reply. Stop and wait for the human only when: review cannot converge, an ambiguity would change the goal (spec), or the next step is outward-facing/irreversible (push/merge/deploy — always a human gate). Never mark a "wait for human" step complete speculatively.

**Why both hook and task list?** The hook (PreToolUse on Agent) is a machine-enforceable backstop — it blocks subagent dispatch while the sentinel file exists; clear the sentinel only once the gate is satisfied (convergence, or a human decision when one was actually needed). The task list is the human-readable contract for what must happen first. Neither is sufficient alone.

---

## Per-Task Checklist

At the start of every implementation task, create the following items with `TaskCreate` before writing any code. Mark each `completed` with `TaskUpdate` as you finish it — do not batch.

```
[ ] Enumerate all behaviors + edge cases in plan file (table: behavior, trigger, expected)
[ ] (If complex — see "Behaviors adversarial review" below) Codex adversarial review of behaviors table — wrong, missing, or underspecified?
[ ] Write failing tests (RED)
[ ] Run tests — confirm failure for the right reason
[ ] Implement (GREEN)
[ ] Run tests — confirm all pass
[ ] Run full suite — confirm no regressions
[ ] Mutation-check every new guard: remove it → tests MUST go red → restore (see below)
[ ] Claude code review (superpowers:requesting-code-review)
[ ] Write docs/reviews/task-N-<name>-review.md
[ ] Codex adversarial review (codex:rescue)
[ ] Write docs/reviews/task-N-<name>-codex.md
[ ] Address all High/P1 and Important findings
[ ] Re-run tests — confirm still green
[ ] Commit
```

**Rule:** a step is not done until it is marked done. If a step is skipped or deferred, it stays open — do not mark it complete.

**Enumerate step:** Write the behaviors table in the task's plan file **before writing any test code**. For each behavior also ask: what if the input is missing or invalid? what if each external call fails? what if it fails mid-chain? Every answer that isn't "impossible" becomes a row in the table and a test case.

**Plan file format — required section:** Each task plan must include an **Enumerated Behaviors** table before any implementation design. Columns: `# | Behavior | Trigger | Expected`. Must include edge cases. This table is the contract tests are written against and that code reviewers check for coverage gaps. Surviving context compression is a key reason to write it in the plan file rather than in conversation.

**Mandatory behavior categories** — check these before writing any rows:
- **URL-generating components:** One row per link, Expected = exact href with every query param named (e.g. `/api/pdf/[id]?outputFolder=…&type=summary`). A row that names the route but omits params is incomplete.
- **Modal/overlay/status-bar components:** One row per dismissal mechanism (backdrop click, Escape, close button, auto-close on done). Zero dismissal rows = incomplete.
- **Optional-prop rendering:** One row for the null/absent state and one for the non-null/present state of each nullable prop. Happy-path-only = incomplete.
- **Cross-module nullable/union values:** for every `T | null` / union crossing a module boundary, one
  row: `Value | Variants | Produced by | Consumer can distinguish?`. If any row answers **No**, make the
  type honest (`{ok:true,…} | {ok:false, reason:'absent'|'unreadable'}`) — do not add a side-channel
  flag. Make the new member **required, not optional**: an optional one does not propagate, and callers
  keep silently inheriting the ambiguous original. Same row names, per boundary, which faults abort versus which are swallowed and reported.

If a task touches URL-generating components, overlays, optional props, or a nullable/union value
crossing a module boundary, and the behaviors table has zero rows in the relevant category, the
Enumerate step is not done.

*(Why: 4 Blocking/High from one `| null` that passed 6 plan rounds — `docs/process-rationale.md`.)*

**Mutation-check step:** for each guard the task adds, delete it → re-run the covering tests → they
MUST go red → restore. A test that passes in both the buggy and fixed world is documentation, not a
guard. **Commit the fix before mutating** (`git checkout` also reverts an uncommitted fix). Note
`as any` / `as never` on a test double opts OUT of compiler enforcement — tsc cannot flag a missing
member behind a cast, so behavioural tests are the only net there.
*(Why: found a defence layer with zero coverage behind 40 green tests — `docs/process-rationale.md`.)*

**Behaviors adversarial review (conditional):** After enumerating behaviors and before writing tests, run Codex adversarial review of the behaviors table when the task has any of: >8 behaviors, SSE/async state machine, multiple error paths, or concurrent interactions. Skip for simple rendering, pure data transforms, or single-function tasks.

---

## TDD Policy

### Is TDD a good fit?

**Yes:** core business logic, parsing/transformation, external API boundaries,
data integrity (file I/O, atomic writes), error handling with branching paths,
security validation, complex orchestration.

**No:** config/scaffold, TypeScript types (compiler validates), thin wrappers
(one smoke test after instead), simple UI layouts and rendering,
UI wiring/integration (E2E covers this), exploratory spikes or prototypes.

If No: implement first → spot-test any non-trivial logic after → review.

### Which TDD skill?

See `docs/plugins.md` — TDD conflict resolution.

### Test layers

Unit (jest + ts-jest) → Component (@testing-library/react) → E2E (Playwright)

Mock external API calls at the lib boundary. No real API calls in unit/component tests.

### Fast feedback loop

Run the narrowest test that covers the changed code first — full suite only before commit.

| Changed file | Run first |
|---|---|
| `components/Foo.tsx` | `npx jest Foo` |
| `lib/bar.ts` | `npx jest bar` |
| Visual / interaction bug | `npx playwright test --grep "keyword" --headed` |
| Cross-component wiring, SSE, routing | `npx playwright test` |

**Watch mode** eliminates manual re-runs during active work:
```bash
npm test -- --watch   # hit p to filter by file, t to filter by test name
```

**Rule:** targeted test green → full `npm test` once → commit. Never skip the full suite before committing, but never wait for it during iteration.

**Known-red suites: quarantine or fix, never normalise.** A permanently-red suite makes "confirm no
regressions" unfalsifiable. Whenever a suite is red for a reason **not** caused by the current work:
1. **Prove it** — stash the working changes and re-run. Same failure on a clean tree ⇒ pre-existing.
2. **Record it** in `docs/roadmap-to-launch.md` → *Dev-infrastructure debt*, with the proof.
3. **Name it in the commit** that ships alongside it — "suite X red on a clean tree, unrelated".
4. The full-suite step is only satisfiable while the set of known-red suites is **explicitly named**.
   If you cannot name why each red suite is red, the gate is not met.

Currently known-red: **none** — the list is empty as of 2026-07-19 (`reservation-release` fixed in
`c8be696`; the full integration suite is idempotent across back-to-back runs). See
*Dev-infrastructure debt* in the roadmap for the live list and the proof. **The list is meant to be
empty.** An entry appearing is the signal to stop adding features and fix the harness — and a green
suite that is only green on its FIRST run counts as red, so verify by running it twice without a DB
reset, not once.

### E2E quality rules

Violating any rule below means the E2E step is not done.

- **Link assertions — assert ALL params, not just one.** Wrong: `expect(url.searchParams.get('type')).toBe('summary')`. Right: one `expect` per param listed in the URL Contracts table (`type`, `outputFolder`, etc.).
- **Status bar / overlay dismissal — test ALL dismissal paths.** For each mechanism (✕ button, Escape, auto-close on done), write one test block that exercises that specific path.
- **Conditional rendering — fixtures must cover null and non-null.** For any nullable prop (e.g. `summaryPdf`, `deepDiveMd`), the E2E fixture set must include at least one video where the prop is `null` and one where it is set.

---

## Adversarial Review

Dispatch Codex (`codex:rescue`) with an explicit adversarial mandate at every phase.
- **Spec:** architectural gaps, underspecified behaviour, security risks, contradictions, edge cases
- **Plan:** missing tasks, wrong order, underspecified acceptance criteria, implementation risks
- **Code:** per-task (Claude + Codex independently). Both must complete before marking a task done.

Address all High/P1 findings before showing the user. Present Medium/P2 for a decision.

### Iterative Re-Review (big / critical changes) — required

One review round is not the gate; **convergence** is. After addressing a round's Blocking/High findings, **re-run the full dual adversarial review (Codex + Claude) on the *revised* artifact**, and repeat until a round reaches **diminishing returns**. Fixes routinely introduce new defects or expose deeper ones that the first pass could not see — a single round gives false confidence.

**When this is required** (any one triggers it):
- Schema / identity / idempotency changes; concurrency, leasing, or locking; auth / RLS / multi-tenant isolation; money-spending or irreversible paths.
- Refactors that touch already-merged, shared code (e.g. a function used by both local and cloud).
- **Any round that returned a Blocking finding, or whose fixes were non-trivial** (more than a reworded line). A Blocking fix is itself a new, unreviewed design — it must be re-reviewed.

For small, contained changes (single-file logic, config, thin wrappers), one round is fine — do **not** over-apply this.

**The loop:**
1. Review (Codex + Claude, independent) → group Blocking/High/Medium/Low.
2. Address all Blocking/High (present Medium for a decision).
3. **Re-review the revised artifact** — both passes again, explicitly scoped to (a) verify each prior finding is *genuinely* fixed, not reworded, and (b) hunt for defects the fixes introduced.
4. Repeat from 2.

**Four rules for the loop** — evidence for each in `docs/process-rationale.md`:
- **At fix time, list the consumers.** Before a fix that changes what state *means*, name every reader
  — including the same code in a **different process**. `grep` for the field name is usually the job.
- **Reviewer disagreement is the signal.** Never resolve a split by majority or by trusting a CONVERGED
  verdict. Adjudicate by reading the code, and **record the adjudication in the review doc**.
- **Each gate re-derives ONE inherited assumption** — chosen because this gate has information the
  earlier one lacked (per-task review re-derives what produces each variant of the types it consumes).
  One question, not a re-review.
- **Convergence measures the prompt too.** Carry a standing list of root-cause *shapes* into each
  round's prompt and ask for siblings by shape, not another read-through. List: rationale doc.

**Where review effort belongs:** per-task review is structurally blind to composition defects. Keep it
light for internally-simple tasks; spend the budget on whole-branch rounds.

**Before deferring a finding, try to turn it into an assertion.** "Unverified — check at deploy" is a
bet that a manual check happens later. If the claim can be expressed as a test using scaffolding that
already exists, write it NOW: it is usually minutes, it either promotes the finding to a fixed bug or
retires it, and either way it leaves a regression guard. Applies hardest to money and data-loss paths,
where the alternative first evidence is a production incident. Determine external behaviour by probing
the live system, not by reading vendor types.
*(Why: a suspected double-charge sat as a roadmap line for a day; one test measured it at 6¢→12¢ —
`docs/process-rationale.md`.)*

**Stop (diminishing returns) when** a full re-review round returns **no new Blocking or High** — only Low/nits, or findings already known-and-accepted (recorded as deferred with an owner). That round is the gate; then get human approval. Do **not** stop merely because you are tired of reviewing or the artifact "feels done."

**Keep going when** a round surfaces a *new* Blocking/High (common after a big rewrite) — that is proof the loop is still earning its cost; another round is mandatory.

**Save every round** to `docs/reviews/` with a version/round suffix (e.g. `-v2-rereview.md`) so the convergence trail is auditable.

*(Empirical basis — Stage 1E-b and Stage 3 cloud-sync: `docs/process-rationale.md`.)*

---

## Project-Specific: Sub-Projects

Two sequential sub-projects. Sub-project 2 does not begin until Sub-project 1 is fully verified and merged.

| Sub-project | Scope |
|---|---|
| 1 — Backend | Types, lib layer, API routes, ingestion pipeline, deep-dive pipeline |
| 2 — Frontend | React components, SSE consumption, Obsidian URI, PDF viewer |

---

## Project-Specific: Mocking Boundaries

| Boundary | What is mocked |
|---|---|
| `lib/gemini.ts` | All Gemini API calls |
| `lib/youtube.ts` | YouTube Data API + transcript fetching |
| API route level | E2E tests mock here, not at the lib boundary |

---

# Process Checklists

The lists you work *through*, not the ones you read to understand the workflow. Kept out of
`docs/dev-process.md` because their read-trigger is different: the spine is read at session start,
these are opened at the moment a gate applies.

**Rule for all of them:** a step is not done until it is marked done. If a step is skipped or
deferred, it stays open — do not mark it complete.

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
[ ] Run every mutation row the SPEC nominated for this task; each stays PROVISIONAL until seen red
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

---

## PRIOR ART is a required spec section (added 2026-08-15)

**Measured cost of not having it: thirteen review rounds and a design review, rediscovering a decision
that was already on disk in three places.**

The model blob was originally keyed by `id` (`2026-07-02-stage-1c-supabase-adapters-design.md:160`).
The address drifted to `base`. A reviewer **caught the drift** and filed it Minor, under a
*"Carry-forward → Task 7"* heading (`task-1f-a-6-materialize-helper.md:19`), where nothing carried it.
The correct destination was then independently re-derived in full
(`2026-08-03-stable-blob-addressing-design.md:179-184`) and parked. Backlog #36 then spent rounds
1–13 arriving at the same place, and paid for it with a High on a money path.

**Nobody searched. Three references, all present the whole time.**

### The rule

> **Before designing against any identifier, run `python3 scripts/prior-art.py <identifiers>` and put
> what it returns — including "searched X, found nothing" — in the spec's `## Prior art` section.**

Give it the names the design will touch: the key constructors, the schema fields, the functions whose
contract you are changing. The output is ranked by document class, because a decision in an ADR or a
spec outranks the same word in a test transcript.

- **`--self-test`** asserts it still finds all three #36 references, and that a nonsense term returns
  nothing (so the matcher cannot pass vacuously).
- **It shows every hit by default.** Its first version defaulted to decision-vocabulary lines only and
  answered *"No hits"* for `MODEL_KEY` — a **false negative from the tool built to prevent false
  negatives.** Narrowing is opt-in via `--decisions`.

### And the reason it went wrong in the first place

> **A "carry-forward" that names no destination is not a carry-forward. It is a note.**

`task-1f-a-6`'s item said *"Task 7 must ensure `base` derives from `videoId`"* — no task id, no backlog
id, nothing that would surface it again. When you defer something, give it an id in
`docs/backlog.md` or the task list **in the same turn**, exactly as
[`dev-process.md`](dev-process.md) already requires for discovered work. A heading called
*Carry-forward* creates the belief that something is carrying it.

*(Why that finding looked Minor is worth keeping too: its own sentence says **"In tests
`base===videoId`"**. A fixture that sets two distinct values equal cannot observe them diverging —
the same defect class as round-11 M3, "right for the input it was tested on".)*

---

## Spec content requirements (Phase 1 gate)

The spec is the human gate, so these are what "the spec is complete" means. Each was added because
its absence was discovered *after* implementation.

   - **For projects with a frontend:** brainstorming includes wireframe + design tokens. `docs/design-spec.md` must contain a `## UI Design` section (ASCII wireframe, token table, badge/component specs) before any Tailwind or styling code is written. The gate is unchanged — user approves the full spec, which now includes the UI section.
   - **For projects that write files:** `docs/design-spec.md` must contain a `## Output File Format` section with: filename convention (with example), required frontmatter/header fields, and an annotated sample file body. No pipeline or file-writing task begins until this section is approved.
   - **For projects with a list/table UI:** `docs/design-spec.md` must enumerate every sort, filter, and grouping operation the user needs — column, direction semantics, and what undefined/missing values do. Discovering missing operations after implementation counts as a spec gap.
   - **For any UI component that triggers an async operation (fetch, ingest, AI generation):** The spec must answer before any component task begins: (1) Blocking or non-blocking? (overlay vs. status bar vs. inline indicator) — default to non-blocking unless the user cannot do anything useful during the operation. (2) What does the user need to see/do while the operation runs? (3) What triggers dismissal? A full-screen blocking overlay requires explicit justification in the spec; "simpler to build" is not justification. Use the brainstorming Visual Companion to show a non-blocking alternative before deciding.
   - **For tasks that include UI components generating URLs or containing modals/overlays:** `docs/design-spec.md` must contain a `## URL Contracts` table (`Component | Link text | Full URL with all params`) — one row per distinct link — and a `## Overlay Dismissal` table (`Component | Mechanism | Expected result`) — one row per dismissal path. Gate: user approves both tables before any component task begins.

2. **Writing Plans** → `docs/implementation-plan.md`

## Spec contents — the coherence section (added 2026-08-09)

Two fields, both cheap, both bought with twelve review rounds. They belong in every spec that adds a
mechanism, before Phase 1's approval.

### 1. The concern → mechanism table

| Concern | Mechanism | Evidence |
|---|---|---|

**Every concern has exactly ONE mechanism. Every mechanism serves exactly ONE concern.** A cell with
two entries is a duplicate protocol; a mechanism appearing twice is a conflation. Both are the smell,
and this table is the only place either becomes visible at a glance — no per-item check can see
"two mechanisms, one job".

Filled in by the same person who designed it, so it is weak by construction. Its value is that the
omission becomes visible **to a reviewer**, not that it prevents the omission.

### 2. "What already does this?"

For each new mechanism: **which existing mechanism serves this concern, and why is it insufficient?**
Answered with a `file:line`. *"Nothing does"* is a fine answer; a vague answer is the finding.

Measured cost of skipping it: a 2800-line spec that never mentions `jobs`, which already had
exclusivity, idempotency, leases and a durable money guard — and six review rounds spent in the seam
between the two protocols.

---

## Writing a GATE (added 2026-08-11)

A gate is a claim that something about the world is true. Everything here exists because
`m1.4-finishup-checklist.md` B5 — *"`npm run check:confinement` passes against the **real deployed
environment**"* — named a **static** script that has no env, no fetch and no network. It emits
identical output everywhere, so it could only ever pass. Run it, see `OK`, tick the box, and now
believe production was verified. A guard that passes in both worlds, except the guard was a sentence.

Enforced by `scripts/check-gate-falsifiability.py` (CI ratchet; `--staleness` for the version half).

**1. `FAILS IF:` — name the observation, not the activity.**
Not *"verify downloads work"* but *"FAILS IF an owner MD download returns non-200, zero bytes, or HTML
when `format=md` was requested."* The clause cannot tell you whether your instrument can observe its
subject — that is judgment — but writing it forces you to look. Writing B5's clause is what exposed
that the command takes no URL.

**2. `VERIFIED AGAINST: vN` on every manual gate.** A tick records *that* something was verified and
never *what against*. Measured 2026-08-11: A1 and A2 were ticked on 2026-07-22/23 (the **v3/v4** era)
while the app ran **v6** — claims about code that had not run in two releases, and nothing knew.
A machine cannot know whether you looked; it can know whether the thing you looked at still runs.

**3. A gate phrased as a question is a MISSING DECISION, not a gate.** B4 — *"check whether a
rendering share starts returning 503"* — has no pass condition because nobody decided what version
skew *should* do. Tolerate / refuse / heal are all coherent, and **the same observation is a pass
under one and a failure under another**. Do not run the experiment; it yields a fact nobody can grade.
Decide, then the gate is one line.

**4. A DECISION filed as a gate cannot fail — convert it to a drift assertion.** *"We chose 5000¢"*
has no falsifier. *"FAILS IF prod `daily_cap_cents` ≠ 5000 and no newer decision is recorded"* does,
and it is the version that would have caught the 500→5000 change made by direct SQL while this repo
said 500¢ for days.

**5. Code-enforced acceptance points do not go stale on deploy; manual ones do.** A2 has three points,
two held by tests. Only the human-checked one was reopened. Reopen the part that rots, not the item.

## Running a gate AS EVIDENCE (added 2026-09-22)

⛔ **A gate run over an uncommitted working tree is not evidence about what CI will read.** Several
gates compare the **committed** diff against a base — `check-dashboard-entry.py`,
`check-review-recorded.py`, `check-backlog-closure.py`. Run before committing, they answer about a
tree that does not exist yet, and the answer is usually a cheerful pass.

MEASURED 2026-09-22, **twice in one session, an hour apart**: a merge resolution that fused two
dashboard entries under one header, and a roadmap edit — both reported *ok* locally and **REFUSED**
in CI. The second happened after the first had been diagnosed and written down, which is the
argument for a line here rather than a remembered lesson.

**Do this:** commit first, then run the gate with the arguments CI uses — `--base origin/master`,
and `--pr-body-file` where the gate reads the PR body. A pass over `git status`-dirty work is a
statement about your editor, not about the branch.

⚠ **And capture the exit code on its own line.** `cmd >out 2>&1; echo "rc=$?"` reports the
redirect's status, not the command's — it produced a false `rc=0` over a red gate and a false
"exit code 0" over a mutation sweep whose log said `NOT MEASURED` on the same day.

## Writing a RATCHET (added 2026-08-11)

**There are EIGHT**, and each invented these independently, differently:
`check-arch-findings.py`, `check-guard-coverage.py`, `check-sentinel-meanings.py`,
`check-vocabulary-collisions.py`, `check-gate-falsifiability.py`, `check-ratchet-contract.py`,
`check-storage-grant-pin.py`, `check-test-counts.py`.
**Do not maintain this list by hand — `python3 scripts/check-ratchet-contract.py` prints it**, from
two independent sources, and is the reason the count below was ever corrected.

*This paragraph originally said "three", written from memory — it undercounted by half, and
`scripts/check-ratchet-contract.py` is what caught it before this document merged. Which is the
argument for the whole section: a convention described from recollection is already wrong.*

**Enforced, not merely written.** `check-ratchet-contract.py` discovers ratchets from two independent
sources — CI step names containing *"ratchet"*, and any `scripts/check-*.py` whose docstring declares
itself one — so neither a forgotten registry entry nor an unwired script can evade it. It enforces the
two rules that are statically decidable (**1** and **4** below) and **says so explicitly** rather than
implying it covers all six. Currently 4 violations, all rule 4, all pre-dating the contract.

**1. "Cannot run" is a FAILURE, never a pass.** The single most important line here. If the tool
cannot reach what it measures, it must exit non-zero and say *treat this as NOT RUN*. Measured
precedents: Codex reviewing by reading because it was sandboxed out of the Docker socket and reporting
success anyway; the integration suite running green against the wrong schema. `check-gate-falsifiability
--staleness` exits 1 when it cannot read the deployed release, verified by running with `fly` off `PATH`.

**2. Exit semantics, all three directions:** at baseline → **0**; above → **1**; below → **0 plus a
nudge to lower it**. Test all three. The first revision of the newest ratchet returned **1 at
baseline**, which would have broken CI the moment it merged.

**3. The baseline is a named constant with a dated comment.** Lowering locks in a gain; raising must
appear in a diff where someone can ask why. A ratchet exists because a big-bang failure over existing
debt gets switched off — the point is to stop the *next* one, not to punish the backlog.

**4. `--self-test`, and mutation-verify the discriminators.** Stub the detector and confirm cases go
red. Expect roughly half your cases to pass against a stub — those are the "expect no findings" ones,
necessary against false positives and useless as proof of life. Then mutate each discriminator
separately and confirm each kills at least one case.

**5. Declare the scope, because an unstated one is assumed total.** `check-guard-coverage.py` reads
`pg_catalog` for the blob-addressing tables only, so migration-defined guards are invisible to it and
its output is byte-identical with and without migration `0024` (backlog #29). Say what is covered in
the file, and prefer failing over silently covering less.

**6. Never mutate repo-tracked files.** Mutate a temp copy. A harness that edits the working tree
corrupted a concurrent reviewer's run: 23/44 vs 44/44 on the same commit.

## A NOMINATED FALSIFIER is provisional until it has been run red (added 2026-08-14)

A spec's mutation table nominates falsifiers: *"mutation M must turn behavior N red."* That is a
**prediction**, and this project has shipped it as a fact repeatedly — the #36 spec alone reached a
**third** vacuous falsifier before anyone counted (task #96, *"fix the injectivity overclaim and the
third vacuous falsifier"*), and each was written by someone who believed the row was load-bearing.

A nominated falsifier fails in exactly two ways, and you must check for both **per row**:

1. **The mutation survives** — the named observable does not actually depend on the named mechanism.
   The row then reads as coverage while proving nothing.
2. **The input is unconstructible** — no caller can reach the state the mutation would corrupt. The
   test can never run, so it can never go red.

**The rule: a mutation row is `PROVISIONAL` until the mutation has been applied and the named
behavior observed RED.** Mark it so in the spec. This is not a Phase 1 obligation and cannot be —
**at spec time there are no tests to mutate.** It is a Phase 3 obligation, and it extends the existing
Mutation-check step from *guards the task adds* to *falsifiers the spec nominated*. A spec may state
its table; it may not state that its table is verified.

**Name an observable, not a mechanism.** *"Behavior 17 admits `℀.md`"* can go red. *"The NFKC pass is
skipped"* restates the mutation and cannot.

*(Why this is not a ratchet: a script can find mutation tables, but deciding whether a named input is
constructible requires reading the callers. `check-gate-falsifiability.py` covers the gate half of
this shape; the mutation half stays human.)*

---

## Qualify every number in prose (added 2026-08-27)

**A bare `#39` is not a reference. Write `backlog #39` or `task #39`.**

Same for every other scarce namespace this project reuses across documents:

| Write | Not |
|---|---|
| `backlog #39`, `task #39` | `#39` |
| `PR #155`, `migration 0027` | `#155`, `0027` |
| `spine M4`, `roadmap M2` | `M4`, `M2` |
| `ADR-0011`, `round 11` | `0011`, `11` |

**Applies to** chat, commit messages, PR bodies, review documents, and newly written doc prose.
**Does not apply** inside the document that owns the namespace — `docs/backlog.md` citing its own
rows as `#31` is unambiguous, and rewriting the 1,556 historical bare references would be churn
with no reader on the other end.

### Why this is a rule and not a ratchet — MEASURED 2026-08-27, three scopes

Before writing this, the obvious script was tried on paper at every scope that could carry it:

| Scope | Bare `#N` found | Verdict |
|---|---|---|
| all of `docs/` | **1,556** of 2,130 | a gate firing 1,556 times is disabled the same day |
| added lines on one branch | **24** | ~90% false positives |

The 24 were `Phase 6 #1`, `Architecture Review #2`, `#54(a)` — **titles and ordinals, not
references into a namespace.** Making the check usable means adding `Phase`, `Review`, `Section`…
i.e. asking *"what did the last counter-example have that a real reference does not?"*, which is a
question about SYNTAX with an unbounded supply of answers. `scripts/run-schema-assertions.sh`
records that exact sequence costing four review rounds in this repo. **A syntactic proxy for
"is this reference resolvable?" is the wrong instrument; the property is semantic.**

### What it actually costs when skipped — two measured instances, same day

- **A wrong turn.** Searching `#26` in `docs/backlog.md` returns nothing, because that file uses
  bare `| 26 |` in a table. The item had to be found by grepping the *concept* instead.
- **A reader had to ask.** Four bare `#39`s were written in one message — in an argument that bare
  numbers are ambiguous — while `task #39` and `backlog #39` are unrelated items. The ambiguity was
  invisible until the reader asked "backlog or task?".

⚠ **Neither is expensive. That is the point:** the cost is a few minutes each time and it is paid
by the *reader*, which is why nothing surfaces it and why it needs to be a habit rather than a gate.

⟳ Related: **backlog #39** — *roadmap items have no permanent identity* — states the general
principle (*separate the label from the identity in any document that other files cite*). Its
`files` column names only the roadmap, so doing it as written would not reach the two collisions
above. Widen the scope there rather than filing a second row.

---

## Reduce defect INJECTION, not just detection (added 2026-09-24)

**Read when:** writing a commit message, a **code comment**, a review document, a PR body, or a
claim about what a change does. Not when reviewing — this is about what the AUTHOR puts on the page
for a reviewer to find.

⟳ **`code comment` restored in r1 (Low).** The proposal's scope was *"a commit message, comment or
doc"* and the first adopted draft silently dropped comments — the surface where a stale count is
hardest to notice, because nothing re-reads a comment.

**The measurement that produced it (backlog #177, `docs/development-velocity.md` §6).** Over the
session that merged PR #342 and implemented backlog #176, a large share of review findings were not
defects in the code at all. They were **the author's own unverified claims**, and each one cost a
full review round to surface:

| Finding | What it actually was |
|---|---|
| PR #342 r5 H1 | a correction **appended below** a false paragraph; the commit message said it was fixed |
| backlog #176 r1 L1 | commit message said `1858 → 1755` lines; measured `1858 → 1869` — the file **GREW** |
| PR #342 r5 M1 + r5 Codex Medium | *"the class is closed"* — asserted twice, both times an instance fix |
| backlog #176 r1 M3 | `183 verdicts` — wrong (184), and copied into three further places |

⭐ **These are the cheapest findings in the repo to prevent and the most expensive to catch.** A
defect in code needs a reviewer who understands the code; an invented number needs only a reviewer
who checks, which is why they survive to round 5. All four rules below cost nothing to follow.

### 1 · No number unless it was measured in THIS session

Not recalled, not carried from a previous document, not inferred from a diff you did not run. If you
did not produce it with a command in this session, either **derive it now** or write what you
actually know without the number.

⚠ **This is NOT the rule at *Qualify every number in prose*** above. That one is about
**resolvability** — `backlog #39`, not a bare `#39`. This one is about **provenance** — whether the
number is true. A number can be perfectly qualified and entirely invented, and `backlog #176 r1 M3`
was exactly that.

⛔ **The corrections fail too.** Re-deriving a remembered number from memory a second time is the
same act. Cite the **symbol or the command**, not the recollection.

### 1b · Say WHAT YOU COUNTED, not just that you counted

⟳ **Added 2026-09-24 from this rule's own first review round, which found three instances of it in
the change that introduced the rule.** A number can be honestly measured and still be false,
because the label names a different population from the command:

| Written | Measured | The gap |
|---|---|---|
| *"28 gates named"* | distinct `scripts/check-*.py` in one workflow | the regex excluded `.sh`; "gates" names steps (54), scripts (34) or workflows — not this |
| *"the draft PR caught #176 r2's Blocking"* | a Blocking that states it rests on an anchor measurement, **not** a CI verdict | the claim named a cause the source explicitly disclaims |
| *"derive from `ci.yml`"* | one of two required workflows | the scope was the hand-written part |
| *"34 distinct scripts invoked by `ci.yml`"* | `grep` over the file's **text** — 33 are invoked | ⟳ **r2 Medium: this table's own row, written to illustrate the rule, committed the defect.** The 34th is mentioned only in a comment |

**So a number carries its population or it is not a measurement.**

⛔ **THE FOURTH ROW IS THE STRONGEST ONE, AND IT WAS NOT PLANNED.** Rule 1b was written in the r1
fold from the three rows above; writing it produced the fourth, in the same paragraph, and review
round 2 found it. A rule that catches its own author while he is writing it down is not a rule
about carelessness — **the slip is in how measuring works**, because `grep` answers a question that
sounds identical to the one you meant and is not. Write *"34 distinct scripts
invoked by `ci.yml`"*, never *"34 gates"*. ⚠ This is the failure mode that survives rule 1: rule 1
asks *did you measure it*, and all three answered **yes**.

### 2 · Fix the sentence IN PLACE

An appended correction is not a fix. The reader meets the wrong sentence first and may stop there.
Edit the claim where it stands; if the history matters, keep the original **as a marked strikethrough
or a ⟳ note attached to the corrected sentence**, never as a later paragraph that argues with an
earlier one.

⚠ The exception is an **append-only store** (`docs/dashboard-entries.md`), where a correction is
required to be a new entry — because there, ids are positional and editing rebinds them. Everywhere
else, in place.

### 3 · A class claim requires a class SWEEP

*"The class is closed"* means every member was **enumerated and tested**. It does not mean the named
instance was fixed and the others look fine. If you cannot state how the members were enumerated,
you do not have a class claim — you have an instance fix, and saying so costs nothing.

**Worked example from the source session:** perturbing **every** module-level constant in both
touched files, then re-running until none survived. That is an enumeration. Reading the file and
concluding it looks complete is not.

⚠ **The survivor COUNT is deliberately not quoted here.** It was carried into an earlier draft from
the rationale document and r1 found the underlying measurement disagreed with it. The method is
what this rule teaches; the number belongs to the measurement that produced it, where it can be
checked. Quoting it here would break rule 1 inside the section that argues for rule 1.

⟳ **This is the AUTHOR-side twin of `review-method.md` §0 Q2 step 5** (*every finding names a
sample, not a scope*). That step binds the reviewer; nothing bound the author, and the two findings
above are what that gap produced.

⚠ **"Do not restate" applies to THAT step, not to this rule** — r1 Low. The paragraphs above state
the author rule in full on purpose, because this is where it governs. What must not be copied here
is the reviewer's step; read that one at its own site.

### 4 · Derive gate lists from the WORKFLOWS, never from memory — and never from one workflow

Before claiming the gates pass, read what `.github/workflows/` actually invokes and run that. A
hand-written list of five gates cost a full CI round-trip in the source session.

⛔ **NOT `ci.yml` ALONE.** `scripts/check-merge-ready.py:52-55` already carries this defect and its
correction, in its own words: *"EVERY WORKFLOW, NOT `ci.yml` ALONE … The first version parsed one
file and claimed the pull-request-only list was 'derived, never hand-written'; the FILE SCOPE was
the hand-written part."* `schema-gates` is the other required context on every PR, so a derivation
that reads `ci.yml` only omits the fifteen schema gates entirely — while congratulating itself on
being immune to exactly that.

⚠ **AND SAY WHICH POPULATION YOU COUNTED** — see rule 1b. Measured 2026-09-24 **by parsing `run:`
blocks, not by grepping the file**: `ci.yml` invokes **33** distinct `scripts/*.py|sh` (of which
**28** are `check-*`) and `schema-gates.yml` a further **4**, while `ci.yml` carries **54** `run:`
steps. "The gates" names none of those on its own.

⛔ **A GREP OVER THE WORKFLOW IS THE WRONG POPULATION, AND THIS SENTENCE SHIPPED WITH THE PROOF.**
The first version said **34**, from `grep -oE 'scripts/…' ci.yml | sort -u`. The extra one was
`scripts/check-schema-gates.sh`, which appears in `ci.yml` **only in comments** (`:267`, `:286`) —
the exact fact this rule's own correction rests on. A text match counts what the file MENTIONS; the
question is what it RUNS.

**Prefer running `scripts/check-merge-ready.py` over assembling a list at all** — it derives its
own, and it reaches the pull-request-only gates a local run cannot.

---

## Presenting a DECISION to the human (added 2026-09-04)

**Read when:** you are about to ask the human to choose. Not when you are discussing a design —
prose is better there — and not when one option is obviously superior, where you should just decide.

The point of this format is that the human can **review the rationale and the trade-offs**, not just
pick a label. A menu of bare labels moves the decision to them while keeping the reasoning with you,
which is the worst split of the two.

### The format

Every option gets, in this order:

1. **A letter** — `A —`, `B —`, `C —`. So the choice can be referred to later ("we took B") and
   discussed without re-quoting the whole label.
2. **A short label** — what the option *is*.
3. **The rationale** — why someone would pick it.
4. **The trade-off** — what it costs, or what it gives up. An option with no stated cost is either
   obviously correct (so do not ask) or under-analysed (so analyse it).
5. **A recommendation on exactly one option**, marked `(Recommended)`, with the reason in its body.
   Withholding a recommendation is not neutrality — it is handing over an unfinished analysis.

Plus, always:

* **The last option is `D — I have a question about these`.** Without it, the only way to say *"these
  options look wrong"* is to fight the form.
* **State in the question text what the options actually differ on** — "A/B differ in whether X goes
  live now". That names the axis, which is the thing being chosen.

### ⛔ The check that this format does not do for you

**Every option must produce DIFFERENT WORK.** Verify before presenting.

MEASURED 2026-09-04: a four-option menu about merging two PRs shipped with A and D as the *same
action* — "merge both in order" and "merge both, review after". The ordering in A was a mechanical
constraint (the second PR was stacked on the first, so it *had* to follow), not a choice at all. The
human's reply was *"What is the difference between first and last choices?"* — the only way they
could raise it, because the menu had no question-shaped exit.

**A menu whose entries collapse is worse than prose**, because it asserts a distinction that is not
there and invites a decision that does not exist.

### When NOT to use this

* **During design** — use prose. Options force a fork before the shape is clear.
* **When one option is obviously superior** — decide, say what you decided and why, and move on.
* **For a mechanical constraint** — an ordering forced by the code is not a decision. Say it is
  forced.

---

## Closing a job: the CHECK / RESULT table (added 2026-09-04)

**Read when:** you are about to report that a unit of work is done.

Do not close with a paragraph. Close with a table, one row per claim, evidence in the row:

```
| check                  | result                                            |
|------------------------|---------------------------------------------------|
| Rows 92, 93, 94 exist  | ✅ all three                                       |
| Old wording gone       | ✅ absent — checked for absence, not just new text  |
| Commit                 | `896f6ef5`                                        |
| Pushed                 | ✅ same SHA on origin                              |
```

**Why the format and not prose.** MEASURED 2026-09-04: a correct prose report of three filings plus
a pointer repair drew the reply *"Have you done this too?"* — because a paragraph asserting the work
is indistinguishable from a paragraph asserting it wrongly. The same content as a table ended the
question. The user's framing: *"this kind of visible marker is important for comprehensibility."*

### Three rules

1. **One row per claim.** Bundling four assertions into a sentence means a reader who doubts one
   must re-check all four.
2. **Evidence in the row.** A SHA, a count, a command's output. Not *"successfully"*.
3. ⛔ **Every row must be a check that could have come back ❌.** A table whose rows can only say ✅
   is a decorated assertion — worse than the paragraph, because the format implies verification that
   did not happen. Ask each row: *what would have made this fail, and did I run that?*

### Two traps, both measured the same day

* **Presence is not absence.** Confirming the NEW text is there passes even if an edit appended
  instead of replacing, leaving the broken version in the file too. Assert the old text is **gone**.
* **The mislabelled row.** An agent printed *"(none listed = nothing left open)"* under a list
  containing one item. Right data, wrong label — worse than no label, because the label is what the
  reader keeps.

### Where this sits

Three affordances, three moments: the **step banner** (`## ▶ STEP n of N`) for *what is happening
now*; the **option list** with rationale and trade-offs for *what you must decide*; this table for
*what was actually verified*. See *Presenting a DECISION to the human* above, and
`docs/portable-practices.md` §19–§20.

---

## Architecture review: re-examine the review topology (added 2026-09-13)

The round topology — concurrent r1, alternating r2+ — is written in
[`review-method.md`](review-method.md) → *Round topology*, and it carries **two observations that
would retire it**. They are read HERE, at the architecture review, because they need a judgement no script can make:
whether two findings are *the same finding*.

| Ask | Retire / revisit if |
|---|---|
| Did any round's **fix delta** contain a finding? | **no** for five consecutive rounds → alternating buys nothing; go back to concurrent-only |
| Did the two halves of one round report the **same finding**? | **twice in five rounds** → the independence premise has weakened; concurrent-plus-dedup is cheaper |

**Derive the evidence, do not remember it.** `docs/reviews/verdicts/*.json` names every Codex round
and the commit it was handed; the halves are under `docs/reviews/<writer>/`. A hand-maintained tally
is stale at commit time, structurally — this project has measured that on a document counting itself.

⚠ **Only step 5 of the protocol has a machine behind it** (`check-review-recorded.py` refuses a
branch where guarded code was committed after every round). Steps 1–4 are convention, so this
re-examination is the only thing that ever observes whether they are being followed.

---

## A SIDE JOB gets a name before it gets work (added 2026-09-22)

**Read when:** something arrives mid-session that is not the thread you are on — a user complaint,
a defect you tripped over, a blocker, a review finding you want to fix now.

**The failure this prevents, measured twice in one session (2026-09-22).** A user-reported Stop-hook
defect was diagnosed, fixed across three guards, given nine mutations and three suites — about
forty tool calls — **with no plan armed, no branch name in any message, and no banner emitted**.
The user could not tell which of two live threads any line belonged to, and said so. Earlier the
same day the same thing happened at smaller scale. Neither was a judgement call that went wrong;
in both cases the work simply started and the naming never happened.

### The rule: SIZE IT FIRST, in one question

> **Will this take more than about five tool calls, or touch a tracked file?**

**No → do it inline.** No plan, no branch, no row. Say in one clause what you are doing. Re-reading
a file, answering a question, a one-line correction: naming these costs more than it returns.

**Yes → it gets a NAME before the first edit**, and the name means three things that must agree:

| | what | why this one |
|---|---|---|
| 1 | a **plan slug** — `scripts/begin-plan.py <slug> …` | banners derive their thread name from the slug. With nothing armed there is no name to print, and the measured outcome is that bannering stops altogether rather than the gap being noticed |
| 2 | a **branch** | `dev-process.md` Phase 5 already requires branch + PR for any `lib/ app/ scripts/ tests/` or config change. A side job is not an exception to it |
| 3 | a **backlog row** — ONLY if you are deferring it | filing what you are about to do in the next ten minutes is bookkeeping. Filing what you are NOT going to do is the point. ⚠ Filing is the user's step — agree before filing |

### ⛔ A side job inherits NO design approval from the slice it arrived in (added 2026-09-24)

The name gets it a thread. It does **not** get it the review the parent work had.

**Measured, one branch, same reviewers, same gates — the only variable was whether the work had a
design** (backlog #177, `docs/development-velocity.md` §4):

| Work on PR #342 | Had a design? | Outcome |
|---|---|---|
| observer-log record | ✅ an architecture review filed beforehand | **CONVERGED by round 3** |
| verdict path | ❌ opportunistic side job, entered mid-round-3 | **thrashed 3 rounds**, then needed its own architecture review |

⚠ **The fix is NOT more upfront review.** The verdict path was out of scope and untouched when the
first review ran, so no amount of reviewing at the start would have covered it — and reviewing
everything upfront to catch what you might stumble into is waterfall. **The gap is that work
entering AFTER the review inherits none of it**, while arriving on a branch that already looks
approved.

So when a side job is sized YES, ask of the side job itself: *does this move a seam — a new module,
a change to who owns what, a new protocol or vocabulary — or is it logic inside an existing one?*
Seam work wants its design settled before it is built, on a branch of its own.

⟳ **When backlog #177's Q0 lands in `review-method.md` §0, this is the moment that re-asks it** —
decided 2026-09-24 with the user, form recorded in that row. Until then the question above is asked
by hand, and the four signals that say *seam* are in `development-velocity.md` §3 — **which are
OBSERVATIONS, usable now.** That document's banner marks §3 *not built*, meaning not mechanised;
it does not mean not applicable, and r1 (Low) found that reading available.

### Switching, and what is actually supervised

⟳ **CORRECTED 2026-09-22, HOURS AFTER THIS RULE WAS WRITTEN.** The first version said
*"`.claude/executing-plan` supervises ONE plan; two threads cannot both be armed."* **False, and
measured false the same afternoon** — with both threads live, the main tree's sentinel held one
plan and a worktree's held the other, simultaneously. `begin-plan.py` resolves `ROOT` from its own
path, so **every tree gets a private sentinel**. The constraint was written from one observation
(the two threads happened to share a tree) instead of from the mechanism.

⛔ **THE REAL LIMIT IS NARROWER AND WORSE: one plan per tree, but only ONE TREE IS SUPERVISED.**
`.claude/hooks/block-idle-stop.sh` derives `REPO_ROOT` from its own path, and the session runs the
hook belonging to the session's cwd. Observed: while work happened in a worktree, the Stop hook
kept reporting the MAIN tree's plan. So a worktree plan **gives banners a name and has no guard
behind it** — premature-stop protection is not running for that thread.

**Same tree as the current thread** (the common case):

1. `--pause` the current thread with a reason that says **how to get back** — name the plan file,
   because the next turn will not remember it.
2. Arm the side job; `--finish` it; re-arm the original with `--plan .claude/plans/<slug>.md`,
   which preserves its ticks.

**A separate worktree** (isolation from an in-flight sweep or a live agent): arm its own plan
directly — no pause/resume dance — **and know its Stop guard is not firing.** That is a reason to
prefer the same tree unless isolation is actually needed, not a free upgrade.

**Either way, mark the switch in the banner:** `⤳ SWITCHED from <old> (state) → <new>` and
`↳ RESUMED <old>`. The glyph is what makes it scannable; the parenthetical state is what makes it
recoverable. This is the half that does not depend on which tree anything is in.

### What is mechanically enforced, and what is not

**Enforced:** a turn that does substantial work with nothing armed and no banner is exactly
`check-banner-armed.py`'s `unheralded` class. That guard is the mechanical half of this rule — do
not restate its threshold here, and read it rather than recalling it.

⚠ **NOT enforced, and stated rather than implied:** nothing checks that the slug, the branch and
the row describe the same job, and nothing can — three names agreeing is a judgement. Nothing
detects a side job that stays under the size question's bar and then grows past it; the honest
mitigation is to ask the question again when it does, not to lower the bar.

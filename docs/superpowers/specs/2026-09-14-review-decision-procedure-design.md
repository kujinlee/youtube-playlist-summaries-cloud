# Review decision procedure — design

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

## Why this exists

**Measured 2026-09-14 on PR #302.** A contained, single-file change to a page generator ran **four**
adversarial review rounds. Rounds 1 and 2 were owed. Rounds 3 and 4 were not: each returned a single
Low **in the coordinator's own test code**, on exactly the change `review-method.md:309` names when
it says *"one round is fine — do not over-apply this."*

⭐ **The cause was a conflation, not a missing rule.** Two different questions were merged and
reported to the user as one:

| | asks | satisfied by |
|---|---|---|
| **Convergence** | has defect discovery dried up? | diminishing returns (`:302`) |
| **Tree identity** | did a round see the code that MERGES? | **four** ways, only one of which is another round |

Rounds 3 and 4 were run to satisfy **tree identity** while being narrated as if convergence were
unmet. The cheaper answers existed, were already written down, and were never offered to the user.

⛔ **And the rule that would have prevented it was already in the file.** `review-method.md:266`:

> **Batch the editorial fixes BEFORE the last round.** … a converged round left one stale-prose Low,
> **fixing it cost another round**, and that round found three more spellings of the same thing.

That paragraph predicted the failure in advance. It was not read; it was recalled. **This is the
same shape as backlog #115** (a waiter rule, written down, imported into every session, broken three
times in one day) and the selection-card rule (written in three places, 1-for-3 in one session).

**So the problem is not absent rules. It is that the rules are spread across five sections of three
documents, phrased as heuristics needing a judge, and consulted from memory at the moment of use.**

## What this changes

Five pieces. §1 and §4 stand alone and land first; §2 and §3 depend on §1 being settled.

---

## §1 — The decision card, as section 0 of `review-method.md`

Six questions, each with **observable** inputs. The existing deep sections stay beneath as the
evidence for each rule — one source per rule, nothing duplicated.

### Q1 · Does this change need the full loop, or one round?

Decided by the **changed path set**, not by judgement.

| Condition | Path |
|---|---|
| touches schema/migrations, auth/RLS/multi-tenant, money or irreversible paths, concurrency/leasing/locking, **or already-merged shared code** | **full loop** |
| anything else — single-file logic, config, thin wrappers, docs | **one round** |

Source: `:305` (the trigger list) and `:309` (*"do not over-apply this"*).

### Q2 · Round 1 — both halves concurrently

1. Dispatch **both halves at once**, isolated per the measured concurrency table (`:171`).
2. ⛔ **Hold both uncommitted until both finish** (`:243`). A committed first half leaks its grade to
   the second through `git log` and the diff. This is the whole fix for leakage.
3. Output contract per half: **Codex's final message IS the review — it writes no file**; each half
   is filed under `docs/reviews/<writer>/`.
4. A half that cannot run is recorded as `REVIEW GAP: <half>` **with the reason**, never omitted.
   Codex unavailable for any reason → fall back to a Claude adversarial half immediately; do not
   wait or retry (`plugins.md`).

**Why concurrent and not duplicated effort:** measured zero overlapping findings across three rounds
on two branches (`:222`). The halves do different work — Codex executes, the Claude half designs
experiments. What *is* duplicated is environment construction; dedupe that, not the reading.

### Q3 · Disposition — decided per finding, with no human gate

⟳ **This REPLACES `:298`'s "Present Medium/P2 for a decision"**, at the user's direction
(2026-09-14). That line was the mandated interruption.

| Finding | Action |
|---|---|
| **Blocking / High** | **FIX**, always |
| **Medium / Low** — inside the delta under review, and the fix is *contained* | **FIX** |
| **Medium / Low** — needs a new mechanism, script, schema, or a policy call | **FILE** to the backlog |

*Contained* is observable: the fix touches only files already in the branch diff, and introduces no
new mechanism.

- **Record the disposition and its reason per finding** in the round document. The human overturns
  any of it after the fact; nothing is silently dropped.
- ⚠ **A reviewer's PROPOSED fix is unverified code** (`:246`). Findings arrive measured; the
  sentence after *"Fix."* never does. Twice in one session a proposed fix was weaker than the
  finding it closed.
- **Filing to the backlog remains the human's step** where the repo already says so — the
  disposition is recorded as *proposed for filing*, and the row is written on agreement.

### Q4 · Is another round owed? — TWO questions, never merged again

**(a) Convergence — has defect discovery dried up?**

| Observation | Decision |
|---|---|
| the round produced a **Blocking or High** | **CONTINUE** |
| the round produced a finding **in the deliverable** | **CONTINUE** |
| the fixes were **non-trivial** (more than a reworded line) | **CONTINUE** (`:307`) |
| **two consecutive rounds** produced no Blocking/High **and** every finding was aimed at the **instrument** (test, guard, harness) rather than the deliverable | **STOP** |

⭐ **Judge by AIM, not by severity.** `:132` already says *"no new Blocking or High is a statement
about the REVIEWERS, not the design"*, and PR #302 measured the same thing from the other side:
severity read "converged" from round 1 and was useless, while the aim column separated the rounds
cleanly. **The same instruction inverted is why PR #299 was right to run seventeen rounds** — there
every round aimed at the deliverable found a fail-open. Read the aim, not the count.

**(b) Tree identity — has a round seen the code that will merge?**

Answers **in cost order**. Take the cheapest that applies:

1. **Batch the editorial fixes BEFORE the last round** (`:266`).
2. **Hold the final fixes uncommitted** so the reviewer sees the state that ships — `:252` calls
   this *"the documented way to do it"*.
3. **`NO-REVIEW: <reason>`** in the PR body.
4. **Another round** — the last resort, not the first.

> ⛔ **NEVER run a round solely to satisfy (b) without first offering options 1–3 to the human.**
> This single line is what PR #302 cost.

Mechanically enforced by `scripts/check-review-recorded.py`, which reads the commit and the git tree
entry of every file handed to each Codex run.

### Q5 · Is this thrashing? → **architecture review**

Per finding, answer **out loud and in the round document**: *did the previous round's fix cause
this?*

| Shape | Tell | Do |
|---|---|---|
| **Thrashing** | findings are introduced by the previous round's own fix; the same component | **ARCHITECTURE REVIEW** |
| **Branch coverage** | *"the rule doesn't say what happens in case X"*, where X is a branch the rule governs but does not own | **FIX** + an exhaustiveness pass |
| **Prose floor** | findings shift from *"this cannot work"* to *"this is under-specified"*; the artifact keeps improving | **STOP REVIEWING.** Write the code and review that |

**The one test** (`:67`): **can a redesign remove it?** If a different shape dissolves the finding it
is a mechanism defect and the redesign is owed; if it would survive every reasonable reshaping, it
is not. Quote the test, never the symptom list — applying the list as a checklist produced a
measured **false REDESIGN** on 2026-08-14.

**Arming condition: two consecutive fix-induced rounds in the same component** (`:45`).

⟳ **THE COUNT NO LONGER ARMS IT** (decided 2026-09-14). Reaching four rounds **obliges asking the
question and recording the answer**; it does not fire the review. See §5.

### Q6 · Record the call

Whichever way each question went, write the reason and the per-finding evidence in the round's
document (`:350`). A decision to stop reviewing looks arbitrary six weeks later.

---

## §2 — A machine-readable header on each coordinator round document

The counters the rules in §1 depend on — *consecutive fix-induced rounds*, *rounds since a finding in
the deliverable* — are exactly what nobody kept on PR #302. They are mechanical, and
`review-method.md:285` already forbids the alternative: *"the evidence is derivable, not remembered.
Do not maintain a hand-written tally of it."*

A fenced block immediately after the round document's title:

```yaml
round: 3
subject: clickable-dashboard-asks
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, disposition: fixed}
  - {id: L1, severity: Low,    aim: instrument, fix_induced: true,  disposition: filed}
```

**Field definitions, chosen so each is observable rather than interpretive:**

| Field | Values | Definition |
|---|---|---|
| `severity` | Blocking / High / Medium / Low | as filed by the reviewer |
| `aim` | `deliverable` / `instrument` | does the finding sit in the code the branch ships, or in a test, guard or harness that measures it? |
| `fix_induced` | true / false | was the defect introduced by a fix written after a previous round? |
| `disposition` | `fixed` / `filed` / `declined` | what Q3 decided, with the reason in prose below |

`aim` and `fix_induced` are judgements **the agent makes and records**; the header does not pretend
to derive them. What becomes mechanical is the **bookkeeping and the decision rule**, which is where
recall failed.

## §3 — `scripts/check-review-decision.py`

Reads the round-document headers for the current branch, the `docs/reviews/verdicts/*.json`, and the
branch diff, and prints exactly one decision:

```
ROUND N OWED — <which question obliges it>
STOP — converged (2 consecutive instrument-only rounds, no Blocking/High)
ARCHITECTURE REVIEW — thrashing: <component>, fix-induced in r<N-1> and r<N>
TREE — cheapest answer: hold the final fixes uncommitted
```

**Contract:**

- **Exit 2 — CANNOT RUN** if any round document for this branch lacks a header, or if the branch has
  no rounds and the diff cannot be read. A missing input is a failure, never a pass.
- Exit 1 when a round is owed; exit 0 when the answer is STOP.
- `--self-test` with a declared count, a manifest entry in `scripts/mutations/`, and a caller — per
  `check-ratchet-contract.py`.

⚠ **What it deliberately does NOT decide.** `review-method.md:274` names the retire-conditions for
the alternating topology and says they *"are read at [the architecture review], not by a script —
they need judgement about whether two findings are the same finding, which is exactly what a script
cannot do."* This script answers *what now*; it does not adjudicate findings.

## §4 — Rename "Phase 6" to "architecture review"

**Measured origin:** the term first appears 2026-08-08 in commit `0b27094e`, the same commit that
introduced the phases table in `docs/dev-process.md`. It is a **row index in one table in one repo**,
used as a proper noun. It is not an industry term — no vendored plugin or skill uses it in this
sense, and `superpowers:improve-codebase-architecture`, the skill it maps to, never uses it at all.

**The usage proves the problem:** Phase 1 has 62 mentions across `docs/`, Phases 2–5 between 21 and
33 — and **Phase 6 has 184**, more than the other five combined. The other phases acquired spoken
names; 6 never did, despite the table naming it **Architecture Review** on the day it was created.

| | Action |
|---|---|
| **Instructions** — `dev-process.md` (5), `review-method.md` (4), `process-checklists.md` (3) | **rename** to *architecture review*; the number survives only as the phases-table index |
| **The record** — merged review documents, ADRs, retrospectives, dashboard entries | **leave unchanged** — rewriting them is editing evidence |

✅ **THE MACHINE-DEPENDENCY GREP WAS RUN, AND IT IS CLEAN** (2026-09-14). Every occurrence in
`scripts/`, `.claude/hooks/` and `.github/` is inside a **comment** — `check-docs.py:290`,
`m4_catalog.py:173`, `check-schema-gates.sh:78,81`, `ci.yml:195,220`. No code keys on the string, so
no gate can unhook. Those comments are provenance and stay as written.

⟳ **Two corrections to this section, measured after it was drafted.** `plugins.md` contains the term
**zero** times and is removed from the rename list above. And the instruction surface is far smaller
than the 74-file total suggests: **3 files, 12 occurrences.** `roadmap-to-launch.md` (8) and
`backlog.md` (9) are **provenance** — *"Phase 6 returned eight findings"*, *"Phase 6's trigger did
fire"* — and are therefore record, not instruction.

## §5 — Resolve the trigger contradiction

`docs/dev-process.md` arms the architecture review after **four non-converging rounds** — a count.
`review-method.md:324` says *"the distinction is the CAUSE of the non-convergence, not the count"*,
and `:337` says *"RAW BLOCKING COUNT IS A BAD DISCRIMINATOR, AND THIS WAS MEASURED"* — the dashboard
spec ran Blocking **4 → 5 → 4**, flat, which reads as thrashing by count and was the prose floor.

**One spine and one method document disagree about when the most expensive gate fires.**

**Resolution (decided 2026-09-14):** the **cause** arms it — two consecutive fix-induced rounds in
one component. The **count obliges asking**: on reaching four rounds, the coordinator must answer
*thrashing or prose floor?* in the round document, with per-finding evidence. It does not fire.

`dev-process.md`'s row 6 trigger is rewritten to point at the thrashing/prose-floor table rather than
restating it — a second copy of a rule is a copy that drifts, and this repo has a script hunting that
shape.

---

## What this does not do — stated, not implied

- **It does not make `aim` or `fix_induced` mechanical.** Both are judgements. The script consumes
  them; it cannot derive them. If they are recorded dishonestly the procedure produces confident
  wrong answers, and nothing detects that.
- **It does not remove the human from merging.** Merging stays a human gate.
- **It does not change the concurrency safety table** (`:171`, `:187`) — what may run at once and
  what must be serialised is untouched.
- **It does not touch the record.** Historical review documents keep the vocabulary they were
  written with.

## How we would know it failed

- A branch runs a round that the card's Q4(a) would have stopped → the card is being recalled, not
  read. **The fix then is not better prose; it is making `check-review-decision.py` a step nobody
  can skip.**
- A round document is filed with no header, and the script exits 2 rather than passing → working as
  designed. A header filled in with everything marked `deliverable` to force more rounds, or
  everything `instrument` to force a stop, is the failure the script cannot see.
- Two consecutive fix-induced rounds occur and no architecture review is convened → §5's arming
  condition is being ignored, and the count that used to catch it is gone.

## Sizing

| Piece | Cost |
|---|---|
| §1 the card + §5 the contradiction | small — one new section, one rewritten table row |
| §4 the rename | small, but touches many files; the grep for machine dependencies is the real work |
| §2 the header | small — a convention plus its documentation |
| §3 the script | **~1h**, nearly all ratchet compliance, by backlog #115's measured sizing of a comparable guard |

⟳ **CORRECTED 2026-09-14 — the budget claim above was wrong, and the real constraint is elsewhere.**
`check-docs.py:191` budgets exactly two files, and `review-method.md` is **not** one of them:

```
docs/dev-process.md : 220 / 220  ok
docs/plugins.md     : 260 / 260  ok
```

So §1's card is unconstrained. ⛔ **But `dev-process.md` is AT its budget — 220/220 — so §5's edit
must be line-neutral or shorter.** A one-line addition there fails CI. The trigger row is therefore
*rewritten in place to point at the thrashing/prose-floor table*, never expanded.

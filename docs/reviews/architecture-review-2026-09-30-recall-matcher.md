# Architecture review — the LLM recall matcher (backlog #191)

**Anchor:** `review-decides-itself` — a review loop decides its own next step from recorded evidence
rather than recall.

**Subject:** `scripts/recall-llm.py` (2204 lines), `scripts/begin-plan.py` (1024),
`.claude/hooks/surface-recall.sh` (78), branch `semantic-recall-replication`, 22 commits off
`master` at `446025ab`. Tree clean, pushed, no PR.

**Convened on judgement, not by arming.** `docs/dev-process.md:108` requires two consecutive
fix-caused rounds in ONE component; `docs/reviews/claude/recall-llm-r2-convergence.md` records that
neither half of that condition is met. The user directed this review in their own words on
2026-09-30 (*"next session will start architecture review"*), and that directive — not the arming
rule — is why it ran.

**State of the gates at the reviewed tree:** `--self-test` 185/185 rc=0 · `check-anchors` rc=0 ·
`check-docs` rc=0 · `check-ratchet-contract` rc=0 · `check-review-rounds` rc=0, 0 silent gaps ·
`scripts/mutations/recall-llm.json` 91 entries, matching `EXPECTED_MUTATIONS` at
`check-plan-code.py:1346`.

---

## The question, and why it was mis-aimed

The handoff posed: *"should the rc contract be enforced at a single boundary, rather than at every
raise site?"*

**That fix is already in place.** `Refusal` subclasses each carry their own `rc`
(`recall-llm.py:126-170`), and the class docstring states the guarantee: *"There is deliberately no
handler anywhere in this file that turns one into a success — `main` prints it and returns
`exc.rc`."* The rc contract has exactly one boundary and it holds.

**What has no owner is CONSULTATION**, and the file says so about itself
(`recall-llm.py:34-46`):

> `⭐ STRUCTURE: EVERY DECISION IS A PURE FUNCTION; THE REST IS PLUMBING.`
>
> `⚠ WHAT IS NOT COVERED BY A CASE, stated rather than implied. […] The IO assembly under it —`
> `read_armed_plan, read_corpus, prepared_prompt, do_arm, do_fire — holds no rule of its own, but`
> `it does hold the WIRING, and a covered predicate with miswired branches is a defect this`
> `repository has measured repeatedly. That wiring was verified by RUNNING it, 2026-09-29 […]`
> `Execution, not a case.`

So the organising principle puts every decision behind a pure function with a case and a mutation
entry each, and designates the region that carries the wiring as *plumbing*. Two review rounds then
found the overwhelming majority of their Blocking and High findings in the wiring. **The risk was
predicted correctly, in writing, and the mitigation chosen was a dated manual run** — real
verification that does not re-run. By this repo's own gate doctrine that is a decision wearing a
checkbox.

⭐ **The architectural answer is therefore neither a sixth consultation nor a new rc boundary. It is
that the seam has no owner a guard population can see** — see F6 and F7 below, which give the
mechanism the review rounds never identified.

---

## Findings verified by hand

Every claim below was re-derived against the tree. Where a number is stated, the command that
produced it is named. Findings sourced from `Explore` agents are in the next section and marked
with their verification status, because agent output is a lead and not a finding.

### F1 · The matcher has no falsifier at its own call site — a false negative is silent by construction

The rc contract distinguishes *cannot-run* (2) from *nothing-fires* (0) deliberately and at length,
under the heading `⛔ FAIL CLOSED — "nothing fires" AND "could not look" MUST NOT LOOK THE SAME`
(`recall-llm.py:67`). There is **no** third distinction between *nothing fires, correctly* and
*something should have fired and did not*.

This is not a hypothetical gap, because `NONE` is frequently the CORRECT answer. The shipped rubric
(`recall-llm.py --print-prompt`, verbatim):

> `* If the person is ALREADY DOING what the lesson advises, the answer is NONE. A lesson the`
> `action already embodies changes nothing`
> `* The test is: WOULD THIS CHANGE WHAT THE PERSON DOES NEXT?`

Measured live during this review: arming the review's own 5-step plan produced
`0 of 5 step(s) matched an entry` over a 146-entry corpus, and inspection of the plan shows each
step's `Why:` line already states its lesson — so `NONE` is very likely right. **That is exactly
the problem: a correct all-NONE run and a totally broken matcher are the same observation at the
call site.** The population that most needs recall — an author who does not know the lesson, and so
does not write the Why — is precisely the population whose output nobody can grade.

⚠ The 20/20 validation is a fixture outside the live path (`scripts/fixtures/recall-replication-2026-09-29.json`).
Nothing observes quality in production.

**Falsifier for this finding:** it is wrong if some mechanism records, for any live firing, an
independent judgement of whether a match should have occurred. None was found.

### F2 · "87 committed plans" is asserted in four sites across two files, measures 93/96 today, and no guard owns it

| site | text |
|---|---|
| `scripts/recall-llm.py:88` | `87 committed plans under docs/superpowers/plans/ are in the unreadable shape today.` |
| `scripts/recall-llm.py:158` | `87 committed plans under docs/superpowers/plans/ are in that shape today.` |
| `scripts/recall-llm.py:1785` | `begin-plan.py's own parser accepts — and 87 committed plans use —` |
| `.claude/hooks/surface-recall.sh` (rc=5 comment) | `87 committed plans are in that shape` |

Measured against the exact `_BOX_RE` (`^- \[([ x])\] \*\*Step (\d+) of \d+\*\*(?:\s*—\s*(.*))?$`,
`re.M`) over `docs/superpowers/plans/*.md`, all 96 of which are tracked by git:

| | count |
|---|---|
| total plan files | 96 |
| readable by the strict `_BOX_RE` | **0** |
| checkboxes present but only loose → the rc=5 population | **93** |
| no checkboxes at all | 3 |

Plan files were added after the number was written (`git log --diff-filter=A --since=2026-09-01 --
docs/superpowers/plans/` is non-empty), so the corpus moved underneath it. No guard reads the
number. `CONTEXT.md`'s own precedent for this exact situation is to **remove** such a figure rather
than correct it: *"The number is removed rather than corrected — it had no owner, and this file is
inside the corpus it describes."*

**Fix shape:** delete the literal from all four sites and name the command instead, or give it a
producer. Correcting `87` to `93` re-creates the defect on the next commit.

### F3 · `CONTEXT.md` carries no vocabulary for this subsystem — and the two prior architecture reviews facing this same symptom both answered it with vocabulary

Measured over `CONTEXT.md`, substring-checked (`grep -oi '[a-z]*arm[a-z]*'` returns exactly one hit,
inside the word *harmless*, so a naive `grep -ic arm` reporting 1 is a false positive):

| term | occurrences |
|---|---|
| `recall` | 0 |
| `arm` / `fire` | 0 / 0 |
| `plan verdict` | 0 |
| `memory entry` / `situation` / `rubric` | 0 / 0 / 0 |

The `cache` (10), `trigger` (2) and `corpus` (1) hits all belong to the mutation harness or to that
file's own self-description, not to this subsystem.

⭐ **The precedent is recorded in `CONTEXT.md` itself.** Its *Verification Stack (Repo Tooling)*
section says:

> `Added 2026-09-03 by Architecture Review #7, which found that seven consecutive review rounds had`
> `been argued in words this file did not contain: with no shared terms, each round could only name`
> `the instance in front of it, and the same defect kept recurring in a sibling.`

And its *Page Generation* section was added the same way. **That is this fold's shape verbatim** —
the same defect recurring in a sibling across rounds, each round able to name only the instance in
front of it. Two previous reviews diagnosed this symptom and both prescribed vocabulary; this
subsystem shipped with none.

### F4 · No roadmap row for 22 commits, a 2204-line script and a live registered hook

`grep -i 'recall-llm\|semantic-recall\|recall matcher'` over `docs/roadmap-to-launch.md` returns
zero hits for this work. `docs/dev-process.md` requires three layers kept in sync — roadmap, task
list, SDD ledger — and states *"A discovered step … goes into the roadmap and the task list in the
same turn."* Backlog row #191 carries the work in detail; the roadmap layer has nothing.

⚠ Related namespace hazard, measured: `PR #191` and `backlog #191` are **different things** and both
appear in `docs/` (`roadmap-to-launch.md:1674`, `dashboard-entries.md:1421` refer to the PR).
`check-backlog-closure.py` already keys on `(backlog #N)` at the subject tail for this reason, so
the guard is aware of the collision and the prose is not.

### F5 · The newest dashboard entry is stale in three ways and still poses a decision the user answered

`docs/dashboard-entries.md:13072` (`## 2026-09-30 [needs-you]`) states **"18 commits"** (git says
22), **"unmerged and unpushed"** (`HEAD` equals `origin/semantic-recall-replication` at
`d26c79d6`), and closes with *"Decide: the next session opens with an architecture review of this.
Is that what you want?"* — which the user answered in their own words the same day.

This is `an-escalation-has-no-closer` in the live repo: nothing closes a `[needs-you]` when the
answer arrives in conversation, so the stale entry outlived its resolution and then contradicted the
handoff that superseded it.

### F6 · The guard population is keyed by FILENAME, so this subsystem inherits none of rules R1–R3 — and its caller is protected by nothing

`scripts/check-ratchet-contract.py:113`:

```python
GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")
```

Run live: `guards discovered (41)`, and `recall-llm.py` appears **0 times** in the output. So rules
R1 (has a `--self-test`), R2 (no fail-open handler) and R3 (**has a caller**) do not apply to it.

The hook states this about itself, correctly and unprompted (`.claude/hooks/surface-recall.sh:6-16`):

> `⛔ M2 — AND THIS COMMENT USED TO CLAIM check-ratchet-contract.py REFUSES A CALLER-LESS GUARD,`
> `WHICH IS FALSE OF THIS FILE. […] So deleting this hook and its .claude/settings.json entry would`
> `leave that gate green. The caller exists by design, not by enforcement, and nothing currently`
> `protects it`

⚠ **Stated precisely:** the subsystem IS inside the mutation-ratchet population —
`EXPECTED_MUTATIONS["scripts/recall-llm.py"] = 91` (`check-plan-code.py:1346`) and the manifest
holds 91 entries, verified equal. The gap is specific to the R1–R3 family, which is the family that
would protect the caller.

### F7 · The code/hook seam has all of its coverage on one side

`.claude/hooks/surface-recall.sh` is 78 lines of rc-interpretation logic, registered at
`.claude/settings.json:57`, and is the matcher's only caller. Measured:

| | result |
|---|---|
| mutation manifests targeting the hook | **none** (`grep -rl surface-recall scripts/mutations/`) |
| scripts or workflows reading the hook | **none** (`grep -rln surface-recall scripts/ .github/`) |
| self-test cases driving the hook end to end | **0** (`grep -n surface-recall scripts/recall-llm.py`) |
| self-test cases driving a real armed world | 6 (`_armed_world`, `recall-llm.py:1898`) |

The 6 end-to-end cases were added *in response to* round 2's Blocking — the coverage arrived after
the defect, which is the point. Nothing reconciles the two halves of the rc contract: the matcher
can emit `{0,2,3,4,5}` and the hook distinguishes `0`, `3`, `5`, with `2` and `4` falling into a
catch-all. Round 1's H4 was exactly a cross-file literal defect at this seam, found by review rather
than by a gate.

⚠ **Latent, not live:** the swallowing of rc=4 is harmless *today* only because `--fire` cannot emit
it — every `ResponseRejected` raise site (`recall-llm.py:520,552,558,573,579,582`) sits inside
`parse_response`, which only `--arm` calls. Nothing asserts that property, and it lives on the far
side of the seam from the code that depends on it. Filed at that weight deliberately.

### F8 · The measurement that convened this review does not reproduce — and its real defect is that one judge's classification was quoted as a measurement

The handoff and `docs/dashboard-entries.md:13072` both state **"15 of 19 at a seam (78%)"**.
Re-derived from the four filed halves by their own finding-level headings:

| half | Blocking | High | how counted |
|---|---|---|---|
| `claude/recall-llm-r1-claude.md` | 1 | 4 | `### B1`, `### H1`–`H4` |
| `codex/recall-llm-r1-codex.md` | 0 | 3 | findings 1–3 labelled High; 4 Medium, 5 Low |
| `claude/recall-llm-r2-claude.md` | 1 | 5 | `### B1`, `### H1`–`H5` |
| `codex/recall-llm-r2-codex.md` | 0 | 2 | findings 1–2 High; 3–4 Medium |
| **total** | **2** | **14** | **16** |

**19 does not reproduce.** The measured Blocking+High total is **16**, or 17 counting the
run-discovered hook-inheritance defect that no half filed.

⛔ **The arithmetic is the lesser half of this finding.** The seam/in-function split was produced by
a single classifier — the same session that then quoted it as the justification for convening an
architecture review. My own independent pass puts 13–14 of the 16 at seams (81–88%), which is
*higher*, and which is worth no more than 78% was: **a one-judge classification is not a
measurement, and correcting the denominator while keeping the method would ship the same defect with
better arithmetic.**

⚠ **The conclusion is unaffected and stands.** Whether the share is 78%, 88% or 94%, the seam
concentration is overwhelming and an architecture review was the right instrument. What needs
repair is the number's provenance, not the decision it supported.

---

## Leads from the Explore agents

Three read-only `Explore` agents were dispatched with explicit refutation mandates, on the measured
grounds that a refuting brief outperforms a confirming one and that verification/research agents are
the gap where that had not been applied:

| agent | brief |
|---|---|
| `refute-consultation-gap` | enumerate every decision function → every call site; answer per-instance whether the proposed repair would have prevented each defect |
| `refute-shallow-modules` | apply the deletion test to every pure function; test whether the mutation harness depends on the structure |
| `refute-protocol-seam` | locate the owner of each of the four protocol parts; verify the 87 number independently |

⛔ **ALL THREE ARE TO BE TREATED AS NOT RUN.** Each went `idle` without delivering a report, and an
explicit resend request to each — sent by `SendMessage`, naming the exact format wanted — went
unanswered. **Nothing in this document rests on them**; every finding above was produced by the
coordinator running the code, with the producing command recorded in the finding.

### F9 · Phase 6's mandated exploration step has a measured ~1-in-4 in-time delivery rate in this repo, and its known remedy has now failed twice

This is a finding about the review process, surfaced by this review's own conduct. Measured over
every architecture review in `docs/reviews/`:

| review | `Explore` outcome |
|---|---|
| `2026-07-30` | returned in time. *"Explorer claims were mostly right, but I dropped and corrected claims on both sides — including one where my own check was the thing that was wrong."* |
| `2026-09-22-observer-family` | **3 dispatched, none returned** before §1–§6 were written; one delivered later and produced F13–F15 as leads |
| `2026-09-23-review-verdict-path` | returned **after** the document was committed and pushed |
| `2026-09-24-number-populations` | none dispatched; every claim established by hand |
| `2026-09-30` (this) | **3 dispatched, none returned; resend request unanswered** |

⭐ **The mechanism is already recorded** (`architecture-review-2026-09-22-observer-family.md` §4.5):

> `None returned before §1–§6 were written, and a partial-results request to each went unanswered;`
> `the agent later reported its replies had been plain text that never routed.`

**So the remedy of asking for partial results has now failed twice, for a recorded reason.** An
`Explore` agent's final message is plain text, and plain text does not route back to the
coordinator; only an explicit `SendMessage` from the agent would, and nothing in the brief compels
one.

⚠ **The consequence for the process is the finding, not the flakiness.** `improve-codebase-architecture`
presents agent exploration as step 1 of its method, and dev-process.md's Phase 6 row inherits that.
Measured, the exploration step informed 1 of the 4 reviews that attempted it, while **every** review
reached its verdict by the coordinator running the code. **Hand verification is not the backstop
here — it is the method**, and the agent step is enrichment that must be declared NOT RUN when it
does not arrive rather than silently waited on.

**Fix shape:** brief every dispatched agent to deliver via `SendMessage` explicitly, and give the
review a stated evidence bound either way. Do not make a Phase 6 verdict wait on it.

---

## Adjacent observation — OUT of this review's subject, recorded so it is not lost

`scripts/check-arch-findings.py` is described in `docs/dev-process.md` as *"ratchet on
architecture-review findings"*. Run live, its report is headed `(2026-07-30 baseline)` and its
criteria doc opens *"Companion to architecture-review-2026-07-30.md"* — its probes are hardcoded
`glob_files()` patterns over `lib/`, `app/` and `tests/`. **It is correctly scoped to one review**;
the pointer row simply reads broader than the script is. The substantive version: the findings of
the twelve architecture reviews since 2026-07-30 are tracked by `docs/backlog.md` and
`check-backlog-closure.py`, which is **warn-only by #56's measured verdict**. Not pursued here
because it is not this subject.

---

## What does NOT arm, and is recorded so it is not re-derived

- **The thrashing condition still does not fire.** This review does not change that; it was run on
  the user's direction. `docs/reviews/claude/recall-llm-r2-convergence.md` holds the per-finding
  evidence.
- **Convergence is unchanged: NOT CONVERGED.** Round 2 found 1 Blocking and 5 High, and its fixes
  are unreviewed. This review is a design gate and does not substitute for a defect round — see
  `gates-detect-defects-not-design`.
- **No PR.** A PR asserts readiness for the human gate and this work is not converged.

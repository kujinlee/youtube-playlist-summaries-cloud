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

⛔ **THE ANSWER THIS SECTION FIRST GAVE WAS "CONSULTATION HAS NO OWNER", AND IT IS REFUTED. It is
kept below, struck through in words rather than deleted, because it was published and pushed and a
reader who saw it needs to meet the correction at the same place.** The refutation came from the
three `Explore` agents this review had dispatched with a mandate to destroy its own hypothesis, and
they delivered AFTER this document was first committed — see F9, which is corrected for the same
reason.

**What they measured, and what I then re-derived by AST rather than relaying:** every verdict
function in `recall-llm.py` is consulted at every production call site. The claim's own pattern
needs a function with N≥2 sites where one ignores it; five functions have N≥2 (`plan_verdict`,
`should_surface`, `read_or_refuse` 4, `memory_dir`, `plan_steps` 3) and **all are consulted**. The
single surviving instance is `decode_verdict`, whose rc is discarded at its only call site
(`:354`, `raise refusal(decode_verdict(...)[1])`) — and that rc is a CONSTANT there, so it is
latent and was filed as a round-2 Medium. Route C is decisive: of the six defects the framing was
built on, the proposed repair would have prevented **at most one**, and for three the precondition
is false because no decision function existed when the defect shipped. What actually closed four of
them was **boundary relocation**, which the file has already done.

⭐ **THE CORRECTED VERDICT — and it predicts where the live defects are, which the refuted one did
not:**

> **The rc contract spans TWO LANGUAGES, nothing reconciles the codes the matcher emits against the
> codes the hook handles, and `rc=2` carries a conjunction in its meaning.**

⟳ **THAT SENTENCE WAS TRUE OF THE REVIEWED TREE AND IS NOW PARTLY STALE — round 3 L1, raised by
the Codex half.** `scripts/check-rc-contract.py` exists on this branch and CI runs it, so the
honest current claim is *"a reconciliation guard exists, and it was shape-fragile"* rather than
*"nothing reconciles"*. ⚠ Round 3 then found that guard reading only two-space-indented arms
(M1) and the `rc=2` conjunction still alive on the `--arm` path (H1) — so the verdict's DIAGNOSIS
held while its "nothing" became wrong, which is the distinction worth keeping rather than
smoothing over. Both are fixed; see backlog #201/#202 and the round-3 documents.

Both live defects found after this document was written (L1 and L2 below, backlog #201 and #202) are
instances of that one sentence. `rc=2` means *nothing is armed* — routine, correctly silent — AND
*armed but the corpus is unreachable*, which the reader needs to hear. That is exactly the
conflation B1 fixed by splitting rc=5 out of rc=2 **for the plan side**; every round then looked at
the plan side, and nobody looked at the corpus side. ⚠ This repo already owns the principle —
`check-sentinel-meanings.py` enforces *"every nullable column means exactly ONE thing; a conjunction
in the meaning is the tell"* — but its subject is database columns, so no guard applies it to rc
codes.

~~**What has no owner is CONSULTATION**~~ (refuted above), and the file says this about itself
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

⭐ **The architectural answer has two halves, and only one of them was in the first version of this
document.** The half that stood: **the seam has no owner a guard population can see** — F6 and F7
below, whose measurements are unaffected by the refutation and give the mechanism the review rounds
never identified. ⟳ **The half that was WRONG: this said the answer is "neither a sixth consultation
nor a new rc BOUNDARY".** The boundary half is false. `rc=2` carries a conjunction, and L2's repair
IS a contract change — a sixth code, or rc=5 widened to mean *armed and unanswerable* whatever the
cause. What the sentence got right is that a sixth CONSULTATION was never the answer; what it got
wrong is ruling out the contract, which is where one of the two live defects actually lives.

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

⟳ **THIS PARAGRAPH SAID "ALL THREE ARE TO BE TREATED AS NOT RUN", AND IT IS NOW FALSE.** All three
delivered, roughly forty minutes after this document was first committed and pushed — the same
shape `architecture-review-2026-09-23-review-verdict-path.md` records ("*returned AFTER this
document was first committed*"), which makes this the second instance rather than a surprise. The
original sentence is corrected rather than rewritten away, because a claim about how a review was
conducted is exactly the kind that gets believed without checking.

⭐ **AND THEY REFUTED THIS DOCUMENT'S PRIMARY VERDICT**, which is the strongest available argument
for the refutation mandate they were briefed with: a confirming brief finds six supporting instances
and stops, which is what my own reading of the same evidence did. The measured corrections they
produced are folded into the question section above, into F8, and into backlog #201–#205.

⚠ **WHAT STILL RESTS ON THE COORDINATOR, stated so the boundary is legible:** every finding in this
document was produced or re-derived by hand with its command recorded, including each claim the
agents made. That was not ceremony — **three of their summary lines were wrong while their data was
right**: one said only two functions have N≥2 call sites (five do, in its own table), one said a
mutation's green "says nothing about any reachable path" (manifest entry #60 names the reachable
case), and one said `cache_document` has two statements (it has one). Phase 6's *agent output is a
lead, not a finding* earned its keep in both directions here.

### F9 · Phase 6's mandated exploration step has a measured ~1-in-4 in-time delivery rate in this repo, and its known remedy has now failed twice

This is a finding about the review process, surfaced by this review's own conduct. Measured over
every architecture review in `docs/reviews/`:

| review | `Explore` outcome |
|---|---|
| `2026-07-30` | returned in time. *"Explorer claims were mostly right, but I dropped and corrected claims on both sides — including one where my own check was the thing that was wrong."* |
| `2026-09-22-observer-family` | **3 dispatched, none returned** before §1–§6 were written; one delivered later and produced F13–F15 as leads |
| `2026-09-23-review-verdict-path` | returned **after** the document was committed and pushed |
| `2026-09-24-number-populations` | none dispatched; every claim established by hand |
| `2026-09-30` (this) | 3 dispatched; resend request unanswered; **all three delivered ~40 min after this document was committed**, and refuted its primary verdict |

⭐ **The mechanism is already recorded** (`architecture-review-2026-09-22-observer-family.md` §4.5):

> `None returned before §1–§6 were written, and a partial-results request to each went unanswered;`
> `the agent later reported its replies had been plain text that never routed.`

**So the remedy of asking for partial results has now failed twice, for a recorded reason.** An
`Explore` agent's final message is plain text, and plain text does not route back to the
coordinator; only an explicit `SendMessage` from the agent would, and nothing in the brief compels
one.

⟳ **AND THE FINDING ITSELF IS CORRECTED, because this review's own agents then delivered.** The
first version read as *they often never arrive*. Measured across all four attempts, the truth is
sharper and more useful:

> **The exploration step has NEVER failed to deliver entirely. It has failed to deliver IN TIME in
> 3 of 4 attempts** — and in two of those three, what arrived late CHANGED the review: F13–F15 in
> 2026-09-22, two corrections in 2026-09-23, and this review's entire primary verdict.

⚠ **That inverts the fix.** "Make the agents deliver" is the wrong repair for a step that always
delivers eventually; the repair is to stop treating a Phase 6 verdict as final at the moment the
document is first committed. The cost of the old framing is visible in this very document: it was
committed AND PUSHED with a headline verdict that its own commissioned agents refuted forty minutes
later, and a reader in that window got the wrong diagnosis of a subsystem with two live defects.

**Fix shape, revised:** (1) brief every dispatched agent to deliver by `SendMessage` explicitly,
since a plain final message does not route and that mechanism is now recorded three times;
(2) do not block the verdict on delivery — but mark the document's verdict section as PROVISIONAL
until every dispatched agent has reported or been timed out, so a late refutation lands as an
expected revision rather than a correction to something already believed. ⚠ The old fix shape said
to declare the step NOT RUN when it does not arrive; that was written from a sample in which
nothing had yet arrived late, and it is the wrong instruction for the measured distribution.

⚠ **Also measured: the remedy of asking for partial results has failed TWICE** (2026-09-22 and
here), for the recorded reason — an `Explore` agent's final message is plain text, and plain text
does not route to the coordinator.

---

## Findings the agents produced, re-derived here by execution

Added after the first commit of this document. Each was reproduced by the coordinator in a built
world, and each states the control that makes the reproduction mean anything.

### L1 · A repeated `rc=5` forwards a permanently hollowed-out message — backlog #201, LIVE

`do_fire` empties the message when its dedupe says the sentence has already been said
(`recall-llm.py:991`):

```python
raise type(exc)("") from exc.__cause__
```

The hook's arms are not symmetric. `0)` and `3)` guard on `[ -n "$OUT" ]`; `5)` does not:

```
.claude/hooks/surface-recall.sh:59   0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;
.claude/hooks/surface-recall.sh:63   3) [ -n "$OUT" ] && PAYLOAD="recall-llm: the recall cache …
.claude/hooks/surface-recall.sh:70   5) PAYLOAD="recall-llm: a plan IS armed and the matcher …
```

**Reproduced end to end** — a sandbox at a resolved temp root, `recall-llm.py` and the real hook
copied in, `HOME` redirected to a fake corpus, an armed plan in the loose-checkbox shape, and the
HOOK as the only caller (⚠ a first attempt failed because the probe's own `--fire` consumed the
dedupe, so "call 1" was already deduped):

| hook call | forwarded | `Detail:` |
|---|---|---|
| 1 | 409 chars | the full 261-char diagnostic |
| 2 | 148 chars | **empty** |
| 3 | 148 chars | **empty** |

The marker persists, so it never recovers: from the second firing onward the reader is told *"a plan
IS armed and the matcher cannot read it … Detail:"* with nothing after it, indefinitely. Worse than
no dedupe — no dedupe repeats a USEFUL message; this repeats a useless one.

⛔ **THE REPAIR IS A DESIGN DECISION, NOT THE OBVIOUS ONE-LINER.** Adding `[ -n "$OUT" ] &&` to the
`5)` arm makes a deduped rc-5 SILENT, and the hook's own comment insists *"rc=5 IS NOT SILENCE"*
because that conflation was B1. So the question is whether the dedupe should apply to an unreadable
plan at all, or whether the hook should drop the `Detail:` label when there is nothing to put after
it. **FALSIFIER:** this is wrong if a second firing forwards a populated `Detail:`.

### L2 · An armed plan with a valid cache and a vanished corpus reaches the reader as SILENCE — backlog #202, LIVE

`cached_entry_verdict` returns `CANNOT_RUN` when the corpus is unreachable
(`recall-llm.py:718-720`), raised at `:1027`; the hook's catch-all then eats it, correctly, because
`rc=2` is also the routine "nothing is armed" state (`surface-recall.sh:72`).

**Reproduced over a GREEN control** — cache written with the module's own `plan_fingerprint`, plan
readable, named entry present, and ONLY `HOME` changed between the two runs. ⚠ A first attempt had a
RED control (it reported "corpus unreachable" with the corpus present, because `memory_dir` uses
`ROOT.resolve()` and macOS `/var/folders` resolves to `/private/var/folders`, so the slug was
computed from the wrong path); nothing below a red control counts.

| run | matcher | hook forwards |
|---|---|---|
| CONTROL — corpus present | rc=0, surfaces the entry | **290 bytes** |
| TEST — only `HOME` changed | rc=2, a 161-char message ending *"NOTHING WAS SURFACED"* | **0 bytes** |

⭐ **THIS IS B1's DEFECT ONE SIDE OVER.** B1 was *"nothing fires" and "could not look" arriving as
one observation*, and it was fixed by splitting rc=5 out of rc=2 **for the plan side**. Every
subsequent round looked at the plan side. `rc=2` still means two things, and the corpus side is the
half nobody examined. **FALSIFIER:** wrong if the hook forwards anything for that run.

⚠ **ITS TRIGGER EXISTS ON THIS MACHINE RIGHT NOW, and I created it.** `memory_dir` slugs the repo
path, and its docstring claims *"Derived, never hardcoded, so a worktree or a clone at another path
still finds its own corpus."* Measured: the main checkout's slug has a corpus, and the worktree
created at `~/code/agentic-ai-docs/yps-memory` on 2026-09-30 has **none**. The derivation is
correct; the premise that each path HAS a corpus is false, because nothing creates one for a new
slug. See S2.

### S1 · `recall-llm.py` holds a second copy of a rule whose owner forbids copies — backlog #203

`check-plan-progress.py:127-128`, in `strip_field`'s docstring, states the rule:

> `So the predicate below is parse_sentinel's own rule applied per line, and nothing else may hold`
> `a second copy of it — begin-plan.py borrows this function rather than writing its own.`

`begin-plan.py` obeys — it imports `parse_sentinel` (`:276`) behind an `ImportError` guard that
names the borrowed symbols (`:111-115`). `recall-llm.py:187` does not:

```python
_PAUSED_RE = re.compile(r"^paused:", re.M)
```

The owner splits on the first colon anywhere in the line and strips the key; this is line-anchored.
**Measured, both parsers on the same bytes — 3 of 6 inputs disagree:**

| sentinel line | owner | `recall-llm` |
|---|---|---|
| `paused: why` | paused | paused |
| `␠␠paused: why` | **paused** | **running** |
| `\tpaused: why` | **paused** | **running** |
| `paused : why` | **paused** | **running** |
| `Paused: why` | not paused | not paused |
| `paused` (no colon) | not paused | not paused |

On a divergent line the Stop guard stands the plan down while the matcher walks past the pause into
the step machinery and surfaces a lesson for a step the reader is not on.

⚠ **LATENT, and the reachability is the documented human path rather than a tool.**
`begin-plan.py:522` writes `paused:` at column 0, so nothing in the repo produces a divergent line —
but `parse_sentinel`'s own docstring says *"the file is also read by humans"*, and the Stop guard's
refusal message instructs a human to *"add a line `paused: <why>`"* by hand. `check-banner-armed.py`
records that exact route as already measured, which is why the other two copies adopted the
colon-split rule; `recall-llm.py` shipped after them and did not.
**FALSIFIER:** wrong if the two parsers agree on every input, or if a tool writes an indented pause.

### S2 · `memory_dir`'s docstring promises a capability it does not have — backlog #204

Quoted (`recall-llm.py:357-368`): *"Derived, never hardcoded, so a worktree or a clone at another
path still finds its own corpus."* Measured 2026-09-30:

| path | slug | corpus present? |
|---|---|---|
| main checkout | `-Users-…-youtube-playlist-summaries-cloud` | **yes** |
| worktree at `…/yps-memory` | `-Users-…-yps-memory` | **no** |

A worktree at another path finds NOTHING, because nothing creates a corpus for a new slug. The
derivation is right and the sentence's promise is not — this repo's *true about the name, silent
about the layer* shape. It is also L2's live trigger, and it is backlog #194's own defect in a new
form: that row records *"committing files into the repo does not make the harness find them; any
in-repo home needs a symlink or a bootstrap step."* It got the symlink, and the symlink inherited a
dependency on which branch is checked out. **FALSIFIER:** wrong if a bootstrap step creates the
corpus for a new slug — `scripts/bootstrap-memory.sh` exists and should be checked against this.

### S3 · `invocation_re` cannot see the form this repo uses to spawn a sibling — backlog #205

Not a defect in this subject, found while repairing #196 and recorded so it is not rediscovered.
`check-ratchet-contract.invocation_re` is lexical over an interpreter list, so it matches
`python3 x.py`, `./x.py`, `bash x.py`, `sh x.py` and nothing else. It misses
`[sys.executable, str(ROOT / "scripts" / "x.py")]`, which is how this repo actually spawns a
sibling from Python. Measured: `brief-compose.py` has three such production callers
(`gen-features-page.py:693`, `gen-backlog-page.py`, `gen-dashboard.py`) and its R3 green comes from
none of them — only `ci.yml:168`, its `--self-test` step. Delete that step and it reddens with three
live callers intact.
⚠ Wrong in ONE direction, the safe one (a false red on a used file), which is why it stays lexical
while `import_re` — wrong in BOTH — was retired. **FALSIFIER:** wrong if `invocation_re` matches a
`sys.executable` spawn.

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

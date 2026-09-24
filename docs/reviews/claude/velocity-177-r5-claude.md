# Claude adversarial review — velocity-177 r5

## Verdict

**NOT CONVERGED — CONTINUE.** Driven by **one Blocking that is mechanical, not editorial**: a
required CI gate is **red on the merge tree and green on `origin/master`**, and this branch caused
it. That alone decides the round; nothing below rests on prose preference.

| Sev | Finding | Aim |
|---|---|---|
| **Blocking** | `check-review-rounds.py` exits **1** on `41040ad8`, **0** on `origin/master`. `ci.yml:203` runs it unconditionally | deliverable |
| **High** | The shape invariant's **scope** is undecidable, and the two available readings give opposite verdicts on `review-method.md` | deliverable |
| **Medium** | The section's **preamble** is outside *"a rule's body"* and carries the one expression in the section that has actually rotted | deliverable |
| **Medium** | The invariant's **general clause is strictly wider than its own enumeration**; three expressions the rules need fall in the gap | deliverable |
| **Low** | *"FIVE consecutive attempts"* over an enumeration of four | deliverable |

⚠ **On de-escalation, which I was invited to recommend and am declining — with the reason stated.**
If B1 did not exist I would recommend STOP: H1/M1/M2 are one-clause edits to a file already in the
diff, and this repo records that a document can be right forever. But B1 is not a wording question —
it is a gate that reports `FAILED`, and *a red is a STOP*. **CONTINUE here means "fix and verify by
re-running the gate", not "convene round six over prose."** The four documentary findings should ride
in that same fix; none of them is worth a round of its own, and I say so explicitly so the
coordinator does not read five findings as five rounds' worth of discovery.

---

## Does the shape invariant hold?

**Split answer, and the split is the finding.**

> **YES** under its enumerated forms, over the five numbered rule bodies. **There is no link four.**
> **NO** under its general clause, and **NO** over the section's own preamble, which it does not reach.

**What I did.** Swept `docs/process-checklists.md:428-590` for every digit, number-word and
positional token —

```
awk 'NR>=428 && NR<=590' docs/process-checklists.md \
  | grep -nE '[0-9]|\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\b|\b(below|above)\b'
```

— **35 lines flagged**, and I read every one. That reproduces the section's own prediction at `:582`
(the sweep flags most of it) a third time: the hits are dates, PR and backlog ids, rule numbers, row
references, text quoted *as retracted*, the word *one* used as a pronoun, and historical facts about
past sessions. **Inside the five `###` rule bodies (`:454-589`), surviving expressions that assert a
current count or locator of repository contents: zero.** The four failed patterns each died because
the next instance wore a new spelling; nothing in the rule bodies wears one. **The invariant genuinely
differs in kind from the four patterns, and it is not itself link four.**

**But it holds by the narrow reading only, and the narrow reading is not the one the text states.**
Two clauses with different extensions sit in the same blockquote at `:571-573` — a general sentence
(*"It makes no claim about the repository's contents"*) and an enumeration (*"no count in digits or in
words, no `file:line` locator, no 'N lines below'"*). **The enumeration is the test that actually ran.**
The general sentence, applied, condemns three expressions the rules depend on (M2), and the heading
above it scopes the rule to *"these rules"* while its own body says *"a governing rule"* (H1).

So the honest verdict on the deciding question: **the terminating move is sound, and it was adopted
without being applied to its own section under its own widest wording.** That is a materially
different failure from the four before it — not *the pattern was too narrow again*, but *the rule was
never read back against itself* — which is exactly what a verifying round is for.

---

## Findings

### B1 (Blocking) — a required CI gate is red on the merge tree, and green on master

`scripts/check-review-rounds.py`, run on this branch at `41040ad8`:

```
FAILED — 3 review round(s) with one half and no stated reason:
  ✗ velocity-177 round 2: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
  ✗ velocity-177 round 3: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
  ✗ velocity-177 round 4: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
rc=1
```

Against a clean extract of `origin/master` (`git archive origin/master | tar -x -C /tmp/crrwt`):

```
review rounds: 336 parsed, 18 pre-existing exemptions, 0 silent gaps
rc=0
```

`.github/workflows/ci.yml:203` runs it as an unconditional step (`- name: Review rounds have both
halves`) in the required `verify` job. **This branch turns a green required check red.**

**Cause — two grammars for one concern.** The coordinator docs record their gaps *only* in the YAML
header, e.g. `docs/reviews/coordinator/velocity-177-r4-coordinator.md:9`:

```yaml
  claude: "GAP: not dispatched — rounds 2+ alternate to the half that did not author the fix; …"
```

That form is sanctioned by `docs/round-header-template.md:29` (*"`halves.<name>` | `ran`, or a string
starting `GAP:`"*), and the template's own example at `:17` is `claude: "GAP: this session spawns no
subagents"`. The gate reads a different grammar — `scripts/check-review-rounds.py:87`:

```python
r"^[*_>#\s-]*REVIEW GAP:[*_\s]*(codex|claude)\b[*_\s]*[—–-][*_\s]*(\S.*?)[*_\s]*$"
```

A line beginning `  claude:` cannot match: `c` is not in `[*_>#\s-]`, the marker is `GAP:` not
`REVIEW GAP:`, and the half name precedes the marker instead of following it. **The template and the
gate disagree about how a gap is written**, which is this repo's own *one mechanism per concern*
shape — `scripts/check-vocabulary-collisions.py` exists for it.

**Siblings — searched, and this is why I am confident the branch caused it.**
`grep -rn "REVIEW GAP:" docs/reviews/coordinator/` returns the prose form in every merged subject
that has a gap — `clickable-dashboard-asks-r2/r3/r4:3`, `harness-progress-r6:1`,
`seed-explainer-serve-manifest-r1`. `grep -n "GAP" docs/reviews/coordinator/review-identity-176-r*.md`
returns **nothing** (both halves ran every round there). **`velocity-177` is the only subject using
the YAML-only form, and the only one failing.**

**Fix (mechanical, and it must be verified by re-running the gate, not by reading):** add a
line-initial `REVIEW GAP: <half> — <reason>` to each of the three coordinator docs, carrying the same
reason the YAML already states. ⚠ **The template/gate divergence is the real defect and is a second
row's worth of work** — `round-header-template.md:29` teaches a form CI rejects, so the next author
walks into this too. That is a mechanism change and belongs in the backlog per Q3, not in this branch.

---

### H1 (High) — the invariant's scope is undecidable, and the two readings contradict each other

`docs/process-checklists.md:569` heads the passage **"The shape *these rules* keep"** — scope: rules
1–4. `:571` states it as **"*A governing rule's* body"** — scope: every governing rule in the repo.
A reader can take either, and they are not the same rule.

**Under the wide reading, measured this session, it condemns the sibling spine document.**
`docs/review-method.md` carries, all inside governing rule bodies:

- **12** bare intra-document locators of the form `` `:NNN` `` — `:173 :238 :277 :349 :352 :358 :372
  :391 :404 :415 :458 :503`, counted by `grep -oE '`:[0-9]+`' docs/review-method.md | wc -l`
  (population: backticked `:NNN` occurrences in that one file);
- **3** cross-file `file:line` locators — `begin-plan.py:518`, `sync-run.ts:380`, `worker/main.ts:69`
  (`grep -oE '[A-Za-z0-9_./-]+\.(py|ts|sh|md|yml|json):[0-9]+'`, deduplicated).

⛔ **And one of those rules positively requires what the invariant forbids.** `review-method.md:153-155`:

> **1. Quote the code you rely on; do not characterise it.** A design decision that depends on how
> existing code behaves **must paste the relevant lines, with a `file:line`**.

It then demonstrates with `worker/main.ts:69` in its own body (`:156-157`). Under the wide reading,
two spine rules contradict outright — one forbids the locator, the other mandates it.

**Under the narrow reading the invariant has no reach beyond this one section** — which makes backlog
#181 (*give the principle a name*) unable to do its job, since a named term inherits the undefined
scope and the first person to reach for it faces the same fork.

**This is mandate questions 2 and 3 answering together.** The **shape test** — *does this expression
have to track the repository to stay true?* — is decidable by reading; I applied it to 35 flagged
lines without ambiguity. The **scope term** is not. A rule whose test is decidable and whose subject
is not has only moved the judgement call.

**Fix:** one sentence stating the scope. If the intent is narrow, say *"these five rules"* and note
that dated review and rationale documents — and `review-method.md`'s own locator convention — are
outside it. If the intent is wide, `review-method.md:153` must be reconciled first, and that is a
separate decision, not a wording fix.

**Siblings — searched.** `grep -oE '[A-Za-z...]:[0-9]+'` over `docs/dev-process.md` (0 cross-file
locators) and `docs/plugins.md` (1: `session-start-hook.sh:795`). `review-method.md` is by far the
heaviest user and the only one containing a rule that mandates the form.

---

### M1 (Medium) — the preamble is ungoverned, and it holds the one expression that has actually rotted

`docs/process-checklists.md:452`:

> ⚠ **They are numbered 1, 1b, 2, 3, 4 — five of them.** An earlier version said *"all four"* and did
> not move when 1b was added (r3, Low): a count of the rules, inside the rules about counts.

A count, in digits **and** in words, of this file's own contents. It sits at `:452`, before
`### 1` at `:454` — **in the section preamble, not in any rule's body** — so the invariant, read
either way, does not reach it.

**The rot is measured, not hypothetical.** `docs/reviews/claude/velocity-177-r3-claude.md:153-157`
records the predecessor: *"All four rules below cost nothing to follow"* at this exact line, over five
`###` headings, stale because 1b was added in the r1 fold and the count above it was not.
⛔ **The r4 fold's repair was to re-pin the count** — the precise move the invariant exists to make
unavailable, applied to the one line the invariant cannot see. Add a rule 5 and it rots again, and
nothing in the section now forbids it.

**Siblings — searched.** The 35-line sweep above; I read all of them. This is the **only** surviving
count of repository contents anywhere in `:428-590`. Everything else is a date, an id, a rule number,
a quotation of retracted text, a pronoun, or a frozen historical fact.

**Fix:** remove the count rather than re-pin it — the sentence's job is to explain why the numbering
carries a `1b`, and it can do that without asserting how many rules there are. Either that, or state
that the invariant governs the whole section including its preamble (which is the H1 fix doing double
duty).

---

### M2 (Medium) — the general clause over-reaches its own enumeration, and three load-bearing expressions fall in the gap

Each of these is **verified true today**, is forbidden by *"makes no claim about the repository's
contents"*, is permitted by the three enumerated forms, and rots if its subject is edited:

| Site | Claim | Verified against |
|---|---|---|
| `:540-542` | verbatim quote of `check-merge-ready.py`'s `WORKFLOW` comment | `scripts/check-merge-ready.py:52-55` — faithful |
| `:561-562` | *"`scripts/check-schema-gates.sh`, which `ci.yml` **mentions only inside comments**"* | `.github/workflows/ci.yml:267` and `:286` — both comment lines, no `run:` invocation |
| `:526` | *"`review-method.md` §0 Q2 **step 5**"* | `docs/review-method.md:59` is item 5 and does say *every finding names a sample, not a scope* |

⚠ **This is the over-reach question answered concretely.** Forbidding these strips rule 4 of its best
evidence and rule 3 of its cross-reference; the repo's own `review-method.md:153` calls quoting-with-a-locator
a *requirement*, not a hazard. So the general clause cannot be the test. **The enumeration is what
actually governs, and the general sentence should be written as the enumeration's rationale rather
than as a wider rule sitting beside it** — otherwise the next author applying the invariant literally
deletes the section's evidence.

`:526` is the genuinely-both case the mandate asked about: a numbered position in another file
(a locator, which the invariant forbids) that is also a pointer to a producer-like named step (which
it permits). The invariant as written does not decide it.

**Siblings — searched.** Same 35-line sweep; these three are the complete set of live repository
assertions in rule bodies. `docs/development-velocity.md` — the r4 Codex half flagged a surviving
*"fifteen schema"* sibling there — is **clean now**: `grep -n "fifteen schema\|schema gates"` returns
nothing. And it would be permitted anyway: `:573` explicitly exempts *"review and rationale documents,
which are dated and expected to go stale"*, and that file's banner (`:1-14`) classes §1/§3/§4/§8 as
measurement and rationale.

---

### L1 (Low) — a count that does not match its own enumeration, in the paragraph that introduces the invariant

`:576-578`: *"**FIVE** consecutive attempts narrowed to the form just seen — bolded digits, then any
digits, then number-words, then **locators**."* Four named forms under a count of five. The source,
`docs/reviews/coordinator/velocity-177-r4-coordinator.md:29`, names five (`file:line` locators and
doc-relative positions kept separate), and backlog #181 names five the same way.

⚠ **Stated honestly: this is my weakest finding.** Reading *locators* as an umbrella for the last two
makes the sentence defensible, and attempts need not map 1:1 onto forms. I report it because the
class is rule 1b's own — *the label names a different population from what was counted* — and it is
in the paragraph that adopts the fix for that class. **It is not worth a round.**

---

## Backlog rows #179 / #180 / #181 — checked, and they hold

**Real and distinct, by reader and by moment**, which each row states rather than leaves implied:
#179 (ADR) is met at Phase 6, whose gate obliges reading `docs/adr/`; #180 (cross-reference) is met at
the moment the figure is typed; #181 (named term) is met when a round is arguing the class. Different
sites, different readers, no overlap.

**Falsifiers — all three carry one**, and each is an observation rather than a feeling: #179 *"a
future architecture review re-derives the principle from scratch, or a governing rule ships a new
pinned figure"*; #180 *"the section is edited and the pointer is not carried"*; #181 *"a later review
round argues this class in words `CONTEXT.md` does not contain."*

**No contradiction with `Qualify every number in prose`.** That section rejected a **syntactic guard**,
measured at three scopes (`:394-408`: 1,556 of 2,130 over all of `docs/`; 24 on one branch at ~90%
false positives). #179 says ⛔ **NOT A GUARD** in its own text; #180 proposes a cross-reference. Neither
re-proposes the rejected instrument.

⚠ **One filing-shape nit on #180, not a contradiction.** That same section closes at `:421-424` with
*"Widen the scope there rather than filing a second row"* — the instinct that a pointer-sized change
belongs inside the existing row rather than beside it. #180's work is literally *"one cross-reference
from that section"*, so it is arguably a widening. The row itself says it is the cheapest of the three
and to be done with or after #179, so nothing is lost either way; flagging it only so the choice is
deliberate.

**Roadmap steps match.** `docs/roadmap-to-launch.md:2098-2121` — the Phase 6 step is `[x]` and its
three follow-ups `[ ]`, matching the backlog statuses. `scripts/check-roadmap-consistency.py` → rc=0,
*"consistent with the checkboxes it summarises (2 tracked item(s) still open: A6, Q0)"*.

---

## What I checked and found clean

**Gates run on this tree** — every docs-scope gate, not a chosen subset:

| Gate | rc | Result |
|---|---|---|
| `check-docs.py` | 0 | *Documentation integrity OK* |
| `check-roadmap-consistency.py` | 0 | consistent |
| `check-anchors.py` | 0 | 13 registered, all claimed, floor 22 held |
| `check-dashboard-entry.py` | 0 | *ok — an entry block was added* |
| `check-backlog-closure.py` | 0 | WARN-only: #117, #159, #177 merged-without-✅ |
| `check-review-rounds.py` | **1** | **→ B1** |

⚠ The `check-backlog-closure` warning on **#177 is correct and expected** — the row is deliberately
🟠 **PARTLY ADOPTED** because Q0 is unbuilt, and the guard keys on the `(backlog #177)` subject tail
that every commit on this branch carries. Warn-only by backlog #56's measured verdict. Not a finding.

**The architecture review's load-bearing claims — verified by hand, not accepted.**

- *The decision exists and is dated 2026-09-21.* ✅ `CONTEXT.md:119` carries the quote verbatim:
  *"The number is **removed rather than corrected** — it had no owner, and this file is inside the
  corpus it describes, so any figure here is stale at the commit that writes it."*
- *It is in none of the ADR files.* ✅ `ls docs/adr/*.md` → 14 files, of which `README.md` is one:
  **13 numbered ADRs**, `0001`–`0013`, none on this subject. The r4 wording *"thirteen ADR files"* is
  correct for the numbered population.
- *It has two homes, and no process document points at either.* ✅ `docs/roadmap-to-launch.md:1984-1985`
  is the second home (*"A stale count in its preamble was removed rather than corrected: it had no
  owner, and the file sits inside the corpus it describes"*). r4's in-place correction of the
  review's original *"no process document points at it"* is the narrower claim and it survives:
  neither `process-checklists.md` nor `review-method.md` points at either home. Confirmed by grep.

**Rule 4 remains followable with its counts gone.** It names the population to read
(`.github/workflows/`, not `ci.yml` alone), the method (parse `run:` blocks, do not grep), and the
producer (`scripts/check-merge-ready.py`). Nothing was load-bearing that left with the digits — I
re-derived the `check-schema-gates.sh` comment-only fact myself from `ci.yml` and rule 4 told me how
to do it correctly without quoting a single number.

**Whole-branch coherence** — `git diff origin/master...HEAD` read in full. The dashboard entry at
`docs/dashboard-entries.md:12174-12234` matches the roadmap and backlog; its plain-language half makes
no claim the technical half contradicts; the append-only exception in rule 2 (`:507-509`) is respected.

---

## Out of scope, reported because it is a live instance of this branch's own class

`docs/dev-process.md:142` says *"one command for all **THIRTEEN** schema gates"* while `:163` says
*"the **fifteen** schema gates, in CI"* — the same population, two counts, in the spine document.
`scripts/check-schema-gates.sh` numbers its gates `n/15` (`grep -oE '[0-9]+/[0-9]+'` → `…5/15 6/15
7/15 8/15 9/15`), and `:148` of the same table records `check-paid-caller-arrival.py` becoming
*"gate 15"*, so **THIRTEEN is the stale one**.

⛔ **Pre-existing on master and NOT introduced here** — `docs/dev-process.md` does not appear in
`git diff --stat origin/master...HEAD`. **It is not a finding against this branch and must not block
it.** I report it because it is the exact defect this branch is about, sitting in the document most
likely to be cited, and because **#180's pointer would not reach it** — #180 points *from*
`process-checklists.md`, and this is in `dev-process.md`. That is a small piece of evidence for #179
(the ADR, read by Phase 6 regardless of which document the number lives in) being the strongest of the
three candidates.

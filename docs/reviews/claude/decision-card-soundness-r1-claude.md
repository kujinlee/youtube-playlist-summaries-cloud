# Claude adversarial review — decision-card-soundness r1

Subject: `docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md` (227 lines, as folded).
Read first: `docs/reviews/codex/decision-card-soundness-r1-codex.md` and
`docs/reviews/coordinator/decision-card-soundness-r1-coordinator.md`. Codex's coverage was numeric —
it reproduced the defect, the calibration and the registry rejection. This half attacks the **design**
and the **prior art**, and the findings below are where it did not go.

## Verdict

**NOT CONVERGED.** The measured defect is real and the mechanism is the right *shape*. But four
things fail at the design level, and each is the kind of gap a Phase 1 gate exists to catch:

1. the spec's **motivating causal claim is not supported by the record**, and the instrument it
   repairs **declares `NO-CALLER`** — a fact the document never states;
2. the calibration's **false-positive rate is materially understated** — measured, **2 of the 3
   refused subjects are ones where the unmodified trigger had already reached
   `ARCHITECTURE_REVIEW` on its own**;
3. **backlog #136 — the filed design task for exactly this defect, with a user-stated preferred
   direction — is absent from PRIOR ART and unaddressed in *Rejected***;
4. the escape hatch, after round 1's fold removed component names from it, is **not readable as
   specified**, and the most natural implementation makes it a **permanent suppression flag**.

None of these are reasons to abandon the design. All four are reasons a human should not approve
this document as it stands.

---

## Findings

### H1 — The failure this spec is justified by is not the failure the record shows, and the instrument it repairs has no caller

Lines 28–29 state the cause historically and in bold:

> **The branch ran four rounds where an architecture review was arguably owed after two, and the
> trigger was silenced by a choice of words rather than by the evidence.**

A trigger cannot be *silenced* if it was never pulled. `scripts/check-review-decision.py:27-31`
declares, in its own module docstring:

```
NO-CALLER: an instrument the coordinator consults at a decision point; CI has no decision to
make about whether to run a review round. Its protection is that `review-method.md`'s
decision card names running it as the step — which is precisely the protection that FAILED
on PR #302 when the step was prose. If it is skipped again, the remedy is not better prose;
it is making this a step nobody can skip.
```

**Measured.** `grep -rn "check-review-decision\|ARCHITECTURE_REVIEW\|thrashing"
docs/reviews/coordinator/velocity-doc-consistency-r*.md` returns **zero hits across all four
coordinator documents** — no record that the card was consulted on the subject this spec is built
on. The same grep over the whole review corpus returns 57 hits in 10 files, including
`docs/reviews/coordinator/peer-sites-r2-coordinator.md` and
`docs/reviews/coordinator/velocity-177-r2-coordinator.md`, and
`docs/reviews/architecture-review-2026-09-24-number-populations.md:3` opens *"Convened by THRASHING,
mechanically. `scripts/check-review-decision.py` returned `ARCHITECTURE_REVIEW — …`"*. So
coordinators **do** run it and **do** record running it — on other branches, in the same week.

Absence of a citation is not proof the card was never run, and I do not claim it was not. What I
claim is narrower and holds either way: **the spec does not distinguish *the card was run and
returned `None`* from *the card was not run*, and the two have different remedies.** If it was not
run, the mechanism this spec adds would equally not have run, and the four rounds happen again
unchanged. The script's own docstring already named that failure and already named the remedy —
*"making this a step nobody can skip"* — and this spec neither adopts it nor argues against it.

The document's *What this does not do* section (lines 144–157) is otherwise careful, and it does not
catch this: it lists six things the change does not do and **"it does not make the card run" is not
among them**, while *How we would know it failed* (line 167) says *"The check's call is removed →
backlog #56's outcome"* — a sentence that presupposes a call that does not exist. That is the
overclaim the section fails to catch (review brief Q7).

**Sibling search.** I grepped `NO-CALLER` across `scripts/` and read `check-ratchet-contract.py`'s
row in `docs/dev-process.md` (every guard needs a caller or a written `NO-CALLER:` reason). I also
grepped `.claude/`, `.github/` and `scripts/*.sh` for `check-review-decision` — **no hook, no CI
step, no shell caller**. This is the only no-caller instrument in the review-decision family; the
sibling scripts (`check-review-rounds.py`, `check-review-recorded.py`) are both invoked.

**What would fix it, as a spec change, not code:** state plainly that the subject is an
un-invoked advisory; say what the refusal is worth in that condition; and say whether this design
supersedes, defers or is orthogonal to the docstring's own stated remedy.

---

### H2 — The calibration understates the false-positive rate: on 2 of the 3 refused subjects the unmodified trigger had *already* reached the right answer

§3 (lines 122–136) reports **5 would-refuse**, of which **3 on `velocity-doc-consistency`** and
**"2 — `peer-sites` r4, `velocity-177` r2"** labelled *debatable*. I replayed the proposed condition
round-by-round alongside the shipped `thrashing_component`, over `rounds_for()`:

| subject | at r2 | at r3 | at r4 | at r5 |
|---|---|---|---|---|
| `peer-sites` | **FIRES `activation`** | **FIRES `activation`** | *REFUSE* | — |
| `velocity-177` | *REFUSE* | **FIRES `number-populations`** | **FIRES** | **FIRES** |
| `velocity-doc-consistency` | *REFUSE* | *REFUSE* | *REFUSE* | — |

Both "debatable" cases are worse than debatable on this evidence:

- **`peer-sites` r4 fires the refusal two rounds *after* the escalation was already raised.** The
  trigger fired at r2 and at r3 on `activation`; `docs/backlog.md:162` (#134) records exactly this —
  *"`check-review-decision.py` fired ARCHITECTURE_REVIEW — thrashing on the component twice, r1/r2
  and r2/r3"* — and records the outcome: the unstable component was split out. The r4 sets are
  non-intersecting **because the split worked**. The refusal fires on the signature of a
  successfully-handled thrashing episode.
- **`velocity-177` r2's refusal is answered one round later by the mechanism itself.** The trigger
  fires at r3 on `number-populations` and that firing produced a real, mechanically-convened
  architecture review (`docs/reviews/architecture-review-2026-09-24-number-populations.md:3-6`). At
  r2 the coordinator would instead owe a `COMPONENTS DISTINCT:` declaration over a **7 × 1 =
  7-pair cross-product** — for a verdict the unmodified card reached unaided at the next round.

So the honest reading of the calibration is not *"5 refusals, 3 good, 2 debatable"*. It is **3
subjects refused; on 2 of them the null hypothesis — change nothing — reached `ARCHITECTURE_REVIEW`
anyway**, and the refusal's contribution on those two is a declaration nobody needed. That is
precisely the information a human needs to judge precision, and §3 does not carry it. It is also the
same species as the High that Codex already found and the fold already corrected: **a population
claim presented without the members that argue against it.**

⚠ **This is a finding about the calibration's honesty, not a refutation of the design.** The
`velocity-doc-consistency` case survives intact, and one true positive in a corpus this small is not
nothing. But the design should then consider the obvious strengthening the spec never raises:
**do not refuse when `thrashing_component` fired on the previous pair** — the escalation is already
live, and re-asking the question as `CANNOT_RUN` cannot improve it. That single clause removes
`peer-sites` r4 and costs nothing measurable.

**Sibling search.** I ran the replay over **every** subject with parseable round records (8
subjects, 29 rounds), not just the three named, and inspected each of the 5 refusals against what the
shipped card answers at the same point. I then read every
`docs/reviews/architecture-review-*.md` opening to find which were thrashing-armed and on which
subject. No further refusals exist in the corpus, so the table above is the complete population.

---

### H3 — PRIOR ART omits backlog #136, the filed design task for this exact defect, and *Rejected* answers a different alternative than the one #136 names

`docs/backlog.md:164` (#136, 🟠, size **L**, *"design first, no code until a spec exists"*) contains:

> `thrashing_component()` (`scripts/check-review-decision.py:96-109`) is a set intersection over
> `component`, a **free-text label the author writes and nothing validates** beyond non-emptiness —
> measured on #313, relabelling one finding either way flips the verdict; it is **blind to a defect
> that MOVES** between components … **The partition should be derived from the file/symbol a finding
> names, removing author naming from the loop.**

That is this spec's subject, its measured defect (already measured once, on #313), and a
**user-stated preferred direction** — and the row carries a standing user instruction:
*"⛔ treat any proposal that makes a gate fire LESS with suspicion"*. The spec's PRIOR ART table
(lines 42–49) lists #167, #154, #56, `check-vocabulary-collisions.py`, `check-merge-ready`, and
`REVIEW GAP:`. **#136 is not there.** Nor are the three other open rows on this same script:
**#117** (the parser redesign its own armed architecture review demanded), **#118** (the exit-code
space — see M3), **#119** (74-of-81 rounds return CANNOT RUN).

The consequence is not bookkeeping. *Rejected, with reasons* (lines 220–226) refutes exactly one
alternative — **a controlled vocabulary / registry** — with a genuinely good measurement (83 names,
67% singletons, 0 shared across subjects). **That measurement does not bear on #136's proposal at
all.** Deriving the partition from the file or symbol a finding names requires no registry, no
reuse across subjects, and no author agreement on wording; the 83-singleton result is an argument
*for* it, not against. So the strongest filed alternative is left standing, unmentioned, while a
weaker one is refuted in its place.

A human approving this spec cannot currently tell whether doing so **closes** #136, **forks from**
it, or **defers** it — and #136 is an `L` with a user-set gate on it.

**Sibling search.** I grepped `docs/backlog.md` for `check-review-decision` and `thrashing` and read
every hit: rows **117, 118, 119, 134, 136** all concern this script or this function. I then grepped
the spec for each row number: it cites `#167`, `#154`, `#56` and none of the five. I also checked
`docs/roadmap-to-launch.md:2100`, which records the mechanical firing but files no competing design.

---

### H4 — After round 1's fold, the escape hatch is not readable as specified, and the natural implementation makes it permanent

Round 1's M1 was folded by **removing component names from the declaration entirely** (lines 102–112:
*"the declaration carries **no component names at all** … There is no partial form to get wrong"*).
I agree with the direction. But it moves the entire burden of identifying *what was judged* onto a
placement rule the spec never states, and §2 says only:

> `COMPONENTS DISTINCT: <reason>`, in the round document, satisfies the check.

**Which** round document? The refusal concerns a **pair** (r*n-1*, r*n*), and there are up to N
documents. Three sub-problems, all unspecified, all of which implementation must invent:

1. **Placement.** If the reader scans *any* of the subject's round documents — the natural
   implementation, because `rounds_for()` (`scripts/check-review-decision.py:348-362`) already globs
   them all — then **one declaration written at r3 silences every later refusal on that branch,
   forever**. The spec insists at line 116 that the line *"is not a suppression flag — it is
   testimony"*. Under that reading it is exactly a suppression flag, and it reaches backlog #56's
   outcome (a gate switched off) by accident rather than by decision — the outcome §2's own
   justification invokes.
2. **Expiry.** The only sound rule I can construct is *the declaration must live in the **last**
   round's document*, so that a new round re-poses the question against a new cross-product. The
   spec does not say this, and it is not deducible from the `REVIEW GAP:` precedent, which is
   per-half and per-document rather than per-pair.
3. **Reader.** `decide()` (`:168`) is pure over parsed headers, and `parse_header()` (`:198-251`)
   returns `{round, findings, fixes_nontrivial}` — **it discards the document prose**. Every
   docstring in the decision path says `PURE.` and the `--self-test` is built on that. So the escape
   cannot be read where the decision is made without either threading document text into a pure
   function or adding an extraction step to the parser. That choice also *determines* (1) and (2):
   extracting per-document into the round dict makes "the last round's document" the natural
   semantics and keeps `decide()` pure. It should be specified, not discovered.

**And the auditability question the brief asks (Q3) turns on the same gap.** The declaration carries
no names, so a later reader can only reconstruct what was asserted from the two round headers — which
*are* committed and *do* carry the sets, so the audit is possible **provided the reader knows which
pair the line belongs to**. That is the placement rule. With it, the no-names decision is sound and
the spec's own falsifier (*"a reason, read later, is wrong"*, line 166) remains checkable. Without
it, the falsifier is unusable, because nobody can tell what the reason was about.

**Sibling search.** I read the `REVIEW GAP:` reader to see whether the grammar transfers:
`scripts/check-review-rounds.py:83-88` anchors it to line start, tolerates emphasis wrapping on
either side, and requires a half name plus an em-dash — hardening bought by measured near-misses. It
lives in a **different script over a different file set**, and nothing in `check-review-decision.py`
reads any prose convention today (`grep -n "REVIEW GAP\|NO-REVIEW\|read_text"` → one `read_text` in
`rounds_for`, one `NO-REVIEW:` inside a `TREE_ANSWERS` string). So §"Sizing" line 174 —
*"refusal message + escape parsing — small — `REVIEW GAP:` supplies the grammar"* — is understated:
the grammar exists, the **reader does not**, and re-deriving one is this repo's 17-times-measured
*a second implementation of one rule drifts*.

---

### M1 — §3's numbers are already wrong in the commit that introduced them, and the corpus is 29 of 71 documents

Re-deriving §3 on the current tree, with `check-review-decision.parse_header` over
`docs/reviews/coordinator/*-r*-coordinator.md`:

| | spec (line 130) | measured now |
|---|---|---|
| subjects / rounds / findings | 7 / 28 / 145 | **8 / 29 / 147** |
| trigger fires normally | 11 | 11 ✅ |
| would refuse | 5 | 5 ✅ |

`git log --oneline -1` on both files returns the **same commit, `f34d16a9`** — the spec and
`decision-card-soundness-r1-coordinator.md` landed together, and that coordinator document is the
8th subject, the 29th round and findings 146–147. **The calibration was stale at the moment it was
committed, by the act of reviewing it.** The headline conclusions survive (the new subject has one
round, so it contributes no pair), which is why this is Medium and not High — but §3 is designated
as the `--self-test` **fixture**, so whatever snapshot implementation takes will disagree with the
document unless someone notices.

Two further disclosures §3 owes and does not make:

- **The corpus is 29 of 71 coordinator round documents.** 42 fail `parse_header` with ``no ```yaml
  header block`` — backlog #119's known population, predating the grammar, and backfilling was
  explicitly rejected by the user. §3 says *"every subject with parseable round records"*, which is
  true and is not the same as saying the calibration covers **41%** of the recorded rounds, all of
  them the newest branches.
- **Freezing the fixture removes the only falsifier for the sensitivity claim.** Line 140 states the
  mitigation honestly — *"The fixture asserts the function's verdict on fixed input, never that the
  live corpus still looks like it"* — but *How we would know it failed* names
  *"`COMPONENTS DISTINCT:` appears in most round documents → too sensitive"* (line 163) as a signal,
  and after freezing, **nothing ever re-measures that**. The fixture protects the behaviour; the
  claim that the behaviour is *acceptably rare* becomes unfalsifiable. Answering the brief's Q5:
  the stated mitigation is sufficient for drift of **behaviour** and not for drift of
  **sensitivity**, which is the failure the spec itself named.

**Sibling search.** I counted the whole directory (71 documents, 18 distinct subjects on disk) rather
than the parseable subset, so the 41% figure is over the real population, not the one the tool
happens to see — this repo's *measure the population the code actually sees* failure, applied in the
other direction on purpose.

### M2 — A refusal nobody answers expires silently; the escape is durable and the refusal is not

`thrashing_component` reads **the last two rounds only**, deliberately (`:98-101`), and the proposed
check inherits that window. So if the tool is not run at r3 (see H1 — nothing runs it), the
(r2, r3) refusal is simply **never emitted**, and at r4 it is gone: if r4 carries no fix-induced
findings the check does not fire at all, and the ambiguity that would have been refused is never
surfaced again. Compare the escape, which — under reading (1) of H4 — persists for the life of the
branch.

That asymmetry is the wrong way round for a safety mechanism: **the suppression outlives the
question it suppresses.** The spec's *What this does not do* correctly declares the single-round
case (line 156) but says nothing about the window, and the brief's Q1 shape — *thrashing that spans
three rounds with a gap* — lands in the same blind spot. That blindness is inherited from the
existing trigger and is arguably out of scope, but it should be **declared**, because the new check
is the first thing to depend on it for something other than firing.

### M3 — The refusal moves five measured cases from exit 1 to exit 2, quietly settling backlog #118

`exit_code_for` (`:391-393`) is `{"STOP": 0, "CANNOT_RUN": 2}.get(decision, 1)`. Measured over the
corpus: **all 5 refusals displace `ROUND_OWED`; none displaces `STOP`.** That is good news the spec
does not claim — the refusal never converts a converged branch into a blocked one, so its blast
radius is bounded (brief Q4).

But it does move five real cases from exit **1** (*a human owes this branch an action*) to exit **2**
(*the tool could not answer*), and `docs/backlog.md:146` (#118) has that code space open as an
explicit, filed question: *"does the code space encode **what to do** (and unknown is a fourth kind
of action) or **whether the tool could answer** (and unknown is a refusal, i.e. 2)?"* — with
*"Deciding that first is what stops the two-line fix being relitigated."* The refusal's payload is
unambiguously a *what to do* (relabel, or declare), filed under the *could not answer* code. The
spec takes a side on a filed open question without saying so, and #118's own bound —
*"the day something calls this script, an ambiguous code becomes a wrong automated decision"* — is
the condition H1 is about.

---

## What I checked and found clean

- **`CANNOT_RUN` is semantically defensible here, and the precedent exists** (brief Q2). The spec
  argues it from the *"could not reach what it measures"* gloss, which is the weaker argument and is
  arguably not what is happening — the guard reaches its subject fine. The stronger argument is
  already in the code and the spec does not cite it: `decide()` (`:172-176`) returns `CANNOT_RUN` for
  `sequence_error` with the reason *"refusing to infer adjacency from list position"* — a record that
  parsed perfectly and was still refused. So *"refusing to infer from a well-formed but unreliable
  record"* is an **established** meaning of exit 2 in this file, not a new one. Recommend the spec
  cite `:174` instead of the gloss; no finding.
- **A missing or blank `component` cannot produce a silent false intersection** (brief Q1's
  "findings with NO component at all"). `_validate` (`:273-285`) raises unless
  `str(f.get("component","")).strip()` is non-empty, and `thrashing_component:108` additionally
  guards with `any(shared)` and `if c`, so `shared == {""}` or `{None}` cannot yield a non-empty
  intersection that returns `None`. This is the one hole I most expected to find in the condition as
  worded ("empty intersection"), and it is closed two layers deep. I checked both the flow-mapping
  and block-style parse paths reach `_validate` (`:240-241`).
- **A component renamed mid-slice fires the check, in the right direction.** `peer-sites` r4 is
  literally that shape and refuses — see H2, where I argue the timing is wrong but the detection is
  not.
- **A single round does not fire.** `len(rounds) < 2` (`:102-103`); the spec's line 155–157 matches.
- **The core measured defect reproduces.** Replaying the shipped `thrashing_component` per-round over
  `velocity-doc-consistency`: it never fires at r2, r3 or r4. I did not independently re-run the
  synonym-merge half — Codex reproduced it and the coordinator recorded it, and my per-round table is
  consistent with it.
- **Line-budget claims hold.** `scripts/check-docs.py:192` budgets `docs/dev-process.md` at **220**
  and budgets nothing else; `review-method.md` and `round-header-template.md` are genuinely
  unbudgeted, and `:266` names `review-method.md` as the designated sink for spine overflow. The
  spec's line 175 and its ⛔ at 178 are correct.
- **Ordering.** Inserting the refusal between Q5 and Q4 does not reorder anything else:
  `sequence_error` still precedes it, `converged` still follows, and `TREE` is still answered last
  (`:168-194`). Measured effect on Q4 is the displacement in M3 — five `ROUND_OWED`s, zero `STOP`s.
- **`check-review-rounds.py` is unaffected.** It reads `docs/reviews/<writer>/` and the flat layout
  for half-presence and `REVIEW GAP:` lines; it never imports or invokes
  `check-review-decision.py`, and the proposed change touches neither its inputs nor its grammar.

## Method

Everything above was derived by reading and running, not by inspection of the prose. The replay
imported `scripts/check-review-decision.py` directly and used its own `parse_header`,
`rounds_for`, `thrashing_component` and `decide`, so the condition was evaluated against the
functions that ship rather than a second implementation of them. Corpus counts were taken over the
whole `docs/reviews/coordinator/` directory (71 documents), not over the parseable subset.

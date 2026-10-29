# Round-document header

Every **coordinator** round document carries this block immediately after its title.

⟳ **2026-10-20: A RELOCATION TO THE HALVES WAS PROPOSED HERE, BUILT, AND WITHDRAWN THE SAME DAY —
and the withdrawn claim is recorded because it is the instructive part.** This paragraph said that
**97%** of rounds carry at least one half against **35%** carrying a coordinator document, and
concluded that moving the fields into the halves lifts feedability to 97%.

⛔ **Round 1 refuted the inference by running it.** Readable subjects went **10 → 10, zero gained**,
because **0 of 435 half documents carry a parseable header**. 97% was the rate at which half
documents **EXIST**, reported as the rate at which rounds become **READABLE**. The three rates
themselves re-derive correctly; the inference drawn from them did not. ⚠ And the corpus was wrong
too: it excluded 294 flat round documents, so the real figures over both layouts are **81 subjects /
392 rounds**, which moves the coordinator share to **29.3%** and both-halves to **71.4%**.

⛔ **THE STRUCTURAL REASON, which is why this is a design question and not a corrected sentence:**
`disposition` and `fixes_nontrivial` are **post-fold facts**. A reviewer writing its half does not
yet know whether its own finding will be fixed, filed or declined, nor whether the fold will be
non-trivial. **A half structurally cannot carry two of the seven fields**, which is why 0 of 435 do.
Deciding which fields a half CAN know — `severity`, `aim`, `component` are candidates — is a grammar
split that wants a spec. Filed as its own slice; see the backlog row that names this paragraph.

**Why it exists.** The decision procedure needs two counters — *consecutive fix-induced rounds* and
*rounds since a finding in the deliverable*. On PR #302 nobody kept either, which is why four rounds
ran where two were owed. `review-method.md` already refuses the alternative: *"the evidence is
derivable, not remembered. Do not maintain a hand-written tally of it."*

````markdown
```yaml
round: 3
fixes_nontrivial: true
subject: clickable-dashboard-asks
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, component: check-review-decision, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: check-review-decision, disposition: filed}
```
````

| Field | Values | Definition |
|---|---|---|
| `round` | integer | the round number; the set must be a gapless `1..N` with no duplicates |
| `fixes_nontrivial` | `true` `false` | were this round's fixes more than a reworded line? **`true` blocks convergence** — a non-trivial fix is unreviewed code |
| `subject` | string | the branch or artifact under review |
| `halves.<name>` | `ran`, or `"GAP: <reason>"` | whether each half ran; a gap carries its reason. ⟳ `check-review-rounds.py` reads this form as a gap (backlog #182) — a prose `REVIEW GAP:` line is no longer also needed. ⚠ **Only this exact spelling is read:** `codex:`/`claude:` at two spaces directly under `halves:`, the value in DOUBLE quotes, a reason that does not start with `#`, in the first fence after the title. Single or no quotes, a trailing comment, a flow mapping or a blank line inside `halves:` is NOT read, and the half counts as missing. The gap must name the half that is actually missing |
| `severity` | `Blocking` `High` `Medium` `Low` | as filed by the reviewer |
| `aim` | `deliverable` `instrument` | does the finding sit in code the branch **ships**, or in a test, guard or harness that **measures** it? |
| `fix_induced` | `true` `false` | was the defect introduced by a fix written **after** a previous round? ⚠ **UNDECIDED:** whether a fix written inside the SAME round — by its first half's fold, reviewed by its second half — counts; see backlog #347 |
| `component` | string | the unit the finding is in — thrashing is judged per component, not per round |
| `disposition` | `fixed` `filed` `declined` `refuted` | what Q3 decided; the reason goes in prose below the header. **`declined`** = real, and not being fixed; **`refuted`** = checked and NOT a defect (backlog #318) — keep them apart. `fixed`, `declined` and `refuted` answer a finding; `filed` leaves it OPEN, because a backlog deferral is not an answer about this branch |

## The two fields that carry the weight

`aim` and `fix_induced` are the inputs the whole procedure turns on, and **both are judgements the
agent records — not values the header derives.**

- **`aim`** answers *would this defect reach a user, or only a measurement?* A finding in
  `scripts/gen-dashboard.py`'s emitted markup is `deliverable`; a finding in the self-test case that
  checks that markup is `instrument`. Two consecutive instrument-only rounds is the stop signal,
  because the reviewer has run out of product to attack.
- **`fix_induced`** answers *did we make this?* It is the difference between a design that is
  under-specified and one that is fighting itself, and it is the arming condition for the
  architecture review.

⚠ **A header filled in dishonestly produces confident wrong answers, and nothing detects that.**
Marking everything `deliverable` forces rounds that are not owed; marking everything `instrument`
stops a review that should continue. ⛔ **WHAT IS ACTUALLY VALIDATED — r7 Medium (Codex) caught this paragraph overclaiming.**
It said *"every field above is now validated"*, which was false, in a document whose subject is a
machine that refuses unvalidated records:

| Field | Enforced? |
|---|---|
| `round` | ✅ required, integer, and the set must be gapless `1..N` with no duplicates |
| `fixes_nontrivial` | ✅ required, must be `true` or `false` |
| `severity` `aim` `fix_induced` `disposition` | ✅ required per finding, each against its allowed set |
| `component` | ✅ required per finding, must be non-empty |
| `subject` `halves` `id` | ❌ **NOT required and NOT validated** — a header carrying only `round`, `fixes_nontrivial` and `findings` parses |

And none of it checks whether a value is **true**. Marking everything `deliverable` forces rounds
that are not owed; marking everything `instrument` stops a review that should continue. **Both limits
are stated here rather than discovered later** — which is the whole point, and is why the overclaim
was worth a finding.

⟳ **AND FOR TWO ROUNDS THE MACHINE DID NOT EVEN DO THAT.** r1 found that block-style items parsed
to *zero* findings; r2 found that the repair proved an item had become a dict but not that it said
anything — a missing colon (`severity High`) dropped the field, and a missing field reads as *"not
Blocking, not deliverable"*, so a recorded High reached `STOP`. The sentence promising validation came first;
the validation came two rounds later.

## An absent header is CANNOT RUN

`scripts/check-review-decision.py` **raises** on a round document with no header and exits 2. It does
not treat it as a round with no findings — that would read as convergence, which is the failure mode
this repository refuses everywhere: *"cannot run" is a failure, never a pass*.

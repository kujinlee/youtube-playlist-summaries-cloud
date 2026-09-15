# Round-document header

Every **coordinator** round document carries this block immediately after its title.

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
| `halves.<name>` | `ran`, or a string starting `GAP:` | whether each half ran; a gap carries its reason |
| `severity` | `Blocking` `High` `Medium` `Low` | as filed by the reviewer |
| `aim` | `deliverable` `instrument` | does the finding sit in code the branch **ships**, or in a test, guard or harness that **measures** it? |
| `fix_induced` | `true` `false` | was the defect introduced by a fix written **after** a previous round? |
| `component` | string | the unit the finding is in — thrashing is judged per component, not per round |
| `disposition` | `fixed` `filed` `declined` | what Q3 decided; the reason goes in prose below the header |

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
stops a review that should continue. The machine checks that the fields are **present and
well-formed**, never that they are **true**. That limit is stated here rather than discovered later.

⟳ **AND FOR TWO ROUNDS THE MACHINE DID NOT EVEN DO THAT.** r1 found that block-style items parsed
to *zero* findings; r2 found that the repair proved an item had become a dict but not that it said
anything — a missing colon (`severity High`) dropped the field, and a missing field reads as *"not
Blocking, not deliverable"*, so a recorded High reached `STOP`. **Every field above is now validated
against its allowed set, and anything else RAISES.** The sentence promising validation came first;
the validation came two rounds later.

## An absent header is CANNOT RUN

`scripts/check-review-decision.py` **raises** on a round document with no header and exits 2. It does
not treat it as a round with no findings — that would read as convergence, which is the failure mode
this repository refuses everywhere: *"cannot run" is a failure, never a pass*.

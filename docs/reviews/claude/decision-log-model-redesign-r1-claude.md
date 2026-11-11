# Round 1, Claude half — `decision-log-model-redesign` (DESIGN review)

Subject: `docs/superpowers/plans/2026-10-20-decision-log-model-redesign.md` (247 lines, uncommitted),
read from disk on branch `decision-route-escalation` @ `740b4df3`.

**This is a design review, not a defect hunt** — escalated by `review-method.md:177-178`, which I
read at those lines rather than recalling. My mandate was to **refute**. Where the document is right
I say so and give the command, because a design review that only lists complaints has not measured
the document's load-bearing claims either.

**Everything below was RUN.** Probes are in `/Users/kujinlee/.claude-tmp/dr-probe/` (never in the
repo — #326's lesson); they drive the real `main()` and the real pure functions over temp logs via
ADR-0014's `log_path` parameter. No mutation sweep, no `npm test`, no guard sweep, no git writes
(a 1,625-mutation sweep was in flight; nothing here is timing-sensitive). I did **not** read the
Codex half, which was already on disk at `docs/reviews/codex/decision-log-model-redesign-r1-codex.md`
when I started — independence is the only thing that makes two halves worth two halves.

Baseline sanity, first: `check-decision-scheme.py --self-test` **133/133**,
`check-review-decision.py --self-test` **85/85**, both rc=0. My findings are not about a broken tree.

---

## What reproduced exactly as the document claims

§1.1 is the strongest part of the document and it survives re-derivation.

| claim (§) | re-derived result |
|---|---|
| The true seven-unit history is **refused**, and refusal takes the whole mechanism offline (§1.1) | **rc=2**, `CANNOT RUN — the log holds unusable rows, so no trigger was evaluated`, rows 1-2 named. The quoted refusal text is verbatim: `route 'split' is not the next route for ('decision-route-escalation', 'relocation'): tried [], so the only route left to bet on is 'accrete'` |
| The five writable units alone → `all triggers quiet` | rc=0, `7 row(s), 2 scored; all triggers quiet`. So §1's sentence — *"`all triggers quiet` is caused by the omission of the decisions the schema refused"* — is **measured, not argued** |
| The seven units and their routes come from the r1 coordinator table, not from recall | `decision-route-escalation-r1-coordinator.md:49-55` matches the §1.1 table row for row (SPLIT/REDESIGN/5×ACCRETE) |
| `t1_not_fed` cannot distinguish 1-of-7 from 2-of-7 (§1.1, #324) | `t1=None` at 1, 2 and 7 of 7 logged units; loud **only** at 0. And the live domain is exactly one subject: `subjects_starved(armed_at)` → `['decision-route-escalation']`, which has a row, so the loudest trigger is bought off by one row **today** |
| `ranker_hit: null` and `"abstained"` are both refused, with a message wrong about its input (§1.1, #325) | `None` → `ranker_hit is NoneType, not a bool — a string coerces to True and erases a miss` |
| `scope_tally` saturates; four components collide at 3 (§1.1, #323) | 4 components at `rounds_appeared=3`; `scope_lead` → `NO LEAD` |
| findings-per-component **13 / 12 / 8 / 6** (§2.3) | exact: `log-schema` 13, `starvation-ratchet` 12, `coverage` 8, `corpus-cannot-run` 6 |
| `returns_after_gap` is **0 for all four** on this slice, so the gap term resolves nothing (§2.3) | exact — and the document says so against its own first draft. Credit where due |
| t2's guard `continue`s past a ladder exhausted in three routes (§3) | `t2_non_termination` returns **None** for `tried=[accrete, split, defer]` with `outcome: continued`; fires only on all four. §3's t2 argument is correct |
| §2.2's provenance | the owner's two steers are at `review-method.md:304-307`, *"a route is never retried"* and *"you stop when the ROUTES ARE EXHAUSTED"* at `:329-332`, and **"Start at the cheapest route"** is indeed an unattributed authored sentence at `:329`. The ordering clause is not the owner's |

Strict increase does genuinely subsume the duplicate and prefix tests: `index(route) > max(index(tried))`
refuses `[accrete, accrete]` (0 > 0 false) and `[accrete, split] + redesign` (1 > 2 false). §4's
four-row bound follows from `|LADDER| = 4`. That part of the argument holds.

**So the unification in §1 is a structural fact, not a rhetorical move** — for three of the four. One
projection (`(unit, bet)` recorded as `(subject, prediction)`) does produce #321, #324 and #325, and
I could not construct a reading in which it does not. **#323 is the exception and does not belong**:
it is a defect in a *ranker over round documents*, which never touches the decision log, has no
`unit`, no `bet` and no row. §3's own table says so — t6 and the ranker *"read the corpus, not the
log"*. Folding it in is what let its answer (§2.3) be written without the constraint the rest of the
document observes, and §2.3 is where two of this review's three Blockings land.

---

## Findings

### B1 — Blocking — the design's own validator takes the mechanism permanently offline, and §1.2.2 is the diagnosis of exactly that
`component: log-schema` · `fix_induced: yes` (the append-only posture is r1's fix)

§2.1 adds `round` and `units_decided` to the row model with no `| absent` and no grandfathering
clause; §2.5 makes `bet` **"REQUIRED once `outcome` is set"**. §6 **T6** then says: *"the existing
four are **not** rewritten (append-only)."* `main()` refuses the entire log if **any** row is
unusable (`check-decision-scheme.py:720-726`).

I implemented §2.1/§2.2/§2.5 verbatim and ran it over the four live rows:

```
row 1 (corpus-cannot-run/accrete):  "missing 'round'"
row 2 (corpus-cannot-run/redesign): "missing 'round'"
row 3 (starvation-ratchet/accrete): "missing 'round'"
row 4 (starvation-ratchet/redesign):"missing 'round'"
=> 4 of 4 live rows unusable.   Narrowest possible reading (ONLY §2.5's `bet` clause): 2 of 4.
```

Either way `main()` prints `CANNOT RUN — … no trigger was evaluated` and returns **2**, in CI, on
every run, for ever, because the rows that cause it may not be rewritten. **§1.2.2 names this
mechanism in the document's own words** — *"`validate_row` refuses a true row, `main` treats any
unusable row as CANNOT RUN for every trigger, and the file cannot be edited afterwards"* — and then
§2.1/§2.5/§6 rebuild it one page later, with the author's own four rows as the victim.

What closes it is a sentence the document does not contain: either the new fields are **required
only from a schema epoch** (a `schema: 2` discriminator, or "required iff `round` is present"), or
append-only admits a **superseding** row and §6 T6 says so. This is a decision, not a detail: it
decides whether shipping the design makes the instrument work or deletes it.

### B2 — Blocking — §2.3 answers #323 with the one move #323 forbids, and drops the remedy #323 prescribes
`component: ranker-caller` · `fix_induced: no`

`docs/backlog.md:307` (#323) and `architecture-review-2026-10-20…:83-86` (F2) — the finding this
document is answering, and the review that armed this document — both say:

> ⛔ **Do NOT simply switch the ranker to finding counts**: that is the noise-sensitivity the
> once-per-round rule exists to prevent … **The honest output is a ranking plus its saturation
> state** — *"4 tied at the ceiling, N=3"* is a different message from *"no component recurred"*.

§2.3 does neither. It rebuts a **different** objection — `scope_tally`'s docstring rejection of
*"total + 2x returns"* as a free parameter — and never mentions the prescribed remedy or the ⛔.
Measured consequences of the tuple it proposes instead, over the 11 parseable subjects:

| | today | proposed tuple |
|---|---|---|
| subjects reporting NO LEAD | **6 of 11** | **2 of 11** |
| `decision-route-escalation` | `NO LEAD — 4 components tied at 3` | `log-schema` leads |

So on the measured case, the saturation message #323 asks to be *reported* is **deleted** rather than
reported — 4 of 11 subjects stop saying "tied at the ceiling" and start naming a winner. And the
winner is chosen by a **one-finding margin**: `log-schema` 13 against `starvation-ratchet` 12, in a
subject whose per-round finding volumes ran **22 / 8 / 20**. Re-attributing a single finding's
`component` — an authored field — flips the name the mechanism prints. That is the noise sensitivity
the once-per-round rule exists to prevent, arriving third in a tuple instead of first in a sum.

§2.3's defence is *"noise-safe at that position because recurrence is already equal before it is
consulted."* The defence assumes ties are rare. **Measured, ties at the top are the majority case:
6 of 11 subjects today.** In the saturated regime — the one #323 is about — `total_findings` is not a
tie-break, it is the decider.

The remedy is cheap and the document can have it: keep the tuple as the *order*, and keep printing
the saturation state (`n1 == N_rounds` with the tied set) as a first-class line, so a lead won on
volume is legible as such. What cannot stand is answering a finding with the move it names and not
saying that is what you are doing.

### B3 — Blocking — §2.4 rejects "the obvious fix" by arguing against a fix #324 did not propose, using a figure from a corpus this slice already corrected
`component: starvation-ratchet` · `fix_induced: yes` (the corrected corpus is r1 Claude M1's own fix)

§2.4's load-bearing paragraph: *"Reading each round's **units** requires a parseable round header,
which is readable for **10 of 57 subjects (18%)** … a unit-granular ratchet derived from the corpus
would be CANNOT RUN on 82% of it."* Three separate problems, all measured.

**(a) That is not the fix #324 filed.** `docs/backlog.md:308` says: *"decide the granularity the
trigger reads — per decided unit, **with the unit set derivable from the round documents' `component`
fields**, or an explicit declaration of units-not-logged with a reason."* The `component` fields —
not a header's unit list. Those fields are what `parse_header` already extracts and what the
architecture review itself used to produce 13/12/8/6. Run on this slice they give

```
8 components across 3 rounds: accounting, baseline-validation, corpus-cannot-run, coverage,
                              log-schema, ranker-caller, relocation, starvation-ratchet
7 routed units:               the same minus `baseline-validation` (filed, never routed)
```

so the derivation is **available and nearly exact**, over-approximating by one. That
over-approximation is a real cost (it would fire spuriously, which is #56's hazard) and it is exactly
what #324's **second** option exists to absorb. The document takes neither option and refutes a third
one nobody proposed.

**(b) The figures are from the superseded corpus.** `baseline.json` carries `57` under the key
**`corpus_ORIGINAL_WRONG`**, with the note *"it reproduced a PREVIOUS SESSION'S denominator, so I
picked the corpus that matched a number rather than the one the code reads (r1 Claude M1)"*. The
corpus the ratchet actually reads is both layouts. Re-derived today with `_round_docs()` +
`parse_header`:

| population | measured | §2.4 says |
|---|---|---|
| subjects with ≥2 rounds | **82** | 57 |
| subjects with a readable round | **11 of 82 = 13.4%** (86.6% CANNOT RUN) | 10 of 57 = 18% (82%) |
| **(subject, round) pairs** — the rule's own domain | **46 of 395 = 11.6%** (88.4% CANNOT RUN) | not stated |

The error direction is favourable to the conclusion, so the conclusion survives — but §2.4 reports
the figure for the **subject** population while the rule it justifies is defined over **(subject,
round)** pairs, and §5's retirement threshold (*"readability passes ~50%"*) inherits the wrong
denominator. This is the repository's twelve-times-measured class landing in the sentence that
decides the design.

**(c) The cross-check it offers has the availability it just rejected.** §2.4 refuses derivation
because it is available on ~12% of the corpus, then offers *"where a header **is** readable (18%),
`units_decided` is cross-checked against it"* as what makes the authored field honest. Both halves
read the same `yaml` block, so they have **identical** availability. On the 88% where there is no
cross-check, an author who omits five rows writes `units_decided: 2` and the arithmetic is
self-consistent and silent — which is the state §2.4 exists to end. See H3 for why the `round` field
alone buys most of the claimed benefit.

### H1 — High — §2.3's falsifier cannot be measured on one case and cannot fail on the other two
`component: ranker-caller` · `fix_induced: no`

§2.3: *"⚠ **FALSIFIER, and the change is refused if it fails:** it must still rank the 3 labelled
subjects **3 of 3**, and must reduce the NO-LEAD count below **5 of 10**. Both are measurable now."*
Run it:

- **The third labelled subject is not measurable.** The labels are `src-caller`,
  `number-populations`, `parse-header` (`review_scope`'s docstring). `src-caller`'s architecture
  review names branch **`ship-src-root-alone`**, and `rounds_for("ship-src-root-alone")` **raises**:
  `finding 'L4' has disposition='refuted', not one of ['declined','filed','fixed']`. On this
  repository's own posture — *cannot run is a failure, never a pass* — a "3 of 3" over a population
  containing an unparseable member is a CANNOT RUN reported as a pass.
- **The other two cannot fail.** `velocity-177` → `number-populations` at `n1=5`, **unique**;
  `review-decision-procedure` → `parse-header` at `n1=5`, **unique**. A lexicographic tie-break acts
  only on ties, so neither top can move: the fit is 2-of-2 **by construction**, whatever the new keys
  are.
- **The second half cannot fail either.** Adding tie-break keys can only reduce or preserve the number
  of exact ties, never increase it. The only way to fail "reduce the NO-LEAD count" is for every tied
  group in the corpus to tie on all three keys. Measured 6 → 2.
- **And the baseline is stale**: measured today it is **6 of 11**, not 5 of 10. The extra subject is
  `decision-route-escalation` itself — so the figure the design states as its own bar is the one
  taken from a population that structurally excludes the slice the design is about, while §1.1 relies
  on that slice separately.

Meanwhile the change *does* move the named component in 2 subjects where there is no label to check
it against (`peer-sites`: `activation` → `parse-hunks`; `decision-route-escalation`:
`corpus-cannot-run` → `log-schema`). Both halves of the falsifier are blind to exactly those cases.
A test that cannot fail is a decision wearing a checkbox, and this one is labelled *"the change is
refused if it fails."*

### H2 — High — §2.2 hands the mechanism a lever on its own figure of merit, and §3 marks that trigger "unchanged"
`component: log-schema` · `fix_induced: no`

`review-method.md:310-312` and the module docstring both state the figure of merit: **"ROUNDS-TO-TERMINATION,
not accuracy."** t4 compares the median of the last five terminated subjects against a median of 4
pinned *before* the scheme shipped — i.e. measured in a regime where skipping rungs was inadmissible.

§2.2 makes skipping admissible, with the only check being that a citation is *present* (§2.2's own
stated bound). A unit that skips two rungs reaches termination in fewer rounds, which lowers
`rounds_at_termination`, which lowers t4's median, which is the statistic that decides whether *"the
mechanism is ceremony, not leverage."* §3 records t4 as **unchanged — "the comparator stays pinned"**.
The comparator is pinned; the **quantity being compared to it** is what §2.2 changes.

This is the fifth consequence the unification predicts and the document does not list, and it is the
one that matters most, because it is the mechanism acquiring the ability to improve its own score by
authoring a sentence. §5's *"measured benefit remains zero"* does not cover it — a benefit that
appears *after* the change, produced by the change's own permission, is worse than zero.

### H3 — High — `units_decided` is a round-level fact carried per row, and the only validator hook is unit-partitioned
`component: starvation-ratchet` · `fix_induced: no`

§2.4 puts `units_decided` on **every** row. Nothing in §2.1 or §6 T4 says what happens when two rows
of the same `(subject, round)` disagree, or which value the ratchet reads. And the consistency check
is not expressible where the design puts the schema: `main()` calls
`validate_row(r, prior=seen.get(unit_key(r)))` (`:713`) — `prior` is **this unit's** earlier rows, a
different partition from `(subject, round)`. A per-row validator handed a unit's history structurally
cannot see the round's other rows.

A round-level quantity recorded once per row, with no agreement rule, read through a unit-shaped hook,
**is a projection of the decisions recorded as the decisions** — §1's own diagnosis, one level down,
introduced by the answer to it.

Note also what the field actually buys. §2.4's primary clause — *"a `(subject, round)` has no rows"* —
needs only `round`, is available on 100% of the corpus, and is already strictly stronger than the
subject rule it replaces (one row no longer silences a subject). Everything beyond that is
`units_decided`, whose only mechanical firing is defeated by the same omission it exists to detect
(B3(c)), and whose §5 retirement condition — *"if `units_decided` is found under-declared twice"* —
names no observer that could find it on the 88% with no cross-check. **§2.4's honesty claim is
therefore half true**: it buys attributability *to a human reading the round document*, which `round`
alone already buys; it buys nothing mechanically; and it is called *"attributability, not
verification"* in a bound that does not say which of the two new fields is doing the work.

### H4 — High — §2.2's rule is not implementable as §6 T1 specifies, and is undefined on the two histories that motivate it
`component: log-schema` · `fix_induced: no`

§2.2 gives the rule twice, and the two statements are not the same rule:

1. *"`LADDER.index(route)` must be **strictly increasing**"* — an admissibility **predicate** over a
   set of acceptable routes.
2. *"`route_next(tried)` becomes the lowest-index route above `max(index)` … one expression, and it
   **replaces** both the prefix test and the duplicate test"* — a **function returning one route**.

A single-valued function cannot express "any strictly greater index is admissible", and §6 **T1**
assigns the change to that function while saying nothing about `validate_row`'s comparison, which is
an **equality**: `if row["route"] != expected: return "route … is not the next route"` (`:478`).
Implemented exactly as T1 is written, `route_next([])` still yields `accrete`, `relocation`'s SPLIT
still fails the equality, and **#321 stays open while T1's own first case ("the two refused real
histories now admit") goes red.** The predicate must move into `validate_row` as an inequality, and
the document should say so, because its stated subsumption claim is what hides the need.

Second, the expression is **undefined on the empty history**: `max(index of [])` raises, and both of
the two real histories the whole design exists to admit are **first rows of their unit** (`relocation`
→ `split`, `log-schema` → `redesign`). The rule needs a stated baseline (implicitly index −1, so a
first `accrete` needs no citation and a first `redesign` cites `accrete`), and §6 T1's case list —
four cases — contains no case for it.

### H5 — High — §2.5 arms t5 while preserving the projection error in it; the newly reachable falsifier misreports position and denominator
`component: log-schema` · `fix_induced: yes` (the filtering is r1 Codex M5's fix)

§2.5: *"`t5_ranker_miss` reads only `named` rows — **semantics unchanged**, but now reachable."*
The unchanged semantics are the defect. `marks` is built from the **filtered** list
(`:227`), and both the index and the denominator printed are indices into that filtered list.
Constructed — misses at log rows 1 and 4, abstentions at 2 and 3, four scored rows:

```
t5 -> "two consecutive ranker misses at rows 1 and 2 of 2 scored — re-fit or retire the ranking"
```

The misses are **not consecutive** (two abstentions sit between them), the rows are **not** 1 and 2,
and there are **4** scored rows, not 2. §2.5 is the section that makes this trigger fire for the first
time; shipping it with the projection intact arms a falsifier that will state three wrong facts the
first time it fires, about a log the design has just made expressive enough to distinguish them.
Either compute consecutiveness over the `(subject, round)` sequence with abstentions as **gaps**, or
print log row numbers and the real denominator — and say which, because "semantics unchanged" is a
choice here, not a no-op.

### H6 — High — §2.4's new domain has no stated arming restriction, and both readings are stated nowhere
`component: starvation-ratchet` · `fix_induced: no`

*"The ratchet fires when a `(subject, round)` in the corpus has **no rows**"* — "in the corpus",
unqualified. Today the restriction lives in `subjects_starved`, which answers *"came into scope after
`armed_at`"*, and `baseline.json` explains why in the file: *"a gate red from birth over 57 historical
subjects gets switched off, which backlog #56 measured."* Measured over the real corpus:

- **395** `(subject, round)` pairs in subjects with ≥2 rounds. Taken literally, §2.4's rule fires on
  essentially all of them → red from birth → switched off, which is the exact argument §2.4 uses two
  paragraphs earlier to kill the derived ratchet.
- **4** pairs are not present before `armed_at`: `(decision-log-model-redesign, 1)` and
  `(decision-route-escalation, 1|2|3)`. So if the restriction *is* preserved, the live domain is four
  pairs — three of which fire on day one, because §6 T6 leaves the only existing rows without a
  `round` to be assigned to, and rounds 2 and 3 then have **zero** rows. `main()` returns **1** on a
  FAIL, in CI.

Both readings are defensible and they are opposite; the document picks neither, and §6 T4's cases
("a round with zero rows fires; `2 rows < 7 declared` fires; a fed round stays quiet") do not pin the
domain either. A ratchet whose population is unstated is the ancestor's death re-run in the other
direction.

### M1 — Medium — §1.1's t7 sentence is wrong about its own measurement
`component: log-schema` · `fix_induced: no`

§1.1 (#325): *"`t7` printed its 74% accuracy bound over 10 scored rows carrying 0 bets — **a sentence
that renders identically whether the ranker was right ten times or never bet**."* Constructed:

```
0 bets   -> "10 scored rows (0 ranker hits) — … the bound reaches 74%"
10 hits  -> "10 scored rows (10 ranker hits) — … the bound reaches 74%"
10 misses-> "10 scored rows (0 ranker hits) — … the bound reaches 74%"
```

It does not render identically against "right ten times"; it renders identically against **"bet ten
times and missed every one."** The real defect is the one the document meant and is still a defect —
the *bound* is quoted regardless — but this sentence is in the section headed *"The measurement, not
the argument"*, and it is an inference stated as a measurement. Three rounds of this slice were each
caught by the next round on this class; the fix is to say "0 hits is indistinguishable from 0 bets."

### M2 — Medium — §2.1's "the UNIT and the ROUND are both identity now" is one word from reinstating the r1 Blocking
`component: log-schema` · `fix_induced: no`

The design needs **three** partitions and names one word for them: `(subject, unit)` for the ladder
(`unit_key`, `group_by_unit`, `derive_routes_tried`), `(subject, round)` for the ratchet, `(subject)`
for t4. If an implementer reads *"both are identity"* as a change to `unit_key`, every row becomes its
own unit, `prior` is always empty, `derive_routes_tried` returns `[]` for every row, strict increase
has nothing to compare and t2 can never fire — which is precisely the r1 Blocking that
`derive_routes_tried` was written to close. §6 contains no case pinning that `group_by_unit` still
ignores `round`. One sentence fixes it; its absence is a loaded gun pointed at the one guarantee the
document's §4 rests on.

### M3 — Medium — §4's stated refuting observation tests the guard, not the property
`component: log-schema` · `fix_induced: no`

§4: *"Observation that would refute it: a unit with two rows whose index does not increase — which
`validate_row` refuses."* An input the guard refuses cannot refute the guard's own theorem; given
strict increase and `|LADDER| = 4` the four-row bound is a **theorem**, and the only way it fails is
the guard not being applied with history. That hole exists and is documented in the code:
`validate_row(row, prior=None)` *"validates the row's own shape only"*, and `None` is the **default**.
So the honest falsifier for §4 is *a caller that validates rows without `prior`* — one exists in the
signature, `main()` is the only caller that gets it right, and §6 adds no case for the new rule's
version of that gap.

### M4 — Medium — a one-row `defer` becomes admissible and immediately reads as "termination refuted"
`component: log-schema` · `fix_induced: yes` (created by §2.2)

With skips admitted and `route_next` redefined, `tried=['defer']` exhausts the ladder in **one row**
(`route_next` → `None`). t2 then fires whenever that unit's last row records `outcome: "continued"` —
which is the honest record for a deferral, since deferring is filing, not fixing. So a legitimate,
properly-cited DEFER prints *"1 unit(s) exhausted every route and still carry findings — the claim
that escalation terminates is refuted, not delayed"* after a single round. Measured: today
`t2(['defer'])` returns **None**, so this is new surface, created by §2.2 and not listed in §3's t2
row, which discusses only the opposite error. `FAILURE_OBSERVATION["defer"]` says *"terminal — nothing
escalates past it"*; t2 needs to agree with it, or the document needs to say that a deferred unit
carrying findings is a genuine refutation of termination (defensible — but it has to be chosen).

### M5 — Medium — the live rows' `ranker` field is deleted by omission, and "inexpressible" is true only of machine-readable data
`component: log-schema` · `fix_induced: no`

All four live rows carry a field §2.1's model does not mention: `"ranker": "abstained — NO LEAD: …"`.
`validate_row` rejects no unknown key, so the abstention **is** in the log — as free text, read by
nothing, checked by nothing. That sharpens #325 (the problem is an unvalidated escape hatch, not
absence) and it means §2.5's `bet` does not *replace* `ranker`: after the change the log carries two
vocabularies for one concern, which is `check-vocabulary-collisions.py`'s subject and the shadow of a
duplicate mechanism. §2.1 says *"one is replaced (`ranker_hit` → `bet`)"* — `ranker_hit` appears in
**zero** live rows and `ranker` in **all four**.

### M6 — Medium — §2.3's `returns_after_gap` derivation lives in the other script, with no owner named
`component: ranker-caller` · `fix_induced: no`

*"`returns_after_gap` is derivable from `component_rounds` today."* True — and `component_rounds` is
in `check-decision-scheme.py:312`, while `review_scope`/`scope_tally` are in
`check-review-decision.py`. The document does not say whether the ranker imports it, or whether a
second gap derivation is written beside `scope_tally`. This repository has measured the second-copy
drift **17 times**, most recently on a two-line split rule. Name the owner in §2.3 and have §6 T5
import it.

### M7 — Medium — strict increase rewrites `review-method.md`'s escalation table, and §6 T7 updates a different thing
`component: log-schema` · `fix_induced: no`

`review-method.md:313-318` is a table whose last column is **"escalates to"**, giving each route a
single successor. §2.2 argues only that *"start at the cheapest route"* is an authored optimisation —
true — but strict increase also converts *route X failed ⇒ X+1* into *route X failed ⇒ any index > X
with a citation*, at every rung, which is a change to the mechanism's documented semantics rather than
to its starting point. §6 T7 updates `§304` "to state the strict-increase rule and the skip citation"
and says nothing about the table that will then be wrong.

### L1 — Low — `route_sequence_error`, reduced to one branch, duplicates a check `validate_row` already makes
`component: log-schema` · `fix_induced: no`

§2.2: *"`route_sequence_error` loses two of its four branches."* Accurate (unknown / duplicate /
order / None → unknown / None). What is left is a ladder-membership test over prior routes, and prior
routes reached `prior` only by passing `validate_row`'s own `row["route"] not in LADDER` check. The
"simpler" claim is stronger than stated: the function can be **deleted**, and keeping a one-branch
survivor whose branch is enforced elsewhere is the duplication the repo guards.

---

## What I could not verify

- **Whether `scope_lead`'s "10 readable / 5 no lead" was true when written.** I measured 11 and 6
  today; the extra subject is this slice itself, which is consistent with the figure having been taken
  before `decision-route-escalation` had two rounds. I report mine as today's, not as a correction of
  the original measurement.
- **Whether `ship-src-root-alone` was parseable when the 3-of-3 fit was taken.** It raises today
  (`disposition='refuted'`). H1's claim is about the falsifier being **measurable now**, which §2.3
  asserts and I falsified; it is not a claim that the original fit was wrong.
- **Anything requiring the mutation harness.** A sweep was in flight; §6 T7's manifest entries are
  unexamined, and #322's repair landed at `740b4df3` without a sweep I could confirm. Treat the
  mutation coverage of every new branch in §6 as **NOT MEASURED** by this half.
- **The Codex half.** Deliberately unread.

---

## Verdict

The document's §1 diagnosis is sound and its §1.1 measurements reproduce to the character — this is
the first artifact in this slice whose central claim I could re-derive without correcting it. The
answers are where it fails. Three are Blocking: **shipping §2.1/§2.5 with §6 T6 returns rc=2 for ever
and deletes the instrument (B1)**; **§2.3 answers #323 with the move #323 forbids and discards the
remedy it prescribes (B2)**; **§2.4 rejects the filed fix by arguing against a different one, on a
ratio taken from a corpus this slice itself corrected (B3)**. Two more are structural: the design
hands the mechanism a lever on its own figure of merit while declaring that trigger unchanged (H2),
and its one self-imposed gate cannot fail (H1).

**NOT CONVERGED** — 3 Blocking / 6 High / 7 Medium / 1 Low.

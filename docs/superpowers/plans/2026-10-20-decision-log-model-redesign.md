# The decision log records a projection of the decisions, and every trigger reads it as the decisions

> **Anchor:** `review-decides-itself` — **ADR:** 0014
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

> ## ⏸️ DEFERRED 2026-10-20 BY THE OWNER — read this before the design below
>
> Both signals this slice relied on are **base rates**, measured over the readable corpus:
> `thrashing_component` arms on **8 of 12** subjects (67%) and `converged()` is false for **12 of 12**,
> because the corpus holds **1 clean round in 48** against a predicate needing two consecutive (backlog #329).
> ⭐ **The mechanism CONSUMES those signals**, so a decision layer over non-discriminating inputs cannot
> work however well it is built. The work moved one level down — **backlog #328** (one `corpus()` owner + a
> denominator guard) and **backlog #329** (make convergence satisfiable).
>
> ⛔ **DEFER is terminal on the ladder — *stop, file it*.** r2's nine findings are **filed, not fixed**;
> §6's tasks are **not** being implemented. The design below stands as the record of what was learned,
> and §1's diagnosis and §1.1's measurements were independently re-derived and hold.
> ⚠ The mechanism cannot record its own deferral: `tried=["redesign"]` for `log-schema`, so `route_next`
> still demands `accrete` — **backlog #321's fourth occurrence**, on the decision that ends the slice.
>
> ## ⟳ CORRECTED 2026-10-21 — THIS DEFERRAL'S STATED PRECONDITION NO LONGER HOLDS, AND PART OF THIS
> ## DOCUMENT HAS SHIPPED. It is a RESUME candidate, not a dead thread.
>
> The deferral above rests on one argument: both signals the mechanism consumes are
> non-discriminating base rates, so *"a decision layer over non-discriminating inputs cannot work
> however well it is built"*, and the work therefore **moved one level down to backlog #328 and
> #329**. ⭐ **Both of those are now ✅ CLOSED** — #328 *"one `corpus()` owner + t6 reads the pinned
> counts"*, #329 *"convergence reads the disposition that already exists"* (both 2026-10-20). The
> condition that justified stopping has been removed.
>
> ⛔ **AND §1.1's FIRST FINDING SHIPPED.** backlog **#321** — the ladder's prefix clause — is ✅ as
> of `ee0e461b` (PR #381, 2026-10-21): a rung is skippable with a required non-empty reason, so the
> two unwritable histories this document measured are now expressible, and the deferral itself is
> recorded in `docs/reviews/decision-scheme/decision-log.jsonl` as the two retroactive rows it
> always should have been. ⚠ So *"r2's nine findings are filed, not fixed"* is no longer true of
> all nine.
>
> ⚠ **WHAT IS STILL OPEN, so this is not read as a green light:** backlog **#314** (the thrashing
> rule ranks by CONSECUTIVE rounds, and consecutiveness is the statistic that loses) is still 🟠,
> and it governs one of the two signals. **#337** and **#338** were filed by #381's own review
> rounds. ⛔ Whether to resume is still the owner's call — this correction changes the EVIDENCE the
> call rests on, not the call.

**This is a DESIGN REVIEW document, not a fold of code.** `review-method.md:178`, quoted rather than
recalled:

> If a component produces findings caused by the PREVIOUS round's fixes in two consecutive rounds, it
> escalates from FIX to REDESIGN, and **the next round is a design review — not another defect hunt.**

⟳ **r1 FOLDED 2026-10-20. Both halves NOT CONVERGED — Codex 1B/4H/3M, Claude 3B/6H/7M/1L — and they
agreed on four defects independently.** Two of this document's own claims were refuted and are
corrected below rather than softened; the fold table in §8 maps all 25 findings. The round record is
[`decision-log-model-redesign-r1-coordinator.md`](../../reviews/coordinator/decision-log-model-redesign-r1-coordinator.md).

---

## 1. The shape

> **The mechanism reasons over `(unit, bet)`. The log records `(subject, prediction)`. Every trigger
> then reads the projection as if it were the thing projected.**

⟳ **THE UNIFICATION IS THREE OF FOUR, NOT FOUR OF FOUR (r1 Claude, structural).** v1 folded backlog #323 in.
It does not belong, and the reason is checkable: `review_scope` ranks components over **round
documents**, never touches the decision log, and has no `unit`, no `bet` and no row — §3's own table
says it *"reads the corpus, not the log"*. **Including it is what let its answer escape the constraint
the rest of this document observes, and that answer collected two of the three Claude Blockings.**
backlog #323 is answered in **§7, outside the model**, and is not evidence for or against the unification.

| # | filed as | the projection that causes it |
|---|---|---|
| **backlog #321** | is the ladder's prefix clause a law or a choice? | the row cannot express a **skip**, so two real routes are unwritable |
| **backlog #324** | `t1_not_fed` is per-SUBJECT while the mechanism reasons in UNITS | the starvation ratchet's domain is the **subject** |
| **backlog #325** | an abstention is inexpressible as data | the bet is projected onto a **boolean**, which has no value for *no bet* |
| ~~backlog #323~~ | ranker saturates at the round count | **NOT this shape** — no unit, no bet, no row. See §7 |

### 1.1 The measurement, not the argument

Driving the real `main()` over a temp copy of the log (ADR-0014 makes `log_path` a parameter, so no
instrument edits its own subject — backlog #326), with the slice's **true** seven-unit history and routes
parsed out of the r1 coordinator document's own table rather than transcribed. ✅ **Every line below
was independently re-derived to the character by the r1 Claude half.**

| unit | route it really took | admissible? |
|---|---|---|
| `relocation` | **SPLIT** | ⛔ *"route 'split' is not the next route … the only route left to bet on is 'accrete'"* |
| `log-schema` | **REDESIGN** | ⛔ same refusal |
| `accounting`, `ranker-caller`, `coverage` | ACCRETE | writable; merely absent |
| `corpus-cannot-run`, `starvation-ratchet` | ACCRETE → REDESIGN | ✅ **the only two in the log** |

⛔ **Writing the truth does not lose two rows — it takes the whole mechanism offline:** `rc=2`,
*"CANNOT RUN — the log holds unusable rows, so no trigger was evaluated."* The five writable units
alone give `rc=0, all triggers quiet`.

> **The log contains exactly the units whose history the schema can express.** `all triggers quiet`
> is not a verdict about the work; it is *caused by* the omission of the decisions the schema refused.

- **backlog #324** — `t1_not_fed` returns `None` at **1, 2 and 7** of 7 logged units; loud **only** at 0. And
  the live domain is one subject (`subjects_starved(armed_at)` → `['decision-route-escalation']`),
  which has a row — so *"the loudest trigger, because it is how the predecessor died at 81%"* is
  bought off by **one row**.
- **backlog #325** — ⟳ **CORRECTED, and the correction is the sharper finding (r1 Codex XM7 + Claude CM5,
  verified by hand before acceptance).** v1 claimed *"today no log can make t5 FAIL."* **That is
  false.** Two rows on distinct units with `ranker_hit: false` both validate, and the real `main()`
  returns **`rc=1, FAIL trigger 5 RANKER MISS`**. ⚠ My own probe had printed `ranker_hit=False ->
  None` on screen and I wrote the opposite sentence beside it. The true, narrower shape: a **miss** is
  expressible; an **abstention** is not (`None` and `"abstained"` both refused, with a message that is
  wrong about its own input — handed `None` it says *"a string coerces to True"*). So an abstention
  must be encoded as absence (invisible to t5 and t7) or as `false` (**scored as a miss**, punishing
  the ranker for declining to guess). That is the defect.
- **t7's real defect** — ⟳ v1's sentence said the 74% bound renders *"whether the ranker was right ten
  times or never bet"* (r1 Claude CM1: wrong about its own measurement). What was measured is one
  arm: **10 scored rows carrying 0 bets print the bound anyway**, and `hits` is reported as `0`. The
  message quotes a bound whose denominator it has just shown to be empty.

### 1.2 Why three rounds could not find this

1. **The fix that caused it was correct.** r1 removed the authored `routes_tried` and **derived** it
   from history, so a *retry* became "inexpressible rather than refused". That was right. The same
   move made a *skip* inexpressible, and nothing asked what else the derivation now **forbade** —
   `a-guard-can-mandate-the-duplication-it-audits`, in a new place.
2. **Append-only couples admissibility to liveness.** `validate_row` refuses a true row, `main`
   treats any unusable row as CANNOT RUN for *every* trigger, and the file cannot be edited. The only
   way to keep the instrument alive was to under-report, permanently.

⛔ **AND v1 REBUILT MECHANISM 2 ONE PAGE AFTER DIAGNOSING IT (r1 XB1 + CB1, both halves).** v1 added
required `round` / `units_decided` / `bet` with no epoch and no grandfathering, while §6 T6 said the
existing rows *"are not rewritten (append-only)"*. Implemented verbatim: **4 of 4 live rows unusable**
(2 of 4 on the narrowest reading) → `rc=2` in CI, for ever, on the author's own rows. §2.1 now carries
the epoch that closes it.

---

## 2. The answer, once

### 2.1 Row model — two row KINDS, and a schema epoch

⟳ **The attempt/observation split is r1's Blocking answered (XB1).** A single row kind cannot carry
both a route claim and its outcome: appending the outcome of a pending REDESIGN either consumes
another rung (a route that was never attempted) or edits an append-only row.

```
# every row
{ "schema": 2, "subject": str, "unit": str, "round": int, "kind": "attempt" | "observation", … }

# kind: "attempt"   — claims a route. CONSUMES a rung.
  "route": one of LADDER,
  "skipped": {"routes": [...], "observation": str}   # REQUIRED iff the route skips a rung
  "prediction": str,
  "bet": {"named": <component>} | {"abstained": <why>},   # REQUIRED on every attempt
  "ranker": str                                            # free prose, PRESERVED (CM5)

# kind: "observation" — scores an earlier attempt. CONSUMES NOTHING.
  "attempt": {"unit": str, "round": int},   # the attempt it scores; must exist and be unscored
  "observed": str,
  "outcome": "stopped" | "continued",
  "hit": bool,                              # REQUIRED iff that attempt's bet NAMED a component,
                                            # REFUSED if it abstained
  "rounds_at_termination": int              # iff stopped
```

⛔ **THE EPOCH, which is what keeps the instrument alive (XB1/CB1).** Every clause above is required
**iff `schema >= 2`**. A row with no `schema` is epoch 1 and is validated by the v1 rules exactly as
today. The four live rows are therefore untouched and remain valid; nothing is rewritten; `main()`
does not refuse them. **Falsifier:** the four live rows must give `rc=0` under the new validator, and
a `schema: 2` row missing `round` must be refused.

⚠ **UNIT IDENTITY IS STILL `(subject, unit)` (CM2).** `round` is an **attribute**, not part of the
key. v1's sentence *"the UNIT and the ROUND are both identity now"* is deleted: making `round` part of
the key would re-partition `derive_routes_tried` and reinstate the r1 Blocking, since a unit's history
would no longer accumulate across rounds.

⭐ **Prospectivity is now structural, not claimed (XH4).** v1 said the log buys *"a bet placed before
the outcome"*, which did not follow: one row could carry prediction and result together. Two kinds in
an append-only file make the ordering observable — an observation row is refused unless the attempt it
names already exists, so the bet is on disk before the scoring is. ⚠ **BOUND:** this orders
*records*, not *reality*. A late import can still append both in sequence, so §6 T6 marks imported
rows `imported: true` and **t5/t7 score only non-imported rows**.

### 2.2 backlog #321 — the prefix clause is a CHOICE, replaced by strict increase

**Why this is not the owner's decision.** Their recorded steers (`review-method.md:304-307`) are *"goal
to make it deterministic may be too strict. Maybe probabilistic ranking and betting on higher side?"*
and *"if we detect the failure of choice … then we should be able to try again with other choices."*
Neither mentions ordering. Termination is carried by *"a route is never retried on the same unit"*
(`:329-332`), and *"you stop when the ROUTES ARE EXHAUSTED"* is the stopping rule. **"Start at the
cheapest route" is an unattributed authored sentence at `:329`** — verified at those lines by the r1
Claude half.

> **THE RULE, STATED ONCE (CH4).** For the attempt rows of one `(subject, unit)` in append order, let
> `i(r) = LADDER.index(r.route)` and define `i(∅) = -1` for a unit with no prior attempt. An attempt
> is **admissible iff `i(route) > i(previous attempt)`**. If it exceeds it by more than one, the row
> must carry `skipped.routes` naming exactly the intervening rungs and `skipped.observation` stating
> the evidence, already in hand, that each cannot work.

⟳ **v1 STATED THIS RULE TWICE AND THE TWO WERE DIFFERENT RULES (CH4).** One was this predicate; the
other was *"`route_next` becomes the lowest-index route above `max(index)`"* — a single-valued
function, which cannot express *"any strictly greater index is admissible"*. Consequences now fixed:

- **The predicate lives in `validate_row` as an INEQUALITY.** `validate_row:478` compares for
  **equality** against `route_next`; v1's §6 T1 never touched it, so implemented as written
  `relocation`'s SPLIT still failed and **backlog #321 stayed open while T1's own first case went red**.
- **`route_next` is demoted to advice** — the cheapest admissible route, used in *messages* and never
  as an admissibility test.
- **The empty history is defined** (`i(∅) = -1`), because **both** histories this design exists to
  admit are first rows of their unit, and `max()` of an empty sequence raises.

⚠ **BOUND.** The guard checks that `skipped.observation` is present, non-empty, and names exactly the
intervening rungs. It cannot check that the observation is **true** — the same posture, and the same
reason, as `prediction` and `observed`.

### 2.3 The skip is a lever on the figure of merit, and that must be neutralised (CH2)

⟳ **ENTIRELY NEW SECTION — the fifth consequence the unification predicted and v1 did not list.**
The figure of merit is **rounds-to-termination**. `t4_no_improvement` compares the median of the last
five terminated subjects against a median of **4 pinned before the scheme shipped** — i.e. measured in
a regime where skipping was inadmissible. §2.2 makes skipping admissible with only a *present*
citation as the check. A unit that skips two rungs terminates in fewer rounds, lowering the very
statistic that decides whether *"the mechanism is ceremony, not leverage."* **v1 marked t4
"unchanged — the comparator stays pinned."** The comparator is pinned; the **quantity compared to it**
is what §2.2 changes.

> **RULE.** `t4` computes its median over subjects **none of whose units skipped a rung**, and reports
> the count it excluded. A skip-bearing subject is never silently folded into a comparison with a
> pre-skip baseline.

**Falsifier:** construct five subjects, each terminating in 1 round via a one-row `defer` with a
citation. Today they lower the median and t4 goes quiet; under the rule t4 must report
`0 comparable subjects, 5 excluded` and **not** claim improvement.

### 2.4 backlog #324 — the ratchet's domain, on the fix that was actually filed

⟳ **v1 REFUTED A FIX NOBODY PROPOSED, ON A CORPUS THIS SLICE ITSELF CORRECTED (CB3 + XM6, both halves).**
Three corrections, all measured:

**(a) The filed fix reads the findings' `component` fields, not a header's unit list.**
`docs/backlog.md:308` asks for *"the unit set derivable from the round documents' `component` fields,
or an explicit declaration of units-not-logged with a reason."* Those fields are what `parse_header`
already extracts and what the architecture review used to produce 13/12/8/6. On this slice:

```
8 components across 3 rounds   (adds `baseline-validation`, which was filed and never routed)
7 routed units
```

so the derivation is **available and over-approximates by exactly one** — and backlog #324's *second* option
exists to absorb that.

**(b) The population figures were from the superseded corpus.** `baseline.json` carries `57` under the
key **`corpus_ORIGINAL_WRONG`**. Re-derived today:

| population | measured | v1 said |
|---|---|---|
| subjects with ≥2 rounds | **82** | 57 |
| subjects with a readable round | **11 = 13.4%** | 10 of 57 = 18% |
| **`(subject, round)` pairs — the rule's own domain** | **46 of 395 = 11.6%** | not stated |

**(c) `units_decided` is dropped (CH3).** v1 put a **round-level** quantity on every row, with no
agreement rule, read through a hook that is **unit**-partitioned (`main()` passes
`prior=seen.get(unit_key(r))`, `:713`) — a per-row validator handed one unit's history structurally
cannot see the round's other rows. That is §1's own diagnosis, one level down, introduced by the
answer to it. And its only mechanical firing was defeated by the same omission it existed to detect.

> **RULE.** The ratchet's domain is `(subject, round)` pairs **that came into scope after
> `armed_at`** — the existing `subjects_starved` restriction, preserved and now stated, because
> `baseline.json` records why: *"a gate red from birth over 57 historical subjects gets switched off"*
> (backlog #56). A pair fires when it has **no attempt rows** and its round document names at least one
> `component`, unless a row declares `units_not_logged: [{unit, reason}]` covering the gap.

⛔ **THE DOMAIN IS NOW PINNED, BECAUSE BOTH READINGS WERE DEFENSIBLE AND OPPOSITE (CH6).** Literal
"in the corpus" → **395** pairs → red from birth → switched off, which is the argument §2.4 uses
against the derived ratchet. Restricted → **4** pairs today. ⚠ And the restriction alone is not
enough: three of those four are `decision-route-escalation` rounds 1-3, whose only rows are epoch-1
and carry no `round`, so they would fire on day one and return `rc=1` in CI. **So the ratchet's domain
additionally starts at a declared `ratchet_epoch` — the first round for which epoch-2 rows exist** —
and the rounds that predate expressible rows are out of domain by construction, not by exception.

### 2.5 backlog #325 — an abstention becomes a value, and t5 stops misreporting (CH5)

> **RULE.** `bet` is required on every **attempt** and is exactly one of `{"named": <component>}` or
> `{"abstained": <why>}`. `hit` lives on the **observation**, required iff the attempt named, refused
> if it abstained. The `ranker` prose field is **preserved** (CM5) — "inexpressible" was only ever
> true of machine-readable data, and deleting the prose by omission would lose the reasoning.

⟳ **"SEMANTICS UNCHANGED" WAS A CHOICE, NOT A NO-OP (CH5).** `marks` is built from the *filtered*
list, and both the index and the denominator printed are indices into that filtered list. Constructed
— misses at log rows 1 and 4, abstentions at 2 and 3, four scored rows — t5 prints *"two consecutive
ranker misses at rows 1 and 2 of 2 scored"*: **three wrong facts** (they are not consecutive, not rows
1 and 2, and there are 4 scored rows). v1 was the section that made this trigger fire for the first
time.

> **RULE.** Consecutiveness is computed over the attempt sequence **with abstentions as gaps** — an
> abstention separates two misses, because the trigger measures the instrument's own run of errors and
> a declined bet is not an error. The message prints **log row numbers** and the **real** scored
> denominator.

> **RULE.** `t7` prints `N scored, M bets, K hits` and **refuses to quote the 74% bound while
> `M < floor`**. The mistyped refusal (`None` → *"a string coerces to True"*) is corrected with it.

⭐ **FALSIFIER:** four scored rows, misses at 1 and 4, abstentions at 2 and 3 → t5 must stay **quiet**
and, with misses at 1 and 2, must name rows **1 and 2 of 4**.

---

## 3. All seven triggers, re-derived

| trigger | verdict | change |
|---|---|---|
| **t1** `not_fed` | **CHANGED** | domain = post-`armed_at` `(subject, round)` pairs from `ratchet_epoch`; component-derived unit set; `units_not_logged` escape (§2.4) |
| **t2** `non_termination` | ⛔ **CHANGED TWICE** | (i) exhaustion must be `route_next(tried) is None`, not `len(set(tried)) < len(LADDER)` — measured: `t2` returns **None** for `[accrete, split, defer]` with `outcome: continued`, so a skipping unit's exhaustion is **skipped by the guard**. (ii) **a one-row `defer` must not read as "termination refuted" (CM4)** — DEFER *is* the answer "stop, file it", and its outcome is expected to be `continued`. t2 fires only when a unit has **≥2 attempts**, the ladder is exhausted, and the last outcome is `continued` |
| **t3** `routes_collapsed` | ⛔ **BROKEN BY §2.1 — r2 YH4, and v2 declared it "unchanged"** | `t3_routes_collapsed` selects rows carrying an `outcome` and then reads their `route`. After the row-kind split the outcomes are on **observation** rows and the routes on **attempt** rows, so it reports `"all 5 scored rows took route None"` over `[accrete, redesign, split, defer, accrete]` — a **false FAIL**, measured. It needs a resolved attempt/observation projection. ⚠ **This is the SECOND trigger an "all seven re-derived" claim has missed** (v1 missed t4), and this time the fix caused it |
| **t4** `no_improvement` | ⛔ **CHANGED (CH2/XH5)** | v1 said "unchanged". It must exclude skip-bearing subjects and report the exclusion count (§2.3). ⚠ **And "terminated subject" is still undefined** — collapsing `stopped` rows by subject counts a subject with one stopped unit and others pending; that definition is **owed and listed in §6 T5** |
| **t5** `ranker_miss` | **CHANGED** | reads `bet`; abstentions are gaps; prints log rows and the real denominator (§2.5) |
| **t6** `denominator_moved` | unchanged | reads the corpus, not the log |
| **t7** `sample_reached` | **CHANGED** | real denominator; refuses the bound under the floor (§2.5) |

⭐ **t2 is why this had to be a design review.** Fixing backlog #321 alone — the handoff's recommendation and
the obvious next move — **disarms the mechanism's primary falsifier** while every gate stays green.

## 4. Termination, and a falsifier that tests the PROPERTY (CM3)

`i(route)` strictly increases within a unit's attempts and `|LADDER| = 4`, so a unit has **at most
four attempt rows**; observation rows consume nothing and are bounded by one per attempt. `defer`
(index 3) is terminal.

⟳ **v1's stated falsifier tested the guard, not the property** — *"a unit with two rows whose index
does not increase, which `validate_row` refuses"*. That asserts the guard refuses what the guard
refuses. **The property-level falsifier, driven through `main()`:** a log in which any unit's attempt
sequence is non-increasing must make `main()` **refuse**, and it must do so when `validate_row` is
reached by the **real** caller — ⚠ the hole is `prior=None`, the documented weaker path a forgetful
caller gets, and a case must drive `main()` rather than call `validate_row` directly.

## 5. What this design refuses, and what would retire it

- It refuses to make `fix_induced` causation observable (measured: 2 of 8 agreement). Not reopened.
- It refuses to verify any authored field's **truth**: `prediction`, `observed`,
  `skipped.observation`, `units_not_logged[].reason`.
- ⚠ **MEASURED BENEFIT REMAINS ZERO.** Four log rows, two scored, no outcome observed for any unit.
  The one datum on the other side is `relocation`'s **5 → 0 → 0** after SPLIT (n = 1) — and
  `relocation` is one of the two units whose history v1's schema **could not express**.
- ⛔⛔ **THIS CONDITION HAS FIRED. r2 returned 4 fix-induced `log-schema` findings and
  `thrashing_component` now returns `'log-schema'` — computed by the tool, not read by me.** The
  route is the owner's: the ladder says **SPLIT** (REDESIGN failed; DEFER is the rung after SPLIT),
  and §5's "not redesign again" is satisfied by SPLIT — but five rounds and an architecture review
  have produced **zero measured benefit**, which is a cost question and therefore theirs. See
  [`…-r2-coordinator.md`](../../reviews/coordinator/decision-log-model-redesign-r2-coordinator.md).
  ⛔ **No third redesign is being written: r2's findings are FILED, not fixed.**
- ⛔ *(original wording, kept so the condition is not quietly reworded after firing)* **Retire this
  document if:** round 2 returns `fix_induced` findings in `log-schema` again — 18 of
  r1's 25 findings were fix-induced *[⟳ the DERIVED figure is **19**; I counted prose, and the
  wrong number is left standing here because this block's purpose is to be unreworded]* and `log-schema` carried 12, so the arming condition would fire on
  a component *inside a document written because it already fired*, which says **DEFER**, not redesign
  again. Or if `(subject, round)` readability passes ~50%, at which point §2.4's component-derivation
  should become the primary rather than the fallback.

## 6. Implementation plan

- [ ] **T1** `validate_row` gains the **inequality** predicate with `i(∅) = -1`; `route_next` demoted
      to advice. Cases: the two refused real histories admit **as first rows**; a non-increasing pair
      refuses; a skip without `observation` refuses; `skipped.routes` not matching the gap refuses;
      an empty history does not raise.
- [ ] **T2** Row kinds + the `schema >= 2` epoch. Cases: the four live rows give `rc=0`; a `schema: 2`
      row missing `round` refuses; an observation naming a non-existent or already-scored attempt
      refuses; an observation consumes no rung.
- [ ] **T3** `t2` exhaustion via `route_next`, **plus** the ≥2-attempts clause. Cases: `[accrete,
      split, defer]` + `continued` FAILS (today it is skipped); a one-row `defer` + `continued` stays
      quiet.
- [ ] **T4** `t1` domain: post-`armed_at` × `ratchet_epoch`, component-derived units,
      `units_not_logged`. Cases: an in-domain round with no attempts fires; the 3 pre-epoch rounds do
      **not**; a declared `units_not_logged` covering the gap stays quiet; `baseline-validation`
      (filed, never routed) is absorbed rather than fired on.
- [ ] **T5** `t4`: exclude skip-bearing subjects, report the count, **and define "terminated
      subject"** — the definition is owed, not assumed.
- [ ] **T6** `bet` / `hit` / abstentions-as-gaps / real denominators in `t5` and `t7`; the mistyped
      refusal corrected; `imported: true` on any retrospective row, excluded from scoring. The five
      unlogged units are appended as epoch-2 attempts with their real routes — **the existing four are
      not rewritten and do not need to be.**
- [ ] **T7** `docs/review-method.md` §304: the escalation table's *"escalates to"* column and the
      prefix sentence both go stale under strict increase (CM7) — update **that table**, and record
      that `returns_after_gap`'s derivation is owned by **`check-decision-scheme.py:312`'s**
      `component_rounds` and imported, never retyped (CM6). ⟳ **r2 YM9: v2 named
      `check-review-decision`, which does not have the function — the wrong module, in the task
      whose whole purpose was naming the owner.** So the relocation is part of the task: the ranker
      lives in `check-review-decision` and the derivation does not.
- [ ] **T8** Mutation manifest entries for every new branch. ⚠ The two subjects' current coverage is
      **62/62 killed, 62 attributed, 0 survivors** (`43`+`19`), measured 2026-10-20 by the harness over
      a pruned `HARNESS_TREE` copy. The full 1,625 sweep is **CI's**, at the PR.
- [ ] **T9** (Low, CL1) delete `route_sequence_error` rather than trim it — the inequality in
      `validate_row` subsumes every branch it has left.

## 7. backlog #323 — outside the model, and it is answered on the terms it set

⛔ **backlog #323's own ⛔, which v1 did not quote and then contradicted (B2 + XM8):** *"Do NOT simply switch
the ranker to finding counts: that is the noise-sensitivity the once-per-round rule exists to prevent
… The honest output is a ranking plus its saturation state"* — *"4 tied at the ceiling, N=3"* is a
different message from *"no component recurred"*.

v1 proposed ranking on `(rounds_appeared, returns_after_gap, total_findings)` and defended
`total_findings` as *"noise-safe at that position because recurrence is already equal."* Measured
refutation:

| | today | v1's tuple |
|---|---|---|
| subjects reporting NO LEAD | **6 of 11** | **2 of 11** |
| `decision-route-escalation` | `NO LEAD — 4 tied at 3` | `log-schema` leads, by **13 vs 12** |

So four subjects **lose** the saturation message backlog #323 asks to have *reported*, and the decider's
margin is **one authored `component` field** in a subject whose per-round volumes ran **22 / 8 / 20**.
Ties at the top are the **majority case** (6 of 11), so in the saturated regime — the one backlog #323 is
about — `total_findings` is not a tie-break, it is the decider.

> **RULE.** Keep the tuple as the **order**. Print the **saturation state as a first-class line**
> whenever `n1 == N_rounds`: the tied set, `N`, and that the lead was won on volume. A lead decided by
> `total_findings` is reported as such, never as recurrence.

⟳ **AND v1'S FALSIFIER COULD NOT FAIL (CH1), which is the one thing a self-imposed gate must not do.**
It said *"must still rank the 3 labelled subjects 3 of 3, and reduce NO-LEAD below 5 of 10."*
Measured: the third labelled subject is **not measurable** — `rounds_for("ship-src-root-alone")`
**raises** (`disposition='refuted'`), so a "3 of 3" over it is a CANNOT RUN reported as a pass; the
other two have **unique** tops, so a tie-break cannot move them and the fit is 2-of-2 by construction;
and adding tie-break keys can only **reduce or preserve** the NO-LEAD count, never raise it. The
baseline was also stale: **6 of 11**, not 5 of 10.

> **FALSIFIER THAT CAN FAIL.** The two subjects where the change actually moves the named component
> have no label: `peer-sites` (`activation` → `parse-hunks`) and `decision-route-escalation`
> (`corpus-cannot-run` → `log-schema`). **For each, the architecture review that convened on it must
> be read and the named component compared.** If either names the component the tuple displaces, the
> tuple is refused. ⚠ And `ship-src-root-alone` must be made parseable (or its `refuted` disposition
> admitted to the vocabulary) **before** any fit over it is quoted — a CANNOT RUN is not a pass.

## 8. Fold table — all 25 r1 findings

| id | half | what changed |
|---|---|---|
| XB1, CB1 | both | §2.1 row kinds + `schema >= 2` epoch; §6 T2/T6 — the live rows stay valid |
| CB2, XM8 | both | §7: tuple kept as order, saturation state reported as a first-class line, backlog #323's ⛔ quoted |
| CB3 | Claude | §2.4(a) the filed fix (component fields); (b) 82 / 11 / 46-of-395; (c) `units_decided` dropped |
| XH2 | Codex | §2.4 counts **attempt rows per pair**, not rows; the arithmetic is gone with `units_decided` |
| XH3 | Codex | §2.4: a pair fires only if its round document names a `component`; a clean round is out of domain |
| XH4 | Codex | §2.1 prospectivity via two kinds + `imported: true` excluded from scoring |
| XH5, CH2 | both | §2.3 (new) + §3 t4 row — skip-bearing subjects excluded, exclusion count reported |
| CH1 | Claude | §7's new falsifier: the two unlabelled movers, and `ship-src-root-alone` must parse first |
| CH3 | Claude | §2.4(c) — the round-level-fact-through-a-unit-hook defect; field dropped |
| CH4 | Claude | §2.2 one rule, in `validate_row` as an inequality, `i(∅) = -1`; T1 rewritten |
| CH5 | Claude | §2.5 abstentions as gaps, log row numbers, real denominator |
| CH6 | Claude | §2.4 domain pinned: post-`armed_at` × `ratchet_epoch`, with the day-one FAIL named |
| XM6 | Codex | §2.4(b) — same correction as CB3(b), reached independently |
| XM7, CM5 | both | §1.1 — the false t5 claim deleted and corrected; `ranker` prose preserved |
| CM1 | Claude | §1.1 — t7's sentence restated to what was actually measured |
| CM2 | Claude | §2.1 — unit identity stays `(subject, unit)`; `round` is an attribute |
| CM3 | Claude | §4 — falsifier tests the property through `main()`; `prior=None` named as the hole |
| CM4 | Claude | §3 t2 — the ≥2-attempts clause, so a one-row `defer` is not "termination refuted" |
| CM6 | Claude | §6 T7 — `component_rounds` named as the owner, imported not retyped |
| CM7 | Claude | §6 T7 — `review-method.md` §304's table updated, not a different thing |
| CL1 | Claude | §6 T9 — `route_sequence_error` deleted rather than trimmed |

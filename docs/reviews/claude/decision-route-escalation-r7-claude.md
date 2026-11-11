# r7 CLAUDE half — adversarial review of the r7 fold (`022f4108`) and the owner change (`1c5376e2`)

Branch `decision-route-escalation`. The Codex half ran first; its four findings are fixed in
`022f4108`, and **the fold is the target of this half**. Mandate: refute.

## Gates I ran myself, and what they said

| Check | Expected (brief) | Observed | Verdict |
|---|---|---|---|
| `python3 scripts/check-decision-scheme.py` | rc=0, trigger-6 WARN only | `6 row(s), 4 scored`; `WARN trigger 6 … rounds_total 392 -> 424 (+8.2%)`; rc=0 | ✅ reproduced |
| `… --self-test` | 179/179 | `179/179 self-test cases passed`, rc=0 | ✅ reproduced |
| scoped mutation sweep | 64/64 killed, 64/64 attributed, 0 survivors | `1 file(s), 64 mutation(s), 64 killed, 64 attributed to the case each names, 0 survivor(s)`, rc=0, 65s | ✅ **re-derived, not taken** |
| `check-plan-code.py --self-test` | — | 215/215, rc=0 (so the `1680` sum pin and the per-file `64` agree) | ✅ |
| `check-selftest-counts.py` | — | `56 script(s) declare a count, every one verified by running it`, rc=0 | ✅ |
| `check-fixture-variation.py` | — | rc=0, 955 parameters examined | ✅ (but see B2 — its question is per-PARAMETER) |
| `check-review-rounds.py` | r7 half-finished | rc=1, `decision-route-escalation round 7: only codex` | ✅ as the fold said; resolves with this file |
| `check-merge-ready.py` | — | **NOT READY** — `CI, mergeability, review rounds` | ⛔ see H4 |

Sweep method: `rsync -a` of all **seven** `HARNESS_TREE` paths into a temp tree, every
`scripts/mutations/*.json` but `check-decision-scheme.json` deleted, `EXPECTED_MUTATIONS` reduced
to that one key **and** the `sum(…) == 1680` case re-pinned to 64 (without the second edit the
control is red and every verdict is an artefact). Control re-proved green at 179/179 before and
after. Separately, every hand-built sever below was run **inside that staged tree** — my first
attempt ran the mutated file from a bare temp dir and all eight "kills" were
`FileNotFoundError` with **zero `[FAIL]` lines**. A crash names nothing; those runs are discarded.

## Findings

| # | Sev | One line |
|---|---|---|
| B1 | **Blocking** | Trigger 1 — the loudest trigger — is green on this branch ONLY because of the two `retroactive: true` rows. CI's own run on the pre-change commit names the same subject. |
| B2 | **Blocking** | Two mutations against the fold's own new `t7` message survive 179/179, one of them restoring Codex M2's exact defect (`13 ranker predictions` over 10 predictions). |
| H3 | High | A retroactive backfill permanently CLOSES a unit's ladder and empties every scoring population while satisfying t1 — three doors, and the written caveat describes one. |
| H4 | High | The fold's `MEASURED AFTER` block reports a locally-run guard subset as "the full ci.yml guard list". Real CI on the branch's pushed head is **red on `verify` for this very subject** and **NOT RUN on `schema-gates`**; neither appears anywhere in the fold. |
| H5 | High | #337's open half should not be Blocking — but its cheap half is implementable now, and leaving it as a prose backlog row is the failure mode this repo has measured. |
| M6 | Medium | `t5` and `t7` now hold TWO different prediction-eligibility rules while the fold claims it borrowed t5's: "one rule, one place". Divergence measured. |
| M7 | Medium | `main()`'s summary line counts retroactive rows (`4 scored`) while every scoring trigger's population is 2. The one number a human reads is the un-split one. |
| M8 | Medium | `t7`'s `74%` is hard-coded for n=10 while `floor` is a parameter: at `floor=3` it states the 95% one-sided bound "reaches 74%" when it is 37%. |
| M9 | Medium | `retroactive` is absent from the module docstring — the schema a row author reads — whose "WHAT THIS CANNOT DO" paragraph still asserts a hindsight label *cannot* be scored. |
| M10 | Medium | #338's refusal reason, applied consistently, refutes the change it defends. |
| L11 | Low | `prospective()` raises `AttributeError` on a non-dict row — the exact class the fold just fixed for `routes_tried`. |
| L12 | Low | `routes_tried: ""` and `()` validate as "no routes tried"; the new type check admits `str`. |
| L13 | Low | `_hit(n, v=True)`'s `v` is never passed a non-default — a dead knob where the miss case should have been. |

---

### B1 — Blocking. Trigger 1 is green because of the retroactive rows, and that is the branch's headline claim

`scripts/check-decision-scheme.py:160` (`prospective`), `:164` (`t1_not_fed`), `:928` (the call).

`prospective()` deliberately does **not** filter `t1_not_fed`, with a written reason: *"a
retroactive row is still a row, and feeding the starvation trigger with real history is the whole
point of the schema change — it proves coverage, not timely use, which is a different complaint."*

**Input** — the live log, `docs/reviews/decision-scheme/decision-log.jsonl`, and the live
`starved()` output:

```
armed_at: 2026-10-20T10:00:00-07:00
starved subjects:    ['decision-log-model-redesign', 'decision-route-escalation']
t1 WITH all 6 rows:  None
t1 WITH the 4 prospective rows:
    1 subject(s) reached >=2 rounds with no log row: decision-log-model-redesign
    — the scheme is not being fed, which is how its predecessor failed at 81%
```

**And CI says the same thing, unprompted.** `verify` on PR #381's head `ea005a3e` — the commit
immediately *before* `1c5376e2` — failed with:

```
decision-scheme: 4 row(s), 2 scored; pinned median 4 vs now 4
  FAIL  trigger 1 NOT FED: 1 subject(s) reached >=2 rounds with no log row: decision-log-model-redesign
```

So the two sides of the experiment already exist in the record: without the two rows, t1 FAILS
naming `decision-log-model-redesign`; with them, t1 is silent. `1c5376e2`'s subject line is
*"trigger 1 goes green by being FED, not patched"* — and `022f4108`, the very next commit, adds a
field whose whole purpose is to declare that those two rows **are not prospective use of the
mechanism**. The branch's headline deliverable therefore reads, after the fold: *trigger 1 goes
green by being fed with rows that are not bets.*

**Why the written reason does not carry it.** "It proves coverage, not timely use, which is a
different complaint" is only sound if *some* trigger owns the timely-use complaint. None does. I
enumerated all seven: t1 starvation, t2 non-termination, t3 route collapse, t4 no improvement, t5
ranker miss, t6 denominator, t7 sample. **Not one asks whether a row was written before its
outcome.** The complaint has no home, so the exclusion is not a division of labour — it is the
only detector of non-use being made satisfiable by backfill. The module docstring makes this the
file's founding concern: *"The predecessor mechanism was correct and saw `rounds=0` on 81% of the
subjects where it applied… A mechanism whose ancestor died of starvation must treat starvation as
its loudest failure."*

**What a fix must change.** Not "t1 reads `prospective()`" — that would demand a prospective row
for a subject whose work is finished, which is unsatisfiable by construction. The honest shapes:

1. **Split t1's answer.** A subject with no row at all stays a FAIL; a subject whose *only* rows
   are retroactive becomes a distinct, named outcome ("fed only in hindsight"), reported rather
   than absorbed into silence. Minimum: the string must name the retroactively-fed subjects.
2. **Make the provenance split visible in the gate's own output** (see M7) so a reader cannot read
   `all triggers quiet` as "the mechanism is being used".
3. Either way, a case must pin it: *t1 over a log whose only rows for a subject are retroactive
   must not be indistinguishable from t1 over a log with prospective rows.* No such case exists.

Severity: Blocking, not High, because this is the branch's stated deliverable and because the
gate's live rc=0 is the thing a merge would be read as having earned.

---

### B2 — Blocking. Two mutations survive 179/179 against the fold's own t7 message, one restoring Codex M2 exactly

`scripts/check-decision-scheme.py:350-356` (`t7_sample_reached`).

The manifest's 64 entries all die (I re-derived that). These two are **outside** the manifest, so
`64/64 killed, 0 survivors` is internally true and still leaves the fix unmeasured in the one
dimension it exists for. Both severs were run in the staged tree over a green 179/179 control.

**Survivor J** — `sample = list(rows)` inserted after `hits` is computed, i.e. the message reports
the row count instead of the sample count:

```
input : 10 rows with ranker_hit: true, plus 3 rows that made no prediction
        (one retroactive defer, one continued, one stopped)
fixed : 10 ranker predictions (10 ranker hits) — re-evaluate now; at 10/10 …
mut J : 13 ranker predictions (10 ranker hits) — re-evaluate now; at 10/10 …
suite : 179/179, rc=0   ← SURVIVOR
```

`13 ranker predictions` over a log containing 10 is **Codex M2 verbatim** — "an accuracy bound
quoted over a sample that did not make predictions" — and the suite cannot tell it from the fix.

**Survivor K** — `hits = sum(1 for r in rows if r.get("ranker_hit"))`, i.e. hits counted over rows
with `.get()` instead of over the sample with `[]`:

```
input : 6 hits, 4 misses, plus one row with ranker_hit: "false"
fixed : 10 ranker predictions (6 ranker hits) — …
mut K : 10 ranker predictions (7 ranker hits) — …
suite : 179/179, rc=0   ← SURVIVOR
```

That re-introduces *both* halves at once: the population error and the `bool("false") is True`
coercion the fold's own commit message calls out as the reason `retroactive` is type-checked.

**Why every existing case is blind to it.** At the point the message is produced, every t7 fixture
has `len(rows) == len(sample)` and every `ranker_hit` is a real bool:

- `_hit(9)` / `_hit(10)` / `_hit(3)` — all rows are predictions.
- `_pred` (10 rows) — all predictions.
- `_pred[:9] + [miss]` — 10 rows, 10 in the sample.
- `_pred[:9] + [retro with ranker_hit]` — 10 rows, 9 in the sample, **but the sample is below the
  floor so the function returns `None` before the message is built.**

So no case ever reaches the `return` with the two populations differing. The ⭐-marked
`…quotes the bound EXACTLY` case pins the whole string — which is the right instinct and the
reason mutation M (`74%` → `99%`) dies — but its fixture makes `len(sample)` and `hits` both 10,
so it cannot separate them either. (The swap mutation `{hits} … ({len(sample)} …)` *does* die, via
`…the hit count is of PREDICTIONS, so a miss is not read as a hit` — that one case is doing real
work.)

This is the defect the fold itself names and fixes one paragraph earlier: *"the THIRD stayed GREEN
while testing nothing it named… it would have passed at ANY N. A case that passes for an ambient
reason is this repository's most-repeated defect."* The replacement has the same shape on a new
axis — not "any N", but "any mix", because the mix is never varied.

Note also that `check-fixture-variation.py` is **green** here and lists `t7_sample_reached.rows`
and `.floor` as varied. Its question is *do two cases pass different values for this parameter* —
and they do. The axis these survivors live on is one level finer: **two populations DERIVED from
one parameter are never made to differ.** That is a new axis for a guard whose own history is a
list of axes (`r2` the want, `r3` the magnitude, `r5` the position, `r6` the other arguments).

**What a fix must change.**

1. One case whose input reaches the message with `len(rows) != len(sample)` **and** a non-bool
   `ranker_hit` present — e.g. 10 bool predictions + 2 prediction-free rows + one
   `ranker_hit: "false"` — asserted against the exact string `10 ranker predictions (10 ranker
   hits) …`. That single case kills J and K together.
2. Two manifest entries in `scripts/mutations/check-decision-scheme.json` naming it, taking
   `EXPECTED_MUTATIONS["scripts/check-decision-scheme.py"]` 64 → 66 and the declared sum
   1680 → 1682.
3. Wrap the new case in `_try` — with the eligibility test removed, `r["ranker_hit"]` is the
   `KeyError` the fold already paid for once.

Severity: Blocking. The code is correct **today** — I verified the fixed outputs above. What is
missing is the falsifier, on a merge candidate, for the exact property the round exists to
establish; and `0 survivors` invites the reader to believe otherwise.

---

### H3 — High. A retroactive backfill closes a unit's ladder for good, and the caveat describes one of three doors

`scripts/check-decision-scheme.py:142-160` (`prospective`), `:505` (the type check), and
`validate_row`'s exhaustion refusal.

The brief's own caveat is that `retroactive: true` "removes a row from every scoring trigger — an
author-controlled silent off-switch". Measured, it does more than that. Four retroactive rows
walking the ladder are each **accepted**, and then:

```
backfilled accrete / redesign / split / defer (all retroactive: true):  validate_row -> None ×4
routes_accounted -> ['accrete','redesign','split','defer']   route_next -> None
now append a REAL prospective row, any route:
    "the ladder is EXHAUSTED for ('live','u') … so this row is a retry after exhaustion"
t1 sees the subject?      None        (starvation satisfied)
t3/t4/t7 population size: 0           (every scoring trigger empty)
```

So one author-controlled boolean, which nothing verifies, buys three things at once: **(a)**
satisfy the starvation trigger, **(b)** empty every scoring trigger, **(c)** make it *permanently
impossible* to record a real prospective bet for that unit, because the ladder is terminal and
`validate_row` refuses every further row. (c) is not in the caveat and is the worst of the three:
it is irreversible in an append-only log.

**Can `retroactive` be derived, as `routes_tried` was in r1?** Partly, and the honest answer is
that it can be *bounded* cheaply and *derived* at real cost:

- **Derivable, in principle.** "Retroactive" means the outcome was observable when the row was
  written. Both halves of that are already in the repo: the row's own write time is
  `git blame`/`git log -L` on its line, and the subject's rounds are
  `docs/reviews/<writer>/<subject>-r<N>-*.md`, whose commit dates `check-review-rounds.corpus`
  already enumerates. A row whose write commit post-dates the last round document of its own
  subject **is** retroactive, mechanically. That makes the lie inexpressible in exactly r1's
  sense. Cost: it needs git, so it carries a CANNOT-RUN path (precedent: `check-backlog-closure.py`
  exits 2 on a shallow clone) and it is the most expensive option.
- **Bounded, cheaply, today.** Pin the count. `retroactive: true` appears twice; a third occurrence
  is then a deliberate edit to a pinned number with a reason, which is what this repo does
  everywhere else. That converts a silent off-switch into a visible one for roughly four lines.
- **Bounded, cheaply, second rule.** Refuse a `retroactive: true` row that is not contiguous with
  the start of its unit's history — i.e. you may backfill a unit's past, never append hindsight
  after a prospective bet. Both live rows satisfy it; it closes door (c)'s general form.

**The honest caveat, if none of those is built**, has to say all three doors and name the
irreversibility: *"`retroactive` is authored and unverified. Setting it removes the row from t3/t4/t7,
leaves it counting toward t1's starvation check, and — if a unit is backfilled to `defer` —
permanently refuses every later prospective row for that unit. Nothing bounds how many rows carry
it."* The caveat as written states one third of that.

---

### H4 — High. "the full ci.yml guard list" was a local subset; CI is red on this subject and the fold does not mention it

`022f4108`'s `MEASURED AFTER` block:

> `full ci.yml guard list    62 steps, GITHUB_BASE_REF=master so the 4 PR-only gates RAN: 60 rc=0,
> 2 rc=1 — and both say THE ROUND IS HALF FINISHED, not that the change is wrong`

Observed, from `check-merge-ready.py` and `gh`:

```
pull request : #381    head ea005a3e    mergeStateStatus BLOCKED
  NO  CI   rc=1   failing: schema-gates, verify
gh pr checks 381:  schema-gates fail | verify fail | mutation-sweep (1..8) pass | …
```

Three separate problems, in increasing order of importance:

1. **The two reds are not the two reds.** The fold names `check-review-rounds` and
   `check-review-recorded`. CI names `verify` and `schema-gates`. Those are different populations,
   and the sentence "both say THE ROUND IS HALF FINISHED, not that the change is wrong" is being
   asked to cover CI's verdict while describing a local sweep's.
2. **`verify`'s failure is this subject.** Its log is the B1 evidence: `FAIL trigger 1 NOT FED …
   decision-log-model-redesign`. It is a real failure of the mechanism under review, at the
   pre-change commit — which makes it the control for B1 and not an environmental artefact.
   `schema-gates`, by contrast, is a genuine **CANNOT RUN**: five failed pulls of
   `public.ecr.aws/supabase/postgres:17.6.1.147` ("Data limit exceeded", then i/o timeout), and the
   script correctly exits 2 saying *"treat this as NOT RUN, never as a pass"*. That half is not a
   defect in the change, and I am saying so rather than counting it.
3. **The change under review has never been in CI at all.** `ea005a3e` is an ancestor of local
   `HEAD`; `1c5376e2` and `022f4108` are unpushed. One commit earlier, `6499cf57` recorded
   *"NO CI RUN HAS EVER EXISTED ON THIS BRANCH, so every 'all green' today was a hand-picked
   subset"*. The `MEASURED AFTER` block is the same shape again, one day later, in the fix for it.

**What a fix must change.** Nothing in the code: the fold's evidence block must either (a) name the
62 steps as *the locally runnable subset* and state plainly that `schema-gates` and `verify` are
NOT RUN against this tree, or (b) push and quote CI. The claim as written is a hand-picked subset
reported in CI's vocabulary.

---

### H5 — High. #337's open half is not Blocking, but it should stop being prose

The brief asks directly whether #337's still-open half should be Blocking on a merge candidate.
**No** — and here is the measurement, not an impression: the live log holds **2** terminated
subjects and `t4_no_improvement` needs **5**, and after the fold both of those are retroactive, so
t4's prospective population is **0**. There is no reachable input today on which the open half
produces a wrong verdict. Calling it Blocking would be a severity invented to express discomfort.

But leaving it as a pending row is the failure mode this repo has already paid for. #337's own
`WORK` field lists three options and its `FALSIFIER` is *"construct a log of 5 subjects, every one
terminated by DEFER at 2 rounds, and run t4"* — a falsifier nobody is scheduled to run, guarding a
hazard that arms silently the moment a fifth prospective termination lands. The cheap half of
option (a) is implementable in this branch, in about four lines:

> In `t4_no_improvement`, a prospective row with `outcome == "stopped"` and `route == "defer"` is
> **not** an improvement datum. Either exclude it and name the exclusion in the message (so the
> denominator cannot be misread), or — more conservative and arguably better — keep it and have the
> function report that *k of the last five terminations were deferrals*, so the reader sees the
> composition instead of a median.

⚠ Do not take the naive exclusion without noticing its corollary: a mechanism that defers
everything would then starve t4 into permanent silence, which is the same silent-off-switch family
as B1. That is why I prefer "report the composition" over "drop the rows". The schema change
(option (b), a third `OUTCOMES` value) remains the honest and expensive one and is correctly the
owner's call, not a reviewer's.

So: **not Blocking; High, as the recommendation to mechanise the latent/live boundary now rather
than to leave a remembered caveat.**

---

### M6 — Medium. "one rule, one place" shipped as two rules in two places

`scripts/check-decision-scheme.py:289` (t5) vs `:350-351` (t7).

The fold's claim, in both the commit message and the t7 docstring: *"This is `t5_ranker_miss`'s own
rule, which t7 had failed to borrow — one rule, one place… presence of an explicit BOOL is the
eligibility test, exactly as t5 has it."*

It is not what t5 has. t5 is `"ranker_hit" in r` plus `bool(r.get("ranker_hit"))`; t7 is
`isinstance(r.get("ranker_hit"), bool)`. Measured divergence:

| `ranker_hit` | t5 eligible? | t5 reads it as | t7 eligible? |
|---|---|---|---|
| `True` / `False` | yes | hit / miss | yes |
| `0` | yes | **miss** | **no** |
| `1` | yes | **hit** | **no** |
| `None` | yes | **miss** | **no** |
| `"false"` | yes | **hit** (coercion) | **no** |
| `""` / `[]` | yes | **miss** | **no** |

Demonstrated end to end on two rows with `ranker_hit: 0`:

```
t5: two consecutive ranker misses at rows 1 and 2 of 2 scored — re-fit or retire the ranking
t7 (floor=2): None
```

`validate_row` refuses a non-bool `ranker_hit`, so `main()`'s path is protected — but these are
documented pure helpers, the divergence is live in the API, and the repo's own standing lesson is
`a-second-implementation-of-one-rule-drifts` (17 recorded instances). Here the second
implementation shipped *in the commit that claims to have removed the duplication*, which is worse
than an ordinary drift because the docstring now tells the next reader the two agree.

**Fix:** one helper — `def is_prediction(row) -> bool: return isinstance(row.get("ranker_hit"),
bool)` — called by t5 and t7, with a case pinning that t5 and t7 agree on the whole table above,
and a manifest entry severing t5's call site (otherwise nothing holds the unification).

---

### M7 — Medium. The summary line counts retroactive rows, so the number a human reads is the one that hid Codex H1

`scripts/check-decision-scheme.py:944-946`:

```python
scored = [r for r in rows if r.get("outcome") in OUTCOMES]
print(f"decision-scheme: {len(rows)} row(s), {len(scored)} scored; …")
```

Live output: `decision-scheme: 6 row(s), 4 scored`. Measured populations behind it: **4**
prospective rows, **2** prospective scored rows, and therefore `len(t3's scored) == 2` — below
every scoring trigger's floor. So the gate tells a reader "4 scored" while the number every scoring
trigger computes over is 2, and it does so in the one line the reader actually sees.

This is the same substitution Codex H1/M2 found inside t3 and t7, left behind in `main()` — and it
matters more than an ordinary cosmetic, because the provenance split is now the thing a reader must
know to interpret `all triggers quiet` (B1). The brief asked whether `main()`'s summary counts
retroactive rows and should. It does, and it should not — or rather, it should count both and say
which: `6 row(s), 4 scored (2 retroactive, so 2 scoreable)`.

**Fix:** derive the line from `prospective(rows)` and print both numbers; one case pinning the whole
string over a log containing a retroactive row; one manifest entry.

---

### M8 — Medium. `74%` is pinned to n=10 while `floor` is a parameter

`scripts/check-decision-scheme.py:354-356`. The bound is the Clopper-Pearson one-sided 95% lower
limit for k=n successes, `0.05 ** (1/n)` — 37% at n=3, 74% at n=10, 94% at n=50. The message hard-codes
`74%` and interpolates `{floor}`:

```
floor=3  : 3 ranker predictions (3 ranker hits) — … at 3/3 the one-sided 95% accuracy bound reaches 74% …
floor=50 : 50 ranker predictions (50 ranker hits) — … at 50/50 the one-sided 95% accuracy bound reaches 74% …
```

At `floor=3` the true figure is 37% — which is the *pre-scheme* bound the docstring quotes as the
thing 10/10 would improve on, so the message states the improvement and the baseline as the same
number. The only case about the parameter —
`the sample floor is a parameter, so three predictions reach a floor of three` — asserts
fires/quiet and never looks at the text, so this is invisible to the suite. (`main()` only ever
calls the default, so no live output is wrong today; this is a latent false claim behind a
parameter the suite exercises.)

**Fix:** derive it — `f"reaches {0.05 ** (1 / floor):.0%}"` — or drop `floor` as a parameter and
pin 10. Deriving is better: `t7_sample_reached.floor` is in `check-fixture-variation`'s varied list,
so the parameter has to stay exercised. Add a case asserting the whole message at a non-default
floor.

---

### M9 — Medium. `retroactive` is not in the schema an author reads, and that docstring now contradicts the field

`scripts/check-decision-scheme.py:1-78` is the module docstring: it is where the mechanism, the
ladder, the skip rule (`skipped` + `why_skipped`, with the owner's decision cited) and the
"WHAT THIS CANNOT DO" caveat all live. **`retroactive` appears nowhere in it.** Grepped: outside
function docstrings the field is documented only in `docs/roadmap-to-launch.md` and
`docs/backlog.md` — process history, not schema.

Worse, the caveat that is there now says something the schema no longer supports:

> *"What the log DOES buy, and the reason it is append-only with `outcome: null` on arrival, is that
> the PREDICTION is written before the outcome is known. A bet placed in advance can be scored; a
> label written with hindsight cannot, which is exactly what backlog #314 records."*

A label written with hindsight is now *expressible and accepted* — that is the fold's whole
mechanism. The paragraph reads as a guarantee about the data and is a statement about intent.

**Fix:** the field belongs in the module docstring beside `skipped`/`why_skipped`, with its three
consequences (H3) and the fact that nothing verifies it; and the `#314` sentence must say that
hindsight labels are recordable, flagged, and excluded from scoring — not that they cannot exist.
`scripts/check-canonical-source.py` is the guard that cares about one-place descriptions; it is
green today because nothing declares this field a canon, which is itself the gap.

---

### M10 — Medium. #338's reason for not building skip provenance, applied consistently, refutes the change it defends

#338 as filed: *"Building a field for a consumer that does not exist is speculative, and this repo
has a measured rule against that."* The premise is **verified** — I grepped every `.py`, `.yml` and
`.sh` under `scripts/`, `.github/` and `.claude/`: the only reader of
`docs/reviews/decision-scheme/decision-log.jsonl` is `check-decision-scheme.py` itself. There is no
training consumer, so Codex's limitation ("I could not demonstrate actual model contamination") is
correctly stated and #338's deferral is defensible on its own terms.

The problem is that the same principle deletes the justification for the thing being defended. The
module docstring's reason for recording skips at all is:

> *"Forcing ACCRETE first is the only thing that produces the label 'accrete was tried on this
> shape and failed', which is the training data the long-term route-predictor needs… a skip is a
> labelled example (shape X, human judged A/R futile, went to S, outcome Y)."*

That consumer does not exist either. So either (i) "no consumer yet" is a reason to defer a field,
in which case it is equally a reason to doubt that the skip label earns its cost today — and the
change's justification has to be re-stated as *the human record*, which is a different and smaller
claim; or (ii) building ahead of the predictor is legitimate, in which case #338 is as justified as
`why_skipped` and the deferral needs a different reason (cost, or the owner's priority).

I am not arguing for (i) or (ii) — the owner picks. I am saying the branch currently holds both,
and the two are load-bearing in opposite directions one paragraph apart.

**Fix:** amend #338's reason to the one the owner actually holds, or amend the docstring's
justification to the human record. One sentence either way.

---

### L11 — Low. `prospective()` raises on a non-dict row, the class the fold just fixed next door

`scripts/check-decision-scheme.py:160`. `prospective([None])` → `AttributeError: 'NoneType' object
has no attribute 'get'`. Codex M4's finding was precisely this shape one function away
(`list(None)` out of the validator), and the fold's answer there was *"a type is named, never
coerced"*, with the sibling case `a non-object row is NAMED rather than raising` for
`validate_row(None)`. The new helper does not adopt that posture. `main()` validates before calling
any trigger, so this is unreachable in the gate — hence Low, not Medium — but it is the fold
re-introducing the class it fixed, in the function it added.

---

### L12 — Low. `routes_tried: ""` and `()` validate as "no routes tried"

`scripts/check-decision-scheme.py:570`: `isinstance(row["routes_tried"], (list, tuple, str))`
admits `str`, and `list("") == []`, so:

```
routes_tried=""  -> None  (accepted)
routes_tried=()  -> None  (accepted)
routes_tried={}  -> "routes_tried is dict, not a list — it is DERIVED now and need not be written"
```

The suite's case `…and every malformed shape reports rather than crashing the caller` passes
`"accrete"` and asserts only *does not raise* — so a string is deliberately in scope, but the
empty-string accept is not what "not a list" says. Low because the field is derived and redundant
now; the clean form is `isinstance(..., list)` plus an explicit tuple allowance if JSON ever needs
it, which also lets the error message be true.

---

### L13 — Low. `_hit(n, v=True)`'s `v` is never passed a non-default

`scripts/check-decision-scheme.py:1480-1482`. All three call sites are `_hit(9)`, `_hit(10)`,
`_hit(3)`. The knob that would have produced a mixed-value fixture exists and is unused — and a
mixed fixture is exactly what B2 needs. Worth taking as the smallest signal of B2's root cause
rather than as a style note.

---

## What I attacked and found SOUND (stated so the gaps are visible)

- **`prospective()`'s exclusion of t2.** Correct, and for the stated reason: exhaustion is observed.
  I checked the converse too — including retroactive rows lets a backfill make a unit *exhausted*,
  which is real and is H3's door (c), not a t2 defect. On the live log t2 is quiet for the right
  reason: `log-schema` is exhausted (`routes_accounted == ['accrete','redesign','split','defer']`,
  `route_next → None`) and its last row's outcome is `stopped`, not `continued`.
- **`prospective()`'s exclusion of t5.** Consistent — t5 is keyed on `ranker_hit`, which no
  retroactive row carries. (The *rule* it is keyed on is M6's problem, not this exclusion's.)
- **t3 falling below its floor when retroactive rows are dropped.** I built the adjacent input —
  4 prospective collapsed ACCRETE rows + 1 retroactive ACCRETE row. With all rows t3 fires ("all 5
  scored rows took 'accrete'"); with `prospective()` it is quiet at 4. That is the floor doing its
  job over the population t3 now claims to be about, not a hole.
- **`any(ch.isalnum() …)` on non-Latin scripts.** Measured: `日本語で説明` ✅, `Ι` (Greek) ✅,
  `٣` (Arabic-Indic digit) ✅, `→ see #337` ✅; refused: `—`, `⛔⛔`, `«»`. I could not construct a
  reason a real author would write that this rejects. The docstring's own limit — content, not
  meaning — is correctly stated, and the rule is covered: severing it reddens exactly the two cases
  that name it.
- **The retroactive rows' value AS DATA — the brief's least-confident question. The fix did NOT
  destroy it.** Measured: the skip labels are still readable
  (`decision-log-model-redesign redesign skipped ['accrete']`, `… defer skipped ['split']`),
  `derive_routes_tried` still returns `['redesign','defer']`, `routes_accounted` still returns all
  four rungs, and `route_next` still reports the ladder terminal. `retroactive` is read by exactly
  one function, `prospective()`, which exactly three triggers call. Nothing else in the repo reads
  the log at all. So the flag scopes the rows out of the three *scoring* triggers and touches
  nothing else — and the scoring triggers were never the consumer the rows exist for. The rows'
  weakness as labelled examples is the one #338 names (rule-imposed vs judgement-imposed is not
  encoded), which predates the fold and is unaffected by it. **Answer: no, and the fix was the
  right trade.**
- **The three rewritten t7 cases** do now supply what they name — that part of the fold is real.
  Severing t7's prospective filter, its eligibility test, the `retroactive` type check, the alnum
  rule and the `routes_tried` type check each reddens with correctly-attributed `[FAIL]` lines and
  no traceback (`_try` is load-bearing and is used). The gap is only the un-varied mix (B2).
- **`EXPECTED_MUTATIONS` bookkeeping.** 64 for this file, declared sum 1680, `check-plan-code.py
  --self-test` 215/215, `check-selftest-counts.py` green at 179 by running it. All consistent.

## NOT RUN (so nobody reads silence as a pass)

- **`schema-gates` against this tree.** CI's run on `ea005a3e` could not pull the Postgres image
  (5 attempts, "Data limit exceeded" / i/o timeout) and exited 2 saying so. I did not run
  `scripts/check-schema-gates.sh` locally. This change touches no schema, so I expect nothing from
  it — but it is NOT RUN, not green.
- **`verify` against this tree.** The only CI evidence is from the pre-change commit, where it
  FAILED (B1's control). The two commits under review have never been through it.
- **The whole-manifest sweep.** I ran the single-manifest scoped form (64 entries, 65 s). The
  1,680-entry ratchet is CI's job and CI has not seen this tree.

## The one thing I would act on first

B1. Everything else is a defect in code or in a number; B1 is the branch's headline claim resolving,
under its own new field, into its opposite — and CI has already printed both sides of the
experiment without being asked.

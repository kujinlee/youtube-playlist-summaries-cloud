# Adversarial review — `review-identity-176` (backlog #176), ROUND 3, Claude half

**Subject:** `f54b6240` — *"A negative schema was read as an old era, which is the FOURTH way
malformed testimony switched this check off"*, the fold of round 2's Codex half. Branch
`review-identity-176`, base `origin/master` (`b2e10e39`). Whole-branch context: `4c29fe25`,
`bd784721`, `d02ab66b`, `4e60c5d8`, `f54b6240`.

**Counts:** 0 Blocking · 2 High · 2 Medium · 1 Low

**Verdict: NOT CONVERGED.**

---

## ⭐ THE ENUMERATION QUESTION, ANSWERED FIRST

> *Is there a FIFTH shape — and is the record validation now a rule, or still a list of patches?*

**It is still a list of patches, there is a fifth shape, and I found it in the one field nobody has
looked at.** I enumerated every field a consumer reads from a verdict record and drove a hostile
value through each on the delivered code. The table is the answer; the evidence for each row is in
the findings below.

The producer `codex-review.verdict_record` (`scripts/codex-review.py:702-716`) writes **13** fields.
Two scripts consume them.

| field | who reads it | validated? | what a hostile value does |
|---|---|---|---|
| `gate_ran` | `read_verdicts:360`, `verdict_problems:304`, **`check-review-recorded.classify_verdict:766`** | present+`bool` in `check-review-rounds` only | ✅ closed there (r2 Claude H1). ⛔ **the OTHER consumer still reads it on truthiness** → H2 |
| `schema` | `schema_of:206`, `era_split:239`, `verdict_problems:293`, `read_verdicts:346,371` | `int`, not `bool`, `>= 1` | ✅ closed for the value (r2 Claude L1 + r2 Codex High). ⚠ the *return* is re-collapsed by `or 0` at three sites → M2 |
| `refused` | `era_split:237`, `verdict_problems:291`, `read_verdicts:370` | `bool` or `None`, at `>= TRUSTED_SCHEMA` | ✅ closed (r1 Codex, r2 Claude M1) |
| **`review`** | `verdict_problems:295,305,312` | ⛔ **NOT AT ALL** | ⛔ a `list`/`dict` → `TypeError` out of the check, **rc 1**, no caveat printed. A wrong-typed scalar with `gate_ran:false` → **0 problems**, silently → **H1** |
| `reason` | `verdict_problems:308,314` | no | f-string only; a newline widens a message. Cosmetic, not a silencer. Not a finding |
| `head` | `check-review-recorded.classify_verdict:768` | non-empty `str` | ✅ closed |
| `dirty` | `classify_verdict:771`, `reviewed_map:783` | `None` sentinel only | ⛔ a non-`dict`, non-`None` (`"oops"`, `[]`, `42`) → `USABLE` with an **empty** reviewed map → the vacuous overlay r11 Medium closed for `{}` vs `None`, reachable again through a type → part of **H2** |
| `tool`, `exit_code`, `model`, `attempts`, `intrusions`, `prompt` | nobody, or a comment says deliberately not | n/a | `exit_code` is *deliberately* not consulted, with a case (`:713`). The rest are unread. Not findings |

**So the set closes in one move, and the move is not a fifth patch.** `read_verdicts` is already the
one place that decides whether a record can be read — it validates three fields there. `review` is
the join key, is read three lines later, and is the only field it skips. A **validating reader that
states the type of every field it will hand on** — the shape `coverage_verdict.py` already records
as the fix for this exact enumeration (*"the rounds were not failing. They were ENUMERATING, one
consumer per round, through a set a real interface closes in one move"*) — does three things a fifth
patch does not:

1. it closes `review` (H1) and `reason` in the same edit;
2. it makes the **next** field added to `verdict_record` fail loudly in `read_verdicts` rather than
   silently, which is the property four rounds of patching has not bought;
3. it gives the second consumer something to import, which is the whole of H2.

⚠ **AND THE REACHABILITY ARGUMENT CUTS THE OTHER WAY, WHICH IS THE PART I WANT ON THE RECORD.**
None of the five shapes is reachable from `verdict_record`: it coerces with `bool()`, `int()` and an
f-string, so its output is always well-typed (I checked — 186/186 records on disk carry `str`
`review` and `bool` `gate_ran`). `refused: "false"`, `gate_ran: "false"`, `schema: "3"` and
`schema: -1` were **equally** unreachable, and each was accepted as a real finding and fixed. Either
the fifth is a finding on the same footing, or the class was never about reachability — in which
case the answer is the validator, not a sixth round. I have filed it as a finding, because the
slice's own four precedents say that is the consistent call.

---

## What I verified GREEN, by running it

**Every claim in `f54b6240`'s message, re-derived.** Commands and output, not characterisation.

### The declared self-test counts, by RUNNING each suite

```
$ python3 scripts/check-review-rounds.py --self-test | tail -1 ; RC via PIPESTATUS
64/64 self-test cases passed                       RC=0   (docstring declares 64 ✓)
$ python3 scripts/codex-review.py   --self-test → 168/168 passed   (docstring declares 168 ✓)
$ python3 scripts/check-plan-code.py --self-test → 131/131 passed
$ python3 scripts/check-selftest-counts.py
self-test counts: 46 script(s) declare a count, every one verified by running it   RC=0
```

### `EXPECTED_MUTATIONS`, by LOADING the module and counting the manifests

```
declared sum: 1024 files: 53
manifest total: 1024 files: 53
(no per-file MISMATCH lines)
```

Per-file agreement, not just the sum — including the row this commit moved,
`scripts/check-review-rounds.py: 24 → 25`.

### The anchor sweep — 1032 anchors, 0 orphans, using the harness's OWN rule

Applied `src.count(find) > 1` → dup, `find not in src` → orphan, **sequentially per mutation**
(`check-plan-code.py:1603-1617`), over every entry of every `scripts/mutations/*.json` against the
delivered files:

```
anchors=1032 orphans=0 dups=0 unknown_file=0
```

This matches the coordinator's measurement exactly. It is the check that caught round 2's Blocking
and it is still in no local suite.

### …and an anchor that BINDS also MEASURES — the four `schema` mutations driven

Staged a copy of the tree under a redirected `$HOME`, applied each mutation, ran the named suite,
restored:

| mutation | rc | failing cases | reds through the case it NAMES? |
|---|---|---|---|
| r2: the consumer's schema threshold drifts above the producer | 1 | 2 | ✅ |
| r2 Claude L1: malformed `schema` stops being unreadable | 1 | 3 | ✅ (all 3 named) |
| r2 Claude L1: ABSENT `schema` becomes unreadable | 1 | 4 | ✅ (both named) |
| **r2 codex: a negative schema read as an old era** (new this commit) | 1 | 2 | ✅ **both named cases** — `a NEGATIVE schema is unreadable…` and `…and an EXPLICIT 0 is unreadable too…` |

The commit's claim *"reds through BOTH named cases"* holds.

### `schema_of` in both directions

`schema_of(-1) → None`, `schema_of(0) → None`, `schema_of(1) → 1`, `schema_of(3) → 3`,
`schema_of({}) → 0`, `schema_of(True) → None`, `schema_of("3") → None`. As stated.

**Is `>= 1` right for every caller?** Yes, as far as I can drive it. There are exactly three call
sites and all three ask the same question (*is this record at or above the trusted era*). A schema
*above* the producer's current version (`{"schema": 999}`) is read as trusted — I drove it, it gives
`checked=1` and the join runs. I considered filing that and **decided not to**: `>=` is the normal
forward-compatible reading, the producer's stamp is pinned to clear the consumer's threshold by a
case that reads `codex-review.py`'s literal from source (`:701-708`), and a record from a *future*
era whose `review` field means something else is a hazard no consumer can detect from the number
alone. Manufacturing it would be a finding invented to look thorough.

### Every `check-*` gate named in `ci.yml`

All `rc=0` except two, both expected and neither a finding:

* `check-review-recorded.py` → `rc=1`, *"2 round(s) ran and guarded code was committed after every
  one of them … the closest never saw scripts/check-plan-code.py, scripts/check-review-rounds.py,
  scripts/mutations/check-review-rounds.json"*. That is precisely the round-3 obligation this commit
  creates, and this review is it.
* `check-plan-code.py` with no argument → `rc=2` *"CANNOT RUN — nothing to do"*. That is the retired
  plan mode refusing by design; CI invokes it as `--mutate .`, which I did not run per the brief.

`check-review-rounds.py` itself: **rc=0**, `186 codex-review verdict(s) read, none contradicted`,
`335 rounds parsed, 18 pre-existing exemptions, 0 silent gaps`.

---

## Findings

### H1 — `review` is the join key, it is the only field no one type-checks, and a `list` value turns this check into an rc-1 traceback that prints nothing

**Premise.** `verdict_problems` reads the join key at `scripts/check-review-rounds.py:295` as
`review = rec.get("review") or "(unnamed)"` and then uses it as a **set membership key** at `:305`
and `:312`. `read_verdicts` validates `gate_ran`, `schema` and `refused` and does not look at
`review` at all.

**Measured on the delivered code**, a record `{"schema": 3, "gate_ran": true, "refused": false,
"review": ["review-identity-176-r1-codex.md"]}` dropped into a scratch copy of `docs/reviews/`:

```
$ python3 scripts/check-review-rounds.py ; echo RC=$?
RC=1
  File ".../scripts/check-review-rounds.py", line 312, in verdict_problems
    elif review not in review_names:
TypeError: cannot use 'list' as a set element (unhashable type: 'list')
--- stdout was EMPTY ---
```

A `dict` does the same. This inverts **three** properties this branch already paid rounds for:

1. **rc 2 vs rc 1 — the r2 Claude L1 finding, byte for byte, one field over.** That finding's own
   words: *"`main` reports an uncaught exception as rc 1 (contradictions were FOUND) rather than
   rc 2 (this check CANNOT RUN) — inverting the one distinction this guard maintains deliberately."*
   `schema` was fixed; `review` does it again through a different type.
2. **the era caveat — r1 L2.** stdout was empty: the exception is raised inside `audit()`, *before*
   `main` reaches the `print`. The r1 L2 fix moved that caveat above the early returns so *"the
   reader hitting a RED run"* could not miss it. This path is a red run with no caveat.
3. **the join itself**, which is what #176 was convened over.

**And the silent direction, which is the fifth shape proper.** A scalar of the wrong type is worse
than a crash because nothing is reported:

```
gate_ran=FALSE review=int 3   → records=1 problems=0
gate_ran=FALSE review=null    → records=1 problems=0
gate_ran=FALSE review=""      → records=1 problems=0
```

A verdict saying *the gate did not run*, naming its review by a key nothing can match, produces
**zero** problems and is **not** reported as unreadable — the r1 B1 direction switched off by
malformed testimony, which is the exact sentence the r2 Codex High used about `refused`.
(With `gate_ran: true` the same records are at least loud: `problems=1`, falsely accusing.)

**Why High, not Blocking.** It is not reachable from `verdict_record`, which builds `review` from
`review_filename(review_id)` — always a `str`. Neither were the four already fixed. Not Blocking
because no record on disk carries it: I derived `review` field types over the whole corpus and got
`Counter({'str': 186})`.

**Proposed fix — and it should be the validator, not the fifth patch.** In `read_verdicts`, beside
the three existing clauses:

```python
_rev = rec.get("review")
if not isinstance(_rev, str) or not _rev.strip():
    bad.append(f"{p.name}: `review` is {type(_rev).__name__}, not a review filename — the join "
               f"key is unreadable, so neither direction of the contradiction can be decided")
    continue
```

It can be held at **every era**, not only above the cutover: measured, 186 of 186 records carry a
`str`. Then delete the `or "(unnamed)"` sentinel at `:295` (see L1). Two mutations: one per
direction, each naming its own case.

**Structural.**

---

### H2 — the second consumer of the same records still reads `gate_ran` on truthiness, and `dirty` by identity only

**Premise.** `scripts/check-review-recorded.py` reads the same `docs/reviews/verdicts/*.json`. Its
`classify_verdict` (`:766`) is `if not rec.get("gate_ran"): return None, SKIP` — the truthiness
idiom r2 Claude H1 removed from the sibling five lines from where r2 Codex removed it from
`refused`.

**Measured** by loading the module and driving `classify_verdict({"gate_ran": v, "head": <40 hex>})`:

```
gate_ran=True     -> (head, 'usable')
gate_ran=False    -> (None, 'skip')
gate_ran='false'  -> (head, 'usable')      ⛔
gate_ran='no'     -> (head, 'usable')      ⛔
gate_ran='0'      -> (head, 'usable')      ⛔
gate_ran=1        -> (head, 'usable')      ⛔
```

A round whose gate did **not** run — recorded as the string `"false"` — is credited by this gate as a
round that **saw the final tree**. That is the fail-open its own docstring says was worth extracting
the function for: *"deleting the `gate_ran` test turned a verdict reading `"gate_ran": false` into
testimony that a round saw the final tree (exit 2 → exit 0)"*. The test is present and the idiom
defeats it.

**And `dirty` by identity only** (`:771`, `:783`):

```
dirty=None    classify-> unusable   reviewed_map-> {}     (correct, r11 Medium)
dirty='oops'  classify-> usable     reviewed_map-> {}     ⛔ vacuous overlay
dirty=[]      classify-> usable     reviewed_map-> {}     ⛔
dirty=42      classify-> usable     reviewed_map-> {}     ⛔
```

`classify_verdict` tests `rec["dirty"] is None`; `reviewed_map` independently returns `{}` for
anything that is not a `dict`. r11 Medium closed exactly this — *"an empty map is exactly the shape
that makes every dirty-overlay comparison vacuous"* — for the `{}`-vs-`None` pair, and a type
reopens it.

**What makes this a finding about THIS slice rather than an unrelated bug.** The r2 Claude H1 fix
declared the class closed inside one file (*"one rule, three call sites"*), and the fourth site is in
the sibling consumer of the same records. `check-review-recorded.py` **already imports**
`has_gap_line` from `check-review-rounds` so *"both gates read one grammar"* (`:1079`, `:1138`) — the
seam exists, is used, and the rule this slice spent four rounds writing is the one not shared.

**Stated mitigation, not papered over.** Both scripts run in CI, so a non-`bool` `gate_ran` makes
`check-review-rounds` exit 2 and the build red regardless. That mitigation is an **undeclared
cross-file invariant** — no comment claims it, no case asserts it, and it evaporates if the two
scripts ever run in different jobs on different triggers (`check-review-recorded` is already a
*PR-only* step at `ci.yml:480` while `check-review-rounds` is not). This is the *second
implementation of one rule drifts* shape, measured 17 times in this repo.

**Proposed fix.** The validator from H1 is the natural home: have `check-review-recorded` obtain its
records through the same reader, or at minimum import a shared `gate_ran_of(rec)` predicate the way
it already imports `has_gap_line`. Failing that, `rec.get("gate_ran") is not True` at `:766` and an
`isinstance(d, dict)` gate before `classify_verdict` returns `USABLE`.

**Pre-existing — this branch does not touch `check-review-recorded.py`.** I am filing it because the
round's mandate is to enumerate what every consumer does with these fields, and this is what the
other consumer does. Whether it lands here or as a backlog row is the coordinator's call; what it
must not do is stay unrecorded.

**Structural.**

---

### M1 — a frozen count that was wrong when it was written and is wronger now, ~40 lines below this file's own rule forbidding frozen counts

**Premise.** `scripts/check-review-rounds.py:349-353`:

> *"Measured over the corpus at this commit: 185 of 185 records carry a real bool (179 True, 5 False
> pre-cutover, 1 True after)"*

**Measured.** Derived from the committed records at both commits via `git ls-tree` + `git show`:

| | total | True | False | post-cutover |
|---|---|---|---|---|
| `4e60c5d8` — the commit that WROTE the sentence | **185** | **180** | 5 | 1 |
| `f54b6240` — HEAD | **186** | **181** | 5 | **2** |
| the sentence | 185 | 179 | 5 | 1 |

It was wrong at birth: **179 + 5 = 184**, not the 185 the same sentence claims — the parenthetical
does not add up to its own total. And it is now stale by one more in every column, because *this
commit* added `review-identity-176-r2-codex.verdict.json`.

**Why that severity.** This is the `⚠ AND THE COUNTS ARE DERIVED, NEVER QUOTED (r1 M3)` block's own
defect, 160 lines below where that block memorialises it (*"This paragraph used to state '183
verdicts, 58 (32%)'; the true figure was 184 … The denominator moves every run, so any frozen copy
is stale by construction"*). A rule stated in a file and broken in the same file is the *document
inside the corpus it measures* shape, and it went past four reviewers.

The **direction** the sentence supports still holds — I re-derived it: `gate_ran types:
Counter({'bool': 186})`, zero non-bool at any era. So the code decision it justifies (hold `gate_ran`
to a `bool` at every era rather than only above the cutover) is **correct** and needs no change.

**Proposed fix.** Delete the parenthetical, or replace it with a claim that does not move — *"measured
at `4e60c5d8`: zero records at any era carry a non-bool `gate_ran`, so unlike `refused` there is no
history to exempt."* Nothing else in the sentence is load-bearing.

**Structural** (the shape), **transitional** in effect (a comment; no behaviour).

---

### M2 — `(schema_of(rec) or 0)` re-collapses, at three sites, the one distinction `schema_of` exists to make

**Premise.** `schema_of` returns `None` for *unreadable* and `0` for *absent*, and its docstring
insists they are different answers: *"AN ABSENT FIELD IS 0, NOT None … only a field that is PRESENT
and is not a version is unreadable."* All three readers then write:

```
scripts/check-review-rounds.py:239   elif (schema_of(rec) or 0) < TRUSTED_SCHEMA:      # era_split
scripts/check-review-rounds.py:293   if   (schema_of(rec) or 0) < TRUSTED_SCHEMA:      # verdict_problems
scripts/check-review-rounds.py:371   if   (schema_of(rec) or 0) >= TRUSTED_SCHEMA …    # read_verdicts
```

`None or 0` is `0`, so at the two pure sites an **unreadable** record is silently bucketed as the
**oldest era** and `continue`d — the silence the whole era gate exists to make legible. (`:371` is
safe today only because `:346` already returned for a `None`.)

**Why this is a finding and not pedantry — the slice's own precedent decides it.** `read_verdicts`
refuses `schema_of(rec) is None` before either pure site is reached, so it is not a reachable
mis-count today. That is *word for word* the footing on which **r2 Claude M1 was accepted** in this
same file: *"`read_verdicts` now refuses a non-bool outright, so no such record reaches either site;
this is the CLASS being closed, not a reachable mis-count."* Both `era_split` and `verdict_problems`
are documented `PURE`, are exported, and are driven directly with arbitrary records by the suite —
which is the only reason r2's `refused` mis-count was demonstrable at all.

It is also the *same truthiness idiom* this slice has removed four times, applied one level up: to
the **return value** of the function written to end truthiness on this field.

**Proposed fix.**

```python
s = schema_of(rec)
if s is None or s < TRUSTED_SCHEMA:   # …or take the validated int as a parameter
```

Better: have `read_verdicts` hand the pure sites the already-validated version, so there is one
answer rather than three readings of it. One mutation per site, or one on a shared helper.

**Structural.**

---

### L1 — the `review` sentinel is expressible as a real value, which is the rule this very commit wrote for `schema`

`scripts/check-review-rounds.py:295` — `review = rec.get("review") or "(unnamed)"`. A record carrying
`{"review": "(unnamed)"}` is byte-indistinguishable from one with no `review` field at all; I drove
both and got identical output.

This commit's own argument, four paragraphs earlier in the same file, for refusing `{"schema": 0}`:

> *"0 is this function's answer for ABSENT, so a record carrying it would be indistinguishable from
> one written before the field existed. **The sentinel must not be expressible as a real value.**"*

Same file, same commit, one field over, opposite treatment. **Low** because there is no behavioural
difference today — `"(unnamed)"` is not a filename, so both readings miss `review_names` — and
because H1's validator deletes the sentinel outright (a validated `review` is always a non-empty
`str`, so `or "(unnamed)"` becomes dead code). Filed so the fix is not forgotten when H1 lands.

**Structural.**

---

## What I could not finish

* **`check-plan-code.py --mutate .`** — not run, per the brief; it runs on GitHub via PR #343. So
  every "the mutation reds through its named case" claim below the four I drove by hand is
  **unverified by me**, and the four I did drive were run on a *staged copy* of the tree under a
  redirected `$HOME`, not through the harness's own `HARNESS_TREE` staging. An entry that binds in
  my sweep is proven to bind, not proven to be *measured by the harness*.
* **CI's actual result for `f54b6240`** — I did not query GitHub. The commit's claim that the
  previous red `verify` was caused by an unpushed r2 Codex half is plausible from the tree (that
  file is in this commit) but I did not confirm it against the run log. Treat it as unverified.
* **The `docs/` changes on the earlier four commits** (`process-rationale.md` +191,
  `development-velocity.md` +186, `plugins.md` +98) — r1 and r2 covered those commits; I spent this
  round on the enumeration question the brief made the priority and did not re-audit their prose
  counts. If nobody has re-derived the numbers in `development-velocity.md`, that is an open gap, not
  a clean bill.
* **Python version** — everything above ran on the local `python3` (3.14.4). `check-python-pin.py`
  is green, but a mismatch is advisory locally; CI pins separately.

---

## Verdict

**NOT CONVERGED — 2 High, 2 Medium, 1 Low.**

`f54b6240` itself is **correct**: every claim in its message re-derived true (the four mutations red
through their named cases, 1032/0 anchors, 1024 declared = 1024 manifest, 64/64, every CI gate green
but the two that are green-by-design), and the `>= 1` floor is the right rule with the right two
edge cases. Nothing in it needs reverting.

What is not converged is the thing the round was convened to ask. **Four rounds have closed four
values on three fields, one at a time, and the fifth field — the join key — was never examined.**
H1 is that field. H2 is the same class in the consumer nobody opened. M2 is the same idiom one level
up, inside the function written to end it. They are one fix: a validating reader that states the type
of every field once, in the one place that already decides whether a record can be read. A fifth
patch closes `{"review": []}` and leaves the sixth field for round 4.

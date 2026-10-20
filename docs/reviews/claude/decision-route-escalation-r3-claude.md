# Round 3, Claude half — `decision-route-escalation`

Subject: `git diff 2d6513a3..HEAD` — commit `d0be6ca8`, the r2 fold. The Claude half owed from r2.

**Everything below was RUN.** Every finding names the command or the constructed input, and every
figure in this document was produced by executing something during this review, not read out of the
fold's own notes. Where I could not execute, the finding says so in its own text and is listed again
under *What I could not verify*.

## What reproduced as claimed, before anything else

| check | result |
|---|---|
| `python3 scripts/check-decision-scheme.py` | rc=0, `4 row(s), 2 scored`, `all triggers quiet` |
| `--self-test` | 128/128 (also 128/128 under `/usr/local/bin/python3.12`, CI's pin) |
| `--rederive` | `no material drift` (median 4 → 4.0, mean 4.84 → 4.8, subjects 81 → 82) |
| `check-review-decision.py --self-test` | 85/85 |
| `check-fixture-variation`, `check-review-rounds`, `check-ratchet-contract`, `check-selftest-counts`, `check-docs`, `check-main-drivable` | all rc=0 |
| **all 60 manifest entries (41 + 19) re-checked under the REAL contract** | **41/41 and 19/19 attribute** — every `expect` EQUALS exactly one red `[FAIL]` case, `all()` not `any()`, equality not substring, on Python 3.12 |

The manifest re-check is mine and independent: I did not trust `probe6.py`. I wrote a probe that
imports `check-plan-code.parse_fail_names` rather than retyping the `[FAIL]` grammar, applies every
edit with `replace(find, repl, 1)` and refuses an anchor count ≠ 1 exactly as `run_mutations` does,
and — unlike `probe6.py` — **never writes into the repository**: the mutated source goes to the
scratchpad and is `exec`'d with `__file__` spoofed to the delivered path, so `REPO`, git and
`docs/reviews` resolve as in production while the delivered file is untouched. `probe6.py` rewrites
`scripts/check-decision-scheme.py` in place, which is an instrument that edits the repo while other
agents are running in it; it happens to restore the file, and that is a property of it not crashing.

So the fold's attribution claim holds. **The claim that CI will ever measure those 41 entries does
not**, which is finding 1.

---

## 1. BLOCKING — the authority this fold defers to cannot run, and this fold made it worse by one case

**File:** `scripts/check-decision-scheme.py`, `_self_test` (the two `tree_at` cases) ×
`scripts/check-plan-code.py`, `mutate_delivered` / `stage_tree` / `control_is_green`.

The brief lists *"the full `--mutate .` is CI's authority"* as deliberate. It is not available.
`mutate_delivered` stages `HARNESS_TREE` into a `TemporaryDirectory` and runs each target's suite
with `cwd=d`. `HARNESS_TREE` does not include `.git`, and `tree_at` passes `cwd=REPO` (= the staged
dir) to git explicitly, so git fails there no matter what cwd the harness chooses.

**Input — the harness's own functions, not a stand-in:**

```python
cpc.stage_tree(root, d); (d/cpc.CHILD_HOME).mkdir()
rc, so, se = cpc.run_suite_parts(d, "scripts/check-decision-scheme.py")
cpc.control_is_green(rc, cpc.merged_output(so, se))
```

**Observed:**

```
=== scripts/check-decision-scheme.py: rc=1 control_is_green=False
[FAIL] tree_at answers from a LISTING of the real repository, not from a diff
  [FAIL] ...while a long-standing file IS, so the listing is not simply empty of reviews
126/128 self-test cases passed
=== scripts/check-review-decision.py: rc=0 control_is_green=True
```

`mutate_delivered` therefore returns
`CANNOT RUN — control run of scripts/check-decision-scheme.py did not prove the suite works
(exit 1) … Every verdict below would be an artefact. Treat this as NOT CHECKED.` and a
`NotMeasured`. And it is not one shard's problem: `shard_slice` is round-robin, so I ran it —
**all 8 of CI's shards contain `scripts/check-decision-scheme.py`** (203/203/203/203/203/203/203/202
mutations, target present in every one). The whole **1,623-mutation sweep** reports NOT MEASURED
until this is fixed.

**What is this fold's share of it.** The first git-dependent case arrived in the r1 fold, so the
breakage predates `d0be6ca8` — but r2's Codex half wrote *"The full mutation sweep was not run"*, so
nobody has run it, and **this fold added a second git-dependent case** (`...while a long-standing
file IS`) rather than removing the dependency. Worse, the fold's headline new case survives the
outage vacuously:

```python
case("⭐ and it lists the HISTORICAL tree — a post-arming file is NOT in it",
     ("docs/reviews/coordinator/decision-route-escalation-r1-coordinator.md" in (_tree or set())),
     False)
```

`_tree or set()` — when git cannot be read, `_tree` is `None`, the membership test is over the empty
set, and **the case that is supposed to prove the instant is read passes because no tree was read at
all.** Its sibling is the only reason the suite goes red. That is this repository's
*a case can pass for an AMBIENT reason* class, in the case written to close r2's YM6.

**Fix direction** (not mine to choose, but the shape is forced): either add `.git` to
`HARNESS_TREE` — which the tuple's own note warns is not a containment boundary, and a mutation
inside a staged tree that can reach git history is a new hazard to argue — or make `tree_at`'s
subject injectable so the cases drive it over a constructed repository instead of this one. The
second is the move the rest of this file already made twice (`shallow_refusal`,
`empty_listing_refusal`).

⚠ This fails **loudly** — CI goes red, it is not a false green. It is Blocking because it means the
fold's coverage claim rests entirely on a probe run by hand on a developer machine, and because the
dashboard entry shipped in this commit tells a human reader *"mutations 41 and 19, all attributing
under the REAL contract"* without saying that the gate which is supposed to assert that cannot.

---

## 2. HIGH — the starvation identity's third door: a RENAMED subject, and a RENUMBERED round

**File:** `scripts/check-decision-scheme.py`, `subjects_starved` / `rounds_in_paths`.

The fold's docstring: *"A `(subject, round)` pair survives a move, survives quoting once the bytes
are read correctly… Only the directory changes under a move; the basename grammar does not."* True
of a move. The subject token is parsed out of the **same mutable filename the path was**, so the
identity is stable against exactly the perturbation r2 happened to find and against nothing else.

**Input (run against the shipped functions):**

```python
before = rounds_in_paths({"docs/reviews/codex/old-name-r1-codex.md",
                          "docs/reviews/codex/old-name-r2-codex.md"})
docs   = {"new-name": {1: {"docs/reviews/codex/new-name-r1-codex.md"},
                       2: {"docs/reviews/codex/new-name-r2-codex.md"}}}
subjects_starved("2026-10-20T10:00:00-07:00", docs, before)
```

**Observed: `(['new-name'], None)`** — an entirely historical subject, both of whose rounds predate
arming, named as newly starved. That is r2 YH2's consequence verbatim (backlog #56's death), reached
by a rename instead of a move.

A second input in the same class: **re-filing a round under a different number.**
`before = {("s",1),("s",2)}`, `docs = {"s": {2: …, 3: …}}` → **`(['s'], None)`**. Nothing about the
work is new; one document was renumbered.

**Why this matters more than its frequency.** Review subjects are branch names, and this repository
renames things on purpose — `block-default-branch-push.sh` is kept under a wrong name *only* because
five merged review docs cite it. The honest resolutions are both small: (a) declare that a rename is
an arming event and say so in `_armed_at_means`, so the false positive is a documented consequence
rather than a surprise; or (b) take the subject from the document's own ` ```yaml ` header
(`subject: decision-route-escalation`), which is a CONTENT identity and survives rename, move and
quoting together — bounded, because only 29.3% of rounds carry a coordinator document, so it is a
partial and has to be stated as one.

⚠ Stated rather than hidden: `git log --diff-filter=R -- docs/reviews` returns nothing, so I have
**not** established a historical rename rate. This door is structural and demonstrated; it is not
measured as live.

---

## 3. HIGH — the subject half of the identity is guarded in ONE direction, and the unguarded one is the predecessor's death

**File:** `scripts/check-decision-scheme.py`, `subjects_starved`; `scripts/mutations/check-decision-scheme.json`, entry 31.

Entry 31 mutates `(subject, n) in before_rounds` → `n in before_rounds`. Because `before_rounds`
holds tuples, that match **never** succeeds: every subject looks new, two cases redden, the entry is
attributed. It covers the OVER-FIRING direction only.

**Input — the same clause made subject-blind in the direction that matches MORE:**

```python
rounds_before = sum(1 for n in rounds if any(n == b for _, b in before_rounds))
```

**Observed: the suite stays green at 128/128**, and the live guard goes from
`(['decision-route-escalation'], None)` to **`([], None)`** — including this branch's own subject,
which genuinely crossed into scope. Trigger 1, *"the loudest trigger, because it is how the
predecessor died"*, goes permanently silent and `main()` prints `all triggers quiet`, rc=0.

A mutation that silences the loudest trigger over the whole corpus is not covered by a mutation that
makes it fire over the whole corpus. Both directions need a case; the suppressing one has none.

---

## 4. HIGH — `_round_docs`, the "now" side of the set difference, has zero cases and zero mutations

**File:** `scripts/check-decision-scheme.py`, `_round_docs`.

The r2 redesign gave the *historical* side a new pure function with six new cases
(`rounds_in_paths`). Its counterpart — the function that produces `docs`, i.e. the live half of
`rounds it had BEFORE arming < 2 <= rounds it has NOW` — is reached by **no self-test case**
(`grep` for `_round_docs` in the suite: zero call sites; every starvation case passes `docs` as a
literal) and by **no manifest entry** (I derived this by locating `_round_docs`'s body and testing
every one of the 41 anchors against it: zero hits).

**Input — one token inside it:**

```python
seen.setdefault(m.group("subject"), {}).setdefault(int(m.group("round")), set()).add(rel)
#                                                  ^^^^ -> m.group("round")   (keys become strings)
```

**Observed: suite 128/128 green. Live `subjects_starved` names 82 subjects** — the entire corpus of
subjects with ≥2 rounds. Trigger 1 FAILS on every run, which is precisely the red-from-birth shape
this design cites backlog #56 to avoid, and the suite cannot see it.

**Second input, same function:** delete the directory filter
(`if path.parent.name not in ("codex","claude","coordinator", reviews.name): continue`).
**Observed: 128/128 green.**

The identity redesign is sound; it is only asserted on one of the two sets it differences.

---

## 5. HIGH — `tree_at` can ignore its `epoch` argument and the suite stays green

**File:** `scripts/check-decision-scheme.py`, `tree_at`; manifest entry 33.

Entry 33 substitutes `sha` → `"HEAD"` and is killed by the new instant assertion. That closes the
*one* substitution r2 named. The brief asks whether there is another. There is, and it is the
general one.

**Input:** `f"--before=@{epoch}"` → `"--before=@1792368000"` (2026-10-19T00:00:00Z — before the
arming instant, inside this repository's history). I also ran the stronger form, replacing `tree_at`
wholesale with a body that ignores its parameter.

**Observed: 128/128 in both cases.** The reason all four assertions survive: the post-arming file is
absent from any older tree, `scripts/check-review-rounds.py` is present in any older tree, the set
is >100 paths, and `tree_at(1)` still refuses because the `int(when) > epoch` check compares the
resolved commit against the *passed* epoch. The assertion pins the tree away from **today** and not
toward the **instant requested**, so the parameter is severable.

**Production consequence.** `baseline.json`'s `_armed_at_means` anticipates re-arming
(*"a maintainer re-arming the ratchet"*); `parse_armed_at`'s docstring is built around that
maintainer. With `epoch` severed the window would not move when `armed_at` does, and every subject
that crossed between the old and new instants would read as historical — silently. The missing case
is the cheap one this suite already knows how to write: **two distinct valid epochs must yield
different trees.** Measured today, `tree_at` at the arming instant resolves `5d957db8` while HEAD is
`2026-10-20T11:53:08-07:00`, so such a pair exists and is stable.

---

## 6. HIGH — YH1 is not closed: a symlinked subtree is skipped by BOTH traversals and yields a partial count with NO `error`

**File:** `scripts/check-decision-scheme.py`, `_corpus_now` (and `_round_docs`, identically).

The fold's comment: *"`os.walk`'s `onerror` is the only way to hear about it."* `onerror` fires on
`scandir` failures. It says nothing about a subtree neither traversal descends into — and
`os.walk(followlinks=False)` and `Path.rglob` **both** refuse to descend a directory symlink, so the
two agree on omitting it and no error is produced.

**Input (constructed in the scratchpad):** `reviews/codex` is a **symlink** to a directory holding
`a-r1..r4-codex.md`; `reviews/coordinator/` really holds `b-r1,b-r2-coordinator.md`.

**Observed, on CI's pinned 3.12 and on 3.14:**

```
_corpus_now  -> {'median': 2, 'mean': 2, 'subjects': 1}      # no `error` key
_round_docs  -> {'b': [1, 2]}                                 # subject `a` does not exist
truth        ->  subjects 2, median 3.0
```

A partial measurement reported as a measurement, `main()` prints `all triggers quiet`, rc=0 — **the
r2 YH1 shape exactly, in the code written to close it.** The `_round_docs` half is the worse one:
a subject whose documents sit behind a symlink can never be named as starved, which is the
predecessor's failure mode with no symptom.

⚠ Two traversals is also two instants. The walk and the `rglob` are separate passes, so a directory
that becomes unlistable between them is skipped silently again. That requires concurrency — and
`docs/plugins.md` designates top-level `docs/reviews/` a *"no-legitimate-writes zone while a Codex
run is in flight"*, i.e. concurrent writers in this exact tree are an acknowledged reality, not a
hypothetical. The structural fix is one traversal: derive the file set from the `os.walk` that
reports its own errors, and delete the `rglob`.

**This finding scores log row 1.** `corpus-cannot-run`'s `redesign` bet predicted *"os.walk(onerror=…)
changes the QUESTION … so a skipped subtree cannot be silent."* A skipped subtree is still silent.
By `FAILURE_OBSERVATION["redesign"]` — *"the unit still carried findings after a restructuring
fold"* — that bet is observed to have failed, and the next route for that unit is **SPLIT**. This is
the first time the ladder will emit a route from derived history rather than from a first guess, and
it is the most useful thing this round hands back.

---

## 7. HIGH — trigger 5 is currently unfalsifiable, and the omission is an authored off-switch

**File:** `scripts/check-decision-scheme.py`, `t5_ranker_miss` / `validate_row`;
`docs/reviews/decision-scheme/decision-log.jsonl`.

The brief asks: *is a documented omission sufficient, or does it make "abstained" indistinguishable
from "nobody recorded it"?* **It is not sufficient, and the answer is measured rather than argued.**

```
rows: 4        keys per row: observed, outcome, prediction, ranker, route, subject, unit
any `ranker_hit` key? False          t5_ranker_miss(live rows) -> None
validate_row({... "ranker_hit": None})        -> "ranker_hit is NoneType, not a bool — …"
validate_row({... "ranker_hit": "abstained"}) -> "ranker_hit is str, not a bool — …"
t5_ranker_miss(10 rows, no key)      -> None
t5_ranker_miss(10 rows, key False)   -> "two consecutive ranker misses at rows 1 and 2 of 10 scored"
```

Three things follow, and together they are worse than the bug that was fixed.

1. **Abstention is inexpressible as data.** `ranker_hit: null` and `ranker_hit: "abstained"` are both
   REFUSED by `validate_row` (the r1 Codex M5 type check, correctly, catches both). So the tri-state
   the fix conceptually needs cannot be written down. The abstention's only record is the free-text
   `ranker` field, which `validate_row` does not mention and no trigger reads.
2. **An omission is how a FAIL trigger gets switched off, and nothing can tell it from a mistake.**
   A coordinator who forgets `ranker_hit` disables trigger 5 permanently, and the run says
   `all triggers quiet`. That is the r1 Claude H1 defect — a silent off-switch on the loudest
   trigger — relocated to a different field. This file's own standard refuses that shape elsewhere:
   `t1`'s docstring says a reason must be recorded, not implied, and `subjects_starved` returns a
   REASON rather than an empty list for exactly this reason.
3. **Right now there is no observation that can make trigger 5 fire.** All four shipped rows omit the
   key, so `marks` is empty. The trigger is present, covered by three cases, manifested — and
   unreachable from the committed log.

**The fix is the one the schema already models twice.** `outcome` is `null`-or-enum and
`rounds_at_termination` is required-when-stopped; a `ranker` field with an enum
(`named` | `abstained`) and `ranker_hit` **required when `ranker == "named"` and refused otherwise**
makes abstention a positive record, makes an omission a validation error, and leaves `t5` reading
only real bets. That is a schema change, not a comment.

---

## 8. HIGH — the log is fed at SUBJECT granularity while the mechanism reasons in UNITS, and #321 is what created the gap

**File:** `scripts/check-decision-scheme.py`, `t1_not_fed`; `docs/reviews/decision-scheme/decision-log.jsonl`; `docs/backlog.md` #321.

The brief asks whether filing #321 is a dodge. My answer: **filing the open design question was
right; shipping the consequence unobserved was not.** Here is the consequence, measured.

The r1 coordinator document decides routes for **seven** units — `relocation` (SPLIT), `log-schema`
(REDESIGN), `corpus-cannot-run`, `starvation-ratchet`, `accounting`, `ranker-caller`, `coverage`
(ACCRETE). The committed log holds **two** of them. And:

```python
t1_not_fed([{"subject": "S", "unit": "only-one", "route": "accrete"}], ["S"])  ->  None
```

`t1_not_fed` intersects `{r.get("subject")}` with the starved list. **One row for a subject satisfies
the loudest trigger however many of its units were decided and never recorded.** So five of seven
decided units are invisible, the guard prints `all triggers quiet`, and the field the whole mechanism
turns on — `route` per `(subject, unit)` — has a 29% recording rate on its own first use, with no
observation that says so. *That is the 81%-starvation argument one level down, and it is live on the
branch whose subject is that argument* — the same sentence the r1 coordinator document wrote about
`rounds=0`.

**And the omission is not random: it is exactly the two units `route_sequence_error` refuses.** The
validator cannot express `relocation → SPLIT` or `log-schema → REDESIGN`, so those two rows do not
exist, so nothing counts them as missing. A validator that makes honest rows inexpressible produces
selection bias in the record it guards, and the bias is invisible because the trigger measures
subjects.

**On the ladder itself — the brief asks me to argue it, so: the prefix requirement is wrong, and
here is the observation that shows it.** Termination needs only that `tried` grows strictly within a
finite set with no repeats; `route_next` and the no-retry clause already give that. The *prefix*
clause adds nothing to termination and is refuted by use at a rate of **2 in 7 (29%)** on the
mechanism's first real application, by a coordinator whose two skips were both argued from measured
evidence (`relocation`'s measured delta was zero subjects; `log-schema`'s field was derivable).
Replacing "is a prefix of LADDER" with "`LADDER.index` is strictly increasing" preserves termination
exactly, refuses de-escalation and retries exactly as now, and admits both real histories. That is
#321's option (b) without the extra field, and it is a smaller change than any of the three filed
candidates. Option (c) — prose plus a rate — should be rejected on this file's own evidence: an
exception rate nobody reads is how the predecessor died.

**What should have shipped alongside the filing**, and is the actual gap: either that one-line
monotonicity change, or a unit-level trigger — *a subject in the log whose round documents name
components with no row of their own* — so the five missing units are an observation rather than a
silence. `component_rounds` already computes the input that trigger would need.

---

## 9. MEDIUM — `t7_sample_reached` attaches a 74% accuracy bound to a denominator of abstentions

**File:** `scripts/check-decision-scheme.py`, `t7_sample_reached`.

`hits = sum(1 for r in scored if r.get("ranker_hit"))` over `len(scored)`. Omitting `ranker_hit` on
an abstention (finding 7) removes the row from `t5`'s numerator **and leaves it in `t7`'s
denominator**, where it can never be a hit.

**Input:** ten scored rows, every one an abstention (no `ranker_hit`).
**Observed:** `10 scored rows (0 ranker hits) — re-evaluate now; at 10/10 the one-sided 95% accuracy
bound reaches 74%, against a ~7% coin`.

Over zero placed bets. The sentence is the guard's own instruction to re-score the instrument, and
it reports the instrument at 0/10 when the truth is 0/0. `scored` is the wrong denominator for an
accuracy claim; the denominator is *rows where a bet was placed*. Fixing finding 7's schema fixes
this one for free; without it, the two triggers disagree about what a row means.

---

## 10. MEDIUM — `derive_outcome`'s third model error: no later round is read as evidence of stopping

**File:** `scripts/check-decision-scheme.py`, `derive_outcome`.

r2 YL7 corrected count → position. The remaining error is absence → negative.

**Input:** `derive_outcome("s", "a", 1, {"a": {1}})` — component `a` found in round 1, and round 2
has not happened yet. **Observed: `"stopped"`.**

Whether the stream stopped is not knowable until a later round exists. The function cannot
distinguish *"a later round happened and did not name this component"* (genuine evidence of
stopping) from *"no later round has happened"* (no evidence at all) — and `None` is the value this
function exists to return for the second. `component_rounds` holds the information needed
(`max` over the union of all round sets); `derive_outcome` is not given it.

⚠ **A self-test case enshrines the defect**: `"...and after round 5 it has stopped, so the boundary
is read from the SET"` asserts `derive_outcome("s","a",5,{"a":{1,5}}) == "stopped"`, where 5 is the
maximum round in the fixture. So this one will not be found by the suite.

**So: is leaving it unwired right?** Yes — and this is the third independent reason, after r2's. The
fold's own ordering (*model first, evidence the model is right second, wiring third*) is correct and
the model has now been wrong twice in two rounds in the same direction: treating a cheap proxy as the
observation. The honest move before wiring is to pass the subject's maximum round and return `None`
above it.

---

## 11. MEDIUM — the walk's scope is the whole tree, the count's scope is four directories: an irrelevant permission fault is CANNOT RUN

**File:** `scripts/check-decision-scheme.py`, `_corpus_now`.

`os.walk(reviews, …)` traverses all of `docs/reviews/`. The count only ever reads
`{codex, claude, coordinator, reviews}`. `docs/reviews/verdicts/` holds **264** files that contribute
exactly zero to any figure.

**Input:** a copy of `docs/reviews` with `verdicts/` at mode `000`, passed as `_corpus_now(reviews=…)`
and then driven through `main(corpus=…)`.

**Observed:** `{'median': None, 'mean': None, 'error': "the review corpus could not be fully
traversed … Permission denied: …/verdicts"}` and `main()` → **rc=2**, `CANNOT RUN`, trigger 1 and all
six others unevaluated.

Fail-closed is the right default, and this is fail-closed over a subtree the measurement does not
read. A gate that goes rc=2 because an unrelated directory's permissions changed is the other face of
backlog #56 — it gets switched off just as surely as a red-from-birth one. Scope the traversal to the
directories the count actually reads, which is the same set the filter already names.

---

## 12. MEDIUM — the two sides of the set difference define their corpus differently

**File:** `scripts/check-decision-scheme.py`, `rounds_in_paths` vs `_round_docs` / `_corpus_now`.

`rounds_in_paths` is handed **every path in the repository** at the arming commit and applies **no
directory filter** — any basename matching `SHAPES` anywhere in the tree becomes a historical
`(subject, round)`. The current side filters to four directories. A matching document under
`docs/reviews/verdicts/`, `docs/reviews/decision-scheme/`, a `tests/fixtures/` tree or anywhere else
therefore counts as pre-existing while being absent from `docs` — **suppressing** starvation, the
dangerous direction.

**Measured at the arming commit `5d957db8`:** 3,081 paths, 415 `(subject, round)` pairs, and
**0** matching basenames outside the four directories. So this is latent today, not live — and it is
latent only by luck: nothing forbids it, and `docs/reviews/` already has two sibling directories that
the filter excludes and the tree listing does not. One shared helper for "which paths are round
documents" would close it; that is the `one rule, one place` argument the fold already made for
`SHAPES`, applied one level up.

---

## 13. MEDIUM — the two extracted refusals are drivable as rules and unguarded as wiring

**File:** `scripts/check-decision-scheme.py`, `tree_at`'s calls to `shallow_refusal` and
`empty_listing_refusal`; manifest entries 27 and 35.

Both entries mutate the **pure functions** (`if flag.strip() == "true":` → `if False:` and
`if not paths:` → `if False:`). Neither touches the **call site**.

**Input:** delete `refusal = shallow_refusal(shallow); if refusal: return None, refusal` from
`tree_at`. Separately, delete `refusal = empty_listing_refusal(paths, sha); if refusal: return None,
refusal`. **Observed: 128/128 green in both cases.**

The extraction rationale is right — *"a rule that cannot be driven is not covered, however correct it
looks"* — and it moved the uncoverable branch rather than removing it: the wiring is now the branch
that cannot be driven on a real repository. That is not a reason to undo the extraction; it is the
reason `tree_at` needs an injectable subject (finding 5's fix), after which both call sites become
drivable and finding 1 dissolves with them. Three findings, one repair.

⚠ Stated for honesty: `empty_listing_refusal`'s wiring is **new in this fold**; `shallow_refusal`'s
is from r1.

---

## 14. MEDIUM — `corpus-cannot-run`'s committed route is a function of ladder position, not an observation

**File:** `docs/reviews/decision-scheme/decision-log.jsonl`, row 2.

The brief asks whether the four rows' routes are honest. Three are; row 2 is not, and the validator
is what made it so.

The `corpus-cannot-run` fix in this fold is twelve added lines **inside** `_corpus_now` — an
`os.walk` pre-pass before the existing `rglob`, same function, same question, same control flow
afterwards. By any plain reading that is accretion. It is recorded as **`redesign`** because
`validate_row` refuses `accrete` twice on one unit, so the second fix on a unit *must* escalate
whether or not the work did. Compare row 4: `starvation-ratchet`'s `redesign` changed the identity
type, added two functions and rewrote the rule — genuinely a restructuring. Both rows say the same
word for work of entirely different character.

This is #321's mirror image and it is **already in the committed log**, not a hypothetical: the
no-retry rule forces escalation *up* just as the prefix rule forbids skipping *ahead*. And three
things read `route` as though it were a choice — `derive_routes_tried`, `t3_routes_collapsed`'s
"all scored rows took route X", and `FAILURE_OBSERVATION`, whose `redesign` text
(*"a redesign applied without stopping the finding stream"*) will be quoted against a unit that
never had one. The monotonicity change proposed in finding 8 does not fix this half; what would is
either a separate `work` field describing what was done, or accepting that `route` is a position and
renaming it so no reader mistakes it for an observation.

---

## 15. LOW — `derive_outcome.subject` is dead, and its fixture-variation case asserts that it is

**File:** `scripts/check-decision-scheme.py`, `derive_outcome`; `scripts/check-fixture-variation.py`,
`EXAMINED_KEYS['check-decision-scheme.py']`.

No clause reads `subject`, and the function returns an enum, not a message, so it cannot be "carried
for the message". The case that satisfies the variation guard —
`("the subject is carried, and the evidence it is given is what decides",
(derive_outcome("other-subject", …), derive_outcome("s", …)), ("continued","continued"))` — asserts
that **both distinct values give the same answer**, i.e. that the parameter is ignored. It cannot
fail on the axis it was written for. The fold's own comment calls this deliberate and says so, which
is better than an exemption; the smaller honest move is to delete the parameter and the entry
together, since the caller already scopes `seen` to one subject.

## 16. LOW — nothing requires two rows of one subject to agree on `rounds_at_termination`

**File:** `scripts/check-decision-scheme.py`, `validate_row` / `t4_no_improvement`.

`rounds_at_termination` is a per-SUBJECT quantity recorded on per-UNIT rows. Two units of one subject
may record 3 and 9; `validate_row` accepts both and `t4` keeps whichever row is last. The `pop()`
fix is correct for "latest by occurrence" (I verified the r2 YM4 input reproduces: nine rows, median
9 reported, previously 1) — but "latest" is now deciding between two values that should not differ.
A one-line check in `validate_row` against the unit's prior rows closes it.

## 17. LOW — a directory named like a round document is counted as one

**File:** `scripts/check-decision-scheme.py`, `_corpus_now` / `_round_docs`.

`rglob("*.md")` yields directories too; neither reader calls `is_file()`. A directory
`docs/reviews/codex/x-r1-codex.md/` would be parsed as a round document. Cheap to refuse, and it is
the same family as the `is_dir` guard the fold added one level up — whose case
(*"a corpus path that is a FILE says so"*) is good and shows the author already thinks in this class.

## 18. LOW — the `ranker` field is unvalidated free text

**File:** `scripts/check-decision-scheme.py`, `validate_row`; the log's four rows.

Every shipped row carries a 300-character `ranker` string asserting an abstention. `validate_row`
never mentions the key; no trigger reads it. It is the only record that the ranker abstained, and it
is prose inside a machine-read log — the shape `dev-process.md` calls *a decision wearing a
checkbox*. Subsumed by finding 7's schema fix; listed separately because it is also true today.

## 19. LOW — the tree assertions name two real repository paths, and one of them is a moving target

**File:** `scripts/check-decision-scheme.py`, `_self_test`.

The brief asks whether the new assertion is stable. The *absent* half is: the r1 coordinator document
cannot enter a tree dated before it, and the suite's `_ARM` is a literal rather than being read from
`baseline.json`, so re-arming the live ratchet does not disturb it (I checked this specifically —
there is no coupling, and a squash or rebase only moves the document's commit later). The *present*
half is not: `"scripts/check-review-rounds.py" in _tree` reddens the suite if that script is ever
renamed, for a reason unrelated to anything it tests. Prefer a path with no plausible rename, or
derive it (`sorted(_tree)[0]`-style) so the assertion is about the listing rather than about one
file's name.

## 20. LOW — verified EQUIVALENT, recorded so it is not re-found

**File:** `scripts/check-decision-scheme.py`, `rounds_in_paths`.

Removing the `break` after a shape matches survives 128/128. I class this as a true equivalent
mutation rather than a gap: the two `SHAPES` are mutually exclusive on any name (shape 2 requires the
name to end `-r<N>.md`, shape 1 requires it to end `-<who>.md`), so the second iteration can never
add a pair. Recorded because a later reviewer running the same probe will see the same survivor, and
an unexplained survivor costs a round.

---

## What I could not verify

* **I did not run the full `--mutate .` sweep.** It cannot complete — finding 1 — and I reproduced the
  exact refusal using the harness's own `stage_tree`, `run_suite_parts` and `control_is_green` rather
  than a stand-in. The per-entry attribution figures (41/41, 19/19) therefore come from my own probe
  against the real repository, where the control IS green, on Python 3.12. That measures the
  manifest; it does not measure CI.
* **A shallow clone.** `shallow_refusal`'s rule is covered by two cases; its wiring (finding 13) I
  could only test by deleting the call site, not by producing a shallow checkout, because that needs
  a git write.
* **The symlink behaviour (finding 6) was measured on macOS**, Python 3.12.x and 3.14.4. I did not
  run it on a Linux CI runner. The mechanism (`followlinks=False` plus `rglob`'s non-recursion into
  symlinked directories) is not platform-specific, but the measurement is.
* **The historical rate of subject renames** in `docs/reviews/` — `git log --diff-filter=R` reports
  none, which is not the same as none having happened, and I did not run rename detection over the
  full history. Finding 2 is demonstrated structurally, not observed live.
* **`check-banner-armed` and `check-review-recorded`** — not run; the brief records them as CANNOT RUN
  outside their hook and rc=1-expected respectively, and I did not re-derive that.
* **Integration and E2E suites** — out of this diff's scope and they need a live Supabase stack.
* **The `t4` interleaving edge in `main()`** — a stopped row lacking `rounds_at_termination` is
  refused by `validate_row`, so finding 16's cousin is unreachable through `main()`; I verified the
  refusal, not every path that could reach `t4` from elsewhere.

## Severity counts

| severity | count | findings |
|---|---|---|
| Blocking | 1 | 1 |
| High | 7 | 2, 3, 4, 5, 6, 7, 8 |
| Medium | 6 | 9, 10, 11, 12, 13, 14 |
| Low | 6 | 15, 16, 17, 18, 19, 20 |

**One repair collapses four of them.** Making `tree_at`'s subject injectable (a `repo` or a
`lister` parameter, the move this file already made twice) removes finding 1's git dependency,
supplies finding 5's two-distinct-epochs case, and makes finding 13's two call sites drivable.
Making `ranker_hit` a required consequence of a `ranker` enum removes findings 7, 9 and 18.

NOT CONVERGED

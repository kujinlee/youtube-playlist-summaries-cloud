# r8 CLAUDE half — adversarial review of `afe3b7cd` (the r8 fold)

> ⟳ **FILED AS r8's CLAUDE HALF, NOT r9 — and this document's own Blocking is why.** It was
> dispatched as "r9" and reviews `afe3b7cd`, the fold of r8's findings. That is exactly what an
> alternating SECOND HALF does, and it is what r7 did (Codex → fold → Claude, both filed as r7).
> Numbering it r9 is what left round 8 with one half and made `check-review-rounds` red, which this
> review found and reported. ⛔ A `REVIEW GAP: claude` was NOT written instead: the half ran, so
> declaring a gap would be a false record — and `docs/plugins.md` forbids that declaration anyway.
> **Verified against the corpus rather than assumed:** `main-drivable` and `shard-mutation-sweep`
> each carry BOTH a codex and a claude half for every one of r7, r8 and r9.

**Scope:** exactly one commit, `afe3b7cd` (`git diff e72ccc2b..afe3b7cd`). Nothing earlier.
**Mandate:** refute, not confirm. Every number below was derived here; none was taken from the
author's MEASURED block.

**Verdict: 1 Blocking, 1 High, 2 Medium, 3 Low + 1 recorded refutation (no action).**

The code half of this fold is sound — the structural refactor is behaviour-preserving (measured),
the "unreachable, not watched" claim is true (measured, 0 violations in 135,322 windows), and both
new wire-tests kill the logic as well as the wiring (measured). **Every finding above Low is in the
RECORDS**, and the Blocking one is a live red on the required CI job, introduced by this commit.

---

## What I verified myself, before looking for anything

| Check | Command | Result |
|---|---|---|
| guard | `python3 scripts/check-decision-scheme.py` | **rc=0**, WARN 6 (denominator) + WARN 8 (hindsight-only), nothing else — as claimed |
| suite | `… --self-test` | **203/203** — as claimed |
| fixture variation | `python3 scripts/check-fixture-variation.py` | rc=0, 960 params / 70 files — as claimed (but see **L1**) |
| main-drivable | `python3 scripts/check-main-drivable.py` | rc=0, D2 OK, 16 drive `main()` over a constructed world |
| plan-code suite | `python3 scripts/check-plan-code.py --self-test` | **215/215** — as claimed |
| manifest cardinality | `grep -c '"file": …'` on the manifest | **82** entries, matching `EXPECTED_MUTATIONS` |
| **scoped sweep** | 7 `HARNESS_TREE` paths rsynced to a temp tree (tuple derived from `check-plan-code.py:199`, not retyped), all manifests but `check-decision-scheme.json` deleted, `EXPECTED_MUTATIONS` reduced to the single entry and the `sum(...)` case re-pinned to 82, then `--mutate .` | **`OK — 1 file(s), 82 mutation(s), 82 killed, 82 attributed to the case each names, 0 survivor(s)`**, control re-proved green. **Reproduced.** |

⛔ **One near-miss worth recording, because it is this project's own recorded failure mode.** My
first four `size`-default probes printed `203/203` four times and I nearly wrote that down as "the
window size is unprotected". The mutation had never been applied — the backup `cp` had gone to a
different directory and the write silently re-read the original. Every probe below now *prints the
mutated line it wrote* before running, and the control is re-run after each restore.

---

## BLOCKING

### B1 — `afe3b7cd` turns the required `verify` job RED, and the commit and the dashboard entry both publish "CI is green"

**Input.** `gh api repos/:owner/:repo/actions/jobs/119540188687` (the `verify` job of CI run
`39691881308`, head SHA `afe3b7cd`).

**Observed.**

```
{"conclusion":"failure","name":"Review rounds have both halves","number":22}
```

Reproduced locally, `scripts/check-review-rounds.py`, **real rc=1** (taken without a pipe):

```
FAILED — 1 review round(s) with one half and no stated reason:
  ✗ decision-route-escalation round 8: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
```

**Cause.** `afe3b7cd` adds `docs/reviews/codex/decision-route-escalation-r8-codex.md` (and its
verdict). There is no `docs/reviews/claude/decision-route-escalation-r8-claude.md` — every *other*
r8 subject in that directory has both halves (`chrome-bar-reachable`, `closing-table`,
`explainer-src-root-self-configures`, `main-drivable`, `recall-llm`, `shard-mutation-sweep`); this
one does not. Round 8 therefore became a round, one-sided, in the commit that filed it. `verify` on
the parent `e72ccc2b` was `success`, so the commit under review introduced the red.

**Against what the commit says.** `docs/dashboard-entries.md:16463` (human half): *"the automated
checks on the pushed branch are now passing, including the database checks that had been failing."*
The commit that published that sentence is the one that broke `verify`.

**What a fix must change — and there is a rule conflict underneath it.** Either
(a) file `docs/reviews/claude/decision-route-escalation-r8-claude.md`, or (b) add a written
`REVIEW GAP:` line for round 8. ⛔ **(b) is contested by project rule:** `docs/plugins.md` says
*"SPAWNING THE SUBAGENT FOR THE CLAUDE HALF IS PRE-AUTHORISED — do not ask, and do not declare a
`REVIEW GAP: claude` over it."* Meanwhile `review-method.md`'s topology rule says **rounds 2+
ALTERNATE**, which makes a one-sided round the *intended* shape. r7 had both halves; **r8 is the
first alternating round, and it turned the required check red immediately.** So this is not only a
missing file: the alternation policy and `check-review-rounds.py` cannot both be satisfied as
written, and nothing in this commit reconciled them. Whichever way it is resolved, it will recur on
every alternating round until one of the two rules moves. That reconciliation is the real fix; the
missing file is the instance.

⚠ **And filing THIS document adds the mirror image, which is expected rather than a second defect.**
After writing it, `scripts/check-review-rounds.py` reports **rc=1, two rounds**:

```
  ✗ decision-route-escalation round 8: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
  ✗ decision-route-escalation round 9: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
```

Round 9's half is the coordinator's to close (its Codex half, or a stated reason). Round 8's is the
finding: it was already red before this half existed, which is why the two are not the same item.

---

## HIGH

### H1 — "REAL CI IS GREEN on `e72ccc2b`" is a hand-picked subset — the exact defect `6499cf57` announced as its own headline one commit earlier

**Claim under review** (commit message of `afe3b7cd`, and `docs/dashboard-entries.md`):

> ⭐ REAL CI IS GREEN on `e72ccc2b`: `schema-gates: pass`, `verify: pass`.

**Input.** `gh run view 39690224594` (the `CI` workflow on `e72ccc2b`).

**Observed.**

```
conclusion: cancelled   status: completed
  verify                    success
  mutation-sweep (3)(5)     success        (2 of 8)
  mutation-sweep (1)(2)(4)(6)(7)(8)  cancelled   (6 of 8)
  mutation-sweep-complete   failure
```

The two checks the record names did pass. The **workflow's own conclusion is `cancelled`**, and the
mutation sweep — *the central evidence of this commit* ("82/82 killed, 82/82 ATTRIBUTED") — **never
completed in CI on that commit at all**, with its aggregator reporting `failure`.

**Fair reading of the cause, stated so the finding is not overstated.** `.github/workflows/ci.yml:21`
sets `concurrency: cancel-in-progress: true`, and `afe3b7cd` was pushed 14 minutes after
`e72ccc2b` (23:12Z vs 22:58Z), so the cancellation is **supersession, not a code failure**, and the
aggregator's own comment says a red sweep *"does not block a merge; `verify` no longer carries it"*.
The defect is therefore not "the sweep failed" — it is that **the sweep is NOT RUN in CI on
`e72ccc2b` and the record calls CI green**, which `docs/dev-process.md` rules on directly: *"Cannot
run is a FAILURE, never a pass."* And the commit immediately before this one (`6499cf57`) has as its
headline *"every 'all green' today was a hand-picked subset"*.

**Second, smaller error in the same block.** The commit says *"Run history dates it: `6ca7abc0`
success, `ea005a3e` failure, `e72ccc2b` failure-then-pass"*. That history is true of **Schema
gates**. For `CI` on `6ca7abc0` the conclusion is **failure** (`verify` failed), not success. Placed
under the heading "REAL CI IS GREEN", a reader takes the list as CI history.

**What a fix must change.** Name the workflow and the SHA in the claim, and say which checks did
**not** report: *"on `e72ccc2b`: `schema-gates` pass, `verify` pass; the `CI` workflow was
superseded by the next push, so `mutation-sweep` is NOT RUN in CI — the 82/82 figure is a local
run."* And re-state the run history as being about `schema-gates`.

---

## MEDIUM

### M1 — mutation entry 81 is attributed to the case that belongs to entry 33, while a case named for its own decision exists and also reddens — M3's shape, inside M3's fix

M3 (r8) was: *an entry whose NAME says "reads the last five by FIRST insertion" was bound to
`[-5:]`→`[:5]`, which is a different decision.* The fold split it in two, and the commit message
claims *"the `[:5]` off-by-end is a separate entry under its own name."* The **name** is separate.
The **case it is measured by** is not.

**Input.** Each mutation applied alone, inside a full `HARNESS_TREE` copy, mutation printed before
each run.

| Entry | Edit | Cases it actually reddens |
|---|---|---|
| 33 — *"trigger 4 reads the last five by FIRST insertion again"* | delete `per_subject.pop(…)` | exactly one: `⭐ the LAST five subjects is by occurrence, not by first insertion` → **202/203** |
| 81 — *"the window takes the FIRST `size` terminations instead of the last, a distinct off-by-end"* | `[-size:]` → `[:size]` | three, including **`only the LAST five subjects count, so early bad ones do not pin it forever`** → **200/203** |

Entry 81's `expect` names `⭐ the LAST five subjects is by occurrence, not by first insertion` — the
case that is entry 33's *only possible* witness. So the two entries share one designated case, and
the case whose name states entry 81's own decision (`only the LAST five subjects count…`,
`scripts/check-decision-scheme.py:1481`) is **named by no manifest entry at all** — verified by
collecting every `expect` string in the manifest.

**What a fix must change.** `scripts/mutations/check-decision-scheme.json`, entry 81 — set
`expect` to `["only the LAST five subjects count, so early bad ones do not pin it forever"]`.
Measured here: that mutation does redden that case, so the re-point is attributable immediately, and
it also gives that case its first witness.

### M2 — L4's fix overwrote r7's dated record with r8's end-state numbers, in both published files

L4 (r8) was: *the published figures said `179 → 200 cases` where the suite said 201.* The correction
was applied to the **r7 bullet**, replacing r7's own delta with r8's final totals.

**`docs/roadmap-to-launch.md:2523`** — inside the bullet whose text is r7's findings (M6…M9):

```
-      be scored while the schema now accepts them (M9). 179 → 200 cases, 64 → 80 mutations,
+      be scored while the schema now accepts them (M9). 179 → 203 cases, 64 → 82 mutations,
       **80/80 killed and 80/80 ATTRIBUTED**, 0 survivors.
```

**`docs/dashboard-entries.md:16433`** — inside the 2026-10-20 (r7) entry:

```
-179 → 200 cases, 64 → 80 mutations, **80/80 killed, 80/80 ATTRIBUTED**, 0 survivors, control
+179 → 203 cases, 64 → 82 mutations, **82/82 killed, 82/82 ATTRIBUTED**, 0 survivors, control
```

**Observed consequences.** The roadmap's r7 bullet now reports `64 → 82 mutations` beside
`80/80 killed` — two figures from different days in one sentence, internally inconsistent. The
dashboard's **dated 2026-10-20 entry** now claims a sweep of `82/82` that was run on 2026-10-21 over
code that entry's commit did not contain; its very next paragraph still describes r7's own fold
("Seven pre-existing manifest entries were damaged by this fold"). The r8 bullet directly below says
`201 → 203 cases, 80 → 82 mutations, 82/82 killed` — so the two adjacent records now disagree about
what r7 delivered. This is the repo's own rule about recording *which build* a check was verified
against: the "what against" was overwritten.

**What a fix must change.** Both lines back to r7's real delivered figures — `179 → 201 cases,
64 → 80 mutations, 80/80 killed and 80/80 ATTRIBUTED` — leaving `201 → 203 / 80 → 82 / 82/82` where
it already correctly sits, in the r8 record.

---

## LOW

### L1 — `check-fixture-variation rc=0, 960 parameters` is published one paragraph after introducing a function that guard cannot see

`termination_window` is module-level and public, but it is called only from `t4_no_improvement`
(`:372`) and `t9_deferral_composed` (`:409`) — **never from the suite**. `analyse()`
(`scripts/check-fixture-variation.py:1089`) examines a parameter only when *"its function is …
called from the suite"*, so `termination_window.rows` and `.size` are outside the population. The
commit did not touch `check-fixture-variation.py`, and the ratchet entry for this file
(`:625`) gained no row — consistent with the function being invisible rather than exempted.

**Not a coverage hole in substance, and I measured that rather than assuming it.** Mutating the
default reddens the suite in every direction:

| `size` default | Result |
|---|---|
| 3 | 201/203 |
| 4 | 200/203 |
| 6 | 195/203 |
| 7 | 195/203 |

So the window size is protected. The finding is the *verification claim*: the records place
`check-fixture-variation rc=0 (960 params/70 files)` immediately beside the new producer, and that
green says nothing about it. One clause in the records fixes it.

Latent, and named because this file set the precedent itself: `size` is a producer parameter whose
two readers hardcode its default into reader-facing text — t4 says *"the last 5 SUBJECTS"* and
*"{defers} of those 5"* (`:381–386`), t9 says *"of those 5 terminations"* and `5 - defers`
(`:415–421`). No caller can pass a `size` today, so nothing lies today. This is exactly r7 Claude
M8, which that round filed against `t7_sample_reached`'s `floor` — and t7 carries the written
defence for it (`:505–511`) while the new producer does not.

### L2 — below the five-subject floor, both triggers are silent while a deferral-composed improving median already exists

The "unreachable, not watched" claim is **true, and I measured it rather than reasoning it**:
300,000 random logs (1–9 subjects, 1–2 rows each, routes incl. `defer`, 25% retroactive, baselines
2/4/7), oracle = *the window itself has `median < baseline` and ≥1 `defer` while both triggers
return `None`*:

```
non-empty windows: 135,322
BOTH SILENT while the WINDOW itself is deferral-composed and improving: 0
```

Which matches the proof: for a non-empty window t4 is silent iff `med < baseline`, and t9 then fires
iff `defers ≥ 1`, so both-silent ⟹ `defers == 0`.

The remaining state is below the floor: **39,505 of those 300,000 inputs had 1–4 terminated subjects
whose median already beat the baseline with a deferral in it, and no trigger says anything.**
`termination_window`'s docstring states this honestly (*"the sample is not reached … no verdict"*),
it is pre-existing (both old copies had the same floor), and `t7_sample_reached` does not cover it —
its population is ranker predictions, not terminations. Recorded as a scope note, not a regression:
the commit's sentence is correctly scoped to *"no window in which both are silent"*, and a reader
could still take it as "both silent is impossible", which it is not.

### L3 — the one case that witnesses both ordering decisions passes when both are broken together

Compound probe (not a manifest shape — the manifest is single-edit): delete the pop **and**
`[-size:]` → `[:size]`. Result **201/203**, and the failing pair is *"only the LAST five subjects
count…"* + *"…while a prospective termination DOES enter that window"* — the designated witness
`⭐ the LAST five subjects is by occurrence, not by first insertion` **passes**. With `_ym4`
(`:1492`, six subjects `[9,9,9,1,1,1]` then A/B/C repeat at 9), both wrongs restore a median of 9.

The suite still goes red, so nothing escapes; what is lost is *which* decision the reader is told
broke. The case name is a conjunction ("the LAST five" ∧ "by occurrence, not by first insertion"),
which is this project's own tell. Fixing M1 above also fixes this, by giving each clause its own
named entry and witness.

### L4 — the retirement is sound, and I am recording the refutation because the mandate asked me to assume it was not

The mandate said to assume there was another M3 in the re-points. There is one (M1 above), and the
*retirement* is not it. The retired entry was t9's duplicate of `for r in prospective(rows):` →
`for r in rows:`; its case `"...and a RETROACTIVE deferral cannot compose the window either"`
(`:1969`) is now named by no manifest entry. But applying the surviving entry 57 alone gives
**201/203**, failing **both**:

```
[FAIL] ⭐ a retroactive termination cannot DISPLACE a subject out of t4's last-five window
[FAIL] ...and a RETROACTIVE deferral cannot compose the window either
```

So the decision is still witnessed; only the explicit attribution moved. Two entries over one anchor
are refused by `check-plan-code` by design, so retirement was the only available move. **No action.**

The two name-scope points that go with it, also no action: entries 16 and 57 are named *"trigger 4
…"* while their edits now sit in a producer **both** readers use. Accurate when written, narrower
than the subject now.

---

## Attacks that found nothing — stated so the silence is not mistaken for not looking

**A1 — does the extraction change t4's or t9's behaviour anywhere?** No. Differential test: both
versions loaded side by side (`git show e72ccc2b:scripts/check-decision-scheme.py` vs the delivered
file), **40,000 random logs × 2 functions**, inputs including missing keys, `rounds_at_termination`
as `None`/`True`/`False`/`0`/`-1`/`2.0`/`"3"`, `outcome` as `None`/`"Stopped"`, `retroactive` as
`True`/`False`/`"yes"`/`None`, 6 subjects × 2 units, baselines `0,1,2,4,7,9,4.5`, exceptions
compared as values:

```
no behavioural difference over 40000 random inputs x 2 functions
```

The `return None` → `return []` change the mandate pointed at is not observable: `termination_window`
returns `[]` only when `len(per_subject) < size`, otherwise a list of exactly `size` elements, so
`if not recent_pairs: return None` is equivalent at every reachable `size`. (`size=0` would make
`len(…) < 0` unreachable and `[-0:]` the whole list — no caller can pass it.)

**A2 — the new `main()`-driven cases: do they pass for an ambient reason?** No. Each trigger's body
was neutered with its **call site left intact** (an early `return None` inserted above the logic):

| Probe | Result |
|---|---|
| t8 body neutered, call site intact | **200/203** — including `[FAIL] ⭐ trigger 8's verdict REACHES the CLI as a WARN, and does not fail the run` → `got: (0, False, False)` |
| t9 body neutered, call site intact | **200/203** — including `[FAIL] ⭐ trigger 9's verdict REACHES the CLI too, naming how many were deferrals` → `got: (0, False, False)` |

So both cases bind the logic *and* the wiring, not the wiring alone. And the fixture-validation worry
is structurally covered: an invalid row makes `main()` print `CANNOT RUN` and return **2**
(`:1079–1083`), and both cases assert `rc == 0` as part of the tuple — so neither can be measuring a
CANNOT RUN. The trigger-9 fixture's five rows (three `accrete`, two `defer` carrying
`skipped`/`why_skipped`) therefore did validate, and the asserted WARN text proves the triggers ran
rather than an early-exit path: the only `return 0` before the trigger table is the `not rows and
not armed` NOT-YET-FED branch, unreachable with five rows.

**A3 — the sweep.** Independently reproduced: 82/82 killed, 82/82 attributed, 0 survivors, control
green, over a temp `HARNESS_TREE` with every other manifest removed and both pins re-derived. The
`215/215` and the 82-entry cardinality also reproduce. **No number in the author's MEASURED block
about the code was found wrong.** The wrong numbers are all in the records (H1, M2).

---

## What a fold must change, in order

1. **B1** — resolve round 8's missing half, and reconcile the alternation rule with
   `check-review-rounds.py` so this does not recur every odd round. Then re-check `verify`.
2. **H1** — re-state the CI claim with the workflow, the SHA, and what did not report; correct the
   `6ca7abc0` line to say `schema-gates`.
3. **M1** — re-point entry 81's `expect` to `only the LAST five subjects count, so early bad ones do
   not pin it forever`; re-run the scoped sweep.
4. **M2** — restore r7's figures in both files.
5. **L1** — add the clause saying `check-fixture-variation` does not examine `termination_window`;
   decide whether `size` keeps its parameter (t7's `floor` precedent says document the bound in the
   message, or drop the parameter).
6. **L2/L3** — scope note on the sub-floor silence; split the conjunction case if M1's fix does not
   already settle it.

**Gates NOT RUN, named rather than silently omitted:** `test:integration` and `test:e2e` (need a
live Supabase stack — out of scope for one commit touching one guard and two docs);
`scripts/check-schema-gates.sh` (no migration or schema change in `afe3b7cd`);
`scripts/check-docs.py` and `check-selftest-counts.py` (not run here — the docs findings above are
hand-derived from the diff, not from those guards, and nothing in this review depends on them).

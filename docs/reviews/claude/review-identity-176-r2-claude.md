# Adversarial review — `review-identity-176`, round 2 (Claude half)

**Subject:** commit `d02ab66b` on branch `review-identity-176`, base `origin/master` = `b2e10e39`.
That commit is the fold of round 1's Codex half (1 High, 1 Medium, 1 Low) over `bd784721`, which was
itself the fold of round 1's Claude half. Backlog #176 — the review's testimony gets a supplied
identity (`--review-id`), the wrapper performs the promotion, and CI joins the two.

**Mandate:** refute, not confirm. The design is not re-litigated; only this fold is. The working
hypothesis I was sent to test — *on this repo a defect inside the previous fix is the norm* — is
confirmed four times over, twice by the fold breaking the guards for round 1's own findings.

**Counts:** 1 Blocking · 1 High · 4 Medium · 1 Low

**Verdict: NOT CONVERGED.**

---

## What I verified GREEN, by running it

Every command was run from the repo root at `d02ab66b` with a clean tree (`git status --short`
empty). Exit codes were read directly from `$?` on the command itself, never through a pipe.

### The declared counts are the real ones — all five

```
$ python3 scripts/check-review-rounds.py --self-test ; echo rc=$?
49/49 self-test cases passed
rc=0
$ python3 scripts/codex-review.py --self-test ; echo rc=$?
162/162 passed
rc=0
$ python3 scripts/check-plan-code.py --self-test ; echo rc=$?
131/131 passed
rc=0
```

Loaded, not read — `EXPECTED_MUTATIONS` against the manifests actually on disk:

```
declared sum: 1015
declared check-review-rounds: 19     check-review-rounds.json actual entries: 19
declared codex-review:        42     codex-review.json        actual entries: 42
actual total entries across all manifests: 1015
```

The docstring counts agree too — `scripts/codex-review.py:69` says `# 162 cases` and
`scripts/check-review-rounds.py:5` says `# 49 cases`, and `check-selftest-counts.py` exits 0 over
both. The r13 drift class (a count in prose disagreeing with the suite) is not present here.

### The pre-cutover claim that carries the schema exemption

The fold's exemption rests on *"measured: 184 records, all `refused=None`"*. Derived from the
corpus, not taken from the message:

```
total verdict files: 185
by schema: {2: 99, 1: 85, 3: 1}
pre-cutover refused values: {'None': 184}
```

True at head. The exemption is sound on its stated ground.

### The join this slice exists to fix actually holds

```
$ python3 scripts/check-review-rounds.py ; echo rc=$?
  ⚠ verdict corpus: 185 read — 1 meaningfully checked below, 184 PRE-CUTOVER …, 0 refusal record(s)
review rounds: 334 parsed, 18 pre-existing exemptions, 0 silent gaps; 185 codex-review verdict(s) read, none contradicted
rc=0
```

The rename described in the commit message landed on both sides: the file is
`docs/reviews/codex/review-identity-176-r1-codex.md`, and
`docs/reviews/verdicts/review-identity-176-r1-codex.verdict.json` carries
`"review": "review-identity-176-r1-codex.md"`, `"gate_ran": true`, `"refused": false`,
`"schema": 3`. Both halves of round 1 are on disk (`…-r1-claude.md`, `…-r1-codex.md`) and the
round parses complete. The `"prompt"` field still names the pre-rename scratch file
`176-r2-codex.md` — that is accurate testimony about which file was passed, not a stale join key.

### The Medium's premise checks out

The commit claims `docs/plugins.md` was already corrected in the r1 fold and only
`process-rationale.md` lagged. Verified at head — `docs/plugins.md:163-164` carries the four-way
contract including `3 = THE GATE RAN, THE REVIEW IS NOT FILED`, and `scripts/codex-review.py:71-79`
plus `RC_NOT_FILED = 3` (`:131`) agree with both documents. The Medium was correctly scoped.

### The two new mutations kill through the cases they name

Applied in a staged `HARNESS_TREE` copy under a redirected `$HOME`, over a control proved green
first (49/49 and 162/162 in the staged tree before any edit):

```
manifest: refused truthiness    rc=1 KILLED
   [FAIL] …but a TRUTHY NON-BOOL `refused` does NOT suppress the check …
   [FAIL] …at a second distinct truthy non-bool, so this is not a special case for one value
manifest: whitespace rule       rc=1 KILLED
   [FAIL] …nor one with leading whitespace, which survives a join and is invisible in a listing
manifest: reserved names        rc=1 KILLED
   [FAIL] …nor a reserved device name, which cannot be created on Windows at all
```

I also drove three unmanifested deletions to check the other new cases are not decorative — the
`read_verdicts` non-bool refusal, the drive-letter rule and the `%2f` rule each go red through their
own case. Those three are falsifiable.

### Every `check-*` gate `ci.yml` runs, locally

`check-docs.py`, `check-selftest-counts.py` (+`--self-test`), `check-gate-falsifiability.py`,
`check-ratchet-contract.py`, `check-anchors.py`, `check-review-rounds.py`,
`check-guard-coverage.py --self-test`, `check-producer-enumeration.py`, `check-group-claims.py`,
`check-fixture-variation.py` — **all rc=0**.

⚠ **And that green is exactly why B1 below is invisible.** Every gate a local run can reach is
green; the one gate that reads the mutation anchors (`check-plan-code.py --mutate .`) is the one
the fold deliberately did not run locally.

---

## Blocking

### B1 — this fold orphaned the mutation anchors for round 1's OWN Blocking and High, and `--mutate .` is a step in the required `verify` job

**Premise.** `scripts/mutations/*.json` bind by exact text. `.github/workflows/ci.yml:436` runs
`python3 scripts/check-plan-code.py --mutate .` inside job `verify` (`ci.yml:26`), and that step's
own comment states its failure conditions: *"FAILS IF: a mutation survives · **an anchor is missing
or ambiguous** · …"*. `check-plan-code.py --self-test` does **not** resolve anchors, so an orphan is
silent locally — which is why 131/131 passed above.

**Measurement.** I swept every entry in every manifest against the delivered tree using the
harness's own rule (`scripts/check-plan-code.py:1558-1575`: `src.count(find)` must be exactly 1):

```
ANCHOR count=0  check-review-rounds.json  'r1 B1: a refusal record is read as testimony that the gate did not run'
                ->  '        if rec.get("refused"):\n            continue'
ANCHOR count=0  codex-review.json         'r1 H1: the relative components stop disqualifying an id'
                ->  '    return review_id not in (".", "..")'
total anchor problems: 2   (out of 1015 entries)
```

Both were intact at the parent `bd784721` and were broken by this commit:

- `scripts/check-review-rounds.py:240` is now `if rec.get("refused") is True:` — the r2 fix itself
  moved the text the r1 B1 mutation names. (The other occurrence, `:191`, does not match: the anchor
  is two lines and `era_split`'s second line is `out["refused"] += 1`.)
- `scripts/codex-review.py:334` is now `if review_id in (".", ".."):` / `return False` — the r2 Low
  rewrote the `return` the r1 H1 mutation names.

**Why Blocking.** Two of this branch's three previous-round findings lose their only mutation guard,
and the required check goes red. `EXPECTED_MUTATIONS` cannot see it: both entries still *exist*, so
19 and 42 still match, and the sum stays 1015 — an orphan keeps the count while removing the
coverage. This is the repo's measured *"an anchor is unbound by ANY nearby edit"* class, and the
fold's own `VERIFIED, by running it` block lists the two **new** mutations and never the manifest as
a whole.

**Status of the CI evidence.** Draft PR #343 is on exactly `d02ab66b`
(`headRefOid: d02ab66b2d8f944f7f1d909d41a55fb36429cf75`) and `gh pr checks 343` showed
`verify  pending` when I looked; `schema-gates` had already passed. So the sweep result is **not yet
observed** — my Blocking rests on the anchor measurement above, not on a CI verdict, and I did not
run `--mutate .` locally per the brief.

**Proposed fix.** Retarget both anchors at the text that is now there — `if rec.get("refused") is
True:\n            continue` → `if False:\n            continue`, and `if review_id in (".",
".."):\n        return False` → `if False:\n        return False` — and re-confirm each still reds
through the `expect` it names. Structural: any fold that edits a guarded line must sweep the
manifests, and nothing local does that today.

---

## High

### H1 — `gate_ran` is tested for truthiness five lines below the truthiness fix, and `read_verdicts` type-checks `refused` but not `gate_ran`

**Premise.** The High this fold closed was: *a truthy non-bool `refused` switched the CI join off
without being reported as unreadable*. The fix was applied to one field. `gate_ran` — which
`read_verdicts` already singles out (`scripts/check-review-rounds.py:279`, *"no `gate_ran` field —
cannot tell whether the gate ran"*) and which `verdict_record`'s docstring calls *"the load-bearing
field"* (`scripts/codex-review.py:614`) — is read at `scripts/check-review-rounds.py:245` as:

```python
        if not rec.get("gate_ran"):
```

**Measurement**, against the delivered functions, trusted-era records (`schema: 3`,
`refused: false`), review filed as `x-r1-codex.md`:

```
A FILED review (the r1 B1 direction) — a false gate_ran must be REPORTED:
  gate_ran=False    -> 1 problem(s)  REPORTED
  gate_ran=0        -> 1 problem(s)  REPORTED
  gate_ran=None     -> 1 problem(s)  REPORTED
  gate_ran='false'  -> 0 problem(s)  ⛔ SUPPRESSED
  gate_ran='no'     -> 0 problem(s)  ⛔ SUPPRESSED
  gate_ran='0'      -> 0 problem(s)  ⛔ SUPPRESSED

Does read_verdicts type-check gate_ran the way it now type-checks refused?
  records: 1  bad: []      # `{"gate_ran": "false"}` is accepted as a good record
```

A verdict carrying `"gate_ran": "false"` therefore (a) reads as *the gate RAN* in both branches of
the join, (b) silences the *failed gate beside a filed review* direction entirely — the r1 B1
direction — and (c) is **not** reported as unreadable, because the new refusal at `:286` names only
`refused`. That is the folded High's own sentence, verbatim, one field over.

And nothing sees it: hardening the line to `if rec.get("gate_ran") is not True:` in a staged copy
left the suite at **49/49, rc=0** — no case distinguishes truthiness from identity for this field,
so the defect and its fix are indistinguishable to the guard.

**Why High, not Blocking.** The producer is typed — `verdict_record` writes `"gate_ran":
bool(gate_ran)` (`scripts/codex-review.py:663`) — so no current record can carry a string, and the
corpus is clean. The exposure is hand-written, drifted or future-producer testimony, which is
precisely the exposure the `refused` High was filed over and fixed for; treating the identical shape
as lower severity on the neighbouring field would be arguing the finding away.

**Proposed fix.** Make it one rule over both fields rather than two half-rules: in `read_verdicts`,
refuse a non-bool `gate_ran` at or above `TRUSTED_SCHEMA` on the same clause as `refused`
(`gate_ran` is *required* to be present, so it needs no `is not None` escape, but the pre-cutover
corpus should be checked before tightening below the era gate), and read it as `is True` at `:245`.
Add the two-distinct-truthy-non-bools case shape the `refused` fix already uses, and a manifest
entry. Structural.

---

## Medium

### M1 — the same truthiness idiom survives in `era_split`, so the two functions now partition one record by two different rules

**Premise.** `scripts/check-review-rounds.py:191`, untouched by this fold:

```python
    for _src, rec in records:
        if rec.get("refused"):
            out["refused"] += 1
        elif (rec.get("schema") or 0) < TRUSTED_SCHEMA:
```

`era_split` is the function r1 M3 created so the printed caveat would be **derived rather than
quoted**; its output is the `⚠ verdict corpus: …` line a reader is given as the honest account of
what the check can mean anything about. The fold's comment at `:239` asserts the rule is complete:
*"`read_verdicts` now refuses a non-bool `refused` outright, so this line and that one are two
halves of one rule"*. There are three sites, not two.

**Measurement**, delivered `era_split` vs delivered `verdict_problems` on the same record:

```
schema=2 refused='false'   era_split={'refused': 1, 'pre_cutover': 0}  verdict_problems=0 (pre-cutover skip)
schema=2 refused='no'      era_split={'refused': 1, 'pre_cutover': 0}  verdict_problems=0
schema=2 refused=1         era_split={'refused': 1, 'pre_cutover': 0}  verdict_problems=0
```

The record is reported to the reader as *a refusal, deliberately excluded* while the check actually
excluded it as *pre-cutover* — two different partitions of the same file, from the function whose
whole purpose is that the partition is not a guess. Hardening `:191` to `is True` in a staged copy
left the suite **49/49, rc=0**: no case and no mutation sees this line's truthiness either.

**Why Medium and not High — stated honestly.** At or above `TRUSTED_SCHEMA` the partner half at
`:286` now refuses a non-bool before `era_split` ever sees it, and below it the 184 pre-cutover
records are frozen at `refused=None` (measured above) with a producer that stamps `schema: 3`. So
there is no reachable mis-count today. The finding is the *class*: the fix was applied as an
instance, and the comment claims a completeness the file does not have.

**Proposed fix.** `is True` at `:191`, and a case driving `era_split` with a truthy non-bool at a
pre-cutover schema. Structural.

### M2 — the reserved-name rule uses the wrong token, so it refuses legal ids and misses the shape it names — and its one case encodes that error

**Premise.** `scripts/codex-review.py:357`:

```python
    return review_id.split("-")[0].upper() not in _RESERVED_NAMES
```

The Windows device-name reservation applies to the filename component's base — the portion **before
the first period** — and to that base followed immediately by an extension (`NUL.txt` is `NUL`). It
does not apply to a hyphen-separated first token. So this token is not the rule it names.

**Measurement**, delivered function:

```
  CON-r3-codex                 accepted=False   win_base='CON-r3-codex'     ← legal on Windows, REFUSED
  aux-tokens-r1-codex          accepted=False   win_base='aux-tokens-…'     ← legal on Windows, REFUSED
  com1-migration-r1-codex      accepted=False                               ← legal on Windows, REFUSED
  prn-layout-r2-claude         accepted=False                               ← legal on Windows, REFUSED
  CON.md-r1-codex              accepted=True    win_base='CON'              ← RESERVED, accepted
  NUL.json-r1-codex            accepted=True    win_base='NUL'              ← RESERVED, accepted
  COM0-r1-codex / LPT0-r1-codex  accepted=True                              ← not in _RESERVED_NAMES
```

Wrong in both directions. The over-refusal side is the live one: an id whose first hyphen token is
`con`, `aux`, `nul`, `prn`, `com1`–`com9` or `lpt1`–`lpt9` is a `CANNOT RUN` before dispatch
(`review_identity` refuses on `is_single_segment`, `scripts/codex-review.py:383`) — fail-closed, so
no spend, but a review that will not start for a reason that is not real.

The one case, `chk("…nor a reserved device name, which cannot be created on Windows at all",
is_single_segment("CON-r3-codex"), False)` (`:1795`), asserts the incorrect behaviour, and the
manifest mutation `return … not in _RESERVED_NAMES` → `return True` is killed **through that case** —
so the guard is green about a property the code does not have.

**Also, the justification.** The comment at `:294-296` reads *"this repo's mutation harness already
stages trees on more than one platform"*. `grep -rn "runs-on" .github/workflows/` returns
`ubuntu-latest` three times and nothing else; the second platform is the developer's macOS machine.
Neither reserves these names. The rule guards a platform this repo does not run on.

**Proposed fix.** Either drop the rule (it protects nothing measured) or make it the rule it names —
`review_id.split(".")[0].upper()`, plus `COM0`/`LPT0` — and replace the case with one that
distinguishes the two tokens (`CON.md-r1-codex` refused, `con-fence-r1-codex` accepted), so the
mutation can no longer be killed by the wrong premise. Transitional if dropped; structural if kept.

### M3 — five new refusal reasons, one unchanged refusal message, which names three rules none of them broke

**Premise.** `review_identity`'s docstring says *"The refusal names BOTH accepted shapes, because a
caller who got the shape wrong needs to see the shape"* (`scripts/codex-review.py:371`). The message
at `:385-386` was not touched by this fold:

```python
            f"CANNOT RUN — --review-id {review_id!r} is a NAME, not a path. It must be ONE path "
            f"segment: no `/`, no `\\`, and not `.` or `..`. …"
```

**Measurement**, delivered `review_identity`:

```
id=' plan-x-r1-codex'         → "… is a NAME, not a path. It must be ONE path segment: no `/`, no `\`, and not `.` or `..`."
id='plan-x-r1-codex '         → (identical)
id='CON-r1-codex'             → (identical)
id='C:plan-x-r1-codex'        → (identical)
id='docs%2Fplan-x-r1-codex'   → (identical)
id='aaaa…' (201 chars)        → (identical)
```

Every one of the five shapes the r2 Low added is refused with a sentence enumerating three rules the
id did not break. The caller is told the wrong reason for a fail-closed stop on a paid gate. The
`{review_id!r}` does at least make trailing whitespace visible, which is the one mitigation.

**Why Medium.** It is the repo's signature shape — a message asserting a property the code no longer
has — on the diagnostic path of a `CANNOT RUN`, and this repo's own rule is that a cannot-run must
say what was wrong. Nothing tests the message against the rule set, so it will drift again.

**Proposed fix.** Have `is_single_segment` return the reason (or a sibling `segment_problem()`
returning `str | None`) and interpolate it, so the enumeration cannot diverge from the checks; add a
case that the refusal text names the rule the id actually broke, for at least two of the five.
Structural.

### M4 — "a stem AT the cap is still accepted, so the bound is a cap and not an off-by-one" is not what the case measures, and I drove the off-by-one surviving

**Premise.** The commit message states this as VERIFIED, and the case at
`scripts/codex-review.py:1799` is:

```python
    chk("…while a stem AT the cap is still accepted, so the bound is a cap and not an off-by-one",
        is_single_segment("a" * 190 + "-r3-codex"), True)
```

The cap in the code is `if len(review_id) > 200:` (`:353`).

**Measurement.**

```
  'AT the cap' case id length = 199   cap in code = 200   accepted=True
  over-cap case id length     = 210   refused=True
  the TRUE boundary: len 200 -> accepted   len 201 -> refused
```

199 is not the cap, and 210 is not one past it — neither case touches the boundary. So I mutated the
comparison in the staged copy:

```
MINE: length cap off-by-one (> 200 -> >= 200)    rc=0 ⛔ SURVIVED
```

The whole 162-case suite stays green under exactly the off-by-one the case is named for. This is the
repo's *"a test that cannot fail"* / *"fixing a premise is not covering the branch"* class: the case
is satisfied, but not by the mechanism it claims.

**Why Medium.** No live defect — the cap is correct as written — but a stated, committed
verification is false, and the boundary is unguarded in both directions, so a later edit to `200`
or to `>` is free.

**Proposed fix.** Pin the two sides of the boundary explicitly: an id of length exactly 200 accepted
and exactly 201 refused, constructed from the length rather than from a hand-counted `"a" * 190`
(the current fixture's length is an accident of `len("-r3-codex")`). Add a manifest entry for the
comparison. Structural.

---

## Low

### L1 — `read_verdicts` promises a CANNOT RUN for a malformed verdict and instead raises an unhandled `TypeError` on a malformed `schema`

**Premise.** The docstring at `scripts/check-review-rounds.py:264` is *"(records, unreadable). A
malformed verdict is a CANNOT-RUN, never a silent skip."* The fold added a type check for `refused`
at `:286` and reads `schema` in the same expression:

```python
        if (rec.get("schema") or 0) >= TRUSTED_SCHEMA and _ref is not None and not isinstance(_ref, bool):
```

**Measurement**, a verdict file containing `{"schema": "3", "gate_ran": false, "refused": "false", …}`:

```
  read_verdicts RAISED: TypeError '>=' not supported between instances of 'str' and 'int'
```

`main` distinguishes rc 1 (contradictions found, `:660`) from rc 2 (CANNOT RUN, `:667`); an
uncaught `TypeError` exits **1**, i.e. a malformed record is reported as a *finding* rather than as
*this check could not be run* — the one distinction this guard maintains deliberately. The same
unguarded comparison is in `verdict_problems:242` and `era_split:193` and is pre-existing there; the
new line is the third copy, added by the commit whose stated purpose was that malformed testimony
must be refused loudly rather than mishandled quietly.

Same paragraph, a smaller sibling: the drive-letter rule is `len(review_id) > 1 and review_id[1] ==
":"` (`:355`), while `:` is nonportable anywhere in a filename, not only at index 1 — so
`foo:bar-r1-codex` passes.

**Why Low.** It needs a hand-edited or non-conforming verdict; the producer writes an int
(`VERDICT_SCHEMA = 3`), the corpus is clean at all 185 files, and a traceback is loud even when it is
the wrong exit code.

**Proposed fix.** One `schema_of(rec)` helper returning an int or flagging the record as bad, used at
all three sites, so a non-numeric `schema` becomes an entry in `bad` with its own case. Structural.

---

## What I could not finish — treat these as NOT RUN

- **The mutation sweep, `check-plan-code.py --mutate .`.** Not run: the brief forbids it locally
  (~14 min) because it runs on GitHub for this branch. Draft PR #343 is on `d02ab66b` and its
  `verify` check read **pending** when I looked. **Any sweep figure in the commit message is NOT
  INDEPENDENTLY VERIFIED by me.** What I did verify is the anchor resolution the sweep depends on —
  B1 — and the two new mutations' kills, both in a staged `HARNESS_TREE` copy over a green control.
- **`test:integration` / `test:e2e`** — need a live Supabase stack; not attempted, not relevant to
  this diff.
- **The Postgres schema gates** — not run; this diff touches no schema, and `schema-gates` passed on
  PR #343 for this exact SHA.
- **The `COM0`/`LPT0` point inside M2** is from documentation I could not open offline. The rest of
  M2 — the `split("-")` token and the measured accept/refuse table — is driven against the delivered
  function and does not depend on it.

---

## Verdict

**NOT CONVERGED.** 1 Blocking · 1 High · 4 Medium · 1 Low.

The two headline findings are both *the fix breaking or missing its own class*: B1, this fold
orphaning the mutation guards for round 1's Blocking and High by editing the exact lines they anchor
on; and H1, the truthiness rule applied to `refused` and not to `gate_ran` five lines below it, with
no case able to tell the two apart. M1 is the third site of the same idiom. That is three instances
of one class in a commit whose message says the rule now has *"two halves… because either alone
leaves a hole"*.

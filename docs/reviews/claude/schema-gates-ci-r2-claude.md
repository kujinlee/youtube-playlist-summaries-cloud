# Adversarial review — `schema-gates-in-ci` (PR #297), round 2 (Claude half)

**Subject: the DELTA since round 1, not the branch.** Round 1 (both halves) found 15 defects and all
were fixed; this round exists because on the previous branch both late defects were introduced by
fixes. So the subject is the repairs.

## ⚠ THE WORKING TREE MOVED THREE TIMES WHILE I READ IT, AND THAT CHANGES WHAT THIS DOCUMENT CLAIMS

This is stated first because a review that silently reviews two different trees is worse than one
that reviews the wrong tree loudly.

| When | `HEAD` | What I had measured by then |
|---|---|---|
| start | `5aca2036` | population of 21, manifest 11, `EXPECTED_MUTATIONS` sum 570 |
| mid | `e00638e2` → `d3fc2a92` → `9ef2338b` | — |
| end | `9ef2338b` + then-uncommitted `check-storage-independence.py`, `check-plan-code.py`, `scripts/mutations/check-storage-independence.json` — **committed as `28c2da08` while I was writing this file** | population **27**, manifest **13**, sum **572**, self-test **46** |

That change carries `⟳ r2 HIGH (codex)` and `⟳ r2 MEDIUM (codex)` markers, so the Codex
half of this round landed and was partly repaired while I was working. **Everything below states
which of the two trees it was measured against.** The findings at the end are all against the LATER
tree — I re-ran every attack after the tree moved rather than reporting against a snapshot that no
longer exists.

Note for the coordinator: `docs/reviews/verdicts/schema-gates-ci-r2-codex.verdict.json` exists
(untracked, 17:21) but `docs/reviews/codex/schema-gates-ci-r2-codex.md` does not. `check-review-rounds.py`
wants both halves filed or a written `REVIEW GAP:`.

---

## Verdict

**3 Medium, 2 Low. No Blocking, no High.** The three repairs I was asked to attack hardest all hold
under the constructions I could build against them; two of the three carry a *stated bound that is
narrower than the code*, which is this branch's recurring shape and is what the Mediums are about.

---

## What I VERIFIED, with the measurement

### 1. The report-format fix is real, and I checked it with the CONSUMER, not a copy of its rule

The brief's warning was that the coordinator's own pre-flight verifier re-implemented the attribution
rule and was more generous than the harness. So I did not write a checker. I imported
`scripts/check-plan-code.py`, filtered `load_manifests` to the one target, pinned
`EXPECTED_MUTATIONS`, and called **`mutate_delivered(REPO)`** — the same function CI runs, which
attributes through `parse_fail_names` (`scripts/check-plan-code.py:1447`).

Measured against `5aca2036` (manifest 11):

```
control  scripts/check-storage-independence.py  rc=0  "self-test: 38 cases, 38 passed, 0 failed"
11 mutations, 11 caught, 11 attributed: True, survivors: []
re-control  rc=0
ok = True   verdict object = Measured
```

Every entry carries both `caught: True` **and** `attributed: True` — the second is the field that was
false in CI's `570 killed, 559 attributed`. Against the later tree the same file's suite is 46 cases
and the manifest is 13; `python3 scripts/check-plan-code.py --self-test` is **128/128** and
`sum(EXPECTED_MUTATIONS) == 572`, which its own `case("the declared counts are the real ones", …, 572)`
asserts. **The fix holds.**

### 2. Every `.py` self-test on the branch uses `[FAIL] `; the two shell ones do not (→ Low 1)

I enumerated each file `master..HEAD` touches under `scripts/` that has a self-test and read its
failure-print line. All eight Python files print `[FAIL] {name}: got … want …`.
`scripts/ci/start-schema-db.sh:254` and `scripts/m4-base-db.sh:150` print `  ✗ …`.

### 3. The container allow-list refuses what it claims to refuse, live

`redis_ru202` is a real unrelated container on this machine — the one Codex used in r1 to prove the
deny-list's reach. It is **still running** after this review. `refuses_name` measured directly:

```
ALLOW   m4_schema_gates    ALLOW  m4_prod_client
REFUSE  redis              REFUSE  m4         REFUSE  M4_x       REFUSE  m4_
```

### 4. The retry's error reporting does what the commit message says

`5aca2036`'s point was that the first version blamed a registry it had never contacted. Measured:

* `backoff_delays 5` → `5 10 20 40 ` (75s across five attempts); `backoff_delays 1` → empty.
* `"${err##*$'\n'}"` **does** yield the last line of a captured multi-line error inside double quotes
  (I ran it rather than reasoning about it — ANSI-C quoting inside `${…}` is exactly the kind of
  thing that is wrong half the time):
  `err="line one\nline two\ntoomanyrequests: Rate exceeded"` → `toomanyrequests: Rate exceeded`.
* `docker info` sits after the name refusal and **before** `pull_image`
  (`scripts/ci/start-schema-db.sh:132` vs `:155`), so a dead daemon costs 0s of backoff, not 75s.
* `docker rm -f "$NAME"` (`:161`) is now after the pull, so a registry failure no longer destroys an
  existing container on the way to failing.

`docker info` passing while pulls cannot is the ordinary case (daemon up, registry throttling) — that
is what the retry is *for*, and the message now quotes the registry rather than guessing at it. I
found no failure mode the retry masks: nothing retries the database build, and `pull_image` ends on
`docker image inspect`, so the return value is a fact about the local image store rather than about
`docker pull`'s exit code.

### 5. "14s unchanged" — confirmed, and the suite is green over the database it builds

```
$ time scripts/ci/start-schema-db.sh m4_review_r2
✅ 'm4_review_r2' ready — 27 migrations applied, M4 PRESENT.
real  0m14.322s

$ PGCONTAINER=m4_review_r2 M4_PHASE=post scripts/check-schema-gates.sh
✅ all schema gates green     (rc=0, 15/15)
```

Built and reaped my own container per the brief; the developer's `supabase_db_…` stack was never
touched.

### 6. The r1 HIGH's own case still holds, and the r2 repair closes three more I built independently

Before I saw the uncommitted r2 fix, I copied the guard's subject tree to scratch and planted storage
reads in files the suite reaches **one level down**. Against `5aca2036` (population 21):

| # | Planted read | 21-file population |
|---|---|---|
| A1 | `…/schema/05_assert.sql` — the r1 HIGH's own case | CAUGHT |
| A6 | `05_assert.sql` widens `nspname in ('public','storage')` | CAUGHT |
| **A2** | `scripts/m4-base-db.sh` (gate 12 runs it; it queries the catalog for a verdict at `:179-189`) | **MISSED** |
| **A3** | `docs/superpowers/specs/m4/seed-assertion-corpus.sql` (gate 8 `cat`s it into the assertion transaction, `run-schema-assertions.sh:47`) | **MISSED** |
| **A4** | `scripts/build-m4-schema.py` (gate 12 pipes its output into `psql`, `mutate-live-schema-check.sh:191-196`) | **MISSED** |

That is the r1 HIGH's class surviving its own fix one level down. **The uncommitted r2 fix closes all
three** — re-run against the later tree, population 27, A2/A3/A4 all CAUGHT, control still 0 findings.
I am recording this as corroboration of the Codex half rather than as a finding, because the repair
landed before I could file it — but the constructions are worth keeping, because they are now the
regression evidence for the transitive step.

---

## Findings

### MEDIUM 1 — the transitive step resolves exactly ONE hard-coded variable NAME, and its comment says "to a fixpoint"

`scripts/check-storage-independence.py` (uncommitted), transitive block:

```python
for var, val in re.findall(r'^([A-Z_]+)="([^"]*)"', body, re.M):
    body = body.replace(f'"${var}"', f'"{val}"').replace(f'"${{{var}}}"', f'"{val}"')
body = re.sub(r"\$\{?REPO\}?/", "", body).replace('"$REPO/', '"')
```

The last line is a special case for the literal identifier `REPO`. It exists because
`run-schema-assertions.sh:46-47` happens to spell its root that way. A gate that computes its root
into `$BASEDIR`, `$ROOT` or `$TOP` and then names a SQL file through it resolves to a path that does
not exist, and the file silently leaves the population — no error, no `CANNOT RUN`, guard still green.

**CONTROL, measured.** The identical shipped file, `REPO` renamed to `BASEDIR` by `re.sub(r"\bREPO\b", …)`
and *nothing else* changed (the rename is faithful — the gate still names the same seed):

```
CONTROL  run-schema-assertions.sh as shipped   population=27  seed-assertion-corpus.sql in scope: YES
RENAME   the same file, $REPO -> $BASEDIR      population=26  seed-assertion-corpus.sql in scope: NO
```

The comment above the block reads *"Resolve TRANSITIVELY: every file admitted is itself read for
variables and path tokens, **to a fixpoint**"*. The fixpoint is real; the *resolution* is not general.
This is the third time on this branch that a fix was written to the shape of the one file it was
fixing — the guard's own header says so about itself at the r1 HIGH (*"I looked for the shape I
expected instead of the shape the file uses"*).

**Falsifier:** rename `REPO` in `scripts/run-schema-assertions.sh` and re-run
`python3 scripts/check-storage-independence.py` — it prints `26 gate files checked` and stays green.

**Cheapest honest fix** (I did **not** run it): drop the `REPO` special case and instead resolve any
`^([A-Z_]+)=` whose value, after stripping a leading `$VAR/` of *any* name, resolves to a real file —
or, if generality is not wanted, state the bound in the docstring beside the two already there
(`SQL assembled at runtime`, the `#`-in-shell approximation) rather than claiming a fixpoint.

### MEDIUM 2 — `NOT_A_GATE` excludes a DIRECTORY, and that directory holds a seed as well as the fixture

```python
NOT_A_GATE = ("supabase/", "scripts/ci/")
```

The comment justifies `scripts/ci/` with one file: *"`storage-service-fixture.sql` creates
`storage.buckets`, which is its entire job."* True — but the directory also holds
`scripts/ci/seed-corpus.sql`, which `start-schema-db.sh:233` applies **after** the migrations and
whose header says it asserts its own postcondition.

**MEASURED.** A `storage.*` read planted in `scripts/ci/seed-corpus.sql` is **MISSED** (population
unchanged at 27, 0 findings). A read planted in the *other* seed,
`docs/superpowers/specs/m4/seed-assertion-corpus.sql`, is **CAUGHT** — because the same commit
admitted that one as verdict-affecting. Two seeds, opposite treatment, and the difference is which
directory they live in.

**The counter-reading, stated fairly:** `seed-corpus.sql` runs at *build* time and is arguably part of
the database the gates read — the subject — while `seed-assertion-corpus.sql` runs *inside* a gate's
own transaction. That distinction is defensible. It is also not the one the code makes: the code makes
a path distinction, and the comment justifies it with a file that is not the one at risk. If the
build-time/gate-time line is the intended rule, it should be the stated one, and
`storage-service-fixture.sql` should be excluded by name or by a marker rather than by owning a
directory.

**Falsifier:** add `select id from storage.objects` to `scripts/ci/seed-corpus.sql`;
`check-storage-independence.py` stays green and still prints `the CI fixture stays scaffolding`.

### MEDIUM 3 — the allow-list's CHARACTER CLASS is unguarded, and the refusal message overstates it

`scripts/ci/start-schema-db.sh:82`:

```bash
m4_[a-z0-9_]*) return 1 ;;                 # the only shape this script may destroy
```

The refusal message at `:124` tells the reader it destroys only
`` `m4_<lowercase/digits/underscores>` ``. The glob constrains **only the first character** after
`m4_`; `*` then matches anything. Measured:

```
ALLOW   m4_UPPER_TAIL      ALLOW   m4_x-y-z      ALLOW   m4_a b      ALLOW   m4_a;rm
REFUSE  m4_   REFUSE  m4   REFUSE  M4_x   REFUSE  m4_../../etc   REFUSE  redis
```

No injection risk — `docker rm -f "$NAME"` is quoted and Docker rejects illegal names — so this is
about the claim, not about reach. The sharper half is that **no case observes the class at all**:

```
CONTROL                                   self-test: 17 cases, 17 passed, 0 failed
MUTATION  m4_[a-z0-9_]*  ->  m4_*         self-test: 17 cases, 17 passed, 0 failed   (rc=0)
```

All four allow-list cases added by `c4516720` discriminate the `m4_` **prefix** and its case
(`M4_UPPER`), never the class. That is the same defect r1 MEDIUM 3 filed against this very function —
*"the case would have gone on passing if this line were deleted"* — reintroduced by the commit that
fixed it, which is precisely the failure mode this round was convened for.

**Falsifier:** the mutation above, already run. **Fix** (not run): either add a case such as
`refuses_name "m4_Prod_Analytics"` → REFUSE and tighten the glob to a `case` that rejects a
non-conforming tail, or correct the message to say `m4_` + one lowercase/digit/underscore, and say the
tail is unconstrained.

### LOW 1 — the report-format fix was applied at one site and not at its two shell siblings

`debae5eb` fixed `check-storage-independence.py`'s `  ✗ <name>` → `[FAIL] <name>: got … want …` and
wrote a 9-line ⛔ block explaining that the format is a contract. The same branch ships
`scripts/ci/start-schema-db.sh:254` with `echo "  ✗ $1 — wanted '$2', got '$3'"`, and leaves
`scripts/m4-base-db.sh:150` (which it edits, for a different reason) with the same shape.

**It is not load-bearing today, and I checked rather than assumed:** `check-plan-code.py:487` runs a
mutation target as `[sys.executable, name, "--self-test"]`, so a `.sh` cannot be a mutation target at
all, and no manifest names one. So this is latent, not live — which is why it is Low and not Medium.
It becomes live the moment anyone wants a mutation entry for either script, and the branch's own
history is that the `✗`-vs-`[FAIL]` gap is invisible until eleven kills go unattributed in CI.

**Falsifier:** add a mutation manifest entry for either shell script; the kill will be red-but-
unattributed.

### LOW 2 — a stale number inside the ratchet's own explanation

`scripts/check-plan-code.py:3003-3006`:

```python
case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 572)
# ⟳ 2026-09-13: 559 -> 566. +7 for `check-storage-independence.py`, the CI storage
```

The **case** is correct (572, verified; `--self-test` 128/128). The sentence beside it states the
wrong new total (566) and the wrong delta (+7 against a manifest that now holds 13). The number moved
`559 → 566 → 570 → 572` across the branch and the prose was updated once. Nothing observes it —
`check-selftest-counts.py` reads the `--self-test # N cases` declaration, not this comment.

**Falsifier:** `sum(EXPECTED_MUTATIONS.values())` is 572 and
`len(json.load(open("scripts/mutations/check-storage-independence.json")))` is 13; the comment says
566 and 7.

---

## Things I checked and will NOT file, with the measurement that stopped me

* **The undeclared self-test count.** `check-storage-independence.py` has no `--self-test  # N cases`
  declaration, so its 46 has no outside observer. I nearly filed it — then measured: **14** of
  `scripts/*.py` with a self-test declare no count (`build-m4-schema.py`, `gen-dashboard.py`,
  `m4_catalog.py`, `verify-exclusion-reasons.py`, …). That is the house norm, not a branch defect.
* **`scripts/ci/*.py` invoked by the suite.** I expected the `scripts/ci/` exclusion to hide a real
  gate placed there. It does not: `gate_files`'s first branch (`scripts/[\w./-]+\.py` out of the
  suite text) applies no `_is_subject` filter, so a suite-invoked `scripts/ci/check-blob-drift.py`
  with a storage read **is** reported. The two branches disagree about `scripts/ci/`, but only in the
  safe direction.
* **The `#`-in-shell approximation.** My first construction (`psql -c "…storage.objects" # comment`)
  was CAUGHT — the reference precedes the `#`. The real bound needs the `#` *before* the reference on
  the same line, which is what the docstring already states. Not a finding; my case was wrong.
* **`${err##*$'\n'}` inside double quotes.** Suspected broken, measured working. See above.
* **`NAME="$(resolve_name ${1+"$1"})"`.** The unquoted `${1+"$1"}` with a quoted inner expansion is
  the correct idiom for "pass the argument through only if it was given"; an argument with spaces
  survives as one word.
* **Missed second-level gates beyond A2/A3/A4.** After the transitive fix I re-enumerated: the
  population of 27 now includes `build-m4-schema.py`, `m4-base-db.sh` and `seed-assertion-corpus.sql`.
  It also picks up `codex-frontier-model.py`, `codex-review.py` and `subject_status.py` — over-inclusion
  from path tokens in prose, harmless (control is clean) but worth knowing the 27 is not 27 gates.

## Coverage of this round

Ran: `check-plan-code.py --self-test` (128/128) · `check-plan-code.mutate_delivered` over the storage
manifest (11/11 caught **and attributed**, 0 survivors, both controls green) ·
`check-storage-independence.py --self-test` (38, then 46 after the tree moved) and ordinary mode
(21, then 27 files, green) · `start-schema-db.sh --self-test` (17/17) and its mutated variant ·
`check-selftest-counts.py` (37 declared, all verified) · `check-ratchet-contract.py` (35 guards, OK) ·
`start-schema-db.sh m4_review_r2` (14.3s, 27 migrations) · the full fifteen-gate suite over it (rc=0).

Not run: the CI workflow itself (no runner), and `--mutate .` in full (571 other mutations, unchanged
by this delta; the one target it changed I ran directly).

---

# Coordinator response — all five accepted and fixed, each verified with the reviewer's own falsifier

**First, the disclosure at the top of this review is my fault and it is the most useful thing in it.**
The tree moved three times while this half was reading, because I was fixing the Codex half's findings
in the same working tree at the same time. The reviewer handled it correctly — re-ran every attack
against the later tree and said which tree each measurement belongs to — but that was luck rather
than design. **A review and the repair of a different review must not run concurrently in one tree.**

## MEDIUM 1 — the transitive resolver was written to the one file it was fixing. Again.

`re.sub(r"\$\{?REPO\}?/", …)` special-cased a literal identifier because `run-schema-assertions.sh:39`
spells its root that way. The reviewer's control: rename `REPO` → `BASEDIR`, change nothing else,
population `27 → 26` and the seed leaves silently.

Now any `$VAR/` or `${VAR}/` is stripped whatever it is called. **Re-run of the reviewer's own
falsifier after the fix: population 30, `seed in scope: YES`.**

⚠ **Two fixture defects had to be fixed before the mutation for this could kill**, and both were mine:
the first fixture assigned its root LITERALLY, so the per-variable substitution already handled it and
the generic strip was never exercised; the second used `TOPDIR="$(…)"`, which the literal-assignment
regex partially captures — the resulting garbage happens to leave a matchable path. Only an UNQUOTED
computed assignment isolates the clause under test, which is what the real file uses.

## MEDIUM 2 — excluded a DIRECTORY, justified by one file in it

`scripts/ci/` held `storage-service-fixture.sql` (which creates the storage tables — its whole job)
AND `seed-corpus.sql` (which runs against the database the gates then read). A `storage.*` read
planted in the second was MISSED while the identical read in the other seed was CAUGHT — two seeds,
opposite treatment, by directory.

The exclusion is now BY FILE (`NOT_A_GATE_FILES`). **Re-run of the reviewer's falsifier: the planted
read in `scripts/ci/seed-corpus.sql` is CAUGHT, and the fixture is still excluded.**

## MEDIUM 3 — the allow-list bound one character, and the message promised otherwise

`m4_[a-z0-9_]*` — a glob class binds ONE character and the trailing `*` matched the rest, so
`m4_UPPER`, `m4_x-y-z`, `m4_a b` and `m4_a;rm` all reached `docker rm -f`. Reject-first now, and six
cases cover exactly the names the old rule admitted.

⚠ **And the first fix was still wrong**: `*[!a-z0-9_]*` let `m4_UPPER` through — a bracket RANGE is
collation-dependent, so outside the C locale `a-z` can cover uppercase. It built a real container
before the case caught it. The class is enumerated character by character now.

## LOW 1 — the report format applied at one site, not its shell siblings

Fixed in `start-schema-db.sh`. Latent, and the reviewer proved it latent rather than assuming:
`check-plan-code.py:487` runs a mutation target as `[sys.executable, name, "--self-test"]`, so a
shell script cannot be one today. Written in the canonical form anyway — this branch already paid for
that gap once, when eleven kills went unattributed in CI.

## LOW 2 — stale prose beside a correct case

`559 → 566` where the case said 572, after the number moved four times. Rewritten to state the whole
path once, beside the case that proves it.

## Verified after fixing

    self-test                                       49/49
    mutations                                       15/15 attributable, control parses to []
    EXPECTED_MUTATIONS                              572 -> 574
    M4_PHASE=post scripts/check-schema-gates.sh     73 ✓ / 0 ✗, 15/15, exit 0
    start-schema-db.sh --self-test                  23/23
    check-plan-code.py --self-test                  128/128
    seven repo guards                               rc=0

# `schema-gates-in-ci` (PR #297) — round 1, CLAUDE half

**VERDICT: NOT CONVERGED. 2 Blocking, 1 High, 5 Medium, 4 Low.**

**The part the brief asked me to attack hardest is the part that holds.** I built the database from
this branch, ran the fifteen gates against it, and then measured the auth fixture against a bare
container of the same image. Every headline number is right, and the fixture runs in the *safe*
direction: on the bare image `auth.role()` returns NULL for an authenticated caller, so
`if auth.role() <> 'service_role' then raise exception 'workers only'` **does not raise** — the
image is the permissive one, and the fixture is what makes CI behave as production does. Details and
the control are in §1.

**Both Blocking findings are about reach, not correctness.** The gates are right; two of them cannot
be reached by the thing that is supposed to run them.

* **B1** — `prod-drift` **can never pass**, secret or no secret. `--prod` reaches production by
  `docker exec`-ing into a container that job never creates. Measured: `rc=2`,
  `CANNOT RUN — No such container`. It fails loudly, which is correct, but it is structurally red,
  and the job's own comment says leaving it red is "the one option that teaches people to ignore a
  red."
* **B2** — the path filter cannot fire on the change gate 15 exists to detect. Gate 15 walks
  `lib/ app/ worker/ components/ scripts/ types/` + `middleware.ts`; the filter admits
  `scripts/**` and `supabase/**`. Measured: a single line added under `lib/` alone flips the gate
  `0 → 1`, and no other CI step runs it. The workflow header states that under-firing was
  **measured** and that exactly one file lies outside the globs. That measurement missed five of the
  six directories its own gate 15 reads.

**What I ran.** Own containers throughout (`m4_review_bare`, `m4_review_claude`, `m4_review_timing`,
`m4_review_client`), all removed. The developer's stack was never opened — which is also why two
sub-claims below are marked *unverified* rather than confirmed.

| | |
|---|---|
| `scripts/ci/start-schema-db.sh m4_review_claude` | `rc=0`, 27 migrations, M4 PRESENT, **12.9s** (claimed 14s) |
| `PGCONTAINER=… M4_PHASE=post scripts/check-schema-gates.sh` | `rc=0`, **15/15**, **73 ✓ / 0 ✗**, **3m04.97s** (claimed 185s) |
| 17 non-database CI guards from `ci.yml` | all `rc=0` on this branch |

---

## 1. The fixtures — what I could confirm, and what I could not

### 1a. The `auth.uid()` / `auth.role()` replacement is a strict superset-reader. VERIFIED.

`scripts/ci/auth-service-fixture.sql:58-63` makes two claims: that the bodies are verbatim from the
running stack, and that they are "strictly a SUPERSET-READER of the image's version — the legacy GUC
is still the first branch of the coalesce, so nothing that resolved before stops resolving."

I measured the second one. I created the image's own bodies alongside the fixture's in one database
(`img.uid()`, `img.role()`) and evaluated both under each GUC regime:

| GUC set | image | fixture |
|---|---|---|
| **A** legacy singular only (`request.jwt.claim.sub` / `.role`) | `uid=1111…` `role=authenticated` | `uid=1111…` `role=authenticated` — **identical** |
| **B** JSON only (`request.jwt.claims`), which is what `05_assert.sql:784-785` sets | `uid=NULL` `role=NULL` | `uid=2222…` `role=authenticated` |

Case A is the superset claim and it holds exactly. Case B is the defect the fixture exists for.

**And the direction is the safe one, which is the question the brief put first.** The worry was a
double more permissive than production. Measured, the *image* is the permissive one:

```
IMAGE   auth.role()=NULL   (auth.role() <> 'service_role') = NULL   -> the `workers only` IF is NOT taken
FIXTURE auth.role()=authenticated   (auth.role() <> 'service_role') = true
```

`supabase/migrations/0008_jobs_queue.sql:100` and fifteen sibling sites are
`if auth.role() <> 'service_role' then raise exception 'workers only'; end if;`. A NULL predicate
means the `IF` is not taken and the guard **silently does not fire**. Without this fixture CI would
have been running a database in which the service-role fence is inert. The fixture removes that.

Two more properties I checked because a replacement can diverge without changing a body:

* `CREATE OR REPLACE` **preserves owner and ACL**. Measured after the fixture: `auth.uid` and
  `auth.role` are still `owner=supabase_auth_admin` with the image's ACL. No divergence introduced.
* `alter table auth.users add column … is_anonymous boolean not null default false`
  (`auth-service-fixture.sql:32`) lands as `boolean nullable=NO default=false`, which is GoTrue's
  own shape.

### 1b. "1 of 14 columns read by our code" — VERIFIED.

The only `auth.users` columns this repo reads are `new.id` and `new.is_anonymous`, both in
`supabase/migrations/0003_provisioning.sql:6,17`. `auth.users` is otherwise referenced only as an FK
target (`0001_core_schema.sql:3`) and a trigger target (`0003_provisioning.sql:11`). Bare image
column count measured at **21**, matching the header.

### 1c. Unverified, and flagged rather than assumed.

* **"COPIED VERBATIM from the running stack via `pg_get_functiondef`."** I did not re-derive this —
  doing so means querying the developer's stack, which my brief forbids. Nothing in the branch
  records the derivation (no committed dump, no digest), so the falsifier named at
  `auth-service-fixture.sql:65-69` is "re-run this command by hand". The bodies match Supabase's
  published platform definitions and the superset property is measured, so I have no reason to doubt
  it; I am flagging that it rests on the author.
* **"35 columns on the local stack"** — same reason. The 21 is confirmed; the 35 is not.

### 1d. The storage fixture is genuinely not load-bearing today — by a check stronger than the one in the workflow.

`storage-service-fixture.sql:24-29` rests on "no schema gate reads `storage.*`", evidenced by
`m4_catalog.CATALOG_SQL` being public-scoped. I checked the gate the header does **not** mention:
`scripts/check-anon-exposure.py` is `nspname = 'public'` at all four of its catalog queries
(`:455, :462, :497, :511`). So the claim holds across both catalog readers, not just the one named.

The *falsifier* for that claim is a different matter — see §3.

### 1e. `seed-corpus.sql` — sound.

The two-tenant argument at `:25-34` is real: gates 1 and 2 refuse a single-workspace corpus rather
than running vacuously, and the postcondition at `:64-80` asserts what the triggers *did* rather
than what the insert returned. `n_profiles/n_workspaces/n_playlists` and three `%` placeholders line
up. I have no finding here.

---

## 2. ⛔ BLOCKING 1 — `prod-drift` cannot pass. It reaches production through a container the job never creates.

`.github/workflows/schema-gates.yml:183-185` is the whole of the job's real work:

```yaml
      - name: Has production drifted from the manifest?
        env:
          CLAUDE_RO_DATABASE_URL: ${{ secrets.CLAUDE_RO_DATABASE_URL }}
        run: python3 scripts/check-live-schema.py --prod --expect-present
```

The job's steps are: `checkout` → credential check → `setup-python` → that. **There is no
`docker run` anywhere in it.** But `--prod` does not open a socket from Python. It goes through
`scripts/m4_catalog.py:506-508`:

```python
    if url:
        return ["docker", "exec", "-i", "-e", "PGU", container,
                "bash", "-c", 'psql "$PGU" -tAq -v ON_ERROR_STOP=1']
```

`container` defaults to `CONTAINER`, which is
`os.environ.get("PGCONTAINER", "supabase_db_youtube-playlist-summaries-cloud")`
(`scripts/m4_base_db.py:40`). `prod-drift` sets no `PGCONTAINER`. Measured — I resolved the command
the job would build, and then ran the job's command with a credential present and no such container:

```
CONTAINER resolves to: supabase_db_youtube-playlist-summaries-cloud
prod command: ['docker','exec','-i','-e','PGU','supabase_db_youtube-playlist-summaries-cloud',
               'bash','-c','psql "$PGU" -tAq -v ON_ERROR_STOP=1']

$ PGCONTAINER=definitely_no_such_container_for_review CLAUDE_RO_DATABASE_URL=… \
    python3 scripts/check-live-schema.py --prod --expect-present
CANNOT RUN — Error response from daemon: No such container: definitely_no_such_container_for_review
Treat this as NOT RUN.
rc=2
```

(I used a throwaway URL pointing at `127.0.0.1:1`. It never gets that far — the container wall comes
first, which is the point.)

**Why this is Blocking and not Medium.** It fails *loudly*, which is the behaviour this repo wants,
so nothing false is reported. But the job is red on a property that has nothing to do with
production, and it is red **for ever**: adding `CLAUDE_RO_DATABASE_URL` changes nothing, because the
credential check at `:160-176` passes and the very next step dies on Docker. The job has never
executed (`schedule` is skipped on PRs), so its first run will be unattended at 09:00 UTC, and it
will go on failing nightly. The workflow's own comment at `:155-159` names exactly this outcome:
*"Leaving it red and ignored is the one option that teaches people to ignore a red."*

**OBSERVATION THAT WOULD MAKE THIS FAIL (i.e. refute my finding):** a `prod-drift` run that exits 0,
or any non-zero exit whose message is about the manifest rather than about Docker.

**Fix — and I RAN it, partially.** The seam is a `docker exec`, so the cheapest fix is to give the
job a container to exec *into* — it is used purely as a psql client, not as a server:

```yaml
      - name: A psql client for the docker-exec seam (check-live-schema.py has no host:port path)
        run: docker run -d --name m4_prod_client --entrypoint sleep <image> infinity
      - name: Has production drifted from the manifest?
        env:
          CLAUDE_RO_DATABASE_URL: ${{ secrets.CLAUDE_RO_DATABASE_URL }}
          PGCONTAINER: m4_prod_client
        run: python3 scripts/check-live-schema.py --prod --expect-present
```

Measured with `public.ecr.aws/supabase/postgres:17.6.1.147` as the image:

```
CANNOT RUN — psql: error: connection to server at "127.0.0.1", port 1 failed: Connection refused
rc=2
```

The container wall is gone and it now fails at the *connection*, which is as far as I can take it
without the real secret. **What I have NOT proved:** that the run then succeeds against production.
Two things remain open and the author should check both before believing the fix — whether the
runner has egress to the Supabase host, and whether `read_identity`/`load_accepted`
(`check-live-schema.py:884-887`) are satisfied by what production returns. Treat my fix as clearing
one known wall, not as a verified green.

A smaller image than the 0.34 GB Postgres one would do (anything with `bash` and `psql`); I used
that one because it was already local. The alternative — teaching `psql_cmd` a non-docker path — is
a change to a money-adjacent gate with five rounds of review on it, and I would not do that here.

---

## 3. ⛔ BLOCKING 2 — the money gate is inside a path filter that excludes the code it watches.

`.github/workflows/schema-gates.yml:37-46` states, as a measurement:

> ⚠ UNDER-FIRING WAS CHECKED, NOT ASSUMED … MEASURED 2026-09-13: of the files the suite reaches,
> exactly ONE lives outside these globs and is genuinely OPENED rather than merely named in a
> comment — `docs/backlog.md` …

Gate 15 is `scripts/check-paid-caller-arrival.py`. Its subject is declared at `:122-123`:

```python
PRODUCTION_DIRS = ("lib", "app", "worker", "components", "scripts", "types")
PRODUCTION_FILES = ("middleware.ts",)
```

The filter admits `scripts/**`, `supabase/**`, two spec directories and the workflow file. **Five of
those six directories, plus `middleware.ts`, are outside it.** The gate's own commentary
(`check-schema-gates.sh:246`) says what it is for: *"a caller could have landed in `lib/` and every
gate, CI job and hook stayed green."*

Measured, by calling the delivered `report()` on two temp trees differing by one file under `lib/`:

```
CONTROL  (lib/ has no paid caller)        rc = 0     DORMANT — no production caller
MUTATION (one line added under lib/ ONLY) rc = 1     ⛔ BACKLOG 26 HAS FIRED — 1 production caller(s)
                                                       lib/paid.ts:1: await supabase.rpc('record_artifact', …)
```

A PR containing only that file changes no path in the filter, so `schema-gates.yml` never runs. And
nothing else runs the guard — grepped across `.github/`, `package.json` and `scripts/*.sh`, the only
hits are its own usage lines and two comments. `ci.yml` does not run it.

So the branch that finally gave backlog 26's trigger a CI home gave it one that is silent on the
exact event it triggers on. This is the asymmetry the same comment block names two lines earlier:
*"under-including makes the gate SILENTLY NOT RUN on the change that breaks it."*

**Why the measurement missed it.** The check appears to have enumerated *path literals* in the gate
scripts. `PRODUCTION_DIRS` is a tuple of bare directory names walked by `rglob` at `:210` — no path
literal to grep for. The header's own warning (`:44-46`) is that a grep cannot tell an opened path
from a mentioned one; the blind spot here is one level further out — a path that is never spelled.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** show `schema-gates.yml` running on a PR whose only
changed file is under `lib/`, or a second CI caller of `check-paid-caller-arrival.py`.

**Fix, not run** (it needs a GitHub event to test, which I cannot produce): either add the six
production surfaces to both path lists, or — cleaner, because it is the only gate in the suite with
no database dependency — move gate 15 to a step in `ci.yml`, which has no path filter, in the same
way `check-docs.py` already covers gate 6. `check-paid-caller-arrival.py` needs no Postgres by
design (`check-schema-gates.sh:252-253`), so that costs nothing. I lean to the second: the first
widens the filter until the "coarse, biased wide" argument stops meaning anything.

---

## 4. HIGH — the storage-independence falsifier misses the way a gate would actually start reading storage

`schema-gates.yml:105-121` is the executable half of `storage-service-fixture.sql`'s header, and
`:28-29` says so: *"That grep is the falsifier; without it this header is just a sentence that was
true once."* I extracted the step verbatim, ran a control, and mutated a **copy** of `scripts/`
(never the repo — an instrument that edits the tree corrupts its peers).

| # | mutation | expected | measured |
|---|---|---|---|
| M1 | `STORAGE_SQL = "select id from storage.objects"` | caught | ✅ **caught**, rc=1 |
| M2 | `CATALOG_SQL` widened: `nspname = 'public'` → `nspname in ('public','storage')` | caught | ❌ **SURVIVES**, rc=0 |
| M3 | `STORAGE_SQL = """select id from storage.objects"""` (one line) | caught | ❌ **SURVIVES**, rc=0 |
| M4 | a NEW gate script `scripts/check-storage-drift.py` reading `storage.buckets` | caught | ❌ **SURVIVES**, rc=0 |
| M5 | code with a trailing `# comment` | caught | ✅ **caught**, rc=1 |

Control on the unmodified tree: `✅ no gate reads storage.* — the fixture stays scaffolding`, rc=0.

**M2 is the one that matters, because it is the realistic mechanism.** Nobody adds `storage.objects`
to `m4_catalog.py` by writing the words; they widen the namespace scope — and that line contains
`'storage'`, never `storage.`. It is not hypothetical: I ran the widened query against the CI
database and it returns the fixture's fabrications.

```
storage.buckets
storage.objects
```

Those two tables have **4 and 3 columns** (`storage-service-fixture.sql:46-57`) against a real
service schema of ten relations. A digest computed over them is a digest over a test double, green
in CI and meaningless about production — precisely the outcome the header says the grep prevents.

**M3 and M4 are cheaper to explain.** The second filter excludes any line containing `"""`, and
these scripts hold their SQL in triple-quoted strings, so a one-line SQL constant is exempt. And
`FILES` is a hand-maintained list of nine paths; the `[ -r "$f" ]` loop at `:112` catches a file
being **removed** and can never catch one being **added**.

Worth noting what the two extra exclusion patterns currently buy: **nothing**. Measured on this
tree, the corpus yields exactly one raw `storage.` match in total —
`scripts/m4_catalog.py:107: # is the RENDERING, not the storage.` — which the first filter already
removes. Both `"""` and `` storage.objects` policies `` exclude zero lines and are pure attack
surface.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** the step going red on M2, M3 or M4.

**Fix, not run** (I did not want to propose a grep that trades these misses for new ones; the repo
has twice had a reviewer's fix come out weaker than the finding). The shape that survives all five
is to assert the *property* rather than blacklist a token — e.g. a step that asserts every
`nspname` predicate in the catalog readers equals `'public'`, plus deriving `FILES` from what
`check-schema-gates.sh` actually invokes rather than restating it. Both are more than a one-line
edit, which is why I am naming the shape and not pretending to have tested one.

---

## 5. Medium

### M1 — the spine still says the schema gates are not in CI

`docs/dev-process.md:162-164`, in the section immediately after **What is mechanically enforced**:

> **Not yet in CI:** `test:integration` and `test:e2e` (need a live Supabase stack), and the schema
> gates (need a live Postgres — wiring them in belongs to the promotion slice). Run these locally
> before asking for a merge.

Both halves are now false. This branch supplies the live Postgres, and the wiring did not wait for
the promotion slice. There is also no row for `.github/workflows/schema-gates.yml` in the
enforcement table — `ci.yml` has one. Grepped: `schema-gates.yml` appears nowhere under `docs/`
except inside the dashboard entry this branch adds.

A stale line in that specific table is the class this repo files findings about — it makes a reader
believe something is not covered when it is, and it survives because it agrees with itself.

**FAILS IF:** `docs/dev-process.md` names `schema-gates.yml` and no longer lists the schema gates as
not-yet-in-CI.

### M2 — "the single place `PGCONTAINER` is read" is false, in the two comments that assert it

`scripts/m4_catalog.py:82-83` and `scripts/check-anon-exposure.py:85-86`, identically:

> ⛔ ONE DEFINITION, NOT A COPY OF THE EXPRESSION. `m4_base_db.CONTAINER` is the single
> place the container name is resolved (and the single place `PGCONTAINER` is read).

Measured — `PGCONTAINER` is read in **seven** places, and the literal default still appears in six
files:

```
docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:71
docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py:32
scripts/m4_base_db.py:40
scripts/mutate-live-schema-check.sh:63
scripts/check-paid-caller-arrival.py:61
scripts/run-schema-assertions.sh:40
scripts/m4-base-db.sh:56
```

Four of those are shell and genuinely cannot import a Python constant — the honest sentence is "one
definition for the Python gates that reach Postgres through `m4_base_db`". But
**`check-paid-caller-arrival.py:61` is Python**, is a gate in this very suite, and could have taken
the same one-line import. It did not, and the comment asserting single-sourcing is three files away
from the copy it missed. That is `check-vocabulary-collisions.py`'s own thesis applied to the change
that introduced it.

Behaviour is fine today — all seven read the same variable with the same default, and I confirmed
the CI path resolves correctly because `schema-gates.yml:135` sets `PGCONTAINER` for the whole gates
step. This is a claim defect, not a live defect. It is Medium because the claim is what tells the
next person that one edit suffices.

**FAILS IF:** a `grep -rn PGCONTAINER` over `scripts/` returns more than one Python reader while
either comment still says "the single place".

### M3 — the empty-name self-test case is not true of the script

`scripts/ci/start-schema-db.sh:186`:

```bash
  refuses_name "" && r=REFUSE || r=allow
  t "an empty name is REFUSED, never defaulted" REFUSE "$r"
```

But `main()` never sees an empty name, because `:43` is `NAME="${1:-${PGCONTAINER:-m4_schema_gates}}"`
and `:-` treats the empty string as absent. Measured:

```
$1=""  PGCONTAINER unset        -> NAME=m4_schema_gates
$1=""  PGCONTAINER=someones_db  -> NAME=someones_db
```

So `scripts/ci/start-schema-db.sh "$SOME_EMPTY_VAR"` does not refuse; it silently `docker rm -f`s
whatever the default resolves to. On this machine that is `m4_schema_gates`, which is a **live
container right now**.

**Bounded, and I want to be accurate about the bound:** it cannot reach the developer's stack. That
name matches `supabase_*` by every route, including via `PGCONTAINER`, so `refuses_name` catches it.
The destructive reach is limited to the CI-default container. The finding is the falsifiability one:
the guard's single dangerous operation is `docker rm -f`, and the one case written about the empty
name exercises a function-level path `main()` cannot reach — so the case would pass unchanged if
`:43` were deleted.

**FAILS IF:** the self-test asserts on the *resolution*, not on `refuses_name` alone, and still
passes. A one-line fix (`NAME="${1-${PGCONTAINER:-m4_schema_gates}}"`, using `-` not `:-`) plus a
case over a `resolve_name()` helper covers it; I did not run this, because testing it means running
the script's `docker rm -f` path.

### M4 — the blind spot was diagnosed and then used again, in the same commit

`scripts/m4-base-db.sh:8-14` now carries a corrected `# 10 cases` (verified: the suite prints
`10 of 10 self-test cases passed`) **and** the reason it was wrong for so long: nothing observes a
declared count in a shell script. `scripts/check-selftest-counts.py:249` globs
`(root / "scripts").glob("*.py")`, and the drift rule at `scripts/check-plan-code.py:1280` reads a
**docstring**, so neither can ever see a `#`-comment header.

The correction therefore *restores a stored claim to an unobserved location*. `start-schema-db.sh`
handled the same situation correctly — `:10-14` declares no count and derives it at runtime — so the
branch contains both the right answer and the wrong one, three files apart. The dashboard entry is
honest about it ("Instance corrected; the blind spot is not filed"), and that is exactly the state
`dev-process.md` says gets lost: a discovery living only in prose.

I checked whether the guard could simply be widened and it cannot cheaply: `count_drift` takes a
docstring and the audit spawns `python3 <script> --self-test`, so shell support needs a new
extractor, a new invocation, and `POPULATION` entries — and `:263` *fails* a script that declares a
count without being pinned. Non-trivial, which strengthens the case for filing it rather than
absorbing it.

**FAILS IF:** `m4-base-db.sh` declares no count (matching its new sibling), or a backlog row exists
for the blind spot.

### M5 — one concurrency group spans two jobs with different subjects

`schema-gates.yml:74-76`:

```yaml
concurrency:
  group: schema-gates-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Declared at workflow level, so it covers both jobs, and `github.ref` is `refs/heads/master` for a
push to master **and** for the 09:00 cron. Whichever starts second cancels the first: a merge at
08:59 can have its `schema-gates` run cancelled by `prod-drift`, and a merge at 09:01 cancels the
night's drift check. A cancelled run is neither green nor red — it reports nothing, which is the one
outcome this repo treats as worse than a failure.

`ci.yml:21-23` uses the same shape but has no schedule, so it has no cross-subject collision.

**FAILS IF:** the group key includes `github.event_name` (or the jobs get their own
`concurrency:` blocks) — then a cron and a push can no longer displace each other.

---

## 6. Low

**L1 — `auth.email()` is left in the legacy form; the "all three helpers" claim is still instance-shaped.**
`auth-service-fixture.sql:54-56` says the fix was applied to the class, not the instance. Measured on
the bare image, it ships **three** helpers — `email`, `role`, `uid` — and `auth.jwt()` **does not
exist at all**. So the fixture replaces two, creates a third, and leaves `auth.email()` reading only
`request.jwt.claim.email`, which is the same defect. Low because nothing in the repo calls it
(`grep 'auth\.email()'` over `supabase/migrations/` and the spec schema: **0 hits**) and the failure
direction is fail-closed: NULL makes an owner predicate false, producing a denial an assertion would
report, not a silent pass. Also note `:71-73` asserts "The image HAS these functions" as the reason
for `create or replace` — false for `jwt`, which the fixture creates fresh (measured after the
build: `jwt owner=supabase_admin acl=(default)`, i.e. PUBLIC EXECUTE; inert and CI-only, but it is
not the "replace an older body" this line describes).

**L2 — "every one of its six relation queries".** `storage-service-fixture.sql:26` and
`schema-gates.yml:109-110`. Measured: `CATALOG_SQL` carries **nine** `nspname = 'public'` predicates
— `m4_catalog.py:338, 345, 372, 380, 406, 412, 428, 437, 442`. The property is stronger than
claimed, which is the harmless direction, but the number is a stored count in two places and wrong
in both.

**L3 — "14s" excludes the image pull.** I measured 12.9s, so the figure is right — with the image
already local. On a cold runner the 0.34 GB pull is additional, and the 3.3-minute total is the
number carrying the "max(verify, schema), not the sum" argument at `:9-11`. Not a defect; worth a
half-sentence in the header so the first slow CI run is not read as a regression.

**L4 — no `permissions:` block.** `permissions` is undefined for this workflow (verified by parsing),
so it inherits the repository default while running `npm ci`, which executes lifecycle scripts.
`ci.yml` has the same gap, so this is pre-existing rather than introduced — `permissions: contents: read`
on both would be consistent hardening. **No injection surface found**: the only `${{ }}` reaching a
`run:` context are `secrets.CLAUDE_RO_DATABASE_URL` passed through `env:` (`:162-163`, `:181-182`),
and no `github.event.*` field is interpolated anywhere.

---

## 7. What I checked and found sound

Stated positively, because most of this branch is right and a review that only lists findings
misrepresents it.

* **The container seam is clean.** No import cycle (`m4_base_db` imports nothing from `m4_catalog`);
  no `CONTAINER` use at import time; `verify-exclusion-reasons.py:66` and `gen-m4-manifest.py:63`
  still get what they expect through the re-export. The three deleted constants were genuinely
  unread — `grep CONTAINER` over `check-guard-coverage.py`, `check-sentinel-meanings.py` and
  `check-vocabulary-collisions.py` now returns nothing. No mutation anchor in `scripts/mutations/*.json`
  binds the deleted literal, so nothing was orphaned. And the environment does **not** leak into a
  self-test: all four suites print identical results with `PGCONTAINER` unset and set
  (`16/16`, `10/10`, `14/14`, `74/74` both ways).
* **The name guard on `start-schema-db.sh` cannot be defeated by any plausible name.** `supabase_*`,
  `*_supabase*`, `postgres` and the CI defaults all behave as the 7 cases say. (The one gap is M3
  above, which is about the empty string, not about the pattern.) The only residual is that
  `docker rm -f` also accepts a container **ID**, which `refuses_name` cannot recognise — I am not
  filing that, because passing a hex ID is not a mistake anyone makes by accident.
* **The readiness logic is right and the `pg_isready` reasoning is sound.** Two conditions in order —
  log marker, then a query that answers (`:100-126`) — and the loop captures before matching
  (`:103-104`) rather than piping into `grep -q`, which is the documented SIGPIPE-under-`pipefail`
  footgun. The result is remembered in `seen`/`elapsed` rather than re-derived. I did not reproduce
  the temporary-init-server race; I have no reason to doubt it and the fix is correct regardless of
  the exact mechanism. I found no third state and no path where `main` returns 0 over a wrong
  database: `:156-165` asserts the two M4 relations exist rather than trusting the migration exit
  codes.
* **The two path lists are byte-identical** — verified by parsing the YAML and comparing the
  extracted lists, not by reading them. The anchors claim is right: GitHub Actions does not expand
  YAML anchors in workflow files, and `js-yaml` *does*, which is the author's point exactly.
* **`npm ci` is genuinely a gate dependency**, not a convenience: gate 15 shells out to
  `scripts/ts-comment-spans.mjs` (`check-paid-caller-arrival.py:144`) and has no fallback by design.
* **The gates themselves pass over the CI-built database.** 15/15, 73 ✓ / 0 ✗, `rc=0`, including
  gate 12's 29 live mutations and gate 8's behavioural assertions — i.e. the fixtures are sufficient
  for the half of the suite that actually executes SQL, which is the strongest single piece of
  evidence that they are not merely shaped right.
* **Nothing existing broke.** All seventeen database-free guards from `ci.yml` are green on this
  branch, including `check-selftest-counts.py`, `check-ratchet-contract.py`, `check-docs.py` and
  `check-producer-enumeration.py`.

---

## 8. Summary

| Grade | Finding |
|---|---|
| **Blocking** | `prod-drift` reaches production via `docker exec` into a container it never creates — measured `rc=2`, permanently red |
| **Blocking** | gate 15's subject (`lib/ app/ worker/ components/ types/`, `middleware.ts`) lies outside the path filter; measured `0 → 1` on a `lib/`-only change, and no other CI caller |
| **High** | the storage falsifier survives 3 of 5 mutations, including the realistic one (widening `nspname`) |
| Medium | `dev-process.md:162-164` still says the schema gates are not in CI |
| Medium | "the single place `PGCONTAINER` is read" — measured false; 7 readers, one of them a Python gate |
| Medium | `start-schema-db.sh`'s empty-name case tests a path `main()` cannot reach; the script defaults instead of refusing |
| Medium | `m4-base-db.sh`'s corrected count went back into the location just proven unobservable; not filed |
| Medium | one concurrency group spans the cron and the push on `refs/heads/master`; either can cancel the other |
| Low | `auth.email()` left legacy; "the image HAS these functions" false for `auth.jwt()` |
| Low | "six relation queries" — measured nine |
| Low | "14s" excludes the image pull |
| Low | no `permissions:` block (pre-existing; no injection surface found) |

**Recommendation: do not merge on this round.** B1 and B2 both leave a gate that reports success
while not running — the failure this branch exists to end. Neither needs a redesign: B1 is a
container plus an env var (one wall cleared by measurement, the rest unverified), and B2 is one step
moved into `ci.yml`. The High is the only finding whose fix I would want measured before I believed
it, and I deliberately did not write that fix.

**Containers used and removed:** `m4_review_bare`, `m4_review_claude`, `m4_review_timing`,
`m4_review_client`. `supabase_db_youtube-playlist-summaries-cloud` was never opened; the branch was
never changed.

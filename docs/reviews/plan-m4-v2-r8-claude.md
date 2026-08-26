# M4 v2 — ROUND 8, CLAUDE HALF. Adversarial review of fork (a).

**Subject:** branch `docs/m4-round7`, committed head `563333d`, base `74f450b`.
**Method:** executed. Every finding below was constructed in a throwaway database and both gates run
against it. Scratch databases were prefixed `r8_claude_`; **all were dropped**, verified at the end
of this document.

> ⚠ **THE SUBJECT MOVED WHILE I WAS REVIEWING IT, AND I AM SAYING SO RATHER THAN QUIETLY REPORTING
> AGAINST WHICHEVER TREE I HAPPENED TO READ.** Partway through, `git status` showed three tracked
> files modified but uncommitted — `docs/adr/0012-*.md`, `schema/05_assert.sql`,
> `scripts/mutate-live-schema-check.sh` — plus an untracked `docs/reviews/plan-m4-v2-r8-codex.md`.
> The Codex half had landed and its findings were being folded in. By the time I finished writing,
> that work was committed as **`522e766` — "round 8 codex — three findings, and the first is a false
> green I shipped today"**.
>
> So every finding below states **which tree it was measured against**: `563333d` is the head I was
> asked to review, `522e766` is the head as of filing. Two of my findings were fixed by `522e766`
> before I filed them; I have kept them, marked ✅ ALREADY FIXED, because the *reasoning* is what
> round 9 needs and because each leaves a residue that `522e766` does not close. The three findings
> that survive `522e766` untouched are **B1, H1 and H2**.

---

## Verdict

**NOT CONVERGED.** 1 Blocking · 2 High · 4 Medium · 3 Low.

The headline: **claim 1 is false, and it is false in the direction nobody looked.** Coverage did not
only move — a whole *polarity* was dropped. `check-anon-exposure.py` RULE 3 asks "does a session role
hold **too much**?" The digest it replaced asked "is the effective access **exactly this**?" Those are
not the same question, and the second half — *too little* — is now asserted by nothing at all. The
maximal case is measured below: **every session-role SELECT grant in the M4 spec can be revoked and
all three instruments stay green.**

---

## 🔴 B1 — The entire session-role READ surface can be revoked and NOTHING notices. The old digest caught it.

**Premise attacked** (`scripts/m4_catalog.py:157-167`, committed):

> "So `public`, `anon` and `authenticated` RELATION access is no longer digested. It moved to
> `check-anon-exposure.py` RULE 3 … **WHAT MOVED, AND WHAT NOW CATCHES IT** (each row is a mutation
> in the harness): `grant insert/update/delete …` `grant insert (blob_key) …` `grant truncate …`"

All three rows in that table are **grants**. There is no row for a **revoke**, and the fingerprint
that was removed carried both directions:

```python
# 74f450b:scripts/m4_catalog.py:153
REL_GRANTEES = ("public", "anon", "authenticated", "service_role")
REL_PRIVS    = ("SELECT", "INSERT", "UPDATE", "DELETE")
```

`SELECT` is in `REL_PRIVS`, so `has_table_privilege('authenticated', rel, 'SELECT')` going
`true → false` changed the digest. At HEAD, `REL_GRANTEES = ()` (`scripts/m4_catalog.py:205`) and
RULE 3 only ever reports `held & FORBIDDEN_ON_M4` where
`FORBIDDEN_ON_M4 = ("INSERT","UPDATE","DELETE","TRUNCATE")` (`check-anon-exposure.py:121`,
`:249-256`). **SELECT is not in that set and cannot be.** A revoke is invisible by construction.

### The spec issues seven session-role SELECT grants

```
01_workspaces.sql:30   grant select on workspaces                              to authenticated, anon;
03_generations.sql:77  grant select on workspace_videos                        to authenticated, anon;
03_generations.sql:564 grant select on video_generations                       to authenticated, anon;
04_artifacts.sql:259   grant select on video_artifact_sources                  to authenticated, anon;
04_artifacts.sql:672   grant select on video_artifacts                         to authenticated, anon;
04_artifacts.sql:799   grant select on video_summary_current, video_artifacts_current
                                                                               to authenticated, anon;
```

Seven of M4's eight relations. Every one was digested at `74f450b`. None is asserted anywhere now.

### Executed evidence

Scratch M4 database built exactly as `mutate-live-schema-check.sh` builds its template
(`pg_dump --schema-only --no-owner --no-privileges` of the container's `postgres`, then
`scripts/build-m4-schema.py`). Control first:

```
live schema [local container db 'r8_claude_tpl' … read_only=on]: M4 is PRESENT as expected
  — checked all 161 objects, BY DEFINITION not just by name
```

Then one clone per mutation. `BASE-digest` = `check-live-schema.py` from a `git archive 74f450b`
checkout; `HEAD-digest` = the committed HEAD gate; `RULE3` = whether the run *names* an M4 problem
(`M4 NOT READ-ONLY` / `M4 OUT OF REACH` / `M4 FN EXECUTABLE` / `ROLE NOT PRESENT`).

```
name                        (old gate)        (new digest)      (new home)
  revsel_auth_v             BASE-digest=FAIL  HEAD-digest=PASS  HEAD-RULE3=silent
  revsel_anon_t             BASE-digest=FAIL  HEAD-digest=PASS  HEAD-RULE3=silent
  revsel_svc_t              BASE-digest=FAIL  HEAD-digest=PASS  HEAD-RULE3=silent
  revall_svc_src            BASE-digest=FAIL  HEAD-digest=PASS  HEAD-RULE3=silent
  revall_svc_col            BASE-digest=FAIL  HEAD-digest=PASS  HEAD-RULE3=silent
  revins_svc_gen            BASE-digest=FAIL  HEAD-digest=PASS  HEAD-RULE3=silent
```

`revsel_auth_v` is `revoke select on video_artifacts_current from authenticated` — the view the serve
path reads.

Re-measured against **`522e766`** (which carries the r8-codex H4 service_role block), with the
assertion suite added as a third instrument, and pushed to the maximal case:

```
  tpl              digest=PASS RULE3=silent assertions=0     <- control
  auth_view        digest=PASS RULE3=silent assertions=0
  auth_sum         digest=PASS RULE3=silent assertions=0
  auth_ws          digest=PASS RULE3=silent assertions=0
  auth_all         digest=PASS RULE3=silent assertions=0
```

where `auth_all` is:

```sql
revoke select on video_artifacts, video_generations, workspace_videos, workspaces,
                 video_artifact_sources, video_artifacts_current, video_summary_current
  from anon, authenticated;
```

**Every session-role read privilege in M4, revoked at once, and all three instruments report green.**

### Consequence in observable units

The plan's Step 7 / Task 9 runs `check-live-schema.py --prod --expect-present` immediately after an
irreversible `supabase db push --linked`. That gate is the thing standing between a bad cutover and
production. After fork (a) it will print *"M4 is PRESENT as expected — checked all 161 objects"* over
a database on which no logged-in user can read a single M4 row. The frontend's manifest read, the
serve path, the sidebar: all 404/empty, gate green.

**And ADR-0012 makes this state MORE likely, not less.** Its rule is *revoke from all four principals,
then grant back*. Before it, a forgotten grant-back on production was masked by the platform's default
ACL — the read still worked. After it, the grant-back line is the only thing between the schema and a
total read outage. Fork (a) removed the only detector of that failure in the same week ADR-0012 made
it reachable.

This is the **same shape as r7 B1** — *"revoking `record_artifact` EXECUTE from `service_role` is a
production write outage and `--expect-present` exited 0"* — which this branch filed as **Blocking**.
Same class, session-role read side, seven grants instead of one.

### Direction

RULE 3 needs the other polarity, and it should be **derived, not typed** — the same argument
`m4_relations()` already makes for the relation list. The spec's own `grant select … to
authenticated, anon` lines are the source of truth; a rule of the form *"every M4 relation the spec
grants SELECT on must still be SELECTable by `anon` and `authenticated`, and the list of such
relations is parsed from the spec"* is falsifiable, environment-invariant (it is a positive grant the
spec controls, not a platform default), and closes all seven at once. The alternative — a capability
assertion in `05_assert.sql` reading each relation as `authenticated` — is weaker here, because gate
8/11 does not run in `M4_PHASE=pre` and never runs against production at all (see M4).

---

## 🟠 H1 — RULE 3 cannot see a SELECT grant on the out-of-reach relation, and its self-test says it can

**Premise attacked** (`scripts/check-anon-exposure.py:49-53`):

> "No `public`, `anon` or `authenticated` may hold INSERT, UPDATE, DELETE or TRUNCATE on any relation
> in the M4 manifest, at TABLE or COLUMN level; **and none may hold anything at all on the one
> relation the spec puts entirely out of reach.**"

And the rule that implements it (`:243-248`):

```python
if rel in no_access:
    if held:
        problems.append(f"M4 OUT OF REACH    `{role}` holds …")
```

The rule is right. **The fetch cannot feed it.** `held` is assembled from exactly two probes
(`:318-323`): `unnest(FORBIDDEN_ON_M4)` at table level — `INSERT, UPDATE, DELETE, TRUNCATE` — and
`unnest(COLUMN_LEVEL)` at column level — `INSERT, UPDATE, REFERENCES` (`:121`, `:123`). **`SELECT`
appears in neither list.** For `video_generations_collectable`, `held` is empty for a SELECT grant,
`if held:` is false, and the rule is silent.

### Executed evidence

```
--- oor_select ---      (grant select on video_generations_collectable to anon;)
anon SELECT on collectable = true
   -> SILENT
--- oor_colselect ---   (grant select (generation_id) on video_generations_collectable to anon;)
   -> SILENT
--- oor_insert ---      (grant insert on video_generations_collectable to anon;)
M4 OUT OF REACH    `anon` holds INSERT on `video_generations_collectable`, which
   -> OUT OF REACH RAISED
```

The old digest caught it, on the same database:

```
$ (cd <74f450b checkout> && python3 ./scripts/check-live-schema.py --database r8_claude_oor_select --expect-present)
⛔ AND 1 object(s) EXIST BUT DO NOT MATCH THEIR DEFINITION —
```

HEAD digest: `PASS`. Assertion suite: `exit 0`.

### And the self-test asserts the opposite, in green

```python
# scripts/check-anon-exposure.py:593-596
case("RULE 3: the out-of-reach relation FAILS on a mere SELECT",
     any("M4 OUT OF REACH" in p for p in
         evaluate_m4([("video_generations_collectable", "anon", "SELECT,")],
                     ("video_generations_collectable",), ())))
```

```
$ python3 ./scripts/check-anon-exposure.py --self-test | grep out-of-reach
  ✓ RULE 3: the out-of-reach relation FAILS on a mere SELECT
…
46/46 passed
```

The fixture string `"SELECT,"` is one the fetch can never emit. This is **`pg_bool`'s own lesson,
repeated in the same file eleven days later**: that docstring (`:348-360`) says *"THE RULE WAS RIGHT
AND THE FETCH WAS BROKEN, and a rule/fetch split is structurally blind to that"*, and the fix it
prescribes — put the parse under test — was applied to `pg_bool` and not to the **privilege list**,
which is the other thing the fetch decides on the rule's behalf.

### Consequence

Bounded but real: the view is `security_invoker=true` (measured: `reloptions={security_invoker=true}`),
so RLS still filters rows for `anon`. What is *not* bounded is the claim. A check that declares "any
session-role privilege here is a defect", ships a self-test proving it, and does not fire, is worse
than a written gap — nobody re-examines it.

### Direction

Two lines. Add `SELECT` to the table-level probe list used for the out-of-reach branch (a separate
tuple from `FORBIDDEN_ON_M4`, since SELECT is legitimate on the other seven relations), and add
`SELECT` to `COLUMN_LEVEL`. Then add the case the self-test is missing: **a self-test case whose
input comes from `parse_rows` over a captured real fetch**, not from a hand-typed privilege string —
otherwise the next list divergence is invisible the same way.

---

## 🟠 H2 — Eleven of the spec's twenty-one grant sites are now asserted by nothing. Claim 2 is partly false.

**Premise attacked** (`scripts/m4_catalog.py:196-199` and ADR-0013): the `service_role` capability
assertions are *"strictly stronger than digesting the grant"*.

They are strictly stronger **about the two capabilities they exercise**. The brief asks what
`service_role` can legitimately DO that neither assertion covers. Measured against **`522e766`**, including the r8-codex H4 block (GC update, collectable read, sources read):

```
  ws_insert     digest=PASS RULE3=silent assertions=0    grant 01_workspaces.sql:29
  ws_update     digest=PASS RULE3=silent assertions=0
  wv_insert     digest=PASS RULE3=silent assertions=0    grant 03_generations.sql:69
  wv_update     digest=PASS RULE3=silent assertions=0
  wv_delete     digest=PASS RULE3=silent assertions=0
  va_delete     digest=PASS RULE3=silent assertions=0    grant 04_artifacts.sql:671
  va_update     digest=PASS RULE3=silent assertions=0
  vg_insert     digest=PASS RULE3=silent assertions=0    grant 03_generations.sql:563
  vg_delete     digest=PASS RULE3=silent assertions=0
  vas_insert    digest=PASS RULE3=silent assertions=0    grant 04_artifacts.sql:258
  vas_delete    digest=PASS RULE3=silent assertions=0
```

Eleven grants, all of which the old digest carried (`REL_PRIVS` covers I/U/D). Two of them are named
in the brief's own list of candidates and are the ones I would act on:

- **`va_update` — the `detached` transition.** §6.1 owes a detached dig *"a route back"*, and the
  assertion file spends ~40 lines proving `recorded → detached → recorded` works
  (`05_assert.sql:486-493`, `:604-623`) — **as `postgres`, never as `service_role`.** Revoke UPDATE on
  `video_artifacts` from `service_role` and every detach and every re-attach fails at runtime with
  three green gates. This is r7 B1's shape a third time.
- **`va_delete` — GC.** Same argument, free renders.

The remaining nine are less clearly load-bearing (the RPC is `SECURITY DEFINER`, so the paid write
path survives all of them), and I am not claiming each is an outage. What I am claiming is the thing
ADR-0013 asserts and this measurement refutes: **"a privilege is not a capability" cuts both ways.**
Step 5 deleted the digest of 21 grant sites and replaced it with assertions covering ten. The gap is
not the difference between "granted" and "works" — it is eleven grants where *neither* is checked.

### Direction

Do not re-widen the digest. Extend the existing `SERVICE-ROLE CAPABILITY` block with the two
capabilities that are named in the spec's own prose — the `detached` transition and the GC delete —
executed `set local role service_role`, exactly as the r8-codex block does for the sweeper. Then write
down, in that block, the grants deliberately left unasserted and why, so the next round does not
re-derive this table. An unexplained omission is how r5 B2 happened; `m4_catalog.py:70` says so.

---

## 🟡 M1 — ✅ ALREADY FIXED — the four "coverage moved" mutations were satisfied by the control

**Measured against the committed head `563333d`**, where:

```bash
# 563333d:scripts/mutate-live-schema-check.sh:48
anon_gate() { python3 ./scripts/check-anon-exposure.py --local --database "$1" >/dev/null 2>&1; }
```

Exit code only. And `check-anon-exposure.py` **exits 1 on every database that harness can build**,
for reasons that have nothing to do with RULE 3 — because the template is built with
`pg_dump --no-privileges`, which strips exactly the ACLs RULE 1 and RULE 2 measure:

```
$ python3 ./scripts/check-anon-exposure.py --local --database r8_claude_ctl2      # UNMUTATED clone
FAILED — 3 problem(s):
UNLISTED           `exec_sql` is SECURITY DEFINER and anon-EXECUTable …
UNLISTED           `record_correction_spend` is SECURITY DEFINER and anon-EXECUTable …
LOWER THE BASELINE 0 money tables are TRUNCATE-able, baseline says 5 …
EXIT=1

$ python3 ./scripts/check-anon-exposure.py --local --database r8_claude_tpl >/dev/null 2>&1
  anon_gate(r8_claude_tpl) exit=1  -> harness would report 'RULE 3 FAILS' = CAUGHT
```

So mutations 10, 17, 22 and 23 — *the entire executed argument that coverage MOVED rather than
vanished* — each reported ✓ on a predicate that is true of a database where the mutation was never
applied. Round 5 H1's masking rule, in the harness written to prove the move.

**`522e766` fixes this correctly**: `anon_gate` now takes the problem TOKEN it expects, and two
per-mutation controls were added. Confirmed by running it:

```
  ✓ CONTROL: an unmutated M4 reports no M4-NOT-READ-ONLY problem
  ✓ insert/update/delete to anon -> RULE 3 names M4 NOT READ-ONLY
  ✓ CONTROL: an unmutated M4 does not report slot_kind as session-executable
  ✓ anon EXECUTE on an M4 function -> RULE 3 names M4 FN EXECUTABLE
✅ every mutation caught — check-live-schema.py is load-bearing
```

**Filed anyway, for the residue: only two of the four moved mutations got a control** (10 and 23). 17 and
22 still assert a token with no control proving that token was absent first, and 22's token is the
bare string `TRUNCATE`, which appears in RULE 3's *boilerplate message text* for every
`M4 NOT READ-ONLY` problem — so mutation 22 would pass on a database whose only defect was an
unrelated `grant insert`. Give 17 and 22 controls, and give 22 a token that is not a substring of the
generic message.

---

## 🟡 M2 — ✅ ALREADY FIXED — ADR-0012 named a falsifier that cannot fire; reproduced independently

**Committed `docs/adr/0012-revoke-before-grant-is-schema-wide.md:78-81`:**

> "**It does not need a gate, because it has one already.** The environments agreeing is what
> `mutate-live-schema-check.sh` mutation 19 asserts … A regressed revoke breaks that agreement and the
> mutation goes red."

I constructed the exact regression the ADR describes — `slot_kind`'s revoke naming three roles
instead of four — on a production-shaped database (`pg_dump --no-owner` **with** privileges, plus
`alter default privileges … grant all/execute to anon, authenticated, service_role`; 3 `pg_default_acl`
rows installed, verified):

```
=== service_role EXECUTE on slot_kind ===
  prodshape_ok           false
  prodshape_regressed    true          <- the regression landed; r7 H2's direct door is open

=== mutation 19's own assertion: gate --expect-present must PASS ===
  prodshape_ok           gate=PASS
  prodshape_regressed    gate=PASS     <- the named falsifier is silent
```

Mutation 19 runs only `check-live-schema.py`, and after step 5 that gate carries no privileges at all
(`REL_GRANTEES = ()`, `FN_GRANTEES = ()`, `m4_catalog.py:205-206`). It became structurally incapable
of failing for a privilege reason **in the same commit series that cited it as the mechanism**.

The instrument that *does* fire is the assertion suite:

```
$ PGDATABASE=r8_claude_prodshape_regressed ./scripts/run-schema-assertions.sh
ERROR:  ASSERTION FAILED — service_role wrote video_artifacts DIRECTLY. record_artifact is not the
        only door, so every guard that function performs can be walked past
  assertions exit=1        (prodshape_ok: exit=0)
```

`522e766` already corrects the ADR (r8 codex H3, same conclusion). **One residue in the
correction:** its new table says the RULE 3 row is verified by "mutations 10, 17, 22, 23 — each with a
control", and only 10 and 23 have one (M1 above). And the correction does not say the thing this
measurement makes obvious: **no gate ever runs the assertion suite against a production-shaped
database**, so the falsifier it now names correctly is one nothing invokes in the environment where
the regression is visible. `run-schema-assertions.sh` defaults to `PGDATABASE=postgres`, the bare
container. That should be stated in the ADR, or a prod-shaped run should be added as mutation 24.

---

## 🟡 M3 — the out-of-reach list is a hand-list, in the file that argues hand-lists go stale silently

`scripts/check-anon-exposure.py:136-143` makes the argument explicitly:

> "**DERIVED, never typed**: … A hand-list would keep passing over the new relation, which is the
> failure this project has a name for — a vocabulary that silently stops matching is worse than no
> check."

and then, twelve lines up in `m4_catalog.py:213`:

```python
M4_NO_SESSION_ACCESS = ("video_generations_collectable",)
```

Nothing derives it, nothing reconciles it against the spec, and no self-test compares it to anything.
The derivation is available and I checked that it reproduces the current value: of the eight manifest
relations, exactly one has no `grant select … to authenticated, anon` line in
`schema/0[134]*.sql` — `video_generations_collectable` (`04_artifacts.sql:944` grants it to
`service_role` alone). So the same parse that B1 needs also *derives* this exception, and the two
fixes are one fix.

Instance-not-class: the derivation argument was applied to the list and not to the exception beside
it, and the exception is the branch with the stronger claim (`any privilege is a defect`).

---

## 🟡 M4 — claim 5's answer: **nothing**. Today, on the real local database, RULE 3 cannot fail, and gate 8 does not run.

Claim 5 asks what observation would make RULE 3 FAIL today. Measured, as `check-schema-gates.sh`
invokes it (`--local`, no `--database`, so the container's `postgres`):

```
subject: LOCAL container supabase_db_youtube-playlist-summaries-cloud db 'postgres'
         M4 relations present: 0/8  — RULE 3 has nothing to check here (pre-0027)  [0 pairs read]
Anon exposure OK — … no session role can write to any of the 0 M4 relation(s) present.
EXIT=0
```

And gate 8, the other home coverage moved to:

```
═══ 8/11 schema ASSERTIONS — SKIPPED, M4_PHASE=pre ═══
```

So **both destinations of fork (a) are non-executing in the phase the project is actually in.** The
banner is honest — it prints `0/8` and says so, which is the right shape and I am not filing it as an
unfalsifiable guard. What I am filing is the composition: the argument for fork (a) was *"the
fingerprint was being widened to relearn what the assertion already knew"*, and the assertion still
does not run, and the new home has nothing to check. The **only** thing proving either bites is
`mutate-live-schema-check.sh` — and M1 shows that proof was unearned at the committed head.

Full suite state, run to confirm nothing else regressed: gates 1, 2, 5, 6, 7, 9, 10, 11 green; 3 and 4
red **by plan** (plan Task 5), 8 skipped. `mutate-schema.py`: `63/63`. `mutate-live-schema-check.sh`:
all 23 caught (`522e766`). `check-anon-exposure --self-test`: 46/46.
`check-catalog-coverage --self-test`: 11/11.

---

## ⚪ L1 — the function half of RULE 3 has no fail-closed missing-role check

`evaluate_m4` gained one and explains why (`:258-269`): *"'anon holds nothing here' and 'anon is not a
thing here' produce the same empty result, and only one of them is a passing state."*
`evaluate_m4_functions` (`:273-286`) has no equivalent. It is mostly covered by the relation half —
but that check is gated on `if seen_rels:`, so on a database with M4 **functions** and no **relations**
(mutation 15's drifted-signature survivor is exactly that shape) a missing session role is silent in
both halves. Same argument, one branch over.

## ⚪ L2 — `COLUMN_LEVEL` probes `REFERENCES`, which no rule consults on the normal path

`COLUMN_LEVEL = ("INSERT", "UPDATE", "REFERENCES")` (`:123`). On the seven ordinary relations,
`held & FORBIDDEN_ON_M4` discards `REFERENCES`, so the term is measured and thrown away. It is only
load-bearing on the out-of-reach branch — which H1 shows is the branch that cannot see SELECT. Worth
one comment saying which branch each list serves; right now the two lists read as one policy.

## ⚪ L3 — role-scoped mutations are CLUSTER-WIDE, and the harness header says the shared stack is never touched

`mutate-live-schema-check.sh:9-14`:

> "This builds the state FOR REAL in throwaway databases and drops them afterwards. **The shared stack
> is never touched**."

True of every mutation currently in the file, because all of them are object-level grants, which are
per-database. It is **not** true of the class. I proved it the expensive way: my own
`grant service_role to anon` probe changed `pg_auth_members`, which is cluster-wide, and it silently
altered `has_table_privilege('anon', …)` in the container's shared `postgres` database as well as in
my scratch clones — which is also why one of my early result tables was garbage. I revoked it
immediately and verified (`anon` memberships: `<none>`). Worth one line in that header, because the
next reviewer who reaches for the membership case — the brief itself lists it as a candidate — will
reach for it in a harness that promises isolation it does not have for that mutation.

---

## What I checked and did NOT find

| Checked | Executed | Result |
|---|---|---|
| **Claim 3** — does the new probe's `auth.users` row perturb later assertions? | ran the full `verify-schema.sh` concatenation with a `t_writes` dump appended before the rollback | **No.** Probe creates 1 `auth.users` + 1 `workspaces` row; every later count assertion is scoped to `vidA`/`vidG`/`vidT4`/`vidR9c`/`ingestNew`. Gate 1 green |
| **Claim 3** — does it perturb the population-coverage ratchet? | same run, group counts dumped | **No.** The probe's write lands in `summary\|paid=true\|slot=summary`, which already had **n=18**; every kind still has a group with n>1. It cannot become a sole satisfier |
| **Claim 3** — does it perturb `mutate-schema.py`? | ran it | **No.** `63/63 mutations behaved as expected` |
| **Claim 3** — fixture ordering vs `t_ws`/`t_w2` | read `05_assert.sql:117-118` vs `:832` | **Safe.** The temp tables are materialised at line 117, the probe workspace is created at 832 |
| **Claim 2** — does the capability block catch r7 B1's own case? | `revoke all on function record_artifact(…) from service_role` | **Yes.** `assertions exit=1`, *"service_role CANNOT call record_artifact … production write outage"* |
| **Claim 2** — does the negative half catch the direct door? | `grant execute on function slot_kind(text) to service_role` | **Yes.** `assertions exit=1`, *"record_artifact is not the only door"* |
| **Claim 4** — can `ROLE NOT PRESENT` fire for a wrong reason? | read `:258-269` against the SQL's `where p = 'public' or to_regrole(p) is not null` | **No.** The cross join guarantees a row per existing role once any relation exists; `public` is always emitted |
| **Claim 4** — does `pg_bool` still fail closed? | `--self-test` | **Yes.** Raises on `"yes"` and `""` |
| `WITH GRANT OPTION` to `anon` | `grant select on video_artifacts to anon with grant option` | **Not a regression.** `BASE-digest=PASS`, HEAD `PASS`, RULE 3 silent — the old digest was equally blind (`has_table_privilege` ignores the grant option). Real but pre-existing; not fork (a)'s doing |
| Role **membership** as an escalation route | `grant service_role to anon` | **Not a regression.** Both old and new use `has_table_privilege`, which is membership-transitive, so RULE 3 *does* see an inherited write. ⚠ but see L3 |
| An M4 object created **after** the manifest | reasoned + gate 9 | **Covered by a different gate.** `gen-m4-manifest.py --check` (gate 9/11) is green and would go red; both the digest and RULE 3 derive from the same manifest, so neither is *more* blind than the other |
| A relation not in the manifest (`videos`, `playlists`, `jobs`) | read the manifest — 5 tables, 3 views, all M4-created | **Not a regression.** Those tables were never in the manifest, so the old digest never carried their ACLs either (`m4_catalog.py:332-338` documents why) |
| Does app code consume the M4 views today? | `grep` over `lib app components worker` | **No consumers yet.** M4 is unshipped — which is why B1 is filed on the *cutover gate*, not as a live outage |
| Do the ADR-0012 revokes actually name four roles? | `grep -h "^revoke" schema/0[134]*.sql \| grep -v service_role` | **Yes, all 21.** The one apparent miss is `record_artifact`'s two-line statement, whose continuation names all four (`04_artifacts.sql:643-645`) |

---

## What I would have had to see to report CONVERGED

A run in which the `auth_all` mutation — every session-role SELECT grant in M4 revoked at once — made
at least one of the three instruments go red and **name the cause**, plus a mutation-harness row with
a control proving that same instrument was silent on an unmutated clone. I got green from all three.

## Cleanup

Every scratch database I created was prefixed `r8_claude_` and **all were dropped**:

```
remaining r8_claude databases:  <none>
all databases:                  _supabase, postgres, storage_vectors, template0, template1
anon role memberships:          <none>          (the L3 leak, revoked and verified)
shared postgres db public tables: 13            (pre-M4, as expected — never touched)
```

No tracked file was modified by this review other than this document.

# M4 v2 — ROUND 9, CLAUDE half

Subject: working tree at `10d7c54` (the two r9-codex fixes were committed by the coordinator while
this review ran; the diff I attacked is byte-identical to that commit). Diff base for round 8:
`563333d`.

**I did NOT read `docs/reviews/plan-m4-v2-r9-codex.md`, at any point.** Everything below is from
reading the branch and executing against a live Postgres. Where a finding touches one of the two r9
codex fixes I re-measured the fix myself rather than trusting the commit message.

Every database I created was prefixed `r9_claude_` and every one is dropped
(`select datname from pg_database where datname like 'r9%'` → `<none>`). The shared `postgres`
database was read (`pg_dump --schema-only`) and never written. No tracked file was modified except
this review.

**Verdict: NOT CONVERGED — 1 Blocking, 2 High, 4 Medium, 3 Low.**

---

## 🔴 B1 — the read polarity is satisfied by a SINGLE COLUMN, so r8 B1's outage is still invisible

**Premise, quoted** — `scripts/check-anon-exposure.py:347-391`:

> `evaluate_m4_reads` … *"The OTHER POLARITY: a session role must still be able to READ."* … *"That is
> a total read outage — no logged-in user can read one M4 row — certified as 'M4 is PRESENT as
> expected' by the gate that guards an irreversible cutover."*

and the fetch it is built on, `check-anon-exposure.py:443-463`:

> *"TWO privilege functions, because a grant can hide at either level."*

The fetch UNIONs `has_table_privilege` with `has_any_column_privilege` into one comma-joined string,
and `evaluate_m4_reads:384` asks only `if "SELECT" not in held`. That union is the correct shape for
the **additive** question — *was a privilege added at either level* (r6 B2) — and the wrong shape for
the **subtractive** one. One surviving column keeps `SELECT` in `held`, and the rule falls silent.

**Executed.** r8 B1's own mutation 24, with the grant-back written the way people narrow a grant:

```sql
revoke select on video_artifacts, video_generations, workspace_videos, workspaces,
                 video_artifact_sources, video_artifacts_current, video_summary_current
  from anon, authenticated;
grant select (workspace_id) on video_artifacts        to anon, authenticated;
grant select (workspace_id) on video_generations      to anon, authenticated;
grant select (workspace_id) on workspace_videos       to anon, authenticated;
grant select (id)           on workspaces             to anon, authenticated;
grant select (workspace_id) on video_artifact_sources to anon, authenticated;
grant select (workspace_id) on video_artifacts_current to anon, authenticated;
grant select (workspace_id) on video_summary_current  to anon, authenticated;
```

```
=== instrument 1: digest ===        check_live_exit=0
=== instrument 2: RULE 3 ===        M4 READ LOST / NOT READ-ONLY / OUT OF REACH / FN EXECUTABLE: 0 lines
=== instrument 3: assertions ===    schema assertions: RE-RUNNABLE subset passed …   assert_exit=0
=== runtime ===
  set role authenticated; select * from video_summary_current limit 1;
  ERROR:  permission denied for view video_summary_current
```

On a narrower clone I confirmed the probe is doing what I claim, not something adjacent:

```
table_select_authenticated=false     anycol_select_authenticated=true     col_blob_key=false
set role authenticated; select blob_key from video_artifacts limit 1;
  ERROR:  permission denied for table video_artifacts
  HINT:  Grant the required privileges … GRANT SELECT ON public.video_artifacts TO authenticated;
```

**Consequence, in observable units.** Identical to the state this branch filed as Blocking one round
ago and shipped a fix for: every logged-in read of the paid manifest raises 42501, the sidebar, the
serve path and the manifest read all fail, and all three instruments certify the database. It is
*more* reachable than mutation 24, not less — mutation 24 needs someone to forget a grant-back
entirely; this needs someone to write one with a column list. And the docstring's own warning
applies with full force: *"ADR-0012 MAKES IT MORE LIKELY, NOT LESS … the grant-back line is now the
only thing standing between the schema and this state."*

**Direction.** The read rule needs a table-level answer, not the union. Emit the two probes as
separate fields from the `---M4REL---` query (`table_privs` and `column_privs`), let `evaluate_m4`
keep using the union — that branch is about addition and the union is right there — and have
`evaluate_m4_reads` require `SELECT` in the **table-level** set. Then add mutation 26 to
`mutate-live-schema-check.sh`: revoke plus a one-column grant-back, requiring `M4 READ LOST`, with
the usual `anon_control` on `$TPL`.

---

## 🟠 H1 — the service-role omission table is a completeness claim, and it is wrong by four rows

**Premise, quoted** — `05_assert.sql:1014-1016`:

> *"Step 5 deleted the digest of 21 grant sites. The blocks above now assert 12. These NINE are known
> to be unasserted, and each line is the reason — not an oversight"*

and `:1029-1032`:

> *"When M4 is wired up, this table is the list to re-derive against real call sites, and any row that
> gains a direct caller needs an assertion here before it ships."*

The 21 is right: enumerated from the spec, `service_role` holds exactly 21 (relation, privilege)
pairs — `workspaces`, `workspace_videos`, `video_generations`, `video_artifact_sources`,
`video_artifacts` × {S,I,U,D} = 20, plus `video_generations_collectable` SELECT
(`01_workspaces.sql:29`, `03_generations.sql:69,563`, `04_artifacts.sql:258,671,944`). 21 − 9 = 12,
so the table asserts that twelve named privileges are watched.

**Executed.** I revoked each one on its own from a clean M4 clone and ran all three instruments:

| revoked from `service_role` | digest | RULE 3 (M4 problems) | assertions |
|---|---|---|---|
| `workspaces` SELECT | 0 | 0 | **0 — nothing sees it** |
| `workspaces` DELETE | 0 | 0 | **0 — nothing sees it** |
| `video_artifact_sources` UPDATE | 0 | 0 | **0 — nothing sees it** |
| `video_artifacts` INSERT | 0 | 0 | **0 — nothing sees it** |
| `workspace_videos` SELECT | 0 | 0 | 1 |
| `video_generations` SELECT | 0 | 0 | 1 |
| `video_generations` UPDATE | 0 | 0 | 1 |
| `video_artifact_sources` SELECT | 0 | 0 | 1 |
| `video_artifacts` SELECT | 0 | 0 | 1 |
| `video_artifacts` UPDATE | 0 | 0 | 1 |
| `video_artifacts` DELETE | 0 | 0 | 1 |
| `video_generations_collectable` SELECT | 0 | 0 | 1 |

The unasserted set is **thirteen**, not nine. Four grants that nothing watches are absent from the
one table written to enumerate exactly that.

**`video_artifacts` INSERT is worse than unasserted — it is ANTI-asserted.** The block at
`05_assert.sql:887-923` asserts that `service_role`'s *direct* insert is refused, and revoking INSERT
**preserves** that refusal, so the block stays green either way. Its 42501 can come from the missing
`slot_kind` EXECUTE (the intended cause, r7 H2) or from a missing INSERT grant, and the block cannot
tell them apart. Its own header states the rule it stops one privilege short of applying to itself:

> *"A negative assertion is only worth its exit code if the ONLY remaining reason to fail is the one
> being asserted"* — `05_assert.sql:884-886`

The anti-mask check below it (`:917-922`) verifies the FK parent landed. It does not verify *which*
privilege produced the 42501.

**Consequence.** The table is the ledger the next author will re-derive against real call sites. It
under-reports by 4 of 13, and one of the four is a grant whose assertion is satisfied by the grant's
own absence.

**Direction.** Derive the table rather than writing it: a small script that parses the six grant
sites into 21 pairs and cross-checks each against a revoke-and-observe run is the same shape as
`derive_no_session_access` and would have produced the table above. Failing that: move
`workspaces` SELECT/DELETE, `video_artifact_sources` UPDATE and `video_artifacts` INSERT into the
omission list with their reasons, and give the RPC-only block a discriminator (assert the direct
insert is refused **while** `has_table_privilege('service_role','video_artifacts','INSERT')` is
true).

---

## 🟠 H2 — a policy attached to an M4 relation opens cross-tenant reads; no instrument sees it

**Premise, quoted** — `scripts/m4_catalog.py:292-295`, the `_rules()` docstring:

> *"Present mode ignores EXTRA objects by design, and r5 recorded that as correct because 'a real
> database legitimately holds more than M4'. True of most extra objects; **false of an object ATTACHED
> to a manifest relation**, which is not an addition to the database but a modification of that
> relation."*

r6 H1 acted on that sentence for `pg_rewrite` and only for `pg_rewrite`. `pg_policy` is attached in
precisely the same sense, and it is in no relation's digest input: the `table:` term
(`m4_catalog.py:303-307`) is `relrowsecurity · relforcerowsecurity · relpersistence · relreplident ·
relhasrules · relispartition · reloptions · _rel_priv (now `''`) · _rules`. Policies appear only as
their own `pol:` objects, and present mode is `MANIFEST ⊆ live`.

**Executed**, on a clean M4 clone carrying one tenant's paid artifact:

```
BEFORE-POLICY:  set role anon;  ->  anon sees 0 of the tenant's artifact rows
create policy r9_wide on video_artifacts for select to anon, authenticated using (true);
AFTER-POLICY:   set role anon;  ->  anon sees 1 of the tenant's artifact rows
                and the blob_key: 00000000-…-0000000000a1/videos/v1/g1/summary.md
```

All three instruments, on a clone carrying *only* the policy (no fixture of mine):

```
policies on video_artifacts now: 2
digest      : M4 is PRESENT as expected — checked all 161 objects … 5 policies    exit=0
RULE 3      : 0 M4 problems
assertions  : RE-RUNNABLE subset passed against the live schema, and rolled back clean
```

The digest prints "5 policies" — the manifest's count — over a database that has six.

**Consequence.** An unauthenticated caller reads every tenant's `blob_key` on the paid manifest, and
the gate that guards the irreversible cutover says PRESENT. RLS is permissive-OR, so one added
`using (true)` policy defeats all five owner-scoping policies at once without touching any of them —
which is r5 B2's exact argument (*"disabling RLS does not touch a single policy row"*) rebuilt out of
an addition instead of a flag.

**Direction.** Fold attached policies into each relation's digest the way `_rules()` folds
`pg_rewrite`: `string_agg(polname || polcmd || polpermissive, ',' order by polname)` over
`pg_policy where polrelid = <rel>`, so a sixth policy moves `table:video_artifacts`. Add the
mutation. Consider the same for triggers attached to manifest relations, which have the identical
shape (an added trigger is caught today, but by luck — see "what I checked and did not find").

---

## 🟡 M1 — `m4_catalog.py` says REFERENCES/TRIGGER/MAINTAIN are covered elsewhere; nothing covers them

**Premise, quoted** — `scripts/m4_catalog.py:144-148`:

> `(anon TRUNCATE/REFERENCES/TRIGGER/MAINTAIN      -                 Dxtm     ✗ diverge — excluded)`
>
> *"The privileges that diverge are exactly the ones the M4 spec never mentions, and **they are already
> covered by `check-anon-exposure.py`, which ratchets them against a recorded per-environment
> baseline** — the right home, because it is environment-aware and this manifest cannot be."*

That is true of TRUNCATE — it entered `FORBIDDEN_ON_M4` (`check-anon-exposure.py:121`) in response to
r7 M4 — and false of the other three. `PROBED_ON_M4:129` is SELECT/INSERT/UPDATE/DELETE/TRUNCATE, so
they are never fetched; RULE 2's ratchet covers the five `MONEY_TABLES:89-90`, none of which is an M4
relation.

**Executed**, each granted alone on `video_artifacts`:

```
base        anon TRIGGER/REFERENCES/MAINTAIN=false/false/false  digest=0 rule3_m4=0 assertions=0
trigpriv    anon TRIGGER/REFERENCES/MAINTAIN=true/false/false   digest=0 rule3_m4=0 assertions=0
refpriv     anon TRIGGER/REFERENCES/MAINTAIN=false/true/false   digest=0 rule3_m4=0 assertions=0
maintpriv   anon TRIGGER/REFERENCES/MAINTAIN=false/false/true   digest=0 rule3_m4=0 assertions=0
```

**Consequence, bounded honestly.** Reaching code through `TRIGGER` also needs CREATE on a schema to
define the trigger function, so this is an unwatched capability rather than a demonstrated hole. What
is not bounded is the sentence: it is the *stated justification* for leaving those privileges out of
the digest, and a reader who checks the claim finds nothing at the address it names. RULE 3's own
message says the contract is *"SELECT and nothing else"* (`check-anon-exposure.py:326-327`) while the
predicate forbids four verbs.

**Direction.** Either add REFERENCES/TRIGGER/MAINTAIN to `FORBIDDEN_ON_M4` and `PROBED_ON_M4` (they
are table-level only; `has_any_column_privilege` already rejects all but REFERENCES, so
`COLUMN_LEVEL` needs no change), or correct the claim in `m4_catalog.py` to name TRUNCATE alone and
say the other three are deliberately unwatched, with the reason.

---

## 🟡 M2 — `anon_control` returns PASS when the instrument CANNOT RUN

**Premise, quoted** — `scripts/mutate-live-schema-check.sh:84-86`:

```bash
anon_out()     { python3 ./scripts/check-anon-exposure.py --local --database "$1" 2>&1; }
anon_gate()    { local o; o=$(anon_out "$1"); case "$o" in *"$2"*) return 0 ;; *) return 1 ;; esac; }
anon_control() { local o; o=$(anon_out "$1"); case "$o" in *"$2"*) return 1 ;; *) return 0 ;; esac; }
```

`anon_out` discards the exit status. `check-anon-exposure.py` exits **2** with a `CANNOT RUN —` banner
on a missing manifest (`:558`), an unreadable catalog (`:611`), an unparseable row (`:618`), an empty
definer list (`:623`), and — the one most likely to bite — a derived/declared out-of-reach mismatch
(`:579`). None of those outputs contains a problem token, so **every control passes.**

**Executed:**

```
$ anon_control r9_claude_no_such_db "M4 NOT READ-ONLY"
CANNOT RUN — could not read the catalog from LOCAL container … TREAT THIS AS NOT RUN.
 -> anon_control returns PASS over a database that does not exist
```

**Consequence.** Five of the suite's ticks are controls (mutations 10, 22, 23, 24, 25), and the
control is the entire mechanism r8 B1 installed so that a tick could not be earned by noise. A
control that passes because the instrument never ran is the same defect one layer out. Project rule,
verbatim: *"If a check cannot reach what it measures, that is a FAILURE, not a pass."* The paired
`anon_gate` would fail in the same run, so today this surfaces as a survived mutation rather than a
false green — that is why it is Medium — but the pairing is an accident of the two calls sharing a
schema, not a property anything asserts.

**Direction.** Have `anon_out` preserve the status (`local o rc; o=$(...); rc=$?`), and make both
helpers return failure on `rc = 2` or on output matching `CANNOT RUN`.

---

## 🟡 M3 — the r9 identifier fix is instance-not-class: case and the grantee side are still verbatim

**Premise, quoted** — `_norm_ident`, `check-anon-exposure.py:151-164`:

> *"a parser that is correct only for the spelling in front of it is a tripwire, not a derivation."*

The fix normalises schema qualification and double quotes **on the relation side**. It does not fold
case, and the grantee side (`session_readable:175`, `{g.strip().lower() …}` against the raw token) was
not touched at all.

**Executed** against the shipped functions:

```
UPPERCASE relation      GRANT SELECT ON VIDEO_ARTIFACTS TO ANON;
   session_readable={'VIDEO_ARTIFACTS'}    derived_out_of_reach=('video_artifacts',)   ✗
mixed case              grant select on Video_Artifacts to anon;
   session_readable={'Video_Artifacts'}    derived_out_of_reach=('video_artifacts',)   ✗
QUOTED GRANTEE          grant select on video_artifacts to "anon";
   session_readable=set()                  derived_out_of_reach=('video_artifacts',)   ✗
column-list grant       grant select (workspace_id, slot) on video_artifacts to anon;
   session_readable=set()                  derived_out_of_reach=('video_artifacts',)   ✗
```

All four are ordinary SQL; Postgres folds unquoted identifiers to lower case, so the first two are
what a `pg_dump`-derived or hand-uppercased spec looks like. Each makes an ordinary readable relation
derive as OUT OF REACH.

**Consequence.** It fails **closed** — `fetch:578-583` exits 2 on the derived/declared mismatch — which
is why this is Medium. But the message it prints is *"One of them is stale. Refusing to guess which."*
and the cheap repair is to edit `M4_NO_SESSION_ACCESS` to match a wrong derivation, which silently
removes a relation from RULE 3's strongest branch. The hand-list is described as *"kept only as a
cross-check that FAILS LOUDLY"* (`:141-146`) — it is currently also the only thing standing between a
spelling change and a disarmed rule.

**Direction.** `return name.strip('"').lower()` when the token was unquoted, and run each grantee
through the same normaliser. Add the four cases above to `--self-test`.

---

## 🟡 M4 — the out-of-reach set is derived from a glob that includes the adversarial test corpus

**Premise, quoted** — `read_spec`, `check-anon-exposure.py:191-198`:

> *"Every schema file, concatenated. Exits 2 rather than deriving from nothing."*

```
$ [p.name for p in sorted(SPEC_DIR.glob('*.sql'))]
['01_workspaces.sql', '03_generations.sql', '04_artifacts.sql', '05_assert.sql']
```

`05_assert.sql` is 2,508 lines of deliberately hostile SQL whose job includes `set local role anon`
and `execute 'truncate video_artifacts'`. It is not the DDL contract; it is the thing that attacks it.

**Executed** — one line appended to the corpus:

```
derived from the real spec                         : ('video_generations_collectable',)
...with ONE grant line added anywhere in 05_assert : ()
```

**Consequence.** Today nothing fires: I grepped `05_assert.sql` for `grant`/`revoke` and every hit is
prose in a comment. The failure mode is latent and it is fail-closed *by side effect* — the hand-list
would then disagree and the gate would exit 2 pointing at `M4_NO_SESSION_ACCESS` as the suspect,
which is the wrong file. It stops being fail-closed the moment M4 gains a second out-of-reach
relation whose assertion corpus grants it to `anon` in order to prove RULE 3 bites: derived and
declared would then agree by coincidence and the relation leaves the strongest branch in silence.

**Direction.** Glob the DDL files explicitly (`01_*`, `03_*`, `04_*`) or exclude `05_assert.sql` by
name, with the reason written next to it, and assert the exclusion in `--self-test`.

---

## ⚪ L1 — round 8 renumbered the suite 11 → 12 and left six live "of 11" references

`scripts/check-schema-gates.sh` runs twelve gates and labels them `1/12` … `12/12`. Still saying
eleven, in files nobody re-ran:

| file:line | text |
|---|---|
| `scripts/m4_catalog.py:202` | `check-anon-exposure.py RULE 3   gate 11/11, every run` |
| `scripts/m4_catalog.py:203` | `check-anon-exposure.py RULE 3   gate 11/11, every run` |
| `scripts/m4_catalog.py:204` | `05_assert.sql                  gate 8/11, M4_PHASE=post only` |
| `…/schema/05_assert.sql:806` | `So gate 1/11 went red on the block's own fail-closed guard` |
| `docs/adr/0012-…md:99,100` | `gate 11/11` · `gate 8/11` |
| `docs/adr/0013-…md:57,58,72` | `gate 11/11` ×2 · `gate 8/11` |
| `scripts/check-schema-gates.sh:112` | *"the suite's other nine gates are all local"* — eleven others now |

`python3 scripts/check-docs.py` is green over all of it (measured, exit 0). This is the fourth
instance this week of the class the round brief names: a change to one file silently invalidating an
anchor in another. The ADRs are the durable decision record for fork (a), and their "what catches it"
column now points at the wrong index.

---

## ⚪ L2 — `evaluate_m4_reads` accepts `expect_roles` and never uses it

`check-anon-exposure.py:347-351` declares `expect_roles: tuple[str, ...] = ()`; `main():904` passes
`SESSION_GRANTEES` to it. Measured — occurrences of `expect_roles` inside the function body: **1**,
which is the signature line itself. The fail-closed-on-a-missing-role behaviour the parameter
advertises is supplied by `evaluate_m4:336-343`, so the composition is correct today. It is the exact
shape of r8 L1 one function over (*"the relation half fails closed on a missing role and this did
not"*), and a parameter that is accepted and ignored is a claim the next reader will believe. Either
implement it or drop it from the signature and the call.

---

## ⚪ L3 — the capability block states a narrowing rule and applies it to one of its five items

`05_assert.sql:977-982` carries:

> *"⚠ ZERO-ROW PREDICATE ON PURPOSE … An UPDATE matching no rows still requires the UPDATE privilege,
> so this discriminates exactly the thing the block is about and collides with nothing … an assertion
> that reaches past its subject steals the failure from the assertion that would have named the
> cause."*

Item 4 follows that. Item 1 does not: `update video_generations set body_collected = body_collected
where … generation_id = 'gDIRECT'` targets the row the previous block inserts, so it must also
survive `video_generations_freeze_trg` and `forbid_collecting_current_trg`. It passes today (measured
— the block is green on an unmutated M4), and a no-op assignment does not trip either guard; the
point is that the same block writes the rule down and applies it once.

Two related inaccuracies in the same comment. `:938-939` cites the grants it asserts as
*"(`03_generations.sql:68-69,562-563`, `04_artifacts.sql:257-259`)"*, omitting `04_artifacts.sql:671`
(`video_artifacts`) and `:944` (`video_generations_collectable`) — which items 2, 4 and 5 are actually
about. And `check-anon-exposure.py:386-390` says a lost read means the consumers *"all return empty"*;
measured, they raise `ERROR: permission denied`, which is the better of the two outcomes and worth
saying correctly.

---

## What I checked and did NOT find

**Both r9 codex fixes are real, and I re-measured rather than trusting the messages.**

- **H1, the mutation-22 token.** On an *unmutated* M4 template `check-anon-exposure.py` prints
  `LOWER THE BASELINE 0 money tables are TRUNCATE-able` — so the old bare `TRUNCATE` token was
  present in the control and every tick was unearned, exactly as claimed. The new token
  `holds TRUNCATE on` appears **0** times on that same template, and the new control asserts it.
  The escaped backticks in `anon_gate "…" "holds TRUNCATE on \`video_artifacts\`"` are literal, not
  command substitution — the mutation matches and reports ✓.
- **M1, `_norm_ident`.** The five new self-test cases are genuine (66/66 green), and the shipped spec
  really does use bare names at all thirteen grant sites, so the codex finding was a latent tripwire
  rather than a live defect. My M3 above is the residue, not a contradiction.
- **All five `anon_gate` tokens now have a control** (mutations 10, 22, 23, 24, 25). I checked each
  token against the template's output and none of them can be earned by the pre-existing noise.

**Gate suite, run one at a time against the live container:**

| gate | result |
|---|---|
| 1 `verify-schema.sh` | **exit 0** — `✅ schema verified (rolled back)`; r8 codex's red is fixed |
| 2 `mutate-schema.py` | **exit 0** — `63/63 mutations behaved as expected` · `baseline restored: GREEN ✅` |
| 3 `check-guard-coverage.py` | exit 1, 10 problems — red by plan (Task 5) |
| 4 `check-sentinel-meanings.py` | exit 1, 5 problems — red by plan (Task 5) |
| 5 `check-vocabulary-collisions.py` | exit 0 |
| 6 `check-docs.py` | exit 0 |
| 7 `check-catalog-coverage.py` | exit 0 — 203 columns, 73 digested, 130 excluded with a reason |
| 9 `gen-m4-manifest.py --check` | exit 0 — manifest current, 161 objects |
| 12 `mutate-live-schema-check.sh` | **exit 0 — 25/25, every mutation caught**, 1m06s |
| — `check-anchors.py` · `check-producer-enumeration.py` | exit 0 |
| — `check-review-rounds.py` | exit 1 only because this half had not been written yet |
| — `run-schema-assertions.sh --self-test` | 12/12 including the live RED proof |
| — `build-m4-schema.py --self-test` · `check-live-schema.py --self-test` | green |

**Regressions I hunted and could not reproduce:**

- **An added trigger that swallows writes** (r6 H1's twin, and the reason I doubted policies would be
  the only gap): `create trigger … before insert on video_artifacts … return null` **is** caught —
  assertions exit 1 on `record_artifact said recorded and left 0 artifact rows`. The r8 read-back
  (`05_assert.sql:861-867`, *"the return value is not the evidence"*) earns its place here.
- **A dropped column default** — caught by the `col:` digest (exit 1).
- **RLS disabled, no-force, `security_invoker = false`, a restrictive policy, `strict`, a changed
  argument default, a renamed rollback survivor, a `do instead nothing` rule** — all still caught
  (harness 25/25, each with its own narrowness falsifier firing).
- **A revoke that undoes a grant.** `session_readable` parses grants only. I checked all 21 `revoke
  all on …` sites in `01`/`03`/`04`: every one precedes its grant (ADR-0012's order), so the grant-only
  parse is correct for the shipped text. Noting it as an unstated assumption, not a finding.
- **A role that exists but was never granted** — `M4 READ LOST` fires; **a role that does not exist** —
  `ROLE NOT PRESENT` fires (`evaluate_m4:336-343`). Both directions covered.
- **A relation added to the manifest after the spec parse** — the manifest is generated from the spec
  by `gen-m4-manifest.py`, so both move together and gate 9 is green.
- **Gate 12's synthetic template vs a real deployment** (round 8's M4): mutation 19 builds a
  production-shaped database with `pg_default_acl` rows and requires PASS; it is green. I did not find
  a privilege state expressible on prod that the template cannot express — the divergence is
  `alter default privileges` and a `claude_ro` grantee, and 19 covers the first. `claude_ro` remains
  untestable locally by construction, which is r6 B1's accepted residue, not new.

## CONVERGED?

**NOT CONVERGED.** B1 reopens the finding this branch's own round-8 commit was written to close, in
the same polarity, one privilege granularity down. H1 and H2 are both new coverage holes in the
newest code on the branch.

To have written CONVERGED I would have had to see: `evaluate_m4_reads` reading a **table-level**
SELECT probe held separately from the column union, with a mutation that revokes and grants back one
column and requires `M4 READ LOST`; the omission table's twelve-asserted arithmetic re-derived by
execution rather than by reading, so `workspaces` SELECT/DELETE, `video_artifact_sources` UPDATE and
`video_artifacts` INSERT appeared on it; and a policy attached to a manifest relation moving that
relation's digest, the way `_rules()` already makes an attached rewrite rule move it.

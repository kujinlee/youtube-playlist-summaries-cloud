# ADR-0007 implementation — adversarial review (Claude), 2026-08-10

**Branch `feat/adr-0007-implementation`, 5 commits on `master`. Surface: `git diff master..HEAD`.**
First review of *code* on this spec; the decision (rounds 13–17, merged `efee284`) was not re-litigated.

## Oracles — both run, independently, against live Postgres

| Oracle | Result |
|---|---|
| `verify-schema.sh` (container `supabase_db_youtube-playlist-summaries-cloud`, PG 17.6.1.147, rolled back) | `ALL_STATEMENTS_OK` — ✅ schema verified |
| `python3 mutate-schema.py` (full run, temp copy) | **59/59 behaved as expected**, 0 INVALID, 0 unexpected GREEN, baseline restored |

I read every RED line rather than the total. Each mutation's captured error names the guard it was
aimed at (`classify()` compares `expect` against the detail on all three branches — the round-6/7/9
sweep is complete), so the count is honest for what it covers. **What it does not cover is the
subject of H1 below.**

Everything measured here ran inside `begin; … rollback;`. No repo-tracked file was modified;
mutations ran on the harness's own temp copy.

---

## Findings

### H1 — Blocking-adjacent. The T4 "only inserter" assertion detects exactly one spelling of INSERT; five ordinary second-inserters evade it. MEASURED.

ADR-0007's foundation for `model`, `dig` and `digDeeper` is *carried, not enforced*, and the ADR
says so explicitly — "**the structural fact is the guard, so the structural fact is what is
tested** — an assertion now fails if a second inserter ever appears"
(`docs/adr/0007-artifacts-are-an-append-only-log.md:525-528`). That assertion is
`schema/05_assert.sql:1356-1368`:

```sql
   where n.nspname = 'public'
     and p.prosrc ~* 'insert\s+into\s+(public\.)?video_generations\y';
```

It is a **regex over `pg_proc.prosrc`, scoped to schema `public`**. I built five second-writer
functions, each of which *actually created a `video_generations` row*, and ran the assertion's own
query after each. All five are invisible to it:

| # | Second writer | Row created | Assertion sees |
|---|---|---|---|
| A1 | `merge into public.video_generations … when not matched then insert` | 1 | `record_artifact` |
| A2 | `insert into public.vg_v …` through an auto-updatable view | 1 | `record_artifact` |
| A3 | `insert into public."video_generations" …` (quoted identifier) | 1 | `record_artifact` |
| A4 | `insert into public . video_generations …` (space around the dot) | 1 | `record_artifact` |
| A5 | the same INSERT in a function in schema `probe_ns` | 1 | `record_artifact` |
| A6 | **control** — the naive spelling | — | `evade_naive, record_artifact` ✅ |

`MERGE` is not exotic: it is the standard multi-row upsert form on PG 15+, and this schema runs on
17.6. An updatable view is the other obvious one — the brief asked specifically whether a view could
evade, and it does.

The branch's own mutation for this rule — `"a SECOND function writes video_generations (T4's carried
invariant, broken)"` (`mutate-schema.py:455-465`) — injects `t4_shadow_writer` using the *naive*
spelling. It goes RED, correctly, and proves the assertion is load-bearing. **It cannot and does not
prove the assertion is complete**, which is this project's own recorded lesson (*"Mutation testing
proves load-bearing, never complete"*).

The cost when the invariant silently degrades is not hypothetical — it is written out in this
branch's own characterisation test at `05_assert.sql:1392-1437`: bare generation → collectable →
swept → paid record lands legally → **invisible in `video_artifacts_current` forever**. Money spent,
content unreachable, no error anywhere.

**Fix:** stop matching source text. Enumerate the actual write surface instead — e.g. assert over
`pg_depend`/`pg_rewrite` for rules and updatable views on the table, and widen the pattern to
`(insert|merge)\s+into\s+[^;]*video_generations` with `nspname` unrestricted (or explicitly
enumerate permitted schemas). At minimum add `merge` and drop the `nspname = 'public'` restriction,
and record in the assertion's comment what spellings it still cannot see — the instrument's success
line currently claims more than its input covers, which is the exact shape `docs/plugins.md` and this
ADR both name.

---

### H2 — `record_artifact` silently ADDS provenance to an already-recorded paid artifact. The stated rule is "the same set, or raise". MEASURED through the RPC alone.

The rule, stated three times (ADR `:732-736`; `04_artifacts.sql:548-551`; the assertion label at
`05_assert.sql:1981`):

> a re-record must present the **SAME** source set, or raise; an OMITTED `p_source_generation_id`
> carries the recorded set forward unchanged.

The implementation (`04_artifacts.sql:560-575`):

```sql
    if v_recorded = '{}'::text[] then
      insert into public.video_artifact_sources …
    elsif v_recorded is distinct from array[p_source_generation_id] then
      raise exception …
```

`v_recorded = '{}'` is read as *"this artifact has no provenance yet, so this is the first write"*.
It also means *"this artifact is recorded as having no sources"* — and those are two different facts
in one sentinel, the conflation this spec has spent five rounds removing elsewhere. Measured, no
direct DML anywhere:

```
C1 first record -> recorded
C1 provenance after first record: <empty>
C2 re-record presenting {gCa} against a recorded set of {} -> already_recorded
C2 provenance is NOW: gCa  <- mutated on an already-recorded paid row
C3 second change refused (as designed): … it records {gCa}, and this record presents {gCb}
```

So the third call raises and the second does not. Provenance is a **ranking input** (the
source-currency rung, `04:734-743`) and a **GC input** (`04:862-864`), and the append-only trigger's
own comment says the provenance branch "moves onto `video_artifact_sources`" (`04:941-944`) — i.e.
the rule is asserted to still hold. It does not, on the one transition a real caller reaches: record
first, learn the source later. Compare the sibling case eleven lines up, where a divergent
`blob_key` *raises* precisely because "it is a caller bug — a SHAPE violation, where rejecting is
correct" (`04:477-478`). The two are treated inconsistently.

It is also **one-way**: the row it adds can never be removed (see H3), so a single wrong call is
permanent.

Neither the assertions nor the mutations reach it. `"T3: the re-record set comparison removed"`
mutates the `elsif`; `"T3: a re-record REPLACES the source set"` mutates the `if` into a delete; the
assertion at `05_assert.sql:1965-1988` exercises same-set, omitted-source and different-source, and
never empty→non-empty. This is an absence, and per the file's own population-ratchet argument an
absence is invisible to every opt-in instrument at once.

**Fix:** distinguish "no row yet" from "recorded empty" — gate the insert on the artifact having
just been created (`not v_existed`) rather than on the recorded set being empty, and raise otherwise:

```sql
    if v_recorded = '{}'::text[] and not v_existed then   -- first write of this artifact
      insert …
    elsif v_recorded is distinct from array[p_source_generation_id] then
      raise …
```

and add the negative to `05_assert.sql` plus a mutation anchored on the new conjunct.

---

### H3 — The GC reachability `not exists` is a permanent pin, not a retention delay. The schema comment claims a release mechanism that cannot fire. MEASURED.

`video_generations_collectable` gained (`04_artifacts.sql:862-864`):

```sql
   and not exists (select 1 from video_artifact_sources vas
                    where vas.workspace_id = g.workspace_id and vas.video_id = g.video_id
                      and vas.source_generation_id = g.generation_id);
```

The comment eleven lines above states the intent and the escape hatch (`04:848-851`):

> ⚠ IT IS DELIBERATELY NOT SCOPED TO *CURRENT* RENDERS. A superseded model still names the summary
> it was built from, and **§8's retention clock — not this view — is what eventually releases it.**

**There is no such release.** Measured:

```
B9  pin is PERMANENT — provenance cannot be deleted:
      video_artifact_sources: cannot DELETE the provenance of a live artifact … (source gS1)
B9b artifact cannot be deleted either:
      video_artifacts is append-only: cannot DELETE recorded paid row (slot model, gen gM1)
C4  gCa: collectable_now = 0, pinned_by = 1
```

The three exits are all closed by design in this same branch: the provenance row is undeletable
while its artifact lives (`04:1011-1017`), the paid artifact is undeletable at all (`04:931-934`),
and the sweeper *selects through* this view (`04:790-793`), so no age predicate it owns can ever
reach a pinned row. The only thing that clears the pin is deleting the account.

Consequence: once any `model` or `digDeeper` is recorded against a summary generation — which is
every served document, since `model` is generated on the first serve — **that summary generation's
blob is never collectable again**. §8's entire retention story ("a paid blob is collected 90 days
after it stops being current") becomes unreachable for the dominant case, and it does so in the
branch whose own trigger comment quotes §8's rule for the opposite direction: *"fail toward
collectable rather than toward pinned forever"* (`04:968-969`).

The assertion pair at `05_assert.sql:1943-1958` tests exactly the half that works — referenced ⇒
protected, unreferenced ⇒ collectable. Nothing tests that a reference is ever released, because
under this design it never is.

**Fix:** either (a) scope the `not exists` to *live* references — sources of artifacts that are
themselves still reachable, i.e. exclude sources whose referencing artifact's generation is already
`body_collected` — or (b) accept the pin explicitly, delete the "§8's retention clock … releases it"
sentence, and record in the ADR that referenced summary generations are retained for the life of the
workspace so the storage consequence is a decision rather than a side effect. What is not tenable is
the current pairing: a hard permanent gate with a comment promising it is temporary.

---

### M1 — The ADR's stated reason for keeping `video_generations.state` names four consumers this branch deleted.

`docs/adr/0007-…md:430-434`:

> It is **kept**, because five consumers still read it: the four completeness constraints (all
> written `state <> 'complete' or …`) and `video_artifacts_generation_complete`

T4 deleted that disjunct from all five constraints (`03_generations.sql:386-430`). `grep -n "state
<> 'complete'"` across `schema/*.sql` now returns only comments, `video_generations_freeze`'s
`new.state <> 'complete'` (line 530) and one assertion read — **no CHECK constraint references
`state` at all.** Four of the five cited consumers are gone.

The schema itself carries the correct, updated justification (`03:305-315`: the CHECKs now bind
unconditionally; `video_artifacts_generation_complete` distinguishes present-and-complete from
`<absent>`; `record_artifact` reads it for `completed_by_another`). The ADR was edited in the same
branch (`95d3739`) and this paragraph was not. Fix: replace the ADR paragraph with 03's three
reasons.

---

### M2 — The per-kind attempt ceiling is deleted with no successor and no decision, and the decision is tracked nowhere.

ADR-0007 Consequences (`:643-650`) assigns this explicitly:

> Deleting the artifact-layer bound silently promotes summaries from 1 to 5. **The implementing
> slice must state which number wins**; this ADR does not get to leave it implicit.

The implementing slice declines (`04_artifacts.sql:309-313`):

> Deleting the artifact-layer bound silently promotes a summary from 1 paid attempt to 5.
> **WHICH NUMBER WINS IS AN OPEN DECISION, not something this file settles.**

Its assertion went with it (`ok (bound): with summary_max_attempts=1 a crashed summary slot is NOT
retryable`, retired). I could find no task or backlog entry carrying it: tasks #44 (T5 code
preconditions) and #45 (`doc_key` re-key) do not cover it, and `docs/roadmap-to-launch.md:880` is
about revisiting the *value* of `summary_max_attempts`, not about the loss of its enforcement site.

Mitigating and stated for calibration: **nothing outside `docs/` implements any of this** —
`grep -rn "reserve_artifact_slot\|record_artifact" --include=*.ts --include=*.sql .` outside `docs/`
returns one hit, a comment in `tests/lib/blob-addressing-caller-contract.test.ts`. So this is a spec
regression today, not a live money regression. It becomes one the day the schema ships, which is
exactly why the ADR asked the implementing slice to close it. Fix: file it (roadmap + task, same
turn), or state the number.

---

### M3 — ADR-0007's `[VERIFIED:]` line tags into the two files this branch rewrote are now largely stale.

37 tags point at `schema/03_generations.sql:N` / `schema/04_artifacts.sql:N`. The branch moved ~600
lines out of `04` and rewrote `03`'s constraint block. I resolved 13 of them; **11 now land on
unrelated content**:

| Tag | Claimed | Actually at that line now |
|---|---|---|
| `04:107` | `art_summary_has_no_source` | `video_artifacts_identity_uq` |
| `04:95` | `art_paid_has_generation` | a comment about tenant coordinates |
| `04:162-163` | `video_artifacts_paid_uq` keys | the `blob_key` round-5 comment |
| `04:814-816` | the ranking view's currency rung | the deleted GC-floor comment |
| `04:91-92` | the provenance FK | `primary key (artifact_id)` |
| `04:969-973` | the append-only PROVENANCE raise | the `detached_at` clock |
| `04:1023` | `video_artifacts_generation_complete` | `before update or delete on video_artifact_sources` |
| `03:291` | `state not null default 'complete'` | a bare comment line |
| `03:394`, `03:395` | `gen_complete_has_produced_at`, `gen_card_complete` | T4 prose |
| `03:498-500` | `video_generations_freeze_trg` | the §6.2 detach comment |

(`03:64` and `03:264` still resolve.) The ADR itself states the standard this violates — *"In a
document whose entire method is these tags, a tag that resolves to the wrong line is the failure
mode, not a typo"* (`:139-142`) — after a round-14 audit of all 57 tags. The audit was run against
the pre-branch schema and not re-run. Fix: re-run the audit; better, make the tags anchor-based
(constraint/function name) so a line shift cannot break them, or add a `scripts/check-docs.py` rule
that resolves them.

---

### M4 — A repo-tracked contract test still documents the fence this branch deletes, contrary to the ADR's own instruction.

`tests/lib/blob-addressing-caller-contract.test.ts:10-18, 30-31` (unmodified by this branch):

> `record_artifact` completes a generation **ONLY for `reserved_by = p_token`** — no fallback, no
> recovery path. […] If one of these ever fails, do not "fix" the test: **the schema's fence must be
> reconsidered**, because its premise has changed.

`reserved_by` is deleted (`03_generations.sql:432-441`) and there is no fence. ADR-0007 Consequences
(`:443-446`) says the test stays but is re-purposed — *"it now documents job-queue behaviour rather
than propping up a schema premise"* — and the re-purposing was not done. A comment describing
behaviour the code does not have is this project's stated definition of an unenforced assertion, and
here it actively misdirects the next reader to a fence that no longer exists. Fix: rewrite the
header; the tests themselves are fine and still pin real `worker-runner` properties.

---

### L1 — `record_artifact` takes a scalar source; the table, the rung and the GC check are all set-shaped.

`p_source_generation_id text` (`04:356`) and `array[p_source_generation_id]` (`04:568`) mean no RPC
caller can build a multi-source artifact. The ADR heads this section **"Multi-source render
provenance — SETTLED (round 13, H4)"**; the code is honest about the gap and says so at
`05_assert.sql:1902-1907` ("an honest gap rather than a choice of style"), writing the two-source
fixture by direct DML. Reported only because the ADR's heading and the code's own note disagree
about how settled this is. No fix needed beyond a line in the ADR.

### L2 — Residual race on the divergent-`blob_key` refusal.

`04:479-487` reads the slot, then `04:528-538` inserts with `on conflict … do update` that
deliberately does **not** assign `blob_key`. Between the read and the insert a peer can land a row
with a different key; the `do update` then silently keeps the peer's key and the caller is told
`already_recorded` — round 9's H3 shape, surviving in the race window. Same class and same size as
the 23514 residual the function already names at `04:427-431`. Worth one sentence beside that
residual rather than a fix.

---

## What I could NOT break

- **The set-shaped provenance enforcer holds.** `video_artifact_sources_insert_once` is an
  `after insert … for each statement` trigger with a transition table; its predicate reduces exactly
  to *"did this artifact have provenance before this statement"*. Every attack the brief named, and
  a few more, were refused with the right message:
  | Attack | Result |
  |---|---|
  | plain second INSERT | refused (`… already records {gS1}, and this INSERT adds {gS2}`) |
  | `on conflict do nothing` with the existing row included in the same statement (the overlap attack — skipped rows do **not** enter the transition table, so the count comparison still holds) | refused |
  | `on conflict do update` (routing the conflicting row onto the UPDATE path) | refused by the sibling `before update` freeze |
  | data-modifying CTE, `delete … returning` + `insert` in **one** statement | refused by the DELETE branch |
  | two statements in one transaction | refused (the second sees pre > 0) |
  | identical-set re-insert with `do nothing` | benign no-op, as intended |
  | multi-row **first** set on a fresh artifact | permitted, as intended |
  Rounds 16 and 17 got the shape wrong twice; this shape is right, and the reasoning at
  `04:1026-1037` for why a per-ROW trigger cannot express the rule is correct.
- **`art_summary_has_no_source` cannot be evaded by mutating the parent.** `slot` and `kind` are
  frozen on paid rows by the append-only trigger; a free row cannot become a summary because
  `art_paid_has_generation` would reject it. The FK ordering argument at `04:1070-1072` holds.
- **The append-only trigger's gate change is strictly a widening.** Old gate
  `old.state in ('recorded','detached') and old.generation_id is not null` → new
  `old.generation_id is not null`. Free rows were never covered and still are not; a paid row in an
  unexpected state is now covered where it previously fell through to `return new`. The retirement of
  the two `pending` permissions removes fail-open branches rather than protection, and
  `"trigger gate narrowed back to recorded-only"` re-anchors the mutation in the correct direction.
- **The GC floor's `state = 'complete'` deletion (T2) removed nothing live.** `record_artifact` is
  the only producer, it writes `'complete'`, and T4 made the domain single-valued, so no reachable
  row could fail the predicate. `video_artifacts_generation_complete` still catches the case that
  matters (`<absent>`), proven by `"record_artifact no longer creates the generation"` going RED with
  the exact `generation gG1 is <absent>` message.
- **The 24 retired assertions.** I walked each. All but one are reservation-protocol mechanisms that
  no longer exist (`reserve`/`renew`/`reclaim`/token/`reserved_by`/`pending`), and each was either
  deleted with its mechanism or replaced by a same-shaped successor (`recorded_after_token_loss` →
  `already_recorded`, "three base tables" → "four", the span carry-forward, the two-writer append).
  The exception is M2 above. No live rule lost its only test.
- **The mutation harness itself.** It reads repo files and writes only into `tempfile.
  TemporaryDirectory` (`:829-857`) — round 9's R9-1 fix holds, and `git status` stayed clean through
  a full 59-mutation run plus three probe suites. `classify()` compares `expect` on all three RED
  branches, so a mutation caught by the wrong guard scores `RED(other)` and counts as a failure. The
  two `GREEN(expected)` entries are `expect is None` by construction and are documented no-ops.
- **`record_artifact`'s read-then-insert.** The `on conflict do nothing` + re-read + `v_made_gen`
  sequence is correct under a concurrent peer, and the freeze trigger backstops content overwrite.

---

## Verdict

**NOT CONVERGED.**

Blocking reason: **H1, H2 and H3.** H1 leaves the assertion that ADR-0007 nominates as the sole
guarantor of its foundational invariant able to see one spelling out of six (measured). H2 breaks a
provenance-immutability rule the branch states in three places, on a caller-reachable path, in a
direction that cannot be undone. H3 converts §8's retention clock into a permanent pin for the
dominant case while the schema comment promises the opposite.

None of the three is in the decision — all three are in the implementation, which is where this
review was pointed. The provenance enforcer, the trigger-gate widening, the GC-floor deletion and
the assertion retirements are all sound, and the 59/59 green is earned for what it measures.

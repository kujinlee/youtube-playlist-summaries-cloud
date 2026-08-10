-- 04 — the artifact manifest, APPEND-ONLY, plus `current` as a view.
--
-- Round 4 J2-1 / Codex #6 (Blocking): `primary key (workspace, video, slot)` admits ONE row per slot,
-- while rule 13 ranks MANY and A-1's record-first order must insert one BEFORE the bytes. All three
-- ways out of that failed. Resolution: the manifest becomes append-only — one row per GENERATION per
-- slot — and `current` becomes a query rather than a stored pointer. That is what "current is derived"
-- always required and the round-2 PK silently forbade.

-- ⚠ `set search_path` PINNED — ⟳ ROUND 6, and this is the FOURTH instance of one class in a single
-- session (the others: `no_corrections_hash`, pgcrypto's `digest`, and an enum literal, all in 03).
-- A `language sql` helper with no pinned path inherits the CALLER's, and this one is reached from
-- inside `record_artifact` — a `security definer set search_path = ''` function — through the
-- `art_slot_kind` CHECK (it was `reserve_artifact_slot` when measured; ADR-0007 deleted that
-- function and left the hazard untouched, because the hazard is the definer path, not the caller).
-- Its unqualified `::artifact_kind` then cannot be resolved and the INSERT
-- fails with `type "artifact_kind" does not exist`, at runtime, from a constraint, three files away.
-- MEASURED; invisible at every direct call site.
--
-- THE GENERAL RULE, since finding it four times by hand is not a strategy: EVERY function this schema
-- ships pins its search_path. A helper without one is not "using the default", it is inheriting an
-- unknown, and definer functions make that unknown EMPTY.
create function slot_kind(p_slot text) returns artifact_kind
  language sql immutable
  set search_path = public
  as $$
  select case
    when p_slot = 'summary'    then 'summary'
    when p_slot = 'model'      then 'model'
    when p_slot like 'dig:%'   then 'dig'
    when p_slot = 'digDeeper'  then 'digDeeper'
    when p_slot like 'pdf:%'   then 'render'
    when p_slot = 'html'       then 'render'   -- round 5 L3/Codex: `like 'html%'` also matched
  end::artifact_kind $$;                       -- 'html-preview', 'htmlish' — an unanchored pattern
                                               -- beside an anchored `pdf:%`. §4.0 names one html slot.

create table video_artifacts (
  workspace_id  uuid not null,
  video_id      text not null,
  slot          text not null,
  generation_id text,                    -- NULL for a free render: it belongs to no generation
  kind          artifact_kind not null,
  -- ⛔ `pending` IS DELETED BY ADR-0007 (T1). A row appears in this table only when its content has
  -- already been produced and paid for, so there is no contentless state to represent. What survives
  -- is the §6.2 lifecycle — a recorded dig may stop matching a section — and nothing else.
  -- The DEFAULT moves with it: `pending` was the default because a row was born by RESERVING, and a
  -- row is now born by RECORDING.
  state         text not null default 'recorded'
                check (state in ('recorded','detached')),
  blob_key      text not null,
  source_generation_id text,             -- §5.1.2: what a derived artifact was built FROM
  start_sec     int,
  end_sec       int,
  -- ⛔ `lease_expires_at`, `lease_attempts`, `lease_token`, `reserved_at` STOOD HERE (round 4 Codex
  -- #5; round 6 H5 / Codex B2) AND ARE DELETED BY ADR-0007. They were a second copy of `jobs`'
  -- coordination vocabulary — `lease_token`, `lease_expires_at`, `attempts`, `locked_by` — and every
  -- defect of rounds 7-12 lived in the seam between the two. The concerns they were carrying already
  -- have owners: producer execution is the job lease + heartbeat, at-most-once spend is
  -- heartbeat-abort plus `guardrail_config`'s per-kind bounds, and "which artifact is current" is
  -- the ranking view below. See docs/adr/0007-artifacts-are-an-append-only-log.md.
  -- ⟳ ROUND 6 — WHEN the row was detached, because §8's retention clock has no other input.
  -- USER DECISION 2026-08-06: a detached artifact is NOT kept forever. §6.2 said a detached dig is
  -- "never a sweep candidate"; §8 says a paid blob is collected 90 days after it stops being current.
  -- A detached dig is never current BY CONSTRUCTION, so those two rules contradicted and the one that
  -- runs would have won. §8 wins: detached artifacts are cleared periodically. §6.2 is corrected.
  --
  -- The clock starts at DETACHED-AT, not at stopped-being-current: a dig can be detached while its
  -- generation is still current, and a not-current clock would then never start at all.
  --
  -- Same argument §6.2 makes for the span, and it is the reason this column is not deferred:
  -- CHEAP NOW, UNRECOVERABLE LATER. Once digs start detaching without a timestamp there is no way to
  -- reconstruct when they detached, and every one of them is paid content on a delete path.
  detached_at   timestamptz,
  updated_at    timestamptz not null default now(),
  -- APPEND-ONLY, but NOT via a primary key. MEASURED 2026-08-06: `primary key (…, generation_id)`
  -- implicitly makes generation_id NOT NULL, which makes every FREE RENDER unrepresentable —
  -- `null value in column "generation_id" … violates not-null constraint` — and makes
  -- art_paid_has_generation unsatisfiable for kind='render' (false = true). That is round 2's C1/B-2
  -- ("nullable in prose, not null in the DDL, so pdf:* stayed unrepresentable") for the THIRD time,
  -- reintroduced as a SIDE EFFECT of round 4's own J2-1 fix. Shape #9, self-inflicted, again.
  --
  -- A surrogate key plus two PARTIAL uniques says what a PK cannot, and states the taxonomy exactly:
  --   paid  -> append-only, one row per (slot, generation); many coexist and are ranked.
  --   free  -> one row per slot, overwritable; a deterministic re-render has nothing to preserve.
  artifact_id   uuid not null default gen_random_uuid(),
  primary key (artifact_id),
  foreign key (workspace_id, video_id)
    references workspace_videos (workspace_id, video_id) on delete cascade,
  foreign key (workspace_id, video_id, generation_id, kind)
    references video_generations (workspace_id, video_id, generation_id, kind),
  -- Round 5 (Codex, M5): source_generation_id was pure documentation — no FK, so a model could claim
  -- provenance from a generation that does not exist, and the rung would score it merely "stale"
  -- rather than "impossible". MATCH SIMPLE disables this FK when the column is NULL, which is the
  -- wanted behaviour: a non-derived artifact has no source and must not be forced to invent one.
  foreign key (workspace_id, video_id, source_generation_id)
    references video_generations (workspace_id, video_id, generation_id),
  constraint art_slot_kind check (slot_kind(slot) is not null and kind = slot_kind(slot)),
  constraint art_paid_has_generation check
    ((kind in ('summary','model','dig','digDeeper')) = (generation_id is not null)),
  -- ⛔ `art_pending_is_leased`, `art_pending_has_token`, `art_pending_has_reserved_at` STOOD HERE
  -- (round 4 Codex #5, round 6 H5) AND ARE DELETED BY ADR-0007. All three were biconditionals on
  -- `state = 'pending'`: they existed only to describe a state that no longer exists, over columns
  -- that no longer exist. Nothing else read them.
  -- Round 5 H2: a summary is not derived from anything, so it must not carry a source — otherwise the
  -- source-currency rung ranks the summary against its own output and the two views disagree about
  -- which summary is current. Guards the DATA; the rung below separately guards the QUERY. Both,
  -- because they fail independently (service_role bypasses policies, not constraints).
  constraint art_summary_has_no_source check (kind <> 'summary' or source_generation_id is null),
  -- Round 5 H6: §6.2 calls persisting the span "cheap now, IMPOSSIBLE to retrofit after the first
  -- sweep runs" — and then declared both columns nullable with nothing requiring them. MEASURED: a
  -- dig:120 row accepted with both NULL. The only finding this round whose cost is irreversible: the
  -- span is recoverable only from a summary.md that §8 is entitled to collect.
  constraint art_dig_has_span check
    (kind <> 'dig' or (start_sec is not null and end_sec is not null and end_sec > start_sec)),
  -- ⟳ ROUND 6 B3 / Codex B1 — ONLY A DIG MAY BE DETACHED. Detachment means "this artifact no longer
  -- maps to a section of the summary", and only `dig:<sectionId>` is section-scoped. VERIFIED against
  -- the producers, because the NAMES mislead: `digDeeper` is not a section-scoped dig, it is the
  -- PER-VIDEO document that presents them (`companion-doc.ts:4` "maintains a per-video
  -- <basename>-dig-deeper.md that accumulates dug sections"; cloud has no such blob at all and
  -- assembles it at serve time, `app/api/html/[id]/route.ts:46-62`). It was never attached to one
  -- section, so it cannot be detached from one. Round 2 already got this backwards once by reasoning
  -- from the slot name and forcing digDeeper to kind='summary' (§5.1's table).
  --
  -- This is a material implication — `detached → dig`, written `¬detached ∨ dig` because SQL has no
  -- implication operator. It never constrains a dig: a dig may be recorded or detached.
  --
  -- It matters as a CHECK and not only as a trigger rule because the append-only trigger is
  -- `before update or delete` — an INSERT written straight to state='detached' fires NO trigger.
  -- A constraint governs STATES, a trigger governs TRANSITIONS, and the design needs both. Both
  -- columns are NOT NULL, which is load-bearing: a CHECK admits a row whose predicate is NULL, so a
  -- nullable `kind` would make this enforce nothing for exactly the malformed rows it targets.
  constraint art_detached_is_dig check (state <> 'detached' or kind = 'dig'),
  -- The retention clock exists exactly while the row is detached. Stated as an equivalence, not as
  -- "detached implies a timestamp", so a stale detached_at cannot survive a re-attachment.
  constraint art_detached_has_timestamp check ((state = 'detached') = (detached_at is not null)),
  -- Round 5 (Codex): nothing tied blob_key to the tuple, so a row could rank gNEW's card while
  -- serving gOLD's bytes — shape #4 on the paid path, and invisible to every other constraint.
  --
  -- ⟳ ROUND 6 H2/Codex H4 — the LIKE version was a pattern match, not a comparison, and MEASURED
  -- three bypasses: a generation id containing `_` matched any character, an id of `%` matched
  -- ANY key at all, and the id was accepted anywhere in the path (`OTHERWS/videos/gDIG/gOLD/…`
  -- passed for generation gDIG). §4.1 leaves the id FORM open and two of its three candidates can
  -- contain `_`, so this could not be fixed by assuming well-formed ids.
  --
  -- Exact segment equality: no metacharacters, and POSITION is constrained, which the anchored-LIKE
  -- alternative still would not have done. Text-to-text throughout — never cast a path segment
  -- (round 1: a policy that RAISES fails the whole query rather than denying one row).
  -- ⟳ ROUND 9 H5 — SPLIT IN TWO, because the WHOLE thing was gated on `generation_id is not null`
  -- and free rows are exactly the ones with a null generation. MEASURED: a `render` row in workspace
  -- A stored `<workspace-B>/videos/vidH5/OTHER-TENANT.pdf` and was ACCEPTED.
  -- Tenant confinement is not a property of paid rows; it is a property of every row, and it was
  -- written inside the constraint that legitimately only applies to paid ones. Shape #10 — the same
  -- one-site habit as the free-render reconciler (round 8 C1) and the free short-circuit (H2), on
  -- the third face of the same free/paid split.
  constraint art_key_names_workspace check (
        split_part(blob_key, '/', 1) = workspace_id::text
    and split_part(blob_key, '/', 2) = 'videos'
    and split_part(blob_key, '/', 3) = video_id),
  -- The generation segment is the part that genuinely only exists for paid rows.
  constraint art_key_names_generation check (
    generation_id is null or split_part(blob_key, '/', 4) = generation_id)
);
create unique index video_artifacts_paid_uq on video_artifacts
  (workspace_id, video_id, slot, generation_id) where generation_id is not null;
create unique index video_artifacts_free_uq on video_artifacts
  (workspace_id, video_id, slot)               where generation_id is null;

-- ⛔ `video_artifacts_inflight_uq` STOOD HERE — "at most one in-flight reservation per slot", the
-- money guard MEASURED independently by all three round-5 reviewers. ADR-0007 DELETES IT, and the
-- reason is that the ADR's load-bearing claim is TRUE and NOT SUFFICIENT, so the two halves must be
-- separated rather than conflated:
--
--   * As a WRITE guard it is dissolved. It had a partial predicate `where state = 'pending'`, and
--     there are no pending rows. Nothing to enforce.
--   * As a MONEY guard it had one live consumer, and that consumer is NOT dissolved. Round 13
--     MEASURED that this index is the only thing stopping two paid `model` producers today: one
--     video in N playlists holds N independent `serve_model_charge` leases against ONE model slot,
--     because `doc_key` carries the playlist (`0020_reservation_release.sql:213`) and the artifact
--     slot does not. Drop the index without re-keying `doc_key` to `(workspace_id, video_id)` and
--     `paid_model_rows_in_one_slot` goes 1 -> 2.
--
-- ⚠ THE RE-KEY IS NOT IN THIS FILE AND NOT IN THIS SLICE. It touches `0012:53`, `0014:47`,
-- `0020:213`, a data migration with a `least(sum(attempt_count), max_serve_attempts - 1)` clamp
-- applied ONLY where a merge occurs, and `tests/integration/serve-doc-materialize.test.ts:78`.
-- SHIPPING THIS DELETION WITHOUT THE RE-KEY IS A MONEY REGRESSION, NOT A SIMPLIFICATION.
-- See docs/adr/0007 — "The coupling that makes the deletion safe".

-- ⛔ `reserve_artifact_slot` AND `renew_artifact_lease` STOOD HERE (round 6 H5 / Codex B2, rounds
-- 7-12) AND ARE DELETED BY ADR-0007. Between them they were ~240 lines implementing reclaim,
-- a per-kind attempt bound from `guardrail_config`, a token-fenced renewal with a `max_duration_seconds`
-- ceiling, and four typed outcomes (`reserved`, `busy`, `exhausted`, `already_recorded`).
--
-- THE REASON IS NOT THAT ANY ONE OF THEM WAS WRONG. Six consecutive adversarial rounds produced a
-- Blocking or High in this protocol, four of them introduced by the previous round's own fix, while
-- every other component of the same spec converged and stayed converged. The failures were not
-- independent: the fence had to be PERMISSIVE so a reclaimed writer could still record work it had
-- already paid for, and STRICT so a stranger could not complete a generation. Those are two
-- coordination philosophies — append-only-plus-merge, and mutual exclusion — wired to one SQL
-- predicate. Five successive credentials did not resolve it because no credential can.
--
-- The dissolution: writers do not contend. A producer writes a NEW generation, a replicator copies an
-- EXISTING one (`lib/cloud-sync/sync-run.ts:372-394` — `transferClassA` makes no Gemini call and mints
-- no id), and the address is derived from the generation id, so their writes land on different keys
-- and append different rows. `video_artifacts_paid_uq` ranks them; it never rejects them.
--
-- ⚠ WHAT THIS DELETION DOES *NOT* CARRY, stated here because it is the money half and it is the part
-- a reader of this file would otherwise assume was handled:
--   * THE PER-KIND ATTEMPT CEILING GOES WITH NO SUCCESSOR. This function bounded attempts per kind
--     from `guardrail_config` — `summary_max_attempts` = 1 (a deliberate product decision, documented
--     as such), `dig_max_attempts`, `max_serve_attempts` = 5. `jobs.max_attempts` defaults to 5
--     (`0008_jobs_queue.sql:14`). Deleting the artifact-layer bound silently promotes a summary from
--     1 paid attempt to 5. WHICH NUMBER WINS IS AN OPEN DECISION, not something this file settles.
--   * THE CRASH-BEFORE-RECORDING GUARANTEE INVERTS. §5.1's rule 19 bought "a crash before recording
--     leaves nothing — no bytes, no row, no orphan — so spending again is correct rather than a
--     double-charge", and it bought it by putting a `pending` row down FIRST. With `pending` gone the
--     row cannot precede the bytes, so a crash after the blob write leaves paid bytes at a
--     generation-derived key no later attempt can name, and the next attempt spends again. §8's
--     grace period on orphan BLOBS is the specified — and UNIMPLEMENTED — mechanism for that.
--
-- Both are recorded in docs/adr/0007 under Consequences; neither is closed by this file.
-- THE APPEND — and it never refuses a writer its own paid work. ADR-0007 deleted the reservation, so
-- there is no holder, no token, no fence and no in-place flip: `record_artifact` INSERTs the
-- generation and INSERTs (or idempotently re-states) the artifact row that FKs it, in one
-- transaction. The FK forces that order.
--
-- ⟳ ADR-0007 / ROUND 17 B1 — THIS FUNCTION IS NOW THE ONLY PRODUCTION WRITER OF `video_generations`.
-- `reserve_artifact_slot` used to insert a `pending` row before the paid call and was the only
-- non-fixture INSERT into that table; every other one in the repo is a fixture in 05_assert.sql.
-- MEASURED with the reservation deleted and this INSERT not yet written: every paid record raised
--   [P0001] cannot mark summary as recorded — generation gG1 is <absent>
--
-- ⟳ ROUND 6 B5 / Codex B3 — THE PAYLOAD, which item 4 deliberately left unspecified. `md_hash` was
-- mandatory (gen_summary_has_hash) and had NO PRODUCER; the card and doc_version_major had the same
-- gap. All three arrive here, and the generation is written IN THE SAME TRANSACTION as the artifact,
-- so there is no instant at which a recorded artifact points at an incomplete generation.
--
-- ⚠ THE GENERATION IS WRITTEN FIRST, AND THE ORDER IS LOAD-BEARING, not stylistic:
-- `video_artifacts_generation_complete` (below) rejects a recorded artifact whose generation is not
-- complete, and with the GC floor's `state` predicate on its way out it is the ONLY guard left
-- between a record and a missing generation. The API and the guard agree rather than one covering
-- for the other, which is cross-derivation C3's rule applied to a protocol.
--
-- `p_produced_at` is a PARAMETER with a now() fallback, never a bare now(). Sync replicates a local
-- generation and must carry its ORIGINAL production time — a receiver stamping its own clock is item
-- 1's detached_at defect exactly, and round 4's J2-3 forbids a clock read anywhere the ranking reads.
-- The fallback is reached only by a fresh cloud summarize, where production time genuinely is now.
--
-- ⚠ `p_token uuid` WAS PARAMETER 7 AND IS DELETED WITH THE MECHANISM IT CREDENTIALLED. Keeping it
-- would leave a `security definer` function advertising a credential it does not check — a fence in
-- the signature and none in the body, which is strictly worse than either having one or not. Round
-- 12's B1 is the measured cost of a token that is handed out and not honoured; a token that is
-- accepted and never read is the same defect with the sign flipped.
create function record_artifact(
  p_ws uuid, p_video text, p_slot text, p_generation_id text, p_kind artifact_kind, p_blob_key text,
  p_source_generation_id text default null,
  p_start_sec int default null, p_end_sec int default null,
  p_md_hash text default null, p_card jsonb default null,
  p_doc_version_major int default null, p_produced_at timestamptz default null)
  returns text language plpgsql security definer set search_path = '' as $$
declare v_existed boolean; v_start int; v_end int; v_src text;
        v_made_gen boolean := false; v_gen_state text; v_gen_hash text;
begin
  -- ⟳ ROUND 8 (guard classification, C1) — THE FREE PATH, which did not exist.
  -- `video_artifacts_free_uq` is a SEQUENCE guard ("a render for this slot already exists") and it
  -- had no reconciler at all: one INSERT statement takes ONE conflict arbiter, and this function's
  -- was the PAID partial index (`where generation_id is not null`), which a NULL generation can
  -- never match. MEASURED: the first render of a slot succeeded and every RE-render failed with a
  -- raw [23505] — against a comment three screens up promising free renders are "overwritable".
  --
  -- Free is genuinely different and the branch is not duplication: there is no generation to write,
  -- and the ADDRESS IS MUTABLE — the append-only trigger skips rows with a null generation_id by
  -- design, so overwriting blob_key here is legal where it would be shape #3 on a paid row.
  -- ⚠ THE COMMENT LIVES ABOVE THE STATEMENT, NOT INSIDE IT. Placed between `on conflict` and
  -- `do update` it split the clause, and a mutation that removes conflict handling then orphaned
  -- the `on conflict` line: `syntax error at end of input`, reported as an untested guard. That is
  -- the "an anchor spanning prose breaks whenever someone explains themselves" lesson, committed
  -- again in the round that recorded it.
  if p_generation_id is null then
    insert into public.video_artifacts
      (workspace_id, video_id, slot, generation_id, kind, state, blob_key)
    values (p_ws, p_video, p_slot, null, p_kind, 'recorded', p_blob_key)
    on conflict (workspace_id, video_id, slot) where generation_id is null
    do update set blob_key = excluded.blob_key, state = 'recorded';
    return 'recorded_free';
  end if;

  -- ⟳ ADR-0007 / ROUND 17 B1 — THE GENERATION IS BORN COMPLETE, AT RECORD TIME, AFTER THE PAID CALL.
  -- There is no longer any moment at which a contentless generation row is legal for a summary:
  -- `state` defaults to 'complete' and — ⟳ T4 — its CHECK now admits nothing else, so the five
  -- completeness CHECKs in 03 bind UNCONDITIONALLY (their `state <> 'complete' or` disjunct became
  -- constantly false and was deleted with it). That is exactly why the row
  -- cannot be created BEFORE the Gemini call — 03's own comment records both doors being locked:
  -- reserving with no generation row raised [23503] on the artifact's FK, and creating the row from
  -- what is knowable pre-call raised [23514] gen_card_complete. `state = 'pending'` was the key cut
  -- for that lock; ADR-0007 throws the key away, so the row simply moves to the far side of the call.
  --
  -- ⚠ THE EXISTENCE READ COMES FIRST, AND IT IS NOT AN OPTIMISATION — MEASURED WHILE WRITING T1.
  -- The first version of this fix went straight to the INSERT and decided everything from `found`.
  -- It failed R11-1 with a RAW [23514] gen_card_complete, because **a CHECK constraint is evaluated
  -- on the PROPOSED TUPLE BEFORE conflict resolution** — the same physical rule this file already
  -- records two screens down for `art_dig_has_span`, hit again in the fix written beside it. A
  -- second writer for an already-complete generation legitimately carries only the values it is
  -- claiming (a hash, say) and no card, so its tuple cannot stand alone; under the old protocol that
  -- was fine because the write was an UPDATE with `coalesce`, and an UPDATE has no proposed tuple to
  -- reject. Turning the write into an INSERT turned a typed `completed_by_another` into a raw
  -- SQLSTATE on the money path — shape #8, introduced by ADR-0007's own prescription.
  --
  -- So: read, then decide, then write only if there is nothing there.
  --   * the row exists and its hash DIFFERS from ours  -> `completed_by_another`, no INSERT attempted
  --   * the row exists and agrees (or we claim nothing) -> fall through to the append, no INSERT
  --   * the row is absent                               -> INSERT it, born complete
  --
  -- ⚠ ON CONFLICT DO NOTHING STAYS, and it is now doing the ONE job it is good at: absorbing a
  -- genuinely concurrent second INSERT between our read and our write. `found` after it is false
  -- exactly when a peer won that race, and we re-read to answer with what the peer wrote rather than
  -- with what we assumed. Nothing here can overwrite a generation somebody else completed — 03's
  -- freeze trigger would refuse it anyway.
  --   ⚠ RESIDUAL, NAMED RATHER THAN HIDDEN: in that race a loser whose own tuple is incomplete still
  --   meets the CHECK before the conflict is seen, and still gets a raw 23514. The window is between
  --   the read and the INSERT of the same statement pair, and a caller in it is claiming to hold paid
  --   summary bytes while presenting no card — a caller bug either way. It is bounded, it is not
  --   zero, and it is the honest state of "a typed outcome per path".
  --
  -- ⚠ ONLY `summary` IS FORCED INTO THIS ORDER BY THE CONSTRAINTS. MEASURED (round 17 T1): a
  -- `model`, `dig` or `digDeeper` row inserted with only `produced_at` is ACCEPTED, because three of
  -- the four completeness CHECKs are additionally gated `kind <> 'summary'`. So "no generation row
  -- exists before its paid call completes" is a CARRIED INVARIANT for those three kinds, not a
  -- derived one — see T4. `model` is the sharp case: no job, no staging, its own serve lease.
  select g.state, g.md_hash into v_gen_state, v_gen_hash
    from public.video_generations g
   where g.workspace_id = p_ws and g.video_id = p_video and g.generation_id = p_generation_id;
  if not found then
    insert into public.video_generations
      (workspace_id, video_id, generation_id, kind, state,
       card, md_hash, doc_version_major, produced_at)
    values (p_ws, p_video, p_generation_id, p_kind, 'complete',
            p_card, p_md_hash, p_doc_version_major, coalesce(p_produced_at, now()))
    on conflict (workspace_id, video_id, generation_id) do nothing;
    v_made_gen := found;
    if not v_made_gen then
      select g.state, g.md_hash into v_gen_state, v_gen_hash
        from public.video_generations g
       where g.workspace_id = p_ws and g.video_id = p_video and g.generation_id = p_generation_id;
    end if;
  end if;

  -- ⟳ ROUND 11 (round 10 B1, second half) — DO NOT REPORT SUCCESS WHEN ANOTHER WRITER'S CONTENT
  -- STANDS. MEASURED, with NO attacker, just two writers:
  --   W1 completes -> recorded ; md_hash SHA_W1
  --   W2 records its REAL work -> a SUCCESS string, while the manifest still claims SHA_W1
  -- Shape #4 and shape #5 together, on the SUCCESS path, on the money path.
  -- Only when the content actually DIFFERS: an idempotent retry presenting the same hash is a
  -- benign second call and must still fall through to the append.
  if not v_made_gen and v_gen_state = 'complete'
     and p_md_hash is not null and v_gen_hash is distinct from p_md_hash then
    return 'completed_by_another';
  end if;

  -- ⟳ ROUND 9 (round 8 Claude H3) — A DIVERGENT ADDRESS IS REFUSED, NOT SILENTLY DROPPED.
  -- The append path's `do update` does not assign blob_key; only the fresh INSERT uses it. MEASURED:
  -- a caller recording with a DIFFERENT key was told success, and the manifest kept pointing at the
  -- first key. The bytes are at one address and the row names another — shape #4, silent, on the
  -- success path, in the spec whose entire subject is the address.
  -- `art_key_names_generation` cannot catch it: both keys agree on all four constrained segments.
  --
  -- Raising rather than assigning, and the choice is forced. Assigning would make a recorded address
  -- MUTABLE, which is shape #3 and the defect this whole design exists to remove. Keeping one of two
  -- divergent addresses silently is the only option that cannot be right. So it is a caller bug — a
  -- SHAPE violation, where rejecting is correct.
  if exists (select 1 from public.video_artifacts
              where workspace_id = p_ws and video_id = p_video and slot = p_slot
                and generation_id = p_generation_id and blob_key is distinct from p_blob_key) then
    raise exception 'video_artifacts: % names blob_key %, but this slot already holds % — an address may not be rewritten',
      p_generation_id, p_blob_key,
      (select blob_key from public.video_artifacts
        where workspace_id = p_ws and video_id = p_video and slot = p_slot
          and generation_id = p_generation_id);
  end if;

  -- ⟳ ROUND 7 B1 — THE APPEND IS IDEMPOTENT, NOT BLIND, and this is the finding that mattered most.
  -- It used to INSERT unconditionally, and `video_artifacts_paid_uq` has no state predicate — so a
  -- worker retrying its own record collided with its own row:
  --   [23505] duplicate key value violates unique constraint "video_artifacts_paid_uq"
  -- The design says this function "never refuses"; measured, it threw the paid work away anyway,
  -- just via a raw SQLSTATE instead of a typed refusal — shape #8.
  --
  -- ⚠ THE SPAN IS RESOLVED BEFORE THE INSERT, NOT INSIDE THE `do update`, and the difference is a
  -- physical rule worth the sweep list: **a CHECK constraint is evaluated on the proposed tuple
  -- BEFORE conflict resolution.** MEASURED — with the coalesce only in the DO UPDATE, a caller that
  -- omitted the span got `[23514] art_dig_has_span` from the VALUES clause and the ON CONFLICT never
  -- ran. `excluded.*` is the tuple that already had to be legal; it cannot be used to repair itself.
  select exists (select 1 from public.video_artifacts
                  where workspace_id = p_ws and video_id = p_video and slot = p_slot
                    and generation_id = p_generation_id) into v_existed;

  -- ⚠ THE SPAN IS RECOVERED FROM THE SLOT; PROVENANCE ONLY FROM THE SAME GENERATION. The distinction
  -- is real rather than a workaround:
  --   start_sec/end_sec describe the SECTION the slot names — `dig:8` is seconds 8..88 in every
  --     generation of it — so borrowing across generations is not just safe, it is the definition.
  --   source_generation_id is PROVENANCE — which summary generation this artifact was built FROM —
  --     and two generations of one slot can legitimately differ. Borrowing it across generations
  --     would manufacture a provenance claim, which is shape #4 in the ranking input round 6's
  --     Codex H5 froze precisely to stop a row rewriting its own.
  -- ⟳ ADR-0007: the ordering term `state = 'pending' desc` is gone with the state; the surviving
  -- term prefers this generation's own row and otherwise takes any sibling row of the same slot.
  select start_sec, end_sec into v_start, v_end
    from public.video_artifacts
   where workspace_id = p_ws and video_id = p_video and slot = p_slot
   order by (generation_id = p_generation_id) desc nulls last
   limit 1;

  select source_generation_id into v_src
    from public.video_artifacts
   where workspace_id = p_ws and video_id = p_video and slot = p_slot
     and generation_id = p_generation_id;

  insert into public.video_artifacts
    (workspace_id, video_id, slot, generation_id, kind, state, blob_key,
     source_generation_id, start_sec, end_sec)
  values (p_ws, p_video, p_slot, p_generation_id, p_kind, 'recorded', p_blob_key,
          coalesce(p_source_generation_id, v_src),
          coalesce(p_start_sec, v_start), coalesce(p_end_sec, v_end))
  on conflict (workspace_id, video_id, slot, generation_id) where generation_id is not null
  do update set
       state                = 'recorded',
       source_generation_id = excluded.source_generation_id,
       start_sec            = excluded.start_sec,
       end_sec              = excluded.end_sec;
  -- A typed outcome per path, never a constraint name for the caller to parse.
  -- ⟳ ADR-0007 RENAMED BOTH. They were `recorded_after_token_loss` and `recorded_after_loss` — two
  -- names describing which half of a reservation the caller had lost. There is no reservation and
  -- nothing to lose, so the surviving distinction is the only one left: had this (slot, generation)
  -- already been written? `already_recorded` is the name 03's freeze-trigger comment was already
  -- using for the crash-retry path, so the schema now says one thing in two places instead of two.
  return case when v_existed then 'already_recorded' else 'recorded' end;
end $$;

-- ⚠ ROUND 6 B1 — MEASURED: `anon`, with no JWT at all, called the previous reclaim and DELETED
-- tenant-1's in-flight reservation. `security definer` means RLS is never consulted, so the GRANT is
-- the entire authorization story — and the default is PUBLIC EXECUTE. This repo revokes PUBLIC on
-- every other definer function it ships (0004:10, 0005:25, 0010:21, 0011:137); the one added as round
-- 5's H4 fix, one file away, was not swept. Sweeping all THREE replacements here, not just the one
-- that inherited the name — that one-site habit is what produced B1 in the first place.
-- ⛔ The grants for `reserve_artifact_slot` and `renew_artifact_lease` went with the functions.
-- ⚠ AND THE SWEEP RULE SURVIVES THEM, which is the point of leaving this note: the habit that
-- produced B1 was applying a revoke at ONE site. Three definer functions became one; the assertion
-- over `pg_proc` in 05 (R8) is what makes "all of them" checkable rather than remembered.
revoke all on function record_artifact(uuid, text, text, text, artifact_kind, text, text, int, int,
                                      text, jsonb, int, timestamptz)
  from public, anon, authenticated;
grant execute on function record_artifact(uuid, text, text, text, artifact_kind, text, text, int, int,
                                          text, jsonb, int, timestamptz)
  to service_role;
revoke all on function slot_kind(text) from public, anon, authenticated;
-- ⟳ ROUND 7 M1 — THE TWO THE SWEEP MISSED, in the file whose comment above claims it swept all of
-- them. MEASURED via pg_proc: `video_artifacts_append_only` and `forbid_collecting_current` were
-- still carrying the default PUBLIC EXECUTE, and `has_function_privilege('anon', …)` returned `t`.
-- Exploitability is near zero — Postgres itself refuses a direct call with
-- `[0A000] trigger functions can only be called as triggers` — and that is exactly why it survived:
-- nothing observable was wrong. What was wrong was the CLAIM OF COMPLETENESS, and this sweep is the
-- only thing standing between this design and round 6's B1 (an unswept definer function through
-- which `anon` deleted another tenant's reservation). Asserted over pg_proc in 05 (R8), so the next
-- definer function added here is caught by the suite instead of by the next reviewer.
-- Their revokes sit beside their own definitions further down — they cannot be hoisted here, because
-- a REVOKE on a function that does not exist yet is an error, and both are declared below.

alter table video_artifacts enable row level security;
alter table video_artifacts force row level security;
-- ⚠ ROUND 6 H4 — REVOKE FIRST. MEASURED: `anon` TRUNCATEd this table to 0 rows.
-- `pg_default_acl` carries `anon=Dxtm/postgres` for every table `postgres` creates in `public`
-- (D=TRUNCATE, x=REFERENCES, t=TRIGGER), so an explicit `grant select` is ADDITIVE and narrows
-- nothing. TRUNCATE fires neither RLS nor a ROW trigger — so it walks straight past both the policy
-- below and the append-only trigger, which is this design's central invariant.
-- The repo already knows this (`0011_cost_guardrails.sql:56` revokes); the new tables were not swept.
revoke all on video_artifacts from anon, authenticated;
grant select, insert, update, delete on video_artifacts to service_role;
grant select on video_artifacts to authenticated, anon;

-- Round 5 B2 — the table had `force row level security` and ZERO POLICIES, so the client grant above
-- was inert: authenticated/anon read nothing. That is safe but misleading, and it is half of why the
-- view leak below was reachable. The client-readable surface is stated explicitly, SELECT only, with
-- writes still service_role-only through an RPC (§5.1's share_tokens precedent).
create policy video_artifacts_owner_read on video_artifacts for select to authenticated
  using (workspace_id in (select id from workspaces where owner_id = (select auth.uid())));

-- `current` — derived, ranked, with a FLOOR. Round 4 J2-4 / A-2:
--   servable  = state 'recorded'. That is the WHOLE test; it cannot empty a non-empty set.
--   preferred = the ranking below. Staleness RANKS, it never GATES.
-- Every rung is a recorded fact carried as DATA (produced_at, not now()) so the result is a
-- deterministic function of the generation set — round 4 J2-3.
--
-- The generation join is a LEFT join, and that is load-bearing rather than defensive. A free render
-- HAS no generation, so an inner join silently erased every `pdf:*` and `html` artifact from
-- `current` — the same class the PK erased, in the same object, by a second mechanism. Both had to
-- be true for a free render to survive, and neither was.
-- `not g.body_collected` had to move inside coalesce for the same reason: NULL is not false, and a
-- WHERE clause drops NULL. An "is it collected?" test that answers NULL for an artifact that can
-- never be collected is absent-vs-failed, shape #1, in a filter.
-- Two views, because the SUMMARY ranking is an input to the ranking of everything derived from it,
-- and a view cannot reference itself. Round 4 J2-4.
-- ⚠ `security_invoker = true` ON BOTH VIEWS IS A SECURITY CONTROL, NOT A STYLE CHOICE.
-- Round 5 B2, MEASURED. A Postgres view runs with the VIEW OWNER's privileges by default, so it
-- bypasses RLS on its base tables. Neither view had it, and neither had a grant — so the first thing
-- any maintainer does is hit `permission denied for view video_artifacts_current` (the serve path
-- cannot read the object the design resolves `current` from) and add the obvious grant. That grant,
-- on a view without security_invoker, hands every authenticated user every tenant's manifest:
--
--   rows visible via the RAW table (RLS enforced)      | 0
--   rows visible via the VIEW (security_invoker unset) | 2      <- two other tenants
--   other tenants' blob_keys leaked through the view   | secret-000651f8-…, secret-00071506-…
--
-- The trap is that the *missing* grant is what makes the leak look like a fix. Shape #2 (identity as
-- grant) and shape #10 (RLS was derived for the tables and not re-derived for the views three files
-- later). service_role is unaffected either way — MEASURED `rolbypassrls = true`.
create view video_summary_current with (security_invoker = true) as
select distinct on (a.workspace_id, a.video_id) a.*
from video_artifacts a
join workspace_videos wv
  on  wv.workspace_id = a.workspace_id and wv.video_id = a.video_id
join video_generations g
  on  g.workspace_id = a.workspace_id and g.video_id = a.video_id
  and g.generation_id = a.generation_id
where a.slot = 'summary' and a.state = 'recorded' and not g.body_collected
order by a.workspace_id, a.video_id,
         -- ⟳ ROUND 6 B4: plain `=`, not `is not distinct from`. Both sides are now NOT NULL — the
         -- column by DDL, the card by gen_card_complete — so the null-tolerant comparison bought
         -- nothing and actively hid the defect: it returned TRUE for two NULLs, which read as
         -- "corrections-current" for every row the migration had failed to backfill.
         --
         -- ⚠ THIS LINE CARRIES NO GUARD OF ITS OWN, and the mutation harness says so out loud
         -- (`mutate-schema.py`, the one entry expected to come back GREEN). While NOT NULL holds,
         -- `=` and `is not distinct from` are behaviourally identical, so reverting this line
         -- changes nothing and no assertion can go red. The protection lives ENTIRELY in the NOT
         -- NULL; this is a clarification riding on it. Recorded rather than quietly asserted,
         -- because "we tightened the comparison" reads like a fix and is not one — if the NOT NULL
         -- is ever relaxed, this line silently stops being equivalent and B4 returns.
         (g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,
         g.doc_version_major desc nulls last,
         -- Round 5 B3: rank the CARD's mdGeneratedAt, not produced_at. reconcileClassA:49 ranks
         -- mdGeneratedAt; this ranked produced_at; MEASURED opposite winners on the same pair, which
         -- is the oscillation §5.3 claimed round 3 had eliminated. An ISO-8601 string compares
         -- lexicographically, which is exactly what reconcile-class-a.ts's `newer()` does.
         -- It also keeps J2-3's property: the card is recorded DATA, not a clock read.
         (g.card ->> 'mdGeneratedAt') desc nulls last,
         g.produced_at desc nulls last,
         a.generation_id desc;

create view video_artifacts_current with (security_invoker = true) as
select distinct on (a.workspace_id, a.video_id, a.slot) a.*
from video_artifacts a
join workspace_videos wv
  on  wv.workspace_id = a.workspace_id and wv.video_id = a.video_id
left join video_generations g
  on  g.workspace_id = a.workspace_id and g.video_id = a.video_id
  and g.generation_id = a.generation_id
left join video_summary_current s
  on  s.workspace_id = a.workspace_id and s.video_id = a.video_id
where a.state = 'recorded' and not coalesce(g.body_collected, false)
order by a.workspace_id, a.video_id, a.slot,
         -- Round 4 J2-4: source-currency RANKS. It must never GATE — a paid model whose source
         -- summary was regenerated still serves (stale, flagged), because the alternative is an
         -- empty magazine view until someone pays for a new model. Rule 14, applied at the second
         -- site: the round-3 fix demoted corrections from filter to rank and left this sibling
         -- three lines away still filtering.
         -- Round 5 H2: `a.slot <> 'summary'` guards the QUERY. Without it the summary is ranked
         -- against its own output, and the two views MEASURED opposite winners — so the summary the
         -- user is SERVED was not the summary every derived artifact is RANKED AGAINST. That is §6's
         -- "sharpest constraint" (cross-generation mixing) violated by the view pair added to enforce
         -- ranking. art_summary_has_no_source guards the DATA; cross-derivation C3 says take both.
         (a.slot = 'summary'
          or a.source_generation_id is null
          or a.source_generation_id is not distinct from s.generation_id) desc,
         (g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,   -- ⟳ round 6 B4; see above
         g.doc_version_major desc nulls last,
         (g.card ->> 'mdGeneratedAt') desc nulls last,   -- round 5 B3; see video_summary_current
         g.produced_at desc nulls last,
         a.generation_id desc nulls last;

revoke all on video_summary_current, video_artifacts_current from anon, authenticated;
grant select on video_summary_current, video_artifacts_current
  to authenticated, anon, service_role;

-- GC MAY NOT COLLECT THE CURRENT GENERATION. Round 5 H3: §5.1.1's floor claimed `state='recorded'`
-- and `not body_collected` together "cannot empty a non-empty set" — and the second conjunct empties
-- it. MEASURED: the summary slot went 2 rows -> 0 when both generations were collected, which is
-- round 3's A-2 failure ("the summary vanishes from the page") reached through GC instead of through
-- corrections. §8 never mentioned body_collected and stated no rule protecting the current row.
--
-- Enforced here rather than written in §8, because "the sweeper must remember to check" is exactly
-- the kind of rule that holds until the day it doesn't, on the one path with no undo.
create function forbid_collecting_current() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  if new.body_collected and not old.body_collected
     and exists (select 1 from public.video_artifacts_current c
                  where c.workspace_id = new.workspace_id and c.video_id = new.video_id
                    and c.generation_id = new.generation_id)
  then
    raise exception 'refusing to collect generation % — it is CURRENT for video %',
      new.generation_id, new.video_id;
  end if;
  return new;
end $$;
revoke all on function forbid_collecting_current() from public, anon, authenticated;   -- ⟳ round 7 M1
create trigger forbid_collecting_current_trg
  before update on video_generations
  for each row execute function forbid_collecting_current();

-- ⟳ ROUND 8 (guard classification, C3) — THE SWEEPER'S PREDICATE, because the trigger above is a
-- SEQUENCE guard that was expressed as an exception.
--
-- It is correct in intent — never collect the current generation — and as a raise it converted
-- "skip this row" into "lose the whole sweep": MEASURED, a batch `update … set body_collected = true`
-- died on the first current generation and rolled back every other row in the statement.
-- And retrying could not help, because a current generation is PERMANENTLY current — so §8's
-- retention sweep could never succeed at all. A guard that makes its own purpose unreachable.
--
-- The fix is not to weaken the trigger. Silently suppressing the change would be worse: the caller
-- would believe it collected bytes it did not (shape #5, silent failure on a best-effort path, on
-- the one path with no undo). Instead the currency test becomes something the sweeper SELECTS
-- THROUGH, and the trigger stays as a backstop for anything writing directly. Cross-derivation C3's
-- rule — take both the data guard and the query guard — applied to GC.
--
-- Deliberately scoped to CURRENCY only. §8's age predicate (90 days since the row stopped being
-- current, or since detached_at) belongs to the sweeper, because it is a tunable retention
-- heuristic and this view is a correctness floor. Mixing them would bury a knob inside an invariant.
--
-- ⟳ ROUND 9 (round 8 M5) — SO READ THIS BEFORE WRITING A SWEEPER: a dig detached ONE SECOND ago
-- appears here (measured). That is correct under the 2026-08-06 retention decision only because the
-- 90-day clock lives in the sweeper, so a sweeper that forgets it deletes paid bytes the user can
-- still see. Stated here rather than in §8 because this view is what a future sweeper author will
-- read. The asymmetry that puts it there survives the deletion below: CURRENCY is correctness and
-- belongs in the floor; AGE is a tunable policy and does not.
--
-- ── ⛔ ADR-0007 (round 13 H1 → round 16 B1) — `and g.state = 'complete'` IS DELETED FROM THIS VIEW ──
-- It was ROUND 9's B1 fix, and it was RIGHT when it was written. Both round-8 reviewers found the
-- defect independently: this view had copied `video_artifacts_current`'s currency test faithfully
-- INCLUDING its blind spot — `current` requires `state = 'recorded'`, so an IN-FLIGHT reservation had
-- no current row and its generation was offered to the sweeper while the paid call was still running.
-- MEASURED end to end, no attacker and no second worker:
--   collectable WHILE IN FLIGHT: 1 ; sweep collected 1 ; holder records -> recorded_as_holder
--   gen complete, artifact recorded, and video_artifacts_current rows for that video: 0
-- Money spent, bytes queued for deletion, no error anywhere.
--
-- ⚠ IT IS REMOVED BECAUSE IT BECAME VACUOUS, NOT BECAUSE IT WAS WRONG. ADR-0007 deletes the `pending`
-- artifact state and `reserve_artifact_slot`, which was the only producer of a non-`complete`
-- generation; `state` is `not null default 'complete'` and nothing else writes it, so no REACHABLE
-- row can fail it. That is retrospective B6's shape — a guard that never starts — arriving by
-- SUBTRACTION, so it is deleted rather than left standing as decoration.
--
-- ⚠ "VACUOUS" MEANS UNREACHABLE, NOT UNUSED, AND THE DIFFERENCE IS MEASURABLE. Deleting it moved
-- 05's C3 sweep from 13 rows to 15: `gPEND` (G3) and `gG10` (G10) are pending generations the
-- assertions now build by DIRECT DML, precisely because no RPC can produce one. Both are collectable
-- now and neither can bury a byte — `video_artifacts_generation_complete` refuses to record or detach
-- an artifact against a non-complete generation, so a pending generation never has content to lose.
-- Left in place, this predicate would have kept scoring load-bearing against exactly those two
-- unreachable fixtures: the harness cannot tell "excludes rows" from "excludes rows a caller can
-- reach", and that is the reason to read it here rather than trust the mutation's colour.
--
-- ⚠ AND IT NEEDS NO SUCCESSOR — DO NOT ADD ONE. `record_artifact` creates the generation row AFTER
-- the paid call returns, so while that call runs there is no row for this view to return: round 9's
-- window is closed by subtraction, not covered by a replacement. Rounds 14-16 designed three covers
-- (a per-kind table, a `serve_model_charge` lease, a `video_generations.in_flight_until` marker) and
-- withdrew all three; round 16 measured that the marker had no row to be written to. What is NOT
-- closed is the BLOB — bytes are written before any row references them, and §8's grace period is the
-- specified, unimplemented mechanism for that orphan. It is not this view's job.
-- Its paired assertion (05_assert.sql, R9-3) and its named mutation in `mutate-schema.py`
-- ("B1: the collectable floor drops `state = complete`") are retired with it, not orphaned.
create view video_generations_collectable with (security_invoker = true) as
select g.*
  from video_generations g
 where not g.body_collected
   and not exists (select 1 from video_artifacts_current c
                    where c.workspace_id = g.workspace_id and c.video_id = g.video_id
                      and c.generation_id = g.generation_id);
revoke all on video_generations_collectable from anon, authenticated;
grant select on video_generations_collectable to service_role;

-- APPEND-ONLY, ENFORCED. Round 5 M1: the header comment and two others assert append-only, and the
-- table had no trigger, no rule, and `grant update, delete to service_role`. The partial unique stops
-- a DUPLICATE (slot, generation); it does nothing about `update … set blob_key = …` on a recorded
-- paid row — shape #3, a mutable value in an address, the exact defect this whole design exists to
-- remove — or a `delete` that orphans paid bytes, which is the serial-coherence defect (PR #42).
--
-- Scoped by cross-derivation C4, because a blanket immutability trigger breaks the design:
--   update/delete recorded paid: nothing needs it                -> REJECTED
--
-- ⟳ ADR-0007 — TWO PERMITTED TRANSITIONS ARE DELETED FROM THIS TRIGGER, AND THAT IS A FIX RATHER
-- THAN BOOKKEEPING. It used to read:
--   update pending -> recorded : rule 19's record-first order    -> PERMITTED
--   delete an expired pending  : C1's reclaim                    -> PERMITTED
-- Both were expressed as ONE clause — `if old.state in ('recorded','detached')` — so a row in any
-- other state fell straight through to `return new` with no immutability check at all. With
-- `pending` deleted those permissions are unreachable, and an unreachable PERMISSION inside the one
-- trigger that makes history immutable is a fail-open branch waiting for the state to be
-- reintroduced. The gate is now `old.generation_id is not null` alone: paid history, all of it.
-- Note the shape — this is a guard that would have gone quietly wider by SUBTRACTION, the mirror of
-- the "vacuously true predicate" the GC floor is being deleted for.
-- ⟳ SELF-INFLICTED, caught by cross-deriving this fix against §6.2 rather than by a reviewer:
-- a blanket "recorded paid rows are frozen" ALSO forbids §6.2's DETACH, which is an update of a
-- recorded dig row. The first version of this trigger made detaching a dig impossible.
--
-- And looking at why §6.2 needed an update at all dissolved the other half. §6.2 says a detached dig
-- moves to slot `dig:<sectionId>@<generationId>` — i.e. detaching REWRITES THE ADDRESS, which is
-- shape #3 in the section that exists to preserve paid content. That suffix was only ever a
-- workaround for the round-2 `primary key (workspace, video, slot)`, under which the detached row
-- would have collided with its replacement. Append-only keys on (slot, generation), so two dig rows
-- for one section coexist naturally and THE SLOT NEVER CHANGES.
--
-- So: recorded -> detached is a change of MEANING, permitted. Everything that is part of the
-- ADDRESS — slot, generation_id, blob_key — stays frozen, which is the actual invariant.
-- ⟳ ROUND 6 B3 + H1 (Claude), B1 + H5 (Codex) — MEASURED, and the gate was the whole defect.
-- The first version gated its entire body on `old.state = 'recorded'`, so a DETACHED row was
-- completely unprotected — and `recorded → detached` is the one transition this trigger deliberately
-- permits. Every protection could therefore be stepped around in two statements:
--
--   P1   detach -> DELETE                              -> the serial-coherence orphaning defect (PR #42)
--   P1b  detach -> rewrite blob_key -> re-record       -> shape #3, IN THE TRIGGER WRITTEN TO STOP IT
--
-- P1b is the one that survives the retention decision: it repoints a paid row at DIFFERENT BYTES
-- while its address column reads as untouched. Retention is irrelevant to it.
--
-- Two of the four measured bypasses are NOT fixed here, deliberately:
--   P10 (detach the current summary, then collect it, and the slot empties) is closed by
--       `art_detached_is_dig` — a summary can no longer be detached at all.
--   P9  (collecting a generation whose dig row is detached) is NOT A DEFECT. It was reported as one
--       because §6.2 promised a detached dig is "never deleted"; the user retired that rule on
--       2026-08-06 (see `detached_at`). GC clearing detached content is the intended behaviour, so
--       `forbid_collecting_current` is left alone and §6.2's prose is corrected instead.
--
-- Codex H5 is folded in here rather than taken separately, because it is the same sentence: the
-- frozen set was `slot, generation_id, blob_key` — the ADDRESS — and left `source_generation_id`,
-- `start_sec` and `end_sec` mutable. Those are not decoration: `source_generation_id` is a RANKING
-- input (the source-currency rung above), so a stale recorded model could rewrite its own provenance
-- to the current summary and win without regenerating a byte; and the span is the durable recovery
-- data §6.2 calls "impossible to retrofit". Immutability has to cover what the row CLAIMS, not only
-- where it points.
create function video_artifacts_append_only() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  if old.generation_id is not null then
    if tg_op = 'DELETE' then
      raise exception 'video_artifacts is append-only: cannot DELETE % paid row (slot %, gen %)',
        old.state, old.slot, old.generation_id;
    end if;
    if new.slot is distinct from old.slot
       or new.generation_id is distinct from old.generation_id
       or new.blob_key is distinct from old.blob_key then
      raise exception 'video_artifacts: the ADDRESS of a % paid row is immutable (slot %, gen %)',
        old.state, old.slot, old.generation_id;
    end if;
    if new.source_generation_id is distinct from old.source_generation_id
       or new.start_sec is distinct from old.start_sec
       or new.end_sec   is distinct from old.end_sec then
      raise exception 'video_artifacts: the PROVENANCE of a % paid row is immutable (slot %, gen %)',
        old.state, old.slot, old.generation_id;
    end if;
    -- ⟳ ADR-0007 — THIS BRANCH IS A REJECTION, NOT A PERMISSION, so it stays. It reads like a
    -- duplicate of the state CHECK now that the domain is exactly {recorded, detached}, and it is
    -- not: a BEFORE ROW trigger runs before constraints are evaluated, so this is what a paid row
    -- being moved to an unknown state hits FIRST, and it answers with a typed P0001 naming the row
    -- rather than a 23514 naming a constraint. Asserted in 05 against a state outside the domain.
    if new.state not in ('recorded','detached') then
      raise exception 'video_artifacts: a % paid row may only be recorded or detached, not %',
        old.state, new.state;
    end if;
    -- THE CLOCK IS SET HERE, NEVER BY THE WRITER — otherwise the party that benefits from postponing
    -- collection is the party that sets the collection deadline. A re-detach must not restart it, or
    -- a detach/re-attach cycle pins paid bytes forever, which §8 explicitly warns against
    -- ("fail toward collectable rather than toward pinned forever").
    if new.state = 'detached' then
      new.detached_at := case when old.state = 'detached' then old.detached_at else now() end;
    else
      new.detached_at := null;
    end if;
    -- `now()` is legitimate here and would NOT be in a ranking rung (round 4 J2-3 requires every rung
    -- to be recorded DATA so `current` is a deterministic function of the generation set). A retention
    -- deadline is wall-clock by nature; a ranking input is not. (The comparison used to be drawn with
    -- `lease_expires_at`, which ADR-0007 deleted — the rule never depended on it.)
  end if;
  return case tg_op when 'DELETE' then old else new end;
end $$;
revoke all on function video_artifacts_append_only() from public, anon, authenticated;  -- ⟳ round 7 M1
create trigger video_artifacts_append_only_trg
  before update or delete on video_artifacts
  for each row execute function video_artifacts_append_only();

-- ⟳ ROUND 6 B5 — THE OTHER HALF OF GATING 03'S FOUR CHECKS ON `state = 'complete'`.
-- Relaxing a constraint to "only while complete" is safe ONLY if something guarantees that everything
-- observable has reached complete. Without this trigger, `gen_card_complete`, `gen_summary_has_hash`,
-- `gen_summary_has_format` and `gen_major_matches_card` all became optional for any writer willing to
-- leave its generation `pending` — the relaxation would be a bypass wearing a lifecycle's clothes.
--
-- With it, every row either ranking view can reach has satisfied all four IN FULL, because both views
-- filter `a.state = 'recorded'`. That is why the views needed no change at all.
--
-- ⟳ T4 — THE RELAXATION IS GONE, AND THIS TRIGGER IS NOT, WHICH IS THE INTERESTING PART. Narrowing
-- `video_generations.state` to a single value made those four CHECKs unconditional again, so the
-- bypass this trigger was written to close cannot be opened by a `pending` generation any more.
-- What it still catches is the OTHER branch of its own test, and that branch is the one T1 measured:
-- a recorded artifact naming a generation that is `<absent>`. `record_artifact` writes the generation
-- first precisely so this never fires on the happy path — the API and the guard agree rather than one
-- covering for the other (cross-derivation C3). Deleting it because "state can only be complete now"
-- would delete the absent-parent check with it and leave a raw [23503] in place of a typed P0001.
--
-- ⚠ `before insert OR UPDATE`, and the INSERT half is not symmetry. `record_artifact`'s
-- append-after-loss path INSERTS a recorded row directly, and 04's append-only trigger is
-- `before update or delete` — so an INSERT is exactly the path that reaches no other guard. Item 1
-- learned this the hard way at `art_detached_is_dig`: a constraint governs STATES, a trigger governs
-- TRANSITIONS, and an INSERT is a state with no transition.
create function video_artifacts_generation_complete() returns trigger
  language plpgsql security definer set search_path = '' as $$
declare v_state text; v_produced timestamptz;
begin
  if new.generation_id is null or new.state not in ('recorded','detached') then
    return new;
  end if;
  select state, produced_at into v_state, v_produced from public.video_generations
   where workspace_id = new.workspace_id and video_id = new.video_id
     and generation_id = new.generation_id;
  if v_state is distinct from 'complete' then
    raise exception 'video_artifacts: cannot mark % as % — generation % is %',
      new.slot, new.state, new.generation_id, coalesce(v_state, '<absent>');
  end if;

  -- ⟳ ITEM 1'S INSERT-PATH GAP, CLOSED HERE RATHER THAN DEFERRED AGAIN. The append-only trigger owns
  -- `detached_at` on UPDATE and deliberately not on INSERT, because sync must replicate an
  -- already-detached dig carrying its ORIGINAL detach time. That left a writer able to BACKDATE its
  -- own retention clock — i.e. request earlier collection of its own paid content — and it was flagged
  -- for round 7 as needing "the generation-write API item 3 has to specify anyway". This is that API.
  --
  -- Not closed by forbidding a supplied value (sync needs it), but by BOUNDING it to the artifact's
  -- actual lifetime: it cannot precede the generation that produced the bytes, and it cannot be in the
  -- future. `produced_at` is frozen by 03's freeze trigger, so the lower bound cannot be walked back
  -- either — which is what makes this a bound rather than a speed bump.
  -- ⚠ `tg_op = 'INSERT'` — ⟳ ROUND 7 B2, and the previous version had this exactly backwards.
  -- It ran on both ops, and the comment below the trigger claimed the firing order was "required"
  -- so these bounds would "read the value append-only settled". Literally true, and the consequence
  -- is the OPPOSITE of what that implies. MEASURED:
  --   writer asked for detached_at = 2020-01-01 via UPDATE -> stored 2026-08-08 (trigger's now())
  -- On UPDATE the sibling trigger OVERWRITES detached_at before this runs, so these bounds could
  -- never fire on writer input — they could only fire on a generation with a future produced_at,
  -- making §6.2's detach permanently impossible for it. A guard that cannot see the input it guards,
  -- and can only reject the innocent.
  --
  -- INSERT is the whole point: it is the one path with no append-only trigger, which is why the gap
  -- existed, and it is the path sync uses to replicate an already-detached dig with its ORIGINAL
  -- clock. So the bound belongs here and only here.
  if tg_op = 'INSERT' and new.state = 'detached' then
    if new.detached_at < v_produced then
      raise exception 'video_artifacts: detached_at % precedes generation % produced_at % (backdated retention clock)',
        new.detached_at, new.generation_id, v_produced;
    end if;
    if new.detached_at > now() then
      raise exception 'video_artifacts: detached_at % is in the FUTURE (postponed retention clock)',
        new.detached_at;
    end if;
  end if;
  return new;
end $$;
revoke all on function video_artifacts_generation_complete() from public, anon, authenticated;
-- ⟳ ROUND 7 H1 — the ordering claim that used to live here was BOTH unpinned and wrong, so it is
-- gone rather than reworded. Wrong: see the `tg_op = 'INSERT'` note above. Unpinned: renaming
-- video_artifacts_append_only_trg to `zz_…` inverted the supposedly load-bearing order and all 89
-- assertions stayed GREEN — no assertion read `pg_trigger`, no mutation touched a trigger name, and
-- the entire argument rested on 'v' sorting after 'a'. Shape #6, under the one paragraph claiming
-- the design depended on ordering.
--
-- The dependency is now REMOVED (the bounds are INSERT-only, where append-only never fires), so
-- these two triggers are genuinely order-independent. The order is asserted anyway in 05 (R7),
-- because "it does not matter" is a claim with the same shelf life as "it must be this way".
create trigger video_artifacts_generation_complete_trg
  before insert or update on video_artifacts
  for each row execute function video_artifacts_generation_complete();
-- ⚠ THE CLOCK HAS TWO OWNERS, DELIBERATELY, and this is the whole of it:
--   UPDATE : trigger-owned. `video_artifacts_append_only` sets `detached_at` and a writer cannot
--            influence it, so no bound is needed OR POSSIBLE — see B2 above.
--   INSERT : writer-supplied, because SYNC must replicate an already-detached dig carrying its
--            ORIGINAL detach time; a receiver stamping now() would reset the retention clock on
--            every replica and the bytes would never be collectable. Bounded by
--            `video_artifacts_generation_complete` to [generation.produced_at, now()].
--
-- ⟳ ROUND 7 M4 — the note that stood here said this gap was "FLAGGED FOR ROUND 7 rather than left
-- silent". It was closed in round 6 (item 3) and the note outlived the defect by one merge. Deleted
-- rather than reworded: per this review's own rule, where prose and schema disagree the prose is the
-- defect, and a stale "known gap" is the mechanism by which a fixed defect gets a second life —
-- the next reader re-reports it, and the round after that re-fixes it.

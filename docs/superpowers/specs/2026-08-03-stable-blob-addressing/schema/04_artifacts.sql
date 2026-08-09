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
-- inside `reserve_artifact_slot` — a `security definer set search_path = ''` function — through the
-- `art_slot_kind` CHECK. Its unqualified `::artifact_kind` then cannot be resolved and the INSERT
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
  state         text not null default 'pending'
                check (state in ('pending','recorded','detached')),
  blob_key      text not null,
  source_generation_id text,             -- §5.1.2: what a derived artifact was built FROM
  start_sec     int,
  end_sec       int,
  lease_expires_at timestamptz,          -- round 4 Codex #5: `pending` MUST be leased, or a writer
  lease_attempts   int not null default 0, --   that dies leaves a permanent `busy`. Same shape as
                                           --   reserve_serve_model's lease/attempt bound (0012/0014).
  -- ⟳ ROUND 6 H5 / Codex B2 — WHO holds the slot, and SINCE WHEN.
  -- `lease_token` is the holder's identity, rotated every time the slot is taken. It exists because
  -- RENEWAL needs it: without it a worker that was already reclaimed could renew the NEW holder's
  -- lease and steal the slot back. It is deliberately NOT a veto on recording — see record_artifact.
  -- `reserved_at` anchors the renewal ceiling. `lease_expires_at` cannot: renewal moves it, so it
  -- measures "time until I give up", never "how long this attempt has been running".
  lease_token      uuid,
  reserved_at      timestamptz,
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
  constraint art_pending_is_leased check ((state = 'pending') = (lease_expires_at is not null)),
  -- ⟳ ROUND 6 H5 — THREE separate constraints, not one compound. This file's header demands that
  -- every negative violate EXACTLY ONE guard; a single `(pending) = (a is not null and b is not null
  -- and c is not null)` would make each of the three untestable in isolation, which is round 5 H1's
  -- masking defect written deliberately instead of by accident.
  constraint art_pending_has_token check ((state = 'pending') = (lease_token is not null)),
  constraint art_pending_has_reserved_at check ((state = 'pending') = (reserved_at is not null)),
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
  -- implication operator. It never constrains a dig: a dig may be pending, recorded or detached.
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

-- AT MOST ONE IN-FLIGHT RESERVATION PER SLOT — the money guard. MEASURED by all three round-5
-- reviewers independently: without it, two writers insert `pending` for the same slot under their OWN
-- generation ids, both succeed (different ids ⇒ the paid unique does not collide), and both call
-- Gemini. `count(*) = 2`.
--
-- Seventh instance of shape #9, and an INTERACTION rather than a defect in either change. Round 3's
-- record-first order made the money guard determinate — but it inherited its mutual exclusion from
-- the old `primary key (workspace, video, slot)`, under which the second writer's insert COLLIDED.
-- Round 4's J2-1 made the manifest append-only so many generations could coexist per slot, which is
-- correct for RECORDED history, and silently removed the collision the guard was standing on.
-- Neither round could see it alone, because each was looking at one change.
--
-- ⚠ THIS INDEX IS HALF A FIX. See the reclaim below — round-5 cross-derivation C1. Landing it alone
-- turns a dead lease from a soft `busy` into a HARD uniqueness violation that never clears, i.e. a
-- permanently dead slot. The index and the reclaim are one change.
--
-- It cannot be `where state='pending' and lease_expires_at > now()`: now() is not immutable and
-- Postgres rejects it in an index predicate. The expiry test has to live in the RPC.
create unique index video_artifacts_inflight_uq on video_artifacts
  (workspace_id, video_id, slot)               where state = 'pending';

-- ⟳ ROUND 6 H5 / Codex B2 — THE RECLAIM WAS NOT A PROTOCOL. Three MEASURED defects in ten lines:
--
--   P2   reclaim(a slot that never existed) = 0, and reclaim(a row with lease_attempts = 0) = 0.
--        Indistinguishable — shape #1 on the money path, in a value the comment said the caller
--        "carries into the next reservation and gives up past a terminal bound".
--   --   the bound was RESETTABLE. Reclaim and reserve were two round trips with nothing atomic
--        between them, so two reclaimers could race and the loser's count won: 2 -> 1, and a poison
--        slot never terminates. The unique index makes the loser's INSERT fail; it does nothing to
--        make the COUNT survive.
--   P22  W1 reserves -> its lease expires while it is still inside Gemini -> W2 reclaims and reserves
--        -> both call Gemini. TWO PAID CALLS in one slot.
--
-- ⚠ THE REVIEWER'S PROPOSED FIX WAS DECLINED, DELIBERATELY, AND THIS IS THE REASONING.
-- H5 asked for a `lease_token` that the record-flip must MATCH, so a reclaimed writer's record is
-- REJECTED. Follow the money: in P22 both Gemini calls are already paid for by the time W1 tries to
-- record. Rejecting W1 does not prevent the double charge — it throws away one of the two things we
-- paid for. And under append-only W1's row is not a defect at all: `video_artifacts_paid_uq` keys on
-- (slot, generation_id), so two recorded generations in one slot is precisely what append-only MEANS,
-- and `current` ranks them. W1 and W2 hold different generation ids (rule 19's record-first order
-- makes the writer choose one before reserving), so their bytes never collide either.
--
-- So P22's two rows are the designed state. The defect is that THE LEASE EXPIRED WHILE THE WORKER WAS
-- STILL ALIVE, and the fix for that is RENEWAL, not rejection. USER DECISION 2026-08-07: proceed and
-- keep the paid work.
--
-- Renewal, however, needs the token anyway — a worker that was already reclaimed must not be able to
-- renew the NEW holder's lease. So the token exists; it identifies the holder rather than vetoing a
-- record. It also gives H5 the channel it correctly said was missing, and gives it EARLIER: a failed
-- renewal tells a worker it lost WHILE IT IS STILL WORKING, so it can stop before spending more,
-- instead of finding out at record time when the money is gone.
--
-- Modelled on `reserve_serve_model` (`0014:50-62`), which has been in production here and already
-- does reclaim-and-reserve as ONE upsert. The round-5 reclaim regressed to DELETE-then-INSERT on the
-- premise that the expired row "must stop existing before the next can be created" — true of an
-- INSERT, false of an UPDATE. The pending row can simply be re-pointed: uniqueness is never
-- challenged, and the append-only trigger does not fire on a `pending` row, so its generation_id is
-- mutable by design. Every defect above followed from routing around a constraint that never applied.
create function reserve_artifact_slot(
  p_ws uuid, p_video text, p_slot text, p_generation_id text, p_kind artifact_kind, p_blob_key text,
  p_source_generation_id text default null, p_start_sec int default null, p_end_sec int default null,
  -- ⟳ ROUND 9 — the durable half of the credential. Optional in SIGNATURE only: a caller that omits
  -- both can still reserve, but has nothing to prove ownership with if it loses its token, so it
  -- gets the round-7 behaviour and no more. See video_generations.reserved_by_worker.
  p_worker_id text default null, p_job_id uuid default null)
  returns table (outcome text, token uuid, attempts int)
  language plpgsql security definer set search_path = '' as $$
declare v_ttl int; v_max int; v_cfg public.guardrail_config; v_row public.video_artifacts;
        v_token uuid; v_made_generation boolean := false;
begin
  select * into v_cfg from public.guardrail_config where id = true;
  v_ttl := v_cfg.lease_ttl_seconds;
  -- ⟳ ROUND 7 H2 — minted ONCE and shared by the generation and the artifact, so the holder of a
  -- slot and the reserver of its generation are provably the same party.
  v_token := gen_random_uuid();
  -- THE BOUND IS PER KIND, because the existing knobs already are and they disagree. MEASURED from
  -- the live `guardrail_config` on 2026-08-08: summary=1, **dig=1**, serve=5, lease_ttl=180.
  -- A single number here would have silently overridden a money guardrail somebody chose
  -- deliberately.
  -- ⟳ ROUND 9 (round 8 M6) — THIS COMMENT USED TO SAY `dig_max_attempts=2`, AND THE RUNNING SYSTEM
  -- SAYS 1. The assertions then SET the value they go on to verify, so the schema's reasoning and
  -- production had drifted apart with a green suite in between. The consequence is not cosmetic: at
  -- 1, the named consequence below (a crashed worker leaves a slot no one can retry) silently
  -- extends from summaries to digs, and round 8's B2 scenario is unreachable in production for the
  -- ACCIDENTAL reason that no dig slot is reclaimable at all — which is not a mitigation, because
  -- the same conjunction is reachable through any kind using max_serve_attempts=5.
  -- The values are quoted rather than read here because this is a comment; the assertions that
  -- depend on a specific value set it explicitly and say so.
  -- `p_kind::text`, NOT a bare `case p_kind when 'summary'`. MEASURED: `type "artifact_kind" does
  -- not exist` AT RUNTIME. Comparing an enum against an unknown literal makes Postgres resolve the
  -- enum's type NAME, and `set search_path = ''` puts it out of reach — the THIRD instance this
  -- session of "correct everywhere except inside a definer function with an empty path" (the other
  -- two were `no_corrections_hash` and pgcrypto's `digest` in 03). Casting to text sidesteps name
  -- resolution entirely; the enum's own constraint already guarantees the value is one of these.
  v_max := case p_kind::text
             when 'summary'   then v_cfg.summary_max_attempts
             when 'dig'       then v_cfg.dig_max_attempts
             when 'digDeeper' then v_cfg.dig_max_attempts
             else v_cfg.max_serve_attempts        -- 'model'; 'render' is free and never reserved
           end;
  -- ⚠ CONSEQUENCE, NAMED RATHER THAN DISCOVERED. `summary_max_attempts` DEFAULTS TO 1, so the first
  -- reservation sets attempts=1 and any later reclaim of that slot returns `exhausted`: a summary
  -- worker that CRASHES leaves a slot no one can retry. That is the money guardrail working as
  -- configured — "pay at most once" — and it is deliberately NOT overridden here, because a crashed
  -- worker may well have been billed already. It is a real product decision (retry costs money;
  -- not retrying leaves the video without a summary), it belongs to whoever owns the guardrail
  -- numbers, and `exhausted` is a TYPED outcome so a caller can surface it instead of hanging.
  -- Asserted in 05, so raising the knob is a decision rather than an accident.

  -- Idempotency, and a REAL case rather than symmetry: a worker that crashed between recording and
  -- reporting job completion retries, and must learn it is done rather than be handed an error.
  -- ⟳ ROUND 9 H2 — `generation_id is not distinct from p_generation_id`, NOT `=`.
  -- Round 8's C1 gave the free path a reconciler in `record_artifact` and left this sibling entry
  -- point alone, and the root cause is invisible on inspection: for a FREE slot both sides are NULL,
  -- and `NULL = NULL` is NULL — never true. So this short-circuit was not merely wrong for free
  -- slots, it was UNREACHABLE for them, and the INSERT below uses the in-flight partial index as its
  -- conflict arbiter, which a recorded FREE row can never match. MEASURED:
  --   record free html -> recorded_free ; re-render -> recorded_free ;
  --   reserve the same free slot -> RAW [23505] on video_artifacts_free_uq
  -- A typed outcome promised, a constraint name delivered. Shape #10, in the round that added C1.
  if exists (select 1 from public.video_artifacts
              where workspace_id = p_ws and video_id = p_video and slot = p_slot
                and generation_id is not distinct from p_generation_id
                and state in ('recorded','detached')) then
    return query select 'already_recorded'::text, null::uuid, null::int; return;
  end if;

  -- ⟳ ROUND 6 B5 — THE GENERATION ROW IS CREATED HERE, PENDING, or the INSERT below cannot satisfy
  -- its own foreign key. MEASURED before this existed: [23503] on
  -- video_artifacts_workspace_id_video_id_generation_id_kind_fkey — a cloud summarize could not
  -- reserve its slot at all, because the only other order (create the generation first) needs a card
  -- and an md_hash that do not exist until after the paid call.
  --
  -- `do nothing`, not `do update`: a generation that already exists is either a completed one being
  -- retried (the `already_recorded` path above did not fire because this slot's row was reclaimed) or
  -- one sync replicated in full. Neither may be reopened — 03's freeze trigger would reject it, and
  -- silently re-pointing a generation is the mutable-address defect this design exists to remove.
  -- ⟳ ROUND 7 H2 — the reserving token is recorded ON THE GENERATION, not only on the artifact.
  -- ⟳ ROUND 7 H3 — and whether WE created it is remembered, because a DENIED reservation must not
  -- leave it behind. Item 3 put this INSERT above the upsert that decides who gets the slot, so
  -- every `busy` loser littered an FK-valid parent that no artifact points at, no ranking view
  -- reaches, and no sweep collects — unbounded growth for a worker looping on `busy` with a fresh
  -- generation id per attempt. It cannot simply move below the upsert: the artifact's FK needs it to
  -- already exist. So it is created here and REMOVED on the denial paths.
  if p_generation_id is not null then
    insert into public.video_generations
      (workspace_id, video_id, generation_id, kind, state, reserved_by,
       reserved_by_worker, reserved_by_job)
    values (p_ws, p_video, p_generation_id, p_kind, 'pending', v_token,
            p_worker_id, p_job_id)
    on conflict (workspace_id, video_id, generation_id) do nothing;
    v_made_generation := found;
  end if;

  -- ONE STATEMENT. The attempt count is incremented BY THE SAME STATEMENT THAT TAKES THE SLOT, which
  -- is what makes the bound un-resettable; a partial unique index is a legal conflict arbiter as long
  -- as its predicate is restated.
  insert into public.video_artifacts
    (workspace_id, video_id, slot, generation_id, kind, state, blob_key,
     source_generation_id, start_sec, end_sec,
     lease_expires_at, lease_attempts, lease_token, reserved_at)
  values (p_ws, p_video, p_slot, p_generation_id, p_kind, 'pending', p_blob_key,
          p_source_generation_id, p_start_sec, p_end_sec,
          now() + make_interval(secs => v_ttl), 1, v_token, now())
  on conflict (workspace_id, video_id, slot) where state = 'pending'
  do update set
       generation_id        = excluded.generation_id,
       kind                 = excluded.kind,
       blob_key             = excluded.blob_key,
       source_generation_id = excluded.source_generation_id,
       start_sec            = excluded.start_sec,
       end_sec              = excluded.end_sec,
       lease_expires_at     = excluded.lease_expires_at,
       lease_attempts       = public.video_artifacts.lease_attempts + 1,
       lease_token          = excluded.lease_token,
       reserved_at          = excluded.reserved_at
     where public.video_artifacts.lease_expires_at < now()
       and public.video_artifacts.lease_attempts   < v_max
  returning * into v_row;

  if found then
    return query select 'reserved'::text, v_row.lease_token, v_row.lease_attempts; return;
  end if;

  -- ⟳ ROUND 7 H3 — WE DID NOT GET THE SLOT, SO UNDO THE PARENT WE CREATED FOR IT. Only if WE created
  -- it (`v_made_generation`): a generation that already existed belongs to someone else — the writer
  -- being retried, or sync — and deleting it would destroy a legitimate row. Safe by construction at
  -- this point: we created it moments ago in this transaction and the reservation that would have
  -- pointed an artifact at it just failed, so nothing references it.
  if v_made_generation then
    delete from public.video_generations
     where workspace_id = p_ws and video_id = p_video and generation_id = p_generation_id
       and state = 'pending';
  end if;

  -- Zero rows: the DO UPDATE's WHERE declined. Read back and say WHICH — never signal an outcome with
  -- a raw 23505, which is shape #8 (a policy that errors rather than denies) and forces callers to
  -- parse a constraint name to tell "busy" from "broken".
  select * into v_row from public.video_artifacts
   where workspace_id = p_ws and video_id = p_video and slot = p_slot and state = 'pending';
  if not found then
    return query select 'busy'::text, null::uuid, null::int; return;   -- lost a concurrent insert
  end if;
  -- ⚠ LIVE LEASE FIRST, EXHAUSTION SECOND — the order is the whole meaning, and getting it backwards
  -- is a defect a caller acts on. MEASURED: with the local `dig_max_attempts = 1`, a second writer
  -- arriving while the FIRST is still inside its Gemini call was told `exhausted` — i.e. "give up on
  -- this slot permanently" — about a slot that was being worked on normally. `busy` says "come back";
  -- `exhausted` says "this will never succeed". Only the second is terminal, so it must be reserved
  -- for the case where nobody holds the slot AND the bound is spent.
  -- `reserve_serve_model` (0014:66-70) already orders it this way; this is the precedent cited three
  -- screens above and then not followed closely enough.
  if v_row.lease_expires_at > now() then
    return query select 'busy'::text, null::uuid, v_row.lease_attempts; return;
  end if;
  if v_row.lease_attempts >= v_max then
    return query select 'exhausted'::text, null::uuid, v_row.lease_attempts; return;
  end if;
  return query select 'busy'::text, null::uuid, v_row.lease_attempts;
end $$;

-- RENEWAL — what actually fixes P22, by keeping a live worker's slot instead of arbitrating after
-- both parties have paid.
--
-- ⚠ THERE IS DELIBERATELY NO `lease_expires_at > now()` HERE. The TOKEN decides ownership; the CLOCK
-- only decides when somebody ELSE may take over. A worker that overran its TTL but that nobody
-- reclaimed keeps its work, rather than losing it to a race that never actually happened.
--
-- The ceiling is what stops renewal from re-creating the failure the reclaim exists to fix — a HUNG
-- worker (alive, not progressing) would otherwise renew forever and the slot would never be
-- reclaimable. It reuses `max_duration_seconds`, already this project's "no single job runs longer
-- than this" knob, rather than inventing a number. It is openly a HEURISTIC and its cost is real and
-- not eliminable: a genuinely slow worker past the ceiling CAN still be reclaimed mid-flight, and
-- then we pay twice. No protocol can tell "slow" from "stuck" from outside. What the design can do is
-- make that rare rather than structural, and never compound it by ALSO discarding paid work.
create function renew_artifact_lease(p_ws uuid, p_video text, p_slot text, p_token uuid)
  returns text language plpgsql security definer set search_path = '' as $$
declare v_ttl int; v_ceiling int; v_exists boolean;
begin
  select lease_ttl_seconds, max_duration_seconds into v_ttl, v_ceiling
    from public.guardrail_config where id = true;

  update public.video_artifacts
     set lease_expires_at = now() + make_interval(secs => v_ttl)
   where workspace_id = p_ws and video_id = p_video and slot = p_slot
     and state = 'pending' and lease_token = p_token
     and reserved_at > now() - make_interval(secs => v_ceiling);
  if found then return 'renewed'; end if;

  select exists (select 1 from public.video_artifacts
                  where workspace_id = p_ws and video_id = p_video and slot = p_slot
                    and state = 'pending' and lease_token = p_token) into v_exists;
  return case when v_exists then 'ceiling_exceeded' else 'lost' end;
end $$;

-- THE FLIP — and it NEVER REFUSES. If the token still matches we own the pending row and update it in
-- place; if it does not, we were reclaimed and we APPEND a recorded row for our own generation. The
-- second path is not a fallback, it is append-only working as designed: the bytes are paid for, the
-- generation is legitimate, and `current` ranks it against the winner's on the recorded facts.
--
-- ⟳ ROUND 6 B5 / Codex B3 — THE PAYLOAD, which item 4 deliberately left unspecified. `md_hash` was
-- mandatory (gen_summary_has_hash) and had NO PRODUCER; the card and doc_version_major had the same
-- gap. All three arrive here, and the generation is completed IN THE SAME TRANSACTION as the flip, so
-- there is no instant at which a recorded artifact points at an incomplete generation.
--
-- ⚠ THE GENERATION IS COMPLETED FIRST, AND THE ORDER IS LOAD-BEARING, not stylistic:
-- `video_artifacts_generation_complete` (below) rejects a recorded artifact whose generation is still
-- pending. Both paths — the in-place flip and the append-after-loss — therefore depend on this UPDATE
-- having already run. The API and the guard agree rather than one covering for the other, which is
-- cross-derivation C3's rule (take BOTH the data guard and the query guard) applied to a protocol.
--
-- `coalesce(p_X, X)` rather than plain assignment, so a caller may complete a generation sync already
-- replicated in full without having to re-send content it does not have. Re-stating IDENTICAL values
-- passes 03's freeze trigger untouched; re-stating DIFFERENT ones raises, which is the honest answer
-- to a caller claiming the bytes behind a frozen address changed.
--
-- `p_produced_at` is a PARAMETER with a now() fallback, never a bare now(). Sync replicates a local
-- generation and must carry its ORIGINAL production time — a receiver stamping its own clock is item
-- 1's detached_at defect exactly, and round 4's J2-3 forbids a clock read anywhere the ranking reads.
-- The fallback is reached only by a fresh cloud summarize, where production time genuinely is now.
create function record_artifact(
  p_ws uuid, p_video text, p_slot text, p_generation_id text, p_kind artifact_kind, p_blob_key text,
  p_token uuid, p_source_generation_id text default null,
  p_start_sec int default null, p_end_sec int default null,
  p_md_hash text default null, p_card jsonb default null,
  p_doc_version_major int default null, p_produced_at timestamptz default null,
  p_worker_id text default null, p_job_id uuid default null)
  returns text language plpgsql security definer set search_path = '' as $$
declare v_existed boolean; v_start int; v_end int; v_src text;
begin
  -- ⟳ ROUND 8 (guard classification, C1) — THE FREE PATH, which did not exist.
  -- `video_artifacts_free_uq` is a SEQUENCE guard ("a render for this slot already exists") and it
  -- had no reconciler at all: one INSERT statement takes ONE conflict arbiter, and this function's
  -- was the PAID partial index (`where generation_id is not null`), which a NULL generation can
  -- never match. MEASURED: the first render of a slot succeeded and every RE-render failed with a
  -- raw [23505] — against a comment three screens up promising free renders are "overwritable".
  --
  -- Free is genuinely different and the branch is not duplication: there is no generation to
  -- complete, no token to check (nothing was ever reserved because nothing was paid for), and the
  -- ADDRESS IS MUTABLE — the append-only trigger skips rows with a null generation_id by design, so
  -- overwriting blob_key here is legal where it would be shape #3 on a paid row.
  -- ⟳ ROUND 9 (round 8 Claude H2) — THE LEASE COLUMNS ARE CLEARED HERE TOO. Both paid paths clear
  -- all three; this one set blob_key and state and left them, so a free slot that had been
  -- RESERVED became permanently unrecordable:
  --   reserve a FREE slot -> reserved (state=pending)
  --   record it           -> RAW [23514] art_pending_has_reserved_at, on every retry, forever
  -- The only thing standing between the design and that was the aside "'render' is free and never
  -- reserved" — a CONVENTION, not a guard, and `reserve_artifact_slot` has a dedicated
  -- `if p_generation_id is not null` branch precisely so a null generation is an ordinary call.
  -- Clearing them makes reserve-then-record work rather than forbidding it, because a free render
  -- has no spend to guard but may still want a lease against two workers doing the same CPU work.
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
    do update set blob_key = excluded.blob_key, state = 'recorded',
                  lease_expires_at = null, lease_token = null, reserved_at = null;
    return 'recorded_free';
  end if;

  -- ⟳ ROUND 9 (round 8 B2 + H1) — THE FENCE ASKS FOR A CREDENTIAL THAT SURVIVES A RESTART.
  --
  -- Round 7's version offered two disjuncts, and round 8 measured BOTH ends failing at once:
  --   `reserved_by = p_token`               — correct, but the token dies with the process.
  --   `the slot's pending row names this generation` — survives a restart, and proves NOTHING:
  --      it is satisfied by anyone who can NAME the slot and the generation. Measured with
  --      p_token = NULL *and* with a random valid token: `md_hash=SHA_ATTACKER` / `SHA_FOREIGN`.
  --      So `p_token is not null` would have fixed nothing; NULL was never the crux.
  -- And the worker that disjunct existed for — restarted, then reclaimed — did not match EITHER,
  -- so it was refused and its paid work destroyed (measured: `[P0001] generation gW1 is pending`,
  -- with the identical call succeeding when it still knew its token).
  --
  -- The replacement is the SAME identity the job queue already fences on
  -- (`heartbeat_job`/`complete_job` filter on `id, locked_by, lease_token`), minus the part that
  -- cannot survive: `worker_id` is stable config and `job_id` is recoverable from `jobs`, so a
  -- restarted worker can present both. A stranger presents a different pair and is rejected. One
  -- change, both directions.
  --
  -- ⚠ `=` ON A NULL CREDENTIAL YIELDS NULL, NEVER TRUE — so a caller passing nothing matches
  -- nothing, and the fence is fail-CLOSED for callers that never supplied a credential. That is the
  -- same NULL-comparison rule that made the free short-circuit unreachable (round 8 H2); here it is
  -- load-bearing in our favour, so it is stated rather than relied on silently.
  --
  -- `state = 'pending'` still makes re-completion a NO-OP rather than an error, which is what stops
  -- the freeze trigger from discarding a second writer's paid work.
  if p_generation_id is not null then
    update public.video_generations g
       set state             = 'complete',
           card              = coalesce(p_card, g.card),
           md_hash           = coalesce(p_md_hash, g.md_hash),
           doc_version_major = coalesce(p_doc_version_major, g.doc_version_major),
           produced_at       = coalesce(p_produced_at, g.produced_at, now()),
           reserved_by       = null
     where g.workspace_id = p_ws and g.video_id = p_video and g.generation_id = p_generation_id
       and g.state = 'pending'
       and (g.reserved_by = p_token
            or (g.reserved_by_worker = p_worker_id and g.reserved_by_job = p_job_id));
  end if;

  -- ⟳ ROUND 9 (round 8 Claude H3) — A DIVERGENT ADDRESS IS REFUSED, NOT SILENTLY DROPPED.
  -- Neither the holder path below nor the append path's `do update` assigns blob_key; only the fresh
  -- INSERT used it. MEASURED: a caller recording with a DIFFERENT key got `recorded_as_holder`, and
  -- the manifest kept pointing at the RESERVED key. The bytes are at one address and the row names
  -- another — shape #4, silent, on the success path, in the spec whose entire subject is the address.
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

  update public.video_artifacts
     set state = 'recorded', lease_expires_at = null, lease_token = null, reserved_at = null
   where workspace_id = p_ws and video_id = p_video and slot = p_slot
     and state = 'pending' and lease_token = p_token and generation_id = p_generation_id;
  if found then return 'recorded_as_holder'; end if;

  -- ⟳ ROUND 7 B1 — THE APPEND IS IDEMPOTENT, NOT BLIND, and this is the finding that mattered most.
  -- It used to INSERT unconditionally, and `video_artifacts_paid_uq` has no state predicate — so a
  -- worker that merely RESTARTED and no longer knew its own token collided with its OWN pending row:
  --   [23505] duplicate key value violates unique constraint "video_artifacts_paid_uq"
  -- No race, no reclaim, live lease. The design says this function "never refuses"; measured, it
  -- threw the paid work away anyway, just via a raw SQLSTATE instead of a typed refusal — which is
  -- shape #8, the exact defect reserve_artifact_slot fixes for ITSELF three screens up and did not
  -- sweep to its sibling. Shape #10, instance seven.
  --
  -- ⚠ AND THE TWO PATHS NOW AGREE GIVEN IDENTICAL ARGUMENTS. The holder path above never reads
  -- span/provenance, so a caller may legitimately omit them and rely on what reserve stored. The
  -- blind INSERT required them, so that caller worked in the common case and failed ONLY under the
  -- race — the worst possible place for a latent argument requirement. `coalesce(excluded.…, …)`
  -- makes omission mean "keep what the reservation recorded" on both paths.
  -- ⚠ THE SPAN IS RESOLVED BEFORE THE INSERT, NOT INSIDE THE `do update`, and the difference is a
  -- physical rule worth the sweep list: **a CHECK constraint is evaluated on the proposed tuple
  -- BEFORE conflict resolution.** MEASURED — with the coalesce only in the DO UPDATE, a caller that
  -- omitted the span got `[23514] art_dig_has_span` from the VALUES clause and the ON CONFLICT never
  -- ran. `excluded.*` is the tuple that already had to be legal; it cannot be used to repair itself.
  select exists (select 1 from public.video_artifacts
                  where workspace_id = p_ws and video_id = p_video and slot = p_slot
                    and generation_id = p_generation_id) into v_existed;

  -- ⚠ THE SPAN IS RECOVERED FROM THE SLOT; PROVENANCE ONLY FROM THE SAME GENERATION. Found by the
  -- P22 assertion (R3b) failing on `art_dig_has_span`, and the distinction is real rather than a
  -- workaround:
  --   start_sec/end_sec describe the SECTION the slot names — `dig:8` is seconds 8..88 in every
  --     generation of it — so borrowing across generations is not just safe, it is the definition.
  --     A reclaimed writer's own row is GONE (W2 re-pointed it), so a same-generation lookup finds
  --     nothing and the caller would have had to re-supply the span — reintroducing exactly the
  --     asymmetry B1c exists to remove, in the fix for B1c.
  --   source_generation_id is PROVENANCE — which summary generation this artifact was built FROM —
  --     and two generations of one slot can legitimately differ. Borrowing it across generations
  --     would manufacture a provenance claim, which is shape #4 in the ranking input round 6's
  --     Codex H5 froze precisely to stop a row rewriting its own.
  select start_sec, end_sec into v_start, v_end
    from public.video_artifacts
   where workspace_id = p_ws and video_id = p_video and slot = p_slot
   order by (generation_id = p_generation_id) desc nulls last, state = 'pending' desc
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
       lease_expires_at     = null,
       lease_token          = null,
       reserved_at          = null,
       source_generation_id = excluded.source_generation_id,
       start_sec            = excluded.start_sec,
       end_sec              = excluded.end_sec;
  -- A typed outcome per path, never a constraint name for the caller to parse. `after_token_loss`
  -- says "this was your own reservation, you just could not prove it"; `after_loss` says "your slot
  -- was taken, your generation is recorded alongside the winner's" — item 4's designed state.
  return case when v_existed then 'recorded_after_token_loss' else 'recorded_after_loss' end;
end $$;

-- ⚠ ROUND 6 B1 — MEASURED: `anon`, with no JWT at all, called the previous reclaim and DELETED
-- tenant-1's in-flight reservation. `security definer` means RLS is never consulted, so the GRANT is
-- the entire authorization story — and the default is PUBLIC EXECUTE. This repo revokes PUBLIC on
-- every other definer function it ships (0004:10, 0005:25, 0010:21, 0011:137); the one added as round
-- 5's H4 fix, one file away, was not swept. Sweeping all THREE replacements here, not just the one
-- that inherited the name — that one-site habit is what produced B1 in the first place.
revoke all on function reserve_artifact_slot(uuid, text, text, text, artifact_kind, text, text, int, int,
                                       text, uuid)
  from public, anon, authenticated;
grant execute on function reserve_artifact_slot(uuid, text, text, text, artifact_kind, text, text, int, int,
                                       text, uuid)
  to service_role;
revoke all on function renew_artifact_lease(uuid, text, text, uuid) from public, anon, authenticated;
grant execute on function renew_artifact_lease(uuid, text, text, uuid) to service_role;
revoke all on function record_artifact(uuid, text, text, text, artifact_kind, text, uuid, text, int, int,
                                      text, jsonb, int, timestamptz, text, uuid)
  from public, anon, authenticated;
grant execute on function record_artifact(uuid, text, text, text, artifact_kind, text, uuid, text, int, int,
                                          text, jsonb, int, timestamptz, text, uuid)
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
create view video_generations_collectable with (security_invoker = true) as
select g.*
  from video_generations g
 where not g.body_collected
   -- ⟳ ROUND 9 B1 — AND THE GENERATION MUST BE FINISHED. Both round-8 reviewers found this
   -- independently, and it is round 8's OWN fix reproducing the defect it was written to remove:
   -- this view was added to stop the trigger aborting a sweep, and it copied the currency test
   -- faithfully INCLUDING its blind spot. `video_artifacts_current` requires `state = 'recorded'`,
   -- so an IN-FLIGHT reservation has no current row and its generation was offered to the sweeper
   -- while the paid call was still running. MEASURED end to end, no attacker and no second worker:
   --   collectable WHILE IN FLIGHT: 1 ; sweep collected 1 ; holder records -> recorded_as_holder
   --   gen complete, artifact recorded, and video_artifacts_current rows for that video: 0
   -- The worker's own record SUCCEEDS and reports success; the row is invisible forever, because
   -- `not coalesce(g.body_collected, false)` now excludes it. Money spent, bytes queued for
   -- deletion, no error anywhere — shape #7 and shape #5 on the one path with no undo.
   -- Item 3 introduced `state` for exactly this distinction, and the view written a day later did
   -- not consult it. Shape #10.
   -- ⚠ A 90-day age predicate in the sweeper would have HIDDEN this while leaving the floor wrong,
   -- which is why the fix belongs here and not in the retention heuristic.
   and g.state = 'complete'
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
--   update pending -> recorded : rule 19's record-first order    -> PERMITTED
--   delete an expired pending  : C1's reclaim                    -> PERMITTED
--   update/delete recorded paid: nothing needs it                -> REJECTED
-- Append-only is a claim about PAID HISTORY, never about in-flight reservations. Stating it as a
-- table-wide property is what made it look enforceable-by-nothing.
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
  if old.state in ('recorded','detached') and old.generation_id is not null then
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
    -- deadline is wall-clock by nature — the same reason `lease_expires_at` is allowed to be one.
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
-- `gen_summary_has_format` and `gen_major_matches_card` all become optional for any writer willing to
-- leave its generation `pending` — the relaxation would be a bypass wearing a lifecycle's clothes.
--
-- With it, every row either ranking view can reach has satisfied all four IN FULL, because both views
-- filter `a.state = 'recorded'`. That is why the views needed no change at all.
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

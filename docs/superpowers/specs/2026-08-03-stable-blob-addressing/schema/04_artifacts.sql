-- 04 — the artifact manifest, APPEND-ONLY, plus `current` as a view.
--
-- Round 4 J2-1 / Codex #6 (Blocking): `primary key (workspace, video, slot)` admits ONE row per slot,
-- while rule 13 ranks MANY and A-1's record-first order must insert one BEFORE the bytes. All three
-- ways out of that failed. Resolution: the manifest becomes append-only — one row per GENERATION per
-- slot — and `current` becomes a query rather than a stored pointer. That is what "current is derived"
-- always required and the round-2 PK silently forbade.

create function slot_kind(p_slot text) returns artifact_kind
  language sql immutable as $$
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
  constraint art_key_names_generation check (
    generation_id is null or (
          split_part(blob_key, '/', 1) = workspace_id::text
      and split_part(blob_key, '/', 2) = 'videos'
      and split_part(blob_key, '/', 3) = video_id
      and split_part(blob_key, '/', 4) = generation_id))
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

-- THE RECLAIM (round 5 H4). The lease columns were added in round 4 and NOTHING EVER READ THEM:
-- grepping the spec for lease_expires/lease_attempts/reclaim returned exactly one hit — the sentence
-- motivating the column. A guard that is written and never read is not a guard.
--
-- DELETE-then-insert, not update, because the unique index above is on the EXISTENCE of a pending
-- row: the expired one must stop existing before the next can be created.
create function reclaim_expired_reservation(p_ws uuid, p_video text, p_slot text)
  returns int language plpgsql security definer set search_path = '' as $$
declare v_attempts int;
begin
  delete from public.video_artifacts
   where workspace_id = p_ws and video_id = p_video and slot = p_slot
     and state = 'pending' and lease_expires_at < now()
  returning lease_attempts into v_attempts;
  return coalesce(v_attempts, 0);   -- caller carries this into the next reservation and gives up
end $$;                             -- past a terminal bound, as reserve_serve_model does (0012/0014)

-- ⚠ ROUND 6 B1 — MEASURED: `anon`, with no JWT at all, called this and DELETED tenant-1's in-flight
-- reservation. `security definer` means RLS is never consulted, so the GRANT is the entire
-- authorization story — and the default is PUBLIC EXECUTE. This repo revokes PUBLIC on every other
-- definer function it ships (0004:10, 0005:25, 0010:21, 0011:137); the one added as round 5's H4 fix,
-- one file away, was not swept. Round 5 B2 was the READ half of this exact shape; this is the WRITE
-- half, reintroduced in the same batch that fixed the read.
revoke all on function reclaim_expired_reservation(uuid, text, text) from public, anon, authenticated;
grant execute on function reclaim_expired_reservation(uuid, text, text) to service_role;
revoke all on function slot_kind(text) from public, anon, authenticated;

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
         (g.card->>'mdCorrectionsHash' is not distinct from wv.corrections_hash) desc,
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
         (g.card->>'mdCorrectionsHash' is not distinct from wv.corrections_hash) desc,
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
create trigger forbid_collecting_current_trg
  before update on video_generations
  for each row execute function forbid_collecting_current();

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
create function video_artifacts_append_only() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  if old.state = 'recorded' and old.generation_id is not null then
    if tg_op = 'DELETE' then
      raise exception 'video_artifacts is append-only: cannot DELETE recorded paid row (slot %, gen %)',
        old.slot, old.generation_id;
    end if;
    if new.slot is distinct from old.slot
       or new.generation_id is distinct from old.generation_id
       or new.blob_key is distinct from old.blob_key then
      raise exception 'video_artifacts: the ADDRESS of a recorded paid row is immutable (slot %, gen %)',
        old.slot, old.generation_id;
    end if;
    if new.state not in ('recorded','detached') then
      raise exception 'video_artifacts: recorded paid rows may only become detached, not %', new.state;
    end if;
  end if;
  return case tg_op when 'DELETE' then old else new end;
end $$;
create trigger video_artifacts_append_only_trg
  before update or delete on video_artifacts
  for each row execute function video_artifacts_append_only();

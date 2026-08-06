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
    when p_slot like 'html%'   then 'render'
  end::artifact_kind $$;

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
  constraint art_slot_kind check (slot_kind(slot) is not null and kind = slot_kind(slot)),
  constraint art_paid_has_generation check
    ((kind in ('summary','model','dig','digDeeper')) = (generation_id is not null)),
  constraint art_pending_is_leased check ((state = 'pending') = (lease_expires_at is not null))
);
create unique index video_artifacts_paid_uq on video_artifacts
  (workspace_id, video_id, slot, generation_id) where generation_id is not null;
create unique index video_artifacts_free_uq on video_artifacts
  (workspace_id, video_id, slot)               where generation_id is null;

alter table video_artifacts enable row level security;
alter table video_artifacts force row level security;
grant select, insert, update, delete on video_artifacts to service_role;
grant select on video_artifacts to authenticated, anon;

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
create view video_artifacts_current as
select distinct on (a.workspace_id, a.video_id, a.slot) a.*
from video_artifacts a
join workspace_videos wv
  on  wv.workspace_id = a.workspace_id and wv.video_id = a.video_id
left join video_generations g
  on  g.workspace_id = a.workspace_id and g.video_id = a.video_id
  and g.generation_id = a.generation_id
where a.state = 'recorded' and not coalesce(g.body_collected, false)
order by a.workspace_id, a.video_id, a.slot,
         (g.card->>'mdCorrectionsHash' is not distinct from wv.corrections_hash) desc,
         g.doc_version_major desc nulls last,
         g.produced_at desc nulls last,
         a.generation_id desc nulls last;

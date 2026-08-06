-- 05 — BEHAVIOURAL assertions. A constraint that CREATES is not a constraint that GUARDS:
-- round 3's slot check created cleanly and accepted slot='html', kind='dig'. Each negative below
-- must RAISE; each positive must succeed. Any deviation aborts the run.
\set ON_ERROR_STOP on
create function assert_raises(p_sql text, p_label text) returns void language plpgsql as $$
begin
  begin execute p_sql; exception when others then raise notice 'ok (rejected): %', p_label; return; end;
  raise exception 'ASSERTION FAILED — should have been rejected: %', p_label;
end $$;

-- fixtures
-- Use a REAL seeded workspace (id = owner_id) rather than inventing one: workspace_videos FKs to
-- workspaces, so the fixture must respect the same ordering the migration does.
create temp table t_ws as select id from workspaces limit 1;
insert into workspace_videos (workspace_id, video_id, corrections_hash)
  select id, 'vidA', 'H_NEW' from t_ws;

insert into video_generations (workspace_id, video_id, generation_id, kind, card, doc_version_major, produced_at)
values
 ((select id from t_ws),'vidA','gOLD','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"3.3","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_OLD"}',
  3,'2026-01-01'),
 ((select id from t_ws),'vidA','gNEW','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
  4,'2026-02-01');

-- POSITIVE: a paid slot with a generation, and a free render with none.
-- This comment used to promise the free render and insert only the two paid rows. That gap is why
-- BOTH defects below reached a green run: the PK's implicit NOT NULL made a free render impossible
-- to insert, and the view's inner join made it impossible to serve. A guard with no test, shape #6 —
-- and here the missing test was named in a comment, which is the most confident way to miss it.
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
values ((select id from t_ws),'vidA','summary','gOLD','summary','recorded','k1'),
       ((select id from t_ws),'vidA','summary','gNEW','summary','recorded','k2'),
       ((select id from t_ws),'vidA','pdf:summary',null,'render','recorded','kPDF');

-- APPEND-ONLY: the two paid generations must COEXIST, not overwrite. This is what round 4's J2-1
-- changed the key for; without it the ranking below would rank a set of one.
do $$ declare n int; begin
  select count(*) into n from video_artifacts where video_id='vidA' and slot='summary';
  if n <> 2 then raise exception 'ASSERTION FAILED — append-only: % paid rows, expected 2', n; end if;
  raise notice 'ok (append-only): two generations coexist in one slot';
end $$;

-- FREE RENDER: representable, and REACHABLE through the view.
do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='pdf:summary';
  if k is distinct from 'kPDF' then
    raise exception 'ASSERTION FAILED — free render not current: %', coalesce(k,'<no row>'); end if;
  raise notice 'ok (free render): a generation-less render is representable AND current';
end $$;

-- NEGATIVES — each must raise
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at)
  values ((select id from t_ws),'vidA','gBAD','summary','{"tldr":"t"}',3,now())$$,
  'summary generation with an INCOMPLETE card');
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,doc_version_major,produced_at)
  values ((select id from t_ws),'vidA','gNIL','summary',3,now())$$,
  'summary generation with a NULL card (round 4 J1-2: must fail CLOSED, not open)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','html','gNEW','dig','recorded','k3')$$,
  'slot=html declared kind=dig (round 3 B-5 failed OPEN on exactly this)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','model',null,'model','recorded','k4')$$,
  'PAID kind with no generation_id');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','dig:9','gNEW','dig','pending','k5')$$,
  'pending row with NO LEASE (round 4 Codex #5: unleased pending is a permanent busy)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','pdf:summary',null,'render','recorded','kPDF2')$$,
  'a SECOND free render in one slot (free is one-per-slot; only paid is append-only)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','summary','gNEW','summary','recorded','k2dup')$$,
  'the SAME paid generation twice in one slot (append-only is not append-anything)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidGHOST','pdf:summary',null,'render','recorded','kX')$$,
  'a free render for a video with NO workspace_videos row (the FK the paid FK cannot enforce)');

-- RANKING: format outranks recency. gOLD is corrections-current-EQUAL but major 3; gNEW is major 4.
do $$ declare v text; begin
  select generation_id into v from video_artifacts_current
   where video_id='vidA' and slot='summary';
  if v <> 'gNEW' then raise exception 'ASSERTION FAILED — ranking picked %, expected gNEW', v; end if;
  raise notice 'ok (ranked): format rung outranks recency';
end $$;

-- FLOOR: make BOTH generations corrections-stale. A stale generation must STILL SERVE (round 4 A-2).
update workspace_videos set corrections_hash='H_TYPED_JUST_NOW'
  where workspace_id=(select id from t_ws) and video_id='vidA';
do $$ declare n int; begin
  select count(*) into n from video_artifacts_current where video_id='vidA' and slot='summary';
  if n <> 1 then raise exception 'ASSERTION FAILED — floor broke: % rows, expected 1', n; end if;
  raise notice 'ok (floor): a user typing a correction does NOT empty the slot';
end $$;
\echo ASSERTIONS_OK

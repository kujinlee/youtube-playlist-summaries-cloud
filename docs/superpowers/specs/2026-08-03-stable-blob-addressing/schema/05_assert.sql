-- 05 — BEHAVIOURAL assertions. A constraint that CREATES is not a constraint that GUARDS:
-- round 3's slot check created cleanly and accepted slot='html', kind='dig'.
--
-- ⚠ ROUND 5 H1 — THE RULE THIS FILE IS WRITTEN TO. Mutation testing found 15 of 25 guards untested,
-- and worse: `art_slot_kind` and `art_pending_is_leased` were MASKING EACH OTHER. Their fixture rows
-- were ALSO FK-invalid, so each assertion was satisfied by a disjunction — remove the CHECK and the FK
-- rejected it; remove the FK and the CHECK rejected it. Red only under a DOUBLE mutation. The round-3
-- and round-4 fixes those two lines were written to verify were both still unverified, in the file
-- written to verify them.
--
-- So: EVERY NEGATIVE BELOW MUST VIOLATE EXACTLY ONE GUARD. A fixture that is invalid in two ways
-- tests neither. Where a row must be FK-valid to isolate a CHECK, it uses a generation of the right
-- kind; where a key must be shaped, it is shaped.
\set ON_ERROR_STOP on
create function assert_raises(p_sql text, p_label text) returns void language plpgsql as $$
begin
  begin execute p_sql; exception when others then raise notice 'ok (rejected): %', p_label; return; end;
  raise exception 'ASSERTION FAILED — should have been rejected: %', p_label;
end $$;

-- ── fixtures ────────────────────────────────────────────────────────────────────────────────────
-- Use REAL seeded workspaces (id = owner_id): workspace_videos FKs to workspaces, so the fixtures
-- must respect the same ordering the migration does.
create temp table t_ws as select id from workspaces order by id limit 1;
create temp table t_w2 as select id from workspaces order by id desc limit 1;   -- a SECOND tenant, for RLS
insert into workspace_videos (workspace_id, video_id, corrections_hash)
  select id, 'vidA', 'H_NEW' from t_ws;
insert into workspace_videos (workspace_id, video_id) select id, 'vidB' from t_w2;

-- Keys are SHAPED (`…/<generation>/…`), because art_key_names_generation now requires it and an
-- opaque 'k1' would make that guard untestable — round 5 (Codex): the executable schema was never
-- proving the stable blob address it exists to enforce.
insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
values
 ((select id from t_ws),'vidA','gOLD','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"3.3","mdGeneratedAt":"2026-01-01","processedAt":"y","mdCorrectionsHash":"H_OLD"}',
  3,'2026-01-01','SHA_OLD'),
 ((select id from t_ws),'vidA','gNEW','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-02-01","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
  4,'2026-02-01','SHA_NEW');
-- gSPARE exists ONLY to isolate art_summary_has_no_source: that negative needs a summary generation
-- with NO artifact row yet, or the paid unique fires first and masks the CHECK. Round 5 H1 again,
-- reintroduced by me in the file rewritten to remove it, and caught by mutation testing rather than
-- by reading — which is the argument for mutation testing in one line.
insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
values ((select id from t_ws),'vidA','gSPARE','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-03-01","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
  4,'2026-03-01','SHA_SPARE');
insert into video_generations (workspace_id,video_id,generation_id,kind,doc_version_major,produced_at)
values ((select id from t_ws),'vidA','gDIG','dig',null,'2026-02-01'),
       ((select id from t_ws),'vidA','gMODEL','model',null,'2026-01-15'),
       ((select id from t_ws),'vidA','wA','digDeeper',null,'2026-02-01'),
       ((select id from t_ws),'vidA','wB','digDeeper',null,'2026-02-01');
insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
values ((select id from t_w2),'vidB','g2','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-02-01","processedAt":"y","mdCorrectionsHash":null}',
  4,'2026-02-01','SHA_2');

-- ── POSITIVES ───────────────────────────────────────────────────────────────────────────────────
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
values ((select id from t_ws),'vidA','summary','gOLD','summary','recorded','W/videos/vidA/gOLD/summary.md'),
       ((select id from t_ws),'vidA','summary','gNEW','summary','recorded','W/videos/vidA/gNEW/summary.md'),
       ((select id from t_ws),'vidA','pdf:summary',null,'render','recorded','W/videos/vidA/renders/s.pdf');
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
values ((select id from t_ws),'vidA','dig:120','gDIG','dig','recorded','W/videos/vidA/gDIG/dig/120.md',120,170);
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,source_generation_id)
values ((select id from t_ws),'vidA','model','gMODEL','model','recorded','W/videos/vidA/gMODEL/model.json','gOLD');
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
values ((select id from t_w2),'vidB','summary','g2','summary','recorded','W2/videos/vidB/g2/summary.md');

do $$ declare n int; begin
  select count(*) into n from video_artifacts where video_id='vidA' and slot='summary';
  if n <> 2 then raise exception 'ASSERTION FAILED — append-only: % paid rows, expected 2', n; end if;
  raise notice 'ok (append-only): two generations coexist in one slot';
end $$;

do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='pdf:summary';
  if k is distinct from 'W/videos/vidA/renders/s.pdf' then
    raise exception 'ASSERTION FAILED — free render not current: %', coalesce(k,'<no row>'); end if;
  raise notice 'ok (free render): a generation-less render is representable AND current';
end $$;

-- FLOOR (round 4 J2-4): a paid model whose SOURCE summary was superseded must still serve.
do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='model';
  if k is distinct from 'W/videos/vidA/gMODEL/model.json' then
    raise exception 'ASSERTION FAILED — stale model was GATED, not ranked: %', coalesce(k,'<none>');
  end if;
  raise notice 'ok (floor): a model whose SOURCE summary was superseded still serves';
end $$;

-- RANKING: format outranks recency. gOLD is corrections-STALE and major 3; gNEW is current, major 4.
do $$ declare v text; begin
  select generation_id into v from video_artifacts_current where video_id='vidA' and slot='summary';
  if v <> 'gNEW' then raise exception 'ASSERTION FAILED — ranking picked %, expected gNEW', v; end if;
  raise notice 'ok (ranked): format rung outranks recency';
end $$;

-- ROUND 5 H2: the two views must AGREE about slot='summary'. They MEASURED opposite winners before
-- the summary slot was excluded from the source-currency rung.
do $$ declare a text; b text; begin
  select generation_id into a from video_artifacts_current where video_id='vidA' and slot='summary';
  select generation_id into b from video_summary_current  where video_id='vidA';
  if a is distinct from b then
    raise exception 'ASSERTION FAILED — views disagree on the current summary: % vs %', a, b; end if;
  raise notice 'ok (agree): both views name the same current summary';
end $$;

-- ── NEGATIVES — one guard each ──────────────────────────────────────────────────────────────────
-- gen_card_complete (3 distinct ways to be incomplete; doc_version_major supplied so
-- gen_summary_has_format cannot mask, and a NULL docVersion makes gen_major_matches_card pass on NULL)
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB1','summary','{"tldr":"t"}',3,now())$$,
  'summary generation with an INCOMPLETE card');
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB2','summary',3,now())$$,
  'summary generation with a NULL card (round 4 J1-2: must fail CLOSED, not open)');
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB3','summary',
   '{"tldr":null,"takeaways":null,"docVersion":null,"mdGeneratedAt":null,"processedAt":null,"mdCorrectionsHash":null}',
   3,now())$$,
  'a card of JSON NULLS (round 5 B1: ?& tests key EXISTENCE — this card WON the ranking)');

select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB6','summary',
   '{"tldr":"t","takeaways":null,"docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":null}',
   4,now())$$,
  'a card with ONE null value (each conjunct must bite, not just the set of them)');

-- gen_summary_has_format (card complete, docVersion present so the major check passes on NULL)
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB4','summary',
   '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":null}',
   null,now())$$,
  'a summary generation with NO doc_version_major');

-- gen_major_matches_card (round 5 H5) — card is complete, only the major disagrees
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB5','summary',
   '{"tldr":"t","takeaways":"k","docVersion":"3.3","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":null}',
   99,now())$$,
  'doc_version_major=99 while the card says 3.3 (the card/body lie, moved into the ranking key)');

select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at)
  values ((select id from t_ws),'vidA','gB7','summary',
   '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":null}',
   4,now())$$,
  'a summary generation with NO md_hash (round 5 B3: sync needs it and nothing persisted it)');

-- art_slot_kind — FK-VALID (gDIG is kind='dig'), spans present, key shaped. ONLY the slot/kind
-- mismatch is wrong. Before round 5 this row was also FK-invalid, which masked the guard entirely.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','html','gDIG','dig','recorded','W/videos/vidA/gDIG/x.html',1,2)$$,
  'slot=html declared kind=dig (round 3 B-5 failed OPEN; round 5 H1: the test was MASKED by the FK)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','html-preview',null,'render','recorded','W/videos/vidA/renders/p.html')$$,
  'slot=html-preview — an UNKNOWN slot must fail closed (round 5 L3: like ''html%'' matched it)');

-- art_pending_is_leased — FK-valid, spans present, key shaped. ONLY the missing lease is wrong.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:9','gDIG','dig','pending','W/videos/vidA/gDIG/dig/9.md',9,20)$$,
  'pending row with NO LEASE (round 4 Codex #5; round 5 H1: this test was MASKED too)');

-- art_paid_has_generation
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','digDeeper',null,'digDeeper','recorded','W/videos/vidA/x.md')$$,
  'PAID kind with no generation_id');

-- art_dig_has_span (round 5 H6 — the one finding whose cost is irreversible)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','dig:300','gDIG','dig','recorded','W/videos/vidA/gDIG/dig/300.md')$$,
  'a dig row with NO SPAN (§6.2: cheap now, IMPOSSIBLE to retrofit after the first sweep)');

-- art_key_names_generation (round 5, Codex)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','digDeeper','wB','digDeeper','recorded','W/videos/vidA/gOLD/dd.md')$$,
  'a row ranking wB''s card while serving gOLD''s BYTES (shape #4 on the paid path)');

-- art_summary_has_no_source (round 5 H2, the DATA half)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,source_generation_id)
  values ((select id from t_ws),'vidA','summary','gSPARE','summary','recorded','W/videos/vidA/gSPARE/s.md','gOLD')$$,
  'a SUMMARY carrying a source_generation_id (it is derived from nothing)');

-- the source FK (round 5, Codex/M5)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,source_generation_id)
  values ((select id from t_ws),'vidA','digDeeper','gDIG','digDeeper','recorded','W/videos/vidA/gDIG/dd.md','gGHOST')$$,
  'provenance from a generation that DOES NOT EXIST');

-- the two partial uniques, and the workspace_videos FK
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','pdf:summary',null,'render','recorded','W/videos/vidA/renders/s2.pdf')$$,
  'a SECOND free render in one slot (free is one-per-slot; only paid is append-only)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','summary','gNEW','summary','recorded','W/videos/vidA/gNEW/s2.md')$$,
  'the SAME paid generation twice in one slot (append-only is not append-anything)');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidGHOST','pdf:summary',null,'render','recorded','W/videos/vidGHOST/r.pdf')$$,
  'a free render for a video with NO workspace_videos row (the FK the paid FK cannot enforce)');

-- ── MONEY: the in-flight guard, and its reclaim (round 5 B4 + H4, ONE fix per cross-derivation C1) ──
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,lease_expires_at)
  values ((select id from t_ws),'vidA','digDeeper','wA','digDeeper','pending',
          'W/videos/vidA/wA/dd.md', now() + interval '5 min');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,lease_expires_at)
  values ((select id from t_ws),'vidA','digDeeper','wB','digDeeper','pending',
          'W/videos/vidA/wB/dd.md', now() + interval '5 min')$$,
  'a SECOND in-flight reservation on one slot (both writers would pay Gemini)');

-- the in-flight row must not stall the READER on another slot, and must not appear as current
do $$ declare n int; begin
  select count(*) into n from video_artifacts_current where video_id='vidA' and slot='digDeeper';
  if n <> 0 then raise exception 'ASSERTION FAILED — a PENDING row was served (% rows)', n; end if;
  raise notice 'ok (floor): a pending reservation is never servable';
end $$;

-- the pending -> recorded flip must be PERMITTED (the append-only trigger must not over-reach)
update video_artifacts set state='recorded', lease_expires_at=null
 where video_id='vidA' and slot='digDeeper' and state='pending';
do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='digDeeper';
  if k is distinct from 'W/videos/vidA/wA/dd.md' then
    raise exception 'ASSERTION FAILED — the record-first flip was blocked: %', coalesce(k,'<none>');
  end if;
  raise notice 'ok (flip): pending -> recorded is permitted, and then serves';
end $$;

-- ── APPEND-ONLY, ENFORCED (round 5 M1) ──────────────────────────────────────────────────────────
select assert_raises($$update video_artifacts set blob_key='W/videos/vidA/gNEW/hijacked.md'
  where video_id='vidA' and slot='summary' and generation_id='gNEW'$$,
  'UPDATE of a recorded PAID row (shape #3 — a mutable value in an address)');
select assert_raises($$delete from video_artifacts
  where video_id='vidA' and slot='summary' and generation_id='gNEW'$$,
  'DELETE of a recorded PAID row (this is the serial-coherence orphaning defect)');
select assert_raises($$update video_artifacts set slot='dig:120@gDIG'
  where video_id='vidA' and slot='dig:120'$$,
  'RENAMING the slot of a recorded dig (§6.2 used to specify exactly this — shape #3)');
-- ...but DETACH must still work, or §6.2 is unimplementable. This is the transition my own
-- append-only trigger forbade in its first version, found by cross-derivation, not by a reviewer.
update video_artifacts set state='detached' where video_id='vidA' and slot='dig:120';
do $$ declare st text; n int; begin
  select state into st from video_artifacts where video_id='vidA' and slot='dig:120';
  if st <> 'detached' then raise exception 'ASSERTION FAILED — detach was blocked (state %)', st; end if;
  select count(*) into n from video_artifacts_current where video_id='vidA' and slot='dig:120';
  if n <> 0 then raise exception 'ASSERTION FAILED — a detached dig is still being served'; end if;
  raise notice 'ok (detach): recorded -> detached is permitted, keeps its row, and stops serving';
end $$;

-- ── THE RECLAIM (round 5 H4): an expired lease must be stealable, or the slot is dead forever ────
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,lease_expires_at,lease_attempts,
   start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:900','gDIG','dig','pending',
          'W/videos/vidA/gDIG/dig/900.md', now() - interval '1 min', 2, 900, 950);
do $$ declare a int; n int; begin
  a := reclaim_expired_reservation((select id from t_ws),'vidA','dig:900');
  if a <> 2 then raise exception 'ASSERTION FAILED — reclaim lost the attempt count: %', a; end if;
  select count(*) into n from video_artifacts where video_id='vidA' and slot='dig:900';
  if n <> 0 then raise exception 'ASSERTION FAILED — expired lease NOT reclaimed (% rows)', n; end if;
  raise notice 'ok (reclaim): an expired reservation is stealable, and carries its attempt count';
end $$;
-- ...and a LIVE lease must survive the reclaim, or the money guard is decorative
do $$ declare n int; begin
  perform reclaim_expired_reservation((select id from t_ws),'vidA','dig:9');
  insert into video_artifacts
    (workspace_id,video_id,slot,generation_id,kind,state,blob_key,lease_expires_at,start_sec,end_sec)
    values ((select id from t_ws),'vidA','dig:9','gDIG','dig','pending',
            'W/videos/vidA/gDIG/dig/9.md', now() + interval '5 min', 9, 20);
  perform reclaim_expired_reservation((select id from t_ws),'vidA','dig:9');
  select count(*) into n from video_artifacts where video_id='vidA' and slot='dig:9';
  if n <> 1 then raise exception 'ASSERTION FAILED — reclaim stole a LIVE lease (% rows)', n; end if;
  raise notice 'ok (reclaim): a live lease is NOT stealable';
end $$;

-- ── GC MUST NOT COLLECT THE CURRENT GENERATION (round 5 H3) ──────────────────────────────────────
-- The floor claimed "cannot empty a non-empty set" while `not body_collected` sat inside it.
-- MEASURED before this guard: the summary slot went 2 rows -> 0 when both were collected.
select assert_raises($$update video_generations set body_collected = true
  where video_id='vidA' and generation_id='gNEW'$$,
  'collecting the CURRENT generation (the floor cannot be emptied by GC either)');
-- ...but a SUPERSEDED generation must still be collectable, or §8 can never reclaim anything.
update video_generations set body_collected = true where video_id='vidA' and generation_id='gOLD';
do $$ declare v text; begin
  select generation_id into v from video_artifacts_current where video_id='vidA' and slot='summary';
  if v <> 'gNEW' then raise exception 'ASSERTION FAILED — collecting gOLD broke the slot: %', v; end if;
  raise notice 'ok (GC): a superseded generation is collectable; the current one is not';
end $$;

-- ── RLS: a second tenant must see NOTHING through the VIEW (round 5 B2) ─────────────────────────
-- MEASURED before security_invoker: 0 rows via the raw table, 2 rows AND their blob keys via the view.
do $$ declare n_raw int; n_view int; other uuid; begin
  select id into other from t_w2;
  perform set_config('request.jwt.claims', json_build_object('sub', other::text)::text, true);
  set local role authenticated;
  select count(*) into n_raw  from video_artifacts        where video_id='vidA';
  select count(*) into n_view from video_artifacts_current where video_id='vidA';
  reset role;
  if n_raw <> 0 or n_view <> 0 then
    raise exception 'ASSERTION FAILED — cross-tenant leak: % raw, % via the view', n_raw, n_view;
  end if;
  raise notice 'ok (RLS): another tenant sees 0 rows through the VIEW, not just the table';
end $$;
-- ...and the owner must still see their own, or security_invoker has broken the serve path.
do $$ declare n int; me uuid; begin
  select id into me from t_ws;
  perform set_config('request.jwt.claims', json_build_object('sub', me::text)::text, true);
  set local role authenticated;
  select count(*) into n from video_artifacts_current where video_id='vidA';
  reset role;
  if n = 0 then raise exception 'ASSERTION FAILED — the OWNER cannot read their own manifest'; end if;
  raise notice 'ok (RLS): the owner still reads their own manifest through the view';
end $$;

-- FLOOR: make every generation corrections-stale. A stale generation must STILL SERVE (round 4 A-2).
update workspace_videos set corrections_hash='H_TYPED_JUST_NOW'
  where workspace_id=(select id from t_ws) and video_id='vidA';
do $$ declare n int; begin
  select count(*) into n from video_artifacts_current where video_id='vidA' and slot='summary';
  if n <> 1 then raise exception 'ASSERTION FAILED — floor broke: % rows, expected 1', n; end if;
  raise notice 'ok (floor): a user typing a correction does NOT empty the slot';
end $$;
\echo ASSERTIONS_OK

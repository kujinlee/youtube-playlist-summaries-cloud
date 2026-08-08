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
-- ⚠ ROUND 6 B2/L5 — THE HARNESS ITSELF WAS LAUNDERING FAILURES, and it is why the round-5 claim
-- "every guard was mutation-checked and came back RED" was FALSE.
--
-- The old version caught `when others`, so ANY error counted as "the guard bit". Round 5 added
-- `md_hash` to six negatives' COLUMN lists without adding a value, and every one of them was then
-- rejected by `[42601] INSERT has more target columns than expressions` — a parse error — while the
-- suite reported `ok (rejected)`. Round 5's Blocking B1 (the all-null card that won the ranking) and
-- High H5 shipped UNVERIFIED, in the file whose header demands each negative violate exactly one guard.
--
-- A fixture that does not parse tests strictly LESS than one violating two guards, so round 5 H1's
-- masking defect was not removed — it was deepened. The instrument has to name what it expects:
-- p_sqlstate, and for a CHECK/constraint violation the constraint name. Anything else RE-RAISES.
-- ⚠ DELIBERATELY THE ONE FUNCTION HERE WITHOUT A PINNED search_path (⟳ round 6). Everything the
-- schema ships pins it; this is a test harness whose whole job is to `execute` caller-supplied SQL,
-- and pinning would run the SQL under test in a path the production caller would not have. Labelled
-- so the sweep that found four missing pins does not "fix" this one and quietly change what is tested.
create function assert_raises(p_sql text, p_label text, p_sqlstate text, p_constraint text default null)
  returns void language plpgsql as $$
declare v_state text; v_con text;
begin
  begin
    execute p_sql;
  exception when others then
    get stacked diagnostics v_state = returned_sqlstate, v_con = constraint_name;
    if v_state <> p_sqlstate then
      raise exception 'ASSERTION FAILED — % : expected SQLSTATE %, got % (%)',
        p_label, p_sqlstate, v_state, v_con;
    end if;
    if p_constraint is not null and v_con is distinct from p_constraint then
      raise exception 'ASSERTION FAILED — % : expected constraint %, got % ',
        p_label, p_constraint, coalesce(v_con,'<none>');
    end if;
    raise notice 'ok (rejected by %): %', coalesce(p_constraint, p_sqlstate), p_label;
    return;
  end;
  raise exception 'ASSERTION FAILED — should have been rejected: %', p_label;
end $$;

-- ── ⟳ ROUND 6 B4 — THE BACKFILL, asserted against the LIVE corpus BEFORE any fixture exists ──────
-- Placement is load-bearing and was found by the assertion failing: run after the fixtures and the
-- `vidA` row (deliberately seeded with a non-constant 'H_NEW') is counted as a corrected video, so
-- this reported `wv has 100, videos has 99`. The subject here is the MIGRATION'S OUTPUT, so nothing
-- may have touched the table yet. B4 measured 2903 of 2904 rows NULL while 99 videos carried real
-- corrections; both numbers are now asserted rather than described.
-- (The rest of the item-2 assertions live at the end of this file, with the ranking fixtures.)
do $$ declare n_null int; n_corr_wv int; n_corr_v int; begin
  select count(*) into n_null from workspace_videos where corrections_hash is null;
  if n_null <> 0 then
    raise exception 'ASSERTION FAILED — % rows still carry a NULL corrections_hash', n_null; end if;
  select count(*) into n_corr_wv from workspace_videos where corrections_hash <> no_corrections_hash();
  select count(distinct (workspace_id, video_id)) into n_corr_v
    from videos where coalesce(data->>'corrections','') <> '';
  if n_corr_wv <> n_corr_v then
    raise exception 'ASSERTION FAILED — backfill lost corrections: wv has %, videos has %',
      n_corr_wv, n_corr_v; end if;
  raise notice 'ok (backfill): 0 NULL hashes, and all % corrected videos carried across', n_corr_v;
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
       ((select id from t_ws),'vidA','g_LD','dig',null,'2026-02-01'),
       ((select id from t_ws),'vidA','%','dig',null,'2026-02-01'),
       ((select id from t_ws),'vidA','wA','digDeeper',null,'2026-02-01'),
       ((select id from t_ws),'vidA','wB','digDeeper',null,'2026-02-01'),
       -- ⟳ round 6 H5: the competing writers in the reservation-protocol block. Each reserve/record
       -- names its OWN generation, which is the point — two writers never share an address.
       ((select id from t_ws),'vidA','gOTHER','dig',null,'2026-02-02'),
       ((select id from t_ws),'vidA','gTHIRD','dig',null,'2026-02-03');
insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
values ((select id from t_ws),'vidA','gRETRY','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-02-04","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
  4,'2026-02-04','SHA_RETRY');
insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
values ((select id from t_w2),'vidB','g2','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-02-01","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
  4,'2026-02-01','SHA_2');

-- ── POSITIVES ───────────────────────────────────────────────────────────────────────────────────
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
values ((select id from t_ws),'vidA','summary','gOLD','summary','recorded',(select id from t_ws)::text||'/videos/vidA/gOLD/summary.md'),
       ((select id from t_ws),'vidA','summary','gNEW','summary','recorded',(select id from t_ws)::text||'/videos/vidA/gNEW/summary.md'),
       ((select id from t_ws),'vidA','pdf:summary',null,'render','recorded',(select id from t_ws)::text||'/videos/vidA/renders/s.pdf');
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
values ((select id from t_ws),'vidA','dig:120','gDIG','dig','recorded',(select id from t_ws)::text||'/videos/vidA/gDIG/dig/120.md',120,170);
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,source_generation_id)
values ((select id from t_ws),'vidA','model','gMODEL','model','recorded',(select id from t_ws)::text||'/videos/vidA/gMODEL/model.json','gOLD');
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
values ((select id from t_w2),'vidB','summary','g2','summary','recorded',(select id from t_w2)::text||'/videos/vidB/g2/summary.md');

do $$ declare n int; begin
  select count(*) into n from video_artifacts where video_id='vidA' and slot='summary';
  if n <> 2 then raise exception 'ASSERTION FAILED — append-only: % paid rows, expected 2', n; end if;
  raise notice 'ok (append-only): two generations coexist in one slot';
end $$;

do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='pdf:summary';
  if k is distinct from (select id from t_ws)::text||'/videos/vidA/renders/s.pdf' then
    raise exception 'ASSERTION FAILED — free render not current: %', coalesce(k,'<no row>'); end if;
  raise notice 'ok (free render): a generation-less render is representable AND current';
end $$;

-- FLOOR (round 4 J2-4): a paid model whose SOURCE summary was superseded must still serve.
do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='model';
  if k is distinct from (select id from t_ws)::text||'/videos/vidA/gMODEL/model.json' then
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
  values ((select id from t_ws),'vidA','gB1','summary','{"tldr":"t"}',3,now(),'SHA_X')$$,
  'summary generation with an INCOMPLETE card', '23514', 'gen_card_complete');
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB2','summary',3,now(),'SHA_X')$$,
  'summary generation with a NULL card (round 4 J1-2: must fail CLOSED, not open)', '23514', 'gen_card_complete');
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB3','summary',
   '{"tldr":null,"takeaways":null,"docVersion":null,"mdGeneratedAt":null,"processedAt":null,"mdCorrectionsHash":null}',
   3,now(),'SHA_X')$$,
  'a card of JSON NULLS (round 5 B1: ?& tests key EXISTENCE — this card WON the ranking)', '23514', 'gen_card_complete');

select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB6','summary',
   '{"tldr":"t","takeaways":null,"docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
   4,now(),'SHA_X')$$,
  'a card with ONE null value (each conjunct must bite, not just the set of them)', '23514', 'gen_card_complete');

-- gen_summary_has_format (card complete, docVersion present so the major check passes on NULL)
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB4','summary',
   '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
   null,now(),'SHA_X')$$,
  'a summary generation with NO doc_version_major', '23514', 'gen_summary_has_format');

-- gen_major_matches_card (round 5 H5) — card is complete, only the major disagrees
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB5','summary',
   '{"tldr":"t","takeaways":"k","docVersion":"3.3","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
   99,now(),'SHA_X')$$,
  'doc_version_major=99 while the card says 3.3 (the card/body lie, moved into the ranking key)', '23514', 'gen_major_matches_card');

select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at)
  values ((select id from t_ws),'vidA','gB7','summary',
   '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
   4,now())$$,
  'a summary generation with NO md_hash (round 5 B3: sync needs it and nothing persisted it)', '23514', 'gen_summary_has_hash');

-- art_slot_kind — FK-VALID (gDIG is kind='dig'), spans present, key shaped. ONLY the slot/kind
-- mismatch is wrong. Before round 5 this row was also FK-invalid, which masked the guard entirely.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','html','gDIG','dig','recorded',(select id from t_ws)::text||'/videos/vidA/gDIG/x.html',1,2)$$,
  'slot=html declared kind=dig (round 3 B-5 failed OPEN; round 5 H1: the test was MASKED by the FK)', '23514', 'art_slot_kind');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','html-preview',null,'render','recorded',(select id from t_ws)::text||'/videos/vidA/renders/p.html')$$,
  'slot=html-preview — an UNKNOWN slot must fail closed (round 5 L3: like ''html%'' matched it)',
  '23514', 'art_slot_kind');

-- art_pending_is_leased — FK-valid, spans present, key shaped. ONLY the missing lease is wrong.
-- ⟳ ROUND 6 H5: token + reserved_at ARE supplied, so only the missing LEASE is wrong. Without them
-- this fixture violates three constraints and tests none of them — round 5 H1's masking shape, which
-- adding two NOT-NULL-while-pending columns would otherwise have reintroduced across the whole file.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec,lease_token,reserved_at)
  values ((select id from t_ws),'vidA','dig:9','gDIG','dig','pending',(select id from t_ws)::text||'/videos/vidA/gDIG/dig/9.md',9,20,gen_random_uuid(),now())$$,
  'pending row with NO LEASE (round 4 Codex #5; round 5 H1: this test was MASKED too)', '23514', 'art_pending_is_leased');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec,lease_expires_at,reserved_at)
  values ((select id from t_ws),'vidA','dig:11','gDIG','dig','pending',(select id from t_ws)::text||'/videos/vidA/gDIG/dig/11.md',11,20,now()+interval '5 min',now())$$,
  'pending row with NO TOKEN (nobody could renew it, and anybody could)', '23514', 'art_pending_has_token');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec,lease_expires_at,lease_token)
  values ((select id from t_ws),'vidA','dig:12','gDIG','dig','pending',(select id from t_ws)::text||'/videos/vidA/gDIG/dig/12.md',12,20,now()+interval '5 min',gen_random_uuid())$$,
  'pending row with NO reserved_at (the renewal ceiling has nothing to measure)', '23514', 'art_pending_has_reserved_at');

-- art_paid_has_generation
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','digDeeper',null,'digDeeper','recorded',(select id from t_ws)::text||'/videos/vidA/x.md')$$,
  'PAID kind with no generation_id', '23514', 'art_paid_has_generation');

-- art_dig_has_span (round 5 H6 — the one finding whose cost is irreversible)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','dig:300','gDIG','dig','recorded',(select id from t_ws)::text||'/videos/vidA/gDIG/dig/300.md')$$,
  'a dig row with NO SPAN (§6.2: cheap now, IMPOSSIBLE to retrofit after the first sweep)', '23514', 'art_dig_has_span');

-- art_key_names_generation (round 5, Codex)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','digDeeper','wB','digDeeper','recorded',(select id from t_ws)::text||'/videos/vidA/gOLD/dd.md')$$,
  'a row ranking wB''s card while serving gOLD''s BYTES (shape #4 on the paid path)',
  '23514', 'art_key_names_generation');

-- ROUND 6 H2: the three bypasses the LIKE version MEASURED. All need an FK-valid generation whose
-- id is itself the hazard, so gWILD ('g_LD') and gPCT ('%') are seeded as real dig generations.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:55','g_LD','dig','recorded',
          (select id from t_ws)::text||'/videos/vidA/gOLD/dig/55.md',55,60)$$,
  'generation "g_LD" matching key segment gOLD (LIKE treated _ as a WILDCARD)',
  '23514', 'art_key_names_generation');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:56','%','dig','recorded',
          (select id from t_ws)::text||'/videos/vidA/ANYTHING/dig/56.md',56,60)$$,
  'generation "%" matching ANY key at all (LIKE treated % as a WILDCARD)',
  '23514', 'art_key_names_generation');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:57','gDIG','dig','recorded',
          'OTHERWS/videos/gDIG/gOLD/dig/57.md',57,60)$$,
  'the generation id appearing in the WRONG segment, of another workspace''s key',
  '23514', 'art_key_names_generation');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:58','gDIG','dig','recorded',
          (select id from t_w2)::text||'/videos/vidA/gDIG/dig/58.md',58,60)$$,
  'a key under ANOTHER workspace''s prefix, with video and generation segments correct',
  '23514', 'art_key_names_generation');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:59','gDIG','dig','recorded',
          (select id from t_ws)::text||'/videos/OTHERVIDEO/gDIG/dig/59.md',59,60)$$,
  'a key naming a DIFFERENT video, with workspace and generation segments correct',
  '23514', 'art_key_names_generation');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:60','gDIG','dig','recorded',
          (select id from t_ws)::text||'/WRONG/vidA/gDIG/dig/60.md',60,65)$$,
  'a key whose second segment is not the literal ''videos''',
  '23514', 'art_key_names_generation');

-- art_summary_has_no_source (round 5 H2, the DATA half)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,source_generation_id)
  values ((select id from t_ws),'vidA','summary','gSPARE','summary','recorded',(select id from t_ws)::text||'/videos/vidA/gSPARE/s.md','gOLD')$$,
  'a SUMMARY carrying a source_generation_id (it is derived from nothing)', '23514', 'art_summary_has_no_source');

-- the source FK (round 5, Codex/M5)
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,source_generation_id)
  values ((select id from t_ws),'vidA','digDeeper','wB','digDeeper','recorded',(select id from t_ws)::text||'/videos/vidA/wB/dd.md','gGHOST')$$,
  'provenance from a generation that DOES NOT EXIST', '23503', 'video_artifacts_workspace_id_video_id_source_generation_id_fkey');

-- the two partial uniques, and the workspace_videos FK
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','pdf:summary',null,'render','recorded',(select id from t_ws)::text||'/videos/vidA/renders/s2.pdf')$$,
  'a SECOND free render in one slot (free is one-per-slot; only paid is append-only)', '23505', 'video_artifacts_free_uq');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','summary','gNEW','summary','recorded',(select id from t_ws)::text||'/videos/vidA/gNEW/s2.md')$$,
  'the SAME paid generation twice in one slot (append-only is not append-anything)', '23505', 'video_artifacts_paid_uq');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidGHOST','pdf:summary',null,'render','recorded',(select id from t_ws)::text||'/videos/vidGHOST/r.pdf')$$,
  'a free render for a video with NO workspace_videos row (the FK the paid FK cannot enforce)', '23503', 'video_artifacts_workspace_id_video_id_fkey');

-- ── MONEY: the in-flight guard, and its reclaim (round 5 B4 + H4, ONE fix per cross-derivation C1) ──
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,lease_expires_at,lease_token,reserved_at)
  values ((select id from t_ws),'vidA','digDeeper','wA','digDeeper','pending',
          (select id from t_ws)::text||'/videos/vidA/wA/dd.md', now() + interval '5 min', gen_random_uuid(), now());
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,lease_expires_at,lease_token,reserved_at)
  values ((select id from t_ws),'vidA','digDeeper','wB','digDeeper','pending',
          (select id from t_ws)::text||'/videos/vidA/wB/dd.md', now() + interval '5 min', gen_random_uuid(), now())$$,
  'a SECOND in-flight reservation on one slot (both writers would pay Gemini)', '23505', 'video_artifacts_inflight_uq');

-- the in-flight row must not stall the READER on another slot, and must not appear as current
do $$ declare n int; begin
  select count(*) into n from video_artifacts_current where video_id='vidA' and slot='digDeeper';
  if n <> 0 then raise exception 'ASSERTION FAILED — a PENDING row was served (% rows)', n; end if;
  raise notice 'ok (floor): a pending reservation is never servable';
end $$;

-- the pending -> recorded flip must be PERMITTED (the append-only trigger must not over-reach)
update video_artifacts set state='recorded', lease_expires_at=null, lease_token=null, reserved_at=null
 where video_id='vidA' and slot='digDeeper' and state='pending';
do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='digDeeper';
  if k is distinct from (select id from t_ws)::text||'/videos/vidA/wA/dd.md' then
    raise exception 'ASSERTION FAILED — the record-first flip was blocked: %', coalesce(k,'<none>');
  end if;
  raise notice 'ok (flip): pending -> recorded is permitted, and then serves';
end $$;

-- ── APPEND-ONLY, ENFORCED (round 5 M1) ──────────────────────────────────────────────────────────
select assert_raises($$update video_artifacts set blob_key=(select id from t_ws)::text||'/videos/vidA/gNEW/hijacked.md'
  where video_id='vidA' and slot='summary' and generation_id='gNEW'$$,
  'UPDATE of a recorded PAID row (shape #3 — a mutable value in an address)', 'P0001');
select assert_raises($$delete from video_artifacts
  where video_id='vidA' and slot='summary' and generation_id='gNEW'$$,
  'DELETE of a recorded PAID row (this is the serial-coherence orphaning defect)', 'P0001');
select assert_raises($$update video_artifacts set slot='dig:120@gDIG'
  where video_id='vidA' and slot='dig:120'$$,
  'RENAMING the slot of a recorded dig (§6.2 used to specify exactly this — shape #3)', 'P0001');
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

-- ── ⟳ ROUND 6 B3/H1 + Codex B1/H5 — A DETACHED ROW IS FENCED LIKE A RECORDED ONE ────────────────
-- The trigger used to gate on `old.state = 'recorded'`, so everything above could be stepped around
-- by detaching first. `dig:120` is detached as of the block above — every negative here runs against
-- a REAL detached row, which is the state that was unprotected.
select assert_raises($$delete from video_artifacts where video_id='vidA' and slot='dig:120'$$,
  'DELETE of a DETACHED paid row (P1 — orphaning, reachable in two statements)', 'P0001');
select assert_raises($$update video_artifacts
  set blob_key=(select id from t_ws)::text||'/videos/vidA/gDIG/dig/HIJACKED.md'
  where video_id='vidA' and slot='dig:120'$$,
  'REPOINTING a DETACHED paid row at different bytes (P1b — shape #3, the serious one)', 'P0001');
-- 121, NOT 999: dig:120's span is (120,170), so `start_sec=999` ALSO violates art_dig_has_span
-- (end_sec > start_sec becomes false) and the test passes under a disjunction — round 5 H1's masking
-- defect exactly. Caught by mutation, not by reading: with the trigger removed the constraint still
-- rejected it and the assertion still went red, for the wrong reason. 121 keeps the span legal so
-- ONLY the trigger can object.
select assert_raises($$update video_artifacts set start_sec=121
  where video_id='vidA' and slot='dig:120'$$,
  'rewriting the SPAN of a detached dig (Codex H5 — durable recovery data)', 'P0001');
select assert_raises($$update video_artifacts
  set state='pending', lease_expires_at=now()+interval '5 min', detached_at=null,
      lease_token=gen_random_uuid(), reserved_at=now()
  where video_id='vidA' and slot='dig:120'$$,
  'reviving a detached paid row back to PENDING (a second writer could then pay)', 'P0001');
-- Codex H5 on a RECORDED row: provenance is a RANKING input, so a stale model rewriting it wins the
-- source-currency rung without regenerating anything. `wA`'s digDeeper row is recorded by now.
select assert_raises($$update video_artifacts set source_generation_id='gOLD'
  where video_id='vidA' and slot='digDeeper' and generation_id='wA'$$,
  'rewriting the PROVENANCE of a recorded paid row (Codex H5 — wins the rung for free)', 'P0001');

-- art_detached_is_dig — only a section-scoped artifact can stop matching a section.
-- Both fixtures carry detached_at so they violate EXACTLY ONE guard (round 5 H1's masking rule):
-- without it art_detached_has_timestamp would reject them too and neither test would prove anything.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,detached_at)
  values ((select id from t_ws),'vidA','summary','gSPARE','summary','detached',
          (select id from t_ws)::text||'/videos/vidA/gSPARE/s.md', now())$$,
  'a DETACHED SUMMARY (P10 dies here — a summary is attached to no section)',
  '23514', 'art_detached_is_dig');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,detached_at)
  values ((select id from t_ws),'vidA','digDeeper','wB','digDeeper','detached',
          (select id from t_ws)::text||'/videos/vidA/wB/dd.md', now())$$,
  'a DETACHED digDeeper (it is the per-video container, never section-scoped)',
  '23514', 'art_detached_is_dig');
-- ...and the equivalence in the other direction, or a stale clock survives a re-attachment.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec,detached_at)
  values ((select id from t_ws),'vidA','dig:61','gDIG','dig','recorded',
          (select id from t_ws)::text||'/videos/vidA/gDIG/dig/61.md',61,65, now())$$,
  'a RECORDED row carrying a detached_at (the clock exists only while detached)',
  '23514', 'art_detached_has_timestamp');

-- POSITIVES. A constraint that rejects everything also passes every negative above, and the whole
-- point of `detached` is that the dig REMAINS RECOVERABLE — §6.1 owes it "a route back".
-- ⚠ THE RE-DETACH CHECK NEEDS A PRE-DATED FIXTURE, and finding out why is the whole reason this file
-- mutation-tests. `now()` is transaction_timestamp() — CONSTANT for the life of this rollback — so
-- comparing two trigger-written timestamps inside it compares now() with now() and can never fail.
-- MEASURED: mutating the trigger to restart the clock unconditionally left the suite GREEN.
-- An INSERT does not fire the trigger (it is `before update or delete`), so this is the one way to
-- get a detached_at the trigger did not write and can therefore be seen to preserve or destroy.
--
-- ⟳ ROUND 6 B5 MOVED THIS DATE, and the move is a finding rather than an accommodation. It read
-- `2020-01-01` — a dig detached six years BEFORE gDIG was produced (2026-02-01), which is not a state
-- the system can reach. Item 3's INSERT-path bound rejected it, and the fixture only ever needed a
-- timestamp the TRIGGER DID NOT WRITE, not an impossible one. `2026-02-02` is still distinguishable
-- from this transaction's now(), so everything the assertion below tests is unchanged.
-- Worth recording: a new guard finding an illegal value inside an existing FIXTURE is the same class
-- as round 5 H1's masking pairs — a test can encode an unreachable world and still pass.
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec,detached_at)
  values ((select id from t_ws),'vidA','dig:777','gDIG','dig','detached',
          (select id from t_ws)::text||'/videos/vidA/gDIG/dig/777.md',777,800,
          timestamptz '2026-02-02 00:00:00Z');
do $$ declare t1 timestamptz; t2 timestamptz; st text; begin
  select detached_at into t1 from video_artifacts where video_id='vidA' and slot='dig:120';
  if t1 is null then raise exception 'ASSERTION FAILED — detaching did not start the retention clock'; end if;
  -- a re-detach must NOT restart it, or detach/re-attach cycling pins paid bytes forever
  update video_artifacts set state='detached' where video_id='vidA' and slot='dig:777';
  select detached_at into t2 from video_artifacts where video_id='vidA' and slot='dig:777';
  if t2 is distinct from timestamptz '2026-02-02 00:00:00Z' then
    raise exception 'ASSERTION FAILED — a re-detach RESTARTED the clock (%)', t2; end if;
  -- re-attachment: the one transition §6.1 requires, and it must clear the clock
  update video_artifacts set state='recorded' where video_id='vidA' and slot='dig:120';
  select state, detached_at into st, t2 from video_artifacts where video_id='vidA' and slot='dig:120';
  if st <> 'recorded' then raise exception 'ASSERTION FAILED — re-attachment was blocked (state %)', st; end if;
  if t2 is not null then raise exception 'ASSERTION FAILED — re-attachment left a stale clock'; end if;
  raise notice 'ok (detached fencing): clock starts once, survives re-detach, clears on re-attach';
end $$;

-- ── ⟳ ROUND 6 H5 / Codex B2 — THE RESERVATION PROTOCOL ──────────────────────────────────────────
-- ⚠ THE BOUND IS PINNED HERE, not assumed. The first draft of this block read "dig_max_attempts = 2
-- leaves room to observe a reclaim" — from the MIGRATION DEFAULT. The live local value is 1, so the
-- block asserted against a number the database did not hold, and the failure it produced looked like
-- a protocol bug. A test whose expectations depend on a tunable knob tests the knob. Set it, inside
-- the rollback, so the protocol is what is under test.
update guardrail_config set dig_max_attempts = 2, summary_max_attempts = 1 where id = true;
do $$ declare o text; t1 uuid; t2 uuid; a int; begin
  -- P2 — a typed outcome. The old reclaim returned a bare int and `coalesce(v_attempts,0)` made
  -- "nothing to reclaim" and "reclaimed a row with 0 attempts" the same value, on the money path.
  select outcome, token, attempts into o, t1, a from reserve_artifact_slot(
    (select id from t_ws),'vidA','dig:700','gDIG','dig',
    (select id from t_ws)::text||'/videos/vidA/gDIG/dig/700.md', null, 700, 750);
  if o <> 'reserved' then raise exception 'ASSERTION FAILED — first reservation: %', o; end if;
  if t1 is null then raise exception 'ASSERTION FAILED — reserved without a token'; end if;
  if a <> 1 then raise exception 'ASSERTION FAILED — first attempt counted as %', a; end if;

  -- P22, the half that IS a defect: a second writer must not start a paid call on a live lease.
  select outcome, token into o, t2 from reserve_artifact_slot(
    (select id from t_ws),'vidA','dig:700','gOTHER','dig',
    (select id from t_ws)::text||'/videos/vidA/gOTHER/dig/700.md', null, 700, 750);
  if o <> 'busy' then raise exception 'ASSERTION FAILED — a LIVE lease was stolen: %', o; end if;
  if t2 is not null then raise exception 'ASSERTION FAILED — a losing reserve handed out a token'; end if;
  raise notice 'ok (reserve): typed outcome, a token, and a live lease is not stealable';
end $$;

-- RENEWAL is fenced by the TOKEN, not by the clock — a worker that overran its TTL but that nobody
-- reclaimed keeps its work rather than losing it to a race that never happened.
do $$ declare o text; t uuid; begin
  select lease_token into t from video_artifacts where video_id='vidA' and slot='dig:700';
  if renew_artifact_lease((select id from t_ws),'vidA','dig:700', gen_random_uuid()) <> 'lost' then
    raise exception 'ASSERTION FAILED — a STRANGER renewed the lease'; end if;
  update video_artifacts set lease_expires_at = now() - interval '1 min'
   where video_id='vidA' and slot='dig:700';
  o := renew_artifact_lease((select id from t_ws),'vidA','dig:700', t);
  if o <> 'renewed' then raise exception 'ASSERTION FAILED — the holder could not renew past TTL: %', o; end if;
  -- ...but the CEILING still bounds it, or a HUNG worker renews forever and the slot is never
  -- reclaimable — the exact failure the reclaim exists to prevent, re-created by renewal.
  update video_artifacts set reserved_at = now() - interval '10 hours'
   where video_id='vidA' and slot='dig:700';
  o := renew_artifact_lease((select id from t_ws),'vidA','dig:700', t);
  if o <> 'ceiling_exceeded' then
    raise exception 'ASSERTION FAILED — a hung worker renewed past the ceiling: %', o; end if;
  raise notice 'ok (renew): token-fenced, survives its own TTL, bounded by the ceiling';
end $$;

-- RECLAIM, and the bound SURVIVES it. The old protocol's count was resettable because reclaim and
-- reserve were two round trips; here the increment is in the statement that takes the slot.
do $$ declare o text; t uuid; a int; n int; begin
  update video_artifacts set lease_expires_at = now() - interval '1 min'
   where video_id='vidA' and slot='dig:700';
  select outcome, token, attempts into o, t, a from reserve_artifact_slot(
    (select id from t_ws),'vidA','dig:700','gOTHER','dig',
    (select id from t_ws)::text||'/videos/vidA/gOTHER/dig/700.md', null, 700, 750);
  if o <> 'reserved' then raise exception 'ASSERTION FAILED — an EXPIRED lease was not reclaimable: %', o; end if;
  if a <> 2 then raise exception 'ASSERTION FAILED — the attempt bound did not survive reclaim: %', a; end if;
  select count(*) into n from video_artifacts where video_id='vidA' and slot='dig:700';
  if n <> 1 then raise exception 'ASSERTION FAILED — reclaim duplicated the row (% rows)', n; end if;
  -- the reclaimed writer LEARNS it lost, and learns it while still working
  if renew_artifact_lease((select id from t_ws),'vidA','dig:700', (select lease_token from video_artifacts where video_id='vidA' and slot='dig:700' and lease_token = t)) is null then null; end if;
  raise notice 'ok (reclaim): one row, re-pointed in place, attempts 1 -> 2 durably';
end $$;

-- ⚠ THE DISCRIMINATING CASE FOR live-lease-first, and the reason it needs its own block: at this
-- point attempts = 2 = dig_max_attempts AND the lease is LIVE. Only here do the two orderings give
-- different answers. The earlier `busy` assertion does NOT test the ordering — with attempts = 1 the
-- exhaustion branch is false anyway, so it returns `busy` under either version. MEASURED: mutating
-- the ordering left the whole suite GREEN until this block existed.
-- The distinction is what a caller acts on: `busy` means come back, `exhausted` means never retry.
do $$ declare o text; a int; begin
  select outcome, attempts into o, a from reserve_artifact_slot(
    (select id from t_ws),'vidA','dig:700','gTHIRD','dig',
    (select id from t_ws)::text||'/videos/vidA/gTHIRD/dig/700.md', null, 700, 750);
  if a is distinct from 2 then
    raise exception 'ASSERTION FAILED — precondition: expected attempts=2 at the bound, got %', a; end if;
  if o <> 'busy' then
    raise exception 'ASSERTION FAILED — a LIVE lease at the attempt bound reported %, not busy', o; end if;
  raise notice 'ok (reserve): a LIVE lease reads as busy even at the attempt bound, never exhausted';
end $$;

-- EXHAUSTION is a typed outcome, not a 23505 (shape #8: a policy that errors rather than denies).
do $$ declare o text; begin
  update video_artifacts set lease_expires_at = now() - interval '1 min'
   where video_id='vidA' and slot='dig:700';
  select outcome into o from reserve_artifact_slot(
    (select id from t_ws),'vidA','dig:700','gTHIRD','dig',
    (select id from t_ws)::text||'/videos/vidA/gTHIRD/dig/700.md', null, 700, 750);
  if o <> 'exhausted' then
    raise exception 'ASSERTION FAILED — past dig_max_attempts=2 the outcome was %', o; end if;
  raise notice 'ok (reserve): the attempt bound terminates, as a value not an exception';
end $$;

-- THE FLIP NEVER REFUSES — USER DECISION 2026-08-07, "proceed, keep the paid work".
-- A reclaimed writer already paid Gemini; rejecting its record would discard bought content without
-- preventing the charge, which happened at reserve time. Append-only makes the second row the
-- DESIGNED state: two generations, one slot, ranked by `current`.
do $$ declare o text; t uuid; n int; begin
  select lease_token into t from video_artifacts where video_id='vidA' and slot='dig:700';
  o := record_artifact((select id from t_ws),'vidA','dig:700','gOTHER','dig',
        (select id from t_ws)::text||'/videos/vidA/gOTHER/dig/700.md', t, null, 700, 750);
  if o <> 'recorded_as_holder' then
    raise exception 'ASSERTION FAILED — the holder could not record: %', o; end if;
  -- now the ORIGINAL writer, long since reclaimed, comes back from its Gemini call
  o := record_artifact((select id from t_ws),'vidA','dig:700','gDIG','dig',
        (select id from t_ws)::text||'/videos/vidA/gDIG/dig/700.md', gen_random_uuid(), null, 700, 750);
  if o <> 'recorded_after_loss' then
    raise exception 'ASSERTION FAILED — a reclaimed writer''s PAID work was discarded: %', o; end if;
  select count(*) into n from video_artifacts
   where video_id='vidA' and slot='dig:700' and state='recorded';
  if n <> 2 then raise exception 'ASSERTION FAILED — expected two ranked generations, got %', n; end if;
  raise notice 'ok (record): the holder flips in place; a reclaimed writer APPENDS, losing nothing';
end $$;

-- IDEMPOTENCY: a worker that crashed between recording and reporting completion must learn it is
-- done, not be handed an error it has to parse.
do $$ declare o text; begin
  select outcome into o from reserve_artifact_slot(
    (select id from t_ws),'vidA','dig:700','gDIG','dig',
    (select id from t_ws)::text||'/videos/vidA/gDIG/dig/700.md', null, 700, 750);
  if o <> 'already_recorded' then
    raise exception 'ASSERTION FAILED — re-reserving a recorded generation gave %', o; end if;
  raise notice 'ok (reserve): re-reserving an already-recorded generation is idempotent';
end $$;

-- ⚠ THE CONSEQUENCE OF summary_max_attempts = 1, ASSERTED SO RAISING IT IS A DECISION.
-- A summary worker that CRASHES leaves a slot nobody can retry: the first reserve sets attempts=1,
-- and the bound is `< 1`. That is the money guardrail working as configured ("pay at most once"),
-- not a protocol defect — but it is a real product trade-off (retrying costs money; not retrying
-- leaves the video with no summary) and it belongs to whoever owns the guardrail numbers.
do $$ declare o text; begin
  select outcome into o from reserve_artifact_slot(
    (select id from t_ws),'vidA','summary','gSPARE','summary',
    (select id from t_ws)::text||'/videos/vidA/gSPARE/summary.md');
  if o <> 'reserved' then raise exception 'ASSERTION FAILED — first summary reserve: %', o; end if;
  update video_artifacts set lease_expires_at = now() - interval '1 min'
   where video_id='vidA' and slot='summary' and state='pending';
  select outcome into o from reserve_artifact_slot(
    (select id from t_ws),'vidA','summary','gRETRY','summary',
    (select id from t_ws)::text||'/videos/vidA/gRETRY/summary.md');
  if o <> 'exhausted' then
    raise exception 'ASSERTION FAILED — summary_max_attempts=1 no longer blocks a retry: %', o; end if;
  raise notice 'ok (bound): with summary_max_attempts=1 a crashed summary slot is NOT retryable';
end $$;

-- ── GC MUST NOT COLLECT THE CURRENT GENERATION (round 5 H3) ──────────────────────────────────────
-- The floor claimed "cannot empty a non-empty set" while `not body_collected` sat inside it.
-- MEASURED before this guard: the summary slot went 2 rows -> 0 when both were collected.
select assert_raises($$update video_generations set body_collected = true
  where video_id='vidA' and generation_id='gNEW'$$,
  'collecting the CURRENT generation (the floor cannot be emptied by GC either)', 'P0001');
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

-- ── ROUND 6 B1 / H4 — THE PRIVILEGE SURFACE ────────────────────────────────────────────────────
-- Both MEASURED as live holes before these revokes: anon DELETED another tenant's reservation
-- through the definer function, and anon TRUNCATEd the paid manifest to zero rows.
-- ⚠ Resolve the fixture id BEFORE switching role. The first version of this block read the TEMP
-- table t_ws *after* `set local role anon`, so it got 42501 from the temp table and never reached
-- the function — an assertion passing for a reason other than the one it names, which is the same
-- class of defect as the `when others` harness. Found by mutation: removing the revoke left it GREEN.
-- ⟳ ROUND 6 H5 — ALL THREE replacements are swept, not just the one that inherited the name.
-- B1 happened because a definer function was added one file away and the PUBLIC-revoke habit was
-- applied at one site; replacing that function with three would have been the ideal way to reproduce
-- the same mistake at triple scale.
do $$ declare ws uuid; fn text; begin
  select id into ws from t_ws;
  foreach fn in array array['reserve_artifact_slot','renew_artifact_lease','record_artifact'] loop
    set local role anon;
    begin
      case fn
        when 'reserve_artifact_slot' then
          perform * from reserve_artifact_slot(ws,'vidA','dig:9','gDIG','dig','k');
        when 'renew_artifact_lease' then
          perform renew_artifact_lease(ws,'vidA','dig:9', gen_random_uuid());
        when 'record_artifact' then
          perform record_artifact(ws,'vidA','dig:9','gDIG','dig','k', gen_random_uuid());
      end case;
      reset role;
      raise exception 'ASSERTION FAILED — anon CALLED % (cross-tenant write)', fn;
    exception when insufficient_privilege then
      reset role;
      raise notice 'ok (rejected by 42501): anon calling %', fn;
    end;
  end loop;
end $$;
do $$ begin
  set local role anon;
  begin
    execute 'truncate video_artifacts';
    reset role;
    raise exception 'ASSERTION FAILED — anon TRUNCATEd the paid manifest';
  exception when insufficient_privilege then
    reset role;
    raise notice 'ok (rejected by 42501): anon truncating video_artifacts';
  end;
end $$;

-- ROUND 6 H3 — round 5's cross-tenant assertion read ONE view and ONE table, so security_invoker on
-- video_summary_current and the two new base-table policies were all mutation-GREEN. Read everything.
do $$ declare n int; other uuid; begin
  select id into other from t_w2;
  perform set_config('request.jwt.claims', json_build_object('sub', other::text)::text, true);
  set local role authenticated;
  select (select count(*) from video_artifacts        where video_id='vidA')
       + (select count(*) from video_artifacts_current where video_id='vidA')
       + (select count(*) from video_summary_current   where video_id='vidA')
       + (select count(*) from video_generations       where video_id='vidA')
       + (select count(*) from workspace_videos        where video_id='vidA') into n;
  reset role;
  if n <> 0 then raise exception 'ASSERTION FAILED — cross-tenant leak: % rows across 5 objects', n; end if;
  raise notice 'ok (RLS): tenant 2 sees 0 rows across BOTH views and all three base tables';
end $$;
do $$ declare n int; begin
  set local role anon;
  select (select count(*) from video_artifacts_current)
       + (select count(*) from video_summary_current) into n;
  reset role;
  if n <> 0 then raise exception 'ASSERTION FAILED — anon read % rows through the views', n; end if;
  raise notice 'ok (RLS): anon (no JWT) sees 0 rows through both views';
end $$;

-- ROUND 6 H3, the other direction. Mutation showed `video_generations_owner_read` was GREEN on
-- removal: with force RLS and zero policies the table denies everyone, so every cross-tenant
-- "sees 0 rows" assertion still passed. A policy's removal is only visible from the OWNER's side —
-- and reading it through the view does not work either, because video_generations is LEFT-joined,
-- so its rows vanishing turns into NULLs rather than into missing rows.
do $$ declare ng int; nw int; me uuid; begin
  select id into me from t_ws;
  perform set_config('request.jwt.claims', json_build_object('sub', me::text)::text, true);
  set local role authenticated;
  select count(*) into ng from video_generations where video_id='vidA';
  select count(*) into nw from workspace_videos  where video_id='vidA';
  reset role;
  if ng = 0 or nw = 0 then
    raise exception 'ASSERTION FAILED — the owner cannot read their own base tables (gen %, wv %)', ng, nw;
  end if;
  raise notice 'ok (RLS): the owner reads video_generations and workspace_videos directly';
end $$;

-- FLOOR: make every generation corrections-stale. A stale generation must STILL SERVE (round 4 A-2).
update workspace_videos set corrections_hash='H_TYPED_JUST_NOW'
  where workspace_id=(select id from t_ws) and video_id='vidA';
do $$ declare n int; begin
  select count(*) into n from video_artifacts_current where video_id='vidA' and slot='summary';
  if n <> 1 then raise exception 'ASSERTION FAILED — floor broke: % rows, expected 1', n; end if;
  raise notice 'ok (floor): a user typing a correction does NOT empty the slot';
end $$;

-- ── ⟳ ROUND 6 B4 — ONE REPRESENTATION OF "NO CORRECTIONS", AND RUNG 1 ACTUALLY DECIDING ─────────
-- The cross-language agreement is a REGRESSION GUARD, not a one-off check. If the SQL canonicalizer
-- and content-hash.ts ever diverge, rung 1 is false for every corrected video and the only symptom is
-- copyToCloud on every sync — a money-path failure with no error anywhere. Vectors verified against
-- `mdHash` in node 2026-08-06: empty, plain ASCII, CRLF + repeated trailing newlines, non-ASCII.
do $$ begin
  if corrections_hash_of('') <> no_corrections_hash() then
    raise exception 'ASSERTION FAILED — empty corrections must hash to the DEFINED constant'; end if;
  if corrections_hash_of(null) <> no_corrections_hash() then
    raise exception 'ASSERTION FAILED — absent corrections must hash to the DEFINED constant'; end if;
  if no_corrections_hash() <> '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b' then
    raise exception 'ASSERTION FAILED — the constant moved; every stamped card is now stale'; end if;
  if corrections_hash_of('call it Clawcode not clawcode')
     <> 'ce1046a668ae0385f2814f1cf824d369a82b9790a0c5cf684c92224ce5e90cc2' then
    raise exception 'ASSERTION FAILED — SQL and content-hash.ts disagree on a plain correction'; end if;
  if corrections_hash_of(E'line1\r\nline2\n\n\n')
     <> '2751a3a2f303ad21752038085e2b8c5f98ecff61a2e4ebbd43506a941725be80' then
    raise exception 'ASSERTION FAILED — SQL and content-hash.ts disagree on CRLF canonicalization'; end if;
  if corrections_hash_of('café') <> '7b49b9e063bd91a4f9252b413261f5557b9c570aa61516989499f64a62dbcdd6' then
    raise exception 'ASSERTION FAILED — SQL and content-hash.ts disagree on NFC normalization'; end if;
  raise notice 'ok (hash): SQL reproduces content-hash.ts on 4 vectors, and the constant is pinned';
end $$;

-- RUNG 1 DECIDES, and this is the test that a mutation can actually turn red. Asserting the boolean
-- `card->>'mdCorrectionsHash' = corrections_hash` would merely re-implement the rung; it has to pick a
-- WINNER against the rungs below it. vidC takes the DEFAULT hash (no corrections), which is exactly
-- the state B4 measured as corrections-current = FALSE for the entire corpus.
insert into workspace_videos (workspace_id, video_id) select id, 'vidC' from t_ws;
insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
values
 -- corrections-CURRENT but older and a LOWER format version: must still win, because rung 1 is first
 ((select id from t_ws),'vidC','gC_CUR','summary',
  ('{"tldr":"t","takeaways":"k","docVersion":"3.3","mdGeneratedAt":"2026-01-01","processedAt":"y",'
   || '"mdCorrectionsHash":"' || no_corrections_hash() || '"}')::jsonb,
  3,'2026-01-01','SHA_C_CUR'),
 -- corrections-STALE but newer and a HIGHER format version: must lose
 ((select id from t_ws),'vidC','gC_STALE','summary',
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-09-09","processedAt":"y","mdCorrectionsHash":"H_STALE"}',
  4,'2026-09-09','SHA_C_STALE');
insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
values ((select id from t_ws),'vidC','summary','gC_CUR','summary','recorded',
        (select id from t_ws)::text||'/videos/vidC/gC_CUR/summary.md'),
       ((select id from t_ws),'vidC','summary','gC_STALE','summary','recorded',
        (select id from t_ws)::text||'/videos/vidC/gC_STALE/summary.md');
do $$ declare g text; begin
  select generation_id into g from video_summary_current where video_id='vidC';
  if g is distinct from 'gC_CUR' then
    raise exception 'ASSERTION FAILED — rung 1 did not decide: current is %, expected gC_CUR', coalesce(g,'<none>');
  end if;
  raise notice 'ok (rung 1): an UNCORRECTED video ranks its constant-hash generation as current';
end $$;

-- THE ANTI-DRIFT TRIGGER. Backfilling repairs today; this is what stops the next write re-opening it.
-- Runs against a REAL `videos` row, not the vidC fixture: vidC exists only in `workspace_videos`, so
-- the first version of this test updated ZERO rows, the trigger never fired, and it reported the
-- copy as drifted. A test that cannot reach the trigger it names proves nothing about it.
-- ANY real video, not one constrained to t_ws — MEASURED: t_ws is `workspaces order by id limit 1`
-- and that workspace holds no videos, so the filtered version selected zero rows and the assertion
-- reported "no real video" rather than silently passing. Every `videos` row has a
-- `workspace_videos` row by now; that is what the backfill above just asserted.
create temp table t_real as select workspace_id, video_id from videos limit 1;
do $$ declare h text; c text; n int; begin
  select count(*) into n from t_real;
  if n <> 1 then raise exception 'ASSERTION FAILED — no real video to test the trigger against'; end if;
  update videos v set data = jsonb_set(v.data, '{corrections}', '"say Clawcode"')
    from t_real r where v.workspace_id=r.workspace_id and v.video_id=r.video_id;
  select wv.corrections_hash, wv.corrections into h, c
    from workspace_videos wv join t_real r using (workspace_id, video_id);
  if h <> corrections_hash_of('say Clawcode') then
    raise exception 'ASSERTION FAILED — the copy drifted: wv has %, expected %',
      h, corrections_hash_of('say Clawcode'); end if;
  if c <> 'say Clawcode' then
    raise exception 'ASSERTION FAILED — the copy kept a stale corrections text: %', coalesce(c,'<null>'); end if;
  -- ...and clearing them must return the DEFINED CONSTANT, not NULL. This is the direction that
  -- re-opens B4 if it regresses: a NULL here is indistinguishable from "never computed".
  update videos v set data = jsonb_set(v.data, '{corrections}', '""')
    from t_real r where v.workspace_id=r.workspace_id and v.video_id=r.video_id;
  select wv.corrections_hash into h
    from workspace_videos wv join t_real r using (workspace_id, video_id);
  if h <> no_corrections_hash() then
    raise exception 'ASSERTION FAILED — clearing corrections did not restore the constant: %', h; end if;
  raise notice 'ok (anti-drift): editing corrections updates the copy; clearing restores the constant';
end $$;

select assert_raises($$insert into workspace_videos (workspace_id, video_id, corrections_hash)
  values ((select id from t_ws),'vidNULL', null)$$,
  'a NULL corrections_hash (absent-vs-failed on the top ranking rung)', '23502');
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gB8','summary',
   '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":null}',
   4,now(),'SHA_X')$$,
  'a card whose ONLY null is mdCorrectionsHash (round 5 C2 permitted this; no producer emits it)',
  '23514', 'gen_card_complete');

-- ── ⟳ ROUND 6 B5 / Codex B3 — THE GENERATION-WRITE API (handoff item 3) ────────────────────────
-- MEASURED before any of this existed, and it is worse than "md_hash has no producer": a cloud
-- summarize could not RESERVE ITS SLOT AT ALL. Both doors were locked and the paid call sat between:
--
--   reserve with no generation row           -> [23503] video_artifacts…generation_id_kind_fkey
--   create the generation row pre-Gemini     -> [23514] gen_card_complete
--
-- §10.0 exists to prevent exactly this and predicted a failure AFTER payment; the real one was
-- BEFORE it. Safer direction, but it made the round-6 reservation protocol unreachable for its
-- primary kind — and all 73 assertions missed it because every fixture above hand-inserts a
-- COMPLETE generation row, which is the one thing no producer can do.
--
-- THE PREMISE THAT FAILED: "a generation row is only ever complete." True while the manifest held one
-- row per slot and the generation was written once, after the fact. Rounds 5-6 gave the ARTIFACT a
-- lifecycle (pending -> recorded -> detached) and a protocol that must insert a pending row BEFORE
-- the content exists, and never gave its FK PARENT the matching lifecycle. Restated:
--   a generation must be complete WHEN SOMETHING RECORDED POINTS AT IT, not from the moment it exists.
-- Same move as item 1 (a CHECK governs states, a trigger governs transitions) and item 2 (the guard
-- lived in the NOT NULL, not in the comparison). The tell each time was an UNSATISFIABLE ORDERING.

insert into workspace_videos (workspace_id, video_id) select id, 'vidG' from t_ws;

-- G1 — THE DEFECT ITSELF. This is the assertion that is red without the fix, and it is a POSITIVE:
-- the failure was an inability to act, so no `assert_raises` can express it.
do $$ declare o text; t uuid; ws uuid; begin
  select id into ws from t_ws;
  select outcome, token into o, t from reserve_artifact_slot(
    ws,'vidG','summary','gG1','summary'::artifact_kind, ws::text||'/videos/vidG/gG1/summary.md');
  if o <> 'reserved' then
    raise exception 'ASSERTION FAILED — a producer cannot reserve a summary slot: %', o; end if;
  raise notice 'ok (item 3): reserve creates its own PENDING generation; no card is needed yet';
end $$;

-- G2 — and what it created is honestly incomplete, not a fabricated placeholder. sync-run.ts:534-542
-- already builds one of those and calls it "an HONEST unresolved placeholder"; round 5 B1 measured
-- such a card WINNING the ranking. A pending generation carries NO content at all instead.
do $$ declare r record; begin
  select * into r from video_generations where video_id='vidG' and generation_id='gG1';
  if r.state <> 'pending' then
    raise exception 'ASSERTION FAILED — reserve did not leave the generation pending: %', r.state; end if;
  if r.card is not null or r.md_hash is not null or r.produced_at is not null
     or r.doc_version_major is not null then
    raise exception 'ASSERTION FAILED — a pending generation fabricated content'; end if;
  raise notice 'ok (item 3): a pending generation carries NO card, md_hash, doc_version or produced_at';
end $$;

-- G3 — THE RELAXATION MUST NOT LEAK. This is the guard that makes gating the four CHECKs safe: it
-- restores the old invariant exactly where it was load-bearing. Without it, every completeness
-- constraint becomes optional for anyone willing to write `state = 'pending'`.
-- Direct UPDATE, deliberately: it isolates the trigger from record_artifact, and the append-only
-- trigger cannot mask it (its body is gated on old.state, which is 'pending' here).
--
-- ⚠ THE LEASE COLUMNS ARE CLEARED IN THE SAME STATEMENT, and that is the header rule rather than
-- tidiness. Without it this negative violates TWO guards — the trigger AND art_pending_is_leased,
-- since `(state='pending') = (lease_expires_at is not null)` is false the moment state flips while
-- the lease is still set. MEASURED via mutation: removing the trigger produced 23514 instead of
-- P0001. The SQLSTATE pin caught it rather than reporting a false GREEN, which is round 6's harness
-- fix doing its job — but a negative that needs the harness to disambiguate it is still round 5 H1.
select assert_raises($$update video_artifacts
  set state='recorded', lease_expires_at=null, lease_token=null, reserved_at=null
  where video_id='vidG' and slot='summary'$$,
  'recording an artifact whose generation is still PENDING (the completeness bypass)', 'P0001');

-- G4 — a pending generation is invisible to BOTH ranking views. Follows from G3, asserted anyway:
-- ranking is where round 5 B1 did its damage, and "follows from" is how round 5 H1's masking pairs
-- were justified.
do $$ declare n int; begin
  select count(*) into n from video_artifacts_current where video_id='vidG';
  if n <> 0 then raise exception 'ASSERTION FAILED — a PENDING generation reached current: % rows', n; end if;
  raise notice 'ok (item 3): a pending generation is in neither ranking view';
end $$;

-- G5 — THE FLIP, carrying the payload item 3 exists to add. One transaction: the generation completes
-- and the artifact records together, so there is no window where a recorded row points at a pending
-- generation (G3 would reject it anyway — the API and the guard agree rather than one covering the other).
do $$ declare o text; g text; r record; ws uuid; t uuid; begin
  select id into ws from t_ws;
  select lease_token into t from video_artifacts where video_id='vidG' and slot='summary';
  o := record_artifact(ws,'vidG','summary','gG1','summary'::artifact_kind,
        ws::text||'/videos/vidG/gG1/summary.md', t,
        p_md_hash := 'SHA_G1',
        p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-03-03",'
               || '"processedAt":"z","mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
        p_doc_version_major := 4, p_produced_at := '2026-03-03');
  if o <> 'recorded_as_holder' then
    raise exception 'ASSERTION FAILED — the holder did not record: %', o; end if;
  select * into r from video_generations where video_id='vidG' and generation_id='gG1';
  if r.state <> 'complete' or r.md_hash <> 'SHA_G1' then
    raise exception 'ASSERTION FAILED — record did not complete the generation: % %', r.state, r.md_hash; end if;
  select generation_id into g from video_summary_current where video_id='vidG';
  if g is distinct from 'gG1' then
    raise exception 'ASSERTION FAILED — the recorded summary is not current: %', coalesce(g,'<none>'); end if;
  raise notice 'ok (item 3): record completes the generation AND flips the artifact, one transaction';
end $$;

-- G6/G7 — md_hash AND the card ARE STILL MANDATORY. The constraints did not weaken; each moved to the
-- moment its value can exist. This is the assertion §10.0 should have forced and did not.
--
-- ⚠ EACH GETS ITS OWN VIDEO, and both parts of that are load-bearing. The generation must be
-- reserved rather than named, or record_artifact updates zero generation rows and the artifact INSERT
-- fails on the FK [23503] — a fixture that never reaches the constraint it names, which is round 5
-- H1's masking defect. And there is only ONE summary slot per video (slot_kind maps exactly one), so
-- sharing vidG would leave G6's pending row holding the in-flight unique and G7 would read `busy`.
insert into workspace_videos (workspace_id, video_id) select id, 'vidG6' from t_ws;
insert into workspace_videos (workspace_id, video_id) select id, 'vidG7' from t_ws;
do $$ declare o text; ws uuid; begin
  select id into ws from t_ws;
  select outcome into o from reserve_artifact_slot(
    ws,'vidG6','summary','gG6','summary'::artifact_kind, ws::text||'/videos/vidG6/gG6/summary.md');
  if o <> 'reserved' then raise exception 'FIXTURE FAILED — G6 reserve: %', o; end if;
  select outcome into o from reserve_artifact_slot(
    ws,'vidG7','summary','gG7','summary'::artifact_kind, ws::text||'/videos/vidG7/gG7/summary.md');
  if o <> 'reserved' then raise exception 'FIXTURE FAILED — G7 reserve: %', o; end if;
end $$;

select assert_raises($$select record_artifact((select id from t_ws),'vidG6','summary','gG6',
   'summary'::artifact_kind,(select id from t_ws)::text||'/videos/vidG6/gG6/summary.md',
   (select lease_token from video_artifacts where video_id='vidG6' and slot='summary'),
   p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y",'
          || '"mdCorrectionsHash":"H_NEW"}')::jsonb,
   p_doc_version_major := 4, p_produced_at := now())$$,
  'completing a summary generation with NO md_hash (the constraint moved, it did not weaken)',
  '23514', 'gen_summary_has_hash');

select assert_raises($$select record_artifact((select id from t_ws),'vidG7','summary','gG7',
   'summary'::artifact_kind,(select id from t_ws)::text||'/videos/vidG7/gG7/summary.md',
   (select lease_token from video_artifacts where video_id='vidG7' and slot='summary'),
   p_md_hash := 'SHA_G7', p_doc_version_major := 4, p_produced_at := now())$$,
  'completing a summary generation with NO card', '23514', 'gen_card_complete');

-- G8 — COMPLETE IS TERMINAL. New content means a NEW generation; that is what append-only means one
-- level up, and without this the frozen artifact address would point at re-writable content —
-- shape #3 relocated from the artifact row into its parent.
select assert_raises($$update video_generations set state = 'pending'
  where video_id='vidG' and generation_id='gG1'$$,
  'reverting a COMPLETE generation to pending', 'P0001');
select assert_raises($$update video_generations set md_hash = 'SHA_TAMPERED'
  where video_id='vidG' and generation_id='gG1'$$,
  'rewriting the md_hash of a COMPLETE generation (the body it addresses cannot change)', 'P0001');
select assert_raises($$update video_generations set doc_version_major = 99
  where video_id='vidG' and generation_id='gG1'$$,
  'rewriting doc_version_major of a COMPLETE generation (the format rung must never be re-pointed)',
  'P0001');

-- G9 — produced_at is CARRIED, NEVER STAMPED. Sync replicates a local generation and must keep its
-- original production time; a receiver stamping now() is item 1's detached_at clock defect exactly,
-- and round 4's J2-3 forbids a clock read anywhere the ranking reads.
do $$ declare p timestamptz; begin
  select produced_at into p from video_generations where video_id='vidG' and generation_id='gG1';
  if p <> '2026-03-03'::timestamptz then
    raise exception 'ASSERTION FAILED — produced_at was stamped, not carried: %', p; end if;
  raise notice 'ok (item 3): produced_at is carried from the producer, not read from the clock';
end $$;

-- G10 — a completed generation needs a produced_at, or the bottom ranking rung reads NULL for a row
-- that genuinely has a production time. Same shape as item 2's NOT NULL: absent-vs-failed on a rung.
-- The pending generation is made by RESERVE, not by hand: an `update … where <no such row>` reports
-- zero rows, raises nothing, and assert_raises would then fail with "should have been rejected" —
-- a test bug that looks like a missing guard. Round 6's harness fix exists because of exactly that
-- confusion, so the fixture has to be real.
do $$ declare o text; ws uuid; begin
  select id into ws from t_ws;
  select outcome into o from reserve_artifact_slot(
    ws,'vidG','model','gG10','model'::artifact_kind, ws::text||'/videos/vidG/gG10/model.json');
  if o <> 'reserved' then raise exception 'FIXTURE FAILED — could not reserve for G10: %', o; end if;
end $$;
select assert_raises($$update video_generations set state='complete'
  where video_id='vidG' and generation_id='gG10'$$,
  'completing a generation with no produced_at', '23514', 'gen_complete_has_produced_at');

-- G11 — TASK #25, and it needs NO SCHEMA CHANGE. `digDeeper` was never bound to one summary
-- generation: the FK is on (ws, video, generation_id, KIND), so a digDeeper artifact points at a
-- digDeeper GENERATION, minted per rewrite of the accumulator. Round 2 got this backwards the other
-- way (forcing digDeeper to kind='summary') by reasoning from the slot NAME rather than the
-- constraints — the same route as item 1's P9, which was also reported as a defect and was not one.
do $$ declare o text; t uuid; ws uuid; n int; begin
  select id into ws from t_ws;
  select outcome, token into o, t from reserve_artifact_slot(
    ws,'vidG','digDeeper','gDD_A','digDeeper'::artifact_kind, ws::text||'/videos/vidG/gDD_A/dig-deeper.md');
  if o <> 'reserved' then raise exception 'ASSERTION FAILED — digDeeper could not reserve: %', o; end if;
  o := record_artifact(ws,'vidG','digDeeper','gDD_A','digDeeper'::artifact_kind,
        ws::text||'/videos/vidG/gDD_A/dig-deeper.md', t, p_produced_at := '2026-03-04');
  if o <> 'recorded_as_holder' then
    raise exception 'ASSERTION FAILED — digDeeper could not record: %', o; end if;
  -- the accumulator is rewritten: a SECOND digDeeper generation, coexisting under append-only
  select outcome, token into o, t from reserve_artifact_slot(
    ws,'vidG','digDeeper','gDD_B','digDeeper'::artifact_kind, ws::text||'/videos/vidG/gDD_B/dig-deeper.md');
  o := record_artifact(ws,'vidG','digDeeper','gDD_B','digDeeper'::artifact_kind,
        ws::text||'/videos/vidG/gDD_B/dig-deeper.md', t, p_produced_at := '2026-03-05');
  select count(*) into n from video_artifacts where video_id='vidG' and slot='digDeeper' and state='recorded';
  if n <> 2 then
    raise exception 'ASSERTION FAILED — the two digDeeper generations did not coexist: %', n; end if;
  select generation_id into o from video_artifacts_current where video_id='vidG' and slot='digDeeper';
  if o <> 'gDD_B' then
    raise exception 'ASSERTION FAILED — current digDeeper is %, expected the newer gDD_B', o; end if;
  raise notice 'ok (#25): digDeeper generations are per-REWRITE, coexist, and rank — no schema change';
end $$;

-- G12 — THE DEFAULT IS THE SAFE ONE. A direct insert that names no state is COMPLETE, so every
-- producer that has not opted in keeps today's behaviour and today's rejection. A `pending` default
-- would have made every completeness CHECK optional for anyone who simply forgot the column.
do $$ declare s text; begin
  select state into s from video_generations where video_id='vidA' and generation_id='gNEW';
  if s <> 'complete' then
    raise exception 'ASSERTION FAILED — a directly-inserted full generation is %, not complete', s; end if;
  raise notice 'ok (item 3): state defaults to COMPLETE, so the relaxation is strictly opt-in';
end $$;

-- G13 — ITEM 1'S INSERT-PATH GAP, BOUNDED. The append-only trigger owns detached_at on UPDATE, and
-- deliberately not on INSERT (sync must replicate an already-detached dig carrying its ORIGINAL
-- detach time). That left a writer able to BACKDATE its own retention clock — flagged for round 7 as
-- needing "the generation-write API item 3 has to specify anyway". This is that API, so it is closed
-- here rather than deferred again. Not by forbidding a supplied value — sync needs it — but by
-- bounding it to the artifact's ACTUAL lifetime: it cannot precede the generation that produced it,
-- and it cannot be in the future. produced_at is frozen by G8, so the lower bound cannot be moved either.
-- ⚠ A DIG GENERATION, not gG1. gG1 is kind='summary', so a dig artifact naming it violates the
-- FK on (ws, video, generation_id, KIND) as well as the bound under test — two guards again, and
-- mutation reported it as `expected P0001, got 23503`. Same defect as G3's lease columns, found the
-- same way, in the same hour: isolating a negative is not something you get right by intending to.
insert into video_generations (workspace_id,video_id,generation_id,kind,produced_at)
  select id,'vidG','gGD','dig','2026-03-03' from t_ws;
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec,detached_at)
  values ((select id from t_ws),'vidG','dig:900','gGD','dig','detached',
   (select id from t_ws)::text||'/videos/vidG/gGD/dig-900.md',900,960,'2026-03-01')$$,
  'inserting a detached dig backdated BEFORE its generation was produced', 'P0001');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec,detached_at)
  values ((select id from t_ws),'vidG','dig:901','gGD','dig','detached',
   (select id from t_ws)::text||'/videos/vidG/gGD/dig-901.md',901,960, now() + interval '1 day')$$,
  'inserting a detached dig whose retention clock starts in the FUTURE', 'P0001');
\echo ASSERTIONS_OK

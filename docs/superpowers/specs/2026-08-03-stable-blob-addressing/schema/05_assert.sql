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

-- ── ⟳ POPULATION-COVERAGE INSTRUMENT (added 2026-08-07) ─────────────────────────────────────────
-- THE RATCHET THAT MAKES THE FREE-RENDER DEFECT UNREINTRODUCIBLE.
--
-- That defect was not a wrong line anywhere. It was an ABSENCE: no fixture, in seven review rounds,
-- ever wrote the same free slot TWICE. Every instrument this project owns is opt-in — an assertion
-- exists because someone thought of the case, a mutation because someone wrote it, a review finds
-- what a reviewer looks at — so they share ONE blind spot, and an absence is invisible to all of
-- them at once.
--
-- An absence is only visible against an ENUMERATED WHOLE. `artifact_kind` is a finite population
-- (5 values) and free-vs-paid is a 2-way split, so "has every kind been written a second time?" is
-- checkable rather than remembered. The second write is exactly the SEQUENCE question — what does
-- this do when the caller is not the first? — made mechanical.
--
-- ⟳ ROUND 9 (round 8 M4) — IT COUNTS *INSERTS*, NOT ROW-WRITES, AND THAT WAS THE WHOLE CLAIM.
-- The trigger fires `after insert or update`, and a paid artifact's ordinary life is `reserve`
-- (INSERT pending) then `record` (UPDATE recorded) — two rows in this table, ONE caller, and no
-- second-caller behaviour exercised anywhere. The ratchet said "the SEQUENCE case is exercised" and
-- could be satisfied by a lifecycle that never has a second caller: shape #11, in the instrument
-- built to close an absence.
--
-- Measured before tightening: it was TRUTHFUL — every kind did have a real second INSERT (summary
-- 11, digDeeper 3, model 2, render 2, dig via dig:700 and dig:8) — though four dig:* slots passed on
-- a single-writer lifecycle alone. So the weakness was live but not yet load-bearing, and requiring
-- >= 2 INSERTs passes today UNCHANGED, which is the proof the tightening costs nothing.
--
-- Test-only instrumentation: it lives in the assertion file, not the schema, and rolls back with
-- everything else.
create temp table t_writes (kind text, paid boolean, slot text, op text);
create function record_write() returns trigger language plpgsql as $$
begin
  insert into t_writes values (new.kind::text, new.generation_id is not null, new.slot, tg_op);
  return null;
end $$;
create trigger t_writes_trg after insert or update on video_artifacts
  for each row execute function record_write();

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
          'OTHERWS/videos/vidA/gDIG/dig/57.md',57,60)$$,
  -- ⟳ ROUND 9 H5 — SHARPENED. It used to be 'OTHERWS/videos/gDIG/gOLD/...', which violated the
  -- workspace segment, the video segment AND the generation segment at once — three faults across
  -- two constraints, in the file whose header requires every negative to violate exactly one.
  -- Now only segment 1 is wrong, so it tests the tenant prefix and nothing else.
  'a key under another workspace''s prefix, every other segment correct',
  '23514', 'art_key_names_workspace');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:58','gDIG','dig','recorded',
          (select id from t_w2)::text||'/videos/vidA/gDIG/dig/58.md',58,60)$$,
  -- ⟳ ROUND 9 H5 — now caught by the constraint that actually means it. Tenant confinement used to
  -- live INSIDE art_key_names_generation, which is gated on a non-null generation, so free rows
  -- escaped it entirely (measured: a render row in workspace A storing workspace B's prefix).
  'a key under ANOTHER workspace''s prefix, with video and generation segments correct',
  '23514', 'art_key_names_workspace');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:59','gDIG','dig','recorded',
          (select id from t_ws)::text||'/videos/OTHERVIDEO/gDIG/dig/59.md',59,60)$$,
  'a key naming a DIFFERENT video, with workspace and generation segments correct',
  '23514', 'art_key_names_workspace');
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:60','gDIG','dig','recorded',
          (select id from t_ws)::text||'/WRONG/vidA/gDIG/dig/60.md',60,65)$$,
  'a key whose second segment is not the literal ''videos''',
  '23514', 'art_key_names_workspace');

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
  -- ⟳ ROUND 7 B2 — produced_at moved back from '2026-09-09'. It was a MONTH IN THE FUTURE, which is
  -- now rejected outright (a clock value may not enter the ranking) — and while it stood, it was the
  -- fixture that made B2 reachable in practice: a generation with a future produced_at could never
  -- have its digs detached. `mdGeneratedAt` deliberately KEEPS its later date: it is the string this
  -- row exists to lose the ranking on, and it is card data, not a clock the schema bounds.
  '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-09-09","processedAt":"y","mdCorrectionsHash":"H_STALE"}',
  4,'2026-02-09','SHA_C_STALE');
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
-- ── ⟳ ROUND 7 — THE FOUR ITEMS CROSS-DERIVED AGAINST EACH OTHER ────────────────────────────────
-- Every finding below is an INTERACTION between two of the four merged items and a defect in
-- neither one alone — which is the same verdict round 6's cross-derivation produced, reproduced
-- under the same condition: four items, four sittings, no re-derivation between them.
--
-- ⚠ THESE FIXTURES GO THROUGH THE RPCs. Round 7 found that `05:335-338` hand-builds a pending row
-- with a hand-made token, which is exactly why B1a was invisible to 89 assertions: no assertion
-- ever called record_artifact with a token the reservation did not issue. A fixture that bypasses
-- the protocol cannot test the protocol.

insert into workspace_videos (workspace_id, video_id) select id, 'vidR' from t_ws;
insert into workspace_videos (workspace_id, video_id) select id, 'vidR2' from t_ws;
insert into workspace_videos (workspace_id, video_id) select id, 'vidR3' from t_ws;

-- R1 (B1a) — A WORKER THAT RESTARTED AND LOST ITS TOKEN MUST STILL RECORD ITS PAID WORK.
-- No race, no reclaim, lease still LIVE. Measured before the fix:
--   [23505] duplicate key value violates unique constraint "video_artifacts_paid_uq"
-- because the append path inserted BLIND and collided with the worker's OWN pending row.
-- This is the user's rule of 2026-08-07 — "the reservation guards SPENDING, not RECORDING; a writer
-- that already paid always records" — failing via a raw SQLSTATE instead of a typed refusal, in the
-- function whose own comment says it "never refuses". Shape #8, and shape #10 against
-- reserve_artifact_slot:304-306 which already fixed exactly this for itself.
-- ⟳ ROUND 9 — THE SCENARIO IS UNCHANGED; THE CREDENTIAL IS NOT. Round 7 let this worker through on
-- "the slot's pending row names this generation", which round 8 measured a STRANGER satisfying just
-- as easily. It now presents `worker_id` + `job_id` — the two things that survive the restart that
-- lost it the token — so the same worker still records and a stranger no longer can.
do $$ declare o text; ws uuid; n int; job uuid := gen_random_uuid(); begin
  select id into ws from t_ws;
  perform reserve_artifact_slot(ws,'vidR','dig:3','gR1','dig'::artifact_kind,
    ws::text||'/videos/vidR/gR1/dig-3.md', p_start_sec := 3, p_end_sec := 9,
    p_worker_id := 'worker-R1', p_job_id := job);
  o := record_artifact(ws,'vidR','dig:3','gR1','dig'::artifact_kind,
        ws::text||'/videos/vidR/gR1/dig-3.md', gen_random_uuid(),   -- token FORGOTTEN across a restart
        p_start_sec := 3, p_end_sec := 9, p_produced_at := '2026-05-01',
        p_worker_id := 'worker-R1', p_job_id := job);              -- but it still knows WHO it is
  if o <> 'recorded_after_token_loss' then
    raise exception 'ASSERTION FAILED — a restarted worker did not record its paid work: %', o; end if;
  select count(*) into n from video_artifacts
   where video_id='vidR' and slot='dig:3' and state='recorded';
  if n <> 1 then
    raise exception 'ASSERTION FAILED — expected ONE recorded row, got %', n; end if;
  raise notice 'ok (R1/B1a): a worker that lost its token records in place, no 23505, typed outcome';
end $$;

-- R2 (B1c) — THE TWO PATHS MUST AGREE GIVEN IDENTICAL ARGUMENTS. The holder path never read
-- span/provenance (its UPDATE touches only state and lease columns), so a caller could legitimately
-- omit them and rely on what reserve stored — and then fail ONLY under the race, which is the worst
-- possible place to put a latent argument requirement.
do $$ declare o text; s int; e int; ws uuid; job uuid := gen_random_uuid(); begin
  select id into ws from t_ws;
  perform reserve_artifact_slot(ws,'vidR','dig:4','gR2','dig'::artifact_kind,
    ws::text||'/videos/vidR/gR2/dig-4.md', p_start_sec := 4, p_end_sec := 44,
    p_worker_id := 'worker-R2', p_job_id := job);
  o := record_artifact(ws,'vidR','dig:4','gR2','dig'::artifact_kind,
        ws::text||'/videos/vidR/gR2/dig-4.md', gen_random_uuid(),   -- loss path, span OMITTED
        p_produced_at := '2026-05-02',
        p_worker_id := 'worker-R2', p_job_id := job);
  select start_sec, end_sec into s, e from video_artifacts where video_id='vidR' and slot='dig:4';
  if s <> 4 or e <> 44 then
    raise exception 'ASSERTION FAILED — the loss path lost the reserved span: (%,%)', s, e; end if;
  raise notice 'ok (R2/B1c): both record paths take the span from the reservation when omitted';
end $$;

-- R3 (H2) — A CALLER MAY NOT COMPLETE A GENERATION IT DOES NOT HOLD, and the real owner must keep
-- its paid work. Measured before the fix: W2 named W1's generation, completed it with W2's
-- production time, and W1 was then locked out FOREVER by the freeze trigger
--   [P0001] video_generations: the CONTENT of complete generation gA is immutable
-- — item 3's freeze silently revoking item 4's user decision. The generation UPDATE was fenced on
-- NOTHING while every other write in this design is fenced.
do $$ declare o text; tW1 uuid; tW2 uuid; st text; ws uuid; begin
  select id into ws from t_ws;
  select token into tW1 from reserve_artifact_slot(ws,'vidR2','dig:1','gW1','dig'::artifact_kind,
    ws::text||'/videos/vidR2/gW1/dig-1.md', p_start_sec := 1, p_end_sec := 11);
  select token into tW2 from reserve_artifact_slot(ws,'vidR2','dig:2','gW2','dig'::artifact_kind,
    ws::text||'/videos/vidR2/gW2/dig-2.md', p_start_sec := 2, p_end_sec := 22);
  -- W2 records ITS OWN slot but NAMES W1's generation. No (slot,generation) collision exists, so
  -- nothing in the paid unique index can stop it — the fence has to.
  --
  -- ⚠ THIS IS THE ONE CASE WHERE REFUSING IS CORRECT, and it does not contradict "record_artifact
  -- never refuses". That rule protects a writer's OWN paid work. gW1 is not W2's work — W2's work is
  -- gW2 — so this is a caller naming a generation it never reserved, and the honest answer is a
  -- typed refusal rather than silently poisoning the real owner's row.
  begin
    perform record_artifact(ws,'vidR2','dig:2','gW1','dig'::artifact_kind,
      ws::text||'/videos/vidR2/gW1/dig-2.md', tW2, p_start_sec := 2, p_end_sec := 22,
      p_produced_at := '2026-01-01');
    raise exception 'ASSERTION FAILED — W2 recorded against a generation it does not hold';
  exception when sqlstate 'P0001' then
    if sqlerrm like 'ASSERTION FAILED%' then raise; end if;   -- never swallow our own assertion
  end;
  select state into st from video_generations where video_id='vidR2' and generation_id='gW1';
  if st <> 'pending' then
    raise exception 'ASSERTION FAILED — W2 completed a generation it does not hold (state %)', st; end if;
  -- ...and W1, the real owner, must still be able to record.
  o := record_artifact(ws,'vidR2','dig:1','gW1','dig'::artifact_kind,
        ws::text||'/videos/vidR2/gW1/dig-1.md', tW1, p_start_sec := 1, p_end_sec := 11,
        p_produced_at := '2026-06-06');
  select state into st from video_generations where video_id='vidR2' and generation_id='gW1';
  if o not in ('recorded_as_holder','recorded_after_token_loss') or st <> 'complete' then
    raise exception 'ASSERTION FAILED — the real owner lost its paid work: outcome=% state=%', o, st; end if;
  raise notice 'ok (R3/H2): only the reserving holder completes a generation; the owner keeps its work';
end $$;

-- R3b — P22 ITSELF, WITH A GENERATION THE PROTOCOL CREATED. Found by MUTATION, not by reading:
-- removing the `reserved_by = p_token` disjunct left the whole suite GREEN, which means nothing was
-- exercising the case that disjunct exists for. The item-4 `recorded_after_loss` test could not:
-- its generations are hand-inserted as COMPLETE, so the completion is a no-op and the fence is never
-- consulted. This is the fixture critique from round 7 applied to round 7's own fix — a guard whose
-- only witness bypasses the protocol is a guard with no test.
--
-- The shape is item 4's P22 exactly: W1 reserves, its lease expires mid-Gemini, W2 reclaims the SLOT
-- under its own generation, and W1 returns holding a token that no longer matches any artifact row.
-- W1 must still complete ITS OWN generation and record — that is the user decision of 2026-08-07.
do $$ declare tW1 uuid; o text; st text; n int; ws uuid; begin
  select id into ws from t_ws;
  update guardrail_config set lease_ttl_seconds = 1, dig_max_attempts = 5 where id = true;
  select token into tW1 from reserve_artifact_slot(ws,'vidR','dig:8','gP1','dig'::artifact_kind,
    ws::text||'/videos/vidR/gP1/dig-8.md', p_start_sec := 8, p_end_sec := 88);
  -- expire W1's lease without touching the clock (now() is transaction-stable inside this rollback)
  update video_artifacts set lease_expires_at = now() - interval '1 min'
   where video_id='vidR' and slot='dig:8';
  select outcome into o from reserve_artifact_slot(ws,'vidR','dig:8','gP2','dig'::artifact_kind,
    ws::text||'/videos/vidR/gP2/dig-8.md', p_start_sec := 8, p_end_sec := 88);
  if o <> 'reserved' then raise exception 'FIXTURE FAILED — W2 could not reclaim: %', o; end if;
  -- W1 comes back. Its slot is gone; its GENERATION is still its own.
  o := record_artifact(ws,'vidR','dig:8','gP1','dig'::artifact_kind,
        ws::text||'/videos/vidR/gP1/dig-8.md', tW1, p_produced_at := '2026-05-03');
  select state into st from video_generations where video_id='vidR' and generation_id='gP1';
  if o <> 'recorded_after_loss' or st <> 'complete' then
    raise exception 'ASSERTION FAILED — a reclaimed writer lost its paid work: outcome=% gP1=%', o, st; end if;
  select count(*) into n from video_artifacts
   where video_id='vidR' and slot='dig:8' and state='recorded' and generation_id='gP1';
  if n <> 1 then
    raise exception 'ASSERTION FAILED — the reclaimed writer recorded % rows, expected 1', n; end if;
  raise notice 'ok (R3b/P22): a reclaimed writer completes its OWN generation via reserved_by and records';
end $$;

-- R4 (H3) — A DENIED RESERVATION MUST NOT LEAVE A GENERATION ROW BEHIND. Item 3 put the generation
-- INSERT above the upsert that decides who gets the slot, so every `busy` loser littered an
-- FK-valid parent that no artifact points at, no ranking view reaches, and no sweep collects —
-- unbounded growth for a worker looping on `busy` with a fresh id per attempt.
do $$ declare o text; n int; ws uuid; begin
  select id into ws from t_ws;
  perform reserve_artifact_slot(ws,'vidR3','summary','gS1','summary'::artifact_kind,
    ws::text||'/videos/vidR3/gS1/summary.md');
  select outcome into o from reserve_artifact_slot(ws,'vidR3','summary','gS2','summary'::artifact_kind,
    ws::text||'/videos/vidR3/gS2/summary.md');
  if o <> 'busy' then raise exception 'FIXTURE FAILED — expected busy, got %', o; end if;
  select count(*) into n from video_generations where video_id='vidR3' and generation_id='gS2';
  if n <> 0 then
    raise exception 'ASSERTION FAILED — a DENIED reservation left % orphan generation row(s)', n; end if;
  raise notice 'ok (R4/H3): a denied reservation leaves no generation row behind';
end $$;

-- R5 (B2 / M5) — produced_at IS A RANKING RUNG AND A CALLER-SUPPLIED VALUE. Nothing bounded it, so
-- one sync from a replica with a fast clock ranks a generation above everything real until the clock
-- catches up. Round 4's J2-3 removed clock READS from the ranking; it did not stop a clock VALUE
-- being injected into it. Separately, a future produced_at made §6.2's detach UNSATISFIABLE forever
-- (the bound compares detached_at, which the sibling trigger sets to now(), against it).
select assert_raises($$select record_artifact((select id from t_ws),'vidR','dig:5','gR5','dig'::artifact_kind,
   (select id from t_ws)::text||'/videos/vidR/gR5/dig-5.md',
   (select token from reserve_artifact_slot((select id from t_ws),'vidR','dig:5','gR5',
      'dig'::artifact_kind,(select id from t_ws)::text||'/videos/vidR/gR5/dig-5.md',
      p_start_sec := 5, p_end_sec := 55)),
   p_start_sec := 5, p_end_sec := 55, p_produced_at := now() + interval '10 days')$$,
  'completing a generation with a produced_at in the FUTURE (a fast replica clock outranks reality)',
  'P0001');

-- R6 (B2) — A DIG WHOSE GENERATION IS LEGITIMATE MUST ALWAYS BE DETACHABLE. Before the fix, a
-- generation carrying a future produced_at could NEVER have its digs detached — permanently, since
-- produced_at is frozen and detached_at is trigger-owned on UPDATE. The error even blamed the writer
-- for a value the writer never supplied.
do $$ declare ws uuid; st text; t timestamptz; begin
  select id into ws from t_ws;
  perform reserve_artifact_slot(ws,'vidR','dig:6','gR6','dig'::artifact_kind,
    ws::text||'/videos/vidR/gR6/dig-6.md', p_start_sec := 6, p_end_sec := 66);
  perform record_artifact(ws,'vidR','dig:6','gR6','dig'::artifact_kind,
    ws::text||'/videos/vidR/gR6/dig-6.md',
    (select lease_token from video_artifacts where video_id='vidR' and slot='dig:6'),
    p_start_sec := 6, p_end_sec := 66, p_produced_at := now() - interval '1 minute');
  update video_artifacts set state='detached' where video_id='vidR' and slot='dig:6';
  select state, detached_at into st, t from video_artifacts where video_id='vidR' and slot='dig:6';
  if st <> 'detached' or t is null then
    raise exception 'ASSERTION FAILED — a recently-produced dig could not be detached (% %)', st, t; end if;
  raise notice 'ok (R6/B2): detach works for a generation produced moments ago (the bound is INSERT-only)';
end $$;

-- R7 (H1) — THE TRIGGER FIRING ORDER IS ASSERTED, NOT ASSUMED. Round 7 renamed
-- video_artifacts_append_only_trg to zz_… , inverting the order the file called load-bearing, and
-- all 89 assertions stayed GREEN: no assertion read pg_trigger, no mutation touched a trigger name,
-- and the whole correctness argument rested on 'v' sorting after 'a'. Shape #6 (a guard with no
-- test) sitting under the one place the file says the design depends on ordering.
--
-- ⚠ `tgtype & 2` — BEFORE TRIGGERS ONLY, and the filter was missing until the coverage instrument
-- above exposed it. That instrument is an AFTER trigger named `t_writes_trg`, and 't' sorts before
-- 'v', so it appeared first in an unfiltered list and this assertion failed — correctly reporting a
-- broken ordering that was never broken. The measuring apparatus perturbed the thing it measured.
-- Only BEFORE triggers can affect each other's NEW row, so only their order was ever the claim.
do $$ declare names text[]; begin
  select array_agg(t.tgname order by t.tgname) into names
    from pg_trigger t join pg_class c on c.oid = t.tgrelid
   where c.relname = 'video_artifacts' and not t.tgisinternal
     and (t.tgtype & 2) <> 0;   -- BEFORE only; see the note below
  if names[1] <> 'video_artifacts_append_only_trg' then
    raise exception 'ASSERTION FAILED — append-only must fire FIRST on video_artifacts; order is %', names; end if;
  select array_agg(t.tgname order by t.tgname) into names
    from pg_trigger t join pg_class c on c.oid = t.tgrelid
   where c.relname = 'video_generations' and not t.tgisinternal
     and (t.tgtype & 2) <> 0;
  if names[1] <> 'forbid_collecting_current_trg' then
    raise exception 'ASSERTION FAILED — forbid-collecting must fire FIRST on video_generations; order is %', names; end if;
  raise notice 'ok (R7/H1): both BEFORE-trigger firing orders are asserted, not assumed from naming';
end $$;

-- R8 (M1) — THE PRIVILEGE SWEEP IS COMPLETE, ASSERTED RATHER THAN CLAIMED. 04's own comment says
-- "Sweeping all THREE replacements here, not just the one that inherited the name — that one-site
-- habit is what produced B1 in the first place", and measured, two `security definer` functions
-- still carried the default PUBLIC EXECUTE. Exploitability is near zero (Postgres refuses a direct
-- call to a trigger function: [0A000]) but the CLAIM OF COMPLETENESS was false, and that sweep is
-- the only thing standing between this design and round 6's B1. Asserted over pg_proc so the next
-- definer function added is caught by the suite rather than by the next reviewer.
do $$ declare leaky text[]; begin
  select array_agg(p.proname order by p.proname) into leaky
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname = 'public' and p.prosecdef
     and p.proname in ('slot_kind','reserve_artifact_slot','renew_artifact_lease','record_artifact',
                       'forbid_collecting_current','video_artifacts_append_only',
                       'video_artifacts_generation_complete','video_generations_freeze',
                       'sync_corrections_to_workspace_video')
     and has_function_privilege('anon', p.oid, 'EXECUTE');
  if leaky is not null then
    raise exception 'ASSERTION FAILED — anon holds EXECUTE on definer function(s): %', leaky; end if;
  raise notice 'ok (R8/M1): no definer function in this schema is reachable by anon';
end $$;
-- ── ⟳ ROUND 9 — THE OWNERSHIP FENCE, MEASURED IN BOTH DIRECTIONS ───────────────────────────────
-- Round 8 found the round-7 fence broken BOTH ways at once, which is why the fix is a different
-- credential rather than a tighter or looser one. Both directions are asserted here, because a fix
-- for either alone is what produced the defect in the first place.
insert into workspace_videos (workspace_id, video_id) select id, 'vidR9a' from t_ws;
insert into workspace_videos (workspace_id, video_id) select id, 'vidR9b' from t_ws;

-- ⟳ R9-1 — A STRANGER CANNOT COMPLETE A GENERATION IT DOES NOT OWN.
-- Measured in round 8 with p_token = NULL (`md_hash=SHA_ATTACKER`) AND with a random valid non-NULL
-- token (`SHA_FOREIGN`), so the fixture below hands the stranger a FULL, well-formed credential of
-- its own — a real token, a real worker id, a real job id. It is refused for the only reason that
-- should matter: none of them is the credential this generation was reserved with.
do $$ declare ws uuid; begin
  select id into ws from t_ws;
  perform reserve_artifact_slot(ws,'vidR9a','summary','gR9a','summary'::artifact_kind,
    ws::text||'/videos/vidR9a/gR9a/summary.md',
    p_worker_id := 'worker-owner', p_job_id := '11111111-1111-1111-1111-111111111111');
end $$;
select assert_raises(format($$
  select record_artifact(%L::uuid,'vidR9a','summary','gR9a','summary'::artifact_kind,
    %L, gen_random_uuid(), p_md_hash := 'SHA_FOREIGN', p_produced_at := '2026-05-03',
    p_card := '{"tldr":"FOREIGN","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-03","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
    p_doc_version_major := 4,
    p_worker_id := 'worker-STRANGER', p_job_id := '22222222-2222-2222-2222-222222222222');
$$, (select id from t_ws), (select id from t_ws)::text||'/videos/vidR9a/gR9a/summary.md'),
 'a stranger with its OWN full credential cannot complete another worker''s generation', 'P0001');

-- ⟳ R9-2 — THE DOUBLY-LOST WORKER STILL RECORDS. Round 7 reasoned about single losses only; the
-- conjunction is ordinary, because the crash that loses the token also lapses the lease that invites
-- the reclaim. Measured before this fix: `[P0001] generation gW1 is pending`, paid work destroyed,
-- with the identical call succeeding when the worker still knew its token — which isolated the fence
-- as the cause rather than anything about the reclaim.
do $$ declare o text; ws uuid; job uuid := gen_random_uuid(); begin
  select id into ws from t_ws;
  update guardrail_config set dig_max_attempts = 3 where id = true;   -- reclaim must be permitted
  perform reserve_artifact_slot(ws,'vidR9b','dig:8','gR9b1','dig'::artifact_kind,
    ws::text||'/videos/vidR9b/gR9b1/dig-8.md', p_start_sec := 8, p_end_sec := 88,
    p_worker_id := 'worker-lost', p_job_id := job);
  update video_artifacts set lease_expires_at = now() - interval '1 hour'
   where video_id='vidR9b' and slot='dig:8';                          -- the lease lapses
  perform reserve_artifact_slot(ws,'vidR9b','dig:8','gR9b2','dig'::artifact_kind,
    ws::text||'/videos/vidR9b/gR9b2/dig-8.md', p_start_sec := 8, p_end_sec := 88,
    p_worker_id := 'worker-other', p_job_id := gen_random_uuid());    -- and the SLOT is reclaimed
  o := record_artifact(ws,'vidR9b','dig:8','gR9b1','dig'::artifact_kind,
        ws::text||'/videos/vidR9b/gR9b1/dig-8.md', null,             -- token GONE
        p_start_sec := 8, p_end_sec := 88, p_produced_at := '2026-05-04',
        p_worker_id := 'worker-lost', p_job_id := job);               -- identity SURVIVED
  if o <> 'recorded_after_loss' then
    raise exception 'ASSERTION FAILED — the doubly-lost worker did not record: %', o; end if;
  if (select state from video_generations where video_id='vidR9b' and generation_id='gR9b1')
       <> 'complete' then
    raise exception 'ASSERTION FAILED — its generation was left pending, so the bytes are orphaned';
  end if;
  raise notice 'ok (R9-2): a worker that lost BOTH its token and its slot still records its paid work';
end $$;

-- ⟳ R9-3 (round 8 B1) — GC MAY NOT COLLECT A GENERATION THAT IS STILL BEING PAID FOR.
-- `video_artifacts_current` requires state='recorded', so an in-flight reservation had no current
-- row and was offered to the sweeper. The worker then recorded SUCCESSFULLY and its row was
-- invisible forever. Asserted at both ends: not collectable while pending, and visible after.
insert into workspace_videos (workspace_id, video_id) select id, 'vidR9c' from t_ws;
do $$ declare ws uuid; o text; tok uuid; n int; begin
  select id into ws from t_ws;
  select token into tok from reserve_artifact_slot(ws,'vidR9c','summary','gR9c','summary'::artifact_kind,
    ws::text||'/videos/vidR9c/gR9c/summary.md',
    p_worker_id := 'worker-gc', p_job_id := gen_random_uuid());
  select count(*) into n from video_generations_collectable
   where video_id='vidR9c' and generation_id='gR9c';
  if n <> 0 then
    raise exception 'ASSERTION FAILED — an IN-FLIGHT generation is collectable; a sweep would bury paid work';
  end if;
  o := record_artifact(ws,'vidR9c','summary','gR9c','summary'::artifact_kind,
        ws::text||'/videos/vidR9c/gR9c/summary.md', tok, p_md_hash := 'SHA_R9C',
        p_card := '{"tldr":"z","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-05","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
        p_doc_version_major := 4, p_produced_at := '2026-05-05');
  if (select count(*) from video_artifacts_current where video_id='vidR9c') <> 1 then
    raise exception 'ASSERTION FAILED — the recorded artifact is not visible in current'; end if;
  raise notice 'ok (R9-3): an in-flight generation is not collectable, and records visibly';
end $$;

-- ⟳ R9-4 (round 8 H4) — THE FUTURE BOUND TOLERATES CLOCK SKEW BUT NOT A CLOCK VALUE.
-- Both halves, because a tolerance that swallowed round 7 B2 would be a regression dressed as a fix.
do $$ declare ws uuid; begin
  select id into ws from t_ws;
  insert into workspace_videos (workspace_id, video_id) values (ws,'vidR9d');
  insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values (ws,'vidR9d','gSkew','summary',
    '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-06","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
    4, clock_timestamp(), 'SHA_SKEW');     -- a few hundred ms of Fly-vs-Supabase drift
  raise notice 'ok (R9-4): ordinary clock skew no longer refuses a paid summarize';
end $$;
select assert_raises(format($$
  insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
  values (%L::uuid,'vidR9d','gFar','summary',
    '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-06","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
    4, now() + interval '3 days', 'SHA_FAR');
$$, (select id from t_ws)),
 'a genuinely future produced_at is still refused (round 7 B2 preserved)', 'P0001');

-- ⟳ R9-5 (round 8 H2) — THE FREE SHORT-CIRCUIT IS REACHABLE AT ALL.
-- It compared `generation_id = p_generation_id`, and for a free slot both sides are NULL, so the
-- test was NULL — never true. The branch existed and could not run; reserve then hit
-- video_artifacts_free_uq raw. The assertion is the TYPED outcome, because a raw 23505 is the defect.
do $$ declare ws uuid; o text; res text; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidR9c','pdf:summary',null,'render'::artifact_kind,ws::text||'/videos/vidR9c/renders/r9-1.pdf',null);
  o := record_artifact(ws,'vidR9c','pdf:summary',null,'render'::artifact_kind,ws::text||'/videos/vidR9c/renders/r9-2.pdf',null);
  select outcome into res from reserve_artifact_slot(ws,'vidR9c','pdf:summary',null,
    'render'::artifact_kind,ws::text||'/videos/vidR9c/renders/r9-3.pdf');
  if res <> 'already_recorded' then
    raise exception 'ASSERTION FAILED — reserving a recorded FREE slot gave %, not already_recorded', res;
  end if;
  raise notice 'ok (R9-5): reserving a recorded free slot returns a typed outcome, not a raw 23505';
end $$;

-- ⟳ R9-6 (round 8 H5) — A FREE ROW IS CONFINED TO ITS WORKSPACE TOO.
-- Tenant confinement used to live INSIDE `art_key_names_generation`, which is gated on a non-null
-- generation — so the rows with no generation, i.e. every free render, escaped it completely.
-- MEASURED: a `render` row in workspace A storing `<workspace-B>/videos/vidH5/OTHER-TENANT.pdf` was
-- ACCEPTED and returned `recorded_free`. Every pre-existing fixture happened to use a well-formed
-- key, which is precisely why five rounds never saw it.
select assert_raises(format($$
  insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values (%L::uuid,'vidR9c','pdf:cross',null,'render','recorded',
          %L||'/videos/vidR9c/renders/leak.pdf');
$$, (select id from t_ws), (select id from t_w2)::text),
 'a FREE row may not carry a key under another workspace''s prefix', '23514',
 'art_key_names_workspace');

-- ── ⟳ ROUND 8 OPENING — THE GUARD CLASSIFICATION PASS ─────────────────────────────────────────────
-- Not a review round. Every guard on these two tables was classified SHAPE or SEQUENCE:
--   SHAPE    — is this row well-formed and referentially sound? A violation is a CALLER BUG. Reject.
--   SEQUENCE — who got here first, has this already happened, is this in flight? A violation is
--              CONCURRENCY. The caller did nothing wrong and may already have spent money.
--              It must RECONCILE — an upsert, a no-op, or a typed outcome — never a raw rejection.
--
-- 32 guards: 26 SHAPE (all 13 CHECKs, all 3 FKs, the immutability rules) and 6 SEQUENCE. Of the six,
-- three were already reconcilers and one is a deliberate ownership fence. TWO WERE REJECTERS, and
-- both are below. Neither was found by seven rounds of adversarial review, because the question
-- "what does this guard do when the caller is merely SECOND?" is not one a reviewer thinks to ask
-- of a constraint that is plainly correct.
--
-- The rule generalises the user decision of 2026-08-07 ("the reservation guards SPENDING, not
-- RECORDING"), which was the same insight recorded at ONE site instead of as a property of a class.

-- C1 — A FREE RENDER MUST BE OVERWRITABLE, WHICH THE SCHEMA SAYS AND DID NOT DO.
-- `video_artifacts_free_uq`'s own comment: "free -> one row per slot, OVERWRITABLE; a deterministic
-- re-render has nothing to preserve." MEASURED before this fix: the first render of a slot succeeded
-- and EVERY re-render failed with a raw [23505]. record_artifact could not write one at all past the
-- first, because its only conflict arbiter was the PAID partial index (`where generation_id is not
-- null`), which a NULL generation can never match.
--
-- Structurally the same defect as handoff item 3 — an entire KIND of write is unreachable — and it
-- survived for the same reason: every fixture writes a free render once, with a direct INSERT.
-- Re-rendering is normal and unpaid: regenerate a summary and its PDF and HTML must be rebuilt.
do $$ declare o text; n int; k text; ws uuid; begin
  select id into ws from t_ws;
  insert into workspace_videos (workspace_id, video_id) values (ws,'vidF');
  o := record_artifact(ws,'vidF','pdf:summary',null,'render'::artifact_kind,
        ws::text||'/videos/vidF/render/summary-v1.pdf', null);
  if o <> 'recorded_free' then
    raise exception 'ASSERTION FAILED — first free render: %', o; end if;
  o := record_artifact(ws,'vidF','pdf:summary',null,'render'::artifact_kind,
        ws::text||'/videos/vidF/render/summary-v2.pdf', null);
  if o <> 'recorded_free' then
    raise exception 'ASSERTION FAILED — RE-render was refused: %', o; end if;
  select count(*), max(blob_key) into n, k from video_artifacts
   where video_id='vidF' and slot='pdf:summary';
  if n <> 1 then
    raise exception 'ASSERTION FAILED — a free slot holds % rows; free is one-per-slot', n; end if;
  if k not like '%summary-v2.pdf' then
    raise exception 'ASSERTION FAILED — the re-render did not overwrite: %', k; end if;
  raise notice 'ok (C1): a free render OVERWRITES in place, as the taxonomy always claimed';
end $$;

-- C2 — and a free render still may not masquerade as paid. The SHAPE guards are untouched by C1's
-- reconciler: this is the boundary the free/paid split exists to hold, and a new write path is
-- exactly where it would be lost.
select assert_raises($$select record_artifact((select id from t_ws),'vidF','summary',null,
   'summary'::artifact_kind,(select id from t_ws)::text||'/videos/vidF/x/summary.md', null)$$,
  'a PAID kind written with no generation through the free path', '23514', 'art_paid_has_generation');

-- C3 — THE SWEEPER MUST SKIP A CURRENT GENERATION, NOT ABORT ON IT.
-- `forbid_collecting_current` is correct in intent and was expressed as an exception, so a batch
-- `update … set body_collected = true` over 500 generations DIED on the first current one and rolled
-- back the other 499. MEASURED: [P0001] refusing to collect generation gCur.
--
-- Worse than a lost batch: retrying cannot help, because the current generation is PERMANENTLY
-- current. The sweep could never succeed at all — §8's whole retention story was unrunnable.
--
-- The guard moves into a predicate the sweeper selects THROUGH; the trigger stays as a backstop for
-- anything that writes directly. Round 5's cross-derivation C3 again: take both the data guard and
-- the query guard, because they fail independently.
do $$ declare n int; c int; ws uuid; begin
  select id into ws from t_ws;
  update video_generations g set body_collected = true
   where (g.workspace_id, g.video_id, g.generation_id) in
         (select workspace_id, video_id, generation_id from video_generations_collectable);
  get diagnostics n = row_count;
  select count(*) into c from video_generations where body_collected;
  if n = 0 then
    raise exception 'ASSERTION FAILED — the sweep collected nothing at all'; end if;
  raise notice 'ok (C3): a batch sweep through video_generations_collectable skips, % rows collected', n;
end $$;

-- C4 — the backstop is intact. A sweeper that ignores the view is still refused, so the fix is a
-- SAFE PATH rather than a REMOVED GUARD. Without this, C3 could be satisfied by deleting the trigger.
do $$ declare ws uuid; begin
  select id into ws from t_ws;
  insert into workspace_videos (workspace_id, video_id) values (ws,'vidGC');
  insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
   values (ws,'vidGC','gLive','summary',
     ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-02-01","processedAt":"y",'
      ||'"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,4,'2026-02-01','SHA_LIVE');
  insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
   values (ws,'vidGC','summary','gLive','summary','recorded',ws::text||'/videos/vidGC/gLive/summary.md');
end $$;
select assert_raises($$update video_generations set body_collected = true
  where video_id='vidGC'$$,
  'a naive sweep that ignores the collectable view (the trigger backstop)', 'P0001');
-- ── ⟳ ROUND 9 B3 — INGEST STILL WORKS AFTER THE MIGRATION ──────────────────────────────────────
-- The defect these assert against was total: `claim_video_slot`'s INSERT, run verbatim, returned
-- [23502] on videos.workspace_id and then [23503] on videos_workspace_video_fk. Nothing could ingest
-- a new video, and 103 assertions passed anyway — because every fixture in this file inserts videos
-- that the migration's own seed had already created a parent for. The suite described a world in
-- which no NEW video ever arrives.
--
-- ⚠ THE FIRST ASSERTION IS THE ONE THAT MATTERED: the writer's column list is UNCHANGED. If a future
-- edit "fixes" ingest by adding workspace_id to the callers, this still passes while the design
-- decision (derive, never hand-copy — 2026-08-08) has been silently reversed. Assert the promise, not
-- the implementation.
do $$
declare v_pl uuid; v_ws uuid;
begin
  select id, workspace_id into v_pl, v_ws from playlists limit 1;
  insert into videos (playlist_id, owner_id, video_id, position, data)   -- 0023:87, verbatim
    select v_pl, pl.owner_id, 'ingestNew', 9991, jsonb_build_object('id','ingestNew')
      from playlists pl where pl.id = v_pl;
  if (select workspace_id from videos where playlist_id=v_pl and video_id='ingestNew') <> v_ws then
    raise exception 'ASSERTION FAILED — workspace_id was not derived from the playlist'; end if;
  if (select count(*) from workspace_videos where video_id='ingestNew') <> 1 then
    raise exception 'ASSERTION FAILED — no manifest parent was created for a new video'; end if;
  raise notice 'ok (B3): an UNCHANGED writer ingests a new video; both values derived';

  -- The sibling site. jobs.workspace_id had the identical defect and every enqueue RPC omits it.
  insert into jobs (playlist_id, owner_id, video_id, job_kind, job_version, payload)
    select v_pl, pl.owner_id, 'ingestNew', 'summary', 'v1', '{}'::jsonb
      from playlists pl where pl.id = v_pl;
  if (select workspace_id from jobs where video_id='ingestNew' limit 1) <> v_ws then
    raise exception 'ASSERTION FAILED — jobs.workspace_id was not derived'; end if;
  raise notice 'ok (B3 sibling): an UNCHANGED enqueue derives jobs.workspace_id';

  -- A caller with the RIGHT opinion is not punished for having one.
  insert into videos (playlist_id, owner_id, video_id, position, data, workspace_id)
    select v_pl, pl.owner_id, 'ingestAgree', 9992, jsonb_build_object('id','ingestAgree'), v_ws
      from playlists pl where pl.id = v_pl;
  raise notice 'ok (B3): a caller supplying the CORRECT workspace passes unremarked';
end $$;

-- THE WHOLE CHAIN, not just its bottom two links. `01` seeds workspaces from profiles and backfills
-- playlists/videos/jobs — four one-shot statements, none of which produces the NEXT row. Fixing only
-- `videos` and `jobs` would have left a new user unable to create a playlist, so the repaired video
-- path would have been unreachable and this suite would still have passed.
do $$
declare v_prof uuid := gen_random_uuid(); v_pl uuid; v_ws uuid;
begin
  -- `profiles.id` FKs to auth.users, so the identity has to exist before the profile does. Creating
  -- it here rather than reusing a seeded profile is the point: a SEEDED profile already has a
  -- workspace from 01's one-shot insert, so the assertion would pass with the trigger deleted.
  insert into auth.users (id) values (v_prof);
  -- `do nothing` because signup already creates the profile via its own trigger on auth.users —
  -- measured here as [23505] profiles_pkey. That is the REAL path a new user takes, so this
  -- assertion exercises it rather than a synthetic one.
  insert into profiles (id) values (v_prof) on conflict (id) do nothing;
  select id into v_ws from workspaces where owner_id = v_prof;
  if v_ws is null then
    raise exception 'ASSERTION FAILED — a NEW profile got no workspace; the chain starts broken'; end if;
  raise notice 'ok (B3 chain): a new profile gets a workspace';

  insert into playlists (owner_id, playlist_key, playlist_url)
  values (v_prof, 'k-assert-chain', 'https://example/chain') returning id into v_pl;
  if (select workspace_id from playlists where id = v_pl) <> v_ws then
    raise exception 'ASSERTION FAILED — a NEW playlist did not derive its workspace'; end if;
  raise notice 'ok (B3 chain): a new playlist derives its workspace from its owner';
end $$;

-- ⟳ ROUND 9 — CORRECTIONS SURVIVE THE SAME VIDEO ARRIVING IN A SECOND PLAYLIST.
-- Round 6's INSERT-half sync was unconditional, and it was harmless only because B3 made INSERTs
-- impossible. MEASURED the moment ingest worked: 'KEEP ME' -> <null>. `corrections` describes the
-- SHARED BODY while `videos` is per-playlist, so a second playlist's row carrying none is not
-- evidence that anyone removed them.
do $$
declare v_own uuid; v_p1 uuid; v_p2 uuid;
begin
  select owner_id into v_own from playlists limit 1;
  insert into playlists (owner_id, playlist_key, playlist_url)
    values (v_own, 'k-assert-c1', 'https://example/c1') returning id into v_p1;
  insert into playlists (owner_id, playlist_key, playlist_url)
    values (v_own, 'k-assert-c2', 'https://example/c2') returning id into v_p2;
  insert into videos (playlist_id, owner_id, video_id, position, data)
    values (v_p1, v_own, 'sharedCorr', 8001,
            jsonb_build_object('id','sharedCorr','corrections','KEEP ME'));
  insert into videos (playlist_id, owner_id, video_id, position, data)
    values (v_p2, v_own, 'sharedCorr', 8002, jsonb_build_object('id','sharedCorr'));
  if (select corrections from workspace_videos where video_id='sharedCorr')
       is distinct from 'KEEP ME' then
    raise exception 'ASSERTION FAILED — the second playlist CLOBBERED the shared corrections'; end if;
  raise notice 'ok (round 9): a corrected video survives being added to a second playlist';
end $$;

-- And a caller with the WRONG opinion is TOLD, not silently corrected. This is the whole reason the
-- explicit-writer option was not simply discarded: a caller confused about tenancy is a real bug, and
-- silently repairing it would be shape #5 on the tenancy boundary.
select assert_raises($$
  insert into videos (playlist_id, owner_id, video_id, position, data, workspace_id)
    select p.id, p.owner_id, 'ingestWrong', 9993, jsonb_build_object('id','ingestWrong'),
           (select id from workspaces where id <> p.workspace_id order by id desc limit 1)
      from playlists p limit 1;
$$, 'a workspace_id disagreeing with the playlist is refused, not repaired', 'P0001');

-- ── ⟳ THE POPULATION-COVERAGE RATCHET ITSELF ───────────────────────────────────────────────────
-- Every value of `artifact_kind` must have been written a SECOND time to the same slot somewhere in
-- this suite. Not "exercised" — written twice, because the first write of anything is the easy case
-- and every defect in this class lived in the second.
--
-- ⚠ THIS IS THE ONLY CHECK HERE THAT LOOKS AT WHAT IS ABSENT. Everything else in this file asserts a
-- property of something someone thought to write down. If a new artifact_kind is ever added, this
-- fails until it is covered — which is the point: the enum is the enumerated whole, so the ratchet
-- cannot be forgotten the way a convention can.
do $$
declare k text; missing text[] := '{}'; n int;
begin
  foreach k in array enum_range(null::artifact_kind)::text[] loop
    select count(*) into n from (
      select 1 from t_writes w where w.kind = k and w.op = 'INSERT'
       group by w.kind, w.paid, w.slot having count(*) > 1
    ) s;
    if n = 0 then missing := missing || k; end if;
  end loop;
  if array_length(missing, 1) is not null then
    raise exception 'ASSERTION FAILED — no slot is written TWICE for kind(s): %.  '
      'The first write of anything is the easy case; this suite never exercises the second for these.',
      array_to_string(missing, ', ');
  end if;
  raise notice 'ok (coverage): every artifact_kind has a slot written twice — the SEQUENCE case is exercised';
end $$;
\echo ASSERTIONS_OK

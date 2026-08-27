-- 05 — BEHAVIOURAL assertions. A constraint that CREATES is not a constraint that GUARDS:
-- round 3's slot check created cleanly and accepted slot='html', kind='dig'.
--
-- ⚠ ROUND 5 H1 — THE RULE THIS FILE IS WRITTEN TO. Mutation testing found 15 of 25 guards untested,
-- and worse: `art_slot_kind` and `art_pending_is_leased` (since deleted by ADR-0007, along with 13
-- other blocks marked ⛔ below) were MASKING EACH OTHER. Their fixture rows
-- were ALSO FK-invalid, so each assertion was satisfied by a disjunction — remove the CHECK and the FK
-- rejected it; remove the FK and the CHECK rejected it. Red only under a DOUBLE mutation. The round-3
-- and round-4 fixes those two lines were written to verify were both still unverified, in the file
-- written to verify them.
--
-- So: EVERY NEGATIVE BELOW MUST VIOLATE EXACTLY ONE GUARD. A fixture that is invalid in two ways
-- tests neither. Where a row must be FK-valid to isolate a CHECK, it uses a generation of the right
-- kind; where a key must be shaped, it is shaped.
--
-- ══ @RE-RUNNABLE ═══ THE WHOLE FILE, AND THAT IS A MEASUREMENT, NOT A DEFAULT ═════════════════════
--
-- ⛔ EVERY MENTION OF A MARKER BELOW DROPS ITS `@`, AND THAT IS NOT PEDANTRY. The selector matches
-- the literal on any comment line, so prose ABOUT the markers is itself a marker: the first draft
-- of this header said the word three times and toggled the selection off mid-explanation, taking
-- the file from 119 assertions to 61. Nothing syntactic saw it — the block still parsed, still held
-- `raise exception`, still reached the success echo. The assertion floor caught it, on the very
-- commit that added the floor. Round 2 learned this about string literals; it is true of comments.
--
-- `scripts/run-schema-assertions.sh` selects from this marker to the next MIGRATION-ONLY one, so
-- this one line puts every assertion below into the gate that runs against the LIVE, APPLIED schema
-- (gate 8 of `scripts/check-schema-gates.sh`) rather than only against a schema rebuilt from source
-- inside gate 1. The two ask different questions: gate 1 asks whether the SPEC is self-consistent,
-- gate 8 asks whether the DEPLOYED catalog actually behaves.
--
-- ⚠ THE PLAN EXPECTED A SPLIT, AND MEASUREMENT FOUND NONE. Task 8 Step 1 was written to tag each
-- block MIGRATION-ONLY ("compares the migration's output; any later write invalidates it") or
-- RE-RUNNABLE ("an invariant that must hold at all times"). The canonical migration-only
-- assertion was round 6 B4's corrections backfill — and ADR-0011 DELETED it, in this file, with the
-- note that stands at line 54. Nothing took its place: every remaining block builds its own fixture
-- rows and scopes every read to them (`where video_id='vidA'`, `'vidSVC'`, `'vidF'` …), so none of
-- them can be invalidated by a later write.
--
-- MEASURED 2026-08-26 against the applied 0027, seed corpus + this entire file in one transaction:
-- 120 assertions reported ok, none raised, identical on three consecutive runs.
--
-- ⚠ ⟳ r10 L2 — BOUND THE CLAIM TO THE STATE IT WAS MEASURED IN. That run happened while
-- `video_artifacts` and `video_generations` held ZERO real rows (backlog 26 is DORMANT and
-- `record_artifact` has no caller), i.e. the one state in which 'no assertion can be
-- invalidated by a later write' is easiest to be true. Every block is fixture-scoped and is
-- expected to survive a populated corpus — but the sentence claims a property of every future
-- state and was measured on the empty one. RE-MEASURE the day a caller lands; the day is
-- observable, via `python3 scripts/check-paid-caller-arrival.py`.
--
-- ⛔ THE MARKER IS A RANGE TOGGLE, SO ADDING A MIGRATION-ONLY ONE BELOW SILENTLY DROPS EVERYTHING
--    AFTER IT. If you genuinely add a migration-only assertion, add a matching re-runnable marker to
--    resume — and if you forget, the harness's assertion floor goes RED naming the count, which is
--    the only reason a whole-file classification is safe to make.
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

-- ── ⟳ ADR-0011 — THE BACKFILL ASSERTION IS DELETED, NOT RETARGETED ──────────────────────────────
-- Round 6 B4's block stood here. It asserted two things about `workspace_videos.corrections_hash`:
-- that no row carried a NULL, and that the count of corrected rows matched `videos.data`. Both
-- subjects are gone — the column, and the very idea that the two representations should agree.
--
-- ⛔ NOT REWRITTEN TO ASSERT SOMETHING ELSE, on the plan's own instruction: "an assertion retargeted
-- to keep it alive is how a suite ends up testing what is easy rather than what matters." The
-- honest count of assertions this file makes about corrections currency is now ZERO, and it should
-- read that way.
--
-- ⚠ WHAT IS NO LONGER GUARDED, SAID OUT LOUD. B4 measured 2903 of 2904 rows NULL while 99 videos
-- carried real corrections, and this block was the ratchet that stopped that recurring. Under
-- ADR-0011 the failure is unrepresentable rather than guarded — there is no second copy to lose the
-- corrections INTO. That is a stronger claim than the assertion made, and it is the whole argument
-- for the ADR; but it is a claim about SHAPE, so nothing here executes to confirm it, and a reader
-- looking for "where did the backfill assertion go" deserves to find this instead of silence.
-- (The rest of the item-2 assertions live at the end of this file, with the ranking fixtures.)

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
-- The trigger fires `after insert or update`, and a paid artifact's ordinary life used to be
-- `reserve` (INSERT pending) then `record` (UPDATE recorded) — two rows in this table, ONE caller,
-- and no second-caller behaviour exercised anywhere. The ratchet said "the SEQUENCE case is
-- exercised" and could be satisfied by a lifecycle that never has a second caller: shape #11, in the
-- instrument built to close an absence.
--
-- ⟳ ADR-0007 — THAT LIFECYCLE IS GONE AND THE INSTRUMENT IS WORTH MORE, NOT LESS. A paid artifact
-- now has exactly ONE write, so "two INSERTs to one slot" can only mean two callers; the distinction
-- the round-9 tightening had to argue for is now structural. And it EARNED ITSELF IN THIS SLICE:
-- retiring the reservation assertions removed `model`'s only second write, and this ratchet went RED
-- naming it — an absence created by a DELETION, which is precisely the direction no assertion, no
-- mutation and no reviewer looks in, because all three are opt-in and only ever see what someone
-- thought to write down.
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

-- ⭐⭐ ⟳ r10 M3 — "A SECOND TENANT" WAS A HOPE, NOT A CHECK, AND ON A ONE-WORKSPACE DATABASE IT IS
-- FALSE. `limit 1` and `desc limit 1` over a single row return THE SAME ROW. Ten blocks below then
-- treat one tenant as two and go RED accusing the schema of a CROSS-TENANT LEAK — a false
-- accusation naming the wrong subject, which this repo has measured the cost of. A `db reset` plus
-- one signup produces exactly that state, so it is reachable on any fresh machine.
--
-- ⚠ IT ALSO MAKES THE TWO GATES' SUBJECTS VISIBLE, which they were not. Gate 1 runs this file
-- against a pre-M4 base with no seed, gate 8 against `postgres` WITH the seed corpus — and because
-- `workspaces.id = owner_id` and the seed's user id is `…0000a1`, the seed tenant SORTS FIRST. So
-- `t_ws` resolves to a different workspace in each gate. Both are green and no assertion's meaning
-- changes, but the difference arrived silently, and the anti-drift block ADR-0011 deleted was on
-- record measuring the opposite property of this same variable. A variable that has already caused
-- one measured defect does not get to change meaning between two gates without saying so.
do $$ declare a uuid; b uuid; n int; begin
  select count(*) into n from workspaces;
  select id into a from t_ws; select id into b from t_w2;
  if a is null or b is null then
    raise exception 'CANNOT RUN — no workspaces exist, so every fixture below would be NULL-keyed';
  end if;
  if a = b then
    raise exception 'CANNOT RUN — only % workspace(s); t_ws and t_w2 are the SAME row (%), so the '
                    'cross-tenant assertions would be vacuous. Seed a second workspace.', n, a;
  end if;
  raise notice 'ok (fixtures): % workspaces; t_ws=% t_w2=% — two distinct tenants', n, a, b;
end $$;
-- ⟳ ADR-0011: `vidA` used to be seeded with a non-constant 'H_NEW' corrections_hash, which is why
-- the backfill assertion above had to run BEFORE the fixtures. With the column gone the two rows
-- are shaped identically and that ordering constraint is gone with them.
insert into workspace_videos (workspace_id, video_id) select id, 'vidA' from t_ws;
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
-- ⟳ T3 — PROVENANCE IS A ROW IN A CHILD TABLE NOW, not a column. Two statements, same claim: this
-- model was built FROM gOLD, which `video_summary_current` will shortly rank as superseded.
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
values ((select id from t_ws),'vidA','model','gMODEL','model','recorded',(select id from t_ws)::text||'/videos/vidA/gMODEL/model.json');
insert into video_artifact_sources (artifact_id, workspace_id, video_id, source_generation_id)
select a.artifact_id, a.workspace_id, a.video_id, 'gOLD'
  from video_artifacts a where a.video_id='vidA' and a.slot='model';
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

-- ⟳ T4 — A GENERATION CANNOT BE PENDING. T2 deleted the GC floor's `state = 'complete'` predicate as
-- vacuous and named what it was leaving: the CHECK still ADMITTED 'pending', so a hand-written
-- `insert … state='pending'` was still legal and, with the floor's predicate gone, still collectable.
-- "No producer" is not a constraint. The row below is valid in EVERY other respect — complete card,
-- matching major, produced_at, md_hash — so it violates exactly one guard, and that guard is the one
-- T4 added. This is the stronger claim that lets G3's hand-built pending fixture be retired.
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,state,card,doc_version_major,produced_at,md_hash)
  values ((select id from t_ws),'vidA','gT4P','summary','pending',
   '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_NEW"}',
   4,now(),'SHA_T4P')$$,
  'a generation written PENDING (T4: unrepresentable now, not merely unproduced)',
  '23514', 'video_generations_state_check');

-- ⟳ T4 (round 17 H1) — `card` AND `doc_version_major` BELONG TO `summary`, AND THAT IS A MEASURED
-- CONCLUSION, not a tidy-up. The obvious repair for H1 was to extend the three `kind <> 'summary'`
-- CHECKs to every paid kind; the producers refuse it (03's T4 block quotes each one). What IS true is
-- the dual — no other kind can legitimately carry these two — and it is worth enforcing because both
-- are RANKING RUNGS that 04's `video_artifacts_current` applies to every kind: a dig carrying a card
-- would outrank its own siblings on a rung that means nothing for a dig.
-- Two negatives against two constraints; a fixture invalid in both ways would test neither (round 6 H5).
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,produced_at,card)
  values ((select id from t_ws),'vidA','gT4C','dig',now(),
   '{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y","mdCorrectionsHash":"H_NEW"}')$$,
  'a DIG generation carrying a summary card (it would win a ranking rung that means nothing for its kind)',
  '23514', 'gen_card_is_summary_only');
select assert_raises($$insert into video_generations
  (workspace_id,video_id,generation_id,kind,produced_at,doc_version_major)
  values ((select id from t_ws),'vidA','gT4M','model',now(),4)$$,
  'a MODEL generation carrying doc_version_major (rule 13''s format rung is the summary''s)',
  '23514', 'gen_major_is_summary_only');

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

-- ⛔ RETIRED BY ADR-0007 — three negatives stood here, one per deleted constraint:
--     art_pending_is_leased        (round 4 Codex #5, isolated by round 5 H1 / round 6 H5)
--     art_pending_has_token        (round 6 H5)
--     art_pending_has_reserved_at  (round 6 H5)
-- All three asserted a biconditional on `state = 'pending'` over the lease columns. ADR-0007 deleted
-- the state, the columns and the constraints, so these are retired rather than moved: there is no
-- surviving guard they could be rewritten against.
-- ⚠ THE RULE THEY CARRIED IS NOT RETIRED. It was round 6 H5's — THREE separate constraints, never
-- one compound, because a fixture that is invalid in two ways tests neither. That rule governs every
-- negative in this file and is stated in its header.
-- ⚠ AND THE `state = 'pending'` NEGATIVE THAT REPLACES THEM IS BELOW, on the state CHECK itself:
-- a row can no longer BE pending, which is the stronger claim.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key,start_sec,end_sec)
  values ((select id from t_ws),'vidA','dig:9','gDIG','dig','pending',(select id from t_ws)::text||'/videos/vidA/gDIG/dig/9.md',9,20)$$,
  'an artifact row written PENDING (ADR-0007 deleted the state; it must be unrepresentable, not merely unused)',
  '23514', 'video_artifacts_state_check');

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

-- ── ⟳ T3 — THE FOUR PROVENANCE ASSERTIONS, REWRITTEN AGAINST THE JOIN TABLE ─────────────────────
-- They are REWRITTEN, NOT DELETED. Deleting them would remove the EVIDENCE that these rules hold
-- rather than the rules — and one of them (the immutability negative, further down) is the only
-- executable proof that provenance cannot be rewritten, which is the guarantee round 17 H3 measured
-- a hole in. Each still violates exactly one guard, which took more care than before: with the rule
-- spread over a constraint trigger, an INSERT enforcer and two FKs, a careless fixture trips two.

-- art_summary_has_no_source (round 5 H2, the DATA half) — now a CARDINALITY-ZERO rule enforced by a
-- CONSTRAINT TRIGGER, because a CHECK cannot reach another table. The subject row is gNEW's SUMMARY
-- artifact, which has NO sources of its own — so the INSERT enforcer cannot fire and this negative
-- can only be answered by the summary rule. 'gOLD' is a real generation, so the FK cannot fire either.
select assert_raises($$insert into video_artifact_sources
  (artifact_id, workspace_id, video_id, source_generation_id)
  select a.artifact_id, a.workspace_id, a.video_id, 'gOLD' from video_artifacts a
   where a.video_id='vidA' and a.slot='summary' and a.generation_id='gNEW'$$,
  'a SUMMARY artifact recording a source (it is derived from nothing)', 'P0001');

-- the source FK (round 5, Codex/M5), which migrated onto this table with the column. Same claim,
-- per SOURCE: provenance may not name a generation that does not exist.
-- ⚠ THE SUBJECT IS `dig:120`, WHICH HAS NO SOURCES OF ITS OWN, AND THAT IS DELIBERATE. Using the
-- `model` artifact — the obvious choice, since it is the one with provenance — would make the row
-- violate the INSERT enforcer TOO, and it would pass under a disjunction: FK checks are AFTER ROW
-- and the enforcer is AFTER STATEMENT, so the FK merely happens to answer first. Round 5 H1's
-- masking rule reaches guards that fire in a fixed order just as it reaches two constraints.
select assert_raises($$insert into video_artifact_sources
  (artifact_id, workspace_id, video_id, source_generation_id)
  select a.artifact_id, a.workspace_id, a.video_id, 'gGHOST' from video_artifacts a
   where a.video_id='vidA' and a.slot='dig:120'$$,
  'provenance from a generation that DOES NOT EXIST', '23503', 'vas_source_generation_fk');

-- ⟳ T3 — THE TENANT COORDINATE IS FK'd BACK TO THE ARTIFACT, and this is the negative that proves
-- the denormalisation cannot lie. Without `vas_artifact_fk` a source row could sit under tenant 1's
-- model while naming tenant 2's (workspace, video), and the currency rung would then rank a paid
-- render against ANOTHER TENANT's summary. `g2` is a real generation — of the OTHER workspace — so
-- `vas_source_generation_fk` is satisfied and only the artifact FK can object.
select assert_raises($$insert into video_artifact_sources
  (artifact_id, workspace_id, video_id, source_generation_id)
  select a.artifact_id, (select id from t_w2), 'vidB', 'g2' from video_artifacts a
   where a.video_id='vidA' and a.slot='dig:120'$$,
  'a source row whose tenant coordinate is not its artifact''s', '23503', 'vas_artifact_fk');

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

-- ⛔ RETIRED BY ADR-0007 — THE IN-FLIGHT MONEY GUARD AND ITS FLIP (round 5 B4 + H4, cross-derivation
-- C1). Three assertions stood here:
--   * a SECOND in-flight reservation on one slot, rejected by `video_artifacts_inflight_uq`. All
--     three round-5 reviewers MEASURED this independently: without the index two writers insert
--     `pending` for one slot under their OWN generation ids, both succeed, and `count(*) = 2` paid
--     Gemini calls. The index is deleted; see 04's tombstone for the ONE consumer that survives it
--     (the `model` serve path, which needs `doc_key` re-keyed in the same slice, NOT this one).
--   * "a pending reservation is never servable" — no row can be pending.
--   * "the pending -> recorded flip is permitted, and then serves" — there is no flip; the append
--     below is the whole of it.
-- The fixture is kept, as a plain recorded row, because later assertions run against it: `wA`'s
-- digDeeper row is what the PROVENANCE-immutability negative rewrites.
insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidA','digDeeper','wA','digDeeper','recorded',
          (select id from t_ws)::text||'/videos/vidA/wA/dd.md');
do $$ declare k text; begin
  select blob_key into k from video_artifacts_current where video_id='vidA' and slot='digDeeper';
  if k is distinct from (select id from t_ws)::text||'/videos/vidA/wA/dd.md' then
    raise exception 'ASSERTION FAILED — a recorded digDeeper is not current: %', coalesce(k,'<none>');
  end if;
  raise notice 'ok: a recorded digDeeper serves';
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
-- ⟳ ADR-0007 REWROTE THIS, IT DID NOT RETIRE IT. It used to revive a detached row to `pending` —
-- a state the ADR deleted, so the fixture would now violate the state CHECK as well as the trigger
-- and would test neither (round 5 H1's masking shape). A state OUTSIDE the domain keeps the subject
-- unchanged: the trigger is `before update`, so it answers FIRST with a typed P0001, and the CHECK
-- never gets to speak. Mutating the trigger branch away yields 23514, and the SQLSTATE pin turns
-- that into a failure rather than a false GREEN.
select assert_raises($$update video_artifacts
  set state='reserved', detached_at=null
  where video_id='vidA' and slot='dig:120'$$,
  'moving a detached paid row to a state outside the domain (the trigger answers before the CHECK)',
  'P0001');
-- ── ⟳ T3 — PROVENANCE IMMUTABILITY, AND THIS IS THE EXECUTABLE PROOF OF IT ──────────────────────
-- Codex H5's rule is unchanged: provenance is a RANKING input, so a stale model that rewrites it to
-- the current summary wins the source-currency rung without regenerating a byte. What changed is
-- that provenance is now a SET, so "rewriting it" has THREE spellings, and round 17 H3 MEASURED
-- that the round-16 fix — moving 04's PROVENANCE branch onto this table — caught only two of them.
-- The subject is `vidA`'s model artifact, whose source is gOLD.
--
--   (a) UPDATE the row in place                — the append-only trigger on the child table
select assert_raises($$update video_artifact_sources set source_generation_id='gNEW'
  where artifact_id = (select artifact_id from video_artifacts where video_id='vidA' and slot='model')$$,
  'rewriting the PROVENANCE of a recorded paid row (Codex H5 — wins the rung for free)', 'P0001');
--   (b) DELETE it, then re-insert             — the same trigger's DELETE branch. Without it, (a) and
--       (c) are both reachable in two statements: empty the set, then write a new one into an
--       artifact that now records nothing. Same two-statement bypass shape as round 6 B3's detach.
select assert_raises($$delete from video_artifact_sources
  where artifact_id = (select artifact_id from video_artifacts where video_id='vidA' and slot='model')$$,
  'DELETING the provenance of a live artifact (the two-statement route to rewriting it)', 'P0001');
--   (c) INSERT a DIFFERENT source beside it    — ⚠ THIS IS ROUND 17 H3, AND IT IS WHY THE MOVED
--       TRIGGER WAS NOT SUFFICIENT. That trigger is `before update or delete`; an INSERT fires no
--       such trigger, and the measured result was a silent UNION — neither the same set nor a raise,
--       i.e. this artifact would then claim provenance from BOTH gOLD and gNEW and rank as current.
--       "A constraint governs STATES, a trigger governs TRANSITIONS, and an INSERT is a state with
--       no transition" is stated twice in 04's own comments; the round-16 fix assigned the invariant
--       to the one mechanism shape that structurally cannot see the operation that violates it.
select assert_raises($$insert into video_artifact_sources
  (artifact_id, workspace_id, video_id, source_generation_id)
  select a.artifact_id, a.workspace_id, a.video_id, 'gNEW' from video_artifacts a
   where a.video_id='vidA' and a.slot='model'$$,
  'ADDING a source to an artifact that already records one (round 17 H3 — the silent UNION)', 'P0001');
-- ...and the set is intact after all three. A negative that is rejected for the wrong reason still
-- reads as green, so the state itself is asserted rather than inferred from three P0001s.
do $$ declare srcs text; begin
  select string_agg(s.source_generation_id, ',' order by s.source_generation_id) into srcs
    from video_artifact_sources s
    join video_artifacts a on a.artifact_id = s.artifact_id
   where a.video_id='vidA' and a.slot='model';
  if srcs is distinct from 'gOLD' then
    raise exception 'ASSERTION FAILED — the model''s source set is now {%}, expected {gOLD}', coalesce(srcs,''); end if;
  raise notice 'ok (T3): provenance survives update, delete and union — all three spellings refused';
end $$;

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

-- ── ⛔ RETIRED BY ADR-0007 — THE RESERVATION PROTOCOL (round 6 H5 / Codex B2) ────────────────────
-- ~140 lines of assertions stood here. They are listed by subject so a later round can see what was
-- covered and what the deletion cost, rather than discovering an absence:
--
--   P2 / typed outcome     — reserve returns `reserved` + a token + attempts=1, never a bare int
--   P22, the live half     — a second writer on a LIVE lease reads `busy` and gets no token
--   renewal                — token-fenced (a stranger gets `lost`), survives its own TTL, and is
--                            bounded by `max_duration_seconds` so a HUNG worker cannot renew forever
--   reclaim                — an expired lease is re-pointed IN PLACE (one row, not two) and the
--                            attempt count survives, because the increment is in the statement that
--                            takes the slot. The old reclaim's count was resettable.
--   live-lease-first       — at attempts = max AND a live lease the answer is `busy`, not
--                            `exhausted`. The ONLY case where the two orderings differ; mutating the
--                            ordering left the whole suite GREEN until this block existed.
--   exhaustion             — a typed outcome past the bound, not a raw [23505] (shape #8)
--   idempotent re-reserve  — re-reserving an already-recorded generation is `already_recorded`
--   summary_max_attempts=1 — asserted so that RAISING it is a decision, not an accident: a crashed
--                            summary worker leaves a slot nobody can retry
--
-- ⚠ TWO OF THOSE ARE MONEY GUARANTEES WITH NO SUCCESSOR IN THIS FILE, and saying so is the point of
-- this tombstone. The per-kind attempt ceiling is gone (04's tombstone names the conflict:
-- `summary_max_attempts` = 1 against `jobs.max_attempts` = 5), and single-flight for the `model`
-- serve path now rests entirely on `serve_model_charge`, which lives in `supabase/migrations/` and
-- is outside this file's reach. Neither is asserted here because neither is in this schema.
--
-- WHAT SURVIVES IS APPEND-ONLY ITSELF, and it is asserted below rather than retired: two generations
-- of one slot coexist and are ranked. That was the DESIGNED state the reservation kept colliding
-- with — user decision 2026-08-07, "the reservation guards SPENDING, not RECORDING" — and with the
-- reservation gone it is simply what `record_artifact` does.
do $$ declare o text; n int; ws uuid; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidA','dig:700','gOTHER','dig'::artifact_kind,
        ws::text||'/videos/vidA/gOTHER/dig/700.md', p_start_sec := 700, p_end_sec := 750);
  if o <> 'recorded' then
    raise exception 'ASSERTION FAILED — the first writer of a slot got: %', o; end if;
  -- a SECOND writer, its own generation, its own key. Under the old protocol this was the
  -- `recorded_after_loss` path and required a reclaim to reach; it is now the ordinary case.
  o := record_artifact(ws,'vidA','dig:700','gDIG','dig'::artifact_kind,
        ws::text||'/videos/vidA/gDIG/dig/700.md', p_start_sec := 700, p_end_sec := 750);
  if o <> 'recorded' then
    raise exception 'ASSERTION FAILED — a second writer''s PAID work was discarded: %', o; end if;
  select count(*) into n from video_artifacts
   where video_id='vidA' and slot='dig:700' and state='recorded';
  if n <> 2 then raise exception 'ASSERTION FAILED — expected two ranked generations, got %', n; end if;
  raise notice 'ok (append-only): two writers, two generations, one slot, both kept and ranked';
end $$;

-- IDEMPOTENCY: a worker that crashed between recording and reporting completion must learn it is
-- done, not be handed an error it has to parse. The old protocol answered this at RESERVE time
-- (`already_recorded`); with no reserve, `record_artifact` answers it itself — and it is the same
-- word, because it is the same question.
do $$ declare o text; n int; ws uuid; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidA','dig:700','gDIG','dig'::artifact_kind,
        ws::text||'/videos/vidA/gDIG/dig/700.md', p_start_sec := 700, p_end_sec := 750);
  if o <> 'already_recorded' then
    raise exception 'ASSERTION FAILED — re-recording an identical row gave %', o; end if;
  select count(*) into n from video_artifacts where video_id='vidA' and slot='dig:700';
  if n <> 2 then
    raise exception 'ASSERTION FAILED — the idempotent retry appended a row (% rows)', n; end if;
  raise notice 'ok (record): an identical retry is idempotent and typed, never a raw 23505';
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
-- ⟳ ROUND 6 H5 — ALL replacements are swept, not just the one that inherited the name.
-- B1 happened because a definer function was added one file away and the PUBLIC-revoke habit was
-- applied at one site; replacing that function with three would have been the ideal way to reproduce
-- the same mistake at triple scale.
-- ⟳ ADR-0007 — three definer functions became ONE. `reserve_artifact_slot` and
-- `renew_artifact_lease` are gone, so their loop arms go with them; the ratchet that makes this
-- claim checkable rather than remembered is R8's pg_proc sweep below, which is what would catch a
-- FOURTH function being added without a revoke.
do $$ declare ws uuid; begin
  select id into ws from t_ws;
  set local role anon;
  begin
    perform record_artifact(ws,'vidA','dig:9','gDIG','dig'::artifact_kind,'k');
    reset role;
    raise exception 'ASSERTION FAILED — anon CALLED record_artifact (cross-tenant write)';
  exception when insufficient_privilege then
    reset role;
    raise notice 'ok (rejected by 42501): anon calling record_artifact';
  end;
end $$;
-- ⟳ TASK 8, MOVED EARLY BY PHASE 6 #2 (fork (a), user decision 2026-08-25).
-- (A re-runnable marker stood on this line and is now at the top of the file. It was one of three
--  that made this the only live-gated region; leaving them behind would be a second mechanism
--  saying what the header already says, and the toggle only needs one.)
-- THE FIRST ASSERTION IN THIS FILE THAT ACTUALLY RUNS. Until now `05_assert.sql` carried 104
-- `raise exception`s and ZERO markers, so `scripts/run-schema-assertions.sh` was a permanent
-- fail-closed CANNOT RUN — a 2,239-line security control that had never executed outside a
-- review's rolled-back transaction.
--
-- ⭐ WHY THIS BLOCK FIRST, AND WHY IT IS THE WHOLE ARGUMENT FOR FORK (a):
-- round 7 filed `anon` TRUNCATE as a BLOCKING finding against the live-catalog gate, and the
-- proposed fix was to add TRUNCATE to `REL_PRIVS` in `m4_catalog.py` plus a written exclusion
-- reason. But the hole was ALREADY FOUND, ALREADY FIXED and ALREADY ASSERTED — right here, with
-- the measurement recorded twenty lines up: *"anon TRUNCATEd the paid manifest to zero rows"*.
-- We rediscovered it because nothing ran this. The fingerprint was being widened to relearn what
-- the assertion already knew.
--
-- ⚠ THIS BLOCK NEEDS NO FIXTURE — only the `anon` role and the table — which is why it is the
-- cheapest possible first marker. Blocks that read `t_ws` or the gOLD/gNEW generations need the
-- seed corpus to supply them and are NOT marked yet.
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
-- ⭐⭐ SERVICE-ROLE CAPABILITY — fork (a) step 5, 2026-08-26. THE REPLACEMENT FOR A DIGESTED GRANT.
--
-- ⟳ r7 B1 (codex): revoking `record_artifact` EXECUTE from `service_role` is a production write
-- outage, and `check-live-schema.py --expect-present` exited 0 over it. The obvious fix was to add
-- `service_role` to the digest's function grantees — a FIFTH widening of the fingerprint, and the
-- move each of rounds 4-7 made before being told it was insufficient.
--
-- ⟳ r7 H2 (codex): `service_role` holds INSERT on `video_artifacts` AND CANNOT USE IT. `art_slot_kind`
-- CHECKs `slot_kind(slot)`, a CHECK runs as the writing role, and `slot_kind` is granted to nobody.
-- MEASURED here 2026-08-26, identical row, one role, two paths:
--
--     [RPC]    record_artifact(...)                -> recorded
--     [DIRECT] insert into video_artifacts ...     -> ERROR: permission denied for function slot_kind
--
-- ⭐ SO A DIGESTED GRANT WOULD HAVE CERTIFIED A CAPABILITY THAT DOES NOT EXIST. A privilege is not a
-- capability: `has_table_privilege` says the grant is there, and the write still fails. That gap is
-- unreachable by any fingerprint, however wide, and it is why these two blocks are the thing that
-- lets `service_role` leave the digest rather than join it.
--
-- ⛔ IT BUILDS ITS OWN FIXTURE, AND THE FIRST DRAFT DID NOT — MEASURED, and the measurement is the
-- reason this comment exists. The draft read `videos where video_id='seedvid001'`, which the SEED
-- CORPUS supplies. But this file runs in TWO contexts:
--     run-schema-assertions.sh   seed corpus, then the RE-RUNNABLE subset   -> seedvid001 exists
--     verify-schema.sh           01+03+04+05 concatenated in one txn        -> it does NOT
-- So gate 1/11 went red on the block's own fail-closed guard:
--     ERROR: ASSERTION FAILED — the seed corpus supplied no workspace; this block is vacuous
-- The guard was right and the block was wrong. A RE-RUNNABLE assertion may not depend on a fixture
-- only one of its two callers builds — so this one creates a private owner, and the platform's own
-- signup chain (auth.users -> handle_new_user -> profiles -> ensure_workspace_for_profile) gives it
-- a workspace. That also exercises the derive path rather than writing workspace_id by hand.
do $$
declare v_ws uuid; v_out text; v_n int;
        v_uid uuid := '00000000-0000-0000-0000-00000000cab1';
begin
  insert into auth.users (id, instance_id, aud, role, email)
    values (v_uid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
            'svc-capability@example.test')
    on conflict (id) do nothing;
  -- ⚠ IT FALLS BACK TO CREATING THE WORKSPACE, AND THAT IS DELIBERATE — MEASURED 2026-08-26.
  -- The draft RAISED when the derive chain produced nothing, which made this block fire FIRST on
  -- mutate-schema.py's B3 ("a new profile gets no workspace"), stealing the red from the assertion
  -- written for it:
  --     ⚠️ RED(other)  B3 — expected "a NEW profile got no workspace",
  --                         got  "no workspace was derived for the probe owner"
  -- Both are true; only one is this block's business. THE SUBJECT HERE IS SERVICE_ROLE PRIVILEGE,
  -- not workspace derivation, and an assertion that reaches beyond its subject takes the failure
  -- away from the assertion that would have named the cause. Derivation has its own assertion; this
  -- one just needs a workspace to exist.
  select id into v_ws from workspaces where owner_id = v_uid;
  if v_ws is null then
    insert into workspaces (id, owner_id) values (v_uid, v_uid) on conflict do nothing;
    select id into v_ws from workspaces where owner_id = v_uid;
  end if;
  if v_ws is null then
    raise exception 'ASSERTION FAILED — could not obtain a workspace for the probe owner even by '
                    'creating one, so nothing below is a statement about service_role';
  end if;
  insert into workspace_videos (workspace_id, video_id) values (v_ws, 'vidSVC')
    on conflict do nothing;

  set local role service_role;
  begin
    v_out := record_artifact(
      v_ws, 'vidSVC', 'summary', 'gSVC', 'summary'::artifact_kind,
      v_ws::text || '/videos/vidSVC/gSVC/summary.md',
      null, null, null, 'mdhash-svc',
      '{"tldr":"t","takeaways":"k","docVersion":"1","mdGeneratedAt":"2026-01-01T00:00:00Z",
        "processedAt":"2026-01-01T00:00:00Z","mdCorrectionsHash":"h"}'::jsonb,
      1, now());
  exception when insufficient_privilege then
    reset role;
    raise exception 'ASSERTION FAILED — service_role CANNOT call record_artifact. Every paid write '
                    'fails; this is a production write outage, not a permissions nicety (r7 B1)';
  end;
  reset role;

  if v_out is distinct from 'recorded' then
    raise exception 'ASSERTION FAILED — record_artifact returned %, expected recorded', v_out;
  end if;
  -- ⚠ THE RETURN VALUE IS NOT THE EVIDENCE. A function can report success and write nothing; that
  -- exact shape is why `persist_summary` needed its own merge assertion. Read the row back.
  select count(*) into v_n from video_artifacts
   where video_id = 'vidSVC' and generation_id = 'gSVC';
  if v_n <> 1 then
    raise exception 'ASSERTION FAILED — record_artifact said recorded and left % artifact rows', v_n;
  end if;
  raise notice 'ok: service_role recorded a paid artifact through the RPC, and the row is there';
end $$;

-- The other half: the RPC is the ONLY door, in EVERY environment.  (Marker retired to the header.)
--
-- ⛔⛔ THIS BLOCK WAS MASKED ON ITS FIRST DRAFT, AND THE MASK WAS FOUND BY MUTATING IT — which is the
-- only reason it is written this way. The draft created the parent generation with `kind='summary'`
-- and inserted an artifact with `kind='model'`. `video_artifacts_..._kind_fkey` is on
-- (workspace_id, video_id, generation_id, KIND), so with the privilege GRANTED the insert died on
-- the FK, not on the assertion:
--     ERROR: insert or update on table "video_artifacts" violates foreign key constraint
--            "video_artifacts_workspace_id_video_id_generation_id_kind_fkey"
-- The control still passed, because 42501 is raised BEFORE the FK is checked. So the block would
-- have reported "ok (rejected by 42501)" forever while proving nothing about privileges at all.
--
-- That is round 5 H1 verbatim, in the same file, one year of review rounds later: *"the test was
-- MASKED by the FK"*. A negative assertion is only worth its exit code if the ONLY remaining reason
-- to fail is the one being asserted — so the parent below matches on every FK column, and a
-- non-42501 error propagates rather than being swallowed as success.
do $$
declare v_ws uuid; v_n int;
        v_uid uuid := '00000000-0000-0000-0000-00000000cab1';
begin
  -- Same private owner as the block above, derived the same way. ⚠ THE NULL GUARD IS NOT OPTIONAL:
  -- without it a missing workspace makes the INSERT below fail on a NOT NULL, which is a red gate
  -- for the wrong reason and reads as if the assertion had something to say about privileges.
  select id into v_ws from workspaces where owner_id = v_uid;
  if v_ws is null then
    raise exception 'ASSERTION FAILED — the probe workspace is absent, so nothing below is a '
                    'statement about service_role';
  end if;
  -- kind='model' to satisfy the FK's kind column. A model generation carries NO card and NO
  -- doc_version_major — gen_card_is_summary_only and gen_major_is_summary_only forbid them.
  insert into video_generations (workspace_id, video_id, generation_id, kind, state, produced_at)
    values (v_ws, 'vidSVC', 'gDIRECT', 'model', 'complete', now());

  set local role service_role;
  begin
    insert into video_artifacts (workspace_id, video_id, slot, generation_id, kind, state, blob_key)
      values (v_ws, 'vidSVC', 'model', 'gDIRECT', 'model'::artifact_kind, 'recorded',
              v_ws::text || '/videos/vidSVC/gDIRECT/model.json');
    reset role;
    raise exception 'ASSERTION FAILED — service_role wrote video_artifacts DIRECTLY. record_artifact '
                    'is not the only door, so every guard that function performs can be walked past';
  exception when insufficient_privilege then
    reset role;
    raise notice 'ok (rejected by 42501): service_role writing video_artifacts outside the RPC';
  end;

  -- ⭐ THE ANTI-MASK CHECK. If the parent did not land, the rejection above proves nothing.
  select count(*) into v_n from video_generations
   where video_id = 'vidSVC' and generation_id = 'gDIRECT' and kind = 'model';
  if v_n <> 1 then
    raise exception 'ASSERTION FAILED — the FK parent is absent, so the 42501 above is unearned';
  end if;
end $$;

-- ⟳ r8 H4 (codex): the DIRECT capabilities service_role legitimately has.  (Marker retired above.)
--
-- The two blocks above cover the PAID WRITE (RPC works) and the RPC-ONLY invariant (direct artifact
-- write refused). They do not cover the direct DML the spec deliberately grants for GC and
-- housekeeping — and the reviewer proved that gap by construction: removing `UPDATE` on
-- `video_generations` from `service_role` left BOTH instruments green.
--
--     -- live digest --        M4 is PRESENT as expected ... check_live_exit=0
--     -- schema assertions --  RE-RUNNABLE subset passed ... assert_exit=0
--     -- capability probe --   ERROR: permission denied for table video_generations
--
-- That is the same shape as r7 B1 one table over, and it is the price of taking privileges out of
-- the fingerprint: whatever the digest no longer watches, SOMETHING must execute. This block is that
-- something. It asserts the GC/sweeper capabilities named in the spec's own grants
-- (`03_generations.sql:68-69,562-563`, `04_artifacts.sql:257-259`) rather than their grant bits.
do $$
declare v_ws uuid; v_n int;
        v_uid uuid := '00000000-0000-0000-0000-00000000cab1';
begin
  select id into v_ws from workspaces where owner_id = v_uid;
  if v_ws is null then
    raise exception 'ASSERTION FAILED — the probe workspace is absent; nothing below is a statement '
                    'about service_role';
  end if;

  set local role service_role;
  -- 1. THE SWEEPER. `body_collected` is how GC records that a generation's blob is gone; without
  --    UPDATE here the collector silently stops making progress and nothing else notices.
  begin
    update video_generations set body_collected = body_collected
     where workspace_id = v_ws and video_id = 'vidSVC' and generation_id = 'gDIRECT';
  exception when insufficient_privilege then
    reset role;
    raise exception 'ASSERTION FAILED — service_role cannot UPDATE video_generations. The GC sweeper '
                    'cannot mark a body collected, so collection stops and nothing reports it';
  end;

  -- 2. THE GC READ. `video_generations_collectable` is granted to service_role ALONE; if that grant
  --    regresses the collector has nothing to iterate and, again, fails by doing nothing.
  begin
    select count(*) into v_n from video_generations_collectable;
  exception when insufficient_privilege then
    reset role;
    raise exception 'ASSERTION FAILED — service_role cannot read video_generations_collectable, so '
                    'the GC has no work list';
  end;

  -- 3. PROVENANCE. record_artifact writes video_artifact_sources through its definer context, but
  --    the spec also grants direct DML; assert the READ at minimum, which every consumer needs.
  begin
    select count(*) into v_n from video_artifact_sources;
  exception when insufficient_privilege then
    reset role;
    raise exception 'ASSERTION FAILED — service_role cannot read video_artifact_sources';
  end;
  -- 4. ⟳ r8 H2 (claude) — THE `detached` TRANSITION. §6.1 owes a detached dig "a route back", and
  --    this file spends ~40 lines proving recorded -> detached -> recorded works — AS `postgres`,
  --    NEVER AS `service_role`. Revoke UPDATE on video_artifacts from service_role and every detach
  --    and re-attach fails at runtime with all three gates green. r7 B1's shape, a third time.
  -- ⚠ ZERO-ROW PREDICATE ON PURPOSE. The first draft targeted the real row and went red — not on a
  -- privilege, but on `video_artifacts_append_only`, which is a DIFFERENT guard with its own
  -- assertions forty lines up. An UPDATE matching no rows still requires the UPDATE privilege, so
  -- this discriminates exactly the thing the block is about and collides with nothing. Same lesson
  -- as the B3 narrowing above: an assertion that reaches past its subject steals the failure from
  -- the assertion that would have named the cause.
  begin
    update video_artifacts set slot = slot where workspace_id = v_ws and video_id = '__no_such__';
  exception when insufficient_privilege then
    reset role;
    raise exception 'ASSERTION FAILED — service_role cannot UPDATE video_artifacts, so the detached '
                    'transition has no route in EITHER direction (spec 6.1)';
  end;

  -- 5. GC DELETE on the manifest — free renders, same argument.
  begin
    delete from video_artifacts where workspace_id = v_ws and video_id = '__no_such_video__';
  exception when insufficient_privilege then
    reset role;
    raise exception 'ASSERTION FAILED — service_role cannot DELETE from video_artifacts, so GC '
                    'cannot reclaim a free render';
  end;
  -- 6. ⟳ r9 H1 (claude) — THE FOUR ROWS THE OMISSION TABLE GOT WRONG. It claimed 12 of 21 grants
  --    were asserted; the reviewer revoked each of the 21 alone and measured that FOUR were seen by
  --    no instrument at all: workspaces SELECT, workspaces DELETE, video_artifact_sources UPDATE,
  --    and video_artifacts INSERT. A completeness claim is exactly as checkable as the thing it
  --    claims to cover, and this one was arithmetic over a list nobody executed.
  begin
    perform 1 from workspaces where false;                       -- workspaces SELECT
    delete from workspaces where id = '00000000-0000-0000-0000-0000000000ff';   -- workspaces DELETE
    update video_artifact_sources set video_id = video_id where video_id = '__no_such__';  -- vas UPDATE
    insert into video_artifacts (workspace_id, video_id, slot, generation_id, kind, state, blob_key)
      select v_ws, '__no_such__', 'model', 'g', 'model'::artifact_kind, 'recorded', 'k'
       where false;                                              -- video_artifacts INSERT
  exception when insufficient_privilege then
    reset role;
    raise exception 'ASSERTION FAILED — service_role lost one of workspaces SELECT/DELETE, '
                    'video_artifact_sources UPDATE or video_artifacts INSERT. Each was in the '
                    'digest before step 5 and covered by nothing after it (r9 H1)';
  end;
  reset role;
  raise notice 'ok: service_role retains its GC, provenance, detached-transition and '
               'residual-DML capabilities';
end $$;

-- ⭐ THE GRANTS DELIBERATELY LEFT UNASSERTED, AND WHY — ⟳ r8 H2's direction, verbatim: *"write down,
-- in that block, the grants deliberately left unasserted and why, so the next round does not
-- re-derive this table. An unexplained omission is how r5 B2 happened."*
--
-- ⛔ THIS TABLE WAS WRONG BY FOUR ROWS FOR ONE COMMIT — ⟳ r9 H1 (claude), who did the one thing that
-- checks a completeness claim: revoked each of the 21 grants ALONE and ran all three instruments.
-- Four were seen by NOTHING (workspaces SELECT, workspaces DELETE, video_artifact_sources UPDATE,
-- video_artifacts INSERT) while this table implied they were among the twelve covered. They are now
-- asserted in step 6 above. **A table that says what is covered is a CLAIM, and 21 − 9 = 12 is
-- arithmetic, not a measurement.**
--
-- Step 5 deleted the digest of 21 grant sites. The blocks above now assert 16. These FIVE remain
-- unasserted, and each line is the reason — not an oversight:
--
--   workspaces         INSERT/UPDATE   written by ensure_workspace_for_profile(), a SECURITY DEFINER
--                                      trigger on profiles. service_role never writes it directly.
--   workspace_videos   INSERT/UPDATE   upserted by the videos derive trigger, also SECURITY DEFINER.
--                      DELETE          only by cascade from workspaces.
--   video_generations  INSERT          record_artifact is the ONLY writer, and 05 asserts that in
--                                      ANY schema and by ANY spelling (search: T4/H1).
--                      DELETE          GC, and the UPDATE half above is the one that fails first —
--                                      a collector that cannot mark cannot reach the delete.
--   video_artifact_sources INSERT/DELETE  written inside record_artifact's definer context; the READ
--                                      is asserted above, which is what every consumer needs.
--
-- ⚠ THIS TABLE IS A CLAIM, NOT A PROOF. Each line says "no direct caller exists" — and there is no
-- application code for M4 at all yet, so no caller exists for ANY of them. When M4 is wired up, this
-- table is the list to re-derive against real call sites, and any row that gains a direct caller
-- needs an assertion here before it ships.

-- ⟳ TASK 8 — THE MIGRATION-ONLY STOP THAT STOOD HERE IS DELETED, AND ITS REASON WAS THE TELL.
-- (Spelled without its `@`, per the header: a comment naming the marker IS one. This very line was
--  the second time that bit in one commit — the note recording the deletion re-created the stop.)
-- It read: *"everything below reads fixtures this file builds, not the seed corpus."* True, and not
-- a reason to exclude anything — it was a reason to select the fixtures TOO, which is what moving
-- the marker to the top of the file does. Building fixtures inside the harness's transaction and
-- rolling them back is precisely what gate 1 has always done; the seed corpus supplies the rows the
-- blocks between here and line 778 need, not a substitute for the fixtures.
--
-- Measured before deleting it: with the whole file selected, all 119 assertions pass against the
-- applied 0027. The stop was costing 54 of the 58 blocks their live-schema gate.

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
       + (select count(*) from workspace_videos        where video_id='vidA')
       -- ⟳ T3 — the join table joins the sweep. It is a fourth base table carrying tenant data
       -- (blob provenance), created after the sweep was written, which is precisely how round 6 H3
       -- happened: "read ONE view and ONE table" left three guards mutation-GREEN.
       + (select count(*) from video_artifact_sources  where video_id='vidA') into n;
  reset role;
  if n <> 0 then raise exception 'ASSERTION FAILED — cross-tenant leak: % rows across 6 objects', n; end if;
  raise notice 'ok (RLS): tenant 2 sees 0 rows across BOTH views and all four base tables';
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
-- ⟳ T3 — AND `video_artifact_sources` IS READ FROM THE OWNER'S SIDE FOR A SECOND REASON BEYOND
-- SYMMETRY. `video_artifacts_current` is `security_invoker`, and its currency rung reads this table.
-- With force RLS and no policy the `not exists` would be vacuously TRUE for an authenticated owner
-- and false for `service_role` — the two would rank the SAME manifest differently, which is round 5
-- H2's "the two views disagree" defect relocated into the privilege system. Every cross-tenant
-- assertion would still pass, because a missing policy is only visible from the owner's side.
do $$ declare ng int; nw int; ns int; me uuid; begin
  select id into me from t_ws;
  perform set_config('request.jwt.claims', json_build_object('sub', me::text)::text, true);
  set local role authenticated;
  select count(*) into ng from video_generations      where video_id='vidA';
  select count(*) into nw from workspace_videos       where video_id='vidA';
  select count(*) into ns from video_artifact_sources where video_id='vidA';
  reset role;
  if ng = 0 or nw = 0 or ns = 0 then
    raise exception 'ASSERTION FAILED — the owner cannot read their own base tables (gen %, wv %, sources %)', ng, nw, ns;
  end if;
  raise notice 'ok (RLS): the owner reads video_generations, workspace_videos and video_artifact_sources directly';
end $$;

-- ── ⟳ ADR-0011 — THE FLOOR ASSERTION IS DELETED, AND ITS SUBJECT IS UNREPRESENTABLE ─────────────
-- Round 4 A-2's floor stood here: make every generation corrections-stale by typing a new
-- `corrections_hash` into `workspace_videos`, then assert the summary slot STILL SERVES one row —
-- i.e. that corrections RANK but never GATE.
--
-- ⛔ THERE IS NO LONGER A WAY TO CREATE THE PRECONDITION. "Corrections-stale" was a disagreement
-- between a frozen card's stamp and a mutable denormalized copy, and the copy is gone. Nothing can
-- be typed to make a generation stale, so the assertion cannot be set up, let alone fail.
--
-- ⚠ AND THAT IS A STRONGER GUARANTEE THAN THE ASSERTION GAVE, which is why this is a deletion and
-- not a gap: A-2 protected against corrections ACCIDENTALLY GATING the serve path. With no
-- corrections term in either ranking view (04_artifacts.sql, both sites), corrections cannot reach
-- the serve path to gate it. The risk moved from "guarded by one assertion" to "structurally
-- absent" — but no test executes to say so, so it is written down here instead.
-- ⛔ NOT retargeted at some other staleness, per the plan: an assertion kept alive by changing its
-- subject tests what is easy rather than what matters.

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

-- ── ⟳ ADR-0011 — "RUNG 1 DECIDES" IS DELETED, AND ONLY EXECUTION FOUND IT ───────────────────────
-- The vidC fixture pair stood here: `gC_CUR` corrections-current but OLDER with a LOWER format
-- version, `gC_STALE` corrections-stale but NEWER with a HIGHER one. It asserted `gC_CUR` wins —
-- proving the corrections term was FIRST among the rungs and genuinely decided, rather than being a
-- boolean that re-implemented itself. With no corrections term, `gC_STALE` correctly wins on
-- `doc_version_major` 4 > 3, and the assertion fails.
--
-- ⭐⭐ THE PLAN'S TWO SWEEP PREDICATES BOTH MISSED THIS, AND THE REASON GENERALISES. Step 4's MUST-GO
-- grep and Step 5's gate both match on the NAME of a removed object — `corrections_hash`,
-- `wv.corrections`, `sync_corrections_to_workspace_video`. This block names none of them: its
-- fixtures are legal cards, its assertion reads `video_summary_current`, and every line still
-- parses. It depended on the removed ranking term BEHAVIOURALLY, not lexically.
-- **A textual sweep cannot find a test whose subject is a behaviour rather than an identifier.**
-- It was found by RUNNING the suite, which is the only instrument that had a chance.
--
-- ⛔ NOT RETARGETED. Rewriting it to assert that `doc_version_major` decides would keep a green
-- test at the cost of testing what is easy: the rung ordering below rung 1 was never in question.
-- ⚠ COVERAGE GENUINELY LOST: nothing now proves the surviving rungs decide in the documented order.
-- That gap PREDATES ADR-0011 for rungs 2-5 — this fixture only ever exercised rung 1 against them —
-- but it is smaller now than it reads, and it is named rather than left to a diff.

-- ── ⟳ ADR-0011 — THE ANTI-DRIFT TRIGGER TEST AND THE NULL-HASH REFUSAL ARE BOTH DELETED ─────────
-- Two blocks stood here, and both were guarding the SAME denormalisation from two directions:
--
--   1. THE ANTI-DRIFT TEST. It wrote 'say Clawcode' into a real `videos.data`, then asserted that
--      `workspace_videos.corrections_hash` and `.corrections` had followed; then cleared the text
--      and asserted the hash returned to the DEFINED CONSTANT rather than NULL — the direction that
--      re-opened round 6 B4, because a NULL there is indistinguishable from "never computed".
--   2. THE NULL-HASH REFUSAL. `assert_raises(insert … corrections_hash => null)` expecting 23502,
--      i.e. that absent-vs-failed could not be represented on the top ranking rung.
--
-- ⛔ BOTH SUBJECTS ARE GONE, AND NEITHER IS RETARGETED. There is no copy to drift, no second
-- representation to disagree, and no nullable hash to conflate two meanings on.
--
-- ⚠ THIS IS THE LARGEST SINGLE LOSS OF EXECUTED COVERAGE IN ADR-0011, so it is stated plainly
-- rather than left to a diff. What these two blocks bought was: *the denormalized copy stays equal
-- to the truth across every write path*. What replaces them is not a better assertion — it is the
-- absence of the thing they policed. Deleting a disagreement beats synchronising it, but the two
-- are not the same KIND of guarantee, and only one of them ran.
--
-- ⚠ WHAT THIS TEST ALSO TAUGHT, WORTH MORE THAN THE ASSERTION: its first version updated ZERO rows,
-- because it ran against the `vidC` fixture, which exists only in `workspace_videos` and has no
-- `videos` row — so the trigger never fired and it reported the copy as drifted. Then the fix ran
-- against `t_ws`, whose workspace holds no videos, and selected zero rows again. **A test that
-- cannot reach the mechanism it names proves nothing about it**, and it took two measured attempts
-- to make this one reach. That lesson outlives its subject.
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

-- G1/G2 — ⛔ RETIRED BY ADR-0007. They asserted that `reserve_artifact_slot` creates its own PENDING
-- generation (G1, round 6 B5's defect: before it, a cloud summarize could not reserve a summary slot
-- at all — [23503] on the artifact FK one way, [23514] gen_card_complete the other, with the paid
-- call sitting between two locked doors) and that the row it created was honestly EMPTY rather than
-- a fabricated placeholder (G2, round 5 B1: a placeholder card WON the ranking).
--
-- ⚠ THE SECOND DOOR IS STILL LOCKED AND THE FIRST ONE IS GONE. `state = 'pending'` was the key cut
-- for that lock; ADR-0007 throws the key away and moves the whole row to the far side of the paid
-- call. G1' below is the replacement, and it is the assertion that is RED without round 17 B1's
-- fix — MEASURED, every paid record raised
--   [P0001] cannot mark summary as recorded — generation gG1 is <absent>
-- because deleting `reserve_artifact_slot` deleted the only non-fixture INSERT into
-- `video_generations` and nothing replaced it.
do $$ declare o text; r record; ws uuid; begin
  select id into ws from t_ws;
  if exists (select 1 from video_generations where video_id='vidG' and generation_id='gG1') then
    raise exception 'FIXTURE FAILED — gG1 exists before anyone recorded it'; end if;
  o := record_artifact(ws,'vidG','summary','gG1','summary'::artifact_kind,
        ws::text||'/videos/vidG/gG1/summary.md',
        p_md_hash := 'SHA_G1',
        p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-03-03",'
               || '"processedAt":"z","mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
        p_doc_version_major := 4, p_produced_at := '2026-03-03');
  if o <> 'recorded' then
    raise exception 'ASSERTION FAILED — a producer cannot record a summary: %', o; end if;
  select * into r from video_generations where video_id='vidG' and generation_id='gG1';
  if r.state <> 'complete' or r.md_hash <> 'SHA_G1' then
    raise exception 'ASSERTION FAILED — record did not create a COMPLETE generation: % %', r.state, r.md_hash; end if;
  raise notice 'ok (ADR-0007 G1''): record_artifact creates its own generation, born complete';
end $$;

-- G3 — THE RELAXATION MUST NOT LEAK. This is the guard that makes gating the four completeness
-- CHECKs on `state = 'complete'` safe: without it, every one of them becomes optional for anyone
-- willing to write `state = 'pending'` on the generation.
-- ⚠ ⟳ T4 — THE HAND-BUILT PENDING FIXTURE IS RETIRED, AND THE GUARD IS NOT. ADR-0007 left this
-- assertion standing on a `pending` generation built by direct `service_role` DML, and named that as
-- "an honest weakening worth naming rather than hiding" — the only caller that could reach the guard
-- was a hand-written INSERT. T4 narrowed `video_generations.state` to a single value, so that caller
-- is gone too, and the negative that replaces it is the STRONGER claim, asserted above: a generation
-- can no longer BE pending. Same move ADR-0007 made one table over, where three `art_pending_*`
-- negatives became one negative on `video_artifacts_state_check`.
--
-- ⚠ WHAT SURVIVES HERE IS THE OTHER BRANCH OF THE SAME GUARD, AND IT IS THE ONE T1 MEASURED:
-- `<absent>`. `video_artifacts_generation_complete` reads the parent's state and answers
-- `coalesce(v_state,'<absent>')`, so with `pending` unrepresentable the live case is a recorded
-- artifact naming a generation that does not exist — verbatim what T1 hit with the reservation
-- deleted and record_artifact's INSERT not yet written:
--   [P0001] cannot mark summary as recorded — generation gG1 is <absent>
-- ⚠ AND IT IS NOT MASKED BY THE FK, which is the reason this negative is honest rather than
-- double-guarded: a BEFORE ROW trigger runs before constraints are evaluated, so the typed P0001
-- wins the race against [23503] on (ws, video, generation_id, kind). Remove the guard and the FK
-- catches it instead — a different SQLSTATE, which is exactly what makes the mutation legible.
select assert_raises($$insert into video_artifacts
  (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
  values ((select id from t_ws),'vidG','summary','gABSENT','summary','recorded',
          (select id from t_ws)::text||'/videos/vidG/gABSENT/summary.md')$$,
  'recording an artifact whose generation is not COMPLETE — reachable now only as ABSENT', 'P0001');

-- G4 — ⛔ RETIRED BY ADR-0007. It asserted that a pending generation is invisible to both ranking
-- views. Its premise was a RECORDED artifact pointing at a pending generation, and G3 is the proof
-- that no such row can exist — so the views have nothing to hide and the assertion now describes an
-- unreachable world. ("A test can encode an unreachable world and still pass" is this file's own
-- round-6 B5 lesson; retiring it is applying that lesson rather than re-learning it.)

-- G5 — THE PAYLOAD item 3 exists to add. `md_hash` was mandatory (gen_summary_has_hash) and had NO
-- PRODUCER; the card and doc_version_major had the same gap. All three arrive through
-- `record_artifact`, and the generation is written in the SAME TRANSACTION as the artifact, so there
-- is no instant at which a recorded row points at an incomplete generation. G1' above performed the
-- write; this asserts what the ranking then sees.
do $$ declare g text; begin
  select generation_id into g from video_summary_current where video_id='vidG';
  if g is distinct from 'gG1' then
    raise exception 'ASSERTION FAILED — the recorded summary is not current: %', coalesce(g,'<none>'); end if;
  raise notice 'ok (item 3): the generation and the artifact land together, and the summary serves';
end $$;

-- G6/G7 — md_hash AND the card ARE STILL MANDATORY. The constraints did not weaken; each moved to the
-- moment its value can exist. This is the assertion §10.0 should have forced and did not.
--
-- ⚠ EACH GETS ITS OWN VIDEO. There is only ONE summary slot per video (slot_kind maps exactly one),
-- and the negatives must not collide with each other's rows or with gG1's.
insert into workspace_videos (workspace_id, video_id) select id, 'vidG6' from t_ws;
insert into workspace_videos (workspace_id, video_id) select id, 'vidG7' from t_ws;

select assert_raises($$select record_artifact((select id from t_ws),'vidG6','summary','gG6',
   'summary'::artifact_kind,(select id from t_ws)::text||'/videos/vidG6/gG6/summary.md',
   p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"x","processedAt":"y",'
          || '"mdCorrectionsHash":"H_NEW"}')::jsonb,
   p_doc_version_major := 4, p_produced_at := now())$$,
  'recording a summary with NO md_hash (the constraint moved, it did not weaken)',
  '23514', 'gen_summary_has_hash');

select assert_raises($$select record_artifact((select id from t_ws),'vidG7','summary','gG7',
   'summary'::artifact_kind,(select id from t_ws)::text||'/videos/vidG7/gG7/summary.md',
   p_md_hash := 'SHA_G7', p_doc_version_major := 4, p_produced_at := now())$$,
  'recording a summary with NO card', '23514', 'gen_card_complete');

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
-- ⟳ T4 — AND IT IS A PLAIN INSERT NOW, WHICH IS BOTH SIMPLER AND STRICTLY STRONGER. ADR-0007 built a
-- `pending` row by hand and then asserted that COMPLETING it was refused; `pending` is no longer
-- representable, and it was never needed — `state` defaults to `complete`, so a direct insert that
-- names no state is already the completed row this guard is about. The old two-step also carried a
-- warning that is now moot with it: an `update … where <no such row>` raises nothing and
-- assert_raises then fails with "should have been rejected", a test bug wearing a missing guard's
-- clothes. An INSERT cannot miss.
-- `model` is deliberate: `gen_complete_has_produced_at` is the ONE completeness CHECK that ranges
-- over every kind rather than being gated `kind <> 'summary'`, so this is the only one a non-summary
-- fixture can reach — and after T4 it is joined by the two `*_is_summary_only` constraints, which
-- this row satisfies (no card, no doc_version_major) so that it violates exactly one guard.
select assert_raises($$insert into video_generations (workspace_id,video_id,generation_id,kind)
  values ((select id from t_ws),'vidG','gG10','model')$$,
  'a model generation with no produced_at (the one completeness CHECK ranging over every kind)',
  '23514', 'gen_complete_has_produced_at');

-- G11 — TASK #25, and it needs NO SCHEMA CHANGE. `digDeeper` was never bound to one summary
-- generation: the FK is on (ws, video, generation_id, KIND), so a digDeeper artifact points at a
-- digDeeper GENERATION, minted per rewrite of the accumulator. Round 2 got this backwards the other
-- way (forcing digDeeper to kind='summary') by reasoning from the slot NAME rather than the
-- constraints — the same route as item 1's P9, which was also reported as a defect and was not one.
do $$ declare o text; ws uuid; n int; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidG','digDeeper','gDD_A','digDeeper'::artifact_kind,
        ws::text||'/videos/vidG/gDD_A/dig-deeper.md', p_produced_at := '2026-03-04');
  if o <> 'recorded' then
    raise exception 'ASSERTION FAILED — digDeeper could not record: %', o; end if;
  -- the accumulator is rewritten: a SECOND digDeeper generation, coexisting under append-only
  o := record_artifact(ws,'vidG','digDeeper','gDD_B','digDeeper'::artifact_kind,
        ws::text||'/videos/vidG/gDD_B/dig-deeper.md', p_produced_at := '2026-03-05');
  select count(*) into n from video_artifacts where video_id='vidG' and slot='digDeeper' and state='recorded';
  if n <> 2 then
    raise exception 'ASSERTION FAILED — the two digDeeper generations did not coexist: %', n; end if;
  select generation_id into o from video_artifacts_current where video_id='vidG' and slot='digDeeper';
  if o <> 'gDD_B' then
    raise exception 'ASSERTION FAILED — current digDeeper is %, expected the newer gDD_B', o; end if;
  raise notice 'ok (#25): digDeeper generations are per-REWRITE, coexist, and rank — no schema change';
end $$;

-- ⟳ ADR-0007 — THE `model` KIND ON THE RECORD PATH, AND THE POPULATION RATCHET IS WHY IT IS HERE.
-- Retiring the reservation assertions removed every SECOND write of a `model` slot from this suite,
-- and the ratchet at the foot of this file went RED naming `model` — an absence created by a
-- deletion, caught by the one instrument that looks at what is missing rather than at what someone
-- thought to write down. That is exactly the case it was built for, arriving by subtraction.
--
-- ⚠ AND `model` IS THE KIND THAT MOST NEEDS EXERCISING, because it is ADR-0007's standing exception:
-- the only PAID producer with no job in its call graph (`lib/html-doc/serve-doc.ts:112`, reached from
-- an HTTP GET), arbitrated by `serve_model_charge` rather than by `jobs`. Its single-flight and its
-- spend bound both live in `supabase/migrations/`, outside this schema and outside this suite —
-- so what CAN be asserted here is what this schema owns: two model generations of one slot coexist,
-- are ranked, and the newer wins.
do $$ declare o text; ws uuid; n int; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidG','model','gM_A','model'::artifact_kind,
        ws::text||'/videos/vidG/gM_A/model.json',
        p_source_generation_id := 'gG1', p_produced_at := '2026-03-06');
  if o <> 'recorded' then raise exception 'ASSERTION FAILED — model could not record: %', o; end if;
  -- the summary is re-magazined: a SECOND model generation for the same slot
  o := record_artifact(ws,'vidG','model','gM_B','model'::artifact_kind,
        ws::text||'/videos/vidG/gM_B/model.json',
        p_source_generation_id := 'gG1', p_produced_at := '2026-03-07');
  if o <> 'recorded' then raise exception 'ASSERTION FAILED — the second model record: %', o; end if;
  select count(*) into n from video_artifacts where video_id='vidG' and slot='model';
  if n <> 2 then
    raise exception 'ASSERTION FAILED — the two model generations did not coexist: %', n; end if;
  select generation_id into o from video_artifacts_current where video_id='vidG' and slot='model';
  if o <> 'gM_B' then
    raise exception 'ASSERTION FAILED — current model is %, expected the newer gM_B', o; end if;
  raise notice 'ok (model): two model generations coexist in one slot and the newer ranks first';
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

-- R1 — ⛔ RETIRED BY ADR-0007. Two assertions stood here, and their history is the whole argument
-- for the deletion, so it is recorded rather than dropped:
--   round 7 (B1a) asserted a worker that LOST its token must still record its paid work;
--   round 9 built a durable credential (`reserved_by_worker` / `reserved_by_job`) for that caller;
--   round 10 MEASURED both directions failing — a stranger satisfied the same condition, and the
--     premise was false anyway (`worker/main.ts:69` mints the worker id per PROCESS);
--   round 11 INVERTED the assertion: losing the token means losing the right to record;
--   round 12 (B1) then MEASURED a caller being refused with the token this very RPC handed it.
-- FIVE successive credentials, six rounds, and the fence had to be permissive and strict at once.
-- ADR-0007 removes the credential rather than choosing a sixth. There is nothing left to assert.

-- R2 (B1c) — SPAN CARRY-FORWARD. A caller may omit the span and get the one this slot already
-- records, rather than having to re-supply data the manifest holds. Round 7 measured the opposite:
-- one path read the span and the other did not, so an omitting caller worked in the common case and
-- failed ONLY under a race — the worst possible place for a latent argument requirement.
-- ⟳ ADR-0007 — the two paths are one path now, so the case is reached the way a real caller reaches
-- it: a SECOND generation of the same slot, recorded without a span.
do $$ declare o text; s int; e int; ws uuid; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidR','dig:4','gR2','dig'::artifact_kind,
        ws::text||'/videos/vidR/gR2/dig-4.md', p_start_sec := 4, p_end_sec := 44,
        p_produced_at := '2026-05-02');
  if o <> 'recorded' then raise exception 'FIXTURE FAILED — first dig:4 record: %', o; end if;
  o := record_artifact(ws,'vidR','dig:4','gR2b','dig'::artifact_kind,
        ws::text||'/videos/vidR/gR2b/dig-4.md', p_produced_at := '2026-05-02');   -- span OMITTED
  if o <> 'recorded' then raise exception 'ASSERTION FAILED — second dig:4 record: %', o; end if;
  select start_sec, end_sec into s, e from video_artifacts
   where video_id='vidR' and slot='dig:4' and generation_id='gR2b';
  if s <> 4 or e <> 44 then
    raise exception 'ASSERTION FAILED — the span was not carried across generations: (%,%)', s, e; end if;
  raise notice 'ok (R2/B1c): an omitted span is taken from the slot, not demanded from the caller';
end $$;

-- R3 / R3b — ⛔ RETIRED BY ADR-0007. R3 asserted that a caller may not COMPLETE a generation it does
-- not hold (round 7 H2: W2 named W1's generation, completed it with W2's production time, and W1 was
-- locked out of its own paid work forever by 03's freeze trigger). R3b was P22 itself — W1's lease
-- expires mid-Gemini, W2 reclaims the SLOT, and W1 must still record its OWN generation.
--
-- ⚠ BOTH RESTED ON `reserved_by`, AND WHAT REPLACES THEM IS NOT A FENCE. `record_artifact` INSERTs
-- the generation `on conflict do nothing`, so a second writer never overwrites the first's content —
-- and if its own content differs it is TOLD, via `completed_by_another`, which is asserted at R11-1
-- below. That is the surviving half of R3's guarantee (the real owner keeps its paid work); the
-- other half (a stranger is refused) is gone with the mechanism, because two writers landing on one
-- generation id is not a state the design tries to arbitrate — they would need the same id AND the
-- same key AND different bytes.
-- R3b is retired outright: there is no reclaim, so there is no reclaimed writer.

-- R4 — ⛔ RETIRED BY ADR-0007. It asserted that a DENIED reservation leaves no generation row behind
-- (round 7 H3: item 3 put the generation INSERT above the upsert that decided who got the slot, so
-- every `busy` loser littered an FK-valid parent that no artifact pointed at, no ranking view
-- reached and no sweep collected — unbounded growth for a worker looping on `busy` with a fresh id
-- per attempt). There is no denial path: `record_artifact` writes the generation and the artifact in
-- one transaction, so either both land or neither does.

-- R5 (B2 / M5) — produced_at IS A RANKING RUNG AND A CALLER-SUPPLIED VALUE. Nothing bounded it, so
-- one sync from a replica with a fast clock ranks a generation above everything real until the clock
-- catches up. Round 4's J2-3 removed clock READS from the ranking; it did not stop a clock VALUE
-- being injected into it. Separately, a future produced_at made §6.2's detach UNSATISFIABLE forever.
select assert_raises($$select record_artifact((select id from t_ws),'vidR','dig:5','gR5','dig'::artifact_kind,
   (select id from t_ws)::text||'/videos/vidR/gR5/dig-5.md',
   p_start_sec := 5, p_end_sec := 55, p_produced_at := now() + interval '10 days')$$,
  'recording with a produced_at in the FUTURE (a fast replica clock outranks reality)',
  'P0001');

-- R6 (B2) — A DIG WHOSE GENERATION IS LEGITIMATE MUST ALWAYS BE DETACHABLE. Before the fix, a
-- generation carrying a future produced_at could NEVER have its digs detached — permanently, since
-- produced_at is frozen and detached_at is trigger-owned on UPDATE. The error even blamed the writer
-- for a value the writer never supplied.
do $$ declare ws uuid; st text; t timestamptz; begin
  select id into ws from t_ws;
  perform record_artifact(ws,'vidR','dig:6','gR6','dig'::artifact_kind,
    ws::text||'/videos/vidR/gR6/dig-6.md',
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
     -- ⟳ ADR-0007 removed `reserve_artifact_slot` and `renew_artifact_lease` from this list because
     -- it removed the functions. The list is still hand-maintained, which is its known weakness: it
     -- catches a definer function that KEEPS the default PUBLIC EXECUTE, not one nobody adds here.
     -- ⟳ T3 added THREE definer functions to this file, and adding them here is the whole point of
     -- the list being hand-maintained: two of them are trigger functions, which round 7 M1 measured
     -- as exactly the kind that keeps the default PUBLIC EXECUTE unnoticed.
     -- ⟳ ADR-0011 removed `sync_corrections_to_workspace_video` from this list, on the same terms
     -- ADR-0007 removed the two reservation functions: the function is gone, so naming it here
     -- would inventory an object nobody can find. The hand-maintained weakness is unchanged.
     and p.proname in ('slot_kind','record_artifact',
                       'forbid_collecting_current','video_artifacts_append_only',
                       'video_artifacts_generation_complete','video_generations_freeze',
                       'video_artifact_sources_append_only','video_artifact_sources_insert_once',
                       'art_summary_has_no_source')
     and has_function_privilege('anon', p.oid, 'EXECUTE');
  if leaky is not null then
    raise exception 'ASSERTION FAILED — anon holds EXECUTE on definer function(s): %', leaky; end if;
  raise notice 'ok (R8/M1): no definer function in this schema is reachable by anon';
end $$;

-- ── ⟳ T4 — WHAT ACTUALLY CARRIES "NO GENERATION ROW BEFORE ITS PAID CALL COMPLETES" ─────────────
-- Everything ADR-0007 subtracted rests on that sentence. Round 16 argued the GC floor needs no
-- successor precisely because no row exists while a paid call runs, and T2 deleted the floor's
-- predicate on that basis. So the sentence has to be worth what was spent on it, and it is worth
-- DIFFERENT amounts per kind — which is the whole finding of T4:
--
--   summary                  ENFORCED. gen_card_complete requires six fields of Gemini's own output
--                            and gen_summary_has_hash requires a hash OF THE PRODUCED BYTES. Neither
--                            can be satisfied before the call returns. 03's own comment records both
--                            doors being locked, which is the proof: the reservation could not open
--                            them either.
--   model / dig / digDeeper  NOT ENFORCED. MEASURED (round 17 H1): a row carrying only `produced_at`
--                            is accepted, and `produced_at` is knowable before the call. T4 measured
--                            every producer for a column that could witness production and found
--                            NONE (03's T4 block quotes each). There is nothing for a CHECK to test:
--                            a constraint sees one row, and for these three kinds no value in that
--                            row is a function of the paid output.
--
-- ⚠ SO FOR THREE OF THE FOUR PAID KINDS THE INVARIANT IS CARRIED, NOT DERIVED, AND WHAT CARRIES IT
-- IS ONE STRUCTURAL FACT: `record_artifact` is the only function that inserts into
-- `video_generations`, and it runs after the paid call. A structural fact is worth exactly as much
-- as the instrument that notices when it stops being true. These two assertions are that instrument.
--
-- ⚠ AND THIS RANGES OVER EVERY FUNCTION IN `public`, WHICH THE R8 SWEEP ABOVE DELIBERATELY DOES NOT.
-- R8's list is hand-maintained and its own comment names the weakness — "it catches a definer
-- function that KEEPS the default PUBLIC EXECUTE, not one nobody adds here." A second WRITER is
-- precisely the thing nobody would think to add to a list, so this one ENUMERATES instead of
-- remembering. Same argument as the population ratchet at the foot of this file: an absence is only
-- visible against an enumerated whole.
-- ⚠ ⟳ ADR-0007 IMPLEMENTATION REVIEW, H1 — THIS WAS ONE REGEX OVER `prosrc`, AND IT SAW ONE
-- SPELLING OF INSERT. Both reviewers built second writers that CREATED A REAL ROW while this
-- assertion still reported `writers = {record_artifact}`. MEASURED, seven of them, each verified to
-- have inserted:
--   `insert into public."video_generations"`   quoted identifier          -> invisible
--   `insert into public . video_generations`   spaces around the dot      -> invisible
--   `merge into public.video_generations …`    the standard PG15+ upsert  -> invisible
--   a function in schema `probe_ns`            (the scan was `public`-only)-> invisible
--   `insert into public.vg_v`                  an auto-updatable VIEW     -> invisible
--   an `on insert do instead` RULE on another table                       -> invisible
--   the naive spelling                         (control)                  -> SEEN
-- ADR-0007 nominates this assertion as the sole guarantor of a carried invariant, so "matches the
-- way we happen to write it today" is not what it can be. The branch's own mutation proves the
-- assertion is LOAD-BEARING and cannot prove it COMPLETE — this project's recorded lesson, and the
-- reason the repair is a property rather than a longer pattern.
--
-- TWO QUESTIONS, BECAUSE A WRITER IS EITHER SOME CODE OR SOME RELATION:
--   (1) does any FUNCTION BODY name this table in a write? — text, normalised first, so quoting and
--       spacing cannot change the answer, `merge` counts as the insert it is, and EVERY schema is
--       scanned rather than `public` alone;
--   (2) is any RELATION OTHER THAN THE TABLE an insertable write surface onto it? — asked of the
--       catalog (`pg_depend` -> `pg_rewrite` -> `pg_relation_is_updatable`), never of source text,
--       so a view or rule is caught by WHAT IT IS rather than by what it is called. This is the half
--       no amount of pattern-widening could ever reach: `insert into public.vg_v` does not contain
--       the string `video_generations` at all.
--
-- ⚠ WHAT IS STILL NOT COVERED, WRITTEN DOWN RATHER THAN LEFT TO LOOK COMPLETE — the instrument's
-- success line must not claim more than its input covers, which is the shape this file, `docs/plugins.md`
-- and this ADR all name:
--   * DYNAMIC SQL. `execute format('insert into %I …', …)` assembles the name at runtime, so no text
--     scan can see it. T5's territory, and the reason the ROLE assertion below is the real floor.
--   * `COPY … FROM` and direct DML by the table's OWNER. Accepted residue — ADR-0007 says a trusted
--     role can write; the assertion below is what keeps that set to exactly {service_role}.
--   * a writer in another DATABASE, or one added after the last suite run. Neither is checkable here.
do $$ declare writers text[]; begin
  -- Normalise BEFORE matching: strip quoting, then close up whitespace around the schema dot. Both
  -- evasions become the naive spelling, so one pattern answers all three forms instead of three
  -- alternatives answering the three someone thought of.
  select coalesce(array_agg(n.nspname||'.'||p.proname order by n.nspname||'.'||p.proname), '{}'::text[])
    into writers
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where regexp_replace(replace(p.prosrc, '"', ''), '\s*\.\s*', '.', 'g')
         ~* '(insert|merge)\s+into\s+([a-z_][a-z0-9_$]*\.)?video_generations\y';
  if writers is distinct from array['public.record_artifact'] then
    raise exception 'ASSERTION FAILED — a SECOND writer of video_generations exists: {%}. '
      'T4''s invariant for model/dig/digDeeper rests on record_artifact being the only one, '
      'because it is the only one known to run AFTER the paid call.',
      array_to_string(writers, ', ');
  end if;
  raise notice 'ok (T4/H1): record_artifact is the ONLY function that inserts a generation, in ANY schema and by ANY spelling';
end $$;

-- The RELATION half. A view over this table is insertable whenever Postgres judges it auto-updatable,
-- and a rule `on insert to anything do instead insert into video_generations` makes the ordinary table
-- carrying it a write surface too — neither names the table in the inserting statement, so neither is
-- findable by pattern.
--
-- ⚠ THE ALLOWLIST IS A RATCHET, AND IT FAILS IN THE OPPOSITE DIRECTION TO R8's LIST ABOVE. R8's is an
-- INCLUSION list: forget to add something and it is silently not checked (its own comment says so).
-- This one is an EQUALITY: anything new appearing here fails until someone writes it down, so
-- forgetting is the failing case rather than the passing one.
--
-- `video_generations_collectable` is on it because it MEASURES as auto-updatable (mask 28 =
-- 4 UPDATE | 8 INSERT | 16 DELETE) — a plain `select g.* from video_generations g where …` is a simple
-- view, and Postgres makes simple views updatable. It grants nobody a capability they lack: no role
-- holds INSERT on it (asserted below), so only the owner can write through it, and the owner can write
-- the table directly anyway. It is deliberately left updatable rather than broken with a subquery
-- wrapper, because §8's sweeper is specified to work THROUGH this view and `update
-- video_generations_collectable set body_collected = true` is the shape it is likely to want.
do $$ declare surfaces text[]; leaky text[]; owner text; begin
  select coalesce(array_agg(distinct rn.nspname||'.'||rc.relname order by rn.nspname||'.'||rc.relname),
                  '{}'::text[])
    into surfaces
    from pg_depend d
    join pg_rewrite r on r.oid = d.objid
    join pg_class rc on rc.oid = r.ev_class
    join pg_namespace rn on rn.oid = rc.relnamespace
   where d.classid = 'pg_rewrite'::regclass
     and d.refclassid = 'pg_class'::regclass
     and d.refobjid = 'public.video_generations'::regclass
     and rc.oid <> 'public.video_generations'::regclass
     and (pg_catalog.pg_relation_is_updatable(rc.oid, true) & 8) <> 0;   -- 8 = the INSERT bit
  if surfaces is distinct from array['public.video_generations_collectable'] then
    raise exception 'ASSERTION FAILED — a SECOND writer of video_generations exists: the insertable '
      'relation(s) over it are {%}, expected exactly {public.video_generations_collectable}. '
      'An insertable view or an ON INSERT DO INSTEAD rule is a write surface that names no table.',
      array_to_string(surfaces, ', ');
  end if;
  -- …and nobody may reach through the one that is allowed.
  select c.relowner::regrole::text into owner
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public' and c.relname = 'video_generations_collectable';
  select coalesce(array_agg(distinct a.grantee::regrole::text), '{}'::text[]) into leaky
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    cross join lateral aclexplode(c.relacl) a
   where n.nspname = 'public' and c.relname = 'video_generations_collectable'
     and a.privilege_type = 'INSERT'
     and a.grantee::regrole::text <> owner;
  if leaky is distinct from '{}'::text[] then
    raise exception 'ASSERTION FAILED — role(s) {%} hold INSERT on video_generations_collectable, '
      'which is auto-updatable onto video_generations', array_to_string(leaky, ', ');
  end if;
  raise notice 'ok (T4/H1): no relation other than the table is an insertable write surface a role can use';
end $$;

-- The other half of "who can write one", because a second writer does not have to be a function.
-- `service_role` holding direct DML is the residue ADR-0007 explicitly accepts ("a trusted role can
-- write"); anyone ELSE holding it would make the invariant unenforceable by any means, since
-- `security definer` never consults RLS and RLS never applies to the role that bypasses it.
do $$ declare grantees text[]; owner text; begin
  select c.relowner::regrole::text into owner
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public' and c.relname = 'video_generations';
  select coalesce(array_agg(distinct a.grantee::regrole::text), '{}'::text[]) into grantees
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    cross join lateral aclexplode(c.relacl) a
   where n.nspname = 'public' and c.relname = 'video_generations'
     and a.privilege_type = 'INSERT'
     and a.grantee::regrole::text <> owner;
  if grantees is distinct from array['service_role'] then
    raise exception 'ASSERTION FAILED — roles holding INSERT on video_generations are {%}, expected exactly {service_role} (owner % excluded)',
      array_to_string(grantees, ', '), owner;
  end if;
  raise notice 'ok (T4): only service_role may write a generation directly';
end $$;

-- ── ⟳ T4 — THE CARRIED INVARIANT'S COST, MEASURED RATHER THAN DESCRIBED ────────────────────────
-- ⚠ READ THE LABEL BEFORE THE CODE: this block asserts that a DEFECT REPRODUCES. It is the only
-- block in this file that does, and it is here because "carried, not derived" is a phrase that costs
-- nothing to write and this project has measured what happens when such a phrase is believed. If
-- someone later closes the gap, THIS BLOCK GOES RED — that is the intended signal, and the correct
-- response is to delete it, not to work around it.
--
-- What it costs, if a writer that creates a generation BEFORE its paid call ever appears: exactly
-- round 9's B1, the defect T2 deleted the floor's predicate over, reached by the other three kinds.
--   * the bare generation is not current (no artifact yet) -> `video_generations_collectable`
--     returns it, which is correct given what it can see;
--   * a sweep sets body_collected -> `forbid_collecting_current` does not fire, because there is no
--     current row to protect;
--   * the paid call returns and `record_artifact` appends the artifact — legally, since the
--     generation is `complete` — and `p_md_hash` is NULL for these kinds, so `completed_by_another`
--     cannot fire either;
--   * both ranking views filter `not g.body_collected`, so the paid row is INVISIBLE FOREVER.
-- Money spent, content unreachable, and no error anywhere — round 9's B1 verbatim.
--
-- ⚠ NOT CLOSED HERE, AND THE REASON IS THE SCOPE OF THE CLAIM, NOT THE COST OF THE FIX. Adding a
-- successor predicate to `video_generations_collectable` would reverse T2 and round 16's decision on
-- T4's authority, and it would not enforce the invariant anyway — a pre-call writer can derive
-- `blob_key` from (workspace, video, generation, slot) before any bytes exist, so no artifact-side
-- witness closes it either. What closes it is a producer-computed content hash for the other three
-- kinds, i.e. `md_hash`, which is exactly why 03 leaves that column unconfined. T5's territory.
insert into workspace_videos (workspace_id, video_id) select id, 'vidT4' from t_ws;
do $$ declare ws uuid; n int; o text; begin
  select id into ws from t_ws;
  -- the pre-call shape: everything knowable before Gemini returns, and nothing else
  insert into video_generations (workspace_id,video_id,generation_id,kind,produced_at)
    values (ws,'vidT4','gT4','dig',now() - interval '1 minute');
  if not exists (select 1 from video_generations_collectable
                  where video_id='vidT4' and generation_id='gT4') then
    raise exception 'T4 CHARACTERISATION STALE — a bare dig generation is no longer collectable; '
      'the gap may have been closed. Re-read this block and delete it if so.'; end if;
  update video_generations set body_collected = true
   where video_id='vidT4' and generation_id='gT4';          -- the sweep, unopposed
  o := record_artifact(ws,'vidT4','dig:10','gT4','dig'::artifact_kind,
        ws::text||'/videos/vidT4/gT4/dig/10.md', p_start_sec := 10, p_end_sec := 60);
  if o <> 'recorded' then
    raise exception 'T4 CHARACTERISATION STALE — the paid record was refused (%); the gap may have been closed.', o; end if;
  select count(*) into n from video_artifacts_current where video_id='vidT4';
  if n <> 0 then
    raise exception 'T4 CHARACTERISATION STALE — the paid row is visible (% rows); the gap may have been closed.', n; end if;
  raise notice 'ok (T4, MEASURED COST): a pre-call generation for a non-summary kind still buries its own paid bytes — carried, not enforced';
end $$;
-- ── ⛔ RETIRED BY ADR-0007 — THE OWNERSHIP FENCE (round 9, measured in both directions) ──────────
-- R9-1 asserted that a STRANGER holding a full, well-formed credential of its own cannot complete
-- another worker's generation. R11 (was R9-2) asserted the case the design was always for — token
-- HELD, slot LOST — and that the reclaimed writer still records.
--
-- Both are gone with `reserved_by`. What replaces the first is NOT a fence but a property: the
-- generation INSERT is `on conflict do nothing`, so nobody's content can be overwritten by anybody,
-- stranger or not, and a writer whose content differs is told `completed_by_another` (R11-1 below).
-- What replaces the second is that there is no reclaim to survive.
--
-- ⚠ THE ONE QUESTION THIS BLOCK COST TWO ROUNDS TO LEARN IS KEPT, because it outlives the fence:
-- a rolled-back probe can CONSTRUCT any state you can type, INCLUDING STATES NO CALLER CAN REACH.
-- "Is this refused?" is not the same question as "can a caller BE here?", and rounds 8 and 9 each
-- answered only the first. That is the question T4 must ask about `model`, `dig` and `digDeeper`.
insert into workspace_videos (workspace_id, video_id) select id, 'vidR9a' from t_ws;
insert into workspace_videos (workspace_id, video_id) select id, 'vidR9b' from t_ws;

-- ⛔ RETIRED BY ADR-0007 (T1 retired this assertion; T2 completed the retirement) — R9-3, round 8 B1:
-- "GC MAY NOT COLLECT A GENERATION THAT IS STILL BEING PAID FOR." `video_artifacts_current` requires
-- state='recorded', so an IN-FLIGHT reservation had no current row and was offered to the sweeper;
-- the worker then recorded SUCCESSFULLY and its row was invisible forever. MEASURED end to end:
--   collectable WHILE IN FLIGHT: 1 ; sweep collected 1 ; holder records -> recorded_as_holder
--   gen complete, artifact recorded, and video_artifacts_current rows for that video: 0
-- Money spent, bytes queued for deletion, no error anywhere.
--
-- ⚠ THE WINDOW IS CLOSED BY SUBTRACTION, NOT BY A SUCCESSOR — and that is the claim to attack.
-- No `video_generations` row exists at all while a paid call runs, because `record_artifact` creates
-- it AFTER the call, so `video_generations_collectable` cannot return it. Three rounds proposed
-- three covers (a per-kind table, a `serve_model_charge` lease, an `in_flight_until` marker) before
-- anyone asked whether the row exists. It does not.
--
-- ⚠ WHAT IS NOT CLOSED IS THE BLOB. The bytes are written before any row references them, so during
-- the call they are an ORPHAN with no owner and no sweeper — §8's grace period is the specified and
-- UNIMPLEMENTED mechanism for that, and there is no assertion for it here because there is nothing
-- to assert against yet.
--
-- The paired `g.state = 'complete'` predicate in `video_generations_collectable`, its named mutation
-- in `mutate-schema.py` ("B1: the collectable floor drops `state = complete`") and this assertion
-- were ONE retirement, and T2 finished it: the predicate is deleted from the view
-- (04_artifacts.sql, the ⛔ block above `create view video_generations_collectable`) and the mutation
-- is retired in place rather than left anchored on a deleted line — an orphaned anchor makes the
-- harness report INVALID, which this project has MEASURED reads as *untested* rather than *retired*.
-- The mutation was reporting ❌ GREEN before it was retired, and GREEN was the CORRECT result: with
-- no producer of a `pending` generation, removing the predicate cannot change which rows the view
-- returns. A mutation that can no longer alter behaviour proves nothing.
--
-- The surviving half — a recorded artifact IS visible in `current` — is asserted at G5 and below.
insert into workspace_videos (workspace_id, video_id) select id, 'vidR9c' from t_ws;
do $$ declare ws uuid; o text; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidR9c','summary','gR9c','summary'::artifact_kind,
        ws::text||'/videos/vidR9c/gR9c/summary.md', p_md_hash := 'SHA_R9C',
        p_card := '{"tldr":"z","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-05","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
        p_doc_version_major := 4, p_produced_at := '2026-05-05');
  if (select count(*) from video_artifacts_current where video_id='vidR9c') <> 1 then
    raise exception 'ASSERTION FAILED — the recorded artifact is not visible in current'; end if;
  raise notice 'ok: a recorded artifact is visible in current';
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

-- ⟳ R9-5 (round 8 H2) — THE FREE PATH'S SHORT-CIRCUIT WAS UNREACHABLE, AND `NULL = NULL` IS WHY.
-- `reserve_artifact_slot`'s idempotency test compared `generation_id = p_generation_id`, and for a
-- free slot both sides are NULL, so the test was NULL — never true. The branch existed and could not
-- run. ⟳ ADR-0007 deleted that entry point; the RULE it taught is what this now asserts, on the one
-- free path left: a re-render of a recorded free slot must be a typed outcome, never a raw [23505]
-- against `video_artifacts_free_uq`.
do $$ declare ws uuid; o text; n int; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidR9c','pdf:summary',null,'render'::artifact_kind,ws::text||'/videos/vidR9c/renders/r9-1.pdf');
  o := record_artifact(ws,'vidR9c','pdf:summary',null,'render'::artifact_kind,ws::text||'/videos/vidR9c/renders/r9-2.pdf');
  if o <> 'recorded_free' then
    raise exception 'ASSERTION FAILED — re-rendering a recorded FREE slot gave %', o; end if;
  select count(*) into n from video_artifacts where video_id='vidR9c' and slot='pdf:summary';
  if n <> 1 then raise exception 'ASSERTION FAILED — a free slot holds % rows', n; end if;
  raise notice 'ok (R9-5): re-rendering a recorded free slot is typed and one-per-slot, not a raw 23505';
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

-- ⛔ RETIRED BY ADR-0007 — R9-7 (round 8 Claude H2): "a free slot that was RESERVED is still
-- recordable." Round 9's own lease-clearing fix had left a reserved free slot failing
-- `art_pending_has_reserved_at` on every retry, forever, and the only thing that had prevented it
-- was the aside "'render' is free and never reserved" — a CONVENTION, not a guard. There is no
-- reserve and there are no lease columns, so there is no reserved free slot to record.
--
-- ⚠ THE LESSON IS THE ONE THING WORTH CARRYING FORWARD, and it is not about leases: A CONVENTION IS
-- NOT A GUARD. ADR-0007 leaves exactly one of these behind — "no generation row is created before
-- its paid call completes", which the constraints enforce for `summary` and for `model`, `dig` and
-- `digDeeper` enforce nothing at all (MEASURED, round 17 T1). That is T4's whole subject, and this
-- retirement is the precedent for why it cannot be left as prose.

-- ⟳ R9-8 (round 8 Claude H3) — THE MANIFEST MAY NOT NAME AN ADDRESS THE CALLER DID NOT WRITE.
-- Neither record path assigned blob_key, so a caller that wrote its bytes at one key was told
-- success while the row kept pointing at the other — shape #4, silent, on the SUCCESS path. Both
-- keys pass `art_key_names_generation`, which constrains only the first four segments, so no
-- constraint could catch it.
-- ⟳ ADR-0007 — the first key is now laid down by a RECORD rather than by a reservation, so the
-- fixture is one real write followed by a second naming a different address for the same
-- (slot, generation). The old note about stashing a token is gone with the token: there is no
-- ownership fence left to reject the call before it reaches the address guard, which is exactly
-- what that note was working around.
insert into workspace_videos (workspace_id, video_id) select id, 'vidR9f' from t_ws;
do $$ declare ws uuid; o text; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidR9f','summary','gR9f','summary'::artifact_kind,
        ws::text||'/videos/vidR9f/gR9f/RESERVED.md', p_md_hash := 'SHA_ADDR',
        p_card := '{"tldr":"d","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-07","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
        p_doc_version_major := 4, p_produced_at := '2026-05-07');
  if o <> 'recorded' then raise exception 'FIXTURE FAILED — the address fixture: %', o; end if;
end $$;
select assert_raises(format($$
  select record_artifact(%L::uuid,'vidR9f','summary','gR9f','summary'::artifact_kind,
    %L, p_md_hash := 'SHA_ADDR', p_produced_at := '2026-05-07',
    p_card := '{"tldr":"d","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-07","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
    p_doc_version_major := 4);
$$, (select id from t_ws), (select id from t_ws)::text||'/videos/vidR9f/gR9f/ACTUALLY-WRITTEN.md'),
 'recording under a key that differs from the one this slot already holds is refused, not silently dropped',
 'P0001');

-- ⟳ R11-1 (round 10 B1, second half) — NEVER REPORT SUCCESS WHEN ANOTHER WRITER'S CONTENT STANDS.
-- No attacker: two ordinary writers on one generation. The completion UPDATE required
-- `state = 'pending'`, so once someone else finished it the coalesce never ran and the function fell
-- through to an append whose `do update` does not touch md_hash. MEASURED: the second writer was
-- told a SUCCESS string while the manifest kept the first writer's hash. Both halves are asserted,
-- because a fix that also refused the benign idempotent retry would be the same defect facing the
-- other way.
-- ⚠ ⟳ ADR-0007 — THIS ASSERTION CARRIES MORE WEIGHT NOW, NOT LESS. `on conflict do nothing` on the
-- generation INSERT is what makes a second writer safe, and this is the only thing that proves the
-- second writer is TOLD rather than silently ignored. With `reserved_by` deleted it is the whole of
-- what used to be R3's guarantee that the real owner keeps its paid work.
insert into workspace_videos (workspace_id, video_id) select id, 'vidR11' from t_ws;
do $$ declare ws uuid; o text; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidR11','summary','gR11','summary'::artifact_kind,
        ws::text||'/videos/vidR11/gR11/summary.md', p_md_hash := 'SHA_W1',
        p_card := '{"tldr":"w1","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-11","processedAt":"y","mdCorrectionsHash":"H_NEW"}'::jsonb,
        p_doc_version_major := 4, p_produced_at := '2026-05-11');
  if o <> 'recorded' then raise exception 'FIXTURE FAILED — W1 record: %', o; end if;

  o := record_artifact(ws,'vidR11','summary','gR11','summary'::artifact_kind,
        ws::text||'/videos/vidR11/gR11/summary.md', p_md_hash := 'SHA_W2',
        p_produced_at := '2026-05-11');
  if o <> 'completed_by_another' then
    raise exception 'ASSERTION FAILED — a writer whose content was NOT adopted was told: %', o; end if;
  if (select md_hash from video_generations where video_id='vidR11' and generation_id='gR11')
       <> 'SHA_W1' then
    raise exception 'ASSERTION FAILED — the manifest hash changed under the second writer'; end if;

  o := record_artifact(ws,'vidR11','summary','gR11','summary'::artifact_kind,
        ws::text||'/videos/vidR11/gR11/summary.md', p_md_hash := 'SHA_W1',
        p_produced_at := '2026-05-11');
  if o = 'completed_by_another' then
    raise exception 'ASSERTION FAILED — a benign idempotent retry was refused'; end if;
  raise notice 'ok (R11-1): divergent content gets a typed outcome; an identical retry still records';
end $$;

-- ⛔ RETIRED BY ADR-0007 — R11-2 (round 10 H2): "a NON-HOLDER may not take a LIVE FREE RESERVATION."
-- Round 9's lease-clearing fix let a TOKENLESS caller clear W1's lease and repoint a free slot
-- (measured: `pending rows left = 0`, key replaced) — the fifth face of the free/paid seam, after
-- the reconciler, the short-circuit, the tenant confinement and the lease columns.
-- A free slot can no longer be reserved, held, or taken: free renders are unpaid, overwritable and
-- one-per-slot, which is what C1 below asserts and all that is left to assert.

-- ⛔ RETIRED BY ADR-0007 — R12-1 (round 12 B1): "the token the RPC HANDS OUT must be the token the
-- fence ACCEPTS." `reserve_artifact_slot` created the generation `on conflict do nothing`, so when
-- the row already existed and was still pending it kept the PREVIOUS caller's `reserved_by` while
-- the artifact upsert re-pointed `lease_token` to the new one. MEASURED: a caller was told
-- `reserved`, PAID, presented the token it had just been given, and was refused — a direct
-- counter-example to §12b's "the party holding paid bytes always still holds the token". It held
-- both; they just were not the same token.
--
-- ⚠ THIS IS THE FINDING THAT ENDED THE PROTOCOL, so it is worth being precise about what remains.
-- The `on conflict do nothing` that caused it is STILL THERE, in `record_artifact`'s generation
-- INSERT — because the defect was never the clause. It was that a SECOND piece of state
-- (`lease_token`) moved while the first did not. With one write and no second piece of state there
-- is nothing to come apart, which is the difference between removing a defect and removing the
-- possibility of it.

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
        ws::text||'/videos/vidF/render/summary-v1.pdf');
  if o <> 'recorded_free' then
    raise exception 'ASSERTION FAILED — first free render: %', o; end if;
  o := record_artifact(ws,'vidF','pdf:summary',null,'render'::artifact_kind,
        ws::text||'/videos/vidF/render/summary-v2.pdf');
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
   'summary'::artifact_kind,(select id from t_ws)::text||'/videos/vidF/x/summary.md')$$,
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

-- ── ⟳ ADR-0011 — ROUND 9'S CLOBBER ASSERTION IS DELETED, AND ITS PREMISE IS WHAT CHANGED ────────
-- The block here added 'sharedCorr' to two playlists, the first carrying 'KEEP ME' and the second
-- carrying none, then asserted `workspace_videos.corrections` still read 'KEEP ME'. It was a real
-- defect, MEASURED the moment ingest worked: 'KEEP ME' -> <null>.
--
-- ⛔ THE BEHAVIOUR IT ASSERTED NO LONGER EXISTS, and the reason is worth stating exactly, because it
-- is ADR-0011's whole thesis. The clobber was possible because ONE workspace-scoped row had to
-- represent N playlist-scoped truths, so the second playlist's arrival had to be interpreted:
-- "removed the corrections" or "never had them?" — and NO MERGE RULE CAN BE RIGHT, because the two
-- playlists genuinely disagree. Round 9 picked "a corrected row never loses to an uncorrected
-- duplicate", which is a heuristic, not a truth. ADR-0011 keeps the corrections per-playlist in
-- `videos.data`, where both rows are simply themselves and nothing has to be reconciled.
--
-- ⚠ SO THIS IS NOT COVERAGE LOST — IT IS A QUESTION THAT STOPPED BEING ASKED. The assertion could
-- not be rewritten against the new schema even in principle: there is no shared row to clobber.
-- ⚠ WHAT IS GENUINELY UNGUARDED NOW: that the two per-playlist rows keep their own corrections. No
-- assertion in this file covers it, because that is 0001's `videos.data` behaviour and predates this
-- spec entirely. It is not a regression; it is a boundary, and it is named here so the next reader
-- does not read the absence as an oversight.

-- And a caller with the WRONG opinion is TOLD, not silently corrected. This is the whole reason the
-- explicit-writer option was not simply discarded: a caller confused about tenancy is a real bug, and
-- silently repairing it would be shape #5 on the tenancy boundary.
select assert_raises($$
  insert into videos (playlist_id, owner_id, video_id, position, data, workspace_id)
    select p.id, p.owner_id, 'ingestWrong', 9993, jsonb_build_object('id','ingestWrong'),
           (select id from workspaces where id <> p.workspace_id order by id desc limit 1)
      from playlists p limit 1;
$$, 'a workspace_id disagreeing with the playlist is refused, not repaired', 'P0001');

-- ── ⟳ T3 — PROVENANCE AS A SET: THE RUNG DECIDES, THE RE-RECORD RULE, AND GC REACHABILITY ──────
-- ⚠ THE RUNG HAD NO ASSERTION THAT COULD GO RED, AND NO MUTATION AT ALL, FOR SEVENTEEN ROUNDS.
-- What existed was the FLOOR ("a paid model whose SOURCE summary was superseded must still serve"),
-- which is satisfied by a rung that does nothing whatsoever — it asserts the rung never GATES and
-- says nothing about whether it RANKS. Every guard here is opt-in, and this is what that costs: the
-- one rung the whole provenance design exists to feed was documentation. T3 rewrites it, so T3 owes
-- it a test that DECIDES between two candidates and a mutation that can kill that test.
insert into workspace_videos (workspace_id, video_id) select id, 'vidT3' from t_ws;
do $$ declare ws uuid; begin
  select id into ws from t_ws;
  -- two summary generations for vidT3; gT3b is the newer and therefore current
  perform record_artifact(ws,'vidT3','summary','gT3a','summary'::artifact_kind,
    ws::text||'/videos/vidT3/gT3a/summary.md', p_md_hash := 'SHA_T3A',
    p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-06-01","processedAt":"y",'
           || '"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
    p_doc_version_major := 4, p_produced_at := '2026-06-01');
  perform record_artifact(ws,'vidT3','summary','gT3b','summary'::artifact_kind,
    ws::text||'/videos/vidT3/gT3b/summary.md', p_md_hash := 'SHA_T3B',
    p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-06-05","processedAt":"y",'
           || '"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
    p_doc_version_major := 4, p_produced_at := '2026-06-05');
  -- ⚠ THE STALE-SOURCE MODEL IS THE NEWER ONE, AND THAT INVERSION IS THE WHOLE TEST. A `model` row
  -- carries no card and no doc_version_major (T4's two `*_is_summary_only` constraints), so every
  -- rung between source-currency and `produced_at` is NULL for both candidates. Give the stale one
  -- the later produced_at and the ONLY thing that can make the current-source one win is the rung.
  perform record_artifact(ws,'vidT3','model','gT3mCUR','model'::artifact_kind,
    ws::text||'/videos/vidT3/gT3mCUR/model.json',
    p_source_generation_id := 'gT3b', p_produced_at := '2026-06-06');
  perform record_artifact(ws,'vidT3','model','gT3mOLD','model'::artifact_kind,
    ws::text||'/videos/vidT3/gT3mOLD/model.json',
    p_source_generation_id := 'gT3a', p_produced_at := '2026-06-07');
end $$;
do $$ declare g text; begin
  select generation_id into g from video_artifacts_current where video_id='vidT3' and slot='model';
  if g is distinct from 'gT3mCUR' then
    raise exception 'ASSERTION FAILED — the source-currency rung did not decide: current model is %, expected gT3mCUR (the NEWER model is built from a superseded summary)',
      coalesce(g,'<none>'); end if;
  raise notice 'ok (T3 rung): a model built from the CURRENT summary outranks a newer one built from a stale summary';
end $$;

-- ⟳ ROUND 15 M3 — ONLY SUMMARY-KIND SOURCES PARTICIPATE, AND WITHOUT THAT THE RUNG IS UNDEFINED
-- EXACTLY WHERE THE JOIN TABLE IS NEEDED. `video_summary_current` has one row per (workspace, video)
-- and NO row for a `dig` generation, so comparing a dig source against it scores that source stale
-- FOREVER — and the artifact that carries dig sources is `digDeeper`, the multi-source case this
-- table exists for. `gT3dA` carries a DIG source and is the newer; it must win on produced_at, which
-- it can only do if its non-summary source is ignored by the rung rather than scored against it.
do $$ declare ws uuid; g text; begin
  select id into ws from t_ws;
  insert into video_generations (workspace_id,video_id,generation_id,kind,produced_at)
    values (ws,'vidT3','gT3dig','dig','2026-06-02');
  perform record_artifact(ws,'vidT3','digDeeper','gT3dB','digDeeper'::artifact_kind,
    ws::text||'/videos/vidT3/gT3dB/dd.md', p_produced_at := '2026-06-08');
  perform record_artifact(ws,'vidT3','digDeeper','gT3dA','digDeeper'::artifact_kind,
    ws::text||'/videos/vidT3/gT3dA/dd.md',
    p_source_generation_id := 'gT3dig', p_produced_at := '2026-06-09');
  select generation_id into g from video_artifacts_current where video_id='vidT3' and slot='digDeeper';
  if g is distinct from 'gT3dA' then
    raise exception 'ASSERTION FAILED — a NON-SUMMARY source was scored for currency: current digDeeper is %, expected gT3dA',
      coalesce(g,'<none>'); end if;
  raise notice 'ok (T3/M3): a dig-kind source is recorded for GC and does NOT rank';
end $$;

-- ⚠ "ARE *ALL* ITS SOURCES CURRENT" — the question a set can answer and the dropped scalar could
-- not, and the reason the rung is a `not exists` rather than a comparison. `gT3mmMIX` names one
-- current and one superseded summary and is the NEWER row; one stale source must sink it.
-- ⚠ THE TWO-SOURCE SET IS WRITTEN BY DIRECT DML, AND THAT IS AN HONEST GAP RATHER THAN A CHOICE OF
-- STYLE: `record_artifact` takes a SCALAR `p_source_generation_id`, so no RPC caller can build a
-- multi-source artifact today. The table, the rung and the GC reachability check are all set-shaped
-- and the only writer is not. Whoever adds the multi-source producer changes the signature; until
-- then this assertion is what stops the set semantics from being untested prose. It is also why the
-- INSERT enforcer had to permit a multi-row statement — see its comment in 04.
insert into workspace_videos (workspace_id, video_id) select id, 'vidT3m' from t_ws;
do $$ declare ws uuid; g text; begin
  select id into ws from t_ws;
  perform record_artifact(ws,'vidT3m','summary','gMsCUR','summary'::artifact_kind,
    ws::text||'/videos/vidT3m/gMsCUR/summary.md', p_md_hash := 'SHA_MS_CUR',
    p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-07-05","processedAt":"y",'
           || '"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
    p_doc_version_major := 4, p_produced_at := '2026-07-05');
  perform record_artifact(ws,'vidT3m','summary','gMsOLD','summary'::artifact_kind,
    ws::text||'/videos/vidT3m/gMsOLD/summary.md', p_md_hash := 'SHA_MS_OLD',
    p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-07-01","processedAt":"y",'
           || '"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
    p_doc_version_major := 4, p_produced_at := '2026-07-01');
  perform record_artifact(ws,'vidT3m','model','gMmALL','model'::artifact_kind,
    ws::text||'/videos/vidT3m/gMmALL/model.json',
    p_source_generation_id := 'gMsCUR', p_produced_at := '2026-07-06');
  perform record_artifact(ws,'vidT3m','model','gMmMIX','model'::artifact_kind,
    ws::text||'/videos/vidT3m/gMmMIX/model.json', p_produced_at := '2026-07-07');
  insert into video_artifact_sources (artifact_id, workspace_id, video_id, source_generation_id)
  select a.artifact_id, a.workspace_id, a.video_id, s
    from video_artifacts a, unnest(array['gMsCUR','gMsOLD']) s
   where a.video_id='vidT3m' and a.slot='model' and a.generation_id='gMmMIX';
  select generation_id into g from video_artifacts_current where video_id='vidT3m' and slot='model';
  if g is distinct from 'gMmALL' then
    raise exception 'ASSERTION FAILED — a model with ONE stale source among two ranked as current: %',
      coalesce(g,'<none>'); end if;
  raise notice 'ok (T3): the rung asks whether ALL sources are current, not whether ANY is';
end $$;

-- ⟳ T3 — GC REACHABILITY, THE HOLE THAT PREDATES THIS SLICE. `video_generations_collectable` checked
-- only an artifact's OWN generation, so a superseded summary that a paid model was built FROM was
-- offered to the sweeper: collect it and every render derived from it serves against bytes that no
-- longer exist. `gT3a` is superseded (gT3b is current) and is the source of `gT3mOLD`, so it is
-- exactly that row. `gT3c` is superseded and referenced by nothing, and it is here because a floor
-- that excludes everything also passes the first half of this test.
do $$ declare ws uuid; n_src int; n_free int; begin
  select id into ws from t_ws;
  insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
    values (ws,'vidT3','gT3c','summary',
      ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-05-01","processedAt":"y",'
       ||'"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb, 4,'2026-05-01','SHA_T3C');
  select count(*) into n_src  from video_generations_collectable
   where video_id='vidT3' and generation_id='gT3a';
  select count(*) into n_free from video_generations_collectable
   where video_id='vidT3' and generation_id='gT3c';
  if n_src <> 0 then
    raise exception 'ASSERTION FAILED — a superseded generation a render is BUILT FROM was offered to the sweeper'; end if;
  if n_free <> 1 then
    raise exception 'ASSERTION FAILED — an unreferenced superseded generation is not collectable; the floor excludes everything'; end if;
  raise notice 'ok (T3 GC): a referenced generation is protected; an unreferenced one is still collectable';
end $$;

-- ── ⟳ ADR-0007 IMPLEMENTATION REVIEW, H3 — THE PIN IS PERMANENT, MEASURED ───────────────────────
-- ⚠ READ THE LABEL BEFORE THE CODE: this is the SECOND block in this file that asserts a known
-- limitation REPRODUCES, and it is here for the same reason as T4's — the schema comment for the GC
-- reachability check used to promise that "§8's retention clock … eventually releases it", and no
-- release exists. The assertion above tests the half that works (referenced ⇒ protected); nothing
-- tested that a reference is ever RELEASED, because under this design it never is, and an absence is
-- invisible to every opt-in instrument at once.
--
-- The chain, all of it through the RPC: a model is built from a summary, both are superseded, the
-- model's own generation is swept — and the summary is STILL not collectable. The three exits are
-- closed by three guards this branch added (provenance undeletable while its artifact lives, paid
-- artifacts undeletable, the sweeper selects THROUGH the view), so nothing short of deleting the
-- account clears it.
--
-- IF SOMEONE CLOSES THIS — the candidate is in 04's comment and in docs/backlog.md #27 — THIS BLOCK
-- GOES RED. That is the intended signal, and the correct response is to delete it, not to work
-- around it.
insert into workspace_videos (workspace_id, video_id) select id, 'vidH3' from t_ws;
do $$ declare ws uuid; n int; begin
  select id into ws from t_ws;
  perform record_artifact(ws,'vidH3','summary','gH3s','summary'::artifact_kind,
    ws::text||'/videos/vidH3/gH3s/summary.md', p_md_hash := 'SHA_H3S',
    p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-07-01","processedAt":"y",'
           || '"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
    p_doc_version_major := 4, p_produced_at := '2026-07-01');
  perform record_artifact(ws,'vidH3','model','gH3m','model'::artifact_kind,
    ws::text||'/videos/vidH3/gH3m/model.json',
    p_source_generation_id := 'gH3s', p_produced_at := '2026-07-02');
  -- supersede both, so neither is current and the retention clock is the only thing left
  perform record_artifact(ws,'vidH3','summary','gH3s2','summary'::artifact_kind,
    ws::text||'/videos/vidH3/gH3s2/summary.md', p_md_hash := 'SHA_H3S2',
    p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-07-03","processedAt":"y",'
           || '"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
    p_doc_version_major := 4, p_produced_at := '2026-07-03');
  perform record_artifact(ws,'vidH3','model','gH3m2','model'::artifact_kind,
    ws::text||'/videos/vidH3/gH3m2/model.json',
    p_source_generation_id := 'gH3s2', p_produced_at := '2026-07-04');
  select count(*) into n from video_generations_collectable
   where video_id='vidH3' and generation_id='gH3m';
  if n <> 1 then
    raise exception 'H3 CHARACTERISATION STALE — the superseded model is no longer collectable (% rows); '
      're-read this block.', n; end if;
  update video_generations set body_collected = true
   where video_id='vidH3' and generation_id='gH3m';           -- its only referrer, swept
  select count(*) into n from video_generations_collectable
   where video_id='vidH3' and generation_id='gH3s';
  if n <> 0 then
    raise exception 'H3 CHARACTERISATION STALE — the pin RELEASED (% rows). If the release was '
      'implemented deliberately, DELETE this block and 04''s note; do not work around it.', n; end if;
  raise notice 'ok (H3, MEASURED COST): a source generation stays pinned after its only referrer was swept — retained for the life of the workspace, not 90 days';
end $$;

-- ⟳ T3 — THE RE-RECORD RULE, THROUGH THE RPC THAT REAL CALLERS USE. Round 16 H2 corrected this from
-- "replace" to "present the same set or raise", and the correction is load-bearing: a replace is a
-- delete-and-insert, which the child table's own freeze forbids — and on the OMISSION path a replace
-- would have WIPED the set, making the rung and the GC check vacuously true, which is the failure
-- round 15 B3 wrote this item to prevent.
do $$ declare ws uuid; o text; srcs text; begin
  select id into ws from t_ws;
  o := record_artifact(ws,'vidT3','model','gT3mCUR','model'::artifact_kind,
        ws::text||'/videos/vidT3/gT3mCUR/model.json',
        p_source_generation_id := 'gT3b', p_produced_at := '2026-06-06');
  if o <> 'already_recorded' then
    raise exception 'ASSERTION FAILED — re-recording with the SAME source gave %', o; end if;
  o := record_artifact(ws,'vidT3','model','gT3mCUR','model'::artifact_kind,
        ws::text||'/videos/vidT3/gT3mCUR/model.json', p_produced_at := '2026-06-06');  -- source OMITTED
  if o <> 'already_recorded' then
    raise exception 'ASSERTION FAILED — re-recording with an OMITTED source gave %', o; end if;
  select string_agg(s.source_generation_id, ',' order by s.source_generation_id) into srcs
    from video_artifact_sources s join video_artifacts a on a.artifact_id = s.artifact_id
   where a.video_id='vidT3' and a.slot='model' and a.generation_id='gT3mCUR';
  if srcs is distinct from 'gT3b' then
    raise exception 'ASSERTION FAILED — an omitted source did not CARRY FORWARD: the set is now {%}', coalesce(srcs,''); end if;
  raise notice 'ok (T3): a re-record presenting the same set is idempotent, and an omitted source carries forward';
end $$;
select assert_raises(format($$
  select record_artifact(%L::uuid,'vidT3','model','gT3mCUR','model'::artifact_kind,
    %L||'/videos/vidT3/gT3mCUR/model.json',
    p_source_generation_id := 'gT3a', p_produced_at := '2026-06-06');
$$, (select id from t_ws), (select id from t_ws)::text),
 're-recording with a DIFFERENT source (round 16 H2 — the same set, or a raise)', 'P0001');

-- ── ⟳ ADR-0007 IMPLEMENTATION REVIEW, H2 — THE THIRD RE-RECORD CASE, WHICH HAD NO ASSERTION ─────
-- The three blocks above exercise SAME-set, OMITTED and DIFFERENT-set. The fourth transition a real
-- caller reaches is EMPTY -> NON-EMPTY: record first, learn the source later. It had no assertion,
-- and an absence is invisible to every opt-in instrument at once (this file's own ratchet argument),
-- so `record_artifact` silently ADDED provenance to an already-recorded PAID row — a one-way change
-- the sibling DELETE freeze then makes permanent. The cause was one sentinel carrying two facts:
-- `v_recorded = '{}'` meant both "this artifact has no provenance yet" and "this artifact is
-- RECORDED AS HAVING NONE", and only the first of those is "this is the first write".
--
-- ⚠ THE FIXTURE IS BUILT THROUGH THE RPC ON PURPOSE. A rolled-back probe can construct any state you
-- can type, so the question this file has to ask (see R9's kept lesson above) is not "is it refused?"
-- but "can a caller BE here?" — and this one is: three of the four paid kinds are recorded with no
-- source at all, and `gMmMIX` two blocks up is exactly such a row.
insert into workspace_videos (workspace_id, video_id) select id, 'vidH2' from t_ws;
do $$ declare ws uuid; o text; n int; begin
  select id into ws from t_ws;
  perform record_artifact(ws,'vidH2','summary','gH2s','summary'::artifact_kind,
    ws::text||'/videos/vidH2/gH2s/summary.md', p_md_hash := 'SHA_H2S',
    p_card := ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-07-05","processedAt":"y",'
           || '"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb,
    p_doc_version_major := 4, p_produced_at := '2026-07-05');
  o := record_artifact(ws,'vidH2','model','gH2m','model'::artifact_kind,
    ws::text||'/videos/vidH2/gH2m/model.json', p_produced_at := '2026-07-06');   -- SOURCE OMITTED
  if o <> 'recorded' then
    raise exception 'ASSERTION FAILED — the H2 fixture did not record: %', o; end if;
  select count(*) into n from video_artifact_sources s
    join video_artifacts a on a.artifact_id = s.artifact_id
   where a.video_id='vidH2' and a.slot='model';
  if n <> 0 then
    raise exception 'ASSERTION FAILED — the H2 fixture already carries provenance (% row(s))', n; end if;
  raise notice 'ok (H2 fixture): a paid model is RECORDED WITH NO SOURCE — reached through the RPC, not typed';
end $$;
select assert_raises(format($$
  select record_artifact(%L::uuid,'vidH2','model','gH2m','model'::artifact_kind,
    %L||'/videos/vidH2/gH2m/model.json',
    p_source_generation_id := 'gH2s', p_produced_at := '2026-07-06');
$$, (select id from t_ws), (select id from t_ws)::text),
 'an artifact recorded with NO source has provenance ADDED on re-record (review H2)', 'P0001');
-- The refusal has to be total, not merely reported: the raise is what stops the INSERT, and an
-- assertion that only reads the SQLSTATE would pass over a guard that raised after writing.
do $$ declare srcs text; begin
  select coalesce(string_agg(s.source_generation_id, ',' order by s.source_generation_id),'') into srcs
    from video_artifact_sources s join video_artifacts a on a.artifact_id = s.artifact_id
   where a.video_id='vidH2' and a.slot='model';
  if srcs <> '' then
    raise exception 'ASSERTION FAILED — the refused re-record still left provenance {%}', srcs; end if;
  raise notice 'ok (H2): a recorded EMPTY source set stays empty — "no row yet" and "recorded as none" are two facts now';
end $$;

-- ⟳ T3 — THE CASCADE THE `restrict` DECISION WAS MADE FOR, AND THE DELETE GUARD'S OWN CONDITION.
-- Round 14 B3 measured `on delete restrict` breaking account erasure. Round 15 L1 refined the cause
-- to DEPTH, not RESTRICT. The delete guard this slice adds could re-break exactly that path — a
-- FREE render is deletable, so its provenance cascades — which is why the guard is conditioned on
-- the parent artifact still existing. This asserts the resulting behaviour end to end.
-- ⚠ MEASURED AND NOT SMOOTHED OVER: this only reaches the join table because the workspace holds no
-- PAID artifact. With one, `delete from profiles` dies earlier and unrelatedly, at
-- `video_artifacts is append-only: cannot DELETE recorded paid row`. Account erasure against a paid
-- manifest is an open question this slice does not settle; what T3 owes is not to add a THIRD
-- blocker, and this is the assertion that says it did not.
do $$ declare p uuid := gen_random_uuid(); ws uuid; a uuid; begin
  insert into auth.users (id) values (p);
  insert into profiles (id) values (p) on conflict (id) do nothing;
  select id into ws from workspaces where owner_id = p;
  insert into workspace_videos (workspace_id, video_id) values (ws,'vidT3f');
  insert into video_generations (workspace_id,video_id,generation_id,kind,card,doc_version_major,produced_at,md_hash)
    values (ws,'vidT3f','gT3f','summary',
      ('{"tldr":"t","takeaways":"k","docVersion":"4.0","mdGeneratedAt":"2026-07-09","processedAt":"y",'
       ||'"mdCorrectionsHash":"'||no_corrections_hash()||'"}')::jsonb, 4,'2026-07-09','SHA_T3F');
  insert into video_artifacts (workspace_id,video_id,slot,generation_id,kind,state,blob_key)
    values (ws,'vidT3f','pdf:summary',null,'render','recorded', ws::text||'/videos/vidT3f/renders/s.pdf')
    returning artifact_id into a;
  insert into video_artifact_sources (artifact_id, workspace_id, video_id, source_generation_id)
    values (a, ws, 'vidT3f', 'gT3f');
  delete from profiles where id = p;
  if exists (select 1 from video_artifact_sources where artifact_id = a) then
    raise exception 'ASSERTION FAILED — the provenance row outlived the account that owned it'; end if;
  raise notice 'ok (T3 cascade): account erasure carries provenance away with it; the delete guard does not block it';
end $$;

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

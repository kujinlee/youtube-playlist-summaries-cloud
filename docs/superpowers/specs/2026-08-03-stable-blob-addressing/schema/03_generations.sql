-- 03 — the workspace-scoped video entity, and generations.
-- Round 4 J3-2: three columns that round-3 fixes depend on existed ONLY in prose. They are here.

-- ⟳ ROUND 6 B4 — "NO CORRECTIONS" IS ONE DEFINED VALUE, AND IT IS NOT NULL.
--
-- `01ba4719c8…` is sha256 of "\n", i.e. today it equals mdHash('') — canonicalizeMd('') returns a
-- lone newline (`content-hash.ts:9-13`). But it is DEFINED here, not DERIVED, and that distinction is
-- the whole reason item 2 could be settled before backlog #23. When corrections become {from,to}
-- pairs, an EMPTY PAIR LIST still hashes to this constant BY DEFINITION rather than to whatever
-- mdHash('[]') happens to be. Re-deriving it is the obvious future "simplification" and it would
-- silently re-open the divergence below, so: do not.
-- search_path pinned for the same reason as every other function here (see 04's `slot_kind`). This
-- body happens to be safe today — a literal and a `pg_catalog` cast — but "safe because of what the
-- body currently contains" is not a property anyone will re-check when the body changes.
create function no_corrections_hash() returns text
  language sql immutable
  set search_path = public
  as $$ select '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'::text $$;
revoke all on function no_corrections_hash() from public, anon, authenticated;

-- The canonicalization is `content-hash.ts`'s, reproduced in SQL: CRLF/CR -> LF, strip trailing
-- newlines, NFC, exactly one trailing newline. VERIFIED byte-identical to the JS on four vectors
-- (empty, plain ASCII, CRLF + repeated trailing newlines, non-ASCII 'café') 2026-08-06. Both sides
-- MUST agree or rung 1 is false for every corrected video, which is B4's failure by another route.
-- ⚠ `public.no_corrections_hash()`, QUALIFIED. MEASURED: unqualified, this function works everywhere
-- EXCEPT where it matters most. A plain SQL function inherits the CALLER's search_path, and the
-- anti-drift trigger below is `security definer set search_path = ''` — so the call resolved fine in
-- the migration and in every direct query, and failed with `function no_corrections_hash() does not
-- exist` only from inside the trigger. Found by the trigger's own assertion, not by reading: the
-- failure is invisible at every call site except one.
-- `set search_path` PINNED ON THE FUNCTION, which is what actually fixes the class rather than the
-- instance. MEASURED twice, one level apart: first `no_corrections_hash()` then `digest()` failed to
-- resolve from inside the trigger. `digest` is pgcrypto's and Supabase installs pgcrypto into the
-- `extensions` schema, NOT `public` — so every unqualified name here is a latent version of the same
-- bug, and qualifying them one at a time would have found the next one on the next run. Pinning the
-- path makes this function resolve identically no matter who calls it.
create function corrections_hash_of(p_corrections text) returns text
  language sql immutable
  set search_path = public, extensions
  as $$
  select case when coalesce(p_corrections, '') = '' then public.no_corrections_hash()
              else encode(digest(
                     normalize(regexp_replace(regexp_replace(p_corrections, E'\r\n?', E'\n', 'g'),
                                              E'\n+$', ''), NFC) || E'\n', 'sha256'), 'hex')
         end $$;
revoke all on function corrections_hash_of(text) from public, anon, authenticated;

create table workspace_videos (
  workspace_id uuid not null references workspaces(id) on delete cascade,
  video_id     text not null,
  -- fields describing the SHARED BODY live here, not on the per-playlist videos row (round 2 B3):
  corrections        text,
  -- ⟳ ROUND 6 B4 — NOT NULL, and this is a correctness fix rather than tidiness. MEASURED: the seed
  -- below left 2903 of 2904 rows NULL while 99 live videos carried real corrections, and rung 1 —
  -- the TOP rung of both view orderings — read the NULL as "this video has no corrections". So a
  -- nullable column conflated "no corrections" with "nobody ever computed this", which is shape #1
  -- (absent-vs-failed) sitting on the ranking key. The consequence was measured on the money path:
  -- cloud permanently rung-1-stale, local current, so reconcileClassA returned copyToCloud on EVERY
  -- sync, forever — verbatim the failure round 5 B3 was written to remove, one rung above it.
  -- NOT NULL makes that conflation unrepresentable rather than fixed-once.
  corrections_hash   text not null default no_corrections_hash(),
                                    -- hash of `corrections`; a generation is "corrections-current"
                                    -- when its mdCorrectionsHash equals this. RANKS, never gates.
  primary key (workspace_id, video_id)
);
alter table workspace_videos enable row level security;
alter table workspace_videos force row level security;
revoke all on workspace_videos from anon, authenticated;   -- round 6 H4; see video_artifacts
grant select, insert, update, delete on workspace_videos to service_role;
-- Round 5 B2, SECOND-ORDER: `security_invoker = true` on the views means the view runs as the READER,
-- so the reader needs SELECT on EVERY base table the view joins — and a policy on each, since both
-- carry `force row level security`. MEASURED without this: `permission denied for table
-- workspace_videos`, i.e. the security fix made the serve path unusable.
-- Neither reviewer named this; it is the fix's own cost, found by executing it. Same shape as every
-- other one-site fix this review has produced — B2 was reported at the VIEW and applies at THREE
-- tables, and the sweep is what turns a security fix into a working one.
grant select on workspace_videos to authenticated, anon;
create policy workspace_videos_owner_read on workspace_videos for select to authenticated
  using (workspace_id in (select id from workspaces where owner_id = (select auth.uid())));

-- videos gains its FK only AFTER workspace_videos is populated (round 4 J1-4).
-- ⟳ ROUND 6 B4 — THE SEED CARRIES THE CORRECTIONS. It used to be `select distinct workspace_id,
-- video_id` and nothing else, so the migration silently DROPPED 99 users' corrections into a column
-- the top ranking rung then read. `distinct on` rather than `distinct`, because corrections describe
-- the SHARED BODY (round 2 B3) while `videos` is per-playlist: the same video in two playlists is two
-- rows, and a bare `distinct` over three columns would emit BOTH and violate the primary key. Ordering
-- by "has corrections first" makes the pick deterministic and biased toward keeping content — a
-- corrected row never loses to an uncorrected duplicate.
insert into workspace_videos (workspace_id, video_id, corrections, corrections_hash)
  select distinct on (workspace_id, video_id)
         workspace_id, video_id,
         nullif(data->>'corrections', ''),
         corrections_hash_of(data->>'corrections')
    from videos
   order by workspace_id, video_id, (coalesce(data->>'corrections','') <> '') desc;
alter table videos add constraint videos_workspace_video_fk
  foreign key (workspace_id, video_id) references workspace_videos (workspace_id, video_id);

-- ⟳ ROUND 8 B3 — THE MIGRATION HAD NO PRODUCER FOR EITHER VALUE IT MADE MANDATORY, so after it ran,
-- NOTHING COULD INGEST A NEW VIDEO. MEASURED, running `claim_video_slot`'s INSERT verbatim (0023:87):
--
--   [23502] null value in column "workspace_id" of relation "videos" violates not-null constraint
--   [23503] ... and supplying it -> violates foreign key constraint "videos_workspace_video_fk"
--
-- Two independent breakages, one behind the other. The seed above populates `workspace_videos` for
-- every video that existed at migration time and nothing populates it ever again; `videos.workspace_id`
-- is NOT NULL with no default while every live writer's column list omits it (0023:87, 0009:94,
-- 0007:35). §5.0.1 calls workspace_videos "the entity the manifest keys on" and never says who
-- inserts a row into it.
--
-- ⚠ WHY A TRIGGER RATHER THAN MAKING EVERY WRITER SUPPLY IT (user decision, 2026-08-08). The
-- explicit option is tempting — NOT NULL fails loudly, so a forgetful writer breaks in dev, not in
-- production. It was rejected because **`videos.workspace_id` is a pure function of `playlist_id`**:
-- `videos.playlist_id` is NOT NULL and `playlists.workspace_id` is NOT NULL (01), so the value is
-- always derivable and never ambiguous. A caller supplying it cannot add information — it can only
-- agree, or DISAGREE. That is not explicitness, it is a DRIFT CHANNEL, and it is the third
-- denormalized copy this project would be maintaining by hand after being bitten by the other two
-- (this file's own corrections_hash, and the serial-coherence slice, PR #42).
--
-- ⚠ AND A DISAGREEMENT RAISES rather than being silently corrected. This is what the explicit option
-- was actually worth: a caller with a WRONG opinion about tenancy is a real bug and must be loud.
-- Silently overwriting it would be shape #5 (silent repair on a path where the caller was wrong) on
-- the tenancy boundary. A caller supplying the RIGHT value passes unremarked.
--
-- ⚠ APPLIED TO `jobs` IN THE SAME BREATH. `jobs.workspace_id` (01:46-48) is the identical defect —
-- NOT NULL, no default, and every enqueue RPC's column list omits it (0008:54, 0009:26, 0011:83,
-- 0018:32). Fixing only `videos` would be shape #10 (a fix applied at one site with an identical
-- sibling nearby) for the EIGHTH time, self-inflicted, in the round that recorded the seventh.
-- ⚠ AND IT IS A CHAIN, FOUR LEVELS DEEP — found by the probe for the two sites above failing on the
-- THIRD. `01` seeds `workspaces` from `profiles`, then backfills `playlists`, `videos` and `jobs`,
-- and EVERY ONE of those is a one-shot statement with no producer for the next row:
--
--   profiles -> workspaces   seeded once from profiles; a NEW user gets no workspace
--   workspaces -> playlists  backfilled once; a NEW playlist cannot derive one  [23502]
--   playlists -> videos      backfilled once; measured above                    [23502]/[23503]
--   playlists -> jobs        backfilled once; every enqueue RPC omits it
--
-- Fixing `videos` and `jobs` alone would have been shape #10 committed INSIDE the fix for shape #10:
-- a new user could not create a playlist, so the repaired video path was unreachable anyway. Each
-- level derives from the one above, so each gets the same treatment rather than a special case.
create function ensure_workspace_for_profile() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  -- The SAME rule as 01's seed (`select id, id from profiles`), in the one place that runs for rows
  -- the seed could not see. When the "one workspace per user" rule expires, both change together —
  -- the seed is dead code by then and this is the only live writer.
  insert into public.workspaces (id, owner_id) values (new.id, new.id)
  on conflict (owner_id) do nothing;
  return new;
end $$;
revoke all on function ensure_workspace_for_profile() from public, anon, authenticated;
create trigger profiles_ensure_workspace_trg
  after insert on profiles
  for each row execute function ensure_workspace_for_profile();

create function resolve_workspace_from_playlist() returns trigger
  language plpgsql security definer set search_path = '' as $$
declare v_ws uuid;
begin
  if tg_table_name = 'playlists' then
    -- One level up: a playlist derives its workspace from its OWNER, exactly as 01's backfill did.
    select w.id into v_ws from public.workspaces w where w.owner_id = new.owner_id;
    if v_ws is null then
      raise exception 'playlists: owner % has no workspace — cannot derive workspace_id',
        new.owner_id;
    end if;
  else
    select p.workspace_id into v_ws from public.playlists p where p.id = new.playlist_id;
    if v_ws is null then
      raise exception '%: playlist % has no workspace — cannot derive workspace_id',
        tg_table_name, new.playlist_id;
    end if;
  end if;
  if new.workspace_id is not null and new.workspace_id <> v_ws then
    raise exception '%: workspace_id % disagrees with playlist %, which belongs to workspace %',
      tg_table_name, new.workspace_id, new.playlist_id, v_ws;
  end if;
  new.workspace_id := v_ws;
  -- The manifest parent, created for the rows the seed could not know about. `do nothing`, because
  -- a video in two playlists is two `videos` rows and ONE shared body (round 2 B3) — the second
  -- insert must not clobber the first's corrections.
  if tg_table_name = 'videos' then
    insert into public.workspace_videos (workspace_id, video_id, corrections, corrections_hash)
    values (v_ws, new.video_id, nullif(new.data->>'corrections', ''),
            public.corrections_hash_of(new.data->>'corrections'))
    on conflict (workspace_id, video_id) do nothing;
  end if;
  return new;
end $$;
revoke all on function resolve_workspace_from_playlist() from public, anon, authenticated;

-- BEFORE, not AFTER: it must set NEW.workspace_id before NOT NULL is checked, and create the parent
-- before the FK is. Split INSERT/UPDATE for the same physical reason documented below — a WHEN clause
-- may reference only OLD/NEW, so `tg_op` cannot appear in one.
-- The UPDATE half is scoped to the two columns that can invalidate the derivation, so ordinary video
-- writes (every summarize, every annotation) cost nothing. `playlist_id` covers relocation;
-- `workspace_id` covers anyone writing the copy directly, which is the drift this exists to prevent.
create trigger playlists_resolve_workspace_ins_trg
  before insert on playlists
  for each row execute function resolve_workspace_from_playlist();
create trigger playlists_resolve_workspace_upd_trg
  before update of owner_id, workspace_id on playlists
  for each row execute function resolve_workspace_from_playlist();
create trigger videos_resolve_workspace_ins_trg
  before insert on videos
  for each row execute function resolve_workspace_from_playlist();
create trigger videos_resolve_workspace_upd_trg
  before update of playlist_id, workspace_id on videos
  for each row execute function resolve_workspace_from_playlist();
create trigger jobs_resolve_workspace_ins_trg
  before insert on jobs
  for each row execute function resolve_workspace_from_playlist();
create trigger jobs_resolve_workspace_upd_trg
  before update of playlist_id, workspace_id on jobs
  for each row execute function resolve_workspace_from_playlist();

-- ⟳ ROUND 6 B4, THE HALF THE FINDING DID NOT ASK FOR — DRIFT IS PREVENTED, NOT REPAIRED.
-- `workspace_videos.corrections_hash` is a DENORMALIZED COPY; the truth lives in `videos.data`.
-- Backfilling it fixes the 2903 rows that are wrong TODAY and says nothing about the next write.
-- B4 offered a choice — "route update_video_annotations at workspace_videos, or keep the two in sync
-- by trigger". The trigger, because a routing rule holds only until someone adds a second writer and
-- there is ALREADY more than one (`update_video_annotations` in 0021, and `persist_summary`'s layer-2
-- merge). A rule that depends on every future caller remembering is the shape this whole review keeps
-- finding; the same argument as `art_detached_is_dig` being a CHECK and not only a trigger rule.
--
-- Fires only when the corrections TEXT actually changes, so ordinary video updates cost nothing.
create function sync_corrections_to_workspace_video() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  update public.workspace_videos
     set corrections      = nullif(new.data->>'corrections', ''),
         corrections_hash = public.corrections_hash_of(new.data->>'corrections')
   where workspace_id = new.workspace_id and video_id = new.video_id;
  return new;
end $$;
revoke all on function sync_corrections_to_workspace_video() from public, anon, authenticated;
-- TWO triggers, not one with `when (tg_op = 'INSERT' or …)`. MEASURED: `column "tg_op" does not
-- exist` — a WHEN clause may reference only OLD/NEW, and OLD does not exist for INSERT at all, so the
-- combined form cannot be written. The UPDATE half keeps its guard so ordinary video writes (every
-- summarize, every annotation) cost nothing.
-- ⟳ ROUND 9 — THE INSERT HALF IS GUARDED TOO, and this was a live defect the moment B3 was fixed.
-- MEASURED: video with corrections 'KEEP ME' in playlist A, then the SAME video added to playlist B
-- with a row carrying none -> `after playlist B insert: corrections = <null>  -> CLOBBERED`.
-- `corrections` describes the SHARED BODY (round 2 B3) while `videos` is per-playlist, so the second
-- playlist's row is not evidence that the corrections were removed — it is a row that never had them.
--
-- Latent until now ONLY because ingest was impossible (B3): no INSERT could reach this trigger at
-- all. Fixing ingest made a dormant defect live, which is shape #9 — and it was found by probing the
-- fix's own blast radius rather than by a reviewer.
--
-- The rule is the seed's, restated: the seed picks `(has corrections) desc` precisely so "a corrected
-- row never loses to an uncorrected duplicate". The trigger now obeys the same bias.
create trigger videos_corrections_sync_ins_trg
  after insert on videos
  for each row
  when (coalesce(new.data->>'corrections','') <> '')
  execute function sync_corrections_to_workspace_video();
create trigger videos_corrections_sync_upd_trg
  after update of data on videos
  for each row
  when (coalesce(old.data->>'corrections','') is distinct from coalesce(new.data->>'corrections',''))
  execute function sync_corrections_to_workspace_video();

create type artifact_kind as enum ('summary','model','dig','digDeeper','render');

create table video_generations (
  workspace_id      uuid not null,
  video_id          text not null,
  generation_id     text not null,
  kind              artifact_kind not null,
  -- ⟳ ROUND 6 B5 / Codex B3 — A GENERATION HAS A LIFECYCLE TOO.
  -- MEASURED: a cloud summarize could not RESERVE its summary slot. Reserving with no generation row
  -- raised [23503] on the artifact's FK; creating the generation row from what is knowable BEFORE the
  -- Gemini call raised [23514] gen_card_complete. The paid call sits between those two, so both doors
  -- were locked and the primary kind of the round-6 reservation protocol was unreachable.
  --
  -- The premise that failed was "a generation row is only ever complete" — true while the manifest
  -- held one row per slot and the generation was written once, after the fact. Rounds 5-6 gave the
  -- ARTIFACT a lifecycle and a protocol that must insert a `pending` row BEFORE the content exists,
  -- and never gave its FK PARENT the matching one. The honest rule is narrower than the old one:
  --   A GENERATION MUST BE COMPLETE WHEN SOMETHING RECORDED POINTS AT IT — not from the moment it
  --   exists. `video_artifacts_generation_complete` (04) is what enforces the second half, and it is
  --   what makes gating the four CHECKs below safe rather than merely convenient.
  --
  -- ⚠ THE DEFAULT IS `complete`, AND THAT IS A SAFETY ARGUMENT, NOT A COMPATIBILITY ONE. A producer
  -- that never heard of this column keeps TODAY's behaviour exactly: its incomplete row is still
  -- rejected by gen_card_complete. Defaulting to `pending` would have made every completeness CHECK
  -- below optional for anyone who simply omitted the column — a fail-open default in the constraints
  -- that round 4's J1-2 fixed for being fail-open. The relaxation is strictly opt-in, and the only
  -- caller that opts in is reserve_artifact_slot.
  state             text not null default 'complete'
                    check (state in ('pending','complete')),
  -- ⟳ ROUND 7 H2 — WHO RESERVED THIS GENERATION. The generation UPDATE inside record_artifact was
  -- fenced on NOTHING — no token, no state, no slot — while every other write in this design is
  -- fenced. MEASURED: W2 named W1's generation, completed it with W2's production time, and W1 was
  -- then locked out of its own paid work FOREVER by the freeze trigger below
  -- ("the CONTENT of complete generation gW1 is immutable"). That is item 3's freeze silently
  -- revoking item 4's user decision that a writer which already paid always records.
  --
  -- The token is the RESERVER's, captured at reserve time and never rotated by a later reclaim —
  -- which is what makes it survive P22: a writer whose SLOT was reclaimed still holds the token that
  -- reserved its own generation, so it can still complete it and record. Fencing on the artifact row
  -- instead would have broken exactly that case.
  reserved_by       uuid,
  -- ⟳ ROUND 11 (round 10 B1/H1) — THERE IS NO SECOND CREDENTIAL, AND REMOVING IT IS THE FIX.
  --
  -- Round 9 added `reserved_by_worker` / `reserved_by_job` here so a restarted worker could prove
  -- ownership after losing its token. Round 10 measured that failing in BOTH directions, again:
  --
  --   REPLAYABLE — both columns live in the row being fenced, and `video_generations` grants
  --     `select` to `service_role`, the same role that may call `record_artifact`. So an attacker
  --     READS the credential and completes the victim's generation. Measured:
  --       ATTACKER reads: worker=worker-VICTIM job=1ab8a512-…  ->  recorded_after_token_loss
  --       md_hash now SHA_ATTACKER, while the victim paid for SHA_REAL
  --   AND STILL UNUSABLE — the premise was false. `worker/main.ts:69` is
  --       `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}`
  --     a fresh uuid and pid minted at PROCESS START, exactly as volatile as the token it replaced;
  --     and `sweep_expired_leases` nulls `locked_by`/`lease_token` and moves the job off `active`,
  --     so "find my job by locked_by = me and status = active" returns nothing precisely when
  --     recovery is needed.
  --
  -- ⚠ AND THE REQUIREMENT ITSELF WAS NOT REAL — which is why the answer is deletion, not a third
  -- credential. The party that holds paid bytes ALWAYS still holds its token:
  --   * a process that crashed lost the Gemini result from memory too, so it has nothing to record;
  --   * a worker that loses its lease STOPS — `lib/job-queue/worker-runner.ts` heartbeats every
  --     third of a lease and calls `leaseLost.abort()`, composed into the handler's AbortSignal;
  --   * and there are NO callers yet: `reserve_artifact_slot` / `record_artifact` / `generation_id`
  --     appear nowhere under `worker/`, `lib/job-queue/` or `lib/cloud-sync/`.
  -- Rounds 7 and 9 each built a fallback for a caller that cannot occur, and each fallback was the
  -- round's worst finding. The token alone is unguessable, is held by exactly the party with the
  -- bytes, and is stored nowhere a caller reads it as a credential.
  --
  -- ⚠ THE CONDITION IS NOW A RULE ABOUT CALLERS, and it belongs in the spec (§ "the caller's
  -- obligation"): a worker MUST hold its reservation token for the life of the job, and a worker
  -- that cannot MUST abandon rather than record. `worker-runner` already behaves this way; when the
  -- cloud caller is written, assert it there.
  --
  -- ⚠ HOW THIS ERROR HAPPENED, because the lesson outlived the code: "worker_id is stable config"
  -- was written into this file as a fact and was never read from `worker/main.ts`. Every instrument
  -- this spec owns points at the SCHEMA, and the false premise was about code outside it. The rule
  -- that would have caught it: QUOTE THE CODE YOU RELY ON, DO NOT CHARACTERISE IT — quoting forces
  -- a read, characterising lets you write from memory.
  card              jsonb,
  doc_version_major int,             -- rule 13's format rung. Round 4 J3-2: ranked on, never defined.
  -- NULLABLE while pending — nothing has been produced yet, and a `not null` here is what forced a
  -- reserving writer to invent a production time. Required again at completion
  -- (gen_complete_has_produced_at), so no ranked row can carry a NULL on the bottom rung.
  produced_at       timestamptz,              -- PRODUCTION time, carried as DATA across replicas —
                                            -- not now(), which is clock-derived (round 4 J2-3).
  body_collected    boolean not null default false,  -- round 1 H7's lifecycle marker.
  -- Round 5 B3: sync's ClassASignals.mdHash had NO cloud source. The spec says so twice in its own
  -- other sections ("grep for mdHash across all 23 migrations returns ZERO"; "needs a persisted hash
  -- of the body, and none exists") while §5.3 asserted reconcileClassA "runs unmodified". It cannot:
  -- reconcile-class-a.ts:17-18 reads mdHash as PRESENCE and :32 as EQUALITY, so projecting it null
  -- makes :23 return copyToCloud unconditionally — every sync appends a new generation, forever, and
  -- every append is a paid slot. Deriving it by READING the blob instead reintroduces shape #1 on the
  -- money path. So it becomes a recorded fact, which is what "runs unmodified" always required.
  md_hash           text,
  created_at        timestamptz not null default now(),
  primary key (workspace_id, video_id, generation_id),
  unique (workspace_id, video_id, generation_id, kind),   -- FK target for video_artifacts (round 2 C2)
  foreign key (workspace_id, video_id)
    references workspace_videos (workspace_id, video_id) on delete cascade,
  -- Card completeness, kind-conditional.
  --
  -- Round 4 J1-2 hardened this against `card = NULL` (SQL null). Round 5 B1 MEASURED that it was
  -- still open one level down: `?&` tests key EXISTENCE, so `{"tldr":null, …}` passed. That is not
  -- merely "an incomplete card is accepted" — the empty card WON THE RANKING and became the served
  -- summary, because `card->>'x'` on a JSON null yields SQL NULL, and rung 1
  -- (`… is not distinct from wv.corrections_hash`) is TRUE when both sides are NULL, which is the
  -- common case (a video with no corrections). An all-null card beat a real doc_version_major=4
  -- generation AND a doc_version_major=99 one. Paid content, unreachable behind an empty row.
  --
  -- Live hazard, not hypothetical: sync-run.ts:534-542 constructs exactly
  -- `{docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null}` and calls it
  -- "an HONEST unresolved placeholder". §5.3 records a local win AS A CARD. It can no longer.
  --
  -- ⟳ ROUND 6 B4 — THE ASYMMETRY IS GONE; `mdCorrectionsHash` IS NOW A REQUIRED VALUE TOO.
  -- Round 5's cross-derivation C2 weakened this deliberately, arguing "a null there is the correct,
  -- meaningful answer for a video with no corrections, and requiring it non-null would make rung 1
  -- false for every uncorrected video." Both halves were wrong, and checking the PRODUCERS rather
  -- than reasoning about the value is what showed it:
  --   * NO PRODUCER HAS EVER EMITTED NULL. `pipeline.ts:272` stamps mdHash('') and
  --     `sync-run.ts:651` computes mdHash(String(… ?? '')) — both a real 64-hex string. The schema
  --     was permitting a value the code does not write, and paying for it with an ambiguity.
  --   * rung 1 is not made false by requiring a value; it is made TRUE, because the uncorrected side
  --     now also carries the constant instead of NULL. The old pairing (card 'mdHash('')' vs column
  --     NULL) is exactly what MEASURED as corrections-current = FALSE for the entire corpus.
  -- Kept as key-presence AND value, since `?&` alone was what let round 5's B1 all-null card win.
  -- ⟳ ROUND 6 B5 — `state <> 'complete' or …` on all four. The constraints did NOT weaken; each moved
  -- to the moment its value can exist. What keeps that from being a bypass is the artifact-side
  -- trigger in 04: nothing may be RECORDED against a generation that is still pending, so every row
  -- either ranking view can ever see has satisfied all four in full.
  constraint gen_complete_has_produced_at check (state <> 'complete' or produced_at is not null),
  constraint gen_card_complete check (
    state <> 'complete' or kind <> 'summary' or (
      card is not null
      and card ?& array['tldr','takeaways','docVersion','mdGeneratedAt','processedAt',
                        'mdCorrectionsHash']
      -- Spelled out rather than `bool_and(...) from unnest(...)`: MEASURED — Postgres rejects that
      -- with `cannot use subquery in check constraint`. A new PHYSICAL rule, and the reviewer's
      -- proposed fix was the thing that did not execute. Add it to the sweep list.
      and card ->> 'tldr'          is not null
      and card ->> 'takeaways'     is not null
      and card ->> 'docVersion'    is not null
      and card ->> 'mdGeneratedAt' is not null
      and card ->> 'processedAt'   is not null
      and card ->> 'mdCorrectionsHash' is not null)),   -- ⟳ round 6 B4; see the note above
  constraint gen_summary_has_format check
    (state <> 'complete' or kind <> 'summary' or doc_version_major is not null),
  constraint gen_summary_has_hash check
    (state <> 'complete' or kind <> 'summary' or md_hash is not null),
  -- Round 5 H5: the ranking trusts `doc_version_major`, and nothing tied it to the `docVersion` the
  -- body actually carries. MEASURED: a card saying "3.3" with the column saying 99 inserted cleanly.
  -- That is §5.2's card/body lie relocated into the ranking key — the one place it does most damage,
  -- since the format rung is the rung that must never regress.
  constraint gen_major_matches_card check (
    state <> 'complete'
    or kind <> 'summary'
    or doc_version_major = split_part(card ->> 'docVersion', '.', 1)::int)
);

-- ⟳ ROUND 6 B5 — COMPLETE IS TERMINAL, AND THE CONTENT FREEZES WITH IT.
-- Without this the artifact's frozen ADDRESS would point at re-writable CONTENT: `video_artifacts`
-- forbids rewriting blob_key on a recorded paid row, and the bytes that key names are described here.
-- Rewriting `md_hash` or `doc_version_major` in place is shape #3 relocated one table up — a mutable
-- value inside an address — and `doc_version_major` is the format rung, the one rung rule 13 says must
-- never regress. New content means a NEW generation; that is what append-only means at this level.
--
-- `body_collected` is deliberately NOT frozen: it is §8's lifecycle marker, the one thing about a
-- finished generation that is supposed to change. Freezing it would break GC, which is the same class
-- of error as the first version of the artifact trigger forbidding §6.2's detach.
--
-- An UPDATE that re-states the SAME values passes untouched, and that is load-bearing rather than
-- incidental: record_artifact completes the generation unconditionally, so the crash-retry path
-- (`already_recorded`) re-completes an already-complete row with identical content. Re-completing
-- with DIFFERENT content raises, which is the honest answer — it is a caller claiming the bytes
-- changed under an address that cannot.
-- ⟳ ROUND 7 B2 / M5 — AND IT NOW ALSO BOUNDS `produced_at` TO THE PAST, on INSERT as well as UPDATE.
-- `produced_at` is a RANKING RUNG (04's two view orderings) and a CALLER-SUPPLIED value —
-- `record_artifact` takes it as a parameter precisely so sync can carry a remote clock's. Nothing
-- bounded it, so ONE sync from a replica with a fast clock outranks everything real until the clock
-- catches up. Round 4's J2-3 removed clock READS from the ranking; it did not stop a clock VALUE
-- being injected into it.
--
-- It also made §6.2's detach UNSATISFIABLE. MEASURED: a dig whose generation carried a future
-- produced_at could never be detached — the sibling trigger sets detached_at to now(), the bound
-- compares it against produced_at, and the error blamed the writer for a value it never supplied:
--   [P0001] detached_at 2026-08-08… precedes generation gFUT produced_at 2026-08-18…
-- Permanently, since produced_at is frozen below and detached_at is trigger-owned. Not exotic: this
-- spec's OWN fixture `gC_STALE` carried a produced_at a month ahead, in a passing test.
--
-- ⚠ A CHECK CANNOT DO THIS — `now()` is not immutable, so it is illegal in a CHECK constraint just as
-- it is in an index predicate (the same physical rule that pushed the lease-expiry test out of
-- video_artifacts_inflight_uq and into the RPC). A trigger is the only place it can live.
create function video_generations_freeze() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  -- ⟳ ROUND 9 H4 — WITH A SKEW TOLERANCE, because the bound was zero-width against a TRANSACTION
  -- timestamp. `now()` is `transaction_timestamp()`, so any value stamped after the transaction
  -- opened is already "the future": MEASURED 0.63s into a transaction, `clock_timestamp()` was
  -- rejected. The realistic trigger is not a long transaction but APP-VS-DATABASE CLOCK SKEW — the
  -- worker runs on Fly, Postgres on Supabase, and `produced_at` is stamped in application code, so a
  -- few hundred milliseconds of NTP drift turned a successful summarize into a raw exception AFTER
  -- the paid Gemini call. Shape #8 on the money path, failing closed in the wrong direction.
  --
  -- Five minutes preserves round 7 B2's intent completely: that finding was a value YEARS in the
  -- future winning the ranking permanently. A tolerance wide enough for clock drift is nowhere near
  -- wide enough to matter to a ranking ordered by production time.
  if new.produced_at is not null and new.produced_at > now() + interval '5 minutes' then
    raise exception 'video_generations: produced_at % is in the FUTURE — a clock value may not enter the ranking',
      new.produced_at;
  end if;
  -- OLD does not exist on INSERT, so the freeze half must be guarded by tg_op rather than by
  -- old.state. Same physical rule that forced 03's corrections sync into TWO triggers.
  if tg_op = 'UPDATE' and old.state = 'complete' then
    if new.state <> 'complete' then
      raise exception 'video_generations: % is COMPLETE and cannot return to %',
        old.generation_id, new.state;
    end if;
    if new.card              is distinct from old.card
       or new.md_hash           is distinct from old.md_hash
       or new.doc_version_major is distinct from old.doc_version_major
       or new.produced_at       is distinct from old.produced_at
       or new.kind              is distinct from old.kind
       or new.generation_id     is distinct from old.generation_id then
      raise exception 'video_generations: the CONTENT of complete generation % is immutable',
        old.generation_id;
    end if;
  end if;
  return new;
end $$;
revoke all on function video_generations_freeze() from public, anon, authenticated;
-- Fires AFTER forbid_collecting_current_trg (04): triggers run in name order, `f` < `v`, and both
-- return NEW unchanged, so neither depends on the other's result.
-- ⟳ ROUND 7 — `before INSERT or update`. The produced_at bound above is worthless on UPDATE alone:
-- a direct INSERT is how sync creates a generation, and it is the path the bound exists for.
create trigger video_generations_freeze_trg
  before insert or update on video_generations
  for each row execute function video_generations_freeze();
alter table video_generations enable row level security;
alter table video_generations force row level security;
revoke all on video_generations from anon, authenticated;  -- round 6 H4; see video_artifacts
grant select, insert, update, delete on video_generations to service_role;
grant select on video_generations to authenticated, anon;   -- see workspace_videos above (round 5 B2)
create policy video_generations_owner_read on video_generations for select to authenticated
  using (workspace_id in (select id from workspaces where owner_id = (select auth.uid())));

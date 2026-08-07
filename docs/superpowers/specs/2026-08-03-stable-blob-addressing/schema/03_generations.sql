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
create function no_corrections_hash() returns text
  language sql immutable as $$ select '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'::text $$;
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
create trigger videos_corrections_sync_ins_trg
  after insert on videos
  for each row execute function sync_corrections_to_workspace_video();
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
  card              jsonb,
  doc_version_major int,             -- rule 13's format rung. Round 4 J3-2: ranked on, never defined.
  produced_at       timestamptz not null,   -- PRODUCTION time, carried as DATA across replicas —
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
  constraint gen_card_complete check (
    kind <> 'summary' or (
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
  constraint gen_summary_has_format check (kind <> 'summary' or doc_version_major is not null),
  constraint gen_summary_has_hash check (kind <> 'summary' or md_hash is not null),
  -- Round 5 H5: the ranking trusts `doc_version_major`, and nothing tied it to the `docVersion` the
  -- body actually carries. MEASURED: a card saying "3.3" with the column saying 99 inserted cleanly.
  -- That is §5.2's card/body lie relocated into the ranking key — the one place it does most damage,
  -- since the format rung is the rung that must never regress.
  constraint gen_major_matches_card check (
    kind <> 'summary'
    or doc_version_major = split_part(card ->> 'docVersion', '.', 1)::int)
);
alter table video_generations enable row level security;
alter table video_generations force row level security;
revoke all on video_generations from anon, authenticated;  -- round 6 H4; see video_artifacts
grant select, insert, update, delete on video_generations to service_role;
grant select on video_generations to authenticated, anon;   -- see workspace_videos above (round 5 B2)
create policy video_generations_owner_read on video_generations for select to authenticated
  using (workspace_id in (select id from workspaces where owner_id = (select auth.uid())));

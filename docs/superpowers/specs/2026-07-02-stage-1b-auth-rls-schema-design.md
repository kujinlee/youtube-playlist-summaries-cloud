# Stage 1B — Auth + RLS Schema Design Spec

**Date:** 2026-07-02
**Repo:** `youtube-playlist-summaries-cloud` (the cloud POC fork)
**Status:** Draft v3 — hardened after two Codex passes (`…-codex.md`, `…-codex-rereview.md`). Awaiting user review.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §7/§7.1/§7.2.

**Decisions (parent + this session):**
- Supabase Auth: **Google OAuth + anonymous auth**; sessions via `@supabase/ssr`.
- Isolation: **forced RLS**, `owner_id = auth.uid()`; `service_role` confined to trusted server code (never user-facing).
- Data shape: **JSONB-per-video**; the cloud `MetadataStore` maps rows ↔ `Video`/`PlaylistIndex`.
- Dev/test: **Supabase CLI local stack (Docker)**.
- **`playlist_key` = the YouTube playlist list-id** (from `list=`); **anon→registered upgrade out of scope**; **plain SQL migrations**.

---

## 1. Goal & scope

Establish auth + the **owned, RLS-isolated core schema** backing the cloud `MetadataStore`, and prove tenant isolation with tests on a local Supabase stack — **before any adapter write exists**.

**In scope (1B):** Supabase app wiring; local stack; core schema `profiles`/`playlists`/`videos` (JSONB) with `owner_id` + forced RLS + policies + the cross-owner integrity FK; auth (Google + anonymous) with a DB provisioning trigger; the reusable RLS convention; RLS isolation + integrity tests.

**Stage-ordering correction (Codex B4):** the parent's "1C = SupabaseAdapter *bundle*" is **decomposed into per-contract stages** (matching the sibling-contracts plan). **1C = `SupabaseMetadataStore` only.** `artifacts` (BlobStore), `jobs` (queue/1E), `usage_counters` (cost/1D), `share_tokens` (share) are each created in the stage that uses them, **each following 1B's RLS convention** (§5.4). 1B fully establishes that convention so no later stage reopens ownership/RLS design.

**Prerequisite for 1C, NOT 1B (Codex re-review, new):** the `MetadataStore` contract is currently **synchronous** (`readIndex(principal): PlaylistIndex`), which suited the local `fs.readFileSync` store but a **networked Supabase adapter cannot honor**. Before 1C, a dedicated task must **async-ify the seam**: `MetadataStore` methods return `Promise`, `LocalFsMetadataStore` wraps its sync calls, and the ~20 consumers `await`. This does not block 1B (schema + auth), but §5.5's semantics below describe the *async* adapter behavior. Flagged here so 1C is not attempted on a sync interface.

**Not in 1B:** `SupabaseMetadataStore` (1C); the other tables (their stages); blob storage-key implementation (BlobStore); local-corpus data migration.

---

## 2. Prerequisites

- **Supabase CLI** (not installed) — install (`brew install supabase/tap/supabase` or `npx supabase`), version pinned in the plan.
- **Docker** (installed 27.5.1) — **daemon must be running** for `supabase start`.
- **Hosted Supabase project** — NOT needed for 1B (local only); user creates it at deploy time.

---

## 3. Supabase app wiring

Add `@supabase/supabase-js` + `@supabase/ssr`. Client factories:
- `lib/supabase/client.ts` — browser (`createBrowserClient`, anon key).
- `lib/supabase/server.ts` — server (`createServerClient`) bound to Next cookies; **RLS-scoped** to the request's session; never service_role.
- `lib/supabase/service.ts` — **service_role** client. Server-only module: first line `import 'server-only'` (build fails if it reaches a client bundle) + a **runtime guard** that throws if `typeof window !== 'undefined'` or the service key env is absent; unused in 1B.

Env from `supabase start`: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (server-only, never `NEXT_PUBLIC_`). Startup validation fails fast if missing.

### 3.1 service_role trust boundary (Codex H1/H2 + re-review)
`FORCE RLS` only makes the *table owner* obey RLS — it does **not** stop `service_role`, which has `BYPASSRLS`. Confinement is a code-boundary problem; a single "no direct import" grep is insufficient (re-exports, wrappers, dynamic/transitive imports bypass it). Enforce **defense-in-depth**:
- The service key exists only in `SUPABASE_SERVICE_ROLE_KEY` (never `NEXT_PUBLIC_`), read only inside `lib/supabase/service.ts`.
- `service.ts` begins with `import 'server-only'` → the build **fails** if it is ever pulled into a client bundle (covers transitive/wrapper paths into client code).
- A **runtime guard** in `service.ts` throws if `window` is defined or the key is missing.
- A **CI import-graph scan** (not just direct-import grep): walk the transitive import graph of every `app/**` route/server-component entry and fail if `lib/supabase/service.ts` is reachable. In 1B nothing imports it; the scan locks that in.
- User-facing reads/writes always use `server.ts`/`client.ts` (RLS-scoped). This is layered enforcement, not a single check.

---

## 4. Auth

- **Providers:** Google OAuth + Supabase **anonymous** sign-in (guest "taste"). Anonymous users get a real `auth.users` row → real `uid` → RLS-scoped identically.
- **Provisioning (Codex B2 + re-review) — single authoritative path:** a Postgres trigger `handle_new_user` `after insert on auth.users` inserts the matching `profiles` row. It **must be `SECURITY DEFINER`**, owned by a role privileged over `profiles`, with `set search_path = ''` (so the insert bypasses `profiles` RLS during signup — an ordinary-privilege trigger would be blocked by RLS and abort the signup transaction). `is_anonymous` is read from `new.is_anonymous` (Supabase sets this column on anonymous sign-ups). Because it runs in the same transaction as the `auth.users` insert, a `profiles` row **always exists before any app write** — no app-side upsert, no race. Failure semantics: a trigger exception aborts signup (fail-closed); tests cover **both** Google and anonymous sign-up producing exactly one `profiles` row.

```sql
create function handle_new_user() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, is_anonymous)
  values (new.id, coalesce(new.is_anonymous, false));
  return new;
end $$;
create trigger on_auth_user_created
  after insert on auth.users for each row execute function handle_new_user();
```
- **Session:** `@supabase/ssr` cookie sessions; `middleware.ts` refreshes the session on each request.
- **Route categories (Codex M2):**
  - *Public* (no session needed): marketing/landing.
  - *Anon-allowed* (auto-provision an anonymous session on first use): the guest "try it" path.
  - *Authenticated* (Google session required): durable library actions.
  Middleware refreshes cookies and redirects unauthenticated access to authenticated routes. The OAuth **callback route** exchanges the code for a session and sets cookies; server components and route handlers read the same refreshed session via `server.ts`.
- **Anonymous lifecycle (Codex M1):** 1B does **not** build anon→registered upgrade or cleanup. Unbounded anonymous rows are a **tracked pre-public gate**: a retention/TTL cleanup job (expire anonymous `profiles` + cascaded data after N hours) must exist before public launch. Recorded as an explicit acceptance gap, not silently ignored.

---

## 5. Core schema (JSONB-per-video) + RLS

Plain SQL migrations under `supabase/migrations/`. Every owned table: `enable` **and** `force` row level security.

### 5.1 Tables
```sql
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  is_anonymous boolean not null default false,
  created_at timestamptz not null default now()
);

create table playlists (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references profiles(id) on delete cascade,
  playlist_key text not null,          -- YouTube list-id; Principal.outputFolder maps here
  playlist_url text not null,
  playlist_title text,
  created_at timestamptz not null default now(),
  unique (owner_id, playlist_key),
  unique (id, owner_id)                -- enables the composite FK below
);

create table videos (
  playlist_id uuid not null,
  owner_id    uuid not null,
  video_id    text not null,           -- Video.id
  position    int  not null,           -- array order in PlaylistIndex.videos
  data        jsonb not null,          -- the whole Video object, verbatim
  updated_at  timestamptz not null default now(),
  primary key (playlist_id, video_id),
  -- Codex B1: a video's owner MUST equal its playlist's owner
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade,
  -- Codex H3 re-review: relational id == JSONB id AND id must be present
  -- (a missing data.id yields NULL, and `NULL = video_id` is UNKNOWN → CHECK
  --  would pass; the IS NOT NULL guard forces rejection).
  check (data->>'id' is not null and data->>'id' = video_id),
  -- Codex H2 re-review: DEFERRABLE so writeIndex reordering can transiently
  -- duplicate a position within the transaction and settle valid at COMMIT.
  -- Must be a CONSTRAINT (deferrable), not a unique INDEX.
  constraint videos_playlist_position_uniq unique (playlist_id, position)
    deferrable initially deferred
);
create index on videos (owner_id);
```

### 5.2 RLS policies
```sql
create policy profiles_self  on profiles  for all
  using (id = auth.uid())        with check (id = auth.uid());
create policy playlists_owner on playlists for all
  using (owner_id = auth.uid())  with check (owner_id = auth.uid());
create policy videos_owner    on videos    for all
  using (owner_id = auth.uid())  with check (owner_id = auth.uid());
```
The composite FK (§5.1) closes the B1 gap: even though the `videos` policy checks only `owner_id`, a row can only reference a `playlist` with the **same** `owner_id`, so an attacker cannot attach a video to a victim's playlist.

### 5.3 `is_anonymous` integrity (Codex L1)
`is_anonymous` is set once by `handle_new_user`. A `BEFORE UPDATE` trigger raises if a client attempts to change it; app logic never trusts a client-supplied value.

### 5.4 Reusable RLS convention (for later tables)
Owner column `owner_id uuid references profiles(id)`; `enable` + **`force`** RLS; one `for all` policy `owner_id = auth.uid()` (using + with check); any child table that references an owned parent uses a **composite FK carrying `owner_id`** (per B1); writes needing bypass go only through the worker's `service_role` client with `owner_id` set explicitly; share-token reads via a `security definer` function.

### 5.5 Principal ↔ schema mapping + method semantics (Codex B3/H3/H4)
`Principal.outputFolder` is redefined as **"the index selector"** — local: a filesystem path; cloud: the `playlist_key`. (The `principal.ts` JSDoc is updated accordingly — a small code touch in 1B.) `principal.id` = the authenticated/anonymous `uid`.

The cloud `MetadataStore` (implemented in 1C, semantics fixed here) must be **behaviorally identical to the local store**:
- **`readIndex(principal)`** → select the `playlists` row `(owner_id=principal.id, playlist_key=principal.outputFolder)` + its `videos` `ORDER BY position`; assemble `{ playlistUrl, playlistTitle, outputFolder: principal.outputFolder, videos: rows.map(r=>r.data) }`. **If no playlist row exists → return exactly `{ playlistUrl: '', outputFolder: principal.outputFolder, videos: [] }`** — byte-identical to the local store's ENOENT branch (`lib/index-store.ts`), which returns `playlistUrl: ''` and **does not Zod-validate on read**. The cloud store likewise does not `PlaylistIndexSchema.parse()` on read, so the empty `playlistUrl` is fine (Codex H1 re-review: the schema's `.url()` is never applied on the read path — parity with local). Never null, never throws for absent.
- **`writeIndex(principal, index)`** → in one transaction: upsert the playlist (by `owner_id`+`playlist_key`, updating `playlist_url`/`playlist_title`), then make the video set **exactly match** `index.videos` — upsert each (with `position` = its array index) and **delete videos not present**. Mirrors the local "write the whole file" semantics.
- **`upsertVideo(principal, video)`** → upsert one `videos` row (position preserved if existing). For a NEW video, position = `max(position)+1` computed **atomically** (Codex M1): the insert takes a `SELECT … FOR UPDATE`/advisory lock on the playlist row (serializing position allocation per playlist), or retries on the `videos_playlist_position_uniq` violation. Writes to a single playlist are expected to be serialized per user; the lock/retry makes concurrent allocation safe regardless.
- **`updateVideoFields(principal, id, fields)`** → JSONB-merge `fields` into `data` for that `(playlist, video_id)`, in a transaction; excludes `id`.
- The adapter **validates `data` against `VideoSchema`** before every write (Codex H5).

---

## 6. Storage-key convention (documented only)

Per parent §7.2: server-constructed canonical keys `{owner_id}/{document_id}/{version}/{type}`; reject `..`/slashes/absolute/Unicode-confusable segments. Documented here for BlobStore to inherit. **Not a 1B success criterion** (Codex L2) — no blob code or key validator ships in 1B.

---

## 7. Testing (local Supabase stack)

Test clients (Codex M4): **admin/Auth-admin API only to create users**; all data operations use the **anon key + the user's JWT** (real RLS path), never the service/admin client.

- **Isolation:** A inserts playlist+videos; a B-scoped client `select` on A's rows returns **0 rows**; `profiles`/`playlists`/`videos` each covered.
- **Mutation semantics (Codex H8), per op:** B `update`/`delete` on A's (invisible) rows ⇒ **0 rows affected** (not an error); a write that would set `owner_id`/`id` to another user (`with check` violation on a visible row) ⇒ **error**. Visibility and mutation asserted independently.
- **Cross-owner FK attack (Codex B1/H7):** B inserts a video with `owner_id=B` but `playlist_id=A's playlist` ⇒ **rejected by the composite FK**. Also B with `owner_id=A` ⇒ rejected by the `with check` policy.
- **Anonymous:** an anon session gets a `uid`+`profiles` row (via trigger), creates only its own rows, sees no other user's rows.
- **Provisioning:** immediately after sign-up (Google + anonymous), the `profiles` row exists (trigger), and a first `playlists` insert succeeds with no race.
- **service_role confinement (Codex H1/H2):** static test — no user-facing file imports `lib/supabase/service.ts`; `service.ts` constructor guard throws client-side.
- **Forced RLS regression:** assert `relforcerowsecurity` is true for each owned table (guards against a migration dropping `force`).
- **Integrity:** a row with `data->>'id' != video_id` **and** a row with `data` missing `id` are both rejected by the CHECK (Codex H3); `is_anonymous` client update is blocked (Codex L1).
- **Reordering (Codex H2):** a `writeIndex` that reverses the video order (transiently duplicating `position` values) succeeds because `videos_playlist_position_uniq` is `DEFERRABLE INITIALLY DEFERRED` — the constraint is checked only at COMMIT. A test writes order [A,B,C] then [C,B,A] in one transaction and asserts success + correct final `ORDER BY position`.
- **Trigger security (Codex re-review):** confirm `handle_new_user` is `SECURITY DEFINER`; without it the `profiles` insert would be RLS-blocked — a regression test asserts the security context.

Unit layer (jest) for client/guard units; a dedicated **integration suite** for RLS gated on `supabase start` (documented run command; not part of the default `npm test` unless the stack is up).

---

## 8. Success criteria

- `supabase start` + `supabase db reset` reproduce the schema from migrations cleanly.
- Google and anonymous sign-in both yield a session and (via trigger) a `profiles` row.
- All §7 tests pass: isolation, per-op mutation semantics, the cross-owner FK attack, anonymous isolation, provisioning-no-race, service_role confinement, forced-RLS regression, integrity CHECKs.
- No user-facing path imports the service client; `tsc --noEmit` clean.
- Additive only: existing local-tool code paths unchanged (`LocalFsMetadataStore` remains default until 1C wires selection).

---

## 9. Decisions (resolved 2026-07-02)
1. **`playlist_key`** = the YouTube playlist **list-id** (extract `list=` from the URL; reject non-playlist/malformed URLs at ingest; the raw list-id is the key). Stable across renames; unique per owner.
2. **Anon→registered upgrade** = out of scope for 1B (guests ephemeral in Stage 1); anonymous retention/cleanup tracked as a pre-public gate (§4).
3. **Migrations** = plain SQL under `supabase/migrations/`.

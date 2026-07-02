# Stage 1B — Auth + RLS Schema Design Spec

**Date:** 2026-07-02
**Repo:** `youtube-playlist-summaries-cloud` (the cloud POC fork)
**Status:** Draft — awaiting user review, then Codex adversarial review.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §7 (Auth & tenant isolation), §7.1 (RLS policy matrix), §7.2 (storage-key isolation). This spec details §7 into concrete migrations + auth wiring.

**Decisions carried in (from parent + this session):**
- Supabase Auth: **Google OAuth + anonymous auth**; sessions via `@supabase/ssr`.
- Isolation: **forced RLS**, `owner_id = auth.uid()`; `service_role` confined to the worker (later stages).
- Data shape: **JSONB-per-video** (chosen 2026-07-02) — the cloud `MetadataStore` maps rows ↔ the existing `Video`/`PlaylistIndex` types with a thin adapter.
- Dev/test: **Supabase CLI local stack (Docker)** — TDD the RLS policies locally; no cloud project until deploy.

---

## 1. Goal & scope

Establish the authentication layer and the **owned, RLS-isolated core data schema** that the cloud `MetadataStore` (Stage 1C) will read/write — **before any adapter write exists** (parent Codex-H6 ordering). Prove tenant isolation with tests against a local Supabase stack.

**In scope (1B):**
1. Supabase wired into the Next.js app (browser + server clients via `@supabase/ssr`, env config).
2. Local Supabase stack (`supabase init` + `config.toml`) for development and RLS testing.
3. **Core schema**: `profiles`, `playlists`, `videos` (JSONB) — with `owner_id`, **forced RLS**, and CRUD policies, as versioned SQL migrations.
4. **Auth**: Google OAuth sign-in/out + anonymous auth; SSR session handling + route protection.
5. **RLS isolation tests** against the local stack: tenant A cannot read/write/list tenant B's rows.
6. The **reusable RLS convention** (owner column + forced RLS + `auth.uid()` policy + service-role rule) that later tables follow.

**Explicitly NOT in scope (deferred to their stages):**
- `SupabaseMetadataStore` implementation (the row↔`Video` mapping) → **Stage 1C**.
- Tables `artifacts`, `jobs`, `usage_counters`, `share_tokens` → created in the stages that use them (BlobStore / 1D cost / 1E queue / share), each following 1B's RLS convention.
- Blob storage-key scheme (§7.2) → documented convention here, implemented in **BlobStore**.
- Migrating the existing local corpus into Postgres → a later data-migration task.
- Creating the hosted Supabase project (user action, at deploy time).

---

## 2. Prerequisites

- **Supabase CLI** — not currently installed. Install (`brew install supabase/tap/supabase` or `npx supabase`). Pinned version recorded in the plan.
- **Docker** — installed (27.5.1); **daemon must be running** for `supabase start`.
- **Hosted Supabase project** — NOT needed for 1B (local stack only). Required later for deploy; user creates it then.

---

## 3. Supabase app wiring

Add `@supabase/supabase-js` + `@supabase/ssr`. Three client factories (App Router conventions):

- `lib/supabase/client.ts` — browser client (`createBrowserClient`), anon key.
- `lib/supabase/server.ts` — server client (`createServerClient`) bound to Next cookies for SSR/route handlers; **RLS-scoped** (uses the request's auth, never `service_role`).
- `lib/supabase/service.ts` — **service-role** client. Throws if imported outside the worker/trusted server context; unused in 1B (present so the boundary is explicit). Never used on user-facing read/list paths.

Env (local stack values from `supabase start`): `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (server-only). Startup validation fails fast if missing.

---

## 4. Auth

- **Providers:** Google OAuth (primary) + Supabase **anonymous** sign-in (for the guest "taste" tier). Anonymous users get a real `auth.users` row → a real `uid` → RLS-scoped like any user (parent §7 H3: anonymous auth is mandatory, not cookie-only).
- **Session:** `@supabase/ssr` cookie-based sessions; a Next.js `middleware.ts` refreshes the session and gates protected routes.
- **Flow:** sign-in (Google button / anonymous auto-provision on first guest action) → callback route exchanges code for session → `profiles` row upserted (see §5). Sign-out clears the session.
- **`profiles`** mirrors `auth.users` (which lives in Supabase's `auth` schema) into the public schema so app tables can FK to it and RLS policies can read it.

---

## 5. Core schema (JSONB-per-video) + RLS

SQL migrations under `supabase/migrations/`. `gen_random_uuid()` for ids. **Every table: `alter table … enable row level security; alter table … force row level security;`**

```sql
-- profiles: one row per auth user (incl. anonymous)
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  is_anonymous boolean not null default false,
  created_at timestamptz not null default now()
);

-- playlists: one per (owner, playlist_key). playlist_key is the cloud analogue
-- of the local outputFolder — the opaque selector the Principal carries.
create table playlists (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references profiles(id) on delete cascade,
  playlist_key text not null,          -- Principal.outputFolder maps here
  playlist_url text not null,
  playlist_title text,
  created_at timestamptz not null default now(),
  unique (owner_id, playlist_key)
);

-- videos: JSONB holds the ENTIRE Video object (types/index.ts). owner_id is
-- denormalized onto the row so RLS is a single-column check (no join).
create table videos (
  playlist_id uuid not null references playlists(id) on delete cascade,
  owner_id uuid not null references profiles(id) on delete cascade,
  video_id text not null,              -- Video.id
  data jsonb not null,                 -- the whole Video object, verbatim
  updated_at timestamptz not null default now(),
  primary key (playlist_id, video_id)
);
create index on videos (owner_id);
```

**RLS policies (the convention every owned table follows):**

```sql
-- profiles: a user sees/edits only their own row
create policy profiles_self on profiles
  for all using (id = auth.uid()) with check (id = auth.uid());

-- playlists & videos: owner-scoped for every operation
create policy playlists_owner on playlists
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy videos_owner on videos
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
```

**Convention (reused by later tables):** owner column `owner_id uuid references profiles(id)`; `enable` + **`force`** RLS; a single `for all` policy `owner_id = auth.uid()` (both `using` and `with check`); writes that must bypass RLS happen only through the worker's `service_role` client and always set `owner_id` explicitly. Share-token reads (later) go through a `security definer` function, not a broad policy.

**Principal ↔ schema mapping (implemented in 1C, defined here):** `readIndex(principal)` = select the `playlists` row where `owner_id = principal.id AND playlist_key = principal.outputFolder`, plus its `videos`, assembled into `PlaylistIndex { playlistUrl, playlistTitle, outputFolder: principal.outputFolder, videos: rows.map(r => r.data) }`. `principal.id` = the authenticated (or anonymous) `uid`; `principal.outputFolder` = the `playlist_key`.

---

## 6. Storage-key convention (documented; implemented in BlobStore)

Per parent §7.2: object keys are server-constructed and canonical — `{owner_id}/{document_id}/{version}/{type}` — never built from user input; reject `..`/slashes/absolute forms/Unicode confusables. Recorded here so BlobStore inherits it; no blob code in 1B.

---

## 7. Testing (local Supabase stack)

RLS is the security boundary, so it is tested directly, not asserted:

- **Isolation:** create two users A and B (via the local Auth admin API); as A, insert a playlist + videos; assert that a B-scoped client `select` returns **zero** rows, and B-scoped `insert`/`update`/`delete` against A's rows are rejected. Repeat for `playlists`, `videos`, `profiles`.
- **Anonymous:** an anonymous session gets a `uid`, can create only its own rows, and cannot see any other user's rows.
- **Service-role boundary:** the `service.ts` client throws if constructed outside the trusted context (unit test).
- **Forced RLS:** confirm `force row level security` is on (a table owner still gets RLS applied) — regression guard against a migration that forgets `force`.

Tests run against `supabase start` (local). Jest layer for the client/mapping units; a dedicated integration suite for RLS (gated on the local stack being up — documented run command).

---

## 8. Success criteria

- `supabase start` brings up the local stack; migrations apply cleanly; `supabase db reset` reproduces the schema from scratch.
- Google sign-in and anonymous sign-in both yield a session and a `profiles` row.
- RLS isolation tests pass: A and B cannot see or mutate each other's `profiles`/`playlists`/`videos`; anonymous users are equally isolated.
- No user-facing path uses `service_role`; `tsc --noEmit` clean; no change to the existing local-tool code paths (this is additive — `LocalFsMetadataStore` remains the default until 1C wires selection).

---

## 9. Open decisions (for spec review)

1. **`playlist_key` derivation** — what string becomes the cloud playlist selector? Candidates: the YouTube playlist list-id (stable, from the URL), or a generated slug. Affects how `getPrincipal` (cloud) builds the Principal in 1C. Recommend: the YouTube list-id (stable, already parsed by the app).
2. **Anonymous → registered upgrade** — when a guest signs in with Google, do we migrate their anonymous rows to the new identity, or discard? Recommend: out of scope for 1B (guests are ephemeral in Stage 1); note for later.
3. **Migration tooling** — Supabase CLI migrations (plain SQL) vs. a schema DSL. Recommend: plain SQL migrations (Supabase-native, reviewable).

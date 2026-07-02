# Stage 1B — Auth + RLS Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up Supabase auth (Google OAuth + anonymous) and the owned, RLS-isolated core schema (`profiles`/`playlists`/`videos`, JSONB-per-video) on a local Supabase stack, and prove tenant isolation with tests — before any adapter write exists.

**Architecture:** Plain SQL migrations under `supabase/migrations/` define the schema, forced RLS, owner policies, a cross-owner integrity composite FK, and a `SECURITY DEFINER` provisioning trigger. Three Supabase client factories (browser/server/service) with the service client confined server-only. A separate, stack-gated integration suite exercises the real RLS path (anon key + user JWT). App wiring (middleware + OAuth callback) makes sessions flow. `LocalFsMetadataStore` stays the default; nothing here changes existing local-tool behavior.

**Tech Stack:** Next.js (modified — see Global Constraints), TypeScript, Supabase (Postgres + Auth + RLS), `@supabase/supabase-js`, `@supabase/ssr`, Supabase CLI local stack (Docker), Jest (via `next/jest`, SWC transform), Zod.

## Global Constraints

- **Additive only.** `LocalFsMetadataStore` remains the default store; no existing local-tool code path changes behavior. No `SupabaseMetadataStore` in 1B (that is 1C).
- **service_role never user-facing.** No file reachable from `app/**` route handlers or server components may import `lib/supabase/service.ts`. Enforced by `import 'server-only'`, a runtime guard, and a CI import-graph scan.
- **Forced RLS on every owned table:** `enable` **and** `force` row level security. A migration that drops `force` is a defect (regression test guards it).
- **Test data operations use the anon key + the user's JWT** (the real RLS path). The service/admin client is used **only** to create users and to inspect the catalog in test setup — never for the assertions under test.
- **`playlist_key` = the YouTube playlist list-id** (the `list=` value). Stable across renames, unique per owner.
- **Next.js is modified in this repo.** Before writing `middleware.ts` or any route handler (Task 10), read the relevant guide under `node_modules/next/dist/docs/` (per `AGENTS.md`). APIs may differ from training data.
- **Jest runs via SWC and does not typecheck.** After each task, `npx tsc --noEmit` is the real type gate — run it before commit.
- **Empty-read parity:** the cloud store's read path (specified in 1C, constrained here) returns `{ playlistUrl: '', outputFolder, videos: [] }` for an absent playlist and does **not** Zod-validate on read — byte-identical to `lib/index-store.ts`'s ENOENT branch.

---

## File Structure

- `supabase/config.toml` — CLI local-stack config (`supabase init`).
- `supabase/migrations/0001_core_schema.sql` — tables, composite FK, CHECK, deferrable position constraint, indexes, forced RLS.
- `supabase/migrations/0002_rls_policies.sql` — the three owner policies.
- `supabase/migrations/0003_provisioning.sql` — `handle_new_user` trigger (`SECURITY DEFINER`) + `is_anonymous` immutability guard.
- `lib/supabase/env.ts` — env var reader + fail-fast validation.
- `lib/supabase/client.ts` — browser client (`createBrowserClient`, anon key).
- `lib/supabase/server.ts` — RLS-scoped server client bound to Next cookies.
- `lib/supabase/service.ts` — service_role client; `import 'server-only'` + runtime guard; unused in 1B.
- `scripts/check-service-confinement.ts` — CI import-graph scan.
- `middleware.ts` — session refresh + route-category redirects.
- `app/auth/callback/route.ts` — OAuth code-exchange callback.
- `tests/lib/supabase/*.test.ts` — unit tests (env, guard, confinement scan).
- `tests/integration/**` — stack-gated RLS integration suite + harness.
- `jest.integration.config.ts` + `test:integration` script — separate runner; **not** matched by the default `npm test`.

---

## Task 1: Dependencies + Supabase local-stack scaffolding + env validation

**Files:**
- Modify: `package.json` (deps + `test:integration` script)
- Create: `supabase/config.toml` (via `npx supabase init`)
- Create: `lib/supabase/env.ts`
- Create: `.env.test.local.example`
- Test: `tests/lib/supabase/env.test.ts`

**Interfaces:**
- Produces: `getSupabaseEnv(): { url: string; anonKey: string }` and `getServiceRoleKey(): string` (throws if the respective vars are missing). Consumed by Tasks 5, 7.

- [ ] **Step 1: Install dependencies**

```bash
cd /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
npm install                      # node_modules is absent in this fresh clone
npm install @supabase/supabase-js @supabase/ssr server-only
```

- [ ] **Step 2: Initialize the Supabase CLI project + enable anonymous auth**

```bash
npx supabase --version           # pin this version in the commit message
npx supabase init                # creates supabase/config.toml + supabase/ dir
```

**Codex B2 — anonymous sign-in must be enabled in config, or `signInAnonymously()` fails locally.** Edit `supabase/config.toml`:

```toml
[auth]
enable_anonymous_sign_ins = true   # required for the guest "taste" path (spec §4)

[auth.email]
enable_confirmations = false       # local stack: admin.createUser uses email_confirm:true;
                                   # disabling confirmations keeps signInWithPassword usable in tests
```

After Task 7's harness exists, smoke-test that `anonSession()` succeeds against a freshly `db reset` stack; if `enable_anonymous_sign_ins` is missing the call returns an "Anonymous sign-ins are disabled" error.

Do **not** run `supabase start` yet (Docker daemon must be up; that is a run-time concern documented in Task 7).

- [ ] **Step 3: Write the failing test for env validation**

```typescript
// tests/lib/supabase/env.test.ts
import { getSupabaseEnv, getServiceRoleKey } from '@/lib/supabase/env';

describe('supabase env', () => {
  const saved = { ...process.env };
  afterEach(() => { process.env = { ...saved }; });

  it('returns url + anon key when both are present', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-123';
    expect(getSupabaseEnv()).toEqual({ url: 'http://localhost:54321', anonKey: 'anon-123' });
  });

  it('throws when the url is missing', () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-123';
    expect(() => getSupabaseEnv()).toThrow(/NEXT_PUBLIC_SUPABASE_URL/);
  });

  it('throws when the anon key is missing', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    expect(() => getSupabaseEnv()).toThrow(/NEXT_PUBLIC_SUPABASE_ANON_KEY/);
  });

  it('getServiceRoleKey throws when the key is missing', () => {
    delete process.env.SUPABASE_SERVICE_ROLE_KEY;
    expect(() => getServiceRoleKey()).toThrow(/SUPABASE_SERVICE_ROLE_KEY/);
  });
});
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `npx jest tests/lib/supabase/env.test.ts`
Expected: FAIL — `Cannot find module '@/lib/supabase/env'`.

- [ ] **Step 5: Implement env validation**

```typescript
// lib/supabase/env.ts
function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

export function getSupabaseEnv(): { url: string; anonKey: string } {
  return {
    url: required('NEXT_PUBLIC_SUPABASE_URL'),
    anonKey: required('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
  };
}

/** Server-only. Never call from client code. */
export function getServiceRoleKey(): string {
  return required('SUPABASE_SERVICE_ROLE_KEY');
}
```

- [ ] **Step 6: Add the example env file and the integration script**

```bash
# .env.test.local.example — copy to .env.test.local and fill from `supabase status -o env`
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

Add to `package.json` scripts:
```json
"test:integration": "jest --config jest.integration.config.ts"
```

- [ ] **Step 7: Run test + tsc, then commit**

```bash
npx jest tests/lib/supabase/env.test.ts   # PASS
npx tsc --noEmit                           # clean
git add package.json package-lock.json supabase/config.toml lib/supabase/env.ts \
        tests/lib/supabase/env.test.ts .env.test.local.example
git commit -m "feat(supabase): deps + local-stack scaffolding + env validation"
```

---

## Task 2: Core schema migration

**Files:**
- Create: `supabase/migrations/0001_core_schema.sql`
- Test: `tests/integration/schema.test.ts` (stack-gated — runs under `test:integration`)

**Interfaces:**
- Produces: tables `profiles`, `playlists`, `videos` with forced RLS enabled. Consumed by Tasks 3, 4, 8, 9.

> Integration tests require the local stack (Task 7 builds the harness). This task's test may be **written now and left failing/skipped until Task 7's harness exists**; the implementer writes the migration and the test file, and confirms the migration applies via `supabase db reset` if Docker is available. If the stack is not up in this task's environment, mark the test `describe.skip` with a `// unskip after Task 7` note and rely on `db reset` output as the RED→GREEN signal for the migration itself.

- [ ] **Step 1: Write the migration**

```sql
-- supabase/migrations/0001_core_schema.sql
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  is_anonymous boolean not null default false,
  created_at timestamptz not null default now()
);
alter table profiles enable row level security;
alter table profiles force row level security;

create table playlists (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references profiles(id) on delete cascade,
  playlist_key text not null,             -- YouTube list-id; Principal.outputFolder maps here
  playlist_url text not null,
  playlist_title text,
  created_at timestamptz not null default now(),
  unique (owner_id, playlist_key),
  unique (id, owner_id)                    -- enables the composite FK below
);
alter table playlists enable row level security;
alter table playlists force row level security;

create table videos (
  playlist_id uuid not null,
  owner_id    uuid not null,
  video_id    text not null,               -- Video.id
  position    int  not null,               -- array order in PlaylistIndex.videos
  data        jsonb not null,              -- the whole Video object, verbatim
  updated_at  timestamptz not null default now(),
  primary key (playlist_id, video_id),
  -- a video's owner MUST equal its playlist's owner (cross-tenant injection guard)
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade,
  -- relational id == JSONB id AND id must be present (NULL guard: NULL = video_id is
  -- UNKNOWN and would pass the CHECK, so IS NOT NULL forces rejection of a missing id)
  check (data->>'id' is not null and data->>'id' = video_id),
  -- DEFERRABLE so writeIndex reordering can transiently duplicate a position within a
  -- transaction and settle valid at COMMIT. Must be a CONSTRAINT, not a unique INDEX.
  constraint videos_playlist_position_uniq unique (playlist_id, position)
    deferrable initially deferred
);
alter table videos enable row level security;
alter table videos force row level security;
create index on videos (owner_id);
```

- [ ] **Step 2: Verify the migration applies cleanly**

```bash
# Requires Docker daemon running.
npx supabase start
npx supabase db reset            # applies 0001 from scratch
```
Expected: reset succeeds, no SQL errors.

- [ ] **Step 3: Write the schema integration test**

```typescript
// tests/integration/schema.test.ts
import { adminClient } from './helpers/clients';

describe('core schema', () => {
  it('has RLS enabled AND forced on every owned table (Codex M1)', async () => {
    const admin = adminClient();
    const { data, error } = await admin.rpc('exec_sql', {
      // helper defined in Task 7 harness; or query pg_class via a SQL function
      sql: `select relname, relrowsecurity, relforcerowsecurity from pg_class
            where relname in ('profiles','playlists','videos') order by relname`,
    });
    expect(error).toBeNull();
    // both flags must be true: `enable` alone lets the table owner bypass RLS;
    // `force` makes even the owner obey it.
    expect(data).toEqual([
      { relname: 'playlists', relrowsecurity: true, relforcerowsecurity: true },
      { relname: 'profiles',  relrowsecurity: true, relforcerowsecurity: true },
      { relname: 'videos',    relrowsecurity: true, relforcerowsecurity: true },
    ]);
  });
});
```
> Note for implementer: the exact catalog-query mechanism (an `exec_sql` RPC vs. a typed view) is finalized in Task 7's harness. Keep the assertion (forced RLS true for all three) fixed; adapt the plumbing to whatever the harness exposes.

- [ ] **Step 4: Run integration test (if stack up) + tsc, then commit**

```bash
npx tsc --noEmit
git add supabase/migrations/0001_core_schema.sql tests/integration/schema.test.ts
git commit -m "feat(schema): core profiles/playlists/videos with forced RLS + composite FK"
```

---

## Task 3: RLS owner policies migration

**Files:**
- Create: `supabase/migrations/0002_rls_policies.sql`
- Test: covered by the isolation suite (Task 8); a `pg_policies` presence check lives in `tests/integration/schema.test.ts`

**Interfaces:**
- Produces: one `for all` owner policy per table (`owner_id = auth.uid()` / `id = auth.uid()` for profiles). Consumed by Tasks 8, 9.

- [ ] **Step 1: Write the policies migration**

```sql
-- supabase/migrations/0002_rls_policies.sql
create policy profiles_self  on profiles  for all
  using (id = auth.uid())        with check (id = auth.uid());
create policy playlists_owner on playlists for all
  using (owner_id = auth.uid())  with check (owner_id = auth.uid());
create policy videos_owner    on videos    for all
  using (owner_id = auth.uid())  with check (owner_id = auth.uid());
```

- [ ] **Step 2: Add a policy-presence assertion to the schema test**

```typescript
// append to tests/integration/schema.test.ts
it('defines exactly one owner policy per table, ALL cmd, with a with_check (Codex L1)', async () => {
  const admin = adminClient();
  const { data } = await admin.rpc('exec_sql', {
    // assert cmd + that with_check is present, not just the name — a malformed
    // policy with the right name but no with_check would otherwise pass.
    sql: `select tablename, policyname, cmd, (with_check is not null) as has_with_check
          from pg_policies where schemaname='public' order by tablename`,
  });
  expect(data).toEqual([
    { tablename: 'playlists', policyname: 'playlists_owner', cmd: 'ALL', has_with_check: true },
    { tablename: 'profiles',  policyname: 'profiles_self',   cmd: 'ALL', has_with_check: true },
    { tablename: 'videos',    policyname: 'videos_owner',    cmd: 'ALL', has_with_check: true },
  ]);
});
```

- [ ] **Step 3: Apply + commit**

```bash
npx supabase db reset            # if stack up
npx tsc --noEmit
git add supabase/migrations/0002_rls_policies.sql tests/integration/schema.test.ts
git commit -m "feat(rls): owner policies for profiles/playlists/videos"
```

---

## Task 4: Provisioning trigger + is_anonymous immutability

**Files:**
- Create: `supabase/migrations/0003_provisioning.sql`
- Test: `tests/integration/provisioning.test.ts`

**Interfaces:**
- Produces: `handle_new_user` (`SECURITY DEFINER`) fires `after insert on auth.users`; a `BEFORE UPDATE` guard on `profiles.is_anonymous`. Consumed by every sign-up path.

- [ ] **Step 1: Write the provisioning migration**

```sql
-- supabase/migrations/0003_provisioning.sql
create function handle_new_user() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, is_anonymous)
  values (new.id, coalesce(new.is_anonymous, false));
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users for each row execute function handle_new_user();

-- is_anonymous is set once at provisioning; reject client attempts to change it.
create function guard_is_anonymous() returns trigger
  language plpgsql as $$
begin
  if new.is_anonymous is distinct from old.is_anonymous then
    raise exception 'is_anonymous is immutable';
  end if;
  return new;
end $$;

create trigger profiles_is_anonymous_immutable
  before update on profiles for each row execute function guard_is_anonymous();
```

- [ ] **Step 2: Write the failing provisioning tests**

```typescript
// tests/integration/provisioning.test.ts
import { adminClient, anonSession, newUser } from './helpers/clients';

describe('provisioning trigger', () => {
  it('creates exactly one profiles row for a Google-style (email) sign-up', async () => {
    const admin = adminClient();
    const { user } = await newUser();                 // admin.auth.admin.createUser
    const { data } = await admin
      .from('profiles').select('id,is_anonymous').eq('id', user.id);
    expect(data).toEqual([{ id: user.id, is_anonymous: false }]);
  });

  it('creates a profiles row with is_anonymous=true for an anonymous sign-up', async () => {
    const { client, userId } = await anonSession();   // client.auth.signInAnonymously
    const { data } = await client.from('profiles').select('id,is_anonymous').eq('id', userId);
    expect(data).toEqual([{ id: userId, is_anonymous: true }]);
  });

  it('is SECURITY DEFINER (else the RLS-protected profiles insert would abort signup)', async () => {
    const admin = adminClient();
    const { data } = await admin.rpc('exec_sql', {
      sql: `select prosecdef from pg_proc where proname = 'handle_new_user'`,
    });
    expect(data).toEqual([{ prosecdef: true }]);
  });

  it('rejects a client attempt to flip is_anonymous', async () => {
    const { client, userId } = await anonSession();
    const { error } = await client.from('profiles')
      .update({ is_anonymous: false }).eq('id', userId);
    expect(error?.message).toMatch(/is_anonymous is immutable/);
  });
});
```

- [ ] **Step 3: Run (RED, if stack up) → apply migration → GREEN**

```bash
npx supabase db reset
npx jest --config jest.integration.config.ts tests/integration/provisioning.test.ts
```
Expected: PASS after the migration is applied.

- [ ] **Step 4: tsc + commit**

```bash
npx tsc --noEmit
git add supabase/migrations/0003_provisioning.sql tests/integration/provisioning.test.ts
git commit -m "feat(auth): SECURITY DEFINER provisioning trigger + is_anonymous guard"
```

---

## Task 5: Supabase client factories + server-only service guard

**Files:**
- Create: `lib/supabase/client.ts`, `lib/supabase/server.ts`, `lib/supabase/service.ts`
- Test: `tests/lib/supabase/service-guard.test.ts`

**Interfaces:**
- Consumes: `getSupabaseEnv`, `getServiceRoleKey` (Task 1).
- Produces: `createClient()` (browser), `createServerSupabase(cookieStore)` (RLS-scoped), `createServiceClient()` (service_role, server-only). Consumed by Task 10 and (later) 1C.

- [ ] **Step 1: Write the failing guard test**

```typescript
// tests/lib/supabase/service-guard.test.ts
describe('service client guard', () => {
  const saved = { ...process.env };
  afterEach(() => { process.env = { ...saved }; (globalThis as any).window = undefined; });

  it('throws if constructed in a browser-like environment', async () => {
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'svc-123';
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    (globalThis as any).window = {};                  // simulate client bundle
    const { createServiceClient } = await import('@/lib/supabase/service');
    expect(() => createServiceClient()).toThrow(/server-only|window/i);
  });

  it('throws if the service role key is absent', async () => {
    delete process.env.SUPABASE_SERVICE_ROLE_KEY;
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    const { createServiceClient } = await import('@/lib/supabase/service');
    expect(() => createServiceClient()).toThrow(/SUPABASE_SERVICE_ROLE_KEY/);
  });
});
```
> `service.ts` starts with `import 'server-only'`. In jest (node env) that import resolves to a no-op; the build-time protection is what `server-only` enforces in a client bundle. Test the **runtime guard** here; the build/CI protection is Task 6.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest tests/lib/supabase/service-guard.test.ts`
Expected: FAIL — `Cannot find module '@/lib/supabase/service'`.

- [ ] **Step 3: Implement the three factories**

```typescript
// lib/supabase/client.ts
'use client';
import { createBrowserClient } from '@supabase/ssr';
import { getSupabaseEnv } from './env';

export function createClient() {
  const { url, anonKey } = getSupabaseEnv();
  return createBrowserClient(url, anonKey);
}
```

```typescript
// lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr';
import { getSupabaseEnv } from './env';

type CookieStore = {
  getAll(): { name: string; value: string }[];
  set(name: string, value: string, options?: Record<string, unknown>): void;
};

/** RLS-scoped to the request's session. Never uses the service role. */
export function createServerSupabase(cookies: CookieStore) {
  const { url, anonKey } = getSupabaseEnv();
  return createServerClient(url, anonKey, {
    cookies: {
      getAll: () => cookies.getAll(),
      setAll: (list) => list.forEach(({ name, value, options }) => cookies.set(name, value, options)),
    },
  });
}
```
> The implementer must confirm the `@supabase/ssr` cookie adapter shape against the installed version's types (getAll/setAll vs get/set/remove) and adjust; run `npx tsc --noEmit` as the check.

```typescript
// lib/supabase/service.ts
import 'server-only';
import { createClient } from '@supabase/supabase-js';
import { getSupabaseEnv, getServiceRoleKey } from './env';

/** service_role client with BYPASSRLS. Server-only; never import from client/route code
 *  reachable by the browser. Unused in 1B. */
export function createServiceClient() {
  if (typeof window !== 'undefined') {
    throw new Error('createServiceClient() must never run in a browser (server-only)');
  }
  const { url } = getSupabaseEnv();
  const key = getServiceRoleKey();
  return createClient(url, key, { auth: { autoRefreshToken: false, persistSession: false } });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest tests/lib/supabase/service-guard.test.ts`
Expected: PASS.

- [ ] **Step 5: tsc + commit**

```bash
npx tsc --noEmit
git add lib/supabase/client.ts lib/supabase/server.ts lib/supabase/service.ts \
        tests/lib/supabase/service-guard.test.ts
git commit -m "feat(supabase): browser/server/service client factories + runtime guard"
```

---

## Task 6: service_role confinement — import-graph scan

**Files:**
- Create: `scripts/check-service-confinement.ts`
- Test: `tests/lib/supabase/confinement.test.ts`

**Interfaces:**
- Produces: `findServiceImporters(): string[]` — returns any user-facing Next entrypoint whose transitive import graph reaches `lib/supabase/service.ts`. Empty in 1B.
- `collectEntrypoints(): string[]` — the exhaustive user-facing entry set (Codex H2): `app/**`, `middleware.ts` (root, edge-executed), and any `pages/**`.

> **Codex H2/H3/H4:** the scan is the **build-time entrypoint confinement proof** that `service.ts` is unreachable from middleware, RSC, and route handlers (the runtime `window` guard in Task 5 is only defense-in-depth). It must (H2) cover **every** user-facing entry, not just `app/**`, and (H3) match **side-effect** imports (`import '@/lib/supabase/service'`) and re-exports, not only `... from '...'`.

- [ ] **Step 1: Write the failing tests (incl. a synthetic side-effect-import fixture)**

```typescript
// tests/lib/supabase/confinement.test.ts
import fs from 'fs';
import path from 'path';
import { findServiceImporters, extractImportSpecifiers } from '@/scripts/check-service-confinement';

describe('service_role confinement', () => {
  it('no user-facing Next entrypoint transitively imports lib/supabase/service.ts', () => {
    expect(findServiceImporters()).toEqual([]);   // app/**, middleware.ts, pages/**
  });

  it('extractImportSpecifiers catches side-effect + re-export imports (Codex H3)', () => {
    const src = [
      `import '@/lib/supabase/service';`,               // side-effect import
      `export { createServiceClient } from './service';`, // re-export
      `const x = await import('@/lib/supabase/service');`, // dynamic
      `import { a } from '@/lib/supabase/env';`,          // named
    ].join('\n');
    const specs = extractImportSpecifiers(src);
    expect(specs).toEqual(
      expect.arrayContaining(['@/lib/supabase/service', './service', '@/lib/supabase/service', '@/lib/supabase/env']),
    );
  });

  it('detects a planted violation reaching service.ts through a side-effect import', () => {
    const dir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'confine-'));
    const entry = path.join(dir, 'evil.ts');
    fs.writeFileSync(entry, `import '${path.join(process.cwd(), 'lib/supabase/service')}';\n`);
    // reach() is exported for this fixture check
    const { reachesService } = require('@/scripts/check-service-confinement');
    expect(reachesService(entry)).toBe(true);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest tests/lib/supabase/confinement.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the transitive scan (broad entrypoints + side-effect imports)**

```typescript
// scripts/check-service-confinement.ts
import fs from 'fs';
import path from 'path';

const ROOT = process.cwd();
const TARGET = path.join(ROOT, 'lib/supabase/service.ts');

function resolveImport(fromFile: string, spec: string): string | null {
  let base: string;
  if (spec.startsWith('@/')) base = path.join(ROOT, spec.slice(2));
  else if (spec.startsWith('.')) base = path.resolve(path.dirname(fromFile), spec);
  else return null;                               // bare package import — not our code
  const candidates = base.endsWith('.ts') || base.endsWith('.tsx')
    ? [base]
    : ['.ts', '.tsx', '.js', '/index.ts', '/index.tsx'].map((e) => base + e);
  for (const cand of candidates) {
    if (fs.existsSync(cand) && fs.statSync(cand).isFile()) return cand;
  }
  return null;
}

/** Codex H3: match named/default/namespace `from` imports, bare SIDE-EFFECT imports
 *  (`import 'x'`), re-exports (`export ... from 'x'`), and dynamic `import('x')`. */
export function extractImportSpecifiers(src: string): string[] {
  const out: string[] = [];
  const patterns = [
    /(?:import|export)\s[^;'"]*?from\s*['"]([^'"]+)['"]/g, // import/export ... from '...'
    /import\s*['"]([^'"]+)['"]/g,                          // side-effect: import '...'
    /import\(\s*['"]([^'"]+)['"]\s*\)/g,                   // dynamic import('...')
    /require\(\s*['"]([^'"]+)['"]\s*\)/g,                  // require('...')
  ];
  for (const re of patterns) for (let m; (m = re.exec(src)); ) out.push(m[1]);
  return out;
}

export function reachesService(entry: string): boolean {
  const seen = new Set<string>();
  const stack = [entry];
  while (stack.length) {
    const f = stack.pop()!;
    if (seen.has(f)) continue;
    seen.add(f);
    if (path.resolve(f) === TARGET) return true;
    if (!fs.existsSync(f)) continue;
    for (const spec of extractImportSpecifiers(fs.readFileSync(f, 'utf8'))) {
      const r = resolveImport(f, spec);
      if (r) stack.push(r);
    }
  }
  return false;
}

function walk(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return /\.(ts|tsx)$/.test(e.name) ? [p] : [];
  });
}

/** Codex H2: every user-facing entry — not just app/**. */
export function collectEntrypoints(): string[] {
  const entries = [...walk(path.join(ROOT, 'app')), ...walk(path.join(ROOT, 'pages'))];
  const mw = path.join(ROOT, 'middleware.ts');
  if (fs.existsSync(mw)) entries.push(mw);
  return entries;
}

export function findServiceImporters(): string[] {
  return collectEntrypoints().filter((e) => path.resolve(e) !== TARGET && reachesService(e));
}

if (require.main === module) {
  const violators = findServiceImporters();
  if (violators.length) {
    console.error('service.ts reachable from a user-facing entrypoint:\n' + violators.join('\n'));
    process.exit(1);
  }
  console.log('service_role confinement OK');
}
```

> A regex walker is a pragmatic backstop; if the reviewer wants stronger guarantees the implementer may swap `extractImportSpecifiers` for a TypeScript-compiler-API pass over the same entrypoint set. Keep the exported signatures + the assertions stable.

- [ ] **Step 4: Run to verify it passes**

Run: `npx jest tests/lib/supabase/confinement.test.ts`
Expected: PASS (no user-facing entry imports the service client in 1B).

- [ ] **Step 5: Wire into CI-style check + commit**

Add to `package.json` scripts:
```json
"check:confinement": "ts-node scripts/check-service-confinement.ts"
```
```bash
npx tsc --noEmit
git add scripts/check-service-confinement.ts tests/lib/supabase/confinement.test.ts package.json
git commit -m "feat(security): transitive import-graph scan confining service_role client"
```

---

## Task 7: Integration test harness (stack-gated)

**Files:**
- Create: `jest.integration.config.ts`
- Create: `tests/integration/setup.ts`
- Create: `tests/integration/helpers/clients.ts`
- Create: `supabase/migrations/0004_test_exec_sql.sql` (test-only catalog-inspection RPC; see note)

**Interfaces:**
- Produces: `adminClient()`, `newUser()`, `signInAs(email, password)`, `anonSession()` for the RLS suite (Tasks 8, 9). Consumes env from `.env.test.local` (populated from `supabase status -o env`).

> **exec_sql RPC:** the catalog assertions in Tasks 2–4 need arbitrary read-only SQL. Ship a `SECURITY DEFINER` function `exec_sql(sql text)` that is **granted only to the service_role** (never anon/authenticated), returning `jsonb`. It exists solely for tests inspecting `pg_class`/`pg_policies`/`pg_proc`; it is never reachable by a user JWT. If the reviewer flags this as attack surface, the alternative is typed views over the three catalogs granted to service_role — implementer may substitute that; keep the test assertions stable.

- [ ] **Step 1: Write the integration jest config**

```typescript
// jest.integration.config.ts
import nextJest from 'next/jest.js';
const createJestConfig = nextJest({ dir: './' });
export default createJestConfig({
  testEnvironment: 'node',
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/$1' },
  setupFiles: ['<rootDir>/tests/integration/setup.ts'],
  testMatch: ['<rootDir>/tests/integration/**/*.test.ts'],
});
```
> The default `npm test` (`jest.config.ts`) does **not** match `tests/integration/**`, so the stack-gated suite never runs under `npm test`. It runs only via `npm run test:integration`.

- [ ] **Step 2: Write the setup (loads local-stack env, fails fast if the stack is down)**

```typescript
// tests/integration/setup.ts
import fs from 'fs';
import path from 'path';

const envPath = path.join(process.cwd(), '.env.test.local');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z_]+)=(.*)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
}
if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
  throw new Error(
    'Integration suite requires a running local Supabase stack.\n' +
    'Run: npx supabase start && npx supabase status -o env > .env.test.local',
  );
}
```

- [ ] **Step 3: Write the client helpers**

```typescript
// tests/integration/helpers/clients.ts
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const url = () => process.env.NEXT_PUBLIC_SUPABASE_URL!;
const anon = () => process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const service = () => process.env.SUPABASE_SERVICE_ROLE_KEY!;

export function adminClient(): SupabaseClient {
  return createClient(url(), service(), { auth: { autoRefreshToken: false, persistSession: false } });
}

let seq = 0;
export async function newUser(): Promise<{ user: { id: string }; email: string; password: string }> {
  const email = `u${Date.now()}-${seq++}@example.test`;
  const password = 'test-password-123';
  const admin = adminClient();
  const { data, error } = await admin.auth.admin.createUser({ email, password, email_confirm: true });
  if (error || !data.user) throw error ?? new Error('createUser failed');
  return { user: { id: data.user.id }, email, password };
}

/** RLS-scoped client authenticated as a real user (anon key + user JWT). */
export async function signInAs(email: string, password: string): Promise<{ client: SupabaseClient; userId: string }> {
  const client = createClient(url(), anon(), { auth: { autoRefreshToken: false, persistSession: false } });
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error || !data.user) throw error ?? new Error('signIn failed');
  return { client, userId: data.user.id };
}

export async function anonSession(): Promise<{ client: SupabaseClient; userId: string }> {
  const client = createClient(url(), anon(), { auth: { autoRefreshToken: false, persistSession: false } });
  const { data, error } = await client.auth.signInAnonymously();
  if (error || !data.user) throw error ?? new Error('anon sign-in failed');
  return { client, userId: data.user.id };
}
```

- [ ] **Step 4: Write the test-only exec_sql migration**

```sql
-- supabase/migrations/0004_test_exec_sql.sql
-- Read-only catalog inspection for the integration suite. Granted to service_role ONLY.
create function exec_sql(sql text) returns jsonb
  language plpgsql security definer set search_path = '' as $$
declare result jsonb;
begin
  execute 'select coalesce(jsonb_agg(t), ''[]''::jsonb) from (' || sql || ') t' into result;
  return result;
end $$;
revoke all on function exec_sql(text) from public, anon, authenticated;
grant execute on function exec_sql(text) to service_role;
```
> The reviewer should scrutinize this: it is a deliberate test-only escape hatch, service_role-gated, and never reachable by a user JWT (RLS suite never calls it as a user). If deemed unacceptable, replace with three typed views over `pg_class`/`pg_policies`/`pg_proc`.

- [ ] **Step 5: Write the exec_sql confinement test (Codex M2)**

```typescript
// tests/integration/exec-sql-guard.test.ts
import { newUser, signInAs, anonSession } from './helpers/clients';

describe('exec_sql is service_role-only', () => {
  it('a user-JWT client cannot call exec_sql', async () => {
    const u = await newUser();
    const { client } = await signInAs(u.email, u.password);
    const { error } = await client.rpc('exec_sql', { sql: 'select 1' });
    expect(error).not.toBeNull();                    // permission denied for authenticated
  });

  it('an anon client cannot call exec_sql', async () => {
    const { client } = await anonSession();
    const { error } = await client.rpc('exec_sql', { sql: 'select 1' });
    expect(error).not.toBeNull();                    // permission denied for anon
  });
});
```

- [ ] **Step 6: Smoke-verify the harness**

```bash
npx supabase start
npx supabase status -o env > .env.test.local
npx supabase db reset
npx jest --config jest.integration.config.ts tests/integration/schema.test.ts tests/integration/exec-sql-guard.test.ts
```
Expected: the previously-skipped Task 2/3 catalog tests now pass (unskip them); the exec_sql guard tests pass.

- [ ] **Step 7: tsc + commit**

```bash
npx tsc --noEmit
git add jest.integration.config.ts tests/integration/setup.ts tests/integration/helpers/clients.ts \
        tests/integration/exec-sql-guard.test.ts supabase/migrations/0004_test_exec_sql.sql
git commit -m "test(integration): stack-gated RLS harness (admin + user-JWT + anon clients)"
```

---

## Task 8: RLS isolation + mutation-semantics + cross-owner FK attack tests

**Files:**
- Create: `tests/integration/rls-isolation.test.ts`

**Interfaces:**
- Consumes: harness helpers (Task 7), schema + policies + trigger (Tasks 2–4).

- [ ] **Step 1: Write the isolation + mutation + FK-attack tests**

```typescript
// tests/integration/rls-isolation.test.ts
import { newUser, signInAs } from './helpers/clients';

async function seedPlaylistWithVideos(email: string, password: string, key: string) {
  const { client, userId } = await signInAs(email, password);
  const { data: pl, error: e1 } = await client.from('playlists')
    .insert({ owner_id: userId, playlist_key: key, playlist_url: `https://youtube.com/playlist?list=${key}` })
    .select('id').single();
  expect(e1).toBeNull();
  const rows = [0, 1].map((i) => ({
    playlist_id: pl!.id, owner_id: userId, video_id: `v${i}`, position: i, data: { id: `v${i}` },
  }));
  const { error: e2 } = await client.from('videos').insert(rows);
  expect(e2).toBeNull();
  return { client, userId, playlistId: pl!.id };
}

describe('RLS isolation', () => {
  it('B cannot see A\'s profiles, playlists, or videos (0 rows, not error) (Codex H5)', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLaaa');
    const b = await newUser();
    const { client: bClient } = await signInAs(b.email, b.password);

    // profiles isolation (spec §7 requires all three tables)
    const prof = await bClient.from('profiles').select('*').eq('id', A.userId);
    expect(prof.error).toBeNull();
    expect(prof.data).toEqual([]);

    const pl = await bClient.from('playlists').select('*').eq('id', A.playlistId);
    expect(pl.error).toBeNull();
    expect(pl.data).toEqual([]);

    const vids = await bClient.from('videos').select('*').eq('playlist_id', A.playlistId);
    expect(vids.data).toEqual([]);
  });

  it('B update AND delete on A\'s invisible rows affect 0 rows (no error) (Codex H6)', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLbbb');
    const b = await newUser();
    const { client: bClient } = await signInAs(b.email, b.password);

    const upd = await bClient.from('videos').update({ position: 99 })
      .eq('playlist_id', A.playlistId).select();
    expect(upd.error).toBeNull();
    expect(upd.data).toEqual([]);                    // invisible → 0 affected

    const del = await bClient.from('videos').delete()
      .eq('playlist_id', A.playlistId).select();
    expect(del.error).toBeNull();
    expect(del.data).toEqual([]);                    // invisible → 0 deleted

    // A's rows are untouched (verified from A's own client)
    const stillThere = await A.client.from('videos').select('video_id')
      .eq('playlist_id', A.playlistId).order('position');
    expect(stillThere.data).toEqual([{ video_id: 'v0' }, { video_id: 'v1' }]);
  });

  it('with-check violation on a VISIBLE own row errors (owner_id reassignment) (Codex H6)', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLwc');
    const b = await newUser();
    const { userId: bId } = await signInAs(b.email, b.password);

    // A tries to hand its own (visible) video to B → with_check(owner_id=auth.uid()) fails
    const reassign = await A.client.from('videos').update({ owner_id: bId })
      .eq('playlist_id', A.playlistId).eq('video_id', 'v0').select();
    expect(reassign.error).not.toBeNull();           // visible row + bad with_check ⇒ error, not 0 rows
  });

  it('cross-owner FK attack: B inserts video with playlist_id=A is rejected', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLccc');
    const b = await newUser();
    const { client: bClient, userId: bId } = await signInAs(b.email, b.password);

    // owner_id=B, playlist_id=A: composite FK (playlist_id, owner_id) has no match → rejected
    const asB = await bClient.from('videos')
      .insert({ playlist_id: A.playlistId, owner_id: bId, video_id: 'x', position: 0, data: { id: 'x' } });
    expect(asB.error).not.toBeNull();

    // owner_id=A (spoof): with-check policy violation → rejected
    const asA = await bClient.from('videos')
      .insert({ playlist_id: A.playlistId, owner_id: A.userId, video_id: 'y', position: 0, data: { id: 'y' } });
    expect(asA.error).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run + tsc + commit**

```bash
npx jest --config jest.integration.config.ts tests/integration/rls-isolation.test.ts   # PASS
npx tsc --noEmit
git add tests/integration/rls-isolation.test.ts
git commit -m "test(rls): isolation, per-op mutation semantics, cross-owner FK attack"
```

---

## Task 9: Integrity, reordering, anonymous, forced-RLS regression tests

**Files:**
- Create: `tests/integration/integrity.test.ts`

**Interfaces:**
- Consumes: harness helpers (Task 7), all migrations.

- [ ] **Step 1: Write the integrity/reorder/anon tests**

```typescript
// tests/integration/integrity.test.ts
import { newUser, signInAs, anonSession } from './helpers/clients';

async function ownedPlaylist(email: string, password: string, key: string) {
  const { client, userId } = await signInAs(email, password);
  const { data } = await client.from('playlists')
    .insert({ owner_id: userId, playlist_key: key, playlist_url: `https://youtube.com/playlist?list=${key}` })
    .select('id').single();
  return { client, userId, playlistId: data!.id };
}

describe('integrity + reordering', () => {
  it('rejects a video whose data.id != video_id', async () => {
    const u = await newUser();
    const { client, userId, playlistId } = await ownedPlaylist(u.email, u.password, 'PLint1');
    const { error } = await client.from('videos')
      .insert({ playlist_id: playlistId, owner_id: userId, video_id: 'v0', position: 0, data: { id: 'MISMATCH' } });
    expect(error).not.toBeNull();
  });

  it('rejects a video whose data has no id', async () => {
    const u = await newUser();
    const { client, userId, playlistId } = await ownedPlaylist(u.email, u.password, 'PLint2');
    const { error } = await client.from('videos')
      .insert({ playlist_id: playlistId, owner_id: userId, video_id: 'v0', position: 0, data: { title: 'x' } });
    expect(error).not.toBeNull();
  });

  it('allows a full reorder within one transaction (deferrable position constraint)', async () => {
    const u = await newUser();
    const { client, userId, playlistId } = await ownedPlaylist(u.email, u.password, 'PLreorder');
    const mk = (id: string, pos: number) =>
      ({ playlist_id: playlistId, owner_id: userId, video_id: id, position: pos, data: { id } });
    await client.from('videos').insert([mk('A', 0), mk('B', 1), mk('C', 2)]);

    // Reverse to [C,B,A] via an RPC that upserts all three in one transaction.
    // Plain multi-statement upsert over PostgREST is not transactional, so reorder
    // uses a SECURITY INVOKER function that runs under the caller's RLS. Implementer:
    // add supabase/migrations/0005_reorder_helper.sql defining reorder_videos(jsonb)
    // as SECURITY INVOKER; it performs the updates inside one transaction so the
    // deferred unique constraint is checked at COMMIT.
    const { error } = await client.rpc('reorder_videos', {
      items: [{ video_id: 'C', position: 0 }, { video_id: 'B', position: 1 }, { video_id: 'A', position: 2 }],
      p_playlist_id: playlistId,
    });
    expect(error).toBeNull();

    const { data } = await client.from('videos').select('video_id,position')
      .eq('playlist_id', playlistId).order('position');
    expect(data).toEqual([
      { video_id: 'C', position: 0 }, { video_id: 'B', position: 1 }, { video_id: 'A', position: 2 },
    ]);
  });
});

describe('anonymous isolation', () => {
  it('an anon session sees only its own rows', async () => {
    const { client, userId } = await anonSession();
    await client.from('playlists')
      .insert({ owner_id: userId, playlist_key: 'PLanon', playlist_url: 'https://youtube.com/playlist?list=PLanon' });
    const mine = await client.from('playlists').select('owner_id');
    expect(mine.data).toEqual([{ owner_id: userId }]);

    const other = await newUser();
    const O = await ownedPlaylist(other.email, other.password, 'PLother');
    const cross = await client.from('playlists').select('*').eq('id', O.playlistId);
    expect(cross.data).toEqual([]);
  });
});
```

- [ ] **Step 2: Add the transactional reorder helper migration**

```sql
-- supabase/migrations/0005_reorder_helper.sql
-- SECURITY INVOKER: runs under the caller's RLS (owner-only). One transaction so the
-- DEFERRABLE INITIALLY DEFERRED position constraint is validated at COMMIT.
create function reorder_videos(p_playlist_id uuid, items jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
declare it jsonb;
begin
  -- Codex H7: explicit ownership guard (defense-in-depth over the caller-RLS no-op).
  -- A user who does not own the playlist (or whose RLS hides it) sees no matching row.
  if not exists (
    select 1 from playlists
     where id = p_playlist_id
       and (owner_id = auth.uid() or auth.role() = 'service_role')
  ) then
    raise exception 'not authorized for playlist %', p_playlist_id;
  end if;

  for it in select * from jsonb_array_elements(items) loop
    update videos set position = (it->>'position')::int, updated_at = now()
     where playlist_id = p_playlist_id and video_id = it->>'video_id';
  end loop;
end $$;

-- Codex H7: not callable by anon/PUBLIC by default; only authenticated + service_role.
revoke all on function reorder_videos(uuid, jsonb) from public, anon;
grant execute on function reorder_videos(uuid, jsonb) to authenticated, service_role;
```
> `SECURITY INVOKER` is deliberate — the caller's RLS still applies, so this helper cannot cross tenants. The explicit `owner_id = auth.uid()` guard + the `revoke`/`grant` are defense-in-depth so it never silently no-ops for a non-owner or runs for an anonymous/PUBLIC role. It exists only to give `writeIndex`-style reordering a single transaction boundary (PostgREST batches are not transactional). The 1C `writeIndex` will use the same pattern.

- [ ] **Step 3: Run + tsc + commit**

```bash
npx supabase db reset
npx jest --config jest.integration.config.ts tests/integration/integrity.test.ts   # PASS
npx tsc --noEmit
git add tests/integration/integrity.test.ts supabase/migrations/0005_reorder_helper.sql
git commit -m "test(rls): integrity CHECK, deferrable reorder, anonymous isolation"
```

---

## Task 10: Auth app wiring — middleware + OAuth callback

**Files:**
- Create: `middleware.ts`
- Create: `app/auth/callback/route.ts`
- Test: `tests/lib/supabase/route-categories.test.ts` (unit test for the category classifier)

**Interfaces:**
- Consumes: `createServerSupabase` (Task 5).
- Produces: session refresh on every request; `/auth/callback` exchanges an OAuth code for a session.

> **Read first (per `AGENTS.md`):** before writing `middleware.ts` or the route handler, read the middleware and route-handler guides under `node_modules/next/dist/docs/`. This repo's Next.js has breaking changes from training data — confirm the `middleware` signature, `NextResponse` cookie API, and route-handler `GET` export shape against the installed version.
>
> **Scope note (Codex B1):** the live Google OAuth redirect needs a hosted project with Google credentials (spec §2) and cannot run on the local stack. It is covered in 1B by three complementary checks, with only the browser round-trip deferred: (1) the **provisioning trigger test** (Task 4) already proves that *any* `auth.users` insert — Google included — yields exactly one `profiles` row; (2) a **mocked callback unit test** (below) proves the code-exchange + error branches; (3) the **live Google round-trip** is a documented deploy-time manual check. See the decision note presented to the user before implementation.

- [ ] **Step 1: Write the failing classifier + provisioning-decision tests**

```typescript
// tests/lib/supabase/route-categories.test.ts
import { classifyRoute, needsAnonProvision } from '@/lib/supabase/route-categories';

describe('route categories', () => {
  it('marketing paths are public', () => {
    expect(classifyRoute('/')).toBe('public');
    expect(classifyRoute('/about')).toBe('public');
  });
  it('the guest try-it path is anon-allowed', () => {
    expect(classifyRoute('/try')).toBe('anon-allowed');
    expect(classifyRoute('/try/abc')).toBe('anon-allowed');
  });
  it('library paths require authentication', () => {
    expect(classifyRoute('/library')).toBe('authenticated');
    expect(classifyRoute('/library/playlists/abc')).toBe('authenticated');
  });
});

describe('needsAnonProvision (Codex H1)', () => {
  it('true only on anon-allowed with no existing user', () => {
    expect(needsAnonProvision('anon-allowed', false)).toBe(true);
    expect(needsAnonProvision('anon-allowed', true)).toBe(false);   // already has a session
    expect(needsAnonProvision('public', false)).toBe(false);
    expect(needsAnonProvision('authenticated', false)).toBe(false); // redirect, don't provision
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest tests/lib/supabase/route-categories.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the classifier + provisioning decision**

```typescript
// lib/supabase/route-categories.ts
export type RouteCategory = 'public' | 'anon-allowed' | 'authenticated';

const PUBLIC = ['/', '/about'];
const ANON_ALLOWED = ['/try'];

export function classifyRoute(pathname: string): RouteCategory {
  if (PUBLIC.includes(pathname)) return 'public';
  if (ANON_ALLOWED.some((p) => pathname === p || pathname.startsWith(p + '/'))) return 'anon-allowed';
  return 'authenticated';
}

/** Codex H1: an anon-allowed route auto-provisions an anonymous session on first use. */
export function needsAnonProvision(category: RouteCategory, hasUser: boolean): boolean {
  return category === 'anon-allowed' && !hasUser;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx jest tests/lib/supabase/route-categories.test.ts`
Expected: PASS.

- [ ] **Step 5: Write the mocked callback error-branch test (Codex M4/B1)**

```typescript
// tests/lib/supabase/auth-callback.test.ts
const exchange = jest.fn();
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: () => ({ auth: { exchangeCodeForSession: exchange } }),
}));
jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

import { GET } from '@/app/auth/callback/route';

function req(url: string) { return { nextUrl: new URL(url), url } as never; }

describe('OAuth callback', () => {
  afterEach(() => exchange.mockReset());

  it('redirects to next on a successful code exchange', async () => {
    exchange.mockResolvedValue({ error: null });
    const res = await GET(req('http://localhost/auth/callback?code=abc&next=/library'));
    expect(exchange).toHaveBeenCalledWith('abc');
    expect(res.headers.get('location')).toContain('/library');
  });

  it('redirects to an auth-error route when the exchange fails (Codex M4)', async () => {
    exchange.mockResolvedValue({ error: { message: 'bad code' } });
    const res = await GET(req('http://localhost/auth/callback?code=abc'));
    expect(res.headers.get('location')).toContain('/auth/auth-error');
  });

  it('redirects to auth-error when no code is present', async () => {
    const res = await GET(req('http://localhost/auth/callback'));
    expect(exchange).not.toHaveBeenCalled();
    expect(res.headers.get('location')).toContain('/auth/auth-error');
  });
});
```

- [ ] **Step 6: Implement middleware + callback (after reading the Next docs)**

```typescript
// middleware.ts  — confirm signature/cookie API against node_modules/next/dist/docs/
import { NextResponse, type NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { getSupabaseEnv } from '@/lib/supabase/env';
import { classifyRoute, needsAnonProvision } from '@/lib/supabase/route-categories';

export async function middleware(request: NextRequest) {
  const response = NextResponse.next({ request });
  const { url, anonKey } = getSupabaseEnv();
  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (list) => list.forEach(({ name, value, options }) => response.cookies.set(name, value, options)),
    },
  });
  const { data: { user } } = await supabase.auth.getUser();     // refreshes the session
  const category = classifyRoute(request.nextUrl.pathname);

  // Codex H1: auto-provision an anonymous session on first visit to an anon-allowed route.
  if (needsAnonProvision(category, !!user)) {
    await supabase.auth.signInAnonymously();                    // sets cookies on `response`
    return response;
  }

  if (category === 'authenticated' && !user) {
    const redirect = request.nextUrl.clone();
    redirect.pathname = '/';
    return NextResponse.redirect(redirect);
  }
  return response;
}

export const config = { matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'] };
```

```typescript
// app/auth/callback/route.ts — confirm route-handler shape against the Next docs
import { NextResponse, type NextRequest } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase } from '@/lib/supabase/server';

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get('code');
  const next = request.nextUrl.searchParams.get('next') ?? '/library';
  if (code) {
    const cookieStore = await cookies();
    const supabase = createServerSupabase(cookieStore as never);
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(new URL(next, request.url));
  }
  // Codex M4: no code, or a failed exchange, must NOT redirect as if successful.
  return NextResponse.redirect(new URL('/auth/auth-error', request.url));
}
```

- [ ] **Step 7: Full suite + tsc + commit**

```bash
npx jest                       # full unit suite green (integration excluded by default)
npx tsc --noEmit               # clean — the real type gate
git add middleware.ts app/auth/callback/route.ts lib/supabase/route-categories.ts \
        tests/lib/supabase/route-categories.test.ts tests/lib/supabase/auth-callback.test.ts
git commit -m "feat(auth): middleware (refresh + anon auto-provision) + OAuth callback with error branch"
```

---

## Post-implementation verification (Phase 4)

Before the final review, from a clean checkout with Docker up:

```bash
npx supabase start
npx supabase status -o env > .env.test.local
npx supabase db reset                    # all migrations apply cleanly
npm test                                 # unit suite green; integration NOT run here
npm run test:integration                 # full RLS suite green (stack up)
npm run check:confinement                # service_role unreachable from app/**
npx tsc --noEmit                         # clean
```

Success criteria (spec §8): migrations reproduce the schema; Google + anonymous sign-in each yield a session + `profiles` row (Google verified at deploy, anon verified locally); all §7 tests pass; no user-facing path imports the service client; `tsc` clean; existing local-tool paths unchanged.

## Known deferrals (tracked, not silently dropped)

- **Async-ify the `MetadataStore` seam** — prerequisite for **1C**, not 1B (spec §1). Sync interface cannot back a networked adapter.
- **Live Google OAuth browser round-trip only** — needs a hosted project + Google credentials; the *provisioning* (Task 4 trigger test) and the *callback code-exchange + error branches* (Task 10 mocked test) ARE covered in 1B; only the real Google redirect is a documented deploy-time manual check (Codex B1 resolution).
- **Anonymous retention/TTL cleanup** — a pre-public gate (spec §4); not built in 1B.
- **`exec_sql` test RPC / typed catalog views** — reviewer's choice (Task 7); test-only, service_role-gated, with a negative anon/authenticated test (Task 7 Step 5).
- **Middleware runtime behavior** (session refresh, anon auto-provision redirect) is unit-tested at the decision level (`needsAnonProvision`); full edge-runtime behavior is an E2E/deploy verification.

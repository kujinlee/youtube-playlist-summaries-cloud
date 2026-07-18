import { promises as fs } from 'fs';
import path from 'path';
import { createClient, type SupabaseClient, type Session } from '@supabase/supabase-js';

export class NoSessionError extends Error {
  constructor() { super('Not signed in to cloud. Run: cloud-sync login'); this.name = 'NoSessionError'; }
}

export interface TokenStore {
  read(): Promise<string | null>;
  write(token: string): Promise<void>;
  clear(): Promise<void>;
}

function anonClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) throw new Error('NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY not set');
  return createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } });
}

/** Fail-closed check on the token's parent directory: reject group/other-writable, require
 *  ownership by the current uid where the platform exposes it (§6). */
async function assertSafeParent(file: string): Promise<void> {
  const dir = path.dirname(file);
  const st = await fs.stat(dir); // throws ENOENT if the dir does not exist
  if (st.mode & 0o022) {
    throw new Error(`refusing: token dir ${dir} is group/other-writable (mode ${(st.mode & 0o777).toString(8)}); tighten to 0700`);
  }
  if (typeof process.getuid === 'function' && st.uid !== process.getuid()) {
    throw new Error(`refusing: token dir ${dir} not owned by the current user`);
  }
}

export function makeFileTokenStore(file: string): TokenStore {
  return {
    async read() {
      try {
        await assertSafeParent(file);
      } catch (e: any) {
        if (e?.code === 'ENOENT') return null; // no dir yet → no token
        throw e;                               // broad/foreign parent → fail closed
      }
      try {
        const st = await fs.stat(file);
        if (st.mode & 0o077) throw new Error(`refusing to read ${file}: permission too broad (mode ${(st.mode & 0o777).toString(8)})`);
        return (await fs.readFile(file, 'utf8')).trim() || null;
      } catch (e: any) {
        if (e?.code === 'ENOENT') return null;
        throw e;
      }
    },
    async write(token: string) {
      const dir = path.dirname(file);
      // Check an EXISTING parent BEFORE touching it — a chmod-then-check would launder a
      // pre-existing group/world-writable or foreign-owned dir (round-2 H2). Only self-heal
      // a dir we create ourselves.
      let exists = true;
      try { await assertSafeParent(file); }
      catch (e: any) { if (e?.code === 'ENOENT') exists = false; else throw e; } // unsafe existing → throw
      if (!exists) {
        await fs.mkdir(dir, { recursive: true, mode: 0o700 });
        await fs.chmod(dir, 0o700);
        await assertSafeParent(file); // verify the just-created dir is safe
      }
      await fs.writeFile(file, token, { mode: 0o600 });
      await fs.chmod(file, 0o600);
    },
    async clear() { await fs.rm(file, { force: true }); },
  };
}

function defaultTokenPath(): string {
  const home = process.env.HOME || process.env.USERPROFILE || '.';
  return path.join(home, '.config', 'youtube-playlist-summaries', 'cloud-sync-token');
}
export const fileTokenStore = makeFileTokenStore(defaultTokenPath());

export async function signIn(email: string, password: string, store: TokenStore = fileTokenStore): Promise<void> {
  const c = anonClient();
  const { data, error } = await c.auth.signInWithPassword({ email, password });
  if (error || !data.session) throw new Error(`sign-in failed: ${error?.message ?? 'no session'}`);
  await store.write(data.session.refresh_token);
}

export async function signOut(store: TokenStore = fileTokenStore): Promise<void> {
  await store.clear();
}

export async function loadSession(store: TokenStore = fileTokenStore): Promise<Session | null> {
  const refresh = await store.read();
  if (!refresh) return null;
  const c = anonClient();
  const { data, error } = await c.auth.refreshSession({ refresh_token: refresh });
  if (error || !data.session) return null;
  await store.write(data.session.refresh_token); // rotate
  return data.session;
}

export async function getAuthedClient(store: TokenStore = fileTokenStore): Promise<SupabaseClient> {
  const session = await loadSession(store);
  if (!session) throw new NoSessionError();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  return createClient(url, anon, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${session.access_token}` } },
  });
}

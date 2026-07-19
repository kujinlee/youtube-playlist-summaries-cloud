// scripts/cloud-sync.ts
//
// Stage 3 Cloud Sync (§9) — the local CLI entrypoint. Wires the authenticated USER-session
// Supabase client into runSync() so a developer/operator can pull cloud changes into their local
// replica (and vice versa) without ever touching the service-role key. `login`/`logout` manage a
// long-lived refresh token via lib/cloud-sync/auth's file-backed TokenStore; `sync` (the default)
// reconciles every union playlist, or one via `--playlist <key>`.
//
// Data-root convention: this project's LOCAL playlist roots are NOT an env var — they are
// lib/settings-store.ts's settings.json (`baseOutputFolder` when set, the parent directory that
// holds every playlist subfolder; falling back to the single-playlist `outputFolder`, which itself
// falls back to the OUTPUT_FOLDER env var when settings.json is absent). This mirrors exactly what
// app/api/resolve-folder/route.ts reads, and what lib/cloud-sync/registry.ts's
// discoverLocalPlaylists() expects: a root whose subdirectories are playlist folders. An optional
// CLOUD_SYNC_DATA_ROOTS override (colon-separated) is supported for scripting/testing convenience.
import { getAuthedClient, signIn, signOut, NoSessionError } from '@/lib/cloud-sync/auth';
import { runSync, type SyncDeps } from '@/lib/cloud-sync/sync-run';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { readSettings } from '@/lib/settings-store';

export interface ParsedArgs { cmd: 'sync' | 'login' | 'logout'; playlistKey?: string; }

export function parseArgs(argv: string[]): ParsedArgs {
  if (argv[0] === 'login') return { cmd: 'login' };
  if (argv[0] === 'logout') return { cmd: 'logout' };
  const i = argv.indexOf('--playlist');
  return i >= 0 && argv[i + 1] ? { cmd: 'sync', playlistKey: argv[i + 1] } : { cmd: 'sync' };
}

/** Real local data-root convention (see file header): settings.json's baseOutputFolder/
 *  outputFolder — NOT a DATA_ROOT env var, which does not exist anywhere else in this codebase. */
function resolveDataRoots(): string[] {
  const override = process.env.CLOUD_SYNC_DATA_ROOTS;
  if (override) return override.split(':').filter(Boolean);
  const settings = readSettings();
  const root = settings.baseOutputFolder || settings.outputFolder;
  return root ? [root] : [];
}

export async function main(argv: string[]): Promise<number> {
  const args = parseArgs(argv);
  if (args.cmd === 'login') {
    const [email, password] = [process.env.CLOUD_SYNC_EMAIL, process.env.CLOUD_SYNC_PASSWORD];
    if (!email || !password) { console.error('Set CLOUD_SYNC_EMAIL and CLOUD_SYNC_PASSWORD to log in.'); return 1; }
    await signIn(email, password); console.log('Signed in.'); return 0;
  }
  if (args.cmd === 'logout') { await signOut(); console.log('Signed out.'); return 0; }

  let client;
  try { client = await getAuthedClient(); }
  catch (e) { if (e instanceof NoSessionError) { console.error(e.message); return 1; } throw e; }

  const { data } = await client.auth.getUser();
  const ownerId = data.user!.id;
  const dataRoots = resolveDataRoots();

  const deps: SyncDeps = {
    local: localMetadataStore,
    cloud: new SupabaseMetadataStore(client),
    localBlob: localBlobStore,
    cloudBlob: new SupabaseBlobStore(client, ARTIFACTS_BUCKET),
    dataRoots, ownerId,
  };
  const report = await runSync(deps, args.playlistKey ? { playlistKey: args.playlistKey } : {});
  console.log(JSON.stringify(report, null, 2));
  return report.errors.length ? 2 : 0;
}

if (require.main === module) {
  main(process.argv.slice(2)).then((code) => process.exit(code)).catch((e) => { console.error(e); process.exit(1); });
}

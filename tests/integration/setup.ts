import fs from 'fs';
import path from 'path';

const envPath = path.join(process.cwd(), '.env.test.local');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
    // STRIP SURROUNDING QUOTES. `supabase status -o env` emits `API_URL="http://127.0.0.1:54321"`,
    // and keeping the quotes yields a URL of `"http://…"` which @supabase/supabase-js rejects with
    // `Invalid supabaseUrl`. This was LATENT for the jest suites and invisible: next/jest loads
    // .env.local (unquoted) before this file runs, and the assignment below is gap-filling only
    // (`!process.env[...]`), so the quoted values never won and never had to be correct. It
    // surfaced the moment a NON-jest runner reused this loader — Playwright, 2026-08-13, which has
    // no next/jest and so fell straight into it.
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^"(.*)"$/, '$1');
  }
}

// `supabase status -o env` emits API_URL / ANON_KEY / SERVICE_ROLE_KEY, but the clients
// read the NEXT_PUBLIC_SUPABASE_* / SUPABASE_SERVICE_ROLE_KEY names. Alias the raw names
// so the simple documented command (`supabase status -o env > .env.test.local`) works
// without --override-name flags.
process.env.NEXT_PUBLIC_SUPABASE_URL ||= process.env.API_URL ?? '';
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||= process.env.ANON_KEY ?? '';
process.env.SUPABASE_SERVICE_ROLE_KEY ||= process.env.SERVICE_ROLE_KEY ?? '';

if (
  !process.env.NEXT_PUBLIC_SUPABASE_URL ||
  !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  !process.env.SUPABASE_SERVICE_ROLE_KEY
) {
  throw new Error(
    'Integration suite requires a running local Supabase stack.\n' +
    'Run: npx supabase start && npx supabase status -o env > .env.test.local',
  );
}

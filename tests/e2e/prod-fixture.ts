/**
 * Shared reads for the M3.1-B production smoke. NOTHING HERE WRITES ANYTHING, ANYWHERE.
 *
 * Spec: docs/superpowers/specs/2026-08-19-prod-readonly-smoke-design.md
 *
 * The one rule this file exists to keep: every value the smoke asserts on is DERIVED AT RUN TIME
 * from production, never committed. A hard-coded playlist id goes red the day it is deleted, and a
 * gate that goes red for a reason the reader learns to dismiss has stopped being a gate.
 */
import fs from 'node:fs';
import path from 'node:path';
import { Client } from 'pg';

export const PROD_URL = 'https://youtube-playlist-summaries.fly.dev';
export const FLY_APP = 'youtube-playlist-summaries';

/** Supabase's PRIVATE root CA, vendored so the pooler connection can be verified rather than
 *  trusted blindly. Public certificate, not a secret. Expires 2031-04-26. */
export const CA_FILE = path.join(__dirname, 'supabase-prod-ca-2021.crt');

export const AUTH_FILE = path.join(process.cwd(), 'playwright/.auth/prod.json');
export const FIXTURE_FILE = path.join(process.cwd(), 'playwright/.auth/prod-fixture.json');

/** Loads `.env.local` for CLAUDE_RO_DATABASE_URL only.
 *
 *  ⚠ `.env.local` is the LOCAL dev environment — measured 2026-08-19, its
 *  NEXT_PUBLIC_SUPABASE_URL is `127.0.0.1:54321`. Only the read-only URL in it points at prod. So
 *  this loader deliberately reads ONE name rather than sourcing the file into the process, which
 *  would silently aim anything else at localhost.
 *
 *  Quote-stripping is copied from tests/integration/setup.ts:14 for the reason recorded there —
 *  `supabase status -o env` emits quoted values and a non-jest runner has no next/jest to mask it.
 */
export function readOnlyDatabaseUrl(): string | null {
  if (process.env.CLAUDE_RO_DATABASE_URL) return process.env.CLAUDE_RO_DATABASE_URL;
  const envPath = path.join(process.cwd(), '.env.local');
  if (!fs.existsSync(envPath)) return null;
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^CLAUDE_RO_DATABASE_URL=(.*)$/);
    if (m) return m[1].replace(/^"(.*)"$/, '$1').trim() || null;
  }
  return null;
}

async function withClient<T>(fn: (c: Client) => Promise<T>): Promise<T> {
  const connectionString = readOnlyDatabaseUrl();
  if (!connectionString) throw new Error('CLAUDE_RO_DATABASE_URL is not set (checked env and .env.local)');
  const c = new Client({
    // ⚠ `sslmode=` IS STRIPPED, AND THE ORDER OF PRECEDENCE IS THE WHOLE REASON. Measured
    // 2026-08-19: with `sslmode=require` left in the URL, pg's connection-string parsing builds its
    // own `ssl` and OVERRIDES the object below — the pinned CA was passed and silently ignored,
    // failing with the same error as before. Worse, pg 8 maps `require` to a NON-VERIFYING
    // connection (its own deprecation warning says so), so the credential URL as supplied was
    // never verifying the server at all. Stripping the parameter is what lets the pin take effect.
    connectionString: connectionString.replace(/([?&])sslmode=[^&]*(&|$)/, (_m, p, tail) => (tail === '&' ? p : '')),
    application_name: 'm3.1b-prod-smoke',
    // ⚠ MEASURED 2026-08-19: without an explicit CA, every read fails with "self-signed
    // certificate in certificate chain". The `psql` path used during design did not hit this,
    // which is why it was not foreseen.
    //
    // The chain was inspected rather than guessed at:
    //     depth 0  CN=*.pooler.supabase.com
    //     depth 1  CN=Supabase Intermediate 2021 CA
    //     depth 2  CN=Supabase Root 2021 CA   (self-signed — a PRIVATE CA, by design)
    //
    // So Node is right to reject it: that root is not in any public trust store. The fix is to PIN
    // that one root, NOT to turn verification off. `rejectUnauthorized: false` was written here
    // first and is the wrong answer — it would accept any certificate at all, including one
    // presented by a machine-in-the-middle, and this connection carries a database credential.
    //
    // The pinned root is fetched from Supabase's published download over PUBLIC TLS and vendored
    // beside this file, so trust is anchored in the public web PKI rather than in whatever the
    // pooler happened to present the first time we looked (trust-on-first-use would be circular).
    //     https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt
    //     sha256 80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA
    //
    // WHEN THIS ROOT EXPIRES the connection fails loudly with a certificate error, which is the
    // correct behaviour for a pin — re-download and re-verify rather than reaching for a bypass.
    ssl: { ca: fs.readFileSync(CA_FILE, 'utf8'), rejectUnauthorized: true },
  });
  await c.connect();
  try {
    // Belt to the credential's braces. `claude_ro` was measured to hold ZERO write grants across
    // all 12 public tables (2026-08-19), but a grant is a property of the ROLE and can be changed
    // by someone else; this is a property of the SESSION and is set by us, here, every time.
    await c.query('set session characteristics as transaction read only');
    return await fn(c);
  } finally {
    await c.end();
  }
}

export type Ledger = { auditMaxId: number; centsTotal: number };

export async function readLedger(): Promise<Ledger> {
  return withClient(async (c) => {
    const r = await c.query<{ audit_max: string | null; cents: string | null }>(
      `select (select max(id) from public.ledger_audit)                                  as audit_max,
              (select sum(reserved_cents + actual_cents) from public.spend_ledger)        as cents`,
    );
    return {
      auditMaxId: Number(r.rows[0]?.audit_max ?? 0),
      centsTotal: Number(r.rows[0]?.cents ?? 0),
    };
  });
}

export type Anchor = {
  playlistId: string;
  playlistTitle: string;
  videoId: string;
  /** First non-empty line of the summary markdown, trimmed — the needle check 4 looks for. */
  summaryNeedle: string;
};

/** The newest video that ALREADY has a summary, plus its playlist. Ordered deterministically so a
 *  failure is reproducible; `limit 1` because the smoke needs one real subject, not a survey. */
export async function readAnchor(): Promise<Anchor | null> {
  return withClient(async (c) => {
    const r = await c.query<{ id: string; playlist_title: string; video_id: string; md: string }>(
      `select p.id, p.playlist_title, v.video_id, v.data->>'summaryMd' as md
         from public.videos v
         join public.playlists p on p.id = v.playlist_id
        where coalesce(v.data->>'summaryMd', '') <> ''
          and coalesce(p.playlist_title, '')     <> ''
        order by v.updated_at desc, v.video_id
        limit 1`,
    );
    const row = r.rows[0];
    if (!row) return null;
    const needle = (row.md.split('\n').find((l) => l.trim() !== '') ?? '').trim();
    return {
      playlistId: row.id,
      playlistTitle: row.playlist_title,
      videoId: row.video_id,
      summaryNeedle: needle,
    };
  });
}

export type SessionState = 'missing' | 'expired' | 'live';

/** Is the captured session usable — asked BEFORE any request reaches prod.
 *
 *  ⭐ THIS IS THE DISAMBIGUATOR THE WHOLE SUITE IS BUILT AROUND. "Bounced to /login" means either
 *  the session expired (could not run) or production authentication is broken (a finding). Reported
 *  as the same red, the first meaning teaches the reader to dismiss the second — the same defect
 *  class as a storage `null` that meant "denied" being read as "missing". Checking expiry before
 *  navigating separates them by construction rather than by interpretation.
 *
 *  Bound, stated rather than hidden: Supabase refreshes sessions, so a cookie that looks live can
 *  still be dead if its refresh token was revoked server-side. That case surfaces as a check-2
 *  failure, not as NOT RUN. See spec §7.1.
 */
export function sessionState(now = Date.now()): SessionState {
  if (!fs.existsSync(AUTH_FILE)) return 'missing';
  let parsed: { cookies?: Array<{ name: string; expires?: number }> };
  try {
    parsed = JSON.parse(fs.readFileSync(AUTH_FILE, 'utf8'));
  } catch {
    return 'missing';                       // unreadable is not "live"; fail toward NOT RUN
  }
  const cookies = parsed.cookies ?? [];
  if (cookies.length === 0) return 'missing';
  // `expires` is unix SECONDS, and -1 means a session cookie (no stored expiry). A session cookie
  // cannot be shown to be expired, so it counts as live and check 2 adjudicates.
  const live = cookies.some((c) => c.expires === undefined || c.expires === -1 || c.expires * 1000 > now);
  return live ? 'live' : 'expired';
}

export type Fixture = {
  ledger: Ledger | null;
  ledgerError: string | null;
  anchor: Anchor | null;
  anchorError: string | null;
  session: SessionState;
  release: string | null;
  releaseError: string | null;
};

export function readFixture(): Fixture {
  if (!fs.existsSync(FIXTURE_FILE)) {
    throw new Error(
      `No prod-smoke fixture at ${FIXTURE_FILE}.\n` +
      'globalSetup writes it. Run the whole config: npm run test:e2e:prod',
    );
  }
  return JSON.parse(fs.readFileSync(FIXTURE_FILE, 'utf8')) as Fixture;
}

/** The message every NOT-RUN failure carries. Deliberately one function, so the phrase is
 *  identical everywhere and a reader grepping for it finds every instance. */
export function notRun(what: string, why: string, fix: string): Error {
  return new Error(
    `TREAT THIS AS NOT RUN — ${what}\n` +
    `  why: ${why}\n` +
    `  fix: ${fix}\n` +
    'This is red because a check that cannot reach what it measures must never report green.',
  );
}

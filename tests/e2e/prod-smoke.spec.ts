/**
 * M3.1-B — the read-only production smoke. Six checks, all free, against the DEPLOYED application.
 *
 *     npm run test:e2e:prod
 *
 * Spec: docs/superpowers/specs/2026-08-19-prod-readonly-smoke-design.md
 *
 * WHAT THIS IS FOR, stated because it is easy to mistake for a second copy of M3.1-A. A catches
 * CODE regressions and runs unattended against a LOCAL stack — so it would stay green while
 * production was entirely broken. This catches the class A structurally cannot reach: the
 * deployment being wrong while the code is right. A secret missing on Fly, an env var set
 * differently, a storage grant that differs between local and hosted.
 *
 * NOTHING HERE WRITES, INGESTS, RENDERS A MAGAZINE, OR SIGNS OUT.
 * The last one is the trap worth remembering. cloud-journey.spec.ts:212 signs out and is right to —
 * copied here it would invalidate the captured session on EVERY run, turning an occasional
 * re-sign-in into a per-run chore and quietly killing the gate.
 *
 * EVERY CHECK EITHER PASSES, FAILS, OR SAYS "TREAT THIS AS NOT RUN" — never skips. A skipped check
 * reads as an absent problem; a red one that names its own blindness does not.
 */
import { test, expect, type Browser } from '@playwright/test';
import { AUTH_FILE, PROD_URL, notRun, readFixture, type Fixture } from './prod-fixture';

let _fx: Fixture | null = null;
// Lazily, never at module scope: Playwright collects spec files BEFORE globalSetup runs, so a
// top-level read fails with ENOENT on a clean checkout and looks like a missing file rather than
// an ordering mistake (the same trap cloud-journey.spec.ts:62-66 records).
const fx = () => (_fx ??= readFixture());

/** A context carrying the captured session — built by hand rather than via the project's
 *  `storageState`, because Playwright loads that when the CONTEXT is created, i.e. before any test
 *  body runs. That would turn "no session captured yet" into an unreadable framework error and
 *  take checks 1, 5 and 6 down with it, when those need no session at all. */
async function signedIn(browser: Browser) {
  const state = fx().session;
  if (state !== 'live') {
    throw notRun(
      'this check needs the captured production session',
      state === 'missing' ? `no session file at ${AUTH_FILE}` : 'every cookie in the session file has expired',
      'npm run prod:session   (signs you in via Google in a real browser, once)',
    );
  }
  return browser.newContext({ storageState: AUTH_FILE, baseURL: PROD_URL });
}

function anchorOrNotRun() {
  const { anchor, anchorError } = fx();
  if (!anchor) {
    throw notRun(
      'this check needs a real production video to anchor on',
      anchorError ?? 'no anchor recorded',
      'ensure CLAUDE_RO_DATABASE_URL is set and at least one video has a summary',
    );
  }
  return anchor;
}

// ⚠ NOT `describe.serial`, and that is a correction rather than an omission. The first version of
// this file copied the A-suite's `.serial`, and the very first run proved it wrong: with no session
// captured, check 2 failed as NOT RUN and Playwright then abandoned checks 3-6 — including 5 and 6,
// which need no session and were the whole reason the suite is useful before a session exists.
// `.serial` aborts the remainder on the first failure, so it silently converts "three checks could
// not run" into "five checks told you nothing". The checks here are genuinely independent: each
// builds its own context and does its own navigation.
test.describe('M3.1-B · production read-only smoke', () => {
  test('1 · the run names the release it tested', async () => {
    const { release, releaseError } = fx();
    if (release === null && releaseError?.startsWith('flyctl unavailable')) {
      throw notRun('the live release could not be identified', releaseError,
        'install flyctl and `flyctl auth login`, or run this from a machine that has it');
    }
    // FAILS (not NOT RUN) when flyctl answered and named no complete release — that is a finding
    // about the deployment, not about the instrument. The two must not print the same verdict.
    expect(releaseError, 'flyctl answered but named no complete release').toBeNull();
    expect(release, 'live release').toMatch(/^v\d+$/);
    console.log(`   ✓ verified against release ${release}`);
  });

  test('2 · the deployed root serves the CLOUD app to a signed-in user', async ({ browser }) => {
    // Not cosmetic. This dispatch broke on the first deploy: `/` was prerendered with
    // STORAGE_BACKEND absent, so a signed-in cloud user was served the LOCAL app and its
    // filesystem ingest, which 400s in a container (cloud-journey.spec.ts:71-74).
    //
    // Reaching here at all means P1 said the session is live, so a bounce to /login is a FINDING
    // about production authentication — not an expired cookie. That separation is the whole point
    // of the pre-flight.
    const ctx = await signedIn(browser);
    try {
      const page = await ctx.newPage();
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await expect(page, 'bounced to /login despite a live session — prod auth, not expiry').not.toHaveURL(/\/login/);
      await expect(page.getByRole('navigation', { name: /playlists/i })).toBeVisible();
    } finally { await ctx.close(); }
  });

  test('3 · the sidebar lists the playlist the DATABASE says exists', async ({ browser }) => {
    // The check that separates "the app renders" from "the app renders YOUR data". A shell that
    // paints an empty sidebar passes check 2 and fails this one.
    const anchor = anchorOrNotRun();
    const ctx = await signedIn(browser);
    try {
      const page = await ctx.newPage();
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await expect(
        page.getByRole('link', { name: anchor.playlistTitle }),
        `prod holds a playlist titled "${anchor.playlistTitle}" that the sidebar does not show`,
      ).toBeVisible();
    } finally { await ctx.close(); }
  });

  test('4 · a summary downloads, and the bytes are the summary', async ({ browser }) => {
    // FREE BY CONTRACT, not by luck: format=md returns before resolveAndParse and therefore cannot
    // reach reserve_serve_model (app/api/html/[id]/route.ts:75-82, comment "D4 money invariant").
    //
    // It also reaches further than it looks. These bytes come out of Supabase STORAGE, so a pass
    // proves the bucket, its grants and the storage credentials are right in the DEPLOYED
    // environment — a class the local suite cannot test.
    //
    // ⚠ THE SPEC'S §7.5 COUPLING IS NOW RESOLVED — AND THE REAL DEFECT WAS MORE BASIC THAN FLAGGED.
    // The spec warned that the needle came from a COLUMN while the route serves bytes from STORAGE,
    // and that the two might differ. Measured 2026-08-21 on the first authenticated run: they are
    // not two versions of the same thing at all. `data->>'summaryMd'` is the blob's KEY
    // (`003_돈-버는-…-다이제스트.md`), so check 4 was looking for a FILENAME inside a document.
    // The needle is now `data->>'title'`, which was OBSERVED in the response (6,010 bytes, HTTP 200)
    // rather than inferred from a column name.
    const anchor = anchorOrNotRun();
    const ctx = await signedIn(browser);
    try {
      const res = await ctx.request.get(
        `${PROD_URL}/api/html/${anchor.videoId}` +
        `?playlist=${anchor.playlistId}&type=summary&format=md&download=1`,
      );
      expect(res.status(), 'markdown download status').toBe(200);
      expect(res.headers()['content-disposition'] ?? '', 'download disposition').toMatch(/attachment/i);
      const body = await res.text();
      // A size floor as well as a match: a 200 carrying an error envelope is short, and
      // `{"error":"not found"}` would satisfy neither, but the floor states the intent plainly.
      expect(body.length, 'served document is implausibly small for a summary').toBeGreaterThan(500);
      expect(body, "served markdown is not this video's document")
        .toContain(anchor.videoTitle);
    } finally { await ctx.close(); }
  });

  test('5 · the locks that make this test semi-manual are still on', async ({ request }) => {
    // A DECISION BECOMES A GATE BY ASSERTING THE WORLD STILL MATCHES IT. Both of these are settings
    // rather than code — changeable with no commit, no diff and no review — and the entire design
    // of M3.1-B rests on them. docs/reviews/task-7-prod-auth-verification.md:7 recorded the email
    // provider as OFF on 2026-07-24 and nothing has re-checked it since.

    // 5a — the dev back door. Needs no key at all.
    const devLogin = await request.get(`${PROD_URL}/dev-login`, { maxRedirects: 0 });
    expect(devLogin.status(), '/dev-login must be 404 in production').toBe(404);

    // 5b — the email/password provider. The anon key and Supabase URL are DERIVED from the deployed
    // bundle rather than configured, so this probes with the exact key production ships. If the
    // bundle stops yielding them the check says NOT RUN — it never silently degrades to passing.
    const creds = await prodSupabaseFromBundle(request);
    if (!creds) {
      throw notRun('the prod Supabase URL / anon key could not be read from the deployed bundle',
        'no chunk under /_next/static/chunks/ yielded both a supabase.co URL and a JWT',
        'set PROD_SUPABASE_URL and PROD_SUPABASE_ANON_KEY, or fix the derivation');
    }
    const probe = await request.post(`${creds.url}/auth/v1/token?grant_type=password`, {
      headers: { apikey: creds.anonKey, 'Content-Type': 'application/json' },
      data: { email: 'm3-1b-probe@example.invalid', password: 'deliberately-not-a-real-password' },
      failOnStatusCode: false,
    });
    const body = await probe.text();
    // "Invalid login credentials" would mean the provider is ENABLED — a security regression, and
    // one that silently makes a whole class of automated prod sign-in possible. Assert the
    // disabled string positively; anything else, including a success, is a failure.
    expect(body, 'production email/password provider is no longer disabled').toMatch(/email logins are disabled/i);
  });

  test('6 · a money guard was armed for this run', async () => {
    // The COMPARISON is the run teardown's job (prod-global.ts), because a check inside a spec is
    // skipped in exactly the window it matters. What this asserts is that the guard exists at all —
    // an unread baseline means the run had no money guard, and that is NOT RUN, never a pass.
    const { ledger, ledgerError } = fx();
    if (!ledger) {
      throw notRun('the production spend ledger could not be read, so no money guard was armed',
        ledgerError ?? 'no baseline recorded',
        'set CLAUDE_RO_DATABASE_URL (read-only) in .env.local or the environment');
    }
    console.log(`   ✓ baseline: ledger_audit ${ledger.auditMaxId}, ${ledger.centsTotal}¢ — compared at teardown`);
  });
});

/** Reads the deployed bundle for the Supabase URL and anon key it actually ships.
 *  Derived rather than configured, on the principle that a cached copy of someone else's value
 *  rots silently. Returns null rather than guessing — the caller turns that into NOT RUN. */
async function prodSupabaseFromBundle(
  request: { get: (url: string) => Promise<{ text: () => Promise<string> }> },
): Promise<{ url: string; anonKey: string } | null> {
  const envUrl = process.env.PROD_SUPABASE_URL;
  const envKey = process.env.PROD_SUPABASE_ANON_KEY;
  if (envUrl && envKey) return { url: envUrl, anonKey: envKey };

  const login = await (await request.get(`${PROD_URL}/login`)).text();
  const chunks = [...new Set(login.match(/\/_next\/static\/chunks\/[^"']+\.js/g) ?? [])].slice(0, 20);
  for (const chunk of chunks) {
    const js = await (await request.get(`${PROD_URL}${chunk}`)).text();
    const url = js.match(/https:\/\/[a-z0-9]+\.supabase\.co/)?.[0];
    const key = js.match(/eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{10,}/)?.[0];
    if (url && key) return { url, anonKey: key };
  }
  return null;
}

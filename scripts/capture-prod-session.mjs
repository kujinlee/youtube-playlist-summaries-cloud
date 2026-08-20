/**
 * Capture a production session for the M3.1-B smoke — the one step that needs a human.
 *
 *     npm run prod:session
 *
 * Opens a real Chrome, takes you to the deployed sign-in page, and waits while YOU complete Google
 * sign-in. Nothing is typed for you and no credential is read, stored or logged by this script; it
 * only saves the cookies the browser ends up holding, to playwright/.auth/prod.json (gitignored).
 *
 * WHY THIS CANNOT BE AUTOMATED, verified rather than assumed:
 *   · prod login is Google OAuth only (app/login/page.tsx)
 *   · the email/password provider is OFF on the prod project
 *     (docs/reviews/task-7-prod-auth-verification.md:7, verified 2026-07-24 — and check 5 of the
 *     smoke now re-asserts it every run, so it cannot quietly change again)
 *   · /dev-login is 404 in prod by design (lib/supabase/dev-login.ts fails closed)
 *
 * TWO THINGS MEASURED WHILE BUILDING THIS, both load-bearing:
 *
 *   1. `channel: 'chrome'` — REAL Chrome, not the bundled Chromium. Google frequently refuses
 *      automation-flagged browsers at the account chooser ("this browser may not be secure"). Two
 *      consecutive spike runs with real Chrome reached the chooser cleanly on 2026-08-19.
 *   2. THE SIGN-IN BUTTON DROPS CLICKS BEFORE HYDRATION. One spike run navigated on the first
 *      click; the very next needed a second. `domcontentloaded` fires before React makes the button
 *      live, so a single-click script does nothing at all, intermittently, and looks like a Google
 *      problem. The retry loop below is not defensive padding.
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from '@playwright/test';

const PROD_URL = 'https://youtube-playlist-summaries.fly.dev';
const AUTH_FILE = path.join(process.cwd(), 'playwright/.auth/prod.json');
const PATIENCE_MS = 5 * 60_000;          // you may need a password manager, 2FA, or a coffee

const browser = await chromium.launch({ headless: false, channel: 'chrome' });
const context = await browser.newContext();
const page = await context.newPage();

try {
  await page.goto(`${PROD_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 60_000 });

  const btn = page.getByRole('button', { name: /google/i }).or(page.getByRole('link', { name: /google/i }));
  if ((await btn.count()) === 0) {
    throw new Error(`No Google sign-in control on ${PROD_URL}/login — the page changed, or prod is down.`);
  }

  let left = false;
  for (let attempt = 1; attempt <= 4 && !left; attempt++) {
    await btn.first().click({ timeout: 10_000 }).catch(() => {});
    left = await page.waitForURL(/accounts\.google\.com/, { timeout: 12_000 }).then(() => true).catch(() => false);
    if (!left) await page.waitForTimeout(1500);
  }
  if (!left) throw new Error('The sign-in button never navigated to Google after 4 attempts.');

  console.log('\n  → Sign in with Google in the window that just opened. I am waiting, not watching.\n');

  // Done when the browser is back on the deployed app and NOT on /login. Waiting for "any app URL"
  // would be satisfied by the /login page we started from.
  await page.waitForURL(
    (url) => url.origin === PROD_URL && !url.pathname.startsWith('/login'),
    { timeout: PATIENCE_MS },
  );

  // One more gate before writing: being on `/` proves a redirect happened, not that a session
  // exists. The app's own signed-in shell is the evidence — the same landmark check 2 asserts.
  await page.getByRole('navigation', { name: /playlists/i }).waitFor({ state: 'visible', timeout: 30_000 });

  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  await context.storageState({ path: AUTH_FILE });

  const { cookies } = JSON.parse(fs.readFileSync(AUTH_FILE, 'utf8'));
  const soonest = cookies
    .map((c) => c.expires).filter((e) => typeof e === 'number' && e > 0)
    .sort((a, b) => a - b)[0];
  console.log(`\n  ✓ Session saved to ${AUTH_FILE}`);
  console.log(`    ${cookies.length} cookies; earliest expiry ` +
    (soonest ? new Date(soonest * 1000).toISOString() : 'none recorded (session cookies)'));
  console.log('\n    Now run:  npm run test:e2e:prod\n');
} catch (err) {
  // Never leave a half-written session behind — a truncated file reads as "captured" to the
  // pre-flight, which is precisely the NOT-RUN-vs-FAIL confusion this suite exists to prevent.
  fs.rmSync(AUTH_FILE, { force: true });
  console.error(`\n  ✗ Capture failed, and no session file was written.\n    ${(err).message}\n`);
  process.exitCode = 1;
} finally {
  await browser.close();
}

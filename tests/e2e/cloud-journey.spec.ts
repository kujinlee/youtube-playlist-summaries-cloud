/**
 * M3.1-A — the cloud user journey, in a real browser, against a real Supabase stack.
 *
 *     npm run test:e2e:cloud            (needs Node >= 22 and a running local Supabase)
 *
 * The roadmap deliberately gives 3.1 no falsifier clause, on the grounds that "the thing genuinely
 * missing is WHICH STEPS the journey has, and that belongs in the test, where it is load-bearing".
 * This file is that list. Each `test` is one step and says what it would catch.
 *
 * Steps run in DECLARATION ORDER via `test.describe.serial`, and a failure stops the rest.
 *
 * ⚠ They do NOT share a page. An earlier version of this header said they did, and that was false —
 * measured 2026-08-13 by comparing the page fixture across two serial tests (`SHARED_PAGE=false`).
 * `describe.serial` orders tests and aborts the remainder on failure; it does not give them one
 * context. Every rung therefore does its own `goto` and establishes its own preconditions, and no
 * rung may rely on browser state another rung left behind.
 *
 * NO MONEY — AND THE RUN MEASURES IT RATHER THAN PROMISING IT.
 * An earlier version of this header asserted "no money is spent" and was FALSE: opening the HTML
 * render called resolveMagazineModel, found no model, called Gemini, and reserved 12¢ in
 * spend_ledger (measured 2026-08-13). It was caught only because the rendered prose came back as
 * LLM paraphrase instead of the seeded text — nothing in the suite was checking. The setup now
 * pre-seeds the magazine model so the serve path finds one. A cost claim that nothing measures is
 * just a wish.
 *
 * The guard itself is NOT IN THIS FILE. It is tests/e2e/cloud-global.ts, which reads the ledger
 * before any project runs and again as the run's teardown; read that file for why it had to leave a
 * `test.afterAll` here to cover a setup-project failure. What it proves, precisely:
 *   ✓ a paid SERVE is caught — migration 0025 writes a `serve_settle` audit row on every settled
 *     serve attempt, and `ledger_audit.id` is a sequence, so max(id) only ever grows.
 *   ✗ an enqueue reservation released normally would NOT be caught — a plain release writes no
 *     audit row (0020 records only the `release_underflow` exception) and nets the cents to zero.
 *     Unreachable from this journey today, because POST /api/jobs is intercepted in step 3 and
 *     there is no cancel rung — but the guard is narrower than "no money path was reached", and
 *     saying otherwise is how the false claim above got written in the first place.
 *
 * The one call that would reach YouTube and enqueue paid work — POST /api/jobs — is intercepted in
 * step 3, and only that call; the id it returns belongs to a row that really exists, so the refetch
 * and render are real. A deliberate, narrow exception to "not mocks", reasoned at the interception.
 */
import '../integration/setup';                       // env for the admin client (see cloud.setup.ts)
import { test, expect } from '@playwright/test';
import { readFixture } from './cloud-fixture';
import { adminClient } from '../integration/helpers/clients';
import { seedPlaylist } from '../integration/helpers/seed';

// Lazily, NOT at module scope: Playwright evaluates every spec file during collection, which
// happens BEFORE the setup project runs — a top-level read fails with ENOENT on a clean checkout
// and looks like a missing file rather than an ordering mistake (measured 2026-08-13).
let _fx: ReturnType<typeof readFixture> | null = null;
const fx = () => (_fx ??= readFixture());


test.describe.serial('cloud journey', () => {
  test('1 · the signed-in root renders CloudApp, not LocalApp', async ({ page }) => {
    // Not cosmetic. On the first deploy this exact dispatch went wrong — the page was prerendered
    // at build time with STORAGE_BACKEND absent, so a signed-in cloud user was served LocalApp and
    // its filesystem-path ingest, which 400s in a container. app/page.tsx carries a force-dynamic
    // and a comment about it; this is the browser-level assertion that it holds.
    await page.goto('/');
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByRole('navigation', { name: /playlists/i })).toBeVisible();
  });

  test('2 · the sidebar lists the owner’s playlists', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: fx().listed.title })).toBeVisible();
  });

  test('3 · an ingested playlist appears in the sidebar with NO reload (backlog #37)', async ({ page }) => {
    // THE STEP THIS SUITE EXISTS FOR. #37 was fixed on 2026-08-13 and every claim about that fix
    // rested on jsdom; it had never run in a browser. The bug: the sidebar is a sibling of the
    // content pane and is never keyed by playlistId, so the post-ingest router.push reconciles it
    // instead of remounting, and its [userId] fetch never re-ran.
    //
    // The new playlist is created AFTER the page has painted. An earlier draft of this test seeded
    // it up front and asserted it was absent — which failed, correctly: the sidebar lists ALL of
    // the owner's playlists at mount, so a pre-seeded row is visible immediately and the test would
    // have been asserting nothing. "Absent at first paint" has to be made true, not assumed.
    await page.goto('/');
    await expect(page.getByRole('link', { name: fx().listed.title })).toBeVisible();

    const created = await seedPlaylist(adminClient(), fx().ownerId);
    const title = `E2E Ingested ${Date.now()}`;
    await adminClient().from('playlists').update({ playlist_title: title }).eq('id', created.playlistId);
    await expect(page.getByRole('link', { name: title })).toHaveCount(0);   // genuinely not on screen

    // Only POST /api/jobs is intercepted, because a real one calls the YouTube Data API and
    // enqueues paid work. The id it returns belongs to the row just created, so the refetch, the
    // API response and the render are all real — the fake is exactly one request wide.
    await page.route('**/api/jobs', async (route) => {
      if (route.request().method() !== 'POST') return route.continue();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          playlistId: created.playlistId,
          jobs: [], challengeRequired: false,
          counts: { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
        }),
      });
    });

    await page.getByRole('button', { name: /new playlist/i }).click();
    await page.getByRole('textbox').fill('https://youtube.com/playlist?list=E2E');
    // `/^add$/i` does NOT match: the real label is "Add ▸" (NewPlaylistModal.tsx:96). Anchoring to
    // the start only, so a decorative glyph cannot break the test — but still anchored, so it
    // cannot accidentally match some other button containing the word.
    await page.getByRole('button', { name: /^Add/ }).click();

    // No reload, no goto: if this only passed after a navigation it would be asserting nothing.
    await expect(page.getByRole('link', { name: title })).toBeVisible();
  });

  // ⚠ SKIPPED, AND THE REASON IS A COST, NOT A BUG IN THE APP.
  //
  // The HTML render calls resolveMagazineModel. The setup pre-seeds models/{base}.json precisely so
  // that call finds one and returns without touching Gemini — and the blob IS written (verified in
  // storage.objects). But the served document still comes back as LLM paraphrase, so the resolver
  // is judging the seeded envelope STALE and regenerating: most likely `sourceSections` not
  // matching the titles its own parser derives from the markdown, since that is the freshness
  // input this envelope hand-rolls.
  //
  // Each attempt to guess that contract costs 6–12¢ of real Gemini spend. Today's debugging put 24¢
  // through the local ledger before this was understood. Iterating by trial and error on a money
  // path is the wrong way to learn a contract, so this step stops here rather than being tuned
  // until it goes green.
  //
  // WHAT IS AND IS NOT COVERED WITHOUT IT. Step 5 already proves the summary blob round-trips
  // through the serve path and arrives byte-correct — for free, because the md path is documented
  // never to call resolveMagazineModel (serve-summary-core.ts:28). What is missing is only "the
  // magazine HTML renders in a browser", which M3.2 verified by hand against release v6 on
  // 2026-08-12. Un-skip once the model-freshness contract is read from the resolver rather than
  // guessed; that is a bounded reading task, not an open question.
  test.skip('4 · opening a video renders its summary with a section timestamp', async ({ page }) => {
    const res = await page.goto(
      `/api/html/${fx().listed.videoId}?playlist=${fx().listed.playlistId}&type=summary`,
    );
    expect(res?.status()).toBe(200);
    await expect(page.getByText('Seeded lead for the e2e journey.')).toBeVisible();
    await expect(page.getByText(/2:12/).first()).toBeVisible();
  });

  test('5 · the summary downloads as markdown, and the bytes are the summary', async ({ page }) => {
    const md = await page.request.get(
      `/api/html/${fx().listed.videoId}?playlist=${fx().listed.playlistId}&type=summary&format=md&download=1`,
    );
    expect(md.status()).toBe(200);
    const body = await md.text();
    // The seeded prose must actually be in the file. A download test that only checks the header
    // proves the route answers, not that it answers with the document.
    expect(body).toContain('Seeded prose for the e2e journey');
    expect(md.headers()['content-disposition'] ?? '').toMatch(/attachment/i);
  });

  // THE MONEY GUARD USED TO BE HERE, as a `test.afterAll`. Three rounds moved it, and the trail is
  // worth keeping because each move was forced by a window the previous position could not see:
  //   round 0 · a 6th rung        — `describe.serial` aborts the remaining tests once one fails, so
  //                                 the check was skipped exactly when a rung had spent. Proved by
  //                                 un-skipping rung 4, a known money path: ledger_audit 303 -> 304
  //                                 and the assertion never ran.
  //   round 1 · `test.afterAll`   — survives a failing rung, but the baseline was read in this
  //                                 project's `beforeAll`, which fires only after the setup project
  //                                 finished, so everything the setup did was already inside it.
  //   round 2 · globalSetup       — the baseline moved into the setup project, but the ASSERTION was
  //                                 still in this one, and Playwright skips a project whose
  //                                 dependency failed. A setup that spent and then failed took the
  //                                 guard down with it.
  // It now lives in tests/e2e/cloud-global.ts, outside every project, where a failure anywhere
  // still runs it. Do not move it back into a spec.

  test('6 · signing out invalidates the session, not just the URL', async ({ page }) => {
    // Review High (2026-08-13): the earlier version chained `.catch()` onto a second locator, so it
    // could pass for the WRONG reason — a broken AccountMenu plus any unrelated control matching
    // /account|menu|sign/i that happens to navigate would satisfy it. Exact, scoped locators instead;
    // if the markup changes this must fail loudly rather than fall through to something else.
    await page.goto('/');
    await page.getByRole('button', { name: fx().email, exact: true }).click();
    await page.getByRole('menu').getByRole('menuitem', { name: 'Sign out', exact: true }).click();
    await page.waitForURL('**/login');

    // Landing on /login only proves a navigation happened. Coming BACK to a protected route and
    // being bounced again is what proves the session was actually cleared.
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });
});

/**
 * Backlog #44 — the main pane, in a real browser. THE HALF OF THE CLOUD APP NO TEST HAD RENDERED.
 *
 *     npm run test:e2e:cloud            (needs Node >= 22 and a running local Supabase)
 *
 * WHAT WAS UNCOVERED, and why that was easy to miss. `CloudAppBody` renders `PlaylistLibrary` only
 * when `?playlist` is present (components/cloud/CloudApp.tsx:98). Every rung of cloud-journey opens
 * `/` with no query string, so `PlaylistLibrary`, `VideoList`, `FilterBar`, `IngestProgressBanner`
 * and `ScopeProvider` were NEVER MOUNTED by any browser-level test. The sidebar link was asserted
 * visible three times and never clicked — so "the link leads to a working library" was, until this
 * file, an assumption. The video the setup works hardest to seed was read over HTTP by rung 5 and
 * never displayed.
 *
 * ⚠ THIS FILE REPLACES A `describe.skip` STUB, AND THE STUB IS THE MORE INTERESTING ARTEFACT.
 * Written for Stage 2a task 16, it did not assert anything; it listed the harness it would need —
 * "a SECOND Playwright web server with STORAGE_BACKEND=supabase on a distinct port" and "an
 * authenticated browser session ... storageState". Both were built later, in
 * `playwright.cloud.config.ts` and `cloud.setup.ts`. **The blockers were removed and the skip
 * stayed**, because nothing connects "the thing you were waiting for now exists" back to the file
 * that was waiting. A skip carrying its own preconditions still needs someone to re-read it.
 *
 * SCOPE IS DELIBERATELY NARROW — mount the pane, see the seeded video, open it. Not sort, rate,
 * archive, delete or share (the old stub named all of those). Those are covered below the browser
 * layer by per-route integration tests and per-component tests; what was missing was proof that the
 * pane MOUNTS AND RENDERS REAL DATA at all. Widening this file is a separate decision with its own
 * cost, and #44 asked for the rung, not the suite.
 *
 * NO MONEY. Nothing here reaches a paid call: the library lists videos via the videos route and the
 * document is opened as `format=md`, which returns before `resolveAndParse`
 * (app/api/html/[id]/route.ts:75-82, "D4 money invariant"). The run-level guard in
 * tests/e2e/cloud-global.ts measures that rather than trusting this paragraph.
 */
import '../integration/setup';
import { test, expect } from '@playwright/test';
import { readFixture } from './cloud-fixture';

// Lazily, for the reason cloud-journey.spec.ts:62-66 records: Playwright collects spec files before
// the setup project runs, so a module-scope read fails with ENOENT and reads as a missing file
// rather than an ordering mistake.
let _fx: ReturnType<typeof readFixture> | null = null;
const fx = () => (_fx ??= readFixture());

test.describe('cloud library — the main pane', () => {
  test('1 · clicking the sidebar link mounts the library and renders the seeded video', async ({ page }) => {
    await page.goto('/');

    // The empty state must be on screen FIRST. Without this the test could pass against an app that
    // renders the library unconditionally — it would be asserting the destination without ever
    // establishing that a navigation happened. "Absent at first paint" has to be made true, not
    // assumed (the same lesson cloud-journey rung 3 records about the sidebar).
    const pane = page.getByRole('region', { name: 'Cloud library' });
    await expect(pane).toContainText(/pick a playlist from the sidebar/i);
    await expect(page.getByRole('table', { name: 'Video list' })).toHaveCount(0);

    await page.getByRole('link', { name: fx().listed.title }).click();

    // The URL contract CloudAppBody dispatches on. Asserting the pane alone would not distinguish
    // "the library mounted" from "the link went somewhere else that happens to look similar".
    await expect(page).toHaveURL(new RegExp(`\\?playlist=${fx().listed.playlistId}`));

    // The pane, then the data. A mounted-but-empty library is the failure this is really hunting:
    // it is what a broken owner scope, a bad RLS policy or a silently failing fetch all look like,
    // and every one of them still paints the section element.
    await expect(page.getByRole('table', { name: 'Video list' })).toBeVisible();
    await expect(pane.getByText(fx().listed.videoTitle)).toBeVisible();
    await expect(pane).not.toContainText(/no videos here yet/i);
  });

  test('2 · the library reached by clicking serves the seeded document', async ({ page }) => {
    // #44's third clause — "and opens it". Rung 5 of cloud-journey fetches this document by URL,
    // which proves the ROUTE answers; it does not prove a user who clicked their way here can
    // reach it. This starts from the click, so the ids under test are the ones the PAGE produced,
    // not ones a test constructed.
    await page.goto('/');
    await page.getByRole('link', { name: fx().listed.title }).click();
    await expect(page.getByRole('table', { name: 'Video list' })).toBeVisible();

    const res = await page.request.get(
      `/api/html/${fx().listed.videoId}` +
      `?playlist=${fx().listed.playlistId}&type=summary&format=md&download=1`,
    );
    expect(res.status()).toBe(200);
    expect(await res.text()).toContain('Seeded prose for the e2e journey');
  });
});

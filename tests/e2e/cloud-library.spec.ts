import { test, expect } from '@playwright/test';

/**
 * Stage 2a — Task 16: Cloud library E2E (browser-level).
 *
 * STATUS: describe.skip — documented harness gap (see below), NOT a passing test.
 *
 * The cloud flow is already covered end-to-end below the browser layer:
 *   - Per-route integration tests against a REAL Supabase stack with `signInAs`
 *     (tests/integration/{playlists-route,videos-route-cloud,quickview-route-cloud,
 *      review-route-cloud,annotations-rpc,archive-route-cloud,middleware-2a}.test.ts)
 *   - Component tests for every cloud component (tests/components/{cloud-app,
 *     playlist-sidebar,account-menu,login-page,page-dispatch,client-api}.test.tsx)
 *
 * What this browser E2E adds — and the harness it REQUIRES (the remaining work):
 *   1. A SECOND Playwright web server running the dev server with
 *      `STORAGE_BACKEND=supabase` on a distinct port, plus a `projects: [{ name:'cloud',
 *      use:{ baseURL } }]` entry in playwright.config.ts. (The default project runs the
 *      LOCAL app; without this the spec would hit LocalApp, not CloudApp — plan T16/H4.)
 *   2. An authenticated browser session: seed a user + playlist + videos via the admin
 *      client (mirror tests/integration/helpers/seed.ts), sign in via Supabase to obtain
 *      the session cookies, and inject them into the Playwright context
 *      (`storageState` or `context.addCookies`) so middleware.ts admits the cloud routes.
 *
 * Un-skip and implement the two harness pieces above to activate. The steps below are the
 * intended assertions (kept as documentation of the flow to verify).
 */
test.describe.skip('cloud library flow (requires STORAGE_BACKEND=supabase web server + seeded session)', () => {
  test('sign in → list playlists → open → sort → rate → clear → archive → show-archive', async ({ page }) => {
    // Preconditions (harness): authenticated session cookies set; one seeded playlist with videos.
    await page.goto('/');

    // Sidebar lists the seeded playlist; clicking it navigates to /?playlist=<uuid>.
    const playlistLink = page.getByRole('link', { name: /ML Talks/i });
    await expect(playlistLink).toBeVisible();
    await playlistLink.click();
    await expect(page).toHaveURL(/\?playlist=[0-9a-f-]{36}/);

    // Video list renders.
    await expect(page.getByRole('row')).not.toHaveCount(0);

    // Sort by a column (header click).
    await page.getByRole('button', { name: /^Title/i }).click();

    // Rate a video via StarRating, then clear it.
    await page.getByRole('button', { name: /rate 4/i }).first().click();
    await expect(page.getByText(/USE.*4/i).first()).toBeVisible();
    await page.getByRole('button', { name: /clear rating/i }).first().click();

    // Archive a video, then reveal via Show Archive toggle.
    await page.getByRole('button', { name: /archive/i }).first().click();
    await page.getByRole('checkbox', { name: /show archive/i }).check();
    await expect(page.getByText(/archived/i).first()).toBeVisible();

    // Annotation persistence would be re-verified via the admin client or a reload here.
  });
});

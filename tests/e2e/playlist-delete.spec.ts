import { test, expect } from '@playwright/test';

/**
 * playlist-sidebar-ux — Task 10: sidebar delete button + confirm modal, browser-level E2E.
 *
 * STATUS: describe.skip — documented harness gap (see below), NOT a passing test. Same gap
 * as tests/e2e/cloud-library.spec.ts (Stage 2a T16): the default Playwright web server runs
 * the LOCAL app (`STORAGE_BACKEND` unset), so `page.goto('/')` renders `LocalApp`, not
 * `CloudApp`/`PlaylistSidebar` — there is nowhere for a route-level mock of
 * `/api/playlists` or `DELETE /api/playlists/[id]` to attach in the current harness.
 *
 * The full behavior set (Task 10 Enumerated Behaviors #1-#9; spec §B7 Overlay Dismissal
 * table) is already covered below the browser layer:
 *   - tests/components/cloud/DeletePlaylistDialog.test.tsx — all four dismissal paths
 *     (Cancel/Escape/backdrop/✕), disabled-mid-delete for all four, success, error, focus
 *     trap, returnFocus, double-submit guard, copy (title + "cannot be undone").
 *   - tests/components/cloud/PlaylistSidebar.delete.test.tsx — trash button is a sibling
 *     of the row `<Link>` (not nested), click opens the modal without the link receiving
 *     the click, per-row wiring (including a null-title fixture), onDeleted
 *     refetch+conditional navigate-home.
 *
 * What this browser E2E adds — and the harness it REQUIRES (the remaining work, same as
 * cloud-library.spec.ts):
 *   1. A SECOND Playwright web server running the dev server with
 *      `STORAGE_BACKEND=supabase` on a distinct port, plus a `projects: [{ name: 'cloud',
 *      use: { baseURL } }]` entry in playwright.config.ts, so `page.goto('/')` renders
 *      `CloudApp`.
 *   2. Once that project exists, route-level mocks are sufficient (no real Supabase
 *      needed for this spec) — `page.route('**\/api/playlists', ...)`,
 *      `page.route('**\/api/playlists/*', (route) => route.request().method() === 'DELETE'
 *      ? route.fulfill({ json: { deleted: true } }) : route.continue())`.
 *
 * Un-skip and implement the harness piece above to activate. The steps below are the
 * intended assertions (kept as documentation of the flow to verify), including the
 * mandatory null-title + titled fixture pair per the conditional-render rule.
 */
test.describe.skip('sidebar playlist delete (requires STORAGE_BACKEND=supabase web server project)', () => {
  const TITLED = {
    id: '11111111-1111-1111-1111-111111111111',
    playlistKey: 'PL_TITLED',
    playlistUrl: 'https://youtube.com/playlist?list=PL_TITLED',
    playlistTitle: 'ML Talks',
    createdAt: '2026-01-01T00:00:00Z',
  };
  const UNTITLED = {
    id: '22222222-2222-2222-2222-222222222222',
    playlistKey: 'PL_UNTITLED',
    playlistUrl: 'https://youtube.com/playlist?list=PL_UNTITLED',
    playlistTitle: null,
    createdAt: '2026-01-02T00:00:00Z',
  };

  async function mockPlaylistsList(page: import('@playwright/test').Page) {
    await page.route('**/api/playlists', (route) => {
      if (route.request().method() !== 'GET') return route.continue();
      return route.fulfill({ json: { playlists: [TITLED, UNTITLED] } });
    });
  }

  test('open → Cancel dismisses without deleting', async ({ page }) => {
    await mockPlaylistsList(page);
    await page.goto('/');
    await page.getByRole('button', { name: `Delete playlist ${TITLED.playlistTitle}` }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: /cancel/i }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await expect(page.getByRole('link', { name: TITLED.playlistTitle })).toBeVisible();
  });

  test('open → Escape dismisses without deleting', async ({ page }) => {
    await mockPlaylistsList(page);
    await page.goto('/');
    await page.getByRole('button', { name: `Delete playlist ${TITLED.playlistTitle}` }).click();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();
  });

  test('open → backdrop click dismisses without deleting', async ({ page }) => {
    await mockPlaylistsList(page);
    await page.goto('/');
    await page.getByRole('button', { name: `Delete playlist ${TITLED.playlistTitle}` }).click();
    await page.getByTestId('delete-modal-backdrop').click({ position: { x: 5, y: 5 } });
    await expect(page.getByRole('dialog')).toBeHidden();
  });

  test('open → ✕ dismisses without deleting', async ({ page }) => {
    await mockPlaylistsList(page);
    await page.goto('/');
    await page.getByRole('button', { name: `Delete playlist ${TITLED.playlistTitle}` }).click();
    await page.getByRole('button', { name: /close/i }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
  });

  test('null-title row: trash button uses the "Untitled playlist" fallback in its aria-label', async ({ page }) => {
    await mockPlaylistsList(page);
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Delete playlist Untitled playlist' })).toBeVisible();
  });

  test('delete success: modal closes, row removed from list', async ({ page }) => {
    await mockPlaylistsList(page);
    let deleteCalled = false;
    await page.route(`**/api/playlists/${TITLED.id}`, (route) => {
      if (route.request().method() !== 'DELETE') return route.continue();
      deleteCalled = true;
      return route.fulfill({ json: { deleted: true } });
    });
    await page.route('**/api/playlists', (route) => {
      if (route.request().method() !== 'GET') return route.continue();
      return route.fulfill({ json: { playlists: deleteCalled ? [UNTITLED] : [TITLED, UNTITLED] } });
    });
    await page.goto('/');
    await page.getByRole('button', { name: `Delete playlist ${TITLED.playlistTitle}` }).click();
    await page.getByRole('button', { name: /^delete$/i }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
    await expect(page.getByRole('link', { name: TITLED.playlistTitle })).toBeHidden();
  });

  test('delete of the ACTIVE playlist navigates to "/" (no ?playlist param)', async ({ page }) => {
    await mockPlaylistsList(page);
    await page.route(`**/api/playlists/${TITLED.id}`, (route) => {
      if (route.request().method() !== 'DELETE') return route.continue();
      return route.fulfill({ json: { deleted: true } });
    });
    await page.goto(`/?playlist=${TITLED.id}`);
    await page.getByRole('button', { name: `Delete playlist ${TITLED.playlistTitle}` }).click();
    await page.getByRole('button', { name: /^delete$/i }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page).not.toHaveURL(/\?playlist=/);
  });

  test('delete error: inline error shown, modal stays open', async ({ page }) => {
    await mockPlaylistsList(page);
    await page.route(`**/api/playlists/${TITLED.id}`, (route) => {
      if (route.request().method() !== 'DELETE') return route.continue();
      return route.fulfill({ status: 500, json: { error: 'boom' } });
    });
    await page.goto('/');
    await page.getByRole('button', { name: `Delete playlist ${TITLED.playlistTitle}` }).click();
    await page.getByRole('button', { name: /^delete$/i }).click();
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByRole('dialog')).toBeVisible();
  });
});

<!-- codex-review: model=gpt-5.5 -->

**Blocking**
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:46): the ledger baseline is taken in the `cloud` project’s `beforeAll`, after the `setup` project has already run. So any money moved by [cloud.setup.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud.setup.ts:52) is outside the assertion window and will be baked into `ledgerAtStart`. This directly contradicts “the suite moved no money” as a suite-level claim. `beforeAll` runs once before the first test in this worker/project, not before each rung.
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:151): the central ledger assertion is only a final net-sum assertion across the shared table. A rung can reserve and later release/refund before rung 6 and the assertion still passes. It can also be offset by unrelated cleanup/release activity from previous runs because it sums every `spend_ledger` row, not just rows attributable to this run. This proves “same net ledger total at the end,” not “no money path was reached.”

**High**
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:158): rung 7 can pass while real sign-out is broken. The first fallback can click any first button matching `/account|menu|sign/i`, and the second fallback can click any `Sign out` button, not necessarily the opened account menu. A broken AccountMenu plus an unrelated “Sign out”/“Sign in” control that does `router.replace('/login')` would satisfy `waitForURL('**/login')` without clearing the Supabase session. Use a scoped exact locator instead:
  ```ts
  const header = page.getByRole('banner');
  await header.getByRole('button', { name: fx().email, exact: true }).click();
  await header.getByRole('menu').getByRole('menuitem', { name: 'Sign out', exact: true }).click();
  await page.goto('/');
  await expect(page).toHaveURL(/\/login/);
  ```
  The post-signout `goto('/')` matters because the current assertion only proves navigation to `/login`, not that the session was invalidated.
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:130): skipping rung 4 removes the only browser assertion for the HTML magazine render, which is also the path previously found to spend money. The comments are honest that this is missing, but the suite/config headers still make broad “no money” claims while the riskiest money path is skipped.

**Medium**
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:10): `test.describe.serial` does not make Playwright reuse the same `page` fixture across tests. Each rung gets its own page/context unless a custom worker-scoped fixture is introduced. The header’s “share one page” and “step 3 asserts state step 2 left behind” claim is false.
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:86): I do not find the route pattern overbroad for `/api/jobs/cancel`; `**/api/jobs` is not going to match that trailing path. The problem is under-verification: the test never asserts exactly one intercepted POST, never asserts no real POST escaped, and never waits for the sidebar’s `/api/playlists` refetch. A future periodic/sidebar refetch could make the title appear while the intended backlog #37 refresh mechanism is broken.
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:106): “No reload” is not verified. The test just avoids calling `page.goto`; it does not assert no document navigation/reload occurred while the app handled ingest.
- [tests/e2e/cloud.setup.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud.setup.ts:54): every run accumulates a new auth user, profile/session-related rows, playlist rows, video rows, and storage objects for markdown/model blobs. The fixture file is overwritten, but Supabase state is not cleaned. Owner scoping prevents most stale playlists from showing in the sidebar, but global tables like `spend_ledger`, `guardrail_config`, quotas, and old reservations remain shared ambient state.

**Low**
- [tests/integration/setup.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/setup.ts:15): quote stripping can corrupt a legitimate value whose intended bytes begin and end with `"`. It is probably fine for `supabase status -o env` output, but this is a shared Jest setup loader, not a Supabase-only parser. Also, gap-filling still means an already-set quoted/bad `NEXT_PUBLIC_SUPABASE_URL` will not be corrected by an unquoted `API_URL`.

Explicitly found nothing on one requested point: the route glob does not appear to catch `/api/jobs/cancel`; the non-POST `route.continue()` branch is mostly dead or only relevant to an exact `/api/jobs` non-POST, not a broad subtree.

NOT CONVERGED

# Adversarial Review — Cloud Summary PDF Implementation Plan (Claude)

**Artifact:** `docs/superpowers/plans/2026-07-11-cloud-summary-pdf.md`
**Spec:** `docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md`
**Reviewer mandate:** find what makes a zero-context engineer FAIL or produce wrong code when executing task-by-task.
**Verdict:** The *design* is sound (two-stage seam, nonce-free determinism, single-flight-outer/semaphore-inner ordering, content-addressed key) — I verified the core logic against real code and it holds. But the plan is **not executable as written**: nearly every test snippet is written against an invented harness that does not match this repo, one required gate test is impossible, and one lib contract is internally contradictory. Fix the test-harness layer and two logic items before coding.

Counts: **Blocking 2 · High 4 · Medium 3 · Low 2**

---

## BLOCKING

### B1 — Preflight gate test uses helpers that do not exist / wrong signatures → the gate that must run FIRST cannot run
**Plan lines 57–58** (also Task 11, lines 942, 948–952):
```ts
import { signInAs, makePrincipal } from '../helpers/supabase'; // existing integration helpers
const { supabase, userId } = await signInAs('atomicity-user');
const principal = makePrincipal(userId, 'atomicity-plist');
```
Every clause is wrong against ground truth:
- **Import path** `../helpers/supabase` does not exist. Real file: `tests/integration/helpers/clients.ts` (`tests/integration/helpers/clients.ts:1`).
- **`makePrincipal` does not exist anywhere in the repo** (`grep -rn makePrincipal` → 0 hits).
- **`signInAs` takes two args and returns `{ client, userId }`**, not one arg returning `{ supabase, userId }`: `export async function signInAs(email: string, password: string): Promise<{ client: SupabaseClient; userId: string }>` (`tests/integration/helpers/clients.ts:22`). A password only exists via `newUser()` (`clients.ts:12`).

Because Preflight is the atomicity gate that **blocks Task 8** (plan line 46 "do FIRST, before Task 2"), a test that cannot compile/run means the gate can never be cleared honestly.

**Fix:** Mirror the real pattern (see `tests/integration/html-download.test.ts:76–83`):
```ts
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';
import { getPrincipalFromSession } from '@/lib/storage/resolve';
const u = await newUser();
const { client } = await signInAs(u.email, u.password);
const { playlistKey } = await seedPlaylist(adminClient(), u.user.id); // real row so storage RLS passes
const principal = getPrincipalFromSession({ userId: u.user.id }, playlistKey);
const { blobStore } = getStorageBundle({ supabaseClient: client });
```
Also set `STORAGE_BACKEND='supabase'` in `beforeAll` (getStorageBundle returns the LOCAL bundle otherwise — `lib/storage/resolve.ts:52–53`).

### B2 — Task 7 "byte-identical GOLDEN_HTML" test is impossible: the html render embeds a random per-request nonce
**Plan lines 657–661:**
```ts
it('html path is byte-identical to pre-refactor for a promoted summary', async () => {
  const res = await GET(reqFor(`/api/html/${VIDEO}?playlist=${PID}&type=summary`), ctx);
  expect(await res.text()).toBe(GOLDEN_HTML); // captured from the pre-refactor route
});
```
The html path renders with `generateNonce()` (`app/api/html/[id]/route.ts:109`) → a fresh `crypto.randomBytes(16)` base64 nonce (`lib/html-doc/csp.ts:4–6`) stamped into ~5 `<script>`/`<style>` tags (`lib/html-doc/render.ts:117–129`, `theme.ts:79–120`, `nav.ts:447`). Every request produces **different bytes**, so a fixed `GOLDEN_HTML` can never match. The existing suite documents exactly this and pattern-matches instead: "Pattern-match the CSP nonce value rather than hard-coding it (generateNonce() is random per request)" (`tests/integration/html-download.test.ts:113–119`; also `tests/api/html-serve-cloud.test.ts:71–77` extracts the nonce with a regex). This RED never goes GREEN for the *intended* reason — it fails forever on the nonce.

**Fix:** Assert behavior-preservation by normalizing the nonce (replace `nonce="[^"]+"` → `nonce="X"` in both actual and golden), or assert the structural invariants the existing tests use (status, content-type, `cache-control: private, no-store`, CSP shape, single consistent nonce across all tags). Do **not** assert raw byte-identity of the html path. (The PDF path in Task 8 *is* deterministic — nonce-free — so its hash-stability test is fine; the contradiction is html-path-only.)

---

## HIGH

### H1 — Task 5 timeout path THROWS instead of returning undefined: contradicts the stated contract, the route's `!buf` branch, and the spec-required M3 test
**Plan lines 481–489** (Task 5 impl):
```ts
await Promise.race([render, timeout]);      // timeout REJECTS on expiry
} catch (err) {
  if (err instanceof PdfRendererUnavailable) throw err;
  throw new PdfRendererUnavailable(`PDF render failed: ${(err as Error).message}`, { cause: err });
}
...
if (opts.returnBuffer) return rendered;     // ← never reached on timeout
```
The current file's `timeout` promise **rejects** (`lib/pdf/generate-doc-pdf.ts:36–42`). So on timeout, `Promise.race` rejects → the new catch wraps it and **throws** `PdfRendererUnavailable`. Control never reaches `return rendered`. This directly contradicts:
- The Task 5 Interfaces block: "on timeout → **writes nothing, returns nothing**" (plan lines 383–384).
- The route's design: `if (!buf) throw new PdfRendererUnavailable('render produced no output (timeout)')` (plan line 808) — dead code for the timeout case.
- **Spec §11's required M3 test:** "generateDocPdf **timeout**: on timeout it **writes nothing** and returns **no buffer**" (spec lines 395–397). Task 5's test list (plan lines 407–424) has **no timeout test at all** — so this spec-mandated behavior is both unimplemented-as-specified and untested.

Net functional effect at the route is still 503 (throw is caught → 503), so it's not a user-visible bug — but it is an internal contract contradiction that will surface the moment someone writes the M3 test as the spec requires (it will fail). **Fix:** either (a) make the timeout path fall through to `return undefined` (distinguish the timeout rejection and swallow it, letting `rendered` stay undefined), and add the M3 test; or (b) delete the "returns nothing on timeout" contract + the route's `!buf` branch and document "timeout throws PdfRendererUnavailable." Pick one; the plan currently asserts both.

### H2 — Task 8 (and Task 7) route tests use invented harness symbols and omit the mandatory auth-plumbing mocks → tests won't run
**Plan lines 651, 660, 729–751, 793:** the tests reference `reqFor(...)`, `ctx`, `GOLDEN_HTML`, and `jest.spyOn(supabase, 'rpc')` — none exist in this repo, and `supabase` is not in scope in those blocks. Target file `tests/integration/html-route-cloud.test.ts` (plan line 638) **does not exist**. Real, verified pattern (`tests/integration/html-download.test.ts:21–37, 85–88, 124`):
```ts
jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn(() => mockClient) }));
import { GET } from '@/app/api/html/[id]/route';
function req(videoId, qs) { return new Request(`http://localhost/api/html/${videoId}?${qs}`); }
function invoke(id) { return { params: Promise.resolve({ id }) }; }
const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc'); // NOT jest.spyOn(supabase,'rpc')
```
The plan never mentions the two `jest.mock(...)` plumbing shims — **without them the route cannot obtain a session client** and every Task 8 route test throws at `createServerSupabase`. Also note the money-guard the plan "adds" in Task 7 already exists as **C2** (`html-download.test.ts:122`), so Task 7 Step 1 is partly re-inventing a passing test.

**Fix:** Rewrite Task 7/8 tests on the real harness (`req`/`invoke`, `SupabaseClient.prototype` rpc spy, the two plumbing mocks, `seedPlaylist`/`seedPromotedVideo`/`seedSummaryBlob` from `./helpers/seed`), target `tests/integration/pdf-route-cloud.test.ts` fresh, and for Task 7 extend `tests/integration/html-download.test.ts` (or `tests/api/html-serve-cloud.test.ts`), not a non-existent file.

### H3 — Task 10 VideoMenu tests target an API the component does not have
**Plan lines 900–918:**
```tsx
render(<VideoMenu {...cloudProps} summaryReady playlistId={PID} video={{ id: 'v' }} />);
fireEvent.click(screen.getByRole('button', { name: /more/i }));
const link = screen.getByRole('menuitem', { name: /view pdf/i });
```
Ground truth (`components/VideoMenu.tsx` + `tests/components/video-menu-cloud-2c.test.tsx`):
- `VideoMenu` has **no `summaryReady` or `playlistId` prop** — readiness is `video.summaryReady` (`VideoMenu.tsx:72`) and playlistId comes from `useScope()` (`VideoMenu.tsx:47, 73`). Cloud mode is set by wrapping in `<ScopeProvider scope={CLOUD_SCOPE}>` (`video-menu-cloud-2c.test.tsx:10–12`), not a `cloudProps` flag.
- **There is no "more" trigger button.** `VideoMenu` renders the `<ul role="menu">` directly; items are always present. `getByRole('button', {name:/more/i})` finds nothing.
- Menu links have **role `link`, not `menuitem`** (`<li role="none"><a …>`, `VideoMenu.tsx:76–83`). Real tests use `getByRole('link', { name: /view summary/i })` (`video-menu-cloud-2c.test.tsx:37`).

Every locator in Task 10 Step 1 fails. **Fix:** Mirror `video-menu-cloud-2c.test.tsx` verbatim — `renderCloud(<VideoMenu {...cloudProps} video={{ ...video, summaryReady: true } as any} … />)`, assert `getByRole('link', {name:/view pdf/i})` href = `` `/api/html`→`/api/pdf/${video.id}?playlist=${PID}&type=summary` ``, and the disabled `<span>` via `getByText`. Note the disabled title is the exact string `Finalizing…` (`VideoMenu.tsx:82`); `/finalizing/i` matches it, fine.

### H4 — Task 5 error-type/message change will break the existing PDF unit test and the local caller assertions (plan says only "extend if present")
`tests/lib/pdf/generate-doc-pdf.test.ts` **already exists** (`ls tests/lib/pdf/`). The current launch-failure throws a plain `Error("Failed to launch Chromium… \n<msg>")` (`generate-doc-pdf.ts:47–51`); Task 5 changes it to `PdfRendererUnavailable` and rewrites the catch to wrap **all** failures. Any existing assertion on the old error type/message will fail. The local caller `app/api/videos/[id]/pdf/route.ts:93–99` is fire-and-forget with a `.catch` — behavior-compatible, but the plan must (a) **update** the existing unit test, not merely "extend," and (b) re-run the local `pdf-path.test.ts` + `generate-doc-pdf.test.ts` to prove no local regression. **Fix:** add an explicit step to reconcile the existing PDF tests and run them in the same GREEN gate.

---

## MEDIUM

### M1 — Preflight/Task 11 storage writes will fail RLS with a fabricated principal (compounds B1)
Even after fixing the import, `makePrincipal(userId, 'atomicity-plist')` (plan line 66) invents an `indexKey` with no backing `playlists` row. `SupabaseBlobStore` writes to `${p.id}/${p.indexKey}/${key}` (`lib/storage/supabase/supabase-blob-store.ts:12`) under the session client (RLS-enforced). Use a **real** `playlistKey` from `seedPlaylist(...)` so the owner-prefixed object path is one the storage policies accept. (Same fix as B1.)

### M2 — Task 7 refactor drops `assertVideoId` from pre-auth validation → 400→401 status flip for unauthenticated bad-videoId requests
**Plan line 674** lists the preserved validation as "outputFolder/type/format/download/playlist" — **videoId is omitted**. In the real route `assertVideoId(videoId)` returns 400 **before** the `getUser()` 401 (`app/api/html/[id]/route.ts:38` then `:42–43`). The refactor moves videoId validation inside `loadSummaryForServe`, which runs **after** `getUser()` (plan lines 677–679). So an unauthenticated request with a malformed videoId flips from **400 → 401**, violating the "behavior-preserving / byte-identical status codes" contract the task and §14 demand. **Fix:** keep `assertVideoId(videoId)` in the pre-auth param block of `serveCloud` (loadSummaryForServe re-asserting is harmless defense-in-depth).

### M3 — Task 6 `resolveAndParse` language type: `(load.video as any).language` relies on an any-cast to satisfy `resolveMagazineModel`
`resolveMagazineModel` requires `language: 'en' | 'ko'` (`lib/html-doc/serve-doc.ts:42`); `Video.language` is `z.enum(['en','ko'])` (`types.ts:51`). The plan casts through `any` (plan line 607), which compiles but silently drops the type guarantee. Low risk (real data is constrained), but prefer typing `LoadResult.video` as `Video` and passing `load.video.language` without the cast so a future schema drift is caught by `tsc`.

---

## LOW

### L1 — `getStorageBundle` is constructed 3× per PDF request
`loadSummaryForServe` (plan line 582), `resolveAndParse` (plan line 603), and the route (plan line 800) each call `getStorageBundle({ supabaseClient })`, instantiating three `SupabaseBlobStore`/`SupabaseMetadataStore` sets. Harmless (cheap constructors) but wasteful; the route already has `load.principal` — consider returning/threading the bundle. Not blocking.

### L2 — Preflight interleaves 20×(2 MB put + get) against real Supabase Storage
Plan lines 66–78 push ~40 MB of round-trips in one test. Fine as a one-time gate, but flag it as potentially slow/flaky in CI; consider `--runInBand` (already specified, line 92) and a smaller iteration count if it proves flaky.

---

## Verified-correct (attacked, found solid)
- **Single-flight OUTER / semaphore INNER ordering (plan line 804) is the right choice.** `runSingleFlight(key, () => withPdfSlot(...))` means a same-key burst enters withPdfSlot **once** (one slot per key → renders once), while different keys each take a slot (cap enforced). Reversing it would let a same-key burst each grab a slot before dedup and saturate the semaphore with duplicate work. Correct as written.
- **Nonce-free determinism holds.** `renderMagazineHtml(parsed, model, { nonce: undefined, dig: false })` — `nonceAttr(undefined)` returns `''` safely (`theme.ts:79–81`), no `Date.now()`/random anywhere in `render.ts`, and `dig:false` omits `navScript` (`render.ts:129`). Same `(parsed, model)` → byte-identical HTML → stable `pdfCacheKey`. The premise Decision B rests on is real.
- **Double `get()` (outside + inside slot) is a correctness optimization, not a race/waste.** The inner re-check (plan line 805) catches a blob written by an earlier, already-settled single-flight whose map entry is gone — avoiding a redundant Chromium render. Fine.
- **`withPdfSlot` release-only-if-acquired** (plan lines 350–355): `active++` then `try/finally active--` only after a successful acquire; the saturation path throws before incrementing. Correct — no over-release.
- **Signatures that DO match:** `resolveOwnedPlaylistKey(client, playlistId, ownerId)` (`serve-playlist.ts:5`), `getPrincipalFromSession({userId}, indexKey)` (`resolve.ts:93`), `getStorageBundle({supabaseClient})` (`resolve.ts:51`), `assertLogicalKey` exported from `@/lib/storage/blob-store` (`blob-store.ts:21`), `resolveMagazineModel` args + all 6 `ResolveResult` statuses mapped exhaustively (`serve-doc.ts:26–44`), `assertVideoId` exported (`lib/index-store.ts:54`), and `pdfHref(playlistId, videoId)` correctly mirrors `summaryHref` order/export style (`lib/client/api.ts:195–206`). Tasks 2, 3, 4, 9 are self-contained and executable as written.

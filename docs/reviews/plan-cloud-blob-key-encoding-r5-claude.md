# Plan review round 5 — Claude half (adversarial), scoped to round 4's fixes

**Subject:** `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md` at commit `093e61a`,
branch `fix/cloud-blob-key-encoding`.
**Method:** every load-bearing claim resolved against the repo by hand; one finding measured against
the live local Supabase stack at `http://127.0.0.1:54321` (asserted local before connecting; the one
user created was deleted).

**Count: 1 Blocking / 1 High / 2 Medium / 3 Low.**

> ⚠ **Working-tree drift.** The tree was clean when this round was dispatched; while I was reading it
> acquired uncommitted edits carrying round-5 **Codex** fixes (`isLocalSupabaseUrl`,
> `RecordingBlobStore.promoteIfAbsent`, the elision recount). **This review is against `093e61a`**, as
> the prompt specifies. I checked those three edits as well and say so where they land — Low 7 below
> is a finding I derived independently and then found already patched in the tree.

---

## Blocking 1 — T9: three of the four seam behaviors throw `playlist not found` before the guard they exist to test

**Task 9.** Plan `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2065-2082`.
**This is v5d's own fix surface** — the round-4 adjudication rewrote these tests to open with the
per-test idiom, and the seeding it chose is not sufficient for the methods being driven.

The plan, verbatim:

```ts
it.each(['upsertVideo', 'updateVideoFields', 'bulkUpdateVideoFields'] as const)(
  'behaviors 26c + 26c2 — %s REFUSES a patch advertising an unservable key', async (method) => {
    const ctx = await makeOwnerContext();
    await prepareSyncCtx(ctx);
    await expect(callWith(ctx, method, {
      summaryMd: 'nested/evil.md',
      artifacts: { summaryMd: { key: 'nested/evil.md', status: 'promoted' } },
    })).rejects.toThrow(/not a servable summary key/);
  });

it('behavior 26c — a Korean key is ACCEPTED', async () => {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await expect(callWith(ctx, 'updateVideoFields', { … })).resolves.toBeUndefined();
});
```

`callWith` (plan `:2051-2061`) builds a `SupabaseMetadataStore(ctx.userClient)` and calls one of the
three methods with `ctx.cloudPrincipal`. **All three methods take `requirePlaylistId` as their FIRST
statement, before the argument carrying the guard is ever evaluated** —
`lib/storage/supabase/supabase-metadata-store.ts`:

```ts
115  async upsertVideo(p: Principal, video: Video): Promise<void> {
116    const id = await this.requirePlaylistId(p);
117    const { error } = await this.client.from('videos').update({ data: stripComputed(video) })   // ← T9 replaces stripComputed here
…
133  async updateVideoFields(p, videoId, fields, opts?): Promise<void> {
139    const id = await this.requirePlaylistId(p);
140    const { error } = await this.client.rpc('merge_video_data', { …, p_fields: stripComputed(fields) …
…
153  async bulkUpdateVideoFields(p, patches): Promise<void> {
157    const id = await this.requirePlaylistId(p);
…
313  private async playlistId(p: Principal): Promise<string | null> {
314    const { data, error } = await this.client.from('playlists').select('id')
317      .eq('playlist_key', p.indexKey).maybeSingle();
320    return data?.id ?? null;
323  private async requirePlaylistId(p: Principal): Promise<string> {
325    if (!id) throw new Error(`playlist not found for indexKey=${p.indexKey}`);
```

**`prepareSyncCtx` never inserts a `playlists` row.** `tests/integration/helpers/cloud.ts:365-376`
sets `ctx.playlistKey`, `ctx.videoId`, the mkdtemp roots and the two principals — nothing else. The
row is created by `seedCloudVideo`, and only there (`:426-433`, `if (!ctx.playlistId) { … insert into
playlists … }`). `26c3`/`26c4` call `seedCloudVideo` and are fine; these four are not.

**MEASURED** against the live local stack (`http://127.0.0.1:54321`), reproducing
`playlistId(p)` exactly for a signed-in fresh user and a `k-<uuid>` index key:

```
playlistId lookup -> {"data":null,"error":null}
requirePlaylistId would throw: true -> "playlist not found for indexKey=k-57d531d7-…"
```

**Failure scenario, executing literally.** All four cases fail in setup:

- the three `it.each` arms reject with `playlist not found for indexKey=…`, so
  `rejects.toThrow(/not a servable summary key/)` fails — the guard is never reached, and the
  message proves it;
- `behavior 26c — a Korean key is ACCEPTED` rejects where it asserts `resolves`.

This is the prompt's own Blocking definition: a fixture that runs but cannot observe its subject.
It is worse than a plain red, because the row exists precisely to prove *each of the three adapter
methods* refuses ("that is only meaningful if each is really called", plan `:2049-2050`) — and a
reader seeing three red arms with an unrelated error will most plausibly conclude the guard is
mis-placed rather than the fixture under-seeded.

**Fix.** Seed the cloud playlist in all four, i.e. `await seedCloudVideo(ctx, {});` in place of (or
after) `prepareSyncCtx(ctx)` — it creates the playlist row *and* a video row, and `prepareSyncCtx` is
its first statement anyway. Checked so the recommendation is not a guess: `merge_video_data`
(`supabase/migrations/0007_storage_and_rpcs.sql`) authorises on the *playlist* and then runs a plain
`update videos … where playlist_id = … and video_id = …`, so a missing video row is a 0-row update
that returns void — the ACCEPT case passes once the playlist exists, and seeding the video as well
costs nothing.

---

## High 1 — T12's row-derived report turns T11's behavior 26e red, in the file T12 appends to

**Tasks 11 and 12.** T11 plan `:2556-2565`; T12 plan `:2893-2910`; T12's verify command `:2946`.

T11 writes, into `tests/integration/cloud-sync/adopt-guard.int.test.ts`:

```ts
it('behavior 26e — cloud->local hydration of an unservable key SUCCEEDS', async () => {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await seedCloudVideo(ctx, { summaryMd: EVIL, mdBody: '# body\n' });       // cloud-only video
  const report = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  expect(report.errors).toEqual([]);
  expect(await localBlobBytes(ctx, EVIL)).not.toBeNull();
});
```

T12 Step 5(b) then says: *"Insert after `sync-run.ts:614` (`const base = manifest.videos[id];`),
inside the per-video `try`"*:

```ts
        if (cv?.summaryMd && !isServableSummaryKey(cv.summaryMd)) {
          report.errors.push({ videoId: id, message:
            `cloud key ${JSON.stringify(cv.summaryMd)} is not servable, so this video cannot be ` … });
        }
```

`lib/cloud-sync/sync-run.ts:612-618` is `lv` / `cv` / `base`, and **the one-sided branch is at
`:618`** (`if (!lv || !cv) { … }`). The insertion point is therefore *above* it, so the push fires
for one-sided rows too. 26e is exactly such a row: cloud-only, `cv.summaryMd === 'nested/evil.md'`,
which is unservable by construction. After T12 lands, `report.errors` has one entry and
`expect(report.errors).toEqual([])` fails.

Nothing in the plan tells the implementer to amend 26e. T12 Step 6's header comment says only
*"APPENDED to the file T11 creates … do not recreate the file"*, and T12 Step 7 runs
`npx tsc --noEmit && npm test && npm run test:integration` before committing — so **T12's own verify
step cannot pass as written**, on a test the plan declared green two tasks earlier.

Checked rather than assumed: this does not hit the other three T11 tests. 26 / 26b / 26f are
local-only (`cv` is null, the `cv?.` short-circuits), and 26c3 arm B in T9 survives because it
excludes only `/not a servable summary key/`, which does not match T12's `… is not servable, so …`
wording.

**Fix.** Narrow 26e to the message class it is actually about, e.g.
`expect(report.errors).not.toContainEqual(expect.objectContaining({ message: expect.stringMatching(/RENAME THE FILE/) }))`,
and state in T12 Step 6 that the append changes 26e — or move the row-derived push below the
one-sided `continue` at `:639` if the standing-defect report is meant for two-sided rows only. The
first is the smaller change; the second is a design question the plan should answer explicitly,
because 26d2 (T12's own test) relies on the report firing for a **two-sided** row and would not
notice the difference.

*(Filed High rather than Blocking because it surfaces loudly at T12's own gate and the repair is one
assertion. Under a strict reading of "a step that cannot be executed as written", it is Blocking.)*

---

## Medium 1 — T13: the volume probe measures a different directory than the assertion

**Task 13.** Plan `:3009-3025` (the probe) and `:3028-3032` (`tmp()`), assertion at `:3088-3097`.

```ts
function volumeAliasesNfcNfd(): boolean {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'nfc-probe-'));      // ← os.tmpdir()
…
function tmp(): string {
  const d = fs.mkdtempSync(path.join(os.homedir(), 'additive-protocol-'));   // ← os.homedir()
```

Behavior 18 writes into `r.p.indexKey`, which is `localPrincipal(tmp())` — under `os.homedir()` —
and then branches on a probe run under `os.tmpdir()`. The fix replaced *"the volume is APFS"* with
*"`TMPDIR` and `HOME` have the same normalization semantics"*, which is a second unstated assumption
in the same place, and this project's own rule is that a check only beats a claim when it reads the
thing the claim is about.

**MEASURED here**, both roots, with node 22:

```
tmpdir  = /var/folders/tg/…/T   {"aliases":true,"names":["probe-café.md"]}
homedir = /Users/kujinlee       {"aliases":true,"names":["probe-café.md"]}
df: both on /dev/disk1s1
```

So the probe is right on this machine — because both paths are on one APFS volume, not because it
measured the right one. The plan's *"returns true here, matching the plan's APFS claim"* is
reproduced.

**Failure scenario.** Any runner where `TMPDIR` is redirected to a different filesystem than the home
directory: a container with `--tmpfs /tmp` and a bind-mounted workspace, a `TMPDIR=/Volumes/scratch`
on a case-sensitive (hence normalization-sensitive) APFS volume, a sandbox that relocates `TMPDIR`.
The probe then reports the wrong volume, behavior 18 asserts the wrong branch, and the result is a
red test nobody can reproduce — the exact failure mode HIGH 1 was written to remove, one layer in.

**Fix.** Probe in the directory the assertion is about. Either `volumeAliasesNfcNfd(base: string)`
called as `volumeAliasesNfcNfd(r.p.indexKey)` (strictly best: it measures the very directory that was
just written), or at minimum default `base` to `os.homedir()` so the probe and `tmp()` share a root.

---

## Medium 2 — the Global Constraints import table names a sixth file that never calls the predicate

**Global Constraints.** Plan `:88-104`, row at `:100`; T4's Interfaces line at `:909`.

The table's column header is *"File that will call it"*, and its sixth row is:

| `lib/html-doc/serve-summary-core.ts` | **already imports `assertCloudSummaryMdKey`** | **EXTEND the existing named import** |

**There is no `isServableSummaryKey` call site in `serve-summary-core.ts` anywhere in the plan.** I
enumerated every occurrence of the identifier in the plan; the production call sites are
`share/serve.ts` (`:1170`), `supabase-metadata-store.ts` (`:2186`), `summary-handler.ts` (`:2424`),
`sync-run.ts` (`:2627`, `:2905`) and `reconcile-serial.ts` (`:2811`, `:2812`). The remaining
occurrence, `:1027`, is **inside `assert-cloud-summary-md-key.ts` itself** (T4 rewrites
`assertCloudSummaryMdKey` to delegate to the new predicate), so it needs no import either. T4's own
Interfaces line agrees and excludes the file: *"the predicate T5, T9, T10, T11, T12 all install"*.

`serve-summary-core.ts:61` calls `assertCloudSummaryMdKey(mdKey)` and gets the new behavior for free.

**Failure scenario.** An implementer following the table literally adds
`isServableSummaryKey` to `serve-summary-core.ts:4`'s named import and never uses it: a dead import
in the file the constraint singles out as *"the one that actually bites"*. Not fatal — but this row
is the entire justification for promoting Low 4 to a Global Constraint, and it is the one row that is
wrong.

Two consequences worth separating:

- If the intent is *"files that will call it"*: **delete row 6**, and say `serve-summary-core.ts`
  needs no change because it routes through `assertCloudSummaryMdKey`.
- If the intent is *"files that already import from this module, so do not add a second import"*:
  the sweep **missed a seventh** — `lib/dig/cloud/resolve-summary-key.ts:1` also imports
  `assertCloudSummaryMdKey` from that path (and also needs no change).

Secondary, on the commit message rather than the plan: `093e61a` states *"there are SIX call sites
across FIVE files"*. By this plan's own counting rule (identifier followed by `(`, outside string
literals, excluding imports/comments/definitions) it is **seven** — `reconcile-serial.ts` has two
(`:2811`, `:2812`) and `sync-run.ts` has two (`:2627`, `:2905`). The five-file count is right.

---

## Low 1 — T9 cites `cloudPrincipal` at `:59`; it is at `:58`

Plan `:2024-2026`: *"`ctx.userClient` and `ctx.cloudPrincipal` both exist — `Ctx` declares them at
`tests/integration/helpers/cloud.ts:44` and `:59`."*

```
44:  readonly userClient: SupabaseClient;          ← correct
58:  cloudPrincipal: Principal;   // { id: userId, indexKey: playlistKey }
59:                                                 ← blank line
```

`:44` is right; `:59` is off by one. Notable only because it sits inside the parenthetical whose
whole point is *"Checked rather than assumed"*, and because it is the eighth wrong citation in a plan
that has now run two dedicated citation sweeps.

## Low 2 — T14's lifted-fixture comment: "four fixtures", seven names, "SIX helpers"

Plan `:3591-3593`:

```
// The four fixtures below are lifted from tests/integration/summary-handler.test.ts — `mockCtx`
// (:46), GEMINI_SUMMARY_RESPONSE (:53), SEGMENTS (:64), resetGeminiMocks (:66), makePayload (:72),
// makeJob (:85) and seedPlaylist (:37). SIX helpers, not the five the prose claimed.
```

Three counts of the same set in three lines: **four**, **seven** (as listed), **six** (as asserted).
Every individual citation is correct — I checked all seven against
`tests/integration/summary-handler.test.ts` (`seedPlaylist` 37-44, `mockCtx` 46-51,
`GEMINI_SUMMARY_RESPONSE` 53-62, `SEGMENTS` 64, `resetGeminiMocks` 66-70, `makePayload` 72-83,
`makeJob` 85-95). Two of the seven are also **not lifted**: `resetGeminiMocks` is inlined into
`beforeEach` (plan `:3609-3615`) and `seedPlaylist` is inlined into `ingestViaHandler`
(`:3638-3644`). The itemization is the check on the total, exactly as the rollout count taught; here
it fails. Say "seven fixtures, five of them verbatim", or drop the number.

## Low 3 — T13's narrative still describes the pre-probe assertion, and its run table still claims the whole file

Plan `:2986-2989` still reads: *"Behavior 18's assertion is `toEqual([NFC])` over the directory's
`.md` files, not `toContain(NFC)` … (Measured on APFS: one file, stored under the NFC name.)"* —
written before the branch at `:3089-3097` existed. And the RED/GREEN table at `:2978-2981` still says
**9 passed / 9** for the file as a whole, as does `:3354`.

Same shape in T8: `:1674-1679` says *"WRITTEN AND RUN against the live local stack … whole file, both
ways … 7 passed / 7"*, and the file now contains `seedLegacyEnvelope` (`:1754-1761`), written in
`3c69804` and never executed. It could not have been covered by that run: the run applied *"T7's
read-side `videoId`"* only, which is precisely the condition under which the OLD fixture still
worked.

Neither is a wrong instruction — the code blocks are authoritative and correct — but a ⚙ EXECUTED
marker whose subject has changed underneath it is the failure this project files hardest against
elsewhere. Mark the two blocks as *"measured before the round-4 fix; the probe branch / the legacy
seeder are unexecuted"*, or re-run and re-state.

---

## Verified, not merely read — the parts of the fix surface that hold

Recorded so the coordinator knows which claims were actually resolved against the repo, and so a
later round need not redo them.

**T8 `seedLegacyEnvelope` (`:1739-1761`) is correct.**
`MODEL_KEY` is exported (`lib/html-doc/model-store.ts:32`) and the T8 import list now includes it
(`:1693`). The bytes match `serialize` exactly — `Buffer.from(`${JSON.stringify(x, null, 2)}\n`)`,
content type `application/json` (`model-store.ts:34-37`, `:52`). The read side tolerates the omission:
`.strict()` is off with the reason stated at `model-store.ts:25-26`, the four required fields
(`sourceMd`, `generatedAt`, `sourceSections`, `model`) are all supplied, and T7 Step 3 (`:1576-1579`)
does add `videoId: z.string().optional()` to `ModelEnvelopeSchema` — which matters, because zod
`.object()` *strips* unknown keys, so without it 18j6's read-back would come back undefined for a
current envelope too. `over` is spread last, so `sourceMd: 'wrong.md'` / `sourceMdHash: 'stale'` win.
18j4 still observes its claim: the sender's `sourceMdHash` equals the winner hash, so
`decideCompanion` returns `ship`, and the assertions (`res.error` undefined, receiver `videoId`
stamped to `ctx.videoId`) go red under exactly the mutation that matters — a guard that treats a
missing `videoId` as a refusal, or one that consults `sourceMd`.

**T9 26c3's two arms really do run in opposite directions.** The winner is decided at
`lib/cloud-sync/reconcile-class-a.ts:49-50`
(`newer(local.mdGeneratedAt, cloud.mdGeneratedAt) ? 'copyToCloud' : 'copyToLocal'`), and that line is
reached for this fixture: both sides have bodies (`lHas`/`cHas`), neither carries
`mdCorrectionsHash` so `bothStale` is true and the currency branches at `:39-40` do not fire,
`docVersionMajor` is equal (neither seed sets `docVersion`) so `:43` does not fire, and the bodies
differ so `:32` falls through. Arm A (local `2026-02-02` vs cloud `2026-01-01`) gives `copyToCloud`
— cloud is the refused receiver. Arm B inverts it and gives `copyToLocal` — the vault, unguarded, as
decision (1) requires. `SeedFields` accepts `summaryMd`, `mdBody`, `mdGeneratedAt` and `position`
(`helpers/cloud.ts:327`, `:380-418`), and `mdGeneratedAt` is only written when truthy (`:396`), which
is what makes the tiebreak reachable. `a` and `ctx` are two block-scoped consts over two different
users — nothing shadowed, no state shared.

**T11 `RecordingBlobStore`.** Against the interface *as it exists today* the surface is complete
(11 members: `copy`, `tryGet`, `provesAbsence`, `put`, `get`, `exists`, `delete`, `putStaged`,
`promote`, `deletePrefix`, `list` — `lib/storage/blob-store.ts:33-79`). Against the interface **T6
leaves behind** it was missing `promoteIfAbsent`, which the working tree now adds; that is right, and
the class around it is closed — T6 Step 6 (`:1466-1474`) already enumerates all seven existing
implementers, I re-derived that list with `os.walk` and got the same seven, and `RecordingBlobStore`
was the only implementer the plan itself creates (`AbsentOnReadBack` at `:3081` *extends*
`InMemoryBlobStore`, so it inherits). `copy` routing through `copyBlob(this, …)` matches
`FailPromoteBlobStore` (`helpers/cloud.ts:184`) and its stated reason.

**Recording `tryGet` is safe for 26f.** `sync-run.ts` never calls `tryGet` on the sender store: the
only sender-side read on the adopt path is `readMdBody(from.blob, from.p, present)` at `:626`, which
goes through `blob.get` (`:67`), and T11's guard is inserted between `:625` and `:626`. Nothing else
touches `deps.localBlob` before the one-sided branch. `expect(gets).toEqual([])` is therefore
satisfiable, and recording both methods makes the instrument strictly stronger.

**T13's ext4 claim survives tracing.** On a normalization-sensitive volume the NFD destination is
genuinely absent, so `promoteIfAbsent` takes the create path and the read-back at `:3254` returns the
newcomer's own bytes — the resume branch is not reached by any other route. `canonicallyEqualName` is
used only in `transferClassA` (`:3317`), not in `copyAdditiveVideo`, so it cannot smuggle the test
back onto the resume path. The copy still succeeds, which is what the unconditional
`resolves.toBeUndefined()` above asserts, and `[NFC, NFD].sort()` matches `readdir(...).sort()`
(NFD sorts first: `U+0065` before `U+00E9`). The probe creates and removes its own directory and does
not touch `roots`.

**T2's header.** Every import resolves: `LocalFsBlobStore`/`localBlobStore`
(`lib/storage/local/local-blob-store.ts:7,92`), `InMemoryBlobStore`
(`lib/storage/testing/in-memory-blob-store.ts:41`), `localPrincipal` + `Principal`
(`lib/storage/principal.ts:5,12`). The `Principal` note is correct — `blob-store.ts:1` imports the
type and does not re-export it, and the export list the plan states matches the file exactly. The
per-test user idiom is `tests/integration/blob-store.test.ts:17-22` as cited, and a synthetic
`indexKey` with no playlist row is that file's own practice (`:47`), so the fixture is legal.
`NEXT_PUBLIC_SUPABASE_URL` is populated by `tests/integration/setup.ts:23`, which is a `setupFiles`
module (`jest.integration.config.ts`) and therefore runs before any `beforeAll` — the ordering the
guard depends on holds. That same file already throws when the variable is absent (`:27-36`), so the
guard's absent-branch is belt-and-braces rather than the primary defence; keep it anyway.
`afterEach`'s swallowed `deletePrefix` cannot hide anything a test asserts — behavior 11 performs its
own `deletePrefix` and asserts on it.

**The T2 prod guard as patched in the working tree is right, and the regex it replaced was wrong.**
`isLocalSupabaseUrl` exists at `lib/supabase/is-local-url.ts:7`, parses with `new URL`, compares the
**hostname** exactly against `localhost` / `127.0.0.1`, and returns false on a throw. The committed
regex `/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/` does pass
`https://localhost:54321@project.supabase.co`, whose real host is `project.supabase.co` — userinfo
before the `@`. I had cleared that regex against `localhost.evil.com` and `127.0.0.1.nip.io` and
missed the userinfo form; the Codex half's finding stands and its fix is the correct one.

**T14.** `loadSummaryForServe(supabase, { videoId, playlistId, userId })` matches
`lib/html-doc/serve-summary-core.ts:34-37`. The inlined playlist insert matches `seedPlaylist`
(`summary-handler.test.ts:37-44`) column for column and uses the same user-client / service-role-handler
split as `(a) happy path` (`:105-113`). `ledgerTotal()` reproduces `Ctx.spendLedgerTotal()`
(`helpers/cloud.ts:153-161`) exactly, and the whole-table claim is right for the stronger reason the
Ctx docstring gives at `:72-75` — `spend_ledger` has **no `owner_id` column at all**, one row per UTC
day — so a cross-user assertion is meaningful. Behavior 14's `mdKey` regex holds: `slugify` keeps
`\p{L}` (`lib/slugify.ts:4`), so a Korean title survives as `한국어-강의`, and `padSerial` pads to
three (`lib/serial-filename.ts:6-8`). No import in the block is unused — `padSerial`, `slugify`,
`localBlobStore`, `localPrincipal`, `fs`/`os`/`path` are all consumed by the vault-filename test at
`:3680-3692`. The ledger cannot move: `mockCtx.billing.metered` is false, Gemini is mocked, and T14
never goes through `enqueue_job`, which is where a reservation would be written.

**T12's elision counts are exactly right.** `sync-run.ts:740-741` is a 2-line comment and `:745-748`
is a 4-line comment, both as marked, and the surrounding code lines quoted at plan `:2828-2842` are
verbatim. The insertion point named for the refusal branch (inside `if (!rec.ok)`, above the generic
throw at `:754`) is correct and the appended alternative is indeed dead.

**Low 7 (independently derived, already patched in the working tree).** The other half of the Low-3
fix was itself miscounted: `helpers/cloud.ts` elides **six** lines at **`:140-145`**, not five at
`:141-145` — `cloudBlob,` is at `:140` and the description lists it. `localBlob` being the third key
is correct (`local` `:137`, `cloud` `:138`, `localBlob` `:139`). The uncommitted tree already carries
this correction.

---

NOT CONVERGED

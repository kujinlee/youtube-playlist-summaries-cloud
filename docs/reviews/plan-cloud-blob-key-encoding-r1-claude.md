# Plan review — `2026-08-15-cloud-blob-key-encoding.md`, round 1, Claude half

**Subject:** the #36 implementation plan (15 tasks, 77 TDD steps) in the working tree, branch
`fix/cloud-blob-key-encoding`. No implementation code exists yet.
**Question asked:** is this plan executable, literally, by an engineer with no context, and does
executing it produce the spec's behaviors without leaving the tree red between tasks?

**Verdict: NOT CONVERGED.** 4 Blocking, 4 High, 7 Medium, 4 Low.

The design is sound and the placement analysis that cost eighteen rounds has survived into the plan
intact — I verified the two things rounds 17 and 18 fought over and both are correctly closed (see
*What holds up*). What has not been done is the pass that asks whether the code in the plan compiles
against the code in the repo. Four of the plan's snippets do not, one of its property tests fails on
100% of its iterations, and roughly ten helper functions its tests invoke do not exist.

**Method note.** `grep` on this machine is ugrep and returns nothing silently, so every existence
claim below comes from `python3` + `os.walk` + `re` over all `.ts`/`.tsx` in the repo excluding
`node_modules`/`.git`/`.next`/`dist`/`build`, or from the Read tool. Every number is counted, and I
say where. Two claims are backed by executed measurements (Node 22.14.0) rather than reading.

---

## BLOCKING

### B1 — every task's verification step names a test runner this repo does not have. All 15 tasks.

The plan's Tech Stack line says "Vitest". It is not installed, and it is not the runner.

| Counted | Value |
|---|---|
| `npx vitest run` occurrences in the plan | **33** |
| `vi.fn()` occurrences in the plan (T7, T10, T11) | **3** |
| `jest` occurrences in the plan | **0** |
| `node_modules/vitest` present | **false** |
| `node_modules/.bin/vitest` present | **false** |

`package.json`: `"test": "jest"`, `"test:integration": "jest --config jest.integration.config.ts
--runInBand"`. Devdeps include `jest ^30.4.2`, `ts-jest`, `@types/jest`, `jest-environment-jsdom`.
Every existing test file in the repo uses `jest.fn` / `jest.mock` — including two files this plan
edits (`tests/integration/share-route.test.ts:11,37`, `tests/lib/storage/blob-store-list.test.ts:35`).

**Failure scenario.** Task 1 Step 2 is the first command an implementer types:
`npx vitest run tests/lib/storage/encode-segment.test.ts`. `npx` finds no local binary and offers to
fetch `vitest` from the registry. If they accept, it runs a Vitest with no config against a repo
whose `@/` alias, TS transform, jsdom environment and integration `globalSetup` all live in
`jest.config.ts` / `jest.integration.config.ts` — so it fails for a reason that has nothing to do
with the code under test. Step 2 says "Expected: FAIL — `Cannot find module …`", which it will
plausibly *also* print, so the implementer can conclude the red is the intended red and proceed. That
is worse than a hard stop.

There is a second half. The two suites need **different** commands, and the plan uses one:

- `jest.config.ts` `testMatch` is `tests/lib/**`, `tests/api/**`, `tests/scripts/**`,
  `tests/smoke.test.ts`, `tests/components/**`. It **excludes `tests/integration/`**.
- `jest.integration.config.ts` adds `globalSetup: tests/integration/global-setup.ts` (applies pending
  migrations — the whole point of PR #46) and `setupFiles`, and its comment states the suite shares one
  Supabase stack and **must** run serially, enforced by `--runInBand` on the npm script.

So `npx vitest run tests/integration/blob-encoding.test.ts` (T2 Step 6), `…/metadata-seam.test.ts`
(T9), `…/summary-handler-guard.test.ts` (T10), `…/cloud-sync-adopt.test.ts` (T11),
`…/cloud-sync-companion.test.ts` (T8), `…/cloud-sync-additive.test.ts` (T13) and
`…/korean-title-e2e.test.ts` (T14) are wrong twice over. And the bare `npx vitest run` that T7 Step 6
and T13 Step 4 use to mean "the whole suite" has no jest equivalent — no single command runs both
suites here.

**Fix.** Replace all 33 with `npx jest <path>` (unit) or
`npm run test:integration -- <path>` (integration). Replace the 3 `vi.fn()` with `jest.fn()`. Correct
the Tech Stack line to "Jest (ts-jest / next-jest), Playwright". Where a step means "the whole suite",
write both commands and say that the integration half needs the local Supabase stack up.

---

### B2 — T2 Step 3's `objectKey` drops the owner segment and the traversal guard.

Plan, T2 Step 3:

```ts
/** Logical -> physical. The ONLY place the encoding is applied (premise P3). */
function objectKey(p: Principal, key: string): string {
  return [p.indexKey, ...key.split('/').map(encodeSegment)].join('/');
}
```

Repo, `lib/storage/supabase/supabase-blob-store.ts:14-18`:

```ts
  /** Server-side owner prefix — never a client absolute path. */
  private objectKey(p: Principal, key: string): string {
    assertLogicalKey(key);
    return `${p.id}/${p.indexKey}/${key}`;
  }
```

Three separate regressions in one replacement, and an implementer with no context has no way to know
the plan is not quoting the real function — it is presented as the implementation, not as a diff.

1. **`${p.id}/` is gone.** Every physical key loses its owner segment. The plan's own Global
   Constraints say "**No migration.** …Nothing in this plan rewrites an existing object key" and cite
   the 2026-08-14 prod gate: 19 objects, 0 outside `SAFE`. Those 19 objects live at
   `<ownerId>/<indexKey>/<key>`. After this change every read computes `<indexKey>/<key>` and finds
   nothing. The constraint is violated for the **SAFE** keys — the ones the encoder was designed not
   to touch.
2. **Tenant isolation collapses.** The line the plan deletes carries the comment "Server-side owner
   prefix — never a client absolute path", and `tests/lib/storage/blob-store-list.test.ts:29-31`
   names this seam explicitly: "the tenant-isolation seam (spec 11.2: cross-tenant enumeration is the
   worst-case leak)". Two owners sharing an `indexKey` would now share a namespace.
3. **`assertLogicalKey(key)` is gone**, and encoding does not replace it. `SAFE =
   /^[A-Za-z0-9._-]+$/` matches `.`, so `encodeSegment('..')` returns `'..'` byte-identical (T1 Step
   3's first branch). A key of `a/../../secret` therefore survives the encoder unchanged, and
   `objectKey` is the only validation `put`, `get`, `exists`, `delete` and `promote` have —
   `putStaged` (`:103`) and `deletePrefix`/`list` (`:130`, `:141`) each call `assertLogicalKey`
   separately, so those four methods lose their only check.

**Fix.** Keep it a private method, keep `assertLogicalKey(key)` as the first statement, keep
`${p.id}/${p.indexKey}/`, and map `encodeSegment` over the segments of `key` **only**:

```ts
  private objectKey(p: Principal, key: string): string {
    assertLogicalKey(key);
    return `${p.id}/${p.indexKey}/${key.split('/').map(encodeSegment).join('/')}`;
  }
```

(This also preserves ADR-0008, which T15 Step 1 says must survive: `objectKey` encodes only `key`, so
both physical keys stay under the same grant. The plan states the property and then writes code that
breaks it.)

---

### B3 — T2 Step 3's `list` calls a method that does not exist, and its offset arithmetic is wrong against the one that does.

Plan, T2 Step 3:

```ts
  const physicalPrefix = objectKey(p, norm);
  const found = await this.rawList(physicalPrefix);
  return found.map((physical) => {
    const remainder = physical.slice(physicalPrefix.length);
```

`rawList` does not exist anywhere in the repo (0 references; also 0 mentions in the spec). The real
method is `private async collectObjectPaths(dirPath: string)` at
`supabase-blob-store.ts:151`, and it differs in both directions:

- **Input.** `list` at `:143` calls it as
  `` const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '') `` — the trailing slash is
  **stripped**, because `collectObjectPaths` uses `` `${dirPath}/${entry.name}` `` internally
  (`:160`) and a doubled slash would corrupt every path. The plan's `norm` deliberately **adds** a
  trailing slash.
- **Output.** It returns **full object paths including `${p.id}/${p.indexKey}/`** — that is why the
  existing `list` does `full.map((f) => f.slice(ownerRoot.length))` at `:145`.

So `physical.slice(physicalPrefix.length)` slices a full path by the length of a prefix that (per B2)
is missing `p.id.length + 1` characters. The remainder is silently short by that many characters,
`norm + remainder` produces a corrupted logical key, and **nothing throws** — the `=h` marker guard is
the only check and a mis-sliced remainder usually will not contain one. `paidKeysUnder`
(`reconcile-serial.ts:102`) feeds `blob.list(p, 'dig/<base>/')` straight into the relocation plan, so
a corrupted key becomes a `copy` source and then a `delete` target.

**Fix.** Write the step against `collectObjectPaths`: keep `assertLogicalKey(prefix)`, build the
physical dir path the way `:142-143` does (owner root + encoded prefix, trailing slash stripped for
the call), and compute the remainder relative to the **encoded owner root + encoded prefix** string
you actually passed. Show the real method name so the implementer can find it.

---

### B4 — T1 Step 5's property test fails on 100% of its iterations. MEASURED.

```ts
it('behavior 1 + 5 — property sweep over the codepoint space', () => {
  for (let cp = 0; cp <= 0x10ffff; cp += 0x40) {
    …
    expect(SAFE.test(out) || out === seg).toBe(true);
```

`SAFE = /^[A-Za-z0-9._-]+$/` (T1 Step 3) does not contain `=`, and every hashed output is
`` `${head}=h${digest}${ext}` ``. So for any non-SAFE input, `SAFE.test(out)` is false and
`out === seg` is false.

I ran T1 Step 3's implementation and T1 Step 5's assertion verbatim under Node 22.14.0:

```
T1 step5 sweep: 17376 iterations, 17376 FAILING the SAFE.test||identity assertion
first failure: { cp: '0', seg: '"003_x\\u0000.md"', out: '003_x=hyOB4ByYzzYRvOZ_iP3Vig1.md' }
max encoded length observed (head 40 + ext 9): 65
```

The plan says "Expected: PASS, 10 tests."

This is not merely a broken assertion — it presents the implementer with a fork whose wrong branch
cascades. The obvious "fix" is to make the hash branch emit a SAFE-alphabet key. That destroys
behavior 4's disjointness (`expect(SAFE.test('a=b')).toBe(false)` two tests earlier), and it destroys
T2 behaviors 9 and 10, whose entire mechanism is that `=h` in a physical remainder is the marker
distinguishing a hashed segment from a nameable one.

**Fix.** Assert against the **physical** alphabet, not `SAFE` — the same one behavior 2's test
already uses six tests earlier:

```ts
    expect(/^[A-Za-z0-9._=-]+$/.test(out)).toBe(true);
```

Note the length half of the sweep is correct: I measured the worst case (32-char head + `=h` +
22-char digest + 9-char ext) at exactly **65**, so `toBeLessThanOrEqual(65)` is tight and right.

---

## HIGH

### H1 — ten helpers the plan's tests invoke do not exist, and no step creates them.

This is the wall an implementer hits on step 1 of six different tasks. Searched with `python3` +
`os.walk` + `re` over every `.ts`/`.tsx` outside `node_modules`/`.git`/`.next`/`dist`/`build`.

**Absent from the repo entirely (0 references):**

| Helper | Used by | Tests affected |
|---|---|---|
| `fakeStoreHolding` | T2 Step 1 | 3 |
| `callWith` | T9 Step 1 | 2 (one is `it.each` over 3 methods) |
| `mintShareToken` | T5 Step 1 | 2 |
| `seedEnvelope` | T8 Step 4 | 1 |
| `ledgerTotal` | T10 Step 1, T14 Step 1 | 2 |
| `spyStore` | T11 Step 1 | 1 |
| `serveSummary` | T14 Step 1 | 4 |
| `ingestLocal` | T14 Step 1 | 1 |
| `readdirNames` | T13 Step 1 | 1 |
| `canonicallyEqualName` | T13 Step 1 | 2 (see H2) |

Task 14 is built **entirely** out of four of these (`ingest`, `ingestLocal`, `serveSummary`,
`ledgerTotal`) and is the task that proves backlog #36 is actually fixed.

**Present, but not what the plan assumes — the sharper half:**

- **`runSync`** exists at `lib/cloud-sync/sync-run.ts:547` as `export async function runSync(` — the
  production sync entry point, with a deps/config signature. The plan calls it with **three different
  invented shapes**: `runSync({ direction: 'copyToCloud', key: 'nested/evil.md' })` (T9),
  `runSync({ local: { summaryMd: … }, cloud: null })` and
  `runSync({ …, localBlob: spyStore(senderGet) })` (T11), and `runSync({ /* same fixture */ })`
  (T12). A name that already denotes something else is worse than a name that denotes nothing: the
  implementer imports it, gets a type error, and has to reverse-engineer what the plan meant.
- **`readVideo`** — T9 and T12 call `readVideo(cloud, cloudP, ID)`. There are two: a **module-private**
  one at `sync-run.ts:80` (not exported) and an exported one at `lib/storage/worker-persistence.ts:32`
  with a different signature. Neither is importable as written.
- **`seedVideo`** exists at `tests/integration/helpers/cloud.ts:296`. T5 calls it as
  `seedVideo({ summaryMd, artifacts: { summaryMd: { key, status } } })` — that shape needs checking
  against the real signature before the step is executable.
- **`storeWith`** exists only as a `const` at `tests/lib/html-doc/model-store.test.ts:110`. T7's tests
  live in that same file, so this one is fine — but it is not importable elsewhere, and the plan does
  not say it is file-local.
- **`putBudget`** exists and is exported (`tests/support/budget.ts:18`). Fine.
- `InMemoryBlobStore`, `localBlobStore`, `rewriteEnvelopeSourceMd` (`lib/serial-provenance.ts:14`) all
  exist and are used correctly.

**Fix.** Either add a step per task that writes the helper (with its signature), or point each one at
the existing fixture it should be built on — `tests/integration/helpers/cloud.ts` and
`tests/integration/helpers/seed.ts` already hold `seedPlaylist`, `seedPromotedVideo`,
`seedSummaryBlob`, `seedVideo`; `tests/lib/storage/blob-store-list.test.ts:34-37` already has a
`fakeClient(entriesByDir)` that is the natural ancestor of `fakeStoreHolding` (note it keys on
**physical** dir paths, so it is not a drop-in). And rename the `runSync` test wrapper — that name is
taken.

---

### H2 — T13 tests `canonicallyEqualName`, which exists in the spec and nowhere in the code, and no step implements it.

T13 Step 1, behaviors 18i and 18k:

```ts
it('behavior 18i — canonicallyEqualName is a PROPER SUBSET of the volume alias relation', () => {
  expect(canonicallyEqualName('café.md'.normalize('NFC'), 'café.md'.normalize('NFD'))).toBe(true);
  expect(canonicallyEqualName('Ａ.md', 'A.md')).toBe(false);   // fullwidth A is NOT an alias
});

it('behavior 18k — canonicallyEqualName(null, key) is FALSE, so a loser with no summaryMd probes', () => {
```

Counted: **9 mentions in the spec** (first at line 320), **0 references in the repo**. T13's File
Structure lists only `lib/cloud-sync/sync-run.ts` (modify) and `scripts/check-encoder-gate-sql.py`
(create). T13 Step 2 describes the protocol in prose — "`putStaged` -> verify the read-back hash ->
`promoteIfAbsent` -> read back and classify" — and never mentions the function. T13 Step 2 is also
the only step in the plan that carries no code at all, so there is nothing to infer it from.

This is a required predicate carrying two behaviors, not a fixture. Its semantics are load-bearing and
non-obvious (NFC/NFD equal, NFKC-fullwidth **not** equal, `null` never equal) — exactly the kind of
thing that gets reinvented wrong.

**Fix.** Give T13 a step that creates it, with its file, its signature
(`(a: string | null, b: string) => boolean`), and the one-sentence reason the relation must be a
proper subset of the volume's alias relation.

---

### H3 — T8's refusal is placed in the ship arm only, so its own test cannot pass; and it re-reads the receiver with the conflated reader the function was fixed to stop using.

T8 Step 1, behavior 18j:

```ts
  expect(res.shareNeedsOwnerServe).toBe(true);
  expect(res.error).toMatch(/envelope videoId/);
  expect(loserBlob.delete).not.toHaveBeenCalled();     // the paid model survives
```

The behavior is named "REFUSES **ship/delete**". `companionTransfer` (`sync-run.ts:444-477`) has three
arms after `decideCompanion` at `:454`:

```ts
  if (decision.kind === 'ship') { … await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob); … }
  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
  // deleteReceiverModel — best-effort; a missing model blob is not an error.
  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
```

T8 Step 3's snippet ends with the ship write, so it reads as an insertion immediately above `:464` —
inside the `ship` arm. A `deleteReceiverModel` decision never passes through it, and `:475` deletes
the loser's paid model with the ownership mismatch unexamined. The test asserting
`loserBlob.delete).not.toHaveBeenCalled()` fails, and the failure mode it was written to prevent —
a paid model deleted on a mismatched ownership claim — is exactly what happens.

**Second defect, same snippet.** It opens with:

```ts
const envelope = await readModelEnvelope(loser.p, base, loser.blob);
```

The receiver's envelope has **already been read**, honestly, at `:451-453`:

```ts
  const [senderModel, receiverModel] = await Promise.all([
    readModelSide(winner, base), readModelSide(loser, base),
  ]);
```

`readModelSide` exists (`:479`) with a docstring that is precisely about why the plan's line is wrong:
"H1 (round 4) — resolve `readModelEnvelope`'s single null into the tri-state `decideCompanion` needs.
A null means absent, corrupt, or unreadable; only a backend that can prove absence
(`BlobStore.provesAbsence`) lets us tell those apart." The plan adds a second network round-trip that
reintroduces the conflation, sitting three lines below the honest read it ignores. On the Supabase
side `get` swallows every failure into `null` (`supabase-blob-store.ts:29-35`), so a transient 5xx
makes `envelope?.videoId` falsy and the guard silently passes — fail-open on the money path.

**Fix.** Hoist the check above `decideCompanion` (`:454`) so it covers all three arms, and derive it
from `receiverModel`, not from a fresh `readModelEnvelope`. State in the step that an `unreadable`
receiver must not be read as "no ownership claim".

---

### H4 — the SKIP cell is visible for exactly one run, then permanently silent.

T12 Step 3 returns `{ ok: true, action: 'skipped-unservable' }` and the plan's sync-run snippet pushes
to `report.errors`. Traced through the caller:

`sync-run.ts:739` is `if (!rec.ok)` — not taken. `:758` is `if (rec.action === 'relocated')` — not
taken. Execution falls through to Class A at `:771` with `cv` unchanged.

Now walk T12's own 26d2 fixture (local: serial, **no** `summaryMd`; cloud: unservable key):

1. `la.mdHash == null` (local has no MD), `ca.mdHash != null`. The `:694`/`:697` unreadable guards do
   not fire.
2. `reconcileClassA` sees local-has-none -> `copyToLocal`.
3. `transferClassA(cloudSide, localSide, cv, id)` writes the body locally and, at `:430-432`, patches
   the **local** row with `artifacts: { summaryMd: { key, status: 'promoted' } }` for the cloud's key.
   The vault is correctly unguarded, so this succeeds. The plan's test asserts exactly this
   (`expect(await localBlob.get(localP, cloudKey)).not.toBeNull()`).
4. **Run 2.** `describeDivergence` (`:147-156`) now computes
   `to = baseOf(localVideo.summaryMd)` = the same unservable base as `from`, so `diverged` is
   `false` and `reconcileCloudBase` returns `{ ok: true, action: 'agreed' }` at `:184`.
   `report.errors` gets **nothing**. `reconcileClassA` returns `skip`. The baseline advances.

So the cloud key stays unservable forever, and the user is told once, on one run, in one line of
`report.errors` they may never read. The plan's comment says "SKIP, **visibly**" and the mechanism
delivers visibility only until the recovery it designed takes effect.

Compare behavior 26b in T11, which holds the sibling refusal to the opposite standard:
"the refusal SURVIVES a second run; it is not routed around" — with an explicit assertion for it.
26d2 has no second-run assertion, which is why the decay is invisible to the test.

Note this is not data loss — the artifact is recovered into the vault, which is the point of the cell.
The defect is the claim of visibility.

**Fix.** Either (a) add a second-run assertion to 26d2 and give the skip a durable signal (the row
still advertises an unservable key; a check at the seam or in the report that fires whenever a cloud
row's `summaryMd` fails `isServableSummaryKey` would fire every run), or (b) amend the plan to say the
signal is deliberately one-shot **because** the artifact has been hydrated locally and nothing further
is at risk — and say what a user is supposed to do with the cloud row. Do not leave the word "visibly"
standing over a one-shot.

---

## MEDIUM

### M1 — T4 drops `statusCode: 409` while claiming the throwing contract is unchanged. 22 existing assertions break.

T4's Interfaces block: "`assertCloudSummaryMdKey(mdKey: string): void` **keeps its name and throwing
contract**". T4 Step 3:

```ts
export function assertCloudSummaryMdKey(mdKey: string): void {
  if (typeof mdKey !== 'string' || !isServableSummaryKey(mdKey)) {
    throw new Error(`not a servable summary key: ${JSON.stringify(mdKey)}`);
  }
}
```

Repo, `assert-cloud-summary-md-key.ts:18`:

```ts
    throw Object.assign(new Error(`invalid cloud summary md key: ${mdKey}`), { statusCode: 409 });
```

**I checked whether this is an HTTP regression and it is not** — worth stating plainly rather than
inflating. The three production consumers all discard the error object: `serve-summary-core.ts:60-64`
is a bare `try { assertCloudSummaryMdKey(mdKey); } catch { return { ok: false, status: 409, error:
'corrupt summary key' }; }`; `resolve-summary-key.ts:16` is `try { … } catch { return null; }`;
`pdf-render-version.ts:14` only mentions it in a comment. And no route in the repo branches on
`statusCode === 409` (routes match `400` and `503`).

What does break is the test suite. `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts:24-33` has
two `it.each` blocks, 18 + 4 = **22 cases**, each ending `expect(e.statusCode).toBe(409)`. T4 Step 4
says "Expected: PASS."

**Fix.** Keep the `Object.assign(…, { statusCode: 409 })`. It costs nothing and the plan already
asserts the contract is preserved.

### M2 — T4's flips of the existing rejection cases are real, uncounted, and two of them contradict the plan's own NFKC claim.

T4 Step 4 hedges: "if one now fails, it was asserting the *allowlist*, not the requirement". True for
most, but the plan should name them, because two are not that.

I ran the plan's `isServableSummaryKey` against all 23 cases in the existing test. **No accept-side
regression** (all 5 accepted keys still pass — including `0007_.md` and `0007_한국어제목.md`).
**5 of 18 rejection cases flip to ACCEPT:**

| Case | Key | NFKC(name) |
|---|---|---|
| `double-dot` | `foo..md` | `foo.` |
| `leading-space` | `' foo.md'` | `' foo'` |
| `leading-dot` | `.foo.md` | `.foo` |
| `fraction-slash-2044` | `a⁄b.md` | `a⁄b` (**unchanged**) |
| `division-slash-2215` | `a∕b.md` | `a∕b` (**unchanged**) |

The first three are the intended widening — `foo..md` in particular is behavior 17d's whole point.

The last two are not. T4 Step 3's comment says "A hand-typed homoglyph denylist cannot be complete;
**NFKC closes that class**." Measured: it does not. U+2044 FRACTION SLASH and U+2215 DIVISION SLASH
have no NFKC decomposition to `/`, so both now pass a guard that previously rejected them by name.
This is harmless in practice — neither is a path separator on any filesystem, and the key is never
re-parsed as a path after this point (`serve-summary-core.ts:66` hands it straight to
`blobStore.get`) — but the plan asserts a completeness property that is false, and that assertion is
the reason nobody will re-examine it. U+FF0F does fold to `/` and is still correctly rejected.

**Fix.** List the five flips in T4 Step 4 with their dispositions, and downgrade the NFKC claim to
what it is: NFKC closes the *compatibility-decomposable* homoglyphs, not all of them; the two
non-decomposing slashes are accepted deliberately because the key is never re-parsed as a path.

### M3 — T6's local `promoteIfAbsent` calls a method that does not exist and uses unimported symbols.

```ts
  } finally {
    rmSync(this.stagingRoot(ref), { recursive: true, force: true });  // 18f: the whole tree
  }
```

`stagingRoot` does not exist on `LocalFsBlobStore`. `StagedRef` is `{ principal, tempKey, finalKey }`
(`blob-store.ts:5`), and `putStaged` builds `` tempKey = `_staging/${crypto.randomUUID()}/${key}` ``
(`local-blob-store.ts:53`) — so the staging root must be derived by parsing `tempKey`, which the step
does not say. Separately, `local-blob-store.ts:1` imports only the namespaces
(`import fs from 'fs'; import path from 'path';`), so bare `mkdirSync`, `linkSync`, `rmSync` and
`dirname` do not resolve. That half `tsc` catches; `stagingRoot` is a genuinely missing helper.

### M4 — T6 Step 4's Supabase recipe is not implementable as stated, and omits the cleanup its own contract test asserts.

"Supabase: `upload()` without `upsert` returns HTTP **409** when the object exists — treat 409 as
success, rethrow anything else."

`promoteIfAbsent(ref: StagedRef)` has no bytes to upload. `promote` (`supabase-blob-store.ts:109-127`)
uses `this.b().move(from, to)`. A create-if-absent finalize needs either `download(tempKey)` then
`upload(final, bytes, { upsert: false })`, or the bucket's `copy`. As written the step cannot be
followed.

Step 4 also says nothing about removing the staging tree, but behavior 18f requires it and the shared
contract test runs `describe.each` **against all three adapters** — so 18d2's
`expect(await store.list(P, '_staging/')).toEqual([])` and 18d3's identical assertion will fail on the
Supabase adapter.

### M5 — T2 lists `deletePrefix` as a file to modify and no step modifies it; premise P3 is not true of the code as it stands.

T2's Files block says "Modify: `supabase-blob-store.ts` (`objectKey`, `list`, `deletePrefix`)". Step 3
implements `objectKey` and `list`. `deletePrefix` is never mentioned again.

It matters because `deletePrefix` (`:129-138`) and `list` (`:140-146`) **both build the physical path
inline** (`` `${p.id}/${p.indexKey}/${prefix}` ``) rather than going through `objectKey`. So T2 Step
3's comment "The ONLY place the encoding is applied (premise P3)" is not a description of the code —
it is a property the task has to establish, and for `deletePrefix` it does not.

**Mitigating, and worth recording so nobody over-fixes it:** the only production caller is
`app/api/playlists/[id]/route.ts:79` with `deletePrefix(principal, '')`, which needs no encoding. Every
other call site is a test. So this is latent, not live. Behavior 11's test (`deletePrefix(P, '')`)
passes vacuously and cannot detect it.

**Fix.** Add the one-line change to Step 3 and one test with a non-empty non-ASCII prefix, or state
explicitly that `deletePrefix` is left alone because `''` is its only production argument.

### M6 — T12's sync-run insertion point is unstated, and the only obvious one is dead code.

```ts
if (rec.ok && rec.action === 'skipped-unservable') { … }
else if (!rec.ok && rec.reason === 'unservable-base') { throw new Error(…); }
```

The existing block at `:739-757` is `if (!rec.ok) { … throw new Error(rec.reason === 'target-occupied'
? … : `base reconciliation failed for ${id}: ${rec.reason}…`); }` — it throws on **every** `!rec.ok`.
Appending the plan's block after it makes the second arm unreachable, and `unservable-base` falls into
the generic tail. That tail produces `base reconciliation failed for <id>: unservable-base at
<key>` — which is precisely the un-actionable message round-16 M1 was filed about, and the reason the
plan wrote two named repair strings in the first place.

`tsc` will flag it (after the unconditional throw, `rec` narrows to `{ ok: true }`, so `rec.reason` is
a type error), so this fails loud rather than silent. But the step should say the branch goes
**inside** the `!rec.ok` block, above the generic throw at `:754`.

### M7 — T2 and T4 commit after running a slice narrower than their blast radius.

- **T2 Step 6** commits after `npx vitest run tests/integration/blob-encoding.test.ts` alone, having
  rewritten `objectKey` — the function every Supabase `put`, `get`, `exists`, `delete` and `promote`
  passes through.
- **T4 Step 6** commits after `npx vitest run tests/lib/html-doc/` alone, having changed
  `assertCloudSummaryMdKey`'s accept set. Its consumers are `serve-summary-core.ts:61`,
  `resolve-summary-key.ts:16` and `pdf-render-version.ts:14`, whose tests live in `tests/api/`
  (`serve-summary-core.test.ts`, `pdf-serve-cloud.test.ts`, `html-serve-cloud.test.ts`) and
  `tests/lib/dig/`.

T3, T7, T11 and T12 all correctly run the wider suite before committing. T2 and T4 should match.

---

## LOW

### L1 — T7's rollout count is recalled, not counted.

Plan: "**41 call sites** (3 production + 38 test) across **11 files**". Counted, by regex over every
non-`node_modules` `.ts`/`.tsx`, excluding the two declarations in `model-store.ts` itself:

| | Plan | Measured |
|---|---|---|
| total call sites | 41 | **43** |
| production | 3 | **3** (`generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464` — all three cited correctly) |
| test | 38 | **39** |
| files | 11 | **11** (3 prod + 8 test) |
| `rerender.test.ts` | 14 | **14** |

The file count, the production trio and the `rerender.test.ts` figure are all right; the totals are
off by two. Separately, "Expect `tsc` to go red in all 41 the moment step 3 lands" overstates the
mechanism — only sites whose envelope literal lacks `videoId` go red, which the plan's own "roughly 20
distinct envelope literals, because fixtures are shared" concedes two sentences earlier.

### L2 — two property sweeps are described as covering the codepoint space and stride past 97% of it.

T1 Step 5 uses `cp += 0x40` (17,376 of 1,112,064 code points, **1.6%**). T4 Step 5 behavior 27 uses
`cp += 0x20` and calls itself "over the whole codepoint space".

I ran behavior 27 at **stride 1 over the full space**, with the post-T3 `slugify` and the plan's
predicate, across all four title shapes it specifies (`ch`, `a${ch}`, `${ch}a`, `'a'.repeat(59)+ch`):
**0 violations**. So the 3.4/3.5 cross-derivation genuinely holds and this is an overclaim, not a
hidden defect. It takes a few seconds at stride 1 — either step by 1 or call it a strided sample.

### L3 — three test bodies cannot be executed because their fixtures are elided.

T12 26d2: `const report = await runSync({ /* same fixture */ });`. T11 26b: `await runSync({ … })`
twice, with a literal ellipsis. T8 Step 1: four calls of the form
`companionTransfer(/* receiver envelope videoId: 'OTHER', row: 'dQw4…' */)` with no arguments at all,
against a function whose real signature is
`(winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video)` (`sync-run.ts:444-446`).
The plan's Self-Review says "No TBDs. Every code step carries real code" — these are TBDs in comment
syntax.

### L4 — T5's target file mocks the module T5 tests.

`tests/integration/share-route.test.ts:37-50` does `jest.mock('@/lib/share/serve', …)` and replaces
`getShareServeContext` with a counting wrapper over `jest.requireActual`. T5's two new tests call
`getShareServeContext` directly, so they will exercise the wrapper. It delegates, so the assertions
should hold — but the wrapper maintains module-level counters (`mockGlobalCallCount`,
`mockArmedAtCount`) that the existing B10b test arms with a `sinceArm === 2` trigger. Adding calls to
that file perturbs shared state the existing test depends on. Worth a sentence in T5, or put the new
tests in their own file.

---

## What holds up

Calibration matters more than finding count here, so these are stated as findings of their own.

- **Spec coverage is complete.** I enumerated §5 independently — **65 behavior rows** — and diffed
  against the plan's task mapping. **Zero unmapped.** The self-review's claim is correct. (`18e` is
  mapped to both T6 and T13, which is harmless; `18j5b` is claimed for T7 but is not a §5 row.) The
  brief's hypothesis that "a self-review that finds a gap is evidence of more" did not pay out.
- **Zero literal control or bidi characters in the plan.** I ran the plan's own detector
  (`unicodedata.category in ('Cc','Cf')`, excluding `\n`) over the whole file: 0 violations. The
  defect that shipped five times is fixed in this draft.
- **Round-18 L1 is correctly closed.** T12's `const origin = localVideo.summaryMd ? 'vault-filename' :
  'cloud-key'` is the *same truthiness predicate* as the ternary it must agree with at
  `reconcile-serial.ts:152-154` (`localVideo.summaryMd ? baseOf(localVideo.summaryMd) :
  baseOf(applySerial(…))`). `summaryMd: ''` takes arm B in both. No nullish/truthy disagreement.
- **Behavior 26d3 is constructible — it is not an unfalsifiable row.** `applySerial`
  (`serial-filename.ts:20-25`) strips `^\d+_` and re-prefixes `padSerial(serial)`. Two constructions:
  (a) a cloud key with **no** serial prefix at 131 code points gains 4 characters and lands at 135;
  (b) `padSerial` "widens automatically past 999", so a 131-code-point key with a 3-digit serial plus a
  local serial of 1000 lands at 132. Both need `localVideo.summaryMd` falsy for `origin` to be
  `'cloud-key'`, which the fixture provides.
- **No task commits with `tsc` red.** The brief's specific worry about T7 does not materialize: Step 3
  breaks the type, Step 4 fixes all the call sites, Step 6 runs `npx tsc --noEmit && <suite>` before
  `git commit`. The tree compiles at every commit boundary in the plan.
- **The money ordering is sound.** T10's mint guard is between `reserveVideoSlot` (`:95`) and the
  Gemini call (`summaryCore`, `:101`), so a refusal costs a serial and no money. T11's adopt guard is
  above both `readMdBody` (`:626`) and `ensureReceiverSlot`'s durable insert. T12 refuses before the
  copy phase. A plan stopped after any task N cannot double-charge or orphan a paid artifact.
- **T9-before-T10/T11/T12 is right and load-bearing**, with one intermediate state worth naming in the
  ordering rationale: between T9 and T12, a video whose relocation target is unservable will have
  `reconcileCloudBase` copy every paid blob and *then* have `updateVideoFields` refused at `:324`,
  caught at `:325` as `metadata-failed`, and rethrown by sync-run at `:754`. That is a **repeating
  stall, not a loss** — sources are retained, the old row is intact, and the §4 gate measured 0 prod
  rows outside `SAFE` — but it is a real state for the duration of three tasks.
- **Every line-number citation I checked is accurate**: `supabase-metadata-store.ts` `:19`/`:119`/
  `:143`/`:160`; `summary-handler.ts` `:95`/`:96`/`:101`; `generate.ts:50`, `serve-doc.ts:174`,
  `sync-run.ts:464`; `sync-run.ts` `:620` `presentIsLocal`, `:624-627`, `:626` `readMdBody`;
  `reconcile-serial.ts` `:69-81`, `:152-154`, `:324`; `serve.ts` `mdKey` at `:47`; the three
  `assertCloudSummaryMdKey` consumers.
- **T1's encoder is correct and its bound is tight.** I measured the worst-case output at exactly
  **65** characters (32-char head + `=h` + 22-char digest + 9-char ext), so `<= 65` is the right
  constant. The `utf16le` choice, the head/ext preservation and the identity/hash disjointness all
  check out.

---

## One paragraph on the spec, as the brief permits

Not re-litigated, and it does not affect the verdict. The one thing I would want on the record: T13's
`check-encoder-gate-sql.py` is given a docstring and no body, and the plan's Self-Review flags it as
"the one under-specified step". Flagging is **not** enough for this particular script, because it is
the behavior-20 instrument whose entire job is to prove the §4 gate's SQL predicate derives from the
encoder rather than being a hand-copied character class. A ratchet specified only by its docstring is
the shape this project has repeatedly measured as a green check over the wrong subject. It needs, at
minimum: which file it reads `SAFE` out of, which file holds the SQL, what "the same one" means when
one is a JS regex literal and the other is a SQL `~` pattern, and the exit-2 condition. The plan says
"model it on `scripts/check-producer-enumeration.py`" — that is the right ancestor, but the mapping
between a JS character class and a Postgres one is the actual hard part and no step addresses it.

---

NOT CONVERGED

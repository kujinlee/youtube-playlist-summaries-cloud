# Plan review round 4 — Claude half (SCOPED)

**Subject:** `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md` at `c964672`,
branch `fix/cloud-blob-key-encoding`.
**Scope as briefed:** the four rewritten fixture blocks (T8, T10, T12, T13) plus round 3's three
smaller findings. Tasks 0-7, 9, 11, 14, 15 not re-derived.

**Method.** Every import path and every free identifier in the four blocks was resolved against the
working tree by reading the target file, not by pattern-matching. Where a claim was executable it
was executed: the T4 predicate was run over the exact keys in T12's four-cell table, the T13 section-4
gate script was transcribed to a scratch file outside the repo and run both ways, the zod write-schema
behaviour behind T8's legacy case was run against the repo's own zod (4.4.3), and the T7 rollout count
was re-counted mechanically under the plan's stated rule. No tracked file other than this one was
touched; the scratch files live under the session scratchpad.

**Counts: 2 Blocking, 1 High, 1 Medium, 4 Low.**

---

## BLOCKING 1 — Task 8, behavior 18j4: the legacy envelope cannot be seeded once T7 has landed

**Plan** `:1708-1719` (the test) and `:1627-1635` (`seedEnvelope`). **Code** `lib/html-doc/model-store.ts:34-53`,
plan `:1481-1492` (T7 Step 3).

The fixture seeds the legacy case like this:

```ts
await seedEnvelope(cloud, base, undefined as unknown as string,
  { sourceMd: 'wrong.md', sourceMdHash: 'stale' });
```

and `seedEnvelope` reaches the blob only through `writeModelEnvelope`:

```ts
await writeModelEnvelope(side.p, base, {
    sourceMd: `${base}.md`, generatedAt: new Date().toISOString(), sourceSections: ['1. Intro'],
    generatorVersion: GENERATOR_VERSION, model: MODEL_FIXTURE,
    sourceMdHash: mdHash(MD), videoId, ...over,
  } as ModelEnvelopeWrite, side.blob);
```

T7 Step 3 makes `serialize` parse the **write** schema, and `writeModelEnvelope` is its only route to
bytes:

```ts
export const ModelEnvelopeWriteSchema = ModelEnvelopeSchema.extend({ videoId: z.string().min(1) });
function serialize(envelope: ModelEnvelopeWrite): Buffer {
  ModelEnvelopeWriteSchema.parse(envelope);   // fail loud, BEFORE any write
```

`videoId` is present-with-value-`undefined`, not absent, and that is still a required-field violation.
**Measured** against the repo's installed zod (`node_modules/zod/package.json` -> `4.4.3`), Node 22.14.0:

```
THREW: [{"expected":"string","code":"invalid_type","path":["videoId"],
         "message":"Invalid input: expected string, received undefined"}]
```

So the `it` block throws inside its own setup and never reaches an assertion. T8's Interfaces block
declares `ModelEnvelopeWrite` a **Consumed** product of T7 (`:1537`), and T7 is numbered first, so this
is the order an implementer executes.

**Why the plan's own measurement missed it.** The RED row at `:1563` states the conditions:
*"v3 code, T0 exports + T7's **read-side** `videoId` applied, no Step-3 guard"*. Only the read schema
was in place; the write requirement — the whole of T7 — was not. The run that produced "3 failed /
4 passed" was therefore not a run of the code the plan tells the implementer to be standing on.

**Failure scenario, executing literally.** After T7 the implementer runs Step 2 and sees **four** red,
not three. Step 2 says: *"Expected, MEASURED: exactly 3 failures ... If any other case is red, the
fixture is wrong, not the production code."* The instruction is right and the diagnosis it points at
is wrong — 18j4 is red because it cannot construct its subject, not because the guard is misplaced —
so the gate sends the implementer to inspect Step 3, which is correct.

**Fix.** Seed a legacy envelope as raw bytes, which is exactly what T7's own behavior 18j5b does at
plan `:1440`. `MODEL_KEY` is already exported (`model-store.ts:32`):

```ts
import { MODEL_KEY, writeModelEnvelope, readModelEnvelope, type ModelEnvelopeWrite }
  from '@/lib/html-doc/model-store';

/** A pre-1F-a envelope: NO videoId. It cannot go through writeModelEnvelope after T7 — that is the
 *  point of T7 — so it is written as bytes, the same way behavior 18j5b seeds its legacy case. */
async function seedLegacyEnvelope(side: Side, base: string, over = {}): Promise<void> {
  await side.blob.put(side.p, MODEL_KEY(base), Buffer.from(JSON.stringify({
    sourceMd: `${base}.md`, generatedAt: new Date().toISOString(), sourceSections: ['1. Intro'],
    generatorVersion: GENERATOR_VERSION, model: MODEL_FIXTURE, sourceMdHash: mdHash(MD), ...over,
  })), 'application/json');
}
```

and call it from 18j4 in place of `seedEnvelope(cloud, base, undefined as unknown as string, ...)`.
Then update Step 2's expected count only if it changes (it should not: 18j4 passes RED and GREEN).

**Note the guard itself is correct** — `receiverModel.envelope.videoId` is truthiness-tested at
plan `:1819`, so a legacy envelope proceeds. Only the fixture is unbuildable.

---

## BLOCKING 2 — Task 12 Step 6: `ctx` is an undeclared free identifier, and the obvious repair is wrong

**Plan** `:2649-2661` (T12 Step 6) and, in the same file, `:2280-2325` (T11 Step 1).

```ts
it('behavior 26d2 — the SKIP is visible on run 1 AND run 2, and copyToLocal hydrates the paid summary', async () => {
  await prepareSyncCtx(ctx);
  await seedLocalVideoFull(ctx, { position: 3, summaryMd: null });
  await seedCloudVideo(ctx, { position: 7, summaryMd: EVIL, mdBody: '# paid\n' });
```

`ctx` is bound nowhere. Grepping the whole plan for `makeOwnerContext`, `let ctx`, `const ctx` and
`beforeEach` returns: `:1582`/`:1639`/`:1732` (all inside T8's file), `:1036` (an unrelated
`getShareServeContext` snippet in T5) and `:2152` (T10's mock-reset `beforeEach`). There is no `ctx`
for `tests/integration/cloud-sync/adopt-guard.int.test.ts` in either task that writes into it.

Two further gaps in the same file, both of which round 3 would have called by name:

- **No import block exists for `adopt-guard.int.test.ts` at all.** `prepareSyncCtx`, `seedLocalVideoFull`,
  `seedCloudVideo`, `cloudVideoRecord`, `localBlobBytes`, `runSync` and `localBlobStore` are all free.
  T8's block, by contrast, opens with a full import list — the contrast is what makes this look like
  an omission rather than a convention.
- **`RecordingBlobStore` (T11 `:2309`) is never defined.** Its comment says *"A recording decorator,
  file-local, same shape as `FailPromoteBlobStore` (helpers/cloud.ts:168)"* — a description of a class,
  where every other file-local helper in this plan is given as code.

**The obvious repair is wrong, which is why this is Blocking and not Low.** A module-level
`let ctx: Ctx` filled once in `beforeAll` does not work: `prepareSyncCtx` early-returns when the ctx is
already prepared —

```ts
export async function prepareSyncCtx(ctx: Ctx): Promise<void> {
  if (ctx.playlistKey) return;          // tests/integration/helpers/cloud.ts:366-367
```

— so tests 2..n would reuse test 1's playlist key, video id and temp data root. `seedLocalVideoFull`
calls `claimVideoSlot` for the same video id and `seedCloudVideo` inserts a second `videos` row on the
same `(playlist_id, video_id)`, which fails on the unique constraint. Both T11's four cases and T12's
one case share the file, so five tests would interfere.

**Fix.** Give the file the shape T8 already uses correctly at `:1638-1645` — a per-test context:

```ts
// tests/integration/cloud-sync/adopt-guard.int.test.ts
import {
  makeOwnerContext, prepareSyncCtx, seedCloudVideo, seedLocalVideoFull,
  cloudVideoRecord, localBlobBytes, type Ctx,
} from '@/tests/integration/helpers/cloud';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { runSync } from '@/lib/cloud-sync/sync-run';
```

and open each `it` with `const ctx = await makeOwnerContext();` instead of `await prepareSyncCtx(ctx);`
(`seedLocalVideoFull` / `seedCloudVideo` call `prepareSyncCtx` themselves — `helpers/cloud.ts:423`, `:450`).
Write out `RecordingBlobStore` as code, delegating every `BlobStore` member to the inner store and
recording only `get`, mirroring `FailPromoteBlobStore` (`helpers/cloud.ts:168-185`) — including the
`provesAbsence` getter, without which the decorated local store stops proving absence and
`readModelSide` flips `none` to `unknown`.

*(T11 is out of this round's scope; it is named because the defect is in the file T12 Step 6 writes into
and cannot be fixed in T12 alone.)*

---

## HIGH 1 — Task 13, behavior 18: a volume-dependent assertion, placed in the suite CI runs, for the reason that CI runs it

**Plan** `:2685-2692` (the placement decision), `:2710-2713` and `:2788-2803` (the test).

The task moves `additive-protocol.test.ts` out of the integration suite and states the reason
explicitly:

> `test:integration` is **NOT in CI** (`docs/dev-process.md`, *"Not yet in CI"*), so leaving money-path
> guards there means CI never runs them.

`jest.config.ts` `testMatch` includes `<rootDir>/tests/lib/**/*.test.ts`, so `npm test` collects it,
and `.github/workflows/ci.yml` runs `npm test -- --ci --json ...` on `runs-on: ubuntu-latest`.

Behavior 18 then asserts a property of the **volume**, not of the code:

```ts
const md = (await fs.promises.readdir(r.p.indexKey)).filter((n) => n.endsWith('.md'));
expect(md).toEqual([NFC]);
```

The plan knows this. `:2710-2713`:

> `toContain` also passes on a normalization-SENSITIVE volume, where `linkSync` would have created a
> SECOND file instead of getting `EEXIST` — which is the entire behavior under test.
> (Measured on APFS: one file, stored under the NFC name.)

Both halves of that sentence are true, and together they say the outcome differs by filesystem.
**Measured here** (Node 22.14.0, this machine's home directory): writing the NFC name and then
`linkSync`-ing the NFD name throws `EEXIST`, and `readdir` shows one `.md` file — normalization-INSENSITIVE,
as the plan says of APFS. `ubuntu-latest` runners are ext4, which is normalization-sensitive: `linkSync`
succeeds, a second file exists, `md` has two entries, and `toEqual([NFC])` is red.

**Failure scenario.** The implementer runs Step 4 locally on a Mac, sees `9 passed / 9`, commits, opens
the PR, and the gate the placement was chosen for goes red on a test nobody can reproduce. Note the
read-back inside `copyAdditiveVideo` still succeeds on ext4 (the newly linked file holds the same
bytes), so the failure surfaces only in the `readdir` assertion — it looks like a flake, not a
platform fact.

**Fix.** Probe the volume once and assert the outcome that volume actually has. This keeps the
strong `toEqual` on the machine where the aliasing resume is reachable, and keeps CI honest instead of
red:

```ts
/** Is this volume normalization-INSENSITIVE (APFS/HFS+) or SENSITIVE (ext4)? Measured, not assumed:
 *  behavior 18 is a property of the volume's alias relation, and CI runs on ext4. */
function aliasesNfcNfd(dir: string): boolean {
  const a = path.join(dir, 'probe-nfc.tmp');            // written under one form
  fs.writeFileSync(a, 'x');
  try { fs.linkSync(a, path.join(dir, 'probe-nfd.tmp')); return false; }
  catch (e: any) { return e.code === 'EEXIST'; }
  finally { /* both probe files are inside the tmp root the afterEach removes */ }
}
```

with the probe written over an actual NFC/NFD pair of the same name, and then
`expect(md).toEqual(aliasing ? [NFC] : [NFC, NFD].sort())`. Do **not** weaken it to `toContain` — the
plan is right that that hides the behaviour. Whatever form is chosen, say in the comment that behavior
18 is only *observable* on an aliasing volume, so a future reader does not read a green ext4 run as
evidence the resume path works.

---

## MEDIUM 1 — Task 7: the rollout count is 41, and the plan says both 42 and 41

**Plan** `:1401` (table: total **42**, test **39**), `:1406-1409` (per-file list), `:1494`
(*"Step 4: Run `tsc` and fix all **41** call sites ... Expected: **~42** errors"*).

**Recounted under the plan's own stated rule** (`:1394-1397`) — walk every non-`node_modules`
`.ts`/`.tsx`, match `writeModelEnvelope(` / `writeModelEnvelopeWithin(`, skip comment and import lines,
subtract the two declarations in `model-store.ts` (`:46`, `:66`). Raw matches: **43**. Comment or
import lines among them: **0**. Minus the two declarations: **41**.

| File | Count | Lines |
|---|---|---|
| `lib/cloud-sync/sync-run.ts` | 1 | 464 |
| `lib/html-doc/generate.ts` | 1 | 50 |
| `lib/html-doc/serve-doc.ts` | 1 | 174 |
| `tests/lib/html-doc/rerender.test.ts` | 14 | 77, 91, 117, 124, 130, 137, 148, 162, 180, 199, 208, 210, 222, 223 |
| `tests/lib/html-doc/model-store.test.ts` | 8 | 36, 43, 79, 86, 117, 132, 142, 149 |
| `tests/integration/serve-doc-materialize.test.ts` | 5 | 144, 201, 231, 247, 267 |
| `tests/integration/share-route.test.ts` | 4 | 82, 192, 223, 285 |
| `tests/lib/model-store-cloud.test.ts` | 3 | 46, 55, 56 |
| `tests/integration/html-download.test.ts` | 2 | 257, 282 |
| `tests/integration/pdf-cloud.test.ts` | 1 | 266 |
| `tests/e2e/cloud.setup.ts` | 1 | 114 |

**Total 41 — production 3, test 38, files 11.** The plan's production row (3) and file count (11) are
right. Its **test row (39) and total (42) are wrong, and its own per-file list proves it**:
14+8+5+4+3+2+1+1 = **38**, not 39.

The round-3 false positive is correctly excluded: `tests/lib/model-store-cloud.test.ts:52` is
`it('writeModelEnvelope overwrites...` — a title, with a space where the rule requires `(`. The plan
cites that file as `model-store-cloud.test.ts`; note the path is `tests/lib/`, not
`tests/integration/` as the round-3 report had it.

**Failure scenario.** At Step 4 `npx tsc --noEmit` names 41 sites. The step heading says 41 and the
sentence beside it says ~42, so the implementer looks for a 42nd that does not exist — which is
precisely the cost this count was re-done twice to avoid.

**Fix.** Table row -> total **41**, test **38**. `:1409` -> *"Expect `tsc` to name all 41"*.

---

## LOW 1 — the wrong noun IS repeated elsewhere in the plan

Round 3 Codex M1 asked for "iterations" -> "assertions" on the behavior-27 sweep. It is fixed at the
three sites that state the measurement: `:47`, `:952-954` and `:962-964` all now read
*"4,448,256 loop iterations ... 3,479,131 non-empty slug assertions ... 969,125 empty slugs skipped"*.
The arithmetic checks out: valid code points 1,112,064 x 4 title forms = 4,448,256, and
3,479,131 + 969,125 = 4,448,256.

It is **not** fixed in the Self-Review's own disposition tables:

- `:3326` — *"T4's behavior 27 is now **stride 1** (3,479,131 iterations, executed)"*
- `:3359` — *"**FIXED** — stride 1, executed, 3,479,131 iterations"*

`:3394` states it correctly three rows below. A disposition row that repeats the error whose fix it
records is the shape that lets it come back. **Fix:** both rows -> "non-empty slug assertions".

## LOW 2 — round 3's line-reference fix took; four neighbours in the same table did not

The named finding is fixed: T0 Step 6 (`:268`) now says `tests/integration/helpers/cloud.ts:131` and
quotes it verbatim; `:131` is indeed `syncDeps(opts: {...}): SyncDeps {`. Confirmed.

Others in the same inventory table were not re-checked:

| Plan | Claims | Actually |
|---|---|---|
| `:168` | `Ctx.spendLedgerTotal()` at `helpers/cloud.ts:157` | declared `:153`; `:157` is `if (error) throw error;` |
| `:169` | `cloudVideoRecord` `:468`, `localVideoRecord` `:473` | `:471` and `:476` |
| `:178` | `seedVideo` at `helpers/cloud.ts:378` | `:296`; `:378` is `buildVideoData`'s docstring |
| `:283` | the `Ctx` declaration of `syncDeps` at `:66` | `:69`; `:66` is a mid-docstring line |

Each costs an implementer one scroll, not a defect — but the table's job is to stop exactly that.

## LOW 3 — two "verbatim today" quotes are not verbatim

T12 Step 5(a) (`:2579-2595`) presents `sync-run.ts:739-757` as verbatim. The real block is 19 lines;
the quote silently drops the comment blocks at `:740-741` and `:745-748`. Every code line, and their
order, is accurate — but the plan marks elisions explicitly elsewhere (`:2987`,
*"...a 9-line comment explaining why put() and not promote()..."*), so an unmarked one reads as a
discrepancy against the file. Same class: T0 Step 6's quote of `:131` elides with a bare `...`.
**Fix:** mark the elisions.

## LOW 4 — no step adds the `isServableSummaryKey` import to the two files that call it

T10 Step 3 (`:2229`), T11 Step 3 (`:2358`) and T12 Step 5(b) (`:2632`) all call `isServableSummaryKey`
inside `lib/job-queue/summary-handler.ts` and `lib/cloud-sync/sync-run.ts`. Neither file imports it
today, and no step says to add the import. `tsc` catches it in seconds, so this is Low — but T10 does
bother to note *"`NonRetryableError` (`lib/job-queue/errors`) is already imported at `:4`"*, which makes
the omission of the one import that is **not** already there conspicuous.

---

## What was checked and holds

Recorded so the next round does not re-derive it.

**Task 8 — imports and free identifiers.** All eight imports resolve.
`@/tests/integration/helpers/cloud` is the idiom the sibling `cloud-sync/e2e.int.test.ts:15-18` uses and
`moduleNameMapper: {'^@/(.*)$': '<rootDir>/$1'}` maps it; round 3's Blocking (`./helpers/cloud` from one
directory too deep) is gone. Every one of round 3's eleven named undeclared symbols is now bound:
`SupabaseMetadataStore`, `SupabaseBlobStore`, `ARTIFACTS_BUCKET`, `ModelEnvelopeWrite` imported;
`MODEL_FIXTURE` declared at `:1606`; `localVideoRecord` imported and real (`helpers/cloud.ts:476`);
`lv` declared inside each `it`; `winner`, `loser`, `cloudSide`, `localSide` no longer appear. Hunting
for ones round 3 missed found none — `MD`, `sides`, `seedEnvelope`, `twoSided`, `Ctx`, `Side`,
`GENERATOR_VERSION`, `mdHash`, `reconcileCloudBase`, `readModelEnvelope` all bound.
`MODEL_FIXTURE` satisfies `MagazineModelSchema` (`lib/html-doc/types.ts:34-47`: strict, >=1 section,
3-7 bullets — it has 1 and 3). `sides()` matches `Side` (`sync-run.ts:62`). The `reconcileCloudBase`
call matches `reconcile-serial.ts:166-174` argument for argument, the zero-parameter `inFlightJob`
arrow is assignable to `InFlightJobProbe` (`:61-64`), and `toMatchObject({ok,action,from,to})` matches
the `relocated` variant at `:71`.

**Task 8 — do the assertions bite?** 18j SHIP: remove the guard and the ship overwrites, so
`after.videoId` is the row id, not `'OTHER'` — RED. 18j DELETE: remove the guard and `decideCompanion`
returns `deleteReceiverModel` (traced: sender hash `'sender-stale'` and receiver hash `'receiver-stale'`
both miss `winnerMdHash`, so `provablyStale` at `companion.ts:151-153` is true), the blob is deleted,
and `(await readModelEnvelope(...))!.videoId` throws — RED. This is the case that catches a ship-arm-only
placement, and v3 did not have it. 18j6: drop `videoId: winnerVideo.id` from the ship write (`:1834`)
and the stamp is `'SENDER-WROTE-THIS'` — RED. 18j2 and 18j4 are controls (they must stay green), which
is correct. 18j3/18j7 is a preservation assertion the plan itself says passes both ways; the mutation
that reddens it is dropping `MODEL_KEY(base)` from `paidKeysUnder` (`reconcile-serial.ts:98`).

**Task 10.** Every import resolves. `HandlerCtx` matches `handler-context.ts:5-10` field for field. The
four file-local helpers match `summary-handler.test.ts:37-95`, including the `client: any` on
`seedPlaylist`. The quoted `summary-handler.ts:95-98` is verbatim, and `:97` is the blank line the
insertion goes into. `slugify('unservable by fiat')` is `unservable-by-fiat` (`lib/slugify.ts`: lowercase,
non-letter/number runs to `-`), so the sentinel matches `0001_unservable-by-fiat.md` and the control
title `'My Test Video'` does not. Critically, the `jest.mock` targets the right module:
T4 puts `isServableSummaryKey` in `lib/html-doc/assert-cloud-summary-md-key.ts` (`:798`, `:881`), which
is what the handler will import.
**Does it bite?** Remove the Step-3 guard: the handler runs to completion, `err` is `null` and both
`not.toHaveBeenCalled()` assertions fail — three assertions red. Throw a bare `Error` instead of
`NonRetryableError` and `toBeInstanceOf` goes red. Move the guard below `summaryCore` and the two
provider assertions go red. The control case is what stops a blanket mock passing the first test for
the wrong reason. The vacuous `ledgerTotal` delta is genuinely gone and the replacement observes the
provider call, which is the thing the placement prevents.

**Task 12 Step 1.** `store` (`:55`), `vid` (`:56`), `cloudReplica` (`:70`), `read` (`:84`), `rowOf`
(`:86`) and `noJobs` (`:32`) all exist in `tests/lib/cloud-sync/reconcile-serial.test.ts`, with the
signatures the cells use. Every predicate verdict in the four-cell table was **re-measured** by running
the T4 Step-3 predicate over the exact keys:

```
true   9cp   007_ok.md              false 18cp   003_nested/evil.md
true 131cp   007_<124a>.md          false 132cp   1000_<124a>.md
false 137cp   007_<130a>.md         true   9cp   003_ok.md
false 137cp   003_<130a>.md
```

`applySerial` / `padSerial` (`lib/serial-filename.ts`) produce the `to` bases the table claims, including
`padSerial(1000) === '1000'` — so 26d3's one-code-point overflow is real and needs no invented character.
All four cells reach the insertion point: divergence is genuine, the holder scan finds nothing (single
video, same id), and `artifacts` is `{summaryMd}` only, so the `unsupported-artifacts` refusal above does
not fire. The `origin` derivation is truthiness, matching the ternary at `:152-154` it mirrors.
**Do they bite?** Drop the `oldServable` arm and 26d/26d3 relocate; drop the both-unservable arm and 26d2
relocates; make the guard a blanket refusal and 26d4 goes red. Each cell has a distinct killer.

**Task 12 Step 4.** The "exactly one existing case flips" claim was re-derived rather than taken: I
enumerated every `reconcileCloudBase` case in the file and computed both bases. Only
`:406` (*"moves a bare digDeeperMd belonging to a directory-qualified summary"*, `summaryMd:
'raw/007_alpha.md'` -> `'raw/003_alpha.md'`) has an unservable pair — both contain `/`. Every other case
uses `003_`/`007_alpha`-shaped bases, all servable. One flip. Confirmed.

**Task 12 Step 5.** `sync-run.ts:614` is `const base = manifest.videos[id];` exactly, `cv` is bound at
`:613`, `report` is in scope, and the insertion is inside the per-video `try` (opens `:611`, caught
`:812-814`). The re-derivation is genuinely on `cv` and not on `rec`, which is the round-1 H4 fix: I
traced run 2 of Step 6's fixture — `transferClassA` writes the **loser** (local), `cv.summaryMd` stays
`'nested/evil.md'`, so the row-derived error fires again. Mutating it back to a `rec`-derived push makes
`for (const r of [first, second])` red on `second`, which is exactly the intended detector. Step 6's
fixture also reaches `skipped-unservable` as claimed: with local serial 3 and no local MD,
`describeDivergence` gives `from='nested/evil'`, `to='nested/003_evil'`, both unservable (measured above).

**Task 13 — identifiers.** `LocalFsBlobStore` is an exported class (`local-blob-store.ts:7`);
`InMemoryBlobStore.failReads(key, cause?)` exists (`in-memory-blob-store.ts:60`); `BlobRead` is exported
(`blob-store.ts:10-13`) and `AbsentOnReadBack`'s zero-parameter `tryGet` override is assignable;
`LocalFsMetadataStore.claimVideoSlot(p, id, serial)` takes the three arguments `loserSide` passes
(`:23`); `localPrincipal(indexKey)` makes `r.p.indexKey` the temp directory, so
`fs.promises.readdir(r.p.indexKey)` is the right path. The `copyAdditiveVideo` quote at `:2916-2928` and
the signature at `:2262` both match `sync-run.ts:221-225` and `:260-270` verbatim. `putStaged` writes
under `_staging/<uuid>/`, a directory, so the staging file cannot pollute the `.md` filter even before
T6's staging-tree removal.

**Task 13 Step 5 — executed.** Transcribed to a scratch file outside the repo, `ROOT` repointed:
`--self-test` prints **10/10 ok**, exit 0. `main()` with `encode-segment.ts` absent prints
`CANNOT READ ... -> TREAT THIS AS NOT RUN`, exit **2** — the fail-loud behaviour the docstring claims,
verified rather than asserted. Against the real spec, `SECTION_4` matches (section 4 spans spec
`:1796-1835`, section 5 begins `:1836`) and `GATE_CLASS` finds **exactly one** class, `A-Za-z0-9._-`,
expanding to 65 characters. The gate sentence at spec `:1804-1805` is quoted correctly. Section 3.2's
`SAFE = /^[A-Za-z0-9._-]+$/` is at spec `:289` as the plan says, and `GATE_CLASS` correctly does not
match it (no backtick immediately before `^[`) — the tautology guard works. T1's declaration
(plan `:382`) is `export const SAFE = /^[A-Za-z0-9._-]+$/;`, which `JS_SAFE` matches, so once T1 lands
the script reaches both subjects. This is the strongest artifact in the four blocks.

**Task 13 — do the assertions bite?** 18b/18c: revert `promoteIfAbsent` to `promote` and the newcomer
overwrites, so `toBe('occupant')` goes red. 18c2: treat a read-back `absent` as a resume and the throw
disappears. 19 (both cases): treat `unreadable` as absent and the throw disappears. 18g/18h: replace
`canonicallyEqualName` with `===` and the NFD-owned case in 18i/18k refuses instead of overwriting.
18h-occupied: drop the guard and `'someone else'` is destroyed. Behavior 18 is the exception — see
HIGH 1: it is red on a normalization-sensitive volume with no mutation at all.

---

NOT CONVERGED

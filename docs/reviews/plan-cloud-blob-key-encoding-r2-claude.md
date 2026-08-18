# Plan review — `2026-08-15-cloud-blob-key-encoding.md`, round 2, Claude half

**Subject:** the #36 implementation plan, **v2** (16 tasks, 87 steps), working tree, branch
`fix/cloud-blob-key-encoding`, plan commit `6e86fc3`. No implementation code exists yet.
**Question asked:** is this plan executable, literally, task by task, by an engineer with no context —
and does executing it leave the tree green between tasks?

**Verdict: NOT CONVERGED.** 3 Blocking, 7 High, 8 Medium, 6 Low.

v2 is a large, honest improvement. **Every round-1 Blocking that was about a specific piece of code is
genuinely closed, and I measured four of them rather than reading them** (see *What holds up* — it is
longer than usual because calibration matters more than finding count here). T1's encoder is now
correct end to end; T2's `objectKey`/`list` arithmetic is right for all three prefix shapes; T4's
predicate passes every behavior it claims; T13's brand-new Class-A ownership guard — the money path —
has the correct signature, the correct argument order at both call sites, and the correct `tryGet`
narrowing. That step is the best-verified thing in the document.

What v2 did not do is repeat round 1's own method on the parts it rewrote. Round 1's root cause was
*"not one snippet was checked against the code it would live in."* v2 added that as a Global
Constraint and applied it to the code it was **fixing**. It did not apply it to the code it was
**adding**: the new T8 refusal calls a field `decideCompanion` does not return, four tasks' tests call
functions `sync-run.ts` does not export, and thirteen verification commands run zero tests.

**Method note.** `grep` here is ugrep and returns nothing silently, so every existence claim comes
from `python3` + `os.walk` + `re` over every `.ts`/`.tsx` outside
`node_modules`/`.git`/`.next`/`dist`/`build`, or from the Read tool. Every number is counted and I say
how. Six claims below are backed by **executed** measurements (Node 22.14.0 / the repo's own jest),
marked **MEASURED**. I modified no tracked file.

---

## BLOCKING

### B1 — thirteen verification commands run ZERO tests. Round-1 B1's second half is not fixed. T2, T5, T8, T9, T10, T11, T13, T14.

The Vitest half of round-1 B1 is fully fixed: **0** `npx vitest` occurrences remain, and the one
surviving `vi.fn()` string is inside the Self-Review table describing the fix (line 1673), not in a
test. The second half — *"the two suites need different commands, and the plan uses one"* — was not.

`jest.config.ts` `testMatch` is `tests/lib/**`, `tests/api/**`, `tests/scripts/**`,
`tests/smoke.test.ts`, `tests/components/**`. It **excludes `tests/integration/`**, which lives in
`jest.integration.config.ts` with the `globalSetup` that applies pending migrations.

**MEASURED**, in this repo, just now:

```
$ npx jest tests/integration/share-route.test.ts
No tests found, exiting with code 1
  Pattern: tests/integration/share-route.test.ts - 0 matches
```

Counted over the plan: **13** commands of the form `npx jest tests/integration/…` (lines 453, 707,
723, 975, 1018, 1076, 1116, 1153, 1173, 1227, 1252, 1432, 1643) and **0** occurrences of
`npm run test:integration`. The **6** bare `npx jest` commands (lines 822, 920, 1116, 1252, 1373,
1588) and the **2** real `npm test` commands mean "the whole suite" and run the unit half only. **The
integration suite is never executed anywhere in this plan.**

**Failure scenario.** T5 Step 2 tells the implementer to run
`npx jest tests/integration/share-route.test.ts -t 'behavior 21'` and expect FAIL. They get exit 1 and
"No tests found" — which reads as the intended red. They write the guard, run Step 4, get exit 1
again, and now have a red they cannot interpret. Worse for T2 Step 6 and T14 Step 2, which are the
*commit* steps: an implementer who adds `--passWithNoTests` (jest's own suggestion, printed in the
error) gets exit 0 and commits with **every integration behavior unverified**. That set includes
behaviors 6, 7, 11, 13, 21, 26c–26c4, 25, 26, 26b, 26e, 26f, 18–19 and all of Task 14 — i.e. the
entire proof that backlog #36 is fixed.

**Fix.** Replace all 13 with `npm run test:integration -- <path>` (it carries `--config
jest.integration.config.ts --runInBand`; the trailing `--` is required to pass the path through npm).
Where a step means "everything", write **both** commands and say the integration half needs the local
Supabase stack up. Round 1 gave this fix verbatim; only its first half was applied.

---

### B2 — T8 Step 3 reads `decision.receiverEnvelope`. `decideCompanion` does not return a field by that name. This is `rawList` again, in the money path.

Plan, T8 Step 3 (lines 990-1000):

```ts
const envelope = decision.receiverEnvelope;   // 'none' | 'unknown' | ModelEnvelope
if (envelope !== 'none' && envelope !== 'unknown'
    && envelope.videoId && envelope.videoId !== winnerVideo.id) {
```

Repo, `lib/cloud-sync/companion.ts:25-28` — the complete return type:

```ts
export type CompanionAction =
  | { kind: 'ship'; envelope: ModelEnvelope }
  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
```

`receiverEnvelope` appears **0** times in the repo. `decideCompanion` takes `receiverModel` as an
*input* (`companion.ts:101`) and returns none of it. The comment's claimed shape is wrong too: the
receiver read is `ModelRead` (`companion.ts:12-15`), a **tagged union** —
`{kind:'envelope';envelope}` / `{kind:'none'}` / `{kind:'unknown'}` — so `envelope !== 'none'` would
never be false even if the field existed, and `envelope.videoId` would be a type error on the tag
object rather than the envelope.

**Second half, and it is the round-1 H3 defect surviving its own fix.** The snippet's last line is

```ts
await writeModelEnvelope(loser.p, base, { ...decision.envelope, videoId: winnerVideo.id }, loser.blob);
```

`decision.envelope` exists only on `kind === 'ship'`. So the block **is** the ship arm — which is
exactly where round-1 H3 said it must not be. The comment three lines above it says *"the refusal must
gate BOTH the ship AND the delete at :475"*, and then the code gates the ship only. An implementer
copying the snippet leaves `loser.blob.delete(loser.p, MODEL_KEY(base))` at `sync-run.ts:475`
reachable with the ownership mismatch unexamined — the paid model the credential exists to protect is
deleted, and T8's own assertion `expect(loserBlob.delete).not.toHaveBeenCalled()` fails. **H3 is fixed
in prose and unfixed in code.**

The Global Constraint at line 45 says *"EVERY code snippet below was verified against the repo at
plan-v2 time."* This snippet is the money-path refusal and it is the one that was not.

**Fix.** Hoist the check above `decideCompanion` at `sync-run.ts:454`, derive it from `receiverModel`
(already read honestly at `:451-453` via `readModelSide`), and write it against the real union:

```ts
// ABOVE decideCompanion at :454, so it covers ship, noop AND deleteReceiverModel.
if (receiverModel.kind === 'envelope'
    && receiverModel.envelope.videoId
    && receiverModel.envelope.videoId !== winnerVideo.id) {
  return { shareNeedsOwnerServe: true,
           error: `companion refused: envelope videoId ${receiverModel.envelope.videoId}, `
                + `row ${winnerVideo.id}` };
}
```

and state that `kind: 'unknown'` must not be read as "no ownership claim". The plan's *reasoning*
about not re-reading with `readModelEnvelope` is correct and worth keeping — it just needs to name the
variable that actually holds the honest read.

---

### B3 — T8, T9, T11, T12 and T13 test functions `sync-run.ts` does not export, and Task 0's inventory asserts the opposite. Round-1 H1's sharper half was resolved WRONG, not deferred.

`lib/cloud-sync/sync-run.ts` has exactly **three** exports, counted by reading every line starting
with `export`:

| Line | Export |
|---|---|
| 40 | `export interface SyncDeps` |
| 51 | `export interface SyncReport` |
| 547 | `export async function runSync(deps: SyncDeps, opts: { playlistKey?: string } = {})` |

Everything the plan's tests call directly is **module-private**:

| Called by | Symbol | Reality |
|---|---|---|
| T8 Step 1 (x4), Step 4 | `companionTransfer` | `sync-run.ts:444`, not exported |
| T13 Step 5 (x4) | `transferClassA` | `sync-run.ts:371`, not exported |
| T13 Step 1 (x4) | `copyAdditiveVideo` | `sync-run.ts:221`, not exported |
| T9 26c4 (x2), T12 | `readVideo` | `sync-run.ts:80`, not exported. The *exported* `readVideo` is `lib/storage/worker-persistence.ts:32` and takes `(client, playlistId, videoId)` — a different function |
| T9 26c3, T11 26/26b/26f, T12 26d2 | `runSync` | exported, but its signature is `(deps: SyncDeps, opts)`. The plan calls it as `runSync({direction, key})`, `runSync({local, cloud})`, `runSync({…, localBlob: spyStore(…)})` — three shapes, none of them `SyncDeps` |

Round 1 filed all five of these under H1 ("Present, but not what the plan assumes — the sharper
half"). v2's Task 0 table (lines 84-90) resolves them as:

> `readVideo`, `runSync`, `applySerial`, `assertLogicalKey`, `localPrincipal`, `collectObjectPaths` | ✅ production

and the Self-Review records **"H1 | 7 helpers missing | FIXED — new Task 0"**. The seven *absent*
helpers did get a task. The five *colliding* names were resolved in the wrong direction, and that is
worse than v1: v1 left an implementer to discover the collision; v2 hands them a table that says the
symbol exists in production, so they import it, get a type error, and have no guidance at all.
(`applySerial` `lib/serial-filename.ts:20`, `assertLogicalKey` `lib/storage/blob-store.ts:87` and
`localPrincipal` `lib/storage/principal.ts:12` **are** correctly exported — the table is right about
three of six. `collectObjectPaths` is a private class method, correct for T2's purpose and
uncallable from a test.)

**Failure scenario.** T8 Step 1 is the first line an implementer types for the money-path task:
`import { companionTransfer } from '@/lib/cloud-sync/sync-run'` — TS2459, no export by that name.
Nothing in the plan says whether to export it, extract it, or drive it through `runSync`, and the
three choices have very different blast radii (`companionTransfer` is currently free to change because
nothing outside the module sees it).

**Fix.** Decide once and write it into Task 0: either add a step that exports
`companionTransfer`, `transferClassA`, `copyAdditiveVideo` and `readVideo` with a one-line
"exported for test" note, or give Task 0 a `runSync` **test wrapper** under a different name that
builds a real `SyncDeps` and returns the report — and then rewrite T9/T11/T12's calls against that
wrapper's signature. Correct the Task 0 table: `readVideo` and `runSync` belong in a third column,
"exists but is not what the tests assume".

---

## HIGH

### H1 — behavior 20's instrument is created and never pointed at its subject. `main()` cannot pass today, and no step makes it able to.

T13 Step 6 now gives `scripts/check-encoder-gate-sql.py` a full body — the round-1 Blocking is
addressed on that axis, and **I ran the body: `--self-test` prints 4 ok and exits 0**, and its
`charset()` expands `A-Za-z0-9._-` to exactly **65** characters. The function is correct.

But its `SQL_CLASS = re.compile(r"~\s*'\^\[([^\]]+)\]\+\$'")` has nothing to match. **MEASURED** over
`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md`: `SQL_CLASS` finds **0**
matches, and there is **0** occurrence of any `~ '…'` regex operator in the file. §4 states its
predicate in prose at **spec line 1805** — "not matching `` `^[A-Za-z0-9._-]+$` ``" — inside backticks
in a sentence, and §4.1 records that the gate already ran against prod on 2026-08-14. There is no
`.sql` file holding it either (searched every `.sql`/`.py`/`.md`/`.ts` for `storage.objects`).

So `main()` returns **2** — "no SQL character class found in the gate -> NOT RUN". The plan says that
is correct and *"Fix the SQL, not the script"*. Nothing fixes the SQL: §4 lives in the approved spec,
no task step edits the spec, and the Global Constraints ratchet loop does not include this script.
And **T13 Step 7's only invocation is `--self-test`**, which exits 0 without reading either subject.

An implementer therefore creates the file, sees green, and ticks behavior 20 — the instrument whose
entire job is proving the §4 predicate is not a hand-copied character class. That is a green check
over the wrong subject, which is the shape `portable-practices.md` §1/§2 record, and it is the same
outcome round 1 filed as Blocking against the docstring-only version. Rated High rather than Blocking
only because the script itself is correct and would fail loudly *if it were ever run*.

**Fix.** Add a T13 step that rewrites §4's gate to carry an executable SQL predicate in a fenced block
(`… where … !~ '^[A-Za-z0-9._-]+$'`), then make Step 7 run `python3 scripts/check-encoder-gate-sql.py`
**by exit code**, with `--self-test` as an additional check rather than the only one. Add the script
to the Global Constraints ratchet loop.

### H2 — no task that changes a type runs `tsc`, and jest here is SWC, which does not type-check. MEASURED.

**MEASURED**, `node_modules/next/dist/build/jest/jest.js`:

```js
transform: {
    // Use SWC to compile tests
    '^.+\\.(js|jsx|ts|tsx|mjs)$': [ require.resolve('../swc/jest-transformer'), … ],
```

`jest.config.ts` is built by `nextJest`, so both suites transpile with SWC and **strip types without
checking them**. `npx jest` and `npm test` cannot go red on a type error. `npx tsc --noEmit` appears
in exactly two places in the plan: T7 Step 4/6 and T13 Step 7.

The tasks that change a type and never run it:

- **T6** adds `promoteIfAbsent` to the `BlobStore` **interface**. Counted: **7** implementers —
  `SupabaseBlobStore`, `LocalFsBlobStore`, `InMemoryBlobStore`, plus `UnreadableModelBlobStore`
  (`tests/integration/serve-model-unreadable.test.ts:57`), `FailPromoteBlobStore`
  (`tests/integration/helpers/cloud.ts:168`), `FailModelPutBlobStore` (`:191`) and the object literal
  at `tests/lib/storage/consistency.test.ts:38`. T6 Step 5's text says *"**Behavior 18d5** — if any
  `BlobStore` implementer … does not implement or forward `promoteIfAbsent`, `tsc` will say so"* — and
  its command is `npx jest tests/lib/storage/ && npx jest`. **The named mechanism is never invoked.**
  T6 Step 6 then commits a tree that does not compile while its tests are green.
- **T12** adds two variants to `SerialReconcileResult`. Round-1 M6's only mitigation was "tsc will
  flag it"; T12 Step 4 runs `npx jest tests/lib/cloud-sync/ && npx jest`. The mitigation is void.
- **T2** rewrites `objectKey`/`list`/`deletePrefix`; **T9** changes a function's name and signature;
  **T11** replaces four lines in `runSync`. None runs `tsc`.

CI does run `tsc --noEmit`, so this is caught eventually — but the question the brief asks is whether
the tree is green *between tasks*, and for T6 and T12 the answer is no.

**Fix.** Prefix every task's final verification with `npx tsc --noEmit &&`. It is one edit per task and
it restores the enforcement mechanism 18d5 and M6 both name.

### H3 — four of T8's five tests assert `res.shipped`, which `companionTransfer` does not return, against an Interfaces block that says the contract is unchanged.

`sync-run.ts:444-446`:

```ts
async function companionTransfer(
  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
): Promise<{ shareNeedsOwnerServe: boolean; error?: string }> {
```

T8 Step 1 and Step 4 assert `.shipped` in behaviors 18j2, 18j4, 18j3+18j7 (`expect((await
companionTransfer(…)).shipped).toBe(true)`), and T8's Interfaces block says *"no new exports.
`companionTransfer` keeps its **never-throws** contract."* Adding a return field is a contract change
that no step makes, and the three `ship` return sites (`:465`, `:467`, `:473`, `:476`) would all need
it.

**Fix.** Either add a step widening the return to `{ shareNeedsOwnerServe: boolean; shipped: boolean;
error?: string }` and update the four return sites and the caller at `:801-805`, or rewrite the three
assertions against something already observable — `readModelEnvelope(loser.p, base, loser.blob)`
returning the shipped envelope, which behavior 18j6 already does correctly.

### H4 — T9 and T11 assert that `runSync` REJECTS. It cannot: every per-video throw is caught and turned into `report.errors`.

`sync-run.ts:610-814` — the per-video loop:

```ts
for (const id of await enumerateVideoIds(…)) {
  try {
    …
  } catch (e: any) {
    report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
  }
}
```

`runSync` then returns the report at `:818`. Four assertions are therefore unsatisfiable:

- T9 26c3: `await expect(runSync({direction:'copyToCloud', key:'nested/evil.md'})).rejects.toThrow();`
- T11 26: `await expect(runSync({local:{summaryMd:'nested/evil.md'}, cloud:null})).rejects.toThrow(/rename/i);`
- T11 26b: `await expect(runSync({ … })).rejects.toThrow();` — "identical, forever"
- T9 26c3's second arm: `.resolves.toBeDefined()` — this one is trivially true either way, so the
  row cannot distinguish the two directions it was written to distinguish (round-16 B1's whole point).

**Why this is High and not Low.** The natural way to make a red test green is to let the throw escape
the per-video catch. That aborts the entire sync run for every *other* video in the playlist, which is
the behavior `:812-813` exists to prevent and which the same file's comment at `:456-462` argues
against at length. The plan pushes an implementer toward a behavior change nobody specified.

**Fix.** Assert against `report.errors` — which is what T12's 26d2 already does correctly:
`expect(report.errors).toContainEqual(expect.objectContaining({ videoId: ID, message:
expect.stringMatching(/rename/i) }))`. Keep `rejects.toThrow` only for the direct calls to
`copyAdditiveVideo` / `transferClassA`, which really do throw.

### H5 — round-1 H4 is marked FIXED, and the fix is a comment describing a mechanism the code does not implement.

T12 Step 3's sync-run snippet (lines 1355-1363) now carries the right diagnosis:

> ⚠ Round-1 H4: this arm returns ok:true, so the caller ADVANCES THE BASELINE and run 2 sees an agreed
> video … The report entry must therefore be emitted from a state the baseline does not erase:
> **re-derive it each run from the row itself** (cloud summaryMd unservable AND local has none), not
> from this branch having been taken.

The code immediately below the comment does the thing the comment forbids:

```ts
if (rec.ok && rec.action === 'skipped-unservable') {
  report.errors.push({ videoId: id, message: `base relocation skipped: …` });
}
```

That pushes *from this branch having been taken*. And 26d2's test (lines 1288-1296) still runs
`runSync` exactly **once** and asserts `report.errors` contains the entry — round 1's specific ask was
a **second-run** assertion, which is what makes the decay visible. Traced again against the current
code, the decay is unchanged: after run 1 hydrates the artifact locally, `describeDivergence`
(`reconcile-serial.ts:147-156`) computes `from === to`, `reconcileCloudBase` returns
`{ok:true, action:'agreed'}` at `:184`, and `report.errors` gets nothing on every subsequent run.

The Self-Review row reads **"H4 | SKIP visible one run then silent | FIXED — re-derived per run, not
from the branch"**. Nothing re-derives.

**Fix.** Either implement what the comment specifies (a check at the seam or in the report that fires
whenever a cloud row's `summaryMd` fails `isServableSummaryKey` and the local row has none) and add
the second-run assertion to 26d2, or amend the comment to say the signal is deliberately one-shot
because the artifact has been hydrated locally — and delete the word "visibly" from Step 3's
`// SKIP, visibly.`

### H6 — Task 0's inventory is incomplete: six more symbols the tests invoke are in neither column. Task 14 is built out of five, of which Task 0 creates two.

Task 0's table lists 7 absent helpers plus `canonicallyEqualName`. Round 1 listed **ten**. Counted
again with `os.walk` + two patterns (declaration-shaped *and* bare-occurrence, so class methods cannot
produce a false negative):

| Symbol | Used by | Occurrences in repo | In Task 0's table? |
|---|---|---|---|
| `serveSummary` | T14, 4 tests | **0** | **no** |
| `readdirNames` | T13 Step 1 | **0** | **no** |
| `runSummaryJob` | T10, the only test | **0** | **no** |
| `EXPECTED_ONE_SUMMARY_COST` | T14 behavior 14 | **0** | **no** |
| `ingest` | T14, 3 tests | 132 (all unrelated: `ingest-*` routes, `ingestPlaylist`, prose) — **0** as a bare callable | **no** |
| `seed` | T13 Step 1, Step 5 | ambiguous; `seedVideo`/`seedPlaylist`/`seedSummaryBlob` exist, bare `seed` does not | **no** |

T10's single test is `runSummaryJob({ title: 'x'.repeat(400), gemini })`. The real entry point is
`makeSummaryHandler(serviceClient): JobHandler` (`lib/job-queue/summary-handler.ts:50`) — the only
export in that file besides `MAX_DURATION_SECONDS`. There is no way to pass a `gemini` mock through
it as written.

**Task 14 is the task that proves backlog #36 is actually fixed**, and it is built out of `ingest`,
`ingestLocal`, `serveSummary`, `ledgerTotal` and `EXPECTED_ONE_SUMMARY_COST`. Task 0 creates two of
those five.

**Fix.** Extend Task 0's table and Step 6 to cover all of them, with signatures — `serveSummary` and
`ingest` in particular need to say which HTTP surface or which pipeline entry point they drive, and
`EXPECTED_ONE_SUMMARY_COST` needs to say whether it is a constant or read from `guardrail_config`.

### H7 — `fakeStoreHolding` returns a `BlobStore`, so T2's three unit tests would exercise the fake instead of `SupabaseBlobStore.list`.

Task 0's Interfaces block: `fakeStoreHolding(keys: string[]): BlobStore`. T2 Step 1 then does

```ts
const store = fakeStoreHolding([`dig/${base}/s1.r2.md`]);
expect(await store.list(P, `dig/${base}/`)).toEqual([`dig/${base}/s1.r2.md`]);
```

If `fakeStoreHolding` returns a `BlobStore`, `store.list` is the **fake's** `list`, and the code under
test — the encoder wiring added in T2 Step 3 — is never executed. Behaviors 8, 9, 10 and 12 would pass
against a fixture, which is the exact failure class this project has filed repeatedly.

The repo already contains the right ancestor and it has the opposite shape.
`tests/lib/storage/blob-store-list.test.ts:35-38`:

```ts
function fakeClient(entriesByDir: Record<string, Array<{ name: string; id: string | null }>>) {
  const list = jest.fn(async (dirPath: string) => ({ data: entriesByDir[dirPath] ?? [], error: null }));
  return { client: { storage: { from: () => ({ list }) } }, list };
}
…
const store = new SupabaseBlobStore(client as never, 'artifacts');
```

It fakes the **client** and injects it into a real store — that is what makes it a test of the seam.

There is a second, related ambiguity Task 0 Step 5's `/* … */` body does not settle: are the `keys`
**logical** or **physical**? Behavior 9's fixture (`'dig/003_x/lost=hABCDEFGHIJKLMNOPQRSTUV.md'`) reads
as physical; behaviors 8/12's (`'dig/003_한국어/s1.r2.md'`) and behavior 10's (`'dig/003_a=b/…'`) only
work if the fake **encodes** what it is given, because the physical dir for those prefixes is
`dig/003_=h…/` and `dig/003_a=h…/`. All three fixtures pass under the "holds logical keys, stores them
encoded" reading and none passes under the "holds physical paths" reading, so the intent is
recoverable — but it is not written down, and it is the difference between a real test and a
tautology.

**Fix.** Change the signature to `fakeStoreHolding(logicalKeys: string[]): SupabaseBlobStore`, state
that it builds the physical layout by running `encodeSegment` over each key and wires the result into
a `fakeClient`-shaped stub keyed on physical dir paths, and point Task 0 Step 5 at
`blob-store-list.test.ts:35` as the thing to generalise.

---

## MEDIUM

The first four are the round-1 items v2 deferred. **All six deferrals are genuine — none is an
omission dressed as one** — but two degraded, and one gained a new error.

### M1 — round-1 M3 (T6's local `promoteIfAbsent`): DEFERRED, verified still broken, unchanged.

T6 Step 3 still ends `rmSync(this.stagingRoot(ref), …)`. Counted: `stagingRoot` has **0** occurrences
in the repo. `lib/storage/local/local-blob-store.ts:1` is
`import fs from 'fs'; import path from 'path'; import crypto from 'crypto';` — namespaces only, so
bare `mkdirSync`, `linkSync`, `rmSync` and `dirname` do not resolve. The staging root must be derived
by parsing `tempKey` (`local-blob-store.ts:53` builds `` `_staging/${crypto.randomUUID()}/${key}` ``),
which the step still does not say. The class's own path helper is
`private abs(p, key)` at `:12`, which the plan does use correctly.

### M2 — round-1 M4 (T6 Step 4's Supabase + in-memory recipes): DEFERRED, still not implementable, and the in-memory half is now WRONG.

Unchanged: *"Supabase: `upload()` without `upsert` returns HTTP 409 when the object exists"* —
`promoteIfAbsent(ref: StagedRef)` has no bytes to upload; a create-if-absent finalize needs
`download(tempKey)` then `upload(final, bytes, { upsert:false })`, or the bucket's `copy`. Still
nothing about removing the staging tree, though 18d2 and 18d3 both assert
`expect(await store.list(P, '_staging/')).toEqual([])` against all three adapters.

**New in v2:** the in-memory recipe `if (!this.map.has(k)) this.map.set(k, bytes)` names a field that
does not exist. `lib/storage/testing/in-memory-blob-store.ts:45` is
`private readonly blobs = new Map<string, StoredBlob>()` — different name, and the value is a
`StoredBlob`, not a `Buffer`. Worth noting for the fix: that class already has
`promoteSemantics: 'create-if-absent'` (`:43`, `:170`), so its `promoteIfAbsent` is close to
`promote()` with that option forced.

### M3 — round-1 M6 (T12's sync-run insertion point): DEFERRED, unchanged, and now UNMITIGATED.

The block is still appended with no stated insertion point, and the only obvious one is after
`sync-run.ts:739-757`, which throws on **every** `!rec.ok` — making
`else if (!rec.ok && rec.reason === 'unservable-base')` dead and routing `unservable-base` into the
generic tail at `:754`, producing exactly the un-actionable message round-16 M1 was filed about. Round
1 downgraded this to Medium because *"`tsc` will flag it"*. Per H2, **no `tsc` runs in T12**, so it
now fails silently instead of loudly.

**Fix.** Say the branch goes *inside* the `!rec.ok` block, above the generic throw at `:754`, and add
`npx tsc --noEmit` to T12 Step 4.

### M4 — round-1 M2 (T4's five flipped rejection cases): DEFERRED, re-measured identical, and the false NFKC claim is still headed for the codebase.

**MEASURED** — I ran T4 Step 3's `isServableSummaryKey` verbatim (Node 22.14.0) against all 23 cases
in `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`. No accept-side regression (5/5 still
accepted). **5 of 18 rejections flip to ACCEPT**, the same five round 1 measured:

| Case | Key |
|---|---|
| `double-dot` | `foo..md` |
| `leading-space` | `' foo.md'` |
| `leading-dot` | `.foo.md` |
| `fraction-slash-2044` | `a⁄b.md` |
| `division-slash-2215` | `a∕b.md` |

The first three are the intended widening. The last two are not, and T4 Step 3's comment still says
*"A hand-typed homoglyph denylist cannot be complete; **NFKC closes that class**."* U+2044 and U+2215
have no NFKC decomposition to `/`, so that sentence is false, and it is about to be committed into
`lib/html-doc/assert-cloud-summary-md-key.ts` where nobody will re-examine it. (Harmless in practice —
neither is a path separator and `serve-summary-core.ts:66` hands the key straight to `blobStore.get`
without re-parsing it. U+FF0F does fold and is still correctly rejected, verified.)

T4 Step 4's blanket "if one now fails, it was asserting the allowlist" **is** a disposition, so this
is a defensible deferral — but the step also says "Expected: PASS" for `npm test`, which is wrong on
first run.

**Fix.** List the five in T4 Step 4 with dispositions, change "Expected: PASS" to "Expected: 5 named
failures, then update them", and downgrade the comment to: NFKC closes the *compatibility-decomposable*
homoglyphs; the two non-decomposing slashes are accepted deliberately because the key is never
re-parsed as a path.

### M5 — T13 Step 3, the additive-create protocol, is the only step in the plan with no code — and it carries five behaviors on the money path.

```
`putStaged` -> **verify the read-back hash** -> `promoteIfAbsent` -> read back and classify: **equal** ->
success; **different** -> refuse; **absent** -> refuse (a fault, not a resume); **unreadable** -> treat
as occupied, refuse (behavior 19 …).
```

No file, no line, no signature — for behaviors 18, 18b, 18c, 18c2 and 19, inside `copyAdditiveVideo`
(`sync-run.ts:221`), which today writes unconditionally. Round 1 filed the same shape against v1's
T13 Step 2 (H2) and v2 moved the prose without giving it a body. Contrast T13 Step 4, which quotes the
real signature, both call sites and the exact line to insert above — that step is executable and this
one is not.

### M6 — T13 Step 7 still runs the ratchet loop with `|| echo`, the exact defect the Global Constraints say was fixed.

Plan lines 1589-1590:

```bash
for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do
  python3 scripts/$c.py || echo "RED: $c"; done
```

`echo` succeeds, so the loop exits 0 whatever happens. The Global Constraint at lines 35-44 carries
the corrected `set -e` form and explicitly names this as round-1 M2 (Codex), and the Self-Review
records **"M(cx) | ratchet loop masked exit codes | FIXED — `set -e`, no `|| echo`"**. The broken copy
survived in the one task that runs it. (All four scripts exist: verified in `scripts/`.)

### M7 — round-1 L3 (elided fixtures): DEFERRED, unchanged. Four of them are calls with no arguments at all.

Still present: T12 26d2 `runSync({ /* same fixture */ })`; T11 26b `runSync({ … })` twice; and T8 Step
1's four calls of the form `companionTransfer(/* receiver envelope videoId: 'OTHER', row: 'dQw4…' */)`
against a function whose real signature is `(winner: Side, loser: Side, winnerMdHash: string,
winnerVideo: Video)`. The Self-Review's *"No TBDs. Every code step carries real code"* is still not
true of these.

### M8 — round-1 L4 (T5's target file mocks the module T5 tests): DEFERRED, unchanged.

`tests/integration/share-route.test.ts:37-50` does `jest.mock('@/lib/share/serve', …)` and wraps
`getShareServeContext` in a counting `jest.requireActual` delegate with module-level counters that an
existing test arms on `sinceArm === 2`. T5's two new tests call `getShareServeContext` directly in
that file and perturb that shared state. Still no sentence in T5.

---

## LOW

### L1 — T7's rollout count is still wrong, and it is now wrong in the "recounted" direction.

Plan: "**41 call sites** (3 production + 38 test) across **11 files**". Self-Review: "**ACCEPTED** —
recounted this session: **41**". Counted by regex over every non-`node_modules` `.ts`/`.tsx`, skipping
comment and import lines and the two declarations in `model-store.ts`:

| | Plan | Round 1 | Measured now |
|---|---|---|---|
| total | 41 | 43 | **42** |
| production | 3 | 3 | **3** (`generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464`) |
| test | 38 | 39 | **39** |
| files | 11 | 11 | **11** (3 prod + 8 test) |

Round 1's 43 counted one comment mention (`serve-doc.ts:158`). The real number is 42.

### L2 — round-1 L2 is half-fixed: T1's sweep is now labelled, T4's behavior 27 still overclaims.

T1 Step 5 now carries an explicit "a stride SAMPLES, it does not cover … this visits ~1.6% of it"
comment — correct and well done. T4 Step 5's test is still named *"behavior 27 — NO slugify output
fails the predicate, **over the whole codepoint space**"* with `cp += 0x20`. Round 1 measured 0
violations at stride 1 over the full space, so this is an overclaim, not a hidden defect.

### L3 — the Tech Stack line says `ts-jest`; the config uses `next/jest` (SWC).

Line 9: "**Jest 30 + ts-jest** (`jest.config.ts`…)". `jest.config.ts` is
`createJestConfig = nextJest({ dir: './' })`. `ts-jest ^29.4.9` is a devDependency but is not the
transform for either config. This is the belief that makes H2 invisible — an implementer who thinks
ts-jest is running reasonably assumes `npx jest` type-checks.

### L4 — T7 Step 3 calls the read schema "unchanged" while changing it.

`export const ModelEnvelopeSchema = z.object({ /* …existing… */ videoId: z.string().optional() })` is
labelled "READ side — unchanged". `ModelEnvelopeSchema` (`model-store.ts:15-24`) has **no** `videoId`
today. The addition is necessary and correct — behavior 18j5b's `expect(got!.videoId).toBeUndefined()`
needs the field in the type, and `.strict()` was deliberately removed at `:25-26` so old readers
already tolerate it — but "unchanged" is the wrong word for the one line an implementer might skip.

### L5 — two stale cross-references from the Task 0 insertion.

The Ordering rationale says "Then **T1–T5 are independent** and unblock everything", but T5's own
Interfaces block says "Consumes: `isServableSummaryKey` from T4". And the File Structure table
(lines 55-69) has no row for Task 0's three created files, including
`lib/cloud-sync/canonically-equal-name.ts`, which T13 imports.

### L6 — T13 Step 4's refusal leaves an orphaned staging tree.

The guard is placed "Before the write at `:394`", i.e. after `putStaged` at `:381` has already written
`_staging/<uuid>/<key>` on the loser and after the read-back verify at `:382-385`. On refusal nothing
removes it — a leak, not a loss, and cheap to fix by moving the guard above `:381` (it needs only
`loserVideo`, `key` and `loser`, all in scope there).

---

## What holds up

Stated as findings of their own, because the calibration matters more than the count. Four of these
are executed measurements, not readings.

- **T1's encoder is completely correct, and round-1 B4 is closed. MEASURED.** I ran T1 Step 3's
  implementation and all ten of Step 1 + Step 5's assertions verbatim under Node 22.14.0:
  `17376 iterations, 0 FAILING` on the sweep, and all 11 individual checks pass (identity, empty
  segment, physical alphabet, `=h` marker, NFC/NFD divergence, disjointness, determinism, the 400-char
  Korean bound, the over-LIMIT ASCII case, and the two lone surrogates differing under `utf16le`). I
  re-measured the worst case at exactly **65** characters, so `toBeLessThanOrEqual(65)` is still tight.
  The property assertion now targets `/^[A-Za-z0-9._=-]+$/` — the physical alphabet — which is the
  right fix and the one round 1 asked for.
- **T2's slice arithmetic is right for all three prefix shapes, and B2/B3/M5 are closed.** Traced by
  hand: for `prefix = ''`, `norm` is `''`, `physicalPrefix` is `''`, `dirPath` is the owner root with
  its trailing slash stripped — identical to today. For `'dig/base/'`, `physicalPrefix` is
  `'dig/base/'` and the remainder is the leaf. For `'dig/003_한국어'` (no trailing slash), `norm` adds
  one, the encoded prefix ends in `/`, and `ownerRoot.length + physicalPrefix.length` lands exactly on
  the leaf. I also traced both **existing** tests in `blob-store-list.test.ts` through the new code —
  including the nested-folder recursion case, whose remainder `nested/120.r9.md` contains no `=h` —
  and both still pass. `${p.id}/`, `assertLogicalKey` and the private-method form are all preserved;
  `deletePrefix` is now named in Step 3.
- **T13 Step 4 — the Class-A ownership guard — is the strongest new material in v2, and I checked
  every part of it.** The quoted signature matches `sync-run.ts:371-373` verbatim. The unconditional
  write it guards is `:394`. Both call sites are correct **including argument order and which record
  is the loser's**: `:782` is `transferClassA(localSide, cloudSide, lv, id)` where the loser is the
  cloud, so `cv` is right; `:793` is `(cloudSide, localSide, cv, id)` where the loser is local, so
  `lv` is right. `tryGet` exists (`supabase-blob-store.ts:63`, `local-blob-store.ts:28`) and returns
  `BlobRead`, so `dest.ok || dest.reason === 'unreadable'` narrows correctly in TypeScript. Treating
  `unreadable` as occupied is right, and choosing `tryGet` over `get` is right for the reason the
  comment gives — `get` swallows RLS denial into the same null as absence
  (`supabase-blob-store.ts:29-35`). Round 1's Codex Blocking on this is genuinely closed.
- **T4's predicate is correct on every behavior it claims. MEASURED.** Run verbatim under Node
  22.14.0: all 6 new accepts pass (Korean, NFD accented Latin, space, emoji, the DIGIT-ONE-FULL-STOP
  class, U+1F100); all 10 new rejects pass (nested, `%2f`, U+FF0F, U+2100, both traversal shapes,
  U+0007 BEL, U+0085 NEL, U+202E RLO, over-long); 129/130/131 accepted and 132 rejected; the astral
  key accepted; the ill-formed key rejected; both 17d cases accepted; and **0 violations** over a full
  `\p{Bidi_Control}` sweep of all 1,112,064 code points. `statusCode: 409` is restored, so round-1 M1
  is closed — and I confirmed the four non-string cases still pass, because `typeof mdKey !== 'string'
  ||` short-circuits before the predicate (which would otherwise throw `TypeError` on `null.endsWith`).
- **T12's core is correct.** `SerialReconcileResult` at `reconcile-serial.ts:69-81` — counted: 2 `ok`
  variants and **10** refusal variants, so "the ten existing refusal variants" is right. The truthiness
  ternary at `:152-154` is the one the plan's `origin` must agree with, and it does. `localVideo`,
  `oldBase` and `newBase` are all in scope at the proposed insertion point, which sits correctly beside
  the `target-occupied` (`:197`) and `unsupported-artifacts` (`:214`) refusals and before the copy
  phase. Round-18 L1 stays closed.
- **T10's placement is exactly right.** `summary-handler.ts:95` is `reserveVideoSlot`, `:96` is
  `const baseName = …`, `:101` is `summaryCore` — the plan quotes all three correctly and puts the
  refusal between them, so a refusal costs a serial and no money.
- **T5's placement is right and covers both producers by construction.** `lib/share/serve.ts:47` is
  `const mdKey = artifact?.key ?? (vid.data as …).summaryMd;` and `:48` is `if (!mdKey) return denied;`
  — so the guard sits after both arms have collapsed into one value, and `mdKey` is a narrowed
  `string` there.
- **T3's one-line repair applies verbatim.** `lib/slugify.ts` is a single chained expression ending
  `.slice(0, 60)`, so `const s = …; return s.isWellFormed() ? s : s.slice(0, -1);` is a literal
  substitution. I traced behavior 16b's fixture: 59 BMP + one astral = 61 units, sliced to 60, leaving
  an orphaned high surrogate — the test is red before and green after.
- **Zero literal control or bidi characters in the plan.** I ran the plan's own detector
  (`unicodedata.category in ('Cc','Cf')`, excluding `\n`) over all 1,701 lines: **0** violations. The
  defect that shipped five times has not shipped a sixth.
- **The gate script's `charset()` is correct, and its `--self-test` genuinely runs.** Extracted and
  executed: 4/4 ok, exit 0. Its `JS_SAFE` regex does match T1's real declaration line (verified), and
  it expands `A-Za-z0-9._-` to exactly 65 characters. The boundary case I expected to break it
  (`i + 2 < len(cls)` on a class ending in a range, e.g. `a-c`) is handled correctly. The problem is
  H1 — nothing points it at its subject — not the code.
- **The money ordering is still sound.** T10's guard is between `reserveVideoSlot` and the Gemini
  call; T11's is above both `readMdBody` (`:626`) and `ensureReceiverSlot`; T12 refuses before the copy
  phase; T13's Class-A guard refuses before `put`. A plan stopped after any task N cannot double-charge
  or orphan a paid artifact. The failure mode of stopping early is *unverified* behavior (B1), not
  *lost* money.
- **`canonicallyEqualName` is now specified properly** — file, signature, three tests, and a docstring
  that says why the relation is a proper subset and why `null` is false. Round-1 H2 is closed.
- **Round-1 M1, M5, M7 and the Codex `ref.key` Blocking are all genuinely closed**, verified against
  the files: `statusCode: 409` restored; `deletePrefix` named in T2 Step 3; T4 Step 4 now runs
  `npm test` rather than a slice; `StagedRef` is `{ principal, tempKey, finalKey }`
  (`blob-store.ts:5`) and T6 Step 3 uses `ref.finalKey` with a comment explaining why.

---

## The deferred six — verdict

Asked directly by the brief: were M2, M3, M4, M6, L3 and L4 deferred, silently fixed, or made worse?

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| **M2** T4's flipped rejection cases | **Genuine deferral, still true** | re-measured: the same 5 flips, and the false NFKC-completeness claim is unchanged (M4 above) |
| **M3** T6's `stagingRoot` + unimported symbols | **Genuine deferral, still true** | `stagingRoot`: 0 occurrences; `local-blob-store.ts:1` imports namespaces only (M1 above) |
| **M4** T6's Supabase/in-memory recipes | **Genuine deferral, made WORSE** | still not implementable, **and** the in-memory recipe now names `this.map`; the real field is `this.blobs` (M2 above) |
| **M6** T12's sync-run insertion point | **Genuine deferral, made WORSE** | unchanged, and its only mitigation ("tsc will flag it") is void because no `tsc` runs in T12 (M3 + H2 above) |
| **L3** elided test fixtures | **Genuine deferral, still true** | 4 argument-less `companionTransfer` calls, 3 elided `runSync` fixtures (M7 above) |
| **L4** T5's file mocks the module T5 tests | **Genuine deferral, still true** | `share-route.test.ts:37-50` unchanged, no sentence in T5 (M8 above) |

**No omission is dressed as a deferral.** All six are honestly carried, exactly as the Self-Review
promised. Two degraded, and none of them is close to being this round's biggest problem — which is
that the *fixes* went unreviewed, not the *deferrals*.

The comparison worth drawing: the Self-Review marks H3 and H4 **FIXED**, and both are fixed only in
prose — H3's snippet still sits in the ship arm and still calls an invented field (B2), H4's code still
pushes from the branch its own comment forbids (H5). **A "DEFERRED" row in v2 was more reliable than a
"FIXED" one.**

---

NOT CONVERGED

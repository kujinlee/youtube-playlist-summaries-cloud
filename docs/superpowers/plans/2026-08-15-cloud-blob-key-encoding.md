# Cloud Blob Key Encoding Implementation Plan (backlog #36)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a video with a title in any language be stored **and served** from the cloud, without changing vault filenames and without migrating anything already in the bucket.

**Architecture:** Two independent halves. (1) **The encoder** — `SupabaseBlobStore` maps a *logical* Unicode key to a *physical* ASCII one at the storage seam, so Storage's ASCII-only rule stops reaching the rest of the app. (2) **The servability guard** — one predicate, `isServableSummaryKey`, installed at points that *dominate* every writer rather than at a list of call sites: `videoDataPayload()` for cloud row writes, `serialize()` for model envelopes.

**Tech Stack:** TypeScript, Next.js, Supabase (Postgres + Storage), Zod, **Jest 30 via `next/jest` (SWC)**, Playwright.

**Spec:** [`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md`](../specs/2026-08-14-cloud-blob-key-encoding-design.md) **v21**, approved 2026-08-15 after 18 dual adversarial review rounds. Section references below (§3.2, §3.5.1b …) point into it. **Read the spec section named in a task before starting that task.** The spec is CLOSED — no task in this plan edits it.

---

## ⛔ THE RULE THIS VERSION WAS WRITTEN UNDER

Two review rounds produced **55 findings**. The plan's **decomposition, ordering, interfaces and
behavior mapping held both times**, confirmed independently by both reviewers. **Every defect lived
in a code snippet written without running it.** v2 added "verify every snippet" as a constraint and
then applied it only to the snippets it was *fixing*, not the ones it was *adding* — so the new T8
refusal called a field that does not exist, four tasks tested functions `sync-run.ts` does not
export, and thirteen commands ran zero tests.

> **Every code snippet in v3 is either (a) EXECUTED AND VERIFIED, or (b) the CURRENT code quoted
> verbatim with file:line plus a precise prose statement of the change. Plausible-looking code that
> has not been run is banned from this document.**

**v4 (round 3) is that rule applied to the four places v3 did not apply it: the TEST fixtures.**
v3 executed every *production* snippet and left four test blocks — T8's, T10's, T12's and T13's —
written rather than run. One of them was an assertion its own step said could never fire. A fixture
that has not been run is the same defect as an implementation that has not been run, and it hides in
a place nobody re-reads.

**What was executed, and what it printed** (Node 22.14.0). Rows 1-9 were run from scratch files
outside the repo, with no tracked file modified. The four **v4** rows could not be: they drive real
seams through jest's `@/` resolution, so each was written as a real test file, run RED, run GREEN
with this plan's own implementation snippets temporarily applied, and then **every temporary edit was
reverted** — `git status` after the round shows this document alone.

| Subject | Result |
|---|---|
| T1 `encodeSegment` — 11 named assertions + a 17,376-iteration sweep | all pass; sweep worst length **32**; the true worst case is **65** (`'a'*32` + a non-SAFE char + an 8-char extension), so `toBeLessThanOrEqual(65)` is exactly tight |
| T0 `canonicallyEqualName` — 4 assertions | all pass |
| T4 `isServableSummaryKey` — 6 accepts, 10 rejects, the 129/130/131/132 bound, the astral key, both 17d cases, a full stride-1 `Bidi_Control` sweep | all pass; **12** Bidi_Control code points exist, 0 violations |
| T4 against the **23 existing cases** in `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts` | 5/5 accepts kept; **exactly 5** rejections flip — enumerated with dispositions in T4 Step 4 |
| T3 `slugify` repair + behavior 16b sweep | old output IS ill-formed (the test is genuinely red first); new output well-formed, 1,536/1,536 |
| Behavior 27 cross-derivation at **stride 1**, all four title forms | **4,448,256 loop iterations → 3,479,131 NON-EMPTY SLUG ASSERTIONS, 969,125 empty slugs skipped, 0 predicate violations, 8.8 s** — so "over the whole codepoint space" is now earned rather than claimed. *(Round-3 Codex M1: v3 called the 3,479,131 "iterations". Re-counted independently this round; all four numbers agree with Codex's re-run.)* |
| T2 `objectKey` / `list` / `deletePrefix` against a fake **client** wired into a real store shape | behaviors 8, 9, 10, 12 pass; both **existing** tests in `blob-store-list.test.ts` still pass; empty-prefix case identical to today |
| T6 `promoteIfAbsent` on **local** and **in-memory** — 18d, 18d2, 18d3, 18d4, absent-final, malformed-tempKey | all pass on both adapters |
| T13 `scripts/check-encoder-gate-sql.py` — `--self-test` (10 cases) **and** `main()` against the real spec | self-test 10/10 exit 0; `main()` **exit 0, "the same 65 characters"**; drift → exit 1; encoder absent → exit 2 |
| **v4 — T8** `companion-videoid.int.test.ts`, whole file, live local stack | **RED 3 failed / 4 passed** (the two 18j arms + 18j6, each for its intended reason) → **GREEN 7/7**, 3.4 s |
| **v4 — T10** `summary-handler-guard.test.ts`, whole file, live local stack | **RED 1/2** (`err` is `null`: no guard) → **GREEN 2/2**. Also killed a vacuous ledger assertion |
| **v4 — T12** the four cells appended to `reconcile-serial.test.ts` | **RED 3/4**, each receiving `{ok:true,action:'relocated'}` → **GREEN 4/4**. Whole-unit-suite blast radius: **exactly 1 existing case flips**, of the repo's 2,703 |
| **v4 — T13** `additive-protocol.test.ts`, whole file | **RED 6 failed / 3 passed** — today's code overwrites the occupant and destroys the loser's artifact → **GREEN 9/9** |

**v4 (round 3) applied the same rule to the four test-fixture blocks that had escaped it** — the
last places in this document where a snippet was written rather than run. Each was written as a
complete file, executed RED against today's code, then executed GREEN with this plan's own
implementation snippets applied; the temporary implementation was then reverted, so the tree carries
only this document. Three previously-unmeasured facts fell out of doing that, and each is in its
task: T10's ledger assertion could not fail, T12's guard flips exactly one existing case, and
today's companion DELETE arm really does destroy the other video's paid model.

The one snippet in this document that has **still** not been run is the Supabase `promoteIfAbsent`
adapter. Round 3 did have the live stack, so the honest statement is no longer "it cannot be run" but
"it was not run" — T6 was outside the four fixtures round 3 was scoped to. T6 Step 4 therefore states it as a change to quoted code and removes its dependence on
an unverified HTTP status — see the note there.

---

## Global Constraints

Every task's requirements implicitly include this section. Values are copied verbatim from the spec.

- **`SAFE = /^[A-Za-z0-9._-]+$/`**, **`LIMIT = 255`** (measured Storage ceiling, per path *segment*). §3.2
- **Hash the logical segment as `utf16le`, never `utf8`.** Node maps every unpaired surrogate to U+FFFD, so two different lone surrogates would hash identically. §3.2
- **The servability bound is `> 3 && <= 131` CODE POINTS**, not UTF-16 units. §3.4
- **Never write a literal control or bidi character into a source file or a test fixture — use escapes.**
  This spec shipped that defect four times and the v1 plan shipped it a fifth. **Before every commit, run:**
  ```bash
  python3 -c "import sys,unicodedata as u; [sys.exit(f'literal control/bidi char at line {s.count(chr(10),0,i)+1}') for p in sys.argv[1:] for s in [open(p,encoding='utf8').read()] for i,c in enumerate(s) if u.category(c) in ('Cc','Cf') and c!=chr(10)]" <files>
  ```
  Conversely **never write backslash-u escapes in prose** — name the code point instead (round-17 L3 found that inverse error).
- **Fixtures with two normalization forms are built with `.normalize('NFC')` / `.normalize('NFD')`, never as two source literals.**
- **Node 22+** is required (`String.prototype.isWellFormed`, Unicode property escapes). CI runs Node 22.
- **No migration.** §4's gate ran against prod on 2026-08-14: 19 objects, 0 rows outside `SAFE`. Nothing in this plan rewrites an existing object key.
- **Decision ① — the vault wins.** Local filenames keep their Unicode. **No guard is ever installed on the local path.** A guard that refuses to write a name *into the vault* is the inverse of this decision and caused round-16 B1.
- **⛔ THE TWO SUITES TAKE DIFFERENT COMMANDS.** `jest.config.ts` `testMatch` is `tests/lib/**`,
  `tests/api/**`, `tests/scripts/**`, `tests/smoke.test.ts`, `tests/components/**` — it **excludes
  `tests/integration/`**, which lives in `jest.integration.config.ts` with the `globalSetup` that
  applies pending migrations. Running `npx jest tests/integration/x.test.ts` prints
  *"No tests found, exiting with code 1"*, which is indistinguishable from the intended red.
  | Suite | Command | `package.json` |
  |---|---|---|
  | unit | `npx jest <path>` / `npm test` | `"test": "jest"` (`:9`) |
  | integration | `npm run test:integration -- <path>` | `"test:integration": "jest --config jest.integration.config.ts --runInBand"` (`:18`) |
  The trailing `--` is required so npm passes the path through. **Every command in this plan is
  labelled with the suite it belongs to.** The integration half needs the local Supabase stack up.
- **⛔ `npx jest` CANNOT GO RED ON A TYPE ERROR.** Both configs are built by `nextJest`, which
  transforms with SWC (`node_modules/next/dist/build/jest/jest.js`: *"Use SWC to compile tests"*) —
  types are stripped, never checked. `ts-jest` is a devDependency and is the transform for neither
  config. **Every task's final verification starts with `npx tsc --noEmit &&`.** `tsconfig.json`
  `include` is `**/*.ts` / `**/*.tsx`, so tests are type-checked too.
- **`scripts/check-producer-enumeration.py` must exit 0** after any task that edits §3.5.1b.
- **Run the full ratchet set before declaring a task done, FAIL-FAST — never `|| echo`:**
  ```bash
  set -e
  for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do
    python3 "scripts/$c.py"
  done
  ```
  *(Round-1 M2: the first draft wrote `python3 scripts/$c.py || echo "RED: $c"`, which exits 0 whatever
  happens because `echo` succeeds. Round-2 M6: the corrected form was written here and the broken copy
  survived in T13, the one task that ran it.)*
- **If a snippet below does not compile, that is a plan defect — stop and fix the plan**, do not
  improvise around it.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `lib/cloud-sync/canonically-equal-name.ts` | **new** — the vault alias relation, a proper subset of it | T0 |
| `lib/cloud-sync/sync-run.ts` | **exports widened** for test reachability (T0); then three behavior edits | T0, T8, T11, T12, T13 |
| `tests/integration/helpers/cloud.ts` | `syncDeps` gains a `localBlob` override (behavior 26f needs it) | T0 |
| `lib/storage/supabase/encode-segment.ts` | **new** — the pure logical→physical segment encoder | T1 |
| `lib/storage/supabase/supabase-blob-store.ts` | wire the encoder into `objectKey`, `list`, `deletePrefix` | T2 |
| `lib/slugify.ts` | one-line orphaned-surrogate repair | T3 |
| `lib/html-doc/assert-cloud-summary-md-key.ts` | replace the allowlist with `isServableSummaryKey` | T4 |
| `lib/share/serve.ts` | the guard moves *inside* `getShareServeContext` | T5 |
| `lib/storage/blob-store.ts` + 3 adapters | **new primitive** `promoteIfAbsent`; `stagingRootOf` + `contentTypeForKey` exported | T6 |
| `tests/support/blob-store-contract-cases.ts` | **new** — the shared `promoteIfAbsent` contract, run by BOTH suites | T6 |
| `lib/html-doc/model-store.ts` | `ModelEnvelopeWriteSchema`; `serialize` enforces it | T7 |
| `lib/storage/supabase/supabase-metadata-store.ts` | `stripComputed` → **`videoDataPayload`** + the seam refusal | T9 |
| `lib/job-queue/summary-handler.ts` | the mint guard, before the Gemini call | T10 |
| `lib/cloud-sync/reconcile-serial.ts` | the four-cell relocate/refuse/skip table | T12 |
| `scripts/check-encoder-gate-sql.py` | **new** — behavior 20: the §4 gate class derives from the encoder | T13 |
| `docs/adr/0009-logical-unicode-physical-ascii.md` | **new** — the ADR | T15 |

**Ordering rationale. T0 comes first** — it makes the functions five later tasks test *reachable*,
and adds the one production helper (`canonicallyEqualName`) they assume. Then **T1–T5 are
independent** except that T5 consumes T4's predicate, so T5 follows T4. T6–T8 are the model/blob
primitives. **T9 must land before T10–T12**, because those three are all *placements* whose refusal
semantics depend on the seam existing. T12 is last of the guards because round-18 B1 was precisely a
T12/T9 interaction. T13 consumes T6, T0 and **T1** (its §4 gate script reads T1's `SAFE`) — round-3
Claude L5 counted this; v3 said "T6 and T4".

---

## Task 0: Make the code under test REACHABLE

**Round-1 H1 + H2, round-2 B3 + H6.** Five tasks call functions `sync-run.ts` does not export, and
v2's inventory table asserted the opposite — which is worse than v1, because it tells an implementer
the symbol exists in production, so they import it and get TS2459 with no guidance.

**`lib/cloud-sync/sync-run.ts` has exactly THREE exports today** (counted by reading every line
beginning `export`): `SyncDeps` (`:40`), `SyncReport` (`:51`), `runSync` (`:547`).

### The inventory, re-counted — and five of v2's seven "missing helpers" DISSOLVE

Counted over `tests/`, `lib/`, `scripts/`, `app/`, `components/` with `python3` + `os.walk` + two
patterns (declaration-shaped **and** bare-occurrence, so a class method cannot produce a false
negative — that is what produced v1's error on `collectObjectPaths`).

| v2 said | Reality | v3 |
|---|---|---|
| `ledgerTotal` ❌ missing | `Ctx.spendLedgerTotal()` **exists** — `tests/integration/helpers/cloud.ts:153`, reads `spend_ledger` via the admin client | use it |
| `readVideo` ✅ production | **collides.** `sync-run.ts:80` is module-private; the *exported* `readVideo` (`lib/storage/worker-persistence.ts`) takes `(client, playlistId, videoId)` — a different function | use `cloudVideoRecord(ctx)` / `localVideoRecord(ctx)`, which **exist** (`helpers/cloud.ts:471`, `:476`) |
| `mintShareToken` ❌ missing | `mintDirect(ownerId, playlistId, videoId, over?)` **exists** in `tests/integration/share-serve.test.ts:17`, which is where T5's tests go | use it |
| `seedEnvelope` ❌ missing | `writeModelEnvelope(...)` through a service-role `SupabaseBlobStore` **is** the seeder — the pattern is `share-route.test.ts:79` `seedFreshModel` | file-local helper in T8 |
| `ingestLocal` ❌ missing | not needed — see T14, which drives the real local write instead of inventing a pipeline entry point | dissolved |
| `fakeStoreHolding` ❌ missing | needed, but v2's signature was wrong (round-2 H7): returning a `BlobStore` means `store.list` is the **fake's** list and the code under test never runs | T2-local, corrected signature |
| `callWith` ❌ missing | needed, one consumer | file-local helper in T9 |
| `spyStore` ❌ missing | needed, one consumer, and it must be **injectable** | Step 3 below + a file-local decorator in T11 |
| `storeWith` ✅ | `tests/lib/html-doc/model-store.test.ts` (file-local) | unchanged |
| `putBudget` ✅ | `tests/support/budget.ts:18` | unchanged |
| `seedVideo` ✅ | `helpers/cloud.ts:296` | unchanged |
| `applySerial`, `assertLogicalKey`, `localPrincipal` ✅ production | correct — `lib/serial-filename.ts`, `lib/storage/blob-store.ts:87`, `lib/storage/principal.ts` | unchanged |
| `collectObjectPaths` ✅ production | a **private class method** (`supabase-blob-store.ts:151`) — correct for T2's purpose and uncallable from a test | unchanged |
| `serveSummary`, `ingest`, `runSummaryJob`, `EXPECTED_ONE_SUMMARY_COST`, `readdirNames`, `seed` | 0 occurrences each — v2's table did not list them at all (round-2 H6) | all four **dissolved** in T14/T13; see those tasks |

**Files:**
- Create: `lib/cloud-sync/canonically-equal-name.ts`
- Modify: `lib/cloud-sync/sync-run.ts` (export widening only — no behavior change),
  `tests/integration/helpers/cloud.ts` (one optional field)
- Test: `tests/lib/cloud-sync/canonically-equal-name.test.ts`

**Interfaces — Produces:** `canonicallyEqualName(stored: string | null | undefined, wanted: string): boolean`;
and the widened `sync-run.ts` surface: `Side`, `copyAdditiveVideo`, `transferClassA`, `companionTransfer`.

- [ ] **Step 1: Write the failing test for `canonicallyEqualName` (behaviors 18i, 18k)** — UNIT

```ts
// tests/lib/cloud-sync/canonically-equal-name.test.ts
import { canonicallyEqualName } from '@/lib/cloud-sync/canonically-equal-name';

it('behavior 18i — NFC and NFD forms of one name are EQUAL', () => {
  expect(canonicallyEqualName('café.md'.normalize('NFC'), 'café.md'.normalize('NFD'))).toBe(true);
});

it('behavior 18i — a PROPER SUBSET: fullwidth A is NOT an alias of A', () => {
  expect(canonicallyEqualName('Ａ.md', 'A.md')).toBe(false);
});

it('behavior 18k — a null left side is FALSE, so a loser with no summaryMd takes the probe branch', () => {
  expect(canonicallyEqualName(null, 'a.md')).toBe(false);
  expect(canonicallyEqualName(undefined, 'a.md')).toBe(false);
});
```

- [ ] **Step 2: Run it — UNIT: `npx jest tests/lib/cloud-sync/canonically-equal-name.test.ts`.**
      Expect FAIL, module not found.

- [ ] **Step 3: Implement it** — ⚙ **EXECUTED: all four assertions above pass under Node 22.14.0.**

```ts
// lib/cloud-sync/canonically-equal-name.ts
/** Is `stored` the same NAME as `wanted` under the volume's alias relation?
 *
 *  A PROPER SUBSET of that relation, deliberately: NFC/NFD are aliases on APFS, fullwidth and
 *  compatibility forms are NOT. Widening this to NFKC would make `Ａ.md` and `A.md` equal and let a
 *  Class-A transfer overwrite a DIFFERENT video's artifact (spec behavior 18i).
 *
 *  `null` is false, never true: a loser row that advertises no key has not claimed this address, so
 *  it must take the create-if-absent branch rather than the overwrite branch (18k). */
export function canonicallyEqualName(stored: string | null | undefined, wanted: string): boolean {
  if (typeof stored !== 'string') return false;
  return stored.normalize('NFC') === wanted.normalize('NFC');
}
```

- [ ] **Step 4: Run it — UNIT: same command. Expect PASS, 3 tests.**

- [ ] **Step 5: Widen `sync-run.ts`'s exports — the decision round 2 asked for, made once, here**

Three functions are tested directly by T8/T11/T13 and one type is needed to build their arguments.
**Export them; do not extract them, and do not drive them through `runSync`.** Reasons, stated so the
choice is reviewable: (a) extraction moves ~200 lines of money-path code in a slice whose subject is
key encoding — a blast radius nobody asked for; (b) `runSync` cannot reach `transferClassA`'s
loser-record branch with a *chosen* loser record, which is exactly what behaviors 18g/18h vary; (c)
`runSync` swallows every per-video throw into `report.errors` (`:812-814`), so a direct call is the
only way to assert *which* error. Where `runSync` **can** express the behavior, this plan uses it —
T9 26c3/26c4, T11, T12 26d2.

These are the four one-word edits (**the function bodies do not change**):

```ts
// :62   interface Side { …               ->  export interface Side { …
// :221  async function copyAdditiveVideo ->  export async function copyAdditiveVideo
// :371  async function transferClassA    ->  export async function transferClassA
// :444  async function companionTransfer ->  export async function companionTransfer
```

Add one line above each, so the widening is not read as an invitation:

```ts
/** @internal Exported for tests only (plan T0). No production caller outside this module. */
```

`readVideo` (`:80`) is **deliberately NOT exported** — the name already means something else in
`lib/storage/worker-persistence.ts` and a second export of it is a vocabulary collision
(`scripts/check-vocabulary-collisions.py` exists for this class of mistake). Tests read records
through `cloudVideoRecord` / `localVideoRecord`.

- [ ] **Step 6: Give `syncDeps` a `localBlob` override — behavior 26f cannot be written without it**

`tests/integration/helpers/cloud.ts:131` is verbatim today:

```ts
    syncDeps(opts: { failCloudPromote?: boolean; failCloudModelPut?: boolean } = {}): SyncDeps {
      const cloud = new SupabaseMetadataStore(userClient);
      let cloudBlob: BlobStore = new SupabaseBlobStore(userClient, ARTIFACTS_BUCKET);
      if (opts.failCloudPromote) cloudBlob = new FailPromoteBlobStore(cloudBlob);
      if (opts.failCloudModelPut) cloudBlob = new FailModelPutBlobStore(cloudBlob);
      return {
        local: localMetadataStore,
        …
        localBlob: localBlobStore,
```

**The change:** add `localBlob?: BlobStore` to the `opts` type (and to the `Ctx` interface's
declaration of `syncDeps` at `:69`), and return `localBlob: opts.localBlob ?? localBlobStore`.
Nothing else moves. Behavior 26f asserts a NEGATIVE — that the sender's blob store was never read —
which is unobservable unless the test can supply the sender's store.

- [ ] **Step 7: Verify and commit**

```bash
npx tsc --noEmit && npm test && npm run test:integration
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/cloud-sync/ tests/lib/cloud-sync/ tests/integration/helpers/cloud.ts
git commit -m "feat(#36): canonicallyEqualName, and make the sync-run seams reachable from tests (behaviors 18i, 18k)"
```

*(The full integration suite runs here because Step 5 changes a module five suites import. It is the
only task that changes an export surface without changing behavior, so a regression here is
unambiguous.)*

---

## Task 1: The segment encoder

**Spec:** §3.2. **Behaviors:** 1, 2, 3, 4, 5.

**Files:**
- Create: `lib/storage/supabase/encode-segment.ts`
- Test: `tests/lib/storage/encode-segment.test.ts` — **UNIT**

**Interfaces:**
- Consumes: nothing.
- Produces: `encodeSegment(s: string): string`, `SAFE: RegExp`, `LIMIT: number` — consumed by T2 and by `scripts/check-encoder-gate-sql.py` (T13).

- [ ] **Step 1: Write the failing test** — ⚙ **EXECUTED: all 11 assertions below pass.**

```ts
import { encodeSegment, SAFE, LIMIT } from '@/lib/storage/supabase/encode-segment';

describe('encodeSegment', () => {
  it('behavior 1 — a SAFE segment within LIMIT is byte-identical', () => {
    expect(encodeSegment('003_intro-part2.md')).toBe('003_intro-part2.md');
  });

  it('passes an empty segment through, so a trailing slash survives', () => {
    expect(encodeSegment('')).toBe('');
  });

  it('behavior 2 — a non-ASCII segment becomes an ASCII physical key', () => {
    const out = encodeSegment('003_한국어.md');   // Korean, a literal — not a control character
    expect(out).toMatch(/^[A-Za-z0-9._=-]+$/);
    expect(out).toContain('=h');
    expect(out.endsWith('.md')).toBe(true);
  });

  it('behavior 3 — NFC and NFD forms encode DIFFERENTLY', () => {
    const nfc = 'café.md'.normalize('NFC');
    const nfd = 'café.md'.normalize('NFD');
    expect(nfc).not.toBe(nfd);
    expect(encodeSegment(nfc)).not.toBe(encodeSegment(nfd));
  });

  it('behavior 4 — identity and hash branches are DISJOINT: `=` is not in SAFE', () => {
    expect(SAFE.test('a=b')).toBe(false);
    expect(encodeSegment('한.md')).toContain('=');
  });

  it('behavior 4 — the hash branch is deterministic', () => {
    expect(encodeSegment('한.md')).toBe(encodeSegment('한.md'));
  });

  it('behavior 5 — every encoded segment is at most 65 characters', () => {
    // 65 is TIGHT, not slack: a 32-char SAFE head + `=h` + 22 digest chars + an 8-char
    // extension is exactly 65, and MEASURED at 65. This fixture is far under it (the
    // Korean head is empty, so it encodes to 27) — the worst case is asserted below.
    expect(encodeSegment('한'.repeat(400) + '.md').length).toBeLessThanOrEqual(65);
    expect(encodeSegment('a'.repeat(32) + '\u{1F600}' + '.abcdefgh').length).toBe(65);
  });

  it('behavior 5 — an over-LIMIT ASCII segment is hashed, not passed through', () => {
    const long = 'a'.repeat(LIMIT + 1);
    expect(encodeSegment(long)).not.toBe(long);
    expect(encodeSegment(long)).toContain('=h');
  });

  it('hashes utf16le, so two DIFFERENT lone surrogates differ', () => {
    // The reason §3.2 chose utf16le: utf8 maps both to U+FFFD and they collide.
    expect(encodeSegment('x\uD840.md')).not.toBe(encodeSegment('x\uD850.md'));
  });
});
```

- [ ] **Step 2: Run to verify it fails** — UNIT: `npx jest tests/lib/storage/encode-segment.test.ts`.
      Expected: FAIL — `Cannot find module '@/lib/storage/supabase/encode-segment'`.

- [ ] **Step 3: Write the implementation** — ⚙ **EXECUTED verbatim; this exact source produced every
      result in the table at the top of this document.**

```ts
import { createHash } from 'crypto';

/** The physical alphabet Supabase Storage accepts, measured in §2.1. */
export const SAFE = /^[A-Za-z0-9._-]+$/;
/** Measured Storage ceiling, per path SEGMENT and not per path (§2.2, premise P2). */
export const LIMIT = 255;

const HEAD = /^[A-Za-z0-9._-]+/;
const EXT = /\.[A-Za-z0-9]{1,8}$/;

/**
 * Map ONE logical path segment to a physical one. Total, deterministic, never inverted —
 * `list()` re-attaches the caller's logical prefix instead (§3.3), which is what makes a
 * one-way hash legal here.
 *
 * utf16le, NOT utf8: Node maps every unpaired surrogate to U+FFFD on the way to a utf8
 * buffer, so two DIFFERENT lone surrogates would hash to the same physical key and one
 * video's blob would overwrite another's. Reachable because `slugify`'s slice cuts UTF-16
 * code units (§3.2, and see T3 which repairs the producer).
 */
export function encodeSegment(s: string): string {
  if (s === '') return '';
  if (SAFE.test(s) && s.length <= LIMIT) return s;
  const head = (HEAD.exec(s)?.[0] ?? '').slice(0, 32);
  const ext = EXT.exec(s)?.[0] ?? '';
  const digest = createHash('sha256').update(Buffer.from(s, 'utf16le')).digest('base64url');
  return `${head}=h${digest.slice(0, 22)}${ext}`;
}
```

- [ ] **Step 4: Run — UNIT: same command. Expected: PASS, 9 tests.**

- [ ] **Step 5: Add the property sweep** — ⚙ **EXECUTED: 17,376 iterations, 0 failing, worst length 32.**

```ts
it('behavior 1 + 5 — property SAMPLE over the codepoint space', () => {
  // ⚠ Round-1 L2: a stride SAMPLES, it does not cover. This visits ~1.6% of the space and is
  // labelled a smoke sweep for that reason. Behaviors 17e and 27 use stride 1, where
  // completeness IS the claim. MEASURED: 17376 iterations, 0 failing, worst length 32.
  for (let cp = 0; cp <= 0x10ffff; cp += 0x40) {
    if (cp >= 0xd800 && cp <= 0xdfff) continue;
    const out = encodeSegment(`003_x${String.fromCodePoint(cp)}.md`);
    // The PHYSICAL alphabet is SAFE plus `=`, the hash-branch marker. Testing `SAFE.test(out)`
    // here contradicts behavior 4 two tests above — `=` is excluded from SAFE ON PURPOSE, so
    // that assertion fails on 100% of non-ASCII iterations after a CORRECT implementation.
    expect(out).toMatch(/^[A-Za-z0-9._=-]+$/);
    expect(out.length).toBeLessThanOrEqual(65);
  }
});
```

Run — UNIT: same command. Expected: PASS, 10 tests.

- [ ] **Step 6: Verify and commit**

```bash
npx tsc --noEmit && npx jest tests/lib/storage/encode-segment.test.ts
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/storage/supabase/encode-segment.ts tests/lib/storage/encode-segment.test.ts
git commit -m "feat(#36): the logical-to-physical segment encoder (spec 3.2, behaviors 1-5)"
```

---

## Task 2: Wire the encoder into `SupabaseBlobStore`

**Spec:** §3.1, §3.3. **Behaviors:** 6, 7, 8, 9, 10, 11, 12, 13.

**Files:**
- Modify: `lib/storage/supabase/supabase-blob-store.ts` (`objectKey`, `deletePrefix`, `list`)
- Test: `tests/lib/storage/blob-store-list.test.ts` — **UNIT**;
  `tests/integration/blob-encoding.test.ts` — **INTEGRATION** (new)

**Interfaces:**
- Consumes: `encodeSegment` from T1.
- Produces: no new exports. `SupabaseBlobStore`'s public surface is unchanged — every method still speaks **logical** keys. This is the property T4–T13 rely on.

- [ ] **Step 1: Write the fake, and the failing unit tests** — UNIT

⛔ **Round-2 H7.** v2's `fakeStoreHolding(keys): BlobStore` would have made `store.list` the **fake's**
`list`, so the code under test never ran and behaviors 8/9/10/12 would have passed against a fixture.
The repo already contains the right ancestor and it has the opposite shape —
`tests/lib/storage/blob-store-list.test.ts:34-37`, verbatim today:

```ts
  function fakeClient(entriesByDir: Record<string, Array<{ name: string; id: string | null }>>) {
    const list = jest.fn(async (dirPath: string) => ({ data: entriesByDir[dirPath] ?? [], error: null }));
    return { client: { storage: { from: () => ({ list }) } }, list };
  }
  …
    const store = new SupabaseBlobStore(client as never, 'artifacts');
```

It fakes the **client** and injects it into a REAL store. Generalise exactly that. The helper is
file-local because it has exactly one consumer; a `tests/support/` module for one caller is a file to
keep in sync for no benefit.

```ts
/** Holds LOGICAL keys. Builds the PHYSICAL directory layout by running the encoder over each
 *  segment — the same function `list` uses — and wires it into a real SupabaseBlobStore.
 *
 *  The keys are LOGICAL, not physical, and that distinction is the whole test: behaviors 8/12's
 *  fixture `dig/003_한국어/s1.r2.md` lives at the physical dir `dig/003_=h…/`, so a fake holding
 *  PHYSICAL paths would make `list` trivially return what it was handed. Verified: after building,
 *  the ENCODED dir is a key of the layout and the logical one is not. */
function fakeStoreHolding(p: Principal, logicalKeys: string[]) {
  const byDir: Record<string, Array<{ name: string; id: string | null }>> = {};
  const removed: string[] = [];
  const ownerRoot = `${p.id}/${p.indexKey}`;
  for (const logical of logicalKeys) {
    const physical = logical.split('/').map(encodeSegment);
    let dir = ownerRoot;
    physical.forEach((seg, i) => {
      const leaf = i === physical.length - 1;
      (byDir[dir] ??= []);
      if (!byDir[dir].some((e) => e.name === seg)) byDir[dir].push({ name: seg, id: leaf ? 'f' : null });
      dir = `${dir}/${seg}`;
    });
  }
  const uploaded: string[] = [];
  const client = { storage: { from: () => ({
    list: async (dirPath: string) => ({ data: byDir[dirPath] ?? [], error: null }),
    remove: async (paths: string[]) => { removed.push(...paths); return { error: null }; },
    upload: async (path: string) => { uploaded.push(path); return { error: null }; },
  }) } };
  return { store: new SupabaseBlobStore(client as never, 'artifacts'), byDir, removed, uploaded };
}
```

⚙ **EXECUTED: every assertion below passes against the Step-3 implementation, and the two EXISTING
tests in this file still pass unchanged (including the nested-folder recursion case, whose remainder
`nested/120.r9.md` contains no `=h`).**

```ts
const P = { id: 'owner1', indexKey: 'pl-key' } as Principal;

describe('SupabaseBlobStore.list — prefix re-attachment (spec 3.3)', () => {
  it('behavior 8 + 12 — returns LOGICAL keys, and a trailing slash is optional', async () => {
    const base = '003_한국어';
    const { store, byDir } = fakeStoreHolding(P, [`dig/${base}/s1.r2.md`]);
    // the fake is not the subject: the layout it built is the ENCODED one
    expect(Object.keys(byDir)).toContain(`owner1/pl-key/dig/${encodeSegment(base)}`);
    expect(Object.keys(byDir)).not.toContain(`owner1/pl-key/dig/${base}`);
    expect(await store.list(P, `dig/${base}/`)).toEqual([`dig/${base}/s1.r2.md`]);
    expect(await store.list(P, `dig/${base}`)).toEqual([`dig/${base}/s1.r2.md`]);
  });

  it('behavior 9 — throws when a physical REMAINDER segment cannot be named', async () => {
    // Hand-built: the LEAF carries a marker the caller did not supply, which is unmappable.
    const byDir = { 'owner1/pl-key/dig/003_x': [{ name: 'lost=hABCDEFGHIJKLMNOPQRSTUV.md', id: 'f' }] };
    const client = { storage: { from: () => ({
      list: async (d: string) => ({ data: (byDir as Record<string, unknown[]>)[d] ?? [], error: null }),
    }) } };
    const store = new SupabaseBlobStore(client as never, 'artifacts');
    await expect(store.list(P, 'dig/003_x/')).rejects.toThrow(/cannot be mapped back/i);
  });

  it("behavior 10 — does NOT throw when the CALLER's own prefix contains `=`", async () => {
    // The marker guard applies to the physical REMAINDER only. Applying it to the caller's
    // prefix strands a video on every run.
    const { store } = fakeStoreHolding(P, ['dig/003_a=b/s1.r2.md']);
    await expect(store.list(P, 'dig/003_a=b/')).resolves.toEqual(['dig/003_a=b/s1.r2.md']);
  });

  it('an EMPTY prefix behaves exactly as it does today', async () => {
    const { store } = fakeStoreHolding(P, ['003_x.md', 'dig/003_x/s1.r2.md']);
    expect((await store.list(P, '')).sort()).toEqual(['003_x.md', 'dig/003_x/s1.r2.md']);
  });

  it('objectKey encodes PER SEGMENT, keeps the owner prefix, and keeps the traversal guard', async () => {
    // `objectKey` is PRIVATE, so it is exercised through `put`, the public method that reveals the
    // physical path it built. Round-1 B2 was exactly a lost owner prefix and a dropped traversal
    // guard, and neither is observable from `list`.
    const { store, uploaded } = fakeStoreHolding(P, []);
    await store.put(P, '003_한국어.md', Buffer.from('x'), 'text/markdown');
    expect(uploaded[0]).toBe(`owner1/pl-key/${encodeSegment('003_한국어.md')}`);
    expect(uploaded[0]).toMatch(/^[A-Za-z0-9._=/-]+$/);              // the physical path is ASCII

    await store.put(P, 'dig/003_한국어/s1.r2.md', Buffer.from('x'), 'text/markdown');
    expect(uploaded[1]).toBe(`owner1/pl-key/dig/${encodeSegment('003_한국어')}/s1.r2.md`);

    await store.put(P, '003_intro.md', Buffer.from('x'), 'text/markdown');
    expect(uploaded[2]).toBe('owner1/pl-key/003_intro.md');          // a SAFE key is IDENTITY

    await expect(store.put(P, '../x.md', Buffer.from('x'), 'text/markdown'))
      .rejects.toMatchObject({ statusCode: 400 });                   // assertLogicalKey survives
    expect(uploaded).toHaveLength(3);                                // and it uploaded nothing
  });

  it('behavior 11 — deletePrefix encodes the prefix it walks', async () => {
    const all = fakeStoreHolding(P, ['003_한국어.md', 'dig/003_한국어/s1.r2.md']);
    await all.store.deletePrefix(P, '');
    expect(all.removed).toHaveLength(2);                 // the whole playlist root
    const one = fakeStoreHolding(P, ['dig/003_한국어/s1.r2.md']);
    await one.store.deletePrefix(P, 'dig/003_한국어/');
    expect(one.removed).toHaveLength(1);                 // reached an ENCODED dir from a logical prefix
  });
});
```

- [ ] **Step 2: Run to verify it fails** — UNIT: `npx jest tests/lib/storage/blob-store-list.test.ts`.
      Expected: FAIL — `list` returns physical keys for the Korean base, and `deletePrefix` walks a
      directory that does not exist so it removes 0 objects.

- [ ] **Step 3: Modify the REAL `objectKey`, `deletePrefix` and `list`**

⛔ **Round-1 B2/B3.** The v1 plan wrote these from scratch and got them wrong: it dropped `p.id` (the
**owner** prefix — a tenancy break, not a typo), dropped the `assertLogicalKey` traversal guard,
invented a method called `rawList`, and sliced by the wrong offset. **These are edits to existing
methods.** This is what is there today, verbatim:

```ts
// lib/storage/supabase/supabase-blob-store.ts:15-18
  private objectKey(p: Principal, key: string): string {
    assertLogicalKey(key);
    return `${p.id}/${p.indexKey}/${key}`;
  }

// :129-138
  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    assertLogicalKey(prefix);
    const root = `${p.id}/${p.indexKey}/${prefix}`.replace(/\/$/, '');
    const objectPaths = await this.collectObjectPaths(root);
    for (let i = 0; i < objectPaths.length; i += 1000) {
      const batch = objectPaths.slice(i, i + 1000);
      const { error } = await this.b().remove(batch);
      if (error) throw error;
    }
  }

// :140-146
  async list(p: Principal, prefix: string): Promise<string[]> {
    assertLogicalKey(prefix);
    const ownerRoot = `${p.id}/${p.indexKey}/`;
    const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
    const full = await this.collectObjectPaths(dirPath); // returns full object paths (or [] if absent)
    return full.map((f) => f.slice(ownerRoot.length)); // strip owner root → logical key
  }
```

**The change is one added line in `objectKey` and `deletePrefix`, and a rewritten `map` body in
`list`.** `collectObjectPaths` (`:151`) is untouched. ⚙ **EXECUTED — this exact code produced the
behavior-8/9/10/12 results and left both existing tests green:**

```ts
  private objectKey(p: Principal, key: string): string {
    assertLogicalKey(key);
    const physical = key.split('/').map(encodeSegment).join('/');   // <- the only new line
    return `${p.id}/${p.indexKey}/${physical}`;
  }

  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    assertLogicalKey(prefix);
    const physicalPrefix = prefix.split('/').map(encodeSegment).join('/');   // <- new
    const root = `${p.id}/${p.indexKey}/${physicalPrefix}`.replace(/\/$/, '');
    // …the batching loop below is UNCHANGED…
  }

  async list(p: Principal, prefix: string): Promise<string[]> {
    assertLogicalKey(prefix);
    const norm = prefix === '' || prefix.endsWith('/') ? prefix : `${prefix}/`;
    const ownerRoot = `${p.id}/${p.indexKey}/`;
    const physicalPrefix = norm.split('/').map(encodeSegment).join('/');   // <- new
    const dirPath = `${ownerRoot}${physicalPrefix}`.replace(/\/$/, '');
    const full = await this.collectObjectPaths(dirPath);
    return full.map((f) => {
      const remainder = f.slice(ownerRoot.length + physicalPrefix.length);  // <- the LEAF only
      // The `=h` marker guard applies to the REMAINDER ONLY — never the caller's own prefix, or a
      // logical key legitimately containing `=` strands a video every run (behavior 10, spec 3.3).
      if (remainder.split('/').some((seg) => seg.includes('=h'))) {
        throw new Error(
          `list: physical segment ${JSON.stringify(remainder)} cannot be mapped back to a logical `
          + `key. The caller supplies the prefix; leaves must be SAFE (spec 3.3, premise P4).`,
        );
      }
      return norm + remainder;                       // re-attach the caller's LOGICAL prefix
    });
  }
```

Traced by hand and then executed, for all three prefix shapes: `''` → `norm` and `physicalPrefix`
are both `''`, `dirPath` is the owner root with its trailing slash stripped, remainder is the whole
logical key — **identical to today**. `'dig/base/'` → `physicalPrefix` is `'dig/base/'` and the
remainder is the leaf. `'dig/003_한국어'` (no trailing slash) → `norm` adds one, the encoded prefix
ends in `/`, and `ownerRoot.length + physicalPrefix.length` lands exactly on the leaf.

- [ ] **Step 4: Run the unit tests** — UNIT: `npx tsc --noEmit && npx jest tests/lib/storage/`.
      Expected: PASS.

- [ ] **Step 5: Write the integration tests (needs the local Supabase stack)** — INTEGRATION

```ts
// tests/integration/blob-encoding.test.ts
const KOREAN = '003_한국어.md';

it('behavior 6 — put then get round-trips a Korean key', async () => {
  await blob.put(P, KOREAN, Buffer.from('hi', 'utf8'), 'text/markdown');
  expect((await blob.get(P, KOREAN))!.toString('utf8')).toBe('hi');
});

it('behavior 7 — putStaged then promote lands a Korean key correctly', async () => {
  const ref = await blob.putStaged(P, KOREAN, Buffer.from('body', 'utf8'), 'text/markdown');
  await blob.promote(ref);
  expect((await blob.get(P, KOREAN))!.toString('utf8')).toBe('body');
});

it('behavior 11 — deletePrefix("") removes everything under the playlist root', async () => {
  await blob.put(P, KOREAN, Buffer.from('x', 'utf8'), 'text/markdown');
  await blob.deletePrefix(P, '');
  expect(await blob.get(P, KOREAN)).toBeNull();
});

it('behavior 13 — the local and in-memory adapters are IDENTITY', async () => {
  for (const store of [localBlobStore, new InMemoryBlobStore()]) {
    await store.put(LOCAL_P, KOREAN, Buffer.from('x', 'utf8'), 'text/markdown');
    expect(await store.list(LOCAL_P, '')).toContain(KOREAN);
  }
});
```

Assert in `beforeAll` that `process.env.SUPABASE_URL` contains `127.0.0.1` or `localhost` and
**throw otherwise**. Clean up every object created. `LOCAL_P` is `localPrincipal(<a mkdtemp dir>)`.

- [ ] **Step 6: Run and commit**

```bash
npx tsc --noEmit && npm test && npm run test:integration -- tests/integration/blob-encoding.test.ts
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/storage/supabase/supabase-blob-store.ts tests/lib/storage/blob-store-list.test.ts tests/integration/blob-encoding.test.ts
git commit -m "feat(#36): encode at the storage seam; list re-attaches the logical prefix (behaviors 6-13)"
```

---

## Task 3: `slugify` drops an orphaned surrogate half

**Spec:** §3.7 and the round-12 H1 box in §3.2. **Behaviors:** 16b.

**Why this is a defect repair, not a naming change:** those titles *today* produce mojibake vault filenames — APFS returns a U+FFFD-bearing name for a key written with a lone high surrogate, and two different lone surrogates collapse onto one file, silently destroying one video's content. Measured. This removes a broken output nobody wants. It is **not** backlog #46 (the NFKC slice), which changes *readable* names and needs its own migration argument.

**Files:**
- Modify: `lib/slugify.ts`
- Test: `tests/lib/slugify.test.ts` — **UNIT**

**Interfaces:** Consumes nothing. Produces: `slugify`'s output is now guaranteed well-formed UTF-16 — T4's predicate and T10's mint guard both rely on this.

- [ ] **Step 1: Write the failing test** — ⚙ **EXECUTED: the current implementation returns an
      ill-formed slug for this fixture, so the test is genuinely red; the repaired one returns
      well-formed. Sweep: 1,536 iterations, 0 violations.**

```ts
it('behavior 16b — never returns ill-formed UTF-16', () => {
  // An astral letter straddling the 60-unit slice boundary leaves an orphaned half.
  const title = 'a'.repeat(59) + '\u{20000}';   // 59 BMP + 1 astral = 61 UTF-16 units
  expect(slugify(title).isWellFormed()).toBe(true);
});

it('behavior 16b — property sweep: no codepoint produces an ill-formed slug', () => {
  for (let cp = 0x10000; cp <= 0x10ffff; cp += 0x800) {
    for (const pad of [58, 59, 60]) {
      expect(slugify('a'.repeat(pad) + String.fromCodePoint(cp)).isWellFormed()).toBe(true);
    }
  }
});
```

- [ ] **Step 2: Run to verify it fails** — UNIT: `npx jest tests/lib/slugify.test.ts -t 'ill-formed'`.
      Expected: FAIL — `expected false to be true`.

- [ ] **Step 3: Apply the one-line repair**

`lib/slugify.ts` is 7 lines and is one chained expression, verbatim today:

```ts
export function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}
```

**The change:** bind the chain to a const and return the repaired value. ⚙ **EXECUTED:**

```ts
export function slugify(title: string): string {
  // .slice(0, 60) cuts UTF-16 code units and can split a surrogate pair. Node then encodes the
  // orphaned half as U+FFFD on the way to a filesystem path, so the vault filename becomes
  // mojibake AND two different lone surrogates collapse onto one file (MEASURED on APFS).
  const s = title
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
  return s.isWellFormed() ? s : s.slice(0, -1);   // drop the orphaned half
}
```

- [ ] **Step 4: Run and verify** — UNIT: `npx tsc --noEmit && npm test`. `slugify` is widely used, so
      the whole unit suite is the blast radius, not `tests/lib/slugify.test.ts`. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/slugify.ts tests/lib/slugify.test.ts
git commit -m "fix(#36): slugify drops an orphaned surrogate half (spec 3.7, behavior 16b)"
```

---

## Task 4: Replace the allowlist with `isServableSummaryKey`

**Spec:** §3.4. **Behaviors:** 16c, 17, 17b, 17d, 17e, 24, 27.

**The whole fix, in one sentence:** the old guard allowlists `[\p{L}\p{N}_-]` while its own docstring says the requirement is *"a single path component"*. Those are different, and the difference is what destroys a Korean-titled paid summary.

**Files:**
- Modify: `lib/html-doc/assert-cloud-summary-md-key.ts`
- Test: `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts` — **UNIT**

**Interfaces:**
- Consumes: nothing (behavior 27's test also imports `slugify`, so run T3 first).
- Produces: **`isServableSummaryKey(key: string): boolean`** — the predicate T5, T9, T10, T11, T12 all install. `assertCloudSummaryMdKey(mdKey: string): void` keeps its name, its throwing contract and its `statusCode: 409`, so its **two** callers are unchanged: `lib/html-doc/serve-summary-core.ts:61` and `lib/dig/cloud/resolve-summary-key.ts:16`. *(Counted: v2 said "three consumers" and listed `pdf-render-version.ts`, which mentions the guard only in a comment at `:14` and never calls it.)*

- [ ] **Step 1: Write the failing test** — ⚙ **EXECUTED: every case below produces the asserted
      result under Node 22.14.0.**

```ts
import { isServableSummaryKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
import { slugify } from '@/lib/slugify';

describe('isServableSummaryKey', () => {
  it('behavior 14/15/16/23 — ACCEPTS what the old allowlist destroyed', () => {
    for (const k of [
      '003_한국어.md',                          // Korean
      ('003_café.md').normalize('NFD'),         // NFD accented Latin
      '003_hello world.md',                     // a space
      '003_\u{1F600}.md',                       // emoji
      '003_lesson-⒈.md',                        // DIGIT ONE FULL STOP — the round-11 B1 class
      '003_\u{1F100}.md',
    ]) expect(isServableSummaryKey(k)).toBe(true);
  });

  it('behavior 17 — REJECTS everything that is not a single path component', () => {
    for (const k of [
      'nested/foo.md', '003_a%2fb.md', '003_a／b.md',   // separators, in every form
      '℀.md',                                          // NFKC-folds to `a/c`
      '001_a．．b.md', '001_a..b.md',                   // traversal-shaped
      '003_x\u0007.md', '003_x\u0085.md',              // C0 (BEL) and C1 (NEL) — ESCAPES ONLY
      '003_x\u202E.md',                                // RIGHT-TO-LEFT OVERRIDE
      '003_' + 'a'.repeat(200) + '.md',                // over-long
    ]) expect(isServableSummaryKey(k)).toBe(false);
  });

  it('behavior 16c — rejects ILL-FORMED UTF-16', () => {
    expect(isServableSummaryKey('003_x\uD840.md')).toBe(false);
  });

  it('behavior 17d — inspects the NAME, not name + ".md"', () => {
    // DIGIT ONE FULL STOP NFKC-folds to `1.`; gluing `.md` on manufactures a `..` in neither piece.
    expect(isServableSummaryKey('003_lesson-⒈.md')).toBe(true);
    expect(isServableSummaryKey('003_lesson-1..md')).toBe(true);
  });

  it('behavior 17b — the bound did NOT narrow: 129, 130 and 131 are ACCEPTED', () => {
    for (const n of [129, 130, 131]) {
      expect(isServableSummaryKey('a'.repeat(n - 3) + '.md')).toBe(true);
    }
    expect(isServableSummaryKey('a'.repeat(129) + '.md')).toBe(false);   // 132
  });

  it('behavior 24 — the bound counts CODE POINTS, not UTF-16 units', () => {
    const key = '\u{20000}'.repeat(64) + '.md';   // 67 code points, 131 UTF-16 units
    expect([...key].length).toBe(67);
    expect(isServableSummaryKey(key)).toBe(true);
  });

  it('behavior 17e — every Bidi_Control code point is rejected, DERIVED not counted', () => {
    // MEASURED: 12 such code points exist; 0 violations; the full stride-1 walk takes ~54ms.
    let seen = 0;
    for (let cp = 0; cp <= 0x10ffff; cp++) {
      if (cp >= 0xd800 && cp <= 0xdfff) continue;
      const ch = String.fromCodePoint(cp);
      if (/\p{Bidi_Control}/u.test(ch)) {
        seen += 1;
        expect(isServableSummaryKey(`003_x${ch}.md`)).toBe(false);
      }
    }
    expect(seen).toBe(12);   // if Unicode adds one, this goes red and the claim is re-earned
  });
});
```

- [ ] **Step 2: Run to verify it fails** — UNIT:
      `npx jest tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`.
      Expected: FAIL — the module has no such export.

- [ ] **Step 3: Implement the predicate** — ⚙ **EXECUTED verbatim.**

```ts
export function isServableSummaryKey(key: string): boolean {
  if (!key.endsWith('.md')) return false;
  // CODE POINTS, not UTF-16 units — the guard this replaces counts code points (it is a /u
  // regex) and this predicate's whole subject is non-ASCII keys. 131 = that guard's ceiling.
  const cp = [...key];
  if (cp.length <= 3 || cp.length > 131) return false;
  // A lone surrogate does not survive the local filesystem: Node encodes it as U+FFFD, the
  // vault filename becomes mojibake, and two DIFFERENT lone surrogates collapse onto one file.
  if (!key.isWellFormed()) return false;

  // Inspect the NAME, NEVER the glued key: folding `name + '.md'` manufactures a `..` at the
  // joint out of one legal character (DIGIT ONE FULL STOP folds to `1.`).
  const name = key.slice(0, -3);
  // Raw form AND compatibility-folded form. ACCOUNT-OF folds to `a/c`, FULLWIDTH REVERSE
  // SOLIDUS to a backslash.
  //
  // ⚠ SCOPE, measured — do not restate this as "NFKC closes the homoglyph class" (round-1 M2,
  // round-2 M4/H2 — the false version survived two rounds). NFKC closes the
  // COMPATIBILITY-DECOMPOSABLE separator forms. FRACTION SLASH (U+2044) and DIVISION SLASH
  // (U+2215) have NO NFKC decomposition to `/` and are therefore ACCEPTED here. That is
  // deliberate and safe: neither is a path separator on any backend this app writes to, the
  // encoder hashes the whole segment before Storage ever sees it, and the serve path hands the
  // key straight to blobStore.get without re-parsing it (serve-summary-core.ts:66). A hand-typed
  // homoglyph denylist would be the alternative, and it cannot be complete either.
  for (const s of [name, name.normalize('NFKC')]) {
    if (s === '' || s === '.' || s === '..') return false;
    if (s.includes('/') || s.includes('\\')) return false;
    if (s.includes('..')) return false;
    if (/[\x00-\x1f\x7f-\x9f]/.test(s)) return false;          // C0 + DEL + C1
    if (/%2f|%5c/i.test(s)) return false;                      // percent-encoded separators
    if (/\p{Bidi_Control}/u.test(s)) return false;             // the PROPERTY, not a hand list
  }
  return true;
}

export function assertCloudSummaryMdKey(mdKey: string): void {
  // ⚠ Round-1 M1: the `typeof` test must stay, and must come FIRST. 4 existing assertions pass
  // null/undefined/123/{} and expect a 409 — without the short-circuit, `key.endsWith` throws a
  // TypeError with no statusCode. And `statusCode: 409` itself is what makes this a 409 rather
  // than a 500; 22 existing assertions read it.
  if (typeof mdKey !== 'string' || !isServableSummaryKey(mdKey)) {
    throw Object.assign(
      new Error(`not a servable summary key: ${JSON.stringify(mdKey)}`),
      { statusCode: 409 },
    );
  }
}
```

- [ ] **Step 4: Run the WHOLE unit suite, and dispose of the five flips** — UNIT: `npx tsc --noEmit && npm test`

Round-1 M7: this predicate has two callers and 22 existing assertions; a slice narrower than the
blast radius is not a verification. **Expected: NOT a clean pass — exactly 5 named failures in
`tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`, and nothing else.** ⚙ **MEASURED by running
the Step-3 predicate against all 23 existing cases: 5/5 accepts kept, 5 of 18 rejections flip.**
Update those five rows, and record the disposition in the commit:

| Existing case | Key | Now | Disposition |
|---|---|---|---|
| `double-dot` | `foo..md` | ACCEPT | **Intended.** The name is `foo.`, which is a legal single path component. The old row asserted the ALLOWLIST (`.` was outside it), not the requirement. Move it to the accept list. |
| `leading-space` | `' foo.md'` | ACCEPT | **Intended.** A leading space is legal in a filename and behavior 16 requires spaces. Move it to the accept list. |
| `leading-dot` | `.foo.md` | ACCEPT | **Intended.** A dotfile is a single path component. Move it to the accept list. |
| `fraction-slash-2044` | `a⁄b.md` | ACCEPT | **Deliberate, and NOT what v2 claimed.** U+2044 has no NFKC decomposition to `/`. Keep the case, flip the expectation, and point its comment at the SCOPE paragraph in Step 3. |
| `division-slash-2215` | `a∕b.md` | ACCEPT | Same as above for U+2215. |

The other 13 rejections and all 4 non-string cases are unchanged. If a **sixth** row fails, stop —
that is a defect, not a widening.

- [ ] **Step 5: Add the cross-derivation property test (behavior 27)** — UNIT

⚠ **Round-1/round-2 L2.** v2 named this *"over the whole codepoint space"* while striding `0x20`.
v3 pays for the name: ⚙ **EXECUTED at stride 1, all four title forms — 4,448,256 loop iterations,
of which 3,479,131 are NON-EMPTY SLUG ASSERTIONS (969,125 empty slugs are skipped), 0 predicate
violations, 8.8 s.** That is over jest's 5,000 ms default, so the timeout argument is REQUIRED.
*(Round-3 Codex M1 — v3 called the 3,479,131 "iterations", which is the assertion count, not the
loop count. The SPEC inherits the same wording; it is CLOSED, so it is not edited here — the
correction is recorded in the Self-Review's round-3 table so it is not lost.)*

```ts
it('behavior 27 — NO slugify output fails the predicate, over the whole codepoint space', () => {
  // The cross-derivation §3.4 and §3.5 each ASSUMED and neither checked. Stride 1 — the name
  // says "the whole codepoint space" and this walks it. MEASURED: 4448256 loop iterations,
  // 3479131 non-empty-slug assertions, 969125 empty slugs skipped, 0 violations, ~8.8s on Node
  // 22.14.0 — which is why the 30s timeout below is not optional.
  for (let cp = 0; cp <= 0x10ffff; cp += 1) {
    if (cp >= 0xd800 && cp <= 0xdfff) continue;
    const ch = String.fromCodePoint(cp);
    for (const title of [ch, `a${ch}`, `${ch}a`, 'a'.repeat(59) + ch]) {
      const slug = slugify(title);
      if (slug === '') continue;      // empty slug is a separate, handled case
      expect(isServableSummaryKey(`001_${slug}.md`)).toBe(true);
    }
  }
}, 30_000);
```

- [ ] **Step 6: Commit**

```bash
npx tsc --noEmit && npm test
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/html-doc/assert-cloud-summary-md-key.ts tests/lib/html-doc/assert-cloud-summary-md-key.test.ts
git commit -m "feat(#36): isServableSummaryKey asserts single-path-component, not ASCII (behaviors 16c,17,17b,17d,17e,24,27)"
```

---

## Task 5: The share guard moves inside `getShareServeContext`

**Spec:** §3.4. **Behaviors:** 21. **§3.5.1b row 6.**

The share path builds `base` at **two** places (`app/s/[token]/route.ts:69` and `:78`). Guarding both is enumeration; guarding the one function that produces `mdKey` covers them **by construction**.

**Files:**
- Modify: `lib/share/serve.ts` (after the `mdKey` assignment at `:47`)
- Test: `tests/integration/share-serve.test.ts` — **INTEGRATION**

⛔ **Round-1 L4 / round-2 M8, CLOSED by choosing the other file.** v2 targeted
`tests/integration/share-route.test.ts`, which does `jest.mock('@/lib/share/serve', …)` at `:37-50`
and wraps `getShareServeContext` in a counting delegate with module-level counters an existing test
arms on `sinceArm === 2`. A new test calling `getShareServeContext` in that file perturbs shared
state. **`tests/integration/share-serve.test.ts` has no module mock**, imports
`getShareServeContext` directly (`:5`), and already carries the two helpers these tests need —
`seedDoc(ownerId, status?)` (`:11`) and `mintDirect(ownerId, playlistId, videoId, over?)` (`:17`).
It is the file whose entire subject is this function.

**Interfaces:**
- Consumes: `isServableSummaryKey` from T4.
- Produces: `getShareServeContext` may now return `{ status: 'denied' }` for a promoted-but-unservable key.

- [ ] **Step 1: Write the failing test** — INTEGRATION

`seedDoc` calls `seedPromotedVideo(svc, { ownerId, playlistId, status })`, whose `base` option
(`tests/integration/helpers/seed.ts:26`) sets both `data.summaryMd` and
`data.artifacts.summaryMd.key` to `` `${base}.md` `` — so an unservable key is seeded by passing
`base`, with no new helper.

```ts
it('behavior 21 — a promoted but UNSERVABLE mdKey is denied, from inside the context helper', async () => {
  const u = await newUser();
  const { playlistId } = await seedPlaylist(svc, u.user.id);
  const { videoId } = await seedPromotedVideo(svc, {
    ownerId: u.user.id, playlistId, base: 'nested/evil',      // -> summaryMd 'nested/evil.md'
  });
  const token = await mintDirect(u.user.id, playlistId, videoId);
  expect(await getShareServeContext(svc, token)).toEqual({ status: 'denied' });
});

it('behavior 21 — a Korean key is NOT denied', async () => {
  const u = await newUser();
  const { playlistId, playlistKey } = await seedPlaylist(svc, u.user.id);
  const { videoId } = await seedPromotedVideo(svc, {
    ownerId: u.user.id, playlistId, base: '003_한국어',
  });
  const token = await mintDirect(u.user.id, playlistId, videoId);
  const ctx = await getShareServeContext(svc, token);
  expect(ctx).toMatchObject({ playlistKey, mdKey: '003_한국어.md' });
});
```

- [ ] **Step 2: Run to verify it fails** — INTEGRATION:
      `npm run test:integration -- tests/integration/share-serve.test.ts -t 'behavior 21'`.
      Expected: FAIL — the first case returns a context instead of `denied`.

- [ ] **Step 3: Implement**

`lib/share/serve.ts:44-48`, verbatim today:

```ts
  const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
    .artifacts?.summaryMd;
  if (artifact?.status !== 'promoted') return denied;
  const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
  if (!mdKey) return denied;
```

**The change:** one line immediately after `:48`.

```ts
  // §3.5.1b row 6: `mdKey` has TWO producers — `artifact?.key` (taken first) and the top-level
  // `summaryMd` fallback. This guard is provenance-BLIND: both arms are refused identically,
  // and it tests exactly the value the serve path goes on to consume. `mdKey` is a narrowed
  // `string` here because of the `if (!mdKey)` above.
  if (!isServableSummaryKey(mdKey)) return denied;
```

- [ ] **Step 4: Run and verify** — INTEGRATION:
      `npx tsc --noEmit && npm run test:integration -- tests/integration/share-serve.test.ts`.
      Expected: PASS.

- [ ] **Step 5: Commit**

```bash
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/share/serve.ts tests/integration/share-serve.test.ts
git commit -m "feat(#36): the share guard lives inside getShareServeContext, covering both base derivations (behavior 21)"
```

---

## Task 6: `promoteIfAbsent` on the BlobStore seam

**Spec:** §3.6.2. **Behaviors:** 18d, 18d2, 18d3, 18d4, 18d5, 18f.

**Files:**
- Modify: `lib/storage/blob-store.ts` (the interface + two new exports),
  `lib/storage/local/local-blob-store.ts`, `lib/storage/testing/in-memory-blob-store.ts`,
  `lib/storage/supabase/supabase-blob-store.ts`, plus **4 more implementers** (see Step 6)
- Create: `tests/support/blob-store-contract-cases.ts` — the shared contract, imported by BOTH suites
- Test: `tests/lib/storage/blob-store-contract.test.ts` — **UNIT** (local + in-memory);
  `tests/integration/blob-store.test.ts` — **INTEGRATION** (Supabase; the file already exists)

**Why the contract lives in `tests/support/`:** `jest.config.ts` matches `tests/lib/**`,
`tests/api/**`, `tests/scripts/**`, `tests/smoke.test.ts`, `tests/components/**` and
`jest.integration.config.ts` matches `tests/integration/**` — **neither matches `tests/support/`**,
so a plain module there is importable by both and collected by neither. That is what lets one set of
cases run against all three adapters without duplicating them or dragging Supabase into the unit run.

**Interfaces:**
- Consumes: nothing.
- Produces: **`promoteIfAbsent(ref: StagedRef): Promise<void>`** on `BlobStore`; plus two helpers
  exported from `lib/storage/blob-store.ts`: **`stagingRootOf(tempKey: string): string`** (new) and
  **`contentTypeForKey(key: string): string`** (exists at `:103`, currently module-private — the
  Supabase adapter needs it because `StagedRef` carries no content type).
- **`promote` is unchanged** (behavior 18d4) and keeps its existing callers.

- [ ] **Step 1: Write the shared contract cases** — ⚙ **EXECUTED against a faithful transcription of
      both the local and the in-memory adapter: 12/12 assertions pass on each.**

```ts
// tests/support/blob-store-contract-cases.ts
// NOT a *.test.ts: neither jest config matches tests/support/, so this module is imported by the
// unit contract file (local + in-memory) AND by the integration one (Supabase). One set of cases,
// three adapters, no duplication and no live stack in the unit run.
export function promoteIfAbsentContract(
  label: string, makeStore: () => BlobStore, makePrincipal: () => Principal | Promise<Principal>,
): void {
  describe(`${label}: promoteIfAbsent`, () => {
    const KEY = '003_x.md';

    it('behavior 18d — leaves an existing occupant BYTE-IDENTICAL', async () => {
      const store = makeStore(); const P = await makePrincipal();
      await store.put(P, KEY, Buffer.from('occupant', 'utf8'), 'text/markdown');
      const ref = await store.putStaged(P, KEY, Buffer.from('newcomer', 'utf8'), 'text/markdown');
      await store.promoteIfAbsent(ref);
      expect((await store.get(P, KEY))!.toString('utf8')).toBe('occupant');
    });

    it('behavior 18d2 — RESOLVES rather than throwing on an existing final, and removes the staging tree', async () => {
      const store = makeStore(); const P = await makePrincipal();
      await store.put(P, KEY, Buffer.from('occupant', 'utf8'), 'text/markdown');
      const ref = await store.putStaged(P, KEY, Buffer.from('x', 'utf8'), 'text/markdown');
      await expect(store.promoteIfAbsent(ref)).resolves.toBeUndefined();
      expect(await store.get(P, ref.tempKey)).toBeNull();
      expect(await store.list(P, '_staging/')).toEqual([]);      // the WHOLE tree, not just the file
    });

    it('behavior 18d3 — creates missing parents, and leaves no _staging tree, on a NESTED key', async () => {
      // Nested deliberately: a plain rmdir here is ENOTEMPTY on exactly the branch this tests.
      const store = makeStore(); const P = await makePrincipal();
      const nested = 'dig/003_base/s1.r2.md';
      const ref = await store.putStaged(P, nested, Buffer.from('body', 'utf8'), 'text/markdown');
      await store.promoteIfAbsent(ref);
      expect((await store.get(P, nested))!.toString('utf8')).toBe('body');
      expect(await store.list(P, '_staging/')).toEqual([]);
    });

    it('an ABSENT final takes the newcomer', async () => {
      const store = makeStore(); const P = await makePrincipal();
      const ref = await store.putStaged(P, KEY, Buffer.from('newcomer', 'utf8'), 'text/markdown');
      await store.promoteIfAbsent(ref);
      expect((await store.get(P, KEY))!.toString('utf8')).toBe('newcomer');
    });

    it('a tempKey that is not `_staging/<uuid>/…` is REFUSED before any write', async () => {
      const store = makeStore(); const P = await makePrincipal();
      await expect(store.promoteIfAbsent({ principal: P, tempKey: 'notstaging/x.md', finalKey: KEY }))
        .rejects.toThrow(/not a _staging/);
      expect(await store.get(P, KEY)).toBeNull();
    });
  });
}
```

Plus, in the **unit** file only, the one case that asserts what `promoteIfAbsent` is NOT:

```ts
it('behavior 18d4 — `promote` is UNCHANGED: it still overwrites (local semantics)', async () => {
  const store = new InMemoryBlobStore();            // default promoteSemantics: 'overwrite'
  await store.put(P, KEY, Buffer.from('old', 'utf8'), 'text/markdown');
  const ref = await store.putStaged(P, KEY, Buffer.from('new', 'utf8'), 'text/markdown');
  await store.promote(ref);
  expect((await store.get(P, KEY))!.toString('utf8')).toBe('new');
});

it('behavior 18d4 — and it still SKIPS under create-if-absent semantics (Supabase)', async () => {
  const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
  await store.put(P, KEY, Buffer.from('old', 'utf8'), 'text/markdown');
  const ref = await store.putStaged(P, KEY, Buffer.from('new', 'utf8'), 'text/markdown');
  await store.promote(ref);
  expect((await store.get(P, KEY))!.toString('utf8')).toBe('old');
});
```

*(Both were executed. The pair is the point: `InMemoryBlobStore`'s docstring at `:15-30` says it
models BOTH shipped adapters because they disagree, and `promoteIfAbsent` must be uniform where
`promote` is not.)*

- [ ] **Step 2: Run to verify it fails** — UNIT: `npx jest tests/lib/storage/blob-store-contract.test.ts`.
      Expected: FAIL — `store.promoteIfAbsent is not a function`.

- [ ] **Step 3: Add the interface method and the two shared helpers**

`lib/storage/blob-store.ts:5` is verbatim `export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }`
and `:103` is verbatim `function contentTypeForKey(key: string): string {`.

```ts
// lib/storage/blob-store.ts — on the BlobStore interface, beside `promote` at :73
  /** Create-if-absent finalize. Resolves (never throws) when the final already exists, leaves its
   *  bytes untouched, and removes the staging tree either way. `promote` is the OVERWRITE form and
   *  is unchanged — the two backends genuinely disagree about `promote` (see InMemoryBlobStore's
   *  docstring), and this primitive exists so the additive path does not have to care. */
  promoteIfAbsent(ref: StagedRef): Promise<void>;
```

```ts
// lib/storage/blob-store.ts — module level, beside assertLogicalKey at :87
/** The `_staging/<uuid>` root that `putStaged` created for this ref.
 *
 *  DERIVED from `tempKey`, because no adapter stores staging state: all three build
 *  `` `_staging/${crypto.randomUUID()}/${key}` `` (local :53, supabase :104, in-memory :152).
 *  The shape is ASSERTED rather than assumed — a malformed tempKey must fail loudly here, before
 *  any adapter starts deleting a prefix computed from it. Shared so the three adapters cannot
 *  drift apart the way `promote()` did (architecture review finding #2). */
export function stagingRootOf(tempKey: string): string {
  const seg = tempKey.split('/');
  if (seg.length < 3 || seg[0] !== '_staging' || seg[1] === '') {
    throw new Error(`stagingRootOf: ${JSON.stringify(tempKey)} is not a _staging/<uuid>/... key`);
  }
  return `${seg[0]}/${seg[1]}`;
}
```

And change `function contentTypeForKey` at `:103` to `export function contentTypeForKey`. Nothing
else about it moves; `copyBlob` at `:156` keeps using it.

**Cleanup is `this.deletePrefix(ref.principal, stagingRoot)` on ALL THREE adapters** — an existing,
already-tested primitive that each one implements correctly for its own backend (local `:66` is
`fs.promises.rm(..., {recursive:true, force:true})`, in-memory `:181` walks the key map, Supabase
`:129` collects and batch-removes). That is why v2's hand-written `rmSync(this.stagingRoot(ref))`
(round-1 M3 / round-2 M1 / Codex B3 — `stagingRoot` had **0** occurrences in the repo and the bare
`rmSync`/`mkdirSync`/`dirname` did not resolve, because `local-blob-store.ts:1` imports namespaces
only) is not merely repaired here, it is replaced by something that already works.

- [ ] **Step 4: Implement on all three adapters**

**Local** — ⚙ **EXECUTED, 12/12:**

```ts
// lib/storage/local/local-blob-store.ts — beside promote() at :58. fs/path/crypto are DEFAULT
// imports (:1) — round-3 Claude L3; every call is qualified either way, and this body was executed.
  async promoteIfAbsent(ref: StagedRef): Promise<void> {
    const stagingRoot = stagingRootOf(ref.tempKey);            // validates BEFORE any I/O
    const final = this.abs(ref.principal, ref.finalKey);       // `abs` is the class's own helper, :12
    fs.mkdirSync(path.dirname(final), { recursive: true });    // 18d3 — missing parents
    try {
      fs.linkSync(this.abs(ref.principal, ref.tempKey), final);  // atomic create-if-absent
    } catch (e: any) {
      if (e?.code !== 'EEXIST') throw e;                       // 18d2 — an existing final RESOLVES
    } finally {
      await this.deletePrefix(ref.principal, stagingRoot);     // 18f — the WHOLE tree
    }
  }
```

**In-memory** — ⚙ **EXECUTED, 12/12, under both `promoteSemantics` settings.** The field is
`private readonly blobs = new Map<string, StoredBlob>()` (`:45`) — **not** `this.map`, and the value
is a `StoredBlob`, not a `Buffer` (round-2 M2 caught v2 naming a field that does not exist):

```ts
// lib/storage/testing/in-memory-blob-store.ts — beside promote() at :157
  async promoteIfAbsent(ref: StagedRef): Promise<void> {
    if (this.promoteFault !== undefined) throw this.promoteFault;
    const stagingRoot = stagingRootOf(ref.tempKey);
    const from = this.physical(ref.principal, ref.tempKey);
    const to = this.physical(ref.principal, ref.finalKey);
    const staged = this.blobs.get(from);
    try {
      if (!staged) {
        if (this.blobs.has(to)) return;                        // already promoted — idempotent
        throw new Error(`promoteIfAbsent: staged blob missing for ${ref.finalKey}`);
      }
      if (!this.blobs.has(to)) this.blobs.set(to, staged);      // create-if-absent
    } finally {
      await this.deletePrefix(ref.principal, stagingRoot);      // 18f
    }
  }
```

**Supabase** — ⚠ **THE ONE SNIPPET IN THIS DOCUMENT THAT WAS NOT EXECUTED.** It needs the live
stack, so it is stated as a change to quoted code and its risky assumption is removed rather than
asserted. Round-1 M4 / round-2 M2 / Codex B4 both said v2's recipe was unimplementable: it said
*"`upload()` without `upsert` returns HTTP 409 — treat 409 as success"* while `promoteIfAbsent(ref)`
**has no bytes to upload**, and it never removed the staging tree.

The relevant code today, verbatim — note that `promote` already solves the harder half of this:

```ts
// lib/storage/supabase/supabase-blob-store.ts:22-25
  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
    if (error) throw error;
  }

// :109-127 — the EXISTING create-if-absent recovery, which this method copies
  async promote(ref: StagedRef): Promise<void> {
    …
    const { error } = await this.b().move(from, to);
    if (error) {
      // A concurrent promoter … may have won the race: destination-exists / source-missing.
      // Re-check the final; treat a present final as success, else rethrow.
      if (await this.exists(ref.principal, ref.finalKey)) { … return; }
      throw error;
    }
  }
```

**The change:** read the staged bytes through `tryGet` (the honest probe on this backend, `:63`),
upload them to the final key with `upsert: false`, and — instead of classifying the error code —
**re-read the final**, exactly as `promote` already does:

```ts
  async promoteIfAbsent(ref: StagedRef): Promise<void> {
    const stagingRoot = stagingRootOf(ref.tempKey);
    try {
      const staged = await this.tryGet(ref.principal, ref.tempKey);
      if (!staged.ok) {
        // absent OR unreadable. If the final is already there this is a resumed promote; otherwise
        // we cannot produce the bytes and must fail loudly rather than silently do nothing.
        if (await this.exists(ref.principal, ref.finalKey)) return;
        throw new Error(`promoteIfAbsent: staged blob ${ref.tempKey} is ${staged.reason}`);
      }
      const { error } = await this.b().upload(
        this.objectKey(ref.principal, ref.finalKey), staged.bytes,
        { contentType: contentTypeForKey(ref.finalKey), upsert: false },
      );
      if (error) {
        // DELIBERATELY NOT a status-code test. v2 asserted "409 means exists"; nothing in this repo
        // verifies that, and a wrong classification here either throws on success or swallows a real
        // failure. `promote()` at :118-126 already solved this by RE-READING, which is true
        // regardless of how the API spells the collision. Same rule: a present final IS success for
        // a create-if-absent finalize; anything else rethrows the original error.
        if (!(await this.exists(ref.principal, ref.finalKey))) throw error;
      }
    } finally {
      await this.deletePrefix(ref.principal, stagingRoot);   // 18f — the WHOLE tree
    }
  }
```

⚠ **The one thing to confirm at Step 5, and it is a `--` not a `??`:** `exists()` here is
`get() !== null` (`:78-80`) and `get` swallows every failure, so on a transient blip it reports
`false` and this rethrows — *fail-closed*, the safe direction, and the same posture `promote`
already has. Do not "improve" it to `tryGet`-based existence without re-reading ADR-0008; the two
methods must stay the same shape or they will drift apart again.

- [ ] **Step 5: Run the contract against all three adapters**

```bash
npx tsc --noEmit
npx jest tests/lib/storage/blob-store-contract.test.ts          # UNIT: local + in-memory
npm run test:integration -- tests/integration/blob-store.test.ts # INTEGRATION: Supabase
```

- [ ] **Step 6: Fix every implementer — behavior 18d5, and `tsc` is the mechanism**

Counted with `os.walk` over every non-`node_modules` `.ts`/`.tsx`, matching both
`implements BlobStore` and a `BlobStore`-typed object literal: **7 implementers**.

| # | Implementer | File |
|---|---|---|
| 1 | `SupabaseBlobStore` | `lib/storage/supabase/supabase-blob-store.ts:7` |
| 2 | `LocalFsBlobStore` | `lib/storage/local/local-blob-store.ts:7` |
| 3 | `InMemoryBlobStore` | `lib/storage/testing/in-memory-blob-store.ts:41` |
| 4 | `UnreadableModelBlobStore` | `tests/integration/serve-model-unreadable.test.ts:57` |
| 5 | `FailPromoteBlobStore` | `tests/integration/helpers/cloud.ts:168` |
| 6 | `FailModelPutBlobStore` | `tests/integration/helpers/cloud.ts:191` |
| 7 | object literal `const blob: BlobStore = {` | `tests/lib/storage/consistency.test.ts:38` |

4–7 forward to an inner store or are stubs. **`npx tsc --noEmit` is what names them** — that is
behavior 18d5, and v2's command (`npx jest tests/lib/storage/ && npx jest`) could not have gone red,
because SWC strips types. For each fault-injection wrapper (5 and 6) state in a comment whether its
injected fault applies to `promoteIfAbsent`: `FailPromoteBlobStore` **must** make it throw too (it
models "the finalize failed"); `FailModelPutBlobStore` forwards it unchanged (the model is written
with `put`, never staged).

- [ ] **Step 7: Verify and commit**

```bash
npx tsc --noEmit && npm test && npm run test:integration
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/storage/ tests/support/blob-store-contract-cases.ts tests/lib/storage/ tests/integration/
git commit -m "feat(#36): promoteIfAbsent on the BlobStore seam, all three adapters (behaviors 18d-18f)"
```

---

## Task 7: `ModelEnvelopeWriteSchema` — `videoId` required at the write side

**Spec:** §3.6.4. **Behaviors:** 18j5, 18j5b, 18j8. **§3.5.1b row 7.**

**The rule is attached to `serialize()`, not to a writer name.** There are two exported writers and a repo tripwire *forbids* merging them; v17 attached the requirement to one, and the cloud serve path — the writer that spends money — compiled unchanged.

⚠ **Rollout cost. THE NUMBER IS 41, and it has now been counted FIVE times** (round-1 L1: 43; v2: 41
without stating a rule; v4's table: 42; round-4 Codex: 41; round-4 coordinator: 41). **v2's 41 was
right.** THE RULE, which is the only reason the last two agree:

> A call site is the identifier followed by `(` **outside a string literal**, excluding **imports,
> comments, and the two declarations** in `model-store.ts` itself (`:46`, `:66`).

Both halves of that rule have now claimed a victim. Omitting *string literals* produced 42 by
counting the test title `it('writeModelEnvelope overwrites…')` at `tests/lib/model-store-cloud.test.ts:52`.
Omitting *comments* also produced 42, by counting the prose mention of `writeModelEnvelope (plain
put …)` inside the comment at `lib/html-doc/serve-doc.ts:158`. **Count with the rule or do not
count.**

| | v2 said | round 1 said | **counted now** |
|---|---|---|---|
| total call sites | 41 | 43 | **41** |
| production | 3 | 3 | **3** — `generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464` |
| test | 38 | 39 | **38** |
| files | 11 | 11 | **11** (3 production + 8 test) |

The 8 test files, with their counts: `rerender.test.ts` 14, `model-store.test.ts` 8,
`serve-doc-materialize.test.ts` 5, `share-route.test.ts` 4, `model-store-cloud.test.ts` **3**,
`html-download.test.ts` 2, `pdf-cloud.test.ts` 1, `e2e/cloud.setup.ts` 1 — **which sums to 38, and
that itemization is the check on the total.** Expect `tsc` to name all
41 the moment Step 3 lands. That is the mechanism working. *(`tests/e2e/cloud.setup.ts` is a
Playwright file — jest never runs it, but `tsconfig.json` `include` is `**/*.ts`, so `tsc` does.)*

**Files:**
- Modify: `lib/html-doc/model-store.ts`; then `generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464`; then the 8 test files.
- Test: `tests/lib/html-doc/model-store.test.ts` — **UNIT**

**Interfaces:**
- Consumes: nothing.
- Produces: `ModelEnvelopeWriteSchema`, `type ModelEnvelopeWrite`. Both writers now take `ModelEnvelopeWrite`. `ModelEnvelopeSchema` (read) **gains `videoId` as `.optional()`** — see Step 3.

- [ ] **Step 1: Write the failing test** — UNIT

```ts
it('behavior 18j5 — an envelope without videoId cannot be SERIALIZED, via either writer', async () => {
  const bad = { ...ENVELOPE } as any;   // no videoId
  await expect(writeModelEnvelope(P, 'a', bad, store)).rejects.toThrow(/videoId/);
  await expect(writeModelEnvelopeWithin(putBudget(5000), P, 'a', bad, store)).rejects.toThrow(/videoId/);
});

it('behavior 18j5 — asserted through the SERVE writer specifically', async () => {
  // serve-doc.ts calls writeModelEnvelopeWithin; a repo tripwire
  // (tests/lib/html-doc/serve-bounded-import-guard.test.ts) forbids it calling the other.
  const put = jest.fn();
  await expect(
    writeModelEnvelopeWithin(putBudget(5000), P, 'a', { ...ENVELOPE } as any, storeWith(put)),
  ).rejects.toThrow(/videoId/);
  expect(put).not.toHaveBeenCalled();      // fail loud BEFORE any write
});

it('behavior 18j5b — READING a legacy envelope with no videoId still succeeds', async () => {
  await store.put(P, MODEL_KEY('a'), Buffer.from(JSON.stringify(ENVELOPE)), 'application/json');
  const got = await readModelEnvelope(P, 'a', store);
  expect(got).not.toBeNull();
  expect(got!.videoId).toBeUndefined();    // the 7 legacy prod envelopes must still parse
});
```

`storeWith(put)` already exists in this file (a `localBlobStore` clone with `put` swapped, preserving
the prototype). `putBudget` is `tests/support/budget.ts:21`.

- [ ] **Step 2: Run to verify it fails** — UNIT: `npx jest tests/lib/html-doc/model-store.test.ts`.
      Expected: FAIL — no rejection; `videoId` is not required anywhere yet.

- [ ] **Step 3: Implement**

`lib/html-doc/model-store.ts:15-37` today declares `ModelEnvelopeSchema` with six fields
(`sourceMd`, `generatedAt`, `sourceSections`, `generatorVersion?`, `model`, `sourceMdHash?`), a
comment recording that `.strict()` was deliberately removed at `:25-26`, and:

```ts
function serialize(envelope: ModelEnvelope): Buffer {
  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
}
```

**The change**, in three parts:

```ts
// 1. The READ schema gains one OPTIONAL field. ⚠ Round-2 L4: v2 labelled this "unchanged" while
//    changing it. `ModelEnvelopeSchema` has NO videoId today, and behavior 18j5b's
//    `expect(got!.videoId).toBeUndefined()` does not type-check without it. Adding it as
//    `.optional()` is what keeps the 7 legacy production envelopes parseable — and safe precisely
//    because `.strict()` is already off, so old readers tolerated the field before this line existed.
export const ModelEnvelopeSchema = z.object({
  /* …the six existing fields, unchanged… */
  videoId: z.string().optional(),
});

// 2. The WRITE side. Attached to the TYPE `serialize` consumes, so any writer — present or future —
//    must supply it to reach the bytes.
export const ModelEnvelopeWriteSchema = ModelEnvelopeSchema.extend({ videoId: z.string().min(1) });
export type ModelEnvelopeWrite = z.infer<typeof ModelEnvelopeWriteSchema>;

// 3. serialize parses the WRITE schema.
function serialize(envelope: ModelEnvelopeWrite): Buffer {
  ModelEnvelopeWriteSchema.parse(envelope);   // fail loud, BEFORE any write
  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
}
```

Then change the `envelope` parameter type of `writeModelEnvelope` (`:49`) and
`writeModelEnvelopeWithin` (`:70`) from `ModelEnvelope` to `ModelEnvelopeWrite`.

- [ ] **Step 4: Run `tsc` and fix all 41 call sites** — `npx tsc --noEmit`. Expected: ~41 errors.

The production sources for the value, all verified in scope:

| Site | Where `videoId` comes from |
|---|---|
| `generate.ts:50` | `runHtmlDoc(videoId: string, outputFolder, …)` — its **first parameter** (`generate.ts:11-12`) |
| `serve-doc.ts:174` | `resolveMagazineModel(args)` declares `videoId: string` at `:48` and destructures it at `:70` |
| `sync-run.ts:464` | **stamp the RECEIVER's** `videoId` — `winnerVideo.id`, in scope at `:445`. NEVER ship the sender's envelope verbatim. T8 Step 3 does exactly this. |

- [ ] **Step 5: Add behavior 18j8** — UNIT

```ts
it('behavior 18j8 — a LOCAL serial migration preserves videoId through the JSON round-trip', () => {
  const before = JSON.stringify({ ...ENVELOPE, videoId: 'dQw4w9WgXcQ', sourceMd: 'old.md' });
  const after = JSON.parse(rewriteEnvelopeSourceMd(before, 'new.md'));
  expect(after.sourceMd).toBe('new.md');
  expect(after.videoId).toBe('dQw4w9WgXcQ');   // unknown-field preservation is why this bypass is safe
});
```

- [ ] **Step 6: Run everything and commit**

```bash
npx tsc --noEmit && npm test && npm run test:integration
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/html-doc/ lib/cloud-sync/sync-run.ts tests/
git commit -m "feat(#36): videoId required at the model WRITE schema, enforced in serialize (behaviors 18j5,18j5b,18j8)"
```

---

## Task 8: The `videoId` ownership credential in `companionTransfer`

**Spec:** §3.6.4. **Behaviors:** 18j, 18j2, 18j3, 18j4, 18j6, 18j7.

**Why an ID and not a name:** round-13 H1 measured `sourceMd` **stale by construction** — `reconcileCloudBase` byte-copies the envelope and never rewrites it. `videoId` cannot go stale, because nothing in the answer moves.

**Files:**
- Modify: `lib/cloud-sync/sync-run.ts` (`companionTransfer`, `:444-477`)
- Test: `tests/integration/cloud-sync/companion-videoid.int.test.ts` — **INTEGRATION** (new)

**Interfaces:**
- Consumes: `ModelEnvelopeWrite` from T7, `Side` + `companionTransfer` exported by T0.
- Produces: **no new exports and no change to the return type.** `companionTransfer` keeps its
  signature `(winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video)` and its
  `Promise<{ shareNeedsOwnerServe: boolean; error?: string }>` return, and its **never-throws**
  contract.

⛔ **Round-2 B3/H3: `shipped` DOES NOT EXIST and this plan no longer invents it.** v2 asserted
`res.shipped` in four tests while its own Interfaces block said the contract was unchanged. Adding a
return field means touching four return sites (`:465`, `:467`, `:473`, `:476`) and the caller at
`:801-805` — a contract change for a test's convenience. **Assert the observable instead:** behavior
18j6 already reads the loser's envelope back with `readModelEnvelope`, and that is what "shipped"
means. Every test below uses that.

- [ ] **Step 1: Write the failing tests** — INTEGRATION

⛔ **Round-1 L3 / round-2 M7 / round-3 Codex H1 — no argument-less calls, no undeclared symbols,
and the import path is the one the sibling files actually use.** v3's block imported
`./helpers/cloud` from a file under `tests/integration/cloud-sync/` (one directory too shallow) and
used eleven symbols it never declared. Its sibling
[`tests/integration/cloud-sync/e2e.int.test.ts:15-18`](../../../tests/integration/cloud-sync/e2e.int.test.ts)
imports `@/tests/integration/helpers/cloud`, and so does this.

⚙ **WRITTEN AND RUN against the live local stack (127.0.0.1:54321), whole file, both ways:**

| Run | Result |
|---|---|
| **RED** — v3 code, T0 exports + T7's read-side `videoId` applied, no Step-3 guard | **3 failed / 4 passed.** 18j SHIP arm: `res.shareNeedsOwnerServe` was `false`, no error. 18j DELETE arm: `res.error` was `undefined` and the probe printed `envelope after = null` — **today's code DELETES the other video's paid model**, which is round-1 H3 measured rather than argued. 18j6: the receiver's `videoId` came back `"SENDER-WROTE-THIS"` — the sender's claim propagated |
| **GREEN** — Step 3 applied | **7 passed / 7** in 3.4 s |

**The 18j fixture is now TWO cases, because `decideCompanion` reaches the two destructive arms by
different routes** and v3's single fixture only reached one of them. With a sender envelope whose
`sourceMdHash` MATCHES the winner hash, `companion.ts:125` returns `ship` — so v3's comment
("`provablyStale` … DELETES") did not describe its own fixture. The delete arm needs a sender that
does **not** match. Both are below; the guard sits above `decideCompanion` precisely so one
placement covers both.

```ts
// tests/integration/cloud-sync/companion-videoid.int.test.ts
//
// §3.6.4 — `videoId` is the model-ownership credential, and it gates the ship AND the delete.
// Behaviors 18j, 18j2, 18j3, 18j4, 18j6, 18j7.
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import {
  makeOwnerContext, prepareSyncCtx, seedCloudVideo, seedLocalVideoFull,
  cloudVideoRecord, localVideoRecord, type Ctx,
} from '@/tests/integration/helpers/cloud';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { companionTransfer, type Side } from '@/lib/cloud-sync/sync-run';   // exported in T0
import { reconcileCloudBase } from '@/lib/cloud-sync/reconcile-serial';
import {
  writeModelEnvelope, readModelEnvelope, MODEL_KEY, type ModelEnvelopeWrite,
} from '@/lib/html-doc/model-store';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';

jest.setTimeout(30_000);

afterAll(async () => {
  const home = os.homedir();
  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
});

const MD = '# T\n\n## 1. Intro\nbody\n';
/** A schema-valid MagazineModel — the minimum MagazineModelSchema accepts (3 bullets). */
const MODEL_FIXTURE = {
  sections: [{
    lead: 'lead',
    bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }],
  }],
};

/** The two replicas as `Side`s. `companionTransfer(winner, loser, …)` takes them in either role. */
function sides(ctx: Ctx): { local: Side; cloud: Side } {
  return {
    local: { store: ctx.local, p: ctx.localPrincipal, blob: ctx.localBlob },
    cloud: {
      store: new SupabaseMetadataStore(ctx.userClient), p: ctx.cloudPrincipal,
      blob: new SupabaseBlobStore(ctx.userClient, ARTIFACTS_BUCKET),
    },
  };
}

/** Seed ONE side's model envelope. This is `seedEnvelope` — file-local, because
 *  `writeModelEnvelope` through that side's own store IS the seeder (the pattern at
 *  tests/integration/share-route.test.ts:79). `videoId` is explicit: it is the subject. */
async function seedEnvelope(
  side: Side, base: string, videoId: string, over: Partial<ModelEnvelopeWrite> = {},
): Promise<void> {
  await writeModelEnvelope(side.p, base, {
    sourceMd: `${base}.md`, generatedAt: new Date().toISOString(), sourceSections: ['1. Intro'],
    generatorVersion: GENERATOR_VERSION, model: MODEL_FIXTURE,
    sourceMdHash: mdHash(MD), videoId, ...over,
  } as ModelEnvelopeWrite, side.blob);
}

/** Seed a LEGACY envelope — one written BEFORE this slice, with no `videoId` property at all.
 *
 *  ⛔ **This CANNOT go through `writeModelEnvelope`, and round-4 Codex caught it trying to.**
 *  T7 makes `serialize` run `ModelEnvelopeWriteSchema.parse`, where `videoId` is
 *  `z.string().min(1)`. Passing `undefined as unknown as string` type-checks — `seedEnvelope`
 *  casts `as ModelEnvelopeWrite`, so the cast swallows it — and then throws at RUNTIME inside the
 *  parse, before writing anything. Behavior 18j4's test would have failed in its own setup.
 *
 *  The population 18j4 is about is exactly the one the new writer refuses to create, so the
 *  fixture must write the bytes DIRECTLY. Note `videoId` is OMITTED, not set to `undefined`:
 *  `JSON.stringify` drops an explicit `undefined` too, but omitting it says what is meant. */
async function seedLegacyEnvelope(
  side: Side, base: string, over: Record<string, unknown> = {},
): Promise<void> {
  const legacy = {
    sourceMd: `${base}.md`, generatedAt: new Date().toISOString(), sourceSections: ['1. Intro'],
    generatorVersion: GENERATOR_VERSION, model: MODEL_FIXTURE, sourceMdHash: mdHash(MD), ...over,
  };
  await side.blob.put(
    side.p, MODEL_KEY(base),
    Buffer.from(`${JSON.stringify(legacy, null, 2)}\n`, 'utf-8'), 'application/json',
  );
}

/** A two-sided video with the SAME MD body on both replicas, base = ctx.videoId. */
async function twoSided(): Promise<{ ctx: Ctx; local: Side; cloud: Side; base: string }> {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await seedLocalVideoFull(ctx, { mdBody: MD });
  await seedCloudVideo(ctx, { mdBody: MD });
  const { local, cloud } = sides(ctx);
  return { ctx, local, cloud, base: ctx.videoId };
}

// ---------------------------------------------------------------------------
// 18j — the refusal covers BOTH destructive arms. Two fixtures, because
// `decideCompanion` reaches them by different routes:
//   sender envelope MATCHES the winner hash  -> 'ship'                (overwrite)
//   sender envelope does NOT match, receiver hash present+different -> 'deleteReceiverModel'
// A guard inside the ship arm only would leave the second one reachable (round-1 H3).
// ---------------------------------------------------------------------------

it('behavior 18j — SHIP arm: REFUSES when the envelope videoId differs from the row, and RETURNS an error', async () => {
  const { ctx, local, cloud, base } = await twoSided();
  await seedEnvelope(local, base, ctx.videoId);                                   // sender: ours
  await seedEnvelope(cloud, base, 'OTHER', { sourceMdHash: 'stale' });            // receiver: NOT ours
  const lv = (await localVideoRecord(ctx))!;

  const res = await companionTransfer(local, cloud, mdHash(MD), lv);

  expect(res.shareNeedsOwnerServe).toBe(true);
  expect(res.error).toMatch(/envelope videoId/);
  // The paid model survives, and it is still the OTHER video's.
  const after = await readModelEnvelope(cloud.p, base, cloud.blob);
  expect(after!.videoId).toBe('OTHER');
  expect(after!.sourceMdHash).toBe('stale');
});

it('behavior 18j — DELETE arm: the same refusal, on the path that would have destroyed the model', async () => {
  const { ctx, local, cloud, base } = await twoSided();
  // Sender does NOT match the winner hash -> nothing shippable; the receiver's present-but-different
  // sourceMdHash is what decideCompanion (companion.ts:151-153) calls `provablyStale` and DELETES.
  await seedEnvelope(local, base, ctx.videoId, { sourceMdHash: 'sender-stale' });
  await seedEnvelope(cloud, base, 'OTHER', { sourceMdHash: 'receiver-stale' });
  const lv = (await localVideoRecord(ctx))!;

  const res = await companionTransfer(local, cloud, mdHash(MD), lv);

  expect(res.error).toMatch(/envelope videoId/);
  expect((await readModelEnvelope(cloud.p, base, cloud.blob))!.videoId).toBe('OTHER');
});

it('behavior 18j — never THROWS, so the caller still advances the baseline', async () => {
  const { ctx, local, cloud, base } = await twoSided();
  await seedEnvelope(local, base, ctx.videoId);
  await seedEnvelope(cloud, base, 'OTHER', { sourceMdHash: 'stale' });
  const lv = (await localVideoRecord(ctx))!;

  await expect(companionTransfer(local, cloud, mdHash(MD), lv)).resolves.toBeDefined();
});

it('behavior 18j2 — SHIPS when the receiver read is `unknown` (cloud loser) or `none` (local loser)', async () => {
  // No receiver envelope at all. On the Supabase loser that read is `unknown` (provesAbsence is
  // false, supabase-blob-store.ts:10); on a local loser it is `none`. Assert the SHIP by reading back.
  const a = await twoSided();
  await seedEnvelope(a.local, a.base, a.ctx.videoId);
  await companionTransfer(a.local, a.cloud, mdHash(MD), (await localVideoRecord(a.ctx))!);
  expect((await readModelEnvelope(a.cloud.p, a.base, a.cloud.blob))!.videoId).toBe(a.ctx.videoId);

  const b = await twoSided();
  await seedEnvelope(b.cloud, b.base, b.ctx.videoId);
  await companionTransfer(b.cloud, b.local, mdHash(MD), (await cloudVideoRecord(b.ctx))!);
  expect((await readModelEnvelope(b.local.p, b.base, b.local.blob))!.videoId).toBe(b.ctx.videoId);
});

it('behavior 18j4 — a LEGACY envelope with no videoId proceeds, and sourceMd is NOT consulted', async () => {
  const { ctx, local, cloud, base } = await twoSided();
  await seedEnvelope(local, base, ctx.videoId);
  await seedLegacyEnvelope(cloud, base, { sourceMd: 'wrong.md', sourceMdHash: 'stale' });
  const lv = (await localVideoRecord(ctx))!;

  const res = await companionTransfer(local, cloud, mdHash(MD), lv);

  expect(res.error).toBeUndefined();
  expect((await readModelEnvelope(cloud.p, base, cloud.blob))!.videoId).toBe(ctx.videoId);
});

it('behavior 18j6 — the ship STAMPS the receiver videoId, from the ROW not the sender', async () => {
  const { ctx, local, cloud, base } = await twoSided();
  await seedEnvelope(local, base, 'SENDER-WROTE-THIS');
  const lv = (await localVideoRecord(ctx))!;

  await companionTransfer(local, cloud, mdHash(MD), lv);

  expect((await readModelEnvelope(cloud.p, base, cloud.blob))!.videoId).toBe(ctx.videoId);
});

it('behavior 18j3 + 18j7 — after a cloud base relocation the ship still succeeds, and the COPIED envelope keeps its videoId', async () => {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  // local carries serial 3 with its own base; cloud carries serial 7 -> reconcileCloudBase relocates.
  await seedLocalVideoFull(ctx, { position: 3, summaryMd: '003_alpha.md', mdBody: MD });
  await seedCloudVideo(ctx, { position: 7, summaryMd: '007_alpha.md', mdBody: MD });
  const { local, cloud } = sides(ctx);
  await seedEnvelope(cloud, '007_alpha', ctx.videoId);

  const rec = await reconcileCloudBase({
    cloud: { store: cloud.store, p: cloud.p, blob: cloud.blob },
    cloudIndex: (await new SupabaseMetadataStore(ctx.userClient).readIndex(ctx.cloudPrincipal)).videos,
    localVideo: (await localVideoRecord(ctx))!,
    cloudVideo: (await cloudVideoRecord(ctx))!,
    inFlightJob: async () => ({ ok: true, inFlight: false }),
  });
  expect(rec).toMatchObject({ ok: true, action: 'relocated', from: '007_alpha', to: '003_alpha' });

  const copied = await readModelEnvelope(cloud.p, '003_alpha', cloud.blob);
  expect(copied!.videoId).toBe(ctx.videoId);   // preserved by the COPY, not by the write schema

  const res = await companionTransfer(local, cloud, mdHash(MD), (await localVideoRecord(ctx))!);
  expect(res.error).toBeUndefined();
});
```

- [ ] **Step 2: Run to verify they fail** — INTEGRATION:
      `npm run test:integration -- tests/integration/cloud-sync/companion-videoid.int.test.ts`.
      **Expected, MEASURED: exactly 3 failures — the two 18j arms and 18j6 — and 4 passes.** If any
      other case is red, the fixture is wrong, not the production code.

- [ ] **Step 3: Implement the refusal ABOVE `decideCompanion`**

⛔ **Round-1 H3 → round-2 B2. `decision.receiverEnvelope` does not exist**, and this is the second
invented identifier in two rounds (v1 invented `rawList`). `lib/cloud-sync/companion.ts:25-28` is the
COMPLETE return type:

```ts
export type CompanionAction =
  | { kind: 'ship'; envelope: ModelEnvelope }
  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
```

`receiverEnvelope` has **0** occurrences in the repo. The receiver is an **input**
(`decideCompanion(args: { winnerMdHash; senderModel; receiverModel })`, `companion.ts:98-102`), and
`companionTransfer` already holds the honest read of it. `sync-run.ts:451-455` is verbatim today:

```ts
  const [senderModel, receiverModel] = await Promise.all([
    readModelSide(winner, base), readModelSide(loser, base),
  ]);
  const decision = decideCompanion({ winnerMdHash, senderModel, receiverModel });
  if (decision.kind === 'ship') {
```

`receiverModel` is a `ModelRead` (`companion.ts:12-15`) — the **tagged union**
`{kind:'envelope';envelope}` / `{kind:'none'}` / `{kind:'unknown'}`, which is exactly the tri-state
this guard needs. **The change:** insert the refusal between `:453` and `:454` — above
`decideCompanion`, so it covers `ship`, `noop` **and** `deleteReceiverModel`:

```ts
  // §3.6.4. The refusal RETURNS — companionTransfer's docstring (:441-443) is explicit that every
  // companion write is best-effort and NEVER throws (M-R6-1): a throw is caught per-video at :812
  // and SKIPS writeVideoBaseline, so the run errors forever.
  //
  // ⚠ It sits ABOVE decideCompanion, not inside the ship arm. Placing it in the ship arm leaves
  // `loser.blob.delete(loser.p, MODEL_KEY(base))` at :475 reachable — and that delete is exactly
  // what fires for a receiver whose envelope has a present, different sourceMdHash
  // (companion.ts:151-153, `provablyStale`), which is the SAME envelope a videoId mismatch
  // describes. So the ship-arm-only placement destroys the paid model the credential exists to
  // protect. (Round-1 H3; v2 marked it FIXED and left the snippet in the ship arm.)
  //
  // It reads `receiverModel`, the tri-state already read honestly at :451-453 via readModelSide —
  // NOT a fresh readModelEnvelope, which collapses absent / unreadable / schema-invalid into one
  // null (supabase-blob-store.ts:29-35 documents exactly that) and would invent an ownership claim
  // out of a failed read.
  //
  //   kind 'envelope' + videoId present + different  -> REFUSE (this guard)
  //   kind 'envelope' + videoId absent (legacy)      -> proceed. Do NOT fall back to sourceMd:
  //     round-13 H1 measured it stale by construction, so the fallback reintroduces the defect for
  //     exactly the envelopes least able to survive it.
  //   kind 'none'                                    -> proceed; nothing claims this address.
  //   kind 'unknown'                                 -> proceed, and this is DELIBERATE: an
  //     unreadable receiver is not an ownership claim. It is also why decideCompanion already
  //     refuses to DELETE on 'unknown' (companion.ts:131-153) — the destructive direction is
  //     already fail-safe there, so this guard does not need to duplicate it.
  if (receiverModel.kind === 'envelope'
      && receiverModel.envelope.videoId
      && receiverModel.envelope.videoId !== winnerVideo.id) {
    return {
      shareNeedsOwnerServe: true,
      error: `companion refused: envelope videoId ${receiverModel.envelope.videoId}, `
           + `row ${winnerVideo.id}`,
    };
  }
```

And **one more line**, in the ship arm at `:464`, which is verbatim today
`await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);` — T7 made `videoId`
required at the write schema, and `decision.envelope` is the SENDER's:

```ts
      await writeModelEnvelope(loser.p, base, { ...decision.envelope, videoId: winnerVideo.id }, loser.blob);
```

*(Behavior 18j6: the stamp comes from the ROW, so a sender envelope carrying another video's id —
or none at all, which is what `generate.ts` writes today — cannot propagate a wrong claim.)*

- [ ] **Step 4: behaviors 18j3 and 18j7 — the LAST `it(...)` in the Step-1 file**

It is in the file above rather than a second snippet, because it needs the same `sides()` /
`seedEnvelope()` fixture. ⚙ **It PASSES both before and after Step 3** — deliberately: it asserts
that a cloud base RELOCATION preserves the envelope's `videoId` through the byte copy (18j7) and
that the ship still succeeds afterwards (18j3), so it is a preservation assertion, not a red-first
one. `reconcileCloudBase`'s five arguments are `{ cloud, cloudIndex, localVideo, cloudVideo,
inFlightJob }` (`reconcile-serial.ts:166-174`); `InFlightJobProbe` returns `{ok:true,inFlight}` or
`{ok:false,cause}` (`:61-64`).

- [ ] **Step 5: Run and commit**

```bash
npx tsc --noEmit && npm run test:integration -- tests/integration/cloud-sync/
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/cloud-sync/sync-run.ts tests/integration/cloud-sync/
git commit -m "feat(#36): videoId is the model-ownership credential, gating ship AND delete (behaviors 18j-18j7)"
```

---

## Task 9: `videoDataPayload` — the metadata seam refuses an unservable advertisement

**Spec:** §3.5.1, §3.5.1b **row 1**. **Behaviors:** 26c, 26c2, 26c3, 26c4.

**⚠ T10, T11 and T12 all depend on this task. Land it first.** Round-18 B1 was exactly a T12/T9 interaction: a placement that let a write through while the seam still refused it.

**The rename is load-bearing, not cosmetic.** `stripComputed` reads as optional hygiene, so a future writer skipping it looks harmless. `videoDataPayload` reads as *the* way to build the payload.

**Files:**
- Modify: `lib/storage/supabase/supabase-metadata-store.ts` (`:19` the function; `:119`, `:143`, `:160` the three call sites)
- Test: `tests/integration/metadata-seam.test.ts` — **INTEGRATION** (new)

**Interfaces:**
- Consumes: `isServableSummaryKey` from T4.
- Produces: no new exports — `videoDataPayload` is **module-private**, which is the entire point. It is the one function every write to `videos.data` through this adapter passes through, so a fourth adapter method added later is covered **by construction**.

- [ ] **Step 1: Write the failing tests** — INTEGRATION

`callWith` is file-local — one consumer, and it needs this file's own `ctx`:

```ts
/** Drive one of the three data-writing adapter methods with a patch. The three take different
 *  argument shapes (upsertVideo takes a whole Video; updateVideoFields takes (p, videoId, fields);
 *  bulkUpdateVideoFields takes (p, [{videoId, fields}])), which is why this exists — behaviors 26c
 *  and 26c2 assert that ALL THREE refuse, and that is only meaningful if each is really called. */
async function callWith(
  method: 'upsertVideo' | 'updateVideoFields' | 'bulkUpdateVideoFields',
  fields: Record<string, unknown>,
): Promise<void> {
  const store = new SupabaseMetadataStore(ctx.userClient);
  const p = ctx.cloudPrincipal;
  if (method === 'upsertVideo') return store.upsertVideo(p, { id: ctx.videoId, ...fields } as Video);
  if (method === 'updateVideoFields') return store.updateVideoFields(p, ctx.videoId, fields as Partial<Video>);
  return store.bulkUpdateVideoFields(p, [{ videoId: ctx.videoId, fields: fields as Partial<Video> }]);
}
```

```ts
it.each(['upsertVideo', 'updateVideoFields', 'bulkUpdateVideoFields'] as const)(
  'behaviors 26c + 26c2 — %s REFUSES a patch advertising an unservable key', async (method) => {
    await expect(callWith(method, {
      summaryMd: 'nested/evil.md',
      artifacts: { summaryMd: { key: 'nested/evil.md', status: 'promoted' } },
    })).rejects.toThrow(/not a servable summary key/);
  });

it('behavior 26c — a Korean key is ACCEPTED', async () => {
  await expect(callWith('updateVideoFields', {
    summaryMd: '003_한국어.md',
    artifacts: { summaryMd: { key: '003_한국어.md', status: 'promoted' } },
  })).resolves.toBeUndefined();
});

it('behavior 26c3 — a Class-A transfer to the CLOUD is refused; to LOCAL it is NOT', async () => {
  // The LOCAL store has no seam guard, correctly, per §3.4 and decision ①. A test written only
  // against copyToLocal would pass VACUOUSLY, which is why this row names BOTH directions.
  //
  // Driven through runSync, not transferClassA, because the DIRECTION is what varies and runSync
  // is where direction is decided. ⚠ runSync NEVER REJECTS: every per-video throw is caught at
  // sync-run.ts:812-814 and pushed onto report.errors. Asserting `.rejects` here is unsatisfiable
  // (round-2 H4), and the "fix" an implementer would reach for — letting the throw escape the
  // per-video catch — aborts the whole playlist, which is the behavior :812 exists to prevent.
  const cloudward = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });   // local wins
  expect(cloudward.errors).toContainEqual(expect.objectContaining({
    videoId: ctx.videoId, message: expect.stringMatching(/not a servable summary key/),
  }));

  // …re-seed so the CLOUD is the winner (newer mdGeneratedAt), then:
  const localward = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  expect(localward.errors).not.toContainEqual(expect.objectContaining({
    message: expect.stringMatching(/not a servable summary key/),
  }));
  expect(await localBlobBytes(ctx, 'nested/evil.md')).not.toBeNull();   // the vault took it
});

it('behavior 26c4 — after the refusal the cloud row still points at its OLD key', async () => {
  const before = await cloudVideoRecord(ctx);
  await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  expect((await cloudVideoRecord(ctx))!.summaryMd).toBe(before!.summaryMd);
  // The accepted residual is an ORPHAN blob at the unservable key, not a lost artifact.
});
```

⚠ **A deliberate detail in 26c3's second arm:** it asserts the absence of a *message*, not that
`report.errors` is empty. T12 adds a per-run report entry for any cloud row advertising an
unservable key, and in this fixture the cloud row is exactly that. Written as
`expect(errors).toEqual([])` this test passes when T9 lands and breaks when T12 lands — a
scope-scoped assertion is what makes it survive both.

- [ ] **Step 2: Run to verify they fail** — INTEGRATION:
      `npm run test:integration -- tests/integration/metadata-seam.test.ts`.
      Expected: FAIL — every patch is accepted today.

- [ ] **Step 3: Rename and add the refusal**

`lib/storage/supabase/supabase-metadata-store.ts:19-22` is verbatim today:

```ts
function stripComputed<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
  return rest;
}
```

**The change:** rename it, keep its body as the tail, and add the refusal ahead of it.

```ts
/**
 * The ONE function that builds what lands in `videos.data` through this adapter. All three
 * data-writing methods pass their payload through it and nothing else calls it, so the
 * entrance count stops mattering — a fourth method added later is covered by construction.
 *
 * Renamed from `stripComputed` deliberately (round-15 M1): a name that says "optional
 * hygiene" invites a future writer to skip it, and skipping this one is a money-path defect.
 */
function videoDataPayload<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
  const patch = v as {
    summaryMd?: unknown;
    artifacts?: { summaryMd?: { key?: unknown; status?: unknown } };
  };
  // ⚠ DECIDED at round 1 (Codex M1). The spec's rule is "`summaryMd` OR
  // `artifacts.summaryMd.status = 'promoted'`". The v1 plan guarded `artifacts.summaryMd.key`
  // REGARDLESS of status, which is STRICTER than specified and would refuse a legitimate
  // non-advertising repair state. Guard the top-level key always; guard the artifact key only when
  // it is being promoted. **A guard stricter than its spec is still a guard nobody agreed to.**
  const advertised = [
    patch.summaryMd,
    patch.artifacts?.summaryMd?.status === 'promoted' ? patch.artifacts?.summaryMd?.key : undefined,
  ].filter((k): k is string => typeof k === 'string');
  for (const key of advertised) {
    if (!isServableSummaryKey(key)) {
      throw new Error(`not a servable summary key: ${JSON.stringify(key)} — refused at the metadata seam`);
    }
  }
  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
  return rest;
}
```

Then replace the three call sites — `:119` `.update({ data: stripComputed(video) })`, `:143`
`p_fields: stripComputed(fields)`, `:160` `fields: stripComputed(x.fields)` — with
`videoDataPayload`. `stripComputed` must have **0** occurrences afterwards; that is the check.

- [ ] **Step 4: Run and verify, then re-run the producer check**

```bash
npx tsc --noEmit
npm run test:integration -- tests/integration/metadata-seam.test.ts
npm test && npm run test:integration
python3 scripts/check-producer-enumeration.py
```
Expected: tests PASS, producer check exit 0.

- [ ] **Step 5: Commit**

```bash
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/storage/supabase/supabase-metadata-store.ts tests/integration/metadata-seam.test.ts
git commit -m "feat(#36): videoDataPayload is the metadata seam and refuses an unservable advertisement (behaviors 26c-26c4)"
```

---

## Task 10: The mint guard — refuse before the money moves

**Spec:** §3.5.1 placement 1, §3.5.1b **row 2**. **Behaviors:** 25.

**Files:**
- Modify: `lib/job-queue/summary-handler.ts`
- Test: `tests/integration/summary-handler-guard.test.ts` — **INTEGRATION** (new)

**Interfaces:** Consumes `isServableSummaryKey` (T4). Produces nothing.

- [ ] **Step 1: Write the failing test** — INTEGRATION

⛔ **Round-3, both halves, Blocking — v3's test was KNOWINGLY IMPOSSIBLE.** It asserted that
`title: 'x'.repeat(400)` rejects, and the same step then said no `slugify` output can reach that
branch. A fake test plus a prose escape hatch, in the no-money-before-refusal path.

**DECIDED this round: option (b) — an explicit, honest test-only seam. The escape hatch is deleted,
and so is the choice.** The reasoning, so it is reviewable rather than re-opened:

- **Behavior 25 is a claim about PLACEMENT, not about the predicate's verdict.** The verdict is T4's
  subject and behavior 27 proves, over the whole codepoint space, that no title reaches the branch.
  A unit test over `` isServableSummaryKey(`${padSerial(n)}_${slugify(t)}.md`) `` — option (a) —
  would re-assert behavior 27 and say nothing about whether the refusal precedes the Gemini call,
  which is the only part of this task that is about money.
- **The seam is a `jest.mock` factory over the predicate module that `jest.requireActual`s the real
  implementation and overrides it for ONE sentinel slug.** It needs no production change, it is
  visible in the test file, and the repo already mocks at module level in exactly this file's
  ancestor (`tests/integration/summary-handler.test.ts:24-25` mocks `@/lib/gemini` and
  `@/lib/transcript-source`).
- **A control case proves the seam is narrow** — a normal title still reaches `generateSummary`. A
  blanket mock would make the first assertion pass for the wrong reason.

⛔ **And v3's money assertion was VACUOUS — this is a second, separate defect, found by executing
it.** `expect(await ledgerTotal()).toBe(before)` cannot fail: `spend_ledger` is moved by
`enqueue_job` (`0011_cost_guardrails.sql:113`) and by the serve path
(`0012_serve_model_charge.sql:86`, `0014_serve_owner_budget.sql:82`) — **never by this handler**, so
a before/after delta around a handler call is invariant with or without the guard. It is a green
check over the wrong subject, exactly the class this plan exists to stop. The paid call this
placement actually prevents is the provider call, so that is what the test asserts.

⛔ **Round-2 H6 still stands: `runSummaryJob` does not exist.** The only exports of
`lib/job-queue/summary-handler.ts` are `makeSummaryHandler(serviceClient: SupabaseClient): JobHandler`
(`:50`) and `MAX_DURATION_SECONDS` (`:27`), so the driver is: mock the modules, then call the
handler. `seedPlaylist` / `mockCtx` / `makePayload` / `makeJob` are copied from
`tests/integration/summary-handler.test.ts:37-95`, where they are file-local, so they are file-local
here too.

⚙ **WRITTEN AND RUN against the live local stack, both ways: RED 1 failed / 1 passed (the guard does
not exist, so the handler completes and `err` is `null`); GREEN 2 passed / 2 with Step 3 applied.**

```ts
// tests/integration/summary-handler-guard.test.ts
//
// §3.5.1 placement 1 / §3.5.1b row 2 — behavior 25: the mint refuses an unservable summary key
// BEFORE the transcript and Gemini calls, so no paid call is made.
//
// ⚠ WHY THE PREDICATE IS MOCKED, AND WHAT THAT DOES NOT FAKE.
// After T3 and T4 **no `slugify` output can reach this branch** — behavior 27 walks the whole
// codepoint space and proves it, and `padSerial(n) + '_' + <=60 chars + '.md'` is far inside the
// 131-code-point bound. The guard is a BACKSTOP: it exists for a future producer change or a
// hand-written base. What behavior 25 asserts is therefore not the predicate's verdict (that is
// T4's subject) but the guard's PLACEMENT — that the refusal happens above the paid calls.
// The seam below is the honest way to observe that: the real predicate is used for every key
// except one sentinel slug, so a test that claimed to drive the guard and could not is replaced
// by one that drives it and says exactly how. The control case at the bottom proves the seam is
// narrow — a normal title still reaches Gemini.
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import type { LeasedJob } from '@/lib/storage/job-queue';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';
import { NonRetryableError } from '@/lib/job-queue/errors';
import type { HandlerCtx } from '@/lib/job-queue/handler-context';
import type { IngestionPayload } from '@/lib/job-queue/ingestion-payload';

jest.mock('@/lib/gemini');
jest.mock('@/lib/transcript-source');
// The seam. `jest.requireActual` keeps the REAL predicate for every other key.
jest.mock('@/lib/html-doc/assert-cloud-summary-md-key', () => {
  const real = jest.requireActual('@/lib/html-doc/assert-cloud-summary-md-key');
  return {
    ...real,
    isServableSummaryKey: (key: string) =>
      (key.includes('unservable-by-fiat') ? false : real.isServableSummaryKey(key)),
  };
});

import { generateSummary, extractQuickView } from '@/lib/gemini';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
// AFTER the jest.mock calls, so the handler's own imports resolve to the mocked modules.
import { makeSummaryHandler } from '@/lib/job-queue/summary-handler';

jest.setTimeout(30_000);

const admin = () => adminClient();

// The four file-local helpers copied from tests/integration/summary-handler.test.ts:37-95.
async function seedPlaylist(client: any, ownerId: string): Promise<{ playlistId: string }> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return { playlistId: data.id as string };
}

const mockCtx: HandlerCtx = {
  isCancelled: async () => false,
  signal: new AbortController().signal,
  setPhase: async () => {},
  billing: { metered: false },
};

function makePayload(over: Partial<IngestionPayload> = {}): IngestionPayload {
  return {
    youtubeUrl: 'https://youtu.be/abc123', title: 'My Test Video', channel: 'Test Channel',
    durationSeconds: 120, playlistIndex: 1,
    videoPublishedAt: '2024-01-01T00:00:00.000Z', addedToPlaylistAt: '2024-01-02T00:00:00.000Z',
    ...over,
  };
}

function makeJob(fields: { ownerId: string; playlistId: string; videoId: string; payload: unknown }): LeasedJob {
  return {
    id: randomUUID(), sectionId: -1, kind: 'summary',
    version: docVersionKey(CURRENT_DOC_VERSION), attempts: 1, leaseToken: randomUUID(), ...fields,
  };
}

beforeEach(() => {
  (resolveTranscriptSegments as jest.Mock).mockReset()
    .mockResolvedValue({ segments: [{ text: 'hello world', offset: 0, duration: 5 }], source: 'captions' });
  (generateSummary as jest.Mock).mockReset().mockResolvedValue({
    summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
    overallScore: 4, videoType: 'Analysis', audience: 'Intermediate', tags: ['x'],
    tldr: 'This video explains alpha.', takeaways: ['Do alpha'],
  });
  (extractQuickView as jest.Mock).mockReset().mockResolvedValue({ tldr: 'f', takeaways: ['f'] });
});

it('behavior 25 — the mint refuses an unservable key BEFORE any paid call, non-retryably', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();

  const handler = makeSummaryHandler(admin());
  const err = await handler(
    makeJob({ ownerId: userId, playlistId, videoId, payload: makePayload({ title: 'unservable by fiat' }) }),
    mockCtx,
  ).then(() => null, (e) => e);

  expect(err).toBeInstanceOf(NonRetryableError);       // never burn max_attempts on a name
  expect(err.message).toMatch(/servable/);
  // THE MONEY ASSERTION. `spend_ledger` is moved by enqueue_job (0011) and by the serve path
  // (0012/0014) — never by this handler — so a before/after ledger delta here is invariant with
  // or without the guard and would be a green check over the wrong subject. The paid call this
  // placement actually prevents is the provider call itself.
  expect(resolveTranscriptSegments).not.toHaveBeenCalled();
  expect(generateSummary).not.toHaveBeenCalled();

  // The accepted cost, asserted rather than assumed (§3.5): a consumed serial and a BARE row —
  // no summary is ever advertised.
  const { data } = await admin().from('videos').select('data')
    .eq('playlist_id', playlistId).eq('video_id', videoId).single();
  expect((data!.data as { summaryMd?: string }).summaryMd ?? null).toBeNull();
});

it('control — the seam is NARROW: a normal title still reaches the paid call', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);

  await makeSummaryHandler(admin())(
    makeJob({ ownerId: userId, playlistId, videoId: randomUUID(), payload: makePayload() }),
    mockCtx,
  );

  expect(generateSummary).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run to verify it fails** — INTEGRATION:
      `npm run test:integration -- tests/integration/summary-handler-guard.test.ts`.
      **Expected, MEASURED: 1 failed / 1 passed** — `expect(err).toBeInstanceOf(NonRetryableError)`
      receives `null`, because with no guard the handler runs to completion. The control case
      passes from the start; that is what it is for.

- [ ] **Step 3: Implement**

`lib/job-queue/summary-handler.ts:95-98` is verbatim today:

```ts
    const serial = await reserveVideoSlot(serviceClient, job.ownerId, job.playlistId, job.videoId);
    const baseName = `${padSerial(serial)}_${slugify(payload.title)}`;

    await ctx.setPhase('transcribing');
```

**The change:** insert between `:96` and `:98`.

```ts
    // AFTER reserveVideoSlot and BEFORE the transcript/Gemini work: a refusal here costs NO MONEY,
    // which is why this placement stays outside the seam. The cost is a consumed serial and a
    // dead-letter retry — accepted, and stated in §3.5.
    if (!isServableSummaryKey(`${baseName}.md`)) {
      throw new NonRetryableError(
        `refusing to mint an unservable summary key: ${JSON.stringify(`${baseName}.md`)}. `
        + `Rename the video title or file a bug — no Gemini call was made.`,
      );
    }
```

`NonRetryableError` (`lib/job-queue/errors`) is already imported at `:4` and is the right class: the
name will not become servable on a retry, so burning `max_attempts` on it holds a worker slot for
nothing. *(v2 threw a bare `Error`, which the runner classifies as retryable.)*

- [ ] **Step 4: Run and verify** — INTEGRATION:
      `npx tsc --noEmit && npm run test:integration -- tests/integration/summary-handler-guard.test.ts`.
      **Expected, MEASURED: 2 passed / 2.** The guard is a **backstop**: behavior 27 is what proves
      no real title reaches it, and this test is what proves that when something does, the refusal
      lands above the paid call.

- [ ] **Step 5: Commit**

```bash
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/job-queue/summary-handler.ts tests/integration/summary-handler-guard.test.ts
git commit -m "feat(#36): the mint refuses an unservable key before the paid call (behavior 25)"
```

---

## Task 11: The adopt guard — in the CALLER, above the sender read

**Spec:** §3.5.1 placement 3, §3.5.1b **row 4**. **Behaviors:** 26, 26b, 26e, 26f.

⚠ **`copyAdditiveVideo` cannot tell which side it is on.** Its signature is
`(to: MetadataStore, toP: Principal, toBlob: BlobStore, playlistMeta, video, mdBody)`
(`sync-run.ts:221-225`) — `MetadataStore` is an interface both stores satisfy. A guard inside it
applies in **both** directions or sniffs the concrete type, and applying it on `copyToLocal` strands
a paid cloud artifact (round-16 B1). **The guard goes in the caller**, where `presentIsLocal` exists.

**Files:**
- Modify: `lib/cloud-sync/sync-run.ts` at `:624-627`
- Test: `tests/integration/cloud-sync/adopt-guard.int.test.ts` — **INTEGRATION** (new)

**Interfaces:** Consumes `isServableSummaryKey` (T4) and T0's `syncDeps({ localBlob })`. Produces nothing.

- [ ] **Step 1: Write the failing tests** — INTEGRATION

⛔ **Round-2 H4: `runSync` cannot reject, and `runSync({local, cloud})` is not its signature.** It is
`runSync(deps: SyncDeps, opts: { playlistKey?: string } = {})` (`:547-549`), and every per-video
throw is caught at `:812-814`. All four tests below assert `report.errors`, and 26b re-runs.

⛔ **Round-4 coordinator, THREE defects in the block that follows, none of which any of the four
review rounds reported — T11 was never in a round's scope.** They are fixed below; they are recorded
because the shape matters more than the fix:

1. **The file had no header anywhere in the plan.** It is marked `(new)` above, and neither T11 nor
   T12 showed a single `import`. Round 3 named four *other* incomplete blocks and v4 fixed exactly
   those four — the sample, not the population. Four new integration files were affected; this is one.
2. **`ctx` was used free.** The repo idiom is NOT a shared `beforeEach` — `sync-run.int.test.ts:25,48`
   and `e2e.int.test.ts` both open **each** test with `const ctx = await makeOwnerContext();`, because
   every call mints a NEW user and a shared one would leak state between tests.
3. **`RecordingBlobStore` was invented** — used once at 26f and defined nowhere. That is the fourth
   invented identifier in this plan's history (`rawList` in v1, `receiverEnvelope` in v2). It is
   written out below, modelled on `FailPromoteBlobStore` (`helpers/cloud.ts:168`), which is the
   nearest real decorator in the tree.

```ts
// tests/integration/cloud-sync/adopt-guard.int.test.ts
//
// Backlog #36, plan T11 + T12 — the adopt guard (T11) and reconcileCloudBase's four-cell table
// (T12, appended in that task). Runs against real local FS <-> local Supabase under an
// authenticated USER session, never service-role.
//
// Money invariant: every behavior here REFUSES before a paid artifact is read or copied, so no
// test in this file may move the ledger.
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import {
  makeOwnerContext, prepareSyncCtx, seedCloudVideo, seedLocalVideoFull,
  cloudVideoRecord, localBlobBytes,
} from '@/tests/integration/helpers/cloud';
import { runSync } from '@/lib/cloud-sync/sync-run';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { copyBlob, type BlobStore, type CopyResult, type StagedRef } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

jest.setTimeout(30_000);

afterAll(async () => {
  const home = os.homedir();
  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
});

/** Records every `get` key and otherwise delegates. 26f asserts a NEGATIVE — that the sender blob
 *  was never read — so the instrument must distinguish "not called" from "called, returned nothing";
 *  a jest mock returning `null` cannot. Full-surface delegation, and `copy` routes through `this`,
 *  both copied from `FailPromoteBlobStore` (`tests/integration/helpers/cloud.ts:168-185`) so the
 *  decorator cannot silently narrow the store the code under test sees. */
class RecordingBlobStore implements BlobStore {
  constructor(private inner: BlobStore, private onGet: (key: string) => void) {}
  get provesAbsence(): boolean | undefined { return this.inner.provesAbsence; }
  put(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.put(p, key, bytes, ct); }
  get(p: Principal, key: string) { this.onGet(key); return this.inner.get(p, key); }
  tryGet(p: Principal, key: string) { this.onGet(key); return this.inner.tryGet(p, key); }
  exists(p: Principal, key: string) { return this.inner.exists(p, key); }
  delete(p: Principal, key: string) { return this.inner.delete(p, key); }
  putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
  promote(ref: StagedRef): Promise<void> { return this.inner.promote(ref); }
  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
  copy(p: Principal, from: string, to: string): Promise<CopyResult> { return copyBlob(this, p, from, to); }
}

const EVIL = 'nested/evil.md';

it('behavior 26 — local->cloud adopt of an unservable key REFUSES, creates no receiver row, and names the repair', async () => {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await seedLocalVideoFull(ctx, { summaryMd: EVIL, mdBody: '# body\n' });   // local-only video
  const report = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  expect(report.errors).toContainEqual(expect.objectContaining({
    videoId: ctx.videoId, message: expect.stringMatching(/RENAME THE FILE/),
  }));
  expect(report.created).toBe(0);
  expect(await cloudVideoRecord(ctx)).toBeNull();     // no bare row
});

it('behavior 26e — cloud->local hydration of an unservable key SUCCEEDS', async () => {
  // The vault is NOT guarded (§3.4, decision ①). Without this row the round-16 B1 regression is
  // invisible, because behavior 26 alone passes whichever direction it is written against.
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await seedCloudVideo(ctx, { summaryMd: EVIL, mdBody: '# body\n' });       // cloud-only video
  const report = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  expect(report.errors).toEqual([]);
  expect(await localBlobBytes(ctx, EVIL)).not.toBeNull();
});

it('behavior 26f — the guard runs ABOVE the sender read: no `get` on the sender blob store', async () => {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await seedLocalVideoFull(ctx, { summaryMd: EVIL, mdBody: '# body\n' });
  // A recording decorator, file-local, same shape as FailPromoteBlobStore (helpers/cloud.ts:168).
  // It must distinguish "not called" from "called and returned nothing" — 26f asserts a NEGATIVE.
  const gets: string[] = [];
  const spy = new RecordingBlobStore(localBlobStore, (key) => gets.push(key));
  await runSync(ctx.syncDeps({ localBlob: spy }), { playlistKey: ctx.playlistKey });
  expect(gets).toEqual([]);       // readMdBody at :626 never ran
});

it('behavior 26b — the refusal SURVIVES a second run; it is not routed around', async () => {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await seedLocalVideoFull(ctx, { summaryMd: EVIL, mdBody: '# body\n' });
  const first = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  const second = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  for (const r of [first, second]) {
    expect(r.errors).toContainEqual(expect.objectContaining({
      videoId: ctx.videoId, message: expect.stringMatching(/RENAME THE FILE/),
    }));
  }
  expect(await cloudVideoRecord(ctx)).toBeNull();    // identical, forever
});
```

*(26b is the one that would catch a "fix" that advances the manifest baseline on refusal: with a
baseline written, run 2's `if (base)` branch at `:621` counts the video as REMOVED instead of
refusing it. The refusal throws, so no baseline is written — but that is the property under test,
not an assumption.)*

- [ ] **Step 2: Run to verify they fail** — INTEGRATION:
      `npm run test:integration -- tests/integration/cloud-sync/adopt-guard.int.test.ts`.

- [ ] **Step 3: Implement in the caller**

`sync-run.ts:624-627` is verbatim today:

```ts
            const from: Side = presentIsLocal ? localSide : cloudSide;
            const to: Side = presentIsLocal ? cloudSide : localSide;
            const body = await readMdBody(from.blob, from.p, present);
            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
```

**The change:** insert a guard between `:625` and `:626`. Nothing else in the block moves.

```ts
            // The receiver is the CLOUD only when the present side is local. Guard before the
            // sender read (behavior 26f) and before ensureReceiverSlot's durable insert
            // (round-13 H2, sync-run.ts:214) — refusing here is strictly earlier than either, so
            // no receiver row and no staged blob can exist.
            //
            // `presentIsLocal &&` is the whole of decision ①: cloud->local hydration of the same
            // key must SUCCEED (behavior 26e), because a guard that refuses to write a name into
            // the vault strands a paid cloud artifact (round-16 B1).
            if (presentIsLocal && present.summaryMd && !isServableSummaryKey(present.summaryMd)) {
              throw new Error(
                `cannot sync ${present.id} to the cloud: the vault filename `
                + `${JSON.stringify(present.summaryMd)} is not a servable key. `
                + `RENAME THE FILE in your vault to a single path component, then re-run sync.`,
              );
            }
```

The throw is caught per-video at `:812-814`, surfaces in `report.errors`, and advances **no**
baseline — so the video stays refused on every run until the user renames it (behavior 26b).

- [ ] **Step 4: Run and verify** — INTEGRATION:
      `npx tsc --noEmit && npm run test:integration -- tests/integration/cloud-sync/ && npm test`.

- [ ] **Step 5: Commit**

```bash
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/cloud-sync/sync-run.ts tests/integration/cloud-sync/adopt-guard.int.test.ts
git commit -m "feat(#36): the adopt guard is scoped to the cloud receiver, in the caller (behaviors 26,26b,26e,26f)"
```

---

## Task 12: `reconcileCloudBase` — the four-cell relocate / refuse / skip table

**Spec:** §3.5.1 placement 2, §3.5.1b **row 3**. **Behaviors:** 26d, 26d2, 26d3, 26d4.

⚠ **This task is where rounds 17 and 18 both put a Blocking. Read §3.5.1 placement 2 in full before
starting.** `newBase` has **TWO** producers (a ternary at `reconcile-serial.ts:152-154`), and
`reconcileCloudBase` writes its row **through the seam** (T9) at `:324`. A guard here that merely
*permits* a write the seam then refuses copies every paid blob and fails anyway.

**Files:**
- Modify: `lib/cloud-sync/reconcile-serial.ts` (the union at `:69-81`; a new refusal after `:216`),
  `lib/cloud-sync/sync-run.ts` (one branch inside the existing `if (!rec.ok)`; one row-derived report)
- Test: `tests/lib/cloud-sync/reconcile-serial.test.ts` — **UNIT** (the four cells);
  `tests/integration/cloud-sync/adopt-guard.int.test.ts` — **INTEGRATION** (26d2's two-run assertion)

**Interfaces:**
- Consumes: `isServableSummaryKey` (T4).
- Produces: two new `SerialReconcileResult` variants — `{ ok: false; reason: 'unservable-base'; key: string; origin: 'vault-filename' | 'cloud-key' }` and `{ ok: true; action: 'skipped-unservable' }`.

- [ ] **Step 1: Write the failing tests — one per cell** — UNIT

⛔ **Round-1 L3 / round-2 M7 / round-3 Codex B2 — all four arms were `/* … */` placeholders.**
They are now real, and **they do not need `InMemoryBlobStore` + a jest-mocked `MetadataStore` built
from scratch**: `tests/lib/cloud-sync/reconcile-serial.test.ts` already defines exactly the fixture
this needs — `vid(id, serial, slug, extra)`, `cloudReplica(videos, blobsByKey)` (a real
`LocalFsMetadataStore` over a temp dir + an `InMemoryBlobStore`), `read`, `rowOf` and `noJobs`. The
four cells are APPENDED to that file and reuse them, which is also why they assert observable state
rather than `expect(cloudBlob.copy).not.toHaveBeenCalled()` — the file's existing "refuses … BEFORE
copying anything" case (`:384-400`) already establishes that idiom.

⚙ **WRITTEN AND RUN, both ways: RED 3 failed / 1 passed — and the three failures are the RIGHT ones
(each returned `{ok:true, action:'relocated', …}`, i.e. the fixture reaches the guard's insertion
point and today's code relocates through it); GREEN 4 passed / 4 with Step 3 applied, `tsc` clean.**

```ts
// Appended to tests/lib/cloud-sync/reconcile-serial.test.ts — `store`, `vid`, `cloudReplica`,
// `read`, `rowOf` and `noJobs` are that file's own helpers.
const LONG = 'a'.repeat(124);        // `007_${LONG}.md` is exactly 131 code points — AT the bound
const TOO_LONG = 'a'.repeat(130);    // `007_${TOO_LONG}.md` is 137 — over it
const CLOUD_AT_BOUND = `007_${LONG}.md`;
const CLOUD_OVER_BOUND = `007_${TOO_LONG}.md`;

it('behavior 26d — servable -> UNSERVABLE: REFUSED in memory, nothing copied, old base intact', async () => {
  const cloudVideo = vid('vid00000001', 7, 'ok');
  const cloud = await cloudReplica([cloudVideo], { '007_ok.md': 'PAID MD' });

  const res = await reconcileCloudBase({
    cloud, cloudIndex: (await store.readIndex(cloud.p)).videos, inFlightJob: noJobs,
    localVideo: vid('vid00000001', 3, 'evil', { summaryMd: '003_nested/evil.md' }),
    cloudVideo,
  });

  expect(res).toEqual({
    ok: false, reason: 'unservable-base', key: '003_nested/evil.md', origin: 'vault-filename',
  });
  expect(await read(cloud, '003_nested/evil.md')).toBeNull();      // nothing copied
  expect(await read(cloud, '007_ok.md')).toBe('PAID MD');          // old base intact
  expect((await rowOf(cloud, 'vid00000001')).summaryMd).toBe('007_ok.md');
});

it('behavior 26d3 — arm B still REFUSES when the old base was servable', async () => {
  // The renumbering is what widens it: `007_` -> `1000_` is one code point, and the cloud key sits
  // exactly ON the 131-code-point bound. No vault file, so `origin` must be 'cloud-key'.
  const cloudVideo = vid('vid00000001', 7, LONG);
  const cloud = await cloudReplica([cloudVideo], { [CLOUD_AT_BOUND]: 'PAID MD' });

  const res = await reconcileCloudBase({
    cloud, cloudIndex: (await store.readIndex(cloud.p)).videos, inFlightJob: noJobs,
    localVideo: vid('vid00000001', 1000, 'unused', { summaryMd: null }),
    cloudVideo,
  });

  expect(res).toEqual({
    ok: false, reason: 'unservable-base', key: `1000_${LONG}.md`, origin: 'cloud-key',
  });
  expect(await read(cloud, CLOUD_AT_BOUND)).toBe('PAID MD');
});

it('behavior 26d4 — unservable -> SERVABLE: RELOCATES. A genuine repair', async () => {
  const cloudVideo = vid('vid00000001', 7, TOO_LONG);
  const cloud = await cloudReplica([cloudVideo], { [CLOUD_OVER_BOUND]: 'PAID MD' });

  const res = await reconcileCloudBase({
    cloud, cloudIndex: (await store.readIndex(cloud.p)).videos, inFlightJob: noJobs,
    localVideo: vid('vid00000001', 3, 'ok'),
    cloudVideo,
  });

  expect(res).toMatchObject({ ok: true, action: 'relocated', from: `007_${TOO_LONG}`, to: '003_ok' });
  expect(await read(cloud, '003_ok.md')).toBe('PAID MD');
});

it('behavior 26d2 — unservable -> unservable: SKIPPED, no copy, no seam write', async () => {
  const cloudVideo = vid('vid00000001', 7, TOO_LONG);
  const cloud = await cloudReplica([cloudVideo], { [CLOUD_OVER_BOUND]: 'PAID MD' });

  const res = await reconcileCloudBase({
    cloud, cloudIndex: (await store.readIndex(cloud.p)).videos, inFlightJob: noJobs,
    localVideo: vid('vid00000001', 3, 'unused', { summaryMd: null }),
    cloudVideo,
  });

  expect(res).toEqual({ ok: true, action: 'skipped-unservable' });
  expect(await read(cloud, `003_${TOO_LONG}.md`)).toBeNull();
  expect(await read(cloud, CLOUD_OVER_BOUND)).toBe('PAID MD');
  expect((await rowOf(cloud, 'vid00000001')).summaryMd).toBe(CLOUD_OVER_BOUND);
});
```

**The four cells, and the two things each one has to satisfy** — `describeDivergence` must actually
report divergence (or the function returns `{ok:true,action:'agreed'}` at `:184` before reaching the
guard), and the predicate's verdict on `oldBase`/`newBase` must be the one the row claims. ⚙ **Every
verdict below was MEASURED by running the Step-3 predicate over these exact keys, not reasoned
about:**

| Cell | local serial | local `summaryMd` | cloud `summaryMd` | `oldBase.md` | `newBase.md` | expected |
|---|---|---|---|---|---|---|
| 26d | 3 | `003_nested/evil.md` — refused by the seam, still a valid *local* name | `007_ok.md` | `007_ok.md` **servable** (9 cp) | `003_nested/evil.md` **unservable** (contains `/`) | refuse, origin `vault-filename` |
| 26d3 | **1000** | `null` | `` `007_${'a'.repeat(124)}.md` `` | **servable**, 131 cp — exactly the bound | `` `1000_${'a'.repeat(124)}.md` `` **unservable**, 132 cp | refuse, origin `cloud-key` |
| 26d4 | 3 | `003_ok.md` | `` `007_${'a'.repeat(130)}.md` `` | **unservable**, 137 cp | `003_ok.md` **servable** | relocate |
| 26d2 | 3 | `null` | `` `007_${'a'.repeat(130)}.md` `` | **unservable**, 137 cp | `` `003_${'a'.repeat(130)}.md` `` **unservable**, 137 cp | skip |

*(26d3 was the one v3 called "the fiddliest" and left an escape hatch for. It is constructible and
needs no invented character: `padSerial(1000)` is four digits where `padSerial(7)` is three, so the
renumbering alone pushes a key that sits ON the bound one code point past it. The escape hatch is
deleted.)*

- [ ] **Step 2: Run to verify they fail** — UNIT:
      `npx jest tests/lib/cloud-sync/reconcile-serial.test.ts`. **Expected, MEASURED: 3 of the 4 new
      cases fail and 26d4 passes** — 26d4 asserts a relocation today's code already performs, and it
      is in the set precisely so the guard cannot be written as a blanket refusal. Each of the three
      receives `{ok: true, action: 'relocated', …}`, which is also the proof that the fixture
      REACHES the insertion point rather than returning `agreed` early.

- [ ] **Step 3: Extend the union and implement the table**

`reconcile-serial.ts:69-81` today has **2** `ok` variants and **10** refusal variants (counted).

```ts
export type SerialReconcileResult =
  | { ok: true; action: 'agreed' }
  | { ok: true; action: 'skipped-unservable' }            // NEW — 26d2
  | { ok: true; action: 'relocated'; from: string; to: string; copied: number; cleanupFailures: number }
  | { ok: false; reason: 'unservable-base'; key: string; origin: 'vault-filename' | 'cloud-key' }  // NEW
  | /* …the ten existing refusal variants, unchanged… */;
```

**Insertion point, stated (round-1 M6 / round-2 M3 / Codex H1 — v2 gave none):** immediately after
the `unsupported-artifacts` refusal at `:214-216` and **before** the backlog-#17 in-flight probe at
`:218`. That places it with the other in-memory refusals — which is where `:220-223`'s comment says
they belong, *"after every in-memory refusal above (which cost nothing) and BEFORE the copy phase"* —
so it costs no round-trip and can leave nothing half-moved. `localVideo`, `oldBase` and `newBase` are
all in scope there (`:175`, `:185-186`).

```ts
  // `origin` is derived from the SAME predicate the ternary at :152-154 branches on — TRUTHINESS,
  // not nullishness. `summaryMd: ''` takes arm B in the code, and a nullish test would report
  // 'vault-filename' for a video that has no vault file (round-18 L1).
  const origin = localVideo.summaryMd ? 'vault-filename' : 'cloud-key';
  const oldServable = isServableSummaryKey(`${oldBase}.md`);
  const newServable = isServableSummaryKey(`${newBase}.md`);

  if (!newServable) {
    if (oldServable) {
      // Protect a WORKING advertisement from being relocated into unreachability.
      return { ok: false, reason: 'unservable-base', key: `${newBase}.md`, origin };
    }
    // Both unservable: relocating buys nothing (the old key was already unreachable) and costs
    // everything — the seam at :324 would refuse the row AFTER every paid blob had been copied,
    // and the throw would stop reconcileClassA -> copyToLocal from ever hydrating the artifact.
    // SKIP. Round-18 B1. The divergence is REPORTED from the row, not from here — see sync-run.
    return { ok: true, action: 'skipped-unservable' };
  }
  // unservable -> servable falls through and RELOCATES: a genuine repair, and the seam accepts it.
```

- [ ] **Step 4: Dispose of the ONE existing case that flips — measured, not predicted**

⚙ **MEASURED: with Step 3 applied, the whole unit suite is 1 failed / 2,706 passed of 2,707** — that
run included the four new cells, so of the repo's own **2,703** tests (`scripts/check-test-counts.py`)
exactly **one** fails and 2,702 pass.
The single failure is `reconcile-serial.test.ts` *"moves a bare digDeeperMd belonging to a
directory-qualified summary"* (`:406-425`), which seeds `summaryMd: 'raw/007_alpha.md'` and expects
`{ok: true, action: 'relocated'}`; it now gets `skipped-unservable`.

**That is the guard working, and the row must be updated rather than the guard weakened.** Both
bases in that case contain a `/`, so both are unservable — and after T9 the seam would refuse the
relocated row *after* every paid blob had been copied. Skipping is round-18 B1's whole point. Change
that case's expectation to `{ok: true, action: 'skipped-unservable'}`, assert the sources are still
intact, and note in the commit that the `raw/`-qualified layout the case documents is now reported
by the row-derived error in Step 5(b) instead of silently relocated. **If a SECOND existing case
fails, stop — that is a defect, not a widening.**

- [ ] **Step 5: The two `sync-run.ts` edits**

**(a) The refusal branch goes INSIDE the existing `!rec.ok` block, above the generic throw.**
`sync-run.ts:739-757` is verbatim today:

```ts
        if (!rec.ok) {
          if (rec.reason === 'metadata-unverified' || rec.reason === 'verification-unreadable') {
            await refreshCloudSnapshot();
          }
          if (rec.reason === 'job-in-flight') {
            throw new Error(
              `base reconciliation deferred for ${id}: a summary/dig job is still in flight for this ` +
              `video, and relocating now would be overwritten by its persist. Re-run the sync once it completes.`);
          }
          throw new Error(rec.reason === 'target-occupied'
            ? `serial collision: ${id} needs serial ${rec.want} on cloud, already held by ${rec.heldBy}`
            : `base reconciliation failed for ${id}: ${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}`);
        }
```

Add a branch beside `job-in-flight`, **above** the generic tail at `:754`. Appending it *after* this
block — the only other obvious place, and the one v2 left an implementer to guess — makes it dead,
because every `!rec.ok` already throws by `:756` (round-1 M6's exact failure):

```ts
          // Round-16 M1 — the generic tail cannot name a repair, and this refusal has two very
          // different repairs depending on which side produced the unservable base.
          if (rec.reason === 'unservable-base') {
            throw new Error(rec.origin === 'vault-filename'
              ? `base reconciliation refused for ${id}: rename the vault file ${rec.key} to a servable single path component, then re-run sync`
              : `base reconciliation refused for ${id}: the cloud key ${rec.key} cannot be relocated — it is unservable and has no local counterpart to rename`);
          }
```

**(b) The `skipped-unservable` report is RE-DERIVED FROM THE ROW, and there is no `rec.action` branch
at all.**

⛔ **Round-1 H4 → round-2 H5.** v2's comment said *"re-derive it each run from the row itself"* and
the code three lines below it pushed `report.errors` **from the branch having been taken** — which
decays to silence, because `skipped-unservable` returns `ok:true`, the caller advances the baseline,
and run 2 sees `describeDivergence` compute `from === to` (`reconcile-serial.ts:147-156`) and return
`{ok:true,action:'agreed'}`. v2 marked this FIXED; nothing re-derived.

The re-derivation is a check on `cv`, not on `rec`. **Insert after `sync-run.ts:614`**
(`const base = manifest.videos[id];`), inside the per-video `try`:

```ts
        // A cloud row advertising a key the serve path cannot serve is a standing defect, not an
        // event: it is true on every run until a human repairs it, and it is independent of what
        // the reconciler decided this run. Deriving it from the ROW is what makes it survive the
        // manifest baseline — the branch-derived version reported once and then went silent
        // forever, which is worse than never reporting it (round-1 H4).
        //
        // After T9 the seam prevents NEW unservable cloud keys, so this only ever fires for rows
        // written before this slice — which is exactly the population backlog #36 is about.
        if (cv?.summaryMd && !isServableSummaryKey(cv.summaryMd)) {
          report.errors.push({ videoId: id, message:
            `cloud key ${JSON.stringify(cv.summaryMd)} is not servable, so this video cannot be `
            + `served or shared from the cloud. The summary is still reachable locally; the cloud `
            + `key needs a manual repair.` });
        }
```

**No `rec.action === 'skipped-unservable'` branch is added.** `rec.ok` is true and `rec.action` is
not `'relocated'`, so control falls through to Class A exactly as it should — which is what lets
`copyToLocal` hydrate the paid artifact into the vault. *(A video can now produce two entries in one
run: this one, plus a refusal from (a). Both are true and they name different repairs; that is
better than suppressing either.)*

- [ ] **Step 6: Add 26d2's second-run assertion** — INTEGRATION

```ts
// ⚠ APPENDED to the file T11 creates — `EVIL`, the imports, the `RecordingBlobStore` decorator and
//    the `afterAll` cleanup are all already in it. T11 runs BEFORE T12; do not recreate the file.
it('behavior 26d2 — the SKIP is visible on run 1 AND run 2, and copyToLocal hydrates the paid summary', async () => {
  const ctx = await makeOwnerContext();
  await prepareSyncCtx(ctx);
  await seedLocalVideoFull(ctx, { position: 3, summaryMd: null });        // serial, no vault file
  await seedCloudVideo(ctx, { position: 7, summaryMd: EVIL, mdBody: '# paid\n' });
  const first = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  const second = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  for (const r of [first, second]) {
    expect(r.errors).toContainEqual(expect.objectContaining({
      videoId: ctx.videoId, message: expect.stringMatching(/is not servable/),
    }));
  }
  expect(await localBlobBytes(ctx, EVIL)).not.toBeNull();   // the paid summary IS recovered
});
```

**Run 2 is the whole point.** Written against run 1 only — as v2 was — this passes against the
branch-derived version that then goes silent forever.

- [ ] **Step 7: Run and commit**

```bash
npx tsc --noEmit && npm test && npm run test:integration
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add lib/cloud-sync/reconcile-serial.ts lib/cloud-sync/sync-run.ts tests/
git commit -m "feat(#36): reconcileCloudBase relocates, refuses or SKIPS per the four-cell table (behaviors 26d-26d4)"
```

---

## Task 13: The additive-create protocol, and the §4 gate derivation

**Spec:** §3.6.2. **Behaviors:** 18, 18b, 18c, 18c2, 18e, 18g, 18h, 18i, 18k, 19, 20.

**Files:**
- Modify: `lib/cloud-sync/sync-run.ts` (`copyAdditiveVideo` `:261-270`, `transferClassA` `:371-395`)
- Create: `scripts/check-encoder-gate-sql.py`
- Test: `tests/lib/cloud-sync/additive-protocol.test.ts` — **UNIT** (new). ⚠ **Round 3 moved this
  file out of the integration suite, and the reason is not tidiness:** every case here drives the
  protocol against a real `LocalFsMetadataStore` + either the real `LocalFsBlobStore` (behavior 18
  needs a real volume to alias NFC/NFD) or `InMemoryBlobStore` (18c2/19 need fault injection).
  **Nothing in it talks to Supabase** — and `test:integration` is NOT in CI (`docs/dev-process.md`,
  *"Not yet in CI"*), so leaving money-path guards there means CI never runs them. The Supabase half
  of `promoteIfAbsent` is covered where it belongs: T6's contract case in
  `tests/integration/blob-store.test.ts`.

**Interfaces:** Consumes `promoteIfAbsent` + `stagingRootOf` (T6), `canonicallyEqualName` (T0),
`copyAdditiveVideo` / `transferClassA` / `Side` (exported in T0). Produces nothing new.

- [ ] **Step 1: Write the failing tests — the WHOLE file, covering Steps 2 and 3** — UNIT

⛔ **Round-3 Codex B3 — three of these four were `/* … */` comment-only calls on the paid-artifact
path.** They are real now, and so are the five that cover Step 3. ⚙ **WRITTEN AND RUN, both ways:**

| Run | Result |
|---|---|
| **RED** — today's code, T0 exports applied (this step) | **6 failed / 3 passed.** 18b/18c, 18c2 and 19 all `Resolved to value: undefined` — today's `promote()` is a rename on the local FS, so the newcomer OVERWRITES the occupant and the function returns normally. 18h (occupied), 19 (unreadable) and 18i/18k each resolved `{mdHash: …, verified: true}` — today's unconditional `put` destroys the loser's artifact. That is backlog #36's money bug, executed |
| **GREEN** — Steps 2 + 3 applied (with T6's local + in-memory `promoteIfAbsent` and T0's `canonicallyEqualName`) | **9 passed / 9** |

The three that pass RED are the ones that must not regress: behavior 18 (the aliasing resume), 18g
(the owned overwrite) and 18h-unoccupied.

⚠ **Behavior 18's assertion is `toEqual([NFC])` over the directory's `.md` files, not
`toContain(NFC)`.** `toContain` also passes on a normalization-SENSITIVE volume, where `linkSync`
would have created a SECOND file instead of getting `EEXIST` — which is the entire behavior under
test. (Measured on APFS: one file, stored under the NFC name.)

`seed` and `readdirNames` (round-2 H6: 0 occurrences each) are gone; the file uses
`store.put(...)` for seeding and `fs.promises.readdir` for the on-disk name.

```ts
/**
 * §3.6.2 — the additive-create protocol and the Class-A loser-record guard (behaviors 18, 18b,
 * 18c, 18c2, 18g, 18h, 18i, 18k, 19).
 *
 * UNIT, not integration: every case here drives `copyAdditiveVideo` / `transferClassA` against a
 * real local metadata store and either the real local FS blob store (behavior 18 needs a real
 * volume) or `InMemoryBlobStore` (the fault injection 18c2/19 need). Nothing here talks to
 * Supabase — the Supabase half of `promoteIfAbsent` is covered by T6's contract case in
 * `tests/integration/blob-store.test.ts`, which is where a live stack is actually required.
 */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { LocalFsBlobStore } from '@/lib/storage/local/local-blob-store';
import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import { copyAdditiveVideo, transferClassA, type Side } from '@/lib/cloud-sync/sync-run';
import type { BlobRead, BlobStore } from '@/lib/storage/blob-store';
import type { Video } from '@/types';

const store = new LocalFsMetadataStore();
const PLAYLIST_META = { playlistUrl: 'https://www.youtube.com/playlist?list=PLX' };
const ID = 'vid00000001';
const KEY = '003_alpha.md';
const WINNER_BODY = '# winner\n\nbody\n';

/** Does this volume ALIAS the NFC and NFD spellings of one name (APFS/HFS+), or keep them as two
 *  distinct files (ext4)? MEASURED per run, never assumed — see behavior 18. `EEXIST` from
 *  `linkSync` is the aliasing signal; any OTHER errno is a real fault and must not be silently
 *  read as "sensitive volume", which would turn a broken environment into a passing test.
 *
 *  ⚠ The probe MUST use an NFC/NFD pair of the SAME name. Two differently-spelled ASCII filenames
 *  measure nothing: they would always link, and the probe would report every volume sensitive. */
function volumeAliasesNfcNfd(): boolean {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'nfc-probe-'));
  try {
    const nfc = path.join(d, 'probe-café.md'.normalize('NFC'));
    const nfd = path.join(d, 'probe-café.md'.normalize('NFD'));
    fs.writeFileSync(nfc, 'x');
    try {
      fs.linkSync(nfc, nfd);
      return false;                                       // two files -> SENSITIVE (ext4)
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === 'EEXIST') return true;   // aliased (APFS/HFS+)
      throw e;
    }
  } finally {
    fs.rmSync(d, { recursive: true, force: true });
  }
}

const roots: string[] = [];
function tmp(): string {
  const d = fs.mkdtempSync(path.join(os.homedir(), 'additive-protocol-'));
  roots.push(d);
  return d;
}
afterEach(() => { while (roots.length) fs.rmSync(roots.pop()!, { recursive: true, force: true }); });

function video(over: Partial<Video> = {}): Video {
  return {
    id: ID, serialNumber: 3, title: 'alpha', youtubeUrl: `https://youtu.be/${ID}`,
    archived: false, summaryMd: KEY, processedAt: '2026-08-01T00:00:00.000Z',
    artifacts: { summaryMd: { key: KEY, status: 'promoted' } },
    ...over,
  } as unknown as Video;
}

/** A replica: the real local metadata store over a temp dir, plus the blob store under test. */
async function side(blob: BlobStore = new InMemoryBlobStore()): Promise<Side> {
  const p = localPrincipal(tmp());
  await store.setPlaylistMeta(p, PLAYLIST_META);
  return { store, p, blob };
}

/** A loser side that already holds a row for ID, so `updateVideoFields` has something to patch. */
async function loserSide(blob: BlobStore = new InMemoryBlobStore()): Promise<Side> {
  const s = await side(blob);
  await s.store.claimVideoSlot(s.p, ID, 3);
  await s.store.upsertVideo(s.p, video({ summaryMd: null } as Partial<Video>));
  return s;
}

/** 18c2 — the read-back reports `absent` although promoteIfAbsent resolved. Not constructible by
 *  timing, so it is injected: everything else is the real in-memory adapter. */
class AbsentOnReadBack extends InMemoryBlobStore {
  async tryGet(): Promise<BlobRead> { return { ok: false, reason: 'absent' }; }
}

// ---------------------------------------------------------------------------
// Step 1's protocol — copyAdditiveVideo
// ---------------------------------------------------------------------------

it('behavior 18 — occupant is BYTE-IDENTICAL under the aliasing form: SUCCEEDS, stored name untouched', async () => {
  // The crash-resume case. Refusing here stalls the video forever.
  const NFC = '003_café.md'.normalize('NFC');
  const NFD = '003_café.md'.normalize('NFD');
  const r = await side(new LocalFsBlobStore());
  await r.blob.put(r.p, NFC, Buffer.from('body', 'utf8'), 'text/markdown');

  await expect(copyAdditiveVideo(
    r.store, r.p, r.blob, PLAYLIST_META, video({ summaryMd: NFD }), 'body',
  )).resolves.toBeUndefined();

  // EXACTLY one .md, under the STORED name: `toContain(NFC)` alone would also pass on a
  // normalization-SENSITIVE volume, where the link would have created a SECOND file.
  //
  // ⚠ ROUND-4 CLAUDE HIGH-1 — but which outcome is correct is a property of the VOLUME, and this
  // file is collected by the UNIT config (`jest.config.ts` testMatch `tests/lib/**`), which CI runs
  // on ubuntu-latest — ext4 (`.github/workflows/ci.yml:27,57`). Hard-coding `[NFC]` passes on the
  // implementer's Mac and goes RED in CI: exactly the gate T13 moved this file into so that it
  // would be run. So probe, do not assume.
  const md = (await fs.promises.readdir(r.p.indexKey)).filter((n) => n.endsWith('.md')).sort();
  if (volumeAliasesNfcNfd()) {
    expect(md).toEqual([NFC]);                    // APFS/HFS+: the link hit the existing inode
  } else {
    // ext4: the two spellings are simply two different names, so there was never an aliased
    // occupant to resume over. The copy still had to SUCCEED — that much is asserted above — but
    // THE CRASH-RESUME PATH THIS BEHAVIOR EXISTS TO TEST IS NOT EXERCISED HERE. A green run on a
    // normalization-sensitive volume is not evidence that resume works; read it as "not applicable".
    expect(md).toEqual([NFC, NFD].sort());
  }
});

it('behavior 18b/18c — occupant has DIFFERENT bytes: REFUSES, occupant intact', async () => {
  const r = await side();
  await r.blob.put(r.p, KEY, Buffer.from('occupant', 'utf8'), 'text/markdown');

  await expect(copyAdditiveVideo(
    r.store, r.p, r.blob, PLAYLIST_META, video(), 'newcomer',
  )).rejects.toThrow(/already occupied by DIFFERENT content/);

  expect((await r.blob.get(r.p, KEY))!.toString('utf8')).toBe('occupant');
});

it('behavior 18c2 — a read-back of `absent` REFUSES: that is a fault, not a resume', async () => {
  const r = await side(new AbsentOnReadBack());

  await expect(copyAdditiveVideo(
    r.store, r.p, r.blob, PLAYLIST_META, video(), 'newcomer',
  )).rejects.toThrow(/could not confirm/);
});

it('behavior 19 — an UNREADABLE read-back is treated as OCCUPIED, not absent', async () => {
  const blob = new InMemoryBlobStore();
  blob.failReads(KEY);                       // in-memory fault injection
  const r = await side(blob);

  await expect(copyAdditiveVideo(
    r.store, r.p, r.blob, PLAYLIST_META, video(), 'newcomer',
  )).rejects.toThrow(/could not confirm/);
});

// ---------------------------------------------------------------------------
// Step 3's guard — transferClassA
// ---------------------------------------------------------------------------

/** The winner always advertises KEY and holds WINNER_BODY at it. */
async function winnerSide(): Promise<Side> {
  const w = await side();
  await w.blob.put(w.p, KEY, Buffer.from(WINNER_BODY, 'utf8'), 'text/markdown');
  return w;
}

it('behavior 18g — the loser row NAMES this address: overwrites', async () => {
  const winner = await winnerSide();
  const loser = await loserSide();
  await loser.blob.put(loser.p, KEY, Buffer.from('loser divergent body', 'utf8'), 'text/markdown');

  await expect(transferClassA(winner, loser, video(), ID, video({ summaryMd: KEY })))
    .resolves.toBeDefined();

  expect((await loser.blob.get(loser.p, KEY))!.toString('utf8')).toBe(WINNER_BODY);
});

it('behavior 18h — loser row names a DIFFERENT address, destination OCCUPIED: REFUSES', async () => {
  const winner = await winnerSide();
  const loser = await loserSide();
  await loser.blob.put(loser.p, KEY, Buffer.from('someone else', 'utf8'), 'text/markdown');

  await expect(transferClassA(winner, loser, video(), ID, video({ summaryMd: 'other.md' })))
    .rejects.toThrow(/Refusing/);

  expect((await loser.blob.get(loser.p, KEY))!.toString('utf8')).toBe('someone else');
});

it('behavior 18h — loser row names a DIFFERENT address, destination UNOCCUPIED: WRITES', async () => {
  const winner = await winnerSide();
  const loser = await loserSide();

  await expect(transferClassA(winner, loser, video(), ID, video({ summaryMd: 'other.md' })))
    .resolves.toBeDefined();

  expect((await loser.blob.get(loser.p, KEY))!.toString('utf8')).toBe(WINNER_BODY);
});

it('behavior 19 — an UNREADABLE destination counts as OCCUPIED', async () => {
  const winner = await winnerSide();
  const blob = new InMemoryBlobStore();
  const loser = await loserSide(blob);
  blob.failReads(KEY);

  await expect(transferClassA(winner, loser, video(), ID, video({ summaryMd: 'other.md' })))
    .rejects.toThrow(/could not confirm/);
});

it('behavior 18i/18k — the ownership test is canonicallyEqualName, not byte equality', async () => {
  // An NFD-form row claiming the NFC-form key is the SAME claim (18i); a null claim is not (18k).
  const NFC = '003_café.md'.normalize('NFC');
  const NFD = '003_café.md'.normalize('NFD');
  const winner = await side();
  await winner.blob.put(winner.p, NFC, Buffer.from(WINNER_BODY, 'utf8'), 'text/markdown');

  const owned = await loserSide();
  await owned.blob.put(owned.p, NFC, Buffer.from('loser divergent body', 'utf8'), 'text/markdown');
  await expect(transferClassA(
    winner, owned, video({ summaryMd: NFC }), ID, video({ summaryMd: NFD }),
  )).resolves.toBeDefined();
  expect((await owned.blob.get(owned.p, NFC))!.toString('utf8')).toBe(WINNER_BODY);

  const unowned = await loserSide();
  await unowned.blob.put(unowned.p, NFC, Buffer.from('someone else', 'utf8'), 'text/markdown');
  await expect(transferClassA(
    winner, unowned, video({ summaryMd: NFC }), ID, video({ summaryMd: null } as Partial<Video>),
  )).rejects.toThrow(/Refusing/);
  expect((await unowned.blob.get(unowned.p, NFC))!.toString('utf8')).toBe('someone else');
});
```

- [ ] **Step 2: Implement the ADDITIVE protocol in `copyAdditiveVideo`** — the step v2 left with no code

⛔ **Round-1 H2 / round-2 M5.** v2 stated this step as one sentence of prose — no file, no line, no
signature — for five behaviors on the money path, while the step beside it quoted real code. Here is
what is there today, `sync-run.ts:260-270`, verbatim:

```ts
  let wroteBlob = false;
  if (video.summaryMd && mdBody != null) {
    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
    const staged = await toBlob.get(toP, ref.tempKey);
    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
      throw new Error(`additive staged MD verify failed for ${video.id}`);
    }
    await toBlob.promote(ref);
    wroteBlob = true;
  }
```

**The change:** `promote` becomes `promoteIfAbsent`, and a read-back classifies the four outcomes.
The `putStaged` + staged-verify above it is unchanged, and everything after `wroteBlob = true` is
unchanged.

```ts
    // §3.6.2 — ATTEMPT THE WRITE THAT CANNOT CLOBBER, then classify. `promote` on the local FS is
    // a rename and OVERWRITES; on this path the destination may be a DIFFERENT video's paid
    // summary, so the create-if-absent primitive is the one that is safe on both backends.
    await toBlob.promoteIfAbsent(ref);
    const after = await toBlob.tryGet(toP, video.summaryMd);
    if (!after.ok) {
      // absent  -> a FAULT, not a resume: promoteIfAbsent resolved, so something must be there
      //            (behavior 18c2).
      // unreadable -> treated as OCCUPIED, never as absence (behavior 19). `tryGet`, never `get`:
      //            on Supabase a null from `get` is absent-OR-denied-OR-network
      //            (supabase-blob-store.ts:29-35).
      throw new Error(
        `additive: could not confirm ${JSON.stringify(video.summaryMd)} for ${video.id} `
        + `after promoteIfAbsent (${after.reason}) — refusing to advertise promoted.`);
    }
    if (mdHash(after.bytes.toString('utf8')) !== mdHash(mdBody)) {
      // OCCUPIED by different bytes: someone else's artifact. Refuse; it is untouched (18b/18c).
      throw new Error(
        `additive: ${JSON.stringify(video.summaryMd)} is already occupied by DIFFERENT content on `
        + `the receiver; refusing to overwrite it for ${video.id}.`);
    }
    // EQUAL -> success, including the crash-resume case AND behavior 18: on a
    // normalization-insensitive volume the occupant may be stored under the ALIASING form of the
    // name, promoteIfAbsent's linkSync gets EEXIST, and the read-back returns identical bytes. The
    // STORED name is preserved, which is what 18 asserts. Refusing here would stall the video
    // forever.
    wroteBlob = true;
```

- [ ] **Step 3: Implement the CLASS-A LOSER-RECORD GUARD — behaviors 18g / 18h / 19**

⛔ **Round-1 Blocking (Codex).** v1 named 18g/18h and gave no step. v2 added one and it was the best
material in that draft — the signature, both call sites and the `tryGet` narrowing were all correct.
**But it was probe-then-write with nothing in between** (round-2 Codex B5): `tryGet` reports absent,
a concurrent worker creates the key, and `put` — which is `upload(..., { upsert: true })`
(`supabase-blob-store.ts:22-24`) — destroys it. v3 closes that window instead of accepting it, using
the primitive T6 added.

Today, verbatim:

```ts
// lib/cloud-sync/sync-run.ts:371-373 — the signature. No loserVideo.
async function transferClassA(
  winner: Side, loser: Side, winnerVideo: Video, videoId: string,
): Promise<{ mdHash: string; verified: boolean }> {

// :381-395 — stage, verify, then OVERWRITE unconditionally.
  const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
  const staged = await loser.blob.get(loser.p, ref.tempKey);
  if (!staged || mdHash(staged.toString('utf8')) !== h) {
    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
  }
  // …a 9-line comment explaining why put() and not promote()…
  await loser.blob.put(loser.p, key, staged, 'text/markdown');
  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
```

**Without a guard, a Class-A transfer writes the winner's body over an address the loser's row does
not claim — destroying a paid artifact.** §3.6.2 R3. Three edits:

```ts
// 1. The signature gains the loser's record.
async function transferClassA(
  winner: Side, loser: Side, winnerVideo: Video, videoId: string, loserVideo: Video | null,
): Promise<{ mdHash: string; verified: boolean }> {

// 2. Replace the unconditional put at :394-395 with a branch on OWNERSHIP.
if (canonicallyEqualName(loserVideo?.summaryMd ?? null, key)) {
  // OWNED. The loser's own row claims this address, so overwriting is the INTENT of a Class-A
  // transfer — the loser's body is the divergent one. This is today's behaviour, unchanged, and
  // the 9-line comment above it (why put() and not promote()) still applies verbatim.
  await loser.blob.put(loser.p, key, staged, 'text/markdown');
  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
} else {
  // NOT OWNED — the loser's row names a different address (or none: canonicallyEqualName(null, k)
  // is false, behavior 18k). A probe-then-put has NOTHING between the probe and the write, so a
  // concurrent owner action lands in the gap and `put` (upsert:true) destroys it. promoteIfAbsent
  // has no such window — it is the create-if-absent primitive on all three adapters (T6) — and it
  // consumes the staged ref AND removes the staging tree, so no temp cleanup follows.
  await loser.blob.promoteIfAbsent(ref);
  const dest = await loser.blob.tryGet(loser.p, key);
  if (!dest.ok) {
    // `unreadable` counts as OCCUPIED (behavior 19); `absent` after a resolved promoteIfAbsent is
    // a fault. `tryGet`, never `get`: get() swallows RLS denial into the same null as absence.
    throw new Error(
      `transferClassA: ${videoId} could not confirm ${JSON.stringify(key)} on the loser `
      + `(${dest.reason}); refusing rather than assuming the write landed.`);
  }
  if (mdHash(dest.bytes.toString('utf8')) !== h) {
    throw new Error(
      `transferClassA: ${videoId} would overwrite ${JSON.stringify(key)} on the loser, whose row `
      + `claims ${JSON.stringify(loserVideo?.summaryMd ?? null)}. Refusing.`);
  }
}

// 3. BOTH call sites pass it — the loser's video is the OPPOSITE side's record. Verified:
//    :782  copyToCloud → transferClassA(localSide, cloudSide, lv, id)  -> add `, cv`
//    :793  copyToLocal → transferClassA(cloudSide, localSide, cv, id)  -> add `, lv`
```

A throw here is caught per-video at `:812-814` and advances no baseline, so the transfer is retried
next run — which is correct: nothing was written.

- [ ] **Step 4: Re-run the file — GREEN** — UNIT: `npx tsc --noEmit && npx jest tests/lib/cloud-sync/additive-protocol.test.ts`.
      **Expected, MEASURED: 9 passed / 9.** The five `transferClassA` cases are the second half of
      the Step-1 file, under its `Step 3's guard` heading, because they share the `side()` /
      `loserSide()` / `video()` fixture. `loserSide()` claims a slot and upserts a row first,
      because `updateVideoFields` is a bare UPDATE that silently affects zero rows otherwise — the
      same hazard round-4 H1 documented for additive creates.

⚠ **Round-3 Claude M4 — the order of these steps is now tests-first.** v3 had Step 1 implement and
Step 2 test, for eleven money-path behaviors, which is TDD inverted; the RED table in Step 1 is what
running them first actually produced.

- [ ] **Step 5: Write the §4 gate derivation script (behavior 20) — WITH A BODY, AND POINTED AT ITS SUBJECT**

⛔ **Round-1 Blocking (both halves), then round-2 H1 + Codex B6.** v1 gave this script a docstring and
no body. v2 gave it a correct body pointed at **nothing**: its `SQL_CLASS` regex looked for a
Postgres `~ '^[...]+$'` operator, and §4 contains **0** such operators — it states its predicate in
prose, inside backticks, at spec line 1805. So `main()` returned 2 forever, the plan said *"fix the
SQL, not the script"*, and no step fixed the SQL because **the spec is closed**. Meanwhile v2's only
invocation was `--self-test`, which exits 0 without reading either subject: an implementer creates the
file, sees green, and ticks the behavior whose whole job is proving the §4 predicate is not a
hand-copied character class. A green check over the wrong subject.

**v3 makes the script match reality.** §4's gate, verbatim (spec `:1804-1805`):

> **Gate — FAILS IF** any `storage.objects` row in `artifacts` has a path segment **after the first two**
> not matching `` `^[A-Za-z0-9._-]+$` ``.

The class is there, in backticks. The script extracts §4's section text and finds it — and requires
**exactly one** such class in the section, so a future §4 that states two (or none) fails as NOT RUN
rather than silently picking the first.

⚙ **EXECUTED, all four ways: `--self-test` 10/10 exit 0; `main()` against the real spec and a real
`SAFE` declaration → `PASS - the encoder and the section-4 gate denote the same 65 characters`,
exit 0; a drifted encoder → `DRIFT: only in the encoder [] | only in the gate ['-']`, exit 1; a
missing encoder → `CANNOT READ … -> TREAT THIS AS NOT RUN`, exit 2.**

```python
#!/usr/bin/env python3
"""Behavior 20 - the section-4 gate's character class DERIVES from the encoder, not from memory.

Reads the JS class out of lib/storage/supabase/encode-segment.ts (`export const SAFE = /^[...]+$/`)
and the class the section-4 gate states in the spec, normalises both to a SET of characters, and
fails if they differ.

Exits 2 - NOT 0 - if either side cannot be located, or if section 4 states more than one class.
A check that cannot reach its subject has NOT passed (portable-practices section 2).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENCODER = os.path.join(ROOT, "lib/storage/supabase/encode-segment.ts")
SPEC = os.path.join(ROOT, "docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md")

JS_SAFE = re.compile(r"export const SAFE\s*=\s*/\^\[([^\]]+)\]\+\$/")
SECTION_4 = re.compile(r"^## 4\. .*?(?=^## )", re.M | re.S)
GATE_CLASS = re.compile(r"`\^\[([^\]]+)\]\+\$`")


def charset(cls: str) -> set:
    """Expand a character-class body to the SET it denotes. `A-Z` -> 26 chars."""
    out, i = set(), 0
    while i < len(cls):
        if i + 2 < len(cls) and cls[i + 1] == "-":
            out |= {chr(c) for c in range(ord(cls[i]), ord(cls[i + 2]) + 1)}
            i += 3
        else:
            out.add(cls[i]); i += 1
    return out


def main() -> int:
    for path in (ENCODER, SPEC):
        if not os.path.isfile(path):
            print(f"  CANNOT READ {path} -> TREAT THIS AS NOT RUN"); return 2
    js = JS_SAFE.search(open(ENCODER, encoding="utf8").read())
    if not js:
        print("  SAFE not found in the encoder -> NOT RUN"); return 2
    sec = SECTION_4.search(open(SPEC, encoding="utf8").read())
    if not sec:
        print("  section 4 not found in the spec -> NOT RUN"); return 2
    found = GATE_CLASS.findall(sec.group(0))
    if len(found) != 1:
        print(f"  section 4 states {len(found)} character classes, expected exactly 1 -> NOT RUN")
        return 2
    a, b = charset(js.group(1)), charset(found[0])
    if a != b:
        print(f"  DRIFT: only in the encoder {sorted(a - b)!r} | only in the gate {sorted(b - a)!r}")
        return 1
    print(f"  PASS - the encoder and the section-4 gate denote the same {len(a)} characters")
    return 0


def self_test() -> int:
    cases = [
        ("charset equal",         lambda: charset("A-Za-z0-9._-") == charset("A-Za-z0-9._-"), True),
        ("charset range differs", lambda: charset("A-Z") == charset("A-Y"), False),
        ("range expands",         lambda: charset("a-c") == charset("abc"), True),
        ("missing char",          lambda: charset("._-") == charset("._"), False),
        ("SAFE has 65 chars",     lambda: len(charset("A-Za-z0-9._-")) == 65, True),
        ("trailing hyphen literal", lambda: "-" in charset("A-Za-z0-9._-"), True),
        ("JS_SAFE matches a real declaration",
         lambda: bool(JS_SAFE.search("export const SAFE = /^[A-Za-z0-9._-]+$/;")), True),
        ("GATE_CLASS matches the backticked prose form",
         lambda: GATE_CLASS.findall("not matching `^[A-Za-z0-9._-]+$`.") == ["A-Za-z0-9._-"], True),
        ("GATE_CLASS does NOT match a JS regex literal",
         lambda: GATE_CLASS.findall("`SAFE = /^[A-Za-z0-9._-]+$/`") == [], True),
        ("SECTION_4 stops at the next h2",
         lambda: SECTION_4.search("## 4. X\nbody `^[ab]+$`\n\n## 5. Y\n`^[cd]+$`\n").group(0).count("^[") == 1, True),
    ]
    bad = 0
    for label, fn, want in cases:
        got = fn()
        good = got == want
        print(f"  {'ok  ' if good else 'FAIL'} {label} -> {got} (want {want})")
        bad += 0 if good else 1
    print(f"\n  {'PASS' if not bad else f'{bad} FAILURE(S)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
```

⚠ **The self-test's last three cases are the ones that matter**, and they are what v2 lacked: they
assert that the two extractors *discriminate* — `GATE_CLASS` matches the prose form and **not** a JS
regex literal, and `SECTION_4` stops at the next `##`. Without them the script could match §3.2's
`SAFE = /^[A-Za-z0-9._-]+$/` (spec `:289`) and compare the encoder to **itself**, which is the
tautology behavior 20 exists to prevent.

- [ ] **Step 6: Run everything — BY EXIT CODE, both invocations**

```bash
npx tsc --noEmit
npm test
npm run test:integration
python3 scripts/check-encoder-gate-sql.py --self-test      # the instrument works
python3 scripts/check-encoder-gate-sql.py                  # …and it reached its subject
set -e
for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do
  python3 "scripts/$c.py"
done
```

⛔ **Round-1 M2 / round-2 M6: this loop is `set -e` with no `|| echo`.** v2 carried the corrected form
in its Global Constraints and left the broken copy — `python3 scripts/$c.py || echo "RED: $c"`, which
exits 0 whatever happens — in this very step. And `main()` is run **by exit code** here, not only
`--self-test`: a self-test that passes proves the tool works, never that it looked at anything.

- [ ] **Step 7: Commit**

```bash
git add lib/cloud-sync/sync-run.ts scripts/check-encoder-gate-sql.py tests/lib/cloud-sync/
git commit -m "feat(#36): the additive-create protocol and the section-4 gate derivation (behaviors 18-19, 20)"
```

---

## Task 14: End-to-end — the bug in backlog #36 is actually fixed

**Behaviors:** 14, 15, 16, 23.

**Files:** Test only — `tests/integration/korean-title-e2e.test.ts` — **INTEGRATION** (new)

⛔ **Round-2 H6: this task was built out of five symbols and Task 0 created two.** `ingest`,
`ingestLocal`, `serveSummary` and `EXPECTED_ONE_SUMMARY_COST` have **0** occurrences in the repo, and
v2's inventory did not list any of them. v3 drives the real code instead of inventing entry points:

| v2 called | v3 drives | Why it is the honest subject |
|---|---|---|
| `ingest({title})` | `makeSummaryHandler(admin())(job, ctx)` with `jest.mock('@/lib/gemini')` | the real cloud ingest, exactly as `tests/integration/summary-handler.test.ts:104` drives it. It runs `slugify`, `padSerial`, `putStaged`, `promote` and `persist_summary` for real |
| `serveSummary(videoId)` → `.status === 200` | `loadSummaryForServe(client, { videoId, playlistId, userId })` → `.ok === true` | `lib/html-doc/serve-summary-core.ts:33` — the exported seam every summary serve route goes through, and the **exact** place today's guard 409s a Korean key (`:61-64`, `return { ok: false, status: 409, error: 'corrupt summary key' }`). Asserting `ok` is stronger than a status code and needs no HTTP harness |
| `ledgerTotal()` + `EXPECTED_ONE_SUMMARY_COST` | `ctx.spendLedgerTotal()`, asserted **unmoved** | with `lib/gemini` mocked at the module boundary — the project's mocking policy — nothing meters, and the handler is called directly so no producer reservation and no runner settle occur. The ledger delta is **0**, and `toBe(before)` is a *stronger* money assertion than an invented constant. `EXPECTED_ONE_SUMMARY_COST` dissolves |
| `ingestLocal({title})` + `vaultPath` | `localBlobStore.put` at the real derived name, then `fs.promises.readdir` | behavior 16's vault half is a claim about the FILESYSTEM round-tripping the name, not about the local pipeline. Writing `${padSerial(n)}_${slugify(title)}.md` through the real local store and reading the directory back is that claim, with nothing invented |

- [ ] **Step 1: Write the tests** — INTEGRATION

```ts
it('behavior 14 — a KOREAN-titled video ingests and SERVES, and the ledger is unmoved', async () => {
  const before = await ctx.spendLedgerTotal();
  const { videoId, playlistId, userId, client } = await ingestViaHandler({ title: '한국어 강의' });
  const load = await loadSummaryForServe(client, { videoId, playlistId, userId });
  expect(load.ok).toBe(true);                     // today: { ok:false, status:409 }
  expect((load as { mdKey: string }).mdKey).toMatch(/^\d{3,}_.*\.md$/);
  expect(await ctx.spendLedgerTotal()).toBe(before);   // Gemini is mocked; nothing may meter
});

it('behavior 15 — an NFD accented-Latin title ingests and serves', async () => {
  const { videoId, playlistId, userId, client } = await ingestViaHandler({
    title: 'Café Introduction'.normalize('NFD'),
  });
  expect((await loadSummaryForServe(client, { videoId, playlistId, userId })).ok).toBe(true);
});

it('behavior 16 — space / emoji titles ingest and serve', async () => {
  for (const title of ['hello world', 'intro \u{1F600}']) {
    const { videoId, playlistId, userId, client } = await ingestViaHandler({ title });
    expect((await loadSummaryForServe(client, { videoId, playlistId, userId })).ok).toBe(true);
  }
});

it('behavior 16 — the VAULT filename is well-formed ON DISK, byte-for-byte, with no U+FFFD', async () => {
  // The astral-at-the-boundary case is a LOCAL claim: slugify's 60-unit slice can orphan a
  // surrogate half, and the filesystem then stores a U+FFFD-bearing name (T3). This asserts the
  // round-trip through the real local blob store, which is what the vault actually uses.
  const dir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'vault-'));
  const P = localPrincipal(dir);
  for (const title of ['hello world', 'intro \u{1F600}', 'a'.repeat(59) + '\u{20000}']) {
    const name = `${padSerial(1)}_${slugify(title)}.md`;
    expect(name.isWellFormed()).toBe(true);
    await localBlobStore.put(P, name, Buffer.from('# body\n', 'utf8'), 'text/markdown');
    expect(await fs.promises.readdir(dir)).toContain(name);   // byte-for-byte; NO U+FFFD
  }
});

it('behavior 23 — a title ending in the U+2488..U+249B or U+1F100 class ingests and serves', async () => {
  for (const ch of ['⒈', '⒛', '\u{1F100}']) {
    const { videoId, playlistId, userId, client } = await ingestViaHandler({ title: `Lesson ${ch}` });
    expect((await loadSummaryForServe(client, { videoId, playlistId, userId })).ok).toBe(true);
  }
});
```

`ingestViaHandler({ title })` is file-local: create a user, sign in, seed a playlist, build the job
with `makeJob`/`makePayload`, run `makeSummaryHandler(admin())(job, mockCtx)`, and return the
coordinates. All five helpers are lifted from `tests/integration/summary-handler.test.ts:36-95`.

- [ ] **Step 2: Run, verify green, commit** — INTEGRATION

```bash
npx tsc --noEmit && npm run test:integration -- tests/integration/korean-title-e2e.test.ts
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
git add tests/integration/korean-title-e2e.test.ts
git commit -m "test(#36): end-to-end — a title in any language ingests and serves (behaviors 14,15,16,23)"
```

---

## Task 15: ADR-0009 and the roadmap close-out

**Files:** Create `docs/adr/0009-logical-unicode-physical-ascii.md`; modify `docs/roadmap-to-launch.md`, `docs/backlog.md`.

- [ ] **Step 1: Write ADR-0009** — *logical keys are Unicode, physical keys are ASCII, the seam owns the mapping.* Record the decision, the three user decisions (①②③), premises P1–P8 with their falsifiers, and that **ADR-0008 survives** (`objectKey` encodes only `key`, never `p.id`/`p.indexKey`, so both physical keys stay under the same storage grant). Task #91.
- [ ] **Step 2: Tick backlog #36 and the roadmap step in the SAME commit as the work** — per Phase 5, the merge tick is written before the PR is opened.
- [ ] **Step 3: Run every gate, by exit code.**

```bash
npx tsc --noEmit && npm test && npm run test:integration
python3 scripts/check-encoder-gate-sql.py --self-test && python3 scripts/check-encoder-gate-sql.py
set -e; for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do python3 "scripts/$c.py"; done
```

- [ ] **Step 4: Commit, open the PR, notify. DO NOT MERGE — merging is a human gate.**

---

## Self-Review — v4, and the disposition of every finding from all three rounds

**The count, enumerated rather than recalled.** Counted by walking the four review documents and
listing every finding heading: round 1 = **25** (Claude 4 Blocking + 4 High + 7 Medium + 4 Low = 19;
Codex 4 Blocking + 2 Medium = 6). Round 2 = **33** (Claude 3 + 7 + 8 + 6 = 24; Codex 7 Blocking +
2 High = 9). Round 3 = **6 from Codex** (3 Blocking + 1 High + 1 Medium + 1 Low) and **0 Blocking
from Claude**, which CONVERGED. **Total 64.**

**FIXED means the CODE in this document changed, not the comment.** v2's self-review marked round-1
H3 and H4 FIXED and both were fixed only in prose — the comment said one thing and the code below it
did the other. Round 2's verdict on that was *"a DEFERRED row in v2 was more reliable than a FIXED
one."* Every FIXED row below names the section of v3 that carries the changed code.

### Round 1 — 25 findings

| # | Finding | v3 disposition |
|---|---|---|
| C-B1 | Vitest: 33 commands + 3 `vi.fn()`; wrong runner | **FIXED in v2, and the second half FIXED HERE** — see R2-B1 |
| C-B2 | `objectKey` dropped `p.id` and `assertLogicalKey` | **FIXED** — T2 Step 3 quotes `:15-18` and adds one line; **executed** |
| C-B3 | `list` called a nonexistent `rawList`, wrong slice offset | **FIXED** — real `collectObjectPaths`, `ownerRoot + physicalPrefix`; **executed**, incl. both existing tests |
| C-B4 | T1's property assertion fails on correct code | **FIXED** — asserts the PHYSICAL alphabet; **executed**, 17,376 iterations |
| C-H1 | Ten helpers the tests invoke do not exist | **FIXED** — T0's re-count: five DISSOLVE (the repo already has them), three become file-local, two are real work |
| C-H2 | `canonicallyEqualName` unimplemented | **FIXED** — T0 Steps 1–4, **executed** |
| C-H3 | T8 refusal in the ship arm only; conflated re-read | **FIXED IN CODE** — T8 Step 3 hoists it ABOVE `decideCompanion` at `:454` and derives it from `receiverModel`. v2 marked this FIXED with the snippet still in the ship arm (R2-B2) |
| C-H4 | SKIP visible one run, then permanently silent | **FIXED IN CODE** — T12 Step 4(b) derives the report entry from `cv.summaryMd`, adds NO `rec.action` branch, and 26d2 now asserts run 1 **and** run 2 |
| C-M1 | `statusCode: 409` dropped; 22 assertions | **FIXED** — T4 Step 3 keeps it and keeps the `typeof` short-circuit that 4 more assertions need |
| C-M2 | T4's flips of existing rejections uncounted; NFKC claim wrong | **FIXED** — T4 Step 4 enumerates all **5** (measured) with per-row dispositions; Step 3's comment now states the SCOPE instead of claiming completeness |
| C-M3 | T6 local `promoteIfAbsent` calls a nonexistent method, unimported symbols | **FIXED** — `stagingRootOf` is a real shared export; cleanup is the adapter's own `deletePrefix`; every `fs`/`path` call qualified; **executed** |
| C-M4 | T6 Supabase recipe not implementable, no cleanup | **FIXED** — T6 Step 4 reads via `tryGet`, uploads with `upsert:false`, removes the whole staging tree, and **drops the 409 assumption** in favour of `promote()`'s own re-read. NOT EXECUTED (needs the stack) — flagged in the header table and in the step |
| C-M5 | `deletePrefix` listed, never modified | **FIXED** — T2 Step 3 shows the exact line; behavior 11's test asserts it reaches an encoded dir; **executed** |
| C-M6 | T12's sync-run insertion point unstated; the obvious one is dead | **FIXED** — T12 Step 4(a) puts it INSIDE `if (!rec.ok)` above the generic throw at `:754`, and says why appending is dead |
| C-M7 | Commit after a slice narrower than the blast radius | **FIXED** — T4 Step 4 runs `npm test`; every task now runs `tsc` + the suite that contains its blast radius |
| C-L1 | T7's rollout count recalled | **FIXED — 41** (3 prod + 38 test) across **11** files, per-file breakdown + method stated. ⚠ v4 first wrote **42**, having counted a test TITLE (`it('writeModelEnvelope overwrites…')`, `model-store-cloud.test.ts:52`) as a call — the identical error the coordinator made and corrected earlier the same day. **A call site is the identifier followed by `(` OUTSIDE a string literal, excluding imports, comments and the two definitions.** Stated here because this number has now been got wrong three times |
| C-L2 | Sweeps described as covering, stride past 97% | **FIXED** — T1's is labelled a SAMPLE with its measured coverage; T4's behavior 27 is now **stride 1** (3,479,131 non-empty slug assertions, executed) with the timeout that requires |
| C-L3 | Three test bodies un-executable, fixtures elided | **FIXED** — T8 Step 1 builds `sides()`/`seedEnvelope`; T11 and T12 use real `runSync(deps, opts)` calls; T12 Step 1 has a four-row fixture table |
| C-L4 | T5's target file mocks the module T5 tests | **FIXED by retargeting** — T5 goes to `share-serve.test.ts`, which has no module mock and already carries `seedDoc`/`mintDirect` |
| X-B1 | T1 property test cannot pass | duplicate of C-B4 — **FIXED** |
| X-B2 | T6 `ref.key` does not type-check against `StagedRef` | **FIXED** — T6 uses `ref.finalKey` / `ref.tempKey`; `StagedRef` quoted from `blob-store.ts:5` |
| X-B3 | T13 Class-A ownership guard has no executable step | **FIXED** — T13 Step 3, with both call sites and four tests |
| X-B4 | Gate script not executable as written | **FIXED** — full body, **executed** four ways |
| X-M1 | T9 seam predicate stricter than the spec | **DECIDED (unchanged from v2)** — scoped to `status === 'promoted'`; a guard stricter than its spec is one nobody agreed to |
| X-M2 | Ratchet loop masks exit codes | **FIXED IN CODE** — `set -e`, no `|| echo`, in the Global Constraints **and** in T13 Step 6, which is where the broken copy survived |

### Round 2 — Claude half, 24 findings

| # | Finding | v3 disposition |
|---|---|---|
| B1 | 13 verification commands run ZERO tests | **FIXED** — every command is labelled UNIT or INTEGRATION; **0** remaining `npx jest tests/integration/…`; the two-suite rule is a Global Constraint with the measured "No tests found" failure written out |
| B2 | `decision.receiverEnvelope` does not exist; H3 survived its own fix | **FIXED** — T8 Step 3 quotes `CompanionAction` (`companion.ts:25-28`) and `ModelRead` (`:12-15`) and derives the guard from `receiverModel`, above `decideCompanion` |
| B3 | Five tasks test functions `sync-run.ts` does not export | **FIXED** — T0 Step 5 exports `Side`, `copyAdditiveVideo`, `transferClassA`, `companionTransfer` with the reasoning; `readVideo` deliberately NOT exported; T0's table corrects the inventory |
| H1 | Gate script created and never pointed at its subject | **FIXED** — the extractor now matches §4's real backticked class; T13 Step 6 runs `main()` **by exit code**; the self-test gains three discrimination cases so it cannot compare the encoder to itself |
| H2 | No task that changes a type runs `tsc`; jest is SWC | **FIXED** — `npx tsc --noEmit &&` on every task's verification, and the reason is a Global Constraint |
| H3 | Four T8 tests assert `res.shipped`, which does not exist | **FIXED** — every T8 test asserts the observable (`readModelEnvelope` on the loser); the return type is explicitly unchanged |
| H4 | T9/T11 assert `runSync` REJECTS; it cannot | **FIXED** — all six such assertions rewritten against `report.errors`, with the reason (`:812-814`) and the danger of the "obvious fix" stated |
| H5 | Round-1 H4 marked FIXED, fixed only in prose | **FIXED IN CODE** — see C-H4 |
| H6 | Task 0's inventory incomplete: six more symbols in neither column | **FIXED** — all six accounted for in T0's table; four dissolve in T14/T13; `runSummaryJob` replaced by `makeSummaryHandler` in T10 |
| H7 | `fakeStoreHolding` returns a `BlobStore`, so the fake is under test | **FIXED** — signature is `(p, logicalKeys) => { store: SupabaseBlobStore, … }`, built on `blob-store-list.test.ts:34`'s `fakeClient`; the logical-vs-physical question is answered explicitly and asserted; **executed** |
| M1 | T6's `stagingRoot` (0 occurrences), unimported symbols | **FIXED** — see C-M3 |
| M2 | T6's Supabase/in-memory recipes; `this.map` does not exist | **FIXED** — the field is `this.blobs` (`:45`) holding `StoredBlob`; both adapters **executed** |
| M3 | T12's insertion point unmitigated (no `tsc` runs in T12) | **FIXED** — insertion point stated (C-M6) **and** `tsc` added |
| M4 | T4's five flipped rejections; false NFKC claim heading for the codebase | **FIXED** — see C-M2 |
| M5 | T13 Step 3 is the only step with no code, and carries five money-path behaviors | **FIXED** — T13 Step 1 quotes `:260-270` and gives the full replacement with all four outcomes |
| M6 | T13 Step 7 still runs the ratchet with `|| echo` | **FIXED** — see X-M2 |
| M7 | Elided fixtures; four calls with no arguments at all | **FIXED** — see C-L3 |
| M8 | T5's target file mocks the module T5 tests | **FIXED** — see C-L4 |
| L1 | T7's rollout count wrong in the "recounted" direction | **FIXED** — 42, counted, with the per-file breakdown |
| L2 | T4's behavior 27 still overclaims | **FIXED** — stride 1, executed, 3,479,131 non-empty slug assertions |
| L3 | Tech Stack says `ts-jest`; the config is `next/jest` (SWC) | **FIXED** — the header says `next/jest` (SWC), and H2's Global Constraint explains why it matters |
| L4 | T7 Step 3 calls the read schema "unchanged" while changing it | **FIXED** — the comment now says a field is being ADDED, why it is `.optional()`, and why `.strict()` being off makes it safe |
| L5 | Two stale cross-references from the Task 0 insertion | **FIXED** — the ordering rationale now says T5 follows T4; the File Structure table has rows for every file T0 creates or modifies |
| L6 | T13 Step 4's refusal leaves an orphaned staging tree | **FIXED, and by a different route than suggested** — the non-owned branch now calls `promoteIfAbsent`, which removes the whole staging tree in its `finally` on every adapter. Moving the guard above `putStaged` (the suggested fix) is no longer possible, because the protocol needs the staged bytes |

### Round 2 — Codex half, 9 findings

| # | Finding | v3 disposition |
|---|---|---|
| B1 | Integration tasks use the unit runner | **FIXED** — see R2-B1 |
| B2 | `decision.receiverEnvelope` + the `shipped` property | **FIXED** — see R2-B2 and R2-H3 |
| B3 | T6 local `promoteIfAbsent` cannot compile | **FIXED** — see C-M3; **executed** |
| B4 | T6 Supabase recipe has no bytes and omits cleanup | **FIXED** — see C-M4. The suggested "copy/download the temp object" is what T6 Step 4 does |
| B5 | T13's Class-A non-owned branch races into an overwrite | **FIXED, not accepted as residual** — T13 Step 3's non-owned branch is `promoteIfAbsent` + read-back classify, exactly the additive protocol Codex proposed; overwrite survives ONLY where `canonicallyEqualName` proves the loser row owns the address |
| B6 | The §4 gate script cannot pass against the approved spec | **FIXED without touching the spec** — the script now reads §4's actual representation; **executed against the real file, exit 0** |
| B7 | Placeholder test bodies in T8, T11, T12 | **FIXED** — see C-L3 |
| H1 | T12's insertion point can route the refusal behind an unconditional throw | **FIXED** — see C-M6. Codex's exact prescription is what T12 Step 4 states, except that the `skipped-unservable` arm needs no sync-run branch at all now that the report is row-derived |
| H2 | T4 does not dispose the five flips, incl. the two NFKC does not close | **FIXED** — see C-M2 |

### Round 3 — the halves SPLIT: Codex NOT CONVERGED (3 Blocking + 1 High + 2 lower), Claude CONVERGED (0 Blocking)

Both halves re-ran v3's executable claims and both found them holding; that part is settled and was
not touched. The dispute was one class, adjudicated by the coordinator as **real, and a WRITING
problem rather than a reviewing one**: four test-fixture blocks that do not compose. **v4's answer
is that all four were written, RUN, and their measured output pasted into the step.**

| # | Finding | v4 disposition |
|---|---|---|
| C-B1 | T10's money-guard test is knowingly impossible | **FIXED** — the fixture is real (a declared seam), the prose escape hatch is DELETED, and the decision is recorded instead of deferred. RED 1/2 → GREEN 2/2 on the live stack |
| C-B1b | *(found by executing C-B1's fix)* T10's `ledgerTotal()` assertion is VACUOUS — the handler never touches `spend_ledger` | **FIXED** — replaced by the provider-call assertions, with the migration line numbers that prove the ledger cannot move here |
| C-B2 | T12's four cells are `/* … */` placeholders | **FIXED** — four real cells on the existing file's own helpers. RED 3/4 (each reaching `relocated`, i.e. the insertion point) → GREEN 4/4 |
| C-B2b | *(found by executing C-B2's fix)* the guard flips ONE existing case | **FIXED** — new T12 Step 4 disposes of it; blast radius MEASURED across the whole unit suite: exactly **1** of the repo's 2,703 tests |
| C-B3 | T13's additive-protocol tests are comment-only calls | **FIXED** — a complete file, RED 6/9 → GREEN 9/9; behavior 18's assertion strengthened so it cannot pass on a normalization-sensitive volume; the file MOVED to the unit suite, because it needs no Supabase and `test:integration` is not in CI |
| C-H1 | T8's fixture imports the wrong path and uses ~11 undeclared symbols | **FIXED** — a complete file importing `@/tests/integration/helpers/cloud` (what its sibling `e2e.int.test.ts:15-18` uses). RED 3/7 → GREEN 7/7. **The 18j fixture became TWO cases**: v3's single one only reached the `ship` arm, and the DELETE arm — the one round-1 H3 is about — was measured deleting the other video's paid model (`envelope after = null`) |
| C-M1 | The full-sweep count is mislabeled "iterations" | **FIXED** — re-run independently this round: **4,448,256 loop iterations / 3,479,131 non-empty slug assertions / 969,125 empty slugs skipped / 0 violations**. All four agree with Codex's re-run. ⚠ **The SPEC inherits the same wording and is NOT edited — it is closed.** Recorded here so it is not lost |
| C-L1 | `helpers/cloud.ts:132` is off by one | **FIXED** — `:131` |
| Cl-M4 | Task 13 inverts TDD — Step 1 implements, Step 2 tests, for eleven money-path behaviors | **FIXED** — T13's steps are reordered tests-first, which is also what produced its RED table |
| Cl-M2 | T10 calls `ledgerTotal()`, which has 0 occurrences | **FIXED** — the T10 file declares every helper it uses; and the assertion it was serving turned out to be vacuous anyway (C-B1b) |
| Cl-L1..L6 | 6 Lows: 9 stale `file:line` citations (one by 82), two "verbatim" blocks with comments stripped, `MODEL_KEY` characterised, T5's Files line vs its Step 3 | **L3 and L5 FIXED** (both were one line and both were verified while executing). **L1, L2, L4, L6 CARRIED FORWARD, not silently dropped** — round 3's remit was the four fixture blocks, and Claude's own verdict classes all six as *would-be-nice* with no executable consequence. They are worth a pass before dispatch |
| — | The brief said 88 steps | **NOT A PLAN DEFECT** — v3 had **87**, counted, and the number lives only in the brief. v4 has **88**: T12 gained a step (dispose of the flipped case) and T13 kept its seven after the reorder. `python3 -c "print(sum(1 for l in open('docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md') if l.startswith('- [ ] **Step')))"` — deliberately NOT baked into prose, because a hardcoded count that nothing checks goes stale silently |

**What v4 did NOT change.** The decomposition, ordering, interfaces and behavior mapping — held for
a third round, by both halves. No production snippet outside the four fixtures was rewritten.

### DEFERRED — ONE item. Two of v3's three were CLOSED in round 3, by execution

| Item | Why, and what an implementer should do |
|---|---|
| **The Supabase `promoteIfAbsent` adapter is the one unexecuted snippet** | It needs the live stack. Mitigation, not hope: its risky half — *"HTTP 409 means the object exists"* — was **removed**, replaced by re-reading the final, which is the recovery `promote()` at `:118-126` already ships and which is true whatever the API returns. T6 Step 5 runs the shared contract against it on the live stack; if the contract fails there, the plan is wrong and the implementer stops (Global Constraint). |

**CLOSED — ~~T10's fixture may be unreachable~~.** It is unreachable, that is now stated as a fact
rather than a worry, and the DECISION was made: an explicit test-only seam (a `jest.mock` factory
that `requireActual`s the real predicate and overrides one sentinel slug), plus a control case
proving the seam is narrow. Written, run RED, run GREEN. **A second defect fell out of executing it:
v3's `ledgerTotal()` assertion was vacuous** — see T10 Step 1.

**CLOSED — ~~T12 behavior 26d3's fixture may not be constructible~~.** It is constructible with no
invented character: `padSerial(1000)` is four digits where `padSerial(7)` is three, so renumbering a
cloud key that sits exactly ON the 131-code-point bound pushes it one past. Measured; the fallback
and the "say which you used" instruction are deleted.

### Type consistency, re-verified against the repo

`isServableSummaryKey` (T4) used identically in T5/T9/T10/T11/T12; `promoteIfAbsent(ref: StagedRef)`
(T6) consumed by T13 in two places; `stagingRootOf` (T6) used by all three adapters;
`contentTypeForKey` (T6) exported for the Supabase adapter only; `ModelEnvelopeWrite` (T7) is what
T8's ship stamps; `videoDataPayload` (T9) module-private, matching §3.5.1b row 1;
`canonicallyEqualName` (T0) used only in T13; `Side` (T0) used in T8's and T13's fixtures.
`SerialReconcileResult` (T12) — counted at `reconcile-serial.ts:69-81`: **2** `ok` variants and
**10** refusal variants today, so "the ten existing refusal variants" is right.

### The one thing a fresh implementer must not do

Install any guard on the local/vault path. Decision ① and round-16 B1. `presentIsLocal &&` in T11
and the absence of any guard in the local metadata store are the whole of it.


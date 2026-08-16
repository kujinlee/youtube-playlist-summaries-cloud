# Plan review — `2026-08-15-cloud-blob-key-encoding.md`, round 3, Claude half

**Subject:** the #36 implementation plan, **v3** (16 tasks, **87** steps — counted, the brief says 88),
2914 lines, plan commit `c8b5031`, branch `fix/cloud-blob-key-encoding`. No implementation code exists.
**Question asked:** is this plan executable, task by task, by an engineer with no context, leaving the
tree green between tasks?

**Verdict: CONVERGED.** 0 Blocking, 1 High, 4 Medium, 6 Low.

v3's governing claim is that *every snippet is either EXECUTED or is a verbatim quote of current
code*. **I tested that claim rather than reading it, and it is substantially true.** I re-ran the
load-bearing executable claims — `isServableSummaryKey`, `canonicallyEqualName`, the behavior-27
stride-1 sweep, the §4 gate script all four ways, the T6 `promoteIfAbsent` contract and the T2 encoder
wiring — and **every one held, three of them reproducing the plan's own numbers to the digit.** Two of
those I ran against the **real adapters and the real `SupabaseBlobStore`**, not against a
transcription, which is a stronger check than the plan performed on itself. I also opened every
`file:line` the plan cites; the verbatim quote blocks are verbatim, and no identifier the plan names
in a code block is invented except one already-dissolved helper.

The single High is that **T8 Step 1's fixture and the five tests below it do not compose** — nine
identifiers are unbound and eight are unimported — while the disposition table marks that finding
class FIXED. It is loud (it fails at `tsc`), local to one task's scaffolding, and cannot lose money.

**Method.** `grep` here is ugrep and returns nothing silently, so every existence and count claim below
comes from `python3` + `os.walk` + `re` with two patterns, or from the Read tool. Executed work ran
under Node 22.14.0 in a scratch directory outside the repo; where I needed the repo's own TypeScript I
copied `lib/` to scratch, applied the plan's edits **verbatim**, and bundled with the repo's own
`esbuild`. **I modified no tracked file** except this one. No literal control or bidi character was
written into any file — I verified my own scratch files with the plan's own detector after catching
myself writing three.

---

## HIGH

### H1 — T8 Step 1's fixture does not compose with T8's own tests. Nine unbound identifiers, eight unimported ones, one mis-parenthesized `await`, and one Side pair the fixture never builds. Task 8.

T8 Step 1 presents itself as the answer to round-1 L3 / round-2 M7: *"Here is the fixture, once, built
from helpers that exist."* It is a genuine and large improvement over v2 — `companionTransfer`'s real
4-parameter signature is respected, `sides()` and `seedEnvelope()` are real bodies, and the four
argument-less calls are gone. But the fixture's outputs and the tests' inputs do not line up.

`sides(ctx)` (plan `:1540-1546`) returns **`{ winner, loser }`**, both bound inside behavior 18j's own
`it` callback (plan `:1565`). Every later test is a separate callback:

| Plan line | Test | Identifiers used but never bound in that scope |
|---|---|---|
| 1583 | 18j "never THROWS" | `winner`, `loser`, `lv` |
| 1589-1591 | 18j2 | `cloudLoser`, `localLoser`, `winner`, `lv`, `base` |
| 1596-1599 | 18j4 | `loser`, `base`, `lv` |
| 1603-1605 | 18j6 | `winner`, `loser`, `base`, `lv` |
| 1699-1713 (Step 4) | 18j3+18j7 | `cloudSide`, `localSide` |

`lv` is never bound **anywhere** in T8 — 18j inlines `await localVideoRecord(ctx)` without naming it.
`base` is bound only at `:1566`. **`cloudLoser` and `localLoser` do not exist and cannot be produced by
`sides()`**, which hard-codes winner = local and loser = cloud; behavior 18j2's whole point is to drive
a **local** loser (so `readModelSide` returns `kind:'none'`) as well as the Supabase one
(`kind:'unknown'`, `provesAbsence = false`, verified at `supabase-blob-store.ts:10`). That second Side
pair is the fixture the task needs and does not have. `cloudSide`/`localSide` in Step 4 are a third
naming of the same two objects.

Used in the fixture but absent from its import list (plan `:1529-1534`): `SupabaseMetadataStore`,
`SupabaseBlobStore`, `ARTIFACTS_BUCKET`, `ModelEnvelopeWrite`, `localVideoRecord`, `reconcileCloudBase`
(Step 4), `Video` (Step 4). `MODEL_FIXTURE` (`:1554`) is neither imported nor defined anywhere in the
plan. `ctx` is used at module scope (`:1537`, `:1555`) and never declared — `makeOwnerContext` is
imported and never called. `ROW_VIDEO_ID` is defined at `:1537` and never used.

**And a type error the plan elsewhere gets right.** Plan `:1570`:

```ts
const res = await companionTransfer(winner, loser, mdHash(MD), await localVideoRecord(ctx)!);
```

`!` binds tighter than `await`, so this is `await (localVideoRecord(ctx)!)` — the non-null assertion is
applied to the **Promise**, and the awaited value stays `Video | null`. `companionTransfer`'s fourth
parameter is `Video` (`sync-run.ts:445`, verified). **The plan writes the correct form twice, two steps
later** — `(await localVideoRecord(ctx))!` at `:1704` and `:1713`.

**Failure scenario.** An implementer opens T8, the money-path task, and copies Step 1. `tsc` reports
`Cannot find name 'lv'`, `'base'`, `'cloudLoser'`, `'localLoser'`, `'MODEL_FIXTURE'`,
`'SupabaseMetadataStore'`, `'ctx'` … and `Argument of type 'Video | null' is not assignable to
parameter of type 'Video'`. Most are mechanically recoverable. `cloudLoser`/`localLoser` are not: the
implementer must decide how to build a local-loser transfer, and that decision determines whether
behavior 18j2 tests the tri-state it was written for or silently tests the Supabase arm twice.

**Why High and not Blocking.** It fails at compile time, not at runtime; nothing is silently green;
the *implementation* snippet (Step 3) is complete, correct and independently verified below; and no
paid artifact is at risk. But the disposition table says **"C-L3 | Three test bodies un-executable,
fixtures elided | FIXED — T8 Step 1 builds `sides()`/`seedEnvelope`"** and **"M7 | Elided fixtures;
four calls with no arguments at all | FIXED"**. Those rows overstate: the *shape* is fixed, the file is
not writable as given.

**Fix.** Hoist a `beforeEach` (or a `fixture()` helper) that binds `ctx`, `base`, `lv`, and both Side
pairs; add the eight imports and a `MODEL_FIXTURE`; build the second pair explicitly
(`{ winner: cloudSide, loser: localSide }`) for 18j2; and correct `:1570` to
`(await localVideoRecord(ctx))!`. Pick one naming — `winner`/`loser` or `localSide`/`cloudSide` — and
use it in both Step 1 and Step 4.

---

## MEDIUM

### M1 — T10 Step 1's fixture cannot make the guard fire, and T10 Step 4 says "Expected: PASS". MEASURED. Task 10.

**MEASURED** under Node 22.14.0, running the plan's own T3 `slugify` and T4 `isServableSummaryKey`
against `padSerial(n) + '_' + slugify('x'.repeat(400)) + '.md'`:

| serial | key length | `isServableSummaryKey` |
|---|---|---|
| 1 | 67 cp | **true** |
| 999 | 67 cp | **true** |
| 99999 | 69 cp | **true** |

`slugify('x'.repeat(400))` is **60** characters. So the guard
`if (!isServableSummaryKey(\`${baseName}.md\`))` never fires, and
`await expect(handler(...)).rejects.toThrow(/servable/)` cannot be satisfied. T10 Step 4 nevertheless
reads *"Expected: PASS."*

**The substance of this is honestly disclosed** — Step 1's ⚠ note (plan `:1943-1954`) states it
precisely, says `'x'.repeat(400)` slugifies to 60, and gives the fallback (convert to a `tests/lib/`
unit test of the predicate over `${padSerial(n)}_${slugify(t)}.md`); the DEFERRED table repeats it. So
this is a legitimate deferral, not a trap. The residual defect is that **Step 4's expectation
contradicts Step 1's own warning ten lines above it**, and Step 2's *"Expected: FAIL — Gemini was
called"* describes a failure mode the fixture also cannot produce (it fails on the missing rejection,
not on a Gemini call).

**Fix.** One sentence: change Step 4 to *"Expected: the fallback unit test PASSES; the integration form
cannot go green — see the note in Step 1"*, and delete the "Expected: PASS" from the integration
command.

### M2 — T10 calls `ledgerTotal()`, which Task 0's own inventory dissolves. Task 10.

Plan `:1932` and `:1939`: `const before = await ledgerTotal();` … `expect(await ledgerTotal()).toBe(before);`

Task 0's table (plan `:145`) resolves this explicitly:

> `ledgerTotal` ❌ missing | `Ctx.spendLedgerTotal()` **exists** — `tests/integration/helpers/cloud.ts:157` … | **use it**

**Counted:** `ledgerTotal` as a bare callable has **0** occurrences in the repo (two patterns,
declaration-shaped and bare-occurrence, over every non-`node_modules` `.ts`/`.tsx`). T14 uses the
correct `ctx.spendLedgerTotal()` throughout; T10 did not get updated. This is the exact class round-2
H6 filed, surviving in one place inside the round that marks it FIXED.

*(The money assertion itself is sound, and I checked it: `lib/job-queue/summary-handler.ts` contains
**0** references to `spend_ledger` — `reserveVideoSlot` reserves a **serial slot**, not money — and the
only three `spend_ledger` mentions in `lib/` are in `sync-run.ts:8` (a comment saying sync never
charges), `companion.ts:35` and `dig/generate.ts:125`. So "the ledger delta is 0" holds for both T10
and T14.)*

**Fix.** Replace both with `ctx.spendLedgerTotal()`, and note that `admin` — used at plan `:1933` — is
`tests/integration/summary-handler.test.ts:35`, one line above the `:36-95` range T10 tells the
implementer to copy.

### M3 — T13 Step 2 carries three elided fixtures and two undescribed decorators, and the disposition table's "FIXED" for that finding names only T8, T11 and T12. Task 13.

**Counted** over the whole plan: **4** calls whose entire argument list is a comment. One (`:1525`) is
the plan quoting v2's defect. The other three are live test bodies in T13 Step 2:

| Plan line | Behavior | Body |
|---|---|---|
| 2434 | 18b/18c — occupant has DIFFERENT bytes | `copyAdditiveVideo(/* …same shape, mdBody 'newcomer' … */)` |
| 2443 | 18c2 — read-back `absent` is a fault | `copyAdditiveVideo(/* …toBlob: absentOnReadBack(store)… */)` |
| 2450 | 19 — unreadable counts as occupied | `copyAdditiveVideo(/* …toBlob: store… */)` |

`absentOnReadBack` (plan `:2443`) and `RecordingBlobStore` (T11, plan `:2056`) are both named as
file-local decorators with a pointer to `FailPromoteBlobStore` (`helpers/cloud.ts:168`, verified) but
no body — and T0 Step 5's table promised this one as *"`spyStore` … a file-local decorator in T11"*,
under a different name.

These are the *five* money-path behaviors T13 Step 1 implements, and the C-L3 row's evidence is
*"T8 Step 1 builds `sides()`/`seedEnvelope`; T11 and T12 use real `runSync(deps, opts)` calls; T12 Step
1 has a four-row fixture table."* T13 is not mentioned. **T12's four elisions ARE disclosed** — its
four-row fixture table (plan `:2187-2192`) is the disposition, and it names its own fallback. T13's are
not.

**Fix.** Give T13 Step 2 the one shared fixture the other tasks now have (`VIDEO`, `PLAYLIST_META`,
`KEY`, `ctx` are all already implied by the 18-test at `:2420-2430`, which *is* complete), and write
the six-line bodies for `absentOnReadBack` and `RecordingBlobStore` — or say in C-L3 that T13 Step 2 is
a deferral, which round 2 measured as the more reliable label.

### M4 — Task 13 inverts TDD: Step 1 implements, Step 2 writes the tests. Eleven behaviors, all on the money path, are never observed red-first. Task 13.

Every other task in the plan is test-first (Step 1 write the failing test, Step 2 run it and see it
fail, Step 3 implement). T13 alone is:

- **Step 1: Implement the ADDITIVE protocol in `copyAdditiveVideo`** — *"the step v2 left with no code"*
- **Step 2: Write the failing tests for Step 1**
- **Step 3: Implement the CLASS-A LOSER-RECORD GUARD**
- **Step 4: Assert both branches**

`docs/dev-process.md` Phase 3 names `superpowers:test-driven-development` as the gate. T13's behaviors
are 18, 18b, 18c, 18c2, 18e, 18g, 18h, 18i, 18k, 19, 20 — the additive-create protocol and the Class-A
ownership guard, i.e. the two places the slice refuses to overwrite a paid artifact. Writing those
assertions after the implementation means **no test in T13 is ever seen to fail**, which is precisely
how a vacuous assertion survives. This project has measured that failure directly (the
`--passWithNoTests` scenario in round-2 B1; the "a negative test that catches *any* error passes on
typos" memory).

Combined with M3 — three of those test bodies being elided — T13's verification is the weakest in the
plan while its subject is the most dangerous.

**Fix.** Swap Steps 1↔2 and 3↔4, and add the "run it, expect FAIL, and expect *this* message" step the
other twelve tasks all carry.

---

## LOW

### L1 — nine `file:line` citations are stale by 1–4 lines, and one by 82. Every symbol exists; none is invented.

Verified by opening each file. These are navigation pointers, not the verbatim quote blocks (those are
correct — see *What holds up*).

| Plan says | Actually at | Δ |
|---|---|---|
| `spendLedgerTotal` `helpers/cloud.ts:157` | `:153` (decl), `:76` (interface) | −4 |
| `cloudVideoRecord` `helpers/cloud.ts:468` | `:471` | +3 |
| `localVideoRecord` `helpers/cloud.ts:473` | `:476` | +3 |
| `seedVideo` `helpers/cloud.ts:378` | **`:296`** | **−82** |
| `syncDeps` body `helpers/cloud.ts:132` | `:131` | −1 |
| `syncDeps` on `Ctx` `helpers/cloud.ts:66` | `:69` (`:66` is inside the docstring) | +3 |
| `seedFreshModel` `share-route.test.ts:78` | `:79` | +1 |
| `putBudget` `tests/support/budget.ts:21` | `:18` | −3 |
| `loadSummaryForServe` `serve-summary-core.ts:33` | `:34` | +1 |
| `target-occupied` refusal `reconcile-serial.ts:197` | `:198` (`:197` is the `if (holder)`) | +1 |

`unsupported-artifacts` at `:214-216` is correct (the return is `:215`). `seedVideo`'s 82-line miss is
the only one large enough to send a reader to the wrong function — `:378` is a docstring about building
`videos.data`.

### L2 — two blocks labelled "verbatim" are the code with comments stripped.

T12 Step 4(a) says *"`sync-run.ts:739-757` is verbatim today"* and omits the comment blocks at
`:740-741` and `:745-748`. T0 Step 6's quote of `helpers/cloud.ts` elides a line but marks it with an
explicit ellipsis, which is honest. Neither changes the instruction — the branch structure, the line
numbers and the insertion point (*"beside `job-in-flight`, above the generic tail at `:754`"*) are all
correct, and I verified `:754` is the generic `throw`. But after two rounds in which "verbatim" was the
load-bearing word, the abridged ones should say so.

### L3 — `local-blob-store.ts:1` holds default imports, not namespace imports.

T6 Step 4: *"fs/path/crypto are NAMESPACE imports (`:1`), so every call is qualified."* The line is
`import fs from 'fs'; import path from 'path'; import crypto from 'crypto';` — **default** imports
under `esModuleInterop`. The operative instruction (qualify every call: `fs.mkdirSync`, not bare
`mkdirSync`) is correct and is what round-1 M3 was about; only the term is wrong.

### L4 — `MODEL_KEY(base)` is characterised where the code has an inline template literal.

T8 Step 3's comment: *"leaves `loser.blob.delete(loser.p, MODEL_KEY(base))` at `:475` reachable."*
`sync-run.ts:475` is
`try { await loser.blob.delete(loser.p, \`models/${base}.json\`); } catch { /* best-effort */ }`.
`MODEL_KEY` exists (`model-store.ts:32`) and expands to exactly that string, so the meaning is right
and the line is right — it is a paraphrase inside a code span, which is the habit this project files
under "quote the code, don't characterise it".

### L5 — the Ordering rationale says "T13 consumes T6 and T4". It consumes T6, T0 and **T1**.

T13's inputs are `promoteIfAbsent` + `stagingRootOf` (T6), `canonicallyEqualName` + the widened exports
(T0), and — for behavior 20 — `scripts/check-encoder-gate-sql.py`, which reads
`lib/storage/supabase/encode-segment.ts`'s `SAFE`, i.e. **T1**. T13 uses `isServableSummaryKey`
nowhere. T13's own Interfaces block gets this right, and T1's Interfaces block says *"consumed by T2
and by `scripts/check-encoder-gate-sql.py` (T13)"*. Harmless — T1 and T4 are both far earlier — but the
rationale is the one place a reader checks ordering.

### L6 — T5's Files line and T5 Step 3 name different insertion points.

Files: *"Modify: `lib/share/serve.ts` (after the `mdKey` assignment at `:47`)"*. Step 3: *"one line
immediately after `:48`"*, with a comment explaining that `mdKey` is a narrowed `string` there *because
of* the `if (!mdKey)` at `:48`. Step 3 is right; the Files line reads as one line earlier, which is
before the narrowing.

---

## What holds up — the executable claims, re-run

Stated at length because calibration matters more than finding count in round 3, and because the whole
of v3's method claim rests on these. **Everything in this section is a measurement I made, not a
reading.**

- **`isServableSummaryKey` is correct on every behavior T4 claims. EXECUTED, 28/28.** I transcribed T4
  Step 3 verbatim and ran all of Step 1 and Step 5's cases under Node 22.14.0, building every non-ASCII
  fixture from explicit code points so nothing could be mangled: 6/6 accepts (Korean, NFD Latin, space,
  emoji, U+2488, U+1F100); 10/10 rejects (nested, `%2f`, U+FF0F, U+2100, both traversal shapes, U+0007,
  U+0085, U+202E, over-long); ill-formed rejected; both 17d cases accepted; 129/130/131 accepted and
  132 rejected; the 67-code-point / 131-UTF-16-unit astral key accepted. The `Bidi_Control` sweep at
  **stride 1 over all 1,112,064 code points** finds exactly **12** such code points and **0**
  violations — the plan's `expect(seen).toBe(12)` is exactly right.
- **T4 Step 4's disposition table is exactly right. MEASURED against the real test file.** I parsed
  `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts` and evaluated its case tuples directly:
  **5 accept cases, 18 reject cases, 4 non-string cases**. The new predicate keeps **5/5** accepts,
  flips **exactly 5** rejections, and they are **exactly** the five the plan names — `double-dot`,
  `leading-space`, `leading-dot`, `fraction-slash-2044`, `division-slash-2215` — leaving 13 rejected.
  All 4 non-string cases still produce `statusCode: 409` through the `typeof` short-circuit. The plan's
  *"if a sixth row fails, stop"* is a real, armed stop condition. Round-1 M2 / round-2 M4 / Codex H2 are
  genuinely closed, and Step 3's SCOPE paragraph now states the U+2044 / U+2215 truth instead of the
  false NFKC-completeness claim that survived two rounds.
- **`canonicallyEqualName` passes all four assertions. EXECUTED, 6/6** (I added two of my own: the
  relation is reflexive on a Korean name, and U+FF21 does fold to `A` under NFKC — which is what makes
  "a proper subset, deliberately" a real claim rather than a decorative one).
- **Behavior 27 reproduces the plan's number to the digit. EXECUTED at stride 1.** All four title
  forms, all 1,112,064 code points: **3,479,131 iterations, 0 violations**, 9.2 s on this machine
  (the plan says 8.7 s). 969,125 empty slugs correctly skipped. The 30 s timeout is genuinely required.
  Round-1/round-2 L2 is closed and the name *"over the whole codepoint space"* is now earned.
- **The §4 gate script is correct AND pointed at its subject — this is the strongest fix in v3.**
  Round-2 H1 and Codex B6 were that `SQL_CLASS` had nothing to match, so `main()` returned 2 forever
  while the only invocation was `--self-test`. I extracted the script from the plan, built a tree with
  the **real spec** and a real `SAFE` declaration, and ran it four ways:

  | Invocation | Result |
  |---|---|
  | `--self-test` | 10/10 ok, **exit 0** |
  | `main()` vs the real spec | `PASS - the encoder and the section-4 gate denote the same 65 characters`, **exit 0** |
  | encoder drops the hyphen | `DRIFT: only in the encoder [] \| only in the gate ['-']`, **exit 1** |
  | encoder absent / `SAFE` absent / §4 states two classes | `TREAT THIS AS NOT RUN`, **exit 2** (all three) |

  And I checked the extractors against the real file rather than trusting them: `SECTION_4` matches
  spec lines **1796–1836** (`## 4. No migration, and how far that is proven`), `GATE_CLASS` finds
  **exactly one** class inside it, at spec line **1805** — the line the plan quotes — and the **whole
  spec contains exactly one** such backticked class, so the tautology the self-test's three new
  discrimination cases were added to prevent is not reachable even in principle. T13 Step 6 runs
  `main()` **by exit code**, not only `--self-test`.
- **T6's `promoteIfAbsent` is implementable exactly as written, on both executable adapters —
  EXECUTED 12/12 against the REAL code, not a transcription.** I copied `lib/` to scratch, applied the
  plan's T6 Step 3 and Step 4 edits verbatim (adding `stagingRootOf`, exporting `contentTypeForKey`,
  adding the interface method and both adapter bodies), bundled with the repo's own `esbuild`, and ran
  the full contract: behaviors 18d, 18d2, 18d3, absent-final and malformed-`tempKey` **pass on both
  `LocalFsBlobStore` and `InMemoryBlobStore`**, and both 18d4 cases (`promote` still overwrites by
  default, still skips under `create-if-absent`) pass. `stagingRootOf` rejects `'notstaging/x.md'` with
  `/not a _staging/` **before any write**, and `store.list(P, '_staging/')` is `[]` afterwards on both.
  Round-1 M3/M4, round-2 M1/M2 and Codex B3 are genuinely closed, and the fix is better than the one
  round 2 asked for: cleanup is each adapter's own already-tested `deletePrefix`, not hand-written
  `rmSync`.
- **T2's encoder wiring is correct — EXECUTED 8/8 against the REAL `SupabaseBlobStore`.** Same harness,
  plan T2 Step 3 applied verbatim. Behaviors 8+12 (logical keys returned, trailing slash optional, and
  the fake's layout asserted to be the *encoded* one), 9 (throws `/cannot be mapped back/` on an
  unmappable remainder), 10 (does **not** throw when the caller's own prefix contains `=`), the
  empty-prefix case, `objectKey` (per-segment encoding, owner prefix kept, `assertLogicalKey` still
  throwing `statusCode: 400` on `../x.md` with **0** uploads), and 11 (`deletePrefix` reaches an
  encoded dir from a logical prefix). **And both EXISTING tests in `blob-store-list.test.ts` still
  pass**, including the nested-folder recursion case. Round-2 H7 is genuinely closed: the corrected
  `fakeStoreHolding(p, logicalKeys)` fakes the **client** and injects it into a real store, so the code
  under test really runs — I confirmed the built layout contains the encoded directory and not the
  logical one, which is the assertion that makes the test non-vacuous.
- **Round-2 B1 is closed, counted.** **0** `npx jest tests/integration/…` commands remain; the only two
  occurrences of that string are the Global Constraint explaining the "No tests found" failure mode
  and the disposition row. **21** `npm run test:integration` commands. Every new integration file path
  matches `jest.integration.config.ts`'s `testMatch` (`tests/integration/**/*.test.ts` — including the
  `.int.test.ts` suffix), and **`tests/support/` is matched by neither config**, exactly as T6 claims —
  I read both configs. `package.json:9` and `:18` are the two scripts the plan cites, verbatim.
- **Round-2 H2 is closed:** `npx tsc --noEmit` appears in **every one of the 16 tasks'** verification.
- **Round-2 M6 / X-M2 is closed:** **0** `|| echo` occurrences are commands — all six are prose
  describing the defect. Round-2 H3 is closed: **0** `.shipped` assertions remain (both occurrences are
  narrative). Round-1 C-B1: **0** `npx vitest`, and the one `vi.fn(` is a disposition-table cell.
- **Round-1 H3 → round-2 B2 is FIXED IN CODE, not in prose.** T8 Step 3's guard sits between `:453` and
  `:454`, above `decideCompanion`, and reads `receiverModel` — the tri-state read honestly at
  `:451-453`. I verified every quote: `CompanionAction` at `companion.ts:25-28` and `ModelRead` at
  `:12-15` are verbatim; `decideCompanion(args: { winnerMdHash; senderModel; receiverModel })` is
  `:98-102`; and `provablyStale` at `:151-153` really is the branch that returns
  `deleteReceiverModel`. Because `receiverMatch` already returned at `:129`, a receiver `sourceMdHash`
  that is *present* is necessarily *different* by `:151` — so the plan's description of the fixture
  ("present and different is exactly what `decideCompanion` calls `provablyStale` and DELETES") is
  accurate, and placing the guard above `decideCompanion` genuinely covers ship, noop **and** delete.
- **Round-1 H4 → round-2 H5 is FIXED IN CODE.** T12 Step 4(b) derives the report entry from
  `cv.summaryMd`, adds **no** `rec.action` branch, and 26d2 asserts run 1 **and** run 2. I checked the
  scope: `cv` is declared at `sync-run.ts:613` (`let cv = await readVideo(...)`), the insertion point
  `:614` is inside the per-video `try` opened at `:611`, and `cv?.summaryMd` handles the null. The
  claim that control then falls through to Class A so `copyToLocal` hydrates the paid artifact is
  correct.
- **T12's insertion point is real and everything it needs is in scope.** `reconcile-serial.ts:214-216`
  is the `unsupported-artifacts` refusal, `:218` is the backlog-#17 probe, and `:220-223` is the
  comment the plan quotes to justify the placement — it says, verbatim, *"after every in-memory refusal
  above (which cost nothing …) and BEFORE the copy phase"*. `localVideo` (`:175`), `oldBase` (`:185`)
  and `newBase` (`:186`) are all in scope. **Counted** at `:69-81`: **2** `ok` variants and **10**
  refusal variants, so *"the ten existing refusal variants"* is right. The `origin` derivation matches
  the truthiness ternary at `:152-154` exactly. Round-1 M6 / round-2 M3 / Codex H1 are closed.
- **T11's insertion point is real.** `sync-run.ts:624` is `const from: Side = presentIsLocal ? …`,
  `:626` is `readMdBody`, and `presentIsLocal` (`:620`) and `present` (`:619`) are both in scope.
  `report.created += 1` is at `:633` and `writeVideoBaseline` at `:634` — **both after** the insertion
  point, so 26's `expect(report.created).toBe(0)` and 26b's "identical, forever" are properties the
  code actually has, not assumptions. Round-2 H4 is closed: T9 and T11 now assert `report.errors`, and
  the plan states why `.rejects` is unsatisfiable (`:812-814`, verified) *and* why the obvious fix is
  dangerous.
- **T13 Step 3's Class-A guard closes round-2 Codex B5 rather than accepting it.** The non-owned branch
  is `promoteIfAbsent` + read-back classify, so there is no probe-then-write window. `tryGet` is on the
  **`BlobStore` interface** (`blob-store.ts:56`, required not optional), so `loser.blob.tryGet` and
  `toBlob.tryGet` type-check. Both call sites are verified verbatim including which record is the
  loser's: `:782` is `transferClassA(localSide, cloudSide, lv, id)` → add `cv`; `:793` is
  `(cloudSide, localSide, cv, id)` → add `lv`. Round-2 L6 (orphaned staging tree) is closed **by a
  better route than I suggested** — `promoteIfAbsent`'s `finally` removes the whole tree on every
  adapter, which I confirmed by execution.
- **T7's rollout count is EXACT this time, and every per-file number with it.** Counted by walking every
  non-`node_modules` `.ts`/`.tsx`, matching `writeModelEnvelope(`/`writeModelEnvelopeWithin(`, skipping
  comment and import lines, subtracting the two declarations: **42 total, 3 production, 39 test,
  11 files** — and `rerender.test.ts` 14, `model-store.test.ts` 8, `serve-doc-materialize.test.ts` 5,
  `share-route.test.ts` 4, `model-store-cloud.test.ts` 4, `html-download.test.ts` 2,
  `pdf-cloud.test.ts` 1, `e2e/cloud.setup.ts` 1. Every one matches. Round-1 L1 and round-2 L1 are
  closed, and this is the first time the number was counted rather than recalled. The three production
  `videoId` sources are all real: `runHtmlDoc`'s first parameter (`generate.ts:11-12`),
  `resolveMagazineModel`'s `videoId` (`serve-doc.ts:48`, destructured `:70`), and `winnerVideo.id`.
- **T6 Step 6's implementer table is exact.** **Counted 7** — 6 `implements BlobStore` classes plus
  1 `BlobStore`-typed object literal — and all seven `file:line` citations are correct to the line.
  `promote` is at `blob-store.ts:73`, where the plan says to add the new method.
- **Every multi-line verbatim quote block I opened is verbatim and correctly located**:
  `supabase-blob-store.ts:15-18`, `:22-25`, `:109-127`, `:129-138`, `:140-146`, `:151`;
  `blob-store.ts:5`, `:73`, `:87`, `:103`, `:156`; `local-blob-store.ts:1`, `:12`, `:53`, `:58`, `:66`;
  `in-memory-blob-store.ts:41`, `:43`, `:45`, `:60`, `:152`, `:157`, `:170`, `:181`;
  `slugify.ts` (all 7 lines); `share/serve.ts:44-48`; `model-store.ts:15-37` (six fields, the
  `.strict()` note at `:25-26`, `serialize` at `:34-37`); `supabase-metadata-store.ts:19-22` and its
  three call sites `:119`, `:143`, `:160`; `summary-handler.ts:95-98`; `companion.ts:12-15`, `:25-28`,
  `:98-102`, `:151-153`; `sync-run.ts:40`, `:51`, `:62`, `:80`, `:221`, `:260-270`, `:371-373`,
  `:381-395`, `:441-446`, `:451-455`, `:464`, `:475`, `:547`, `:614`, `:621`, `:624-627`, `:739-757`,
  `:782`, `:793`, `:801-805`, `:812-814`; `reconcile-serial.ts:61-64`, `:69-81`, `:147-156`, `:166-174`,
  `:184`, `:214-216`, `:218`; `blob-store-list.test.ts:34-37` (round 2 cited `:35-38`; v3 corrected it).
- **Round-2 M8 / C-L4 is closed by retargeting, and the reason is real.**
  `tests/integration/share-serve.test.ts` has **0** `jest.mock` calls, imports `getShareServeContext`
  directly at `:5`, and carries `seedDoc` (`:11`) and `mintDirect` (`:17`).
  `tests/integration/share-route.test.ts` — the file v2 targeted — has **4**.
- **T10 and T14's driver citations are accurate.** `summary-handler.test.ts:24-31` is exactly the
  `jest.mock` + post-mock-import pattern; `seedPlaylist` `:37`, `mockCtx` `:46`, `makePayload` `:72`,
  `makeJob` `:85` are all inside the cited `:36-95`; `:104` is the happy-path test that drives the
  handler. `makeSummaryHandler` is `:50` and `MAX_DURATION_SECONDS` `:27`, so *"the only exports"* is
  right. `NonRetryableError` is imported at `:4`, so T10's choice of class needs no new import.
- **Money safety across a half-executed plan still holds, and I re-checked it against v3's changes.**
  T4's five flips are all **widenings**, so no key that serves today stops serving. T5's guard applies
  the same widened predicate at a point the serve path already 409'd. T9's seam is scoped to
  `status === 'promoted'` (the X-M1 decision) so it cannot refuse a non-advertising repair state.
  T10 refuses between `reserveVideoSlot` and the Gemini call — costing a serial, never money. T11
  refuses above both `readMdBody` (`:626`) and `ensureReceiverSlot`'s durable insert. T12 **skips**
  rather than relocating when both bases are unservable, which is precisely what stops paid blobs being
  copied before the seam refuses the row. T13 refuses before `put` in both branches.
  **A plan stopped after any task N cannot double-charge, and cannot lose a paid artifact.** The worst
  residual is an orphan blob at an unservable key, which T9's 26c4 names and accepts explicitly.
- **Step numbering is clean:** every one of the 16 tasks numbers its steps 1..N with no gap or
  duplicate. The File Structure table has a row for every file any task creates or modifies, including
  all three of Task 0's — round-2 L5 is closed. Round-2 L3 is closed: the header says
  *"Jest 30 via `next/jest` (SWC)"*, and the reason it matters is a Global Constraint. Round-2 L4 is
  closed: T7 Step 3's comment now says a field is being **added**, why it is `.optional()`, and why
  `.strict()` already being off makes it safe.

---

## The three DEFERRED items — verdict

Asked implicitly by the brief, since round 2's closing line was that a DEFERRED row was more reliable
than a FIXED one.

| Item | Verdict |
|---|---|
| **The Supabase `promoteIfAbsent` adapter is the one unexecuted snippet** | **Genuine, and correctly mitigated.** Its risky half — *"HTTP 409 means the object exists"* — is genuinely gone, replaced by re-reading the final. I verified that `promote()` at `supabase-blob-store.ts:109-127` really does ship that exact recovery, so the new method copies a pattern already in production rather than inventing one. `tryGet` (`:63`), `exists` (`:78-80`) and `deletePrefix` (`:129`) all exist. Honestly flagged in the header table, in Step 4, and in the DEFERRED table. |
| **T10's fixture may be unreachable** | **Genuine, and I measured it: it IS unreachable** (M1). Written down rather than hidden, with a stated fallback. The only residue is Step 4's contradictory "Expected: PASS". |
| **T12 behavior 26d3's fixture may not be constructible** | **Genuine.** The table gives the intended shape, an explicit fallback (introduce unservability by character rather than by length) and the instruction to record which was used, and correctly notes that the assertion under test is `origin === 'cloud-key'` and both shapes reach it. |

**No omission is dressed as a deferral, and this round the FIXED rows are overwhelmingly real** — I
verified 26 of them, 8 by execution. The three that overstate are C-L3/M7 (H1, M3), R2-H6 (M2), and
they overstate by *scope*, not by direction: the fix exists and is incomplete, rather than existing
only in a comment. That is the specific failure round 2 named, and it did not recur.

---

## Executable-blockers vs would-be-nice

The brief asks for this explicitly.

**Executable-blockers: none.** No step loses, orphans, strands or double-charges a paid artifact. No
step is both unexecutable *and* undisclosed. Every task's implementation snippet — the code that ships —
is either executed or a verified quote.

**Fix before dispatching the task it belongs to** (each is minutes, none blocks starting the plan):
H1 before T8, M1+M2 before T10, M3+M4 before T13.

**Would-be-nice:** all six Lows. L1's `seedVideo:378` is the only one worth doing eagerly, because 82
lines is far enough to land a reader in the wrong function.

---

## Verdict

v3 is a different kind of document from v1 and v2. The decomposition, ordering, interfaces and behavior
mapping have now been confirmed by two reviewers across three rounds and were never in question. What
was in question was whether the code in the snippets was real — and the answer this round is that it
is. I re-ran seven independent executable claims and every one held; three reproduced the plan's own
figures exactly (3,479,131 iterations; 12 Bidi_Control code points; exactly 5 flips, and exactly the
five named). Two I ran against the repo's real adapters rather than a transcription and they passed
12/12 and 8/8. The instrument that round 2 found aimed at nothing now exits 0 against the real spec and
fails loudly four different ways. The count that was wrong twice is now exact to the file.

The residue is scaffolding in test bodies for two tasks, and it fails at `tsc` rather than in
production. Withholding convergence for that, on a plan that fixes a live bug destroying paid
summaries, would be the failure the brief warns about.

CONVERGED

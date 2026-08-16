# Adversarial review: cloud blob key encoding plan v2

## BLOCKING

### B1 — integration tasks still use the unit Jest runner. Tasks 2, 5, 8, 9, 10, 11, 13, 14.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:9` says integration runs under `jest.integration.config.ts --runInBand`.
- But the task commands still say bare `npx jest tests/integration/...`: lines 453, 707, 723, 975, 1018, 1076, 1116, 1153, 1173, 1227, 1252, 1432, 1643.

Code evidence:

- `package.json:9` defines `"test": "jest"`.
- `package.json:18` defines `"test:integration": "jest --config jest.integration.config.ts --runInBand"`.
- `jest.config.ts:11-17` matches only `tests/lib/**`, `tests/api/**`, `tests/scripts/**`, `tests/smoke.test.ts`, and `tests/components/**/*.test.tsx`.
- `jest.integration.config.ts:8-10` loads the integration setup and matches `tests/integration/**/*.test.ts`.

Failure scenario: an engineer follows Task 10 literally and runs `npx jest tests/integration/summary-handler-guard.test.ts`. Jest uses `jest.config.ts`, does not load `tests/integration/setup.ts`, does not apply `globalSetup`, and does not match the file. The red/green step is not executed against local Supabase at all.

Proposed fix: replace every `npx jest tests/integration/...` command with `npm run test:integration -- <pattern-or-path>`. Commit gates that changed integration behavior should run at least `npm test && npm run test:integration && npx tsc --noEmit`, with the local-Supabase localhost assertion retained in the tests.

### B2 — T8 uses `decision.receiverEnvelope`, a field `decideCompanion` does not return. Task 8.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:990` says `const envelope = decision.receiverEnvelope`.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:939` says `companionTransfer` produces no new exports and keeps its existing contract.
- The same test block expects a `shipped` property at lines 957, 963, and 1011, but the stated return contract remains `shareNeedsOwnerServe` plus optional `error`.

Code evidence:

- `lib/cloud-sync/sync-run.ts:454` calls `decideCompanion({ winnerMdHash, senderModel, receiverModel })`.
- `lib/cloud-sync/companion.ts:25-28` defines `CompanionAction` as only `{ kind: 'ship'; envelope }`, `{ kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }`, or `{ kind: 'noop'; shareNeedsOwnerServe }`.
- `lib/cloud-sync/companion.ts:98-102` returns `CompanionAction`; there is no `receiverEnvelope`.

Failure scenario: implementing T8 literally makes `sync-run.ts` fail TypeScript on `decision.receiverEnvelope`. If the engineer patches around that by re-reading the receiver envelope, they reintroduce the round-1 H3 bug the plan says it fixed: `readModelEnvelope` collapses absent, corrupt, and unreadable into `null` on the Supabase path.

Proposed fix: keep the already-read `receiverModel` local in `companionTransfer` and derive the guard from it before both ship and delete branches. For example, treat `receiverModel.kind === 'envelope' ? receiverModel.envelope : receiverModel.kind` as the credential source. Either add `shipped` to the stated return type and all call sites, or remove those assertions and assert on writes/deletes.

### B3 — T6 local `promoteIfAbsent` still cannot compile. Task 6.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:801-813` uses bare `mkdirSync`, `dirname`, `linkSync`, `rmSync`, and `this.stagingRoot(ref)`.

Code evidence:

- `lib/storage/local/local-blob-store.ts:1` imports namespaces only: `import fs from 'fs'; import path from 'path'; import crypto from 'crypto';`.
- `lib/storage/local/local-blob-store.ts:51-55` creates `tempKey = _staging/${crypto.randomUUID()}/${key}` and returns `{ principal, tempKey, finalKey }`.
- `lib/storage/local/local-blob-store.ts:58-62` has `promote`, but the class has no `stagingRoot` method.

Failure scenario: an engineer types the plan snippet and `tsc` fails on every bare fs/path symbol plus `this.stagingRoot`. If they only fix imports, the staging cleanup still has no implementation, so the contract test at plan lines 758-764 cannot pass.

Proposed fix: spell the real implementation against this file: use `fs.mkdirSync`, `path.dirname`, `fs.linkSync`, and `fs.rmSync`. Derive the staging root from `ref.tempKey`, validating it has the `_staging/<uuid>/...` shape, then remove that root.

### B4 — T6 Supabase `promoteIfAbsent` recipe has no bytes to upload and omits required staging cleanup. Task 6.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:758-764` requires existing-final success and removal of the whole `_staging/` tree.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:816-818` says Supabase should use `upload()` without `upsert` and treat 409 as success, but gives no source bytes or cleanup step.

Code evidence:

- `lib/storage/blob-store.ts:5` defines `StagedRef` as `{ principal, tempKey, finalKey }`; it contains no bytes.
- `lib/storage/supabase/supabase-blob-store.ts:109-127` implements current `promote` with `move(from, to)`, not upload.
- `lib/storage/supabase/supabase-blob-store.ts:102-106` uploads the temp object, so a create-if-absent finalize must read/copy from `tempKey` or use a storage copy API.

Failure scenario: the engineer cannot call `upload(final, bytes, { upsert: false })` from `promoteIfAbsent(ref)` because `ref` has no bytes. If they use `move`, destination-exists semantics and cleanup still diverge from the contract. The shared contract fails on Supabase, or worse, leaves staged paid artifacts under `_staging/`.

Proposed fix: define the Supabase algorithm fully: copy/download the temp object, upload/copy to the final key with create-if-absent semantics, treat final-exists as success, verify or classify failures, and remove the complete `_staging/<uuid>/` tree in `finally`.

### B5 — T13's Class-A non-owned branch still races into an overwrite. Task 13.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1437-1439` requires `putStaged -> verify -> promoteIfAbsent -> read back and classify`.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1464-1477` then probes with `tryGet` and writes with `await loser.blob.put(...)`.

Code evidence:

- `lib/storage/supabase/supabase-blob-store.ts:22-24` implements `put` as `upload(..., { contentType, upsert: true })`.
- `lib/cloud-sync/sync-run.ts:381-395` currently stages, verifies, then overwrites the final with `loser.blob.put`.

Failure scenario: in the non-owned branch, `tryGet` returns absent, a concurrent worker or owner action creates the destination key, then `put(... upsert:true)` overwrites that paid artifact. The ownership guard prevents only objects present at probe time; it does not provide create-if-absent finalization.

Proposed fix: after the loser-record guard, use the additive protocol for the non-owned destination: staged bytes, `promoteIfAbsent`, then read back and classify equal/different/absent/unreadable. Keep overwrite semantics only for the branch where `canonicallyEqualName(loserVideo.summaryMd, key)` proves the loser row owns that address.

### B6 — the §4 gate script cannot pass against the approved spec as written. Task 13.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1538` searches for `~ '^[...] +$'` shape.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1556-1560` exits 2 if no SQL character class is found.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1581-1583` says that exit 2 is correct and to fix the SQL, but Task 13's Files block at lines 1389-1392 does not include modifying the spec or SQL.

Spec evidence:

- `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:289` contains the encoder regex prose, `SAFE = /^[A-Za-z0-9._-]+$/`.
- `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1805` only says "not matching `^[A-Za-z0-9._-]+$`"; there is no Postgres `~ '^[...]+$'` form for the script to find.

Failure scenario: the engineer creates the script and runs the mandated gate at plan lines 1587-1590. It exits 2 forever against the approved, closed spec. Since the plan does not authorize editing the spec/SQL in this task, behavior 20 cannot be completed literally.

Proposed fix: either add the exact §4 SQL/spec edit to Task 13's Files and steps, or change the script to parse the actual approved §4 representation. Do not leave the task with a mandatory gate that intentionally cannot reach its subject.

### B7 — several deferred L3 test bodies are still placeholders, not executable tests. Tasks 8, 11, 12.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:945-962` calls `companionTransfer(/* ... */)` with no actual arguments.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1008-1011` uses `reconcileCloudBase({ /* relocate oldBase -> newBase */ })` and `companionTransfer(/* ... */)`.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1220-1221` uses `runSync({ ... })`.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1282-1306` leaves every T12 fixture as a comment placeholder.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1691` explicitly deferred L3 to round 2.

Code evidence:

- `lib/cloud-sync/sync-run.ts:444-446` shows `companionTransfer(winner, loser, winnerMdHash, winnerVideo)`.
- `lib/cloud-sync/reconcile-serial.ts:166-174` shows `reconcileCloudBase` requires `cloud`, `cloudIndex`, `localVideo`, `cloudVideo`, and `inFlightJob`.

Failure scenario: an engineer pastes the tests and immediately gets syntax/type failures, not meaningful red tests. Task 0 does not create a `runSync` fixture builder or concrete `reconcileCloudBase` fixtures to fill these holes.

Proposed fix: replace each placeholder with concrete fixtures using existing helper shapes, or add Task 0 helpers that return fully-formed `Side`, `Video`, `SyncDeps`, and `reconcileCloudBase` inputs. The review criterion is literal execution, not intent.

## HIGH

### H1 — T12's insertion point is still ambiguous enough to route the new refusal behind an unconditional throw. Task 12.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1352-1368` says to add a `skipped-unservable` / `unservable-base` branch, but does not say it must go before the existing generic `!rec.ok` throw.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1691` deferred M6 to round 2.

Code evidence:

- `lib/cloud-sync/sync-run.ts:739-757` currently throws for every `!rec.ok`, with the generic tail at lines 754-756.

Failure scenario: placing the plan snippet after the existing block makes the `unservable-base` arm unreachable; placing only the `rec.ok && skipped-unservable` arm after it leaves the actionable repair string dead. The plan was written to fix exactly that generic message.

Proposed fix: state the insertion point: handle `rec.ok && rec.action === 'skipped-unservable'` before the `!rec.ok` block, and handle `rec.reason === 'unservable-base'` inside the existing `if (!rec.ok)` block above the generic throw.

### H2 — T4 still does not dispose the five existing rejection flips, including the two NFKC does not close. Task 4.

Plan evidence:

- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:619` says "NFKC closes that class."
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:645` says if an existing case now fails, update it because it asserted the allowlist.
- `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1691` deferred M2 to round 2.

Code evidence:

- `lib/html-doc/assert-cloud-summary-md-key.ts:14` is the current allowlist regex.
- `lib/html-doc/assert-cloud-summary-md-key.ts:16-19` throws 409 on anything outside it.

Failure scenario: the implementer flips old rejection cases without recording which are intended. The round-1 measured cases `a⁄b.md` and `a∕b.md` do not NFKC-fold to `/`, so the plan's stated completeness reason is false even if accepting them is operationally safe.

Proposed fix: add the five flipped cases and their dispositions to T4. Downgrade the claim to "NFKC closes compatibility-decomposable separator forms"; explicitly accept or reject U+2044 and U+2215 with tests.

## CHECKED WITHOUT FINDING

T2's new `list` slice arithmetic is correct for `prefix === ''` and for a prefix with no trailing slash, assuming T1's `encodeSegment('') === ''` from plan lines 191-193 and 264-266. For `dig/base`, `norm` becomes `dig/base/`, `collectObjectPaths` returns paths below `ownerRoot + dig/base`, and slicing by `ownerRoot.length + physicalPrefix.length` starts at the leaf. For `''`, both `norm` and `physicalPrefix` are empty, so slicing by `ownerRoot.length` returns the full logical key. `deletePrefix` really does need the same physical-prefix encoding for non-empty non-ASCII prefixes; v2 names it but should still show the exact line.

T13 step 4's call-site order is correct: current `copyToCloud` calls `transferClassA(localSide, cloudSide, lv, id)` at `lib/cloud-sync/sync-run.ts:782`, so the loser record is `cv`; current `copyToLocal` calls `transferClassA(cloudSide, localSide, cv, id)` at `lib/cloud-sync/sync-run.ts:793`, so the loser record is `lv`.

NOT CONVERGED

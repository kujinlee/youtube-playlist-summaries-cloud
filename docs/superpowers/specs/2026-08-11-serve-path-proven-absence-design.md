# Serve path — corroborate absence before spending (backlog #34)

**Status:** draft, awaiting user approval. **Branch:** `fix/serve-path-proven-absence`.
**Origin:** M1.4 gate **B3** failed on 2026-08-11 against hosted staging with the spend authorised.
Evidence: PR #76 (*the share tolerates version skew — and B3 found a real defect*), and
[`docs/m1.4-finishup-checklist.md`](../../m1.4-finishup-checklist.md) §B3.

> **In one paragraph:** the serve path decides whether to pay for a new magazine model by asking
> storage whether the cached one is there. Supabase answers `404` both when the object is missing and
> when a permission rule hides it, so a permissions fault reads as "absent" and the owner is charged
> again for a model that already exists. The fix is to stop treating a bare `404` as proof: before
> spending, re-read a file we know we just read successfully. Because the permission rule depends only
> on the first path segment — shared by both keys — a successful control read proves the rule is
> permitting this user in this folder, which makes the `404` genuine.

---

## 1. Purpose

Stop the owner being charged a second time for a magazine model that already exists, when the model
blob could not be read for a reason that is not absence.

**In scope:** the money guard in `lib/html-doc/serve-doc.ts` (`resolveMagazineModel`).
**Out of scope:** everything in §8.

## 2. Background — the measured defect

`resolveMagazineModel` will not spend on an unprovable read. It probes with `tryGet`, which is meant to
separate "missing" from "could not read":

```ts
const probe = await blobStore.tryGet(principal, MODEL_KEY(base));
if (!probe.ok && probe.reason === 'unreadable') return { status: 'busy' };
```

`SupabaseBlobStore.tryGet` classifies on the status code — `'404'` → `absent`, anything else →
`unreadable` (`lib/storage/supabase/supabase-blob-store.ts:44-57`).

**Measured 2026-08-11, hosted staging.** The raw Storage error is byte-identical for an object that
exists behind a dropped policy and one that never existed:

```
{"message":"Object not found","name":"StorageApiError","status":400,"statusCode":"404"}
```

Row-level security makes the row invisible, so the API cannot say more. The probe therefore returns
`absent`, the guard does not fire, and the path reserves and regenerates. Measured: spend **6¢ → 12¢**,
`attempt_count` 1 → 2, a second real Gemini call, then the write failed with
`new row violates row-level security policy`.

**The repo already carries the correct idea.** `SupabaseBlobStore` declares
`readonly provesAbsence = false` (`:10`), and the sync path consults it before acting on a null
(`lib/cloud-sync/sync-run.ts:697`) — which is why gate **B2** passed. The serve path never asks.
`serve-doc.ts`'s own comment claims `tryGet` distinguishes *"5xx, timeout, RLS denial, transport
error"*; it distinguishes three of the four and misses the one it names first.

**Reachability — honest.** This needs a misconfiguration, not a bad moment: a dropped or broken
storage policy, or a folder whose first segment is not the caller. It is **not** produced by 5xx,
timeout or transport failure — those carry a non-404 status and are already classified `unreadable`,
and that is the common case. An expired session cannot produce it either: `reserve_serve_model` raises
on a null `auth.uid()` (`0012_serve_model_charge.sql:41`). Never observed in production. But when it
does occur it is global and repeating rather than a stray charge, bounded at
`magazine_est_cents` × `max_serve_attempts` = **6¢ × 5 = 30¢ per document per day**.

## 3. Two things that were considered and rejected

**A durable record that a model was written.** The obvious corroboration — "the database says a model
exists, so a 404 is a contradiction". Rejected: it is real machinery (a new table, and a new obligation
on every path that deliberately deletes a model, including the sync companion delete) against a
misconfiguration-only fault. It also introduces a fresh way to be wrong: a stale record would block
regeneration forever.

> Note for the record: backlog #34's own fix lead proposed `serve_model_charge.attempt_count >= 1` as
> that record. **It does not work.** `attempt_count` increments at *reserve* time
> (`0012_serve_model_charge.sql:63`), so it counts attempts, not successes — a failed generation
> increments it too. And the row is `unique (owner_id, doc_key, day)`, so it resets daily; a model
> written yesterday leaves no row today. The backlog entry is wrong on this point and is corrected by
> this spec.

**Probe with the `service_role` credential.** A read that bypasses RLS cannot be denied by RLS, so its
`404` would be trustworthy. Rejected: `scripts/check-service-confinement.ts:97` authorises `service.ts`
in exactly **three** entrypoints, each with a written justification, and the HTML and PDF serve routes
are not among them. This would add two more. That is a security-surface change, and the whole point of
the confinement list is that it stays short and deliberate.

## 4. Decisions

| # | Decision | Rationale |
|---|---|---|
| **D1** | **A `404` is not proof of absence. Before spending, corroborate it with a CONTROL READ.** | The status code cannot carry the distinction on this backend. Corroboration is the only honest source. |
| **D2** | **The control read is the summary markdown, with the SAME principal and the SAME store as the model probe.** Proceed to spend **only if it returns bytes**. | `objectKey` is `${p.id}/${p.indexKey}/${key}` (`supabase-blob-store.ts:17`) and the storage policy predicate is **only** `bucket_id = 'artifacts' and split_part(name,'/',1) = auth.uid()` (`0007_storage_and_rpcs.sql:14`). Both keys therefore share the entire basis on which access is granted. A successful read proves the rule permits this user in this folder, so a `404` beside it is genuine. |
| **D3** | **The corroboration lives INSIDE `resolveMagazineModel`.** No new parameter, no caller obligation, no "the caller already checked" comment. | Caller-supplied evidence can be silently removed by a later change, and the guard would go quiet rather than loud. That is precisely how this defect arose. |
| **D4** | **Skip the control read when the store proves absence** (`blobStore.provesAbsence === true`). | The property already exists and already means exactly this. Reusing it keeps ONE mechanism for one concern instead of a second, parallel notion of trustworthy absence. The local FS store returns null only on `ENOENT`, so its `absent` is already proof. |
| **D5** | **A failed control read returns `busy`** — the existing transient status — with no reserve, no Gemini call and no ledger movement. | Same status the single-flight branch already uses; maps to `503 "generating, retry shortly"`, which the client already handles. No new status, no new client work. |
| **D6** | **Control-read key = `parsed.sourceMd ?? \`${base}.md\``** — the same expression the envelope write already uses for `sourceMd`. | One formula, one place. A second hand-written key would drift, and a wrong key here fails **closed forever** (§7), so it must be the key the caller actually read. |
| **D7** | **No schema change, no migration, no new table, no new credential.** | Follows from D1–D6. Keeps the change reviewable as a money-path diff. |

## 5. The change

One block in `resolveMagazineModel`, replacing the current early return:

```ts
const probe = await blobStore.tryGet(principal, MODEL_KEY(base));
if (!probe.ok && probe.reason === 'unreadable') return { status: 'busy' };

// D1/D2 — `absent` is a CLAIM on a backend that cannot prove absence. Corroborate before spending.
if (!probe.ok && probe.reason === 'absent' && blobStore.provesAbsence !== true) {
  const control = await blobStore.tryGet(principal, parsed.sourceMd ?? `${base}.md`);
  if (!control.ok) return { status: 'busy' };   // absent OR unreadable — nothing here is trustworthy
}
```

**Cost:** one extra storage read, and only on the branch that is about to reserve money and call
Gemini. Against a ~6¢ charge and a multi-second model call, it is free.

**Why `!control.ok` and not `control.reason === 'unreadable'`:** if the markdown itself now reads as
absent, the document the caller just parsed has vanished mid-request. That is not a state in which to
spend money either.

## 6. Behaviours

| # | Case | Expected |
|---|---|---|
| **B1** | Model readable and fresh | `ok`; no probe consequence, no reserve, no Gemini *(unchanged)* |
| **B2** | Model `absent`, control read returns bytes | reserve → generate → write → `ok` *(unchanged behaviour, now justified rather than assumed)* |
| **B3** | **Model `absent`, control read `unreadable`** | **`busy`. No reserve, no Gemini call, `spend_ledger` unchanged, `attempt_count` unchanged** — the fix |
| **B4** | Model `absent`, control read also `absent` | `busy`; same reasoning (D5) |
| **B5** | Model `unreadable` (non-404) | `busy` *(unchanged)*; control read never runs |
| **B6** | Store with `provesAbsence === true` (local FS) | control read **never runs**; `absent` is trusted (D4) |
| **B7** | The control read uses the same `principal` and the same store instance as the model probe | asserted directly, not implied |
| **B8** | Money invariant across B3/B4/B5 | zero `reserve_serve_model` calls and zero `generateMagazineModel` calls |

## 7. Failure modes, stated before they are found

**Too strict is the dangerous direction here.** A control read that fails for a reason unrelated to
permissions returns `busy` on every view, so the document never generates and never heals — worse than
the bug being fixed. Two guards:

1. **D6 pins the key to the one the caller demonstrably read.** The caller parsed those exact bytes
   before calling in (`serve-summary-core.ts:100`), so a key that cannot be read is not reachable
   without a separate defect.
2. **B2 is a required test**, not an optional one. It is the assertion that the fix did not simply
   stop the app spending altogether — the trivially "correct" mutation that a
   fix-the-double-charge test alone would happily accept.

**Accepted residual:** if a permission rule is dropped in the window *between* the two reads, one
charge slips through. Single, not repeating, and it requires someone breaking the policy mid-request.
Not worth a transaction.

**Unchanged and NOT claimed fixed:** `SupabaseBlobStore.get` still collapses every failure into `null`.
This spec corroborates one decision point; it does not reform the seam.

## 8. Out of scope

- **The dig serve path.** Checked: `lib/dig/cloud/load-dig-for-serve.ts:30` reads the cached envelope
  but never regenerates and never charges, so a failed read degrades the render and costs nothing.
  Backlog #34 listed this as an open question; it is answered, not deferred.
- **`isFresh` / the owner freshness rule.** Refusing an envelope there triggers a paid regeneration, so
  tightening it is a money change with the opposite sign. Its own slice.
- **The share path.** Never charges (spec 1F-b B18b), so it has no money hole to close.
- **Reforming `BlobStore.get`'s null-collapsing** — see §7.

## 9. Testing

**Unit / integration, with a fault-injecting store** — the pattern already exists in
`tests/integration/serve-model-unreadable.test.ts` (`UnreadableModelBlobStore`).

- **B3** — store where the model key returns `{ok:false, reason:'absent'}` and the markdown key returns
  `{ok:false, reason:'unreadable'}`. Assert `busy`, zero Gemini calls, `spend_ledger` unchanged,
  `attempt_count` unchanged.
- **B2** — model `absent`, markdown readable. Assert the charge **does** happen. Guards the too-strict
  direction (§7).
- **B4**, **B5**, **B6** — one case each.
- **B7** — assert the control read is issued with the same principal, and against the same store, as the
  model probe.

**Mutation check (required, not optional).** Revert the corroboration block and confirm **B3 fails**.
A guard nobody has watched fail is not known to be load-bearing. This project has measured that more
than once — see `docs/reviews/blob-addressing-retrospective-2026-08-09.md` and the mutation discipline
in [`docs/review-method.md`](../../review-method.md).

**No hosted infrastructure is needed for the regression tests.** The fault is injected at the store
seam, so they belong in the ordinary suite that runs in CI. This is a deliberate improvement on B3,
which could only be run by hand against a live project.

## 10. Acceptance

1. All of §6 green; the §9 mutation check verified failing.
2. `tsc` clean; unit + integration suites green; `check-service-confinement` still passes with **no new
   entry** in its allowlist (D7 — if this needs an exception, the design was wrong).
3. **Gate B3 re-run against hosted staging and PASSING**, recorded in
   `docs/m1.4-finishup-checklist.md` with `VERIFIED AGAINST:` the release it ran on. This closes M1.4.
4. Only then may staging project `neeufoxdbgbpkjukzzuc` be deleted.
5. Backlog #34 updated to note that its own fix lead was wrong, and why (§3) — a fix lead that survives
   as folklore is worse than none.

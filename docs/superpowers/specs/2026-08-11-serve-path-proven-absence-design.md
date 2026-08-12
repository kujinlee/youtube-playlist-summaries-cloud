# Serve path — make the absence protection enforced instead of accidental (backlog #34)

**Status:** draft v2, awaiting user approval. **Branch:** `fix/serve-path-proven-absence`.
**Origin:** M1.4 gate **B3**, 2026-08-11. Evidence: PR #76 and
[`docs/m1.4-finishup-checklist.md`](../../m1.4-finishup-checklist.md) §B3.

> **v1 of this spec was written against a premise that is false, and v2 exists because the adversarial
> review's cost objection sent me back to the caller.** v1 proposed adding a corroborating "control
> read" before spending. That protection **already exists**, one stage upstream, and the real defect is
> that nothing enforces or documents it. See §2.

> **In one paragraph:** `resolveMagazineModel` decides whether to pay for a magazine model by asking
> storage whether the cached one is there. Supabase answers `404` both when the object is missing and
> when a permission rule hides it, so that answer is not proof. It is nevertheless *safe today*, because
> the only caller has already read the summary markdown from the same folder with the same credential
> and bails out if that fails — which means a permissions fault can never reach the charging code. That
> protection is **accidental**: it is an ordering property no signature requires, no test pins, and no
> comment mentions, while a comment in the blob store asserts the opposite. This slice makes it
> enforced.

---

## 1. Purpose

Prevent a future caller from reaching the serve path's charging code without the upstream read that
makes its absence check trustworthy — and delete a comment that currently tells the next editor the
opposite of the truth.

**Not** a user-facing bug fix. Nothing is broken for users today (§2).

## 2. What gate B3 actually measured, and what it did not

**Measured, hosted staging, 2026-08-11.** With the owner storage policy dropped, calling
`resolveMagazineModel` directly produced spend **6¢ → 12¢**, `attempt_count` 1 → 2, and a second real
Gemini call for a model already in the bucket. The mechanism is real: Supabase returns a 404-shaped
error for a *denied* read, byte-identical to a *missing* object —

```
{"message":"Object not found","name":"StorageApiError","status":400,"statusCode":"404"}
```

— so `tryGet` classifies the denial as `absent` (`lib/storage/supabase/supabase-blob-store.ts:44-57`)
and the money guard does not fire.

**NOT reachable through the application.** `resolveMagazineModel` has exactly one production caller,
`resolveAndParse`, and it runs only after `loadSummaryForServe`, which reads the summary markdown with
the *session-scoped, RLS-enforced* store and **fails closed**:

```ts
const mdBytes = await bundle.blobStore.get(principal, mdKey);
if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' };
```
`lib/html-doc/serve-summary-core.ts:66-67`

A broken policy therefore breaks *that* read first and the request ends at **409 "repair needed"**
before any reserve. Both keys live under `${p.id}/${p.indexKey}/…`
(`supabase-blob-store.ts:17`) and the storage policy grants on the first segment alone
(`0007_storage_and_rpcs.sql:14`), so there is no policy state that hides the model while revealing the
markdown.

**The B3 harness bypassed that.** It read the markdown with the `service_role` client in order to
isolate the model read, and so constructed a state — markdown readable, model denied — that the
application cannot be in. **The charge was real; the scenario was manufactured.** Recorded here rather
than quietly dropped, because the checklist and backlog both currently describe it as a live
double-charge.

## 3. What is actually wrong

**(a) A comment asserts the opposite of the measurement.** `supabase-blob-store.ts:39-43`:

> *"Supabase reports a missing object as a StorageApiError carrying `statusCode: "404"` … so a 404 **IS
> provable absence**. Everything else — 5xx, timeout, **RLS denial**, a thrown network error — is
> `unreadable`."*

It quotes the exact error string measured in B3 and draws the wrong conclusion, because it was verified
against a *missing* object and never against a *denied* one. It also names RLS denial as producing
something other than 404, which is the specific case that is false. A money-path editor reading this
would conclude the classification is trustworthy on its own.

**(b) The protection is unenforced and unwritten.** That `resolveMagazineModel` is safe *only because*
its caller already proved the folder is readable appears in no signature, no comment and no test. The
parameter carrying those very bytes, `mdBody`, is **optional** —
*"Optional for back-compat with callers that pre-date this signal"* (`serve-doc.ts:56-59`) — so a new
caller (another route, a background warm path, a batch job) can reach the charging code with no
upstream read at all, and nothing would fail.

## 4. Decisions

| # | Decision | Rationale |
|---|---|---|
| **D1** | **Correct the blob-store comment** to state that a 404 is returned for BOTH a missing object and an RLS-denied one, quoting both measurements, and that `absent` is therefore **not** proof of absence on this backend. | The comment is the primary interface to this distinction; it currently teaches the opposite. |
| **D2** | **`mdBody` becomes REQUIRED**, and is documented as the money-path precondition: the caller must have successfully read the summary markdown for this document, through **this** store with **this** principal. | Turns an ordering property into a signature obligation. A caller that has not done the read cannot satisfy it without lying, and cannot omit it silently — omission becomes a type error. |
| **D3** | **Pin the upstream short-circuit with a test**: markdown unreadable → `409`, and **zero** reserve calls, zero Gemini calls, `spend_ledger` unchanged. | This is the assertion that actually protects the money. If a later change makes `loadSummaryForServe` tolerate an unreadable markdown, this fails loudly instead of the charge reappearing. |
| **D4** | **No control read, no new table, no new credential, no schema change.** | v1 proposed a control read. It would duplicate a check the caller already performs, cost a full extra download on every first serve of every document (adversarial review, High-2), and add an unbounded read with no timeout to a path whose too-strict failure mode is a document that never generates. |
| **D5** | **Do not "fix" `tryGet`'s classification.** | It is correct for what it can observe. The API cannot distinguish the two cases; pretending otherwise inside the adapter would move the lie rather than remove it. |
| **D6** | **Correct the record in `docs/backlog.md` #34 and `docs/m1.4-finishup-checklist.md` §B3** rather than leaving them describing a live double-charge. | Both currently overstate the defect. A backlog entry that overstates a money bug distorts every future priority call made against it. |

## 5. The change

Four edits, no behaviour change on any reachable path:

1. `lib/storage/supabase/supabase-blob-store.ts` — replace the false comment (D1).
2. `lib/html-doc/serve-doc.ts` — `mdBody: string` (was `mdBody?: string`), with the precondition
   documented at the parameter and restated at the money guard (D2).
3. Update the direct callers that omit it — production already supplies it
   (`serve-summary-core.ts:105`); the affected sites are integration tests.
4. Tests per §6.

## 6. Behaviours

| # | Case | Expected |
|---|---|---|
| **B1** | Summary markdown unreadable (policy denied / transient) | `409 "repair needed"`; **zero** `reserve_serve_model`, **zero** Gemini calls, `spend_ledger` unchanged — the money-protecting assertion (D3) |
| **B2** | Markdown readable, model cached and fresh | `ok`, no reserve, no Gemini *(unchanged)* |
| **B3** | Markdown readable, model genuinely absent | reserve → generate → write → `ok` *(unchanged — the app must still be able to make a model)* |
| **B4** | Model read fails as `unreadable` (non-404) | `busy`, no reserve, no Gemini *(unchanged, already covered by `serve-model-unreadable.test.ts`)* |
| **B5** | A caller omits `mdBody` | **does not compile** (D2) |

## 7. What this does NOT claim

- **It does not make `absent` provable.** It records that it is not, and relies on the upstream read —
  now a stated precondition — for safety.
- **It does not defend a caller that passes an `mdBody` it never read.** A required parameter defends
  omission, never a wrong value of the right shape. B1 is what pins the real behaviour; D2 makes the
  contract explicit so that lying requires intent rather than inattention.
- **It does not address a hypothetical narrower storage policy** (adversarial review, High-1: a policy
  granting `*.md` but not the model key). No such policy exists — the only one grants on the first path
  segment (`0007_storage_and_rpcs.sql:14`) — and under D2 the charge path would be reachable in that
  world. Recorded as a known assumption, not fixed here: making it a checked invariant belongs with the
  schema gates, and is filed as a follow-up rather than smuggled into a money diff.

## 8. Out of scope

- **The dig serve path** — verified twice (by hand and by the review): `load-dig-for-serve.ts:30` reads
  the cached envelope but never regenerates and never charges. A failed read degrades the render only.
- **The share path** — never charges (1F-b B18b), verified in the review against `app/s/[token]/route.ts`.
- **`isFresh` / owner freshness** — tightening it triggers *paid* regeneration; opposite sign, own slice.
- **`BlobStore.get`'s null-collapsing** — unchanged and not claimed fixed.

## 9. Testing

- **B1 is the new test and the point of the slice.** Drive `loadSummaryForServe` (or the route) with a
  store whose markdown read fails, and assert `409` plus zero reserve / zero Gemini / unchanged
  `spend_ledger`. Use the existing fault-injection pattern from
  `tests/integration/serve-model-unreadable.test.ts`.
- **Mutation check (required).** Make `loadSummaryForServe` tolerate a null `mdBytes` and confirm **B1
  fails**. A guard nobody has watched fail is not known to be load-bearing — see
  [`docs/review-method.md`](../../review-method.md).
- **B5** is `tsc`, not a runtime test: removing `mdBody` from a call site must fail the build.
- **B3 must stay green** — the too-strict direction. The app must still be able to generate a model.
- Existing suites must pass unchanged; no reachable behaviour changes.

## 10. Acceptance

1. §6 green; the §9 mutation check verified failing; `tsc` clean; unit + integration suites green.
2. `check-service-confinement` unchanged and passing, with **no new allowlist entry**.
3. **Backlog #34 and checklist §B3 corrected** to describe what was actually measured — a real
   classification defect, reached by a harness that bypassed the application's own short-circuit — and
   no longer to describe a live double-charge (D6).
4. **Gate B3 is re-stated, not re-run as-is.** Its money clause tested a state the app cannot enter. The
   replacement is B1 above, which runs in CI on every change instead of by hand against live infra.
5. Staging project `neeufoxdbgbpkjukzzuc` may then be **deleted** — nothing outstanding needs it.

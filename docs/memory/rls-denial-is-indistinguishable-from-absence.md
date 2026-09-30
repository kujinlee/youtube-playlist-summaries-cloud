---
name: rls-denial-is-indistinguishable-from-absence
description: "FIRES-WHEN: writing a guard that distinguishes missing from denied on Supabase Storage — Supabase Storage returns an identical 404 for \\\"denied by RLS\\\" and \\\"genuinely missing\\\", so any guard discriminating on statusCode cannot see the difference — measured by B3 on 2026-08-11"
metadata: 
  node_type: memory
  type: project
  originSessionId: 44563227-eadb-43b6-9b7a-a92b0c8e93e9
  modified: 2026-08-12T01:02:05.036Z
---

**Measured 2026-08-11** (M1.4 item B3, hosted staging). The raw Storage error is **byte-identical**
for an object that exists but whose owner policy was dropped, and one that never existed:

```
{"message":"Object not found","name":"StorageApiError","status":400,"statusCode":"404"}
```

RLS makes the row invisible, so the API honestly reports 404. Therefore `SupabaseBlobStore.tryGet`,
which discriminates on `statusCode === '404'`, classifies an **RLS denial as `absent`**.

**⚠ CORRECTED 2026-08-11 — NOT a live double-charge.** The mechanism above is real and the 6¢ → 12¢
was measured, but the scenario was manufactured. `resolveMagazineModel`'s only caller goes through
`loadSummaryForServe`, which reads the summary markdown with the SAME store and principal and fails
closed at `409 "repair needed"` (`lib/html-doc/serve-summary-core.ts:66-67`). Both keys sit under
`${id}/${indexKey}/` and the policy grants on segment 1 alone, so a permissions fault kills the
markdown read FIRST. My B3 harness read the markdown with `service_role` to isolate the model read,
constructing a state the app cannot enter. **I reported a live money bug without asking what caller
reaches that state** — the exact check recorded in [[quote-the-code-dont-characterise-it]].

**What was genuinely wrong, and was fixed:** the blob store's comment asserted a 404 "IS provable
absence" and listed RLS denial as producing something else (both false — and it quoted the very error
string that disproves it, having been verified against a *missing* object only); and the protection was
ACCIDENTAL — `mdBody` was optional, so a new caller could reach the charging code with no upstream read.
`mdBody` is now required and `tests/integration/serve-md-unreadable-no-charge.test.ts` pins the
short-circuit, mutation-verified.

**The shape worth remembering:** the repo *already knew*. `SupabaseBlobStore` declares
`readonly provesAbsence = false`, and the **sync** path consults it (`lib/cloud-sync/sync-run.ts:697`)
— which is the actual reason B2 passed. The **serve** path never asks. One backend property, two
consumers, only one of them reading it. Same family as [[one-rule-one-place]].

Also: `serve-doc.ts`'s own comment claims `tryGet` distinguishes *"5xx, timeout, RLS denial, transport
error"*. It distinguishes three of the four and **misses the one it names first** — a comment
asserting coverage nobody measured. See [[quote-the-code-dont-characterise-it]].

**Scope, stated honestly:** only the RLS-denial class was exercised. A real 5xx/timeout carries a
non-404 status and *would* pass. The guard is **narrower than its comment claims**, not useless.

**Fix lead:** `serve_model_charge.attempt_count >= 1` already records that a model was successfully
written for that `doc_key`, so a later *absent* read there is corroborated-suspicious.

Repro harness: `scratchpad/b3-serve.ts` (phases 0–3) + `scratchpad/b3-raw.ts` (gitignored), staging
project `neeufoxdbgbpkjukzzuc` — **do not delete it until B3 re-runs green**
([[staging-supabase-project]]).

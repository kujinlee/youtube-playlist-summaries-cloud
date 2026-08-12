---
status: accepted
---

# The serve path's money guard is corroboration-by-ordering, and it depends on the storage grant staying coarse

Serving a summary may need to (re)generate the **magazine model**, which reserves against the daily cap
and makes a live Gemini call. The decision to spend rests on one question — *is the cached model already
there?* — and on Supabase that question **has no trustworthy answer**: an object hidden by row-level
security returns a 404 byte-identical to one that never existed. `SupabaseBlobStore` therefore declares
`provesAbsence = false`, and `tryGet → absent` means only *"404-shaped"*, i.e. **absent OR denied**.

**The decision: corroborate that unprovable absence by ORDERING, not by a second permission probe.**
The only caller reaches the charging code through `loadSummaryForServe`, which first reads this
document's summary markdown — same store, same principal, same folder — and **fails closed at
`409 "repair needed"`** when that read comes back empty (`lib/html-doc/serve-summary-core.ts:66-67`).
A permissions fault therefore ends the request before any reserve.

**That inference is only valid because the storage grant is coarser than a single object.**
`supabase/migrations/0007_storage_and_rpcs.sql:12-15` grants on the first path segment:

```sql
using (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text)
```

The markdown and the model both live under `<owner-id>/<index-key>/`, so **one grant covers both** and a
policy that reveals the markdown while hiding the model cannot exist. Reading the markdown successfully
is thus evidence about the model's readability. **Narrow that grant and the evidence evaporates.**

## Why this needs recording

`ADR-0005` exists because the `Dockerfile` looked *wrong* without it — a missing ffmpeg read as an
oversight, so a reviewer went looking for the reason. **This is the inverse, which is the more dangerous
direction: the migration looks completely fine.** Nobody goes hunting for an ADR when the code reads
correctly, and the change that would break this is a change that looks like *better* security.

Measured 2026-08-12, while generating an `explain-diff` explainer for PR #78:

- grepping `supabase/migrations/0007_storage_and_rpcs.sql` for *serve* / *money* / *charge* / *reserve*
  returns only the words **"preserves"** and **"preserved"**;
- `split_part` appears in **that migration and no other**;
- the dependency is recorded solely in a comment inside `lib/html-doc/serve-doc.ts`, which a migration
  author has no reason to open.

## What was rejected

**An explicit "can I read this folder?" probe immediately before the reserve.** Rejected because the
caller has *already* performed exactly that read: a probe would be a second mechanism for a concern the
existing read already serves — the duplicate-mechanism shape this project has paid for before — plus a
storage round-trip on every serve. The cost of the rejection is that the guarantee lives in an
**ordering** rather than in a local check, which is precisely why it needs an ADR.

## Consequence — the thing that must not change silently

> **If the `artifacts` storage grant is ever narrowed below owner-folder granularity** — per playlist,
> per object, membership-scoped, anything where reading the markdown no longer implies the model is
> readable — **the serve path's money guard must be replaced with an explicit permission probe in the
> same change.** Otherwise `resolveMagazineModel` reserves and regenerates a model already in the
> bucket: measured **6¢ → 12¢**, `attempt_count` 1 → 2, a second live Gemini call, with every test green.

Two further properties this rests on, both true today and both worth re-checking if they change:

- **One production caller.** `grep "resolveMagazineModel({"` over `lib/ app/ worker/` returns exactly
  one non-test invocation, `lib/html-doc/serve-summary-core.ts:105`. A second caller that reaches the
  reserve without the upstream read reintroduces the hole. `mdBody` was made **required** by PR #78 so
  that omission is a compile error — but a required parameter defends omission, never a wrong value of
  the right shape.
- **The upstream read fails closed.** `serve-summary-core.ts:67` returns 409 on an empty read. Making
  that tolerant re-opens the charge. `tests/integration/serve-md-unreadable-no-charge.test.ts` pins it
  and states so in its header.

## Anchoring — and where it is still missing

`lib/html-doc/serve-doc.ts` and `lib/storage/supabase/supabase-blob-store.ts` reference this ADR at the
code that looks wrong without it.

**The migration is not annotated. It is PINNED instead** — `scripts/check-storage-grant-pin.py`, run in
CI, fails when the `artifacts_owner_rw` statement changes and names this ADR in the failure message.

That was backlog #35, and the question it was blocked on has since been answered by measurement against
prod (2026-08-12, via the read-only `claude_ro` role):

- `supabase_migrations.schema_migrations` has **no checksum column** — it is `version : text`,
  `statements : ARRAY`, `name : text` — so editing an applied migration would break nothing;
- **but `statements` retains SQL comments.** `0007` stores 15 statements, 6 containing `--`, and the
  `artifacts_owner_rw` statement is stored *with* its leading comment block. Editing the file would make
  the repo's copy diverge from the record of what actually ran.

So editing was permissible and lossy. The deciding argument was neither: **a comment does not fail.**
Whoever narrows this grant edits the policy and its comment in one motion, and the warning leaves with
the thing it was warning about. A pin fails in their CI run, in the same PR, before it merges.

**What the pin cannot do**, stated because an unstated scope is assumed total: it detects that the
policy text changed. It cannot distinguish a widening from a narrowing, or a rename from a semantic
change — that judgement is what its failure message asks for. A reviewer who re-pins the constant
without reading this ADR defeats it entirely, and nothing prevents that.

# Plan — `InMemoryBlobStore` (architecture review finding #3)

Closes the gap named in `docs/reviews/architecture-review-2026-07-30.md` §3: **there is
no in-memory adapter**, so tests substitute at the *module* level (`jest.mock`) or with
partial fakes cast through `as unknown as`, and the seam is not the test surface.

## Why an adapter, not a mock

A fake that implements 1 of 9 methods cannot catch a caller that starts using a second
method — the test still passes. An adapter satisfying the whole interface makes that a
compile error.

## The one real design decision: `promote()` is not uniform

The review verified that the two shipped adapters disagree when **both** the staged temp
and the final key exist:

| Adapter | Code | Final ends up |
|---|---|---|
| `LocalFsBlobStore` | `fs.renameSync(from, to)` | **new** body (overwrite) |
| `SupabaseBlobStore` | `if (exists(final)) { remove(temp); return; }` | **old** body (skipped) |

`lib/cloud-sync/sync-run.ts` discovered this and worked around it *at one call site*.
An in-memory adapter that silently picked one semantic would bake the disagreement into
the test suite as a truth.

**Decision:** the adapter takes `promoteSemantics: 'overwrite' | 'create-if-absent'` and
models both. Behavior #14 below asserts the divergence explicitly, so the seam bug is
documented by a test instead of a comment.

Same reasoning for `provesAbsence` (local `true`, Supabase `false`) — it drives whether a
failed read throws or collapses to `null`, which is the defect class behind the live
6¢→12¢ double-charge cited in `blob-store.ts`.

## Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Stores bytes | `put(p,k,b,ct)` then `get(p,k)` | same bytes |
| 2 | Overwrites | `put` twice on one key | second body wins |
| 3 | Absent read | `get(p, missing)` | `null` |
| 4 | `tryGet` present | key exists | `{ok:true, bytes}` |
| 5 | `tryGet` absent | key missing | `{ok:false, reason:'absent'}` |
| 6 | `tryGet` unreadable | key marked faulted | `{ok:false, reason:'unreadable', cause}` |
| 7 | Faulted `get`, proves-absence adapter | faulted key, `provesAbsence:true` | **throws** (local rethrows non-ENOENT) |
| 8 | Faulted `get`, non-proving adapter | faulted key, `provesAbsence:false` | `null` (Supabase swallows) |
| 9 | `exists` | present / absent | `true` / `false` |
| 10 | Delete | `delete` then `get` | `null` |
| 11 | Delete absent | `delete(p, missing)` | resolves, no throw |
| 12 | `putStaged` does not publish | `putStaged` | temp readable, **final still absent** |
| 13 | `promote` publishes | `putStaged` → `promote` | final has bytes, temp gone |
| 14 | **`promote` divergence** | temp **and** final both exist | `overwrite` → final = new body; `create-if-absent` → final = **old** body. Temp removed in both. |
| 15 | `promote` idempotent | temp absent, final present | no-op, no throw |
| 16 | `list` under prefix | keys written under `dig/x/` | those keys, owner-root-relative |
| 17 | `list` absent prefix | no such prefix | `[]` |
| 18 | `list('')` | any keys | all of the principal's keys |
| 19 | `deletePrefix` | keys under prefix | all removed |
| 20 | `deletePrefix` absent | no such prefix | no-op, no throw |
| 21 | Rejects unsafe keys | leading `/`, `..` segment, `\0` | throws, `statusCode: 400` |
| 22 | Principal isolation | two principals, same logical key | each sees only its own bytes |
| 23 | Fault: `promote` fails | promote fault armed | throws (covers `FailPromoteBlobStore`) |
| 24 | Fault: `put` fails | put fault armed | throws (covers `FailModelPutBlobStore`) |

### Edge cases folded in above

- What if the input is missing/invalid? → #21 (unsafe keys), #3/#5 (absent).
- What if a read fails rather than being absent? → #6/#7/#8 — the whole reason `tryGet`
  is a required interface member.
- What if it fails mid-chain? → #12 (staged but not promoted), #23 (promote throws after
  a successful stage).

## Out of scope

- `InMemoryMetadataStore` — 13 methods, 3 of which throw `cloud-only` on the local
  adapter. Worth doing, but a separate slice; `BlobStore` is where the `as unknown as`
  fakes and the three hand-forwarding decorators actually are.
- Migrating the Supabase integration decorators that genuinely wrap a **live** store —
  they are testing Supabase behaviour, not the interface.

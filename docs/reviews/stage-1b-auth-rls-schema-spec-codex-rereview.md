# Codex Adversarial RE-REVIEW — Stage 1B Auth + RLS Schema Spec v2

**Reviewer:** Codex (frontier), fresh session
**Date:** 2026-07-02
**Target:** spec v2 (`…stage-1b-auth-rls-schema-design.md`)
**Verdict:** confirms B1/B4/H7/H8 fully resolved; 2 Blocking + 5 High + 1 Medium remain (partials + 1 new architectural finding). All addressed in v3.

## Confirmed resolved
B1 (composite FK), B4 (stage decomposition), H7 (FK-attack test), H8 (per-op mutation semantics).

## Remaining — addressed in v3
- **[Blocking] Trigger security context (was B2-partial).** `handle_new_user` must be `SECURITY DEFINER` (owned by a privileged role, `set search_path=''`) or its insert into RLS-protected `profiles` fails / aborts signup. → v3 §4: SECURITY DEFINER, `is_anonymous` from `new.is_anonymous`, failure behavior, both-provider tests.
- **[Blocking] Principal contract still contradicts (B3-partial).** `principal.ts` JSDoc still says cloud `outputFolder` unused. → **Fixed in code** (JSDoc updated to "index selector; cloud = playlist_key") + v3 references it.
- **[High] Empty `readIndex` vs schema (H3-partial).** Grounded in actual local code: `readIndex` ENOENT returns `{ playlistUrl: '', outputFolder, videos: [] }` and does **not** Zod-validate on read. → v3: cloud returns that exact shape; read does not validate (parity). Concern moot.
- **[High] `writeIndex` reordering violates `unique(playlist_id, position)` mid-txn.** → v3: make it a **deferrable initially deferred** unique constraint (not a unique index).
- **[High] CHECK permits missing `data.id`** (NULL → CHECK passes). → v3: `CHECK (data->>'id' IS NOT NULL AND data->>'id' = video_id)`.
- **[High] service_role confinement bypassable** (re-export/dynamic/transitive). → v3 §3.1: defense-in-depth — `import 'server-only'` in `service.ts` + runtime guard + transitive-import CI scan; acknowledged as layered, not a single grep.
- **[High — NEW] `MetadataStore` is synchronous; a networked adapter can't be.** → v3: adds an explicit **prerequisite for 1C** — async-ify the `MetadataStore` contract + `LocalFsMetadataStore` + ~20 consumers (Promise + await). Does not block 1B; §5.5 semantics describe the async adapter.
- **[Medium] Concurrent `upsertVideo` position race** (two inserts compute same max+1). → v3 §5.5: position allocation via `ON CONFLICT` retry / serialized-per-playlist expectation.

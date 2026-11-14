---
name: stage-1f-b-design-state
description: "FIRES-WHEN: citing Stage 1F-b (share tokens, /s/<token>), PR #8, or the share path's never-charge invariant — MERGED bb71d32, 2026-07-10"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

**Stage 1F-b is MERGED** — PR #8, merge commit `bb71d32`, 2026-07-10; branch `feat/stage-1f-b-share-tokens` deleted.
An owner mints an opaque capability link (`/s/<token>`) to ONE promoted summary doc; anyone with the link reads the
rendered HTML, no login. Nothing outstanding on this slice (1F-c also merged — [[stage-1f-c-design-state]]).

**Core invariant:** the share path **never generates or charges** — it only READS an already-materialized magazine
model ("serve-if-fresh, else not-ready"); the sole new privileged surface is a **read-only, token-gated `service_role`**
fetch of exactly one doc's blobs. Structural guarantee (D13): generate-free leaf module `lib/html-doc/read-model.ts`
(`readFreshMagazineModel` + `isFresh`, imports only readModelEnvelope + GENERATOR_VERSION, never gemini/reserve); the
share route imports only that; ESLint no-restricted-imports + B18 runtime spies enforce it.

**Key design (spec §3):** token = 256-bit random, base64url in URL, SHA-256-hashed at rest (32-byte CHECK), plaintext
shown once. Expiry owner-set at mint (default 30d, `never`, bounded 1..365), enforced in BOTH route AND definer RPC.
Revoke one + revoke-all; in-flight revoke closed by a mandatory step-5 re-check. Confused-deputy guard: resolve by
global `playlist_id AND owner_id`, assert owner match (D15). Runtime `get`-only blob wrapper (D16). Share-mode render
strips owner-structure metas. No-store + `Referrer-Policy: no-referrer`. force-RLS + service_role-only `share_tokens`;
all writes via SECURITY DEFINER RPCs (mint/revoke/revoke-all/list). The "manage links" UI shipped later in Stage 2c.

**1G follow-ups (PR #8 body + `whole-branch-1f-b.md`):** anonymous-route rate-limit / `(token_hash,generatorVersion)`
HTML cache; GENERATOR_VERSION-bump staleness heal-at-mint (recipients get no signal on stale links); orphaned token-row
GC; token-entropy-at-DB residual (owner self-harm via direct RPC weak hash); mint TTL-400-before-401 ordering and
create_share_token errors collapsing to 404 — both cosmetic.

## History
- Chosen by user 2026-07-10 over 1F-c / 1G / frontend. Spec v4 (3 dual rounds, user-approved) → plan v2 (Post-Plan
  Gate: 4 Blk/4 High fixed) → 7 SDD tasks, §8 iterative re-review on 1/2/6/7 → whole-branch READY TO MERGE. tsc clean,
  unit 1792, integration 216/218 (+2 pre-existing skips). Trail `docs/reviews/{spec,plan,task,whole-branch}-1f-b-*.md`.
- Notification setup: user enabled `agentPushNotifEnabled`+`remoteControl` 2026-07-10; alarms suppress while the
  terminal is active. See [[process-conventions]], [[stage-1f-a-design-state]].

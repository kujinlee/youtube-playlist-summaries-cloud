---
name: stage-1f-b-design-state
description: "FIRES-WHEN: resuming Stage 1F-b (share tokens) — Stage 1F-b (share tokens) design phase — current state + resume"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

Stage 1F-b = **share tokens**: an owner mints an opaque capability link (`/s/<token>`) to ONE promoted summary doc; anyone with the link reads the rendered summary HTML, no login. Branch `feat/stage-1f-b-share-tokens` (off master after 1F-a PR #7). Chosen by user 2026-07-10 over 1F-c / 1G / frontend.

**Core invariant:** the share path **never generates or charges** — it only READS an already-materialized magazine model ("serve-if-fresh, else not-ready"); the sole new privileged surface is a **read-only, token-gated `service_role`** fetch of exactly one doc's blobs. Structural guarantee (D13): a NEW generate-free leaf module `lib/html-doc/read-model.ts` (`readFreshMagazineModel` + `isFresh`, imports only readModelEnvelope + GENERATOR_VERSION, never gemini/reserve); share route imports only that; ESLint no-restricted-imports + B18 runtime spies enforce it.

**Key design (spec §3):** token = 256-bit random, base64url in URL, SHA-256-hashed at rest (32-byte CHECK), plaintext shown once. Expiry owner-set at mint (default 30d, `never`, bounded 1..365) enforced in BOTH route AND definer RPC (trust boundary). Revoke one + revoke-all; in-flight revoke closed by a mandatory step-5 re-check. Confused-deputy guard: resolve by global `playlist_id AND owner_id`, assert owner match (D15; belt-and-suspenders over the `videos(playlist_id,owner_id)` composite FK). Runtime `get`-only blob wrapper (D16). Share-mode render strips owner-structure (source-md/video-id/generator metas). No-store + `Referrer-Policy: no-referrer`. force-RLS + service_role-only `share_tokens` table; all writes via SECURITY DEFINER RPCs (mint/revoke/revoke-all/list). Backend only — the "manage links" UI is Sub-project 2.

**Phase:** ✅ **MERGED to master** — PR #8 merged 2026-07-10 (merge commit `bb71d32`); branch deleted. Spec v4 converged (3 dual rounds, user-approved) → plan v2 (Post-Plan Gate: 4 Blk/4 High fixed) → 7 SDD tasks, each dual-reviewed with §8 iterative re-review on 1/2/6/7 (negative-control-verified guards) → whole-branch review READY TO MERGE both passes → PR #8. Verification: tsc clean, unit 1792, integration 216/218 (+2 pre-existing skips). Full trail `docs/reviews/{spec,plan,task,whole-branch}-1f-b-*.md`.

**1G follow-ups (in PR #8 body + whole-branch-1f-b.md):** anonymous-route rate-limit / `(token_hash,generatorVersion)` HTML cache; GENERATOR_VERSION-bump staleness heal-at-mint (recipients get no signal on stale links); orphaned token-row GC (un-promote/anon-reap cascade); token-entropy-at-DB residual (owner-self-harm via direct RPC weak hash); mint TTL-400-before-401 ordering + create_share_token errors collapsing to 404 (masks infra errors) — both cosmetic.

**Next action:** none outstanding for 1F-b. Remaining 1F slices: 1F-c (downloads/PDF/Obsidian). Or Sub-project 2 (frontend). AFK boundary = human-in-loop through spec + merge; automate plan+impl. See [[process-conventions]], [[stage-1f-a-design-state]]. Notification setup: user enabled `agentPushNotifEnabled`+`remoteControl` 2026-07-10 (was off); alarms suppress while terminal active, fire when idle.

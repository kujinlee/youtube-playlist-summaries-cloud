---
name: stage-1f-a-design-state
description: "FIRES-WHEN: citing Stage 1F-a (authorized summary-HTML serving), PR #7, or the serve-side money path (reserve_serve_model, Option A model upsert) — MERGED 288f591, 2026-07-10"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

**Stage 1F-a is MERGED** — PR #7, merge commit `288f591`, 2026-07-10; branch `feat/stage-1f-a-authorized-doc-serving`
deleted. Authorized, blob-backed serving of the summary rendered HTML from Supabase storage (owner-scoped, any tier
incl. anon). Foundation of Stage 1F (share tokens = [[stage-1f-b-design-state]], downloads = [[stage-1f-c-design-state]]).
Nothing outstanding on this slice.

**Key design (spec §3 canonical):** worker UNCHANGED; render on-serve; magazine model materialized **lazily on view**
(version/drift-gated). Serve-side spend = **A+ lease** `SECURITY DEFINER reserve_serve_model` RPC (owner from
`auth.uid()`; verifies owned+`promoted`; generation lease single-flights Gemini; **charges `magazine_est_cents=6¢` per
attempt**; **K=5-attempt bound** per `(owner,doc,UTC-day)`; no release RPC; coarse statuses). Session/anon client
only; nonce CSP; playlistId UUID. **Cloud model persists via `writeModelEnvelope` = `put`/`upload(upsert:true)`
(Option A, overwrite-safe, self-heals on drift/version-bump) — NOT staged→promote (that stays for the worker MD path).**

**Money-path fork (user, 2026-07-09):** chose **Option A** (cloud model upsert-overwrite) over staged-promote-with-overwrite
/ defer-to-1G — the R2 re-review caught that create-if-absent promote couldn't overwrite a stale model → fleet-wide
re-charge on GENERATOR_VERSION bump. Governed by [[process-conventions]].

**1G follow-ups it raised (PR #7 body):** registered-residual = up to the WHOLE shared daily cap (a registered $0
reclaim-loop can exhaust it; anon hard-bounded 60≤100) → addressed by Stage 1G G1, see [[stage-1g-design-state]];
staging-blob GC; config-invariant quota-drift; test strengthening (uuid distinctness, route in_flight race,
full-stack E2E).

## History
- 9 SDD tasks, per-task dual gates (Claude + Codex); whole-branch READY TO MERGE; tsc clean, unit 1746, integration
  182+2 skips. Spec v8 approved (`8ca22ab`); plan `82f3aaa` (3 rounds). Trail: `docs/reviews/{spec,plan,task}-1f-a-*.md`
  + `whole-branch-1f-a.md`.
- This merge superseded "next is frontend" in [[stage-1d-merged-followups]].

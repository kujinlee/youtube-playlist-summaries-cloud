---
name: stage-1f-a-design-state
description: "FIRES-WHEN: resuming Stage 1F-a (authorized summary-HTML serving) — Stage 1F-a (authorized summary-HTML serving) design phase — current state + resume"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

Stage 1F-a = authorized, blob-backed serving of the **summary rendered HTML doc** from Supabase storage (owner-scoped, any tier incl. anon), on branch `feat/stage-1f-a-authorized-doc-serving`. Foundation slice of Stage 1F (share tokens = 1F-b, downloads/PDF/Obsidian = 1F-c).

**Phase:** ✅ **MERGED to master** — PR #7 merged 2026-07-10 (merge commit `288f591`); branch deleted. All 9 SDD tasks converged through per-task dual gates (Claude + real Codex); whole-branch review READY TO MERGE (no Critical/High); verification green (tsc; unit 1746; integration 182+2skips). Spec CONVERGED v8+approved (`8ca22ab`); plan converged `82f3aaa` (3 rounds). Full trail: `docs/reviews/{spec,plan,task}-1f-a-*.md` + `whole-branch-1f-a.md`.

**1G follow-ups (in PR #7 body):** registered-residual = up to WHOLE shared daily cap (spec D10/§9 "fraction" wording undersells — a registered $0 reclaim-loop can exhaust the cap; anon hard-bounded 60≤100) → per-owner serve budget/anon controls; staging-blob GC; config-invariant quota-drift (canonical seed restore); nice-to-have test strengthening (uuid distinctness, route in_flight race, full-stack E2E).

**Key design (spec §3 canonical):** worker UNCHANGED; render on-serve; magazine model materialized **lazily on view** (version/drift-gated). Serve-side spend = **A+ lease** `SECURITY DEFINER reserve_serve_model` RPC (owner from `auth.uid()` internally; verifies owned+`promoted`; generation lease single-flights Gemini; **charges `magazine_est_cents=6¢` per attempt**; **K=5-attempt bound** per `(owner,doc,UTC-day)`; no release RPC; coarse statuses). Session/anon client only; nonce CSP; playlistId UUID. **Cloud model persists via `writeModelEnvelope` = `put`/`upload(upsert:true)` (Option A, overwrite-safe, self-heals on drift/version-bump) — NOT staged→promote (that stays for the worker MD path).**

**Next action:** **SDD implementation** (`superpowers:subagent-driven-development`, task #14) — 9 tasks, fresh implementer + per-task dual review, §8 iterative-re-review triggers on Task 1 (money RPC) + Task 5 (shared render). Start clean from the ledger. → whole-branch review → PR (`--repo …-cloud`).

**Money-path fork resolved (user, 2026-07-09):** chose **Option A** (cloud model upsert-overwrite) over staged-promote-with-overwrite / defer-to-1G — the R2 re-review caught that create-if-absent promote couldn't overwrite a stale model → fleet-wide re-charge on GENERATOR_VERSION bump. Governed by [[process-conventions]]. Supersedes "next is frontend" in [[stage-1d-merged-followups]].

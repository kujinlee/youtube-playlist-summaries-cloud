---
name: stage-1d-merged-followups
description: "FIRES-WHEN: citing Stage 1D cost guardrails — Stage 1D cost guardrails merged (PR"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

Stage 1D (cost guardrails) merged to master 2026-07-09 via PR #6 (merge commit `12a9f88`). Atomic per-owner debit in `enqueue_job` (SECURITY DEFINER, direct INSERT revoked), two-client enqueue route, Gemini caps, drift-proof cap-soundness guard. All 13 tasks dual-reviewed; whole-branch review = READY TO MERGE.

**Open follow-ups (not blocking, tracked in PR #6 body + docs/reviews/task-1d-*.md):**
- `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED = false` in `lib/gemini.ts` — ships cloud audio-fallback DISABLED (fail-closed; caption-less videos dead-letter). To ENABLE: run the live gate `RUN_LIVE_GEMINI=1 npm run test:integration -- gemini-live-gates` against real Gemini, confirm `thoughtsTokenCount===0` + video-scale `countTokens`, record to `docs/reviews/1d-live-gemini-gates.md`, then flip the flag.
- Codex adversarial pass on T13 (`59dd275`) never completed (Codex bg task hung); a Claude-opus adversarial substitute ran (no Blocking/High). Re-run Codex on that commit if desired.
- Deferred: T11 IP-velocity XFF-spoof (plan-mandated Medium; per-owner quota is the real bound); N1 `truncateSegmentsToByteCap` O(n²) on pathological input; `getGuardrailConfig()` uncached; `jobs` WITH-CHECK RLS no longer directly covered (grant-revocation tested instead).

Next: Sub-project 2 (frontend) per [[dev-process]] — does not begin until this backend work is verified/merged (now done).

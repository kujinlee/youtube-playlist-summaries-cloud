---
name: stage-1d-merged-followups
description: "FIRES-WHEN: citing Stage 1D cost guardrails, or enabling the cloud audio-transcribe fallback — merged PR #6 (12a9f88, 2026-07-09); the fallback flag still ships false"
metadata: 
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

**Stage 1D (cost guardrails) is merged** — PR #6, merge commit `12a9f88`, 2026-07-09. Atomic per-owner debit in
`enqueue_job` (SECURITY DEFINER, direct INSERT revoked), two-client enqueue route, Gemini caps, drift-proof
cap-soundness guard. 13 tasks dual-reviewed; whole-branch review READY TO MERGE.

**Still true (verified 2026-11-14):** `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED = false` in `lib/gemini.ts:27` — the cloud
audio fallback ships DISABLED (fail-closed; caption-less videos dead-letter). **To enable:** run
`RUN_LIVE_GEMINI=1 npm run test:integration -- gemini-live-gates` against real Gemini, confirm
`thoughtsTokenCount===0` + video-scale `countTokens`, record to `docs/reviews/1d-live-gemini-gates.md`, then flip it.

**Other follow-ups (non-blocking; PR #6 body + `docs/reviews/task-1d-*.md`):**
- Codex adversarial pass on T13 (`59dd275`) never completed (bg task hung); a Claude-opus substitute ran (no Blocking/High).
- Deferred: T11 IP-velocity XFF-spoof (per-owner quota is the real bound); `truncateSegmentsToByteCap` O(n²) on
  pathological input; `getGuardrailConfig()` uncached; `jobs` WITH-CHECK RLS covered only via grant revocation.

## History
- At merge the next step was Sub-project 2 (frontend) under the rule "2 does not begin until 1 is verified and
  merged" (`docs/dev-process.md`) — that rule was retired 2026-09-20; the frontend has since shipped.

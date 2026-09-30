---
name: cost-per-video-analysis
description: "FIRES-WHEN: needing the real per-video Gemini cost, or reasoning about the reservation — Real per-video Gemini cost ≈ 8¢ (Flash), NOT the 150¢ reservation; billing over-states it (Pro dev digs + re-runs); the settle slice is the durable fix"
metadata: 
  node_type: memory
  type: project
  originSessionId: 85979056-578d-429d-82a7-aaa8678bb1d9
---

**Question (2026-07-22):** is the 150¢ per-video charge over-estimated? **Answer: massively — by ~37×.**
Done as the first pass of the [[launch-roadmap-state]] "periodic cost recalibration" item.

**Realistic PROD cost (everything runs on gemini-2.5-flash), computed from `lib/gemini-cost.ts`:**
- Summary — worst case (30-min, all 12 retries) = **$1.15** ← what 150¢ reserves (+ headroom).
- Summary — typical (16-min, 1 clean pass) ≈ **$0.065**.
- Dig — worst case (15-min segment) = **$0.22**; typical (~5-min section) ≈ **$0.015**.
- **Realistic per-video (summary + dig, Flash) ≈ $0.08.** vs the $3.00 (150+150) reservation.

**Why the June billing ($15.18, 90-day $27.44) tells you almost nothing about prod cost:**
1. **Model mix (the big one).** Dev token charts are Pro-dominated (teal). Local dig defaults to
   **gemini-2.5-pro**; CLOUD dig overrides to **flash** (`lib/dig/generate.ts` — Pro can't disable
   thinking, uncostable to ≤150¢). Prod makes NONE of those expensive Pro calls. Cross-check: the
   Flash-filtered chart shows OUTPUT is Flash-heavy (summaries) while INPUT is Pro-heavy (dev digs).
2. **Dev re-runs** — same videos regenerated many times testing; prod generates once.
3. **150¢ was never a real cost** — it's a worst-case *reservation* ceiling.

**Key distinction — reservation vs actual.** `summary_est_cents`/`dig_est_cents` = 150 are
RESERVATIONS with guard tests proving 150¢ bounds the genuine worst case (`digWorstCents() <= 150`).
**Do NOT just lower them** — a pathological 30-min video hitting all retries really can approach
$1.15, and under-reserving risks the overspend the guardrail exists to prevent.

**The durable fix = the deferred "real-cost settle slice"** (Parking Lot): reserve 150¢, then SETTLE
to actual from `usageMetadata` and release the difference. Then the daily cap tracks REAL spend — at
~8¢/video a $5 cap fits ~60 videos instead of 3. That is the user-facing win (the cap feels ~20×
tighter than it needs to because reservations never settle down). Pricing constants
(`PRICE_*_PER_1M_CENTS`, gemini-2.5-flash dated 2026-07) also want periodic refresh — the recurring
half of the recalibration item.

**Interim taken 2026-07-22:** raised prod `daily_cap_cents` 500¢→**5000¢ ($50)** (was blocking full playlists).
Safe because actual spend is ~5% of reservations. See [[launch-roadmap-state]], [[access-tiers-vision]].

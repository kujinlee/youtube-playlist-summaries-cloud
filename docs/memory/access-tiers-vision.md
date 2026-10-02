---
name: access-tiers-vision
description: "FIRES-WHEN: needing the product direction for access tiers, limits or pricing — Product direction for access tiers: anon + Google-auth free tier with limits (mostly built), future credit-card subscription lifts limits (not built)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 85979056-578d-429d-82a7-aaa8678bb1d9
---

**User's access-tier vision (stated 2026-07-21, during M1.3 deploy):**
- **Free tier** — anonymous and Google-authenticated users, each with usage **limits**.
- **Paid tier (future)** — users subscribe with a **credit card**, which **lifts the limits**.

**How much already exists (do NOT rebuild):**
- `quota_allowance` — per-kind monthly limits, held **separately for anon vs authenticated**. This is
  the "different limits per tier" mechanism, already deployed (migrations, in prod).
- `guardrail_config` — `daily_cap_cents` (global spend ceiling) + `max_free_users` (caps how many
  free accounts can exist) + per-op est-cents. This is the real budget protection.
- So **"free tier with limits" is built.** The gap is a **billing / subscription layer** — nothing
  maps a credit-card subscription to a raised `quota_allowance`. That is the new work.

**Two operational consequences captured the same day:**
- **The signup toggle is NOT the budget guard** — `daily_cap_cents` + `max_free_users` are. Before
  opening `Allow new users to sign up` to the public, verify the PROD guardrail defaults (they came
  from migration defaults, possibly generous), don't assume.
- **Bootstrapping:** a fresh prod DB has zero users. Turning signup OFF before creating your own
  account locks you out — Google sign-in *creates* the user. Sequence: signup ON → deploy → sign in
  (creates your account) → then signup OFF. Grouped under the "before sign-ups open" trigger with the
  [[launch-roadmap-state]] exec_sql item.

Filed as a roadmap Parking Lot item ("subscription/billing tier") with a trigger. See
[[launch-roadmap-state]].

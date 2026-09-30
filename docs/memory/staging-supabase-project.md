---
name: staging-supabase-project
description: "FIRES-WHEN: needing the throwaway staging Supabase project — Throwaway hosted Supabase project neeufoxdbgbpkjukzzuc (yps-m14-staging) created 2026-08-11 for the M1.4 B-group checks — DELETE IT when B3/B4 are done"
metadata:
  node_type: memory
  type: project
  originSessionId: eebd3332-cf66-40d2-9e14-9cb83552f20e
  modified: 2026-08-11T16:36:26.827Z
---

**⚠ AN EXTERNAL RESOURCE EXISTS THAT THE REPO DOES NOT CREATE.** Recorded here at the moment of
creation, because that is exactly the discipline [[process-conventions]] says was missing when
prod drifted to migration `0022` unrecorded.

- **Project `neeufoxdbgbpkjukzzuc`** — name `yps-m14-staging`, org `pmxcbkdbfggdoynjxqxp`, us-east-1,
  created **2026-08-11**. Second project in the org (prod is `uykwcybxqgewmbltroxf`); expected to sit
  in the free tier, **not verified against billing**.
- **Why it exists:** the M1.4 B-group checks need *hosted* infra (real TLS, real pooler, real network),
  which is **not** the same as needing *production*. Running them here meant no Storage policy was
  revoked on live data. User decision, 2026-08-11.
- **State:** all 25 migrations, 12 tables all `rls_forced`, private `artifacts` bucket with both
  policies, test user `m14-staging@example.com` (owner `9e440cb5-0a70-42b9-998c-40760e1c9bcd`),
  password auth ENABLED (safe here; it is deliberately OFF on prod), ~10 synced videos + blobs.
- **🗑 DELETE IT when B3/B4 finish** — `supabase projects delete neeufoxdbgbpkjukzzuc`. Nothing in the
  repo references it; if this memory is lost it becomes an orphan nobody can explain.
- Credentials/URLs were written to the **session scratchpad only** (never the repo, never git). They
  die with the session — recreate via `supabase projects api-keys --project-ref neeufoxdbgbpkjukzzuc`.

**Worth keeping even after deletion:** applying the full migration set to a blank database proved for
the first time that it **builds a correct schema from scratch** (25/25, 12 tables, all `rls_forced`).
Prod's incremental history had never tested that, and no CI job does either.

See [[launch-roadmap-state]] for the B-group results themselves.

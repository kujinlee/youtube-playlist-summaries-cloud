---
name: staging-supabase-project
description: "FIRES-WHEN: seeing project ref neeufoxdbgbpkjukzzuc (yps-m14-staging), or deciding whether a check needs hosted infra — the throwaway staging project was DELETED 2026-08-12; record any new external resource the moment it is created"
metadata:
  node_type: memory
  type: project
  originSessionId: eebd3332-cf66-40d2-9e14-9cb83552f20e
  modified: 2026-08-11T16:36:26.827Z
---

**The staging project `neeufoxdbgbpkjukzzuc` (`yps-m14-staging`) NO LONGER EXISTS — deleted 2026-08-12**
(`docs/roadmap-to-launch.md`: Gate B3's money clause tested an unreachable state and was replaced by a CI test,
`tests/integration/serve-md-unreadable-no-charge.test.ts`, so hosted infra was no longer needed; prod verified
untouched afterwards). Nothing to clean up. Prod is `uykwcybxqgewmbltroxf`.

**Rule it carries:** an external resource the repo does not create is recorded **at the moment of creation**, with
its delete condition — the discipline [[process-conventions]] says was missing when prod drifted to migration `0022`
unrecorded. Credentials go to the session scratchpad only, never the repo.

**Worth keeping:** applying the full migration set to a blank database there proved for the first time that it
**builds a correct schema from scratch** (25/25 migrations, 12 tables, all `rls_forced`). Prod's incremental history
had never tested that.

## History
- Created 2026-08-11 (org `pmxcbkdbfggdoynjxqxp`, us-east-1; free tier assumed, not verified against billing) for the
  M1.4 B-group checks, which needed *hosted* infra (real TLS, pooler, network) — not *production*. User decision
  2026-08-11: run them there so no Storage policy was revoked on live data. Test user `m14-staging@example.com`,
  password auth enabled there only (deliberately OFF on prod). See [[launch-roadmap-state]] for the B-group results.

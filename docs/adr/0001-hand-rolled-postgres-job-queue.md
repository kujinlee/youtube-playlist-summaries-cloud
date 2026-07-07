---
status: accepted
---

# Hand-rolled Postgres job queue instead of pg-boss

For the cloud durable job queue (Stage 1E-a) we build a single owned `jobs` table with `SELECT … FOR UPDATE SKIP LOCKED` leasing rather than adopting **pg-boss**, even though the parent cloud-publishing architecture (§9) explicitly named pg-boss. We chose this because our requirements make one owned table simpler than reconciling pg-boss's parallel lifecycle: the table must be **RLS-owner-scoped** (users poll their own jobs directly), keyed by a **domain idempotency tuple** (work target + job kind + job version) rather than an opaque string, and it must be the **FK anchor for Stage 1D's quota/spend reservation** so a retry never re-charges. `SKIP LOCKED` is the same primitive pg-boss uses internally, and we only run two job kinds (summary, dig), so the durability mechanics we actually need are a small, well-understood slice of what pg-boss offers.

## Considered options

- **pg-boss owns the lifecycle** — least code, but its schema sits outside RLS (needs a wrapper API for "poll my jobs"), idempotency is a string not the domain tuple, and 1D's reservation has no natural FK target.
- **pg-boss for delivery + our RLS `jobs` table as source of truth** — reuses pg-boss's tested lease/retry/DLQ, but introduces a two-store reconciliation seam (pg-boss lifecycle vs. our row) with its own consistency bugs.
- **Hand-rolled `SKIP LOCKED` (chosen)** — one source of truth, native RLS, domain idempotency, clean 1D FK; cost is that we own and test the lease/heartbeat/backoff/dead-letter logic ourselves.

## Consequences

By not using pg-boss we take on obligations it would have provided, and must supply them explicitly: lease fencing (lease token on every worker mutation), a dead-letter bound on crash-loops, hot-path indexes, and — deferred with named owners — queue-depth/concurrency caps (1D), and dead-letter retention/observability (1H). Both adversarial reviews (Codex + Claude) of the 1E-a spec checked these; the spec v2 addresses the in-scope ones and lists the deferred ones. Revisiting this (adopting pg-boss later) would mean migrating the `jobs` table and re-pointing 1D's reservation — meaningful but bounded.

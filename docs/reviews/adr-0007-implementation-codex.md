<!-- codex-review: model=gpt-5.5 -->

**Findings**

Medium — T4’s “only `record_artifact` inserts generations” assertion is too syntax-shaped to protect the invariant it claims to protect.  
Evidence: the assertion only scans `pg_proc.prosrc` for `insert\s+into\s+(public\.)?video_generations\y` in `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:1356`, while the ADR says the carried invariant depends on that assertion firing if a second inserter appears in `docs/adr/0007-artifacts-are-an-append-only-log.md:525`. I measured two bypasses in rolled-back transactions: a function inserting through an auto-updatable view over `video_generations` inserted a row while the assertion still reported `writers={record_artifact}`, and a function using `public."video_generations"` also left the assertion green. Current repo search found no existing production inserter besides `record_artifact` at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:442`, so this is not an existing caller bug.  
Fix: extend the ratchet beyond the current regex: at minimum catch quoted identifiers, explicit rewrite rules, and insertable view aliases over `video_generations`; preferably forbid insertable aliases for this table in the spec schema unless explicitly whitelisted.

Low — The ADR/schema comments still say `video_generations.state` is read by the completeness CHECKs, but the implementation removed those reads.  
Evidence: `docs/adr/0007-artifacts-are-an-append-only-log.md:430` says the column is kept because the completeness constraints are “all written `state <> 'complete' or …`”; `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql:305` repeats that claim. The actual checks at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql:404` through `:429` no longer reference `state`. The code behavior appears intentional and covered by T4; the stale text is the gap.  
Fix: update the ADR and schema comment to say those checks used to read `state`; today `state` is kept for the single-valued domain, `record_artifact`’s outcome read at `04_artifacts.sql:438`, and the typed artifact guard at `04_artifacts.sql:1120`.

**What I Could Not Break**

Both required oracles passed: `verify-schema.sh` completed with `ASSERTIONS_OK` / `ALL_STATEMENTS_OK`, and `mutate-schema.py` reported `59/59 mutations behaved as expected` with baseline restored green.

I could not defeat the set-shaped provenance enforcer with the cases requested: first multi-row source-set insert succeeded; later additions in a second statement failed; `ON CONFLICT DO NOTHING` did not bypass a real new source; identical set/subset `ON CONFLICT DO NOTHING` altered no data; the GC reachability and source-currency mutations went red.

I also could not find an existing view, rule, trigger, RPC, or non-fixture code path in the repo that currently inserts a generation outside `record_artifact`; the problem is that the assertion would not notice several plausible future forms.

NOT CONVERGED — no Blocking finding, but the load-bearing T4 ratchet has measured blind spots.

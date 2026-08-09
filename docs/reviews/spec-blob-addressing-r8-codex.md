<!-- codex-review: model=gpt-5.5 -->

**JOB 1**

**BLOCKING**: `record_artifact` lets a tokenless caller complete and record a pending paid generation it does not own.

Scenario: W1 reserves `summary/gOWNER`; W2 or any service-role caller names that pending slot/generation with `p_token = NULL`, supplies its own card/hash, and the function returns `recorded_after_token_loss`. Measured result: `gen_state=complete`, `md_hash=SHA_ATTACK`, `tldr=attacker`, `art_state=recorded`, `lease_token=NULL`.

Evidence: [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:450) accepts either `reserved_by = p_token` or “pending slot names this generation”; [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:466) then fails the holder update on `NULL` token but [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:518) upserts the same paid row.

Change: require non-null proof of ownership for completion, and do not let the slot-name disjunct stand alone; the “forgot token” path needs a separate restart credential or should be explicitly rejected before content completion.

**BLOCKING**: `video_generations_collectable` can collect an in-flight pending generation, after which recording succeeds but the artifact is permanently invisible.

Scenario: reserve a summary, run the sweep through `video_generations_collectable` before the worker records, then record normally. Measured: `collectable_before_record = 1`, `record_outcome = recorded_as_holder`, then `state=complete`, `body_collected=t`, `current_rows=0`.

Evidence: [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:730) excludes only rows visible through `video_artifacts_current`; [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:661) makes `current` require `state='recorded'`, so pending reservations are collectable.

Change: exclude any generation referenced by a non-collected pending/recorded/detached artifact, or at minimum require `g.state = 'complete'` and no pending artifact before GC eligibility.

**HIGH**: `produced_at > now()` rejects valid writes in long transactions because `now()` is transaction timestamp, not statement/wall-clock time.

Scenario: begin transaction, wait, insert a generation with `produced_at = clock_timestamp()`. Measured error: `ERROR: video_generations: produced_at 2026-08-08 20:28:02.866394+00 is in the FUTURE — a clock value may not enter the ranking`.

Evidence: [03_generations.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql:286) uses `now()` inside the trigger.

Change: compare against `statement_timestamp()` or `clock_timestamp()` with a small explicit skew tolerance; document how sync handles replicas behind/ahead.

**MEDIUM**: the guard-coverage ratchet can be satisfied by a mutation name appearing anywhere in `mutate-schema.py`, not by an actual mutation covering that guard.

Scenario: remove the mutation tuple for `video_artifacts_free_uq` but leave the string in a comment; `if name not in mutation_text` still passes.

Evidence: [check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:156) reads the mutation file as raw text; [check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:180) uses substring membership.

Change: parse the `MUTATIONS` labels or add structured guard IDs to mutation entries.

**MEDIUM**: `t_writes` measures row writes, not second-caller behavior, so a single paid writer’s `pending -> recorded` update can satisfy “written twice.”

Scenario: a new paid artifact kind with only reserve+record coverage records an insert and an update, making the population ratchet pass without ever exercising conflict/retry behavior.

Evidence: [05_assert.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:89) records every insert/update; [05_assert.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:1436) only requires `count(*) > 1`.

Change: record call-site/scenario labels, or assert specific second-write cases per enum value through `record_artifact`/reservation APIs.

**JOB 2**

**HIGH**: the `reserve_artifact_slot` `already_recorded` check-then-act race is real by construction and can still surface raw `23505`.

Scenario: T1 passes the `exists` check at [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:256); T2 records the same `(workspace, video, slot, generation)`; T1’s insert then conflicts on `video_artifacts_paid_uq`, while its `ON CONFLICT` only targets `video_artifacts_inflight_uq`.

Evidence: [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:154) defines the paid unique; [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:297) reconciles only the pending-slot conflict.

Change: make the reservation insert also handle paid-unique conflicts, or replace the pre-check with a single insert/upsert path that returns typed `already_recorded`.

The “inert pending generation” is not inert; the GC finding above is the measured counterexample. I did not find a separate measured `persist_summary` freeze-trigger failure in this pass.

**JOB 3**

The guard classification is incomplete in the way that matters most: it verifies labels exist, but two new instruments can report coverage without proving the second-caller behavior they claim. The reservation rule is therefore not structurally protected yet; the tokenless `record_artifact` path and pending-generation GC path both bypass the intended spending/recording boundary.

Gates: after restoring mutation residue left by the first interrupted run, `./scripts/check-schema-gates.sh` passed: schema/assertions green, 44/44 mutations as expected, 32 guards classified, docs OK.

Verdict: **NOT CONVERGED**.

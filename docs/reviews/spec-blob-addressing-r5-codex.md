<!-- codex-review: model=gpt-5.5 -->

**JOB 1**

**BLOCKING**

- `video_artifacts_current` and `video_summary_current` can pick different current summary rows because the generic artifacts view applies the `source_generation_id` rung to `slot='summary'`, while the summary view does not. Scenario: insert two recorded summary artifacts where the better-ranked summary has a non-null/stale `source_generation_id`; `video_summary_current` picks it, but `video_artifacts_current where slot='summary'` can pick the null-source row instead. Evidence: `schema/04_artifacts.sql:80`, `schema/04_artifacts.sql:95`, `schema/04_artifacts.sql:112`. Fix: either make `video_artifacts_current` union `video_summary_current` for `slot='summary'`, or apply source-currency only to derived slots and constrain `source_generation_id is null` for summaries/free renders.

- `source_generation_id` is documented as provenance but is not enforced by any FK or kind check. Scenario: a model row can claim it was built from `gDOES_NOT_EXIST`, or from a model/dig generation rather than a summary, and the view merely ranks it stale while serving a row whose provenance is false. Evidence: `schema/04_artifacts.sql:29`, `schema/04_artifacts.sql:48-55`, `schema/04_artifacts.sql:112-113`, spec `...design.md:899`. Fix: add an enforced source-summary reference, likely via a source generation FK plus a way to require referenced `kind='summary'`, and add negative assertions.

- The new in-flight money guard is asserted but absent from the schema. Scenario: two pending `model` rows for `wA` and `wB` in the same `(workspace, video, slot)` pass `video_artifacts_paid_uq` because generation ids differ, so both writers can reserve and pay Gemini; the new assertion at `05_assert.sql:112` would fail if the verifier could run. Evidence: `schema/04_artifacts.sql:57-59` has only paid/free uniques; `05_assert.sql:102-115` expects `video_artifacts_inflight_uq`. Fix: add `create unique index ... on video_artifacts(workspace_id, video_id, slot) where state='pending'`.

**HIGH**

- `blob_key` is not tied to `(workspace_id, video_id, generation_id, slot)`, so a row can rank one generation’s card while serving another generation’s bytes. Scenario: insert `generation_id='gNEW'`, `slot='summary'`, `blob_key='<ws>/videos/<vid>/gOLD/summary.md'`; all constraints pass, and the current view serves old bytes with new card facts. Evidence: address contract at spec `...design.md:181-184`, key table at `...design.md:276-281`, unconstrained `blob_key text not null` at `schema/04_artifacts.sql:28`. Fix: add key-shape validation/parsing checks or make `record_artifact` derive `blob_key` server-side from the tuple.

- §5.3’s “field for field” sync claim is false. Scenario: implementing cloud-to-sync projection from that prose omits/renames load-bearing fields: `ClassASignals` includes `summaryMdKey`, `mdHash`, and `backfilled`, while the SQL ranking uses `produced_at` and `source_generation_id`; the card also requires `tldr`, `takeaways`, `processedAt`, which `ClassASignals` does not carry. Evidence: `lib/cloud-sync/types.ts:4-10`, `lib/cloud-sync/reconcile-class-a.ts:38-50`, `schema/04_artifacts.sql:112-117`, spec `...design.md:1354-1361`. Fix: rewrite §5.3 as an explicit projection/mapping, not “field for field”, and name the extra fields deliberately.

- `slot_kind` accepts `html%`, which admits slots the taxonomy does not define. Scenario: `slot='html-preview'`, `kind='render'`, `generation_id=null` is accepted and served as its own free slot even though §4.0 only names `slot='html'`. Evidence: `schema/04_artifacts.sql:17`, spec `...design.md:280`, slot definition `...design.md:80`. Fix: change to `p_slot = 'html'` unless multiple HTML slots are a real chosen invariant, and test both `html` positive and `html-preview` negative.

**JOB 2**

`verify-schema.sh` did not run in this sandbox: Docker socket access is denied.

Measured error: `permission denied while trying to connect to the Docker daemon socket ... connect: operation not permitted`.

Because of that I could not honestly mutate-and-rerun guards against live Postgres. Static guard sweep still found these test/design gaps:

**BLOCKING**

- The new in-flight assertion is ahead of the DDL, so the verifier should go red once Docker access is available. Evidence: `05_assert.sql:112-115` expects rejection; `schema/04_artifacts.sql:57-59` lacks the needed pending-slot unique index. Fix as above.

**HIGH**

- `05_assert.sql` does not test bogus `source_generation_id`, summary rows with non-null `source_generation_id`, or equality between the two current views for summaries. Evidence: `05_assert.sql:87-100` only tests stale-but-existing `gOLD`; no negative for non-existent/wrong-kind source. Fix: add those assertions.

- `05_assert.sql` does not test key/tuple congruence. Evidence: inserts use opaque `k1`, `k2`, `kPDF` at `05_assert.sql:32-35`, so the executable schema never proves the stable blob address shape it is supposed to enforce. Fix: use real-shaped keys and add malformed/wrong-generation key negatives.

**JOB 3**

**HIGH**

- Rule 14’s floor is reintroduced as a gate in prose a few lines after the fix. Scenario: a reader follows `...design.md:1061-1064` and implements “corrections-stale is not eligible to be current,” recreating the empty-summary-on-correction bug that `...design.md:999-1025` just removed. Evidence: `...design.md:999-1025` versus `...design.md:1061-1064`; inventory still says “state = recorded, full stop” at `docs/reviews/spec-blob-addressing-rules-inventory.md:190-193`. Fix: replace “not eligible to be current” with “loses ranking to a corrections-current generation.”

- Rule 13’s “same ordering in two implementations” is not yet worth its cost unless the tuple is named precisely. Scenario: SQL uses `produced_at`; `reconcileClassA` uses `mdGeneratedAt`; §5.3 says they are the same hierarchy, but they are not the same field. Evidence: `schema/04_artifacts.sql:115-117`, `lib/cloud-sync/reconcile-class-a.ts:48-50`, spec `...design.md:1365-1371`. Fix: decide whether `produced_at` equals `mdGeneratedAt` by definition, then encode that in schema/projection/tests.

**Verdict: NOT CONVERGED**. New Blocking and High findings remain.

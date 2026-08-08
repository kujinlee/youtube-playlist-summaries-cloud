<!-- codex-review: model=gpt-5.5 -->

**JOB 1**

**BLOCKING**

`reserve_artifact_slot` creates a pending `video_generations` row even when it returns `busy` or `exhausted`, and `record_artifact` can later complete that unreserved generation and append a recorded artifact with no lease ownership.

Failure scenario: W1 reserves `dig:700/gDIG`; W2 calls `reserve_artifact_slot(... gOTHER ...)`, gets `busy` and no token, but the function has already inserted `video_generations(gOTHER, pending)`. If W2 incorrectly continues and calls `record_artifact(... gOTHER ..., random_token)`, the generation update at lines 396-403 succeeds, the holder update at lines 406-410 affects zero rows, and the append path at lines 412-417 inserts a recorded row. That violates §9.2’s rule that the reservation guards who may start paid work.

Evidence:
[04_artifacts.sql:252](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:252) checks `already_recorded` before generation creation, but [04_artifacts.sql:268](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:268) creates the generation before the reservation upsert knows its outcome. [04_artifacts.sql:307](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:307) then returns `busy`/`exhausted` without cleaning that parent row. [04_artifacts.sql:397](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:397) completes by generation id only, and [04_artifacts.sql:412](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:412) appends after any token miss.

Change I would make: make generation creation conditional on actually acquiring the reservation, likely by deferring the artifact FK inside the RPC or by adding a durable reservation-attempt row keyed by `(slot, generation_id, token)`; then make `record_artifact` require proof that this generation previously acquired the slot, while still allowing the deliberate reclaimed-writer append path.

**JOB 2**

**HIGH**

The mutation harness’s new `RED(trigger)` classification ignores the expected assertion substring, so any `raise exception` whose message starts with `video_artifacts:` or `video_generations:` is accepted as the intended guard.

Failure scenario: a mutation expected to hit “generation is still PENDING” could instead trip `video_artifacts: the ADDRESS...` earlier and still be counted as `RED(trigger)`, because the branch returns success without comparing `expect`.

Evidence:
[mutate-schema.py:274](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py:274) validates `expect` for assertion failures and can return `RED(other)`. [mutate-schema.py:292](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py:292) classifies trigger errors by prefix only, and [mutate-schema.py:315](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py:315) treats all `RED(trigger)` as acceptable.

Change I would make: carry the same expected-substring check into `RED(trigger)`, returning `RED(other)` when the trigger prefix matches but the expected detail does not.

Measured execution:
`verify-schema.sh` could not run here because Docker socket access is blocked: `dial unix /Users/kujinlee/.docker/run/docker.sock: connect: operation not permitted`. The supplied mutation copy was also outside writable roots, so I copied it to `/tmp`; mutation still could not execute SQL because the verifier could not reach Docker, producing `0/35 mutations behaved as expected` with `no error captured; SQL did not run`.

**JOB 3**

No separate new invariant finding beyond the Blocking above. The weak invariant is exactly “reservation guards spending, not recording”: it only holds if a `busy`/`exhausted` loser cannot leave behind a recordable generation. Today it can.

Verdict: **NOT CONVERGED**.

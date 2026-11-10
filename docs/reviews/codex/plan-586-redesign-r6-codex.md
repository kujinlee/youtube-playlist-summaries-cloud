<!-- codex-review: model=gpt-6.1-sol -->

Found **one BLOCKER and one MAJOR** in the scoped fold.

**BLOCKER — A fast report clock permanently freezes a run before its re-run deadline.**  
At plan lines 1102–1107, `observe_final` compares runner-local `observed_at` with GitHub’s `created_at`, without establishing a common clock or allowing for skew. Taking the timestamp before listing does not resolve that difference.

Concrete failing input, executed against the extracted blocks:

1. PR #620 is recorded clean at run 55, attempt 1, created `2027-01-01T10:00:00Z`.
2. GitHub’s actual time is `2027-01-31T09:59:59Z`. The report runner is two seconds fast, recording `observed_at = 2027-01-31T10:00:01Z`.
3. The listing truthfully returns run 55 as attempt 1, `completed`. `final_runs` produces:
   ```json
   {"55":{"attempts":1,"observed_at":"2027-01-31T10:00:01Z"}}
   ```
4. Before GitHub’s deadline, attempt 2 is requested legally. It later completes with a stable miss.
5. A report allowed to loosen supplies the observation. `absorb_epoch` records it, and `absorb_errors` accepts the rebuilt ledger.
6. Every subsequent `settled("620", ledger, {55: attempt_2})` returns **True**. The frozen branch at lines 1140–1143 ignores the newly visible attempt count. Attempt 2’s miss is never compared.

The executed adjacent control returns `decide_pr([["clean", "miss"]]) == "miss"`: omission loses evidence that should latch. This needs no false GitHub metadata. GitHub documents the [30-day re-run window](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs?tool=cli).

“First observation kept” makes the premature observation permanent; even a later observation of attempt 2 cannot replace it. Archiving the epoch also preserves the freeze because `settled` reads archived `final_runs`. Both consequences passed the executable reproduction.

**MAJOR — The 45-day listing cannot supply the claimed coverage or steady-state cost.**  
Concrete input: the fold’s own estimate of 4,560 matching runs. GitHub [caps filtered workflow-run searches at 1,000 results](https://docs.github.com/en/rest/actions/workflow-runs); pagination does not retrieve all 4,560.

The extracted parser accepts a truncated listing without checking completeness. An unfrozen decided run outside those returned results is absent from `runs_now`, so it triggers per-PR re-comparison and artifact downloads. I executed that construction: it correctly refuses to settle, but defeats the claimed 15-day observation cushion and approximately 63-call steady state. This adds repeated artifact work beyond backlog #594’s newly undecided PRs. It is liveness/cost rather than a separate unsafe omission.

Other attack results:

- Exactly +30 days does not freeze; `queued` and `in_progress` do not produce final observations.
- A listing count different from the compared count does not produce an observation.
- Wrong-epoch reports cannot add observations; invented or dropped ledger entries fail rebuild.
- #594 remains fail-closed **under the stated report contract**: listing/download failure exits nonzero and upload requires success. The embedded blocks do not implement that orchestration, so they cannot independently prove its eventual implementation rejects partial output.

Extracted Task 7.2/7.3 into `$TMPDIR/r6-fold-n5ms8udg` and ran the assertions with `python3 -I`; all passed. No repository files were edited, committed, or filed.

VERDICT: NOT CONVERGED

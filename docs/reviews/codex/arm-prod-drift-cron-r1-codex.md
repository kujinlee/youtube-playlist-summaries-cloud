<!-- codex-review: model=gpt-5.5 -->

## Verdict
CONVERGED

## Findings
None.

I checked the workflow diff against the live file and the relevant script paths:

- `schedule` is correctly indented as a sibling of `pull_request`, `push`, and `workflow_dispatch` under `on:` at `.github/workflows/schema-gates.yml:126`.
- The scheduled event does start the workflow, but `schema-gates` is excluded by `if: github.event_name != 'schedule'`, so the cron does not run the repo-schema job/container suite. It runs `prod-drift` only.
- `prod-drift` is gated to exactly `schedule` and `workflow_dispatch` via `.github/workflows/schema-gates.yml:195`, so push/PR runs do not hit production.
- The concurrency key includes `github.event_name` at `.github/workflows/schema-gates.yml:138`, so a push to `refs/heads/master` at 08:59 and the 09:00 cron on `refs/heads/master` land in different groups and cannot cancel each other. Same-event cancellation remains possible and intended.
- Missing secret fails before any schema claim with `exit 2` in the workflow step. Rotated/revoked-but-nonempty credentials fail through `check-live-schema.py`/`m4_catalog.py` as `RuntimeError`, caught as `CANNOT RUN ... Treat this as NOT RUN.`, also `rc=2`.
- I did not find a path where the scheduled prod check reports success after checking nothing: empty/malformed manifest, unreachable database, missing URL, no owned relations, and ambiguous catalog subjects all refuse before verdict.
- Cost is bounded by `timeout-minutes: 10`, one checkout, Python setup, one sleeping Postgres image used as a psql client, and cleanup under `if: always()`.
- The new comment is careful about scope: it says a green run proves the path can pass, not that future red means drift, and it preserves the missing/revoked credential as “NOT RUN” rather than “no drift.” I did not find an overclaim in the armed-schedule comment.

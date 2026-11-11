<!-- codex-review: model=gpt-6.1-sol -->

No new actionable findings in `origin/master..f2431a61`. The known visibility prerequisite remains; this verdict does not clear it for merge.

- **Digest handling:** Read the whole script. Every `$IMAGE` use is quoted; there is no tag parsing. Inspect, pull, run and logging accept the unchanged reference. Self-test: `"23 cases, 23 passed, 0 failed"`. It tests names and backoff, not digest I/O.
- **Env scope:** Both consumers inherit workflow `SCHEMA_DB_IMAGE`; no job override or `services:` exists. Step env maps introduce other variables only. This matches [GitHub’s env rules](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables). The remaining executable ECR literal is the script’s intentional local fallback; no workflow overrides the mirror with ECR.
- **Failure contract:** With a Docker stub rejecting the digest pull, startup returned **2**, printing `"pull attempt 1/1 failed: unauthorized: authentication required"` and `"CANNOT RUN — could not obtain … after 1 attempt(s)."`. The actual folded prod-client block, with startup rejected, returned **2** and printed `"Treat this as NOT RUN, never as a pass."` Real registry/Docker execution: **UNVERIFIED**. A cached pinned image may run despite registry deletion/private visibility; that still tests the intended bytes.
- **Guards:** Self-tests passed: python-pin **111/111**, guard-coverage **37/37**, storage-independence **50/50**, ci-watched **82/82**, merge-ready **74/74**. Normal runs: first three rc=0; python-pin reports the local Python 3.14 versus CI 3.12 advisory. ci-watched without flags returns usage/rc=2; merge-ready returns `"CANNOT RUN — no pull requests found for branch \"ci/ghcr-schema-image\""`/rc=2. No env-induced parsing regression observed.
- **Supply chain:** Digest pinning improves content integrity over the previous mutable tag. A compromised package owner can delete content, restrict access or replace tags, causing unavailability; they cannot substitute different accepted bytes under the pinned digest under Docker’s content-verification model. Pinning freezes upstream tag updates, including security fixes, until explicitly updated. It does not establish that the original image was trustworthy. See [Docker’s digest contract](https://docs.docker.com/reference/cli/docker/image/pull/).
- **Records:** Closing #310 as a duplicate is accurate independently of deployment completion. Dashboard text states public visibility and this PR’s green check as prerequisites. Historical throttle counts and mirror digest equality were **UNVERIFIED independently**.

No repository files or images were changed.

VERDICT: CONVERGED

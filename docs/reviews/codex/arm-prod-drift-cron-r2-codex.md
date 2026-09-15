<!-- codex-review: model=gpt-5.5 -->

## Verdict
FINDINGS

No new Blocking or High. I checked the GitHub docs for scheduled-workflow disable and notification routing, verified the repo is PUBLIC, read `check-live-schema.py` for the `manifest <= live`/accept-list direction, parsed the workflow YAML, checked the cron remains under `on:` beside `workflow_dispatch`, verified the dashboard entry header exists, and confirmed `check-dashboard-entry --base origin/master` passes.

## Findings
### Low Scheduled-notification routing is documented, but the comment says it is not
**Where:** `.github/workflows/schema-gates.yml:133`

**What:**  
```yaml
# does reach them by email. What is genuinely weak: that channel is undocumented, it transfers
```

**Why it matters:** GitHub’s docs for `schedule` say scheduled workflow notifications go to the user who last modified the cron syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule. The real residual is still worth documenting: the recipient silently changes with a cron edit, and scheduled failures are not PR checks. But calling the channel “undocumented” is an overclaim in a gate comment.

**Suggested fix:** Replace “that channel is undocumented” with “that channel is easy to miss” or “that channel is not surfaced on PRs,” keeping the transfer/PR-check warning intact.

# Round 1 — `arm-prod-drift-cron` (PR #308) — coordinator

```yaml
round: 1
fixes_nontrivial: false
subject: arm-prod-drift-cron
halves:
  codex: ran
  claude: ran
findings:
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, component: merge-readiness, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: schedule-durability, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: failure-visibility, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: drift-interpretation, disposition: fixed}
```

## Verdict: CONVERGED — no Blocking, no High

**Both halves agree, and the second reproduced all eight of the first's checks and disputed none.**
`review-method.md:625` — stop when a full re-review returns no new Blocking or High.

## What the halves established between them

The change is a two-line uncomment, so the value of the round was in what it *ruled out*:

- `schedule` is correctly a sibling of `push`/`pull_request`/`workflow_dispatch` under `on:`.
- **The cron does not drag in the container suite:** `schema-gates` is excluded by
  `if: github.event_name != 'schedule'`, so the nightly runs `prod-drift` **only**. This was the
  brief's first question and neither I nor the change's author had checked it.
- `prod-drift` is gated to exactly `schedule` and `workflow_dispatch`, so push and PR runs never
  touch production.
- The concurrency key includes `github.event_name`, so an 08:59 push to master and the 09:00 cron
  land in **different groups** and cannot cancel each other.
- ⭐ **Two facts fetched from GitHub's documentation rather than recalled**, which close two holes
  the brief asked about: scheduled runs execute **only on the default branch**, and **path filters
  do not apply to `schedule`**.
- No path found where the scheduled check reports success having checked nothing: `--expect-present`
  cannot pass on an empty or partial catalog, on top of the `owned_relations` empty-set refusal.
- Credential exposure on a public repo is already closed — `m4_catalog.py` keeps the URL out of
  `argv` by design.

## Findings — all fixed, none blocking

### M1 — the PR was CONFLICTING → **FIXED**

`origin/master` advanced (#307) and appended to the same tail of `docs/dashboard-entries.md`. Merge
readiness, not a design defect. Resolved by keeping both entries.

### L1 — ⛔ the schedule can disarm itself silently → **FIXED (one sentence)**

**This repository is PUBLIC, and GitHub disables scheduled workflows after 60 days with no
repository activity.** The comment asserted armed-ness as durable. Low today only because this repo
sees daily pushes — but the failure mode is *absence of runs*, and absence is exactly what no gate in
here can see. Now written down beside the cron.

### L2 — who sees a red → **FIXED (recorded, after being refuted)**

⭐ **The reviewer chased this as a possible High and then refuted its own hypothesis**, which is
worth more than the finding: the arming commit is authored `t <t@example.com>`, which appears on none
of master's last 30 commits — but squash-merges land re-authored as the owner (verified on
`430b2fc1`), and GitHub routes scheduled failures to whoever last modified the cron syntax. So a red
**does** email the owner. What survives is weaker and true: the channel is undocumented, it transfers
silently to whoever next edits that line, and a scheduled failure appears on **no pull request's
check list**.

### L3 — a red is not always drift → **FIXED (labelled a hypothesis)**

The nightly compares production against **master's** manifest, and `manifest <= live` has no
accept-list in that direction, so a schema shipped to master but not yet deployed reads the same as
production having drifted. Narrow in practice, and **the scenario was not executed** — recorded as a
hypothesis, in those words, beside the code.

## The decision, argued rather than assumed

Asked for the strongest available criticism of *arming a nightly job nobody may watch*, the reviewer
concluded arming is right: the alternative is no detection at all for the one subject no push
corresponds to; the job fails closed on every path it could push; the cost is ~21s/day of free
minutes. **The real weakness is that *did not run* looks identical to *ran clean*** — which is a
sentence to write, not a redesign, and it is now written.

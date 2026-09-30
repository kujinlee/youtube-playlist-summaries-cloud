---
name: gh-two-remotes-footgun
description: "FIRES-WHEN: using gh pr and unsure which remote it resolves — RESOLVED 2026-08-04 — the `upstream` remote was removed, so bare `gh pr` is now unambiguous. Keep the fact that `official-plugins` is the OLD, frozen repo — superseded, do not edit it"
metadata:
  node_type: memory
  type: project
  originSessionId: d8be4c73-9b3a-4239-af59-51f83f200fe0
  modified: 2026-08-04T23:03:38.131Z
---

✅ **RESOLVED 2026-08-04 — `git remote remove upstream`.** The working dir now has exactly one
remote (`origin` = `kujinlee/youtube-playlist-summaries-cloud`), so bare `gh pr` commands can no
longer resolve to the wrong repo. Verified: `gh pr list` with no `--repo` returns #47/#46/#45 from
`-cloud`. Removal was safe — 0 remote-tracking refs under `upstream/`, no branch tracked it, and no
script, hook or workflow referenced it.

**What `official-plugins` is (confirmed 2026-07-29, unchanged by the removal):** the **OLD local
repo** — superseded by `-cloud`. Both share root commit `508cb81`; `official-plugins` stopped at 594
commits, `-cloud` continued past 1254. It has **no `STORAGE_BACKEND`, no Supabase, no
`lib/storage/`** — it is *not* the "local mode" runtime in the architecture diagram (that node is the
`-cloud` codebase run with `STORAGE_BACKEND=local`). **Treat it as frozen: do not edit or push to
it.** When the user says "local", they mean this working dir / local mode of `-cloud`, NOT that repo.

**The damage it did, worth remembering as a shape.** PR numbers are per-repo and the two ranges
overlapped (both had a PR #2). A wrong-repo command does not error — it returns a valid PR with a
title, diff and merge state, all belonging to a different codebase. A mutating `gh pr edit 2` once
overwrote the WRONG repo's PR body. Same failure shape as
[[integration-suite-does-not-apply-migrations]]: not a red signal, a **green one that proves
nothing**. Removing the ambiguity beats remembering to work around it.

**Still true:** write PR bodies to a file and use `--body-file`; a `--body "$(cat <<'EOF' … )"`
heredoc breaks on the apostrophes and backticks these bodies contain. That rule is independent of
remotes. `gh api repos/OWNER/REPO/...` (explicit path) was never affected by either issue.

**Pending doc edit (not yet landed):** `docs/dev-process.md` Phase 5 still describes the two-remotes
footgun and mandates `--repo`. Per the repo's own batching rule it rides the next open branch rather
than getting a standalone PR. Related: [[process-conventions]], [[stage-1c-supabase-adapters]].

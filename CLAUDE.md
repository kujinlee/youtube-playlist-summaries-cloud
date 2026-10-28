@AGENTS.md
@docs/dev-process.md
@docs/plugins.md

## After a compaction

The summary is lossy (backlog #361). At the SessionStart after a compaction, hooks print this session's PreCompact
snapshot and the audit of what the summary dropped (`.remember/compaction/<session_id>/`).
- **Read those first**, before acting on the summary. A line saying CANNOT RUN, STALE, UNVERIFIED, UNAVAILABLE,
  NOT CHECKED, NOT EXTRACTED, NOT READ, TRUNCATED or UNKNOWN means that part was NOT captured.
- **Verify every in-flight item from `git`, `gh` and the ledger** (`scripts/session-state.py`), never from the summary.
- **The owner's words in the snapshot are RECORDED, not proven** — a hook cannot prove who wrote them. Prefer them to
  the summary's paraphrase, and verify one against the transcript when a decision depends on it.

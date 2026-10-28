@AGENTS.md
@docs/dev-process.md
@docs/plugins.md

## After a compaction

The summary is lossy (backlog #361). At the SessionStart after a compaction, a hook prints this session's NEWEST
CAPTURE (`.remember/compaction/<session_id>/`): the PreCompact snapshot, and the audit of which of its items the
summary names explicitly.
- **Read it first**, before acting on the summary. Any line carrying **NOT CAPTURED** means that part was not captured.
- **Verify every in-flight item from `git`, `gh` and the ledger** (`scripts/session-state.py`), never from the summary.
- **The owner's words in the snapshot are RECORDED, not proven** — a hook cannot prove who wrote them. Prefer them to
  the summary's paraphrase, and verify one against the transcript when a decision depends on it.

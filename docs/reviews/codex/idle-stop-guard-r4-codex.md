<!-- codex-review: model=gpt-6.1-sol -->

- **BLOCKER — scripts/check-idle-stop.py:267:** Completed builder work permits an announcement-only first stop. Concrete fixture: sibling builder `.git` aged 86,400 s, final output aged 120 s, builder finished with no process remaining; usage cache absent; CI response `[]`. Payload: `{"hook_event_name":"Stop","stop_hook_active":false,"background_tasks":[],"last_assistant_message":"Now starting backlog #657."}`. Through `main()`: **exit 0**, silent. The timestamps model legitimate completed work; the stopping agent forges no signal. With the same fixture 601 s later: **exit 2**. Recency substitutes for running work.

Removal audit found no remaining production transcript or pause-marker reader. Remaining agent-writable work signals are the already-filed #664/#665.

Self-test last line: `78/78 self-test cases passed`

VERDICT: NOT CONVERGED

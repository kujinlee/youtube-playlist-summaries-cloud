<!-- codex-review: model=gpt-6.1-terra -->

- **BLOCKER — A foreign listener can be reported as ours and signalled.** [scripts/explainer-serve.py:1526](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/e631/scripts/explainer-serve.py:1526) treats an occurrence of the script’s path anywhere in `ps` output as proof that the process runs the script. I started a different Python HTTP server on an ephemeral port with the script path as an extra argument and put its PID in the per-port pidfile. `--status` returned 0 and reported “ours, older code”; `--stop` returned 0 and terminated it with SIGTERM. The fold caused this remaining X2 failure. The self-test’s legacy stand-in also passes the script path as an extra argument, so its positive control endorses this false identification.

- **MAJOR — Existing servers on non-default ports lose their pidfile.** [scripts/explainer-serve.py:165](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/e631/scripts/explainer-serve.py:165) considers `.serve.pid` only on port 7391, but master writes `.serve.pid` even when `EXPLAINER_SERVE_PORT` is set. A pre-branch server on another port therefore has no recorded PID from HEAD’s perspective: start and status reject its listener, and stop reports “not running” without stopping it. This fold-caused gap leaves X5 incomplete.

- **MAJOR — A record-write failure can leave a running, unmanageable child.** [scripts/explainer-serve.py:2600](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/e631/scripts/explainer-serve.py:2600) writes the identity after forking, outside any cleanup handler. For example, if `.serve.<port>.token` is a directory or the filesystem rejects the write, the parent raises while the child can bind and keep serving; the parent neither reaps it nor produces usable records. This was caused by the fold.

- **MAJOR — Concurrent starts can overwrite the winning server’s records.** [scripts/explainer-serve.py:2600](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/e631/scripts/explainer-serve.py:2600) writes before establishing which child bound the port, without serializing starts. Two starts that both see a free port can write different identities; if the loser writes last, the winner’s token no longer matches the record. The winner may then be left running while subsequent status and stop reject it. This race was caused by the fold.

The requested self-test completed: **334/334 passed**. Its coverage supports the ordinary X1, X3, X4, X6, X7 and X8 scenarios, and X10’s limitation is documented. X9 has added cases and mutations, but the passing suite does not catch the legacy false positive above. I did not independently reproduce every round-1 scenario or run every mutation, nor verify the Linux-specific parsing, multiple-listener and symlink cases; those remain review limits. The inspected `lsof` failure path fails closed, which also means a real legacy server cannot be managed when `lsof` is unavailable. No process on port 7391 was touched.

## Loosening answers
LOOSENING-CHECK b2e4eac449b5: not a loosening
LOOSENING-CHECK 788ef2f927e5: not a loosening
LOOSENING-CHECK bc2f5b58709f: not a loosening
LOOSENING-CHECK d1873ad3ae0b: not a loosening
LOOSENING-CHECK f4631f9b0c4f: not a loosening
LOOSENING-CHECK d30f34f027ed: not a loosening
LOOSENING-CHECK ae4248e994e5: not a loosening
LOOSENING-CHECK 9728b8b30a53: not a loosening
LOOSENING-CHECK e3a4cb7e2c09: not a loosening
LOOSENING-CHECK f282f6e86a7d: not a loosening
LOOSENING-CHECK 1fa8feb292f4: not a loosening
LOOSENING-CHECK 07f7ec40b017: not a loosening
LOOSENING-CHECK d9dbaca13512: not a loosening
LOOSENING-CHECK 9b05c65c83f3: not a loosening
LOOSENING-CHECK 3c20a80eb0ff: not a loosening
VERDICT: NOT CONVERGED

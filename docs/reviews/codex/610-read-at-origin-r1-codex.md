<!-- codex-review: model=gpt-6.1-sol -->

1. **MAJOR — `scripts/goal-tree.py:983,1062`: successful fetch can leave `origin/master` stale.**  
   Concrete input: configure `remote.origin.fetch=+refs/heads/other:refs/remotes/origin/other`, retain an older `origin/master`, then advance remote master. In a temporary repository, `git fetch --quiet origin master` returned 0 and updated `FETCH_HEAD`, while `origin/master` remained unchanged. The branch consequently reads stale documents and presents them as current. With that tracking ref absent, the document reads instead fail despite a successful fetch. The new tests mock fetch success without checking which ref it updates.

2. **MINOR — `scripts/goal-tree.py:622`: the recommended catch-up command fails on divergence.**  
   Concrete input: HEAD and `origin/master` each have one unique commit. I reproduced `HEAD...origin/master` counts of `1 1`; the page recommends `git pull --ff-only`, which exited 128: “Not possible to fast-forward, aborting.” The behind count itself is correct, but the remedy is misleading. Neither the tests nor the eight mutations exercise divergence.

3. **MINOR — `scripts/goal-tree.py:2557`: backlog-link existence still comes from the checkout.**  
   Concrete input: refreshed master contains a new row referenced by a dashboard ask, while the checkout lacks that row. `collect()` reads the new ask, but `publish_rows(root)` reads local `docs/backlog.md` (`scripts/gen-backlog-page.py:4329`), causing its valid backlog reference to render without a link. I invoked `publish_rows()` on a temporary older backlog and confirmed `key_link("backlog", 999)` returned `None` for a row absent locally. This leaves two inconsistent backlog views within one page.

4. **MINOR — `scripts/goal-tree.py:1062–1065`: the Git read silently accepts invalid UTF-8 that the disk read refused.**  
   Concrete input: a committed backlog containing otherwise valid rows followed by `invalid: \xff`. I reproduced a `UnicodeDecodeError` from the former strict UTF-8 disk read, versus successful `git show` through `_SS._run`, replacement with U+FFFD, and no `row_fates()` problems. `_SS._run` uses locale decoding with `errors="replace"` (`scripts/session-state.py:165`). Thus malformed source bytes can now be treated as successfully read. Trailing-newline removal and CRLF conversion did preserve both parsers’ fixture results in my probes.

5. **MAJOR — `scripts/goal-tree.py:4272–4305`: tests do not pin successful dashboard reads to master.**  
   Concrete wrong implementation: after a successful dashboard `git show`, discard its output and use the checkout’s dashboard instead; retain the correct shared backlog behavior. I applied this mutation **in memory only** and ran the complete self-test: **486/486 passed**. The original implementation also passed 486/486. The eight new mutations include reverting both document reads together, but no dashboard-only reversion; their backlog-fates assertion cannot establish dashboard freshness.

The replay path correctly omits the lag line, and the lag metadata is excluded from derived snapshots. The ledger and plans retain their documented local sources. Thread declarations and answers also remain checkout reads (`:2507,2529,2427`), so those contents still require checkout updates.

## Loosening answers
LOOSENING-CHECK d97f64a842ee: not a loosening
LOOSENING-CHECK 57d1d721c380: not a loosening
VERDICT: NOT CONVERGED

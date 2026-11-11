<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 98e7877d82566261f881f2c3803297886d13d296

Round 4, Codex half; `merge-delta`, PR #491, backlog #426. Read the r1–r3 coordinator history and reviewed the r3 fold. REVIEW GAP: claude — alternation.

1. **High — BLOCKER: yes — text decoding collapses distinct filenames, producing a false CLEAR.**  
   `scripts/check-review-recorded.py:1039`, `:1195`, `:1112`.

   Concrete fixture, reproduced on this Mac with Git 2.49.0 and Python 3.14.4:

   - At the reviewed commit, create `scripts/a\n.py` and `scripts/a\r.py`, both containing `reviewed\n`.
   - After review, change only `scripts/a\n.py` to `UNREVIEWED\n`.
   - Add a review document and a usable verdict pointing to the reviewed commit, with `dirty: {}`.
   - Run the checker against the pre-branch base.

   `subprocess.run(text=True)` performs universal-newline conversion, translating the carriage return in the second filename into a newline. Both entries therefore become the dictionary key `scripts/a\n.py`. The unchanged CR-named entry overwrites the edited LF-named entry. HEAD and the synthetic merge consequently agree on the **wrong equal entry**.

   The complete CLI returned **exit 0**:

   ```text
   ok — the final tree was in the tree handed to fixture.verdict.json
   ```

   The actual edited blob was `9e027e7403567120d09a013600c8e2f40f222f29`; both compared entries instead held the unchanged blob `8f1188e8bde9a1f689e8575eea578c4ed46e7f8e`.

   **Fix-induced:** full-tree listing admits the unrelated colliding entry. This meets the round-cap BLOCKER test: a measured false green on a normal developer machine, with a local fix in the changed script. Capture Git output as bytes and explicitly decode with UTF-8/surrogateescape, preserving CR bytes; add this collision fixture.

2. **Medium — BLOCKER: no — surrogateescape is incomplete in the branch-level diff readers. FILE for backlog.**  
   `scripts/check-review-recorded.py:1428`, `:1487`.

   Concrete fixture: use `update-index --cacheinfo` to commit a pathname containing raw byte `0xe9`, such as `scripts/caf\xe9.py`. Calling either `changed_paths("base")` or `added_paths("base")` raises:

   ```text
   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 ...
   ```

   Both subprocess calls still use strict text decoding. The new `_git` and isolated-runner settings do not cover them. This prevents completion rather than clearing unreviewed code, so it is **not a BLOCKER**. Apply byte-preserving decoding consistently to these readers too.

Verification completed:

- Self-test: **275/275 passed**.
- Required scoped mutation sweep: **102 killed, 102 attributed, 0 survivors**, exit 0. This is the requested diagnostic slice.
- Real-Git probes correctly charged gitlinks, symlinks, case-distinct entries under `core.ignorecase=true`, file/directory transitions, and a guarded file renamed into prose with rename detection configured on.
- Failed HEAD listing refused to clear; unresolved `onto` kept guarded paths charged.
- Full-tree listing plus parsing: **4,375 entries, 447,010 bytes; 30 runs, median 25.8 ms, maximum 33.3 ms**. No material performance finding.
- Temporary `node_modules` symlink removed; repository status unchanged. Did not read `.claude/plans/` or edit repository files.

VERDICT: NOT CONVERGED

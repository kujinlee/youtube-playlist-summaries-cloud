<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — ` b/` inside a path invents a rename.** `scripts/check-merge-ready.py:531`. In a scratch repository, changing only `.claude/hooks/a b/z` from mode `100644` to `100755` produced real `git diff -U5 -M --no-color` output:
   ```text
   diff --git a/.claude/hooks/a b/z b/.claude/hooks/a b/z
   old mode 100644
   new mode 100755
   ```
   `diff_files()` returned old path `.claude/hooks/a` and new path `z b/.claude/hooks/a b/z`. `hold_reasons()` falsely reported an out-of-scope rename and HOLD. The lazy header split chooses an embedded ` b/` delimiter; mode-only diffs have no subsequent path headers to repair it.

2. **Medium — valid quoted Unicode paths can crash `_unquote()`.** `scripts/check-merge-ready.py:503`. With `core.quotePath=false`, deleting `.github/workflows/gat<TAB>😀.yml` emitted literal Unicode inside Git’s quoted path. Passing that real diff to `diff_files()` raised `UnicodeEncodeError` at `.encode("latin-1")`, preventing a readiness verdict. A separate quoted path containing `é` silently decoded to `�`. Decode Git escapes while preserving literal Unicode.

3. **Medium — gaining a role is incorrectly classified as losing one.** `scripts/check-merge-ready.py:650`. Executed a real, 100%-similarity rename from `scripts/check-old.sh` to `scripts/check-schema-gates.sh`. The code role survives; the destination additionally has the caller role. Nevertheless, comparing role tuples with `!=` yields HOLD, claiming “nothing runs it as a gate any more.” Test whether an **old role disappears**, rather than whether any role changes.

Executed verification:

- Required self-test: **146/146 passed**.
- Green control followed by all **50 mutations** applied independently in memory: **50/50 killed through their named cases**.
- First-parent replay over 40 commits at `origin/master`: **8/40**, matching the documented PRs.
- Additional real Git probes covered escaped quotes, backslashes, tabs, leading spaces, quoted renames, a gitlink, symlinks, and a binary rename.
- Historical replay and mutation claims reproduced; the three findings above contradict the current path-identity and role-preservation claims. The script’s stated detector bounds remain applicable.

VERDICT: NOT CONVERGED

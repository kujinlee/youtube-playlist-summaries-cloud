<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `2dee42b2` against `origin/master`, using temporary copies. One finding remains.

1. **Major — pre-existing: aliases traversing the retired symlink remain current.**

   **Location:** `scripts/explainer-serve.py:836`; overstated guarantee at `pr389.md:12`.

   **Reproduction:** In a temporary served root:
   ```sh
   printf 'STALE work-lines page' > live.html
   ln -s live.html work-lines.html
   ln -s work-lines.html 2026-10-28-alias.html
   ln -s 2026-10-28-alias.html 2026-10-28-chain.html
   ```
   Through the real HTTP handler:

   - `/work-lines` and `/work-lines.html` redirect to the archive.
   - Both dated aliases return **200 with stale content**.
   - `/` lists both aliases; `/latest` selects one.

   Resolution erases the intermediate retired name, while `retired_as()` explicitly excludes a symlinked retired entry from inode comparison. I reproduced the same failure at round 2’s `4b8dda56`, confirming this is an unresolved pre-existing bypass.

   **Fix:** Preserve the symlink traversal identities and retire aliases whose traversal passes through the retired entry. Apply that classification to serving and listing, while preserving direct access to an independently live target. Add handler, index and `/latest` regression cases. Until fixed, narrow the PR’s alias guarantee.

The remaining checks held:

- Re-ran the round-2 reproductions, including the missing-main-plans-directory and display-label collision arrangements.
- Hard links, aliases of a regular retired file, symlink chains, symlinked directories, Unicode case folding, NFC/NFD spellings, trailing dots/spaces, encoded slashes and below-root aliases produced no additional bypass.
- Coordinator scan: **666 strings, 2,760 six-word windows, zero hits**. Its historical positive control produced five hits. Expanded checks covered wrapped quotations, shorter fragments, full plan contents and slugs; no additional private disclosure was established. Slug matches already exist on `origin/master`.
- All **348 scoped mutations** were killed by their named cases, with green controls and re-controls. Retirement reasons are recorded. Actual and expected global totals both equal **2,504**.
- All nine edited scripts’ self-tests pass. The retirement docstring states its regular-file restriction; the PR’s broader alias claim fails the reproduction above.

Repository unchanged.

VERDICT: NOT CONVERGED

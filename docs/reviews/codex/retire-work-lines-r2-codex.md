<!-- codex-review: model=gpt-6.1-sol -->

Reviewed HEAD `4b8dda56` against `origin/master`, with execution in temporary copies. Four findings remain.

1. **High — FIX-INDUCED: a real plan objective survives the public-content scrub.**  
   **Location:** `docs/reviews/claude/retire-work-lines-r1-claude.md:58`  
   **Reproduction:** The added review quotes [a plan objective — redacted pending backlog #194]. This matches the `serving:` line in the main checkout’s gitignored `.claude/plans/banner-thread-armed.md:3`. It is real plan content, not a synthetic fixture. The review artifact entered in `c1f945b8` and survives `4b8dda56`.  
   **Fix:** Redact the objective excerpt and scan review artifacts for partial quotations too. `pr389.md:19` overstates withholding: searching complete objective/step strings misses this excerpt.

2. **Major — FIX-INDUCED: resolving a symlink erases the retired filename.**  
   **Location:** `scripts/explainer-serve.py:808`  
   **Reproduction:** In a temporary served root:
   ```sh
   printf 'STALE current work-lines page' > live.html
   ln -s live.html work-lines.html
   ```
   Through the real HTTP server, both `/work-lines.html` and `/work-lines` return **200 with STALE content**. The round-1 implementation redirected the exact retired URLs regardless of their filesystem targets; the fold introduces this regression.  
   **Fix:** Check the normalized requested identity as well as the resolved target. Symlink resolution must not discard retirement of the requested name.

3. **Major — pre-existing: mixed-case URLs bypass retirement on the supported macOS filesystem.**  
   **Location:** `scripts/explainer-serve.py:809`  
   **Reproduction:** With an ordinary stale `work-lines.html`, real HTTP requests for `/WORK-LINES.html` and `/WoRk-LiNeS.hTmL` return **200 with stale content**. `/work-lines.html` returns 302. The filesystem resolves these spellings to the same file, while `RETIRED_FILES` membership remains case-sensitive.  
   **Fix:** Match filesystem-equivalent identities, respecting filesystem case behavior, and add handler-level cases. The PR’s “any spelling” claim is currently false.

4. **Medium — pre-existing: the index still advertises retired-file symlinks as current pages.**  
   **Location:** `scripts/explainer-serve.py:761`  
   **Reproduction:** Keep stale `work-lines.html`, then:
   ```sh
   ln -s work-lines.html 2026-10-28-work-lines.html
   ```
   `/` lists `2026-10-28-work-lines.html` with its current timestamp; `/latest` redirects to it. Following that alias subsequently redirects to the archive, but the listing itself presents work-lines as current. The index filters lexical filenames rather than the canonical identity used by serving.  
   **Fix:** Apply retirement classification to listing candidates, including resolved aliases.

The remaining checks held:

- The original missing-main-plans-directory and display-label-collision reproductions pass.
- All nine edited scripts’ self-tests pass.
- All **344 scoped mutations were killed and attributed to their named cases**, with green controls and re-controls. The truncated expectation is fixed.
- Retirement reasons are recorded; actual and expected global totals both equal **2,500**. The PR’s 2,495 figure is explicitly historical.
- Encoded and normalized round-1 URLs redirect. Double encoding, backslashes and bare trailing slashes tested did not expose stale content.
- The archive accurately describes its retained metadata/counts and withheld contents; the rendered goal tree links it once.
- The dashboard overlap remains the previously recorded deferral.

Repository unchanged.

VERDICT: NOT CONVERGED

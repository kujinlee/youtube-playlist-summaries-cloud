<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `1d6091d0` against `origin/master`, executing attacks and mutation sweeps in temporary copies. One finding refutes the bet.

1. **Major — FIX-INDUCED: an extensionless request can serve a retired hard-link fallback.**

   **Location:** `scripts/explainer-serve.py:884–885`; contradicts the hard-link guarantee in `pr389.md:15`.

   **Reproduction:** In a temporary served root:
   ```sh
   root=$(mktemp -d)
   printf 'STALE work-lines page' > "$root/work-lines.html"
   mkdir "$root/alias"
   ln "$root/work-lines.html" "$root/alias.html"
   ```
   Set the imported server module’s `ROOT` to this directory and issue `GET /alias` through `Handler`.

   **Observed:** A real HTTP connection returns **200 containing stale content**. `retirement()` classifies the existing `alias` directory as live and returns immediately. `resolve_page()` skips that directory and serves `alias.html`, whose hard-link identity never gets classified. Everything is inside the served root; no symlinked directory component is involved.

   The identical fixture at round 3’s `2dee42b2` returns **302 to `/work-lines-archive`**, confirming a regression from the fold.

   **Fix:** Share candidate selection between classification and serving, preserving the selected candidate’s unresolved path for chain inspection. Do not let an existing directory suppress classification of the served `.html` fallback. Add a handler regression and a named mutation for this mismatch.

The remaining checks held:

- Round-3 chain, longer chains, absolute and relative targets, and `..` targets normalizing inside the root retire correctly. Live chains of 16 links serve; 17 links, loops, and chains leaving then returning to the root receive 403.
- Symlinked directory components remain outside the documented walk; tested escapes were bounded by the resolver and returned 404. Index and `/latest` excluded retired and refused chains.
- Leak scan: **666 strings, 2,760 six-word windows, 2,036 added tracked lines, zero hits**.
- All **353 scoped mutations** were killed by their named cases, with green controls and re-controls. Retirement reasons are recorded. Actual and expected global totals both equal **2,509**.
- `pr389.md:12–17` states the intended traversal bound and directory-component exclusion, but its hard-link guarantee fails the reproduction above.

Repository unchanged.

VERDICT: NOT CONVERGED

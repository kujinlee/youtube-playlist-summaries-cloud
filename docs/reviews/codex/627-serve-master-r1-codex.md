<!-- codex-review: model=gpt-6.1-sol -->

Both suites pass: **260/260** and **115/115**. Temporary-copy mutations removing overlay validation, footer injection, and either isolation guard failed their corresponding named cases. The temporary server control passed 260/260. Repository unchanged; no GitHub actions.

1. **MAJOR — A damaged copy silently enables stale local edits.**  
   `served_page`, lines 1401–1416, treats an absent copy file as “not on master,” provided `.git/HEAD` remains valid.  
   **Reproduction:** commit page A, advance master’s page to B, leave the checkout at A with local edit E, then delete that page only from the serve copy. Before deletion, B is served with a yellow bar. Afterwards, E is served without the bar, labelled `local edits on <A> — not on master`. Master still contains B; the footer misdiagnoses copy corruption as absence from master.

2. **MAJOR — Concurrent checkout breaks the footer’s source guarantee.**  
   `served_page` records a SHA and returns a mutable pathname; `page_body` reads that pathname again. The writer’s lock does not protect these reads.  
   **Reproduction:** position the copy at A; call `s = served_page(url, setup)`; move the copy to B; call `page_body(s, url)`. Observed: **B’s bytes with `Source: master @ <A>`**. Background fetching creates this interleaving naturally. File deletion during checkout can also invalidate a previously selected pathname.

3. **MAJOR — `/` and `/latest` still hide master-only pages.**  
   Both routes return before source selection or fetching, using only `ROOT` (`do_GET`, lines 1654–1663).  
   **Reproduction:** local root contains `2026-01-01-old.html`; current serve copy additionally contains `2026-01-02-new.html`. `/` omits the new page, and `/latest` redirects to the old page. `/` also has **no source footer**. An empty/deleted local root makes `/latest` return 404 despite available master pages.

4. **MAJOR — Local retirement metadata can suppress master’s valid page.**  
   `retirement(path, ROOT)` runs before deciding which copy supplies the page.  
   **Reproduction:** master contains a normal `2026-01-01-topic.html`; replace the local file with a symlink to `work-lines.html`. Requesting `/2026-01-01-topic.html` returns **302 `/work-lines-archive`**, although `served_page` would select master’s valid page. Local state therefore bypasses the overlay rule and hides master.

5. **MAJOR — The second isolation guard fails for staged script copies.**  
   The guards are distinct, but `regen-pages._is_this_repository` returns false when its own staged directory is outside Git. It consequently cannot protect the checkout captured by the server’s module-level `ROOT`.  
   **Reproduction:** copy scripts into a temporary nongit directory; model the original `~/explainers` root with a separate temporary checkout; remove only `and not _IN_SUITE`; run the complete server self-test. I observed **an actual fetch into that separate checkout**, despite `regen-pages._IN_SUITE == True`. The suite eventually reports 259/260, after the fetch. With an ordinary HOME, the captured root can identify the real checkout. All reproduction fetches used temporary repositories and local origins.

6. **MINOR — A slow fetch serves the old copy without a freshness warning.**  
   `CopyFetcher.note()` returns an empty string while fetching unless an earlier failure exists.  
   **Reproduction:** hold `sync()` on an event, call `poke(FETCH_WAIT)`, then select the page using `note=f.note()`. The wait ends, but the footer remains simply `master @ <old-sha>`, without saying refresh is pending or timed out. If fetching subsequently fails, `/_rev` excludes the error note from its revision, so an already-open page need not acquire the failure warning.

Traversal probes covering `..`, encoded traversal, double encoding, and an escaping symlink were refused, including with local-source selection.

VERDICT: NOT CONVERGED

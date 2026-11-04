<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 668e4cc1738fce837ee8feb80fa26ef104e2082e

1. **P2 — Rule 2 silently drops `%`-formatted hrefs containing a complete forbidden literal.** `scripts/check-page-links.py:132–138`.

   ```python
   h = "/goals#%s" % slug
   h = "/pull/%s" % n
   ```

   Each produces `built_hrefs("x.py", source) == []`. `inner` suppresses children of every `BinOp`, but `_literal` handles only `Add`; consequently the `%` expression and its literal both disappear. This exceeds the documented limitation about assembly through variables. Literal-only assembly through `.format`, `join`, and `f"/goals{'#'}{slug}"` also bypasses detection.

2. **P2 — CI’s Python 3.12 reads nonexistent elements inside RCDATA.** `scripts/page_markup.py:260`; `scripts/check-page-links.py:171–184`.

   Input:

   ```html
   <a href="#fake">go</a><textarea><b id="fake">text</b></textarea>
   ```

   `ids()` returns `{"fake"}` and `check_pages()` exits **0**, reporting one checked fragment. HTML5 parsing produces textarea text and **no element with that ID**. The round-1 false-target problem survives in another HTML surface. Python 3.14 behaves differently here, making local success insufficient evidence for CI.

3. **P2 — Rule 5 passes executable invalid script content without checking it.** `scripts/check-page-links.py:203–209`; `scripts/page_markup.py:303`.

   ```html
   <script/>broken (</script>
   ```

   Browsers ignore the self-closing flag on HTML `script`; its body is `broken (`. `inline_scripts()` returns `[]`, and `check_pages()` exits **0**, claiming zero scripts parsed.

   On Python 3.12, `<script>broken (` also exits **0**: the parser emits no body event, the start token absorbs the remaining bytes, and rule 5 checks an empty string.

4. **P2 — Self-closing anchors bypass rule 1b and leave keys without a destination.** `scripts/page_markup.py:316`; `scripts/check-page-links.py:167`.

   ```html
   <a href="/x"><a/>backlog #7</a>
   ```

   `link_html()` preserves this; `unlinked_keys()` and `nested_anchors()` both return `[]`; `check_pages()` exits **0**. HTML5 parsing closes the first anchor and creates a second anchor **without `href`** around `backlog #7`. Rule 1b ignores `startend` tokens even when their `in_a` flag is true.

5. **P2 — The exemption stack is neither a complete element stack nor browser-equivalent.** `scripts/page_markup.py:310–314`.

   ```html
   <p class="key-missing">x<div>backlog #7</div>
   ```

   Browsers implicitly close `p` before `div`. The tokenizer retains the marked `p`, so linking leaves the visible key untouched and checking exits **0**.

   Conversely:

   ```html
   <span class="key-missing"><span>x</span>backlog #7</span>
   ```

   The unmarked inner span is never pushed. Its closing tag pops the marked outer span, and `link_html()` inserts an anchor inside content that should remain exempt.

6. **P2 — Unterminated comments break idempotence and receive generated markup.** `scripts/page_markup.py:277–278, 297–305`.

   On Python 3.12:

   ```text
   input: <!--backlog #7
   pass 1: <!--<a href="/backlog-table#i7">backlog #7</a>
   pass 2: <!--<a href="/backlog-table#i7"><a href="/backlog-table#i7">backlog #7</a></a>
   ```

   Browsers treat the remainder as a comment. The tokenizer exposes it as linkable data instead. An unterminated `<![CDATA[backlog #7` similarly accumulates anchors. `<plaintext>` also receives inserted anchor syntax that the browser displays literally.

7. **P3 — The offset map assigns literal suffix characters to an entire entity-like run.** `scripts/page_markup.py:327–338, 365`.

   ```text
   input:  &ampbacklog #7
   output: <a href="/backlog-table#i7">&ampbacklog #7</a>
   ```

   The intended decoded match is `backlog #7`, excluding the preceding `&`. However, `_decode_map("&ampbacklog")` assigns every decoded character the same raw interval `[0, 11)`, pulling the preceding ampersand into the link. This changes link boundaries while the checker passes.

8. **P3 — The tokenizer does not partition every input and can raise on malformed declarations.** `scripts/page_markup.py:297–303`.

   `page_tokens("</>")` returns no tokens; concatenating their raw spans yields `""`. With `</>backlog #7`, the leading three bytes remain uncovered. On Python 3.12, `page_tokens("<![foo]>")` raises `AssertionError: unknown status keyword 'foo' in marked section`. Thus the advertised total, byte-exact tokenizer contract is false.

Validation: all nine changed suites’ `--self-test` commands passed. The tokenizer and checker suites also passed under Python 3.12. `--build` passed over five pages, checking **7,914 fragments and 11 inline scripts**. Rebuilt pages and emitted fragments partitioned exactly and remained unchanged under repeated linking.

The actual `main(["--build", "--ci"])` path, with an emitted page mutated before checking to add `<p>backlog #7</p>`, returned **1**; that gate is not vacuous. Scoped sweeps passed: **36/36** tokenizer mutations and **30/30** checker mutations killed, with green controls and re-controls. Browser behavior above was corroborated with HTML5 parsing through jsdom.

No repository files were changed, the temporary dependency symlink was removed, and `.claude/plans/` was not read.

VERDICT: NOT CONVERGED

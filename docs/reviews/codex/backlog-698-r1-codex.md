<!-- codex-review: model=gpt-6.1-terra -->

1. **MAJOR — Image fallback text can hide a six-word quote.** [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:157) inserts spaces around every image’s alt text. In a fresh real build, I added:

   ```markdown
   I [almost](https://x) ne![ver](x.png) pay attention to
   ```

   When the image is unavailable and its alt text is displayed, the reader sees “I almost never pay attention to,” but `--check` returned **PASS**. The renderer view splits `ne` and `ver`; the raw view contains the link destination. Treat inline image fallback text as inline text, without unconditional surrounding spaces, and test an image embedded inside a word.

2. **MAJOR — A failed renderer can return a correctly shaped response and produce a false pass.** [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:131) validates only the number and type of returned strings. A substitute node process returning empty document strings and plausible inline strings made a directory containing the round-4 reproducer pass; the same response with `renderer error` on stderr also passed. The raw view cannot rescue a quote whose raw Markdown breaks the run. Validate the renderer and its response sufficiently to reject incomplete rendering, including stderr failures, before searching any view.

3. **MINOR — Non-UTF-8 renderer output crashes instead of returning CANNOT RUN.** At [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:124), a node substitute writing byte `0xff` raised an uncaught `UnicodeDecodeError`; expected rc 2 with CANNOT RUN. Catch decoding failures around the subprocess call.

4. **MINOR — Removing the source quote’s plain view loosens a previous refusal.** At [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:272), I changed one fixture source quote to `see [aside](https://example.com) before you merge anything` and checked output containing `see aside https example com before you merge anything`. Master returned **1**; this branch returned **0**. The output views are add-only relative to each other, but the source side no longer includes master’s plain view. Preserve it as an additional source-fragment view if the previous refusal is intended to remain.

The real build and subsequent check passed, as did the four adjacent negatives in the self-test. The suite passed 41/41. In a full external clone with `node_modules` linked, six new mutations each failed their named case; the mutation harness’s staged control reached markdown-it. The complete 34-mutation sweep was not finished. The 38-shard cost estimate was 850–986 seconds per shard, below the 30-minute PR budget, though this is an estimate rather than a CI measurement. Missing node, missing bundle and a shortened timeout produced CANNOT RUN; a 4 MB input rendered successfully. I did not establish behavior for every node version or the corpus’s eventual viewer. The documented CommonMark limitation remains relevant to viewers with extensions such as Obsidian links or GFM tables.

## Loosening answers
LOOSENING-CHECK 169c08d5f317: not a loosening
LOOSENING-CHECK 8c08951f5d7e: not a loosening
LOOSENING-CHECK de62ef368291: not a loosening
LOOSENING-CHECK 3e58e77f52b1: not a loosening
LOOSENING-CHECK ca964ae7f0eb: not a loosening
LOOSENING-CHECK 73d42d6fc6cc: finding: source quotes with real links no longer retain their plain-view destination words for matching
LOOSENING-CHECK ed4660bb0eb7: finding: source quotes with real links no longer retain their plain-view destination words for matching
LOOSENING-CHECK 250c739c54f2: finding: source quotes with real links no longer retain their plain-view destination words for matching
LOOSENING-CHECK eeaff0d7f286: finding: source quotes with real links no longer retain their plain-view destination words for matching
VERDICT: NOT CONVERGED

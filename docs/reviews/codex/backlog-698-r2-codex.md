<!-- codex-review: model=gpt-6.1-terra -->

1. **MAJOR — Mixed boundaries still let a rendered quote pass.** `fix_induced: false`; component: `corpus-views`. In [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:192), the tight reading joins every unlisted tag boundary, while the loose reading splits every tag boundary. On a real build, this input returned **rc 0**:

   ```markdown
   I [almost](https://x) ne<em>v</em>er<center>pay attention to</center>
   ```

   The browser displays the six-word group-D run “I almost never pay attention to.” The tight reading joins `never` to `pay`; the loose reading splits `never` inside the word; the raw view includes the link destination. A similar probe with a format character beside the inline tag also passed. **Expected:** rc 1. Cover combinations of boundary decisions within one run, rather than applying one decision globally.

2. **MAJOR — The branch drops refusals made by master’s link-reduced view.** `fix_induced: false`; component: `corpus-views`. Against the same real build, master returned **rc 1** for the following input, while HEAD returned **rc 0**:

   ```markdown
   [I](https://x) [almost](https://x) never [pay](extra words) attention to
   ```

   Master’s link-reduced view discarded `(extra words)` and found the quote. HEAD’s rendered view retains those visible words, and its raw view includes the URL. Restoring the plain source view at [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:245) does not restore the former link-reduced source and output views. **Expected:** preserve master’s refusal as an add-only view, with regression cases on both sides.

3. **MINOR — Whitespace-only stderr is accepted.** `fix_induced: true`; component: `renderer-call`. [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:152) uses `r.stderr.strip()`. A node wrapper that delegates to the real renderer and writes a space and newline to stderr returned rendered output successfully. The documented contract says *anything* on stderr is CANNOT RUN. **Expected:** rc 2; test `r.stderr` directly and add a whitespace-only case.

4. **MINOR — Closed `<details>` content can interrupt a visible run.** `fix_induced: false`; component: `corpus-views`. The hidden-text handling at [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl698/scripts/build-shipped-corpus.py:183) retains content inside closed `<details>`. A probe with a real link followed by `never <details><summary>zz</summary>hidden words</details> pay attention to` returned rc 0. Closed details conceal their body; a matching case with an empty summary can place the surrounding quote words consecutively in the visible text. Model closed details, including their visible summary, or explicitly state this bound.

The real build and `--check` passed, as did **51/51** self-test cases. In a full external clone with `markdown-it` copied in, six new mutations each failed its named case. The 38-shard cost estimates range from **978–995 seconds**, below the 30-minute budget. The canonical-source prefix includes the trailing slash and does not match sibling names such as `markdown-it-extra`.

The pinned probe caught the tested ordinary renderer failures, including non-UTF-8 output. A substitute that renders the probe correctly but empties other documents can still pass the probe; this is a limitation of a liveness check against a deliberately deceptive executable, rather than evidence that the installed renderer behaves that way.

## Loosening answers
LOOSENING-CHECK 169c08d5f317: not a loosening
LOOSENING-CHECK 8c08951f5d7e: not a loosening
LOOSENING-CHECK de62ef368291: not a loosening
LOOSENING-CHECK 3e58e77f52b1: finding: output with a real link and a look-alike link can pass after master removed both destinations and found the quote
LOOSENING-CHECK ca964ae7f0eb: finding: output with a real link and a look-alike link can pass after master removed both destinations and found the quote
LOOSENING-CHECK 73d42d6fc6cc: finding: source quotes no longer retain master's link-reduced reading for look-alike links
LOOSENING-CHECK ed4660bb0eb7: finding: master's link-reduced reading is absent and its refusals can pass
LOOSENING-CHECK 250c739c54f2: finding: master's link-reduced reading is absent and its refusals can pass
LOOSENING-CHECK eeaff0d7f286: finding: master's link-reduced reading is absent and its refusals can pass
VERDICT: NOT CONVERGED

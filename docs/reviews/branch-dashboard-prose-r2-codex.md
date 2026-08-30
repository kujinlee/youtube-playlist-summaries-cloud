<!-- codex-review: model=gpt-5.5 -->

NOT CONVERGED

**Low**
- [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:141): URL scanning now greedily consumes adjacent inline delimiters, losing old behaviour for URL-abutting markup.

  Code:
  ```python
  INLINE_URL = re.compile(r"https?://[^\s<]+[^\s<.,;:)\]]")
  ```
  and the scanner applies it at [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:199).

  REPRODUCED:
  ```text
  IN  https://x.y/z**bold**
  OLD <a href="https://x.y/z">https://x.y/z</a><strong>bold</strong>
  NEW <a href="https://x.y/z**bold**">https://x.y/z**bold**</a>
  ```

  Same class:
  ```text
  IN  https://x.y/z`code`
  OLD <a href="https://x.y/z">https://x.y/z</a><code>code</code>
  NEW <a href="https://x.y/z`code`">https://x.y/z`code`</a>
  ```

  I grepped `docs/dashboard-entries.md`; the real dashboard store has no `http(s)` token immediately abutting backticks or `**`, so this does not break today’s page. It is still a behaviour regression outside the two deliberate changes named in the prompt.

**Could Not Fault**
- `python3 scripts/gen-dashboard.py --self-test`:
  ```text
  193/193 passed
  ```
- `python3 scripts/check-plan-code.py --self-test`:
  ```text
  136/136 passed
  ```
- Live page checksum before and after mutation stayed identical:
  ```text
  da60e10b361dc749505c235cfb0101674eb69b0350d87445338cffccceda8ef5
  ```
- `python3 scripts/check-plan-code.py --mutate .`:
  ```text
  OK — delivered scripts mutated: 2 file(s), 53 mutation(s), 0 survivor(s)
  ```
- The 9 new manifest entries were checked individually in a scratch copy. Each failed through the exact case named by its `expect`; no survivors, no unrelated-case catches.
- Scanner totality: I fuzzed 16,000 delimiter-heavy inputs and long stress strings. I did not reproduce crossed tags, dropped output, loops, or recursion blowups.
- `_write_sandbox`: I verified normal and raising paths restore `OUT_DEFAULT` and remove the temp tree. Early `return` is covered by the context manager; exceptions inside `_self_test` are covered. `os._exit` would bypass Python cleanup by definition, but I did not find an in-code path using it.

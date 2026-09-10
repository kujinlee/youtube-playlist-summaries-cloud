# Codex adversarial review — `fix/backlog-110-parser-completeness`, round 2

**Subject:** the working diff on branch `fix/backlog-110-parser-completeness` after the round-1 fold
(`scripts/gen-backlog-page.py` + `.claude/hooks/regen-backlog-page.sh`).
**Reviewer:** `codex exec` via `scripts/codex-review.py`, model `gpt-5.5`
(`gpt-5.6-sol` / `-terra` / `-luna` returned HTTP 400 and were skipped by the wrapper).
**Verdict file:** `docs/reviews/verdicts/backlog-110-parser-completeness-r2-codex.verdict.json`
(`gate_ran=true`) — this round used a subject-named `--out`, so no stem collision.

> ⚠ The wrapper reported one watched file changed during the run
> (`scratchpad/r2.diff`, writer unattributed). It is outside the repo and outside `docs/reviews/`;
> the concurrent Claude half was running as documented. Adjudicated as backlog #92's known
> false-attribution shape, not an intrusion. `git status` showed no unexpected repo change.

Everything below the rule is the reviewer's final message verbatim.

---

<!-- codex-review: model=gpt-5.5 -->

```
$ git rev-parse --abbrev-ref HEAD
fix/backlog-110-parser-completeness

$ git diff --stat
 .claude/hooks/regen-backlog-page.sh |  11 ++
 scripts/gen-backlog-page.py         | 278 +++++++++++++++++++++++++++++++++++-
 2 files changed, 284 insertions(+), 5 deletions(-)

$ grep -n "in_table" scripts/gen-backlog-page.py | head -5
738:    # CONTIGUOUS BLOCK. ⚠ Reading is untouched: `in_table` gates the REPORT and nothing else.
739:    in_table = False
749:            in_table = after_header = False
755:            in_table = after_header = False
759:            in_table, after_header = True, True
```

Exact lines present only in this working diff:

```python
+    in_table = False
```

```bash
+echo "$OUT" | grep -E '^⚠|^   UNREAD:' || true
```

I read both round-1 review files first. I also ran:

```
$ python3 scripts/gen-backlog-page.py --self-test | tail -5
  ok    the real file parses at all (fail-closed on a restructure)
  ok    the REAL backlog has no row the parser silently skips
  ok    the REAL backlog does not contradict itself about what is closed

110/110 passed
```

**High**

[gen-backlog-page.py:747](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:747)

```python
if line.startswith("```"):
    fenced = not fenced
    in_table = after_header = False
    continue
if fenced:
    continue
```

Concrete failing input:

```python
["## Items", "~~~", "| # | Item | Status |", "|---|---|---|",
 "| 7 | example | pending |", "~~~"]
```

Measured output:

```text
rows [7]
unread ['~~~']
```

This is a healthy Markdown fenced block, but the parser reads the example row as backlog item `#7` and reports the closing fence as unread table content. The same happens for an indented legal fence:

```python
["## Items", "   ```", "| # | Item | Status |", "|---|---|---|",
 "| 7 | example | pending |", "   ```"]
```

Measured:

```text
rows [7]
unread ['   ```']
```

The fix changed what `parse` reads, but only for column-zero backtick fences. I would replace the toggle with a GFM fence recognizer: up to three leading spaces, backticks or tildes, at least three chars, and close only with the same marker char and length.

**High**

[gen-backlog-page.py:751](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:751)

```python
if fenced:
    continue
```

Concrete failing input:

```python
["## Items", "```", "example never closed",
 "| # | Item | Status |", "|---|---|---|", "| 7 | real | pending |"]
```

Measured output:

```text
rows []
unread []
```

An unclosed fence now silently drops the rest of the file from both the page and the unread report. This is round-2 damage: fence tracking moved from “reporting hygiene” into the read path. If the generator is going to skip fenced content, EOF while `fenced` is still true must fail closed with `ShapeError`, or at minimum produce an unread warning that names the fence opener.

**Medium**

[gen-backlog-page.py:783](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:783)

```python
if not line.strip():
    in_table = False           # a blank line ends a Markdown table. So does `## `.
elif unread is not None:
    unread.append(line)
```

Concrete failing input:

```python
["## Items", "| # | Item | Status |", "|---|---|---|",
 "| 5 | x | y |", "### Notes", "ordinary prose"]
```

Measured output:

```text
rows [5]
unread ['### Notes', 'ordinary prose']
```

A heading or HTML comment immediately after a table is healthy Markdown block content, but the detector reports it as an unread backlog row unless there is a blank line or exactly `## `. Another measured healthy-looking example:

```python
["## Items", "| # | Item | Status |", "|---|---|---|",
 "| 5 | x | y |", "<!-- note -->"]
```

Measured:

```text
rows [5]
unread ['<!-- note -->']
```

I would end `in_table` on any Markdown block opener after the table body, not only blank lines and `## `. At minimum: any ATX heading `#{1,6} ` and HTML comments should close the report population without warning.

**Medium**

[regen-backlog-page.sh:114](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/regen-backlog-page.sh:114)

```bash
echo "$OUT" | grep -E '^⚠|^   UNREAD:' || true
```

This two-prefix contract preserves unread details, but now drops details for every other successful warning that uses the same “⚠ summary, indented detail” shape. Concrete current producer:

[gen-backlog-page.py:2523](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:2523)

```python
print("⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:")
...
print("   The page renders and reloads; only the ask-a-question button is missing.")
```

Concrete failing output through the hook’s grep:

```text
wrote /tmp/backlog.html  (110 rows, 69 open)
⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:
   missing token: --paper
   The page renders and reloads; only the ask-a-question button is missing.
```

Hook shows only:

```text
⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:
```

The round-1 fix made the success path no longer silent, but it can now surface an unactionable warning for non-UNREAD cases. I would make `main` emit machine-readable warning blocks, or have the hook keep indented continuation lines following any `^⚠` line, not only `^   UNREAD:`.

**Low**

[gen-backlog-page.py:2090](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:2090)

```python
case("a fenced example table is neither read nor reported",
     lambda: _unread_of(["## Items", "```", "| # | Item | Status |", "|---|---|---|",
                         "| ⭐8 | bad | pending |", "```"]) == []
     and parse(["## Items", "```", "| # | Item | Status |", "|---|---|---|",
                "| 7 | real? | no |", "```"]) == [])
```

This test reddens only if column-zero closed backtick fences regress. It does not redden for the three live fence mutations above: `~~~`, indented backticks, and unclosed backticks. Add one case per mutation, especially the unclosed-fence case, because that one silently drops real rows.

Verdict: NOT CONVERGED.

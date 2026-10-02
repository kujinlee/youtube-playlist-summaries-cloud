---
name: backlog-md-stays-markdown
description: "FIRES-WHEN: about to propose converting backlog.md to JSON or another format — docs/backlog.md stays a Markdown table, not JSON — decided 2026-09-10 with the numbers; don't re-derive the question"
metadata: 
  node_type: memory
  type: project
  originSessionId: 24bed3bc-51b2-4b47-b1fe-a488b2d3db19
  modified: 2026-09-10T19:21:08.403Z
---

**Decided 2026-09-10, by the user, after measuring.** The user asked whether `docs/backlog.md` could
become a list of JSON objects so nothing has to parse tricky table delimiters. Answer: **no, it stays
Markdown** — and the reasoning is recorded here so the question is not re-opened from scratch.

**The argument FOR was real and should not be dismissed if it comes up again:** JSON's failure mode is
loud by construction. A malformed JSON file raises at parse; a malformed Markdown table degrades
*silently*, dropping a row — which is backlog #110 verbatim. If the source were structured, that
entire defect class could not be filed.

**What settled it, measured on the file that day:**

| | |
|---|---|
| rows | 110 |
| **median row length** | **2,632 characters** |
| longest row | 10,612 characters |
| rows containing backticks | 107 of 110 |
| readers | 8 scripts + 1 hook (`check-docs`, `check-backlog-closure`, `check-roadmap-consistency`, `gen-backlog-page`, `gen-goals-page`, `explainer-serve`, `page_markup`, `check-review-recorded`, `regen-backlog-page.sh`) |

Those cells are multi-paragraph prose with inline code, and the file's primary audience is a human
reading it **rendered on GitHub** — its own preamble treats that rendering as a feature. In JSON each
cell becomes one long double-quoted string with escaped quotes and `\n` per newline: worse to
hand-edit, and the GitHub view is gone. `attach_history` also diffs *historical* versions of the file
through git, so a format change breaks "what changed in this row, when" for everything before the cut.

⚠ **There is no middle path that dodges the parse.** Generating JSON *from* the Markdown still parses
the Markdown once. The only thing the format changes is whether that one parse fails loudly.

**How to apply:** if this resurfaces, the transferable part is not the format — it is that a
hand-edited source of truth needs a loud parse failure. PR #287 gave `backlog.md` exactly that.
The same question is still open for the other hand-edited sources in that file's own module —
`GROUPS`, `DEPENDS`, `ROOTS` — which is where the idea would actually pay.

See also [[backlog-110-parser-completeness-merged]].

---
name: a-positional-read-needs-a-verified-shape
description: "FIRES-WHEN: indexing or reading a parsed row, cell, column or list by position — cells[-2], [3], tail -1, split()[i] — MEASURED 2026-08-19 — a check that reads `cells[-2]` as the Status column silently read the ITEM cell on malformed rows, and closed backlog #46 and #50 while both were open; the fix is to verify the shape BEFORE the content"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-19T17:42:11.576Z
---

**A check that locates its subject BY POSITION is only as true as the shape it assumes** — and the
shape is exactly the thing nobody verifies.

`scripts/check-docs.py`'s `check_backlog_closed_markers` reads the Status cell as `cells[-2]`. Five
rows in `docs/backlog.md` carried **two** of the six columns, so for those rows `cells[-2]` **was the
Item cell**. An inline ✅ written for something else — `**✅ PROD MEASURED 2026-08-14**`,
`**(a) ✅ DONE — auto-refresh SHIPPED**` — read as a whole-row closure. On 2026-08-18 commit
`7e2e434` duly marked **#46 and #50 CLOSED. Neither was**: `lib/slugify.ts` has no NFKC call, and
the `/brief` skill still lists an open *Known gaps* section.

**Two of the three rows that commit "fixed" were false positives, and the wrong state propagated** —
into a severity triage, then into a status briefing, before anyone re-derived it. This is CLAUDE.md's
own rule failing inside the repo's own gate: *a green check over the wrong subject is an assertion in
better packaging*.

## What made it invisible

The same file also rendered wrong and nobody noticed. Measured with **GitHub's own renderer**
(`gh api -X POST /markdown`, mode `gfm`): **36 `<tr>` for 54 item rows** — items #35–#53 were
paragraphs of literal `|` text, because two stray blank lines had ended the table (a blank line
terminates a GFM table). After the fix, 56 `<tr>`, all 54 rows. **Nothing failed, so nothing said so.**

## The two rules worth carrying

1. **Verify the SHAPE before reading the CONTENT.** `backlog_shape_errors` now returns the set of
   rows whose Status cell is provably where we think it is, and the marker check consumes only
   those. Suppressing marker *advice* about an unparseable row matters as much as the check itself —
   that advice is what someone followed.
2. **Fail closed on "no rows matched".** If the row pattern stops matching, the check must say
   *verified NOTHING*, never pass. Same rule as `check_advisory_count`'s missing anchor.

## The instance-vs-class step, which came out clean for once

Ran the same shape check over every other living doc (roadmap, dev-process, plugins, review-method,
portable-practices, available-skills, README, CONTEXT): **zero** malformed rows. `backlog.md` was the
only one. Worth recording because the class check usually finds more — see
[[a-shim-can-fail-in-both-directions]], where measuring turned one name into six.

Ratchet + `--self-test` (13 cases, 2 of them this regression) shipped in **PR #116**.
Mutation-tested 5/5, each mutation turning a **named case** red.

Related: [[a-convention-catches-what-you-read]], [[a-test-that-cannot-fail]],
[[test-harness-can-launder-failures]], [[guard-operands-from-one-closure]].

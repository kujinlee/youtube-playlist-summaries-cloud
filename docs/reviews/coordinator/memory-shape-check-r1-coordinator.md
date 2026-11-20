# Round 1 — `memory-shape-check` — coordinator — ❌ NOT CONVERGED (3 High, 3 Medium)

Both halves reviewed `24edb87d` (branch `memory-shape-check`, PR #605, `scripts/check-memory-shape.py`, its
mutation manifest and its CI steps). Codex (`gpt-6.1-terra`, `docs/reviews/codex/memory-shape-check-r1-codex.md`,
2 MAJOR) and Claude (`docs/reviews/claude/memory-shape-check-r1-claude.md`, 1 MAJOR, 3 MINOR). Both were NOT
CONVERGED. Both quote the same baseline: `self-test: 50/50`, and the live run `memory shape ok — 195 files`.

```yaml
round: 1
fixes_nontrivial: true
subject: memory-shape-check
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: High, aim: deliverable, fix_induced: false, component: frontmatter-parser, disposition: fixed}
  - {id: XM2, severity: High, aim: deliverable, fix_induced: false, component: link-reader, disposition: fixed}
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: history-marker, disposition: fixed}
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: false, component: history-marker, disposition: fixed}
  - {id: Cm2, severity: Medium, aim: deliverable, fix_induced: false, component: history-marker, disposition: fixed}
  - {id: Cm3, severity: Medium, aim: deliverable, fix_induced: false, component: link-reader, disposition: fixed}
```

`X` = the Codex half, `C` = the Claude half; `M` = MAJOR, `m` = MINOR. Every finding was REPRODUCED before it was
fixed: each input was built and run against `24edb87d` first, and each gave the observation the review reported.
The new cases were then run against the OLD rule code, with the new suite attached: **59/89, 30 red**. Every
finding has at least one of the red cases.

## Fold

| Id | Finding | Reproduced on `24edb87d` | Fix | Cases (red on the old code) |
|---|---|---|---|---|
| XM1 | malformed YAML passes: `description: [unterminated` | `[]`, no violation | `scalar_problem()` refuses an unterminated `"…"` / `'…'`, an unquoted value led by a YAML indicator (`[ ] { } \` @ & * ! \| > % # , ?`) or holding `: `, and a non-blank frontmatter line with no `key:`. A refused line becomes FRONTMATTER | 6 FRONTMATTER cases + 1 direct `scalar_problem` case; 3 adjacent negatives (`"A: \"b\""`, `'it''s: fine'`, `10:30`) stay green |
| XM2 | a link inside an HTML comment counts toward reachability | `<!-- [[b]] -->` → `[]` | `link_targets` drops `<!-- … -->` first. An UNCLOSED `<!--` hides the rest of the text, as it does in HTML | UNLISTED via a comment-only link; `link_targets` on a closed and an unclosed comment |
| CM1 | `_DECORATION` lacks ⚠, and list / `(` / date-first prefixes hide `⟳` | `⚠ ⟳`, `⚠️ ⟳`, `- ⟳`, `1. ⟳`, `(⟳`, `**<date> ⟳**` → `None` | ⚠ and `(` join `_DECORATION`. A list marker (`-`, `+`, `9.`, `9)`) is stripped. Decoration and the marker are stripped until stable. `⟳` may follow a leading date | 7 HISTORY-FIRST cases, including `- ⚠ ⟳` (the until-stable loop) |
| Cm1 | `History\b` fires on a current-rule sentence | `History goes BELOW …`, `HISTORY of …`, `History-first …` → `'History'` | Outside a heading, `History` is a LABEL only: then `:`, `(`, `—`, `–` or the end of the line, through a closing bold. In a HEADING the bare word still counts (`## History and detail` is witnessed in the corpus) | 3 NOT-history cases. Every witnessed opener form stays red: 4 new cases (`## History and detail`, `## History — …`, `**History:**`, `**History**:`) and the existing `## History` / `History:` cases |
| Cm2 | `Was` is case-sensitive, and cannot cross a closing bold | `WAS:`, `was:`, `**Was** (<date>):` → `None` | Both `Was` patterns are IGNORECASE. `\**` is allowed before and after the date | 4 HISTORY-FIRST cases, including `<date> — was`; a negative where a label precedes the date stays green |
| Cm3 | MISSING fails open for an anchored, titled or aliased index link | `[x](gone.md#h)`, `[x](gone.md "t")`, `[[gone\|alias]]`, `[[gone#h]]` → `[]` | A link is read whole, then normalised: `#anchor`, `"title"`, `<…>`, a leading `./` and a wiki `\|alias` are dropped | 4 MISSING cases; an anchored + aliased index link REACHES its file; `link_targets` normalisation |

**A live defect XM1's fix found.** The live corpus held ONE frontmatter value that YAML refuses. It is in
`docs/memory/a-forced-choice-test-cannot-fail.md`:
`description: FIRES-WHEN: scoring …`, an unquoted `: `, which YAML reports as "mapping values are not allowed".
The value is now double-quoted, in this commit. The corpus, as measured: 189 double-quoted values, 796 plain values,
0 single-quoted, 0 flow-collection, 0 indicator-led. The `: ` rule has no other hit.

**Bound, now stated in the docstring.** These are NOT caught:
- a marker that is not at the line's start after decoration (`**Note:** ⟳ …`);
- a label before the date (`**MERGED <date>** — was …`). A date-then-`Was` is caught only when the date leads;
- a link inside a code span or fence. It still counts, because a reader can see it and follow it.

**Instruments.**
- Manifest: 36 → 65 mutations. Six anchors were rebound to the rewritten markers, decoration string and link
  reader. Six expects were re-aimed where the harness showed another case was the guard. 29 mutations were added.
  `check-plan-code.py --mutate . --only scripts/check-memory-shape.py` ran on a scratch copy of the tree:
  65 killed, 65 attributed, 0 survivors.
- `EXPECTED_MUTATIONS` was raised to 65.
- `check-fixture-variation.py`'s pin for this file gained `scalar_problem.value`. It was re-derived with
  `analyse()`: 8 keys, no findings.
- The docstring's declared count is now 89 cases.

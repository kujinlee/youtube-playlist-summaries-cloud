Reviewed head: 24edb87d173e4548081a91e1dd9cc461ca10aeeb

# memory-shape-check — review round 1, Claude half

Subject: `git diff origin/master...HEAD` (merge base `7a6ffa00`). The new `scripts/check-memory-shape.py`, its CI
steps, mutation manifest, registry entries, the `check-shipping-sets.py` pin 344→346, and the `docs/dev-process.md`
pointer row. All experiments ran in directories outside the repository (the session scratchpad).

## What was run (last lines quoted)

- `python3 scripts/check-memory-shape.py --self-test` → `self-test: 50/50 cases passed`, rc 0.
- `python3 scripts/check-memory-shape.py` → `memory shape ok — 195 files in docs/memory, every rule passed`, rc 0.
- Pre-audit control (`git archive 4d76f76a^ docs/memory`) → rc 1, `5 violation(s) over 181 files`: 2 FRONTMATTER
  (`a-harness-cannot-read-a-cause-from-a-childs-text.md`, `a-vendored-line-number-has-no-owner.md`) and 3
  HISTORY-FIRST (`launch-roadmap-state` ⟳, `m4-superseded-trail` and `slice-history` "Split out of"). This matches
  the docstring's CONTROL paragraph.
- Docstring reachability figures recomputed: 195 files, 138 at hop 1, 57 at hop 2. They match.
- Mutation slice, run in a `git archive HEAD` copy outside the repo:
  `check-plan-code.py --mutate . --only scripts/check-memory-shape.py` → `36 mutation(s), 36 killed, 36 attributed
  to the case each names, 0 survivor(s)`.
- Hand-built controls, with the suite run on each mutant copy. Every rule removal turns the suite red. The cases
  and pass counts:
  - drop TYPE → 49/50
  - drop NAME → 48/50
  - drop EMPTY-BODY → 49/50
  - drop HISTORY-FIRST → 38/50
  - drop the ⟳ marker → 45/50
  - drop "Split out of" → 49/50
  - drop "History" → 47/50
  - drop MISSING → 49/50
  - drop hop 2 → 17/50
  - make reachability transitive → 49/50
  - drop UNLISTED → 48/50
  - drop the `description` requirement → 49/50
  - let an empty corpus pass → 49/50
  - remove ⛔ from the decoration → 49/50
- Fail-open probes. Each corpus was built outside the repo:
  - no MEMORY.md → rc 2, CANNOT RUN
  - a `chmod 000` memory file → rc 2 (PermissionError)
  - a directory named `b.md` → rc 2 (IsADirectoryError)
  - an index with no links → rc 1 (every file UNLISTED)
  - an empty index → rc 1
  - a BOM before `---` → rc 1 (FRONTMATTER, fails closed)
  - an undecodable file → rc 2 (self-test case)

  None of these printed `ok`.
- CI: both steps sit in job `verify`, with no `continue-on-error` and no `if:`. The workflow has no path filter
  (`pull_request: branches: [master]`). Default bash `-e` fails the step on exit 1 and exit 2.
- `check-docs.py` → `Documentation integrity OK`, `docs/dev-process.md : 215 / 220 TIGHT (5 line(s) of runway)`.
  This is within budget, but the runway is now 5 lines.
- Shipping-set pin. The live edge set was computed with `check-shipping-sets.py`'s own `tracked`/`exec_edges` at
  the merge base and at HEAD: 344 → 346. Gained: `scripts/check-memory-shape.py -> scripts/fixture_git.py` and
  `scripts/check-selftest-counts.py -> scripts/check-memory-shape.py`. Lost: none. This is exactly what the re-pin
  comment claims.

## Findings

- **MAJOR — scripts/check-memory-shape.py:92:** `_DECORATION` strips ⛔ ⭐ ✅ but not ⚠. In this corpus ⚠ is the
  MOST frequent line-start house glyph (70 line starts in `docs/memory/*.md`, against ⛔ 43, ⭐ 53, ✅ 11). Because
  of this, HISTORY-FIRST misses a history opener with a one-glyph prefix. Input:
  `history_marker("⚠ ⟳ 2026-10-01 corrected")`, and the same with `⚠️`. Observed: `None`. The docstring's bound
  (lines 43–52) lists what is not caught "on purpose", and this shape is not on that list. So the stated bound is
  incomplete for the rule's primary target. Other openers are missed for the same reason. A list-item opener
  `- ⟳ …` / `1. ⟳ …` → `None`; the pre-audit corpus has a `9. ⟳` line. A parenthesised `(⟳ …)` → `None`; it is
  witnessed live mid-body at `docs/memory/a-report-format-is-a-contract.md:22`. A date-first `**2026-10-01 ⟳** …`
  → `None`. Measured: adding ⚠ to `_DECORATION` keeps the suite at 50/50 and the live run at rc 0 / 195 files. So
  the fix costs nothing on today's corpus, and it needs a new HISTORY-FIRST case (`⚠ ⟳ …`) so that the fix is
  witnessed. For list markers and `(`, either strip them too or name them in the bound.
- **MINOR — scripts/check-memory-shape.py:96:** `History\b` with IGNORECASE fires on a CURRENT-rule opener that
  starts with the word. Inputs: `"History goes BELOW the current rule."`, `"HISTORY of this rule is in
  slice-history"`, `"History-first openers are refused."`. Observed: each → `'History'` → HISTORY-FIRST. This
  fails closed, so it is noisy and not unsafe. But the rule's own subject (history-below-rule) is exactly what a
  memory about this practice would open with. The adjacent negative covers only `Historyless`. A tighter shape,
  e.g. `History` followed by `:`, `(`, or end of line or heading, would match every witnessed form (`## History`,
  `## History (condensed)`, `History: split out of …`).
- **MINOR — scripts/check-memory-shape.py:98:** The `Was` patterns are case-sensitive, while `History` and
  `Split out of` are IGNORECASE. The first pattern also cannot cross a closing bold before the date. Inputs:
  `"WAS: ask first"`, `"was: ask first"`, `"**Was** (2026-10-01): old"`. Observed: each → `None`, while
  `"**Was:** old"` and `"Was (2026-10-01): old"` fire. This marker is witnessed zero times (docstring line 39), so
  the impact is low. Either make it consistent or say "case-sensitive" in the bound.
- **MINOR — scripts/check-memory-shape.py:102:** MISSING fails OPEN for anchored, titled or aliased links in
  MEMORY.md. The regex requires `.md)` immediately, and `[[…]]` without `|` or `#`. Input: index `[[a]]` plus any
  one of `[x](gone.md#h)`, `[x](gone.md "t")`, `[[gone|alias]]`, `[[gone#h]]`, where `gone.md` does not exist.
  Observed: `[]` (no MISSING) for each. The same forms do not count toward reachability, but that side fails
  closed, as UNLISTED. Docstring line 59 defines "a link" narrowly, so this is a stated limit. But "MEMORY.md links
  resolve" is a claim of the check, and a dead `#anchor` link in the index is plausible. Either strip `#…` and a
  title, or `|alias` and `#…`, before resolving, or name these forms in the bound.

Not findings. These were checked and hold:
- Two-hop reachability is exactly two hops. `sorted(reached)` is evaluated once at loop entry, so additions inside
  the loop are not iterated. This is confirmed by the "transitive" control going red and the THREE-hop case.
- It accepts nothing beyond "linked by the index or by a file the index links". Reachability via a link placed
  inside an HTML comment or a code span in a hop-1 file is accepted. That is consistent with the stated rule, and
  it is not a defect of this diff.
- A `](./x.md)` index link reports a false MISSING. This fails closed and is not raised.

## Loosening answers

- **Does this diff loosen any existing gate?** No.
  - `check-shipping-sets.py`: the pin moves 344→346, `2cfb6a85…`→`6b80eee9…`. Verified: lost 0 edges, and gained
    exactly the two the comment names.
  - `shipping-sets.json` `expected_count` 102→103 adds only `scripts/mutations/check-memory-shape.json`.
  - `expected_mutations.py` adds a new key (36), and the harness measured 36/36 killed.
  - `check-fixture-variation.py` adds an `EXAMINED_KEYS` entry for the new file only.
  - `check-selftest-counts.py` adds the file to `POPULATION`, which tightens.
  - `check-plan-code.py` adds the path to a self-test list.
  - `sweep-costs.json` adds a new priced entry.

  No existing threshold, exemption or allow-list for another script changed.
- **Does the new check have a CANNOT RUN that could read as a pass?** No. rc 2 on absent, unreadable or empty
  input, with the words "Treat this as NOT RUN", and the CI step fails on it.
- **Is any rule's bound wider than stated?** Yes, for HISTORY-FIRST (the MAJOR above, the ⚠ / list-item / `(`
  prefixes) and for MISSING (the last MINOR). Everything else matches its docstring.

VERDICT: NOT CONVERGED

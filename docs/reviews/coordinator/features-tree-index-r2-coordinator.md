# Round 2 — `features-tree-index` (PR #624) — coordinator — fold

```yaml
round: 2
fixes_nontrivial: true
subject: features-tree-index
halves:
  codex: ran
  claude: skipped
findings:
  - {id: R2-1, severity: Major, aim: deliverable, fix_induced: false, component: fragment-ids, disposition: fixed}
  - {id: R2-2, severity: Major, aim: tests, fix_induced: false, component: gap-counts, disposition: fixed}
```

REVIEW GAP: claude — alternation

Reviewed head `a3930b57` (Codex half only). Fold commits `478e4758`, `d4ee585c`, `7147ca37`, plus this document's commit.
Neither finding came from round 1's fix: R2-1 is present at the round-0 head (ids were the bare slug), and R2-2 is
the round-1 comparator's own scope, not a regression it introduced.

## Findings

**R2-1 — a node named like a chrome control shares the chrome's id. VERIFIED, FIXED.** The features page carries
chrome ids `chrome-theme`, `chrome-refresh` and `chrome-refresh-say`. The new case renders nodes named
`chrome-theme`, `schemer`, `chrome-refresh` and `chrome-refresh-say`. It reads every id on the page back through
`page_markup.page_tokens` and runs the page's hash handler against all of them in document order. Red before the
fix: `['chrome-refresh', 'chrome-refresh-say', 'chrome-theme']` were duplicated, and 3 of 4 index links opened
nothing. `schemer` opened its card only because this page has no schemer control. Fix: `frag_id` returns
`page_markup.feature_id(<id-safe name>)`, which is `f-<name>`. This copies the `g-` prefix that `goal_id` already
uses for the same reason. `key_link("feature")` now targets `/features#f-<slug>`, so a cross-page feature link
still names the card. Today nothing in the repo calls it, but it would otherwise point at an id that no longer exists.
The stub DOM now keeps the FIRST element of a shared id, as `getElementById` does. A control (`<p id=a>` before
`<details id=a>`) shows the stub observing that. A second case shows the reservation itself: no id on a page with no
cards starts with `FEATURE_ID_PREFIX`, and `key_link('feature', s)` equals `/features#` + `frag_id(s)` for every
real slug. Round 1's injectivity property and the odd-name case still pass; they compare ids with hrefs, so the
prefix does not change them. The OPEN_HASH_JS vm cases use synthetic ids (`a`, `b`) and needed no change.

**R2-2 — the rendered-gap test compared severity totals, not row identities. VERIFIED, FIXED.** Confirmed by
construction: a fixture that renders `#999 🟠` where `#11 🟠` belongs still gives `gap_disagreements(...) == []`.
That assertion stays in the new case as the record of the blind spot. Fix: `rendered_gap_counts` also returns each
card's closed rows. `row_disagreements(page, order, expected)` reports every card whose rendered open and closed rows
(key and severity, in document order) differ from an expected set written out by hand in the self-test. The fixture's
severities are literals, so it does not depend on `sev_order`. It covers 13 open rows past `GAP_CAP` (10), with
#20–#22, #90 (plain string, `·`) and #100 capped behind "more". It also covers the shared row #100 under two
nodes, and the closed rows #91, #92 and #94. Controls, each reported: one row id swapped, one closed row rendered open,
a card on one side only, a card id two cards share, and a second severity order (the order is read). The round-1
totals case is kept: heading and index against the band, over the fixture and the real tree.

**Found during the fold:** after the prefix change, two id mutations were KILLED but UNATTRIBUTED. One was round
1's "the card's id stops reading frag_id"; the other was the new prefix drop. A self-test regex lookup returned None,
and the resulting AttributeError ended the suite before the case each manifest names had run. The lookups now read a
miss as `""` (`_found`), so the suite runs to the named case (`d4ee585c`). `check-fixture-variation` then flagged
`row_disagreements(order=)` and `rendered_gap_counts(page=)`, each passed one value at every call site. Both are now
driven at a second value (`7147ca37`).

## Verification (head `7147ca37`, before this document's commit)

- `gen-features-page.py --self-test`: 38 → 41/41. The docstring's declared count is now 41. `page_markup.py --self-test`
  205/205. `check-page-links.py --self-test` 94/94.
- Mutations, run in a full scratch clone at `7147ca37` with `check-plan-code.py --mutate . --only <script>`:
  - gen-features-page: **43 mutations, 43 killed, 43 attributed, 0 survivors**. That is +6: prefix drop,
    stub first-wins, comparator severity-only, closed rows dropped, shared-id clause, one-side clause.
  - page_markup: **80 killed, 80 attributed, 0 survivors**. That is +1: `key_link("feature")` drops the prefix.
  - Pins: `expected_mutations.py` 37 → 43 and 79 → 80.
- All-manifest anchor resolve (`load_manifests`): 107 manifests, 6,632 entries, every anchor exactly once,
  problems `[]`.
- `check-selftest-counts --only scripts/gen-features-page.py` rc=0. `check-fixture-variation` rc=0. Its ⭐ note
  about `codex-review.py` is unrelated and untouched. `check-test-counts` rc=0 (2,937 / 280). `check-docs` rc=0.
  `check-features` rc=0.
- `check-page-links --build --ci` rc=0: 4 pages, 4,974 fragment links resolve with the new ids, 0 duplicate ids.
  The goal-tree page is NOT RUN, because it needs the local log.
- NOT RUN: a real-browser pass at this head. The handler is unchanged; only the ids it receives changed.
  `check-selftest-counts --only scripts/page_markup.py` is CANNOT RUN: page_markup is not in that check's population.

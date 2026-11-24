# Round 1 — `features-tree-index` (PR #624) — coordinator — fold

```yaml
round: 1
fixes_nontrivial: true
subject: features-tree-index
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: fragment-ids, disposition: fixed}
  - {id: XM2, severity: Major, aim: tests, fix_induced: false, component: gap-counts, disposition: fixed}
  - {id: XM3, severity: Major, aim: tests, fix_induced: false, component: hash-handler, disposition: fixed}
  - {id: CM1, severity: Major, aim: tests, fix_induced: false, component: hash-handler, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: prose, fix_induced: false, component: dashboard-entry, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: tests, fix_induced: false, component: gap-counts, disposition: fixed}
  - {id: Cm3, severity: Minor, aim: deliverable, fix_induced: false, component: hash-handler, disposition: fixed}
  - {id: Cm4, severity: Minor, aim: deliverable, fix_induced: false, component: layout, disposition: fixed}
  - {id: Cm5, severity: Minor, aim: deliverable, fix_induced: false, component: layout, disposition: fixed}
  - {id: Cm6, severity: Minor, aim: deliverable, fix_induced: false, component: absent-card, disposition: deferred}
```

Reviewed head `96d8f2e8` (both halves). Fold commits `48bf60b7`, `d4c46668`, `2151d6bc`.
XM3 (Codex) and CM1 (Claude) are one defect, fixed once.

## Findings

**XM1 — fragment links break for names with URL-significant characters. VERIFIED, FIXED.**
`check_features.parse_features` takes the heading text verbatim as the slug, so `### 100% complete` is a valid node.
Red before the fix, with the handler RUN: the odd-name case opened 8 of 9 (`100% complete` failed: its `%` made
`decodeURIComponent` throw), and the malformed-hash case observed `URIError: URI malformed`. Fix: `frag_id` — the
one id function read by both the card's `id` and the index link's href. Any character outside `[A-Za-z0-9-]`
(including `_`) becomes `_<hex>_`, so the map is injective and the result contains no character a browser
percent-encodes. The handler compares and looks up the hash verbatim and no longer decodes it. Case
`every node name, however odd, gets a distinct id its index link opens when RUN` covers `# ? % space & é _`.
It includes the pair `s p` / `s_20_p`, which a version that left `_` unencoded would merge (measured: without that
pair, that mutation SURVIVED; with it, the mutation goes red). Real slugs are all `[a-z0-9-]`, so their ids are unchanged.

**XM2 — count tests derive the expectation from the code under test. VERIFIED, FIXED.** The old real-tree case
compared `gap_label(open_gaps(...))` with the index. That is the same function on both sides. The markup also could
not tell the reader which listed rows were closed. Fix: closed rows render as `frag closed`. `rendered_gap_counts`
reads the heading summary, the index line and the band's open rows back from the HTML with regexes, and shares no
code with `open_gaps`/`gap_label`. `gap_disagreements` compares them. The fixture covers rows past `GAP_CAP`, two
closed rows, a plain-string row, and a row shared by two nodes. The case also runs over the REAL page. Controls: the
reader is driven at a second page and a second order, and `gap_disagreements(page, [])` must flag both gapped cards.
Red before the fix: both fixture cards and 19 real cards disagreed, because closed rows were indistinguishable.
Mutation `the Known-gaps band drops its first open row…` (`for e in shown[1:]`) names it.

**XM3 / CM1 — the hash handler was asserted by tokens. VERIFIED (Claude measured five surviving removals), FIXED.**
`run_hash_script` runs the page's own emitted script (the `<script>` that is not the chrome script) under `node`.
Each scenario gets a fresh `vm` context with a stub window/document/location whose listeners are captured and fired.
Five cases, one per behaviour: load, hashchange, re-click of the current hash, non-`<details>` target, and
missing id + malformed escape. A control case shows the stub observes a failure (an inert script opens nothing).
A missing `node` is a `CANNOT RUN` string that fails the cases, never a pass. The five removal mutations Claude listed
are manifested against the case each one breaks.

**Cm1 — dashboard entry count. FIXED:** `Self-test 19 → 38; mutation pin 16 → 37`, plus a line on the fold.

**Cm2 — `gap_label`'s plain-string and unranked-glyph clauses untested. VERIFIED, FIXED.**
`gap_label(["plain", {"sev": "🔶"}, …])` == `3 gaps (1🟡 1· 1🔶)` was added to the gap-summary case, with two
mutations. The first mutation run showed the unranked-glyph raise went red with NO `[FAIL]` line (unattributable).
The call is now wrapped (`_caught`), so a raise becomes the case's observed value.

**Cm3 — malformed escape throws. VERIFIED (red, `URIError`), FIXED** by XM1's change: nothing is decoded.

**Cm4 — index below the first phone screen. VERIFIED, FIXED.** The build note now follows the index. At 390×844 the
index starts at y=480, and the first link is at y=585 (was ≈734 for the index label). Build note at y=2174.

**Cm5 — fold marker orphaned at 390px. FIXED.** The marker hangs off `.slug::before`, so it wraps with the slug.
Measured over every card summary at 390, light and dark: no `.slug` whose first line box is the marker alone.
Screenshot `features-r1fold-390-light-open.png` shows `▾ explanation-on-demand` on one line.

**Cm6 — absent card's reason behind the fold; "not built · 0 gaps". DEFERRED — owner's call.** The reviewer labelled
it transitional/cosmetic and the owner's decision. It is a presentation choice (open absent cards, or move the
reason into the summary, or `—` for 0), not a defect in what is counted.

## Verification (head `2151d6bc`)

- `gen-features-page.py --self-test`: 31 → 38/38.
- Mutations (full scratch clone at `2151d6bc`, `check-plan-code.py --mutate . --only scripts/gen-features-page.py`):
  **37 mutations, 37 killed, 37 attributed to the case each names, 0 survivors**. The run at `48bf60b7` had one
  survivor (the `_` encoding) and one unattributable kill (the unranked glyph); both were fixed in `2151d6bc`.
  Manifest 27 → 37 (`expected_mutations.py` pinned 37). All-manifest anchor resolve: 107 manifests,
  6,625 entries, every anchor exactly once, `load_manifests` problems `[]`.
- `check-fixture-variation` rc=0; `check-selftest-counts --only scripts/gen-features-page.py` rc=0
  (`--changed` stalled past 10 min and was killed: NOT RUN); `check-test-counts` rc=0 (2,937 unit / 280 suites);
  `check-docs`, `check-features`, `check-dashboard-entry --base origin/master` ("an entry block was added") rc=0.
- Real browser (Playwright, 390×844, light and dark, page built from this head): `scrollWidth == 390`; an index
  click opens `explanation-on-demand`; folding it and re-clicking the same line reopens it; loading
  `#%E0%A4%A` raises no page error. Screenshots: `.screenshots/features-r1fold-390-{light,dark}{,-open}.png`.

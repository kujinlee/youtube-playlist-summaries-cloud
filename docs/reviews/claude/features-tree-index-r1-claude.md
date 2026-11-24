Reviewed head: 96d8f2e8c9b7d99759ec5cf8f57b1e17f8048122

# PR #624 (features-tree-index) — round 1, Claude half

Scope: `git diff origin/master...HEAD` — `scripts/gen-features-page.py` (tree index, `open_gaps`/`gap_label`,
folded `<details>` cards, `OPEN_HASH_JS`), `scripts/mutations/gen-features-page.json` (+11),
`expected_mutations.py` pin 16 -> 27, one dashboard entry.

## What was run

- `python3 scripts/gen-features-page.py --self-test` -> 31/31 pass (1.7 s).
- Page built to scratch (`--out .../ft1/features.html`: 35 nodes, 31 built, 4 absences, 967 fragments) and served
  over local HTTP; driven in Chromium (Playwright) with real clicks and real navigations:
  - index click on `explanation-on-demand` -> URL hash set, that card `open`, top at 43 px (under the sticky chrome
    bar), the only open card; heading reads `BUILT 24 gaps (6🟠 13🟡 5🟢)`; band shows 10 rows + `14 more · 2 closed`
    = 24 open, equal to the count.
  - fold the card by clicking its summary, scroll to top, click the SAME index link again (no hashchange) -> reopens.
  - fresh load (`about:blank` first) with `#wake-on-visit` (a `####` child whose parent card is folded) -> the child
    opens and is visible; only it is open.
  - `#no-such-node` -> nothing opens, no scroll, no console error.
  - `#%E0%A4%A` -> uncaught `URIError: URI malformed` (see m3).
  - 390x844, light and dark: no horizontal overflow (`scrollWidth == 390`), no clipped index line or summary.
- Mutation probes: candidate edits applied IN MEMORY to the module source (exec with the real `__file__`), then
  `self_test()`. Two controls (`el.open = false`, closed rows counted) went red (rc=1), so the probe can detect a kill.

## Owner's two complaints — answered?

- "doesn't show feature list and hierarchy": yes. The index is the first content block, group -> `###` -> `####`
  nested with a rule line, every line linked. Desktop 1280x900: index starts at y≈515, so the first two groups are on
  screen at first glance. Mobile 390: it starts at y≈734 of 844 — only its label is on the first screen (m4).
- "'explanation-on-demand' is Built with many open backlogs": yes. `BUILT 24 gaps (6🟠 13🟡 5🟢)` sits beside the badge
  in both the index line and the folded card heading, coloured `--pending` when non-zero.

## Counting rule — refutation attempts

One function (`split_closed` -> `open_gaps`) feeds the band, the heading and the index; the band's own shown+extra
split is over the same open list. I could not construct an input where index, heading and band disagree: closed rows
are excluded everywhere; a plain-string entry is counted (as `·`) and also listed; rows past `GAP_CAP` are counted and
listed under "N more"; a two-tag row is counted under each node that lists it, which is what each line says it counts
(the `.ilab` caption states "each line counts its own node's open gaps"). The "no subtree subtotal" choice is sound
and documented at `render_index`.

## Findings

### Major

**M1 — The hash-opens-card behaviour is asserted by tokens, not by behaviour; four of its five clauses can be deleted
with the suite green.** `scripts/gen-features-page.py:916-919` checks `OPEN_HASH_JS in _tree`, `"hashchange" in
OPEN_HASH_JS` and `".open = true" in OPEN_HASH_JS`. The case NAME claims "on load and on hashchange". Measured, each
of these survives (rc=0, all 31 pass):
  - drop the load call `openFrom(location.hash);` (`:312`) — a shared link lands on a folded card;
  - drop the `hashchange` listener (`:308`) — every index click on a NEW line fails to open its card (the click handler
    only fires when `href === location.hash`, i.e. the re-click case);
  - drop the re-click handler (`:310`);
  - invert the guard `el.tagName !== "DETAILS"` -> `===` (`:302`) — nothing ever opens;
  - delete `el.scrollIntoView(...)`.
  The manifested `el.open = false` mutation is killed only because its literal token disappears — the house's
  "assert the property, not the mechanism" defect. These clauses are the whole navigation the PR adds: with the cards
  folded, a broken handler makes every index link land on a one-line summary.
  **Fix:** execute `OPEN_HASH_JS` under `node` (already required by `scripts_parse`) against a ~30-line stub
  `window`/`document`/`location` (a `getElementById` returning `{tagName, open:false, scrollIntoView(){}}`, captured
  `addEventListener` callbacks), and assert, as separate observations: (a) load with `#x` opens `x`; (b) firing the
  captured `hashchange` after setting `location.hash="#y"` opens `y`; (c) a click whose target `closest()` yields an
  `<a href="#x">` while `location.hash=="#x"` reopens a re-folded `x`; (d) a hash naming a non-DETAILS id opens
  nothing; (e) a missing id throws nothing. Then manifest the five mutations above against those cases. Missing `node`
  stays CANNOT RUN, as `scripts_parse` already does.

### Minor

**m1 — The dashboard entry states the wrong self-test count.** `docs/dashboard-entries.md:21529` says "Self-test
19 → 29"; the suite prints 31/31 and the module docstring says 31. Fix: "19 → 31".

**m2 — Two `gap_label` clauses its docstring promises are untested** (`scripts/gen-features-page.py:221-238`, both
probes survive): a plain-string entry counting as `·` (`else "·"` -> `else "?"` stays green), and "a glyph not in
`order` is shown last rather than dropped" (`rank.get(kv[0], len(rank))` -> `rank[kv[0]]`, which would raise on an
unranked glyph, stays green). Fix: add `gap_label(["plain", {"sev":"🔶"}, _g(1,"🟡")], _order)` ==
`"3 gaps (1🟡 1· 1🔶)"` to the gap-summary case.

**m3 — A malformed percent-escape in the hash throws on load.** `decodeURIComponent` at `:301` raises
`URIError: URI malformed` for `#%E0%A4%A` (observed in the console). Harmless today (listeners are registered
first), but an uncaught error on every such load. Fix: wrap in `try { … } catch (e) { return; }`.

**m4 — At 390 px the index is below the first screen.** The standfirst and the "Built …" note push `.tindex` to
y≈734 of 844, so on a phone the first glance still shows no feature list. Fix: render the index before the build note
(or collapse the note to one line), so the first screen carries at least the first group.

**m5 — At 390 px the fold marker orphans on long slugs.** `details.node > summary::before` (`:528-530`) is a flex
item of the wrapping `.nhead`; for `mutation-and-test-quality` and `hooks-and-session-continuity` the `▸` sits alone
on its own line above the slug (screenshot, dark, 390). Fix: hang the marker off `.slug::before` instead of the
summary, so it wraps with the slug.

**m6 — A declared absence's reason is now behind the fold, and its line reads "not built · 0 gaps".** `render_node`
`:623` — the absence reason was the card's distinctive content ("the half of this page the first design could not
show") and it is now hidden until opened; "0 gaps" beside "not built" invites the reading that nothing is missing.
Fix (either): render absent cards `open`, or put the one-line reason in the summary; and show "—" rather than
"0 gaps" for an absent node. Transitional/cosmetic, owner's call.

## Not findings (checked)

- Escaping: slugs go through `esc` in href, id and text; `gap_label` output is escaped; slugs are constrained by the
  `docs/features.md` grammar anyway.
- Nesting: a `####` child's card is a sibling in `.kids`, not inside the parent `<details>`, so a folded parent never
  hides a child the index links to (verified by real load of `#wake-on-visit`).
- An orphan `####` (no preceding `###`) is a top-level entry in both index and cards (`group_tree`, shared).
- Id collision: the page's other ids (`chrome-theme`, `tray`, `qt`, `qbox`, …) predate this PR and no current slug
  collides.
- The other 9 new manifest entries name cases that read the property they mutate; the `sev` field drop is caught by
  the real-tree severity cross-check.

## Counts

BLOCKER 0 · Major 1 · Minor 6

VERDICT: NOT CONVERGED

<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. **Open-state title CSS cannot match the proposed DOM**  
   Evidence: spec CSS says `details[open] .entry .title` at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:128-129`. Current cards put `.entry` on the `<article>` outside the fold at `scripts/gen-dashboard.py:995-1002`.  
   Scenario: implement the spec as written: `<article class="entry"><details open><summary><p class="title">...</p>...`. The selector `details[open] .entry .title` looks for an `.entry` descendant inside the open `<details>`, so it never un-clips the opened card title. Also, the proposed `summary{display:flex}` at spec `:126` lacks `min-width:0`/`flex:1` on `.title`, so `text-overflow:ellipsis` may not engage in a flex row.  
   Smallest fix: change the selector to `.entry details[open] .title` or `details[open] .title`, and specify `.title{flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}` plus the open override.

**High**

2. **The spec can delete the `cap` API while `_prose` still calls it**  
   Evidence: `_first_sentence` currently takes `cap` with default `TITLE_CAP` at `scripts/gen-dashboard.py:123`, and `_prose(..., drop_headline=True)` calls `_first_sentence(first, cap=len(first))` at `scripts/gen-dashboard.py:250-252`. The spec deletes `TITLE_CAP` and the truncation branch at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:163-169`, while also saying `drop_headline` is unchanged at `:180`.  
   Scenario: an implementer removes the `cap` parameter along with `TITLE_CAP`; every rendered normal entry calls `_prose(..., drop_headline=True)` from `scripts/gen-dashboard.py:1001` and raises `TypeError: _first_sentence() got an unexpected keyword argument 'cap'`.  
   Smallest fix: explicitly require either keeping `_first_sentence(text, cap=...)` as a compatibility no-op, or updating `_prose` to call `_first_sentence(first)` and adding a self-test for rendering a normal entry.

3. **Per-entry heading navigation regresses or is left undefined**  
   Evidence: current normal entries emit an `<h3>` per card at `scripts/gen-dashboard.py:995-999`. The spec replaces each card with one `<details>` whose `<summary>` is the row at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:95-112`, then claims “The title above it is now the disclosure's own heading” at `:141-142`. A `<summary>` is not automatically a document heading.  
   Scenario: a screen-reader user navigating by headings currently has entry-level stops under “What changed”; after the spec, they may jump from the `h2` “What changed” directly to the next section because no entry heading remains.  
   Smallest fix: specify the heading semantics: keep a real `h3` inside the summary row or otherwise provide an explicitly tested heading structure. Add a falsifier that counts entry headings in the What changed section.

4. **Several falsifiers can pass vacuously while the feature is absent or wrong**  
   Evidence: F1-F9 are stated at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:197-211`. Existing code already documents this exact class: `scripts/gen-dashboard.py:1520-1525` says a bare `<details` assertion passed because the glossary always emits one.  
   Scenario: F2 passes if no normal card row renders at all; F3 passes if the fixture has no badge or no summary; F4 passes if no tech fixture exists; F5 passes if no broken fixture is generated; F6 passes if all entry details are deleted; F7 passes if titles are missing or long-title fixtures do not bind to the entry card; F8/F9 pass for glossary-only details because they assert global id arithmetic, not entry-card existence. F1 can also pass against the whole page if a sentinel appears in the ask tray rather than the card.  
   Smallest fix: bind each falsifier to a parsed HTML fragment for a specific synthetic entry id. Require positive existence checks first: `details id="{eid}-card"`, its `summary`, its `.title`, its badge fixture, its nested `-tech`, and a broken-entry fixture. Use unique sentinel text not present in the glossary or ask tray.

**Medium**

5. **Entry anchor preservation is assumed, not specified**  
   Evidence: the needs tray links to `href="#{_slug(e["id"])}"` at `scripts/gen-dashboard.py:877-880`; current cards provide that target on `<article id="{eid}">` at `scripts/gen-dashboard.py:995-996`. The spec only says the new fold should have `{eid}-card` because `{eid}` is taken at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:221-223`.  
   Scenario: implementation moves the canonical id from `<article>` to `<details id="{eid}-card">` or drops it while adding the new details id. “What needs you” links still render but no longer resolve to the entry.  
   Smallest fix: explicitly require preserving `<article id="{eid}">` and add a test that every needs-tray entry link resolves to an id in the What changed section.

**Low**

6. **Deleting `_close_orphan_markup` leaves stale shared-renderer documentation**  
   Evidence: `page_markup.orphaned_delimiters` says its “one consumer is `gen-dashboard._close_orphan_markup`” at `scripts/page_markup.py:253-264`. The spec says `page_markup.py` is “untouched” at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:241-244`, while deleting `_close_orphan_markup` at `:168-169`.  
   Scenario: after implementation, the shared renderer documents a non-existent consumer and a truncation policy that no longer exists. That is not a runtime break, but it is a spec-induced documentation defect in the exact seam the spec says is out of scope.  
   Smallest fix: include a small `page_markup.py` docstring update, or explicitly retain/update the consumer relationship.

Verification run: `python3 scripts/gen-dashboard.py --self-test` passed `266/266`; `python3 scripts/check-plan-code.py --mutate .` passed with `120 mutation(s), 0 survivor(s)`.

Verdict: **NOT CONVERGED**.

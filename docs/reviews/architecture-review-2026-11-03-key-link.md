Reviewed head: ac71e3f427fd4c60051c85932bb5ea0c3b4a97e6

> **Architecture review, Phase 6, triggered by THRASHING** on PR #489 (backlog #470): two consecutive rounds carried fix-induced findings in `page-reading` (r2 X-5/X-7/X-8 from the r1 redesign; r3 C-F1/C-F3/C-F4 from the r2 split). Outcome adopted 2026-11-03: the render-time redesign is FILED as backlog #494, not folded — no BLOCKER is open at this head and round 4 (Codex) CONVERGED. The unit closes on DEFER (`docs/reviews/decision-scheme/decision-log.jsonl`).

# Phase 6 architecture review: component `page-reading` (PR #489, backlog #470)

Narrow review, triggered by THRASHING (r2 X-5/X-7/X-8, then r3 F1/F3/F4, all fix-induced, all `page-reading`).
Read-only. Nothing inside the worktree was written. The measurement wrote only to the scratchpad.

## Verdict

**THRASHING, not a prose floor.** A redesign can remove most of it, and that redesign is already the spec's own design.
**Recommendation: FILE it. Do not fold it into this PR.** No BLOCKER is open at this head (see *Is anything a BLOCKER now?*).

## 1. Class

**A writer that depends on a reader reproducing a browser.** `link_html` splices links into FINISHED HTML. So the
splice is only safe where `html.parser` and an HTML5 tree builder agree about what is text. That is an open-ended
surface (`review-method.md` §0 Q0). Each round's fix moved where the surface sits, and none removed it:

| Round | Fix | Fix-induced findings the next round found |
|---|---|---|
| r1 | regex replaced by `html.parser` (REDESIGN) | r2: 7 malformed-HTML divergences, i.e. parser ≠ browser |
| r2 | refuse outside a strict subset (SPLIT) | r3 F1 (BLOCKER): the subset was stricter than our own renderer, so **all five generators raised**. F3: the subset's model was incomplete (`<p>` closers, scope list, NBSP). F4: version claims about the parser |

F4 is prose (comments). F1 and F3 are not prose: they are the surface. **F1 is the important shape.** The SPLIT
coupled the reader's strictness to PRODUCTION. A reader that is too strict should fail a check loudly. Here it
crashed the page build, and the containment channel is PostToolUse stdout, which the r3 record itself calls weak.

`decision-log.jsonl` already recorded the r2 split prediction as refuted by F3 (r3 coordinator, *The round 2 split
prediction*). That is the stop condition for this route: the SPLIT's own falsifier fired.

## 2. The render-time option, measured

### What exists already (MEASURED, by reading the code)

- **Keys are ALREADY linked at render time.** `page_markup.scan` links `KEY_REF` (precedence: code → link → bold → del →
  em → **key** → bare URL; `scripts/page_markup.py:755-761`). `goal-tree._html_line` links through `key_segments`
  (`scripts/goal-tree.py:952-964`). So the current design has **two linkers**:
  - render time, inside 8 renderers;
  - the post-pass `link_html` over the finished page, for whatever the first one missed.
  They answer "is this a key that should be a link?" separately: `scan`'s precedence and `keys=False` on one side,
  `text_keys`/`NO_LINK` on the other. They agree because of how each is built, and because the fixed-point property
  checks it. The comment at `page_markup.py:535` ("THE ONE answer … for the linker and the checker alike") is true of
  the post-pass and the checker, but not of `scan`.
- **The spec's design IS render-time.** Spec §3 (`docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md:96-97`)
  names `key_link` and `link_keys(text) -> str` ("renders every key found in prose"). `link_html` does not appear in
  the spec (grep: 0 hits). `page_markup.link_keys` exists (`:220-226`, 7 lines) and has **0 production callers**: its
  only callers are its self-test cases at `:1006`, `:1010` and `:1264`.
- **Renderers.** There are 8 named in `GENERATOR_RENDERERS`, and they already share ONE inline renderer.
  - 7 of the 8 are `page_markup.render_inline`, `render_unlinked`, or a wrapper over `scan`:
    `gen-dashboard._prose/_inline/_inline_unlinked`, `gen-backlog-page.md` (`:827`), `gen-goals-page.inline_md`,
    `gen-features-page.inline_md/inline_unlinked`.
  - The eighth, `goal-tree._html_line`, uses `page_markup.key_segments` (it renders no markdown).
  - So "share one inline renderer" is already true. No unification is needed.

### How much key text reaches the page WITHOUT the renderers (MEASURED, by instrumenting)

**Method.** Each generator ran with `page_markup.link_html` wrapped (`scratchpad/r489/runner.py`, output to the
scratchpad, cwd = worktree, as `check-page-links --build` runs them). Before delegating, the wrapper counted:
- every key that `text_keys` still reported in an unlinked, non-exempt text node, i.e. what the POST-PASS decides,
  link or `key-missing` mark;
- the anchors the renderers had already built (`<a href="/backlog-table#i…` or `…/pull/N`).
All five generators exited 0, so every built page is inside the subset at this head.

| Page | keys linked at render time (approx., href regex) | keys only the post-pass reached | where the post-pass keys sit |
|---|---|---|---|
| goals | 175 | **0** | — |
| features | 476 | **0** | — |
| dashboard | 109 | **407** | 405 in `<pre>` of `e["tech"]` (`gen-dashboard.py:1110`, bare `_html.escape`). 2 in the needs list, a PR title (`:1005-1006`) |
| backlog-table | 1,814 | **1,364** | 1,359 in the history word-diff (`gen-backlog-page.py:1165-1169`, three bare `html.escape`). 5 in `td.what` (`plain()`, `:804`/`:2014`) |
| goal-tree | 9,039 | **116** | 111 in `pre.tree` plus 4 more. These are mostly NOT missed links: `_html_line`'s `else` branch (`goal-tree.py:963`) prints a key whose row is missing as plain text, and the post-pass then wraps it in `key-missing`. One is the literal `(backlog #389)` in the lede template (`:1010`), and one is a needs-list item (`:929`) |

**Result.** About **1,887 of about 13,500 keys (about 14%)** depend on the post-pass. They come from **7 call sites**,
about 9 lines, all bare `html.escape` (or the `_html_line` plain branch, or one template literal). Two of the five
pages depend on it for nothing.

### What the post-pass protects that render-time would not

1. **New bare-`html.escape` sites get linked automatically.** Under render-time linking, a new site that prints a key
   through `html.escape` produces an unlinked key, and **rule 1 reports it loudly**. That costs a red, not a defect.
   ⚠ **One real gap:** CI's `--build --ci` builds dashboard, backlog, goals and features, but **NOT goal-tree**
   (`check-page-links.py` CI_PAGES, said so in its docstring). So a new unlinked site on goal-tree is caught only by a
   local `--build`. The repair is to make the goal-tree page buildable from a fixture log in CI, or to accept the gap.
2. **ROWS and repo are applied in one place, at the end.** Render-time already relies on `use_rows` and `use_repo`
   running before rendering, because `render_inline` reads the `REPO` global, so nothing new is lost. goal-tree is the
   exception: it passes a per-snapshot repo, and the post-pass currently re-links with `log[-1].repo`. That is a quiet
   override today, and render-time linking would make the choice explicit.
3. **Byte preservation of the splice.** This is moot once there is no splice.

Things neither design links: a key split across elements (`backlog <del>#17</del>`), which is the same bound either way.

### Lines

The counts are MEASURED where a symbol is named (AST line spans) and ESTIMATED where marked "~".

**Deleted, linker only (the checker keeps its parser and subset):**
- `link_html` 33, `_decode_map` 10, `_RAW_PIECE` and its comment ~5, `require_subset` 5, `OutsideSubset` 7:
  **~60 lines** in `page_markup.py`;
- the 5 generator call sites (`gen-dashboard:3541`, `gen-backlog-page:4283`, `gen-goals-page:1359`,
  `gen-features-page:776`, `goal-tree:1061`);
- the 10 mutation entries keyed to the splice (keyword-classified).

**Also deleted, if the checker drops rule 0's browser-parity subset:**
- `subset_problems` 72, `_implied_close` 30, and the subset constants block (`:266-330`, 26 non-comment lines plus
  about 40 lines of comments): **~170 lines**;
- **43 mutation entries**: 39 in `page_markup.json` and 4 in `check-page-links.json` (keyword-classified);
- **~64 self-test cases**, by a keyword heuristic over 208 case lines;
- the parse5 differential.

**Added:**
- 7 sites changed from `html.escape(x)` to `page_markup.link_keys(x, REPO)`, or to `key_html` for the `_html_line`
  plain branch and the lede literal: **~10 lines, roughly line-neutral**;
- one self-test case and one mutation per converted site, ~7 + ~7;
- the r3 renderer property rewritten from "render → `link_html` → check" to "render → check". It shrinks.

`drop_cut_reference` STAYS either way. An href ending in `&quot` is a broken link whoever links it. The property that
found it is the renderer's property, not the linker's.

### Does the checker still need the subset?

The subset exists so that **a splice** can be trusted (`link_html` docstring: "no splice could be trusted"). Once
nothing splices, the checker's own disagreement with a browser costs:
- **too strict:** a loud red in CI, which is a stronger channel than the hooks;
- **too loose:** a missed unlinked key, or a missed nested `<a>`, which is cosmetic.
Neither crashes a generator. Rules 3 and 4 read ids and hrefs from parsed start tags, and are robust without the
subset. So a parser-based checker WITHOUT a browser-parity subset is adequate, and the asymmetry the brief names
holds: a strict checker fails loudly, while a strict linker crashed generators.

**Recommendation:** keep `page_tokens` for the checker, and demote or retire rule 0 when the move lands. Retiring it is
what deletes the surface. Moving the linker alone only takes the surface out of production.

The "stricter, smaller question" ("does every rendered text segment come through one renderer") is **not checkable on
a built page**, because the HTML carries no provenance. As a SOURCE rule, like rule 2, it would be noisy: there are
**109 `html.escape`/`esc(` uses** across the five generators (34, 22, 22, 24 and 7), most of them for attributes, ids
and labels. Built-page rule 1 is the better falsifier and already exists.

## 3. Is anything a BLOCKER now?

**No, on the evidence at this head:**
- all five generators build inside the subset (measured above: rc 0, `link_html` did not raise);
- the r3 property reports 0 failures over 24,056 renderer compositions;
- the parse5 differential reports 0 disagreements over 24,069 pages. That is the fold's own number. I did not re-run
  either.

**What remains is LATENT and is not a current defect.** Any future edit to a generator's TEMPLATE markup, or a bare
`html.escape` placed in a context the subset refuses, makes that generator raise. The page then goes stale, and the
only report is on the weak hook channel. That is the F1 shape, reachable from outside the 8 renderers the property
covers. It argues for filing with a priority, not for a fold at r4.

**A one-line interim, offered rather than recommended for r4:** have `link_html` return the page UNLINKED when it is
outside the subset, instead of raising, and let rule 0 and rule 1 fail the CI build. That ends the production crash
class at once. Its cost: a page outside the subset ships with up to 14% of its keys unlinked, until CI turns red.

## 4. Recommendation

**Keep the current design for this PR, and FILE a backlog row:**

> Link keys at RENDER time only (spec §3's `link_keys`): convert the 7 bare-`html.escape` sites, delete `link_html`
> and its splice, then retire or demote the browser-parity subset (rule 0) from the checker. Falsifier: `--build` reports
> 0 unlinked keys with `link_html` removed, and every generator builds when a page is deliberately placed outside
> the subset. Close the CI gap: make goal-tree buildable from a fixture log.

Why file rather than fold:
- this is round 4 under the cap;
- no BLOCKER is open;
- the change touches all five generators plus the checker, so it would need its own review rounds;
- the current design is correct over everything measured;
- the move is mostly a DELETION (~230 lines and ~53 mutation entries against ~10 added lines), so it is cheap to do
  later and not urgent.

## Measured vs inferred

**MEASURED:**
- head SHA;
- per-page counts of keys the post-pass decides (instrumented builds: 0 / 0 / 407 / 1,364 / 116), and their element
  paths and sites;
- render-time anchor counts (an href regex, approximate: it misses `key-missing` spans and thread links);
- all five generators build inside the subset at this head;
- `link_keys` has 0 production callers;
- the spec names `link_keys` and never `link_html`;
- 7 of the 8 renderers sit on `scan`/`render_inline`;
- function line spans (AST);
- 109 escape uses;
- CI builds no goal-tree page.

**INFERRED or ESTIMATED:**
- which mutations and self-test cases belong to the subset (a keyword heuristic, ±);
- the "~" line counts for comments and constants;
- that the checker without a subset fails only cosmetically or loudly (reasoned from the rules, not tested);
- that the 7 sites convert to `link_keys` with no behavioural change beyond linking (not built);
- that most of goal-tree's 116 are `key-missing` marks rather than links (inferred from sampled output, not counted).

**NOT RE-RUN:** the r3 property and the parse5 differential (the fold's numbers are cited).

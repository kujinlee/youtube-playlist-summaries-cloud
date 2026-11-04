Reviewed head: 08ffe5d69223002e7ad8aae1241d6f269e83782e

# key-link (backlog #470, PR #489): Claude half, round 1

Mandate: refute that the generated pages are still correct after `page_markup.key_link` / `link_html` landed.
Method: I built all five real pages from this head into a scratch dir, then parsed them with
`html.parser` (nesting, duplicate ids, `<a>` inside interactive elements). I extracted every inline
`<script>` and ran `node --check` on it, probed `link_html` with constructed inputs, ran every changed
suite's `--self-test` and the mutation harness per changed script, and traced the 13 dangling links to
`docs/backlog.md`.

## Findings

### F1: HIGH. The features page has 29 rows with an `<a>` nested inside an `<a>`
`scripts/gen-features-page.py:422` and `:433`:
`body = f'<a href="{esc(href)}">{inline_md(text)}</a>'`. `inline_md` goes through `render_inline` → `scan`,
which now links every `backlog #N` / `PR #N` (`page_markup.py`, the new key branch in `scan`). Any backlog
row title that cites a key therefore produces a link inside the row link.

Concrete input → output (built page, this head):
row #45, title "… unactioned when PR #98 merged" →
`<div class="frag"><a href="/backlog-table#i45">#45 🟡 M3.1 round-5 residue — … when <a href="https://github.com/…/pull/98">PR #98</a> merged</a></div>`
(features.html line 599; also #193 → PR #295, #260 → backlog #168, …).
Measured: 29 `div.frag` rows on `features.html` carry a nested `<a>`, and `html.parser` reports 33/34
nested-`<a>` events (fragment/full page).

Effect: this is invalid HTML. The parser's adoption-agency step closes the outer row link at the inner
`<a>`, so the text after the key (" merged") is no longer part of the row link, and the stray `</a>` is
dropped.

This is the defect the PR's own docstring forbids ("no `<a>` in an `<a>`", `link_html`), and the PR
already fixed it once. `gen-dashboard.py` gained `_inline_unlinked` for exactly this case (the PR-option
link, gen-dashboard `:103`, `:973`, with a case). The fix was applied to that one instance and not to the
class: `grep -nE "<a [^>]*>\{[a-z_.]*(inline|render)" scripts/*.py` finds the dashboard site, fixed, and
these two features sites, not fixed. The other generators are clean on today's data (0 nested `<a>` on
dashboard, backlog-table, goals and goal-tree).

Fix: render these two bodies with keys off. Better, give `page_markup` a public `render_inline(s, keys=False)`
or an `inline_unlinked` helper, so that `gen-dashboard._inline_unlinked` and the features sites share one
function.

### F2: MEDIUM. No check can see F1, so the guard went green over it
`check-page-links.py` rule 1 (`unlinked_keys`) strips `<a>…</a>` lazily and then looks for unlinked keys.
A nested anchor sits inside the outer `<a>` and is exempt, so `--dir` over the built pages reports no
rule-1 failure on `features`. No case, no mutation and no rule asserts "no `<a>` inside an `<a>`". The
three mutation-killed manifests (page_markup 23/23, check-page-links 16/16, gen-goals-page 28/28) all pass
over a page with 29 invalid rows.

Suggest a rule-1b, "a built page has no `<a>` opened while an `<a>` is open", with a fixture taken from the
features row above and a mutation that reverts F1's fix. That turns this class into a gate rather than a
reviewer's catch.

### F3: LOW. The closure prose says "11" dangling links; the measurement is 13 pairs over 9 rows
`docs/backlog.md` row 470 ("rule 3 RED on DATA, not code: 11 links") and the new `docs/dashboard-entries.md`
entry ("found 11 links that go nowhere") both say 11. Running `check-page-links.py --dir` on this head
gives `dangling()` = **13** page→target pairs. Those cover **9** distinct rows: 221, 241, 242, 245, 246, 247,
248, 293 and 411. Neither count is 11. State one of them and say which unit it counts.

### F4: LOW / INFO. The 13 dangling links are a real data defect, not a check bug, with a caveat
None of the 9 rows exists in `docs/backlog.md` under any marker. I checked `^\| *N ` rows, other backlog
files (there are none) and `git log -S'| 221 |'` / `'| 245 |'` (no hit: the rows never existed in the
file). Every one is cited in pre-existing prose, except `backlog #245`. On the backlog page, `backlog #245`
appears only in row 470's own new closure text. On the dashboard page, `#245` comes from the new entry.
So this PR adds citations of a row it has just reported as nonexistent.

The larger risk is the one rule 3 cannot see. Row 470's prose itself names "the backlog #242 to backlog #260
collision", a renumbering. A citation of a renumbered id that now names a DIFFERENT existing row resolves
cleanly, so it is a confidently wrong link and no rule reports it. That is worth one sentence in the bounds
of `check-page-links.py`, if nothing else.

### F5: LOW (latent). `link_html`'s `TAG_SPLIT = <[^>]*>` breaks on a raw `>` in an attribute value
`link_html('<span title="a > backlog #5">x</span>')` →
`<span title="a > <a href="/backlog-table#i5">backlog #5</a>">x</span>`, which corrupts the attribute and
leaves stray markup. On today's pages, 0 attribute values contain `>` (parsed with `convert_charrefs`),
because the generators escape with `quote=True`. So this is latent. It is reachable as soon as any
generator emits an unescaped `>` in an attribute, such as an inline handler with `=>` or a hand-written
`title`. The docstring says "Attribute values are never text", which holds only under that escaping
assumption. Say so, or make the tag split quote-aware.

### F6: LOW (latent). Goal-card ids are bare slugs in the same namespace as the chrome's ids
`gen-goals-page.py:720` emits `id="{slug}"`. The goals page also carries chrome ids: `tray`, `qbox`,
`qt`, `sendbtn`, `closebtn`, `sentnote`, `chrome-theme`, `chrome-refresh`, `chrome-refresh-say`,
`feature-map`. A goal whose slug is one of those (`SLUG` allows `tray`) would give the page a duplicate id.
The Ask-tray script's `getElementById` would then hit the goal card. No collision exists today: 0 duplicate
ids on all five pages. Threads got a `t-` prefix (`thread_id`) for exactly this reason, and goals did not.

### F7: INFO. Links now sit inside `<summary>`
These are new on the dashboard (for example `/backlog-table#i393` and `…/pull/425`), and goal-tree has
them too. Clicking the key navigates instead of toggling the `<details>`. That is valid HTML and probably
intended, but it changes the press target of those disclosure rows.

## What I checked and found correct
- **Inline JS.** Every `<script>` on all ten built files (5 full + 5 fragments, 15 scripts) passes
  `node --check`. `link_html`'s VERBATIM cut keeps script, style, textarea, title and comments
  byte-identical, `<script type="application/json">` included.
- **Attribute values.** None of the five full pages has an `<a href` or a key href inside an attribute value.
- **Duplicate ids.** There are 0 on all five pages, including the new `t-<kind>-<N>` and goal-slug ids.
  The live-tree-only rule (`render_tree_html(ids=True)`) holds.
- **Unclosed `<div>` at `</body>`** on the composed pages: this is pre-existing. It comes from
  `page_chrome`, which this diff does not touch.
- **`<a>` inside `<svg>` on backlog-table** (`href=#i19` …): these are the existing dependency-graph links,
  not this PR's.
- **Rule 2** (`--sources`) is green on the live tree. Its self-test proves it goes red on a hand-built href.
- **Mutations.** Every manifest I could run kills every mutation and attributes each one to the case it
  names, so the bindings are right.
- **Explainer and Ask-tray pages.** `link_html` is called only by the five generators' `main`, never by
  the explainer composer.

## Commands run
- `git diff origin/master...HEAD --stat`: 19 files.
- Each generator built with `--out` into scratch (`goal-tree.py --page`): all rc=0, 1–26 s.
- `python3 inspect.py <scratch>/new`: html.parser nesting, ids, `<a>` in interactive elements, and
  `node --check` per script. Result: F1 found, all JS ok.
- `python3 scripts/check-page-links.py --dir <scratch>/new` → rc=1, rule 3: 13 dangling.
  `python3 scripts/check-page-links.py --sources` → rc=0.
- Self-tests, all rc=0 except one:

  | Suite | Result |
  |---|---|
  | page_markup | 123/123 |
  | check-page-links | 36/36 |
  | gen-backlog-page | 237/237 |
  | gen-features-page | 18/18 |
  | gen-goals-page | 81/81 |
  | gen-dashboard | 326/326 |
  | goal-tree | 205/205 |
  | check-fixture-variation | 67/67 |
  | check-selftest-counts | 59/59 |
  | check-plan-code | **278/281, rc=1** |

  The 3 check-plan-code failures are all `node_modules/typescript` missing in this worktree. That is
  environmental, not this diff.
- `check-plan-code.py --mutate . --only scripts/<s>`, run on a `git archive HEAD` copy with `node_modules`
  symlinked:

  | Script | Mutations killed |
  |---|---|
  | page_markup | 23/23 |
  | check-page-links | 16/16 |
  | gen-goals-page | 28/28 |
  | gen-dashboard | 70/70 |
  | goal-tree | 115/115 |
  | gen-backlog-page | NOT RUN: stopped by me at 11/65 after 484 s; each mutation reruns a 44 s suite |

- `link_html` edge probes: F5 confirmed. `<button>` / `<option>` / `<svg><text>` get links. None occurs
  on today's pages.
- `grep`/`git log -S` over `docs/backlog.md` for the 9 dangling rows: F4.

F1 is a correctness defect on a shipped generated page, of the exact class the change set out to forbid,
and it is reachable on today's data. It is not converged.

VERDICT: NOT CONVERGED

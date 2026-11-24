Reviewed head: be768f8e6e2521a605457eb33fa06c527e562c1e

# Round 3 — `features-tree-index` (PR #624) — Claude half

Reviewed head `be768f8e` in the `features-tree` worktree. Scope: the round-2 fold (`git diff a3930b57..HEAD`) and
anything earlier rounds missed in `git diff origin/master...HEAD`. Mandate: refute.

## What was run

- `python3 scripts/gen-features-page.py --self-test` — **41/41 passed**.
- `python3 scripts/page_markup.py --self-test` — **205/205 passed**.
- Two hand mutations, each in a `git archive HEAD` copy in the scratchpad, never in the worktree (C3-1).
- `render([], {})` read back through `page_markup.page_tokens`: the ids are `chrome-theme`, `chrome-refresh`,
  `chrome-refresh-say`. None starts with `f-`.

## The three things the brief asked about, refutation attempted

1. **Every consumer of the `f-` prefix.** I grepped the whole repo for `features#`, `key_link("feature"`,
   `frag_id` and `feature_id`, skipping `node_modules`, `.git`, `.next` and `.claude/plans`. I also searched
   `~/explainers/*.html`. Every place that makes a card id or an in-page link goes through `frag_id`: the index
   line (`gen-features-page.py:277`) and the card (`:762`). `key_link("feature")` has **no production caller**.
   Its only callers are the two self-tests. The only `/features#` text in `~/explainers` is prose on the
   backlog page, inside `<code>`, not an href. `SLUG` (`page_markup.py:100`) is a subset of `_ID_SAFE`, so
   `key_link("feature", s)` and `frag_id(s)` agree for every key `key_link` accepts, and it returns `None`
   for every other key. The prefix is applied to every name, so the map stays injective: `frag_id("f-x")` is
   `f-f-x` and `frag_id("x")` is `f-x`. **Not refuted.** One stale document: C3-2.
2. **Is `row_disagreements` independent of the code under test?** `_expected_rows` uses literal ids
   (`"f-job-queue"`, not `frag_id(...)`), literal keys and literal glyphs. The fixture severities are the
   literal `_sev13`. The one input shared with the code is `_order = sev_order()`, which `glyph_of` reads.
   If that order were wrong, a glyph would read as `·` and the case would go red, so it cannot pass
   vacuously. I checked each control (swap, reopen, one-side, shared id, second order) against its
   expected value. Each one changes exactly the card it names. **Not refuted.** But the comparator reads
   every row in the band **regardless of whether it sits inline or behind "more"**. So the fold's comment
   claims coverage of the cap that nothing asserts: C3-1.
3. **Could the lookup that "reads a miss as empty" (`_found`) make a case pass vacuously?** It has four uses
   (`:1047`, `:1052`, `:1053`, `:1065`). Each is a positive membership test (`"<label>" in _found(...)`)
   expected to be `True`, or a `not in` that adds the slug to a list expected to be `[]`. `gap_label`
   never returns `""`, so a miss gives `"" → False`, or the slug is listed. Either way the case goes red.
   No `_found` result feeds a case that expects a negative. **Not refuted.**

## Findings

### C3-1 — Minor — the inline cap and the "N more" count are asserted by nothing, and the fold's comment says they are covered

`scripts/gen-features-page.py:728` (`shown, extra = entries[:cap], entries[cap:]`),
`scripts/gen-features-page.py:741` (`bits.append(f"{len(extra)} more")`) and the comment at
`scripts/gen-features-page.py:1173`. The comment says "13 open rows exceed GAP_CAP (10), so #20–#22, #90 and
#100 are the capped ones behind 'more'". The r2 coordinator document says the same.

**Failing input, run.** In a scratch copy of HEAD:

- `shown, extra = entries[:cap], entries[cap:]` → `shown, extra = entries, []` (no cap at all; every row
  inline, no "more"): `--self-test` gives **41/41 passed**.
- `bits.append(f"{len(extra)} more")` → `bits.append(f"{len(closed)} more")` (the job-queue card would say
  "2 more · 2 closed" where there are 5 more): **41/41 passed**.

`rendered_gap_counts` finds `<div class="frag( closed)?">` anywhere in the band. An inline row and a capped
row read the same, so `row_disagreements` and `gap_disagreements` cannot tell them apart. The round-1 case
that counted `GAP_CAP + 5` open rows was dropped in r2, and it only counted the total anyway. The cap itself
is not new; master has it and does not test it. What is new is a comment and a review record that claim the
fixture covers it.

**Fix.** Pick one:
- (a) Have `rendered_gap_counts` also return each card's inline rows, the `frag` divs before
  `<details class="more">`. Add `"inline": [...10 literal keys...]` to `_expected_rows["f-job-queue"]`, and
  assert that the `more` summary text equals `"5 more · 2 closed"` as a literal.
- (b) Reword the comment so it does not claim the cap is covered. Then file the cap as untested.

Severity is Minor: the counts on the heading and the index stay right, and a broken cap is a cosmetic
display fault.

### C3-2 — Minor — the spec's key table still names `/features#<slug>` as the card's fragment

`docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md:85` says
``| Feature | node slug | `/features` | `/features#<slug>` |``. Since r2, the card id is `f-<slug>`, and
`key_link("feature")` targets `/features#f-<slug>`. A reader who builds a link from the spec gets a fragment
that opens nothing. The handler finds no element, and `check-page-links` rule 3 would report it as dangling
if a generated page carried it. The goals row on line 84 is stale in the same way, and that predates this
PR (`g-` is not mentioned). Related: on master the card was `<article id="<slug>">`, so a `/features#<slug>`
link written by hand before this PR (in a note or a chat) now lands at the top of the page and opens no card.
No such link exists in the repo or in `~/explainers`, and I checked both.

**Fix.** Update both spec rows to `/features#f-<slug>` (`page_markup.feature_id`) and `/goals#g-<slug>`
(`goal_id`). Optionally, have `OPEN_HASH_JS` retry `"f-" + id` when the hash names no element, so legacy
links still open their card. Not required.

## Not run

- Mutation sweeps (`check-plan-code.py --mutate`): not run, as the brief said. The r2 coordinator records
  43/43 and 80/80 at `7147ca37`. The only mutations I ran are the two hand mutations in C3-1, in a scratch copy.
- A real-browser pass over the built `/features` page.
- `check-page-links --build --ci`.

**Verdict: CONVERGED** (no Blocker or Major; C3-1 and C3-2 are Minor).

VERDICT: CONVERGED

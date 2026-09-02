# Dashboard entries

Append-only. One `## YYYY-MM-DD` block per entry; **newest at the end**.
Nothing here is edited or deleted — corrections are appended.
Grammar: `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` §6.2.
Rendered by `scripts/gen-dashboard.py`; enforced by `scripts/check-dashboard-entry.py`.

## 2026-08-28
Started building the dashboard — a page that shows what changed while you were away.
<!--tech-->
Spec v5 merged as `c5fcb07`. Task 2 of the project-dashboard plan.

## 2026-08-29 [needs-you]
The dashboard is built and ready for you to look at. It is one page at
http://127.0.0.1:7391/dashboard with three things on it: what needs you, what changed recently in
plain words, and a small chart of how busy each of the last fourteen days was.

Two things worth knowing. Entries like this one do not get written by accident any more — a branch
that changes files and adds no entry is now refused, so the page cannot quietly stop describing the
work while still looking healthy. And if a branch genuinely has nothing worth writing, it says so in
its pull request, and the page lists those too, so you can see the rule being skipped rather than
having it happen silently.

Answers you get on a served page now also appear without you reloading it, which previously never
worked on any standing page.

**Waiting on you:** CI now checks the plan document against the code, so fixing a bug in either
script will turn CI red until the plan is edited to match. That is deliberate, but nothing says when
it stops applying, and the first person to hit it will probably just delete the check.
<!--tech-->
Tasks 1–6 of `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`. Ships
`scripts/check-dashboard-entry.py` (the ratchet, and the owner of the entry-header grammar),
`scripts/gen-dashboard.py`, the append-only store, `.agents/skills/dashboard/`,
`.claude/hooks/regen-dashboard.sh`, and the CI wiring in `.github/workflows/ci.yml` —
`fetch-depth: 0` plus a `pull_request`-only ratchet step.

Live reload: `/_rev` resolved via `safe_path` while the page GET used `resolve_page`, so
`/_rev?p=/dashboard` 404'd forever. One concern, two mechanisms; now one.

⚠ The ratchet has never been **seen to refuse on GitHub** — this PR is the first real exercise of
`fetch-depth: 0`, and a shallow clone is exactly what breaks it. Locally it passes on this branch
and refuses against `HEAD~1`.

## 2026-08-29 [resolved: 2026-08-29/1]
Decided: the CI check that keeps the plan document and the two dashboard scripts identical stays,
and it now says in writing when it goes away. It retires when the mutation checks are rewritten to
run against the real scripts instead of against copies pasted into the plan — not on a date, and not
by someone switching it off.

The reason to keep it at all: those mutation checks are the only thing proving the page's guards
still work, and they found four real defects while this was being built. The reason it could not
just stay forever unwritten: every future bug fix in either script would have paid a tax to a
document nobody reads, with no note explaining why, and the likeliest outcome was somebody deleting
the check to get a green build.
<!--tech-->
Option C of four. Condition recorded in `.github/workflows/ci.yml`'s own step comment, so the exit
ships with the thing it governs; work filed as backlog #70.

The framing that settled it: the step protects *"the mutation evidence describes the code that
ships"*. Byte-identity with `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md` is only
the route to that, and a poor one — it keeps a second copy of 1,401 lines in a tree
`scripts/check-docs.py:46` marks `FROZEN`. Retarget the 43 mutations at the delivered scripts and
the guarantee gets stronger while the byte-identity requirement dissolves. A supersession, not a
switch-off.

## 2026-08-29
Fixed: links on the dashboard were nearly invisible in dark mode. You reported it twice — first the
blue entry titles, then the purple "Elsewhere" links — and both were the same cause: the page never
said what colour a link should be, so the browser used its own, which is chosen for white
backgrounds.

Measured rather than eyeballed. Against the dark background the old colours scored 1.9 and 1.6 out
of a required 4.5 for readable text; light mode scored 8.8 and 10.4, which is why nobody caught it —
everyone who reviewed this page, including me, was reading it in light mode. The new colours score
8.9 and 8.4 in dark, 6.6 and 6.9 in light.

A test now fails if either colour goes missing again, in either mode.
<!--tech-->
`scripts/gen-dashboard.py` had no `a{}` rule at all, so `#0000EE` and `:visited` `#551A8B` came from
the UA sheet. Adds `--link` / `--link-visited` to both `:root` scheme blocks and declares
`a` and `a:visited` explicitly — `:visited` is stated rather than left to the cascade, since
browsers restrict and mis-report visited styling.

Two self-test cases, mutation-tested four ways: deleting either rule, or defining either variable in
only one scheme, reddens exactly the case that names it. Contrast ratios computed, not judged.

⚠ Verified in a real browser at `http://127.0.0.1:7391/dashboard` — every link computes to
`rgb(140,189,224)` against `rgb(20,24,27)`. `getComputedStyle` reports the unvisited colour even for
visited links (browser privacy), so the `:visited` rule is confirmed from the served source and the
guard, not from a computed value.

⚠ First exercise of the plan-as-CI-dependency decided today: this fix required the identical edit in
`docs/superpowers/plans/2026-08-28-project-dashboard-plan.md` and an evidence regeneration. Backlog
#70 is what ends that.

## 2026-08-29
Reviewed the link fix above, and it needed two more repairs before it was safe to merge.

The test I wrote to stop the problem coming back did not actually check the thing that had gone
wrong. It checked that a colour instruction was *present* — not that the colour was *readable*. So
setting the link back to the exact unreadable blue that started all this left the test passing.
Three different ways of breaking it slipped through; a harmless tidy-up of the spacing, which breaks
nothing, was the one thing it caught. It is now rewritten to measure the actual readability score,
which covers all of those at once.

The second repair: the backlog page had the same fault, and slightly worse — 1.98 and 1.84 against
the required 4.5, where the dashboard scored 1.9. It had five link-colour rules, all correct, but
they each covered one part of the page and three links sat outside all of them. Those are now
covered, with the same kind of measured test.

Worth knowing, because it says something about how much to trust a green tick: the automated
reviewer read the backlog page and reported it clean. It was describing the five rules that exist,
not the links they miss.
<!--tech-->
Finding 1 — `gen-dashboard.py`'s two cases asserted `"a{color:var(--link)}" in ht` and
`ht.count("--link:") == 2`. Mutation-tested on a copied `scripts/` tree, control 105/105: value
swaps to `#0000EE` (1.90:1), `#551A8B` (1.62:1) and `#f2f4f6` all SURVIVED, as did moving both
definitions into `:root` and deleting the dark one — the count is a total, blind to which block
holds them. `a { color` was caught. Replaced by `contrast_failures()`, which parses the emitted
palette and asserts the WCAG ratio for `--link`/`--link-visited`/`--ink` against
`--bg`/`--panel`/`--need-bg`/`--err-bg` in both schemes. All eight mutations now caught; 105 → 111.

⚠ This supersedes the previous entry's "mutation-tested four ways". Those four rows were accurate;
the set was not exhaustive, and the sentence read as though it were.

Finding 2 — `gen-backlog-page.py` had no unscoped `a{}`, only `.qabody a`, `.depmap a`, `.rootref a`,
`.num a`, `td.mono a`. Three anchors in `.prose`/`.status` — rendered from `md(r['body'])`, so the
count grows with the backlog — fell through to `#0000EE`. Adds `a{color:var(--structural)}` (6.40:1
worst case over six surfaces) and `link_contrast_errors()` over all four palette blocks, including
the `data-theme` ones the manual toggle uses. 55 → 64.

Finding 3, found while fixing 2 — that guard's own refusal used a bare substring test for
`a{color:var(--structural)}`, which the SCOPED rules contain, so it passed with the unscoped rule
deleted. Now `re.search(r"^a\{…", re.M)`, with the near-miss pinned as its own case.

⚠ The plan's 43-mutation manifest was NOT extended to the new cases. Coverage is hand-verified and
reproducible but not mechanised; backlog #70 retargets that manifest and would discard the work.

⚠ All three mutation harnesses run today reported a meaningless control on first use. Every "caught"
here comes from a run whose control was green.

## 2026-08-29
A second review round found the repair above was still incomplete, so this is a third pass on the
same problem.

The backlog page's item numbers — the `#17`, `#25` links down the left of every row, seventy of
them — take their colour from the row rather than carrying one of their own. My readability test
didn't know that, so it never checked them. Breaking them to a 1.4-out-of-4.5 grey left everything
green.

Worth reporting plainly: my first attempt to fix *that* also didn't work. The test now knew the
numbers borrowed their colour, but not from where — so changing where they borrowed it from slipped
through again, and I only found out because I re-ran the reviewer's exact test instead of assuming
my fix had worked. The second attempt holds.

This is the fourth time in this small piece of work that something was correct about the thing it
named and blind to the layer around it, and the second time a fix created the next one.
<!--tech-->
`link_contrast_errors` used a flat `LINK_FG x LINK_BG` cross-product. It missed
`.num a{color:inherit}` (inherits `--ink-3` from `.num`; `.item` is `--card`), so Codex's mutation
`.num{color:var(--ink-3)}` -> `var(--line)` — 1.37:1 light, 1.30:1 dark — SURVIVED 64/64.

⚠ Codex's proposed fix was declined, measured: adding `--ink-3` to the foreground list asserts it
against `--ground` (4.26:1) and `--pending-bg` (4.22:1), both sub-AA today, reddening a correct
page. The defect was the MODEL — a cross-product asserts pairs that never co-occur and misses pairs
that do. It passed only because `--structural` clears AA everywhere.

Now explicit `LINK_PAIRS`, plus `link_rule_drift` asserting the emitted CSS still matches the nine
modelled link rules, plus `LINK_INHERITS` pinning an inherited colour at its SOURCE — which the
first fix did not do, so the same mutation survived a second time at 69/69. Control 71/71; both
repoint mutations now caught. 64 -> 71 cases.

⚠ REVIEW GAP: the independent Claude reviewer for round 2 had not returned at commit time. This
round is Codex plus coordinator verification, which is weaker than round 1. Round 3 should re-run it.

⚠ Out of scope, reported not fixed: `--ink-3` is sub-AA as body text on `--ground` (4.26:1) and
`--pending-bg` (4.22:1). Pre-existing, not a link issue.

## 2026-08-29
The second reviewer came back after I'd already committed, and found something worse than what it
was sent to look for: the readability limit itself had no protection.

The whole point of these tests is a number — 4.5, the level at which text is readable. Changing that
one number to zero switched off the entire check, on both pages, and the suite still reported
everything passing. Every future readability problem would have shipped green. The test measured
carefully against a standard that anyone could delete without noticing.

Both limits are now pinned, along with the list of what gets measured, so quietly shrinking the
check fails too.

Also worth recording: it independently made — and caught — the same mistake I did earlier today. It
first measured those seventy links against the wrong backgrounds, got three failures, then checked
where the links actually sit and withdrew all three. Two reviewers and me, same trap, same exit.
<!--tech-->
`CONTRAST_MIN = 4.5 -> 0.0` SURVIVED at 111/111 in `gen-dashboard.py`. `LINK_MIN` in
`gen-backlog-page.py` was caught, but only incidentally — by a positive-assertion case that happens
to need a non-empty result. Luck is not a guard; both are now pinned, plus the sweep sets
(`LINK_FOREGROUNDS`/`LINK_SURFACES`, `LINK_PAIRS`) so narrowing coverage also reddens. Backlog #69's
class, fresh instance.

Also fixed: `scheme_palettes` demanded `@media(` with no space while the sibling generator emits
`@media (` with one, so a harmless reformat raised — and because `case` evaluates arguments eagerly,
that raise arrived as an uncaught traceback that skipped every later case. Regex is now
whitespace-tolerant (fail on ABSENCE, never formatting) and `_safe()` turns a raise into one failed
case. Deleting the dark palette for real is still caught, now cleanly at 112/113.

Re-measured with green controls (113/113, 73/73): all seven mutations from both reviewers caught,
plus three new ones. Their `--ink-3` finding was already closed by the previous commit.

⚠ Round 2 is now CONVERGED and its REVIEW GAP is closed — both halves ran, both with green controls.

⚠ Still open, now quantified: the plan's mutation manifest is 43 before and 43 after, against 17 new
cases. `--verify-evidence` passing says nothing about whether the contrast guards are
mutation-covered. Backlog #70.

## 2026-08-29
A planning document no longer has a veto over two production scripts.

Until today, fixing a bug in either dashboard script turned the build red until you also
copied the identical edit into a 3,170-line planning document. That document held a second
copy of both scripts — about 1,500 lines — and a check enforced that the two matched
character for character. The check was doing something real: it made sure the tests we
claim to run are running against the code that actually ships. But it went about it by
comparing the code to a copy in a document, which is a strange way to check anything.

The tests now run against the real files directly. The document's copy is deleted rather
than left with a warning label, because code in a document that nothing checks quietly
stops being true, and looks authoritative while doing it.

Honest about what's left: this doesn't remove the coupling entirely. About 45 specific
lines are still named by the tests, so changing one of those still means updating the test.
That's down from every line in both files. Over the busiest editing day these files have
had, none of the 45 were touched.
<!--tech-->
`check-plan-code.py <plan> --compare . --verify-evidence` is gone from CI, replaced by
`check-plan-code.py --mutate .`. The 43-entry manifest lives in `scripts/mutations/*.json`,
moved verbatim by script with a lossless round-trip proved first.

The mutation engine is unchanged — extracted to `run_mutations(d, muts, known)` so it has two
callers and is indifferent to where the code came from. Verdict identical before and after:
43 mutations / 0 survivors. `--mutate` copies the WHOLE `scripts/` tree (siblings import each
other) and refuses a red control before applying anything.

`EXPECTED_MUTATIONS` pins coverage per script — exact, not a floor — and lives in the runner,
not beside the entries it counts. Without it, deleting a manifest entry would narrow coverage
with CI still green: backlog #69's class, and the shape found in `CONTRAST_MIN` the same day.

Equivalence demonstrated on one tree (43/0 both paths) and each path shown to FAIL: a broken
delivered file makes the control red and the run refuse; a deleted entry is named with both
numbers. 121 → 136 cases.

⚠ Three defects in the plan were found by EXECUTING it, after two reviewers had read it: the
substitution table read 1:1 where two entries occur twice; the instruction to insert cases
"before the final return" put them after the line that PRINTS the total, so the suite printed
121 while the drift check saw 125 and stayed silent; and a fixture anchor was ambiguous.

## 2026-08-29
The dashboard showed you a page that was mostly wrong, and one part of it was wrong in a way
that looked fine.

Three of its four panels said plainly that they could not reach git or GitHub, which is what
they are supposed to do. The fourth said "No entries yet" — in green, as if the project simply
had no history — when in fact it had eight entries it had failed to find. That is the exact
failure this page was built to prevent: looking healthy while describing a world that isn't there.

The cause was that the page only worked when it was generated from inside the project folder.
Run it from anywhere else and it looked for the project's history in the wrong place, found
nothing, and reported nothing rather than reporting that it had looked in the wrong place.

Fixed, with a test that reproduces the original break: the page now finds the project by its own
location rather than by wherever it happened to be started from.

**Correction to the entry above:** it says the mutation manifest holds 43 entries. It held 43 when
that was written; a 44th was added during review, before merge. The live count is checked by the
build, not by this page.
<!--tech-->
`scripts/gen-dashboard.py` was cwd-dependent in three places while `ROOT` (line 14, derived from
`__file__`) already existed and was used in exactly one. `--store` defaulted to the RELATIVE
string `docs/dashboard-entries.md`; `commit_dates`' `git log` and `_gh_json`'s `gh` inherited the
caller's cwd.

⚠ The fail-open is the interesting half. `main()` deliberately treats a missing DEFAULT store as
"nothing written yet" (a real distinction — the store is created by the first entry), and that
carve-out is correct. Its PREMISE — that the default path is repo-anchored — was what broke. The
`store_error` branch existed, was well-reasoned, had its own store_error cases (`:794`, `:796`), and never fired.

Fix: `STORE_DEFAULT = ROOT / "docs" / "dashboard-entries.md"`, plus `cwd=ROOT` on both
subprocesses. 113 → 117 cases. Reproduced from a foreign cwd before and after: 3 × "not a git
repository" + a green "No entries yet" → 8 entries (before this entry; 9 after), zero error markers.

⚠ The first version of the new store case asserted the repo's OWN store was found, which coupled
the suite to `docs/` existing beside `scripts/`. `check-plan-code.py --mutate` copies `scripts/`
ALONE, so its control went red and it refused to mutate — **the control caught the bad test.**
Rewritten to plant a DECOY store in the foreign cwd and assert it is NOT read, which is the
property with no dependency on the environment.

## 2026-08-29
**Correction to the entry above, after review.** The fix described there was right but its
safety net was not. A dual adversarial review found that the new test guarding the exact
problem the page had would still have passed if the page failed to render at all — it
checked that a wrong answer was absent, and "nothing at all" is also absent. It also found
that the specific decision that made the original bug invisible had no test of its own; three
different ways of breaking it all went unnoticed by a fully passing suite. Both are fixed, and
the same missing test was found in the sibling script that guards this page's entries.

Two smaller things: the page had started printing the file path of the machine that generated
it, which nobody reading it needs; and a comment in the code claimed it ran from a kind of hook
it does not run from.
<!--tech-->
Round 1, both halves NOT CONVERGED → CONVERGED after fixes. All findings re-verified by
execution before acceptance; see `docs/reviews/branch-dashboard-cwd-r1-{claude,codex}.md`
and the Disposition table there.

H1 (both halves): the decoy case asserted only an absence, and `_txt` is `""` when the fragment
is missing — measured green at 117/117 with the store bug restored AND the write emptied. Now
paired, per the rule `:786` already stated in the same file.

H2 (Claude half, deepest of the round): `if a.store != ap.get_default("store")` had no coverage —
`!=`→`==`, deleting the guard, and `pass` ALL survived. The first renders the green "No entries
yet" for `--store docs/typo.md`: the reported symptom, new input, green suite. Named-vs-omitted is
now an `is None` SENTINEL, because the post-fix correctness rested on `PosixPath.__eq__(str)` being
NotImplemented — adding the obvious `type=pathlib.Path` would have silently reopened it.

M2: `check-dashboard-entry.py:233,235` had the identical cwd bug. Fixed rather than filed — this
entry claims a class fix, and making that true cost less than narrowing it.

113 → 120 cases. Mutation battery 8/8 killed, including 4 that survived before the round.
`--mutate .` still 44/0; anchors undisturbed.

⚠ NOT fixed, deliberate: an explicitly-passed RELATIVE `--store` still resolves against cwd. That
is the right convention for a path a caller typed, and it fails loudly.

## 2026-08-29
The "what this means" sections were a wall of text. They are now typeset.

Every entry was already written in paragraphs — nine of the ten in this file — and the page
was throwing all of them away and printing each entry as one unbroken block running the full
width of the page. The blank lines you typed had never once reached the screen.

Emphasis was not working either. Writing **like this** to mark the one sentence a reader
must not skip past printed the asterisks literally, so the marking did the opposite of its job.

And an entry's heading was cut at whatever point the text happened to wrap when it was typed,
which is why one of them ended mid-phrase with "It is one page at". A heading is now the first
sentence, and it is not repeated at the top of the text it was taken from.
<!--tech-->
`gen-dashboard.py` rendered the whole human half as a single escaped `<p>`, so paragraph breaks
collapsed and `**bold**` survived as literal asterisks. Three functions now: `_prose` (blank-line
paragraphs, first as `.lede`), `_inline` (escape FIRST, then bold/code/autolink), `_first_sentence`
(headline).

The markup set was chosen by MEASURING the store, not by taste: `**bold**` 3/10 entries, `code`
1/10, bare URL 1/10, bullets and `[md](links)` **0/10**. Supporting more would invent a contract
no author uses.

De-duplication is derived by re-applying `_first_sentence`, NOT by prefix-matching the displayed
title — the title is capped and may end in "…", which can never prefix-match, so matching on it
declined to drop anything on exactly the entries with the longest openings. Measured on the real
page: 6 entries repeating → 1, and that one is a single-sentence entry with nothing else to
promote (an empty fold is worse than a repeat).

Typography: 64ch measure (was the full 820px shell, ~110 characters a line), 1.7 leading, lede at
full `--fg` with the body at `--fg2` so the glance lands on the idea.

⚠ 120/120 passed BEFORE any of these cases existed — the whole prose path was uncovered. 138 now.
Mutation battery 9/9 killed, including one that survived first: reverting the headline wiring while
`_first_sentence` stayed perfect. A helper can be correct and unused.

## 2026-08-29
The mutation checker was overwriting this page with a blank one, and nobody noticed.

You saw it: an empty dashboard, twice. It was not the page generator — it was the checker
that runs the mutation tests. To test the page code it makes a scratch copy and deliberately
breaks it in small ways, one at a time, to confirm the tests object. But a broken copy still
knew where the real page lives, so some of those deliberate breakages published a blank page
over the live one. The tool that exists to protect this page was quietly destroying it.

Fixed: the test run now writes only inside its own scratch directory, and it fails if that
ever stops being true.

Separately, and what you asked for: the heading, the summary and the emphasised text were
all the same near-white, so nothing stood out from anything else. They now have their own
colours — the summary brightest, the heading cooler, supporting text dimmer, and emphasis
in the same amber this page already uses for things that need you.
<!--tech-->
⛔ MEASURED: `check-plan-code.py --mutate .` replaced `~/explainers/dashboard.html` with a
0-article page. Route: the suite calls `main()`; `main()` falls through to `--out`; `--out`
defaulted to a REAL path outside any temp tree. Four call sites, all unpinned.

Fixed at the DEFAULT (`OUT_DEFAULT` hoisted out of argparse, repointed by `_self_test` into
`mkdtemp` for the whole run), not at the four call sites — a case written later inherits the
sandbox instead of having to remember it. Two falsifiers assert the redirect is live and that
the real path is still what a normal run uses. Verified by the thing that broke it: `--mutate .`
44/0 with the live page byte-identical before and after.

⚠ This is the harness merged as #176 editing the user's artifacts. Adjacent to backlog #67's
class (an instrument that corrupts what it observes), and NOT filed — filing is the user's step.

Colour ramp: title/lede/strong were all `--ink` (13.10:1), separated only by weight — one colour
doing three jobs. Now `--p-lede` / `--p-head` / `--p-detail` / `--p-mark`, chosen by measuring
contrast on `--panel` in BOTH themes. Cases pin the RELATIONSHIP (summary > heading > detail, all
≥ AA, four distinct values, tokens defined AND consumed), not the hexes — asserting hexes would
pass on an inverted hierarchy and fail on a harmless re-tint. Battery 7/7 killed.

## 2026-08-29
The chart has a key now, so you can tell an alarm from a decoration.

You asked what the colours and the stripes meant. Nothing on the page said. The stripes were
the serious one: a day where work was committed and no entry was written — the exact failure
the entry rule exists to prevent — and it looked like just another bar.

The key only lists what is actually in the chart, so a state gets named on the day it appears
rather than sitting in a permanent list of things that are mostly not happening.
<!--tech-->
The chart encoded four meanings (height, `--ok`, `--need`, `--err` hatch + cap) and shipped no
legend. `_day_states` returns only states PRESENT in the window; `_legend` renders them.

⚠ The swatch carries the CHART's classes (`bar needs`, `bar unwritten`) rather than restating
the colours. A legend with a private copy of the palette is a second source of truth, and one
that drifts silently is worse than no legend — a key is believed. A case asserts the swatch
markup contains no `var(--err)` of its own.

The alarm row is suppressed when the store is unreadable, matching `_bar`'s existing §9
suppression — naming a state the chart deliberately did not draw would be a lie about the page,
and the lie would point at the scariest row.

⚠ 152/152 passed before any of these cases existed, and the wiring mutation (delete `{legend}`
from the page template) SURVIVED the first battery at 159/159 — the key can vanish while its
builders stay perfect. Third instance today of testing the helper and not the caller. 161 now,
6/6 killed.

## 2026-08-29
A review of tonight's dashboard work found eleven things, and one of them was on the page you
were reading.

The worst was quiet: an entry whose first paragraph had no full stop at the end lost that
paragraph entirely. The heading showed the first hundred-odd characters and the rest appeared
nowhere at all — written down, and invisible. Also, a heading containing emphasis printed its
asterisks instead of the emphasis, which you would have seen on the current page.

The rest were guards that did not guard: the colour checks measured a copy of the palette
rather than the one that ships, the contrast bar could be lowered to nothing, and a rule
referred to a colour this page does not define.

All fixed, and each with a test that fails if the fix is removed. Not re-reviewed yet — the
fixes were written by the same person who wrote the defects.
<!--tech-->
Round 1 dual adversarial, both halves NOT CONVERGED. Codex 3M+1L, Claude 3H+5M+3L. Full table in
`docs/reviews/branch-dashboard-prose-r1-{claude,codex}.md`.

Content loss (Codex M2, I rate High): a first paragraph with no `.?!` made `_first_sentence`
return the WHOLE paragraph, so the fold dropped it while the title showed only `TITLE_CAP`.
Refuses to drop a non-sentence now. Codex M1: "Met with Dr. Smith…" → headline `Met with Dr.`,
lede opening `Smith…`; `_ends_in_abbreviation` added.

H2: the headline used `_html.escape` while the body used `_inline` — one live title was rendering
`**Correction**`. H1: reverting the entire prose fold at the call site was GREEN — 4th wiring gap
this session. H3/Codex-M3: the autolink's scheme restriction had no negative case; swapping
`https?` for `(?:https?|javascript)` passed.

⚠ Three guards SURVIVED the first battery, two of them written minutes earlier: a CSS **comment**
reading `returns to --fg:` counted as a *definition*; and the legend's contrast case measured a
token by NAME while nothing asserted the rule consumed it. Both closed.

⚠ `--mutate .` went 44 → 43 and REFUSED — the H2 fix moved a line the manifest anchors on. Anchor
re-pointed. That is the documented 45-anchor coupling working: it refused rather than quietly
measuring less. 161 → 187 cases.


## 2026-08-29
The four review findings left over from the last round are fixed, and the fixes were checked by
deleting them again to make sure something noticed.

Three were small. The fourth was not really a bug so much as a gap in the safety net: the automated
check that proves these scripts are actually tested had never been told that the file grew by a
third. It was still measuring the old thirty-two things while reporting a clean result — technically
true, and quietly meaningless. It now measures fifty-three, including nine written today.

One of those nine found something real that nobody had asked about. Text you write in an entry can
end up inside a link, and links have quotes around them; if the quoting were ever turned off, a
stray quote character in a web address could break out and become page markup. Nothing was wrong —
but nothing would have told us if it became wrong, which is the same position the other findings
were about.

The overlapping-emphasis bug is gone, and the way it is gone matters more than the bug: the code no
longer makes three separate passes that cannot see each other. It reads the text once, left to
right. That class of error cannot recur, rather than having been patched where it showed.
<!--tech-->
Round-1 carried findings, all four closed. **Cx-Low**: `_inline`'s three stacked `re.sub` passes
emitted crossed tags — `**bold `code** tail`` → `<strong>bold <code>code</strong> tail</code>`.
Replaced with a single left-to-right scan (`_inline_scan`), not a fourth regex. The case asserts the
PROPERTY (tags close in the order opened) with a companion proving the checker rejects the old
output, so it cannot go vacuous.

**L1/L2**: the `atexit` restore had no falsifier and could not have had one — an exception out of
`_self_test` kills the process, so rebinding a global there is unobservable. What it actually bought
was the `rmtree`. Replaced by `_write_sandbox()`, a context manager wrapped around the CALL in
`main()`: the restore is now in-process (so it has a falsifier — a nested raising body) and the
window covers every line of `_self_test`, including ones not yet written, which is what L2 wanted.

**M5**: manifest 32 → 41 for `gen-dashboard.py`; `EXPECTED_MUTATIONS` and the total pin bumped in
the same commit (44 → 53). Includes the four the reviewer named — the `:750` fold call site,
`quote=True`, the `https?://` scheme restriction, `PROSE_CONTRAST_MIN`.

⚠ `_html.escape(s, quote=False)` SURVIVED 192/192 before this. It is load-bearing: the autolinker is
the one construct writing entry text into an `href` attribute, and `[^\s<]+` admits `"`. Case added.

⚠ Two of my own new guards were caught by the instruments, not by reasoning. A hand battery showed
the "unpaired delimiter" case went red via an unrelated case, because `"code" in ...` was satisfied
by the bold span's content — now counts delimiters. And the scheme mutation's `+` needed two
characters after the colon, so `vbscript:x` never matched and that guard was never reached — now `*`.

`--mutate .` 53/0, gen-dashboard 193/193, check-plan-code 136/136. Live page checksummed identical
before and after every mutation run.

## 2026-08-29
Round two of the review found something worth telling you plainly: **the check I added this morning
to prove your dashboard could not be overwritten was itself the one thing capable of overwriting
it.**

Nothing was lost. Your page is intact and was never touched — I have the before-and-after checksums
for every run. But the risk was real rather than theoretical, and it would have fired on the shared
build server, not just on my machine. To prove it I built a fake home directory with a stand-in
page, and watched the stand-in get destroyed. Then I rebuilt the check so it tests the same thing
without ever being able to reach a real file, and re-ran all forty-seven checks against the
stand-in: none of them could touch it. I also confirmed the old broken version *would* have been
caught by that test, so "none of them could touch it" is a measurement and not a hope.

The shape is worth naming because it has now happened twice in two days. Each time, the thing that
went wrong was not the feature — it was the safety net added around the feature, written by the
same person who had just written the feature. That is why there are two reviewers, and why neither
of them is me.

Four smaller things were also unguarded: a decision about how code snippets render — which affects
a line already on this page — plus two scanner rules and a temp-file cleanup check that would have
passed even if the file it deletes had never existed. All now have tests, and each test was proved
to fail when its fix is removed.
<!--tech-->
Round 2 dual adversarial. Codex 1 Low; Claude 2 High + 2 Medium + 1 Low. Both halves filed at
`docs/reviews/branch-dashboard-prose-r2-{claude,codex}.md`; disposition table at the end of the
Claude one. **Every finding re-reproduced by the coordinator before being acted on.**

**H2 (the serious one, and self-inflicted).** Manifest entry 39 — added in *this branch's previous
commit* to prove `_write_sandbox` works — replaced the `with` block in `main()`, so `OUT_DEFAULT`
stayed at `Path.home()/"explainers"/"dashboard.html"`, an absolute path unaffected by `--mutate .`
running from a temp copy. REPRODUCED with a sentinel: entry 39 + one `--out`-defaulting case →
`SENTINEL INTACT=False`. Harmless today only by accident (no case lets `--out` default) — and
`_write_sandbox`'s own docstring invites the next author to write exactly that case. Fixed by
keeping the sandbox armed and lying about `real_out` instead; still red via the case it names.

**H1.** `real_out = OUT_DEFAULT` had no falsifier — hardcoding the real-page literal survived
193/193 and broke re-entrancy, so the nested sandbox restored `OUT_DEFAULT` to the live page and
left the suite's tail unsandboxed at green. Case now asserts the value IN FORCE (positive paired
with negative), and subsumes the `main()` wiring coverage entry 39 used to provide, safely.

**M1** code-literal (affects `dashboard-entries.md:87`), **M2** two scanner rules, **L1** the
temp-tree case as an unpaired negative — all REPRODUCED green, all now guarded.

**Codex Low.** The scanner made the autolinker greedy where the three-pass order could not be:
`https://x.ee/z**bold**` ate the emphasis into the `href`. The URL now stops at a delimiter and is
re-validated after the cut.

⚠ **M2's second item is PARTLY REFUTED — an equivalent mutant.** `close` is the FIRST `**` after the
opener, so `body` can never contain `**`; `strong=False` gates an unreachable branch. Measured on
three inputs. The comment claiming it was load-bearing is corrected rather than a case invented.

⚠ `--mutate .` REFUSED once mid-fix: renaming a case left entry 38's `expect` naming a case that no
longer existed. Round 1's anchor-drift class, same correct behaviour.

Manifest 41 → 47; `EXPECTED_MUTATIONS` + total pin 53 → 59. 193 → 198 cases, `--mutate .` 59/0,
check-plan-code 136/136. **47/47 manifest entries proved unable to reach the real page**, with the
old dangerous form as a control that the instrument reports as a breach.

## 2026-08-29
A third review round, and the thing it found was on your page as you read it.

The entry I wrote last round — the one explaining that the safety check could have destroyed your
dashboard — had a pair of stray asterisks in its own headline. Raw markdown, printed instead of
rendered, on a page whose entire purpose this week has been to typeset prose properly. Round one
found that same symptom and fixed it. It came back by a different route, because I searched for the
mechanism that caused it rather than for the property that should always hold.

The cause is a seam. The headline gets shortened to fit, and the shortening happens before the
emphasis is applied. If the cut lands in the middle of a bold phrase, the opening marks lose their
partner and print as themselves. Neither half was wrong; nothing owned the join between them. Now
the shortening closes what it opens, so the words still appear and the emphasis still works.

Also fixed: a change I made last round to stop web addresses swallowing nearby formatting turned out
to be cutting HTML escape codes in half, which inserted a stray semicolon into your text. I measured
it across 64,000 samples — my change had made the renderer slightly worse overall, not better. It is
now better than either previous version, and nothing that worked before is broken.

And one I found in my own work rather than being told: a comment claimed the rewritten formatter
behaved identically to the code it replaced. It does not, in 59 cases out of 96,000. The behaviour is
an improvement — the old version silently dropped characters — but the claim was false, and a false
claim in a comment is how a change nobody noticed rides along with one everybody reviewed.
<!--tech-->
Round 3: three inputs — a fresh Claude hunt, Codex, and a re-verification of round 2's findings by
the reviewer who filed them. Filed at `docs/reviews/branch-dashboard-prose-r3-{claude,codex}.md`;
r2's verification appended to `branch-dashboard-prose-r2-claude.md`. Every finding re-reproduced by
the coordinator before action.

**H1 (High, LIVE).** `<p class="title">…plainly: **the check I added…` on the delivered artifact.
`_first_sentence` truncates at `TITLE_CAP`; `parse_entries` stores that; `:774` marks it up
afterwards. `_inline` then correctly printed the orphaned opener. Fixed with
`_close_orphan_markup`, on the truncation path only — an author's unpaired delimiter still prints
as itself. Guarded synthetically AND against the real store.

**M1 (Medium).** Round 2's `rstrip(".,;:)]")` ran on ESCAPED text and severed entities:
`…&amp</a>;<strong>`. Re-measured rendered-vs-typed fidelity across 64,368 inputs on three trees —
pre-r2 **4157**, delivered-r2 **4245**, fixed **3850**, with **0** newly broken. Round 2 shipped a
net regression as an improvement.

**M2/M3/L1** closed. **r2's re-verify** confirmed H1/H2/M1/L1 CLOSED and withdrew its `strong=False`
item — my equivalent-mutant refutation was independently confirmed over 173,488 inputs, and it went
further: the whole `strong` parameter is vestigial.

**Codex's Medium REFUTED as a regression** — the pre-round-2 renderer produces byte-identical output
on its own repro. The paren drop is `INLINE_URL`'s trailing-char class, deliberate and pre-existing.

⚠ Two of mine: the `_write_sandbox` docstring over-claimed its scope (`--fragment-only` and explicit
`--out` bypass it; a relative path escapes to cwd — latent, live page unreachable, CI safe), and the
`body.strip()` comment asserted a FALSE equivalence with the deleted regex. Both corrected, both
now guarded — the second by a case that reads this suite's own source.

⚠ The gate refused twice, correctly: two entries repeated an earlier entry's anchors, and the
real-store case reported CANNOT RUN under `--mutate .` (only `scripts/` is copied). The skip is now
declared and itself asserted.

Battery 8/8 killed via the named case. 55/55 manifest entries proved unable to reach a real file,
old dangerous form as instrument control. Manifest 47 → 55, pins 59 → 67, cases 198 → 206.

## 2026-08-30
Round four. Both reviewers independently found the same root cause this time, which has not happened
before in this sequence, and it was a mistake with a clear shape: I had written the same rule twice.

Last round I added something to close off formatting marks that a shortened headline had left
dangling. But the code that decided which marks needed closing was a *second, simpler copy* of the
code that actually renders the page — and the two disagreed about one thing. The renderer treats
anything inside backticks as plain text; my copy did not. So a headline containing a code snippet
with asterisks in it got an extra pair of asterisks added, inside the snippet, which then showed on
the page as literal characters nobody typed.

The repair was to delete the copy. There is one implementation now: the closing marks are chosen by
running the real renderer and checking the result, so the two cannot disagree — because there are no
longer two.

The other one worth telling you about is a check that was passing for the wrong reason. It was meant
to prove that no test writes to a file path outside its sandbox, and it did this by reading the test
code looking for a quoted filename. There are no quoted filenames in that code — every call builds
its path a different way — so the check was green because it could not see anything, not because
everything was safe. Proven by adding a test that wrote outside the sandbox: still green, file still
destroyed. It now watches the values actually handed over at run time.

I also made two process mistakes worth writing down. I edited files while a reviewer was reading
them, which gave it a false alarm it had to spend time disproving. And when a reviewer explained
that a test's sample data was too simple to exercise the bug, I wrote a new test with sample data
that was too simple in exactly the same way — and it passed while the bug was present.
<!--tech-->
Round 4, scoped to `7bbabad..dee62f2`, prose renderer. Codex 1B+1H+1M; Claude 1B+1H+2M+2L. Filed at
`docs/reviews/branch-dashboard-prose-r4-{claude,codex}.md`. **Both halves independently isolated the
same Blocking** — first convergence on one root cause in four rounds.

**B1 (Blocking).** `_close_orphan_markup` was a second scanner beside `_inline_scan` and disagreed on
one rule: code content is literal. `` `code ** tail `` gained a `**` closer that rendered inside the
`<code>`. Fixed structurally — candidate closers are judged by running the shipping renderer
(`_orphaned_delimiters`), so there is one implementation, not two. The case asserts the property that
survives a mechanism change: the truncated span's CONTENT is a prefix of the full span's.

**H1 (High).** The `--out`/`--fragment-only` absolute-path guard matched source text for a literal
after the flag. The suite has 5 flags and **0** adjacent literals — every call site passes
`str(<Path>)`. Green because it could not look. REPRODUCED: a relative `str(Path(...))` destroyed a
cwd sentinel at 206/206. Replaced with a recording proxy over `main`; the source-scanning version is
deleted rather than kept alongside.

**`&#x27;`**: `ENTITY_TAIL` accepted hex digits but not the `x`, so it matched `&#39;` (never
emitted) and missed the form `html.escape` always produces. **L1**: closers were appended past
`TITLE_CAP` — 148/60,000 inputs, max 113; now inside the cap, re-fuzzed to 0. **L2**: the entity
case's conjuncts all passed with the trim removed; now asserts rendered text == typed text.

⚠ **Two of my process failures, recorded.** I edited the tree mid-review and caused a false red the
reviewer had to disprove (it correctly labelled it NOT RUN and re-measured against `git archive`).
And my first cap case repeated the blind-filler mistake the same review had just described — it
SURVIVED at 208/208; the passing input now comes from the fuzz that found the defect.

Battery: second scanner restored verbatim, ENTITY_TAIL reverted, cap check dropped, recorder
silenced, relative `str(Path)` — all killed via the case each names. `--mutate .` 73/0; 61/61 entries
proved unable to reach a real file. Anchor ratchet refused 3× as my edits moved quoted lines, plus
once for an entry whose subject I deleted (retired, not re-pointed). Manifest 59 → 61, pins 71 → 73,
cases 208 → 209.

## 2026-08-30
The project has twenty-four small scripts whose job is to catch mistakes. Two of them — three, it
turned out — were never actually run by anything. They sat on disk, working, checking nothing.

Worse, one of them was listed in the process document under a heading that says "what is
mechanically enforced". So the written record claimed a check was running, and it was not.

The thing that should have caught this is a script whose entire purpose is to police the other
checks. It could not, and the reason is worth understanding: it found the checks to police by
looking at which ones the build already ran, and by looking for ones that describe themselves as
checks. Both of those questions assume the answer. A check that nobody runs and that does not
advertise itself is invisible to both. It found fourteen of the twenty-four.

It now finds them by looking at the disk, which cannot be evaded by omission, and it asks a new
question of each: does anything actually run this? If not, the script must say in writing why not —
and "no reason given" is refused, because an excuse that needs no reason is not an excuse.

Two things fell out of widening it. A checking rule had been quietly wrong for a while: it flagged
one script for reporting failure as success, which it does not do — the rule could not tell the
number zero from the word "false", and Python treats them as equal. And this failure has been
recorded four separate times in this project across the past month, each time fixed for that one
instance. The check that finds the whole class had never been written, on an inventory that already
existed.
<!--tech-->
Phase 6 candidate 2 (findings A/B/C of `docs/reviews/architecture-review-2026-08-30.md`).

`check-ratchet-contract.py`: population is now the FILESYSTEM (`discover_guards`), not CI step names
+ self-declaring docstrings. Both presupposed the guard was already wired or self-labelled — 14 of
24 discovered, and the 10 missed included every orphan. New **R3 has-a-caller**, statically
decidable, with a `NO-CALLER: <reason>` opt-out that refuses a bare marker. `invocation_re` demands
an invocation, not a mention, so a row in dev-process's "mechanically enforced" table cannot satisfy
it.

THREE orphans, not the two the review reported — I had grepped hooks for `check-explainer-delivery.py`
and matched a COMMENT. Same "mechanism not property" error the review refuted for
`check-paid-caller-arrival`, in the opposite direction. All three wired as CI steps; each exits 0.

Widening found a PRE-EXISTING R2 false positive: `check-dashboard-entry.py:34` is `except ValueError:
return False` (fail-closed) and `False == 0`, so the constant test could not tell a predicate from an
exit code. Now `type(val) is int`.

`evaluate()` extracted so main() and the suite drive one verdict — with the rules inline, deleting
the `check_caller` call left every caller case green. Two wiring cases now cover that.

Battery 7/7 killed via the named case, including unwiring a guard from `ci.yml`. ⚠ One SURVIVED
first: my comment claimed `\s*` would match the closing `"""`, but `ast.get_docstring` strips — a
false claim written from how source looks rather than what the parser returns. Fixed with a real
input (`OPTED_OUT_BARE_THEN_PROSE`) and a corrected comment.

Contract 21/21, clean over 24 guards. dev-process 218/220 lines.

## 2026-08-30
Four of the local pages this project generates — the dashboard, the backlog table, the goals view and
the explainer viewer — each turn markdown into HTML using their own separate code. They were written
at different times and they no longer agree with each other, and that is now visibly damaging the
backlog page.

The clearest example is on the backlog page right now. A line in the backlog file contains a piece of
SQL, `select count(*) filter (...)`. The page renders it with the asterisk swallowed and turned into
italics, so what you read is `count()` — SQL that would fail if you copied it. The same thing happens
to file paths containing a `*`: the asterisks vanish and the name goes italic. Ten places on the page
have mangled formatting like this, and fifteen more have styling applied inside text that was meant
to be shown literally.

None of this is new breakage. The page generator that had this exact bug was fixed a few days ago,
carefully, over four rounds of review. The fix simply lives in a file the other three cannot reach,
because none of these generators shares code with any other.

The plan agreed today is to write the markdown-to-HTML step once and have all four use it, with one
behaviour rather than four. It is filed as backlog item 71 with a written spec. The order was settled
too: this first, the sandboxing decision alongside it, and the larger question of whether the testing
around the dashboard has too many layers comes last, because doing this first changes the answer.
<!--tech-->
Branch `fix/inline-renderer-seam`, docs only so far. Backlog #71, spec at
`docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md`, anchor `status-visibility`.
Phase 6 candidate 1 from `docs/reviews/architecture-review-2026-08-30.md`.

Measured 2026-08-30 by importing the four delivered renderers and running them over the real
corpora: they disagree on 11 of 13 probe inputs. On `~/explainers/backlog-table.html` as it stood on
disk (built 2026-08-29 16:42, not regenerated to produce the numbers): 10 crossed tag spans, 15 cases
of markup emitted inside a code span. Root cause is stacked `re.sub` passes blind to each other's
output; `gen-dashboard._inline_scan` is a single left-to-right scan and is unreachable from the other
three. Two more holes of the same shape: `gen-backlog-page` renders `[text](url)` with no href
sanitiser while `explainer-serve.safe_href` exists unshared, and `gen-goals-page.esc()` omits the
apostrophe.

Decided with the user: one behaviour = the union feature set on the single-scan algorithm, NOT
`gen-dashboard`'s current rule — adopting that wholesale would strip 59 `<em>` spans and 3 links off
the backlog page, because its feature set is minimal only because its corpus is (0 links in 593
lines). The shared module becomes its own guard subject, 25th in `check-ratchet-contract.py`, and the
generators' inline cases are deleted rather than kept, so the layer count falls.

Also noted, not fixed: `project-dashboard`, the anchor the architecture review declares, is not in
`docs/anchors.md`. `check-anchors.py` passes only because `docs/reviews/` is out of scope by design.
<!--tech-->

## 2026-08-30
The markdown-to-HTML work described in the previous entry is finished. All four pages — this
dashboard, the backlog table, the goals view and the explainer viewer — now share one piece of code
for turning markdown into HTML, and the mangled formatting is gone: zero on all three generated
pages, against six and ten on the backlog page this morning. The SQL that was rendering with a
character swallowed now reads correctly.

Two things are worth knowing beyond that. The tests that used to protect this on one page moved with
the code, so they now protect all four — the total is unchanged at seventy-three, deliberately,
because a number that stayed the same is the only way to tell that coverage was *moved* rather than
deleted. And the goals page turned out to gain nothing visible from the change: it renders only
one-line goal sentences, none of which use any of the formatting involved. An earlier note here
predicted a large change there; that prediction was wrong and is corrected.

Nothing is waiting on you except two things: whether to merge the pull request, and one open
question about how the test harness should sandbox itself.
<!--tech-->
Branch `fix/inline-renderer-seam`, 5 commits. Backlog #71 T1–T4 done; #72 and #73 filed.
`scripts/page_markup.py` is the single renderer; all four generators import it.

Falsifiers, measured on the regenerated pages: `backlog-table.html`, `goals.html` and
`dashboard.html` all report 0 crossed tag spans, 0 markup emitted inside a code span, 0
`javascript:` hrefs. The four generators agree on 8/8 probe inputs; before the seam they disagreed
on 11 of 13. `--mutate .` reports 3 files, 73 mutations, 0 survivors, with EXPECTED_MUTATIONS split
gen-dashboard 47 + page_markup 14 + check-dashboard-entry 12.

⚠ The costly find was not in the renderer. All 12 relocated mutations reported `expect matched 0 red
case(s)` because `check-plan-code.py:495` identifies a reddened case by parsing lines that START
WITH `[FAIL] `, and page_markup's self-test used a different failure format — so nothing was ever
seen as red. A formatting choice was indistinguishable from a total coverage hole, and it masked
three real edit bugs underneath.
<!--tech-->

## 2026-08-30 [needs-you]
The tool that deliberately breaks our own code to check the tests notice can no longer touch the
pages you actually read. It runs that broken code with a fake home directory, so anything it writes
lands in a scratch folder that is thrown away, instead of in `~/explainers/` where this dashboard
and the backlog table live.

This was the open question left by the previous entry, and it turned out not to be a close call. The
reason to hesitate was that a fake home might make the tests less realistic — but nothing in the
code names a real home path, so the fake one shifts both sides of every comparison together and
changes no result. The full check reports the same seventy-three broken-code cases caught, none
missed, exactly as before.

The more useful thing came out of testing the new safeguard rather than writing it. A safeguard that
protects against something nothing currently does is invisible when it breaks — "it held" and
"nothing tried" look identical — so the new test genuinely writes a marker file and then checks
where it landed. Doing that carelessly the first time left the marker behind and would have made the
check fail forever afterwards, including once the problem was fixed. It names the marker per run now
and cleans up after itself.

Two things are waiting on you. One is whether to merge the pull request. The other is a
recommendation: the review that started this work suggested the checking machinery had grown too
tall and should be cut back. Having re-measured it, I think that is the wrong reading — the recent
sharing work means the same checks now protect four pages instead of one, so their cost per page
quartered. What the measurement does show is that the tallest layer, the checking tool itself, is the
only one nothing checks in return. I tried it and it works. That is a proposal, not something I have
filed.
<!--tech-->
Branch `fix/mutation-harness-home-redirect`, commit `75497af`. Phase 6 candidate 3.

`check-plan-code.py:run_suite` is the only spawn point of a delivered script (4 call sites), so the
redirect lives there via a new `child_env(d)` and cannot be forgotten by a caller. `mutate_delivered`
creates the `.home` inside its own `TemporaryDirectory`; `child_env` deliberately does NOT mkdir,
because `run_suite` is reachable from a case that passes `.` and would otherwise create `./.home` in
the repo — an instrument editing the tree it measures.

Measured, not assumed: `grep -rn '/Users/…' scripts/*.py scripts/mutations/*.json` finds no
hardcoded home literal, over a control pattern that hits. `--mutate .` = 3 files, 73 mutations, 0
survivors (unchanged). `--self-test` 136 → 139 cases; layer 7's `count_drift` caught the docstring
drift unprompted. Mutation-tested with the parent's HOME redirected too: dropping `env=child_env(d)`
reddens exactly the 3 new cases and leaves no debris.

⚠ Candidate 4 re-scope, measured. Layers and their coverage: gen-dashboard 209 cases / 47 mutations,
page_markup 78 / 14, check-dashboard-entry 46 / 12 — and check-plan-code.py 139 cases / **0
mutations**, though it is 1,696 lines and every one of those 73 verdicts passes through it. Its own
comments record two guards whose deletion left its suite green (`count_drift` inline, round 5;
`_drift_rc`'s call, "deleting it left 92/92 green"). A scratch probe adding it as a 4th target ran
4 files / 75 mutations / 0 survivors with clean controls — and immediately exposed the stateful
canary above. Nothing filed to `docs/backlog.md`; that is the user's step.

## 2026-08-30 [needs-you]
The tool that checks all our other checks is now checked itself, and turning that on immediately
found three places where a safety check had quietly stopped working.

Some background. When we write a safety check, we prove it actually works by deliberately breaking
the code it guards and confirming the check complains. Four files in this project get that
treatment. The tool that runs the whole procedure was not one of them — every verdict passes through
it, and nothing tested it back. That was the finding from re-measuring the review item you asked
about; it is now fixed.

Switching it on found three checks whose deletion left everything green, meaning they had been
doing nothing detectable for a while. All three had been added deliberately after past reviews. One
of them was written yesterday, in the change you merged an hour ago, and shipped with no test — that
is the third time in this session a fix landed unguarded, which is a pattern worth naming rather
than a one-off.

Then the review round found two more problems in the new work, both real. The stricter one: a safety
marker I added, meant to let test data mention a dangerous pattern without tripping the alarm, could
be abused to switch the alarm off for real code — and worse, could switch it off by accident if the
marker text merely appeared inside a piece of text. It now reads the code properly rather than
matching lines, and it flatly refuses to excuse code that actually runs. The reviewer also caught me
asserting something confidently and wrongly: I had dismissed one test as pointless on reasoning that
does not hold, and it turned out to cover a real case.

One cost worth knowing: this check now takes three minutes instead of thirteen seconds, because it
runs a large test suite twenty-one times over. That is a real slowdown on every change, and if it
becomes annoying the fix is to run them in parallel rather than to check less.

Waiting on you: whether to merge, and nothing else.
<!--tech-->
Branch `feat/mutation-coverage-for-the-runner`. Backlog **#74** filed; Phase 6 **candidate 4 CLOSED
as answered-no-flattening**, dispositions recorded in `docs/reviews/architecture-review-2026-08-30.md`.

`scripts/mutations/check-plan-code.json` — 21 entries. `EXPECTED_MUTATIONS` = gen-dashboard 47 +
page_markup 14 + check-dashboard-entry 12 + check-plan-code 21 = **94**. `--self-test` 152 → 158.
Not circular: the orchestrator is the repo copy, the target is the temp copy, and the nested spawn
inherits `child_env`'s redirected `HOME` from PR #181.

Discovery: of 17 candidates, 13 reddened a case and **4 survived at 152/152** — 2 were equivalent
mutants of mine, 3 were real gaps (after-sequence control; duplicate-anchor refusal; `check()`'s
`.home` mkdir, i.e. PR #181's own fix).

Review round: Codex High — `ESCAPE_EXEMPT` had two bypasses (marker inside a string literal dropped
the whole line; marker on live code exempted live code). `home_escapes` is now tokenised: the marker
counts only as a `COMMENT` token, and exempts only when the route vanishes with `STRING` tokens
blanked. Unparseable source is scanned raw with no exemptions. Codex Medium — my "semantically
equivalent" dismissal of `caught = rc == 1` → `rc != 0` was WRONG (`rc == 2: continue` excludes 2
only; rc 3 would be credited as caught); it now has cases and is in the manifest.

⚠ The harness refused my predicted `expect` on one entry — the mutation reddened four other cases —
so the entry was narrowed and its `expect` taken from the run. Third occurrence of predicting rather
than measuring an `expect`. ⚠ `--mutate .` 13s → **3m13s**.

## 2026-08-30 [resolved: 2026-08-30/5] [resolved: 2026-08-30/6]
Both of the changes that were waiting on you are merged, so nothing is waiting on you now.

That closes the whole set of four improvements the architecture review proposed at the start of the
day. Two were built earlier, one was the sandboxing question you handed back to me, and the fourth
turned out not to need building at all — re-measuring it showed the work it asked for would have
made things worse, and the useful work was the opposite of what it named.

Worth stating plainly, because it is the honest summary of the day: of the defects found across
these two changes, the reviewers found more than I did, and two of them were in fixes I had written
during the review itself. The checking machinery earned its cost.
<!--tech-->
PR #181 (`ebec7bc`) and PR #182 (`a5a012c`) merged; branches deleted. Master verified independently
after the squash: `--self-test` 158/158, `--mutate .` 4 files / 94 mutations / 0 survivors.

Phase 6 candidates 1–4 all closed: #180, #179, #181, and 4 closed-as-answered with backlog #74 as
its residue. Dispositions in `docs/reviews/architecture-review-2026-08-30.md`.

This entry is the status tick for #74, batched per `dev-process.md` rather than pushed to master
alone. ⚠ The tick was NOT written before the PR opened, which the process asks for — that is why it
needs its own follow-up here.

## 2026-08-31
The status page was putting the oldest update of the day at the top, so after a busy day the newest
thing had scrolled off the bottom and the page looked broken. It was not broken. That is fixed —
newest first now — and three related items are written down.

You spotted the second half of it yourself: the backlog page was showing three items as "open" that
do not exist yet for anyone but me. It was built from work in progress on my machine, and it had no
way to say so. That is now part of the item covering page freshness — a page will say which version
of the project it was built from, not just what time it was built.
<!--tech-->
Branch `fix/dashboard-entry-ordering`, split out of `feat/page-chrome-seam` because it is
independent and verified, and leaving it unmerged left backlog #75 reading OPEN on a page the user
reads.

#75 fixed: `gen-dashboard.py:_ordered` sort key `-p[0]` → `p[0]`. Spec row 123 of
`2026-08-28-project-dashboard-design.md` rewritten in place — it mandated the old rule. 209 → 213
cases, three of which pin that entry IDS do not move: ids are positional and a standing
`[resolved: <id>]` points at one, so letting render order reach id assignment would silently rebind
every resolution. Verified on the live page — top card is `2026-08-30/7`.

#76 and #77 filed here too, still OPEN. ⚠ #77 gained a requirement measured today: the generated-at
stamp must carry PROVENANCE (commit + dirty flag), not a clock reading. A page rendered from an
unmerged tree is indistinguishable from a current one, which is the same class of defect as #75 —
correct content that cannot be told apart from broken content.

⚠ The `page_chrome` module and the `POST /regenerate` route stay on `feat/page-chrome-seam`,
unwired, because `gen-dashboard.py:1573` reads palettes positionally
(`css.split("prefers-color-scheme:dark")[1]`) and adding `data-theme` blocks would leave the
contrast guard checking the OLD palettes while reporting green.

## 2026-08-31
Every page this project generates now has a light/dark switch and tells you when — and from what — it
was built. That was your request, and the second half came from your observation that a page can look
current while being built from work that exists only on my machine.

Five pages were involved and none of them had a switch before; two of them contained the styling for
one that had never been built, and a checking script asserted in writing that it existed. The switch
is now built once and used by all five, and the thing that stops it being decorative is a check that
refuses to write a page where pressing the button would do nothing.

It was pressed, in a browser, on the real page: dark to light to dark, remembered across a reload.
The stamp was watched changing from "uncommitted changes" to a clean commit as the work was
committed underneath it.

A review found seven problems, two of them serious, and both serious ones were in code I had written
specifically to prevent that kind of problem. Fixing them cost two more, which the test machinery
caught rather than me.
<!--tech-->
Branch `feat/page-chrome-seam`. Backlog **#76** and **#77**; #75 shipped separately as PR #184.

`scripts/page_chrome.py` — mechanism shared, palette local. `assert_wired()` gates every write.
`provenance()` lives here so five pages cannot compute it five ways. `POST /regenerate` in
explainer-serve: allow-list of literals, per-page lock (ThreadingHTTPServer), and a `⚠` line from a
generator travels back as `warning` so a degraded rebuild is not reported as success.

⚠ Prerequisite fixed first: `gen-dashboard.py` read its palettes POSITIONALLY, so adding
`data-theme` blocks would have left the contrast guard checking the old ones and reporting green.
Both readers now enumerate. Proved with a control — legible toggled palette 0 reports, illegible 12,
including `toggled-dark: --link #111111 on --bg #000000 = 1.11:1`.

Review round 1 (`docs/reviews/page-chrome-{codex,coordinator}-r1.md`), 7 findings, 2 High: a script
merely CONTAINING "chrome-theme" satisfied the binding check; and the composer trusted the button id
alone, composing an inert control with no stamp. Then my fixes broke a manifest anchor and turned a
caught mutation into a survivor — both found by `--mutate .`, not by reading.

  page_chrome 47/47 · gen-dashboard 217/217 · brief-compose 40/40 · explainer-serve 71/71
  gen-backlog-page 71/71 · gen-goals-page 15/15 · --mutate . 5 files, 105 mutations, 0 survivors

## 2026-08-31 [needs-you]
The page can no longer tell you that something needs you and then decline to say what.

You reported three cards flagged "needs you" while the line above them read "Nothing needs you." Both
were right about different things, which is the whole problem: the summary line worked out which asks
had since been closed, and the cards printed the label exactly as it was first written, with nothing
ever clearing it. One page, one question, two answers. The cards now say "resolved", and the three in
question are.

The second half is what you actually asked for. An ask used to show its headline, so "whether to
merge" arrived with no pull request named and no choices offered. An ask now carries its decisions,
and the page lists them with the options unfolded. Where an option names a pull request, the page
checks whether it is still open and marks it stale if you already merged it — the exact trap you hit
by hand this morning.

Anything that only needs your awareness is now a separate thing called a heads-up, in its own block,
and it is not allowed to ask for anything.

Three rounds of adversarial review, none of which agreed with me the first time. The most useful one
found that a correctly written ask could silently lose options: indent a sub-bullet four spaces and
every choice after it disappeared from the page, while the checker complained that the ask offered
only one option. On a change whose entire purpose is listing your choices, quietly dropping choices
was the worst thing available, and no test I had written could have found it.

**Decide:** Merge the ask-choices change
- merge PR #186 [recommended]
- hold it and tell me what to change
- close it unmerged

**Decide:** The heads-up expiry, which I argued for on reasoning that turned out to be wrong
- keep no expiry — a heads-up that ages out silently looks the same as one you dealt with [recommended]
- give heads-ups a bounded lifetime after all
- leave it open and decide when a heads-up actually gets old
<!--tech-->
Branch `feat/dashboard-ask-choices`, 12 commits. Spec v3 + plan v2 + four review docs.

Renderer-only enforcement by your decision; the CI gate half is backlog **#78**, filed with its
measurements. `decision_errors` lives in `check-dashboard-entry.py` because that file owns the
grammar and the import arrow already points generator → gate.

The grammar is recognised only outside fenced code, indented code, HTML comments and blockquotes —
which is why this entry can carry a fenced example without tripping its own gate:

```
**Decide:** Not a real ask
- a
- b
```

`gen-dashboard` 217 → 266 cases, `check-dashboard-entry` 46 → 77, `EXPECTED_MUTATIONS` 105 → 120,
`--mutate .` 120/0 survivors.

⚠ v1 of the spec asserted that `git diff -U0` omits an added entry's body. It does not — an appended
entry is entirely additions. Both round-1 reviewers agreed with the false premise; one `git diff`
refuted it, and v3 deleted the machinery v2 had built on top of it.

## 2026-08-31 [resolved: 2026-08-31/3]
Both asks on the previous entry are settled: the change is merged, and heads-ups will not expire.

You chose no expiry. The reasoning that survives is the one that does not borrow authority from
anywhere: a heads-up that ages out on its own is indistinguishable from one you dealt with, and this
page exists so that absence and denial never look alike. If the block ever gets long, that means
things need resolving, not hiding.

The original argument for it was withdrawn before you decided. It claimed a script enforced
"one mechanism per concern" here; that script compares database column names across tables and could
never have fired on a dashboard entry. The decision stands on its own merits, taken with that
correction in hand.
<!--tech-->
Squash `cadd7348` (PR #186). Spec §3's re-decision box and §12 row 3 are settled in the same change;
`[resolved: 2026-08-31/3]` clears the entry that carried both `**Decide:**` blocks, so the tray
returns to "Nothing needs you."

This is the first exercise of the resolution mechanism on an entry written in the new grammar — the
same `[resolved: <id>]` marker for both categories, which is why no expiry was needed.

## 2026-08-31 [heads-up]
The backlog page refused to build until the newest item was described in plain words, which is the
guard working rather than failing.

Filing backlog #78 yesterday added a row the reader's backlog page had no plain-English line for, and
that page will not render an item it cannot describe — it stops rather than quietly leaving it out.
So the fix is one sentence explaining what #78 is, and the page builds again: 78 rows, 56 open.

Worth knowing because it will happen to the next person who files something: the refusal is not a
bug report, it is the page declining to show you an incomplete list.
<!--tech-->
`gen-backlog-page.py` `GROUPS` gains an entry for 78 under the guard-inventory group, beside #72/#73.
`coverage_errors` fails both ways — an open item missing from `GROUPS`, and `GROUPS` naming an item
that is no longer open — so it cannot drift in either direction.

This is the first `[heads-up]` written under the grammar merged in PR #186: it asks nothing, so it
carries no `**Decide:**` block, and it renders in "Worth knowing" rather than "What needs you".

## 2026-08-31

The status page is now a tight list: each update is one line you can read at a glance, and clicking it opens the explanation.

Before, every update took four lines before it said anything — a date row, a title, and two closed folds — so about five fitted on a screen. Now there is one row per update: its id, any badge, and the title, with a small triangle at the end. Click the row and the plain-words explanation appears, with **Raw technical detail** tucked at the end of it. An update with nothing more to say has no triangle at all, because a control that opens onto nothing is a lie about the content.

Two smaller things came with it. The date used to print twice on every row — "2026-08-31 2026-08-31/3" — because the id is built from the date, so the duplication was guaranteed rather than occasional. The bare date is gone and the id stays, since that is the reference you can quote back.

And a real defect, found while measuring the first two: a title longer than 110 characters was cut, and the rest of that sentence was displayed **nowhere on the page**. Two rules that were each correct on their own — cut the title, and don't repeat the title inside the fold — combined to delete words you had written. The cap is gone; the line is clipped by the browser instead, so the full text stays in the page where find-in-page and an opened card can both reach it.

<!--tech-->
Spec `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md` v3; plan `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md` v2. Four review rounds, both halves each (2 spec, 1 plan, + fold-ins).

Each entry is now one `<details>` inside the existing `<article id="{eid}">`, whose `<summary>` is a single `<h3 class="row">` — `<summary>`'s content model allows phrasing content or ONE heading element, and a `<summary>` is not itself a heading, so this keeps the per-entry heading stops and improves them (the outline used to read as 29 bare dates).

DELETED, not disabled: `TITLE_CAP`, the truncation branch, `_close_orphan_markup`, `gen-dashboard._orphaned_delimiters` and `page_markup.orphaned_delimiters`. The orphan repair existed only to heal a wound the cut inflicted — cutting mid-`**bold**` orphaned the opener.

Mutations 120 → 123 (3 deleted with the code they guarded, 6 added, 2 re-anchored). `--mutate .`: 5 files, 123 mutations, 0 survivors. Suite 266 → 276; page_markup 78 → 74.

⚠ Two honest gaps. (1) Emptying the title is caught by the ORDERING guards, not by the title-specific one, which did not fire even after re-binding; recorded as a `note` in the mutation manifest. (2) No browser has yet been driven against this — the flex-ellipsis behaviour is asserted from the stylesheet text only, and the spec says the falsifiers are necessary and not sufficient.

## 2026-08-31

An ask's choices now render as an actual list, and a settled ask stops looking like it is still waiting for you.

You reported both from the live page. The options ran together on one line — "Merge the ask-choices change - merge PR #186 [recommended] - hold it and tell me what to change - close it unmerged" — with the dashes you typed showing as hyphens mid-sentence. And the card said **Decide:** over three live-looking options while its badge said resolved, so a settled decision read as an open one.

The cause was that the renderer split your text on blank lines only, so an opener and its bullets counted as one paragraph and went out as a single block of prose. The structure you wrote was in the file the whole time; nothing looked at it. That is the same thing this renderer was fixed for once before, for paragraphs — lists were simply never done.

A resolved ask now reads **Was decided:** and recedes. It deliberately does **not** say which choice you made, because the store records which entry resolved an ask, never which option won — and where there are two asks in one entry it keeps asking rather than claim either was settled.

<!--tech-->
`_ask_block` renders a `**Decide:**` paragraph as a question plus `<ul class="opts">`. The option grammar is NOT re-implemented — it comes from the gate's `decisions()`, the same parser the ask tray reads.

⚠ THREE DEFECTS FOUND AND FIXED DURING THE ONE REVIEW PASS, all in the fix itself:
1. Parsing the PARAGRAPH ALONE stripped the surrounding context, so a `**Decide:**` inside a fence or indented code — 0 decisions to the gate over the whole entry — parsed as 1 and drew a live options list over inert text. Found by probe.
2. Matching asks by QUESTION TEXT is not an identity: an inert copy of a later ask's question consumed that ask's options, so the real ask flattened. Now matched by LINE POSITION using the gate's own `_inert_lines`.
3. Two openers in one paragraph rendered only the first and dropped the rest of the paragraph. Now the whole paragraph stays prose — nothing is lost.

Also: `settled` is an entry-level fact, so with two asks it claimed both were decided. It now applies only when the entry holds exactly one ask.

Suite 276 → 290. Mutations 123 → 127, 0 survivors. One mutation SURVIVED on first run and was replaced: `d = live[0]` never reached the code it named, because an early return already protected inert text. A mutation that cannot reproduce the defect it describes is a claim, not a guard.

⚠ NOT DONE, deliberately: the card's options omit the tray's PR links and live PR-state notes, so for a LIVE ask the same option can read differently in the two places. Filed as a follow-up — it wants a shared option renderer, which is a seam change, not a patch.

## 2026-09-01
Switch the dashboard to its light theme and point at either button at the top of the page, and the
button's label disappears. It is still there and still clickable — it just becomes the same colour
as the button underneath it. This is not new and it is not from yesterday's work on the cards; it
arrived with the theme switch itself, and it only happens when your computer is set to dark mode
and you have asked this page for light.

Nobody had seen it because the buttons look perfectly fine until you point at them, which is not a
state anyone photographs.

The cause is more interesting than the symptom, and it is why this ships a check rather than a new
colour. The pages are built from three files. One of them fills in a set of dark colours whenever
your computer is in dark mode. Another declares the colours for light mode — but it names only some
of them. For the eight it does not name, nobody ever supplied a light value, so the dark one simply
stays. Seven of those eight are currently invisible problems: they tint the little bar chart and the
badges slightly wrong on a light page. The eighth paints the buttons, and that is the one you can
see. Nothing here is a badly chosen colour; the list of colours is just shorter than it should be.

So the colours are not fixed yet — that is a design decision about what light versions those eight
should be, and it is written up as backlog item 79. What ships today is a check that stops the
problem growing: if a ninth colour ever goes missing the build fails, and as the eight are fixed the
check forces the list of known-missing ones to shrink with them, so it cannot sit there claiming
debt that has already been paid.

Separately, yesterday's change that collapses long entries to one line was checked by hand in a real
browser for the first time. Clicking a card opens it to the full sentence, the arrow turns, and the
full text of a shortened title is still findable with the browser's own search — the words are on
the page, just not painted. Two of the six checks could not be run as written and are recorded as
not run rather than passed.
<!--tech-->
Ships `scripts/check-theme-token-coverage.py` (12 self-test cases) plus two CI callers, backlog #79,
and the `GROUPS` entry that keeps `gen-backlog-page.py` building.

MEASURED in Chrome: `--ink` `#1b2024` on `--card` `#1d1c22` = **1.03:1** against WCAG AA's 4.5, on
both `#chrome-theme` and `#chrome-refresh`, so it is `.chrome-btn` and not one control. Un-hovered
both are 9.94:1 — the resting state is readable *by accident*, because `--ink-soft` also kept a
dark-theme value that happens to work on the dark pill. Dark theme is 13.62:1.

`brief-compose.py:93-97` declares 11 tokens on `html` inside `@media (prefers-color-scheme: dark)`;
that keys off the OS, so `data-theme` cannot override it, and its own comment says the shim "only
supplies what nobody supplied". `gen-dashboard.py:1120` `light_vars` declares 17 and omits 8 of the
shim's 11 — `--card --ink-soft --ink-faint --good --defect --structure --structure-bg
--structure-br`. Confirmed live: all 8 read byte-identical in both themes while `--ink`/`--bg` flip.

⚠ Why a new guard when two contrast guards exist. `gen-dashboard.py:1290` `LINK_SURFACES` omits
`--card`, so the failing pair is never enumerated — but adding it would not have helped, because
`scheme_palettes()` reads gen-dashboard's OWN emitted stylesheet and `--card` is not defined there
at all. Each contrast guard owns one stylesheet; the reader opens a page composed from three. This
check measures COVERAGE, not ratio: a ratio needs both colours, and the failure is that one is
silently absent.

Mutation-tested on a temp copy, control proved green first: 9th token falls through → rc=1; a
pinned token becomes covered → rc=1; shim block deleted → rc=2 CANNOT RUN. All three name the case.

Task #201 residue, recorded rather than ticked: `resize_window` reported success twice while
`window.innerWidth` never moved, so "narrowing the window moves the clip" is NOT RUN — substituted
by varying container width (painted chars 106/89/80/52/32 while textContent stayed 201). And the
extension sends keystrokes to the page, not browser chrome, so literal Cmd-F is not drivable;
verified via `window.find()`, which selected the phrase inside a closed card's clipped title.
Falsifier (4), "a single-sentence entry has no triangle", has NO SUBJECT in current data — all 31
entry cards have bodies; the one triangle-less `<details>` is the glossary.

## 2026-09-01
Several of the small checking scripts in this project state, in their own header, how many tests
they run — "16 cases". Nothing ever confirmed that number, because a test suite cannot check its own
final score: to do that it would have to watch itself finish. So the numbers were taken on trust.

They were wrong. Five of the nine were out of date, one of them badly: a script claiming 12 tests
actually runs 27, and another claiming 47 runs 71. Two had drifted the other way and claimed more
tests than they run, which is the direction that matters — a stated number that is too high reads as
reassurance nobody earned.

There is now a check that runs each of those suites and compares what it printed against what it
claims. All five stale numbers are corrected. The check is included in its own list, so the thing
that could not previously be checked from the inside now has something outside it watching — and
that immediately paid off: it failed on itself the first time it ran, because it was reading an
example number quoted in one of its own test names rather than the real total. That was a genuine
bug, found only because it was pointed at itself.

Deliberately not done yet: this check has no entry in the automated sabotage suite — the tool that
breaks our checks on purpose to confirm they notice. Adding one would have collided with the change
already waiting for you in the other pull request, so it is filed as follow-up rather than forced
through. Its ability to fail was instead confirmed by hand, and doing so turned up one more real
weakness, now fixed: if a helper it borrows were renamed, it used to crash in a way that looked like
"the numbers disagree" instead of "this tool is broken".
<!--tech-->
Ships `scripts/check-selftest-counts.py` (17 self-test cases) plus two CI callers. Closes backlog
**#69**; `GROUPS` updated so `gen-backlog-page.py` still builds (78 rows, 55 open).

DESIGN. Runs each declaring suite as a SUBPROCESS and compares the printed total against the
docstring. Reuses `check-plan-code.count_drift` — the declaration form `--self-test  # N cases` and
its regex ALREADY EXIST, and a second copy of one rule is a measured defect in this repo. Also
imports `child_env`, so every spawned suite runs under a redirected `$HOME`: six delivered scripts
resolve `Path.home()` at MODULE level and would otherwise write to the reader's live pages. A new
spawner inherits none of that protection unless it asks — which is exactly how the earlier incident
happened.

POPULATION is PINNED, not derived: 38 scripts accept `--self-test`, 8 declared a count, this is the
9th. Declaring is voluntary, so the ratchet runs both ways — a pinned script that stops declaring
fails, and a new declaration outside the set fails.

CORRECTED: check-anchors 14→15, check-test-counts 12→27, explainer-serve 47→71, gen-goals-page
16→15, page_chrome 35→47.

⚠ SEPARATELY VERIFIED, and it came out clean: `dev-process.md` quotes eight case counts for scripts
OUTSIDE this population. All eight are accurate against the real suites — including
`check-handoff-path.py` (10) and `check-producer-enumeration.py` (11), which print no total at all,
so their case lines were counted directly.

⚠ TWO DEFECTS THE WORK FOUND IN ITSELF.
(1) `printed_total` took the FIRST `N/M … passed` line; this script's own case labels quote example
summaries, so it read 12 while the suite printed 13. Now LAST-match, with the two-summary limit
(`check-dashboard-entry` ends `6/6 cannot-run cases passed`) stated and pinned by a case rather than
hidden. A guard whose test data resembles its input is where a first-match parser breaks.
(2) Mutating it revealed that renaming `count_drift` upstream got past the import and died on
attribute access — uncaught `AttributeError`, rc=1, i.e. the code for "a count disagrees" when the
truth was "the instrument is broken". `BORROWED` is now asserted at load; that mutation re-run exits
**2 CANNOT RUN**.

Hand mutation on a temp copy, control green first, repo untouched: population ratchet neutered →
rc=1; parser reverted to first-match → rc=1 naming both affected cases; borrowed name renamed →
rc=2.

⚠ NOT DONE: no `scripts/mutations/` manifest entry. `EXPECTED_MUTATIONS` is edited by the open
theme-token PR, and a second edit here would conflict; basing this branch on that one would make
this PR silently carry it. Filed as follow-up, to land once that merges.

## 2026-09-01
The tool that runs the second opinion on our own work — an outside reviewer we ask to attack each
plan — turned out to be able to fail without telling anyone, and on one occasion it destroyed the
very thing it was supposed to produce. A review you had already committed was overwritten four times
in one run, and its verdict flipped from "not ready" to "ready" between one reading and the next.

None of that was a mistake in the reviewer. The instruction we sent it said, in one sentence, "write
the review to the path you were given" — except no path was ever given, so it guessed one from the
filenames of earlier reviews, guessed correctly, and wrote over a real file. The same instruction is
right for our other reviewer, which does write files. One shared instruction, two reviewers that
need opposite things.

Three fixes, all in place. The tool now refuses outright, before contacting anything, if the file it
would write already exists — so a review you have already filed cannot be quietly replaced; you can
override that deliberately. It watches the folder while the reviewer works and names any file the
reviewer touched behind its back, whether the run succeeded or failed. And it warns, quoting the
exact phrase, whenever the instruction we are about to send contains a "write a file" order — the
one input guaranteed to make the whole thing fail silently.

**Waiting on you:** one part is a decision, not code. Nothing stops the *caller* from throwing away
the tool's answer — that is how the original failure went unnoticed, with the real result sitting
unread in a log. The choice is between constraining how it is called and having the tool write its
verdict somewhere that must be read. Until you pick, the rule is to capture the result on its own
line.
<!--tech-->
Backlog **#68 (a)(b)(c) shipped; (d) is the open decision.** `scripts/codex-review.py`: refuses with
**exit 2 before contacting any model** when `--out` exists (`--allow-overwrite` to mean it);
`dir_snapshot`/`unexpected_writes` name every file the agent CREATED, OVERWROTE or DELETED in the
`--out` directory, reported on BOTH the success and failure paths; `prompt_demands_a_file` warns and
quotes the matched phrase. 28 self-test cases, 13 new.

⚠ The matcher is deliberately NARROW, and two cases exist to keep it so: a prompt that merely REVIEWS
file-writing code must not trip it, and round 2's brief (which captured cleanly, same wrapper and
model ladder) must stay silent. A warning that cries wolf gets ignored, which would rebuild the
original failure with extra steps.

`docs/plugins.md` states the per-half contract at the DISPATCH POINT in four lines and points onward;
the round-3 story, its exact control, the exit codes and the open (d) decision moved to
`docs/process-rationale.md` → *The review gate that wrote over its own evidence*. ⚠ `check-docs.py`
refused the first draft — plugins.md was 36 lines over its 260-line budget — and its message is
right: move detail, do not raise the budget. The file now sits at exactly 260.

Verified end to end without invoking Codex: existing `--out` → `rc=2`, file byte-identical
afterwards; `--allow-overwrite` proceeds to the model chain; a write-a-file prompt prints the warning
quoting `'Write the review to'`.

## 2026-09-01
A correction to the entry above, which is worth more than the fix it corrects.

While testing the new safeguard, the outside reviewer wrote a file into our reviews folder — a
location nobody gave it, which it worked out from the name of the branch. That is precisely the
failure the safeguard was built to stop, happening during the test of the safeguard, and getting
past it. The reason is almost funny: the new watcher was told to watch wherever the output was being
sent, and for that test the output was being sent to a scratch folder, so it watched the scratch
folder attentively while the real folder was written to behind it.

It watched the unsafe way of calling it and ignored the safe one.

That is now fixed — the reviews folder is watched always, whatever the output setting says. And a
failed run no longer merely complains about files the reviewer left behind; it moves them out of the
way, so a run that failed cannot leave something behind that looks like a finished review. Nothing is
deleted.

The file the reviewer wrote turned out to be a genuine, and correct, critique of this very change. It
has been kept, with a note at the top explaining how it arrived.
<!--tech-->
`ARTIFACT_ROOTS = ("docs/reviews",)`; `watched_dirs()` returns `--out`'s directory UNION the repo
artifact roots, so the documented safe shape (`--out` outside the repo, promote on success) is no
longer the blind spot. Failure path now QUARANTINES created files via `os.replace` into a temp dir
and prints the destination; overwrites cannot be restored from a digest, so `git checkout --` is
named rather than implied — the trade against keeping byte copies of 600+ review files every run is
stated in the docstring. Self-test 28 → **35**.

Also corrected, both caught by that same review: `plugins.md` claimed `--self-test (15 cases)` when
it runs 35, and still advertised `--out docs/reviews/...` as the example — the very call shape the
incident argued against.

⚠ Verified nothing was lost: the path was new (`git log` on it shows no prior commit) and
`find -newermt '-35 minutes'` reports no other modified file in the repo.

## 2026-09-01
Two of our own tests turned out not to be testing anything — and the only reason we know is that we
went looking with a tool that breaks things on purpose.

Some background. We keep a set of small programs that check the project for mistakes. Each one comes
with its own tests. But a test that has quietly stopped working looks exactly like a test that is
passing, so once a year's worth of them pile up you are trusting a lot of green ticks that nobody has
ever challenged. The way to challenge them is to deliberately break the thing being tested and check
that the test notices. If it doesn't notice, the test was decoration.

We did that to the checker that verifies our test counts — the one added a few days ago after it
turned out five of nine declared numbers were wrong. Eight deliberate breakages. Six were caught as
expected. Two were not:

- One test claimed to check that a stray number on an unrelated line gets ignored. It didn't. The
  rule it was aimed at had been changed a while back to read the *last* number rather than the first,
  and that change quietly made the test unable to see what it was pointed at. We deleted the rule
  entirely and the test still passed.
- Another test was checking its own copy of a rule rather than the real one. Delete the real rule and
  the test carried on happily comparing its duplicate against itself.

Both are the same story, and it is a story this project keeps living: two changes that were each
correct on their own, combining into a test that no longer bites. Reviewing one change at a time
cannot see it, because neither change looks wrong.

Both are fixed, and the deliberate-breakage set is now permanent, so neither can rot back without
something going red. No behaviour anyone uses has changed — this is the safety net being checked, not
the product.
<!--tech-->
Task #203, backlog #69 follow-on. Branch `selftest-counts-mutations`, commit `11bd559f`.

Adds `scripts/mutations/check-selftest-counts.json` (8 entries); `EXPECTED_MUTATIONS` **131 → 139**
at `check-plan-code.py`. Measured: `python3 scripts/check-plan-code.py --mutate .` → **7 files, 139
mutations, 0 survivors**. `check-selftest-counts.py` 17 → **18** self-test cases.

The two defects, precisely:

1. **`"a ratio on a line without the word is ignored"` was VACUOUS.** `printed_total` was hardened to
   take the LAST `N/M … passed` match (a real first-match defect it found in itself). The case's
   input was `"scanned 3/4 files\n8/8 passed"` — the stray ratio BEFORE the real summary — so
   last-match-wins discards it and deleting the `if "passed" not in line: continue` guard *still*
   returns 8. **Proved by execution, not reading:** the mutated parser was run standalone against
   both orderings. Input is now `"8/8 passed\nscanned 3/4 files"`, which returns 4 when the guard is
   deleted.
2. **`"every borrowed name is present upstream"` tested its own copy.** It re-derived
   `[n for n in BORROWED if not hasattr(pc, n)]` rather than calling the rule in `_load_plan_code`,
   so `missing = []` there left the case green. Extracted as `borrow_errors(mod)`; the case and the
   refusal now share one implementation, and a new case (`"a missing borrowed name is named, not
   swallowed"`) covers the refusal's own branch via a stub. That is the 18th case.

Also: `"…and it names the script"` indexed `[0]` on a list a mutation can empty. IndexError kills the
suite, so every later case prints nothing and the mutation would be scored against a truncated
`[FAIL]` list rather than a red case. Now `any(...)`.

⚠ **One number left alone deliberately.** The `EXPECTED_MUTATIONS` narrative comment closes one step
at 126 and opens the next at 127. The literal has always matched the table — the case asserting it
has never been red — so the discrepancy is in the prose. Editing a past step to make the story add up
would invent a +1 nobody can point at, so it is annotated in place instead.

Batched doc fixes riding this branch: backlog row 69 said "16 self-test cases" — stale, in the row
about stale declared counts, and invisible to the guard because the guard reads the script's own
docstring, never prose about it. The roadmap's deferred manifest checkbox is ticked; its written
**Fails if** condition (`scripts/mutations/check-selftest-counts.json` does not exist once PR #191
merges) is now satisfied.

Gates green: `check-docs`, `check-roadmap-consistency`, `check-producer-enumeration`,
`check-ratchet-contract`, `check-anchors`, `check-review-rounds`, `check-selftest-counts`,
`check-theme-token-coverage`, `check-explainer-delivery`, `check-arch-findings`,
`check-guard-coverage` — all rc=0. `check-plan-code --self-test` 158/158.

## 2026-09-01
The buttons at the top of this page had labels that vanished when you pointed at them — and finding
out why turned up something more useful than the bug.

If you switched this page to its light look, the two small buttons up top ("Theme" and "Refresh")
stayed dark, and hovering one made its label almost exactly the same colour as the button behind it.
Not hard to read — *invisible*. Sitting still they were fine, which is why nobody caught it: a button
only breaks at the moment you reach for it.

The cause was not a badly chosen colour. The page borrows a set of colours from a shared component,
and that component hands over a dark set whenever it thinks you want dark. The page's light look was
only replacing some of those colours and quietly inheriting the rest — eight of them. One was the
button background, and that one showed. The other seven were sitting there waiting for something to
use them.

Then the check we set up to confirm all this **disproved its own reasoning**, which is the part worth
keeping. The note said the problem only happens when your computer is set to dark mode. So we set the
computer to light mode and tried again — and it happened anyway. It turns out the browser has its own
light/dark setting that overrides the computer's, and that is what the page actually listens to. So
the problem was **more common than we thought**, not less: anyone whose browser is set to dark hits
it, whatever their computer says. Three separate documents recorded that backwards. All three are
corrected.

All eight colours are now filled in, in both looks, and none of them was invented — each was copied
from somewhere that already had the right answer. Checked in a real browser afterwards: the label
went from unreadable to plainly readable, and the dark look is unchanged.

Two extra things. First, we now check the thing that actually matters — *can you read the label* —
rather than only *is the colour filled in*. Those are not the same, and a page could pass the second
while failing the first. Second, the sister page at /goals turned out to be fine, but only by luck:
it happens to define its own colours. Nothing was making sure of that, and nothing checks the other
three pages either. That is filed separately.
<!--tech-->
Backlog **#79 CLOSED**; residue filed as **#80**. Branch `theme-token-coverage`, commit `651f64ab`.

**The refuted premise.** #79 recorded the trigger as OS `prefers-color-scheme: dark`. Measured with
macOS in LIGHT mode — `osascript … dark mode` → `false`, `AppleInterfaceStyle` unset — and it
reproduced at **1.03:1** regardless, because Chrome's own Appearance setting overrides the OS for web
content. A freshly created tab reported `prefers-color-scheme: dark` too, ruling out per-tab DevTools
emulation. Trigger is **"browser reports dark AND page toggled light"**. Corrected in `docs/backlog.md`
row 79, the roadmap section, and `check-theme-token-coverage.py`'s own header.

**The prediction held, so the verdict is the seam.** Counterfactual run through the browser's cascade,
not arithmetic: the eight shim-only tokens set to `initial` on `html` (list from the guard's own
`shim_tokens()` parser, not from reading CSS) → pill `rgba(0,0,0,0)`, hover **15.46:1**.

**Fix.** `gen-dashboard.py` `light_vars` **and** `dark_vars` each declare all 8. `--card`/`--ink-soft`
= this page's own `--panel`/`--fg3`; `--good`/`--defect`/`--structure`/`--structure-br`/`--structure-bg`
= the shim's own values (light from its UNCONDITIONAL block, dark from its media block, so a purely
light or purely dark render is byte-unchanged); `--ink-faint` from `gen-goals-page.py`. Six of the
eight have no consumer here — declared anyway, because the leak is a property of the token SET.
`KNOWN_GAP` → **empty**; guard reads `shim declares 11, light palette declares 25, 0 pinned, 0
unexplained`.

**Property, not mechanism.** 4 cases in `gen-dashboard --self-test` read the EMITTED stylesheet and
require `.chrome-btn` hover + resting to clear `PROSE_CONTRAST_MIN` (4.5) on their own pill, per
theme. A missing token FAILS rather than skipping — undefined is the exact state the bug hid in.
**CONTROL:** stripping the 8 light tokens on a temp copy turns exactly `light: .chrome-btn HOVER…`
and `light: .chrome-btn RESTING…` red (rc=1); restored → rc=0. Dark correctly unaffected.

**Browser verification**, `http://127.0.0.1:7391/dashboard`, `isHovered: true` both times:
light `--card` `#1d1c22` → `#fff`, hover **1.03 → 16.42:1**; dark `--card` `#1b2125`, hover
**13.1:1** (13.62 before — the palette swap, not a regression).

**Mutations:** `scripts/mutations/gen-dashboard.json` 63 → **64**; `EXPECTED_MUTATIONS` 139 → **140**;
`--mutate .` → 7 files, 140 mutations, **0 survivors**.

**#80, the cause behind the symptom.** `page_chrome.py` is ONE module rendering `.chrome-btn` onto
FIVE pages, consuming `--card`/`--rule`/`--ink`/`--ink-soft`/`--structural`, and no page is obliged to
define any of them. Counted: gen-dashboard **0 of 8**, gen-goals-page **7 of 8**, explainer-serve
**2 of 8**. `/goals` measured immune (`--card: #fffefb`) — luck, not mechanism. And
`check-theme-token-coverage.py`'s population is `brief-compose.py` vs `gen-dashboard.py` **only**, so
the ratchet protects one page of five. The #76/#77 seam unified the chrome markup and left the
palette duplicated.

Gates green: check-docs, check-roadmap-consistency, check-anchors, check-theme-token-coverage,
check-producer-enumeration, check-ratchet-contract, check-review-rounds, check-selftest-counts,
check-explainer-delivery, check-arch-findings, check-guard-coverage — all rc=0. Self-tests:
gen-dashboard 294/294, check-plan-code 158/158, check-theme-token-coverage 12/12.

## 2026-09-01 [resolved: 2026-09-01/3]
The tool that runs our second opinion now writes down whether it actually ran — and the note goes
somewhere the person calling it can't quietly drop.

This closes the question that was waiting on you. Background: we ask an outside reviewer to attack
our own work, and the tool that runs it reports success or failure the way most command-line tools
do — with a status code. The trouble with a status code is that it exists for about a second, has
exactly one reader, and is trivially thrown away by accident. That is precisely what happened: the
call was written in a way that reported the status of the *wrong command*, so a failure sat unread
in a log while everyone carried on believing the review had happened.

You chose to have the tool write its verdict to a file instead. It now does, on every path —
succeeded, failed, or refused to start.

But a file on its own would not have fixed anything, and that is the interesting part. If the person
calling the tool is also the only one reading the file, then ignoring the file is exactly as easy as
ignoring the status code — the same problem with an extra step. So the verdict is filed into the
project itself, and one of our automatic checks reads it during the build, where nobody is in a
position to skip it. It complains about one specific thing: the review did not run, yet a document
claiming to be that review was filed anyway. That is the original accident, described precisely.

It stays quiet when the review genuinely could not run and nothing was filed — that is our documented
fallback and punishing it would just push people back toward saying nothing.

Two honest notes. It only sees verdicts that get committed, so someone determined could delete one;
we chose that scope deliberately, because the failure we were fixing was an accident and accidents
do not delete files. And while testing it, the old trap sprang again — a command was piped, the shell
reported success, and the failure was real. The verdict file recorded the truth anyway. That was not
planned, and it is the best evidence we have that this works.
<!--tech-->
Backlog **#68(d) CLOSED** — user decision 2026-09-01. Branch `codex-verdict-file`, commit `b90c8ba9`.
Resolves the ask filed as 2026-09-01/3.

`scripts/codex-review.py` writes `docs/reviews/verdicts/<review-stem>.verdict.json` via a single
`emit()` covering the success, failure and refusal returns — a new branch cannot forget one.
`verdict_path`, `verdict_record` and `write_verdict` are pure/near-pure so cases reach them.

**Design point.** The verdict lands INSIDE the repo, not beside `--out` (which the documented safe
call shape puts outside it). A verdict where only the caller can see it recreates the defect; the
consumer had to be something else. `scripts/check-review-rounds.py` — already a CI ratchet — reads
`verdicts/*.json` and fails on `gate_ran == false` while the named review exists in `docs/reviews/`.

- `gate_ran` is **stated, not derived** from `exit_code`. Case *"exit_code is not consulted"* pins it;
  re-deriving would be a second implementation of the wrapper's rule.
- Unwritable verdict → **exit 2 CANNOT RUN** (an unrecorded success is the failure being fixed).
- Malformed/field-less verdict → **exit 2** on the reading side, never a silent skip.
- Absent verdicts directory → not an error. Verdicts exist only from now; back-filling would be
  inventing testimony.

**CONTROL** through `audit()` on a temp tree: no verdict → 0 problems; `gate_ran:false` + artifact
filed → 1 problem naming the review; `gate_ran:false` + nothing filed → 0 problems.
**END-TO-END:** `--model definitely-not-a-model` → HTTP 400 → verdict `{gate_ran:false, exit_code:1}`,
no `r.md` left behind.

⚠ **The `$?` trap sprang again during that very check** — the run was piped into `tail`, so the shell
printed `rc=0` while the wrapper had returned 1. The verdict file was correct regardless. Unplanned,
and the strongest evidence in this entry.

⚠ **STATED LIMIT:** committed verdicts only. Deleting one pre-commit evades the check. Deliberate —
the fixed failure was an accident, and accidents do not delete files.

Counts: codex-review 35 → **51**, check-review-rounds 14 → **22**. `docs/plugins.md` holds at exactly
**260/260** — `check-docs.py` refused two drafts that went over, and its message ("move detail, do not
raise the budget as a reflex") is why the account sits in `process-rationale.md`.

Gates green: check-docs, check-roadmap-consistency, check-anchors, check-selftest-counts,
check-review-rounds, check-ratchet-contract, check-producer-enumeration, check-explainer-delivery,
check-theme-token-coverage, check-arch-findings, check-guard-coverage.

## 2026-09-01
The buttons at the top of every page stopped borrowing a colour they had no business borrowing —
and the check that was supposed to make that safe turned out to say the opposite.

You asked for the shared bar at the top of these pages to supply its own colours instead of taking
them from whichever page it is sitting on. Reading the code first turned up a problem with that: the
module has a written rule saying it must *never* name a colour, backed by an automatic check that
rejects any colour written into it — a check that already caught one slipping in. The reason is
good: five pages look deliberately different, and a shared component naming colours would make them
all look the same.

So the literal version of your instruction would have deleted a decision someone made on purpose.

Looking at what the bar actually borrows narrowed the problem a lot. It takes five things from the
page. Four of them are text and border colours, which are safe: a page picks its text colour to be
readable on its own background, so borrowing it is fine. The fifth was a *background* — a second
surface the page's text colour was never checked against. That one token was the entire cause of
yesterday's invisible-label bug.

The fix is that the buttons no longer take a background at all. They are outlines now, sitting
directly on the page, so their label is on the surface the page chose its text for. No colour named,
the rule intact, all five pages fixed at once.

One thing nearly went wrong and was caught by measuring instead of assuming. Taking the background
away moves the label onto the page's main background, which is a different surface — and on the
dashboard, the grey used for that label measured just under the readability standard there. That is
the *same* mistake this page's chart legend made once before, at the identical number. Fixed by
using the darker grey that was already chosen for exactly this situation.

Checked in a real browser afterwards, in both looks and on two different pages. Everything reads
clearly.
<!--tech-->
Backlog **#80 CLOSED** — user chose (b). Branch `chrome-owns-its-surface`.

⛔ **Literal (b) was refused by an existing decision.** `page_chrome.py`: *"reads the page's OWN
variables, never its own colours … if this module named a colour, every page would acquire it"*,
enforced by a case failing on any hex (it caught a `#777` pre-ship).

**The narrowing.** Of five consumed tokens, four (`--ink-soft`, `--ink`, `--rule`, `--structural`)
are foreground/border with `currentColor`/`inherit` fallbacks — page-derived and safe by
construction. Only `--card` supplied a **second surface**. `.chrome-btn{background:transparent}`.
⚠ `var(--card, transparent)` could never have helped: the shim **defines** `--card`, so the fallback
never fires. The fix is refusing to borrow, not defaulting better.

⚠ **It moved the floor.** Resting label now on `--bg`: dashboard `--ink-soft` #6b7780 = **4.32:1**,
under AA — identical to the legend's recorded trap (*"the legend sits on --bg, not --panel"*, same
4.32). Retuned to `#5c5b67`, the value already chosen for that surface. `--ink-soft` has exactly one
consumer (the chrome), so the change is contained.

**Browser-verified**, browser reporting dark throughout: dashboard light **15.46 / 6.28**, dashboard
dark **14.37 / 5.84**, `/goals` light resting **7.36** with border intact, all `pillBg:
rgba(0,0,0,0)`.

**CONTROL:** reverting to `var(--card,transparent)` turns all three new cases red (rc=1). The rule
asserts the PROPERTY — *paints no background it did not choose* — and pins the four legal tokens by
name, so a fifth cannot arrive unexamined. page_chrome 47 → **50**.

**`GROUPS` fired twice and was right twice** — when #68/#79 closed and #80 was filed, then again when
#80 closed. It refuses to build until the open set is described in plain words. Not a red; the
mechanism working, exactly as the 2026-08-31 entry describes.

⚠ **Residue, stated:** the theme-token guard's population is still the dashboard alone, and three
duplicated palettes still exist. This removed the chrome's DEPENDENCE on them, not the duplication.
Option (a) stays available and is cheaper now — the property is one contrast pair per page.

Gates green: check-docs, check-roadmap-consistency, check-anchors, check-selftest-counts,
check-review-rounds, check-ratchet-contract, check-producer-enumeration, check-explainer-delivery,
check-theme-token-coverage, check-arch-findings, check-guard-coverage. Self-tests: gen-dashboard
294/294, page_chrome 50/50, gen-goals-page 15/15.

## 2026-09-01
Fifteen minutes ago I broke the main branch, and the way I broke it is worth more than the fix.

Every change here goes through an automatic check before it is allowed in. This time I merged a
change *while that check was still running*, because I used a command I believed would wait for it.
It does not — on this project that setting was never switched on, so the command quietly merged
straight away instead. The check then ran on the main branch, after the fact, and failed.

Compounding it: earlier today I agreed to skip one slow local check on the grounds that the
automatic one would catch anything. That was reasonable on its own. It is only reasonable if I
actually wait for the automatic one. I did both things — skipped locally, and did not wait — and the
two together are what put a failure on the main branch.

The failure itself was small and the machinery caught it exactly as designed. Yesterday's colour fix
changed one grey. A deliberate-breakage test was pinned to the old grey by name, so it no longer
matched anything, and the tooling refused rather than pretending the test still ran.

Fixing that revealed a second thing I would not otherwise have found: because the buttons no longer
paint a background, that same test now only exercises one of the two things it used to. The other
had quietly lost its safety net. It has its own test now.

Everything is measured green again. The lesson is recorded rather than smoothed over: skipping a
local check is only safe if you wait for the remote one.
<!--tech-->
Branch `fix-mutation-anchor`, repairing a red I introduced by merging PR #197 early.

**Root cause of the red:** `gh pr merge --auto` does **not** queue on this repo — auto-merge is not
enabled, so `gh` falls back to an immediate merge. `verify` was `IN_PROGRESS` at the time; it ran on
master and failed. Compounded by the 2026-09-01 lighter-verification decision to skip local
`--mutate .` *because CI runs it* — sound only if CI is actually awaited.

**Defect 1 — orphaned anchor.** PR #195's mutation *"the light palette stops covering the OS-dark
shim's tokens"* pins the literal `light_vars` string, including `--ink-soft:#6b7780`. PR #197 retuned
that to `#5c5b67` for the AA floor. Anchor stopped matching → `anchor NOT FOUND — it was not applied,
so its 'caught' verdict would be meaningless`. The manifest refusing is correct behaviour.

**Defect 2 — only visible after fixing 1.** The `expect` named two cases, by pre-#80 names (*"on its
own pill"* → *"on the page surface"*). Not just a rename: with the chrome no longer painting a pill,
removing the eight gap tokens now reaches only **RESTING** (`--ink-soft`). **HOVER** reads `--ink`,
which the light palette still defines, so it stays green. One red case now, not two — which left the
HOVER guard with **no mutation at all**. Added *"the light palette stops defining the hover ink"*.

gen-dashboard 64 → **65**; `EXPECTED_MUTATIONS` 140 → **141**; `--mutate .` → 7 files, 141 mutations,
**0 survivors**. check-plan-code --self-test 158/158.

⚠ **Also learned:** `check-dashboard-entry.py` did not recognise `NO-ENTRY:` wrapped in `**bold**` in
a PR body — the line must start with the marker. Same emphasis-tolerance class as `REVIEW GAP:`,
which was fixed once already. Not filed; noted here because the next person will hit it.

## 2026-09-01 [needs-you]
You spotted that answered items still say "waiting on you", and the cause turned out to be me, not
the page.

There is already machinery for this. When something you have answered gets marked as settled, the
page is supposed to change its wording from "Decide:" to "Decided:" and drop the orange emphasis —
built and tested a few days ago. It has never once run, because it only recognises a specific way of
writing the question, and I have always written those questions as ordinary sentences instead.

So the page could not know those sentences were questions. Nothing was broken; the feature was
simply never fed.

Costs nothing to start doing right, and this entry is the first one written the correct way — you
should see the difference below when it settles.

**Decide:** should I also add an automatic check that refuses an entry claiming to wait on you without writing the question in the recognised form?
- hold it for now, see whether writing them correctly is enough [recommended]
- add the check as well
- neither — this is fine as it is

I lean toward holding: the check would have to recognise phrases in freely written prose, and this
project has repeatedly found that checks like that go stale silently. If I slip back into the old
habit, that is the evidence the check is needed.
<!--tech-->
Filed as backlog **#81** 🟢 at the user's request. Branch `file-ask-grammar-disuse`.

**MEASURED:** `Decide:` appears **zero times** in `docs/dashboard-entries.md`. All seven "waiting on
you" occurrences are free prose. The three the user cited — **2026-08-30/6**, **2026-08-30/5**,
**2026-08-29/1** — are resolved and still read in the present tense.

`_ask_block` (`gen-dashboard.py:279`) flips a resolved ask's opener to `Decided:` and drops the
warning colour, with `settled` **derived from the badge** (`:1072`). Shipped in PR #186, tested,
mutation-covered — and unreachable from prose, because prose carries no state. A derived badge over
a hand-written body is two implementations of one rule; only one can update itself.

⚠ `_ask_block` renders nothing without **option bullets**, which is why this entry's ask carries
three. "Whether to merge" must be written with its choices.

**Tier 3 is impossible by design:** the store is append-only and ids are POSITIONAL — editing the
three existing entries renumbers ids and silently rebinds standing `[resolved:]` markers. They stay,
and they were true on their date.

## 2026-09-01 [resolved: 2026-09-01/10]
You chose to hold the automatic check. No code changes; what changes is how I write.

The question was whether to add a check that refuses an entry claiming to wait on you unless the
question is written in the form the page can recognise. You said hold it and see whether simply
writing them properly is enough — which is what I recommended, so this is not a compromise between
us, it is the same answer twice.

What that means in practice: from now on, every question I put in front of you here gets written as
a question with its choices listed underneath. Not as a sentence buried in a paragraph. That is all
tier one ever was.

Now the part I got wrong, which you should know because I told you the opposite this morning.

I said the page's mechanism for marking a question as answered had never once run, because I had
never written a question in the form it recognises. That is false. I checked it properly this time,
by asking the page's own reader rather than searching the text myself, and there was already an
entry from yesterday with two questions written correctly — both answered, both already displaying
as settled. The machinery has been working. I simply had not looked at it with the right instrument.

What went wrong is worth one sentence, because it is a mistake this project keeps making in
different costumes: I searched for questions written at the start of a line, and every real one is
written in bold, so my search found none and I believed the feature was dead. The search was
looking at a different thing than the page reads.

So the real problem is smaller and more ordinary than I described. The page understands these
questions perfectly well. I have just been inconsistent — sometimes writing them properly,
sometimes burying them in a paragraph — and the three entries you spotted are the buried ones. Being
consistent is the whole fix, which makes holding the automatic check a better decision than it was
when you made it, not a worse one.

I should also be straight about one limit, because it affects what you will see. The page records
*that* a question was answered, never *which* answer you gave. So your choice survives only because
it is written into this text. If that turns out to matter to you, it is a separate change.

There is no deadline on this and nothing expires. If I go back to burying questions in prose, that
is the evidence the check is needed, and we add it then.
<!--tech-->
Backlog **#81 — tier 2 HELD by user decision 2026-09-01.** Resolves the ask filed as
**2026-09-01/10** (PR #199, squash `8ef18f4d`). Tier 1 is in force and needs no mechanism: author
asks as `**Decide:** <question?>` + `- option` bullets, all one paragraph.

⛔ **#81's HEADLINE PREMISE IS REFUTED, by the render this entry was written to produce.**
*"The ask grammar has never been used, so the settle mechanism has never fired"* is **false**.
MEASURED by `check-dashboard-entry.decisions()` — the gate's own parser, over every entry:

| Entry | Decisions the GATE counts | State |
|---|---|---|
| **2026-08-31/3** | **2** | resolved by `[resolved: 2026-08-31/3]`; both render `<div class="ask settled">` |
| 2026-09-01/10 | 1 | resolved by this entry |

Render of the store as of this commit: **3 settled ask blocks, 0 live**. Two of the three predate
today. The mechanism has fired **since 2026-08-31** and was never dead.

**How the false measurement happened** (reconstruction consistent with every number, not a recovered
command): `grep -c '^Decide:'` → **0**, because all 10 occurrences are `**Decide:**`. Anchoring at
line start cannot see a bold marker. That is the SAME emphasis-blindness class as `NO-ENTRY:` and
`REVIEW GAP:` — recorded in entry 2026-09-01/9's tech note, hours earlier, about a different script.
The instrument that measured the grammar had the defect the grammar's own gates keep being fixed for.

**What survives, unchanged:** the user's actual report. 2026-08-30/6, 2026-08-30/5 and 2026-08-29/1
carry their asks as PROSE, so they read present-tense after resolution. The defect is **inconsistent
authoring**, not an unused mechanism — narrower than filed, same fix (tier 1), same severity (🟢).

**Falsifier for this entry's own claim, run before committing:** `[resolved: 2026-09-01/10]` must
make `_ask_block` (`gen-dashboard.py:279`) emit `<div class="ask settled">` with
`<span class="was">Decided:</span>` for 2026-09-01/10, and `unresolved()` must return `[]`. Both
observed. ⚠ Counting the STRING `Decided:` in the HTML is NOT this falsifier — it returns 7, mostly
from this entry's own prose. Count the rendered BLOCKS.

⚠ **Stated limit, not a defect:** `[resolved: <id>]` records the resolving ENTRY, never the CHOICE
(docstring `:305-306`). The page cannot display which option was taken, so the choice lives only in
the prose above. Retaining the choice structurally would mean widening the marker grammar — a
separate change, not filed.

**Not re-litigated:** tier 3 remains impossible by design (append-only store, positional ids).

## 2026-09-01
The check that makes sure every change gets written up here could not see the write-ups themselves.

There is an automatic check that refuses a change if nobody wrote a note about it. It has a sensible
exception: if the *only* thing you changed was this notes file, you obviously do not owe another
note. That exception was doing too much work. It stopped the check dead, so the note you had just
written was never looked at — and writing only a note is the most common way notes get written.

The effect was that a badly formed note would sail through and only reveal itself on the page, as an
item saying "could not read this". The page would tell you; the check never would.

It was one yes-or-no question being asked to answer two different things — *does this change owe a
note?* and *is the note it wrote any good?* — so excusing the first quietly excused the second. Those
are now two questions. The exception still applies to the first, exactly as before. The second now
runs no matter what.

I confirmed the old behaviour before changing anything, by feeding the same made-up note to the old
version and the new one: the old one said fine, the new one refuses and names what is wrong with it.
That is the whole change, and it is the sort of hole that only ever shows up when you go looking for
it, because everything reports success.
<!--tech-->
Backlog **#78 — half (1) shipped, row stays 🟠 because half (2) is open.** Branch `fix-78-entry-gate-content-split`.

**THE DEFECT, and it was live on the branch that found it:** `verdict()` short-circuits at
`if not real: return 0, "no tracked files changed outside the exempt paths"`
(`check-dashboard-entry.py:145-148` as filed) ABOVE every other branch, and
`docs/dashboard-entries.md` is in `EXEMPT_FILES`. So an entry-only branch never reached any
inspection of the entry it added. Pinned by its own case — `case("entry-only branch is exempt", …)`.

**CONTROL, run before the fix and quoted rather than characterised.** Same fake git output
(entry-only branch, added header `## 2026-02-30 [needs-you]`), master's copy vs the branch's:

```
BEFORE (master): rc=0  ok — no tracked files changed outside the exempt paths
AFTER  (branch): rc=1  REFUSED — the entry this branch adds is malformed … not a real calendar date
```

**THE SPLIT.** `_added_entry_line` stays strict — a malformed header is not an entry — because that
is correct for *does this branch owe an entry?*. New `added_entry_problems()` recognises the
**ATTEMPT** (`^\+##(?!#)`, not `^\+## <valid date>`) and reports why it fails, through the SAME
`header_error` the page's parser uses. `verdict()` takes `entry_problems` and refuses on it **above**
the exemption — the ORDER is the fix; below it the hole simply returns.

⚠ `(?!#)` is load-bearing in the other direction: without it a `###` sub-heading inside a body reads
as a failed entry header and the gate refuses entries that are fine. Mutation-covered.

⚠ **SCOPE, stated rather than implied — the decision grammar is NOT wired in here.** Doing so would
refuse a `[needs-you]` entry carrying no parsed decision, which is **#81's tier-2 guard, HELD by
user decision today**. Different mechanism (structural flag, not prose phrase-matching), same
effect — so it is the user's call, not a side effect of this fix. `added_entry_problems` is the seam
that makes it a one-line change if #81's re-open trigger fires.

Counts: `--self-test` **92 pure + 13 cannot-run**; `check-dashboard-entry` mutations **18 → 23**;
`EXPECTED_MUTATIONS` **141 → 146**. THREE of the five mutations are on the WIRING — the predicate can
be perfect and never called, and every pure case stays green either way.

⚠ **The pinned total refused the run and was right to.** Bumping the per-file count to 23 without
the separate `sum(...) == 141` case made the control exit 1, and the harness printed
*"CANNOT RUN … Every verdict below would be an artefact"* rather than re-baselining. Two independent
statements of one number, behaving as designed.

**NOT done here, and it is half of #78 as filed:** the gate runs `if: github.event_name ==
'pull_request'` while the skill regenerates the page immediately — the reader still sees the page
before the gate sees the branch. That half is a CI-timing decision, not a code defect, and is left
open on the row.
## 2026-09-01
A way of writing a note-exemption that looks completely normal was being rejected.

When a change genuinely does not need a write-up, you say so in the pull request with a short marker
and a reason. If you wrote that marker in **bold** — which is the natural thing to do, and which the
project's own documents do constantly — the check did not recognise it and refused the change anyway.

Nobody noticed because the failure is loud and harmless: you get refused, you shrug, you rewrite the
line without the bold, it works. It never let anything through that should have been stopped. It just
wasted a minute and made the tool look arbitrary.

This is the third time today that the same underlying mistake has surfaced in a different place —
looking for a word at the very start of a line, when in practice people decorate it. Earlier the same
thing made me report a feature as completely unused when it had in fact been used the day before.

Bold now counts. Everything that should *not* count still does not: a marker inside quoted code, or
indented, or in a comment, or in a quotation still exempts nothing, because those all mean somebody
was showing an example rather than making a declaration. Bold means the opposite — somebody made it
louder on purpose.
<!--tech-->
Branch `fix-no-entry-emphasis`, stacked on `fix-78-entry-gate-content-split` (PR #201). **NOT a filed
backlog row** — noted in entry 2026-09-01/9's tech block as *"not filed; filing is the user's step"*,
and fixed here under the AFK instruction to work items that need no decision. Trivially revertable.

**MEASURED BEFORE THE FIX**, `exemption_reason` on six bodies:

```
'NO-ENTRY: typo fix'            -> 'typo fix'
'**NO-ENTRY:** typo fix'        -> None      <- refused a well-formed declaration
'*NO-ENTRY:* typo fix'          -> None
'> NO-ENTRY: quoted'            -> None      <- correct, blockquote is inert
'NO-ENTRY: keep **bold** here'  -> 'keep **bold** here'
```

**⚠ EMPHASIS IS NOT AN INERT CONTEXT — that is the whole distinction, and it is why this is a fix
rather than a loosening.** Fenced, indented, commented and blockquoted all mean *not deliberate*, so
they must not exempt. `**NO-ENTRY:**` means the OPPOSITE: someone made it louder. The stated principle
("an exemption must be DELIBERATE") already covered this; only the implementation did not.

**THIRD INSTANCE OF ONE CLASS IN ONE DAY:** `REVIEW GAP:` (fixed for it once already), this, and
`Decide:` — where `grep -c '^Decide:'` returned **0** over **10** bold occurrences and put a false
premise into backlog #81 and PR #199. **A marker people are told to write WILL be emphasised.**

`_declaration_reason()` is ONE definition called from BOTH of `exemption_reason`'s scan points — the
bare line and the text before an inline `<!--`. They were separate copies of `startswith(NO_ENTRY)`
and would each have needed the same fix; one mutation exists purely to prove the second site is
wired, because no other case reaches it with an emphasised marker.

The closer is stripped **only when it matches the opener**, so the author's own emphasis inside a
reason survives verbatim (`NO-ENTRY: keep **bold** here`), and `**NO-ENTRY:* odd` keeps the unmatched
`*` as reason text rather than silently eating it.

Counts: `--self-test` **104 + 13**; `check-dashboard-entry` mutations **23 → 27**;
`EXPECTED_MUTATIONS` **146 → 150**.

⛔ **THE MOST USEFUL THING THIS BRANCH FOUND, and it is about the branch itself: collapsing two
copies into one helper ORPHANED TWO EXISTING MUTATIONS.** `head path skips the indent check` and
`line-leading rule removed` both anchored on text the refactor deleted. The harness refused them by
name — *"anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless"* — and
reported **FAILED**, not a clean run with two fewer mutations.

**This is the SAME CLASS as the red I put on master four hours ago** (`86ecade5`, PR #198: the #80
palette retune orphaned a mutation anchor). Twice in one day, and the shape is exact: *a refactor
that improves the code silently unhooks the coverage that was protecting it.* Both repaired to the
new anchors with their INTENT preserved — delete the indent guard, accept the marker mid-line — so
the same two cases still go red.

⚠ **And a third refusal worth keeping:** my new mutation named TWO expected cases, one of which
(`NO-ENTRY reason is echoed`) never goes red, because it asserts the reason is a SUBSTRING of the
message and an un-stripped reason still contains it. The harness rejected the entry rather than
crediting it — *"an expect must name EXACTLY ONE, or it cannot show which case is the guard"*. A
mutation whose expectation is vaguely right is a mutation that proves nothing.

**None of these three would have been visible from a green suite.** 104/104 passed throughout.

## 2026-09-01
The review I skipped found something my checks could not, within minutes of running.

Earlier today three changes went to the main branch without the second-opinion review this project
normally requires. You asked whether anything had gone out unmarked; it had, and I ran the review
afterwards.

It found a real hole, and it is the same kind of hole those three changes were meant to close. A
note can carry a marker saying "this answers an earlier question", and the marker is supposed to name
which one. If you wrote the marker but left the name off, the check waved it through and the page
then displayed the note as unreadable. Exactly the split the morning's work was about: check happy,
page broken.

It is fixed. The check now refuses a marker with nothing after it, and — this is the part I like —
it refuses with word-for-word the same sentence the page uses, so the two cannot drift apart by
quietly disagreeing about phrasing.

I also went looking for the rest of the family rather than just the reported case. There are five
such shapes. Two are now closed. The other three ask a question no check of this kind can answer:
whether the name points at a note that actually exists is a fact about the whole file, and this
check only ever sees the lines you just added. Closing those means moving a bigger piece of the
machinery, which is written down as a proper item rather than rushed in now.

Worth being plain about the score: my own tests, all one hundred and fifty of my deliberate
sabotage checks, and every automatic gate passed straight over this. They all measure the work
against itself. The outside reviewer looked once and saw it.
<!--tech-->
Fixes the **High** from `docs/reviews/entry-gate-retro-r1-codex.md` (Codex, retrospective round 1
over `8ef18f4d..4de2c055` — PRs #200, #201, #203, all merged unreviewed). Files backlog **#82** for
the referential half.

**MEASURED, gate vs page, before:** `header_error("## 2026-09-01 [resolved:]") -> None`,
`added_entry_problems -> []`, `verdict(entry-only) -> (0, "no tracked files changed outside the
exempt paths")` — while `parse_entries` set `"[resolved:] with no entry id after it"`.

**THE CLASS IS FIVE SHAPES, and it splits:**

| shape | kind | now |
|---|---|---|
| `[resolved:]`, `[resolved:   ]` | SYNTACTIC | **closed** |
| `[resolved: nonsense]`, `[resolved: 2026-09-01/99]`, `[resolved: 2026-13-45/1]` | REFERENTIAL | **#82** |

⚠ **A tighter regex was the wrong fix and I measured that before writing one.** The obvious
`[^\]]*` → `[^\]]+` closes `[resolved:]` and NOT `[resolved:   ]`, because `\s*` matches nothing
and `[^\]]+` then eats the spaces. The shipped fix is an explicit named check in `header_error`
returning **the page's exact string**, so gate and page agree on the WORDS, not merely on refusing.

⚠ **The duplicate-anchor rule earned its keep.** My first attempt put both mutations on the one
regex line; `check-plan-code` refused — *"repeats the edit anchors of an earlier entry — it measures
nothing new"* — which pushed the fix into two separately-mutable decisions (`payload = …strip()` and
`if not payload:`). The harness improved the design, not just the coverage.

⛔ **`header_error`'s docstring claimed gate and page "CANNOT disagree about what a header is". That
was false, and false before the sentence was written** — `parse_entries` has a PASS 2 the ratchet
never had. Corrected in place; the honest contract is now stated as SYNTAX agrees, REFERENCE does not.
**I repeated that false claim in #201's commit message.**

⛔ **And the obvious structural fix is FORBIDDEN:** having the gate import `parse_entries` inverts
`_gate_module`'s written rule — *"a GATE must not import the thing it guards"*. Measured: a lazy
import works technically, which is exactly why the rule has to be honoured on purpose. #82's shape
is therefore to RELOCATE the parser into the gate, arrow preserved.

Verified: `--self-test` **108 + 13**; `--mutate .` **7 files / 152 mutations / 0 survivors**; real
store **44 entries, 0 parse errors**, all five `[resolved:]` markers still bound; `check-docs` OK.
Counts: mutations 27 → **29**, `EXPECTED_MUTATIONS` 150 → **152**.

⚠ **The Claude review half NEVER RAN** (idled twice, produced nothing). Recorded as
`REVIEW GAP: claude` in the review doc. This round is **NOT CONVERGED** and one-sided — and a
single-half round is the shape this project has already recorded as unsafe.

## 2026-09-01
Your dashboard was telling you something untrue about your own work, and I put it there.

Near the bottom of the page there is a list of changes that were allowed to skip their write-up.
The point of it is so you can see how often the discipline slips — if eleven of the last twelve
changes skipped a note, that list is how you would find out.

It was empty. Then a change I merged a few hours ago made it show one entry: a change from earlier
today, marked as having skipped its write-up. That change wrote forty-nine lines of write-up. So
every item in the list was false, and it was false in the direction that flatters me.

The cause is worth understanding because it is not obvious. I widened what counts as a valid
"skip this one" note. But that same reading is also used, after the fact, to re-examine changes
that were merged long ago — so widening it did not merely change what happens next, it rewrote what
the page says about the past.

The repair is that the list now checks whether a change actually wrote a note, rather than trusting
what its description claimed. A change that wrote one cannot appear as having skipped one, whatever
its text says. That holds regardless of how the wording rules change later.

Confirmed against the real data: before, the list showed that one false item; after, it is empty
again, which is the truth.

I did not find this. The second reviewer did — the one I reported as having produced nothing. It had
in fact done the whole review and my message about it never arrived.
<!--tech-->
Fixes the second **HIGH** of the retrospective round, from the Claude half
(`docs/reviews/entry-gate-retro-r1-claude.md`, recovered from its transcript).

**CONTROL against live `gh`, same call both sides:**

```
BEFORE (master)      no_entry_prs(40) -> [198]
AFTER  (this branch) no_entry_prs(40) -> []
```

**ROOT CAUSE, and it is the generalisable part:** `no_entry_prs` RE-DERIVES a verdict for
already-merged PRs by re-parsing their bodies through the gate's CURRENT `exemption_reason`. PR #203
widened that matcher to accept `**NO-ENTRY:**`. PR #198's body carries
`**NO-ENTRY: repair of a red I introduced in #197…**` AND it changed `docs/dashboard-entries.md` by
49 lines. So the widening did not only change future verdicts — **it rewrote the displayed past**,
against a docstring that says *"the page shows exactly the exemptions the gate granted. A display
that disagrees with the gate is worse than none."*

**THE FIX IS THE CLASS, NOT THE INSTANCE:** a declared exemption is not a taken one. The listing now
requires that the PR did **not** touch the entry store, using `gh`'s own file list as the authority
— so it is correct no matter how the matcher changes later. `ENTRY_STORE` is DERIVED from
`STORE_DEFAULT`, not written out again, because a path mismatch here fails SILENTLY (nothing would
ever match and the defect would quietly return).

⚠ A missing `files` key is a CANNOT-TELL that returns an error, not a default of "wrote no entry" —
mutation-covered, because the fail-open version is the one that restores the bug invisibly.

Counts: `gen-dashboard --self-test` **298**; mutations gen-dashboard 65 → **67**,
`EXPECTED_MUTATIONS` 152 → **154**, 0 survivors.

⛔ **STILL OPEN — the Claude half's first High:** `ENTRY_ISH`'s `(?!#)` excludes `###` while the
renderer's `BLOCK = ^##\s*\S` MATCHES it, so an entry body carrying a sub-heading passes the gate
and renders "could not parse". My justification for `(?!#)` — *"several entries use one"* — is FALSE:
the store contains **zero** `^###` lines. I wrote that in a comment, repeated it in #201's commit
message, and pinned it with a mutation. Not fixed here; it needs the two matchers derived from one
grammar rather than hand-written twice.

## 2026-09-01
Closed a trap in the dashboard's own plumbing: an entry containing a sub-heading would have been cut in half, losing everything written after it.
Two separate programs read the file these entries live in — the one that builds the page you are
reading, and the check that refuses a branch whose entry is malformed. Each kept its own private
rule for where one entry stops and the next begins, and the two rules disagreed about a single
shape: a line starting with three hashes. The page-builder treated such a line as the start of a
brand-new entry; the check did not.

The consequence was not a visible error. It was silent loss: the entry would render truncated at
the sub-heading, the prose after it would be absorbed into a fragment labelled "could not parse
this entry", and nothing anywhere would say that words had gone missing.

Nobody has hit this — no entry has ever used a sub-heading — so no page you have read was affected,
and this change alters nothing you can see today. The page renders byte-for-byte identically. What
changes is that the trap is gone for whoever writes the first one.

There is now one rule instead of two. The check owns it, and the page-builder asks the check rather
than keeping a copy, so the two can no longer drift apart.
<!--tech-->
Branch `fix-block-start-divergence`. The open High from the retrospective dual review recorded at
the end of entry 2026-09-01/15.

**The previous entry got the DIRECTION wrong, and the spec settles it.** That entry proposed the
gate's `(?!#)` was what "re-opened the divergence", and warned that fixing it meant deleting a case
and the mutation pinning them — *"a test now protects the bug."* It does not. Spec §6.2 defines
block start as `` `## ` `` at column 0 **with the space**, and its `##`-inside-detail row reads *"only
column-0 `## ` splits blocks"*. So the GATE was correct and `gen-dashboard.py`'s
`BLOCK = ^##\s*\S` was the divergent one — `\s*` takes zero characters and `\S` takes the third `#`.
Nothing was deleted; coverage went up.

Measured end to end before choosing, because the symptom was worse than "could not parse":

    ## 2026-08-28        -> entry renders, body TRUNCATED at the ###
    ### Worth knowing    -> splits off as a second block, "could not parse this entry"
    After the heading.   -> swallowed into the orphan; never reaches the reader

⚠ **That example is INDENTED, not fenced, and writing it fenced first is how a second live defect
was found.** §6.2 says *"indent **or fence** it to include one literally"* — but `parse_entries`
has no fence awareness whatever: it tests every line against `BLOCK` regardless of fencing. Written
in a ``` block, the `## 2026-08-28` line above split THIS entry, rendered the remainder as *"could
not parse this entry"*, and — worse — CLAIMED the id `2026-08-28/2`, which is exactly how a standing
`[resolved:]` gets silently rebound to the wrong item. Measured on the real store with the real
parser: 48 entries, 1 error, before this was indented. Same shape as the bug this branch fixes — the
spec promises a behaviour the code never implemented — and NOT fixed here. Filed below.

`BLOCK` MOVED to `check-dashboard-entry.py` beside `HEADER`/`FLAG`; `gen-dashboard.py` binds
`BLOCK = _GATE.BLOCK` (required, not `getattr`-optional — without a block-start rule there is nothing
to parse); `ENTRY_ISH` is now DERIVED, `r"^\+" + BLOCK.pattern.lstrip("^")`. Dependency arrow
unchanged and still generator → gate.

⚠ It stays permissive about the space — `##Nospace` still starts a block — deliberately. That is a
near-miss header, and swallowing one into the previous body is the silent failure the gate exists to
prevent. `###` differs in kind: deliberate markup, not a typo.

**The alternative was rejected on measurement, not taste.** Making the gate refuse `###` instead
would have both sides agree too, but `header_error("### Worth knowing")` returns *"check the space
after the ##"* — misleading advice for a deliberate sub-heading — and its only advantage, failing
loudly pre-merge, is defeated by backlog #78 half (2), still open: the gate runs on `pull_request`
while the skill regenerates the page immediately, so the reader sees the page before the gate sees
the branch.

**The control did real work.** Reverting only the fix on a temp copy reddened the new cases — and
exposed one of my own as VACUOUS: `sub[0]["error"] is None` passed in BOTH worlds, because `sub[0]`
is the well-formed header and the error lived on the orphan `sub[1]` the bug created. Rewritten to
assert across all returned entries; it now fails in the control.

⚠ **A refactor orphaned a mutation, for the third time in this repo** — caught by scanning every
anchor against disk, not by recollection. `entry-attempt regex stops excluding sub-headings` pinned
a literal that no longer exists. RETARGETED onto `BLOCK` (not duplicated), so one edit now reddens
both suites. The same scan found `gen-dashboard`'s `BLOCK` had **zero** mutation coverage for its
whole life — the regex at the centre of this bug was the one thing nothing measured. New mutation
restores the page's private copy, failing exactly the way the original defect did.

**REVIEW ROUND 1 — NOT CONVERGED at dispatch: 3 Blocking, all addressed.**
`docs/reviews/whole-branch-block-start-divergence-review.md`. Two of the three were mine and
neither was visible by reading — the Codex half found both by running `--mutate .`:

- `expect` in the gate's manifest named a case from the RENDERER's suite. `mutate_delivered` runs
  `run_suite(d, fname)` for the MUTATED FILE ALONE (`check-plan-code.py:694`), so it resolved to
  zero red cases. **I had told the user the harness runs every suite per mutation. It does not, and
  I never ran it before saying so** — the same shape as the defect this branch fixes.
- The other `expect` dropped a leading `...` the case name actually carries. Exact match, not
  substring (`check-plan-code.py:730-735`, a round-6 hardening).
- Third Blocking is the FENCE defect above — pre-existing, deferred, awaiting your call.

⚠ **REVIEW GAP: claude — author self-review, not an independent half** (session instructions
forbid spawning a reviewer unless asked). Recorded rather than hidden. It still found that the
agreement case was an UNPROVEN guard: load-bearing when measured, but the `BLOCK` mutation cannot
prove it fires, because corrupting the shared rule moves both sides together and leaves the case
green. Only breaking the DERIVATION separates them, so that is now its own mutation.

Counts: `check-dashboard-entry --self-test` 108 → **112** + 13; `gen-dashboard` 298 → **301**;
`check-plan-code` 158; `EXPECTED_MUTATIONS` 154 → **156** (gen-dashboard 67 → 68, gate 29 → **30**).
The gate's +1 is NOT the relocation — that was a retarget and deliberately moved no count. It is the
derivation guard the review added. `--mutate .`: 7 files, **156 mutations, 0 survivors**, rc=0.
All guard self-tests green; `check-selftest-counts`, `check-docs`, `check-anchors`,
`check-ratchet-contract`, `check-review-rounds` green on real runs.
Falsifier: rendered page byte-identical before and after (958,032 bytes both).

## 2026-09-01
The spec told entry authors they could fence a code example. The parser never learned to read fences, so one example could quietly delete every entry after it.
Entries are written in a file, and the page splits that file into cards wherever a line begins a
new entry. The guide for writing them says: if you want to *show* what an entry header looks like,
put it in a code block and the page will leave it alone. The page never did leave it alone. It had
no idea what a code block was.

So an entry containing a code example got cut in half, and the example itself became a card of its
own — a real-looking one, with a real date, no error on it. It also took the identifier that the
next real entry should have had. Those identifiers are how one entry says *"this answers the thing
you were asked about on Tuesday"*, so a stray example could point that answer at the wrong item, or
leave a question sitting in "what needs you" forever.

Nothing you have read was affected — no entry had ever used a fenced example until the one written
yesterday, which is how this was found. The fix teaches the page what a code block is, using the
rules the pull-request checker already knew.

Worth knowing, because it says something about how these fixes go wrong: the first version of this
fix looked correct, passed, and **deleted a real entry from the page**. Caught by counting the
entries before and after rather than by reading the code.
<!--tech-->
Backlog #84. Branch `fix-parser-fence-blindness`. Closes the third Blocking from PR #205's review
round 1, deferred there by agreement and filed with the user's approval.

**CONTROL, run before the fix and quoted rather than characterised:**

    backtick fence   entries=2 ids=['2026-08-28/1','2026-08-29/1'] errors=0 tail_kept=False
    tilde fence      entries=2 ids=['2026-08-28/1','2026-08-29/1'] errors=0 tail_kept=False
    indented         entries=1 ids=['2026-08-28/1']                errors=0 tail_kept=True

⚠ **Note `errors=0`.** The phantom is not a visible "could not parse" card — it is a fully VALID
entry holding a real id, rendering like any other. My backlog filing said otherwise, having only
seen the variant whose header carried trailing text. A regression case asserting only "no error"
would have passed ON THE BUG; the id list is what discriminates.

**⛔ THE FIRST CUT WAS WRONG IN THE OTHER DIRECTION, AND IT REACHED THE LIVE STORE.** `parse_entries`
was wired to the gate's `_inert_lines`, which was cheaper reuse and looked equivalent — a probe over
blockquote, indent and fence shapes showed the only newly-suppressed line was the fenced header.
**That probe had no HTML comment in it.** Run against the real store: **47 entries → 46. Entry
2026-09-01/16 VANISHED** — line 1924 of this file mentions `` `<!--` `` in prose while explaining
this machinery, `_inert_lines` treats an unclosed `<!--` as running to end-of-input, and everything
after it disappeared. Over-approximating fails SAFE for *"is there an ask here?"* and DANGEROUS for
*"does a block start here?"*. A measurement is only as good as its corpus.

**THE SEAM.** `fenced_lines()` EXTRACTED into `check-dashboard-entry.py` beside `FENCE`; the page
binds `_FENCED_LINES = _GATE.fenced_lines` as **required**, not `getattr`-optional — losing it does
not degrade, it silently mints phantom entries. Deliberately NOT a third hand-written scanner: this
file already carries two (`exemption_reason`, `_inert_lines`) which have drifted once before, per
the `startswith` note. Same shape as PR #205, one seam over.

⚠ **The harness refused the first mutation pair** — *"it measures nothing new"* — because both fence
rules sat in one `and`-chain sharing an anchor. Correct refusal, and it improved the design for the
second time today: the closing test is now two named decisions (`same_char`, `long_enough`), each
independently falsifiable.

**REVIEW ROUND 1 — NOT CONVERGED at dispatch: 1 High, 0 Blocking.**
`docs/reviews/whole-branch-parser-fence-blindness-review.md`.

⛔ **The Codex half found that the defect SURVIVED MY FIX, one shape over.** A closing fence may
carry only whitespace in CommonMark; mine accepted trailing text, so an annotated inner fence —
    ``` ``` not a CommonMark closing fence ``` — read as a closer, the lines after it stopped being
code, and a valid phantom entry appeared again. Reproduced before fixing: 2 entries, ids
`['2026-08-28/1','2026-08-29/1']`, errors `[None, None]`. That shape is not exotic — it is how
anyone quotes markdown inside markdown, which this project's own skill teaches. `exemption_reason`
had already paid for the sibling fence-LENGTH rule the same way; I ported two of its three rules
and missed the third. FIXED as `no_trailing_text`, its own decision, cases and mutation.

⚠ **SECOND TIME THIS BRANCH that my measurement was sound and my CORPUS was not** — first a probe
with no HTML comment (which deleted a live entry), then fence cases with no trailing text. Both
times the code did what I measured; both times I measured the wrong set.

⚠ **STATED, NOT HIDDEN:** three fence-aware implementations still exist. This branch takes the
duplication from "two copies, one about to become three" to "three copies, one canonical and
documented". An improvement, not a resolution. Unifying them needs a fence-token helper called
after `_inert_lines`' comment branch, and it touches two functions whose escapes were paid for in
production — deliberately not folded into a branch already carrying a High fix.

⚠ **REVIEW GAP: claude — author self-review, not an independent half** (session instructions).

Counts: `check-dashboard-entry --self-test` 112 → **123** + 13; `gen-dashboard` 301 → **307**;
`EXPECTED_MUTATIONS` 156 → **162** (gate 30 → 34, gen-dashboard 68 → 70). Six mutations: four pin
the extracted scanner's rules (wrong closing character, ignored LENGTH, dropped marker lines,
trailing text on a closer), two pin BOTH directions the parser can fail — under-rejecting
(fence-blind) and over-rejecting (the `_inert_lines` wiring that deleted a live entry).
`--mutate .`: 7 files, **162 mutations, 0 survivors**.

## 2026-09-01
Filed the leftover from yesterday's fence fix: three copies of one rule where there should be one.
The fence fix that just shipped left something behind, and it is now written down rather than
living in a merge note. The checker that reads pull-request bodies, the part that decides whether a
question is really being asked, and the new shared scanner all separately know what a code block
is. Only one of them is the shared one.

Nothing is broken by this today, and the part your page actually uses is the correct one. It is
filed because these copies have already disagreed twice — once silently, in a way that made a real
question invisible — and because the next person to touch any of them has no way to know the other
two exist unless it is recorded.

Worth knowing about how the last fix was described: the merge notes could be read as saying the
duplication was solved. It was not. It went from two copies to three, one of which is now the
official one. That is progress and it is not a fix, and the difference is the sort of thing that
quietly becomes untrue in a summary.
<!--tech-->
Backlog #85 🟡, filed with the user's agreement from the Codex half of PR #206's review round 1
(rated Medium there, accepted as debt rather than folded into a branch already carrying a High fix).
`exemption_reason` and `_inert_lines` hold hand-written copies; `fenced_lines` is the extracted
canonical one that `parse_entries` asks.

⚠ `_inert_lines`' docstring still claims *"⚠ ONE scanner, sharing `exemption_reason`'s discipline"*
— true about the RULES, false about the CODE. Same shape as the false comment PR #205 deleted, and
left in place deliberately rather than patched here, so the row and the code say the same thing.

⛔ **The obvious unification is wrong, and was measured wrong once already.** Precomputing
`fenced_lines` inside `_inert_lines` changes comment-vs-fence PRIORITY: today a ``` inside an HTML
comment does not open a fence, and precomputing would make it. Shape is Codex's — a fence-TOKEN
helper returning marker plus rest, called AFTER the comment branch.

⚠ A differential check is mandatory, not a green suite. Both of PR #206's wrong turns passed
everything until the corpus grew, so the corpus must carry all four dimensions that have each
already produced a defect: HTML comments, tildes, fence length, trailing text on a closer.

⛔ **AND WRITING THIS ENTRY IMMEDIATELY FOUND A LANDMINE I SHIPPED IN PR #206.** Line 2247 of this
store — inside entry 2026-09-01/17, the one describing the fence fix — began at column 0 with four
backticks. Under CommonMark that OPENS a fence with an info string, and nothing ever closed it, so
**every future entry would have been silently swallowed.** This entry was the first to exist after
it, and it vanished: 48 entries, last id 2026-09-01/17, mine absent.

The fix worked exactly as designed. I wrote the bug.

⚠ **THIRD INSTANCE OF ONE LESSON IN A DAY, and the sharpest.** Entry /17 verified clean when I
committed it — 48 entries, 0 errors — because the swallowed region was AFTER the last entry and
there was nothing yet to lose. A true measurement over a corpus that could not yet contain the
failure. The same shape as the probe with no HTML comment and the fence cases with no trailing
text.

⚠ **REPAIRED IN PLACE, and disclosed rather than done quietly.** The line is now indented, so it is
inert code rather than a fence opener. This edits an already-merged entry, which the store's
append-only rule forbids — the rule exists so that ids cannot be rebound, and this change touches
no header, so `/16` and `/17` keep their ids (verified: 49 entries, last `/18`, 0 errors). Appending
a correction could not have fixed it: the landmine would still be armed.

⚠ **WORTH A GUARD, NOT FILED:** nothing refuses an entry that leaves a fence open at end-of-store.
That is mechanically detectable and would have caught this at the gate. Left for the user's call —
filing is their step.

No code change on this branch. Backlog row + this entry; `master` is `f76eaa7e`.

## 2026-09-02
The backlog page had been silently missing its four newest items since yesterday afternoon — you found it by looking for one of them.
The page at `/backlog-table` is built from the backlog file rather than being the file, and it had
stopped rebuilding. Four items were filed after the last successful build and none of them appeared:
the two from yesterday evening and the two from this session.

Two things had to go wrong together, and both did.

The rebuild is supposed to happen automatically whenever the backlog file is written. It watches for
a particular *kind* of write, and the edits that added these items were made a different way, so it
never noticed them. Separately, the builder refuses to publish at all until every open item has a
plain-English description written for it — a deliberate rule, and the right one, because an item
that appears as a bare row nobody wrote a sentence for is not really on the page. But the refusal
was printed into a log at the moment it happened, and nobody was reading that log afterwards.

So the page did not break loudly. It just stopped moving, and looked exactly like a current page.
All four items are now described and the page is rebuilt.
<!--tech-->
Found by the user: *"I refreshed /backlog-table and tried to find backlog #85, but couldn't."*
`docs/backlog.md` had row 85 on master (`392e6175`) the whole time; `~/explainers/backlog-table.html`
was last written 2026-09-01 13:22.

**CAUSE 1 — the hook watches the TOOL, not the FILE.** `.claude/hooks/regen-backlog-page.sh` reads
`tool_input.file_path`, a field only present on Write/Edit tool calls. Rows #84 and #85 were added
by a `python3` heredoc inside a **Bash** call, so the path came back empty, the `case` fell through
to `exit 0`, and the hook did nothing. It is not that the hook failed — it never saw the edit.

**CAUSE 2 — the generator had been REFUSING since #82.**

    REFUSED: GROUPS does not cover the open set — open items missing from GROUPS: [82, 83, 84, 85]
    Nothing was written; the existing page is left as it was.

That refusal is correct and deliberate (the script's own header explains it, and the hook's header
even predicts it). It fails closed rather than publishing an ungrouped row. But its only audience
was a transcript line at the moment of the edit.

⚠ **The two compose into the failure that actually matters:** cause 1 meant the refusal was never
even reached for #84/#85, and for #82/#83 it was reached, printed, and scrolled past. The page's own
header comment describes exactly this — *"NOTHING on the page says the source has moved on since"* —
which is why the reader is the one who discovers it.

FIXED HERE: `GROUPS` in `scripts/gen-backlog-page.py` gains all four items. Page regenerated:
**85 rows, 59 open**, all four verified present by their own text (not by a row-number grep — the
first grep I wrote looked for an anchor format the page does not use and reported 0 for items that
were there).

⚠ **CORRECTION, same day, prompted by the user asking what the Refresh button does.** An earlier
draft of this entry said *"nothing makes staleness visible."* That is FALSE and I had not read the
button before writing it. `POST /regenerate` re-runs the generator, and a refusal comes back as
**500 NOT REBUILT** with the reason attached, which the button renders as *"could not rebuild:
… REFUSED: GROUPS does not cover the open set …"*. Pressing Refresh WOULD have shown this.

**What is actually missing is PASSIVE visibility.** A browser reload re-serves the stale file and
says nothing; you have to press the button to learn the page is behind. The reader has no reason to
press a button on a page that looks current — which is exactly how this went unnoticed for a day.

⚠ For the record on what the button does and does not do: it re-runs `gen-backlog-page.py`; it does
not and cannot update it. `GROUPS` is hand-written prose, one plain-English sentence per open item,
and there is nothing to derive it from.

⚠ **NOT FIXED, and it is the part that will recur:** the hook stays blind to non-tool edits, and a
refusal still only reaches whoever is watching that turn or thinks to press Refresh. Two shapes
worth considering — have the page state the source commit it was built from, or have a gate compare
them — but that is a design question, and filing is the user's step.

## 2026-09-02
The pages can now tell you when they are out of date, instead of sitting there looking current.
Three changes, all from you asking what the Refresh button actually does.

**The backlog page no longer refuses to build.** Until now, filing a new item and not writing it a
plain-English summary stopped the page being rebuilt at all — which is how four items went missing
for a day. Undescribed items now appear in a section that says plainly that nobody has described
them yet. The pressure to write the summary is still there; it just sits on the page where you can
see it, rather than in a log line nobody re-reads.

**A page whose server has died now says so.** Previously the page kept quietly retrying forever and
looked perfectly normal, so a dead server and a healthy one were indistinguishable. After three
failed checks in a row it says "server not responding — this page may be out of date". Three, not
one, because a single blip is not worth shouting about and a warning that cries wolf gets ignored.

**A page that has fallen behind its source now says that too.** The page already stamped which
version of the project it was built from, but nothing compared that to the current state. It does
now, and says "the backlog file has changed since this page was built — press Refresh".

Together those mean the answer to "is what I am reading current?" is on the page, rather than
something you have to know to check.
<!--tech-->
Branch `feat/page-staleness-visible`, off `d39fa658`. All three approved by the user after the
`/backlog-table` incident.

**1 — fail-visible.** `undescribed()` split out of `coverage_errors`; `build` appends a synthetic
final group; `main` re-calls the same pure function to print a `⚠` line, which
`explainer-serve._regenerate` already forwards to the Refresh button as *"rebuilt WITH A WARNING"*.
No new channel. ⚠ ONLY the missing half moved — `extra` and `dupes` still refuse, because missing
means the reader LOSES information while those two mean the page ASSERTS something false.

**2 — the empty catch speaks.** The injected poller counted nothing; now `misses`/`MISS_LIMIT=3`
writes into `#chrome-refresh-say`, the span the Refresh button already owns.

**3 — `/_stale?p=`.** A DIFFERENT question from `/_rev` ("has the output changed?") so it is a
different endpoint, not a fourth field. `PAGE_SOURCES` maps page → source; a self-test asserts its
keys equal `REGENERABLE`'s, because two maps of one thing drift. Fails QUIET on unknown/missing
sources — a false staleness banner would teach you to ignore the true ones.

⚠ **A defect in my own test, caught before it shipped:** the first draft defined `_stale_verdict`
INSIDE `self_test` — a second copy of `newest > built` that would have kept passing after the
handler changed. Extracted to a module-level `stale_verdict` both call. Writing that duplication
into the test of a duplication fix would have been remarkable.

⚠ **An existing case was REWRITTEN, not deleted:** *"coverage FAILS on an open item nobody
grouped"* asserted the behaviour being removed. It now asserts the split — `coverage_errors`
returns `[]`, `undescribed` returns the item — so the record shows the old contract existed and
the change was deliberate.

⛔ **THE THING I TRIED AND COULD NOT DO, stated because a silent omission here is the whole theme.**
Neither `explainer-serve.py` nor `gen-backlog-page.py` has ANY mutation coverage, and this slice
attempted to give them some. Manifests were written, then WITHDRAWN: `mutate_delivered` copies only
`scripts/` into its temp tree, while both suites read repo files outside it. Measured:
`FileNotFoundError: …/tmpw8okpx8z/docs/backlog.md`, 9 files mutated, **0 mutations run**. Shipping
a manifest whose suite cannot execute would report coverage that does not exist — the exact failure
the harness exists to prevent. Making them mutable means making their suites runnable outside a
checkout; that is its own piece of work and is NOT done here.

⚠ The harness also refused a redundant mutation for sharing an anchor — correct, and the second
time today that refusal improved the result. Kept the WEAKER edit (`>` → `>=`) that still fails via
the case it names.

Counts: `explainer-serve --self-test` 71 → **76**; `gen-backlog-page` 74 → **75**; `gen-dashboard`
307; `check-plan-code` 158; `EXPECTED_MUTATIONS` **162 unchanged** — deliberately, since the two
touched files could not join. `--mutate .`: 7 files, 162 mutations, 0 survivors.
Falsifier, driven against the live server: `/_stale` answered `fresh` → **`stale`** after touching
`docs/backlog.md` → `fresh` after a rebuild, and `fresh` for an unknown page (no false alarm).

## 2026-09-02 [needs-you]
PR #209 finally got the review it was missing, and the review was worth running: the new "this page
is out of date" warning was being wiped out most of the time by the other check running next to it.
So the feature built to stop a page looking current while stale was itself, intermittently, letting
a page look current while stale. Fixed and confirmed in a real browser. The page now also names the
file that actually changed, instead of telling everyone the backlog moved.

**Waiting on you:** PR #209 is ready to merge. I do not merge; that stays your call.

Also filed backlog #86 — the `/clean_gone` repair you asked about lives only in files a plugin
update will quietly orphan.
<!--tech-->
**Round 1, Codex half** — `docs/reviews/209-r1-codex.md`, model `gpt-5.5`, verdict
`docs/reviews/verdicts/209-r1-codex.verdict.json` (`gate_ran=true`). `gpt-5.6-sol`, `-terra` and
`-luna` each returned HTTP 400 from the pinned CLI; `scripts/codex-review.py` walked down to a
working model on its own. A raw `codex exec` would have died on the first one.

⛔ **REVIEW GAP: claude — not invoked** (session instruction forbids unasked subagents). One
reviewer, not two. Recorded in the review doc rather than papered over.

**High — the stale warning was erased by the liveness poll.** `check()` fires `poll()` and
`pollStale()` together at a `ThreadingHTTPServer`; `poll()`'s success ran `say('')`, an
unconditional clear of a status line it shared with `pollStale()`. Last promise to settle won.
Codex modelled the ordering; I ran it instead, in Chrome, source genuinely touched and `/_stale`
answering `stale` every time — the warning survived **2 of 6** trials. Fix: neither poll owns the
string, each owns its own state (`serverMsg`, `staleMsg`) and one `render()` composes them with
unreachable outranking stale. After: **6 of 6**. ⚠ The rate is measured; the *direction* of the
bias is NOT — latency sampling (15 pairs, ~1.2–1.6 ms both) does not support the obvious
"`/_stale` does more `stat()` work" story, and 6 trials cannot separate bias from chance.

**Medium — every page claimed the backlog had changed.** One hardcoded literal against a
`PAGE_SOURCES` map of three different sources, so `/dashboard` correctly detected staleness and
then pointed at a file that had not moved. Fixed server-side: `/_stale` now answers
`stale <repo-relative path>` and the client renders that path. The client already matched with
`indexOf(...) === 0`, so the suffix needed no protocol change — and `PAGE_SOURCES` stays the single
source of truth rather than growing a second slug→label map on the client. Verified live:
`backlog-table → stale docs/backlog.md`, `dashboard → stale docs/dashboard-entries.md`,
`goals → fresh`, unknown page → `fresh`.

**Low — a case that could not fail for the feature it named.** `"reload client asks /_rev, the only
endpoint added"` stayed green if the entire `/_stale` poll were deleted, and its name had been
false since `/_stale` shipped. Renamed and joined by three cases, one asserting the *property*
(nothing blanks the whole line) rather than the tokens this fix introduced.

⚠ **That new case went red on my own comments, which is the right failure.** Written as a plain
substring test it matched the prose quoting the old call while explaining its removal — a check
about code answered by prose. Now strips `//` comments via `_js_code_only`, whose one precondition
(no `//` inside a string literal) is itself asserted rather than assumed.

**Change 1 independently confirmed, against the real store, by accident of timing.** Filing backlog
#86 left a genuinely undescribed open item; varying only the code: `master` → `REFUSED … [86]`,
exit 1, nothing written, page left stale. This branch → `wrote (86 rows, 60 open)`, exit 0, plus
`⚠ 1 open item(s) have no description in GROUPS: [86]`. Real condition, not a fixture. The control
needed a `master` worktree — a scratchpad copy died on `ModuleNotFoundError: page_chrome`, then
`FileNotFoundError: …/scripts/check-docs.py`, which is a **second independent measurement of why
those two suites cannot join the mutation harness**: neither script is runnable outside a checkout.
`EXPECTED_MUTATIONS` stays **162**, still deliberately.

Counts: `explainer-serve --self-test` 76 → **80** (declaration updated; `check-selftest-counts.py`
caught the drift on the first run). Gates green: `check-docs`, `check-review-rounds` (131 rounds,
0 silent gaps), `check-selftest-counts`, `check-ratchet-contract`, `check-dashboard-entry`,
`check-plan-code --self-test` 158/158.

## 2026-09-02
A second review round on PR #209 came back clean apart from one thing, and the one thing was a
check I had written an hour earlier that could not actually catch what it claimed to. Fixed, with
a control showing the old version passing the exact case it was supposed to fail on.

PR #209 is still ready and still waiting on you; nothing here changes that.
<!--tech-->
Round 2 was **scoped at round 1's own fixes**, not the original change, because this project keeps
measuring that the next round's findings are regressions from the previous round's fix.
`docs/reviews/209-r2-codex.md`, model `gpt-5.5`, verdict `gate_ran=true`. **CONVERGED — no
Blocking, no High, one Low.** `REVIEW GAP: claude` again, recorded not hidden.

**The Low, and it is the interesting one.** Round 1 added `_js_code_only` (strip `//` comments) so
a check about CODE could not be satisfied by PROSE, and guarded its unsound assumption with
`"://" not in RELOAD_JS`. Codex produced a counterexample and executed it:

`var path = '//local'; say('')` contains no `://`, so the guard stayed green — while
`_js_code_only` truncated the line to `var path = '`, deleting a `say('')` that had just
reintroduced the round-1 High. ⛔ **Same defect class as the finding it was written to prevent:** a
check answering a narrower question than it claims. `://` was one instance; the class is "a `//`
the helper thinks is a comment and is not".

Replaced with `_js_strip_is_sound` — quote parity before the first `//`, i.e. the helper's actual
question. Control run, all five as expected: the counterexample, its double-quoted variant, and the
URL case the old guard *did* catch all report unsound (nothing lost); an ordinary trailing comment
and a comment-free line report sound. And the old guard on the counterexample returns **True** —
the hole, executed rather than asserted. The new predicate also has its own falsifier case, since
one with no negative case can return a constant unnoticed.

⚠ Residual written into the docstring: it does not model escaped quotes or template literals.
`RELOAD_JS` has neither. If it grows them, **replace the helper, do not widen it**.

**Found while probing, NOT filed and NOT this branch's.** `GET /_stale?p=%00` closes the connection
with no response (`curl` 52, `RemoteDisconnected`). Checked before claiming: `/_rev?p=%00`, `/%00`
and `/dashboard%00` do the same, and `/_rev` predates #209 — pre-existing and server-wide. Every
other hostile input failed closed to `fresh`, which is the safe direction. Filing is yours.

Counts: `explainer-serve --self-test` 80 → **81**. Gates green: check-docs, check-review-rounds
(132 rounds, 0 silent gaps, 4 verdicts read), check-selftest-counts, check-ratchet-contract.

## 2026-09-02
The branch-cleanup command's repair now lives in this repository instead of in files a plugin
update would quietly stop reading. Left alone, it would eventually have gone back to announcing
"no cleanup was needed" on a repository full of dead branches — and that reads as success, which
is the kind of wrong answer nobody goes back and checks.

Filed as backlog #86 and fixed in the same change, because the fix is one file.
<!--tech-->
**The trap, measured, and it is worse than "a vendored edit gets reverted".**
`~/.claude/plugins/marketplaces/claude-plugins-official` **is** a real git checkout (`origin` =
`kujinlee/claude-config`), so `git status` inside it runs and looks authoritative — but
`.gitignore` line 3 is a bare `*`. `git check-ignore -v` on the command file returns
`.gitignore:3:*`, and `git status --untracked-files=all` over that subtree is **empty**: the file
cannot even surface as a `??`. Asking "is my fix committed?" the obvious way returns a clean tree
that means nothing at all.

⚠ **"A `/plugin update` reverts it" was imprecise.** `installed_plugins.json` records a
`gitCommitSha` and the cache path's version segment IS that SHA, so an update installs a **new**
SHA-keyed directory and stops reading the old one. The edit is not overwritten — it is orphaned.
Nothing changes and nothing warns, which is quieter than a clobber and harder to notice.

**What was at risk** — four repairs, each bought by a measured failure: `git fetch --prune` as
step 1 (fixture recorded inline: before 0 `[gone]`, after 2); `git branch -v` printing the literal
`[gone]` where `-vv` prints `[origin/<branch>: gone]` and the grep silently matches nothing
(git 2.49.0); the skip for the branch you are standing on (the loop otherwise dies on *"cannot
delete branch used by worktree"*); and echoing each SHA before `git branch -D` so a force-delete
leaves a reflog handle.

**Shipped:** `.claude/commands/clean_gone.md` (repo-tracked, `disable-model-invocation: true`,
`allowed-tools: Bash(git *)`), plus a section in `docs/plugins.md` beside the existing
`mattpocock:handoff` three-layer table — this is the second instance of that same layer-3 class,
so it belongs next to the first rather than in a new place.

⚠ **NOT confirmed, and it decides whether one layer suffices:** a repo command appears to invoke
as `/clean_gone` while the plugin's is `/commit-commands:clean_gone`, so the two **coexist** rather
than one shadowing the other — anyone typing the plugin's name after an update still gets the
unrepaired version. Falsifier written into both the backlog row and `docs/plugins.md`: run
`/plugin update`, invoke the plugin's name, check whether step 1 is `git fetch --prune`. Not run
here because it mutates the local plugin install, which is not mine to do unattended.

⚠ **A `GROUPS` line was written for #86 rather than leaning on PR #209's new tolerance.** This
branch is based on `master`, whose `gen-backlog-page.py` still REFUSES on an undescribed item —
measured: `REFUSED: GROUPS does not cover the open set … [86]`, exit 1, nothing written. #209's
change is a safety net for a forgotten description, not a licence never to write one. With the
prose in place the page builds on both generators: `86 rows, 60 open`, exit 0, no warning.

⚠ **Expect a conflict in this file.** This branch and `feat/page-staleness-visible` both append to
`docs/dashboard-entries.md` from a common base, which this project has measured before: same-day
parallel branches conflict on the append. Whichever merges second needs a rebase. The two entries
reference no ids of each other, so positional renumbering is harmless.

## 2026-09-02
Backlog #85 was filed as tidy-up — three copies of one rule, "nothing is broken today". It was
broken. One of the three copies is the check that decides whether a branch is allowed to skip
writing you a dashboard entry, and a declaration hidden inside a code block was getting through it.
Fixed, with the before-and-after measured across 420 cases rather than argued.

The row has been re-rated from 🟡 to 🟠 to match what was actually found.
<!--tech-->
**What was wrong.** PR #206 added the CommonMark rule that a *closing* fence carries no trailing
text — to `fenced_lines` and nowhere else. `_inert_lines` and `exemption_reason` kept hand-written
subsets. MEASURED 2026-09-02:

    exemption_reason("```\n``` x\nNO-ENTRY: r\n```\n")  ->  'r'

A `NO-ENTRY:` that GitHub renders as grey code **inside a code block** exempted the branch from the
dashboard-entry gate. That is the same escape the LENGTH rule was added to stop, one rule over —
the class question was never asked when #206 fixed the instance. Across a 420-case corpus spanning
the four dimensions the row itself names (HTML comments, tildes, fence length, trailing text), the
two line scanners disagreed on **8** bare inputs.

⚠ **The row's own reasoning is the more useful lesson.** It rated 🟡 because *"`fenced_lines` is
the one the page uses, so the reader-facing path is correct"* — true, and beside the point. The
consumer that mattered was the GATE, not the page.

**The fix.** One `fence_closes(run, rest, open_run)` holding the three rules as **three separately
anchored statements** — not an `and`-chain, because one line cannot show that three rules are each
load-bearing. All three consumers call it; each keeps its own comment-vs-fence priority, which is
exactly why the obvious unification (precomputing `fenced_lines` inside `_inert_lines`) was refused.

**Differential, 420 cases, old vs new:** scanner disagreements **8 → 0**; exemptions **revoked 4**
(precisely the trailing-text bypasses, backtick and tilde, bare and after-comment); exemptions
**newly granted 0** — no new hole. The 10 surviving exemptions are correct: `` ``` `` closed by
`` ``` ``, `` ```` `` or `` ````` `` are all valid closers.

**The new tests were controlled against master before being trusted.** Two go False → True (real
regression guards); one control stays True → True (the fix broke nothing). Worth noting the suite
was **123/123 green over the live defect** — no case had ever compared the consumers to each other,
which is how the drift survived.

⚠ **A guard that turned out to be weaker than it looks, recorded rather than quietly kept.** The
new "the two scanners agree" case matched **0 red cases** under the trailing-text mutation, and the
harness said so. Of course: both now call `fence_closes`, so a wrong shared rule breaks them
identically and they still agree. It guards against RE-FORKING the rule, not against the rule being
wrong. That limit is now written into the case and into the manifest note.

**Mutations: 162, 0 survivors, count HELD.** Five anchors were retargeted onto the extracted rule
rather than orphaned — anchoring is by text, so a refactor silently unhooks its own guards, which
this repo has recorded twice. Two of the five became better guards than they replaced: one on the
gate's CALL to the shared rule, one on the COMPOSITION (that the three rules are ANDed).

Gates: check-docs, check-review-rounds, check-selftest-counts, check-ratchet-contract,
check-dashboard-entry all green; `check-dashboard-entry --self-test` 123 → **127**.

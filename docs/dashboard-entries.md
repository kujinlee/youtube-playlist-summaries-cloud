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

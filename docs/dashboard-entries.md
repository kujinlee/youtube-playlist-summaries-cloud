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

## 2026-09-02 [resolved: 2026-09-02/3]
All three pull requests merged, so nothing is waiting on you any more — that item is closed here.

Then I audited the backlog for rows that were already fixed but still marked open, and found two.
The honest part: I found them because you asked me to look, not because anything in the repo could
have told you. A finished piece of work can sit on the list as outstanding indefinitely and no
check notices.

Open items: **60 → 59**. High-severity: **20 → 18**.
<!--tech-->
**Merged:** #209 → `e18cc83f`, #210 → `b3d44f09`, #211 → `7a99fb2e`. Branch protection now requires
the `verify` check on `master`, with `enforce_admins` on. Proven rather than assumed: a throwaway PR
showed `mergeStateStatus=BLOCKED` with `verify:QUEUED`, and a merge attempt was refused with *"the
base branch policy prohibits the merge"*. PR closed, branch deleted.

**Re-tagged CLOSED, with evidence:**

- **#71** — `scripts/page_markup.py` shipped in PR #180 (`0972c55e`, *"One renderer for four pages"*),
  and grepping every generator for a private inline renderer returns nothing; all four delegate.
  Tasks T1–T4 all closed. The row had said OPEN for **three days** after the fix landed.
- **#84** — the parser half shipped in PR #206 (`parse_entries` asks `fenced_lines`, 3 call sites)
  and the CLASS closed today in PR #211. Its own GROUPS prose already said *"Fixed and merged; the
  row stays for the record"* — the prose knew, the row did not.

⚠ **Also corrected: #68 was never open.** Its status cell leads `✅ CLOSED 2026-09-01`. My first
audit script counted it as open because it substring-matched the word "OPEN" inside 400 characters
of prose — the same wrong-population mistake this project keeps recording, this time in my own
instrument. Two further hand-rolled counts also disagreed (32, then 62) before I stopped guessing
and called `gen-backlog-page.parse()`, whose answer cross-checks against the page footer exactly.
**The only trustworthy count came from the consumer that already computes it.**

⚠ **And the repo caught me twice more, which is the encouraging part.** `gen-backlog-page.py`
refused to build because `GROUPS` still described two now-closed items — the coverage check is
bidirectional, not just "every open item is described". Then `check-docs.py` refused because both
rows still LED with 🟠 while their status said `✅`, and it named the reason: *"a severity scan will
count it as open"*. That is exactly the bug my audit script had. The convention already knew.

**Filed: #87** 🟢 — a NUL byte in any query makes the explainer server close the connection with no
response (`curl` 52, `RemoteDisconnected`). Checked before blaming the new endpoint: `/_rev?p=%00`,
`/%00` and `/dashboard%00` do the same and `/_rev` predates #209, so it is pre-existing and
server-wide. Every other hostile input in that sweep failed CLOSED to `fresh`, the safe direction.
🟢 because it binds 127.0.0.1 only, fails closed, the server survives, and nobody types a NUL byte
into a URL.

⚠ **NOT decided, left for you:** **#41** (M3.1-B prod read-only smoke) says *"NO LONGER GATES M3"*
and its task is marked completed, but the row keeps itself open for the smoke test itself. That is
a judgement call about scope, not a stale tag, so I have not touched it.

**What the tooling lane actually contains, after the audit:** **#67** (concurrent-agent
interference — the rule is in the wrong place and names deleted scripts), **#72** (the guard
inventory cannot see a guard that is not NAMED like one), and **#78 half (2)** (the entry gate runs
on `pull_request` while the skill regenerates the page immediately). Three items, not the five it
looked like this morning.

## 2026-09-03 [needs-you]
Ran the architecture review that was convened yesterday and never written. The question it was
convened to answer — *why has this plan failed four review rounds in a row?* — has an answer, and it
is not "the plan is badly written".

The repo keeps **four separate hand-maintained lists of its own safety checks**, and no two of them
agree. There are 26 checks on disk. Nine are pinned for one kind of coverage, seven for another,
twenty are named in CI — and **eighteen of the twenty-six have neither kind of coverage at all**.
Nothing in the codebase compares these lists to each other. The only place they are reconciled is
the plan document, and a document cannot enforce anything. So every review round finds a
reconciliation error, the fix introduces the next one, and the count grows without the *kind* of
problem ever changing.

**The decision waiting on you: which fix becomes the next piece of work.** My recommendation is the
narrow one — make one of those four lists derive itself from the directory it is currently copying
by hand. It is small, it is measured, and it removes the exact defect the last four rounds kept
producing rather than patching this instance of it.

Also worth knowing: the previous architecture review's four findings are all **verified closed**.
The ratchet built for them worked.

<!--tech-->
`docs/reviews/architecture-review-2026-09-03.md` — Phase 6, second arming condition, on the branch
`fix/guard-inventory-population` (unpushed, no PR, zero lines of `scripts/` changed).

Inventories measured **by importing the owning module**, never by string-splitting — an earlier
string reader returned `0` for two of the four, and a zero is indistinguishable from a broken
reader. `check-ratchet-contract` population **26**; `check-selftest-counts.POPULATION` **9** (6 are
guards); `scripts/mutations/` + `EXPECTED_MUTATIONS` **7**, sum **162** (4 are guards); distinct
`scripts/*.py` in `ci.yml` **20** (17 are guards). Reachability is fine — **0 of 26** guards are
unrun (17 via CI, 8 via `check-schema-gates.sh`, 3 via a hook).

Findings: **A** 🟠 four inventories, nothing reconciles them. **B** 🟠 `check-plan-code.py:625-626`
returns on count drift five lines before the `copytree` at `:630`, so the run aborts having measured
nothing while emitting `0 mutation(s), 0 survivor(s)` from the empty initializer at `:584` — not
fail-open (exit is non-zero), but a true-looking coverage claim on a path where nothing ran.
**C** 🟡 `EXPECTED_MUTATIONS`' key set is a verified duplicate of `scripts/mutations/*.json`; the
per-file counts (`:426-431`) and the sum literal `162` (`:1956`) are deliberate and must survive any
fix. **D** 🟡 backlog #48 records "STOP-HOOK VERDICT: NOT BUILT, deliberately" — it was built
2026-08-24 (`8b9643d9`) on a better discriminator. **E** 🟢 `block-idle-stop.sh:5` says 18 self-test
cases; the script reports 17, and nothing catches it.

Review #4's A/B/C/D re-verified **CLOSED**. Findings deliberately **unfiled** pending your triage,
per review #4's precedent. `.claude/plan-gate-pending` remains **ARMED**. Gates green:
`check-arch-findings`, `check-anchors`, `check-docs`, `check-roadmap-consistency`.

## 2026-09-03
You picked the narrow fix I recommended, and it was wrong. I tested its premise before writing a
spec, and the test refuted it.

The recommendation was to stop one of the four lists copying a directory by hand and let it derive
itself. I had checked that the two always match. What I had not checked is **why** they always
match — and it turns out the hand-maintained copy is the only thing that notices when a file is
**deleted**. Derive it, and a deleted safety check would vanish from both sides at once and nobody
would be told. I would have removed a working guard from the one stack whose entire job is that
coverage cannot shrink quietly.

**What replaces it is smaller and still worth doing.** When those two lists disagree, the tool stops
before it measures anything — correctly — but still prints *"0 mutations, 0 survivors"* in the same
breath. That line reads like a clean result. It should not be printed at all on a run that never
started.

Worth saying plainly: **this review recommended a fix built on a premise it had only read, not run —
which is the exact failure it was convened to diagnose.** Catching it cost one command. It is
recorded in the review rather than quietly swapped out.

<!--tech-->
Finding C **REFUTED BY EXECUTION**; candidate 2 **WITHDRAWN**; candidate 2′ replaces it.

Tested on a temp copy of `scripts/` via `mutate_delivered(root)`, never the repo. Deleting
`scripts/mutations/page_chrome.json` yields `scripts/page_chrome.py: manifest holds 0 mutation(s),
expected 11` — caught **only** because `EXPECTED_MUTATIONS` still names the file (`:592` is
`got = counts.get(target, 0)`). The key set is the **deletion detector**: the ratchet reasoning
already written for the counts at `:426-431`, applied to *existence* rather than *cardinality*, and
never written down. `:598-600` catches an **undeclared** file; `:591-597` catches a **deleted** one —
two directions, two mechanisms, and I proposed deleting one of them.

How the error survived the review: I quoted `:598-600` as proof the lists are forced identical (true)
and read that as "the second list carries no information" (false). Same shape as the project's own
recorded lesson that *a shim can fail in BOTH directions*, met from the other side.

**Candidate 2′** — `mutate_delivered` returns at `:625-626` five lines before the `copytree` at
`:630`, with `ev` still its `:584` initializer, so the caller renders a tally from an empty
structure. Confirmed by execution twice (manifest deleted; manifest undeclared), both
`mutations_run=0, survivors=0`. Falsifier: add a manifest entry, leave `EXPECTED_MUTATIONS` alone,
run the gate — drift message, **no** tally.

⚠ The claim that candidate 2 "dissolves round 4's Blocking" is **withdrawn with the candidate**.
That Blocking is a plan defect (T4 vs T7) and still needs the count decided in one place: six
entries, `EXPECTED_MUTATIONS` 6, sum **168**.

## 2026-09-03
The spec went through its review gate and came back **not converged** — both reviewers, independently,
found the same fault, and it was in the fix I had recommended.

The fix was meant to stop the tool printing a clean-looking summary on runs where it measured nothing.
My version keyed off the wrong moment: it would have marked a run as "measured" slightly too early, so
the single worst case — where the tool's own safety check fails before any real work starts — would
still have printed **"7 files, 0 survivors"**, which reads like a clean sweep, on a run that says of
itself *treat this as not checked*.

The outside reviewer also caught something neither I nor my own review saw: the spec quoted a running
total that **another in-flight document also quotes**, and whichever lands first changes the other's
number. The fix is to stop quoting the total in either place and let each derive it when it lands.

Nothing is built yet, and that is the point: the gate cost about twenty minutes and caught a fix that
would not have fixed the thing it was for.

<!--tech-->
Spec **v2**; round 1 filed, BOTH halves, `check-review-rounds` green.

**Blocking, found by both halves independently.** v1's R1 was scoped *"returns without reaching the
`copytree` at `:630`"* and option (a) flipped its sentinel there. `mutate_delivered` has **four**
returns (`ast`-enumerated): `:586`, `:626` before, **`:646`, `:663` after**. `:646` is the
control-failure return — `ev["files"]` populated at `:639`, `mutations`/`survivors` set only at
`:648` — so the flag would be `True` and the tally would print. Reproduced by forcing a target's
control suite to exit 1: `FAILED — delivered scripts mutated: 7 file(s), 0 mutation(s), 0
survivor(s)`. **v2 restates R1 as "were mutations RUN", moves the flip to `:648`, and adds R1a: the
file count is part of the claim.**

**Codex-only findings.** ① The `168` in §7 is unstable — this spec moves the sum 162→163, so the
sibling plan's total is 168 *or* 169 depending on order; v2 states the dependency and drops the
number, keeping only the per-file `6`. ② F2/F4 were vacuous — F4 named no anchor, no target, no case;
v2 writes the manifest entry out and warns that `:723` parses only `[FAIL] ` lines, so an unmatched
case name reports zero red cases rather than a mismatch. ③ Call sites are **8**, not 9.

**Confirmed by both:** the 🟠→🟡 downgrade (no early return yields exit 0 or `OK`), and option (c)'s
refutation (`ok=False` also at `:773`/`:779`). Codex ran F3: `OK — … 7 file(s), 162 mutation(s), 0
survivor(s)`, exit 0.

⚠ **The wrapper's "THE AGENT WROTE BEHIND THE WRAPPER" warning was a FALSE POSITIVE** — it names
files the *coordinator* wrote while the two halves ran in parallel. Verified by `git status` and by
the Claude half still holding its own text. A cry-wolf risk on the detector that exists to catch a
real overwrite; noted in the Codex review doc, not filed.

## 2026-09-03
**The first code of this branch — 28 commits in.** Everything before today was a spec, a plan, an
architecture review and twenty-one review documents. This is the first change to a script.

The tool that mutation-tests this repo's own guards could print a clean-looking summary on runs where
it measured nothing. The worst version wasn't a row of zeros — it was **"161 of 162 mutations, 0
survivors"**, which reads as coverage confirmed while one declared check silently never ran.

Three attempts at this failed, each caught by both reviewers, because each keyed on *where the code
stopped* rather than *whether the number could be trusted*. The fix stops asking about position and
asks arithmetic instead: **did every declared check actually run, and were the before-and-after
sanity runs both clean?** A skipped check now shows up as a count shortfall no matter where it
happened — including in two skip paths nobody had enumerated.

**It caught its own author on the very first run.** Editing the code moved a line that one of the
existing checks was anchored to, so that check silently stopped applying. The old tool would have
printed 161-of-162 and looked like an ordinary failure; the new one refused to give a verdict and
said exactly how many were missing. Then the replacement anchor turned out to match *two* places in
the file — caught before it shipped by checking, not by reading.

Six situations were built and run, one per way the tool can fail. All six behave. A clean run's
output is unchanged, byte for byte.

<!--tech-->
`scripts/check-plan-code.py` — first `scripts/` change on `fix/guard-inventory-population`.

`ev["trustworthy"]` defaults **False** and is earned, never assumed: set at `:648` to
`len(m_muts) == len(muts)`, cleared at the after-control. The `--mutate` printer emits **no tally at
all** when it is False — including the **file count**, which on a control-failure run reports the
*control* runs and asserts work that measured nothing.

**Why arithmetic, not position.** `run_mutations` skips without appending at three places — unknown
target file `:685`, anchor not found `:711`, empty `expect` `:763`. Only the middle one had been
enumerated; the count comparison covers all three and any fourth added later. Three prior attempts
keyed on `copytree`, on `run_mutations` returning, and on which return was taken; each was true while
the property was false.

**Six falsifiers, all executed.** S0 dup anchors `:586`, S1 count drift `:626`, S2 control red before
`:646`, S3 clean, S4 after-control red `:663`, S5 mutation skipped `:663`. S0/S1/S2/S4/S5 →
`NOT MEASURED … Treat this as NOT CHECKED`, exit 1. S3 → `OK — delivered scripts mutated: 7 file(s),
163 mutation(s), 0 survivor(s)`, exit 0.

**S4 was wrong on first run and the falsifier found it:** the message read *"produced no coverage
verdict (162 of 162 declared mutation(s) produced a verdict)"*. The parenthetical now appears only
when a shortfall is actually the reason.

Two named cases added (**160/160**), one mutation added (**163/0**), `EXPECTED_MUTATIONS`
`check-plan-code.py` 21→22 and the deliberate sum literal 162→163, docstring 158→160 — that last one
caught by `count_drift`. Nine gates green.

## 2026-09-03
You asked whether the code had been dual-reviewed. It had not — three rounds had reviewed the
*document*, and the code had zero. Running that review found a real fault in the fix.

The change stops the tool reporting coverage it didn't measure. **It had the same fault inside it.**
When a check *times out*, the tool records it as a result rather than as a non-result — so a
two-minute hang was being counted as "one check ran, one survivor found", and the new safeguard let
it through because the arithmetic balanced.

I had reviewed my own code and called it clean. The outside reviewer found this in one pass, and it
had already been found once before at the same line — there is a comment there saying so, which my
review walked straight past.

**What that says about the process:** an author reviewing their own work is the weakest check
available. The parts of my review that survived were the ones stated as claims someone could
contradict; the part that failed was a characterisation nobody could test.

Fixed, and the fix now has its own test and its own deliberate-sabotage check.

<!--tech-->
**Codex Blocking, reproduced and confirmed:** `check-plan-code.py:751-757` — `rc == 2` is
`run_suite`'s CANNOT RUN. It appends to **both** `ev_muts` and `ev_survivors`, so
`len(m_muts) == len(muts)` balanced, `trustworthy` stayed True, and the printer emitted
`FAILED — … 1 mutation(s), 1 survivor(s)` over a timeout.

**Why the Claude half missed it:** it enumerated the append sites with `ast` **for cardinality**
(correct, and that claim still stands) and then asserted what the appends **MEAN** without reading
the branch above one of them. The comment at `:746-750` records the identical defect being found in
round 5 and the review walked past it.

**Fix:** entries carry `"measured"` — False on the cannot-run append, True on the normal one:
```python
ev["trustworthy"] = (len(m_muts) == len(muts)
                     and all(m.get("measured") is True for m in m_muts))
```
`.get("measured") is True` **fails closed**: a future append site that forgets the key yields `None`,
so the run is untrusted. Chosen over `m["measured"]` (crashes the harness) and `.get(..., True)`
(defaults to trusted — the shape being fixed).

**Verified against the reviewer's own scenario**, rebuilt and run in-process with `run_suite` stubbed
to time out the mutated run only: `NOT MEASURED … Treat this as NOT CHECKED.`, exit 1.

Two cases added (**162/162**), one mutation added (**164 mutations, 0 survivors**),
`EXPECTED_MUTATIONS` 22→23, sum 163→164, docstring 160→162 — the last caught by `count_drift`, its
third catch today. Six gates green. Round 1 of the CODE review filed, both halves;
**NOT CONVERGED → folded → round 2 owed.**

## 2026-09-03
Second review of the code, and the outside reviewer was right about something I had rated as minor.

We had both spotted the same thing — the tool has a *second* place that reports results, and it
hadn't been fixed. I called it minor because I reasoned about it from the code. The outside reviewer
**ran** it, and found it was worse than a wrong count: the detailed report was printing a check that
timed out as **"SURVIVED"** — i.e. claiming the safeguard had been exercised and lost, when it had
never run at all.

**The lesson is about severity, not about the bug.** A severity assigned to something you haven't run
is a guess with a number on it. I had even written "not checked" next to it.

Fixed by making both reporters share one rule instead of two copies. And the harness caught me
mid-fix: copying the rule made a sabotage-check ambiguous and the whole run refused to give a verdict
— which is precisely the behaviour this change added.

<!--tech-->
**Codex Blocking (r2), reproduced.** `check()` — the second producer of the evidence dict — had no
`trustworthy` concept, so `main([plan])` printed `1 file(s), 1 mutation(s), 1 survivor(s)` and
`--evidence` printed `SURVIVED timeout mutation`. Pre-existing (`da5cd27e`, PR #176), out of CI, but
the same class the change exists to remove.

**Claude half rated it Low and had explicitly labelled the end-to-end run NOT CHECKED.** The gap was
`evidence()` — a different function from the printer I reasoned about — rendering `SURVIVED`.

**Fix:** `check()` gains the same default-deny flag; `evidence()` renders `NOT RUN` for
`measured is not True`; the plan-mode printer gates identically, with `declared is None` as the
escape for assemble/compare-only runs.

⚠ **The fix's duplication was caught by the harness.** Copying the predicate made a mutation anchor
match twice → `anchor matches 2 times … Tighten it`, **164 of 165**, exit 1. Correct fix was removing
the duplicate, not tightening the anchor: `verdicts_are_trustworthy(m_muts, declared)`, one function
two callers — `check-vocabulary-collisions.py`'s subject exactly.

After: `--self-test` **164/164**; `--mutate .` **165 mutations, 0 survivors, exit 0**; both Codex
observations reversed. Seven gates green. **Round 2 filed both halves, NOT CONVERGED, folded.
Round 3 owed.**

## 2026-09-03
The tool that checks whether our safety-net tests actually work had been quietly reporting
"everything passed" in situations where it had measured nothing at all. Three separate versions of
that report were wrong in three different ways, and the third round of review found the most
serious one: if the test suite was **already failing before any check began**, the tool would still
announce that every check had passed. A change that altered nothing but a comment could be recorded
as "caught".

The deeper problem was subtler and worth saying plainly. The previous round had pulled the shared
rule out into a single function so two places could not disagree — a good instinct. But the rule has
three parts, and the extracted function could only see two of them. **A shared function that holds
part of a rule is more dangerous than two copies, because it looks like the whole rule.** The part it
dropped was the one that stops a broken environment being mistaken for a working test.

Separately: the fix from the previous round could be deleted four different ways without any test
noticing. It has now been given the missing tests, so a future edit that quietly removes it turns the
build red instead of passing.

One of the two automated reviewers read all of this and reported "no defects found". Everything it
checked was true; it checked the parts that had already been fixed and not the part that had been
changed. That disagreement is recorded in the review file rather than smoothed over, because a clean
verdict from one reviewer has been wrong here before.
<!--tech-->
Code review r3 of the mutation-drift-report contract, both halves, folded.
`scripts/check-plan-code.py` + `scripts/mutations/check-plan-code.json`.

- **B1 (Blocking)** — `check()` asserted `trustworthy: True` over a RED control.
  `verdicts_are_trustworthy` now takes `controls_green` and holds all three clauses; both producers
  compute it once, after both controls.
- **B2 (Blocking)** — the r2 fix had NO falsifier: four inversions each left `--self-test` at
  164/164. Closed with 8 mutations + 13 cases.
- **B4 (High)** — `evidence()` read neither `declared` nor `trustworthy`; its header asserted
  "declared and run" over `NOT RUN` entries and over the after-control path. Now gated, and the
  refusal sentence is ONE renderer (`not_measured_line`) with THREE callers — the third copy was
  refused by the mutation pre-flight, which caught the duplicate anchor.
- **B5 (High)** — the cardinality conjunct had no red case. **B6 (Low)** — the docstring credited
  `is True` with fail-closed-on-missing-key; `.get()` already does that. Corrected + cased.
- **TWO mutations were orphaned by this round's own refactor** and the pre-flight refused to write
  the manifest until both were retargeted. Third occurrence of anchors-bind-by-text.
- Counts: self-test 164 → **177**; this file's mutations 24 → **32**; `EXPECTED_MUTATIONS` sum
  165 → **173**. `count_drift` caught the docstring for the fifth time this slice.

⚠ The Codex half returned **CONVERGED** over 2 Blocking + 2 High. Adjudication is written into
`docs/reviews/code-mutation-drift-report-contract-r3-codex.md`.

⚠ This run also **overwrote a committed verdict file** — `--out` was named `r3-codex.md` and the
wrapper derives the verdict path from that stem, colliding with the *spec* round-3 verdict. Restored
from `HEAD`; re-saved as `codex-code-r3.verdict.json`. Backlog #68 closed the wrapper's path
inference but not the collision channel: verdict names are a namespace with no allocator.

## 2026-09-03
A fourth review round on the same piece of tooling found that the previous round's fix had been
applied to the wrong copy of the thing it was fixing.

The tool has two places that print a result. The previous round's whole finding was "this fix has
no test that would catch it being deleted" — and it then wrote that test for one of the two
printers. It picked the one our automated build **never runs**, and left the one the build actually
depends on with no test at all. Deleting that safety check left every test passing.

That is the seventh round running where the new defect was inside the previous round's fix. The
shape has been consistent enough to name: a correct fix gets applied to the instance in front of us
and not to its sibling, and the sibling is often the one that matters more.

Two smaller things in the same family. The report that gets pasted into documents — and therefore
outlives the console output — was still printing "caught" next to each check, directly underneath
its own line saying nothing had been measured. And the phrase "a working test run" quietly meant two
different things in the two halves of the tool, one round after those halves were unified
specifically to stop that.

Four more of the tool's own safety checks were unhooked by this round's edits, and refused to be
written until they were re-pointed. That is the fourth time; it is now a known property of how this
code is guarded rather than a surprise.
<!--tech-->
Code review r4, both halves, on `review/drift-report-r4` off `87ea0001` (PR #214, merged).
All four findings reproduced by the coordinator before folding.

- **B1 🔴** — `--mutate`'s `if ev["trustworthy"]:` had zero mutations naming it; plan mode's gate
  had one. `ci.yml` runs `--mutate .` and never plan mode. Gate hardcoded open → 177/177 green.
  Closed with a mutation + a case driving `main(["--mutate", …])` on a freshly poisoned tree, so
  the failure is the after-control path (complete counts, every entry measured).
- **H1 🟠** — `evidence()`'s body printed `caught N` + per-entry `caught` under its own
  `NOT MEASURED`. Now: no `caught` figure, and every entry renders `NOT RUN` when untrustworthy.
- **M1 🟡** — extracted `control_is_green(rc, out)`; `mutate_delivered` had required rc 0 alone.
- **L1 🟢** — four skip-without-append sites, not three; corrected in all four copies.
- **4 mutations orphaned by these edits**, retargeted before the manifest was written.
- ⚠ **The harness went RED on this round's own fix.** Doing *both* halves of H1's suggested
  repair made the per-entry `measured` test unreachable; `--mutate .` reported 1 survivor naming
  it. Collapsed to one mechanism, subsumed mutation retired with its reason.
- Counts: 177 → **183** cases; 32 → **35** mutations here (36 then −1 retired); sum 173 → **176**.

⚠ Codex returned **CONVERGED** for the second round running over live defects. Its checks were
individually true and aimed at what the previous round *fixed*, not what it *changed*.

⚠ I also broke the dual-review output contract this round: one shared brief for both halves told
Codex to write a file, so the wrapper captured a *report* rather than the review. Nothing was lost
(`gate_ran: true`, real review on disk) but the loud-failure mechanism was bypassed. Fix: per-half
output instructions, never one brief.

## 2026-09-03 [needs-you]
Phase 6 — the architecture review that fires when four review rounds in a row fail to settle —
ran on the tooling we have been fixing all day, and found why it would not settle.

Seven rounds of review each found a problem inside the previous round's fix. None of those rounds
was wrong; each fix was correct. The reason they kept finding more is structural: the thing they
were all reviewing is a bag of loose values passed between six functions, and the one rule that
matters — *never report a coverage number without also reporting whether it was actually measured* —
is written down nowhere except in comments. Each round fixed one place that forgot the rule. Nothing
made the next place safe. The rounds were not failing; they were counting, one at a time, through a
list a proper design could have closed in a single move.

Two related things. Sixteen of our checking scripts each contain their own private copy of the same
test-reporting helper, and none of them share one — which is exactly how we once got twelve checks
reporting "nothing failed" over output nobody could read. And the project's glossary describes the
product in nine sections but has no words at all for this checking machinery, so seven rounds of
argument happened in vocabulary the project does not officially have.

**Waiting on you:** three candidates are written up, in order of cost. The cheapest — giving this
machinery a name in the glossary — is a precondition for discussing the other two. My recommendation
is to do that first and then the interface fix, and NOT to run a fifth review round, which would
most likely find an eighth instance of the same thing.
<!--tech-->
`docs/reviews/architecture-review-2026-09-03b.md`. Triggered by dev-process.md:107 (four
non-converging rounds), not a milestone. Second arch review today; findings A–E of
`architecture-review-2026-09-03.md` and ADRs 0001–0013 explicitly not re-opened.

- **F1 🔴** — `ev` is a plain dict: 7 keys, 2 producers, 6 touchers. `trustworthy` read by 2 of 6;
  `check` reads `mutations`/`survivors`/`files` and never reads it. Every one of the seven rounds'
  defects was a producer holding part of the contract or a consumer skipping the verdict.
  Measured by AST, `scratchpad/phase6-ev.py`.
- **F2 🟠** — 16 scripts define a private `case()`; zero import a shared one. One `count_drift`,
  one importer. Distinct from this morning's finding A: that was counting, this is shape.
- **F3 🟡** — `check-plan-code.py` 2,517 lines, 50% its own suite, four jobs, one CLI seam.
  Stated as the weakest of the three.
- **Not written down:** `CONTEXT.md` has 9 sections, all product; `grep` for
  mutation/harness/guard/ratchet returns ONE incidental line.

Candidates: (3) name the stack in CONTEXT.md — precondition; (1) give the coverage verdict an
interface — recommended; (2) one self-test-result seam across 16 guards — grill the cost first.
Nothing filed to docs/backlog.md; triage is the user's step per review #4's precedent.

## 2026-09-04 [needs-you]
The design for fixing the thing seven review rounds kept circling is written down, and it is short
enough to disagree with.

The problem in one line: the tool reports two things — some numbers, and whether those numbers mean
anything — and nothing stops a reader taking the numbers without the second part. Seven rounds each
found one more place that forgot to check. The design makes that impossible rather than discouraged:
when a run measured nothing, **the numbers do not exist to be read**. A future author who copies a
line from the working case onto the broken one gets an immediate error instead of a plausible wrong
figure.

The alternative — keep one object and put a guard in front of the numbers — was rejected, and the
reason is specific rather than stylistic: that is exactly what the previous round already tried. It
built one shared rule and still shipped holding two of its three parts, because nothing stopped a
caller from being wrong. A guard you can forget to consult is a convention with a better name.

**Waiting on you:** the spec is a Phase 1 gate, so it needs your approval before any code. It also
carries three questions I deliberately did not settle alone — where the new type should live, what
happens to the freshness check that re-derives the report, and how the test suite keeps building
deliberately-broken states once broken states become unconstructable.

One thing the spec says about itself, which matters more than the rest: it narrows the class of
defect but does not close it. If an eighth round finds something, the honest prediction is that it
will be in how a value is *produced*, not in how the report is *read*.
<!--tech-->
Backlog **#91** filed at the user's instruction (Phase 6 #7, finding 1). Spec v1 at
`docs/superpowers/specs/2026-09-04-coverage-verdict-interface-design.md`, anchor `status-visibility`.

- **Decided:** tagged union `Measured | NotMeasured`. `NotMeasured` has **no `survivors` field at
  all** — the "0 survivor(s)" success sentence cannot be printed over a run that measured nothing —
  and its list is named `entries`, not `mutations`, so copying a line from the measured path raises
  `AttributeError` rather than returning a wrong number.
- **`Measured`'s constructor enforces all three clauses** (controls green; `len == declared`; every
  entry measured). The contract moves out of a predicate a caller may forget to call and into a
  constructor that cannot be bypassed.
- ⛔ **Guarded accessor REJECTED, reason recorded so it is not re-litigated:** it fails exactly as
  `verdicts_are_trustworthy` did in r3.
- **8 falsifiers**, including F6/F7 — a clean run's stdout must stay byte-identical (F2-S3).
- **3 open questions carried deliberately:** own module vs inline; `verify_evidence` making the
  pasted block's grammar part of the interface; the ~10 hand-built `ev` dicts in the suite that
  construct invalid states on purpose.
- §7 states what this does NOT fix: it stops bad *consumption*, not bad *production* of a clause.

## 2026-09-04 [needs-you]
The guard that was supposed to stop me walking away mid-job has never once fired. It now can.

Back in August a check was built for one specific failure: a turn ends on a summary whose last
sentence names the next step, and then nothing happens. It has occurred four times, most recently
on 2026-09-03, when a turn closed with "I'll take steps 1-4 without checking back" and nine hours
passed with a merge sitting ready.

The check reads a small file that says which plan is being worked and how many of its steps are
still open. That file has never been written — not once since the check shipped — so the check has
been switched off in practice while looking, in every listing, like it was on. There is now one
command that writes it, and the same command prints the "STEP 3 of 6" banner you already expect to
see before each step. So arming the guard and announcing the step are the same keystroke.

I proved it rather than assuming it: with nothing armed the session was allowed to end, with two
steps open it was refused, and once both were ticked it was allowed again. Same hook, unmodified,
three runs.

**Waiting on you — one decision.** What I built removes the *excuse* for not arming the guard; it
does not remove the *possibility*. I could still type that banner by hand and leave the guard
asleep, and you would see no difference. Closing that requires a second, more intrusive piece: a
check that notices a turn announced "step 3 of 6" while nothing was armed, and refuses to end the
turn. That is a real behaviour change with a real false-alarm risk, so I have not built it. Say the
word if you want it, and I will; say no and this stands as-is, with the gap written down in the
code rather than hidden.
<!--tech-->
`scripts/begin-plan.py` (new, 33 self-test cases) on branch `task-224-begin-plan`. Task #224 — my
own to-do note, not a GitHub issue.

- **What was dormant:** `scripts/check-plan-progress.py` (17 cases) reads `.claude/executing-plan`,
  which nothing ever wrote. `.claude/hooks/block-idle-stop.sh` has been wired at
  `.claude/settings.json:82` the whole time.
- **Measured, not argued:** unarmed `rc=0` (control run first) → 2 unticked steps `rc=2` → all
  ticked `rc=0` and the sentinel self-clears. `--pause "<why>"` also releases it; a bare `--pause`
  with no reason is refused, because an unexplained pause and an abandoned plan are
  indistinguishable to whoever reads the file next.
- **Mutation-tested on a temp copy:** deleting the `_arm(plan_rel)` call in `cmd_begin` turns the
  suite red **via the two cases that name it**. Before those cases existed all 29 were pure-function
  tests, so that deletion would have stayed green — the same "the function is covered, the CALL that
  makes it load-bearing is not" shape `check-plan-code` round 6 recorded.
- **Count drift caught itself:** the docstring's hand-written "26 cases" failed against the 28 that
  ran, on the first execution. Now pinned in `check-selftest-counts.POPULATION` (9 → 10), which
  refused the file until it was pinned — the two-way ratchet doing its job in both directions.
- **Plans land in `.claude/plans/` (gitignored), not `docs/superpowers/plans/`:** that directory is
  `check-anchors.py:121`'s population and requires a Goal + Anchor header on every dated file. A
  session to-do list is per-machine execution state, like the two sentinels beside it.
- **One rule, one owner:** `count_steps` / `next_pending_task` / `parse_sentinel` are imported from
  `check-plan-progress.py` and asserted present at import, never re-implemented; `count_drift` is
  borrowed from `check-plan-code.py`. The banner and the blocking guard count the same boxes by
  construction.
- **Gates green:** `check-selftest-counts` (10/10), `check-ratchet-contract` (26 guards),
  `check-docs`, `check-anchors`, and `begin-plan --self-test` 33/33. `begin-plan.py` is not a
  `check-*.py`, so the ratchet contract's population never sees it — `check-selftest-counts` is its
  only outside observer, which is why pinning it mattered.
- ⚠ **Stated limit, in the module docstring:** the banner↔arming coupling is conventional, not
  mechanical. Not claimed as covered.

## 2026-09-04 [needs-you]
Three checks that were quietly not working now work — and the review round found the pattern is structural, not a run of bad luck.

Following on from the entry above, three separate jobs landed, and they turned out to be the same
problem wearing different clothes: a check that exists, reports success, and is not reaching the
thing it claims to measure.

First, you asked for the warning version of the "did you actually arm the guard" check rather than
the blocking one. It is built. When a turn announces "step 3 of 6" and nothing was armed, it says
so loudly and does not stop anything. Every time it fires it writes one line to a log, so the
question "does this cry wolf?" will have a number rather than an impression when you decide whether
it should ever block.

Second, a guard that was supposed to catch a specific mistake in review instructions had missed the
real occurrence, because it only recognised one way of phrasing it. It now recognises four more.
While using it, it also turned out to *reject* the correctly-worded instruction — it read "do not
write the review to a file" as a demand to write one. Fixed, with three extra tests whose only job
is to stop that fix becoming a loophole.

Third, two checks CI had never once run — because they were parked behind a database they do not
need — now run on every push. One of them is specifically the check that would have caught the
architectural problem the last review found.

**Then the review round, and this is the part that needs you.** Two independent reviewers examined
yesterday's fixes. Both said not converged. They disagreed with each other, and when I ran the code
myself, *each was right about something the other missed* — so trusting either alone would have got
the severity wrong.

The substantive finding: the coverage added yesterday protects against someone *deleting* a check,
but not against someone *weakening* it. Four different weakenings all pass the full suite. Worse,
the most natural tidy-up a person would make — having two near-identical checks share one
implementation — is one of those four. Doing the obviously-good thing silently reinstates
yesterday's bug and the tests stay green.

**Waiting on you — one call.** This is the seventh round running where the new defect is inside the
previous round's fix. The project's own architecture review predicted exactly this and it happened.
My recommendation is **do not run round eight on the same axis**: the repetition is structural, not
carelessness, and another round will find a ninth instance. The alternative is a design change to
how coverage is expressed. I have not started either — the axis is your decision.
<!--tech-->
Branch `queued-jobs-222-p6-223`, stacked on `task-224-begin-plan` (PR #218). Three commits:
`5f1b536d`, `3c5d8a74`, `8c8179be`.

- **Warn-only detector** — `scripts/check-banner-armed.py` (25 cases). Warns iff the HIGHEST banner
  in the turn is `STEP i of N` with `i < N` AND nothing armed. Taking the HIGHEST is what keeps the
  common case quiet: a 5-step job finished in one turn emits `STEP 5 of 5`, so `i == N`. Exit 1 =
  Claude Code's non-blocking error (stderr to the user, stop proceeds); exit 2 = CANNOT RUN. Never
  exit 2 from the hook — a detector that only observes must not be able to wedge a turn.
  Log: `.claude/banner-warnings.log` (gitignored).
- **#222** — `prompt_demands_a_file` widened for the relative clause, `at`, and the passive.
  Control table old-vs-new: 4 missed→FIRES, 1 already-caught still fires, 2 false-positive controls
  quiet in BOTH columns.
- **Negation** — `do not write your review to a file` matched `write your review to`. Predates the
  widening (pattern 1 is original); the existing prohibition case used "write no file", which has
  no `write ... to`, so nothing covered it. Fail-CLOSED, so never unsafe — but it blocked the
  CORRECT brief. `_is_negated`: 60-char lookback, `[^.!?\n]` stops it crossing a sentence. THREE of
  six new cases exist to stop the negation becoming a universal off-switch. Suite 51→63.
- **`docs/plugins.md` claimed 35 cases; the suite ran 51.** Drift of 16 for an unknown span.
  `codex-review.py` now declares canonically and is pinned in `check-selftest-counts.POPULATION`.
- **Phase 6 #7 finding 4** — `check-guard-coverage.py` + `check-vocabulary-collisions.py` had one
  automated caller (`check-schema-gates.sh`, needs Postgres, itself referenced 0× in ci.yml).
  Neither touches a DB; both docstrings already said "the rule never needed the container".
  Own CI steps now. `dev-process.md` rows corrected — they claimed enforcement while nothing ran them.
- **CI YAML validated by a real parser** (ruby/psych, 41 steps). PyYAML absent locally; skipping
  silently would have been a NOT RUN reported as a pass.
- **r5 Claude H1** — three refusal paths through the `--mutate` printer; `grep -n 'main(["--mutate"'`
  returns exactly ONE hit (`:2225`), covering one. Four *weakening* mutations survive at 183/183.
  M-A is the verbatim gate-harmonisation `check-vocabulary-collisions.py` encourages.
- **r5 adjudication** — Codex High vs Claude Low on `control_is_green`. Executed:
  `verdicts_are_trustworthy([], 0, True) = True` (Codex's route real);
  `control_is_green(0,'0/0 passed') = True`. With mutations declared it IS fail-closed (Claude's
  bound real). Settled **Medium**. Fourth "reviewers split = the signal", and the first where
  picking the finding-reviewer would ALSO have been wrong.
- ⚠ **The Codex half ran DEGRADED and the brief was the cause.** "Do not create, modify or delete
  anything on disk" → it reported `NOT RUN` for `--self-test` and `--mutate .` and reviewed by
  reading. Re-dispatched as `codex-code-r5b`. Corrected rule in the coordinator doc: forbid the
  review ARTIFACT and repo writes, never "disk".
- **NOT FOLDED.** Findings recorded only.

## 2026-09-04
Three backlog items filed, and the reason you had to ask "is CI done yet" turned out to be embarrassing.

You asked me to file three things I had found, so they are now written down properly rather than
living in a review document nobody re-reads: a review tool that accuses itself of writing files it
did not write, a tidy-up that would silently reintroduce a bug we fixed yesterday, and a guard whose
documentation promises slightly more than it delivers.

While filing them I nearly created a fourth problem. An existing item pointed at "item 92" — and
item 92 had never been written. Taking that number for one of mine would have quietly redirected
the old pointer at something unrelated, which is the sort of thing nobody notices for months. The
old item now says the thing it was pointing at was never filed, and why leaving it unnumbered is
deliberate.

**Then the more interesting one.** You noticed I had no way of knowing when CI finished, and you
were right about the symptom. The cause was not what either of us assumed: I *did* have a watcher,
it worked, and it had already caught a real failure earlier in the day. I had armed it for one push
out of three. So the tool was fine and arming it was the problem — which is now the third time today
that a perfectly good check sat switched off.

There is now a check at the end of every turn that notices when CI is running and nobody is
listening. It cannot start the watcher for me, so it is a nag rather than a cure, and the code says
so plainly instead of implying otherwise. The design detail that matters: it remembers *which
commit* is being watched, so pushing new work automatically switches it back on. "I armed it once,
so I'm covered" is precisely the mistake it exists to catch.

It earned its place within the hour: this very change went red in CI, and I knew before you did.
<!--tech-->
Branch `backlog-and-axis-fix` → PR #221. Commits `896f6ef5` (backlog), `5a641e19` (CI watcher).

- **Backlog #92 🟡 / #93 🟠 / #94 🟢** — filed at the user's instruction. #92: `dir_snapshot` diffs a
  directory across the run window, so it cannot separate *"the agent wrote this"* from *"this
  directory changed"* — and dual review guarantees a concurrent writer, since both halves write into
  `docs/reviews/`. #93: the M-A trap — harmonising the two printer gates is what
  `check-vocabulary-collisions.py` encourages and it reinstates r4's Blocking with CI green; the
  gates differ ON PURPOSE (`:2459` omits the `declared is None` escape). #94: the anti-nag is
  per-continuation-chain; a background-task notification starts a fresh turn with
  `stop_hook_active` false, so it blocked three times in one session.
- ⚠ **#91 referenced a `#92` that never existed.** Claiming the number would have rebound the
  pointer. Corrected in place with the reason stated — same class as the recorded positional-read
  defect that closed two open items by hitting the wrong cell.
- **`scripts/check-ci-watched.py`** (22 cases), Stop-hook question #3. Measured: watcher armed for
  `26698462` ✅, absent for `cb4bfc7b` and `a62de138` ❌. **SHA-scoped sentinel** —
  `decide(SHA, OLD_SHA, pending) -> WARN` is a dedicated case. An **unknown** check state counts as
  unresolved, never as done. **No `gh` call at all** on the default branch or a branch with no
  upstream: measured 0.03s.
- ⚠ **Option B (a push-and-watch command) REJECTED with a reason:** unlike `begin-plan.py`, whose
  banner is independently required and human-checked, there is no artifact to couple to, so it
  degrades to a convention with a file attached.
- **This entry exists because the ratchet refused the branch** — 5 tracked files changed, no entry.
  The gate worked; I skipped its step.

## 2026-09-04 [resolved: 2026-09-04/1]
Three small tooling items closed, one design decision made, and the big one deliberately shelved so the next stretch can be about making things easier to follow.

You asked to focus on comprehensibility, and to finish what was already planned first. That is what
this branch is. Four of the five planned items are done. The fifth — the deep fix behind the seven
review rounds that kept circling — is **parked on purpose**, with a written reason and a written
trigger for picking it up again, so it is shelved rather than forgotten.

The one that turned out to matter more than filed: our review tool had been **accusing the wrong
writer**. When two reviewers work at once, it saw a file appear and blamed whichever one it was
watching — it had done this in four recorded reviews. Worse, and nobody had noticed: when a review
*failed*, the tool would physically **move the other reviewer's finished work out of the project**.
That is the exact situation where a second reviewer is most likely to be working, because a failed
review is supposed to be replaced by one. Nothing was lost — it is caught now, and the fix was to
change where reviewers file their work rather than to weaken the check.

<!--tech-->
Branch `wrap-planned-residue`.

- **Backlog #93 — CLOSED as an explanation, not a fix.** Comments at both printer gates in
  `check-plan-code.py` (now `:2536` and `:2583`, moved from the row's `:2459`/`:2506` by the axis
  fix). ⚠ **My first draft of that comment was FALSE**: it named a mutation
  `harmonise the two printer gates` that does not exist, and **cannot** — the harness refuses a
  second manifest entry repeating an earlier entry's edit anchors, and that anchor is taken by
  `the --mutate printer stops gating on trustworthiness (r4 B1)`. Corrected to name the real guard.
  MEASURED on a temp copy, control first: unmutated `189/189 rc=0`; gate harmonised `188/189 rc=1`,
  red via `a run whose CONTROL failed prints no tally at all (r5 H1, path 2 of 3)`.
- **Backlog #94 — CLOSED.** `check-plan-progress.py` docstring now states the anti-nag is
  **per continuation chain**, not per plan (`stop_hook_active` is false on a turn begun from a
  background-task notification). Fourth escape line added for *blocked on in-flight work*, and
  `begin-plan.py --pause` no longer sells itself as hand-back-only. Used it on this branch.
- **Backlog #92 — CLOSED, both halves, and the second half was not in the row.** (a) Wording:
  `CREATED/OVERWRITTEN by the agent` → `... (writer unattributed)`; a digest diff cannot see a
  writer. (b) **MEASURED on temp dirs**: on the FAILED path `quarantine()` moved a legitimate
  `slice-r6-claude.md` out of `docs/reviews/`. Fix chosen by the user — **halves file under
  `docs/reviews/<writer>/`**, invisible to the non-recursive snapshot, so the top level becomes a
  no-legitimate-writes zone and quarantining what appears there is correct.
  `check-review-rounds.py` reads BOTH layouts and **refuses a basename filed in both**
  (22→27 cases). Full account in `process-rationale.md` → *The reviewer blamed for its partner's work*.
- **Phase 6 findings D and E — CLOSED.** D: backlog #48's `STOP-HOOK VERDICT: NOT BUILT,
  deliberately` corrected in place — it WAS built (`8b9643d9`), and #48's reasoning was right about
  the design it rejected, which is the actual lesson. E: the hook's hardcoded case count is
  **deleted**, not corrected — `check-plan-progress.py` now declares its own count and is pinned in
  `check-selftest-counts.POPULATION` (13→14 observed scripts).
- **Backlog #91 — PARKED by user decision.** Spec approved, Phase 2 plan not written. MEASURED that
  the round-4 Blocking on to-do note #217 no longer reproduces: an `EXPECTED_MUTATIONS` drift now
  prints `NOT MEASURED — … Treat this as NOT CHECKED.` instead of `0 mutation(s), 0 survivor(s)`.
  The design defect is unfixed; unpark trigger is written on the row.
- ⚠ **`dev-process.md` said `check-review-rounds.py` had 14 self-test cases; the suite ran 22.** A
  third declared-count drift, found only because this branch happened to touch the file.

## 2026-09-04
Settled items on this page now look settled, and say who settled them.

Two small things you reported are fixed. First, an item that has been decided was still shouting:
the bold "Waiting on you:" line stayed warning-orange while the little "resolved" badge beside it
was almost invisible — so the marker that was *right* whispered and the sentence that was *stale*
shouted. Both now follow the item's actual state.

Second, a settled question used to go quiet without saying how it ended. It now names the entry that
settled it and links to it, in that entry's own words — "settled by 2026-09-01/11: You chose to hold
the automatic check". Nothing new had to be recorded; that link existed the whole time and was simply
never drawn.

Also fixed: a stray character in a web address could make the local page server hang up without
answering at all, which cost nothing today but would have cost someone ten confused minutes later.

<!--tech-->
Branch `comprehensibility-slice-a` — backlog **#83 (A + B)** and **#87**, the two rows in the
comprehensibility bundle whose shape was fully decided.

- **A1** `<article>` gains `settled`, derived from the SAME `_b` as the badge and ask label. Also
  hardened the `_fragment` self-test helper, which located cards by the exact string
  `class="entry"` — every existing fixture is uncleared so it still passed, and the trap would have
  sprung on whoever wrote the first settled fixture.
- **A2** `.entry.settled .prose strong` → body token; `.entry.settled .flag.resolved` → opacity 1.
  **Scoped to the state, never the token** — restyling `--p-mark` would silence every LIVE warning.
- **A3** `resolvers(entries) -> {cleared_id: resolving entry}`; `cleared_ids` is now
  `set(resolvers(...))`. ONE traversal, two views.
- **A4** backlog #87: `safe_path` resolved outside its own `try`. Fixed at the RESOLVER, not the
  handler — four URLs, two handlers, and `/_rev` goes through `resolve_page`.

**MEASURED IN CHROME** on the live page: 7 settled cards; settled `.prose strong` `rgb(230,231,227)`;
an INJECTED uncleared `**Waiting on you:**` still `rgb(224,160,80)` — the falsifier, which needed
injecting because the store has no natural uncleared instance; settled flag opacity 1; 3
back-references, all resolving to existing cards.

**MEASURED against the server**: `/_stale?p=%00` → 200, `/_rev?p=%00` `/%00` `/dashboard%00` → 404.
Before: curl exit 52, no status line.

Suites: gen-dashboard 314/314 (was 309), explainer-serve 84/84 (was 81), check-plan-code 189/189.
EXPECTED_MUTATIONS 70 → 73 for gen-dashboard, sum 176 → 179; three mutations added, each naming the
case it must go red through. `--mutate .` deferred to CI per the lighter-verification default.

## 2026-09-04
A /brief page can now be answered in tomorrow, not just today — and two finished items finally say so.

When I build you a /brief page, the page itself lands somewhere permanent but the working file it was
built from used to live in a temporary folder named after the session. So the moment that session
ended, nobody could rebuild the page to add an answer to it — while every page carried a printed
promise that you could come back and ask. The promise was real; the means to keep it was not. The
working file now sits next to the page, so any later session can pick it up.

Also: two items I finished earlier today were still listed as open. That is now corrected.

<!--tech-->
Branch `comprehensibility-slice-b` — backlog **#88**, plus the **#83 / #87** status closes owed from
PR #223.

- **#88** `brief-compose.py main()` writes the fragment beside the page as `<page>.fragment.html`.
  MEASURED 2026-09-03: 43 pages in `~/explainers/`, zero fragments; the source lived under
  `.claude-tmp/<session-uuid>/scratchpad/`. `explainer-delivery.md` §1 puts the page outside the
  repo so it outlives its session; §6 requires answers be written INTO it — unachievable once the
  source dies with the session. ⛔ NOT a `--from-page` mode: that makes the rendered page its own
  source of truth, the failure this script exists to prevent.
- Four cases, and the last two are the point — existence proves nothing. The sibling must be
  **byte-identical** to what composed the page, and must **re-compose into a page that still has the
  tray**. ⚠ They drive `main()` with `--out` into a temp dir on purpose: `ROOT` binds at import from
  `Path.home()`, so the default path would write into the reader's live `~/explainers/`. Verified
  after the run: 0 fragments there.
- **#83 / #87 closed** with their merge SHA and what was measured. ⚠ `check-docs` refused the first
  attempt — a CLOSED row must lead `✅ (was <severity>)`, not the bare severity, or a severity scan
  counts it as open. Same class as the missing-Status-column error that once marked #46 and #50
  closed while they were open.

Suites: brief-compose 44/44 (was 40). Not run locally: schema gates (need Postgres), `--mutate .`
(CI runs it; `brief-compose.py` carries no manifest).

## 2026-09-05
The harness can now notice when I stop announcing my work, which is the one thing it could not
notice before — and which you, not it, had to spot.

There is a Stop-hook check that warns when I announce "step 2 of 6" and then wander off without a
plan armed. It was blind in the other direction: a plan armed, work being done, and no announcement
at all. That is the direction that actually failed last session, because the tool that prints the
banner prints it into a command's output — which I see and you do not. The banner existed every
time and reached nobody.

Two things worth knowing about how this went. First, the check that was supposed to catch it could
not run at all in the state it was written for: a sibling guard refuses the stop first, and the
script exits before ever reaching it. Fixing that also revealed the same thing had been quietly
happening to the CI watcher added the day before — it too was skipped whenever a plan was mid-flight.
Only one of the two was moved; moving both would buy a network call on every blocked stop.

Second, and more usefully: six review rounds all found the same class of problem, which was that
the tests I had written did not test what they claimed. They were written into a plan document,
which cannot be run. The fix was to build the whole change in a throwaway copy of the repo and run
it first — which immediately caught two more broken tests that rounds of careful reading had not.
Eight such tests were found before the pull request; the round after it found two more, one of them
guarding a fix written *during* the previous round. The pattern only broke when I stopped reading
and started reverting each fix in turn to watch a named test go red for it.

Then the guard turned out to have the same disease as the thing it was built to catch, and that is
the part worth your attention. You noticed a "Stop hook error" printing too often. Explaining one of
its warnings showed the check reads the transcript of a turn that is *still being written* — so the
banner that CLOSES a sequence, normally the last thing I say, is invisible to it. It had been
reporting "step 2 of 3" for turns that reached step 3. Confirmed on two sessions by timestamp, one
of them this one.

That is a real defect and it is **not fixed**. You chose to document it rather than chase it, which
I think was right: the honest repair means judging the *previous* completed turn, and that needs
state the guard does not carry, so it is a design change rather than a patch. What shipped instead
is a retraction — the guard's docstring no longer claims a precision it does not have, and the
warning no longer tells you how many steps are unannounced, because it cannot know. The warning log
was cleared, because its entries mix real misses with this artifact and nothing can separate them
after the fact. Filed as backlog #96.

**Merged.** Nothing is waiting on you here.
<!--tech-->
Backlog #95, branch `backlog-95-banner-guard`. `scripts/check-banner-armed.py` gains the
plan-without-banner branch: `armed AND unticked > 0 AND edited AND zero banners`. `_armed()` now
honours `paused:` as `check-plan-progress` does; `count_steps`/`parse_sentinel` are borrowed by path
import rather than re-implemented, with `total == 0` mapped to CANNOT RUN; the transcript window
stops treating `isMeta` records as turn boundaries (but keeps task notifications as boundaries —
measured: 52 of 72 such records begin a genuinely new turn); `log_line` gains a reason column so the
banner-less class can be recorded at all. `.claude/hooks/block-idle-stop.sh` runs the observer ahead
of `check-plan-progress.py`, which also matters because that script unlinks the sentinel as a side
effect. MERGED as `956a4de6` (PR #225). 78/78 self-tests, `bash -n` clean; the final sweep breaks
five fixes in turn and each is killed via the case it names.

Code review r2 (both halves NOT CONVERGED) found five, and the sharpest was that the r1 fold's OWN
fix shipped naked: `_armed()` became three-valued and nothing tested that `run_decide` maps `None`
to CANNOT RUN — mutating `if armed is None:` to `if False:` left the suite green at 75/75. Same
shape as r1's own M5 finding ("delivered against the predicate, not the wiring"), fixed there for
`edited` and reintroduced for `armed` in the same commit. Also: the `OSError` arm of `_armed()` was
untested; F6 — the ONLY guard on the observer/blocking ordering this slice exists to create — was
satisfiable by a COMMENT, because `_obs` was a bare filename and `str.index` takes the first hit
anywhere (now pinned to `check-banner-armed.py" --decide`); the NotebookEdit case passed
`file_path`, so the `notebook_path` fallback that branch actually takes was untested.

⚠ THE SELF-TEST HARNESS ITSELF WAS LYING, which is why `safe()` exists. Measuring the `OSError`
fix, the sweep reported ZERO red cases — the PermissionError propagated through `case()` and ABORTED
the run, so no `FAIL` line and no summary line was ever printed. A harness grepping for `FAIL` reads
that as "nothing caught it". `safe()` makes a raise a failed case, and the sweep now checks for the
summary line rather than trusting an empty grep.

Backlog #96 (option B) then retracted this guard's own precision claim in its docstring, stopped the
WARN message asserting `total - step` steps unannounced, and re-baselined
`.claude/banner-warnings.log` (six entries archived: 2 confirmed artifacts, 1 real partway stop, 2
undetermined — they cannot be retro-classified). ⚠ #96's structural fix, judging the PREVIOUS
completed turn, is NOT taken: `_armed()`/`_plan_steps()` sample the sentinel at decide time while
the banners would come from the prior turn, so it needs per-turn state and is a spec, not a patch.
Round 3 was deliberately NOT run — measured, no decision predicate changed between the PR head and
the merge, so it would have reviewed prose.

Spec+plan: `docs/superpowers/{specs,plans}/2026-09-04-banner-guard-inverse*`; twelve review files
under `docs/reviews/{claude,coordinator}/`. ⚠ `check-ci-watched.py` is deliberately still unreachable
on blocked stops — moving it would add a `gh pr view` call (25s timeout) per blocked mid-plan stop.

## 2026-09-05
Yesterday's summary of the banner-guard work was wrong, and this corrects it. Worth a line of its
own because a stale record is the kind of thing you would never find by looking — it reads as
confidently as a true one.

The entry above was written at the first commit of that work and never touched again, so it stopped
before both review rounds, before the defect they turned up, and before the merge. It still told you
merging was waiting on you, after it had been merged. Its test counts were the numbers from a week
of work ago. The backlog row for the open defect said "not started" while half of it had already
shipped; it now says which half, because "partly done" without saying which half is worse than
either extreme.

The reason this is worth telling you rather than just fixing: the check that is supposed to catch a
missing record could not see it. It verifies that an entry *exists*, not that it is still true, and
those are very different guarantees. The same shape as the defect the entry above describes.

**And this pull request failed CI on exactly that point**, which is the good news. I had run the
entry check locally and read it as green — but I ran it before committing, when the branch had no
commits and the check was comparing nothing to nothing. It passed over an empty diff. CI ran it
against the real change and refused. The gate did its job; my local reading of it was the part that
was broken.

Nothing is waiting on you.
<!--tech-->
Follow-up to PR #225 (`956a4de6`). `docs/dashboard-entries.md`: the 2026-09-05 entry rewritten to
cover code review r1+r2, backlog #96 and the merge — it had drifted to `55 self-tests` (78),
`11/11 mutations` (the final sweep breaks five fixes, each killed via the case it names),
`four review rounds` (six), and a live `**Waiting on you:** merging` after the merge.
`docs/backlog.md` row 96 status now states the split: (a) DOCUMENTED — docstring retraction, the
WARN message no longer asserting `total - step` unannounced steps, log re-baselined; (b) NOT DONE —
the `SHAPE:`, judging the PREVIOUS completed turn, which needs per-turn sentinel state and is a spec
rather than a patch. ⚠ `check-dashboard-entry.py` counts entry blocks ADDED, so editing an existing
block registers as zero; and run WITHOUT `--base`, against an uncommitted tree, it passes
vacuously — CI runs it as `--base origin/$GITHUB_BASE_REF --pr-body-file`, which is the invocation
to reproduce locally before believing a green. Dashboard page regenerated (derived, ADR-0010; writes
to `~/explainers/`), not committed.

## 2026-09-05
Two small hardening changes, and the second one is a change of method rather than a fix.

Your bookmark could have shown you the wrong page. The tool that builds a briefing writes two files
side by side — the finished page, and the raw body it was built from — with the same date and, as it
turns out, the same timestamp. The "show me the latest" link picks the newest, and on a tie it was a
coin flip. Half the time you would have got the raw body: it renders, it looks fine, and it has no
box to answer in. Fixed, and the test for it deliberately uses a tie, because that is the only
setting where the test can tell right from wrong.

The second is the one worth your attention. Yesterday's slice shipped about ten tests that passed
whether or not the bug they were written to catch was present. Six rounds of careful reading found
four of them. Breaking each fix on purpose and watching a named test go red found the rest in
minutes. So there is now a rule: a guard must carry a file describing how to break it, or say in
writing why it does not need one. Twenty-three guards currently do not have one — that number is
recorded, and the check fails if it goes UP, and also if it goes DOWN without the number being
corrected in the same change. Paying the debt down is a separate job, not this one.

**And this pull request failed CI on the same gate as the last one**, for the same reason, an hour
apart: a change that touches tracked files has to add an entry here, and I edited without adding.
Knowing why something failed is evidently not the same as applying it the next time — which is the
argument for the rule above, made at my own expense.

**Waiting on you:** one decision. I recommended a push gate for feature branches; the premise was
wrong, because the mechanism already exists and is better than what I proposed. The remaining gap is
real but its fix would make every routine push need a special prefix, and a warning everyone learns
to type past is worse than none. Your call, and I have not guessed at it.
<!--tech-->
`scripts/explainer-serve.py`: `explainers()` now excludes `*.fragment.html`, so `/latest` and the
index skip composer inputs; `resolve_page` is untouched, so a fragment is still servable by direct
path. REPRODUCED before the fix on an mtime tie: `/latest -> /2026-09-05-brief-x.fragment.html`.
88/88 (declared count 84 → 88, caught by `check-selftest-counts`); mutation reverting the exclusion
kills the two cases that name it, measured as a delta because a temp-copy control cannot run the
repo-reading case.
`scripts/check-ratchet-contract.py`: new R4 — a `scripts/mutations/<name>.json` or a written
`NO-MUTATIONS: <why>`, mirroring NO-CALLER. Wired inside `evaluate()` with its own wiring case, and
`manifest_stems` is a REQUIRED parameter so a caller cannot get the vacuous everything-has-one
answer. `MANIFEST_BASELINE = 23`, an EXACT match not a ceiling, counted separately from R1/R2/R3.
⚠ The baseline came from the delivered tool: a throwaway measuring script said 24, disagreeing by
one because it re-implemented the population — *a second implementation of one rule DRIFTS*.
Falsified in a clean full worktree, both directions: new guard → "debt GREW — 24 vs 23"; one paid
down → "debt SHRANK — 22 vs 23". 22/22.

## 2026-09-05
The push guard now refuses the two pushes that can never be routine, and that is the whole of it.

You chose the narrow option, and it was the right one. A background agent had armed an automatic
push earlier today; the obvious repair — make every push to any branch require a special prefix —
would have closed that, and would also have made the prefix a reflex within a day. A warning
everyone learns to type past protects nothing. So instead the line is drawn at the two forms nobody
uses by accident: the force-push that destroys history, and the flag that skips checks. Everything
else pushes exactly as before, with no new friction.

One deliberate exception, which is the part worth stating: the SAFE form of force-push is still
allowed. Denying it would have pushed anyone in a hurry toward the dangerous one — a guard that
makes the bad option the convenient one.

The guard had never had a test of any kind in the five weeks it has existed. It has nine now, and
each one was checked by breaking the guard on purpose and confirming that named test goes red.
**Nothing is waiting on you.**
<!--tech-->
`.claude/hooks/block-default-branch-push.sh` gains RULE 2, checked BEFORE the branch rule so a
`--force origin master` reports the irreversible half. Denies `(^|[[:space:]])(--force|-f)([[:space:]=]|$)`
and the same shape for `--no-verify`; escape `ALLOW_DANGEROUS_PUSH=1`, SEPARATE from
`ALLOW_DEFAULT_BRANCH_PUSH=1` so neither intent grants the other. ⚠ `--force-with-lease` CONTAINS
`--force`, so the word boundary is load-bearing — a substring test inverts the stated rule, and the
⭐ case exists for exactly that. Flags are matched against the ISOLATED push invocation, not `$cmd`,
reusing the multi-line defect fix already recorded below the branch rule.
First `--self-test` this hook has ever had: 9 cases driving the real stdin JSON contract through the
delivered script (not a re-implementation — one drifted from its tool by one earlier today).
4/4 mutations killed via the case each names: dropping the `--force` word boundary → the
force-with-lease case; removing `--no-verify` → its own; sharing one escape flag → the
two-intents case; `push_only="$cmd"` → the commit-message case. Filename NOT renamed: cited by
`.claude/settings.json`, three live docs and five merged review documents, and rewriting a
historical record to keep it true is not keeping a record.

## 2026-09-05
The check that nags about missing step-headings has been reading a half-written page, and we now
have a design for fixing it properly.

The problem: that check runs at the moment a turn ends, and reads the record of the turn — but the
last thing written in a turn is not on disk yet when it looks. So the closing heading, the one that
says the work finished, is invisible to it. It then complains that a finished job stopped partway.

Measuring it across every session ever recorded here — 524 of them — gives the honest size. Only 48
turns ever used these headings at all, and of those, **9 hid their closing heading and 8 got the
wrong answer because of it**. Roughly one in six of the turns it can actually judge.

Two things turned up that were not previously known. The check can also go wrong in the *other*
direction — staying silent when it should have complained — which the recorded description of this
bug says it cannot. And the obvious simple fix turns out to be quietly wrong: it would be blind on
exactly the turns that under-announce, which are the ones the check exists to catch.

Nothing is fixed yet. This is the written design and its first review round, which both reviewers
failed — three serious problems, all now folded in. The code comes next.
<!--tech-->
Spec `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md` (v2), the structural half
of backlog #96, deferred out of PR #225. Anchor `status-visibility`.

Design: judge the PREVIOUS completed turn, whose text is durably on disk. `decide()` is unchanged —
its inputs change era, not its rules. `armed`/`steps` cannot be re-sampled at judgement time, so they
travel in a per-session journal written at each Stop; `block-idle-stop.sh:62` already runs this guard
ahead of the blocking check precisely so it samples the sentinel before `check-plan-progress.py:180-182`
unlinks it, so the sample point was already right and was simply being discarded.

Round 1, both halves NOT CONVERGED (`docs/reviews/{claude,coordinator}/banner-guard-prior-turn-r1-*.md`).
Three Blockings, all folded: one shared journal file breaks under concurrent sessions in one working
copy; "non-empty window" defined as *has assistant text* would have made the plan-without-a-banner
class structurally unreachable for tool-only turns; and a blocked stop re-firing within one turn
overwrites the still-needed sample and reports CANNOT RUN against a subject it just had.

⚠ The Codex half refuted v1's rejection of the `UserPromptSubmit` alternative and was right —
`:326-327` returns QUIET before `armed` is consulted, so "every turn that finished a plan warns
wrongly" was false. The rejection now rests on the narrow true case, and the residue is the
interesting part: it lands only on turns that under-announce, which is the guard's own subject.

The v1 falsifier list promised behaviour; v2 turns each Blocking into F8–F11, and adds F11 for the
durability assumption that was argued but never measured.

## 2026-09-05
Correction to the entry above, same day: the design changed after it was written.

That entry said the fix would carry a small saved note between turns, so the check could remember
what it saw. It no longer does. The reviewer pointed out that the reason we had ruled out the
simpler approach was itself wrong, and once that was corrected the simple version turned out to
dissolve all three of the serious problems the review had found — they were all consequences of
saving that note.

So the check will now do its work when you send your next message, rather than when a turn ends.
Nothing is saved between turns at all.

It is not free. There is one situation where the simpler version gets the wrong answer: a job that
finished its plan but stopped announcing before the last step. **We cannot measure how often that
happens** — it depends on information that was never recorded — so the check keeps saying out loud
that its number may be wrong, and there is now a test whose job is to make that blind spot show up
rather than hide.
<!--tech-->
Spec v3. §3.1 `UserPromptSubmit` chosen; the per-session journal of v2 is §3.3, rejected on cost
rather than correctness — its sample point is provably right, and `block-idle-stop.sh:62` already
runs ahead of `check-plan-progress.py:180-182`'s unlink for exactly that reason.

⚠ The v3 blind spot: a false `unarmed` needs the plan to have finished that turn AND the highest
banner to be below its total. 26 of 50 bannered turns ended below total, but that is an upper bound
so loose it is nearly uninformative — turns that ended low with no plan ever armed are the warning
firing CORRECTLY, and sentinel state leaves no trace in a transcript, so the two cannot be separated.
Rate unknown and unknowable from this corpus; §3.2 says so instead of quoting the available number.

Round 1's three Blockings are DISSOLVED, not fixed. F9/F10 are kept as absence-falsifiers so
cross-turn state cannot quietly return; F12 asserts the blind spot is real and hedged. F11 matters
more now, not less — the durability margin is the gap between a turn ending and the next prompt,
not a whole turn, and it is still unmeasured.

⚠ Round 1 reviewed the journal. Round 2 reviews a mechanism no reviewer has seen.
The guard also leaves `block-idle-stop.sh` and needs a `UserPromptSubmit` registration in
`.claude/settings.json`, which has no such entry today.

## 2026-09-06
The check that nags about missing step-headings has been fixed. It now waits until a turn is
finished before judging it.

The problem was that it looked at the record of a turn while that turn was still being written, so
the last thing said — usually the heading announcing the final step — was invisible to it. It then
complained that a finished job had stopped partway. Measured across every session recorded here:
of the 48 turns that ever used these headings, 9 hid their closing one and **8 got the wrong answer
because of it**. About one in six.

It also went wrong in the other direction, staying silent when it should have spoken. The recorded
description of this bug said it only ever over-complained; that was incomplete, and is corrected.

Two things are worth knowing about how this was checked, because both were nearly missed:

The test that was supposed to prove the fix **could not fail**. It compared the order of records in
a file, which is fixed by how the file is split — so it would have reported success against a
completely broken check. It has been replaced by something that actually watches for the problem
while running, and reports it when it happens.

And the first attempt to prove the bug even existed showed no difference between old and new. That
was the test setup being wrong, not the bug being absent. Reproducing it properly needed the old
check to see the turn exactly as it looked at the moment it ran.
<!--tech-->
Backlog #96 structural half. `scripts/check-banner-armed.py` now judges the PREVIOUS completed
turn, using the sentinel sample taken at THAT turn's own stop, carried in a per-session journal at
`.claude/banner-turn-state/<session_id>.json`.

The sample point was already correct — `block-idle-stop.sh:62` runs this guard ahead of
`check-plan-progress.py:180-182`'s unlink precisely so it sees the sentinel before deletion. The
observation was simply discarded; it is now kept for one turn. The guard does NOT move hooks.

Round 1 and round 2 both NOT CONVERGED on both halves. v3 briefly switched to `UserPromptSubmit`
(no state at all) and was reverted: that mechanism reads the sentinel AFTER the turn it describes,
so its race is about TIME and cannot be repaired without the state it exists to avoid — and its
failure mode is a SILENT MISS of the plan-without-a-banner class, versus a noisy CANNOT RUN.
Recorded as spec §3.2, rejected, with the reasoning.

Journal carries prev_* (a blocked stop re-fires the hook inside one turn), last_judged_uuid
(exactly one verdict per turn), and sampled_turn_len — the F11 replacement, which compares how many
records a turn held at its own stop against one stop later, so a late flush is observed rather than
argued. ⚠ Pyright, not a test, caught that a journalled `armed: null` is falsy and would have turned
CANNOT RUN into a false accusation.

93/93 self-test (78 → 93); 7-mutation manifest added, so R4 debt 23 → 22 with MANIFEST_BASELINE
lowered in the same commit. F6 ran once as a migration check — 526 transcripts, 526 identical —
because after the refactor it too would have been a tautology.

## 2026-09-06
The check that shipped this morning was warning on almost every turn, and it has been quietened
without being thrown away.

It was watching for something real — and it found it. The question the previous slice could not
answer was whether a turn's text is reliably on disk by the time the next one ends. It is not
always, and that is now proven by observation rather than argued. But the check treated every
occurrence as an alarm, when in fact it is the ordinary case, so it cried wolf ten turns running.

Two things were wrong, and only one of them was obvious. The alarm is the visible half. The quieter
half is that each false alarm was being filed in the log under the name of a completely different
problem — so the record that is supposed to tell us whether this check is worth trusting was being
filled with entries describing something that never happened. That log is the evidence for a
decision we have not made yet, and this is the second time it has been polluted.

The measurement stays, moved to its own file where counting it means something. Nothing is waiting
on you beyond merging.
<!--tech-->
Backlog #97, branch `backlog-97-late-flush`. Three changes to `scripts/check-banner-armed.py`:

(a) The `QUIET -> WARN` promotion at `:754-755` is deleted. The note now rides along only with a
warning that would have printed anyway.

(b) The observation moves to `.claude/banner-flush-observations.log` (gitignored, new). A third
`reason` value in `banner-warnings.log` was rejected: that file's stated job (`:451-454`) is to be
the false-alarm rate OF THE WARNING, so a non-warning line in it is the same category error as the
defect being fixed. Nothing parses either file — re-verified by grep, and two prior review rounds
concluded the same independently.

(c) The predicate is `len(texts_of(window))`, not `len(window.body)`. That is not a proxy for the
durability question: it is the literal list `decide()` consumes at `:742`. Journal keys renamed
`sampled_turn_len` -> `sampled_text_len` (and `prev_*`), so a record written by the shipped code is
invisible to the new comparison — one turn of blindness, taken deliberately, because reusing the
names would compare an all-records count against a text count and under-report forever.

HOW THE DIAGNOSIS WAS MADE, since it is not obvious from the symptom: 9 of the 10 log lines read
`unbannered` + `0 unticked`, which `decide()` cannot emit — its banner-less WARN (`:411`) requires
`unticked > 0`, and the log derives that field (`:813-814`) from the same `steps` object `decide()`
was handed. The 10th read `STEP 7 of 7`, and `:428-429` returns QUIET on `step >= total` before
`armed` is read. Both shapes were therefore unreachable except through the escalation.

⛔ F11 RE-ANCHORED. Its cases discriminated on the exit code (`grow=True -> WARN`); with the
escalation gone both sides are QUIET and the pair would assert nothing — vacuous for the THIRD
time, after being a tautology in spec v2 and v3. It now reads the observation record. The manifest
mutation "the late-flush comparison is inverted" names F11a and dies through it.

96/96 self-test (93 -> 96; five cases replace two). Mutation verified on a throwaway copy with the
control proved green FIRST: control 94/94, mutant 91/94 with F11a dead. 94-vs-96 is the known
scripts-only delta for the two cases reading `.claude/hooks/`. selftest-counts, ratchet-contract
(22, at baseline), guard-coverage 16/16, check-docs, review-rounds all green.

Warn log re-baselined again: 16 lines archived to `.claude/banner-warnings-archived-2026-09-06.log`,
10 of them escalation artifacts that cannot be separated from real warnings retrospectively. Also
corrected backlog row 96's merge tick, which named a deleted branch instead of PR #229.

## 2026-09-06
Before picking the next piece of comprehensibility work, I re-read every open item in that group
against the code — and found that the backlog was describing a world that had moved on.

Twice in a row I proposed building something the project already had. Both times the code, not my
memory, caught it. That is worth recording as a habit rather than an embarrassment: the rows are
written once and then trusted for weeks, while the code they describe keeps changing underneath
them.

The concrete finds: one item had already shipped and its row still said "not started"; one item's
stated harm was solved four days after it was filed; one was waiting on something that has since
merged; and my own newly-filed item turned out to be warned about, in advance, by an older item
nobody had connected it to.

Nothing is waiting on you. The work this pass replaced — a slice to build staleness detection —
was cancelled, because staleness detection already exists and works.
<!--tech-->
Branch `entry-gate-timing-78b`. No code changed; this is a records pass plus the three corrections
committed earlier as `3d53980c`.

FINDINGS, each verified against the tree rather than recalled:

- **#88** — merged as PR #224 (squash `65cd509e`) while its 1422-char status cell said "OPEN —
  not started". Corrected. Filed the blindness as **#98**: `check-docs.py` compares the severity
  MARKER to the STATUS CELL, both internal to the row, so a stale row's two fields agree with each
  other and disagree only with git. One-directional, the same shape as #95's banner detector.
- **#78 half (2)** — premise HOLDS (`ci.yml:313` is still `pull_request`-only) but its stated harm
  does NOT. `/_stale` + `RELOAD_JS` (`explainer-serve.py:811-830`) poll every 2s and on
  `visibilitychange` and tell the reader which source file moved; `gen-dashboard.py:1187` renders
  "Could not parse this entry". Filed 2026-08-31, answered 2026-09-02, never re-read. Now recorded
  as a CI-timing preference rather than a reader-facing defect.
- **#89** — its stated blocker (#88) is cleared. Also noted: every open question in it is about
  forking agents, so it cannot be validated while the Agent tool is off.
- **#98 ↔ #56** — ⭐ the best find. #56 already says *"Do NOT rebuild the reconciliation as a gate:
  it fires on every docs-only commit and gets disabled."* #98 proposes exactly a row-vs-git check.
  That measured verdict settles #98's open warn-vs-block question in favour of WARN, and the
  cross-reference is recorded on both rows so it is not derived a third time.
- **#82, #40, #50, #90** — premises intact; no correction needed.

⚠ A SLICE WAS CANCELLED, deliberately and mid-flight. `entry-gate-timing` was armed to widen the
regen hook's trigger and add serve-time staleness detection. Reading `explainer-serve.py` before
writing the spec showed the second half already shipped, which also bounded the first half's harm
to a "press Refresh" banner instead of an auto-refresh. The plan was paused with the refuting
reason rather than completed. The measured fact behind it stands and is NOT filed, because its
consequence is now small: `regen-dashboard.sh:30` keys on `tool_input.file_path`, so a Bash
heredoc append moves the store without regenerating the page.

## 2026-09-06
The check that guards dashboard entries can now catch a broken cross-reference — the last thing it
was blind to.

An entry can point at another entry to mark it settled. Until now the check could confirm that
pointer was well-formed but never that it pointed at anything real, so a reference to an entry that
does not exist sailed through and only showed up later as an error on the page. The reason is
duller than it sounds: the check was only ever shown the lines a branch changed, and whether a
reference is real is a fact about the whole file.

So it now reads the file — before and after — and reports only what your branch actually broke. A
pre-existing problem is not yours to fix, which matters more than it sounds: a check that fails
every branch for someone else's old mistake is a check people turn off.

The independent reviewer found five things, two of them serious, and one of those was about my
testing rather than my code. All fixed. Nothing is waiting on you beyond merging.
<!--tech-->
Backlog #82, branch `backlog-82-referential-gate`.

- **T1** `parse_entries` (139 lines) + `_first_sentence` and five constants moved from
  `gen-dashboard.py` into `check-dashboard-entry.py`. There is now exactly ONE `def parse_entries`
  in `scripts/`. The arrow still points page → gate: the gate does not import what it guards
  (`_gate_module`'s rule). The dependency set was SIX names and my first scan — a regex requiring a
  lowercase start — found none of them; the AST free-name closure named the rest at once.
- **T2** `added_reference_errors(base, head)` parses both stores and returns the multiset
  difference. `collect()` runs `git show <base>:docs/dashboard-entries.md`; `verdict()` refuses
  above the exemption short-circuit. An unreadable baseline reports rather than passes.
- **T3** eight mutations moved with the code — `run_suite(d, fname)` runs only the mutated file's
  own suite, so a mutation whose killing case is elsewhere reads as a survivor. gen-dashboard
  73→64, gate 34→43, **sum held at 107**.

⛔ THREE SEPARATE NEAR-MISSES, each of which a green suite reported as fine:
1. Eight new cases sat BELOW `print(f"{ok}/{ok+fail} passed")`. They ran and gated the exit code
   while the summary still said 127/127 — invisible to `check-selftest-counts` and to mutation
   attribution. Found because the number did not move when it should have.
2. Three of eleven new cases could not reach the branch they named (a bad-DATE block never claims
   an ordinal; `[blocked]` is not matched by FLAG so it takes the header path). Found by running
   the mutations one at a time: 5 killed, 3 survived.
3. Codex found a mutation that SURVIVED because I ran the gate's manifest and never
   gen-dashboard's. Third corpus error of the day.

Review: `docs/reviews/coordinator/referential-entry-gate-code-r1-codex.md` — 2 Blocking, 3 High,
NOT CONVERGED, all folded. The Blocking that mattered most: I keyed the diff on `(title, error)`
because `parse_entries` never set `header`; titles are legally duplicated, so a newly added broken
entry could collide with a pre-existing one and go unreported. `parse_entries` now records
`entry["header"]` and the spec's original key stands.

⚠ `REVIEW GAP: claude` — the Agent tool is disabled this session.

Verified: gate 146/146 + 13/13, page 314/314, check-plan-code 189/189, controls green FIRST then
43/43 and 64/64 mutations with zero survivors, and every ratchet green.

## 2026-09-06
A warning I was about to dismiss as noise turned out to be reporting something real: a safety check
had been switched off for hours without anyone noticing.

Partway through the last piece of work I paused the plan at a checkpoint. When we resumed, I ticked
off the remaining steps and finished the job — but nothing ever cleared the pause. The tool that is
supposed to stop me ending a turn with work outstanding only does that while a plan is *running*,
and as far as it was concerned nothing was.

So the warning was correct, and its wording is what made it easy to ignore. Filed, with the fix
left as a genuine choice rather than an assumption — the options differ in whether resuming should
be something you say out loud or something that just happens.
<!--tech-->
Backlog **#99** 🟠, branch `backlog-99-paused-tick`.

`.claude/executing-plan` still carried `paused: T1+T2 committed and pushed…` from a checkpoint
hours earlier. `_armed()` returns **False** on a paused sentinel, so every turn after the resume was
judged as "nothing armed" — the `unarmed` warning was literally right.

⛔ THE COST IS THE GUARD, NOT THE WARNING. `check-plan-progress.py:100` and `:206` treat
`"paused" in fields` as *allow the stop immediately*. Arming a plan exists so that script REFUSES a
premature stop; from the pause to the end of the slice that protection was off — through four
steps, a code review and a PR.

`begin-plan.py:369` writes the `paused:` line and `--tick` never consults or clears it, so a plan
can be simultaneously *paused* and *5 of 6 done* with nothing noticing.

Three shapes recorded, not decided: `--tick` refuses on a paused plan; or it clears the pause
implicitly; or the Stop guard reports `paused with N steps outstanding` instead of allowing
silently. Falsifier: pause, tick, then stop with steps outstanding — today that is ALLOWED.

⚠ The step number in the warning (`STEP 3 of 6`) is NOT trustworthy — `highest_banner` conflates
sequences with different totals, the defect #96 spec §8 deliberately left open. The armed/unarmed
half was right; the number was not, and it should not be cited as evidence.

Also this turn: PR #232 merged (`3ec912f6`, backlog #82), and the stale sentinel removed by hand.

## 2026-09-06
The pause that never ended now has a way to end. Yesterday's finding was that pausing a plan quietly
switched off the check that stops a turn ending mid-work — and that once paused, nothing could
un-pause it except editing a file by hand. Both halves are fixed, and you chose the shape.

Two things changed. Ticking off a step on a paused plan is now refused outright, and the refusal
tells you the one command that resumes. And when a plan really is paused with work left, the guard
says so at the end of every turn instead of standing down in silence — it still lets you stop, which
is the whole point of pausing, it just stops being indistinguishable from a plan that finished.

The third option — having a tick quietly un-pause the plan — was rejected, because pausing is also
how work says it is waiting on something, and a wait that cancels itself without telling anyone is
how you lose track of what you were waiting for.

Worth knowing: the fix was proved by running the failure end to end against an unmodified copy of
yesterday's code, side by side. The old copy drove a paused plan from one step done to two with the
guard off; the new one refused. Nothing here rests on a test that only ever saw the fixed version.
<!--tech-->
Backlog **#99** 🟠 CLOSED, PR #234, branch `backlog-99-paused-tick`. Decided shapes **(a)+(c)**;
**(b)** rejected.

⚠ TWO CORRECTIONS TO THE ROW AS FILED, both found by reading the code rather than the row.
(1) It told (a) to say *"run `--resume` first"* — **`--resume` did not exist.** `paused:` had ONE
writer (`begin-plan.py:369`) and ZERO removers; a state with a setter and no clearer is why a stale
pause could only ever be cleared by hand. (2) (c) could not be "ALLOW with a message":
`check-plan-progress.py` sent every non-BLOCK message to **stdout**, which
`.claude/hooks/block-idle-stop.sh` swallows — the stream that made `begin-plan.py`'s banner reach
nobody for a whole session (CLAUDE.md records it). So (c) is a third exit code, `WARN = 3`, message
on **stderr**, wrapper allow-list `{0,3}`. **NOT 1** — a traceback exits 1 and every other non-zero
is a fail-closed BLOCK, so reusing 1 turns a broken interpreter into a polite warning.

`strip_field` lives in `check-plan-progress.py` beside `parse_sentinel`, and `--resume` BORROWS it:
one owner for "which line is the `paused` line", because `check-banner-armed.py:499` already records
what two disagreeing parsers of that grammar cost.

FALSIFIER (the row's own, run by hand against an `origin/master` control) — they separate at all
four points: stop-while-paused says nothing / names `2 of 3`; tick-while-paused ADVANCES the plan /
refuses byte-identically; `--resume` exits 2 no-such-flag / exits 0; the stop after that is allowed
silently / BLOCKS. 203 mutations, 0 survivors.

⛔ OUT-OF-SCOPE FINDING, and the useful one. Both files printed `FAIL  {name}` while the mutation
harness parses `[FAIL] {name}: got … want …` (`check-plan-code.py:887`), so **all 17 new mutations
killed their suites and NOT ONE could be attributed** — "the guard did not fire" and "nothing could
see it fire" are the same output. `check-banner-armed.py:924` records the identical finding from the
same day. Latent in both files for exactly as long as neither had a manifest.

`MANIFEST_BASELINE` 22→21 (only `check-plan-progress.py` is R4 population; `begin-plan.py` is not a
`check-*` guard and was never counted as owed). `EXPECTED_MUTATIONS` 186→203. Declared self-test
counts 17→31 and 33→42.

⟳ AFTER REVIEW — the shipped behaviour CHANGED. Dual adversarial r1 (Codex gpt-5.5 + an
independent Claude subagent) came back NOT CONVERGED from both halves: 0 Blocking, 1 High,
5 Medium, 8 Low between them. The High and Codex's top Medium are THE SAME FINDING, reached
independently — the first cut deleted a paused-but-fully-ticked sentinel, discarding the reason
text, and said so only on stdout, which the Stop wrapper swallows.

Fixed by PRESERVING rather than clearing-and-announcing, which is the opposite of what the Claude
half recommended — its own escalation clause ("Blocking if the remaining work is tracked outside
the checkbox list") describes a checkpoint pause exactly, and since #94 a pause means *waiting*.

Also folded: `--pause` refuses a multi-line reason (r1 M3 drove a real `plan:` field injection that
left the guard supervising a DIFFERENT plan); seven stale cross-file line citations replaced by
symbol references, five of them broken by this very commit; `cmd_tick` reads the sentinel once.

⚠ THE FOLD BROKE ITS OWN COVERAGE, TWICE, AND ONLY EXECUTION SAW IT. The `_armed_plan` refactor
orphaned a mutation anchor (anchors bind by TEXT), a new anchor collided with an existing one, and
a third mutation SURVIVED because it re-ticked an already-ticked box. 206 mutations / 0 survivors
only after re-running. Reading the diff would have found none of them.

⟳ ROUND 2 FOUND A HIGH IN THE ROUND-1 FIX, and both halves found it independently again. The
multi-line guard added in r1 tested for two characters. Python's `splitlines()` — which the sentinel
reader actually uses — breaks on eleven, so EIGHT separators walked straight through the new guard
and re-opened the exact injection it was written to stop. Measured: `parse_sentinel` returned the
injected plan path.

The fix is not a longer character list. The guard now asks `splitlines()` itself, and the test
derives its separator corpus the same way, so neither can fall behind the reader again. That was the
real defect: a hand-written copy of the consumer's rule, covering 2 of 11.

Two more from r2, both my own errors. The claim "ten stale citations removed" was wrong — the diff
removed seven, and FOUR wrong ones survived in the same file, three of them sitting just above the
paragraph declaring that line numbers expire. Corrected in both documents and the sweep finished.
And the preserve message's `--finish` guidance had no mutation — which is r1's own finding recurring
inside the code written to fix it.
<!--tech-->
r2 both halves NOT CONVERGED: Codex 1 High; Claude 1 High + 2 Medium + 8 Low. Filed under
`docs/reviews/{claude,coordinator}/backlog-99-paused-tick-r2-*.md`.

Separators that defeated the r1 guard: `\v` `\f` `\x1c` `\x1d` `\x1e` `\x85` U+2028 U+2029.
Codex named the last two; enumerating the `splitlines()` set found the other six.

Also folded: `_load_plan_progress` now asserts `decide` and `WARN` (r2 L2 — borrowed but
unasserted, so a rename surfaced as a bare AttributeError instead of the explanatory ImportError);
a no-op `cmd_tick()` whose comment claimed an action replaced by an explicit precondition assertion
(r2 L3 — the same line that let a mutation survive earlier).

EXPECTED_MUTATIONS 206→207. Declared counts 47→50. r2 L1/L4/L5 recorded as dispositions: L1 is a
correction to a COVERAGE CLAIM, not code — the "isolating" mutation narrows 3 co-red cases to 2 and
cannot isolate further, because the r1 L3 rename made the sibling a superset assertion.

**Decided: merge, and file the design question rather than run a third round.** Two review rounds
both came back not-converged, and every single finding in the second round had been introduced by
the first round's own fix. The review method has a name for that shape and a prescribed response,
and the response is not "review again" — it is to stop and look at the design.

So what got filed is the thing underneath all of it: the small file that records which plan is
running has no agreed shape, and the code that writes it checks different rules from the code that
reads it. Three defects this slice looked unrelated and were all that one fact.
<!--tech-->
Backlog **#100** 🟡 filed (`M`, comprehensibility). NOT a live defect — all three instances it names
are fixed in PR #234. The call was made with `docs/review-method.md:195`'s own discriminator, *"did
the previous fix cause this?"*, which answered **yes for five of five** r2 findings: the thrashing
tell, whose prescribed response is Phase 6 rather than another round.

⚠ Recorded so it is not read as a verdict on the slice: the ROUNDS were not converging but the
FIXES were — each was more structural than the last, and r2's removed its class by delegating to
the consumer's own parser instead of patching another instance.

Three r2 dispositions ride to merge unfixed and are named on the PR: L1 (a corrected coverage
CLAIM, not code), L4 (no mutation in the fix-went-too-far direction), L5 (a message printed before
a pause still says the sentinel will be cleared, which the preserve branch no longer does).

## 2026-09-06
The next three pieces of work are now written down, so a context reset cannot lose them.

Until now the roadmap offered a *candidate pool* — a list to pick from, explicitly not a plan. It now
carries one plan, chosen by the user: settle a continuous-integration timing question that has
already been demoted twice and may simply be closeable; pay down the mutation-testing debt owed by
21 guard scripts; and work out how the status pages get built without consuming the main
conversation's working memory. None of the three depends on the others, so they can be taken in any
order.

Nothing was broken and nothing was fixed here. This is bookkeeping, and its whole value is that the
next session starts with an answer to "what now" instead of a search for one.
<!--tech-->
A `CURRENT GOAL` block is added inside `docs/roadmap-to-launch.md`'s `▶ NEXT ACTIONS` section rather
than as a competing top-level heading — two answers to *what's next* is the duplicate-mechanism
shape `scripts/check-vocabulary-collisions.py` exists to catch. Mirrored as three entries in the
session task list (Claude Code's own in-session to-do list — **not** GitHub issues and **not**
`docs/backlog.md` rows), which is the layer that does not survive `/compact`; the roadmap is the one
that does.

**Measured this session, not recalled:**
`.github/workflows/ci.yml` triggers on **both** `pull_request` and `push: branches:[master]`, and
exactly **one** step in the workflow is `pull_request`-gated — the dashboard entry ratchet — because
it feeds `--base "origin/$GITHUB_BASE_REF"` and a `--pr-body-file` from
`github.event.pull_request.body`. ⚠ That does **not** mean the gate cannot run on a push:
`check-dashboard-entry.py` defaults `--base` to `origin/master` and `--pr-body-file` to `None`, so it
would execute against an empty diff and hit the exempt short-circuit — **vacuous, not impossible**.
`scripts/check-ratchet-contract.py` reports 21 R4 manifest violations against `MANIFEST_BASELINE`
21, at baseline; 10 manifests exist in `scripts/mutations/`. The baseline is compared with `!=`, so
paying one down reddens CI until the constant drops in the same commit.

Backlog **#89**'s stated dependency is cleared: backlog **#88** merged as PR **#224** (squash
`65cd509e`, verified by `git show`). ⚠ Note the namespace hazard in that neighbourhood — commit
`8642b2e0` carries `(#88)` as a **PR** number while `a0ea4d79` names **backlog** #88; same digits,
different registries.

Gates run on this branch: `check-docs`, `check-roadmap-consistency`, `check-anchors` — all `rc=0`
(anchors: 10 registered, all claimed, floor 22 held). No new anchor was allocated: `docs/anchors.md`
holds names of durable goals claimed by a spec or plan, and three unrelated maintenance items are
not one goal. The deliverable-declaration question inside backlog #89 — which *would* be an anchor
change — is deliberately left to the user.

## 2026-09-06 [needs-you]
The "should the entry check run earlier?" question has an answer, and the answer is no — it can be closed.

The worry was that a reader might see a badly-formed status entry on the page before the automated
check had a chance to reject it, because that check only runs when a change is proposed for merging.
Reading the code settles it: **every rule the check enforces, the page also enforces — and the page
runs first.** So the reader is never quietly shown something the check would have rejected; the page
says "could not parse this entry" at the moment it is written, hours before the check ever looks.

That is a different reason from the one written down when the item was demoted, and a stronger one.
The note on file argued from a *staleness* banner, which answers "this page is out of date" — a
genuinely different question from "this entry is malformed".

**Waiting on you:** closing the item is your call, not mine. The engineering is done and needs nothing.

Along the way this turned up a comment in the checking script that had gone out of date the same day,
describing a limitation that a change merged hours earlier had removed. That is fixed here.
<!--tech-->
**Backlog #78 half (2) — RECOMMEND CLOSE.** Verified rather than argued:

* `header_error` is **shared** between `check-dashboard-entry.py` (gate) and the page's parser, so
  header SYNTAX cannot diverge.
* Backlog #82 (`3ec912f6`, merged today) added the REFERENTIAL half: `collect()` → `added_reference_errors(base_text, head_text)` → `verdict(..., ref_problems)`, refused **above** the exemption
  short-circuit. Wiring confirmed at `collect():1271` and `main():1426,1435` — not merely present.
* `decision_errors` runs in the RENDERER only and is deliberately not wired into the gate (backlog
  #81 tier 2, held by user decision 2026-09-01). So on content the page is currently **stricter**
  than the gate, never weaker.
* ⇒ For every content rule in force, page ⊇ gate, and the page renders at write time while the gate
  runs at PR time. The `if: github.event_name == 'pull_request'` window therefore has **no
  reader-facing hole**. The gate's other job — refusing a branch that owes an entry — is a process
  rule that runs on every PR, and every change reaches master through one.
* ⚠ Residue, stated not hidden: a FUTURE rule added to the gate with no renderer counterpart would
  break that inclusion. The seam is documented at `added_entry_problems`, so it is visible, not latent.

**Defect found and fixed here.** `header_error`'s docstring ended *"Until then a wrong-but-existing
`[resolved:]` id reaches the reader as 'could not parse this entry' on the page rather than as a
refusal at the gate."* Measured today, that is false: `header_error("## 2026-09-02 [resolved: 2026-09-01/99]")` → `None`, but `added_reference_errors` → `['… names no entry in this file']` and
`verdict` → `rc=1`. **True about the FUNCTION, stale about the FILE** — the shape this repo keeps
producing. The replacement states what the function decides and names the sibling that decides the rest.

Control run BEFORE the edit: 146/146 + 13/13 `rc=0`. After: identical. `check-ratchet-contract`
21/baseline 21 unmoved; `check-selftest-counts` 14 scripts verified. Diff is docstring-only. The ten
Pyright unused-variable warnings are **pre-existing** — identical on `origin/master`.

## 2026-09-06
The first of twenty-one unchecked safety nets now has a test that it actually catches things.

The project has a set of small scripts that guard against mistakes. Each has its own tests — but a
test can pass while the thing it tests has quietly stopped working, so there is a second layer that
deliberately breaks each guard and checks the tests notice. **Twenty-one guards had no second layer.
This is the first one paid off**, and the debt counter drops from 21 to 20.

Doing it turned up something worth more than the coverage. The guard reported its own failures in a
slightly different format from the one the checking machinery reads. Everything looked fine — the
tests passed, the guard worked — but had anyone added this coverage without noticing, all five checks
would have reported "we broke the guard and nothing caught it", when in truth the guard caught all
five and merely said so in words the machine could not read. **A false report of no coverage, which
would most likely have been answered by writing more tests that were never needed.**

That is now fixed and, more importantly, demonstrated: the same five checks were run against the old
format and against the new one, and the difference is exactly the five wrong answers.
<!--tech-->
**GOAL 2/3, first payment. `scripts/mutations/check-explainer-delivery.json` — 5 mutations.**
`EXPECTED_MUTATIONS["scripts/check-explainer-delivery.py"] = 5`; `MANIFEST_BASELINE` **21 → 20 in the
same commit**, which the ratchet requires — it compares with `!=`, not `>`, so paid-down debt cannot
be silently re-accrued.

Chosen first because its rules are pure: 8 self-test cases against synthetic trees, no live Postgres,
no network. Each mutation is the WEAKEST edit that still fails via the case it names:

| # | Mutation | Red via |
|---|---|---|
| 1 | citation requirement dropped | `missing citation caught` |
| 2 | `Monitor({` check dropped | `Monitor block caught` |
| 3 | hollow shared reference accepted | `hollow shared file caught` |
| 4 | restatement sought in whole text, not only fences | `prose mention allowed` |
| 5 | restatement sweep narrowed to one skill | `restatement in another skill caught` |

**⛔ THE FAIL-LINE CONTRACT HAD TO BE FIXED IN THE SAME CHANGE.** `self_test` printed
`  ✗ {label}: got {got!r}`. `check-plan-code.py` attributes a kill by taking lines that **start with**
`[FAIL] ` and doing `.strip()[7:].rsplit(": got ", 1)[0]`, so it could not see these at all.

**MEASURED BOTH WAYS on a temp copy** (never the repo — an instrument that edits the repo corrupts
its peers):

* control, unmutated: `rc=0`, zero `[FAIL]` lines;
* with the fix: 5/5 red **via the case each names**, no extras, nothing killed by something else;
* with the OLD format, same 5 mutations: `rc=1` every time and **attributable cases `[]` every time** —
  the `matched 0 red case(s) … caught by something else: []` shape. Red, and mute about why.

Same defect, same day, as the one the handoff records for `begin-plan.py` and
`check-plan-progress.py`. It stays latent until a manifest first points at the file, so **expect it on
the next several of the remaining 20** — check the print format before writing any mutations.

`check-ratchet-contract` now reports 20 violations against baseline 20, at baseline. Guard self-test
unchanged at 8/8; its declared count is still 8, so `check-selftest-counts` is unaffected.

## 2026-09-06
A second guard is covered, and this one would have lied rather than gone quiet.

Same job as the previous entry — proving a safety net actually catches things — but the guard in
question reported its failures in a format that *almost* matched what the checking machinery reads.
The others in this family are unreadable to it and produce an obviously empty answer. This one
produced a **plausible but wrong** answer instead, which is the harder kind to notice.

Debt drops from 20 to 19.
<!--tech-->
`scripts/mutations/check-handoff-path.json` — 5 mutations, `EXPECTED_MUTATIONS` +5 (total 212 → 217),
`MANIFEST_BASELINE` 20 → 19 in the same commit.

⚠ **THE NEAR-MISS, which is why this guard was taken second and not last.** It printed
`[FAIL] {name}: expected {expected}, got {got}` — note `, got `, not `: got `. It therefore CLEARS
`check-plan-code.py`'s `startswith("[FAIL] ")` filter, unlike its 18 siblings. But attribution is
`rsplit(": got ", 1)[0]`, and **`rsplit` on an absent needle returns the whole string**. MEASURED
before the fix:

    'pristine upstream — the reversion this exists to catch: expected 1, got 0'   ← today
    'pristine upstream — the reversion this exists to catch'                      ← after

The first is a case name no `expect` entry can ever match, delivered with the confidence of a real
one. All four print sites in the file now use `: got {got} want {want}`.

The five mutations, each the weakest edit that reddens exactly one case, verified on a temp copy with
a green control first — no extras, none killed by something else:
`CONSUMED_PATH` loses its directory → *near-miss: remember.md without the directory*; missing file
returns 0 not 2 → *missing file is CANNOT RUN*; empty file returns 0 not 2 → *empty file is CANNOT
RUN*; the violations→exit-code map inverted → *compliant file exits 0*; a `mktemp` mention
short-circuits the check → *pristine upstream — the reversion this exists to catch*.

That last one matters beyond coverage: `check-handoff-path` is layer 2 of the three-layer defence in
`docs/plugins.md`, and *pristine upstream* is the exact reversion it exists to catch. Gates: 189/189,
ratchet 19/baseline 19 at baseline, all rc=0.

## 2026-09-07
The automated check caught something my own testing could not, which is the point of having it.

Yesterday's second safety-net fix looked complete: every local check passed. The shared automated
check then refused it — correctly. The tool that verifies these nets needs the word "passed" in a
suite's summary line to tell "everything worked" apart from "nothing ran at all", because a program
that does nothing also finishes without complaint. The guard in question said "PASS" instead, so the
tool declined to report anything and said so, rather than guessing.

Nothing was broken by this and nothing shipped wrong — the refusal happened before the merge. It is
the third undocumented expectation this exercise has turned up about how these guards must speak,
and finding it early is worth more than the fix.
<!--tech-->
**CI red on #238, diagnosed and fixed.** `check-plan-code.control_is_green(rc, out)` is literally
`rc == 0 and "passed" in out`. `check-handoff-path.py` printed `PASS`, so the control was rejected —
*"did not prove the suite works (exit 0) … Every verdict below would be an artefact"* — and all five
verdicts were correctly withheld as NOT CHECKED. Its summary now reads `10/10 self-test cases passed`,
matching every sibling. It is not in `check-selftest-counts.POPULATION`, so no declared count moves;
10 = 7 text + 3 file cases, which is what `docs/plugins.md` already claims.

⚠ **THIS IS A THIRD CONTRACT, on the SUCCESS side**, distinct from the two FAIL-line ones: (1) the
line must start `[FAIL] `, (2) it must contain `: got ` for `rsplit` to name the case, and now
(3) a green suite must print `passed`. All three are enforced only when a manifest first points at a
file. **Check all three before writing mutations for any of the remaining 19.**

⚠ **AND THE LESSON ABOUT MY OWN VERIFICATION.** I verified attribution with a purpose-built harness
that mirrored the parse rule but *not* the control predicate — so it could not see this. Per the
lighter-verification default I skipped the local `--mutate .` and let CI own it; CI earned its keep.
Now run and green here too: **12 files, 217 mutations, 0 survivors.**

## 2026-09-07 [resolved: 2026-09-06/7]
Fourteen more safety nets are now watched by a check that already existed.

Two days of paying down testing debt kept running into the same thing: the tool that verifies these
guards expects them to report results in a particular way, and almost none of them did. The obvious
response was to build something new to enforce it. **That would have been a mistake** — a check
already in the project does exactly this, as a by-product of its real job, and it was simply pointed
at fourteen too few files. Widening it was cheaper, safer, and added nothing new to maintain.

Measured before deciding: of the guards already covered, every single one already met the
requirement. Of the fourteen outside, one did not. That ratio is what settled it.

Separately, the question about whether a status check runs early enough is **closed** — but not for
the reason previously written down. And a genuinely different gap found while merging yesterday is
filed on its own rather than folded in, because merging two questions into one is the exact mistake
the closed item documents.
<!--tech-->
**`check-selftest-counts.POPULATION` 14 → 28.** All 14 additions declare `--self-test  # N cases` and
the guard verifies each **by running it**: *"28 script(s) declare a count, every one verified by
running it"*. Counts came from live runs, never literals: 74, 16, 15, 13, 16, 19, 16, 117, 32, 11,
26, 14, 6, 10.

**Why widen rather than build.** `control_is_green(rc, out)` is `rc == 0 and "passed" in out`;
POPULATION membership enforces that as a side effect of parsing `N/M … passed`. MEASURED: of the
unpaid guards, **5 were already members and 5 of 5 satisfied it**; of the 14 outside, **1 did not**.
A new guard would have needed its own `--self-test`, non-fail-open, a caller and a manifest — adding
to the very R4 debt it existed to pay down — and would have been a second mechanism for one concern,
the shape `check-vocabulary-collisions.py` exists to catch. **Result: all 19 remaining unpaid guards
now satisfy contract (3); measured 0 failures.**

⚠ **MY OWN CAVEAT WAS WRONG, in the useful direction.** I flagged that `check-live-schema`,
`check-catalog-coverage` and `check-anon-exposure` might be ineligible because they need a live
catalog. Their **entry points** do; their `--self-test` rules are pure and run in ~0.1s. Conflating
those two is what left three ratchets untestable for eight days once already. All 14 were eligible.

Two output defects fixed: `check-producer-enumeration` printed `PASS` (now `11/11 self-test cases
passed`, with the total **counted**, not a literal — two literals drift together and agree); and
`check-live-schema`'s summary sat **before** a multi-line epilogue while `printed_total` reads the
**last** ratio line — correct only because that prose happened to contain no ratio. Moved to last.

**Backlog #78 half (2) CLOSED** on a measured inclusion: `header_error` is shared, #82 (`3ec912f6`)
added the referential half wired through `collect():1271` and `main():1426,1435`, and
`decision_errors` is renderer-only — so page ⊇ gate on content, and the page renders first.
**Backlog #101 FILED**: a PR based on another branch gets no CI at all, and *"no checks reported"*
sits where a green tick would, with `mergeStateStatus` still `CLEAN`.

## 2026-09-07
Two planned pieces of work turned out to be wrong, and finding that out is the result.

The plan was: build a small rule to catch a reporting mistake, then work through the remaining
nineteen safety nets. **Neither survived contact with measurement, and both failures are cheap
now instead of expensive later.**

The rule cannot be written. Distinguishing a mangled label from a legitimately punctuated one needs
information that simply is not in the text — and the existing machinery already reports the problem
when it matters. Building it would have added false alarms and caught nothing new.

The remaining nineteen are not nineteen. **Four of them cannot be covered as written**, because
their tests read project files that the coverage tool deliberately does not copy. Those four need a
small change first. The other fifteen are ready.
<!--tech-->
**Step 2 (contract-(2) static rule) — DROPPED, with evidence.** The rule I proposed was
*"a `[FAIL]` print must also contain `: got `"*. It is wrong twice over. (a) `[FAIL] {name}` with
**nothing** after it is already correct — `rsplit(": got ", 1)` on an absent needle returns the whole
string, which IS the name; `gen-dashboard.py` uses exactly that shape and has 64 working mutations, so
the rule would have flagged a working guard. (b) Scoped to manifested files it produced **11 false
positives** in `check-plan-code.py` itself, whose case names are plain text (`[FAIL] f returns one:
got %r`). The root reason it cannot work: `check-plan-code.py`'s own docstring records that **a case
name may contain a colon**, so `[FAIL] my case: expected 2, got 1` is indistinguishable from a
legitimately punctuated name. The needed information is not in the literal. ⇒ contract (2) is
**detectable only at manifest time**, which the existing harness already does as
`expect matched 0 red case(s)`.

**Step 3 re-scoped by measurement.** `mutate_delivered` does `shutil.copytree(root/"scripts", …)` —
**scripts/ only**. A suite whose `--self-test` reads anything else fails its control in the harness
and can never be manifested. Run in a tree containing only `scripts/`:

| | |
|---|---|
| **15 manifestable now** | anchors, arch-findings, catalog-coverage, ci-watched, docs, gate-falsifiability, guard-coverage, live-schema, plan-task-order, producer-enumeration, review-rounds, roadmap-consistency, sentinel-meanings, test-counts, vocabulary-collisions |
| **4 blocked (non-hermetic)** | `check-anon-exposure` (rc=2), `check-function-revokes` (rc=1), `check-paid-caller-arrival` (rc=20), `check-storage-grant-pin` (rc=1) |

`check-storage-grant-pin` is the worked example: `MIGRATION = ROOT/"supabase"/"migrations"/"0007_storage_and_rpcs.sql"`, and `ROOT` resolves into the temp tree. Its fix is a decision, not a
typo — make the self-test hermetic (inline a fixture) or teach the harness to copy more — so it is
recorded, not guessed at.

**Kept from the attempt:** its per-case line printed `PASS`/`FAIL` with no bracket, a contract-(1)
violation. Now `[FAIL] {name}: got … want …`. That fix is what made the control failure *readable* —
it reported `[FAIL] policy is extractable from the migration: got False want True` instead of an
unattributable red. Debt stays at **19**; nothing was registered.

## 2026-09-07
A third guard is covered — and this one is the guard that watches for duplicated vocabulary.

Same routine as the last two: deliberately break the safety net five ways and confirm its own tests
notice each one. It needed the usual reporting fix first, and two of the five attempts were wrong
before they were right — one broke the same line twice, and one turned out not to break anything at
all. Both were caught here rather than by the shared check, which is the point of running it locally.

Debt drops from 19 to 18.
<!--tech-->
`scripts/mutations/check-vocabulary-collisions.json` — 5 mutations against `evaluate`, the pure
rule split out of `main()` so the check can run without Postgres. `EXPECTED_MUTATIONS` +5
(217 → 222); `MANIFEST_BASELINE` 19 → 18, same commit.

Contract (1) fixed first: it printed `✓`/`✗`, invisible to the attribution parser.

**Three things went wrong and each is worth keeping:**

1. **Two mutations shared one anchor** (`len({…tables…}) > 1`). `check-plan-code` refuses duplicate
   anchors, so this would have been rejected. Caught by asserting uniqueness *before* registering.
2. **A mutation SURVIVED.** Truncating the header's table list to `[:1]` left the per-hit lines
   below still naming both tables, so `the problem names both tables` still passed. The fix is a
   two-edit mutation that removes both. **A mutation that survives is not a coverage gap — it is a
   wrong hypothesis about what the case reads.**
3. ⚠ **MY VERIFY HARNESS WAS WRONG, and it had been wrong for two guards.** It copied a SINGLE
   file; `mutate_delivered` does `shutil.copytree(root/"scripts", …)`. On a guard importing a
   sibling it reported `CONTROL FAILED — rc=1 fails=[]` — a harness bug wearing the costume of a
   guard defect. Now copies the whole tree. This is the second time a substitute for the real
   checker inherited only the rules I had noticed.

Also fixed: the manifest-inventory case compares against `sorted(EXPECTED_MUTATIONS)`, and I
inserted the new name in the wrong position — same members, different order, one red case. The list
is sorted; position is not free.

Verified: control green on the full tree, 5/5 red **via the case each names**. Real harness:
**13 files, 222 mutations, 0 survivors.** 189/189; `check-selftest-counts` 28 verified by running.

## 2026-09-07
The architecture-findings ratchet is covered, and one of its five checks defends against a guard quietly switching itself off.

Fourth of these done, and the routine is holding: fix how the guard reports failures, then break it
five ways and confirm its own tests catch each. No surprises this time — every attempt worked first
try, which is what the last three rounds' corrections bought.

Debt drops from 18 to 17.
<!--tech-->
`scripts/mutations/check-arch-findings.json` — 5 mutations across the two pure functions,
`line_counts` and `Metric.run`. `EXPECTED_MUTATIONS` 222 → 227; `MANIFEST_BASELINE` 18 → 17, same
commit. Contract (1) fixed first — it printed `✓`/`✗`.

| # | Mutation | Red via |
|---|---|---|
| 1 | `/*` dropped from the comment-skip set | `a block open … is NOT counted` |
| 2 | `skip_comments` ignored | `skip_comments=False counts the comment too` |
| 3 | indentation not stripped | `a line comment … is NOT counted` |
| 4 | `cur > baseline` → `>=` | `sitting exactly ON the baseline is OPEN, not REGRESSED` |
| 5 | `lower_is_better=False` loses its REGRESSED branch | `lower_is_better=False — more is better` |

⭐ **Mutations 1–3 defend a defect this script shipped on its FIRST run**: it reported finding #2/2a
as REGRESSED because `sync-run.ts:329` is a *comment explaining* that `promote()` is
create-if-absent — the one site that had already fixed the bug counted as a site still exhibiting it.
A ratchet that scores its own fix as a regression is one somebody switches off.

⭐ **Mutation 5 defends the subtler failure.** A `target == baseline` regression guard is only safe
with `lower_is_better=False`; under the default, deleting the guarded file makes `cur < baseline`
classify as **OPEN**, so `main()` returns 0 and the guard is silently disarmed. That branch now has
a mutation proving the case which asserts it is load-bearing.

Verified: control green on the full tree, 5/5 red via the case each names. Real harness:
**14 files, 227 mutations, 0 survivors.** 189/189; `check-selftest-counts` 28 verified by running.

## 2026-09-07
The "one column, one meaning" guard is covered — including the branch that exists because this guard once disarmed itself.

Fifth of these. The interesting one is a check that catches an *excuse outliving the thing it
excused* — a note saying "this exception is fine" that stays behind after the exception is gone.
This guard had already suffered exactly that, silently, and the branch that now prevents it had no
coverage of its own until today.

One attempt had to be softened: removing a guard clause outright made the program crash rather than
report a failure, and a crash proves nothing about which check was watching.

Debt drops from 17 to 16.
<!--tech-->
`scripts/mutations/check-sentinel-meanings.json` — 5 mutations against `evaluate()`, the pure rule
split out of `main()` so it runs without Postgres. `EXPECTED_MUTATIONS` 227 → 232;
`MANIFEST_BASELINE` 17 → 16, same commit. Contract (1) fixed first (`✓`/`✗`).

| # | Mutation | Red via |
|---|---|---|
| 1 | UNDOCUMENTED sweep dropped | `a nullable column with NO recorded meaning is caught` |
| 2 | STALE sweep dropped | `a documented column that is no longer nullable is STALE` |
| 3 | the `ORPHAN JUST.` label renamed | `a justification … does not exist is an ORPHAN` |
| 4 | `STALE JUST.` branch dropped | `a justification whose meaning has NO conjunction …` |
| 5 | `CONJUNCTION` loses `\b` | `a word containing a conjunction does not trip it: 'brand'` |

⭐ **Mutation 4 guards the disarm this script actually suffered.** Its one `CONJUNCTION_OK` entry had
gone unreachable: the meaning for `video_artifacts.generation_id` was reworded to
`"CONFLATED — see CONJUNCTION_OK"`, which contains no conjunction, so the search `continue`d before
consulting the allowlist. The conflation was still live. **The guard had been disarmed by an edit to
the text it inspects** — this project's most-repeated defect shape — and it was found by this
script's own new self-test, not by reading it. That branch now has a mutation.

⚠ **Mutation 3 had to be WEAKENED.** Removing `if key not in meanings:` let the `elif` reach
`meanings[key]` and raise `KeyError`: the suite went red with **zero** `[FAIL]` lines, so nothing
could say which case was watching. **A crash is not a kill.** Renaming the label instead reddens the
one case that reads it.

⭐ **Mutation 5's case is protective in the other direction**: `CONJUNCTION` uses `\b` so ordinary
English — "brand", "record" — does not trip the rule. A guard that fires on prose gets muted rather
than obeyed.

Verified: control green on the full tree, 5/5 red via the case each names. Real harness:
**15 files, 232 mutations, 0 survivors.** 189/189; `check-selftest-counts` 28 verified by running.

## 2026-09-07
The guard that demands other guards be tested is now itself tested.

Sixth of these, and the most self-referential: this is the check that classifies every database
guard and insists the ones that matter have deliberate-breakage coverage. It was demanding of others
what it did not have. It does now.

Two of the five checks defend its **escape hatches** — the ways a person can legitimately say "this
one is exempt". An escape hatch that silently stops working is worse than none, because people plan
around it and only find out when the plan fails.

Debt drops from 16 to 15. Ten of the original twenty-one now covered or resolved.
<!--tech-->
`scripts/mutations/check-guard-coverage.json` — 5 mutations against `evaluate()`.
`EXPECTED_MUTATIONS` 232 → 237; `MANIFEST_BASELINE` 16 → 15, same commit. Contract (1) fixed first.

| # | Mutation | Red via |
|---|---|---|
| 1 | UNCLASSIFIED sweep dropped | `a guard in the schema but not classified is caught` |
| 2 | STALE sweep dropped | `a classified guard no longer in the schema is STALE` |
| 3 | UNJUSTIFIED check dropped | `a SEQUENCE guard with no reconciliation note is UNJUSTIFIED` |
| 4 | `COVERED_BY` needs only ONE token | `COVERED_BY requires EVERY listed token, not just one` |
| 5 | `MUTATION_EXEMPT` stops working | `MUTATION_EXEMPT suppresses only the mutation requirement` |

⭐ **4 and 5 cover the two escape hatches.** `COVERED_BY` lets a differently-named mutation label
satisfy a guard; `MUTATION_EXEMPT` waives the mutation requirement entirely. Both are deliberate
concessions, and the suite's own comment says it plainly: *"the two escape hatches must actually
work, or people will stop trusting them."* Mutation 4 is the sharper one — narrowing `for token in
wanted` to `wanted[:1]` means a guard listing two required tokens is satisfied by one, so coverage
looks complete while half is missing.

⚠ Checked explicitly this round: the inventory case compares `sorted(EXPECTED_MUTATIONS)`, so the
new name's **position** matters, not just its presence. That cost a red case two rounds ago; asserted
before running this time.

Verified: control green on the full tree, 5/5 red via the case each names. Real harness:
**16 files, 237 mutations, 0 survivors.** 189/189; `check-selftest-counts` 28 verified by running.

## 2026-09-07
The guard that insists every check can fail is now proven able to fail itself.

Seventh of these. This one enforces the rule that a checkbox must say what observation would make it
*fail* — otherwise it is a wish, not a gate. Its own five checks now include the one that matters
most: that an item ticked without saying **which build it was verified against** gets reported rather
than quietly waved through.

The same trap as two rounds ago recurred and was caught the same way: deleting a guard clause made
the program crash instead of reporting a failure, and a crash proves nothing about which check was
watching.

Debt drops from 15 to 14 — two thirds of the original twenty-one now done.
<!--tech-->
`scripts/mutations/check-gate-falsifiability.json` — 5 mutations against `find_gate_defects`.
`EXPECTED_MUTATIONS` 237 → 242; `MANIFEST_BASELINE` 15 → 14, same commit.

**Contract (1) fixed at BOTH print sites**, and the multi-line form collapsed to one line: it printed
`FAIL {name}` + indented `expected`/`got` continuation lines. No bracket, so the parser could not see
it — and the detail sat on lines the parser never inspects anyway. Now
`[FAIL] {name}: got {got!r} want {expected!r}`.

| # | Mutation | Red via |
|---|---|---|
| 1 | `unversioned_tick` finding renamed | `a tick with no VERIFIED AGAINST is reported, never silently skipped` |
| 2 | staleness compares `<=` | `a tick verified against the current release is clean` |
| 3 | ticked items no longer skipped for falsifiers | `ticked items are out of scope` |
| 4 | investigation phrasing loses its diagnosis | `investigation phrasing is called out specifically` |
| 5 | unknown npm scripts stop being flagged | `an unknown npm script is flagged` |

⭐ **Mutation 1 covers the fail-open the whole script exists to prevent.** Its own comment says it:
*"NOT silently skipped. Saying 'nothing is stale' while being unable to judge most items is the
fail-open this whole exercise is about."*

⚠ **Mutation 1 had to be WEAKENED — second time this session.** Removing `if m is None:` let the
`elif` call `m.group(1)` on `None` and raise `AttributeError`: red suite, **zero** `[FAIL]` lines,
nothing able to say which case was watching. Renaming the finding kind reddens exactly one case.
**A crash is not a kill**, and guard clauses are exactly where that trap lives.

Verified: control green on the full tree, 5/5 red via the case each names. Real harness:
**17 files, 242 mutations, 0 survivors.** 189/189; `check-selftest-counts` 28 verified by running.

## 2026-09-07
The guard that keeps every document pointing at a named goal is covered — one check per rule it enforces.

Eighth of these, and the tidiest: this guard has five numbered rules and now has exactly five
deliberate-breakage checks, one per rule. Nothing needed weakening or retrying.

Debt drops from 14 to 13. Eight of the original twenty-one done, and the pace is now limited by
reading each guard carefully rather than by anything going wrong.
<!--tech-->
`scripts/mutations/check-anchors.json` — 5 mutations against `audit()`, one per numbered rule.
`EXPECTED_MUTATIONS` 242 → 247; `MANIFEST_BASELINE` 14 → 13, same commit. Contract (1) fixed first
(`✓`/`✗`).

| Rule | Mutation | Red via |
|---|---|---|
| R2 | registry membership unchecked | `R2 unregistered anchor caught` |
| R3 | any ADR number accepted | `R3 dangling ADR caught` |
| R4 | unclaimed-anchor sweep dropped | `R4 unclaimed registry anchor caught` |
| R5 | ROOTS key may sit outside the registry | `R5 ROOTS key outside the registry caught` |
| R6 | the header floor never breaches | `R6 floor breach caught` |

⭐ **R5 and R6 are the two worth naming.** R5 enforces *one vocabulary, not two* — a `ROOTS` key in
`gen-backlog-page.py` that is not a registry anchor means the project has grown a second naming
scheme for the same concept. R6 is a **floor**: it fires when the number of documents carrying a
valid anchor header drops, so silently deleting headers is caught rather than read as "nothing to
check". A floor with no test is a number nobody has watched move.

Verified: control green on the full tree, 5/5 red via the case each names, no extras. Real harness:
**18 files, 247 mutations, 0 survivors.** 189/189; `check-anchors` itself `rc=0` against the live
registry (10 anchors, all claimed).

## 2026-09-07
Four guards had no safety-net coverage because the test harness was copying too little of the project for their tests to run at all.
The harness proves a guard's tests are real by breaking the guard on purpose and checking the tests notice. It does that inside a throwaway copy of the project — and that copy held only the `scripts/` folder. Four guards whose subject lives elsewhere (a database migration, a spec folder, a TypeScript helper) could not run there at all, so they were left uncovered. The copy now includes what they need. Nothing else changed: all eighteen already-covered guards still pass in the wider copy.
<!--tech-->
`scripts/check-plan-code.py` — new `HARNESS_TREE` tuple and `stage_tree()`; `mutate_delivered` stages scripts + supabase + docs + node_modules/typescript instead of `copytree(root / "scripts")` alone. Self-test 189 → 194: list completeness, complete stage, every entry arrives, per-entry CANNOT RUN, and the message names the path rather than blaming the guard. `_mini` scaffolds every entry by iterating the tuple, so adding one there cannot leave nine cases red here.

MEASURED in a scripts-only tree, 2026-09-07: `check-anon-exposure` rc=2 before case 1 (concealing all 74), `check-function-revokes` 15/16, `check-storage-grant-pin` aborted at 1/2 (it has 6), `check-paid-caller-arrival` 12/32. In the widened tree: 74/74, 16/16, 6/6. The fourth needed `node_modules/typescript` as well — `ts-comment-spans.mjs` imports typescript and `:177` refuses to fall back, deliberately.

WHY WIDENING, NOT FIXTURES: `check-function-revokes`' one failing case is *"the real migrations directory is non-empty (else this gate is vacuous)"* and `check-storage-grant-pin`'s is *"policy is extractable from the migration"*. Both assert something about the real repo, so a fixture turns both into tautologies. And the scripts-only copy was never a containment boundary — `copytree` yields a COPY; the boundary is `child_env`'s `$HOME` redirect, which is unchanged.

Controls 18/18 green in the widened tree; `check-docs`, `check-ratchet-contract`, `check-guard-coverage`, `check-selftest-counts` all green. Unblocks R4 manifest debt 13 → 9.

## 2026-09-07 [needs-you]
Two decisions about the comprehensibility suite are waiting on you, and goal 3 cannot be finished without them.
First — is the comprehensibility suite an official deliverable of this project? It is seven page-producers and forty-three built pages, and nowhere does the project actually say it is one. Most of it therefore has no declared goal, and the check that exists to catch exactly that cannot see the gap.
Second — is publishing it to the marketplace still the plan? If it is, then being usable outside this repo stops being a nicety and becomes something that blocks release.
<!--tech-->
Both are recorded in `docs/backlog.md` row 89, which states them as the user's call and deliberately does not act on them.

(1) A deliverable declaration's home is `docs/anchors.md`. Of its 10 anchors exactly one touches comprehension — `status-visibility`, scoped to *"a person who was AWAY"* — which covers `brief` and the three hook-regenerated pages but not `explain-diff`, `explain-topic` or `explain-findings`, all of which serve a human who is PRESENT. None of the four skill files declares an anchor at all, and `check-anchors` cannot see this because it enforces declarations on specs and plans, not on skills.

(2) Marketplace publication is outward-facing and irreversible, so it is a human gate. Coupling measured in row 89: `shared/explainer-delivery.md` has **0** project-specific references, `explain-topic` and `explain-findings` **1** each, and `brief/SKILL.md` **9** — all of them step 1's ground-truth command list. The generalization problem is concentrated in one file, which `brief`'s own *Known gaps* section already confesses.

## 2026-09-07 [resolved: 2026-09-07/11]
The comprehensibility suite is now written down as a deliverable of this project, and as one that is meant to ship.
You had said both of these before — that the suite is a main deliverable, and that you planned to publish it to a marketplace — and neither had ever been recorded anywhere. They are now in the file that indexes the project's second deliverable, so a future session reads them instead of rediscovering them. The practical consequence: working outside this repo stops being a nicety for those nine files and becomes something that blocks release.
One thing is deliberately still open, and is flagged rather than quietly closed. Three of the four pages serve a person who is *present* and trying to understand something, and the project's registry of goals has no name for that — only a name for the person who was *away*. The missing name is owed, but allocating it today would turn a silent gap into a failing check, because the registry refuses a name no document uses yet. It lands with the design work.
<!--tech-->
`docs/portable-practices.md` — the opening two-deliverable statement now carries a block naming the suite (9 files / 3,599 lines, enumerated in backlog #89, not recalled) as part of deliverable 2, with marketplace publication as the stated target. That promotes the file's own filter 2 (*project-independent*) from an entry-quality bar to a release blocker for the suite. Measured coupling, unchanged from #89: `shared/explainer-delivery.md` 0 project-specific references, `explain-topic` and `explain-findings` 1 each, `brief/SKILL.md` 9 — all in step 1's ground-truth command list.

`docs/backlog.md` row 89 — records (a) YES and (b) YES with reasoning, and (c) NOT TAKEN. (c) was fork-validation permission for the design pass; declined for now because questions (1)-(5) have no written draft, so spawned agents would have nothing to falsify. Trigger stated explicitly: the first draft of the design pass. Row stays 🟡 OPEN — the engineering half is untouched.

⛔ The second anchor is owed and deliberately NOT allocated: `check-anchors.py` R4 fails an anchor claimed by no document, and the claimant is #89's design pass. Allocating now trades an invisible gap for a red gate. Must not be closed by widening `status-visibility` — one anchor for two different readers is the one-name-two-meanings defect this repo runs a guard for.

⚠ Entry 2026-09-07/11 was malformed: the page flagged it *"no decision — add a `**Decide:**` line with at least two options"*. The ask-tray guard caught it and got louder, as designed. Recorded because the author did not notice; the page did.

## 2026-09-07
The storage-grant guard now has a safety net, and writing it found one of its six checks was testing nothing at all.
This guard watches a database permission that a money-path protection depends on: if the permission is ever narrowed, serving a summary could start paying twice. It had six checks. Proving each one actually works — by breaking the guard on purpose, six different ways, and confirming the right check complains each time — turned up a check that compared a value to itself. It read as the check that pins *what* gets measured, and no possible bug could have made it fail. It now edits the file and re-reads it, which is what its own comment always claimed it did.
<!--tech-->
`scripts/mutations/check-storage-grant-pin.json` — 6 mutations, one per self-test case, all attributed via the case each names. Targets are the pure functions: `POLICY_RE`, `normalise`, `digest`, `extract_policy`.

⭐ **Case 5 was vacuous.** It read `digest(stmt) == digest(stmt + "")` — a string compared to itself, true for every possible implementation of `digest`, `normalise` and `extract_policy`. No mutation could kill it. Now `digest(extract_policy("-- an unrelated comment\n" + real) or "") == digest(stmt)`, which fails if extraction ever widens from the statement to the whole file. Found by asking what would kill each case *before* writing mutations, which is the only step that could have found it.

⚠ **One mutation SURVIVED first time and the hypothesis was wrong, not the coverage.** `re.sub(r"\s+"," ")` → `re.sub(r" +"," ")` left case 2 green: collapsing *runs* of spaces maps both `"\n  "` and `"\n   "` to `"\n "`, so reflow stays equal. Replaced with `re.sub(r"\n+"," ")` — collapsing the wrong character class — which reddens case 2 alone. Measured, not reasoned: the real statement has 3 newlines and 3 double-spaces.

Registration, all four numbers in one commit because the ratchet is an exact match: `EXPECTED_MUTATIONS["scripts/check-storage-grant-pin.py"] = 6`; the live sum 247 → 253; the guard added to the sorted want-list; `MANIFEST_BASELINE` 13 → 12. `check-plan-code --self-test` 194/194; `check-ratchet-contract` at baseline, not growing.

First of the four guards PR #247 made stageable. Remaining: `check-function-revokes` (16 cases), `check-paid-caller-arrival` (32), `check-anon-exposure` (74).

## 2026-09-07
The revoke guard now has a safety net, and writing it found two ways the guard was harder to trust than it looked.
This guard checks that every new database function explicitly withdraws the permission Postgres hands out by default — miss one and it becomes callable by anyone on the internet. Proving its sixteen checks actually work turned up two problems. First, when a check failed it announced this in a format the mutation harness cannot read, so a broken guard would have looked like a guard nobody had tested rather than a broken one. Second, the checks were quietly running against a private copy of the file-ordering logic rather than the real one, so the function that decides ordering was exercised by nothing at all.
<!--tech-->
`scripts/mutations/check-function-revokes.json` — 6 mutations, all attributed via the case each names. Targets: the `seen`/replacement branch in `audit()`, the DROP discard, the grantee filter, the REVOKE pattern's `public.` tolerance, `migrations()` ordering, and the `MIGRATIONS` path itself.

⚠ **CONTRACT (1) WAS VIOLATED and that is why the first run scored 0/6.** The suite printed `❌  {label}` — no `[FAIL] ` prefix, no `: got ` — so every mutation reddened it with **zero parseable failure lines**, reported as CRASH. `check-plan-code` attributes kills via `.strip()[7:].rsplit(": got ", 1)[0]`; with nothing to parse, a real kill and no coverage look identical. Fixed first, then re-verified 6/6. The rule binds only once a manifest points at the file, which is why it sat latent.

⭐ **`migrations()` was covered by NOTHING.** The self-test's `tree()` helper ended `return sorted(d.glob("*.sql"))` — a second copy of `migrations()` — and every one of the sixteen cases calls `audit(tree({...}))`. The case named *"ordering is by FILENAME, so 0002 sees 0001's function"* therefore tested the fixture's private sort, not the delivered function whose ordering `audit()` depends on. `tree()` now delegates to `migrations(d)`, so a mutation there reaches the cases.

Registration: `EXPECTED_MUTATIONS["scripts/check-function-revokes.py"] = 6`; live sum 253 → 259; want-list; `MANIFEST_BASELINE` 12 → 11. 194/194, ratchet at baseline, 16/16.

## 2026-09-07
Every one of the eleven guards still owing a safety net announces its failures in a format the checker cannot read — so the next ten attempts would each have failed the same way the last one did.
When a guard is put under test, the test breaks it on purpose and checks the guard complains. That only works if the complaint is written in the one format the checking tool parses. The guard finished today turned out to use a different format, which made all six of its tests look like they had crashed rather than worked. Rather than fix that one and move on, the same question was asked of every guard still waiting: all eleven have the same problem. Fixing it is a prerequisite for the remaining work, and it is not a find-and-replace — the eleven use at least four different formats between them.
<!--tech-->
⭐ **MEASURED 2026-09-07, with a control.** Contract (1) — a failure line must start with `[FAIL] ` and contain `: got ` — is violated by all **eleven** remaining unmanifested guards. Each has **zero** `[FAIL]` literals: `check-paid-caller-arrival`, `check-anon-exposure`, `check-ci-watched`, `check-docs`, `check-plan-task-order`, `check-producer-enumeration`, `check-review-rounds`, `check-roadmap-consistency`, `check-test-counts`, `check-catalog-coverage`, `check-live-schema`.

**CONTROLLED, because a uniform zero is the shape that is usually a broken measurement:** five already-manifested guards — `check-anchors`, `check-sentinel-meanings`, `check-storage-grant-pin`, `check-guard-coverage`, `check-explainer-delivery` — each have exactly **3**. So the zero is the world, not the grep.

**CONSEQUENCE.** `check-plan-code` attributes a kill via `.strip()[7:].rsplit(": got ", 1)[0]`. With no parseable line, a mutation that genuinely kills and a guard with no coverage produce the same observation — reported as CRASH. This is precisely what made `check-function-revokes` score 0/6 on its first verify run (PR #250). The rule binds only once a manifest points at a file, which is why eleven violations sat latent.

⚠ **NOT MECHANICAL — do not script it.** The eleven use at least four printer shapes: `{'✓' if ok else '✗'} {name}` (`check-anon-exposure`, `check-docs`), `{'PASS' if ok else 'FAIL'}  {name}` (`check-ci-watched`, `check-plan-task-order`), `{'ok  ' if ok else 'FAIL'} {name:<38} flagged=… expected=…` (`check-producer-enumeration`), plus per-case bespoke forms (`check-paid-caller-arrival` prints `✗ {name} — wanted exit X, got Y`). A uniform substitution would corrupt the ones that differ. Each also has to keep printing `passed` on a green run — contract (3).

Debt now **11** (PRs #249, #250 merged). Remaining: 2 of PR #247's four (`check-paid-caller-arrival` 32 cases, `check-anon-exposure` 74) plus 9 hermetic.

## 2026-09-07
All eleven guards still owing a safety net can now be tested at all — and proving it needed breaking each one on purpose, because a passing test never runs the code that reports failure.
Yesterday's finding was that every remaining guard announces its failures in a format the checking tool cannot read, which makes a genuine failure and a guard nobody has tested look identical. All eleven are now fixed. The fix could not be verified by running them, because they all pass — and a passing run never executes the code that prints a failure. So each was forced to fail on purpose and the resulting output was fed through the real parser: 390 failure lines across the eleven, every one readable.
<!--tech-->
Contract (1) — a failure line starts with `[FAIL] ` and contains `: got ` — now satisfied by all eleven: `check-anon-exposure`, `check-docs`, `check-ci-watched`, `check-plan-task-order`, `check-producer-enumeration`, `check-paid-caller-arrival`, `check-review-rounds`, `check-catalog-coverage`, `check-live-schema`, `check-test-counts`, `check-roadmap-consistency`.

⭐ **VERIFIED BY FORCING, NOT BY PASSING.** For each guard, its printer's success branch was disabled in a staged copy and the output parsed with `check-plan-code`'s exact rule — `line.strip()[7:].rsplit(": got ", 1)[0]`. Result: **390 parseable case lines, 11/11 guards OK**, every extracted name non-empty. Running the suites green proves only contract (3); it says nothing about a branch it never enters.

⚠ **`check-producer-enumeration` had FOUR printers, not one, and the first sweep fixed one.** The survey that found "one printer per guard" used `grep … | head -3`, and the truncation hid the other three. Caught only because the forced-failure check reported **0 parseable lines** for that guard while the other ten reported plenty. A static token count would have said "conforming=1" and passed. This is the repo's own recorded lesson — grep the concept **without `head`** — and it cost a wrong first answer here.

All 11 suites still green and still print `passed` (contract 3): 74, 13, 22, 16, 11, 32, 27, 15, 117, 27, 26. `check-selftest-counts` verifies all 28 declared counts by running them; `check-docs`, `check-guard-coverage`, `check-ratchet-contract`, `check-plan-code` (194/194) green; ratchet at baseline 11.

This unblocks every remaining manifest. Debt is unchanged at **11** — this PR adds no coverage, it makes coverage measurable.

## 2026-09-07
The guard that watches the money trigger now has a safety net, and two of the six tests written for it were wrong in ways only running them could show.
This is the guard that fires when real code first calls the function that spends money. Six deliberate breakages were written to prove its thirty-two checks work; four behaved as predicted and two did not. One breakage changed nothing at all, because the check it was aimed at is actually caught by a different part of the code than assumed. The other made the test crash rather than fail, which reads as "no coverage" rather than "caught it". Both were replaced with breakages that do what was claimed.
<!--tech-->
`scripts/mutations/check-paid-caller-arrival.json` — 6 mutations, all attributed via the case each names, over a green control (32/32) in the staged tree. Targets are all in the pure halves: the per-occurrence line scan (`col = line.find(SYMBOL, col + len(SYMBOL))` — the r12 blocking defect), the comment/code bucket assignment, `strip_sql_noise`'s string blanker, its block-comment NESTING depth, its line-comment blanker, and `ledger_net_effect`'s file ordering.

⚠ **TWO FIRST ATTEMPTS WERE WRONG, and the harness distinguished the two failure modes.**
1. Disabling the dollar-quote branch **SURVIVED**. The case named *"…nor a dollar-quoted body"* is in fact killed by the **string** branch — its fixture is `do $$ begin raise notice 'create function record_artifact'; end $$;`, and the create sits inside single quotes, which the string lexer blanks regardless. The case's name attributes it to a mechanism that is not what makes it pass.
2. Removing `"scripts"` from `PRODUCTION_DIRS` **CRASHED** with 0 `[FAIL]` lines. The self-test mkdirs its fixture tree *from that same tuple*, so the case then writes to a directory that no longer exists. A crash is not a kill — the harness reports it separately for exactly this reason.

Replaced with: the SQL line-comment blanker (kills *"a comment cannot resurrect a dropped symbol (r12 H1)"*) and reversed ledger ordering (kills *"a LATER migration dropping the symbol is CANNOT RUN (r10 H3)"*).

Registration: `EXPECTED_MUTATIONS["scripts/check-paid-caller-arrival.py"] = 6`; live sum 259 → 265; sorted want-list; `MANIFEST_BASELINE` 11 → 10. 194/194; ratchet at baseline; 32/32.

## 2026-09-07
A fourth hidden rule turned up: the louder a guard failed, the less its failure counted.
CI rejected the previous entry's work, saying two of the six deliberate breakages had not been caught. They had been — the right check complained in both cases. The problem was the exit code. The checking tool treats "exactly 1" as the signal for a caught breakage, and this one guard reported the *number* of things that broke instead. So a breakage that failed one check reported 1 and counted; a breakage that failed sixteen reported 16 and was recorded as not caught at all. Every other guard in the project already reported 0 or 1; this one was alone.
<!--tech-->
⭐ **CONTRACT (4), and it is a fourth latent one.** `run_mutations` decides a kill with `caught = rc == 1` (`check-plan-code.py:998`) — exactly one, not non-zero. `check-paid-caller-arrival.self_test()` ended `return bad`, the COUNT of failing cases.

MEASURED: of six mutations, the four that broke exactly one case exited 1 and were caught; the two that broke **16** and **7** cases exited 16 and 7 and were recorded as SURVIVORS — while their named case sat plainly in the red list, confirmed by membership test. Fixed to `return 1 if bad else 0`. Real instrument now: **verdicts=6, survivors=0**.

**CLASS CHECKED, and it is an instance:** all twelve other guards already return `1 if failed else 0` or `0 if passed == len(cases) else 1`. This file was the only one returning a count.

⚠⚠ **THE SCRATCHPAD VERIFY HARNESS GAVE A FALSE GREEN and is retired for verdicts.** It reported 6/6 by parsing `[FAIL]` lines and ignoring the exit code entirely — a second implementation of `check-plan-code`'s attribution rule that drifted from it. That is the defect the mutation harness exists to catch, reintroduced one layer out, in the tool used to check the tool. Future manifests are verified by calling `check-plan-code`'s own `run_mutations`, not a copy of its logic. (Guards in PRs #249 and #250 are unaffected — both passed real CI.)

Like contracts (1)–(3), this binds only once a manifest first points at a file, which is why it sat latent through every previous run of this guard.

## 2026-09-07
The guard that checks each documented value names the right number of producers now has a safety net.
Five deliberate breakages, each caught by the check it was aimed at, first time — no wrong hypotheses on this one. All five were verified by calling the real checking tool rather than a lookalike, which is the change of habit the previous entry paid for.
<!--tech-->
`scripts/mutations/check-producer-enumeration.json` — 5 mutations, all attributed, over a green 11/11 control. Targets are all in the pure rules: the ternary probe's `(?!\.)` optional-chain exclusion, `bare_alias`'s `ALIAS_RHS.fullmatch` gate, `ALIAS_RHS`'s `+` repeat quantifier (so a deep path stops matching), and the `\|\|` and `\?\?` branch patterns.

⭐ **Verified through `check-plan-code`'s OWN `run_mutations`**, on a staged tree, not through the retired scratchpad copy: `verdicts=5 survivors=0`. All four output contracts checked BEFORE choosing targets, including the newly-found contract (4) — this guard already returned `1 if failures else 0`.

Registration: `EXPECTED_MUTATIONS["scripts/check-producer-enumeration.py"] = 5`; live sum 265 → 270; sorted want-list; `MANIFEST_BASELINE` 10 → 9.

## 2026-09-07
The guard that keeps the backlog rendering as a real table now has a safety net.
Four deliberate breakages, each caught by the check aimed at it, first time. This guard exists because the backlog once silently stopped being a table on GitHub — nineteen rows rendered as raw pipe-delimited text — and because a row missing four of its six columns caused two items to be marked closed that were not.
<!--tech-->
`scripts/mutations/check-docs.json` — 4 mutations, all attributed, over a green 13/13 control, verified through `check-plan-code`'s own `run_mutations` (`verdicts=4 survivors=0`). Targets are all in `backlog_shape_errors`, the pure half: `CELL_SPLIT`'s `(?<!\\)` escaped-pipe lookbehind, the `len(cells) != expected` column comparison, the delimiter-row `count("-") >= 3` threshold, and the `prev_was_row` flag that a blank-line split depends on.

All four output contracts checked before choosing targets; this guard already returned `1 if failed else 0`.

Registration: `EXPECTED_MUTATIONS["scripts/check-docs.py"] = 4`; live sum 270 → 274; sorted want-list; `MANIFEST_BASELINE` 9 → 8.

## 2026-09-07
The guard that stops the database check from quietly narrowing now has a safety net — and writing it found two ways the guard could have gone wrong in silence.
Seven deliberate breakages, all caught first time. Five of them confirm rules the guard's fifteen existing checks already covered. The other two are genuine gaps, and both are the same shape: a claim about coverage that nothing ever ran. First, when this guard cannot read the file it needs, one small edit would have made it report "no problems" instead of "I could not run" — the exact failure it is supposed to prevent in others. Second, one rule about database privileges is written down twice in the same file, and nothing checked the two copies still agree; the check that looked like it did was only searching for a word in the text, so either copy could have quietly changed while everything stayed green.
<!--tech-->
`scripts/mutations/check-catalog-coverage.json` — 7 mutations, all attributed, over a green 15/15 control, verified through `check-plan-code`'s own `run_mutations` (`verdicts=7 survivors=0`). All four output contracts checked BEFORE choosing targets; this guard already satisfied all four, including contract (4)'s `return 1 if failures else 0`.

**GAP 1 — a fail-open on the CANNOT-RUN path.** `_moved_problems_for`'s unreadable-harness branch was driven by NO case, so `return []` in its place was caught by nothing. That is *"cannot run" reported as clean* — inside the one script whose whole job is to stop "covered elsewhere" claims going unverified. Fixed by a `harness` seam so `--self-test` can pass `""`, plus two cases: the result is non-empty, **and** it says `TREAT THIS AS NOT RUN`. Both are load-bearing — one mutation kills each.

**GAP 2 — one rule, two copies, no agreement check.** `^(relacl|proacl|attacl|typacl)$` appears in both `EXCLUDED` (line 92) and `MOVED_COVERAGE` (line 177). The case that appeared to bind them, `any("relacl" in pat …)`, is a **substring test on the pattern text**: it passes as long as those six letters appear somewhere, so either copy could narrow and leave a column excluded here and claimed by nobody there. New case asserts every `MOVED_COVERAGE` pattern is one `EXCLUDED` actually uses — which fails in *both* directions of drift.

Self-test 15 → 18 cases, declared in the docstring (this guard is in `check-selftest-counts.POPULATION`, so an undeclared count is itself a red gate).

Registration: `EXPECTED_MUTATIONS["scripts/check-catalog-coverage.py"] = 7`; live sum 274 → 281; sorted want-list; `MANIFEST_BASELINE` 8 → 7 — read off `check-ratchet-contract.py`'s own output, never computed.

## 2026-09-07
The guard that catches a plan using something before it has been built now has a safety net — and five of its sixteen existing checks turned out to be untestable.
Nine deliberate breakages, all caught. The striking part is what writing them exposed: five checks were passing for a reason other than the one their name gives. Each one described a rule, but the example it used was filtered out earlier by a *different* rule, so the rule under test was never reached. Delete the thing the check is named for and it still says PASS. Nothing was broken — the guard works — but five of its sixteen assurances were worth nothing, and only running a deliberate breakage against them could tell. Two more of my own tools failed the same way during this work, and both are now fixed.
<!--tech-->
`scripts/mutations/check-plan-task-order.json` — 9 mutations, all attributed, over a green 16/16 control, verified through `check-plan-code`'s own `run_mutations` (`caught=9 survivors=0`). All four output contracts already held; no repair needed.

⭐ **FIVE UNFALSIFIABLE CASES, one shape: the fixture used an input a DIFFERENT rule filters first.** Each was MEASURED by disabling the named rule and watching the case stay green — not inferred by reading.

| Case | Named mechanism | What actually satisfied it |
|---|---|---|
| file paths name no symbol | `"/" in span` | the lowercase-prose rule — `lib/…` is lowercase |
| file:line citations name no symbol | the citation regex | same rule — `parse.ts:42` is lowercase |
| a non-Produces bullet is not a Produces | the `else: mode = None` reset | `epsilon` is lowercase, dropped whatever the mode |
| un-indented prose ends the block | the prose-termination branch | the preceding bullet had already reset the mode |
| forward reference detected | `all(t > num for t in owners)` | every fixture symbol had exactly ONE producer, so `all`/`any` and `>`/`>=` agree |

Fixes: capitalise the fixture symbols (`Epsilon`, `Omega`, `MyModule/index.ts`, `Parse.ts:42`) so the named rule is the thing reached; add prose directly after a LIVE `- Produces:`; add two multi-producer ordering cases. **16 → 21 cases**, declared in the docstring (pinned at `check-selftest-counts.py:98`).

⚠ **TWO OF MY OWN INSTRUMENTS FAILED THE SAME WAY, both caught by measurement, both fixed:**
1. The manifest generator asserted each anchor was unique **in the file** but not **across mutations**. Two mutations disabling opposite halves of one `if` shared an anchor; `load_manifests` refuses a duplicate, dropped one, and the run reported **8 of 9 with no error at the call site**. Now checked, and the anchors are distinct substrings.
2. My first anchor for the ordering predicate collided with the self-test **comment that quotes it** — caught by the generator on its first run, which is what that check is for.

Registration: `EXPECTED_MUTATIONS["scripts/check-plan-task-order.py"] = 9`; live sum 281 → 290; sorted want-list (⚠ a red caught my first insert — `check-plan-progress` sorts before `check-plan-task-order`); `MANIFEST_BASELINE` 7 → 6, read off the tool.

## 2026-09-08
The guard that notices when CI is running and nobody is watching now has a safety net — and the instructions for writing these safety nets turned out to be wrong.
Nine deliberate breakages, all caught. Two things came out of it. First, one of the guard's own checks was passing for the wrong reason: it claimed to prove that upper/lower case does not matter, but the example it used would have been handled correctly anyway by a different rule, so the case-handling could have been deleted without the check noticing. Second, and more consequential: the written instructions for how these safety nets declare *which* check must fail said one thing, and the tool that reads them does another — it requires the exact name, not a fragment. The instructions had been wrong since the day the tool was tightened. I wrote four declarations against the wrong sentence before the tool refused them. Both the sentence and my own tooling are now fixed, so the next person cannot repeat it.
<!--tech-->
`scripts/mutations/check-ci-watched.json` — 9 mutations, all attributed, over a green 22/22 control, verified through `check-plan-code`'s own `run_mutations` (`caught=9 survivors=0`). All four output contracts already held.

⭐ **STALE DOCSTRING ON THE RULE THAT DECIDES WHETHER COVERAGE COUNTS.** `check-plan-code.py:79` said `expect` is *"a substring of the self-test case name"*. `:1060` implements `w == f` — **exact equality** — and has since round 6, whose own comment says why: *"an `expect` naming a completely unrelated case, or a mere fragment of a name, still certified the mutation."* The round-5 sentence survived the round-6 fix. Four expects here were written against it and were rejected by the real instrument. Docstring corrected; the round-6 rationale is now stated in it.

**Guard finding:** `state matching is case-insensitive` used `"pending"` — which the **unknown-state fallback** classifies as unresolved anyway, so `.upper()` could be deleted and the case stayed green. Only the resolved direction can see the folding happen; added `lowercase SUCCESS is still resolved`. **22 → 23 cases.**

⚠ **NOT a mutation target, and now commented as such:** `state in UNRESOLVED` is disjoint from the resolved set, so it always implies the second disjunct and **no input can distinguish it**. It is defensive (it catches a future edit that moves a pending state into the resolved list), not decisive. Mutating it would be unkillable-by-construction — the `check-storage-grant-pin` case-5 shape.

**My generator now harvests the real case names** from a green `--self-test` run and refuses any `expect` that is not an exact match, printing the near-miss it found. It caught all four of mine before a five-minute sweep could.

Registration: `EXPECTED_MUTATIONS["scripts/check-ci-watched.py"] = 9`; live sum 290 → 299; sorted want-list; `MANIFEST_BASELINE` 6 → 5. ⚠ Second want-list mis-sort in two PRs (`check-catalog-coverage` sorts before `check-ci-watched`) — the position is now DERIVED and the literal asserted sorted, rather than placed by eye.

## 2026-09-08
The guard that checks the roadmap's "what's next" section against its own checkboxes now has a safety net, and it had one rule written down in two places.
Twelve deliberate breakages, all caught. Two things worth knowing. The rule for "which items are still open" existed as two identical copies — one deciding whether the check fails, the other deciding the sentence it prints when it passes. Nothing kept them in step, so a future edit to one would have let the check fail while announcing that everything was finished. They are now one shared rule. Separately, one check could never have failed: it was meant to prove that a range like "B1 to B5" covers its last member, but both ends of such a range are recognised on their own anyway, so the part being tested was never actually used. A range written with the prefix on one side only is the shape that tests it, and that case now exists.
<!--tech-->
`scripts/mutations/check-roadmap-consistency.json` — 12 mutations, all attributed, over a green 26/26 control, verified through `check-plan-code`'s own `run_mutations` (`caught=12 survivors=0`). All four output contracts already held.

⭐ **ONE RULE, TWO OWNERS.** `sorted(i for i, m in marks.items() if m in (" ", "~"))` appeared at `:319` (the **verdict** — does `no_coverage` fire?) and `:494` (the **explanation** `main()` prints). Byte-identical, with nothing holding them that way: drift would fail the check while printing *"every tracked checkbox is ticked"*. Extracted to `open_items()`. Safe to share because the whole rule **is** that one expression — the `a-shared-function-can-hold-half-a-contract` hazard needs a clause one caller has and the other doesn't. Bonus: the self-test cases for the verdict now also protect the printed reason, which `main()` otherwise puts out of their reach.

**Unfalsifiable case:** `range(a, b + 1)` → `range(a, b)` survived *every* range case. `B1–B5` and `C1–C3` have both endpoints matched by `ident_re` independently, so expansion only ever supplied the **interior**. Added `a range written B1-5 with the prefix on one side still covers the TOP member` — measured: it is the only case that mutation kills. **26 → 27 cases.**

**Also:** the guard printed nothing for passing cases, so its case names were invisible to any outside tool and an `expect` could only be hand-transcribed. It now prints `PASS <name>` like every other guard in the suite, and my generator harvests those names to refuse an inexact `expect`.

Registration: `EXPECTED_MUTATIONS["scripts/check-roadmap-consistency.py"] = 12`; live sum 299 → 311; sorted want-list — position now **derived and asserted sorted** (27 entries), which is why there was no third mis-sort; `MANIFEST_BASELINE` 5 → 4.

## 2026-09-08
The guard that makes sure every review round has both of its halves now has a safety net, and two of its own checks were proving nothing.
Twelve deliberate breakages, all caught. The interesting part: two checks said "this pairs up correctly" by confirming that no complaint was raised — and if you delete the code that finds the files in the first place, no complaint is raised either. So the parts that locate review files, in both the old flat layout and the new per-writer folders, could each have been removed without either check noticing. They now also confirm the pair was actually *found*, not merely un-complained-about.
<!--tech-->
`scripts/mutations/check-review-rounds.json` — 12 mutations, all attributed, over a green 27/27 control, verified through `check-plan-code`'s own `run_mutations` (`caught=12 survivors=0`). All four output contracts already held.

⭐ **TWO VACUOUS ABSENCE-ASSERTIONS, one shape.** `both halves pass` and `halves in per-writer subdirectories pair normally` both assert `audit(d, set())[0] == []`. Delete `flat = sorted(reviews.glob("*.md"))` or `nested.extend(...)` and the audit finds **no files**, so it reports **no problems** — the same empty list. *"Nothing went wrong" satisfied by "nothing happened."* Both scans were therefore unguarded, in the guard whose entire job is noticing a missing half.

Fix: companion cases asserting `stats["rounds"] == 1` — the pair was **seen**. Measured: each is the only case its scan's mutation kills. **27 → 29 cases.**

The other ten cover the rules worth having: `gate_ran` is READ and never re-derived from `exit_code` (a second implementation of the wrapper's rule, which the docstring forbids); a `REVIEW GAP:` line still needs a reason; `verdicts/` is not scanned for halves; a basename filed in two layouts is REPORTED, not silently deduped.

Registration: `EXPECTED_MUTATIONS["scripts/check-review-rounds.py"] = 12`; live sum 311 → 323; sorted want-list (28 entries, position derived); `MANIFEST_BASELINE` 4 → 3. ⚠ The declared self-test count uses `--self-test # N cases` here, not the `--self-test  # N cases` spacing of its siblings; my first edit missed it and `check-selftest-counts` caught the drift — the outside observer doing its job.

## 2026-09-08
The guard that stops the roadmap claiming a test count the suite does not have now has a safety net.
Eleven deliberate breakages, all caught — but one of them only after a correction worth recording. I wrote a breakage meant to strip the "how to fix it" line out of an error message, and the check stayed green. The words I deleted were not the ones the check looks for: it looks for the command flag, which sits on the following line. The breakage *read* like the one the check names and touched something else entirely — the same trap this whole exercise keeps finding, this time in my own work rather than the code's.
<!--tech-->
`scripts/mutations/check-test-counts.json` — 11 mutations, all attributed, over a green 27/27 control, verified through `check-plan-code`'s own `run_mutations` (`caught=11 survivors=0`). All four output contracts already held.

⚠ **ONE SURVIVED FIRST, and the reason is the session's recurring shape.** The case is `the absent-file message names the command that produces it`, which asserts `"--outputFile=" in str(exc)`. My mutation removed `"no jest results at {path}. Produce one with\n"` — prose that *reads* like the guidance — while `--outputFile=` lives on the **next** f-string fragment. Retargeted to the fragment carrying the claim; the survivor is what told me, which is the harness earning its keep.

The other ten cover rules with real history: **ambiguity is cannot-run** (two `**N unit / M suites**` statements and the check cannot say which it read); a **failed** jest run raises rather than reporting counts from a world we are not in; the **staleness** check of task #144 (a three-day-old results file once reported a confident match); and `test_sources` globbing from the **config's own directory**, whose absence made the empty-inventory refusal unable to fire.

Also: the guard printed nothing per passing case, so its case names were invisible to any outside tool. It now prints `PASS <name>`.

Registration: `EXPECTED_MUTATIONS["scripts/check-test-counts.py"] = 11`; live sum 323 → 334; sorted want-list (29 entries, position derived); `MANIFEST_BASELINE` 3 → 2.

## 2026-09-08
The guard that stops logged-out visitors reaching data they should not see now has a safety net.
Thirteen deliberate breakages, all caught first time — no wrong guesses on this one. What it protects is worth stating plainly: this check derives, from the schema files themselves, which tables a signed-out visitor is allowed to read, and then verifies the live database agrees. Two of the breakages recreate real defects this guard has already been through, where the text-parsing was correct only for the exact spelling in front of it — an ordinary schema-qualified name, or a quoted role name, and the check would have decided a perfectly readable table was off-limits, or vice versa. Those are now held by executable tests rather than by a comment explaining what went wrong last time.
<!--tech-->
`scripts/mutations/check-anon-exposure.json` — 13 mutations, all attributed, over a green 74/74 control, verified through `check-plan-code`'s own `run_mutations` (`caught=13 survivors=0`). All four output contracts already held. **First-try, 13 for 13.**

Every target is in the PURE half — `_norm_ident`, `session_readable`, `derive_no_session_access`, `read_spec`, `m4_functions`, `m4_relations`, `justification_holds` — so the manifest needs no database.

⭐ **The two the guard already paid for, now covered rather than commented:**
- **r9 M1** — schema qualification unstripped: `public.video_artifacts` matches no manifest name, so an ordinary **readable** relation derives as **out of reach** and the cross-check refuses to run.
- **r9 M3** — the grantee side used a different normaliser from the relation side, so `to "anon"` matched nothing. The comment in the source calls this out as "instance-not-class"; both directions now have a mutation.

Also covered: `05_assert.sql` stays **excluded** from the corpus (2,500 lines of deliberately hostile SQL — the thing that attacks the contract, not the contract); views stay in the derived relation set; and all four arms of `justification_holds`, including that an **unknown** kind is never a justification.

Registration: `EXPECTED_MUTATIONS["scripts/check-anon-exposure.py"] = 13`; live sum 334 → 347; sorted want-list (30 entries, position derived); `MANIFEST_BASELINE` 2 → 1.

## 2026-09-08
The last guard is covered. Every safety check in this project now has a safety check of its own — the count of unprotected ones is zero.
Twelve deliberate breakages on the final guard, all caught, and one more real gap found on the way. This guard compares what is actually in the production database against what the project believes it put there. Last month it was taught to notice stray indexes, after one slipped through unseen — but the test proving it notices them was never written. Removing that capability again passed all one hundred and seventeen checks. It has a test now. That closes a run of twenty-one guards: the ones that were entirely unprotected are all done, and along the way roughly a dozen individual checks turned out to be unable to fail for the reason their name gave.
<!--tech-->
`scripts/mutations/check-live-schema.json` — 12 mutations, all attributed, over a green 117/117 control, verified through `check-plan-code`'s own `run_mutations` (`caught=12 survivors=0`).

⭐ **MEASURED GAP: `idx` had the fix but not the case.** It joined `ATTRIBUTABLE_KINDS` on 2026-08-28 because `create unique index rev_uq on video_artifacts (video_id)` **PASSED** — and no self-test case arrived with the fix. Removing `"idx"` from that tuple survived all 117 cases. The drift table is a loop over `(kind, extra)` pairs and simply had no INDEX row; it does now. **117 → 119 cases.**

The other targets are this file's own documented history, now executable rather than commented:
- **r5 B1** — absent mode matched `name@digest`, so every DRIFTED survivor was invisible: a hot-fixed guard function, or `record_artifact` drifted by one defaulted parameter, stays live on a database the gate certifies as M4-free.
- **r5 L2** — `_keys` matches every spelling, so an added argument cannot smuggle an ADR-0011 object past `forbidden`.
- **backlog 65** — present mode is `manifest <= live` **and** no unexpected object on an owned relation; the subset test alone catches removals and passes additions silently.
- the `accepted-additions.txt` exit, without which a legitimate later migration turns the gate permanently red with no remedy.

Registration: `EXPECTED_MUTATIONS["scripts/check-live-schema.py"] = 12`; live sum 347 → 359; sorted want-list (31 entries); **`MANIFEST_BASELINE` 1 → 0** — `check-ratchet-contract.py` now prints `ratchet contract OK` with zero violations, for the first time since the R4 rule was written.

## 2026-09-08
A design is drafted for how these explanation pages should be built — and checking its stated precondition found the earlier fix has never actually done its job.
The question backlog #89 asks: these pages exist to help you follow what is happening, they are not the work itself, so should an agent be building them inside the main conversation at all? The draft says: hand the expensive research and writing to a separate agent, but keep the final step — actually opening the page in a browser and checking it works — in the main thread. That is deliberate. Twice, defects were invisible in the source and only appeared when the page was run; a helper that skips that step reports success it has not earned. Keeping verification here also means the page cannot go out stale, because the one participant that cannot be out of date about this conversation is this conversation.

Along the way: a fix from four days ago was supposed to make every page save its own source alongside it, so a question asked tomorrow can be answered in the page. The code does that unconditionally. Across 47 files, exactly two sources exist — and both belong to the two pages that a hook regenerates, never to the ones an agent writes, which is the group the fix was for. One page written after the fix landed still has no source beside it. This needs closing before anything else here is built.
<!--tech-->
`docs/superpowers/specs/2026-09-08-observability-execution-mode-design.md` — **v1 DRAFT, nothing implemented.** Answers backlog #89's questions (1), (2), (3), (5). New anchor **`explanation-on-demand`** allocated (`check-anchors.py`: 11 registered, all claimed, floor 22 held).

⚠ **The anchor is NEW, not a widening.** `status-visibility` is scoped to *"a person who was AWAY"*; `explain-diff` / `explain-topic` / `explain-findings` serve someone who is HERE and chose the subject. One name for two readers is how a goal stops being falsifiable.

**MEASURED — #88's precondition is cleared in code, unproven in practice:** `frag_out.write_text` entered `brief-compose.py` at `65cd509e` (2026-09-04 15:28), unconditional. `~/explainers/` holds **47 files, 32 brief pages, 2 fragments** — and both fragments are `dashboard`/`goals`, the hook-regenerated Group B. **Zero brief fragments**, including a page written 2026-09-05 10:14, after the fix. #88's own falsifier still fails for every brief page on disk. That is **T0**, and it blocks the rest.

**The deviation from #89's sketch, and why.** #89 proposed the fork do everything then `SendMessage({to: "main"})` after §5b. This draft splits it: **fork builds, parent verifies and announces.** The measured cost is research and drafting (22,576-byte fragment × 5 rewrites, 986,929-byte page, ten ratchet runs); browser verification is a few tool calls. Forking the expensive half captures nearly all the saving while keeping the step that caught the `document.hidden` false negative and the missing `#modechip` block — neither visible in source. It also **dissolves question (1)**: the parent verifies, so it already holds the URL, and no path exists where an unverified page is announced.

**§5 is a HYPOTHESIS, labelled as one** — a fork writing only under `~/explainers/` should not trip the Codex overwrite detector, but that is unreproduced. Until T4 measures it, the conservative rule stands: do not build a page beside a Codex review.

## 2026-09-08
The check that would have noticed the four-day-old fix wasn't working is now in place.
Every explanation page is supposed to save its own source alongside it, so a question asked tomorrow can be answered inside the page rather than by rebuilding it from memory. The code that does this was added four days ago and does it unconditionally — I confirmed by running it. But across 47 files only two sources existed, and both belonged to the pages a hook regenerates, never to the ones an agent writes. The reason nothing caught this is simple: the step where a page gets checked before being handed over never looked for the source file. The write shipped without the observation, so there was no way to tell whether it had happened. That one-line check now runs first, before the expensive browser checks, because it is the cheapest thing that can fail.
<!--tech-->
**T0 of the #89 design.** `.claude/skills/shared/explainer-delivery.md` gains **§5b.0** — `test -f "${PAGE%.html}.fragment.html"` — ahead of the browser verification, because it is the cheapest check that can fail.

**EXECUTED, not reasoned:** ran `brief-compose.py --content … --out <tmp>/out.html` into a temp directory. It produced a 1,080,287-byte page **and** `out.fragment.html`. So the script is not the bug — the write at `:303` is unconditional and works. What was missing is anything that asserts it fired.

**Why §5b and not a script:** `~/explainers/` is outside the repo and 32 historical pages will never have a fragment. A repo-side ratchet would be permanently red with its own printed remedy unable to clear it — the failure `check-live-schema`'s accepted-additions list exists to prevent. §5b already runs once per page, at the only moment the answer is knowable.

⚠ **T0 is not closed by this commit, and the spec should not be read as saying so.** The observation now exists; **the next `/brief` build is what proves it.** If that page also lacks a fragment, §5b.0 fails loudly and names the cause — which is the whole point.

`check-explainer-delivery.py`: 1 shared description, 5 skills cite it, 0 restatements. `--self-test` 8/8.

## 2026-09-08
The shared instructions for building these pages now say who is supposed to build them.
Backlog #89's whole question was whether an agent should be constructing these pages inside the main conversation at all, and the file that describes how the pages work said nothing about who runs it. It does now: the research and writing may be handed to a separate agent, the final check — opening the page and driving it — stays here, and so does announcing the URL. Keeping that last step here is not caution for its own sake; it removes two other problems at once. The page cannot be announced before it has been checked, because whoever checks it is the one who has the address. And it cannot go out describing a decision as pending after you have made it, because the checker is the only participant that cannot be out of date about this conversation.
<!--tech-->
**T1 of the #89 design.** `.claude/skills/shared/explainer-delivery.md` gains **§0 — WHO RUNS THIS**, placed before §1 because it governs everything below.

| Step | Who |
|---|---|
| research, write the fragment, compose | a fork (optional) — this is the measured cost |
| **§5b execute and verify** | **the parent, always** |
| print the URL | the parent |
| answer a reader's question | the fork, resumed by name |

⛔ **§5b is not delegable**, and the section states the evidence rather than asserting it: two defects in the 2026-09-03 page were visible only by executing it — a `document.hidden` gate producing a false *"0 of 5 buttons reachable"* (a backgrounded tab has 0×0 geometry) and a missing `#modechip` block whose CSS **and** JS both existed. A fork that skips §5b ships a page that looks verified and is not.

The section also records the fork obligations: **name it at spawn** (an unnamed fork is unaddressable and §6's second half has nowhere to go), give it an explicit `as of`, and **write nothing inside the repository** — with the Codex-detector hazard labelled **UNMEASURED**, so the conservative rule stands until T4 runs.

**T2 needs no work and is confirmed by the gate:** `check-explainer-delivery.py` still reports 1 shared description, 5 skills cite it, **0 restatements** — adding a section did not create one. `--self-test` 8/8. Doc 273 → 314 lines.

## 2026-09-08 [needs-you]
The experiment about how these explainer pages get built has finished, and it answered the question
it was built to answer. A page was researched and written by a separate agent, then checked and
handed over by this session. The check caught something the writer could not see: in light mode the
page's body text was very nearly the same colour as its background, which makes it unreadable. That
was fixed and re-measured, and the page is fine now.

The reason this matters more than one page: the separate agent had even flagged that area as worth
checking, and still could not find it, because from the source both light and dark looked properly
defined. It only appears when the page is actually opened in a browser. So the split — one agent
writes, a different one opens the result and checks it — earned its keep the first time it was used.

Four things this turned up have been written down as work for later, at your instruction. The one
worth knowing about is that a safety check meant to catch exactly this colour problem only ever
looks at one of the five pages that could have it, and nothing said so.

A fifth thing turned up afterwards and is NOT written down yet, because that is your call: building
the same page five times from identical input produced five different files, each slightly larger
than the last. Since answering a reader's question rebuilds the page, a page that gets used grows
every time.

<!--tech-->
Backlog #89 T0, T3 and T4 all run; spec §8 records them. T0 discharged — first Group-A `.fragment.html`
ever written (`~/explainers/` 47 files/2 fragments -> 49/3). T3: fork spent ~786k tokens and 82 tool
uses outside the parent's context; parent's §5b cost ~15 tool calls and caught light-theme body
contrast at **1.03:1**, fixed to **8.69:1** worst case across all eight theme/OS states, re-measured
independently in Chrome. Geometry probe passed 8/8 distinct positions, refuting the fork's own
prediction. T4 attempt 1 was VACUOUS (page write 10:18:36 vs verdict 10:17:09 — no overlap) and is
recorded as such; attempt 2 arranged the overlap (write 10:21:28 inside window 10:20:51-10:21:50)
and returned `intrusions: []`, `docs/reviews/` unchanged at 866, zero quarantine. ⚠ The falsifier
CANNOT fire: `ARTIFACT_ROOTS = ("docs/reviews",)`, `watched_dirs()` is `dirname(--out)` plus that,
and `dir_snapshot()` is non-recursive, so a writer confined to `~/explainers/` never appears there.
§5 is confirmed for THIS MECHANISM only; CPU and a shared Postgres remain unmeasured. Filed #102-#105.
Corrected a false sentence in `explainer-delivery.md` §5 — monitors do NOT die with their session
(five were armed; one probe fired five events). Unfiled: `brief-compose.py` recompose is not
idempotent (1,139,120 -> 1,151,240 bytes over five identical inputs; it lifts the tray from the
NEWEST page, which after the first write is itself).

## 2026-09-08 [resolved: 2026-09-08/10]
You made the call on the experiment: keep the split. A separate agent researches and writes the
page; this session opens the finished result, checks it, and only then hands it over. The part that
must never be handed off is the checking — that is the step that caught the unreadable page today.

That closes the one question the design deliberately left open. The cost of working this way had
been measured; the benefit had only been argued. Now it has been seen once, so the argument is
retired.

You also settled the other open thing: rebuilding a page produces a slightly different file every
time, and that is now written down as work for later. Nothing is waiting on you.

<!--tech-->
Spec §9 records the decision verbatim and closes §7's first open item. `explainer-delivery.md` §0
promotes the fork from "(optional)" to the default and carries the measured figures (~786k tokens /
82 tool uses inside the fork, ~15 parent tool calls). Two things deliberately NOT fixed by the
decision: that every page must be forked (a trivial page inline is fine), and the cost side — §9
carries an expiry falsifier, since the benefit is context saved and that number moves with model
context limits. The invariant that IS fixed: no page reaches the human that the parent did not
execute. The fifth finding is filed as backlog **#106** — recompose is not idempotent (five
byte-identical inputs, 1,139,120 -> 1,151,240 bytes; the tray is lifted from the NEWEST page, which
after the first write is the page itself, and three of five runs self-lifted while two took it from
`goals.html`). Structure held across all five — one `#tray`, one `#qbox`, buttons matching headings,
contrast unchanged at 8.69:1 — so it degrades size and determinism, not correctness yet.
PR #267 carries all of it.

## 2026-09-08
You read the briefing page and spotted that some of what it asked for had already been done. That
was right: the page was built at 10:24 and everything it asks about happened afterwards, so it was
about forty minutes out of date by the time you read it.

Reconciling it turned up one genuine gap. The page listed four things as needing your yes/no; three
had been written down, and one had not — that the backlog cannot be counted reliably. Three
reasonable ways of counting the same 101 rows gave 59, 61 and 63 open items.

That is now recorded, deliberately as evidence on an existing item rather than as a new one, because
the item it belongs to already said the status column was doing too many jobs. What it was missing
was proof.

<!--tech-->
Folded into row #90 rather than opening #107 — #90 already owns "one Status column has to serve all
three — which is how #46 and #50 were once marked closed while still open", so a new row would be
duplicate coordination vocabulary for a concern it already covers; what was absent was the
measurement. Cause: Status cells are append-only, up to 3,889 chars, verdict at the END, so a
first-marker parse returns the ORIGINAL filing — row #78 parsed as open while its tail reads
`✅ CLOSED 2026-09-07`. Falsifier added: two independent open/closed parsers over the table must
agree; today they differ on four rows. Consequence recorded for the page generators: any headline
count of open work is a RANGE, not a number. Page rebuild follows this commit so it reports the
settled state.

## 2026-09-08
The tool that checks whether our safety checks actually work had a flaw that made it expensive to
maintain: seven reviews in a row each found a mistake inside the previous review's fix. None of those
fixes was wrong. The problem was the shape of the thing they were all editing — a bag of seven loose
values, where the one saying "these numbers are trustworthy" was easy to forget to look at. So each
review found one more place that forgot, and there was always one more place.

That bag is now a type with two shapes: either the run produced a real result, or it did not. When it
did not, the numbers **do not exist** to be read — in particular the count of problems found, which
reads as "all clear" and is the single most misleading thing you can print about a run that measured
nothing. You can no longer reach for it by accident, because there is nothing there to reach for.

The nicest part is something we did not expect. There were two rules elsewhere in the code that look
identical, mean opposite things, and were held apart only by a long comment warning people not to
tidy them into one. Under the new shape they are genuinely different things, so the comment describes
a fact rather than pleading for one.

No behaviour changed. The tool prints exactly what it printed before, checked character by character.
<!--tech-->
Backlog #91, from architecture review 2026-09-03b (the four-non-converging-rounds trigger).
`scripts/coverage_verdict.py` holds `Measured | NotMeasured`. `NotMeasured` has no `survivors` field
and its list is `entries`, so copying a line from the measured path raises `AttributeError` instead of
printing a wrong number. `Measured.__post_init__` enforces all three clauses; `controls_green` is an
`InitVar`, so you cannot ask a `Measured` whether its controls were green — it only exists if they were.

⭐ Plan mode's `declared is None` maps to `Measured(declared=0)`, NOT `NotMeasured`. Measured with a
control: the same shape with `declared=1` and no verdicts raises. This is what makes backlog #93's
two-printer-gate asymmetry a type distinction rather than a comment.

`tally`/`compared` moved to a frozen `RunContext`, and that parameter is REQUIRED — the default made
`evidence()` claim "--compare was not given" over a run where it was, which is r4 H1 reintroduced as a
default argument. Eleven fixture call sites were leaning on it; a case now asserts the refusal, because
a mutation restoring the default would survive.

`EXPECTED_MUTATIONS` held at 359 (check-plan-code 35 → 30, coverage_verdict 5) — a relocation must not
read as a deletion. `--mutate .` → 359 mutations, 0 survivors.

⚠ Two importlib loaders (`check-selftest-counts.py`, `begin-plan.py`) now register the module in
`sys.modules` before exec: `check-plan-code.py` gained a `@dataclass` under
`from __future__ import annotations`. Reverting that one line gives
`AttributeError: 'NoneType' object has no attribute '__dict__'` from inside dataclasses.

⚠ F6 cannot be byte-identical as the spec words it: the new module joins the mutation corpus, so the
file count moves 31 → 32. Everything else is unchanged (359 / 0). F7 IS byte-identical, both the plan
stdout and the evidence block. Spec §4 F7 should also name its subject rather than say "clean".

⚠ A first anchor measurement reported 12 orphaned mutations and was WRONG — it matched the delivered
repo's manifest against rewired code, when a retarget edits the manifest too. The `--mutate .` run
refuted it. Measure each tree against its own manifest.

## 2026-09-08
Three rounds of adversarial review of that same tool are now folded in. Each round was scoped to the
*previous* round's fixes, which is deliberate: the failure this whole change exists to end is a fix
that quietly introduces the next defect, and rounds one, two and three each found exactly that.

Round three found four. Two were the same mistake seen twice — a fix applied to one of two places
the same thing happens, so the path a real document takes was still wrong. Two were the tool
contradicting itself in the report it leaves behind: one line said a block had been assembled and
another, four lines below it, said none had; and a run given a flag reported in one sentence that it
was given and in another that it was not.

All four are fixed, and the fixes are held by tests that fail when reverted rather than by comments
saying they were checked. One thing is worth flagging honestly: **three review rounds in a row have
found their defects inside the previous round's fixes.** Our own process says that at four rounds we
stop patching and review the design instead. We are one round from that line, and the rule for round
four is written down in advance rather than argued after the fact.
<!--tech-->
Fold of `docs/reviews/{claude,coordinator}/plan-coverage-verdict-union-r3-*.md` — 0 Blocking, 4 High,
2 Medium, 1 Low, three of the four Highs regressions from r2's own fixes.

**H1+H2, one fix.** `extract()` returns a fifth value `mut_readable`; r2's caller-side match on two
problem STRINGS is deleted. It guarded one of `check()`'s two returns — the one a plan with NO code
takes — so `declared = len(muts)` still built `Measured(declared=0)` over an unparseable declaration
on the reachable path. And the string set was already incomplete on three routes (a `FILE_TAG`
silently clearing `want_mut`; `{}` and `""`, valid JSON extending to nothing with an EMPTY problems
list). Searching the class found two more: a second `<!-- mutations -->` clobbering the first, and
`[1, 2]`, whose "names" every `mut.get(...)` would read off a `str`. L1 (`null`/`0` →
unhandled `TypeError`) has the same cause and is fixed in the same edit. ⚠ Fifth POSITIONAL value,
not a `tally` key: 19 stale call sites raised `ValueError` at the unpack; a dict key would have been
silent to miss — the fail-open `coverage_verdict.py` exists to delete.

**H3.** `tally['tagged']` was rendered as "N assembled" while the subject sentence speaks for `files`;
on a tagged-then-DROPPED block one artifact printed `1 assembled` above `no block was assembled`. The
count now moves with the file at the drop site, the key is `assembled`, and the drop is stated:
`(0 assembled, 1 tagged then DROPPED, 0 illustrative)`. Both lines asserted in ONE case.

**H4.** `verify_evidence`'s `mode` read `ctx.compared` (the result) instead of `ctx.compare_requested`
(the invocation). r1 had corrected it by accident, r2 recorded it as checked-and-clean **in prose**,
and deleting the `{}` state reverted it with nothing to fail. Both directions cased.

**M1 — the anchor orphaning was called BEFORE the fix, a first on this branch.** Two entries were
orphaned by this fold and RETARGETED: the r2-H3 anchor (its line is deleted outright) and the
honest-zero predicate, for the FOURTH time here. `EXPECTED_MUTATIONS["check-plan-code.py"]` 33 → **41**,
declared sum 362 → **370**; self-test 207 → **223**.

EXECUTED: `stage_tree` complete, control **223/223 green**, then the 10 new/retargeted entries run
individually — **10/10 caught, measured, 0 survivors, each red via the case it NAMES**. Static anchor
sweep over all 32 manifests: **375 edits, 0 orphaned, 0 ambiguous**. Full `--mutate .` deferred to CI.
⚠ One of my own mutations was a NO-OP dressed as a mutation (it re-appended the same message and left
the flag standing) and reported SURVIVED; running them is what caught it.

**REVIEW GAP: codex** — third consecutive round unavailable (`gpt-5.6-sol/-terra/-luna` all HTTP 400,
`gpt-5.5` timed out). Treat the Codex pass as NOT RUN, not clean.

⛔ **Round 4 rule, set in advance:** `evidence()` and `verify_evidence()` narrate one run from two
variables with no shared derivation, and every round so far has fixed one narrator and left the other
disagreeing. If round 4 produces another self-contradicting artifact, Phase 6 convenes instead of a
fifth fold.

## 2026-09-08 [needs-you]
A fourth review round on the same tool, and this one is different in a way worth two minutes.

The one significant finding is a mistake I made and then wrote a comment claiming I had not. Round
three fixed a case where the tool's report contradicted itself, and I added a note saying the whole
class of that problem was now closed. It was not. There was a second route to the same
contradiction, the tool has printed it since long before this work started, and none of our 223
automated checks could see it — in either direction. A reviewer found it by running the actual
command and reading the output.

Everything else went the right way. This round introduced no new breakage, which is the first time
in four rounds; the fixes from round three survived being attacked directly; and the two independent
reviewers **disagreed** — one said all clear, the other found the problem. Had I trusted the clean
one, which arrived first, it would have shipped.

**A decision is waiting on you, and it is not about this change.** Our rule says four inconclusive
rounds should trigger a design review rather than a fifth round of patches. I do not think the
design review should be about the thing we keep patching. It should be about a fact nobody has
acted on: **none of the 92 plan documents we have actually use the feature these four rounds have
been reviewing.** Its only exerciser is its own test suite. Whether that feature should exist, or
should be exercised by something real, is a question I can't answer for you.

The work itself is merged and the tool is meaningfully better than it was this morning.
<!--tech-->
Fold of round 4 — `docs/reviews/{claude,coordinator}/plan-coverage-verdict-union-r4-*.md` plus the
first Codex half in the series (`gate_ran=true`, `gpt-5.5`). Claude: 0B/1H/2M/2L NOT CONVERGED.
Codex: **CONVERGED** 0/0/0/1. ⭐ The halves disagreed and the finding-reviewer was right — Codex
enumerated `mut_readable`'s routes correctly and the defect was in the CENSUS, which its question
could not reach. Fourth recorded instance of *dual halves are not redundant*.

**H1** — a file tagged with a NON-python fence is reported AND assembled, but the census incremented
inside the `is_py` branch, so the CLI printed `0 assembled` two lines above `a.py 1 blocks
assembled`; and a tagged-then-DROPPED non-python block decremented zero, making the drop invisible.
**Identical on `master`** — not a regression, but r3's comment declared the class closed. Fixed by
counting where the block enters `files`. Both lines asserted in one case on a non-python fixture.
⚠ `assembled` may now exceed `python fences`; different denominators, and the label says so.

**M1** — `except VerdictContractError:` caught bare, so three refusals rendered one byte-identical
durable sentence. Now `as exc` → `from_counts(..., cause=str(exc))` → `not_measured_reason`, where
the arithmetic already lives. Cased as an INEQUALITY. ⚠ Residue: the two *declaration* causes still
share a sentence; separating them needs the flag to carry its reason, which is the second-meaning
shape this branch spent three rounds deleting. ⚠ Entry 22's anchor spanned the `except` line and
orphaned exactly as the reviewer predicted BEFORE the fix — retargeted onto the raise message.

**M2** — the anchor-split from earlier today was justified as "each says which one failed", and that
had no falsifier: both messages collapsed to one string still gave 223/223. Three cases added. A fix
that shipped without its case, in a branch about fixes that ship without cases.

Self-test 223 → **231**; coverage_verdict 22 → **27**; EXPECTED_MUTATIONS 41 → **44** and 5 → **6**,
sum 370 → **374**. Two green controls, **15/15** new-or-retargeted entries red via their named case,
`load_manifests` 374/0 problems.

⭐ Two defects in my OWN new mutations/cases, both found by running rather than reading: a case read
`.reason` off what a mutation turns into a `Measured` (no such attribute) and crashed the SUITE, so
the entry reported `0 red cases … caught by something else: []` — the *report format is a CONTRACT*
shape; and an `expect` named a case the mutation couldn't kill because both messages embed
`type(parsed).__name__`.

⛔ **Phase 6:** the pre-registered r3 rule fired on its literal terms (H1 is a self-contradicting
artifact) and its stated CAUSE was measured false — the three narrators now agree. Per
`review-method.md` the trigger is read off the cause, so Phase 6 is NOT convened on `evidence()`.
Escalated instead: **0 of 92 plans exercise plan mode's file path**; four rounds spent on a renderer
whose only exerciser is its own `--self-test`. That is a goal-moving question → user's call.

## 2026-09-08
Plan mode is retired. The tool that used to check a planning document by assembling the code
inside it, running that code and generating the evidence now refuses to do so, and says why. The
job it did moved to a better mechanism a week and a half ago; what stayed behind was a second way
of doing it that nothing used. This change makes it unreachable and puts a fence around the hole
it leaves. Nothing is deleted yet — that is a separate, smaller change, and it is safe only
because this one landed first.

The one thing worth knowing: the guard written to be that fence was **wrong on its first run**,
and it said so out loud rather than passing quietly. It flagged a review document from last week
that had merely *quoted* a plan. The fix was to stop reasoning about how the old parser behaved
and to run it — which showed the quoted text had never been visible to it. The guard now carries
the parser's own rule, taken by measurement.
<!--tech-->
Branch `retire-plan-mode`, PR 1 of 2. Uncommitted work inherited from the previous session plus
this session's completion.

**The refusal.** `check-plan-code.py main()` now returns **rc=2** with a sentence naming the
retirement for `<plan>`, `--evidence`, `--compare`, `--verify-evidence`. Refused, not removed:
argparse's "unrecognized arguments" reads like a typo, and someone who typed `--verify-evidence`
believed a subject was being measured. rc=2 (CANNOT RUN), never 0.

**The fence** — `scripts/check-plan-file-tags.py`, new, 21 cases, 8 mutations, CI step + self-test
step. Fails if any `docs/**/*.md` line is a standalone `<!-- file: … -->` or `<!-- mutations -->`
tag. MEASURED baseline: **0 line-anchored tags across 1,115 documents**, while **13** documents
mention the tag in backticked prose and must keep passing — a bare substring test breaks all 13,
which `plan-mutation-retarget-r1` finding 3 already paid for. An **empty corpus is rc=2**, because
the whole finding is a zero and a zero over nothing is not a finding.

⭐ **v1 had no fence rule**, justified by a claim about `extract()` written from reading it. First
live run flagged `docs/reviews/claude/plan-coverage-verdict-union-r3-claude.md:159`. Running the
parser on those exact bytes: `files=[]` — never seen. Control: the same indented tag *without* the
fence assembles `m.py`. So the fence is the cause and indentation is not; an indented or
info-string fence opens nothing (`INVISIBLE_FENCE`), so a tag under one is live. All four branches
are now cases. The alternative — editing a committed review document to satisfy a checker — was
avoided by measuring rather than assuming.

⭐ Two further defects found by running, not reading: my manifest had **two entries sharing an edit
anchor** (`load_manifests` refused it — the count would have held while coverage shrank), and a
case reading `f[0].detail` **crashed the suite** when a mutation emptied the list, so the entry
reported `0 red case(s) … caught by something else: []` while working perfectly. That is the
recorded *report format is a CONTRACT* shape, second instance in two days. Every indexing case in
the file is now a whole-list comprehension.

Counts: `EXPECTED_MUTATIONS` **374 → 382** (+8, RISING — the decrease belongs to PR 2 and must be
recorded there as a deliberate retirement); `check-plan-code` docstring **231 → 229** (the drift
that blocked every downstream gate); `check-selftest-counts` population 29 → **30**.
`dev-process.md` 218 → 219 lines (budget 220), with the stale "the mode still exists" sentence
corrected in place. **No ADR** — checked, PR #176's own supersession produced none; the precedent
is a `dev-process.md` row plus the code comment, which is what this does.

Verified: 8/8 mutations red via the case each names over a green control; `load_manifests` 382
entries / 0 problems; self-tests green — plan-code 229/229, file-tags 21/21, ratchet-contract
22/22 (29 guards discovered incl. the new one), selftest-counts 18/18, review-rounds 29/29,
anchors 15/15, ci-watched 23/23, dashboard-entry 13/13, explainer-delivery 8/8, task-order 21/21.
Live guard run: `plan-mode tags: 0 across 1115 documents under docs/`.

## 2026-09-08
Correction to the entry above, and the reason it exists. A review pass over that change found a
real defect in the new guard — it disagreed with the tool it was meant to mirror about where a
line ends, in exactly the direction that would let a tag slip past unnoticed. Found by running
both against the same input rather than reading either. Fixed, with a case for each of the nine
ways they could have disagreed.
<!--tech-->
Review round 1, Claude half, filed at `docs/reviews/claude/retire-plan-mode-r1-claude.md`.

**H1 (fixed in-round).** `check-plan-file-tags.audit` iterated `text.splitlines()`;
`check-plan-code.extract` iterates `md.split("\n")`. `splitlines()` breaks on NINE further
separators (`\v \f \x1c \x1d \x1e \x85 U+2028 U+2029 \r`). Measured: for 8 of them,
`x<SEP>```" opened a fence in the guard that never opens in the parser, so the tag beneath was
skipped as fenced while `extract()` assembled it — `files=['m.py']` vs **0** findings. Third
recorded instance of imitating a parser instead of asking it. Fixed to `split("\n")`; re-measured
**0 disagreements across all nine**, over the file both consumers actually read.

⚠ My first re-measurement said `\r` still disagreed. That was a defect in the TEST — `read_text()`
does universal-newline translation, so I fed `extract()` a raw string and the fence a translated
file, then called the difference a divergence. A false finding accepted there would have driven a
fix to code that was already correct.

Cases 21 → **29** (one per separator — the class, not the instance). `EXPECTED_MUTATIONS` for the
guard 8 → **9**, sum 382 → **383**. Verified: 9/9 mutations red via the case each names over a
green control; live run 0 tags across 1,115 documents; all gates green.

⚠ **REVIEW GAP — the Codex half produced no output and must be re-attempted before merge.** Per
the bounded-wait rule that is a Codex gap, not a clean Codex verdict. Recorded in the review doc.

## 2026-09-08
The second reviewer finally ran, and it found a hole the first one missed. The new guard was
checking a smaller set of documents than it claimed to — and nothing could tell, because both
its own tests and its live run stayed green while a fifth of the files, including every single
one of the planning documents it exists to police, went unread. Fixed, with a check that
compares what was read against what is actually there.

Worth stating plainly: had the second review been skipped as "probably redundant", that hole
would have shipped.
<!--tech-->
The Codex half of review r1 succeeded on a second dispatch — `--model gpt-5.5 --timeout 1800`,
skipping the three deterministic HTTP 400s and giving the one reachable model enough budget.
~22 minutes. Filed at `docs/reviews/coordinator/retire-plan-mode-r1-codex.md`; verdict updated
to `gate_ran: true`. The earlier REVIEW GAP is closed.

⭐ **Cx-H1 (CONFIRMED, FIXED).** `DOCS` is read by `main()` and by NO case — every case drives
`audit()` on a temp root. Re-measured on HEAD with `DOCS` pointed at `docs/reviews`: live run
**rc=0, "0 across 896 documents"** (vs 1116) and self-test **29/29** — both green while 220
documents went unread, **including all 92 plans**. My empty-corpus rc=2 clause refuses a corpus
of *nothing*; it never saw a corpus of *something smaller*. The clause I was most confident in
guarded the case that could not happen.

Fix: `coverage_shortfall()` — `main()` refuses unless `scanned` equals the count under
`ROOT/"docs"`, re-derived by the CALLER. That asymmetry is the mechanism: mutating `DOCS` moves
what `audit` reads and not what this counts. Falsifier after the fix: **rc=2, "read 896 of
1116"**. Cases 29 → **33** (with a presence twin, so an always-fires check is caught too);
mutations 9 → **11**; `EXPECTED_MUTATIONS` 383 → **385**.

**Cx-L1 (CONFIRMED).** The retirement gate returns before the `--mutate`-combination check, so
that more specific refusal can never fire. Behaviour is fail-closed and right; the **comment**
was wrong to imply a caller can reach it. Corrected in place.

**Cx-Blocking** was the `splitlines()` divergence — already fixed in `92b2b362`. Codex reviewed
`71f86f9a` and rediscovered it independently: same defect, same nine separators, same direction.

⭐ **Fifth recorded instance of *dual halves are not redundant* — and the first where the half
that nearly got skipped is the one that caught the defect.** Round score: 4 defects, 1 by the
Claude half, 1 by CI's mutation sweep, 2 by Codex.

Codex honestly reported CANNOT RUN on `--mutate .` (two attempts, both interrupted) — which is
the very check that caught the orphaned mutation.

## 2026-09-09
A second review round — this one aimed at the fixes from the first round, not at the original
change — found three more problems, all of them in the repairs themselves. The most serious: the
guard meant to prove it had read the right documents was only counting them. A different set of
files of the same size passed as if nothing were wrong, with a live violation sitting unread
inside the set it skipped.

The pattern is now the headline of this branch: **every round of fixes has introduced its own
defects.** That is not a surprise here — it is what the project's own history predicts — but it
is the reason this work is not finished when the tests go green.
<!--tech-->
Round 2, SCOPED to r1's fixes (`git diff 71f86f9a..6e5b2b78`). Both halves filed:
`docs/reviews/claude/retire-plan-mode-r2-claude.md`,
`docs/reviews/coordinator/retire-plan-mode-r2-codex.md` (`gate_ran: true`, gpt-5.5).

⭐ **Cx-H1 — cardinality is not identity.** `coverage_shortfall` compared COUNTS. Codex's
measurement: intended `docs/` = {`a.md`, `has-tag.md`} with a LIVE tag; a different root =
{`x.md`, `y.md`}; `scanned == total == 2` → verdict `None`. False green over a corpus never
scanned. Fixed to a SET difference (`want - seen`, `seen - want`), reported by name. Codex's exact
construction now REFUSES, naming `a.md` as never visited.

**H1 (Claude half) — wrong cause, right cause suppressed.** `rglob` counts PATHS, `scanned` counted
files READ, so an unreadable document printed "the corpus was NARROWED" and `main()` returned
before the finding naming the file could print. Measured: rc=2, stdout empty. Fixed with a typed
`Finding.unreadable` (not a substring match on my own message) and by printing findings first.
Codex found the same defect independently — its M1.

**H2 (Claude half) — the fixes ORPHANED mutation anchors twice.** Anchors bind by TEXT, so
improving code silently unhooks them; only the sweep can tell. Three re-bound, then re-bound again
when the Cx-H1 fix rewrote the same region.

⚠ Two failed attempts at one mutation, both recorded: the first SURVIVED because a guard clause it
never touched still caught the case; the second CRASHED the suite (`0 red case(s) … caught by
something else: []`), exposing a real latent fall-through that indexed an empty list. Restructured
so every branch reports its own condition and `None` is the final fallback.

Cases 33 → **39**; guard mutations 11 → **14**; `EXPECTED_MUTATIONS` 385 → **388**.

**Running total for this branch: 7 defects across 4 instruments** — 3 by the Claude half, 1 by CI's
mutation sweep, 3 by Codex. No instrument found more than half. Round 2 is NOT CONVERGED by the
usual reading (it found things), so a round 3 scoped to THESE fixes is the honest next step.

## 2026-09-09 [needs-you]
Review round 3 is done and the plan-mode retirement still is not finished — but for the first time
the problems are with the checking, not with what the code does.
Three rounds of review have now found ten things. None of them changes what the guard does on the
real project: it still correctly reports zero retired tags across 1,120 documents. Round 3's
findings are all about the guard's own honesty — a field that was added to tell two kinds of
failure apart and is in fact read by nothing, a comment that says it is doing a job it cannot do,
and two entries in the test suite that crash it while appearing to pass.
Two of the three checking machines used today were themselves broken, which is the part worth
knowing. One review assistant produced a long, confident, well-argued review of a completely
different piece of work, and nothing about the document itself gave that away. My own quick check
of the test suite reported all fourteen entries healthy when two of them were killing the suite
outright. Both were caught only by looking at something the machine could not fake.
**A decision is waiting on you: fix these and run a fourth round, or record them and ship.**
Neither is wrong. Nothing found in three rounds affects what a person using this actually sees.
<!--tech-->
Branch `retire-plan-mode`, head `f9d2c498`, PR #270 OPEN, CI `verify` green. VERDICT: NOT CONVERGED.
Both halves filed: `docs/reviews/claude/retire-plan-mode-r3-claude.md`,
`docs/reviews/coordinator/retire-plan-mode-r3-codex.md`,
`docs/reviews/verdicts/retire-plan-mode-r3-codex.verdict.json` (`gate_ran: true`, gpt-5.5).
`check-review-rounds.py` rc=0, 167 rounds parsed, 0 silent gaps.

**3 Medium, 3 Low, 1 Codex High REFUTED.** Nothing Blocking.
* **F1** `Finding.unreadable` has NO production reader — `coverage_shortfall(docs_root, seen)` never
  receives a `Finding` and `main()` never mentions it. Falsifier run twice independently: delete
  field + kwarg → production stdout BYTE-IDENTICAL, same rc. The real r2-H1 fix is `visited.add(md)`
  at `:188`. Its comment cites backlog #91's type work, which makes the claim credible and it is false.
* **F2** r2 moved the undecodable case from rc=2 (CANNOT RUN) to rc=1 (FAIL) and prints "put it in
  backticks" for a file that cannot be decoded. Filed against itself: FAILS-IF does list it. Coupling
  is the point — if rc=1 is intended, `unreadable` is *unwireable*, so F1 and F2 cannot both be waved.
* **F3** manifest entries 6 and 11 CRASH the suite (`IndexError`, no summary line, case 39 never runs)
  via `sorted(n)[0]` introduced by THIS commit at `:417` — banned by the same file at `:264-269` and
  recorded in `check-plan-code.py:1668` as measured 2026-09-08. They attribute only because their named
  case prints before line 417: ordering luck. The r2-H1 entry also does not model its name (deleting
  `visited.add` ≡ its sibling `return findings, set()`); the faithful edit gives 1 red case, no crash.
* **F4/F5/F6 + coordinator C2/C3/C4** — mislabelled presence twin; the remediation sentence printing
  the whole corpus (1120) as though it counted backticked mentions (19); stale `scanned` prose and
  READ/VISITED labels; docstring "13 documents" now 17; "5 of 5 separators tested" is really 8 of 9;
  `rglob` does not descend symlinked dirs and BOTH walks share that blindness, so the shortfall check
  cannot see it (0 symlinks under `docs/` today).
* **Cx-H1 REFUTED**, independently by both the Claude half and the coordinator: `check():1295` is
  `plan.read_text(encoding="utf-8")`, so universal-newline translation precedes both splitters and `\r`
  cannot diverge. SECOND time this exact wrong conclusion was reached on this file by different readers.

⚠ **TWO INSTRUMENT FAILURES, both caught only by out-of-band evidence.** (1) The first Claude-half
subagent emitted 27,489 bytes BYTE-IDENTICAL to the committed
`docs/reviews/plan-project-dashboard-r3-claude.md` — wrong plan, wrong branch, wrong findings — then went
idle. Caught because the brief had been amended mid-flight to demand a FILE, for an unrelated reason. The
retry brief now requires live `git rev-parse HEAD` + `git diff --stat` pasted first. (2) The coordinator's
own mutation harness reported "14/14 OK" while two entries crashed: it parsed for the named `[FAIL]` line
and never checked for a completion summary, and an uncaught exception also exits 1.
⚠ **The Codex wrapper OVERWROTE a committed verdict** on the first run: `verdict_path()` derives the
filename from `--out`'s basename with no collision check, so `--out r3-codex.md` clobbered
`docs/reviews/verdicts/r3-codex.verdict.json` (committed under PR #214). Detected by `git status`,
restored, re-run under a unique stem. Verbatim recurrence of a defect already in project memory.

## 2026-09-09 [resolved: 2026-09-09/2]
You chose to fix the round-3 findings rather than ship as-is, and that is done.
The headline repair is one worth explaining, because it is the opposite of what I proposed. Round 3
found a piece of bookkeeping that was supposed to tell two kinds of failure apart — a document with
forbidden content in it, versus a document the checker simply could not open — and proved nothing
was reading it. My plan was to delete it as dead weight. Working through the second finding showed
that wrong: the reason the checker was giving nonsensical advice on unreadable files ("put it in
backticks", to a file that is not even text) is precisely that nothing distinguished the two cases.
So it was wired up instead of removed. It now decides which advice to print, and the proof it is
genuinely in use is that deleting it no longer produces identical output — it stops the program.
Also fixed: two entries in the checker's own test suite were killing that suite while appearing to
pass, and four recorded measurements had drifted away from what the code does. One of those, a count
of how many documents mention the thing being checked, moved while I was correcting it — because
the review documents I had just written mention it too, and joined the count. It is now written as
a dated observation that says out loud it will keep rising.
The full sweep that mutates every checking script and confirms each one still catches what it
claims: 390 checks, none escaping.
<!--tech-->
Branch `retire-plan-mode`, PR #270. Folds r3's 3 Medium + 3 Low + coordinator C1–C3; C4 recorded,
F2 decided (rc=1 stands, message repaired). Both review docs carry a DISPOSITIONS section.

* **F1 FIXED BY WIRING, NOT DELETING.** `main()` now selects its closing message with
  `any(not f.unreadable for f in findings)`. FALSIFIER RE-RUN: deleting the field + kwarg used to
  leave stdout BYTE-IDENTICAL (that is how r3 proved it inert); it now raises
  `AttributeError: 'Finding' object has no attribute 'unreadable'` inside `main()`.
* **C1 FIXED.** The live corpus count is GONE from the remedy rather than corrected — a number
  re-measured on every failing run is a liability. Unreadable-only runs print "Every finding is a
  document this could not open, so it was NOT CHECKED".
* **F3 FIXED, both halves.** `sorted(n)[0]` → `r / "bad.md"` (the fixture's own path, cannot raise);
  the r2-H1 entry retargeted to the faithful weakest edit (`visited.add(md)` after a successful
  read) instead of one indistinguishable from its sibling. Re-measured: **16/16 entries, 0 crashes**,
  each reddening the case it names, control 43/43.
* **C3 FIXED + the CAUSE of the twice-repeated false High.** The splitter comment now states that
  `\r` cannot reach EITHER splitter (both readers use `read_text`, universal-newline translation
  precedes splitting) and that the loop drives 8 separators because the 9th is UNREACHABLE, not
  overlooked. Re-measured: old `splitlines()` 8-of-9 disagreements, delivered `split("\n")` 0-of-9.
* **F4/F6/C2 FIXED** — mislabelled presence twin; retired `scanned` prose; READ→VISITED labels;
  the mention count dated (17 at r3, **19** once r3's own docs landed).

⚠ THREE THINGS WENT WRONG DURING THE FOLD, all caught by instruments rather than by reading:
(1) renaming a case ORPHANED its mutation anchor — 4th orphaning on this branch, caught in seconds
only because the harness now reports `named-hit`; (2) the full sweep went RED and refused a verdict
because two new mutations shared an edit anchor — `load_manifests` rejects that, correctly, since an
entry repeating another's anchors measures nothing; (3) a `$?` read after a pipe would have reported
the sweep's exit code as the pipe's — every rc here is taken from a redirect.

Counts: cases 39 → **43**; guard mutations 14 → **16**; `EXPECTED_MUTATIONS` 388 → **390**. RISING.
Gates: self-test 43/43 · check-plan-code 229/229 · check-selftest-counts · check-review-rounds
(167 rounds, 0 silent gaps) · check-ratchet-contract · check-docs — all rc=0. **Full sweep:
33 file(s), 390 mutation(s), 0 survivor(s).** 0 orphaned anchors across all 33 manifests.

## 2026-09-09
A fourth review round found four more things, all of them in the checking rather than in what the
tool does — and this round the reviewer was mostly correcting my own writing.
The one real fix: the test suite could be killed outright by a fault in the code it was testing, and
when that happened it produced no failure report at all — the automated checker then read the silence
as "something else caught it". Four lines turn that silence into three clearly named failures.
The rest were claims I had written that did not survive being checked. I had asserted that an earlier
round dated a measurement in a particular place; it never did, and I had taken that from the earlier
round's write-up instead of from the code — inside a paragraph arguing that exactly this is dangerous.
And a count of how many documents mention a piece of syntax has now been wrong three separate ways in
three rounds: stale, then correct-but-measuring-something-else, then ambiguous between three defensible
answers (19, 18, or 15, depending on what you mean). It is now deleted rather than corrected a third
time, with a note saying not to put one back.
Reviewing has stopped here. Four rounds, and the problems have moved steadily from "the tool is wrong"
to "the notes about the tool are wrong", which is the point at which more review stops paying.
<!--tech-->
Branch `retire-plan-mode`, PR #270. Folds r4: 1 Medium + 4 Low, all inside the r3 fold. Both review
halves filed with DISPOSITIONS. **Full sweep: 33 file(s), 392 mutation(s), 0 survivor(s).**

* **F1 (Med) FIXED — and the coordinator had WRONGLY dismissed it.** I filed the crash-instead-of-red
  shape as "pre-existing and inherent" and declined to act. The Claude half's decisive fact: **before
  the r3 fold, NO case in this file invoked `main()`** — every case drove pure functions over an
  explicit root — so the fold added the first four that call the entry point and genuinely enlarged
  the surface. `_drive_main` now returns `(-1, "main() RAISED …")`. MEASURED with an injected raise:
  `3 named [FAIL] lines + 41/44 cases passed`, was `no summary, no [FAIL], traceback`.
* **F2 (Low) FIXED, and F1's fix is what made it fixable.** The `finally` restore could be deleted
  with the suite still 43/43 green. With the suite now surviving a raise it has a real beneficiary,
  and a new case placed after the block is its only observer. Both guarded by new mutations.
* **F3 (Low) FIXED as a recorded correction.** The header claimed r2 dated a measurement in
  `coverage_shortfall`'s docstring. Verified false both ways: no date at any revision, and r2 added
  no dated line to the file at all. Sourced from r2's REVIEW DOC, not the code.
* **F4 + Cx-L1 (Low) FIXED by DELETION.** "Both numbers" was three; `1,116`, `29/29` and `15/16` were
  stale. The backticked-mention count is GONE — three predicates give 19 / 18 / 15 and the prose named
  none. Header now says **"Do not reintroduce a count here."**

Counts: cases 43 → **44**; guard mutations 16 → **18**; `EXPECTED_MUTATIONS` 390 → **392**. RISING.
Gates rc=0: self-test 44/44 · check-plan-code 229/229 · check-selftest-counts · check-review-rounds
(168 rounds, 0 silent gaps) · check-ratchet-contract · check-docs. 0 orphaned anchors, 33 manifests.

⚠ **PHASE 6 — count fires, cause does not.** Four non-converging rounds is the written trigger, but
`dev-process.md` says read it off the CAUSE. The series decayed monotonically: r1 behaviour defects ·
r2 a real false-green (cardinality vs identity) · r3 one inert mechanism + one wrong message ·
r4 test scaffolding + four claims ABOUT the code. Nothing in r4 changes what the guard does to any
document. That is the documented "prose has nothing to execute — go build" signature, not a design
fight. Judgement recorded, not assumed; reviewing stopped by decision.

## 2026-09-09
Plan mode is now actually gone, not just switched off.
Yesterday's change made four old commands refuse to run and explain why. They kept
refusing, but the machinery behind them — a parser for plan documents, a runner, and the
thing that wrote up the results — was still sitting in the file, about sixteen hundred
lines of it, unreachable and unread. This removes it. The file is now roughly half its
former size, and the refusals still work exactly as before, which is the point: someone
who types the old command still gets a sentence telling them what happened, rather than
a confusing error that looks like a typo.
Worth knowing, because it is the kind of thing that goes wrong quietly: I wrote a small
program to do the deletion mechanically, and three times it damaged code that was
supposed to survive. The worst instance left five tests that could no longer fail — they
would have gone on reporting success forever while checking nothing. All three were
caught by running the tests before and after and comparing, never by reading the result.
A deletion this size is exactly where a green tick is least trustworthy.
The count of tests fell from 229 to 74 and the count of deliberate sabotage-checks from
44 to 23. Both are meant to only ever go up, so both falls are recorded in the code
itself, saying how many and why, rather than being quietly adjusted.
<!--tech-->
Branch `retire-plan-mode-pr2`, 4 commits off `4ec7e82a`. `scripts/check-plan-code.py`
3,607 → 1,983 lines.

* **C1** `main()`'s plan-mode tail (53 lines) + the `--mutate` combination guard, both
  unreachable past PR #270's refusal. **0 cases lost** — which is what "unreachable"
  was supposed to mean, now measured rather than asserted.
* **C2** `verify_evidence`, `pasted_evidence`, `EV_MARK`. 11 cases. ⚠ `EV_MARK` orphaned
  one commit earlier than the inventory predicted: `evidence()` writes that sentence as
  its own literal (`:1476`) instead of using the constant.
* **C3** the core — `extract`, `check`, `evidence`, `compare_delivered`, `unsafe_tag`,
  7 constants, 143 cases. One commit, not five: the transitive closure is one connected
  component, so splitting it leaves each commit holding dangling fixtures.
* **C4** docs. Docstring CONTRACT deleted with its parser (a documented contract nothing
  implements is worse than none); `dev-process.md` row updated.

**Ratchets, all moved with their subject:** cases 229 → 74 (docstring, `_drift_rc`
checks it every run) · `EXPECTED_MUTATIONS` 44 → 23 · declared sum 392 → 371. ⭐ 23 is
EXACTLY the figure the pre-work inventory predicted, reached by a different method —
the inventory attributed anchors by enclosing line range, the deletion retired them by
whether `src.find(anchor)` still resolves.

⚠ **THE PRUNER DAMAGED SURVIVING CODE THREE TIMES.** (1) it recursed into a nested `def`
whose PARAMETERS its binding scan could not see and emptied `_constructs`, leaving five
verdict-contract cases that could not fail; (2) reads were counted before subtracting
what a statement binds itself; (3) a `def` binds via `FunctionDef.name`, not an
`ast.Name` store, so killing a helper did not propagate to its callers. Every one was
found by RUNNING the suite against the 229/229 control, none by reading the diff.

⚠ **Two case-groups deleted as UNFALSIFIABLE, not as dead:** the escaping-tag block
("the delivered file is NOT overwritten", "nothing leaked outside the sandbox") and the
`evidence()`-requires-ctx probe. With their subject gone both assert an absence that
deleting the subject also satisfies — the recorded shape, not a judgement call made
loosely.

Gates rc=0: self-test 74/74 · check-selftest-counts (30 scripts, each re-run) ·
check-ratchet-contract · check-docs · check-review-rounds · check-plan-file-tags
(0 across 1,123 docs) · check-anchors. All four retired entry points and a bare
invocation exit 2 via redirect, never a pipe; `--mutate /nonexistent` exits 2 for its
OWN reason, so the surviving mode is not swallowed by the refusal. `--mutate .` is left
to CI, which is the run that measures the shipped code.

## 2026-09-09
The deletion above shipped to CI red, and what CI caught is the interesting part.
Five of the sabotage-checks stopped working. Not because the code they watch was
removed — it is still there and still running — but because the *test* that made each
sabotage visible happened to live in the part being deleted. Those tests reached the
code the long way round, through the machinery that has now gone, so removing the
machinery quietly removed the alarm while leaving the thing it was guarding in place.
Locally everything looked perfect: 74 of 74 tests passing, every other check green.
The only instrument that could see the gap was the one I had chosen to leave to CI on
the grounds that it is slow. That judgement was wrong and is worth remembering: the
check you skip because it is expensive is often the only one measuring the thing you
just changed.
The repair adds four small tests that check the same five properties directly, against
the code that owns them, instead of through two layers of something else. That is where
they should always have been — a test that reaches a rule via someone else's parser is
a test that dies when that parser does.
<!--tech-->
Branch `retire-plan-mode-pr2`, PR #271. CI run 34360995951: **3 survivors + 2 expects
matching 0 red cases**, over a local suite sitting at 74/74 green.

The five all had one cause: their only red case was a PLAN-MODE case driving
`run_mutations` end-to-end through `check(plan)`. The guarded code (`run_mutations`,
`run_suite`) survives; the caller did not. The recorded shape *a refactor orphans the
mutation guarding it*, inverted — the deletion orphaned the CASE, not the anchor.

⚠ **Retiring the five would have been wrong** and was the tempting move, since the
slice was already retiring 20. Their subject still ships, so retirement would have
shrunk real coverage inside a PR whose whole discipline is that coverage may only fall
when its subject does.

Repair: 2 `expect` fields retargeted onto surviving cases (one uses the LIST form,
naming both legitimate observers rather than picking one), and 4 new cases driving
`run_mutations` directly — ambiguous anchor refused, empty expect list refused, and the
mid-line `[FAIL]` pair. Cases 74 → **78**; `EXPECTED_MUTATIONS` unchanged at 23.

⚠ **The mid-line fixture is where an unfalsifiable case nearly shipped.** The parser is
`l.strip()[7:].rsplit(": got ", 1)[0].strip()`, so the marker must sit past a SEVEN-char
prefix for the mutated reader to yield a matching name. My first fixture had the offset
wrong: the case passed, and the mutation still SURVIVED. Fixed, and the offset is now
explained at the fixture rather than being a magic string.

**MEASURED after the repair:** the five re-run through the real harness (`stage_tree` +
`run_suite` + `run_mutations`, not a re-implementation) — control green at 78/78, then
**5 caught, 0 survivors**. Full `--mutate .` locally: **33 file(s), 371 mutation(s),
0 survivor(s), rc=0**. All seven doc/ratchet gates rc=0.

⚠ **Also recorded: I read the first CI result through a pipe.** `gh pr checks --watch`
was piped into `tail`, so the exit code reported was `tail`'s 0, not `gh`'s 1 — the
"$? after a pipe is the pipe's" hazard already twice in project memory, hit while using
it as a merge signal. The red was found by reading the checks again, not by the code.

## 2026-09-09 [needs-you]
We checked whether the automated sabotage-testing can be trusted, and the answer is a
qualified yes with one real gap.
Twenty-three deliberate sabotages are kept on file; each is supposed to break the tool in
a way one named test catches. All twenty-three do — confirmed three separate times, by two
independent reviewers and by me, all producing identical results. That part is sound.
The gap is one level up. There is a single line of code that decides whether a test
failing "counts" as catching the sabotage it was aimed at, or merely failed for some other
reason. That line has no sabotage test of its own. If it were ever weakened, every one of
the 371 checks in the project could be credited to the wrong test and nothing would say so.
It is correct today; what is missing is the guard on it. A second, similar gap sits beside
it. Neither is urgent — nothing is broken — but they are on the one file whose whole job is
to notice this kind of thing.
Separately, we now know the answer to a question that had been open for two weeks: is it
safe to run two review agents at once? Yes, when they only read files and work in their own
temporary copies — measured today, three overlapping processes, identical results. It is
NOT safe for three specific operations, and those are now grouped as one body of work so
they stop being three unrelated notes.
<!--tech-->
Branch `mutation-faithfulness-r1`, commits `f2eca70a` + `1e847c71`. No production code
changed; this is a review round plus a backlog filing.

**Round 1, dual adversarial on merged `3afe62c0`.** Both halves filed under their writer
directories per #92. `check-review-rounds`: 169 rounds, 0 silent gaps, 39 codex verdicts,
none contradicted.

* **All 23 entries FAITHFUL**, verified three ways: Codex ran each individually; the Claude
  half rebuilt the experiment with its own driver; my matched-pair probe confirmed the five
  newest cases track the guard's MEANING not the manifest's string (a semantically-null
  rewrite stays green; a *different* real weakening fires the named case). All three runs
  produced identical red-set data. No case is named by two entries; no compound edits.
* **F1 (High) — `:975` `w == f` has NO manifest entry.** Reverting equality to substring
  survives at **78/78, rc=0**. That line is what converts "the suite went red" into "went
  red via the case it names", for all 371 mutations in all 33 manifests. Its own comment
  records the round-6 defect where `expect: "does NOT count"` matched seven case names.
  NOT Blocking — intact on this commit; the *protection* is what is absent.
* **F2 (Medium) — the colon rule at `:923` is unfalsifiable.** Every fixture name reaching
  that parser is colon-free, so `rsplit(": got ")` and `split(":")` agree by construction.
  Reverting to the buggy splitter survives at 78/78. The recorded "the fixture uses an input
  a DIFFERENT rule filters first" shape.
* **F9/F10 (Low)** — entry 11's edit INVERTS (`!=` → `==`) rather than disables; shipped
  4 reds vs 2 for the weakest edit that still fires the named case.
* Both F1 and F2 independently re-run by me before acceptance. ⚠ The Claude half went idle
  mid-document and had to be pinged — third instance of that failure mode.

**Backlog `(concurrency safety)` bundle** — #67 rescoped to the user's goal (classify
operations safe-concurrent vs must-serialise; serialise the OPERATION, not the agent),
extended 4,204 → 7,296 chars; #92 and #103 joined it. New positive result recorded: the
safe method already exists — per-run temp tree + `$HOME` redirect. Three must-serialise
operations named, none mechanically enforced. One cheap measurement outstanding: two
concurrent `--mutate .` runs.

**⛔ WAITING ON YOU:** whether to fold F1/F2 now as a small slice (2 manifest entries +
2 cases, `EXPECTED_MUTATIONS` 23 → 25, rising) or leave them filed; and whether the
product-level races #17/#19/#20 should join the concurrency-safety bundle.

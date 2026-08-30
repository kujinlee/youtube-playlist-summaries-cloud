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


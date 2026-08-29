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

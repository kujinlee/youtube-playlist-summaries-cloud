<!-- codex-review: model=gpt-5.5 -->

**Blocking**
Claim attacked: “No user installs anything, so no user lacks it, so **there is no fallback renderer** — nothing to build, nothing to test, nothing to rot.” ([spec:162-166](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:162))

What I checked: `scripts/explainer-serve.py` serving rules at [scripts/explainer-serve.py:660-668](scripts/explainer-serve.py:660), delivery contract at [.claude/skills/shared/explainer-delivery.md:33-36](.claude/skills/shared/explainer-delivery.md:33), and `npm pack mermaid@11.17.2`.

Verified: the server can serve `.js` only when the file exists under `~/explainers`; a plugin-bundled file is not automatically served from the plugin install directory. `/src/` cannot be used as a script URL because non-raw source files are wrapped in HTML at [scripts/explainer-serve.py:655-659](scripts/explainer-serve.py:655). The shared delivery rule still says generated HTML must be self-contained with no network access.

Inferred: the spec has silently introduced a new asset-deployment requirement: copy or symlink `mermaid.min.js` into the served root, set a stable URL, test MIME, and define what happens when that asset is missing. The “no user lacks it” conclusion is false unless that delivery path exists and is checked. The plain-text “Mermaid unavailable” message is not a renderer fallback, but it is still a required failure path and must be exercised.

**Blocking**
Claim attacked: “Request state is derived by comparing `questions.md` entries against pages that exist in `~/explainers`.” ([spec:285-286](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:285))

What I checked: server question writer at [scripts/explainer-serve.py:476-488](scripts/explainer-serve.py:476).

Verified: `POST /questions` appends only timestamp, `doc`, and free-form text. It does not create a request id, request type, requested skill, target output filename, or status field.

Inferred: comparing question blocks to existing pages is ambiguous and will misclassify. Two requests can have the same text, one page can answer several requests, and a page can exist for unrelated reasons. The dashboard’s “waiting/done” list needs an explicit request identity and answer marker; otherwise the honest-state claim is not implementable.

**High**
Claim attacked: “`check-explainer-delivery.py` | `dashboard` is absent from `PAGE_SKILLS`, or the skill restates the delivery loop” ([spec:298-299](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:298))

What I checked: [scripts/check-explainer-delivery.py:49-53](scripts/check-explainer-delivery.py:49), [scripts/check-explainer-delivery.py:73-95](scripts/check-explainer-delivery.py:73), and ran `python3 scripts/check-explainer-delivery.py`.

Verified: `PAGE_SKILLS` is hardcoded to `["explain-diff", "brief", "explain-findings", "explain-topic"]`. The audit checks only those skills for citation. It scans all skills for restated command blocks, but it does not discover “this skill produces a page” and cannot fail merely because `dashboard` is absent. The check currently exits green.

Inferred: the §9 mechanical check is overstated. It will only catch dashboard omission after somebody manually adds `dashboard` to `PAGE_SKILLS` or adds a separate discovery rule.

**High**
Claim attacked: “Counts are derived by `gen-backlog-page.py`’s existing parser, not re-counted.” ([spec:208](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:208))

What I checked: ran `python3 scripts/gen-backlog-page.py`, `python3 scripts/gen-backlog-page.py --self-test`, and imported `parse()` directly.

Verified: `gen-backlog-page.py` currently refuses to rebuild: `GROUPS does not cover the open set — open items missing from GROUPS: [66]`. `build()` raises on that at [scripts/gen-backlog-page.py:781-784](scripts/gen-backlog-page.py:781). Direct parser import reports `rows 66`, `open 49`, `closed 17`, `open_missing [66]`.

Inferred: the dashboard cannot safely treat backlog counts/diagram as a clean reusable source today. If it imports only `parse()`, it bypasses the existing page’s loud “GROUPS out of date” refusal. If it shells out to the generator, it inherits a current failure. Either way this needs explicit behavior in the spec.

**High**
Claim attacked: “This holds because a dashboard is a **live view**… nobody archives it, so `explainer-delivery.md` §2’s ‘opens on its own in five years’ requirement is not in play.” ([spec:186-189](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:186))

What I checked: delivery contract at [.claude/skills/shared/explainer-delivery.md:33-36](.claude/skills/shared/explainer-delivery.md:33) and existing server standing-page behavior at [scripts/explainer-serve.py:380-417](scripts/explainer-serve.py:380).

Verified: the shared rule makes self-contained/offline rendering a blanket rule for generated HTML pages. The server supports standing pages, but that code does not distinguish “archival” vs “live” for dependency policy.

Inferred: the spec reverses a live delivery invariant by assertion. If standing pages are allowed external local assets, that is a new class in the delivery contract and needs to be changed there, not waived inside this spec.

**Medium**
Claim attacked: “Nothing here is being rebuilt.” ([spec:38](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:38)) and “gathers facts: … milestone state … git activity … open requests.” ([spec:234](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:234))

What I checked: `gen-goals-page.py` docstring and parsing functions at [scripts/gen-goals-page.py:18-29](scripts/gen-goals-page.py:18), plus `parse_milestones()` at [scripts/gen-goals-page.py:95-118](scripts/gen-goals-page.py:95).

Verified: `/goals` is already explicitly “a dashboard” over goals, deriving milestone state, ADR status, backlog rows, and git activity. The dashboard spec says a new `gen-dashboard.py` will gather milestone state and git activity again.

Inferred: unless `gen-dashboard.py` imports shared functions from `gen-goals-page.py` or the functions are factored into a common module, this becomes a fourth status surface with duplicate derivation logic. §2’s “addition, not a new system” is not yet earned.

**Medium**
Claim attacked: “a day with commits but no written entry shows a bar with nothing under it — the gap is visible instead of invisible.” ([spec:226-228](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:226))

What I checked: no implementation exists; checked the stated data sources in §5.2 and §6.

Verified: the activity chart is specified as commit-derived; entries are manually written.

Inferred: this mitigation only makes one failure visible after the fact. It does not prevent the assistant from skipping entries, does not catch uncommitted work, and does not tell the user what happened on a commit-only day. For the stated problem, “the user cannot hold the thread across days,” a visible blank under a bar is at best an alarm, not a recovery mechanism.

**Medium**
Claim attacked: “It fails if the user opens the dashboard after two days away and still has to ask ‘what happened?’ in chat. That is the observation that falsifies this design.” ([spec:290-292](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:290))

What I checked: §9 mechanical checks at [spec:294-305](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:294).

Verified: the spec admits the checks do not measure comprehension.

Inferred: the falsifier is real as user feedback, but weak as an acceptance criterion. It is not attributable: failure could mean stale entries, too many folds, missing glossary, no rendered Mermaid, bad prioritization, or simply that the user wanted more context. The spec needs smaller observable criteria, such as “dashboard shows last changed date, current branch, latest entry date, pending user decisions, and every commit-day without an entry.”

**Low**
Claim attacked: “Current page sizes | brief 67 KB · goals 71 KB · backlog-table 477 KB” ([spec:156](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:156))

What I checked: `ls -l ~/explainers/...` and direct `stat`.

Verified: current files are: brief `69049` bytes, goals `81525` bytes, backlog-table `488855` bytes. In KiB, that is about 67.4 KiB, 79.6 KiB, and 477.4 KiB.

Inferred: brief/backlog are effectively KiB numbers mislabeled KB, but goals is stale by about 8.6 KiB. Not design-breaking, but this is exactly the document’s “measured claims drift” failure mode.

**Low**
Claim attacked: “serves `~/explainers` only” ([spec:42](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:42))

What I checked: optional source root at [scripts/explainer-serve.py:99-103](scripts/explainer-serve.py:99), [scripts/explainer-serve.py:309-315](scripts/explainer-serve.py:309), and `/src/` handling at [scripts/explainer-serve.py:646-659](scripts/explainer-serve.py:646).

Verified: primary pages are served from `~/explainers`, but the server also has an optional read-only `/src/` root controlled by `EXPLAINER_DOCS_ROOT`.

Inferred: “serves `~/explainers` only” is stale shorthand. Security-wise the confinement still uses `safe_path`, but the spec should not make an absolute claim that the code no longer satisfies.

**Low**
Claim attacked: “Any chart beyond the four in §5.” ([spec:73](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:73)) versus “Five graphics (§5).” ([spec:60](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:60))

What I checked: §5 headings at [spec:103-206](docs/superpowers/specs/2026-08-28-project-dashboard-design.md:103).

Verified: §5 names progress, activity, health, work-flow, Mermaid, and backlog. Depending on whether Mermaid/backlog are counted as graphics, the document says both four and five.

Inferred: this is not fatal, but it signals unsettled scope. For a page meant to reduce cognitive load, ambiguity over how many visual elements ship in v1 matters.

NOT CONVERGED

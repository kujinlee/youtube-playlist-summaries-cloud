<!-- codex-review: model=gpt-5.5 -->

**Blocking · Task 5 Step 3, [plan:699](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:699) · `decision_errors` for `heads-up` is never called**

What is wrong: Task 5 says it consumes `decision_errors`, but the proposed `worth_html` loop only calls `unresolved_heads_up(entries)` and renders the first paragraph. A `heads-up` entry containing a live `**Decide:**` block renders as valid.

Why it matters: Spec §4 says a recognized `**Decide:**` in a `heads-up` is malformed. This rebuilds the same “renderer accepts both broken and valid states” class the spec explicitly tried to remove.

Suggested fix: In the `unresolved_heads_up` loop, call `decision_errors(e["plain"], "heads-up")` at call time and render a loud “Could not read one heads-up” row instead of normal prose when problems exist.

**Blocking · Task 6 Steps 1/3, [plan:799](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:799), [plan:848](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:848) · VERIFIED BY EXECUTION · the “missing PR” test fails against the proposed implementation**

What is wrong: The test stubs `gh` with `returncode=1`, empty stderr. `_gh_json` then returns `err == "gh exited 1: "`, which does not contain `"not found"` or `"no pull requests"`, so `pr_state()` returns `"unknown"`, not `"missing"`.

Why it matters: Task 6 cannot reach green as written. Real `gh pr view 999999 --json number,state` in this repo produced `GraphQL: Could not resolve to a PullRequest...`, which also does not match either substring, so the real missing branch is broken too.

Suggested fix: Match GitHub CLI’s actual missing-PR stderr, and make the test stub use that stderr.

**High · Task 3 Step 3, [plan:370](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:370) · VERIFIED BY EXECUTION · `_inert_lines` is not the existing scanner and diverges on HTML comments**

What is wrong: The plan claims parity with `exemption_reason`, but `_inert_lines` only starts comment mode when `line.strip().startswith("<!--")`. `exemption_reason` scans for `<!--` anywhere in the line and continues across lines. A fixture like `x <!--\n**Decide:** hidden\n- a\n- b\n-->\n` is inert to `exemption_reason` but parsed as a real decision by the plan.

Why it matters: This violates spec §4’s HTML-comment inert context and makes a `heads-up` entry fail or a hidden ask render depending on formatting.

Suggested fix: Factor the existing line scanner into a shared helper, or exactly port its inline-comment state machine.

**High · Task 3 Step 3, [plan:421](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:421) · VERIFIED BY EXECUTION · nested list items are counted as separate options**

What is wrong: `OPT = r"^\s*[-*+]\s+"` accepts any indentation, and `decisions()` does not remember the first option indent. Running the proposed parser on `**Decide:** Q\n- parent\n  - child\n- second\n` returns three options: `parent`, `child`, `second`.

Why it matters: Spec §4 says list items indented more than the first option are continuation text, not new options. The tray can misstate the user’s choices.

Suggested fix: Track the first option’s indent column and only start new options at that indent or less; append deeper list lines to the previous option text.

**Medium · Task 2 Step 7, [plan:265](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:265) · VERIFIED BY EXECUTION · the stated before measurement is wrong**

What is wrong: The plan’s measurement command searches `class="flag ">needs you<`, but current `scripts/gen-dashboard.py:768` emits `class="flag">needs you</span>` with no space. Running the command at commit `7417264` prints `0 / 0 / True`, not the claimed `3 / 0 / True`.

Why it matters: The evidence step does not actually prove the reported contradiction before the fix.

Suggested fix: Change the before/after probe to count both `class="flag">needs you<` and `class="flag ">needs you<`, or parse the HTML less brittlely.

**Medium · Task 6 Step 5, [plan:917](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:917) · repo slug lookup runs on every `build()`**

What is wrong: `_repo = repo_slug()` is inserted immediately after `REC_SPAN`, before knowing whether any option contains `PR #N`. That calls `gh repo view` for renders with zero PR options and outside the PR cache/budget.

Why it matters: A no-PR dashboard render now depends on `gh` latency/auth state. It also weakens the “bounded render” guarantee because the repo lookup is not counted in the 10-call/60-second budget.

Suggested fix: Resolve `repo_slug()` lazily only after the first `PR_TOKEN` match, and include it in the same render budget or give it a separate explicit bound.

**Low · Task 5 Step 4, [plan:725](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:725) · VERIFIED BY EXECUTION · a fenced `python` block is not Python**

What is wrong: The template insertion snippet is fenced as `python` but contains raw HTML plus `...`; `ast.parse` fails.

Why it matters: The plan tells reviewers and implementers to execute code blocks. This one is intentionally not executable but mislabeled.

Suggested fix: Fence it as `html` or plain text.

**Low · Task 4/5 tests, [plan:524](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:524), [plan:663](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:663), [plan:671](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md:671) · some “failing tests” pass before implementation**

What is wrong: Before Task 4, “a cleared ask is never validated” and “and it is not marked broken” already pass. Before Task 5, “it is NOT inside the fold” and “no heads-ups means no heading” already pass.

Why it matters: These cases are useful regression guards, but they are not red-phase evidence. A fresh implementer could treat the red/green claim as stronger than it is.

Suggested fix: Mark those as regression assertions, not expected initial failures, and add one red assertion for each branch they are meant to guard.

NOT CONVERGED

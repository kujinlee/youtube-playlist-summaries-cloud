<!-- codex-review: model=gpt-5.5 -->

START HEAD: `22baf58496ef55f9da26471312f2fa3193d9f4e2`

**Findings**

**High / Structural — `do_GET` can drop the injection and the suite stays green.**  
Premise: [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:1013) says driving `do_GET` “needs a bound server”, but the same self-test already documents the opposite at [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:2185): “NO PORT IS BOUND”. The shipped call is [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:1279): `body = decorate_html(body)`.

Measurement: I changed that line to `body = body`; `python3 scripts/explainer-serve.py --self-test` still reported `210/210 passed`. I also drove `do_GET` externally with `object.__new__(Handler)` and a stubbed `_send`; a sandbox `.html` response included both `--emph` and `/_rev?p=` with no bound port.

Why High: the actual shipped behavior can be severed while all tests pass. `decorate_html()` is load-bearing as a unit test target, but it is theatre as proof that served pages receive the baseline.

Fix: add a self-test that builds a sandbox `ROOT`, serves `/probe.html` through real `do_GET`, and asserts the response body contains the original bytes, `--emph`, and `/_rev?p=`. Add a mutation entry for `body = decorate_html(body)` -> `body = body` or `body = body + RELOAD_JS.encode()`.

**Medium / Structural — the CSS breaks bold text inside links and other colored contexts.**  
Premise: [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:1001): `b,strong{color:var(--emph, var(--fg2, inherit))}`. The comment claims at [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:984) that `inherit` is “exactly today’s behaviour”.

Measurement: real pages contain links with nested bold, e.g. [docs/explainers/2026-09-23-topic-pr-336-338.fragment.html](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/explainers/2026-09-23-topic-pr-336-338.fragment.html:134) has `<a href="#order">... <b>revised</b></a>`, and [docs/explainers/2026-09-24-brief-velocity-ledger.fragment.html](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/explainers/2026-09-24-brief-velocity-ledger.fragment.html:125) has `<a ...><strong>Development velocity...`. A specified `color` on `b/strong` beats inherited link color from `a`, so those bold words become `--fg2`, not the link accent.

Why Medium: this is a visible regression in affordance/readability, especially because the rule is injected into every served HTML page.

Fix: either scope the baseline to prose contexts that are not inside links, or add an override such as `a b,a strong{color:inherit}` after the baseline. Also reconsider locally colored containers: `--fg2` is a root-ish token, not “today’s inherit” when a parent intentionally sets another color.

**Low / Structural — the “BARE b,strong” test does not test bare.**  
Premise: [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:1731) names “BARE b,strong”, but asserts only `"b,strong{" in BASELINE_CSS and "." not in BASELINE_CSS.split("{")[0]`.

Measurement: evaluating the case against `<style>a b,strong{color:var(--emph, var(--fg2, inherit))}</style>` returns `True`. So `"." not in ...` only constrains “no class dot before the first `{`”; it does not reject ancestor selectors, IDs, attributes, pseudo-classes, or higher element specificity.

Why Low: it weakens the cascade-safety proof, though not the runtime rule as currently written.

Fix: parse or exactly match the selector, e.g. assert the style text contains exactly `<style>b,strong{...}</style>` or extract the selector before `{` and compare to `b,strong`.

**Low / Transitional — the new comment block splits the `RELOAD_JS` comment from `RELOAD_JS`.**  
Premise: the live-reload explanatory comment starts at [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:955), but the new baseline block begins at [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:966), while `RELOAD_JS` is not defined until [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:1021).

Measurement: direct line inspection.

Why Low: readability defect only, but it makes a long, evidence-heavy comment appear to introduce the wrong constant.

Fix: move the baseline block above the live-reload block, or move the live-reload comment down immediately above `RELOAD_JS`.

**Other Measurements**

`python3 scripts/explainer-serve.py --self-test` passed: `210/210 passed`.  
`python3 scripts/check-plan-code.py --self-test` passed: `131/131 passed`.

Manifest: parsed `master:scripts/mutations/explainer-serve.json` and HEAD JSON; 46 prior entries are equal and order-preserved, 2 added. The two added entries at [scripts/mutations/explainer-serve.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/explainer-serve.json:509) and [scripts/mutations/explainer-serve.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/explainer-serve.json:520) were killed by exactly their named cases when applied by hand.

Definition order: safe. `decorate_html()` references `RELOAD_JS`, but Python resolves that global at call time; the function is not called before `RELOAD_JS` is assigned in normal import/self-test flow.

File contract: verified no baseline is written to disk. `rg` found `BASELINE_CSS` only in the server code/self-tests, and scanning `docs/**/*.html` found no `--emph`.

Falsifiability of the 8 new cases: the three `decorate_html` cases are falsifiable by dropping CSS, dropping JS, or replacing/prepending the body. The `--emph`, `--fg2`, `inherit`, and `color-mix` cases are string-shape guards. The selector case is only partially falsifiable; it catches a class selector before `{`, but not several realistic specificity regressions.

**Could Not Measure**

`python3 tools/partial-sweep.py scripts/explainer-serve.py` could not run because `tools/partial-sweep.py` does not exist in this checkout. I substituted manual mutation edits and restored the worktree; final `git status --short` is clean.

END HEAD: `22baf58496ef55f9da26471312f2fa3193d9f4e2`

NOT CONVERGED: 0 Blocking · 1 High · 1 Medium · 2 Low

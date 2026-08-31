<!-- codex-review: model=gpt-5.5 -->

**Findings**
- High: [scripts/page_chrome.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/page_chrome.py:229) `assert_wired()` accepts any script that merely contains `"chrome-theme"`.
  Failure scenario: `<script>console.log("chrome-theme")</script>` plus palettes and the button passes, but no click handler exists. I reproduced this with a direct probe.
  Fix: require the actual chrome script, a stable script marker, or specific binding shape like `getElementById('chrome-theme')` plus `addEventListener('click'...)`.

- High: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:212) treats any fragment containing `id="chrome-theme"` as already wired and adds nothing.
  Failure scenario: a fragment with palettes and the button but no chrome script composes to a page with one inert theme control and no generated stamp. I reproduced: `theme controls 1`, `chrome_script present False`, `stamp count 0`.
  Fix: in the `has_control(content)` branch, call `page_chrome.assert_wired(content, ...)` and separately require/preserve a stamp, or make the branch detect a full chrome bar rather than only the button id.

- Medium: [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:2403) `--fragment-only` writes before any `page_chrome.assert_wired()` call.
  Failure scenario: if `build()` regresses to emit a control without palettes/script, normal output is guarded but fragment output ships the dead control.
  Fix: move `page_chrome.assert_wired(frag, "gen-dashboard.py")` before `a.fragment_only.write_text(...)`.

- Medium: [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:437) `index_html()` is a page producer with a theme control but never calls `assert_wired()`.
  Failure scenario: a future edit drops either data-theme palette or the script from the served index; no test/guard at the producer boundary catches it.
  Fix: build into `doc`, call `page_chrome.assert_wired(doc, "explainer-serve index")`, then return/send.

- Medium: [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:990) `scheme_palettes()` overwrites duplicate `:root[data-theme="..."]` blocks instead of cascading them.
  Failure scenario: first dark override sets `--link:#111` on `--bg:#000`, later duplicate block sets only `--ink:#fff`; browser keeps the bad link, parser replaces the whole toggled-dark map with base plus `--ink`, hiding the reachable bad value.
  Fix: accumulate per theme in source order: start from base, merge each matching block into the existing `toggled-{theme}` palette.

- Medium: [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:760) `/regenerate` has no per-page lock or atomic output contract.
  Failure scenario: two tabs POST refresh for the same page; two generators write the same target concurrently. Also, [gen-backlog-page.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:1930) returns 0 after writing a degraded no-Ask-tray fragment when compose fails, so `/regenerate` reports success for a materially degraded rebuild.
  Fix: serialize per page, write to temp and atomically replace, and have regenerate run generators in a strict mode or verify the resulting page invariants before returning 200.

- Low: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:269) writes before the final tray-presence check at line 271.
  Failure scenario: if `has_tray(doc)` fails, the bad output is already on disk despite the failure message saying the composed page was unusable.
  Fix: check `has_tray(doc)` before `out.write_text(...)`.

**Checked**
- `python3 scripts/page_chrome.py --self-test`: `43/43 passed`.
- `python3 scripts/brief-compose.py --self-test`: `38/38 passed`.
- `python3 scripts/explainer-serve.py --self-test`: `71/71 passed`.
- `python3 scripts/check-plan-code.py --self-test`: `158/158 passed`.
- `python3 scripts/check-plan-code.py --mutate .`: `105 mutation(s), 0 survivor(s)`.
- Manifest count verified: total `105`; `page_chrome` manifest has `11`; `EXPECTED_MUTATIONS` sums to `105`.

No command-injection path found through `/regenerate`; non-string, unknown, Unicode, and long page values do not reach argv because lookup is literal and type-gated. Browser execution of `chrome_script()` was NOT CHECKED; I only reviewed/probed it statically.

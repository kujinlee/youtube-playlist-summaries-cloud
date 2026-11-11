<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 08ffe5d69223002e7ad8aae1241d6f269e83782e

1. **P1 — Actual `/features` output contains 29 nested anchors.** `scripts/page_markup.py:365`, consumers at `scripts/gen-features-page.py:422` and `:433`.
   
   The feature generator wraps `inline_md(text)` in an existing link; the newly enabled key rendering inserts another anchor. Built output includes:
   ```html
   <a href="/backlog-table#i45">#45 … when
   <a href="https://github.com/kujinlee/youtube-playlist-summaries-cloud/pull/98">PR #98</a>
   merged</a>
   ```
   HTML5 parsing reports 29 `unexpected-start-tag-implies-end-tag` errors and 29 corresponding unexpected closing anchors. Browsers close the outer link early, leaving part of the row label outside its link. `link_html` preserves this malformed output, and rule 1 passes it. Apply the dashboard’s unlinked-inline treatment to these consumers and test the emitted artifact.

2. **P2 — A legal quoted `>` causes attribute corruption.** `scripts/page_markup.py:207`.
   
   Input:
   ```html
   <p title="x > backlog #7">ok</p>
   ```
   Output:
   ```html
   <p title="x > <a href="/backlog-table#i7">backlog #7</a>">ok</p>
   ```
   `TAG_SPLIT` stops at the first `>` without respecting quotes. The inserted `href` quotes terminate the original attribute and change the parsed DOM. This affects `title`, `data-*`, `href` and ARIA attributes alike. Rule 1 returns no violations for this corrupted output.

3. **P2 — Verbatim regions reset link/code nesting state.** `scripts/page_markup.py:223` and `:232`.
   
   Input:
   ```html
   <a href="/x">before<!-- c -->backlog #7</a>
   ```
   Output:
   ```html
   <a href="/x">before<!-- c --><a href="/backlog-table#i7">backlog #7</a></a>
   ```
   Each side of the comment is processed with a fresh `depth = 0`. A comment inside `<code>` similarly causes literal text to become linked. A `<style>` region inside an anchor produces the same nested-anchor failure. Preserve parser state across skipped regions.

4. **P2 — The delivered pages violate the required fragment-resolution invariant.** `scripts/page_markup.py:180`; `docs/backlog.md:451`.
   
   Building all five pages succeeds, but checking them returns exit **1** with **13 distinct page→target failures** across missing rows **221, 241, 242, 245–248, 293 and 411**. For example:
   ```text
   backlog #241 → href="/backlog-table#i241" → no matching target id
   ```
   Row 470’s completion prose also supplies new citations that become dangling links. Describing these as data problems does not satisfy §6 row 1’s explicit requirement that generated fragments resolve. Correct the citations or define and implement unknown-key handling before marking this complete.

   CI currently cannot catch this: `.github/workflows/ci.yml:809` runs only `--sources`. The stated obstacles—authenticated inputs and a local goal-tree log—explain why the current live `--build` cannot simply run in CI. They justify providing deterministic build fixtures and artifact checks, rather than leaving rules 1 and 3 unenforced there.

5. **P2 — Rule 2 exempts production code following a self-test definition.** `scripts/check-page-links.py:83`.
   
   Concrete input:
   ```python
   def self_test(): pass
   def main():
       return "/goals#" + slug
   ```
   `built_hrefs("x.py", source)` returns **`[]`**. The exemption discards the entire remainder of the file, including production entrypoints. Independently, `href = "/goals" + "#" + slug` also returns `[]`, while the comment `# See /goals#slug` falsely fails. The documented literal-matching bound does not justify exempting production functions; identify test bodies structurally.

6. **P2 — Linker and rule 1 disagree about visible keys and exempt content.** `scripts/page_markup.py:241`; `scripts/check-page-links.py:68`.
   
   Both inputs remain unchanged after `link_html`:
   ```html
   <p>backlog &#35;7</p>
   <p>backlog <b>#7</b></p>
   ```
   Both display `backlog #7`, and rule 1 reports them as unlinked. Conversely, `<textarea>backlog #7</textarea>` is intentionally preserved by the linker but incorrectly fails rule 1 because its exemption list omits `textarea`. Share HTML text-node semantics between rendering and checking.

7. **P2 — Rule 3 accepts nonexistent IDs found inside script strings.** `scripts/check-page-links.py:76` and `:101`.
   
   Input:
   ```html
   <script>const x = 'id="fake"';</script>
   <a href="#fake">x</a>
   ```
   `dangling({"goals": input})` returns **`([], 0)`**, although the DOM contains no element with that ID. Regex scanning also treats attribute-like strings in comments as declarations. Read IDs and hrefs from parsed elements.

Validation: all ten changed suites’ `--self-test` commands ran. Nine passed; `check-plan-code` passed **278/281**, with all three failures caused by missing local `node_modules/typescript`. `--sources` passed. All five pages built; every emitted inline script passed `node --check`. No duplicate IDs appeared in those artifacts. No files under `.claude/plans/` were read.

VERDICT: NOT CONVERGED

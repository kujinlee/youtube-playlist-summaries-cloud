# Phase 6 architecture review — backlog #616 — `brief-compose` decision-scan

- **Subject:** `_DecisionScan` and `render_decisions` in `scripts/brief-compose.py`.
- **Where reviewed:** worktree `agent-af12d5dac01fa01be`, branch `603-decision-tags`, HEAD `096f1f04` (PR #563).
- **Mode:** read-only. I edited nothing in the repository. The probes and the prototype are in the scratchpad, under `p6/`.
- **Read first:** `CONTEXT.md`, ADR-0015, and every 603 review record (r1 to r4, all three writers). No ADR is re-litigated here.
- **Self-test:** `python3 scripts/brief-compose.py --self-test` → **226/226 passed** (4.4 s).

## Verdict

**The thrashing is structural. Another patch will not close it.**

- The scanner is a **denylist model of visibility**: it re-implements part of the HTML tree builder and part of the browser's rendering rules.
- It fails **open** on anything it does not model. Every round added a member to the list, and the next round found another one.
- The probes below find **18 more fail-open shapes** beyond the r3/r4 list. **12 of them involve no misnesting at all**, which contradicts the docstring's bound.
- Neither a real HTML parser nor a longer denylist removes the class.

**Recommended redesign:** **fail closed by grammar**, and let **the browser own what only a browser can see.**

- **Static half (stdlib Python).** Use allowlisted hosts, containers and attributes, and require strict explicit nesting. It needs no model of the parser at all.
- **Browser half.** Add a small in-page `checkVisibility()` self-check that turns the counter red. Automated rendered checks fold into backlog #387.

The repository has already made this exact decision once, for this exact class of defect. The 2026-10-27 em-guard architecture review cut the static guard down to the half that can be decided from text and gave the rendered half to a browser (backlog #387; `docs/reviews/architecture-review-2026-10-27-em-guard.md:17-30`). ADR-0015 resolved its own thrashing the same way, by restricting what is allowed rather than chasing paraphrase shapes.

## Method

1. **Composer side.** `p6/probe.py` loads the module and runs `render_decisions` on each fragment, recording COUNT or REFUSE.
   - For refused fragments it re-runs with refusals cleared, so the oracle can tell a correct refusal from a false one.
2. **Oracle.** `p6/oracle.js` loads the output in **real Chromium** (Playwright 1.60.0, `chromium-1223`, under `<!doctype html>`). For each inserted `span.ex-decision` it evaluates `checkVisibility({checkOpacity, checkVisibilityCSS})` and requires a non-zero box.
3. **Corpus.** The 34 `docs/explainers/*.fragment.html` were measured with `p6/strict*.py` and `p6/allow.py`.

## Findings

### P6-1 — STRUCTURAL (Major in kind, low exposure) — the denylist is an open set: 12 well-formed shapes are counted and not seen

- **Where:** `scripts/brief-compose.py:1128` (`_DECISION_REFUSE_INSIDE = {"template","noscript","select","datalist"}`), `:1130` (`_DECISION_HIDING_ATTRS = {"hidden","inert"}`), and the ancestor loop in `handle_starttag`.
- **Evidence:** the oracle verdict for every row below is **SILENT-COUNT, `COUNT 1`, `UNSEEN`**. None of the shapes is misnested.

| Mechanism | Fragment |
|---|---|
| UA-hidden element | `<dialog><p data-decision>…</p></dialog>` |
| Hiding attribute not in the list | `<div popover><p data-decision>…</p></div>` |
| Fallback content not rendered | `<canvas>`, `<video>`, `<audio>`, `<object data=… type=image/png>` around `<p data-decision>` |
| Children not rendered | `<meter>`, `<progress>` around `<span data-decision>` |
| UA `display:none` | `<ruby>a<rp><span data-decision>…</span></rp>…` |
| **Retroactive** attribute merge onto an ancestor | `<p data-decision>before</p><body hidden>`, and the same with `<html hidden>` |
| Declarative shadow DOM (unslotted light child) | `<div><template shadowrootmode="open">…</template><p data-decision>…</p></div>` |

- **Exposure:** a grep of the 34 fragments for `<dialog|popover|<canvas|<object|<video|<audio|<meter|<progress` finds **0**. That is why this is not a BLOCKER.
- **Why it is structural:** each row is one more set member. r1 added the `REFUSE_*` sets, r2 the `<details>` handling, r3 `svg`/`math`. The HTML standard keeps adding hiding mechanisms (`popover` arrived in 2024; `hidden=until-found`), so a denylist can never be complete.
- **Remedy:** redesign (below), not a patch.

### P6-2 — STRUCTURAL (Major in kind, low exposure) — CSS hiding is outside the model, and no static parser can see the class-rule half

- **Evidence:** all five rows are **SILENT-COUNT, UNSEEN**:
  - `<div style="display:none">…`
  - `<div style="visibility:hidden">…`
  - `<div style="content-visibility:hidden">…`
  - `<style>.c{display:none}</style><div class="c"><p data-decision>`
  - `<style>.ex-decision{display:none}</style><p data-decision>`
- **The bound omits it:** the module's stated rule (`:1113`, *"A DECISION THE OWNER CANNOT SEE MUST NOT BE COUNTED"*) never mentions CSS or script.
- **What each remedy reaches:**
  - A grammar can refuse a `style` attribute on the chain.
  - Only a browser can evaluate class rules and the fragment's own script.
  - This is the #387 boundary, reached a second time.

### P6-3 — Minor (pre-existing, same root as r3 F2) — the misnest list is not closed either: a 7th shape

- **Fragment:** `<span hidden><p>x</span><b data-decision>after</b>`
- **Result:** SILENT-COUNT, UNSEEN.
- **Browser behaviour:** the browser *ignores* `</span>`, because a special element (`p`) sits above it on the stack.
- **Scanner behaviour:** `handle_endtag` (`:1307-1311`, `del self._stack[i:]` on the nearest same-named entry) pops through it.
- **Prototype check:** my own first prototype, which allowed popping past optional-end-tag elements, also counted this shape. That is evidence that **any** rule which emulates end-tag recovery re-enters the class.

### P6-4 — Minor (doc) — the docstring's bound is false as written

- **Where:** `:1221-1229` says the silent counts are MISNESTED shapes: *"Every such shape is hostile misnesting; no real fragment has one."*
- **Why it is false:** P6-1 and P6-2 add 17 shapes that are well-formed. If the bound is kept, it must say *"anything this model does not enumerate"*.

### P6-5 — Low (friction direction; acceptable) — false refusals, for the record

The oracle reports FALSE-REFUSE (the scanner refuses, the browser shows the tag) for:
- `<ul><li hidden>x<li data-decision>`
- `<dl><dt hidden>x<dd data-decision>`
- `<a hidden href=1>x<a data-decision href=2>`
- `<table hidden>…<p data-decision>` (foster-parented out of the table)
- `<p hidden>x<table>…<td data-decision>` (the documented quirks-mode omission)
- `<div hidden style="display:block">`

The model is wrong in **both directions**. That is the same signature the em-guard review recorded before it cut the guard down.

### Aside, not this subject

`markup_of` is defined twice in `scripts/brief-compose.py` (`:259` and `:361`). The second one silently overrides the first, and the docstrings differ. I did not examine it further. It may deserve its own row.

## Candidate redesigns, weighed

**Repository constraints, measured:**
- `brief-compose.py` and `page_chrome.py` use the standard library only (imports at `:59-74`; `page_chrome.py:80-87`).
- `html5lib` is not installed (`ModuleNotFoundError`).
- `parse5@7.3.0` is present only as a transitive dependency of `jest-environment-jsdom`/`jsdom`. `npm ls` flags it extraneous/invalid in this worktree. It is not a direct dependency.
- CI's `brief-compose self-test` step (`ci.yml:456-457`) runs in a job that has `npm ci` (`:361`).
- No workflow runs `playwright install` (grep returned nothing), so CI has no browser.
- Locally, `~/Library/Caches/ms-playwright/chromium-1223` exists.
- Nothing else in `scripts/` calls `_DecisionScan` or `render_decisions`.

| Option | What it removes | What it leaves | Cost / constraint | Verdict |
|---|---|---|---|---|
| **A. Real HTML parser** (html5lib via pip, or parse5 via a `node` subprocess) | The tree-construction subset: the 6 misnests from r3/r4, P6-3, the `<body>`/`<html>` merge, probably shadow DOM. About 9 of the 23 silent counts. | dialog, popover, canvas, video, audio, object, meter, progress, rp, and all CSS (14 of 23). A visibility **denylist over the parsed tree** is still needed, so the class survives as rendering semantics. | A new pip dependency (CI and portability), or a Node subprocess in a stdlib composer, relying on a transitive package nobody pinned. | **Reject.** It moves the thrashing from parse rules to render rules. |
| **B. Restricted grammar** (allowlist + strict nesting, refuse anything else) | Every HTML-structural shape. Unknown and new elements fail **closed**. All parser emulation goes. | CSS class rules and script (P6-2, the class-rule half). | Stdlib, about 70 lines. Measured corpus cost: 0 (below). | **Adopt as the static half.** |
| **C. Real browser at compose time** (Playwright `checkVisibility`) | Everything, CSS and script included. | Nothing in kind. | Chromium plus Node in a stdlib composer that skills invoke. Not installable in CI today. Slower. | **Defer to #387.** It is the right *automated* instrument, but it is the wrong place for a hard dependency. |
| **D. In-page runtime self-check** (the reader's browser is the oracle) | Everything visible at load, CSS and script included, at the moment the owner reads. | Pages read with JavaScript off (the static half B still holds there). No compose-time failure. | About 20 lines of JavaScript in the composed page, plus a case asserting the emitted script parses (`node --check`; Node is in the CI job). | **Adopt as the browser half.** |

## Recommended redesign — B + D, with #387 owning automation

### Static half: `_DecisionScan` replaced by an allowlist scanner

A prototype was run; it is in the scratchpad (`p6/allow.py`, `p6/strictest.py`). It is not repository code. The rules:

1. **Hosts.** A mark may sit only on an allowlisted element: `p div span h1-h6 li td th dt dd blockquote section article aside header footer main figcaption b strong em i code small label`.
2. **Containers.** Every open ancestor must be in `HOSTS ∪ {ul ol dl table thead tbody tfoot tr figure nav a u s mark sub sup abbr cite q time kbd samp var}`.
   - Anything else is refused, with the element named: `dialog`, `details`, `object`, `canvas`, `video`, `svg`, `math`, `select`, `template`, `noscript`, custom elements, and future elements.
3. **Attributes.**
   - Prototype: no `hidden`, `inert`, `popover` or `style` on the host or the chain.
   - Better: an **attribute allowlist** (`class id title lang dir data-* aria-* role colspan rowspan scope href`), so new hiding attributes also fail closed.
   - Measured chain attributes in the corpus: only `class`, `data-decision` and `data-decision-label`.
4. **Strict nesting.** An end tag must close the **top** of the stack. Anything else (popping past any element, or a stray end tag) marks the document *misnested*, and every mark **after** that point is refused with *"close every element explicitly"*.
   - Start tags never pop the stack. A browser's implicit close can then only remove a non-hidden ancestor, so the stale stack errs toward refusal **by construction**. That is the property the r2 docstring claimed and r3 F2 refuted for the old design.
   - Self-closing `/>` is honoured only inside `svg`/`math` (which are refused as hosts and containers anyway). On a non-void HTML element it should be refused rather than treated as void, because `<div hidden/>` opens the div.
5. **Page-level refusals.** Any `<body>`, `<html>`, `<head>` or `<plaintext>`, or any `shadowrootmode` attribute, in a page that carries a decision is refused. These are the only retroactive and swallow-the-rest mechanisms.
6. **Unchanged:** `CDATA_CONTENT_ELEMENTS` (the 3.12/3.14 raw-text parity), id-collision refusal, offset guard, labels, counter, CSS.

**Prototype results:**
- All **18 HTML-structural silent counts are REFUSED**: the 6 from r3/r4, P6-3, and the 12 in P6-1.
- 3 of the 5 CSS shapes are refused (the `style` attribute ones). The 2 class-rule shapes still COUNT; those belong to the browser half.
- **Corpus:** on the whole fragment text, the strictest rule flags 1 of 34 fragments: `2026-10-07-topic-retrieval-fixed-gap-open`, `</tbody>` closing an unclosed `<tr>` at line 296. That fragment has **0 marks**, so it is unaffected.
- The walkthrough still composes **13 decisions**. Every mark's chain is within `div > div > div > table > tr > td`, `div > div > {div, span, h4}`.

### Browser half: in-page self-check

- **What it does:** after `load`, and after the fragment's own script runs (`requestAnimationFrame`), a script checks every `.ex-decision` with `checkVisibility({checkOpacity:true, checkVisibilityCSS:true})` and a non-zero box.
- **On failure:** it rewrites the counter in place to a red state, *"⚠ N counted · K not visible on this page — this counter cannot be trusted"*, listing the K ids.
- **Why it fits:** the delivery doc requires static markup that is correct with JavaScript off, with *"a small script"* sharpening it (`.agents/skills/shared/explainer-delivery.md:304`). The static counter stays derived and B-sound, and the script turns any CSS or script hiding from silent into loud.
- **Automation:** a headless, compose-time or CI version of the same assertion belongs to **#387**. It is the same instrument (drive the composed page in Chromium), so extend that row rather than filing a third.

### What the redesign deletes

- **Constants:** `_DECISION_REFUSE_ON` (replaced by `HOSTS`), `_DECISION_REFUSE_INSIDE`, `_DECISION_REFUSE_FOREIGN`, `_P_CLOSERS`, `_P_SCOPE`, `_FORMATTING`, `_DETAILS_REFUSAL`.
- **Machinery:** `_close_p`, the `<details>`/`<summary>` state (`collapsed`, summary-seen) and its four refusal branches, and most of the 1113-1311 comment block.
- **Size:** roughly 200 lines become about 70.

### Cost and behaviour changes

- **Deliberate re-refusals (owner-visible friction, all fixable by the author):**
  - `<p hidden>h<div data-decision>` — r2 X3's fixed case — is refused again: *"close the hidden <p> explicitly"*.
  - A mark on a `<summary>` is refused.
  - Marks after any misnesting are refused.
- **Self-test:** about 10 decision-scan cases (`:3041-3110`) are rewritten; their expected values flip for X3 and `<summary>`.
- **Mutations:** about 22 decision-related entries of the 94 in `scripts/mutations/brief-compose.json` are retired or replaced (a rough regex count).
- **New cases:**
  - the 23 silent-count fragments above as negatives;
  - adjacent positives: the same shapes, closed explicitly or with an allowlisted element;
  - an independent-copy case for the allowlist (per the class-fix memory);
  - `node --check` on the emitted self-check script.
- **Falsifier for this design:** **if any fragment shape passing B's static rules, with no `class` or `style` on its chain, renders a tag that `checkVisibility()` reports hidden, the static half is unsound.** In that case, refute the allowlist; do not add a denylist member.

## What I found sound

- **Counting:**
  - The **derived-never-typed** counter: one list feeds `n of N`, total, remaining and next.
  - Answer, label and whitespace handling.
  - Escaping.
  - Id namespacing and collision refusal.
  - The `_decision_offset` position guard.
- **Parity:** the raw-text parity across Python 3.12 and 3.14 (`CDATA_CONTENT_ELEMENTS`) and the `<plaintext>` handling.
- **Other parts of the change:**
  - The `DECISION_CSS` contrast checks (r2 X4 fold), and the emitted-only-when-needed rule.
  - The r2 decision to **remove** the `<details>` auto-open rather than patch it. That is the right instinct, and this redesign applies it to the whole component.
  - All 13 real marks are SEEN in Chromium (the real-corpus rows in the probe).
  - The 33 decision-free pages are byte-identical (recorded by r3 and r4; not re-run here).
- **What none of this reaches:** detecting *unmarked* decisions is backlog #615, a judgement about prose.

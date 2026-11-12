Reviewed head: 4699e55a79d956034f99271179f8a92440ec0a70

# 603-decision-tags — round 1, Claude half (adversarial)

**Subject:** PR #563, branch `603-decision-tags`, head `4699e55a`, diff `origin/master...HEAD`.
**Mandate:** refute. **Reviewer:** Claude (fresh subagent), 2026-11-11.

## What was run

| Check | Result |
|---|---|
| `python3 scripts/brief-compose.py --self-test` (3.14.4) | 207/207 |
| same, under `/usr/local/bin/python3.12` (the CI pin, `ci.yml:94`) | 207/207 |
| Byte-identity: every `docs/explainers/*.fragment.html` that has a page (32) composed with `origin/master`'s `brief-compose.py` and with the branch's, same tray, fixed stamp | **31 identical, 1 differs** (the walkthrough, the only fragment with `data-decision`) |
| Committed walkthrough page against a fresh recompose of its fragment | identical apart from the provenance stamp |
| The 12 new `603:` mutations, each applied to a copy of `scripts/` (docs symlinked) | **12/12 killed by the case they name** |
| Control for my mutation harness (copy, no edit) | 207/207 (a copy *without* `docs/` fails 1 case, so the symlink is needed) |
| 6 extra mutations of my own | **5 SURVIVED** (F4) |
| Contrast (WCAG, computed from `DECISION_CSS`) | light open 10.72, light done 7.59, dark open 9.77, dark done 7.83 — all pass AA and AAA |
| Rendered in Playwright (Chromium), light and OS-dark, and `data-theme` toggled both ways under OS-dark | colours resolve as declared in all four states; all 11 tags have a non-zero box; counter at y=194, under the title |

Screenshots: `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.playwright-mcp/r603-light-top.png`,
`r603-light-d5.png`, `r603-dark-d7.png` (same directory).

## Findings

### F1 — MAJOR — the walkthrough says "2 remaining", and both "open" decisions were already answered
`docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html:810` (`<h4 data-decision>1 · Is the lopsided evidence acceptable?`) and `:1047` (`<div class="box ok" data-decision>`, approve / push back / redirect).

- **DECISION 7 (Q1, lopsided evidence)** was answered on 11-09: `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md:126` — *"The lopsided evidence is accepted for this milestone. 19:45 … answered by selection card A: accept it now, evaluate deeper later"*, and `:367` *"the 11-09 lopsided-evidence answer stands (§2b)"*.
- **DECISION 11 (approve the spec)** was answered on 11-11 at 05:53: spec `:7` *"Status: SPEC, APPROVED by the owner 2026-11-11 05:53 (walkthrough page)"*, `:138` quotes the owner (*"Had I already approved this? If not, I approve"*); also `docs/goal-threads.md:86` and `docs/dashboard-entries.md:20267`. That spec state is on `origin/master` (`d18167ce`, an ancestor of HEAD).

So the counter the owner reads first — measured on the rendered page: *"✍ 11 decisions on this page · 2 remaining · 9 answered · next: DECISION 7"* — sends them to a question they answered two days ago. This is the failure the feature exists to prevent: a page that asks for the owner's attention when nothing needs it. The renderer is correct; the marks are wrong. Both should carry their answers, e.g. `data-decision="Accepted, evaluate deeper later (selection card A, 11-09)"` and `data-decision="Approved 11-11 05:53"`.

Related, same root cause (marks written from the page, not from the spec): DECISION 8's answer `"Yes, with a harvest axis (D6)"` (`:901`) is out of date. Spec `:148` (§2c, 19:07 and 19:11) widened it: effort (2) is *"Evaluated for SHIPPING as a portable, engine-agnostic CI layer, not only as a harvest"*.

### F2 — MAJOR — owner decisions on the same page carry no tag, so "11 decisions on this page" is also undercounted
`…walkthrough.fragment.html:525-534` and `:557`.

- `:525` is labelled *"C5 is new … two halves, and both need you"*. The corpus half (`:534`) is *"a content review — now deliverable 11, listed as yours"*. It is still open: spec §2c, D11 row, *"our own corpus passes the owner's content review (C5's corpus half)"*.
- `:557` *"the copyright holder … not yet named … a legal name or entity is still yours to give"*.

Neither has `data-decision`. Combined with F1, the counter is wrong in both directions: it shows 2 open questions that are closed, and misses at least 2 owner items that are still open. The counter states completeness ("N decisions on this page"), and nothing checks that claim. At minimum, the re-rendered page has to be correct. A note in the docstring that a decision without the mark is invisible to the counter would help too.

### F3 — MINOR — a decision can be counted and still not be visible at its spot; nothing refuses this
`scripts/brief-compose.py:1147` (`render_decisions`), `:1173` (the tag goes right after the start tag, whatever the element). I ran each case through `render_decisions` (scratch harness `edge.py`). Each is counted in total and remaining:

| Fragment shape | Where the browser puts the tag |
|---|---|
| `<details><summary>…</summary><p data-decision>` | inside a closed `<details>`: hidden. The counter's "next" link is the only way to reach it |
| `<details data-decision><summary>` | the span goes before `<summary>`: it is non-summary content, so hidden while the element is closed |
| `<tr data-decision>` | `<span>` directly in `<tr>`: foster-parented above the table, not at the spot |
| `<option data-decision>` | span markup dropped inside `<option>` |
| `hidden`, `<template>`, `<noscript>` ancestor | not rendered |

No current fragment is affected (0 of 34 use `<details>`), so this is latent. **Interpreter dependence:** under Python 3.12 (CI), `<textarea>`, `<title>` and `<xmp>` content IS counted and tagged (the span is shown as literal text in a textarea). Under 3.14 it is not, because the parser treats those as raw text there. The same fragment gets a different N depending on the interpreter. Cheapest fix: refuse (CANNOT RUN) a mark whose element or ancestor is one of `details/summary/table-section/tr/option/select/template/noscript/textarea/title/xmp`, or one with `hidden`.

### F4 — MAJOR (Mb) / MINOR (the rest) — five behaviours the suite does not pin; mutations survive
Applied to a copy of `scripts/` with `docs/` symlinked. Control 207/207. Each survivor below also ended at 207/207:

| Id | Mutation | Line | Result |
|---|---|---|---|
| **Mb** | the OS-dark `@media` half `:root:not([data-theme="light"])` gets the **light** values | 1110 | **SURVIVED** |
| Mc | `.ex-decision-done` uses `--decide*` (an answered tag renders yellow) | 1121 | **SURVIVED** |
| Ma | counter's "answered" shows `{remaining}` instead of `{total - remaining}` | 1181 | **SURVIVED** |
| Md | `.strip()` dropped: a whitespace-only value counts as ANSWERED with an empty answer | 1143 | **SURVIVED** |
| Me | the "not found where the parser reported it" CANNOT RUN guard replaced by `if False:` | 1164 | **SURVIVED** |

**Mb is the serious one.** The default state for a dark-mode reader is the OS-dark half (no toggle pressed). The case at `:2817` checks only that the `@media` block declares the variable NAMES; the "light and dark differ" case compares `html` with `:root[data-theme="dark"]` and never reads the `@media` block's values. This is the half-live toggle the `DECISION_CSS` comment itself cites as the reason for writing the dark half twice, and the half that is not pinned is the one most readers get. Mc means the green/yellow distinction — the owner's "yellow tag" — is pinned only by class name, not by colour. Ma leaves one of the counter's three numbers free to disagree with the tags.

### F5 — MINOR — two numbering systems collide, and the page's label style rewrites the answer
- Tag numbers run in document order and land on differently numbered D-decisions: **DECISION 5 = D7**, **DECISION 6 = D5**, **DECISION 10 = D9**, and Q1-Q4 become DECISION 7-10. On a page that says "D5" throughout, "DECISION 5" means something else. This makes the tags harder to read, which is what they are for. Consider showing the fragment's own label (e.g. a `data-decision-label="D7"`), or a prefix that cannot be read as a D-number.
- Tags inside `.box .lbl` inherit `text-transform: uppercase` (fragment `:90`). Screenshot `r603-light-d5.png` shows *"DECISION 5 OF 11 — ANSWERED: MIT (D7)"*, so the recorded answer is not shown as written. `.ex-decision` sets `font` and `letter-spacing` but not `text-transform: none`.

### F6 — MINOR — duplicate ids are not checked
`brief-compose.py:1168-1171` emit `id="decision-{n}"` without checking the fragment. A fragment `<p id="decision-1">` composes silently with two `#decision-1` elements, and the counter's link goes to the fragment's element (measured with the `dup-id` case). No current fragment collides (`grep id="decision-` matches only the composed walkthrough).

## Refuted or confirmed clean
- **Counter and tags agree:** both come from one list (`scan.found`). The numbering is document order. Nested marks each count. Attribute values, script and style strings, and comments are not counted.
- **Answer injection:** `html_escape` runs on the parser-unescaped value. `a " &amp; <script>` renders as text, and the mutation that removes the escaping is killed.
- **Pages without decisions are byte-identical** (31/31 real fragments). The CSS ships only when a page has a decision.
- **Contrast** is good in all four theme states. The theme toggle works both ways under OS-dark.
- **Idempotence:** using the decision page as its own tray source recomposes byte-identically.
- **The 12 manifest mutations** each fail the case they name. The pin (58) matches the manifest length.

## Verdict
F1 and F2 are content defects on the one page this PR re-renders as its proof: its headline numbers are wrong. F4-Mb leaves the default dark path unpinned.

VERDICT: NOT CONVERGED

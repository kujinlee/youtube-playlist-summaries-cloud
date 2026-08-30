# Branch review — dashboard prose readability + chart key (PR #178), round 1, Claude half

**Subject:** `feat/dashboard-prose-readability` at `a41e045`, 5 commits, `git diff master..HEAD`.
**Reviewer:** Claude half of a dual adversarial round. Codex half ran independently; no coordination.
**Method:** executed, not read. Control first, then hand mutations against a **copy** of `scripts/`
under `$TMPDIR`. No tracked file was modified and no git command wrote to the working tree.
`~/explainers/dashboard.html` was checksummed before and after every run that could reach it and is
byte-identical (`d22cee7615e602bf90dce824271248c7`, 470659 bytes, before and after).

## Verdict: **NOT CONVERGED**

3 High · 5 Medium · 7 Low. Nothing Blocking: no defect here corrupts data, moves money, or breaks
the page. Every High is a *guard* defect — the branch's three headline behaviours can each be
reverted with the suite green — plus one visible rendering defect the branch set out to fix and
did not.

Control for every mutation below: an unmutated copy of `scripts/` reports **161/161 passed**.

---

## H1 — The prose fold has no wiring case. Reverting the whole feature at the call site is green.

**Severity: High.** `scripts/gen-dashboard.py:660`. **REPRODUCED** (two independent mutations).

```python
f'<div class="prose">{_prose(e["plain"], drop_headline=True)}</div>'
```

Every assertion about paragraphs, ledes, `<strong>` and the dropped headline is made against
`_prose` / `_inline` **directly** — `:1428`, `:1429`, `:1448`, `:1465`, `:1478`. Nothing asserts
that a **built page** contains a `<p class="lede">`. Measured, on a temp copy:

| mutation at `:660` | verdict |
|---|---|
| `{_prose(e["plain"], drop_headline=True)}` → `{_html.escape(e["plain"])}` (revert to master's behaviour) | **SURVIVED 161/161** |
| → `<p>{_html.escape(e["plain"])}</p>` (the exact wall-of-text this branch exists to kill) | **SURVIVED 161/161** |
| → `{_prose(e["plain"])}` (drop_headline dropped at the caller) | **SURVIVED 161/161** |

So reported problem 1 (the wall of text) and reported problem 2 (the repeated headline) can both be
undone in one token, at a fully green suite.

This is not a shape the branch is unaware of — it names it three times and fixes it three times
elsewhere:

- `:1376` *"deleting `{legend}` from the page template SURVIVED all of them at 159/159"* → wiring case added at `:1383`.
- `:1414` *"none of them proves the dict reaches the stylesheet"* → wiring case added at `:1416`.
- `:1492` *"reverting `parse_entries` to the old first-LINE title SURVIVED all of them at 132/132"* → wiring case added at `:1499`.

The one feature that is the branch's title got the comment and not the case. `_section(html, "What
changed")` already exists at `:1028` and is what such a case would use.

## H2 — `**bold**` still prints as literal asterisks in the headline, on this branch's own page.

**Severity: High.** `scripts/gen-dashboard.py:658` (and `:577`). **REPRODUCED** — built the real
page to `$TMPDIR/r178-page.html` with `--fragment-only` and read the HTML:

```html
<p class="title">**Correction to the entry above, after review.** The fix described there was right but its safety net was not.</p>
```

`_inline` is applied to `e["plain"]` and never to `e["title"]`, which goes through
`_html.escape` alone at `:658` and `:577`. Reported problem 1 was *"`**bold**` printed literally
(3/10 entries)"*; it is fixed inside the fold and left standing on the most prominent line of every
card. The store shipped in this same branch (`docs/dashboard-entries.md`) contains a live instance.

There is a second-order effect in the same line. `SENTENCE_END` is `(?<=[.!?])\s+`, and in
`…after review.** The fix…` the `.` is followed by `**`, not whitespace — so the split does not
happen and the headline swallows **two** sentences. Fixing the asterisks fixes the run-on too.

Not a trivial patch, and worth saying so: `:577` puts the title inside `<a href=…>`, where
`_inline`'s autolink would nest an `<a>` inside an `<a>`. A title-specific variant (bold + code, no
autolink) is the shape that works.

## H3 — `_inline`'s two security properties are the two with no falsifier.

**Severity: High** (as a guard defect; the shipped code is **correct** — I could not defeat it).
`scripts/gen-dashboard.py:116`, `:119`. **REPRODUCED.**

I attacked `_inline` with 29 payloads (`$TMPDIR`-side script, output inspected by hand and by
`html.parser`): attribute breakout, `&quot;` re-entry, unbalanced and nested `**`, backticks inside
bold, `</a>` and `</code>` inside spans, `javascript:`, control characters, NBSP. **All are
correctly neutralised as shipped.** Escape-then-mark-up is sound here because the only markup
inserted is `<strong>`, `<code>` and `<a href="…">`, and after `_html.escape` the captured group can
contain neither `"` nor `<`. `&quot;` inside a double-quoted attribute value is a character
reference, not a delimiter — verified by parsing the output with `html.parser`, which reports one
attribute (`href`) and no event handler.

The problem is what holds that up. Two mutations, both one token:

| mutation | verdict | consequence |
|---|---|---|
| `:116` `_html.escape(s)` → `_html.escape(s, quote=False)` | **SURVIVED 161/161** | stored XSS |
| `:119` `(https?://…)` → `([a-z]+:…)` | **SURVIVED 161/161** | `javascript:` hrefs |

The first is a demonstrated breakout. Entry text `https://x.com/"onmouseover="alert(document.domain)" x="`
produces, under the mutant:

```html
<a href="https://x.com/"onmouseover="alert(document.domain)"">…</a>
```

`html.parser` reads that as `{'href': 'https://x.com/', 'onmouseover': 'alert(document.domain)', '"': None}` —
a live event handler, from a file any contributor edits, on a page the author opens.

The existing security case at `:1474` asserts four things — `&lt;script&gt;` present, `<script>`
absent, `<b>` absent, `&amp;` present — and not one of them touches `"` or the scheme. It pins the
property that is not the dangerous one. `quote=False` is a plausible edit: it is what someone
reaches for when `&#x27;` shows up somewhere it should not.

**Reasoning, not reproduced:** I did not run this in a browser. The attribute-tokenisation claim
rests on `html.parser` and the HTML spec, both of which agree.

---

## M1 — The prose AA check measures a Python copy of `--panel`, not the emitted stylesheet.

**Severity: Medium.** `scripts/gen-dashboard.py:48`, cases at `:1399-1403`. **REPRODUCED.**

```python
PROSE_CARD = {"light": "#ffffff", "dark": "#1b2125"}   # `--panel`, what they sit on
```

That is a second statement of `--panel`, and nothing reconciles it with the first. Mutating the
stylesheet's dark `--panel:#1b2125` → `#3a4046` **SURVIVED 161/161**, while the real ratios become:

| role | on the real `--panel` | on `#3a4046` |
|---|---|---|
| `--p-lede` | 13.61 | 8.78 |
| `--p-head` | 9.34 | 6.03 |
| `--p-detail` | 6.72 | **4.33 — below AA** |
| `--p-mark` | 7.22 | 4.65 |

The older link guard in this same file does it correctly: `contrast_failures()` at `:854` reads the
palette **out of the generated HTML** via `scheme_palettes(css)`, which is exactly why it caught
three value mutations that a presence check missed (the comment at `:786` tells that story). The new
prose check reads a dict instead, and the `--p-*` tokens are not in `LINK_FOREGROUNDS` (`:799`), so
neither mechanism covers them. Two contrast mechanisms now exist in one file and the newer one is
the weaker. The branch's own `_legend` docstring (`:509`) states the principle it violates here: *"A
legend with its own copy of the palette is a second source of truth that drifts silently."*

Cheapest fix: derive `PROSE_CARD` from `scheme_palettes(build(...))["light"]["--panel"]` and add
`--p-*` to `LINK_FOREGROUNDS`, deleting the parallel mechanism.

## M2 — `PROSE_CONTRAST_MIN` can be lowered to 1.0 with a green suite.

**Severity: Medium.** `scripts/gen-dashboard.py:60`. **REPRODUCED** — `PROSE_CONTRAST_MIN = 4.5` →
`1.0` **SURVIVED 161/161**.

The sibling constant has precisely this case, twelve lines away:

```python
case("the contrast floor is WCAG AA, not a number someone lowered", CONTRAST_MIN, 4.5)   # :1148
```

`PROSE_CONTRAST_MIN` did not get one. The whole `for _theme…` block at `:1399` is vacuous under a
lowered floor.

## M3 — The new legend's text is below AA in light mode.

**Severity: Medium.** `scripts/gen-dashboard.py:730`. **REPRODUCED** by measurement with the file's
own `_contrast()`.

```css
.legend{…font-size:12.5px;color:var(--fg3)}
```

The legend is emitted **outside** `.chart` (`:777`), so it sits on `body{background:var(--bg)}`:

| theme | `--fg3` on `--bg` | on `--panel` |
|---|---|---|
| light | **4.32** | 4.59 |
| dark | 5.84 | 5.32 |

4.32 < 4.5, at 12.5px. `--fg3` is in neither `LINK_FOREGROUNDS` nor `PROSE_COLOURS`, so no guard in
the file looks at it. The token is pre-existing (`.note`, `.when`, `summary` share it) but this
branch ships **new** text in it — and it is the key that tells a reader an alarm from a decoration,
in a branch whose stated method is *"values chosen by MEASUREMENT… asserted in both themes"*.

## M4 — `.entry .prose code{color:var(--fg)}` names a custom property that does not exist.

**Severity: Medium.** `scripts/gen-dashboard.py:766` (new in this branch). **REPRODUCED.**

The stylesheet defines `--ink`, `--fg3`, `--p-*`, … and never `--fg`. `var(--fg)` with no fallback
is invalid at computed-value time, so `color` becomes `unset`; `color` is inherited, so inline
`<code>` silently takes the surrounding paragraph's colour. The rule does nothing.

Two comments in the same block assert the same non-existent vocabulary:

- `:755` *"the supporting detail recedes to --fg2"* — `--fg2` is not defined anywhere.
- `:757` *"`strong` returns to --fg"* — `strong` is `--p-mark` (`:765`), not `--fg`.

This is the shape the project already has a memory for (*a shim can fail in both directions; a
self-referential CSS var resolves to nothing either way*). A ratchet is cheap: parse
`var\((--[a-z0-9-]+)\)` out of the built page, subtract the properties actually defined by a
`(--[a-z0-9-]+)\s*:` match **outside comments**, assert empty. Note the trap — I wrote that check
naively first and it reported zero, because the comment text `--fg:` at `:757` matched as a
definition.

## M5 — Coverage shrank relative to the file, and the survivors are on the new code.

**Severity: Medium.** `scripts/check-plan-code.py:302-305`, `scripts/mutations/gen-dashboard.json`.
**REPRODUCED** (measured, not inferred).

| | master | HEAD |
|---|---|---|
| `scripts/gen-dashboard.py` lines | 1361 | 1795 (+32%) |
| assertions (`--self-test`) | 120 | 161 |
| manifest mutations | 32 | **32** |

`--mutate .` reports `2 file(s), 44 mutation(s), 0 survivor(s)` and exits 0 — a true statement about
a manifest that never learned the new code exists. Of **34** hand mutations I wrote against this
branch's additions, **8 survived**: H1 (×3), H3 (×2), M1, M2, and `--p-head` set to exactly `--link`
(L3). The manifest cannot shrink — `EXPECTED_MUTATIONS` pins it — but it also does not grow, and
"cannot shrink" reads as "still covers this file" when the file grows by a third.

The four that *should* be added, in order of what they defend: the `:660` call site, `quote=True`,
the `https?://` scheme restriction, and `PROSE_CONTRAST_MIN`.

---

## L1 — The atexit restore added by `a41e045` has no falsifier, and its stated hazard cannot occur.

**Severity: Low.** `scripts/gen-dashboard.py:890-899`. **REPRODUCED** — deleting
`_atexit.register(_restore_out)` **SURVIVED 161/161**.

The commit message is *"the write-sandbox restore did not survive a raising case"*. Trace the raising
case: an exception in `_self_test` propagates out of `main()`, out of `sys.exit(main(sys.argv[1:]))`,
and the process dies. `globals()["OUT_DEFAULT"] = _real_out` in an `atexit` handler of a dying
process is unobservable — nothing imports this module and calls `_self_test` in-process
(`check-plan-code.py:247` runs it as a subprocess). What the handler *does* buy is the
`_shutil.rmtree(_sandbox)` on the raising path: a temp-directory leak, which is real but is not what
the commit claims. Worth restating the comment at `:890` to match.

## L2 — The sandbox is restored three lines before the end, where the next case will be written.

**Severity: Low.** `scripts/gen-dashboard.py:1695-1698`. **Reasoning.**

`:881` claims the redirect *"is what makes it structural: a case written later inherits the sandbox
instead of having to remember it."* True for cases written before `:1695`, where `OUT_DEFAULT` is
restored and the sandbox `rmtree`'d — and the natural place to append a new case is between there
and `print(f"\n{ok}/{ok+fail} passed")`. A case added there that calls `main()` without `--out`
writes to the reader's real page. Moving the restore into a `try/finally` around the body, or simply
leaving it to the already-registered `atexit`, closes it.

## L3 — `--p-head` can be set to exactly `--link` with a green suite.

**Severity: Low.** `scripts/gen-dashboard.py:44`. **REPRODUCED** — `"head": ("#3a5261", "#b9c6d1")`
→ `("#1f5d8c", "#8cbde0")` (the `--link` values verbatim) **SURVIVED 161/161**.

`:35` claims the headline is *"desaturated well clear of `--link`, so a title never reads as
clickable."* Nothing asserts it. The `no two roles share a colour` case at `:1408` only compares the
four prose roles to each other, not to `--link`.

## L4 — `_first_sentence`'s cap can produce a one-word headline.

**Severity: Low.** `scripts/gen-dashboard.py:103-104`. **REPRODUCED**:
`_first_sentence("a " + "b"*200)` → `"a…"`. `out[:110].rsplit(" ", 1)[0]` keeps everything before
the **last** space in the window; when the only space is at index 1, that is one character. Not
crashing, and `rsplit` cannot return `""` (leading whitespace is normalised away at `:95`, and a
space-free window returns the whole slice) — so the brief's specific worry is unfounded — but the
degenerate output is real.

## L5 — A mid-sentence abbreviation still breaks the headline once the floor is cleared.

**Severity: Low.** `scripts/gen-dashboard.py:99-102`. **REPRODUCED**:
`_first_sentence("The release, i.e. the thing, is out.")` → `"The release, i.e."`.

`TITLE_FLOOR = 12` saves the *leading* abbreviation cases ("Dr. ", "e.g. ", "U.S. ") — I confirmed
those come out right — but only because the fragment is short. Once the accumulated text is ≥ 12
characters the loop breaks at the first `.`+space, wherever it is. Version numbers are safe (`2.5`
has no following space). Low because the store has no instance today.

## L6 — A needs-you day that also shipped with no entry would be keyed amber and drawn red.

**Severity: Low** — the state is **unreachable** today, which is why this is Low and not Medium.
`scripts/gen-dashboard.py:536-541`, `:715-718`. **REPRODUCED** at the function level.

`_bar` emits `class="bar needs unwritten"` for such a day. `.bar.unwritten` (`:717`) follows
`.bar.needs` (`:715`) in the cascade with equal specificity, so the amber is entirely hidden by the
red hatch — while `_legend` lists a "needs you" row with an amber swatch that appears nowhere on the
chart. That is the exact failure `_day_states`' own docstring forbids (*"a small lie about what is
on screen"*).

It cannot happen through `bucket_days` (`:349-350`): `flagged` is derived from `unresolved`, whose
members all have `error is None`, so every flagged date is also in `with_entry`, so `needs_you`
implies `has_entry`, and `unwritten` requires `not has_entry`. Both functions take free-form day
dicts, though, and nothing records that the exclusion is load-bearing.

## L7 — For a single-sentence entry the fold repeats the headline verbatim.

**Severity: Low.** `scripts/gen-dashboard.py:161-162`. **REPRODUCED** on the built page: the
`2026-08-28` entry ("Started building the dashboard — a page that shows what changed while you were
away.") renders its title, then a "What this means" fold whose only content is the same sentence.

This is the documented decision (*"an empty fold is worse than a repeated sentence"*), and I am not
arguing the decision. The third option is not taken: when `_prose(…, drop_headline=True)` would
return only the headline, omit the `<details>` entirely rather than offering the reader a
disclosure that discloses nothing.

---

## Verified sound — what I checked, and how

- **The write sandbox is real, and so was the defect it closes.** Not taken on trust. I built a fake
  `HOME` containing a real tray-bearing explainer (so `brief-compose.py:48`'s `find_source` succeeds
  exactly as it does for the reader), applied the manifest's own `main: a non-positive --window is
  silently accepted` mutation to a copy, and ran `--self-test`:
  - `master`: the fake live page went **32 → 31395 bytes**. The defect is real and I reproduced it.
  - `HEAD`: **32 bytes, untouched**. The fix works.
  My first attempt at this repro showed *no* overwrite on master and would have read as a refuted
  premise — the fake home had no page with a tray, so `brief-compose` refused and returned 1. The
  environment, not the code, was the difference.
- **The live page.** `md5 ~/explainers/dashboard.html` = `d22cee7615e602bf90dce824271248c7` before
  and after `python3 scripts/check-plan-code.py --mutate .` (real exit code captured, not `$?` after
  a pipe: `EXIT=0`, `2 file(s), 44 mutation(s), 0 survivor(s)`). Unchanged. Every `gen-dashboard.py`
  run I made used `--fragment-only` to a `$TMPDIR` path.
- **Every write path in the file.** Grepped `write_text` / `mkdir` / `open(…,"w")` / `rmtree` /
  `subprocess` / `chdir`. Five writes: `:1529` `:1645` `:1652` (temp), `:1755` `--fragment-only`
  (only ever passed a temp path, `:1536`), `:1758-1771` `--out` (sandboxed default, or an explicit
  temp path). The `os.chdir` at `:1530` is restored in a `finally` at `:1549` — I checked, because
  `:893` asserts it and an unverified claim about a `finally` is worth ten seconds.
- **`_inline` against 29 payloads.** Listed in H3. Output inspected by eye and, for the breakout
  candidates, by `html.parser` attribute tokenisation. No escape found in the shipped code.
- **`_prose(drop_headline=True)` cannot over-drop.** `rest = first[len(head):]` is safe because
  `head` is provably a prefix: `first` is whitespace-normalised at `:150`, `_first_sentence`
  re-normalises to the same string at `:95`, `SENTENCE_END` therefore splits on single spaces, and
  the loop rejoins with single spaces. It cannot empty the fold: `rest.lstrip()` empty falls to the
  `elif len(paras) > 1` promote, and a lone paragraph is kept.
- **`parse_entries` and `_prose` cannot disagree on the headline.** Both take the first paragraph —
  `:296-302` stops at the first blank line, `:135` splits on `\n[ \t]*\n` — and both derive the
  headline through `_first_sentence`. The differing `cap` cannot cause divergence because `_prose`
  passes `cap=len(first)`, which can never truncate. This is the fix `:143-148` describes and it
  holds.
- **`_day_states` agrees with `_bar` on all three states.** `marked` ↔ `quiet`
  (`has_entry and commits == 0`), `unwritten` (identical expression including the `store_unknown`
  suppression), `needs` (`needs_you`). Compared term by term; the only divergence is the CSS-cascade
  one in L6.
- **The legend is suppressed wherever the chart is not drawn.** `legend = ""` is initialised at
  `:604` and assigned only in the `else` at `:616`; both error branches leave it empty, and
  `_legend` returns `""` for a lone axis row. Confirmed by the `_err_page` case and by building one.
- **`--panel` is what prose sits on, in both themes.** `.entry{background:var(--panel)}` (`:741`)
  and `.prose` is inside `.entry`. `.entry.broken` uses `--err-bg` but renders `<pre>`, never
  `.prose`. So the *surface* in the AA check is right; M1 is about how it is obtained, not which one.
- **The four `--p-*` tokens reach the page.** Built the real page: `--p-lede:` … `--p-mark:` each
  appear twice (light + dark root), each consumed by a `var()`. 13 `<p class="lede">`, 24
  `<p class="body">`, 3 `<strong>`, 2 `<code>`, 1 autolink, 1 `<ul class="legend">`. The rendering
  claims are true of the shipped page.
- **The colour cases are not vacuous** (except M2's floor). Falsifiers I ran and that fired: ramp
  inverted → killed; two roles sharing a hex → killed; `mark` off the `--need` amber → killed;
  `--p-mark` no longer consumed → killed.
- **Sibling gates.** `check-dashboard-entry.py --self-test` 6/6 and clean run; `check-plan-code.py
  --self-test` 136/136; `check-docs.py --self-test` 13/13 and clean run. All green on this branch.
- **34 hand mutations, control-first.** Every batch ran an unmutated copy first (161/161) so a
  survivor cannot be a broken harness. Two entries reported `ANCHOR-MISSING` and were re-run by line
  number rather than counted as passes.

## Not checked

- **No browser.** All rendering claims are from the emitted HTML/CSS and from `html.parser`. The
  cascade claim in L6, the `:has()` selector at `:738`, and the `flex:0 0` override at `:732` are
  read off the stylesheet, not observed.
- **`brief-compose.py`'s own write paths** beyond `find_source` and `out.write_text` (`:233`). It
  writes exactly where it is told; I did not audit its tray-injection path.
- **The `\x01` case.** A control character inside a URL passes into `href` unescaped
  (`https://\x01x.com/a`). Browsers strip C0 controls during URL parsing, so I believe this is inert,
  but I did not confirm it in a browser. Labelling it rather than filing it.

---

# Disposition — coordinator, same session

Both halves **NOT CONVERGED**. Codex: 3 Medium + 1 Low. Claude: 3 High + 5 Medium + 3 Low.
Every finding acted on was **re-verified by execution** first; two were partly refuted and are
recorded as such rather than accepted.

| # | Finding | Verified how | Disposition |
|---|---|---|---|
| **H2** (C) | `**bold**` printed literally in a HEADLINE — on the shipped page | found 1 real title on the live page rendering `**Correction**` | **FIXED** — the headline is prose; it now goes through `_inline` like the body |
| **H1** (C) | Reverting the whole prose fold at the call site was GREEN | reviewer used 2 mutations; I reproduced | **FIXED** — asserted on the BUILT page. **4th wiring gap this session** |
| **H3** (C) / **M** (X) | `_inline`'s two SECURITY properties had no falsifier | Codex swapped `https?`→`(?:https?\|javascript)`: green | **FIXED** — 4 negative cases + a positive so they cannot go vacuous |
| **M1** (C) | AA measured a PYTHON COPY of `--panel`, not the stylesheet | reproduced | **FIXED** — reads the emitted CSS. ⚠ exposed a real bug: `_relative_luminance` could not parse `#fff`, which the stylesheet actually uses |
| **M2** (C) | `PROSE_CONTRAST_MIN` could be lowered to 1.0, green | reproduced | **FIXED** — pinned |
| **M3** (C) | Legend text below AA in light mode | **partly refuted**: 4.32:1 on `--bg` (not `--panel`, as filed), and the pre-existing `.note` shares it | **FIXED for the legend** (its own token, wired + checked). The pre-existing `.note` is NOT changed and NOT filed |
| **M4** (C) | `var(--fg)` names a property this page never defines | reproduced | **FIXED**, and generalised: every consumed property must be defined |
| **L3** (C) | `--p-head` could be set to exactly `--link`, green | reproduced | **FIXED** — pinned |
| **Cx1** (X) | "Met with **Dr.** Smith…" → headline `Met with Dr.`, lede opens `Smith…` | reproduced | **FIXED** — `_ends_in_abbreviation` |
| **Cx2** (X) | First paragraph with NO terminator → whole paragraph dropped from the fold | reproduced: text past `TITLE_CAP` appeared **nowhere on the page** | **FIXED** — refuses to drop a non-sentence. ⚠ I rate this **High**, not Medium: it is content loss |
| **Cx-Low** (X) | Overlapping `**bold` + `` `code` `` → malformed nesting | reviewer reproduced; not re-run | **NOT FIXED** — cosmetic, needs a real parser, not a 5th regex |
| **M5** (C) | Coverage shrank relative to the file; survivors on new code | — | **NOT FIXED** — backlog #69's shape. One manifest anchor WAS updated (below) |
| **L1/L2** (C) | `atexit` restore unfalsified; sandbox restored 3 lines early | — | **NOT FIXED**, stated |

## Falsification of the fixes

Battery on a scratch copy. **9/9 killed** after two rounds; **3 survived the first pass** and are
worth recording because two were holes in guards written minutes earlier:

- `M4` **survived** — a CSS **comment** reading `returns to --fg:` was counted as a *definition*.
  The guard was matching text, not declarations. Comments are stripped first now.
- `M3` **survived** — the case measured `--p-detail` **by name**; nothing asserted the legend rule
  *consumed* it. Wiring case added.
- `M1`'s "survivor" was **not a valid mutation** — it edited the case, not the product. Discarded.

⚠ **`--mutate .` went 44 → 43 and REFUSED**: the H2 fix moved a line that
`scripts/mutations/gen-dashboard.json` anchors on (`entry title not rendered`). The anchor was
re-pointed at the new code. This is the 45-anchor coupling the CI comment documents, behaving
exactly as designed — it refused rather than silently measuring one mutation less.

**Verdict after fixes: NOT RE-REVIEWED.** 161 → 187 cases, all gates green. A round 2 is owed:
every fix above was written by the author of the defects, and this round's own lesson is that
that is when guards come out vacuous.

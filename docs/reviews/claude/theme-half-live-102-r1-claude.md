# Adversarial review — backlog #102, "refuse a half-live theme toggle at compose time" (Claude)

## SUBJECT, and why this file has two rounds in it

**Round 1** reviewed commit `0670e2f8` (sha256 `0bd8da39…` of `scripts/brief-compose.py`, extracted
with `git archive` outside the repo). 12 findings.

**Round 2** — this document's substance — reviews the **fixes** applied on disk in response to the
Codex half and to r1. The file moved four times while I worked. Final snapshot, everything below
re-measured against it:

```
$ shasum -a 256 scripts/brief-compose.py
a1d76ab41dd377bfb457b5b6258f02081ebf236302c4a34b122cd15d965d7c80   (mtime 2026-09-10 06:15:13)
$ python3 scripts/brief-compose.py --self-test
62/62 passed
```

Method throughout: **execute, don't reason.** Every claim below is a constructed input and its
observed output.

### r1 findings, current status

| r1 | Finding | Status at `a1d76ab4` |
|---|---|---|
| F1 | `referenced_vars` ignores `var(--x, y)` | **FIXED** — `vars_read_anywhere` |
| F2 | `chrome_css()` contributed zero tokens | **FIXED** — now yields `--ink --ink-soft --rule --structural` |
| F3 | `SHIM`'s own reads absent from `also_read` | **FIXED** — `SHIM` appended. ⚠ *and this fix is the cause of R2-1 and R2-5 below* |
| F4/F4b | `:root` in a dark media query / in a comment credited as light | **FIXED** |
| F5 | `live_control` conditional untested | **FIXED** — gutting it now fails the suite |
| F6 | `head` vs `content` corpus | **FIXED** — *and this fix is the cause of R2-3 and R2-4* |
| F7 | prose flips `live_control` | partially — see **R2-6**, **R2-7** |
| F8 | vacuous no-control fixture | **FIXED** |
| F9 | no CI step / no mutation manifest | **HALF** — CI step added at `ci.yml:130`; still **no mutation manifest** (**R2-10**) |
| F10 | `shim_dark_tokens("")` fails open | **FIXED** |
| F11 | second selector in the media query silently dropped | **OPEN** — **R2-11** |
| F12 | refusal ordering vs `assert_wired` | **OPEN** — **R2-9** |

---

# R2-1 — BLOCKING. All five self-test cases written for the five fixes are **vacuous**: each produces a missing-token list byte-identical to the empty control.

**file:line** — `scripts/brief-compose.py`, the `r1 ADVERSARIAL REVIEW` block, cases
`⛔ a var() WITH an inline fallback still counts as READ`, `⛔ a SECOND <style> block is seen by the
guard`, `⛔ an inline style= attribute is seen by the guard`, `⛔ a :root inside
@media(prefers-color-scheme) does NOT cover a token`, and `a control id mentioned only in a CSS
COMMENT does not draw the half-live diagnosis`.

Four of the five are `case(name, not _c(...))` — *"assert this fragment is REFUSED"*. **The control
nobody ran is `_c()` with no feature at all**, and it is already refused:

```
V1 vacuous control (bare fixture, no feature): --card, --good, --ink-faint, --ink-soft, --rule, --structure
V2 fallback case                             : --card, --good, --ink-faint, --ink-soft, --rule, --structure
V3 second <style> case                       : --card, --good, --ink-faint, --ink-soft, --rule, --structure
V4 inline style= case                        : --card, --good, --ink-faint, --ink-soft, --rule, --structure
V5 media-query-coverage case                 : --card, --good, --ink-faint, --ink-soft, --rule, --structure
```

Not merely "also refused" — **the same six tokens, in the same order**. The feature each case names
contributes nothing to its own outcome.

**Cause.** The fixture `_c(inner, tail)` builds a page whose light palette is
`:root[data-theme="light"]{--ink:#111;--bg:#fff}` — two tokens. The F3 fix put `SHIM` into
`also_read`, and `SHIM` reads six *other* shim tokens on every page. So the fixture is refused for
`--card --good --ink-faint --ink-soft --rule --structure` before `inner` or `tail` is ever consulted.
Each case is about `--card`, and `--card` is in that list unconditionally:

```
>>> "--card" in vars_read_anywhere(SHIM)
True
```

**Mutation confirmation.** Control `62/62 passed`. Each of these reverts the fix the case claims to
pin, and the suite stays green:

| mutation | result |
|---|---|
| N4 drop `SHIM` from `also_read` | **62/62 passed** |
| N5 drop `chrome_css()` from `also_read` | **62/62 passed** |
| N6 revert the scan corpus `content` → `head` (undoes Codex Blocking 2) | **62/62 passed** |
| N7 make the media-query strip a no-op (undoes Codex High 3) | **62/62 passed** |
| N3 stop comment-stripping `has_control` (undoes Codex Medium 4) | 61/62 — killed |
| N1 gut `assert_theme_complete` (early `return`) | 54/62 — killed |

**Four of the five fixes can be reverted with the suite green.** The `⛔` markers assert coverage
that does not exist.

**The fifth case** is a different vacuity — an absence assertion:

```python
case("a control id mentioned only in a CSS COMMENT does not draw the half-live diagnosis",
     "does not cover every token" not in _refusal_for(_comment_page))
```

Under N1 (`assert_theme_complete` gutted so it can never speak) this case **passes**, verified:

```
✅  a control id mentioned only in a CSS COMMENT does not draw the half-live diagnosis
```

Deleting the subject satisfies the assertion. This is the project's recorded pattern *"the assertion
is an ABSENCE that deleting the subject also satisfies"*.

**Fix shape:** every one of these needs a control/defect pair. Give the fixture a light palette
covering all 11 shim tokens **except** the one under test, assert the bare fixture **composes**, then
assert the feature-carrying variant is refused **and that the message names exactly that token**.
`_refusal_for` already exists and returns the message; four of five cases discard it for a boolean.

---

# R2-2 — BLOCKING. The real `/backlog` page fails this guard, silently ships **without its Ask tray**, and the generator exits **0**.

**file:line** — measured live; `scripts/gen-backlog-page.py:2245-2252` is the swallowing caller.

```
$ python3 scripts/gen-backlog-page.py --out /tmp/bl.html   # current working tree
wrote /tmp/bl.html  (109 rows, 68 open)
⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:
   brief-compose: this page has a WORKING theme toggle, but its light palette does not cover…
   The page renders and reloads; only the ask-a-question button is missing.
$ echo $?
0
$ grep -c 'id="tray"' /tmp/bl.html
0
```

The full refusal, captured by spying on the subprocess:

```
  --bg, --defect, --rule, --structure
```

**This is not a regression from the fixes.** Identical output, identical four tokens, at
`0670e2f8`. So the shipped commit already broke a production page, and neither review round found
it, because **neither ran a generator.** The docstring's *"Measured 2026-09-10, on the first live
run"* refers to the goals page only. I ran all three: `gen-goals-page.py` OK, `gen-dashboard.py` OK,
`gen-backlog-page.py` **degraded**.

**Why it is Blocking rather than a palette chore.** `brief-compose.py`'s own module docstring:

> *FAIL LOUD, NEVER SILENT — … A brief that renders without its Ask tray is the failure this script
> exists to prevent, and it would be invisible — the page looks fine.*

A new guard inside that script now **causes** exactly that outcome on a real page, through a caller
that is designed to degrade rather than fail. The four tokens are genuinely read — by the lifted
tray (`--bg --defect --rule --structure`, all no-fallback) — so the finding is not that the guard is
wrong, it is that **the only consequence of being right is losing the tray, permanently and quietly.**

Either the backlog page's light palette gains those four, or the guard must not be able to cost a
page its tray. Shipping with it red is the state the project describes as *"a knowingly-red gate
makes CI a thing people learn to ignore"*, one layer down.

---

# R2-3 — HIGH. The corpus widening made the read scan parse **page prose and code samples as CSS**. Backlog row #102's own text is what breaks the backlog page's `--structure`.

**file:line** — `scripts/brief-compose.py`, `compose`: `assert_theme_complete(content, live_control, …)`.

Scanning `content` instead of `head` correctly picked up second `<style>` blocks and `style=`
attributes (Codex Blocking 2). It also picked up **every word of the page body**.

**Isolated control/defect pair** — same page, complete light palette minus `--defect`, the only
difference being one sentence of prose:

```
   no prose                              : COMPOSES
   prose shows <code>var(--defect)</code>: --defect
```

**Live instance, self-referential.** Attributing each token the real backlog page is refused for:

```
  --bg         <- the lifted TRAY css, SHIM
  --defect     <- the lifted TRAY css
  --rule       <- fragment CSS, the lifted TRAY css, chrome_css(), SHIM
  --structure  <- fragment BODY — prose/markup, the lifted TRAY css, SHIM
```

and the body site is backlog row #102 describing this very guard:

```
…nothing in the repo reads</strong> (the goals page draws that border with
<code>color-mix(var(--structure))</code>). A guard demanding…
```

The guard reads its own backlog entry's prose as a stylesheet. Body-only shim tokens on that page
are `--card` and `--structure`; `--card` escapes notice only because the backlog page happens to
declare it.

This class will grow, not shrink: `/brief`, `/explain-diff` and `/explain-topic` pages exist to
*show CSS*, and they all compose through this file.

**Fix shape:** extract `<style>` block contents and `style="…"` attribute values, and scan those —
not the raw document. `extract_tray` already does `re.search(r"<style>(.*?)</style>")`.

---

# R2-4 — HIGH. Same root, opposite direction: a palette shown in a `<pre>` sample is accepted as real **coverage**.

**file:line** — `light_palette_tokens(fragment_css)` is now called with the whole `content`.

**Trigger:** page reads `var(--defect)`, its real light palette omits `--defect`, and a `<pre>` block
displays `:root[data-theme="light"]{--defect:#a00}` as an example.

```
      -> COMPOSES (a <pre> sample accepted as coverage)
```

**Expected:** refused — nothing in that page declares a light `--defect`; the browser renders `<pre>`
as text. R2-3 is the false positive, this is the false negative, and one corpus fix produced both.
`check-theme-token-coverage.py`'s self-test already pins *"a bare mention of a token name does not
count as a declaration"*; this implementation of the neighbouring rule does not hold that line.

---

# R2-5 — HIGH. Two individually-correct fixes collapsed the narrowing: **8 of 11** tokens are now demanded of every page unconditionally, while the docstring still describes the narrowing as live.

**file:line** — `assert_theme_complete` docstring `⛔ ONLY TOKENS THE PAGE ACTUALLY READS`; `compose`'s
`also_read`.

```
V6 unconditionally demanded 8 of 11 -> ['--bg','--card','--good','--ink','--ink-faint','--ink-soft','--rule','--structure']
V7 still narrowed:                     ['--defect','--structure-bg','--structure-br']
```

`SHIM` is on every composed page and reads 9 of its own 11 tokens (mostly through its alias block:
`--verified: var(--good,…)`, `--fg3: var(--ink-faint,…)`, `--line: var(--rule,…)`,
`--structural: var(--structure,…)`). Once fallbacks count as reads (Codex Blocking 1) **and** `SHIM`
joins the corpus (r1 F3), "tokens the page reads" is very nearly "all of them".

The docstring still says:

> *Measured 2026-09-10, on the first live run: the goals page was refused for `--structure-br`, which
> nothing in the repo reads… Demanding a light value for a token with no consumer forces a
> declaration with no observable effect.*

That rationale now applies to only 3 tokens. The self-test case pinning the narrowing removes
`--structure-bg` — one of the 3 survivors — so it still passes and cannot see the collapse.

Note the alias subtlety this exposes: `SHIM` *declares* `--line`/`--structural` on `:root` (0,1,0),
and pages like `/backlog` override those at `:root[data-theme="light"]` (0,2,0). For such a page the
shim's read of `var(--rule)` is dead — its only consumer is an alias the page outranks — yet
`--rule` is demanded anyway. Either accept that the narrowing is gone and say so, or exclude `SHIM`'s
alias reads.

---

# R2-6 — MEDIUM. `has_control` strips **CSS** comments but not **HTML** comments — the actual way a button gets commented out.

**file:line** — `compose`: `page_chrome.has_control(strip_css_comments(content))`;
`strip_css_comments` is `re.sub(r"/\*.*?\*/", …)`.

```
>>> has_control(strip_css_comments('<!-- ' + page_chrome.theme_control() + ' -->'))
True
```

Composing such a fragment: `REFUSED: --card, --good, --ink-faint, --ink-soft, --rule, --structure` —
the half-live diagnosis, on a page whose only button is commented out.

The Codex Medium fixed `/* id="chrome-theme" */` inside a stylesheet. `id="chrome-theme"` is HTML,
so the comment syntax that actually surrounds it is `<!-- -->`. This is instance-not-class on that
fix — the recorded pattern *"after fixing, SEARCH for the class"*.

---

# R2-7 — MEDIUM. The two arms of `live_control` are asymmetric: arm 1 is comment-stripped, arm 2 is not.

**file:line** — `compose`:

```python
    live_control = page_chrome.has_control(strip_css_comments(content)) or not (
        page_chrome.missing_palettes(content + page_chrome.theme_control()))
```

Arm 2 receives raw `content`. Trigger — both palettes present **only inside a CSS comment**, no
button:

```
   arm1 has_control            = False     (comment stripped — correct)
   arm2 not missing_palettes   = True      (comment NOT stripped)
   -> REFUSED: --bg, --card, --good, --ink, --ink-faint, --ink-soft, --rule, --structure
```

The fix was applied to the arm the finding named and not to its neighbour, so a comment still
reaches the predicate by the other route. The same raw-substring exposure covers palettes shown in
prose or a `<pre>` sample (r1 F7, still reachable this way).

---

# R2-8 — MEDIUM. The refusal's token list is on line 2, and the production caller prints line 1.

**file:line** — `scripts/gen-backlog-page.py:2249`.

```python
        print("   " + (composed.stderr.strip() or composed.stdout.strip() or "no output").splitlines()[0])
```

Line 1 is `brief-compose: this page has a WORKING theme toggle, but its light palette does not cover
every token the OS-dark shim supplies:` — it names **no tokens**. Line 2 is `--bg, --defect, --rule,
--structure`. Observed in the live run above: the operator is told a page lost its tray and is not
told which four tokens to declare.

`_refusal_text`'s own docstring is the falsifier for this:

> *⚠ Asserting the MESSAGE, not just the exit. A refusal that does not name the missing tokens sends
> the author back to diff two palettes by hand, which is the work the guard exists to do.*

The self-test asserts the tokens are in the message; the only real caller drops the line they are on.
Put the token list on line 1, or have the caller print the whole message.

---

# R2-9 — MEDIUM (r1 F12, still open). `assert_theme_complete` still runs before `assert_wired`, so an unwired button gets the wrong diagnosis.

**file:line** — `compose`: `assert_theme_complete(...)` precedes `chrome_for(...)` → `assert_wired`.

Trigger — button present, **no** palettes at all (`assert_wired`'s exact subject). First line of the
refusal:

```
brief-compose: this page has a WORKING theme toggle, but its light palette does not cover every token…
```

The page's toggle is not working; it is unwired. The new self-test case acknowledges this
(*"the half-live guard spoke FIRST and blamed a theme toggle the page does not have"*) and pins the
symptom for one input via an absence assertion (R2-1) rather than moving the call. Moving
`assert_theme_complete` after `chrome_for` fixes the class.

---

# R2-10 — LOW (r1 F9, half open). CI step added; **no mutation-manifest entry**, which is what the surviving mutations need.

`ci.yml:130-131` now runs `python3 scripts/brief-compose.py --self-test`. Good — but:

```
$ grep -l "brief-compose" scripts/mutations/*.json
(none)   # 34 manifests, 30 files covered
```

A green self-test is exactly what N4/N5/N6/N7 in R2-1 return. `check-plan-code.py --mutate .` is the
mechanism this project uses to prove a case is load-bearing, and this file is still outside it.
`check-ratchet-contract.py` also cannot see it (population is `check-*.py`), which the new CI comment
records honestly.

---

# R2-11 — LOW (r1 F11, still open). `shim_dark_tokens` silently shrinks its subject if the media query gains a second selector.

**file:line** — `shim_dark_tokens`, `(.*?)\}`.

```
>>> shim_dark_tokens("@media (prefers-color-scheme: dark) {\n html { --bg:#000; }\n body { --card:#111; }\n}")
['--bg']
```

Comments are now stripped and a zero-token parse is CANNOT RUN — both good — but a *partial* parse is
still silent, and the docstring's premise is that the shim is edited often. One token short is
indistinguishable from one token covered.

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| Blocking | 2 | R2-1, R2-2 |
| High | 3 | R2-3, R2-4, R2-5 |
| Medium | 4 | R2-6, R2-7, R2-8, R2-9 |
| Low | 2 | R2-10, R2-11 |

The five fixes are individually correct and I reproduced each working. The problem is what they do
as a set, which is the composition failure this project's Phase 6 exists for:

- **Adding `SHIM` to the read corpus** (r1 F3) made six shim tokens unconditionally demanded. That
  silently hollowed out every fixture written for the *other four* fixes — the bare control now
  produces the identical refusal, so four of five fixes can be reverted with `62/62 passed`
  (**R2-1**), and the narrowing the docstring still advertises now covers 3 of 11 tokens
  (**R2-5**).
- **Widening the corpus from `head` to `content`** (Codex Blocking 2) correctly caught second
  `<style>` blocks and `style=` attributes, and simultaneously started parsing prose as CSS in both
  directions (**R2-3**, **R2-4**) — with the live instance being backlog row #102's own text.
- Two fixes were applied to the instance named rather than the class: CSS comments but not HTML
  comments (**R2-6**), and one arm of `live_control` but not the other (**R2-7**).

Independent of the fixes, **R2-2** was true of the shipped commit and is true now: `/backlog` loses
its Ask tray, exit 0, and neither review round ran a generator. That is the one finding that costs a
reader something today.

VERDICT: NOT CONVERGED

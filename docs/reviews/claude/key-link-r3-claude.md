Reviewed head: 0ea207e8b6baad277a99f03a653cd2325b43732d

# key-link (backlog #470, PR #489): Claude half, round 3

Diff reviewed: `668e4cc1..0ea207e8` (the r2 fold: the supported HTML subset, rule 0, `OutsideSubset`, the
`brief-compose.extract_tray` close, rule 2's `%` / `.format` / join / f-string reading).
Mandate: REFUTE. Round 3 is the last folded round, so every finding is marked BLOCKER yes or no.

## Summary

One BLOCKER. The subset is too strict for text our own renderer produces. `page_markup.scan` cuts a bare URL
in the middle of an entity. So an author who writes a URL in quotes or angle brackets, which this repo's
markdown does 435 times, gets a `&quot` / `&#x27` / `&gt` / `&amp` with no `;`. The subset refuses that, and
`link_html` raises inside all five generators. The page is not written, the regen hook fails, and CI's
`--build --ci` goes red. Before r2 this was a cosmetic defect: a stray `;` after the link. r2 turned it into a crash.

The other three findings are not blockers: one renderer path that emits `<a>` in `<a>`, a gap in the subset's
`<p>`-closer model, and a measurement claim about "CI's Python" that was made on a different patch release.

Questions 3 (tray), 4 (CI parity, in outcome) and 5 (idempotence) hold, and the evidence is below.

## Findings

### F1. A URL in quotes or angle brackets crashes every generator. High. BLOCKER: yes

`scripts/page_markup.py:72` and `:725-737`, made fatal by `:309` (`_BARE_REF`) through `:476` (`require_subset`)
and `:553` (`link_html`).

`render_inline` escapes first and then scans. `INLINE_URL = r"https?://[^\s<]+[^\s<.,;:)\]]"` runs over the
ESCAPED text, so a trailing `"` (now `&quot;`) is matched up to, but not including, its `;`. The resulting link's
href and text both end in a reference with no `;`. That is outside the subset by rule (`_BARE_REF`), so
`link_html` raises `OutsideSubset`, and every generator calls `link_html` on its whole page
(`gen-dashboard.py:3541`, `gen-backlog-page.py:4283`, `gen-goals-page.py:1359`, `gen-features-page.py:776`,
`goal-tree.py:1061`).

Inputs to `page_markup.render_inline`, measured on the head:

| author text | emitted | subset |
|---|---|---|
| `see "https://x.com/a" now` | `&quot;<a href="https://x.com/a&quot">https://x.com/a&quot</a>; now` | refused, `&quot` |
| `see 'https://x.com/a' now` | `…<a href="https://x.com/a&#x27">…&#x27</a>; now` | refused, `&#x27` |
| `see <https://x.com/a> now` | `…<a href="https://x.com/a&gt">…&gt</a>; now` | refused, `&gt` |
| `see https://x.com/a& now` | `<a href="https://x.com/a&amp">…&amp</a>; now` | refused, `&amp` |

End to end, in a scratch clone of the head:
- **Dashboard.** Appending a `## 2026-11-03` entry to `docs/dashboard-entries.md` with the body
  `The page is served at "http://127.0.0.1:7391/dashboard" now.` makes `gen-dashboard.py --fragment-only` exit
  **rc 1** with `page_markup.OutsideSubset: … line 172: <a> has a character reference with no ';': '&quot'`.
- **Backlog.** Adding ` See <https://example.com/x> and "https://example.com/y". ` to row 470's cell makes
  `gen-backlog-page.py` exit **rc 1**, `OutsideSubset … '&gt' … '&quot'`.
- **CI step.** The same dashboard entry under `python3.12 scripts/check-page-links.py --build --ci`: see *Commands*.

How close the corpus is: `grep -rhoE "[\"'<]https?://[^ \"'<>]+[\"'>]" docs --include=*.md` counts **435**
quoted or angle-bracketed URLs in this repo's markdown. None is in the four page sources today, which is why
`--build` is green. One is enough. The dashboard store gets a new entry on nearly every PR, and goal-tree
renders the owner's own request text.

For the owner, the effect is the regen hook (`.claude/hooks/regen-dashboard.sh` and the others) failing on an
ordinary edit, with a traceback and no page.

Why r2 did not see it: the corpus run was the only measurement of "is the subset too strict", and the corpus
happened not to contain this input. The subset was checked against what the generators EMITTED, never against
what the renderer CAN emit.

Fix direction (a hypothesis, not verified):
1. In `scan`, never let a bare URL end inside a reference. After the match, drop a trailing
   `&[A-Za-z0-9#]*` that has no `;` (the escaped quote, apostrophe, `>` or `&` belongs outside the link) and
   re-validate.
2. Make the case a PROPERTY over the escape table, not one input. For each character `html.escape` rewrites
   (`& < > " '`), `subset_problems(wrap(render_inline(f"x https://a.b/c{ch} y"))) == []`, and the same with the
   character in front of the URL.

That is the identity case that would have caught it, and it covers the class rather than the four inputs above.

### F2. A URL inside markdown link text renders `<a>` inside `<a>`. Medium. BLOCKER: no

`scripts/page_markup.py:678`. A link's TEXT is scanned with `keys=False`, which turns off key links only. The
bare-URL branch (`:725`) still runs inside it.

- Input: `[https://a.com/x](https://b.com)`
- Output: `<a href="https://b.com"><a href="https://a.com/x">https://a.com/x</a></a>`

Through `gen-dashboard.py` (a scratch entry), the page is written (rc 0) with this nesting, and
`check-page-links.nested_anchors` reports `['line 172']`. So rule 1b turns `--build --ci` red on ordinary
markdown (a link whose text is its URL), and a browser's adoption agency splits the anchors.

It is not a BLOCKER: the defect predates r2, the gate reports it loudly with a line, and the corpus does not
contain it today (the grep for `[https://…](` over the four page sources found 0).

It is the same class as F1, though: renderer output that the page gate refuses. The F1 property case should
include it. `scan(m.group(1), False)` should suppress bare URLs as well as keys.

### F3. The subset lets through `<p>` closers it does not model, so the r2 prediction is falsified on its own terms. Low. BLOCKER: no

`scripts/page_markup.py:290` (`_P_CLOSERS`) and `:459`.

The r2 coordinator's split prediction holds "if r3 finds no page INSIDE the subset on which `html.parser` and a
browser disagree about … which element is open". I compared against parse5 (the HTML5 tree builder jsdom uses,
from the repo's `node_modules`), with a `<!DOCTYPE html>` wrapper. These pages are INSIDE the subset
(`subset_problems == []`), and the two readers disagree:

| input (in `<body>`) | html.parser path of `c` | browser path of `c` |
|---|---|---|
| `<p>a<li>b</li>c</p>` | `body>p` | `body` (`<li>` closed the `<p>`) |
| `<p>a<dd>b</dd>c</p>` / `<dt>` | `body>p` | `body` |
| `<p>a<summary>b</summary>c</p>` | `body>p` | `body` |
| `<p>a<center>b</center>c</p>` / `<dir>` / `<listing>` | `body>p` | `body` |
| `<table>&nbsp;<tr><td>x</td></tr></table>` | `\xa0` stays a table child | foster-parented out of the table |

The causes:
- `_P_CLOSERS` omits `li`, `dd`, `dt`, `summary`, `center`, `dir` and `listing`. All of them close a `<p>` in
  button scope (HTML "in body" insertion mode).
- `x.strip()` at `:459` treats U+00A0 as whitespace. HTML's "whitespace" is only tab, LF, FF, CR and space.

Impact today is small. A `<p>` is not an exempt element, so no key changes exemption. No generator emits these
shapes: all five built pages and the fuzzed dashboard entry stayed inside the subset with no such construct.
The fix is mechanical:
- add the seven names to `_P_CLOSERS`;
- test `x.strip(" \t\n\r\f")`.

It is recorded because the r2 decision-log row named exactly this observation as its falsifier.

### F4. "`--build --ci` rc 0 under 3.12 (CI's Python)" was measured on 3.12.9, and CI runs 3.12.15, whose `html.parser` differs. Low. BLOCKER: no

`docs/reviews/coordinator/key-link-r2-coordinator.md` (the corpus paragraph), and the comments at
`scripts/page_markup.py:286` and `:357-361`.

CI's setup step logs `Successfully set up CPython (3.12.15)` (run 41718938754, job `verify`). The local
`python3.12` is **3.12.9**. The difference matters for exactly the two rules r2 called "3.12 only":
- **RCDATA.** 3.12.9 has no `HTMLParser.RCDATA_CONTENT_ELEMENTS`. The uv-managed **3.12.12** has
  `('textarea', 'title')`, backported, so CI's 3.12 reads `<textarea>` / `<title>` like 3.14. The comment
  "3.12's html.parser reads tags in them" is true of 3.12.9 and false of what CI runs.
- **The AssertionError.** On 3.12.12, `HTMLParser().feed('<![foo]>x')` does NOT raise. The `_events` docstring
  says "3.12's parser RAISES `AssertionError` on a marked section". That is again true of 3.12.9 only.

The OUTCOME still matches. On 3.12.12, which is closer to CI than 3.12.9:
- the `page_markup` self-test passes 192/192;
- the `check-page-links` self-test passes 88/88;
- the `brief-compose` self-test passes 196/196;
- `--build --ci` exits rc 0.

The self-test drives both "3.12-only" rules artificially, so they are covered on any patch release.

So no gate result is wrong. The claim names the wrong subject, and two comments state a parser behaviour that
CI's parser no longer has. Fix:
- reword the comments to "3.12 before 3.12.11-ish (measured: 3.12.9 yes, 3.12.12 no)";
- state the version a parity claim was measured on.

## The mandate's questions, answered

1. **Too strict?** Yes. That is F1, a BLOCKER, and F2 is the same class. Everything else I fed the dashboard
   generator stayed inside the subset: a list-shaped paragraph, `R&D`, raw `<b>` / `<details>` in prose, a
   fenced block, a pipe table, and a tech section with `<!-- -->` and a `&` query URL. All of it is escaped, and
   prose is never wrapped around a block element. The backlog page's data-dependent boxes (`unread_box`,
   `drift`, `gen-backlog-page.py:2033-2059`) put `<ul>` inside a `<div>`, not a `<p>`.
2. **Too loose?** Slightly. That is F3. The other differences parse5 shows fall inside the stated bounds:
   - the implied `<tbody>` (no text moves);
   - HTML breaking out of `<svg>` / `<math>`;
   - the adoption agency for `<a>` in `<a>`;
   - the first newline after `<pre>` (dropped by a browser, kept by html.parser; it changes no key and no
     exemption).
3. **Tray fix.** It does not change behaviour. I composed `features` with `brief-compose.py` from the owner's
   truncated `~/explainers/features.html` with the head (`comp1`) and with the base's `brief-compose.py`
   (`comp0`). The only diff is one `</div>` (line 1240). Under jsdom with `runScripts`, both pages:
   - have `#tray` as a child of `<body>`, with `.in` and all five ids (`qbox`, `sendbtn`, `closebtn`, `sentnote`,
     `qt`);
   - have 3 `.askbtn`;
   - open the tray on a click (`#tray.on`, `#qt` filled);
   - raise 0 script errors.

   The one difference: the tray script is no longer INSIDE `#tray` (it was 1 script there, now 0). No tray CSS
   uses a child or last-child selector (`#tray{`, `#tray.on{`, `#tray .in{` only).
4. **CI parity.** In outcome, yes. In claim, no: that is F4.
5. **Idempotence.** It holds.
   - `link_html(x) == x` for every page and fragment built from the head: dashboard, goals and features
     fragments, and the backlog page and its fragment.
   - Composing `features` twice (`comp1` as the second run's source) is byte-identical (`cmp`).
   - The tray close appends 0 on a whole source.
6. **New crash path?** Yes, F1. `OutsideSubset` is raised from `link_html` inside all five generators' normal
   run, on author text the renderer itself mis-escapes. No generator catches it, so the regen hooks fail with a
   traceback.

## Commands run, and results

All from the worktree at `0ea207e8` unless a scratch clone (`git clone` of the worktree, checked out at the head)
is named.

| command | result |
|---|---|
| `python3 scripts/page_markup.py --self-test` (3.14.4) | 192/192, rc 0 |
| `python3.12 scripts/page_markup.py --self-test` (3.12.9) | 192/192, rc 0 |
| uv `python3.12` 3.12.12 `scripts/page_markup.py --self-test` | 192/192, rc 0 |
| `check-page-links.py --self-test` on 3.14.4 / 3.12.9 / 3.12.12 | 88/88 each, rc 0 |
| `brief-compose.py --self-test` on 3.14.4 / 3.12.9 / 3.12.12 | 196/196 each, rc 0 |
| `check-plan-code.py --self-test` on 3.14.4 / 3.12.9 | 278/281. The 3 FAILs are all `node_modules/typescript is missing` under this worktree, which has no `node_modules`: environmental and not this diff. Treat this suite as NOT RUN here |
| `python3 scripts/check-page-links.py --build` | rc 0. Rule 0 read 5 pages, all inside the subset; 11 scripts parsed; 7,914 fragment links checked |
| `check-page-links.py --build --ci` on 3.14.4 / 3.12.9 / 3.12.12 | rc 0 each. 4 pages; 7 scripts parsed; 3,525 fragment links checked; goal-tree NOT RUN, as stated |
| `check-page-links.py --sources` | rc 0 |
| scratch clone: dashboard entry with `"http://…"`, `gen-dashboard.py --fragment-only` | **rc 1, `OutsideSubset` (`&quot`)**, F1 |
| scratch clone: backlog row 470 with `<https://…>` and `"https://…"`, `gen-backlog-page.py` | **rc 1, `OutsideSubset` (`&gt`, `&quot`)**, F1 |
| scratch clone: the same dashboard entry, `python3.12 check-page-links.py --build --ci` | **rc 2, CANNOT RUN: `gen-dashboard.py exit 1 … OutsideSubset … &quot`**, so the CI step is red. F1 |
| scratch clone: dashboard entry with `[https://a.com/x](https://b.com)` | gen rc 0; `nested_anchors` → `['line 172']`, F2 |
| parse5 against `html.parser` over 21 handcrafted bodies | F3 table; the other differences are in the stated bounds |
| jsdom: tray on `comp0` (base) against `comp1` (head) | identical behaviour, Q3 |
| `link_html` idempotence over 5 built pages / fragments; compose twice + `cmp` | identical, Q5 |

Mutation sweeps were not run, as briefed.

VERDICT: NOT CONVERGED

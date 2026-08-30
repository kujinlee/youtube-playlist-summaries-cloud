# Inline renderer seam — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Backlog:** #71. **Origin:** Phase 6 finding D, `docs/reviews/architecture-review-2026-08-30.md`.
**Status:** drafted 2026-08-30. Candidate 1 of the Phase 6 candidates; the user set the order
**1 → 3 → 4** on 2026-08-30.

---

## 1. What is wrong today

Four page generators each render inline markdown, and **no generator imports another's renderer**:

| generator | renderer | algorithm |
|---|---|---|
| `scripts/gen-dashboard.py` | `_inline` / `_inline_scan` (`:234`, `:259`) | one left-to-right scan |
| `scripts/gen-backlog-page.py` | `md` (`:548`) | 4 stacked `re.sub` passes |
| `scripts/gen-goals-page.py` | `esc` + `inline_md` (`:139`, `:144`) | 2 stacked `re.sub` passes |
| `scripts/explainer-serve.py` | `md_inline` (`:179`) | 5 `re.sub` passes + a code-span placeholder |

They are not four copies of one rule. They implement **four different rules**, and the differences
are not deliberate — they are the accumulated history of whichever page last had a defect reported.

### Measured, 2026-08-30

Every number below came from running the **delivered** functions, imported rather than
re-implemented, over the **real** corpora. Scripts used are throwaway; each measurement is
reproducible from the description.

**① The four disagree on 11 of 13 probe inputs.** A representative four:

| input | `gen-dashboard` | `gen-backlog` | `gen-goals` | `explainer-serve` |
|---|---|---|---|---|
| `` **bold `code** tail` `` | `<strong>bold \`code</strong> tail\`` | crossed tags | crossed tags | `**bold <code>code** tail</code>` |
| `` `**not bold**` `` | literal (correct) | bolds inside the code span | bolds inside the code span | literal (correct) |
| `[click](javascript:alert(1))` | left literal | **`<a href="javascript:alert(1">`** | left literal | `<a href="#">` |
| `it's fine` | `&#x27;` | `&#x27;` | **not escaped** | `&#39;` |

**② The corruption is live, not hypothetical.** Read out of `~/explainers/backlog-table.html` **as it
stood on disk** (generated 2026-08-29 16:42; not regenerated to produce this spec):
**10 crossed tag spans and 15 cases of markup emitted inside a code span.** Two instances, both from
`docs/backlog.md` prose:

- `` `select count(*) filter (where normalize(name, NFKC) <> name)` `` renders as
  `select count(<em>) filter …` — the page shows SQL that would fail if copied.
- `` `supabase/migrations/*persist_summary*` `` renders with the glob asterisks eaten and the name
  italicised.

**③ The root cause is the algorithm, and the fix already exists one file away.** Stacked `re.sub`
passes are blind to each other's output: the `*em*` pass reaches inside the `<code>` element the
code-span pass just emitted. `gen-dashboard._inline_scan` was rewritten as a single left-to-right
scan in PR #178 for exactly this reason, and says so in its own docstring — *"Those passes were blind
to each other's OUTPUT."* That fix is unreachable from the other three.

**④ Two more holes of the same shape.** `gen-backlog-page` renders `[text](url)` with **no href
sanitiser**, while `explainer-serve.safe_href` (`:145`) exists and is not shared — its docstring
records that rendering *this repo's own documents* already produced clickable `javascript:` hrefs
with no attacker involved. And `gen-goals-page.esc()` omits the apostrophe.

**⑤ Why widening features without the scan would make it worse.** Across the four corpora,
**39 lines carry a `*` inside a code span** (12 dashboard, 17 backlog, 10 goals, 0 explainer). A
left-to-right scan consumes the code span whole before `*em*` is considered, so all 39 are safe.
Adding `*em*` to any of the stacked-pass implementations would corrupt them.

---

## 2. What this changes, and what it deliberately does not

**Decided with the user, 2026-08-30: one behaviour for all four pages.** The measurement that
shaped it: unifying on `gen-dashboard`'s **current rule** would be a regression, not a fix —

| corpus | lines differing | of which substantive |
|---|---|---|
| `gen-goals` | 198 | 10 |
| `explainer-serve` | 13 | 0 |
| `gen-backlog` | 60 | **60** — strips 59 `<em>` spans and 3 links |

`gen-dashboard._inline` is minimal because its *corpus* is minimal (0 markdown links across 593
lines). That is a fact about dashboard entries, not a property of a good renderer. So:

> **One behaviour = the union feature set, carried by `gen-dashboard`'s single-scan algorithm.**
> Keep the algorithm. Widen the features. These are separable and the split is the whole design.

**The union:** `**bold**`, `` `code` ``, `*em*`, `~~del~~`, `[text](url)` through `safe_href`, and
bare-URL autolinking. Escaping unified on `html.escape` (`&#x27;`).

### What each page gains or loses

- **`explainer-serve`** — 0 substantive change. Its `md_inline` already *is* the union feature set;
  it simply is not shared, and its scan is weaker.
- **`gen-backlog`** — keeps its em and links, gains 2 autolinks, and **fixes the 10 crossed spans and
  15 markup-in-code cases now on the page**. Gains `safe_href`.
- **`gen-goals`** — the largest visible change: **145 emphasis spans across 132 lines, and 17 links**,
  start rendering where they now print as literal asterisks and brackets. 14 of 14 sampled are
  authored emphasis (e.g. `docs/adr/0005-…md:134`, a deliberately italicised parenthetical). Gains
  apostrophe escaping.
- **`gen-dashboard`** — 5 lines newly italic; 0 link changes, since its corpus contains none.

### Deliberately NOT in scope

- **Contrast.** `gen-dashboard.contrast_failures` and `gen-backlog-page.link_contrast_errors` are
  *checkers*, not renderers, and each already has its own gate. Folding them in is scope creep.
- **Block-level markdown.** `explainer-serve.md_blocks` / `md_render` and each generator's table and
  heading handling stay where they are. Only the **inline** layer moves.
- **`_close_orphan_markup`.** It is dashboard-specific *truncation policy*, not inline rendering. It
  stays in `gen-dashboard.py` and calls the shared module — which is already how it works
  (`:169`: *"judged by the RENDERER, not a copy of it"*), so the seam it needs simply gets a new
  address. `_trim_url_tail`, `INLINE_URL` and `ENTITY_TAIL` **do** move: they are autolinking.

---

## 3. Design

### 3.1 The module

`scripts/page_markup.py`. **Underscored deliberately.** The hyphenated `scripts/*.py` files are
executables and are not importable by name — `gen-dashboard.py:408` records that *"not importable, so
importlib is the only route."* `page_markup` is a **library**, and the repo already distinguishes
these: `m4_base_db.py`, `m4_catalog.py`, `subject_status.py`. The underscore is the convention that
says *import me directly*.

It is a **peer**, not a gate. The documented generator → gate arrow (`gen-dashboard.py:402-408`)
governs a page importing the guard that checks it. A renderer is not a gate, and making three
generators import a 2,458-line page generator would be worse than the duplication. All four import
`page_markup` as equals; `page_markup` imports none of them.

### 3.2 Public surface

```python
escape(s: str) -> str                  # html.escape, quote=True — the ONE escaping rule
render_inline(s: str) -> str           # escape, then scan. The entry point generators call.
scan(escaped: str) -> str              # the scan alone, over ALREADY-ESCAPED text
safe_href(url: str) -> str             # '#' unless the scheme is one a document may navigate to
orphaned_delimiters(s: str) -> int     # what dashboard truncation needs from the renderer
```

`scan` is public and separately named because `render_inline` must never be called twice on the same
text, and **one caller genuinely needs the escaped-input form**: `explainer-serve.md_render` (`:197`)
escapes a whole document once and then renders blocks over the escaped text (`md_blocks:204`,
`md_cells:168`). ⚠ `gen-dashboard._inline_scan` has **no** external caller today — only `_inline`
(`:256`) and itself recursively (`:294`). An earlier draft of this spec justified the public `scan`
by claiming otherwise; the justification is `explainer-serve`, and nothing else.

### 3.3 The algorithm

`gen-dashboard._inline_scan`, widened. One left-to-right pass; each construct consumes its whole span
before the next is considered, so a span cannot begin inside one region and end inside another.
Precedence, highest first: **code span** → **link** → **bold** → **del** → **em** → **bare URL**.
Code first is what protects the 39 globs. Unpaired delimiters print as themselves — dropping text to
balance tags trades a cosmetic defect for content loss, which is the trade `_inline_scan`'s docstring
already refuses.

### 3.4 The guard stack — decided with the user

**`page_markup.py` becomes its own guard subject:** its own `--self-test`, its own
`scripts/mutations/page_markup.json`, and a row in `scripts/check-ratchet-contract.py`'s inventory —
which as of `e9532e2` discovers 24 guards from the filesystem, so it will be found whether or not
anyone remembers to register it.

**The four generators' inline cases are deleted, not kept as consumer-side contract tests.** This is
the version where candidate 1 *reduces* the layer count: the cases that today defend one page's
renderer move once and then defend four. The generators keep only page-level cases — that a heading
renders, that a row appears — not "does `**x**` become `<strong>`".

`EXPECTED_MUTATIONS` (`check-plan-code.py:302`) and the literal sum at `:1521` both move with the
manifest entries. As of `e9532e2` that sum is **73** across two files (61 `gen-dashboard.json`,
12 `check-dashboard-entry.json`); the retarget changes both numbers and `--mutate .` is the check.

### 3.5 Concern → mechanism

| Concern | Mechanism | Evidence |
|---|---|---|
| Inline markup renders identically on all four pages | `page_markup.render_inline`, single implementation | `--self-test`; a differential over all four corpora |
| A construct cannot begin in one region and end in another | one left-to-right scan | the 39 globs-in-code render literally |
| HTML in source text cannot become HTML on the page | `page_markup.escape`, `quote=True` | `--self-test` injection cases |
| A link cannot carry an executable scheme | `page_markup.safe_href` | `--self-test`: `javascript:`, `data:` |
| Truncation cannot fabricate text | `gen-dashboard._close_orphan_markup` calling `orphaned_delimiters` | already guarded; unchanged behaviour |
| The renderer cannot silently rot | `--self-test` + `scripts/mutations/page_markup.json` | `--mutate .`, 0 survivors |

**What already does this, and why it is insufficient:** `gen-dashboard._inline_scan:259` already
implements the correct algorithm and is already guarded to the standard this spec asks for. It is
insufficient for exactly one reason — **it has no seam**. Nothing else can reach it. That is the
whole finding, and the fix is an address, not an algorithm.

---

## 4. How we will know it worked

1. `python3 scripts/page_markup.py --self-test` passes.
2. `python3 scripts/check-plan-code.py --mutate .` reports 0 survivors, with `page_markup.json`
   included and `EXPECTED_MUTATIONS` updated.
3. `python3 scripts/check-ratchet-contract.py` discovers **25** guards and reports OK.
4. `python3 scripts/gen-dashboard.py --self-test` still passes.
5. A differential over all four real corpora: every line renders identically under all four
   generators, because there is one renderer.
6. `~/explainers/backlog-table.html`, regenerated: **0 crossed tag spans, 0 markup inside a code
   span** — against 10 and 15 today.

### Falsifiers — the observation that makes each claim FAIL

| Claim | FAILS IF |
|---|---|
| One renderer serves four pages | any of the four still defines an inline-markup function, or `grep -c` for inline-markup refs in a generator exceeds its page-level needs |
| The scan protects code spans | any of the 39 globs-in-code renders with an `<em>` or `<strong>` inside the `<code>` |
| The backlog corruption is fixed | the regenerated page contains a crossed tag span |
| The layer count fell | the four generators' combined inline case count did not decrease |
| The module cannot rot unnoticed | `check-ratchet-contract.py` does not list `page_markup.py`, or it has no `--self-test` |
| No page silently lost a feature | the goals page renders fewer than 145 emphasis spans, or the backlog page fewer links than today |

---

## 5. Scope

**Touches:** `scripts/page_markup.py` (new), `scripts/gen-dashboard.py`, `scripts/gen-backlog-page.py`,
`scripts/gen-goals-page.py`, `scripts/explainer-serve.py`, `scripts/mutations/*.json`,
`scripts/check-plan-code.py` (counts only), `CONTEXT.md` (the term), `docs/dev-process.md` (pointer
row only if the enforcement table gains one).

**Does not touch:** the product. No `lib/`, `app/`, `components/`, `worker/`, or `supabase/` file is
involved. This is repo tooling.

**Size:** M.

---

## 6. Open, and deliberately not settled here

- **Candidate 3 (`HOME`)** is a separate decision and a separate slice, running alongside. Measured
  2026-08-30: the whole harness passes under a redirected `HOME` (73 mutations, 0 survivors, nothing
  written into the fake home), so the structural option is available — the open question is whether
  redirecting permanently trades a destruction hazard for output-path fidelity.
- **Candidate 4 (flatten the stack)** is deliberately deferred until this lands, because this changes
  its arithmetic.
- **`project-dashboard` is not a registered anchor.** `docs/reviews/architecture-review-2026-08-30.md`
  declares it; `docs/anchors.md` does not list it. `check-anchors.py` passes only because
  `docs/reviews/` is out of scope by design. Noted, not fixed here.

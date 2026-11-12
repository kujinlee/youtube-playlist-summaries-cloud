Reviewed head: f22cf182c7e0bb25b2f5c8079ab8d35f34c44d1a

# 603-decision-tags — round 3 — Claude half (adversarial)

Subject: `scripts/brief-compose.py` decision tags (PR #563, backlog #603). Head `f22cf182` (the r2 fold).
r2 fold diff read: `git diff 097096b6..f22cf182`. Only half this round (alternation).

## Method — what was run

- **Oracle.** Every hostile fragment was composed with `render_decisions` and the OUTPUT parsed by
  `parse5` (the WHATWG reference parser, `node_modules/parse5`) as `<!doctype html>` (no-quirks). For each
  inserted `span.ex-decision` the oracle reports SEEN, or why not: an ancestor with `hidden`/`inert`, template
  content, `select`/`noscript`, or a `<details>` whose child on the path is not its FIRST `<summary>` child.
  For a REFUSED fragment, the same composition was made with refusals stripped (a subclass clearing them) so a
  refusal of a mark that would have been SEEN shows as FALSE-REFUSE. 61 fragments; identical output under
  python3.12 and python3.14. The same 61 were run against the r1 composer (`6cc2fd04`) to attribute each
  result to a fold.
- **Real fragments.** All 34 `docs/explainers/*.fragment.html` composed with master's composer
  (`origin/master` = `2f5e3f3d`) and this head, under 3.12 and 3.14, one fixed `--source`. 33 decision-free
  pages byte-identical after normalising the timestamp, on both interpreters; the walkthrough differs from
  master only by the decisions, is identical 3.12 vs 3.14, identical to the r1 composer's output, counts 13
  tags, and the oracle reports all 13 SEEN.
- **Self-test:** `224/224 passed` on python3.12 and python3.14.
- **Mutants** on a temp copy (`git archive HEAD scripts docs`, outside the repo) — 21 run, listed under F3.
  ⚠ A first run with only `scripts/` archived was INVALID: every mutant was "killed" by the real-fragment
  case failing on the missing `docs/explainers/` — the unmutated copy itself scored 223/224. Re-run with
  `docs/` present; the baseline is then 224/224.

## Dispositions of r2 — each verified

| r2 finding | Disposition | Evidence | Closed? |
|---|---|---|---|
| X1 quoted ` open ` read as the attribute | auto-open REMOVED; mark in collapsed part refused | `<details title=" open "><summary>S</summary><p data-decision>` → REFUSE, oracle `collapsed <details>` | yes |
| X2 named group shows one section | same | `<details name="g" open>…<p data-decision>` → REFUSE (oracle agrees); a mark on the FIRST `<summary>` of a named group → COUNT, oracle SEEN | yes |
| X3 `<p hidden>` + block sibling false-refused | `_close_p` | Codex's exact fragment → COUNT 1, oracle SEEN; also `ul/li`, `h2`, `hr`, `p`, `pre`, `dl/dt`, `form`, `summary`, `details`, `<button><p hidden>x<div>` all COUNT and SEEN; hidden `b`/`i`/`a` above the p → REFUSE and the oracle confirms the reconstructed hidden clone wraps the tag | yes (see F1, F3) |
| X4 contrast read only 6 digits | `_hex_lum` refuses non-opaque / non-hex | mutants `rgba(...)`, `var(--ink)`, `transparent`, `#3a28` in `DECISION_CSS` each KILLED (222/224) | yes |

`<details>` probes beyond the self-test, all agreeing with the oracle: a mark on a later `<summary>` refused;
`<summary>` not a direct child refused; a `<p>` before the first `<summary>` (`<details><p>pre<summary data-decision>`)
COUNTED and SEEN; a nested `<details>` in the collapsed part refused; a mark in a `<details>` nested inside
the outer FIRST `<summary>` but in the inner's collapsed part refused; `<details/>` then a `<p data-decision>`
refused (the slash is ignored, so the p IS inside it — correct); `<summary/>` then content counted and SEEN.
No false refusal and no silent count among the `<details>` shapes.

## Findings

### F1 — MINOR — `_close_p` crosses the SVG/MathML scope boundaries, so a decision inside a hidden `<p>` is COUNTED and not seen — `fix_induced: true`

`scripts/brief-compose.py:1147` (`_P_SCOPE`) and `:1267-1277` (`_close_p`). HTML's "p in button scope" also
stops at MathML `mi mo mn ms mtext annotation-xml` and SVG `foreignObject desc title`. `_P_SCOPE` lists only
the HTML ones, so `_close_p` walks past `foreignobject`/`mi`/… , pops the hidden p, and the mark is counted.

Evidence (parse5 oracle, same on 3.12 and 3.14):

```
SILENT-COUNT ('COUNT', 1) oracle=['hidden <p>']  :: <p hidden>x<svg><foreignObject><div data-decision>fo</div></foreignObject></svg>
SILENT-COUNT ('COUNT', 1) oracle=['hidden <p>']  :: <p hidden>x<svg><desc><div data-decision>desc</div></desc></svg>
SILENT-COUNT ('COUNT', 1) oracle=['hidden <p>']  :: <p hidden>x<math><mi><div data-decision>mi</div></mi></math>
SILENT-COUNT ('COUNT', 1) oracle=['hidden <p>']  :: <p hidden>x<math><mtext><div data-decision>mt</div></mtext></math>
```

The r1 composer REFUSED all four (its stack kept the p). Caused by the r2 fold: it converts a refusal into the
one outcome the component exists to prevent (counted, not seen). Exposure is low — 7 real fragments contain
`<svg`, none `foreignObject` or `<math`, none `<p hidden` — hence MINOR. Fix direction: add the foreign
boundaries to `_P_SCOPE` (HTMLParser lowercases `foreignObject` → `foreignobject`); keeping a p can only refuse.

### F2 — MINOR — an EXPLICIT end tag pops past a scope boundary and drops an implicitly-closed hidden formatting element, so five shapes are counted and not seen; the docstring says this cannot happen — `fix_induced: false`

`scripts/brief-compose.py:1282-1286` (`handle_endtag`: `del self._stack[i:]` on the nearest same-named
entry, with no scope check and no active-formatting reconstruction) and the claim at `:1205-1208`
("Any OTHER element closed implicitly stays on the stack, which can only cause a refusal, never a silent
count"). Evidence (oracle):

```
SILENT-COUNT ('COUNT', 1) oracle=['hidden <b>']   :: <p>a<b hidden>c</p><div data-decision>d</div>
SILENT-COUNT ('COUNT', 1) oracle=['hidden <b>']   :: <div><b hidden>x</div><p data-decision>after misnest</p>
SILENT-COUNT ('COUNT', 1) oracle=['hidden <b>']   :: <div><b hidden>x</div><div data-decision>after misnest</div>
SILENT-COUNT ('COUNT', 1) oracle=['hidden <p>']   :: <p hidden>x<object></p><div data-decision>d</div>
SILENT-COUNT ('COUNT', 1) oracle=['hidden <div>'] :: <div hidden><table><tr><td></div><span data-decision>s</span></td></tr></table>
```

The first three are the r2 fold's own mechanism (the browser RE-OPENS a hidden formatting element around the
tag span) reached through an explicit end tag instead of an implicit `</p>` — the fold handled the implicit
route only. The last two: the end tag is ignored by the browser (no element of that name in scope) but the
scanner pops it. All five were silent counts under the r1 composer too, so not caused by the r2 fold; it
did restate the false invariant in the docstring. Misnested hidden markup is hostile, not seen in any real
fragment. Fix direction (if folded): on an end tag, do not pop past a `_P_SCOPE` element, and keep a hidden
`_FORMATTING` element "re-openable" until its own end tag — or file it and correct the docstring.

### F3 — MINOR — the self-test does not pin the p-closure sets, nor the false-refusal direction of the formatting check — `fix_induced: true` (instrument)

Doubt-driven mutants on the temp copy, baseline 224/224:

| Mutant | Result | Which direction it breaks |
|---|---|---|
| `_close_p()` call removed | KILLED | |
| formatting check removed | KILLED | |
| formatting check ignores `hidden` (any `b`/`i` keeps the p) | **SURVIVED** | false-refuses `<p hidden>a<b>c<div data-decision>` (oracle SEEN) |
| scope stop removed / `button` out of `_P_SCOPE` | KILLED | |
| `object` out of `_P_SCOPE` | **SURVIVED** | silent count: `<p hidden>x<object><div data-decision>` |
| `td` out of `_P_SCOPE` | SURVIVED | near-equivalent (`table` above every td also stops) |
| `li` / `hr` / `h2` out of `_P_CLOSERS` | **SURVIVED** (each) | false-refuses `<p hidden>x<li>`, `<hr><span>`, `<h2>` (oracle SEEN) |
| `table` INTO `_P_CLOSERS` | SURVIVED | the deliberate no-quirks omission; behaviour then matches the oracle — not a defect |
| `close_p` keeps the p; any `<summary>` allowed; `anc_collapsed` ignored; ON-`<details>` allowed; collapsed flag not stacked | KILLED (each) | |
| contrast: `rgba`, `var()`, `transparent`, `#3a28` in `DECISION_CSS` | KILLED (each) | |

`scripts/brief-compose.py:3067-3076` (the r2 implicit-`</p>` case) uses `ul`, `div`, `button` and a hidden
`b` only. One survivor (`object`) is in the silent-count direction. Not checked here whether the 86-entry
manifest (`scripts/mutations/brief-compose.json`) holds these mutations — this is about the self-test.

## Not findings (checked)

- `<p hidden>` then `<table>` → REFUSE though the oracle shows SEEN (2 fragments): the documented deliberate
  quirks-safe omission; errs toward refusal.
- 33 decision-free real fragments byte-identical to master's composer on both interpreters.

## Fold attribution

F1 and F3 are caused by the r2 fold, in `decision-scan` (F3's instrument is that component's self-test). Per the
r2 coordinator note, a fold-caused finding in `decision-scan` at round 3 is the THRASHING shape — that is the
coordinator's call; both are MINOR and neither is a BLOCKER.

VERDICT: NOT CONVERGED

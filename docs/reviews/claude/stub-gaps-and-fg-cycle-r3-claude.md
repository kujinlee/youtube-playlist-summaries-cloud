# Round 3 — `stub-gaps-and-fg-cycle` — Claude half (adversarial, final tree `4aabf35d`)

Subject: `git diff origin/master...HEAD`. Mandate: refute. Codex gap for this round is the coordinator's
alternation note, not mine.

## The bet (last row of `decision-log.jsonl`)

> round 3 finds no Blocking/High/Medium: no real chrome_script() defect inside the stated bound passing
> all cases, and no unexpected rendering change.

**Refuted on its first clause.** Two real `chrome_script()` defects inside the stated bound (load × storage ×
OS light/dark, one press of each control) pass **233/233** (M1, M2). Neither was caused by the r2 fold. Both
are pre-existing gaps in the stub suite, and #350 did not set out to close them. The rendering clause holds
(see "Checks that held").

Method. I mutated a COPY of `scripts/page_chrome.py` (one anchor per mutant, checked to bind exactly once on
its line) and ran `--self-test` on the copy. Nothing was written in the worktree, and `git status` is clean
after the run.

## Findings

### M1 — Medium — `scripts/page_chrome.py:990` (the code), `:2247` (the gap): on load, a SAVED theme never reaches the button's `aria-pressed`

The stub never loads with a saved `yps-theme`. The only saved-storage run is `saved={"explainer-scheme": "2"}`
at `:2247`. So the button's initial pressed state is checked only where the stored theme equals the OS theme.

Mutant: the initial state reads the OS instead of `cur()`:

```
b.setAttribute('aria-pressed',String(cur()==='dark'));
  -> b.setAttribute('aria-pressed',String(!!(window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches)));
```
```
## theme-aria-ignores-saved: rc=0 233/233 passed
```

What it breaks: take a reader whose OS is light and who saved dark. The page renders dark, and the button
announces "not pressed". An OS-dark reader who saved light gets the inverse. This is the r4 Codex Medium's
class (`aria-pressed` is what a screen reader announces), on the load path.

**Fix:** add one stub run with `os_dark=False, saved={"yps-theme":"dark"}` that asserts
`pressed0 == "true"` and `data-theme == "dark"`, and its mirror with `os_dark=True, saved={"yps-theme":"light"}`.
Both clauses are needed: the attribute half is today guarded only by a substring case
(`the script applies the stored theme before paint`). Not caused by r2 (pre-existing).

### M2 — Medium — `scripts/page_chrome.py:1015` (the code), `:2247` (the gap): on load, a SAVED opt-out style is applied but no option is marked

The saved-style run asserts only `scheme0`, the attribute. The options' class and `aria-pressed` are asserted
on load only for the default (`aria0`).

Mutant: the load path sets the attribute directly instead of calling `sset`:

```
sset(sv==='1'||sv==='2'?sv:TD);
  -> if(sv==='1'||sv==='2')R.setAttribute(TA,sv);else sset(TD);
```
```
## text-load-attr-only: rc=0 233/233 passed
```

What it breaks: on every reload by a reader who chose style 1 or 2, the page shows that style while no option
is marked, either visually or to a screen reader. This is the same class as M1.

**Fix:** extend the `:2247` case to `_field(..., "scheme0", "aria0")`, expecting `("2", ["false","true","false"])`,
and add the class for that option. Not caused by r2 (pre-existing).

### L1 — Low — `scripts/page_chrome.py:2179` (the press), `:1007` (the write): only ONE opt-out value is ever pressed, so persistence is witnessed at one input

The only opt-out pressed is `sbs[0]`. It is both the FIRST option and value `'1'`, so any write that produces
`'1'` satisfies `stored`:

```
localStorage.setItem(TK,s) -> localStorage.setItem(TK,'1')
## text-store-constant: rc=0 233/233 passed
localStorage.setItem(TK,s) -> localStorage.setItem(TK,box.querySelectorAll('button[data-s]')[0].getAttribute('data-s'))
## text-store-first-option: rc=0 233/233 passed
```

With either mutant, choosing style 2 brings back style 1 on reload. The first is contrived. The second
(the wrong element) is plausible. The memory lesson "two distinct inputs, in one case" applies directly.

**Fix:** press `sbs[1]` (`'2'`) as well as, or instead of, `sbs[0]`, and assert `stored` after each press.
Not caused by r2.

### L2 — Low — `scripts/page_chrome.py:2147` (stub) and `:2171`/`:2176` (the report): the new `--chrome-h` clause passes for an AMBIENT reason

In the stub, `root.style` is a plain object, and its `setProperty` writes `root.style[k]=v`. So the #350
case's `--chrome-h` value cannot tell `setProperty` apart from bracket assignment. In a real browser, bracket
assignment does nothing (Chromium 148, measured):

```
{"bracket":"","setProperty":"43.109375px","ua":"Chrome/148.0.7778.96"}
```

The plain mutant is killed, but not by the case this branch added:

```
## chrome-h-bracket: rc=1 232/233 passed
    [FAIL] ...and the same measurement feeds both the slot and scroll-padding, so they cannot disagree: got (True, False) want (True, True)
```

That is the substring gate at `:1958`. A mutant that keeps the substring present (dead code) survives:

```
"var _sp=document.documentElement.style;_sp['--chrome-h']=h+'px';if(0)_sp.setProperty('--chrome-h',h+'px');"
## chrome-h-bracket-keep-text: rc=0 233/233 passed
```

The keep-text form is contrived, so this is Low. Still, the new value clause, whose purpose was to stop relying
on substrings (#350 (2)), does not guard this half.

**Fix:** keep custom properties in a separate map,
`root.props={};root.style.setProperty=function(k,v){root.props[k]=String(v);}`, and report
`root.props['--chrome-h']`. Bracket assignment then reads `null`. Introduced by this branch (initial commit),
not by the r2 fold.

### L3 — Low — `docs/backlog.md:332` (row #350): the closure still describes superseded state, and "both VERBATIM" is not accurate

- *"one case asserts `['40px','40px']`"*: the case asserts `["43.109375px","43.109375px"]` and
  `["130.5625px","130.5625px"]`. The r1 fold changed the box and appended a ⟳ note, but left this sentence
  reading as current.
- *"Both r5 mutants are now manifest entries VERBATIM"*: r5's mutant (b) (`comprehensibility-chrome-cases-r5-claude.md:54`)
  appends `slot.style.minHeight='0px';` right after the write, INSIDE `sync()`. The manifest entries
  `the slot's reserve is zeroed after load` and `--chrome-h is zeroed after load` overwrite ONCE, after the
  `ResizeObserver` line, outside `sync()`. Only mutant (a) is verbatim. I ran r5's (b) verbatim, for both values,
  and the named case kills it (`232/233`), so coverage holds and only the claim is wrong. This is the same
  claim r1 Claude graded Medium. It recurs in milder form because the r1 fold fixed the instance and not the
  sentence.

**Fix:** drop or qualify the `['40px','40px']` clause, and write "(a) verbatim; (b) as two once-after-load
overwrites, which also kill r5's in-`sync` form". Caused by the r1 fold, not r2.

## Checks that held (constructed and run)

- **All 9 new manifest entries** bind exactly once and redden the case they name. Two have a co-killer, which
  is legitimate: `keeps the stored opt-out` (also `...clears the stored key`) and `the reserve is rounded`
  (also `the reserve is measured in fractional pixels`). **All 112** page_chrome entries were re-run through
  my own driver on a copy with a redirected `HOME`: `entries 112 problems 0`. That backs the record's
  "112/112 killed and attributed". Manifest total `2026` equals `EXPECTED_MUTATIONS`, and
  `check-plan-code.py --self-test` gives `215/215 passed`.
- **Other mutants inside the bound, all killed:** a stored theme constant (`'light'`); the saved theme applied
  for dark only; opt-out `'1'` dropped from the load whitelist; the pinned early-return removed from `sync`;
  the reserve set on the bar instead of the slot; r5 (b) verbatim, both values.
- **Six-state differential in Chromium 148** (1280×900; OS via `colorScheme`; press via the stored `yps-theme`,
  so the real script applies it), branch against `origin/master`, every `body *` element across 14 computed
  properties plus leaf text:
  - In five states, each page differs ONLY in `SPAN.chrome-when` and its `TIME`: 2/636 and 2/716.
  - In OS-light with nothing pressed, 500/636 and 597/716 differ. On master all of
    `--fg/--fg2/--fg3/--ink/--ink-soft/--ink-faint/--prose` are `""` and `.ex-body p.lede` is `rgb(0, 0, 0)`.
    On the branch they are `#1b1a18/#3d3a35/#6b6560` (identical in the three pairs) and `rgb(61, 58, 53)`.
  - `--fg/--fg2/--fg3` resolve in all 12 branch states, and `--ink*` equals `--fg*` in every state, so the
    literals match their blocks.
  - **Min bold contrast ≥ 4.5:1 in every state.** why-not-converging is 5.06 (OS light, nothing pressed: master 5.06).
    decision-ladder is 4.66 in its dark states (a bold `code` in `--fg3`, identical on master) and 5.14 in
    OS light with nothing pressed (master 5.62). My probe is wider than the "7.79:1" Codex reported: it counts
    any element of weight ≥ 600, including `th` and `code`, not only emphasis. No state falls below 4.5.
  - My element counts (636/716) differ from the dashboard's 643/723 by 7 on each page. That is consistent with
    a `*` probe that also counts `html`/`head` children, so it is not an overstatement.
- **Dashboard entry and #351 closure:** supported as written. The lay line ("almost all text showed in plain
  black … nothing else changed") matches the differential.

## Is the r2 fold implicated?

No. The r2 fold (bar grows 43.109375 → 130.5625px across the resize) does what it says: the "first height
forever" mutant is a manifest entry and is killed. Nothing in M1–L3 comes from it. M1, M2 and L1 are
pre-existing, L2 comes from the initial commit, and L3 from the r1 fold. **No finding this round is r2
fix-induced**, so the thrashing watch on `stub-page` does not advance on these.

## Disposition note for the coordinator

M1 and M2 are the bet's named failure observation: a real defect inside the stated bound, passing all cases.
They are outside #350's two named gaps. If the predecessor branch's DEFER rule ("a coverage gap inside the
stated bound is FILED, not folded") governs here, they are candidates to FILE. Either way, the bet as written
is refuted.

VERDICT: NOT CONVERGED

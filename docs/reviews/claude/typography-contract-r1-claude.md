# typography-contract — round 1, Claude half (adversarial, mandate: REFUTE)

Subject: `git diff origin/master...HEAD` at `68e0f8ee` in the `wt-typo` worktree. Three files:
`.agents/skills/shared/explainer-delivery.md` (+21, §2), `docs/backlog.md` row 226, `docs/dashboard-entries.md`.

## What I ran

- Read `scripts/page_chrome.py` (`TEXT_*` :124-141, `TEXT_SCOPE_CLASS` :689, `chrome_bar` :1302,
  `text_style_control` :742, `text_style_css` :761, `chrome_script` :968-1015), `scripts/brief-compose.py`
  `SHIM` (:89-160) and `chrome_for` (:796-812), `CONTEXT.md` *The common look* (:116-121),
  `scripts/check-theme-token-coverage.py`, the four explain-* / brief SKILL.md files.
- Rendered every committed composed page that carries `.ex-body` in Playwright Chromium (`colorScheme`
  dark and light, JS on and off, fresh context, so no stored theme) and computed the colour of `h2`,
  `.ex-body` and the first `b`/`strong`, plus WCAG contrast against the effective background.
  Scripts: `typo-r1-tmp/m.mjs`, `typo-r1-tmp/n.mjs`.
- Grepped every committed `*.fragment.html` for status-token declarations and every page for
  `setItem` in the switcher.
- `check-explainer-delivery.py` rc=0 (0 restatements), `check-canonical-source.py` rc=0,
  `check-docs.py` OK, `check-dashboard-entry.py` "an entry block was added", `check-backlog-closure`,
  `check-features`, `check-anchors` all rc=0.

## Findings

### F1 — HIGH — closing #226 hides part (c), and part (c) is a live 1.90:1 defect on the pages the contract describes

`docs/backlog.md:252` closes the row as ✅. The row lists three parts. Part (c) is *"light/dark parity
for the new `--em` under `check-theme-token-coverage.py`, the guard that exists because a page once
shipped 1.03:1 contrast."* Neither the earlier PARTLY note nor this closure says (c) shipped. It did not:

- `check-theme-token-coverage.py` compares the shim's OS-dark tokens against **`gen-dashboard.py`'s**
  light palette (`PAGE_SRC`, :70). It never sees `--em` or any explainer page.
- The shim gives `--em` three values: `html{… --em:#2d4a7c}`, `:root[data-theme="light"]{--em:#2d4a7c}`,
  `:root[data-theme="dark"]{--em:#9db8e8}` (`brief-compose.py:106,115-116`). The OS-dark block
  `@media (prefers-color-scheme: dark){ html{…} }` (:128-131) **does not set `--em`.**
- `chrome_script` sets `data-theme` **only when a choice is stored** (`page_chrome.py:986`
  `if(s==='dark'||s==='light')R.setAttribute(A,s)`). So a first-time reader on a dark OS gets no
  attribute, and `--em` stays at the light value.

Measured, fresh Chromium context, `colorScheme: 'dark'` (same with JS on and off):

| page (composed, carries `.ex-body`) | emph colour | bg | contrast |
|---|---|---|---|
| `2026-10-20-topic-why-not-converging.html` | rgb(45,74,124) = `#2d4a7c` | rgb(30,29,35) | **1.90** |
| `2026-10-23-topic-decision-ladder.html` | `#2d4a7c` | rgb(30,29,35) | **1.90** |
| `2026-10-07-topic-retrieval-fixed-gap-open.html` | `#2d4a7c` | rgb(21,22,26) | **2.05** |
| `2026-10-06-brief-dev-process-speed.html` (declares its own `--em`) | `#9db8e8` | rgb(22,21,26) | 9.04 |

So three of the four pages that actually spend the `--emph` role render every bold phrase at about
2:1 for a dark-OS reader. That breaks the bullet directly above the new text (*"Light and dark both
legible"*, `explainer-delivery.md:100`), and it is the same "light value survives on a dark page"
failure the 1.03:1 guard was written for. The new bullet also points readers to *"the `--em` pair …
[in] `brief-compose.py`'s shim"*. That pair has no OS-dark half, so the pointer leads to the defect.

The defect predates this branch (the branch changes no code), but closing the row is what hides it:
the row is the only place that records (c), and it is now ✅.

**Fix:** do not close #226. Either keep it open for (c), or close (b) and file (c) as its own row with
this measurement. The code fix is probably `--em:#9db8e8` in the shim's OS-dark `html` block. A
`[data-theme="light"]` toggle still beats it (0,1,1 against 0,0,1). Check `check-theme-token-coverage`
afterwards: it would then ask the dashboard light palette to cover `--em`. Add a measurement line to §2
as well (emphasis contrast in OS-dark with no stored theme). The bullet has no "check it by measuring"
recipe of its own, and a measurement like that would have caught this.

### F2 — MEDIUM — the RESERVED set is incomplete and contradicts `CONTEXT.md` and the explain-* skills

`explainer-delivery.md:113`: *"The status colours `--verified` and `--warn` are RESERVED"*. Naming two
tokens makes the list read as exhaustive. But:

- `CONTEXT.md:120` names a different set: *"`--verified`/`--cool` mean measured and `--hot` means
  defect"*.
- `--defect` is declared in **19 of 22** committed fragments and in the shim itself
  (`brief-compose.py:92,129`), always in a red hue. `--good` is in 19 too, aliased to `--verified`.
- `explain-diff/SKILL.md:114`, `explain-findings/SKILL.md:137` and `brief/SKILL.md:131` each assign a
  semantic hue to **defects** (and to structure and decisions), not only to verified and warning.

Under the new wording, spending `--defect` red on emphasis is allowed, which is the exact harm the
paragraph exists to prevent. Two files now name different reserved sets for one concern.

**Fix:** reserve the class instead of two names. For example: "every status token — `--verified`/`--good`,
`--warn`, `--defect`, and any page-local `--hot`/`--cool` — is reserved; emphasis spends `--em` only."
Make `CONTEXT.md:120` agree with it or point to it.

### F3 — MEDIUM — "opts in with `.ex-body`" does not say that a page MUST opt in, or what happens if it does not

`explainer-delivery.md:102-105`: the heading says *"Structure is carried by COLOUR ROLES"*, then
*"Content opts in with the `.ex-body` class"*. The code says nothing emits that class
(`page_chrome.py:676-680`: *"NOTHING in this repository emits it … hand-authored"*). The composer also
silently drops both the switcher and `text_style_css()` when the class is absent (`brief-compose.py:797-809`).
Grepping `.agents/` for `ex-body` finds only this line. No explain-* skill tells an author to put it on
the content wrapper.

So a fork that follows the skills produces a page with no roles and no switcher, and no gate refuses it.
That fork's page is #226's own falsifier: *"a page producer emits a page whose heading, body and emphasis
resolve to the same colour"*. I measured that state on a committed page:
`2026-10-02-topic-recent-prs-found-solved.html` gives h2 = p = b = rgb(236,234,240). The row's title
problem is "documented nowhere **and enforced nowhere**". This branch fixes "documented" and closes the
row while "enforced" stays true and the FAILS IF condition is still producible.

**Fix:** say it as an instruction: "wrap the page's content in `<… class="ex-body">`. Without it the
composer omits the switcher and the roles do not apply." Either keep the row open for enforcement, or
record in the closure that FAILS IF has no guard.

### F4 — LOW — "storage holds only the opt-outs" is false of the named reference implementation

`explainer-delivery.md:119`. True of `page_chrome.chrome_script` (:1006: `localStorage.removeItem(TK)`
for the default). False of `docs/explainers/2026-10-05-topic-why-x-not-y.{fragment.,}html:219`
(`try{ localStorage.setItem('explainer-scheme',s); }`, which runs for `'3'` too). The same inline copy is
in `2026-10-06-brief-dev-process-speed` and `2026-10-15-brief-status-alignment.fragment.html`. #226 still
calls that page the *"Reference implementation … (copy from it)"*. Nothing renders differently, because
load ignores a stored `'3'` (`page_chrome.py:995-1001` says so). But the sentence is stated as a property
of the contract, and its reference implementation does not have that property.

**Fix:** "the shared switcher (`page_chrome.chrome_script`) stores only the opt-outs". Or drop the
storage clause: the render argument (no attribute means colour) does not depend on it.

### F5 — LOW — two smaller factual slips in the new text and the closure note

- *"green and amber in the committed fragments"* (`explainer-delivery.md:114`) is not the whole set.
  `--warn:#8a2f2f`/`#e39a9a` (red) is declared in `2026-09-23-topic-pr-336-338.fragment.html`, and
  teal-leaning `--verified` (`#1f5c4a`/`#7fc0ab`, `#0f5c4a`/`#63c9ab`) appears in others. The backlog
  closure goes further: *"so 'teal and red' would have been a false colour claim"*. Teal and red are both
  present, so that is an overstatement. The useful point (hue varies, so name the token) survives. Say
  "mostly green and amber" or just "varies".
- *"The tabular producers (dashboard, goals, backlog) do not opt in"*. Also true of `gen-features-page.py`
  and `gen-work-lines.py`. `chrome_bar`'s own docstring (`page_chrome.py:1307-1308`) lists features as
  one of the four tabular callers. The clause is true but incomplete. Say "the non-explainer producers
  (every `gen-*.py`)" or list all of them.

### Checked and found TRUE

- The role table matches `text_style_css()` :779-785 (`--head:var(--accent)`, `--prose:var(--fg2)`,
  `--emph:var(--em)`; `h1`–`h4`, `.ex-body` itself, `strong,b`).
- "Colour is the no-attribute default, so JS-off still renders in colour": bare `:root` block, and with
  JS disabled the colours above match the JS-on run.
- The pointers resolve: `--accent` pair at `CONTEXT.md:117`, `--em` pair and fallbacks in `SHIM`.
  No value is copied into §2.
- Restatement: `check-explainer-delivery.py` and `check-canonical-source.py` are green. The bullet lives
  in the shared contract, which is the canonical home, and no skill restates it.
- The §1 location contradiction the row mentions really is gone from §1 on master.

## Round classification

All five findings concern the new prose or the closure decision. None was caused by an earlier round's
fix (this is round 1).

VERDICT: NOT CONVERGED

# PR #175 — dual review, round 1 (Claude half)

**Subject:** `origin/master..247dc12` on `fix/dashboard-link-contrast` — 2 commits, 4 files.
**Codex half:** [`pr-175-link-contrast-codex.md`](pr-175-link-contrast-codex.md) (`gpt-5.5`; `gpt-5.6-*`
returned HTTP 400 and the wrapper walked down unaided, which is the documented normal path).
**Why this round happened at all:** the branch was authored, guarded and judged green by one person
and merged nothing. Four of the six real defects in the preceding slice were found by a reviewer
rather than the author, so *unreviewed* was the honest description, not *ready*.

**Verdict: NOT CONVERGED at round 1. Three findings, all fixed in this branch; re-review needed.**

---

## The findings

### 1 — Blocking. The new guard was inverted: blind to the defect, loud on a reformat

`scripts/gen-dashboard.py`, the two cases added by `14a3bb9`. They asserted that
`a{color:var(--link)}` was **present** and that `--link:` occurred **twice**. Neither statement is
the property the rule exists for. Mutation-tested against a copied `scripts/` tree, control green at
105/105:

| mutation | real effect | old guard |
|---|---|---|
| `--link:#8cbde0` → `#0000EE` | **1.90:1** — the exact original defect | **survived** 105/105 |
| `--link-visited:#c3a6e0` → `#551A8B` | **1.62:1** | **survived** 105/105 |
| `--link:#1f5d8c` → `#f2f4f6` | invisible in light mode | **survived** 105/105 |
| dark `--link` → the *light* value, kept in `:root` | dark mode broken, total still 2 | **survived** 105/105 |
| delete the dark `--link` definition | rule breaks | caught |
| delete `a{}` | rule breaks | caught |
| `a{color` → `a { color` | **nothing** | caught |

Two independent blind spots — **value** and **scheme** — plus `a:hover` uncovered. Three symptoms,
one cause: a guard written from the symptom that had already happened rather than from the property.
Patching each separately would have been the instance-not-class trap a fourth time.

**Fixed:** `contrast_failures()` reads the palette out of the emitted stylesheet and asserts the
WCAG ratio for `--link`, `--link-visited` and `--ink` against `--bg`, `--panel`, `--need-bg` and
`--err-bg`, in both schemes. All eight mutations above are now caught; control 111/111. The
presence cases are kept — a palette can be perfect while nothing references it, which is exactly
the state that shipped.

### 2 — Blocking. The fix was instance-not-class: the sibling generator had the same defect, worse

`scripts/gen-backlog-page.py` carried **five** link rules — `.qabody a`, `.depmap a`, `.rootref a`,
`.num a`, `td.mono a` — every one correct. Three anchors on the generated page sit in `.prose` and
`.status` (rendered from `md(r['body'])`, so the count grows with every markdown link filed into a
backlog item) and match none of them. They inherited the browser default:

| | dark `--ground` `#101318` | dark `--card` `#171b22` |
|---|---|---|
| `#0000EE` | **1.98:1** | **1.84:1** |
| `#551A8B` | **1.69:1** | **1.57:1** |

Worse than the dashboard bug this branch was opened to fix. `.prose code` sets background but no
colour, so the `<code>` inside those anchors inherited it too.

⚠ **Codex explicitly cleared this file** — *"gen-backlog-page.py … define link colors via theme
variables; I did not find the same defect."* True of the selectors it named, silent about the
anchors those selectors do not reach. That is this repo's dominant defect shape, committed inside
the review of a fix for that same shape. Recorded because it is the argument for the dual gate, not
against Codex.

**Fixed:** an unscoped `a{color:var(--structural)}` — measured, 6.40:1 worst case across all six
surfaces — plus `link_contrast_errors()` in that script's own suite, checking all **four** palette
blocks (the page has a manual theme toggle, so `:root[data-theme=…]` is live CSS). 55 → 64 cases.

### 3 — Important, found while writing the fix for 2. The new guard's own check was vacuous

`link_contrast_errors()` first refused a page with no unscoped rule via
`"a{color:var(--structural)}" not in page`. That substring is **contained in the scoped rules**
(`.qabody a{color:var(--structural)}`), so it stays true with the unscoped rule deleted — the guard
passed on precisely the defect it existed to catch. Now anchored with `re.search(r"^a\{…", re.M)`,
with the near-miss pinned as its own case. Mutation-verified: unanchoring the guard **and** deleting
the rule is caught by that case, and only by that case.

---

## What was checked and found sound

- **Every number in the added comments is exact**, recomputed: 1.90, 8.84, 1.62 (dashboard);
  1.98, 1.84 (backlog).
- **All 12 tinted-surface combinations pass** (`--need-bg`, `--err-bg`, both schemes): worst 5.64:1.
  Neither the original author nor Codex measured these; they hold.
- `ht.count("--link:")` genuinely could not be inflated by `--link-visited:` — `'--link:'` is not a
  substring of `'--link-visited:'`. The old guard was wrong for other reasons, not that one.
- **Backlog #69/#70 summaries** match the real rows in `docs/backlog.md`, in the right group.
- **Scope is clean.** All four files are mechanically required.
- `a:hover{color:var(--ink)}` is sound: 12.43–16.42:1 on every surface, LVHA order correct. It is
  now covered by the ratio assertion rather than by a dedicated presence case.

## Corrections to claims made earlier in this branch

- The comment *":visited is declared EXPLICITLY rather than left to the cascade"* justified the rule
  with a hazard the sibling `a{}` rule already removes: author-origin declarations beat the UA
  `a:visited` rule regardless of specificity, so the cascade would yield `var(--link)`, not
  `#551A8B`. The rule is good styling; its stated reason was stale. **Superseded** — the comment
  block was replaced wholesale by the fix for finding 1.

## Instrument failures encountered (all three reviewers, same shape)

Every one of the three mutation harnesses run today — Codex's, the reviewing subagent's, and this
one's — **reported a red or meaningless control on first use**: a copied script that could not find
its siblings, a baseline read from an already-mutated file, a generator whose repo root did not
resolve. Each was caught only because a control run was executed. Without one, every "caught" row
in the tables above would have been an artefact. Two homemade instruments also had to be discarded
here: an anchor scanner that over-counted 9 → 3 by unwinding its stack on an unmatched end tag, and
a `grep -c` that returned 4 for a rule that appears once.

## Known gap, stated rather than hidden

The plan's **43-mutation manifest was not extended** to cover the new cases. Their coverage is
hand-verified above and reproducible, but it is not in the mechanised manifest, so it is not
enforced by CI. Retargeting that manifest onto the delivered scripts is **backlog #70**, which this
branch's own CI step names as its retirement condition; adding entries to the plan-side manifest now
would be work thrown away by #70. `--compare . --verify-evidence` passes at 2 files / 43 mutations /
0 survivors, and the evidence block was regenerated by script, never typed.

## Gates

`gen-dashboard.py --self-test` 111/111 · `gen-backlog-page.py --self-test` 64/64 ·
`check-dashboard-entry.py --self-test` 46/46 + 5/5 cannot-run · `check-plan-code.py --self-test`
121/121 · `check-docs.py` OK · `check-anchors.py` OK · `check-review-rounds.py` OK ·
`check-plan-code.py --compare . --verify-evidence` OK.

**Not run:** `test:integration`, `test:e2e` (need a live Supabase stack) — unchanged by this branch,
which touches no TypeScript.

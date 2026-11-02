# stub-gaps-and-fg-cycle — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at `4b52350c`, worktree `wt-gaps`. Mandate: REFUTE.
I wrote nothing in the worktree or repo and ran no git writes. All mutants ran on copies under `gaps-r1-tmp/`.

## What I ran, and what held

| CHECK | RESULT |
|---|---|
| `page_chrome.py --self-test` on HEAD | `233/233 passed` |
| The 3 new manifest entries, each applied by hand to a copy | each anchor occurs exactly once; each one turns the case it names red (`expect` matched a `[FAIL]` line) |
| Scoped `check-plan-code.py --mutate .` on a pruned copy of HARNESS_TREE (+ `.agents/skills`), only `page_chrome.json`, other EXPECTED counts zeroed in the copy | `106 mutation(s), 106 killed, 106 attributed … 0 survivor(s)` — reproduces the claim |
| The exact r5 mutants from `docs/reviews/claude/comprehensibility-chrome-cases-r5-claude.md:53-54` (`setItem(TK,'1')` in the default branch; `minHeight='0px'` / `--chrome-h` `0px` appended inside `sync`) | each one fails ONLY the new #350 case (`232/233`), so the new case is what kills them |
| Ambient-pass check on the new case | `reserve` is `[null,null]` unless `sync()` really ran; `back[0]` stays `'1'` if the default press does nothing; `back[1]` is backed by the earlier `stored` case, which proves the key was written first. No ambient pass found, apart from the constant height in F3 |
| Chromium, master page vs branch page, both pages, 6 states (OS light/dark × nothing / `yps-theme=light` / `yps-theme=dark`), computed `color`, `background-color`, borders, outline, decoration, fill, stroke, box-shadow, caret, column-rule on every element and on generated pseudo-elements | **OS-light, nothing pressed:** differs on 604 of 723 elements (decision-ladder) and 507 of 643 (why-not-converging). **The other 5 states: 0 differing on both pages.** Claim confirmed |
| Does the cycle resolve on the branch? | yes. `--fg`, `--fg2`, `--fg3`, `--ink`, `--ink-soft` and `--ink-faint` all resolve in all 6 states. Master resolves all six to the EMPTY string in OS-light-nothing-pressed, and body is `rgb(0, 0, 0)` there |
| Are the literals the right ones? | yes. In each of the 4 blocks per fragment, the new `--ink`, `--ink-soft` and `--ink-faint` equal the same block's `--fg`, `--fg2` and `--fg3` (light `#1b1a18/#3d3a35/#6b6560`, dark `#ece9e3/#c6c1b8/#918a80`) |
| Other pages carrying the cycle? | `grep -E -e '--(ink\|ink-soft\|ink-faint) *: *var\(--fg\|--card *: *var\(--bg2\|--good *: *var\(--verified'` over `docs/explainers/*.html` returns 0 hits, so the class is empty on disk |
| `check-theme-token-coverage.py` (+ `--self-test`), `check-selftest-counts.py`, `check-docs.py`, `check-dashboard-entry.py` | all green (`12/12`, 59 counts verified, docs OK, entry added) |

## Findings

### F1 — MEDIUM — the closure says both r5 mutants are manifest entries, but r5 mutant (1) is not, and the entry standing in for it was already dead before this branch
`docs/backlog.md:332` (closure text) and `scripts/mutations/page_chrome.json:1136`.
- **Claim:** *"Both r5 mutants are manifest entries, plus the dropped `removeItem`"*. The row's own FALSIFIER is *"each mutant above, as a manifest entry, must go red via a named case."*
- **What is on disk:** the manifest holds 3 entries, not 4:
  1. `choosing the default text style keeps the stored opt-out`, which drops `localStorage.removeItem(TK)`;
  2. `minHeight='0px'`;
  3. `--chrome-h` set to `0px`.
- Mutant (1) of r5 is **`localStorage.removeItem(TK);localStorage.setItem(TK,'1');`** (r5-claude.md:53), and it is in none of them.
- Entry 1 is a different mutant. I applied it to a copy and it turned **two** cases red. One was the new case. The other was the pre-existing substring case at `page_chrome.py:1835`, `...and clears the stored key rather than storing the default` (`"localStorage.removeItem(TK)" in _js`). So that mutant was already killed on master and adds no kill.
- **Effect:** the new case does kill r5 (1) (measured, `232/233`). But no ratchet pins that kill. If the case is later weakened, the gap reopens with the manifest still green, and that is exactly what a manifest entry exists to prevent.
- **Fix:** add r5 (1)'s exact edit as an entry, or replace entry 1 with it, naming the #350 case. Bump `EXPECTED_MUTATIONS` (106→107 if added). Then say "r5 (1) and r5 (2, as two entries) plus the dropped `removeItem`".

### F2 — LOW — choosing the default text style can wipe the saved THEME and every case still passes
`scripts/page_chrome.py:2179` (`REP.back` records only `'explainer-scheme' in ST`).
- **Mutant:** in `sset`'s default branch, `localStorage.removeItem(TK);` → `localStorage.removeItem(TK);localStorage.removeItem(K);`
- **Result:** **`233/233 passed`**.
- **What a reader sees:** they pick the default text style, reload, and their dark/light choice is gone.
- This is inside the bound, because the stub records storage, and it is the same class as #350 (1): a removal that is not asserted.
- **Fix:** record the whole store after the default press (`REP.back=[…, JSON.parse(JSON.stringify(ST))]`). Assert it equals `{"yps-theme": "light"}`, the value the two theme presses leave.

### F3 — LOW — "the bar's MEASURED height" is indistinguishable from a constant, because every stub box is 40px tall
`scripts/page_chrome.py:2131` (`getBoundingClientRect` returns `height:40` for every element) and the new case at `:2254`.
- **Mutant:** `var h=bar.getBoundingClientRect().height;` → `…height;h=Math.round(h);`
- **Result:** **`233/233 passed`**. The substring case at `:1952`, "the reserve is measured in fractional pixels", still finds its text, and the stub's integer height cannot show the rounding. The mutant defeats exactly what that case defends.
- The same constant also means a reserve measured off any other element (slot, theme button) gives the same `'40px'`. Today only substring cases kill those.
- **Fix:** give the bar a distinct fractional height (e.g. `37.5`) that no other stub box shares, and assert `['37.5px','37.5px']`.

### F4 — LOW — the reserve is asserted only at load, so a resize that zeroes it passes
`scripts/page_chrome.py:2171` (only read point) and `:2175` (`rcb([])`, where only the margin is read).
- **Mutant:** `new ResizeObserver(sync)` → `new ResizeObserver(function(){sync();slot.style.minHeight='0px';})`
- **Result:** **`233/233 passed`**.
- Contrived, but it is the same "executed, not asserted" class as #350 (2), on the resize path the stub already invokes.
- **Fix:** read `slot.style.minHeight` and `--chrome-h` again after `rcb([])`.

### F5 — LOW — the comment above each new literal still says to do the opposite, and it is the template that produced the cycle
Both fragments, lines 9, 23, 44 and 57 (and the composed pages at the matching lines).
- **The comment reads:** *"Declared as var() references so each resolves to THIS palette's own role — a shared hex would collapse the roles and **a second literal would drift**."*
- **The line directly below it now reads:** `--ink:#1b1a18; --ink-soft:#3d3a35; --ink-faint:#6b6560;`. That is a second literal, and it was chosen because a `var()` reference forms a cycle with `brief-compose.py:92` (`--fg: var(--ink, …)` on `:root`, concatenated after the fragment, so it wins at equal specificity in the bare light state).
- The next author who copies this palette is told to use `var(--fg)`, which recreates the cycle. That is how these two pages got it.
- There are now 12 duplicated literals per fragment that must track `--fg/--fg2/--fg3`, and nothing checks that they agree.
- **Fix:** rewrite the comment to say the literal is deliberate and why (a `var(--fg)` alias cycles through the shim's `--fg:var(--ink)` in OS-light). Make sure backlog #351 (on PR #396's branch, which I could not see) covers a guard against the alias shape. The `grep` above is that guard's subject.

### F6 — LOW — the dashboard understates what was broken
`docs/dashboard-entries.md:17468`.
- **The entry says:** *"body text on two explainer pages showed in plain black"*.
- **Measured:** all six tokens were invalid, not only `--fg`: `--fg2`, `--fg3`, `--ink-soft` and `--ink-faint` were empty too. Secondary and faint text, and any border using `currentColor`, also fell back to black. That is 604 of 723 and 507 of 643 elements with a different computed colour.
- *"nothing else on those pages changed"* is true: 0 differing elements in the other five states.
- **Fix:** "text on two explainer pages — body, secondary and faint — showed in plain black …".

## Verdict reasoning
- **(B) is correct as shipped:** the differential is exactly as claimed, the literals are right, the cycle is gone, and no other page carries it.
- **(A)'s new case is genuine and kills both exact r5 mutants.**
- **But the closure's record is wrong on its own falsifier (F1):** r5 (1) is not a manifest entry, and the entry offered in its place was already killed on master.
- The fix is a one-entry manifest change plus a sentence, so it is cheap. F2–F4 are survivors inside the stated bound, of the class #350 is about, and can be filed under the defer bet. F5–F6 are wording.

VERDICT: NOT CONVERGED

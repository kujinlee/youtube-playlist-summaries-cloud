# Round 5 — `comprehensibility-chrome-cases` — claude (adversarial, final tree)

Subject: `git diff origin/master...HEAD`. Worktree head `0ab98e9b`, clean. Mandate: refute.
All scratch work is in `scratchpad/claude-r5-tmp/`. Nothing in the worktree was written, and no git writes were run.

## What I re-derived (the parts that held)

| Claim | Re-derived how | Result |
|---|---|---|
| 11 / 3 / 8 tracked pages carrying `#chrome-theme`, pinned and not (on master) | `git ls-tree` over every `.html` at `origin/master`, matched `id="chrome-theme"` and `chrome-pinned{position:fixed` | **11 / 3 / 8** on master; **11 / 4 / 7** on HEAD (+1 recomposed page). Holds |
| The other 6 fragments use the exclusion form and `missing_palettes` refuses them | `missing_palettes(fragment + theme_control())`, which is how `brief-compose.py:773` calls it | `['light']` for all 6, and `[]` for `dev-process-speed`. Holds. ⚠ Calling it on the bare fragment gives `[]`, because `has_control` is false there |
| There are 19 committed fragments with an exclusion (the architecture review) | `git ls-files … \| xargs grep -l ':root:not([data-theme="light"])'` | 19. Holds |
| Cases 232 | `page_chrome.py --self-test` | `232/232 passed`. `check-selftest-counts.py` is green |
| Manifest +14; `EXPECTED_MUTATIONS` page_chrome 103, total 2017 | counted `scripts/mutations/*.json` | 89 → **103** (14 new names); sum **2017**. Holds in the code |
| `missing_palettes` is identical to master | diffed the function at `origin/master` against HEAD | function body byte-identical. One stray blank line follows it (F5) |
| `brief-compose.py` change is comment-only | diff | inside the `SHIM` CSS comment only. `brief-compose --self-test` 153/153. `_applied_css` strips comments, and the comment has no `:root[data-theme=…]` substring, so no predicate changes |
| Scoped mutation run | copied the HARNESS_TREE paths plus `.agents/skills` to `claude-r5-tmp/mroot`, pruned to 3 entries and overrode `EXPECTED_MUTATIONS` in the copy | `OK — 1 file(s), 3 mutation(s), 3 killed, 3 attributed to the case each names, 0 survivor(s)` for *the OS fallback asks the LIGHT query*, *a saved text style is never read* and *the switcher's pressed state is announced inverted* |
| Ambient passes in the new cases | ran 9 of my own semantic mutants (not in the manifest) against the self-test | unpin-no-resync, inverted unpin, schemer-never-moved and sync-while-pinned were all **killed**. Two real survivors, in F4 |

CI guards: I ran every `python3 scripts/check-*` step in `ci.yml` (62 commands), with `--base origin/master` and an empty PR body. **61 passed and 1 failed** (F1). One was NOT RUN: `check-test-counts.py --results jest-results.json` needs a jest run.

## Findings

### F1 — Medium — `check-review-recorded.py` is RED on this tree, and neither this round nor the r5 `REVIEW GAP: codex` line can clear it
- **Where:** `.github/workflows/ci.yml:792` runs `scripts/check-review-recorded.py`. The rule is `tail_verdict`, `scripts/check-review-recorded.py:915`. The gap escape at `:936` applies only when `tails` is empty, meaning no Codex verdict at all.
- **What happens (quoted):**
  ```
  FAILED — 3 round(s) ran and guarded code was committed after every one of them.
    The closest (comprehensibility-chrome-cases-r1-codex.verdict.json) never saw:
      scripts/check-plan-code.py, scripts/mutations/page_chrome.json, scripts/page_chrome.py
    Run one more round against the current tree, or put `NO-REVIEW: <reason>` in the pull-request body.
  ```
  The newest Codex verdict (r4) has `head: 608af169`. The r4 fold `0ab98e9b` then changed `page_chrome.py`, `page_chrome.json` and `check-plan-code.py`. This round is the Claude half and leaves no verdict. The r5 coordinator's `REVIEW GAP: codex — alternation …` reaches only the empty-tails branch, so the gate stays at rc=1.
- **Why it matters beyond this PR:** backlog #339's 2026-10-24 note says of the two readings of *alternate* that "the gate accepts both". That is true of `check-review-rounds`, which is green here. It is **false of `check-review-recorded`**. Under the one-half-per-round reading, any branch whose last fold follows its last Codex round is structurally red. #339 does not record this second gate.
- **Fix:** run a Codex round over the final tree, which clears it with no text change. Alternatively, use `NO-REVIEW: <reason>` in the PR body if the owner accepts that. Also amend #339 to name `check-review-recorded`'s final-tree rule as a third party to the conflict.
- **Caused by the r4 fold?** Yes, in sequence: guarded code was committed after the last Codex round, under the one-half alternation reading. It is not a code defect.
- **Bet:** this is a Medium outside stub-page coverage, so it is the DEFER bet's named failure observation. Scored strictly, the bet **loses**. Leniently, the miss is in the process gate, not in what ships.

### F2 — Low — the dashboard entry's mutation counts are stale by the r4 fold
- **Where:** `docs/dashboard-entries.md:17455`. It reads `mutations page_chrome 89 -> 102, total 2003 -> 2016; scoped run 102 killed, 102 attributed, 0 survivors.`
- **What happens:** the tree holds **103** and **2017** (manifest count, `EXPECTED_MUTATIONS`, and the `check-plan-code.py` self-test literal `2017`). Commit `0ab98e9b`'s own message says `102 -> 103, total 2016 -> 2017; scoped run 103/103`, but the entry was not updated. No guard reads this prose: `check-dashboard-entry` passed.
- **Fix:** change the entry to 103 / 2017 / 103.
- **Caused by the r4 fold?** Yes.

### F3 — Low — the recomposed page is not what the composer now produces
- **Where:** `docs/explainers/2026-10-06-brief-dev-process-speed.html:184`, which reads `toggle (#283). */`.
- **What happens:** I recomposed the page in scratch with `brief-compose.py --content <fragment> --source <page> --out …` and `HOME` redirected. Ignoring the `<time>` stamp, the only difference from the committed page is this line. The current `SHIM` says `toggle (PR #283). */`, so the page was composed before the comment's final wording within `a38bb55b`. There is no behavioural effect, since it is a CSS comment. It does mean the committed page is not reproducible from the committed producer.
- **Fix:** recompose the page.
- **Caused by the r4 fold?** No. It came from `a38bb55b`.

### F4 — Low, INSIDE the stub's stated bound → FILE, do not fold (under the bet)
Two observable effects that the stub records, or could record, have no assertion:
- **(a) The default text-style option is never pressed.** The case presses `sbs[0]` only (`scripts/page_chrome.py:2179`). The `sset(TD)` branch (`:1007`: `removeAttribute(TA)` plus `localStorage.removeItem(TK)`) is not executed after a press. Mutant: append `localStorage.setItem(TK,'1');` inside that branch. Result: **`232/232 passed`**. A reader who picks "default" gets style 1 back on reload. The bound says "one press of each control", and the switcher is one control, so this does not contradict the stated bound. It is still a gap within what the stub executes.
- **(b) The slot reserve and `--chrome-h` writes are executed but not asserted.** Mutant: after `slot.style.minHeight=h+'px';`, append `slot.style.minHeight='0px';`. Result: **`232/232 passed`**. The same holds for overwriting `--chrome-h` with `0px`. The substring cases at `:1878`/`:1958` keep the original text present, so they cannot see an overwrite. The stub already records `slot.style` and `root.style`, so an assertion would be cheap.
- **Fix:** file on #305's successor. Press `data-s="3"` after `"1"` and assert attribute removed and key removed. Assert `slot.style.minHeight === '40px'` (the stub height) and `root.style['--chrome-h'] === '40px'` after load.
- **Caused by the r4 fold?** No. Both are present since `aba58da6`.
- Nothing outside the bound is claimed as covered. #305's row explicitly excludes the no-IO fallback and refresh, and #304's row explicitly excludes reachability. Both checked.

### F5 — Info — stray blank line left by the revert
- **Where:** `scripts/page_chrome.py:271`, three blank lines between `missing_palettes` and `has_control`.
- **What happens:** the function body is byte-identical to master, so the architecture review's "byte-identical" claim holds for the function. The file still carries a one-line residue of the reverted route.
- **Fix:** delete the line.
- **Caused by the r4 fold?** No. It came from the split revert `608af169`.

VERDICT: NOT CONVERGED

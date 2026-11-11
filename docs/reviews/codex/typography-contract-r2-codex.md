<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — `scripts/brief-compose.py:126`: the new default overrides deliberate fragment colours and can regress contrast.**

   The shim’s `:root:not([data-theme="light"])` has specificity `(0,2,0)`. It ties the fragment’s customary OS-dark selector and wins because the shim is appended later.

   Reproduction: copy `2026-10-06-brief-dev-process-speed.fragment.html` outside the worktree; change its dark `--bg` and `--card` to `#666666`, and dark `--em` to `#ffffff`. Both versions compose successfully.

   Chromium, **OS dark, nothing pressed**, measuring bold text “freeze point”:

   | Composer | Computed emphasis | Background | Contrast |
   |---|---|---|---|
   | Before the new rule | `#ffffff` | `#666666` | **5.74:1** |
   | HEAD | `#9db8e8` | `#666666` | **2.86:1** |

   This also falsifies `.agents/skills/shared/explainer-delivery.md:124–125`: **“A fragment that declares its own value overrides those … a page’s actual colours are the fragment’s, then the shim’s.”**

   **Fix:** make fallback selectors less specific than fragment declarations, including the explicit-theme defaults if they are to satisfy that contract. Add a computed-colour regression case using a fragment with its own distinct dark emphasis.

   **Caused by r1 fold:** **yes**. Removing only the added rule restores 5.74:1 in the affected state.

   Reproduction artifacts: [fragment](/tmp/typo-r2-review/custom.fragment.html), [Chromium measurements](/tmp/typo-r2-review/results.jsonl).

Other checks:

- All four existing role-using pages passed all **24 theme combinations**; minimum contrast across their visible `b`/`strong` elements was **7.57:1**.
- The three recomposed pages contain only the shim addition and generation-stamp changes.
- All **22 fragments** composed before and after; normalized outputs differed only in the shim and stamp.
- No additional actionable defect found in §2. Backlog #226 correctly remains open; the dashboard’s readability claim concerns the three repaired pages and holds for them.

The last-row bet is **refuted**: an accepted composed page acquires sub-4.5:1 emphasis, and the fragment-precedence sentence is false.

No repository files changed or git writes performed.

VERDICT: NOT CONVERGED

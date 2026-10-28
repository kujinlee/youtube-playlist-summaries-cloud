<!-- codex-review: model=gpt-6.1-sol -->

1. **P2 — Lexically matching aliases still select the wrong root.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:119`.

   The hook computes `real`, but discards it whenever the original path already matches `docs/memory/MEMORY.md`.

   **Reproduction, executed in a `mktemp` copy:** Create checkout B with a 27,000-character index. Create `alias/docs/memory -> B/docs/memory`, then invoke the registered launcher with `alias/docs/memory/MEMORY.md`. Result: rc 0, **NOT MEASURED**, despite B having its checker. With checkout A’s `docs/memory/MEMORY.md` symlinked to B’s index, the hook instead runs **A’s checker**. Substituting a healthy checker in A produced silence despite B’s overflow.

   **Fix:** Use the successfully resolved path for root selection regardless of whether the original path matches. Add integration cases for aliases whose lexical names also match the index suffix.

   The new comment at lines 113–117 and header at lines 12–19 consequently overclaim resolution and selection of the repository containing the edited file.

2. **P2 — A checkout name ending in a newline silently redirects the check to its sibling.**  
   **Location:** `.claude/hooks/check-memory-index-budget.sh:51`.

   **Reproduction, executed in temporary copies:** Create sibling checkouts `nl` and `nl<newline>`. Give `nl` a healthy index and `nl<newline>` a 26,000-character index. Invoke the registered launcher with the latter’s absolute index path. Result: **rc 0, no output**. `dir=$(dirname "$dir")` strips the checkout name’s trailing newline while walking upward and selects the healthy sibling.

   **Fix:** Walk parent paths with shell parameter expansion that preserves newlines, and preserve the initial directory extraction too. Add this sibling-checkout integration case.

   This also falsifies the header’s containing-file guarantee and CI’s unconditional “until the next tool write to the index” statement at `.github/workflows/ci.yml:535`.

Both round 1 reproductions no longer demonstrate their reported defects:

- **P1:** The normal harness alias now emits `OVER BUDGET`, rc 0.
- **P2:** The retargeted mutation fails its newly named divergent-registration case. **All 34 manifest mutations fail every declared named expectation.** Controls pass **45/45**; hook self-tests pass **14/14**.

Other executed attacks returned rc 0 and completed within **360 ms**: symlink loop, dangling symlink, spaces and quotes, an embedded-newline alias, relative paths, a symlink chain, and an ordinary alias into another checkout. The ordinary cross-checkout alias correctly measured B’s 27,000-character index. An outside-repository target with the canonical suffix emitted `NOT MEASURED`; an outside target without that suffix stayed silent.

These timings establish prompt completion for the tested inputs, not a general timeout guarantee: line 129 still waits synchronously for the checker.

VERDICT: NOT CONVERGED

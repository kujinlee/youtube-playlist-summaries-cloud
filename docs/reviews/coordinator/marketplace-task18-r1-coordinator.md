# Round 1 — `marketplace-task18` — coordinator — the quote check misses punctuation changes (both halves); a paraphrase dropped rule figures; C5 stays unanswered

Both halves reviewed 0f8fb5f4 (plan Task 18, PR #617), concurrently:

- `docs/reviews/codex/marketplace-task18-r1-codex.md`: X1, X2 and X3, all MAJOR; NOT CONVERGED.
- `docs/reviews/claude/marketplace-task18-r1-claude.md`: C1 MAJOR, C2–C5 MINOR; NOT CONVERGED.

Round 1, so no finding is fix-induced. Every disposition below was verified by the coordinator against the code or the plan
before the fold.

## Dispositions

- **X1 = C1 (MAJOR): the quote check misses a quote with altered punctuation. ACCEPT.**
  - **Cause:** `norm()` in `scripts/build-shipped-corpus.py` removes only `*_`, backtick and backslash; every other
    punctuation mark survives into the six-word windows.
  - **Evidence:**
    - Codex: `#297, is, not, ready, to, merge` passed.
    - Claude: 9 of the 51 real D quotes passed with their punctuation stripped.
  - **Fix:** compare words, not characters — map every non-alphanumeric run to one space in both the quote and the
    output. Add a self-test case built from both reviewers' inputs, and a mutation for the clause. Re-run the 51-quote
    plant, expecting 0 passes.
- **X2 (MAJOR): C5 should move off `unanswered` because the build passes. REJECT.**
  - Plan Task 18 says C5 moves off `unanswered` *"only when"* the build and both checks pass. That is a necessary
    condition, not a sufficient one.
  - The same task also says the corpus row *"carries `C5: unanswered — blocked on the content review` until H1 lands"*,
    and *"Condition (b) is Human step H1 and is never decided here"*.
  - The spec expects the row to end this milestone unanswered.
  - **What is fixed instead:** the row's notes misquote the plan as "C5 moves off unanswered when…" and frame it as a
    deviation. The notes are reworded to quote "only when", and to say there is no conflict.
- **X3 = C3: a paraphrase dropped rule figures. ACCEPT, at MAJOR (Codex's severity).**
  - The owner's rule (`decision-5-suspect-files.md` → *Answered*; plan Task 18) removes names, dates, numbers and
    project details **from the quotes**, and keeps every rule.
  - `a-budget-stop-is-soft-with-a-reserve.md` blurred rule figures that sit outside any quote: the 14%/day trend, the
    A=12/B=20 band, the ≥8% per later day invariant, the 2–3 point reserve, and the cron line with its 7-day expiry.
  - **Class fix:** every one of the six D paraphrases is re-checked against its source, and each rule figure outside a
    quote is restored. A pointer to a script the recall package does not ship is replaced by the figures inline.
- **C2 (MINOR): CANNOT RUN only fires when every D file has zero quotes. ACCEPT** — cheap, and it closes a silent pass.
  A single D file with zero quotes becomes CANNOT RUN. Add a case and a mutation.
- **C4 (MINOR): the experiment doc's *Outcome* credits the primary run with hook behaviour. ACCEPT.**
  - In the primary run the hook never reached the matcher: `dirname` was missing, so `REPO_ROOT=/` and the hook exited
    at line 61.
  - Only the supplementary run, with `dirname` available, measured the hook. That run is what supports
    `recall.a = false`.
  - The gap is the probe's allow-list, not a stranger's host. Reword both points.
  - `a` stays `false`: both halves agree the supplementary run measured a silent no-op.
- **C5 (MINOR): check 2 matches excluded files by name only. ACCEPT** — cheap. An output file whose content equals an
  excluded source file's also fails. Add a case and a mutation.

## Raised by the builder, not by either reviewer

- **The recall package in `docs/marketplace/shipping-sets.json` installs the RAW `docs/memory/`, not the built corpus.**
  Out of Task 18's scope (Task 18 builds the corpus; the package declaration is slice C's). Nothing publishes before
  Task 21, which is the owner's stop. FILED as a backlog row in this fold.
- **Two kept files contain the repository's GitHub slug** (`stage-2-batch-autonomy-plan.md`, `gh-two-remotes-footgun.md`).
  Decision 5 did not cover them. This is a question for the owner, raised with H1, and not changed here.

## Not verified by either half

The Claude half saw `check-plan-code` and `check-paid-caller-arrival` self-tests red inside `check-selftest-counts` in a
clone without `node_modules`. CI ran `check-selftest-counts` on 0f8fb5f4, and the only failing step was
`check-review-recorded`, which failed because this round was not yet committed.

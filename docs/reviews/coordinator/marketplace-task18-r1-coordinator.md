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
  - **Fixed in e4e21b37** (mutation anchor 8f45cde8, pin 44dbbe37): `norm` maps every `[\W_]+` run to one space on both sides; two cases (the punctuated span and a stripped/changed real quote; a `norm` unit case); mutation *punctuation is not normalised away*. Plant of all 51 D quotes: 0 pass stripped, 0 added, 0 changed (the old code: 9, 51, 3). Real build `--check` PASS over 708 fragments.
- **X2 (MAJOR): C5 should move off `unanswered` because the build passes. REJECT.**
  - Plan Task 18 says C5 moves off `unanswered` *"only when"* the build and both checks pass. That is a necessary
    condition, not a sufficient one.
  - The same task also says the corpus row *"carries `C5: unanswered — blocked on the content review` until H1 lands"*,
    and *"Condition (b) is Human step H1 and is never decided here"*.
  - The spec expects the row to end this milestone unanswered.
  - **What is fixed instead:** the row's notes misquote the plan as "C5 moves off unanswered when…" and frame it as a
    deviation. The notes are reworded to quote "only when", and to say there is no conflict.
  - **Fixed in e4e21b37:** the memory-corpus notes quote *"only when the build and both checks pass"*, call it a necessary condition, and say C5 stays unanswered until H1; the deviation framing is gone.
- **X3 = C3: a paraphrase dropped rule figures. ACCEPT, at MAJOR (Codex's severity).**
  - The owner's rule (`decision-5-suspect-files.md` → *Answered*; plan Task 18) removes names, dates, numbers and
    project details **from the quotes**, and keeps every rule.
  - `a-budget-stop-is-soft-with-a-reserve.md` blurred rule figures that sit outside any quote: the 14%/day trend, the
    A=12/B=20 band, the ≥8% per later day invariant, the 2–3 point reserve, and the cron line with its 7-day expiry.
  - **Class fix:** every one of the six D paraphrases is re-checked against its source, and each rule figure outside a
    quote is restored. A pointer to a script the recall package does not ship is replaced by the figures inline.
  - **Fixed in e4e21b37:** all six paraphrases re-read against their sources. Figures restored in `a-budget-stop…` (14.3%/day trend, A=12/B=20, ≥ 8% invariant and its formula, +8 note margin, ~2–3 reserve, ~2 burned, cron `7 0 * * *`, prompt prefix, 7-day expiry, the history's formulas and measurements), `route-agents…` (model names, ratios, cache rates, token figures) and `the-user-does-not-follow…` (call/turn counts, the 90–120 s heartbeat, the >~2 min threshold); the usage-pace pointer replaced by the figures inline. The other three carry no rule figure outside a quote. Real build `--check` PASS.
- **C2 (MINOR): CANNOT RUN only fires when every D file has zero quotes. ACCEPT** — cheap, and it closes a silent pass.
  A single D file with zero quotes becomes CANNOT RUN. Add a case and a mutation.
  - **Fixed in e4e21b37** (pin 44dbbe37): `check()` returns rc 2 naming each D source with no quote; case *ONE source D file with no quote is CANNOT RUN*; the existing no-quotes mutation retargeted to `if unread:`.
- **C4 (MINOR): the experiment doc's *Outcome* credits the primary run with hook behaviour. ACCEPT.**
  - In the primary run the hook never reached the matcher: `dirname` was missing, so `REPO_ROOT=/` and the hook exited
    at line 61.
  - Only the supplementary run, with `dirname` available, measured the hook. That run is what supports
    `recall.a = false`.
  - The gap is the probe's allow-list, not a stranger's host. Reword both points.
  - `a` stays `false`: both halves agree the supplementary run measured a silent no-op.
  - **Fixed in e4e21b37:** *Outcome* rests on the supplementary run `mkt18.rc0f4sjc`; the primary hook rows are marked NOT MEASURED (no `dirname`, `REPO_ROOT=/`, exit at line 61); the supplementary run's 7 records checked for `/memory/` paths (none); `hook-surface-recall` and memory-corpus notes say allow-list gap, not host-tool gap.
- **C5 (MINOR): check 2 matches excluded files by name only. ACCEPT** — cheap. An output file whose content equals an
  excluded source file's also fails. Add a case and a mutation.
  - **Fixed in e4e21b37** (pin 44dbbe37): an output file whose sha256 equals an excluded source's fails check 2 (`EXCLUDED CONTENT PRESENT`); a positive and a negative case; mutation *an excluded file's content under another name is not reported*.

## Raised by the builder, not by either reviewer

- **The recall package in `docs/marketplace/shipping-sets.json` installs the RAW `docs/memory/`, not the built corpus.**
  Out of Task 18's scope (Task 18 builds the corpus; the package declaration is slice C's). Nothing publishes before
  Task 21, which is the owner's stop. FILED as a backlog row in this fold.
  - **Filed in e4e21b37** as backlog #697.
- **Two kept files contain the repository's GitHub slug** (`stage-2-batch-autonomy-plan.md`, `gh-two-remotes-footgun.md`).
  Decision 5 did not cover them. This is a question for the owner, raised with H1, and not changed here.

## Not verified by either half

The Claude half saw `check-plan-code` and `check-paid-caller-arrival` self-tests red inside `check-selftest-counts` in a
clone without `node_modules`. CI ran `check-selftest-counts` on 0f8fb5f4, and the only failing step was
`check-review-recorded`, which failed because this round was not yet committed.

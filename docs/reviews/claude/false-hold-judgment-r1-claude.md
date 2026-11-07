Reviewed head: 54667f2cc6e26996f3d0ce17aad719a4fe9d55ab

Adversarial Claude half, round 1, subject `false-hold-judgment` (backlog #508). I tried to make the gate clear a real loosening through each input in the brief. These all **held**:

- a verdict recorded on a different tree, and an edit committed after the round, including a docs-only edit (`tree_matches` checks every changed path plus the overlay);
- a verdict whose gate did not run, or one that was refused;
- a `dirty: null` record;
- a verdict that is not JSON, or whose head cannot be read. `PathsDisagree` is a `ValueError`, so the per-record `except` skips only that record and does not affect the others;
- an exception in `main()`. `answered` is bound to the empty set before the `try`, so an error leaves every line held;
- an answer that is indented, quoted with `>`, listed with `-`, given a suffix, or left as a `<id>` placeholder;
- two identical removed lines. The occurrence number is part of the id;
- a rising count that also changes indentation or other text, or a count that falls.

I found **no BLOCKER**: every defect below either fails closed or needs a dissent written in the wrong form. There are three real problems. (1) **The parser is equally strict for "yes" and "no".** A reviewer who flags a loosening in a near-canonical form, for example `Finding:` or a bolded line, has their dissent silently dropped. The other half's `not a loosening` then clears the line. That is the one fail-open path I found. (2) **The exempt set leaves out the records this repo commits after its final round.** These are the coordinator document and the decision log. As the process is actually run, the answers are therefore voided on every PR, and the gate HOLDs every flagged PR as before. The feature fails closed, so it is safe, but it does not do what it is for. (3) **`--flagged-block` reads only committed history.** The documented step-5 way to finish, with the last fixes still uncommitted, is never asked about the lines those fixes flag. Each mutation I measured is anchored exactly once and killed through the case it names (24 of 24; table below). On the three lines this PR itself flags, my answer is: two are a real loosening that the owner sanctioned, so this PR should HOLD for the owner as designed; the third is not a loosening.

## Findings

### M1 (MAJOR): a dissent worded slightly wrong is discarded, and the other half's assent then clears the line

`codex-review.loosening_answers` parses assent and dissent with the same strict regex. A line that matches neither form is dropped, not counted against. `check-merge-ready.answered_flags` then sees only the assent, so `clear - other` contains the id. Its own docstring says "Any other text counts as a finding". That is false at the point where it matters, because other text never reaches it.

How I tested it: one record answers `{X: "not a loosening"}` and a second record carries the dissent below, run through the parser. Every one of these was parsed as `{}`, so the line was **cleared** (output from `scratchpad/probe508.py`):

    **LOOSENING-CHECK 0123456789ab: finding: exit 1 now 0**      (markdown bold, which reviewers use)
    LOOSENING-CHECK 0123456789ab: Finding: exit 1 now 0          (capital F)
    LOOSENING-CHECK 0123456789ab: a loosening: exit 1 now 0
    LOOSENING-CHECK 0123456789ab:  finding: x                    (two spaces)
    - LOOSENING-CHECK 0123456789ab: finding: x
    LOOSENING-CHECK 0123456789ab : finding: x
    LOOSENING-CHECK 0123456789AB: finding: x                     (upper-case id)

Round 1 runs both halves, so this is the normal topology: one half writes the canonical assent, and the other writes its dissent in bold. The owner's rule is "passes only when every flagged line is answered `not a loosening`... and no verdict answers it with a finding", and a dissent is plainly a finding.

Suggested fix: keep assent strict, but read dissent loosely. Any line that mentions `LOOSENING-CHECK` followed by a known id, matched case-insensitively and anywhere in the line, and that is not exactly the canonical assent, should count as `finding`. This creates no new risk for an echoed prompt: the block's rows read "- id `x` in ..." and never contain the `LOOSENING-CHECK <hex id>` form.

How far this reaches: I searched both recorders. `record-review-verdict.py` calls the same parser, so the Claude half has the same gap.

### M2 (MAJOR): as rounds are actually run here, the final round's answers never reach the merge, so every flagged PR HOLDs

`REVIEW_RECORDS` covers only `docs/reviews/{verdicts,claude,codex}/`. The repo also commits other round records after the final round. #515 through #519 each committed the following after the review that adjudicated them:

- `docs/reviews/coordinator/<subject>-r<final>-coordinator.md`, for example `hook-master-guard-r10-coordinator.md` beside `hook-master-guard-r10-codex.verdict.json`;
- `docs/reviews/decision-scheme/decision-log.jsonl`;
- usually `docs/backlog.md`, `docs/dashboard-entries.md` and `docs/goal-threads.md`.

The coordinator document for round N cannot exist before round N's review does. Measured with `tree_matches(R, {}, {**R, p: new}, [p])`: the result is `False` for the coordinator path, the decision-log path, `docs/dashboard-entries.md` and `docs/backlog.md`, and `True` only for a verdict path.

There is a second gap. Step 5 of `docs/review-method.md` names "holding the last round's fixes uncommitted so the reviewer sees the final state" as the documented way to finish. `--flagged-block`, however, builds its list from `gather`, which uses `status_cmd`, which reads `origin/master...HEAD`, so it sees committed history only. A line that the uncommitted final fixes newly flag is never put to that round. It shows up after the commit, unanswered.

Both gaps fail closed, which is why this is MAJOR and not a BLOCKER. The cost is that the feature does nothing in practice: the author or owner judges the HOLD exactly as on master. A PR clears only if every post-round record is committed before the final round, and the review method does not say to do that.

Suggested fix: add `docs/reviews/coordinator/` and `docs/reviews/decision-scheme/` to `REVIEW_RECORDS`, because they are the round's own records by the code's own rationale. Then do one of two things: (a) state in the review method that dashboard, backlog and goal-thread edits are committed before the final round, or (b) have `--flagged-block` include the working-tree overlay. Add a real-git case that commits a coordinator document after the round, so this composition is tested.

### m3 (MINOR): a finding on a line that has not changed is dropped once the tree moves on

The rule that a finding beats an assent applies only between verdicts on the tree being merged. Here is an input that clears:

1. Round 1, the Claude half, on commit c1: `{X: finding}`.
2. The author commits only a docs fix, giving c2. The flagged line `X` is identical.
3. Round 2, under alternation, has ONE half. Codex, on c2: `{X: not a loosening}`.

The result is that `X` is cleared. The round-1 finding is now just a "reviewed a different tree" note, and nothing says that a finding was overruled. This follows the owner's literal rule, which only requires the exact tree. Still, an unresolved finding on an unchanged line should at least be visible.

Suggested fix: when an older-tree verdict answered an id `finding` and that id is still flagged, print an `⚠ answers:` note naming it.

### m4 (MINOR): an example in a fenced code block is parsed as an answer

Parsing `Example:\n` + "```" + `\nLOOSENING-CHECK 0123456789ab: not a loosening\n` + "```" returns `{id: "not a loosening"}`. The section comment says "any other wording, indentation, quote or list marker is no answer", and fences are missing from that list. For this to clear a line, the reviewer has to quote the canonical assent for a live id, so the risk is low.

Suggested fix: skip the lines inside fences.

### m5 (MINOR): the block shows a line's text but not where it is

`flagged_block` lists `` `return 1` `` with no hunk position. When a file removes the same text twice, the reviewer cannot tell which id is which occurrence. The occurrence number is also counted over the committed diff (see M2), so it can point at a different site once the final fixes are committed. This currently fails closed, because the larger final flag set always leaves an id unanswered. But the reviewer is being asked to judge a line it cannot locate.

Suggested fix: include the base line number, or a few lines of hunk context, in each row.

### m6 (MINOR): a Claude half's overlay is captured when the verdict is recorded, not when the review ran, and it is now what clears a merge

`record-review-verdict.py` records `reviewed_state(root)` at the moment the coordinator runs it. Here is an input that clears:

1. The review on H answers the removed `return 1` "not a loosening", having seen its replacement `return 2`.
2. A fold edit, still uncommitted, changes `return 2` to `return 0`.
3. The coordinator then runs `record-review-verdict.py --head H`. The overlay records the edited blob as "seen".
4. The edit is committed. The tree matches, and the id is unchanged, because it hashes only the REMOVED text. The line clears.

The tool's refusal text tells the coordinator to "Record ... before any fold edit". The code states this trust boundary. What is new is that an ordering slip now clears a merge HOLD; before, it only made the round look recorded.

Suggested fix: either refuse to record when the overlay includes a path outside `REVIEW_RECORDS` that the half's brief did not mention, or keep the bound and state it in `review-method.md` beside the step-5 line.

### m7 (MINOR, bound only): the rising-count exemption assumes the count is a comment

`rising_count` checks that ONLY the number changed, which is correct for the documentation lines it exists for. It would also exempt a line where that number is code. The input that clears is:

    LIMIT = int('--self-test # 3 cases'.split()[3])  ->  LIMIT = int('--self-test # 99 cases'.split()[3])

I found no such line in the repo, so this is contrived. It is worth one line in the docstring so the bound is stated.

## Self-tests

    python3 scripts/check-merge-ready.py --self-test     -> 292/292 self-test cases passed
    python3 scripts/codex-review.py --self-test          -> 221/221 passed
    python3 scripts/record-review-verdict.py --self-test -> 100/100 passed

## Mutations

I ran every manifest entry that is new or changed against `origin/master`. Each was applied to a staged COPY: `check-plan-code.stage_tree`, then `run_mutations`. The driver is `scratchpad/mut508.py`, run once per manifest. The control was green each time.

| Manifest | New/changed | Anchor matches | Killed via the named case |
|---|---|---|---|
| check-merge-ready.json | 16 | each exactly 1 | 16/16, every one attributed |
| codex-review.json | 5 | each exactly 1 | 5/5 attributed |
| record-review-verdict.json | 3 (one re-anchored) | each exactly 1 | 3/3 attributed |

No entry tests M1's case. "a FINDING beats" is pinned only for the canonical form.

## The gate's flagged lines

`6bd002a6d73a` and `e8b3c3bfbf22` are the two halves of one statement in `hold_reasons`. On master, ANY failure-path removal HOLDs. On this branch, it does not HOLD in two cases: (a) a line whose only change is a rising `--self-test  # N cases` count, and (b) a line answered `not a loosening` by a verdict on the merging tree. That is a deliberate loosening, sanctioned by the owner (card A), not a defect. By the block's own test, though, the branch no longer refuses everything master refused on that path, so the honest answer is a finding, and this PR should HOLD for the owner. `f13e64d753fa` only extends `verdict_record`'s signature with a parameter that defaults to None, which adds a field and changes no refusal.

LOOSENING-CHECK 6bd002a6d73a: finding: the "removes or rewrites N line(s) on a failure path" HOLD no longer fires for a line whose only change is a rising self-test count, nor for a line answered `not a loosening` by a verdict on the merging tree (owner-sanctioned, card A; and per M1 a malformed dissent is dropped, so one half's assent can clear it)
LOOSENING-CHECK e8b3c3bfbf22: finding: same statement as 6bd002a6d73a; the message now names only the unanswered lines, and the HOLD is skipped entirely when every flagged line in a path is answered `not a loosening` or is a rising-count line
LOOSENING-CHECK f13e64d753fa: not a loosening

VERDICT: CONVERGED

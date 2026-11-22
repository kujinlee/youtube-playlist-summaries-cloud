# Round 3, Claude half: `marketplace-task18` (PR #617, plan Task 18), the round-2 fold's link reduction deletes visible words

Reviewed at afcb6e85, in the worktree `.claude/worktrees/mkt-task18`. The mandate was adversarial: try to show the
branch is wrong. Part 1 covers the round-2 fold (`git diff cd9d93cd..afcb6e85`). Part 2 covers the whole task
(`git diff origin/master...HEAD`) against plan Task 18.

## What was run

| Check | Result |
|---|---|
| `python3 scripts/build-shipped-corpus.py --self-test` | 28/28 pass |
| `--out <scratchpad>/task18/r3/build1` (a fresh, empty dir) | 180 files, 708 fragments, 16 excluded names, **PASS** rc 0. The canonical hash false-matches no KEPT file |
| `check-plan-code.py --mutate . --only scripts/build-shipped-corpus.py` in the fold-r2 clone at afcb6e85 | 25 mutations, 25 killed, **25 attributed to the case each one names**, 0 survivors. The clone was clean afterwards |
| Does any real group-D quote change under the new link and URL reduction? (I compared `norm` with and without the two new `re.sub` lines over all 51 quotes) | None. One quote has a `[mm-dd hh:mm]` but no destination, so it normalises the same either way |
| Stale-paraphrase check | Not affected. `build` still compares the raw `_sha` against `sources.json` (line 138). `_canon_sha` is used only by check 2 (lines 176 and 183) |
| `rests_on` ids of the six effort-1 rows, compared with `scan-2026-11-17.json` | Every cited id exists. Each uncited finding id for these components is named as "not a ground" in its row's notes |
| Probe record `task18/probe-results-dirname.json` (the supplementary run) | Allow-list is `python3, git, bash, claude, dirname`. Seven records, each with 44–47 `opened` paths, and none contains `memory`. rc values 0/2/2/2/0/3/6, as the write-up's table gives them |
| Line citations in `experiment-tier-a.md` (`surface-recall.sh:41`, `:61`; `recall-llm.py:120–122`, `:417`) | Correct at HEAD. Those files have not changed since 8efb3d0a |
| Shipped-corpus paraphrases (diffed against `docs/memory/` sources, then grepped for owner name, paths, project names, `#N`, dates) | No owner quote, name, date or PR number survives. The figures that remain are rule figures outside a quote, as the edition banner says |
| Backlog #697, `shipping-sets.json` | Matches the tree: `recall.installed_files` holds 196 `docs/memory/` files. `expected_count` is now 107 for the new manifest |

## Findings

1. **MAJOR — the round-2 link and URL reduction deletes VISIBLE text, so a quote the round-1 code caught now passes**
   (`fix_induced: true`). Location: `scripts/build-shipped-corpus.py:94-95` (`norm`).
   - **The cause.** The link pattern accepts `\([^)\n]*\)` and `\[[^\]\n]*\]` as destinations, including text that
     contains spaces. In CommonMark, `[a](b c d)` is not a link, because a destination cannot contain spaces. Likewise
     `[a][b c d]`, with no reference definition, is not a link. Both render literally, so the words in the second part
     are visible to the reader, and `norm` throws them away.
   - **The URL pattern is too greedy.** `https?://\S+` also swallows a word glued to the URL, for example the text
     after `<https://x>`.
   - **Reproduction.** Make a fresh build, copy it, and append one line to the kept file
     `a-convention-catches-what-you-read.md`. Then run `--check` on the copy. Each line below is a real group-D quote
     and gives **PASS** at afcb6e85, but **FAIL (1 hit)** under the cd9d93cd script (the control: `check()` loaded from
     `git show cd9d93cd:scripts/build-shipped-corpus.py`, on the same copy):
     - `Context [note](Merging #297 stays yours) here.`
     - `Context [aside][you are not emitting banners] here.`
     - `see <https://x>Merging #297 stays yours`
   - **How much is lost.** The parenthesised and second-bracket forms delete every window of a quote of any length. The
     glued-URL form loses one word, so only a short fragment of 3–6 words is missed.
   - **The docstring was not updated.** Its *What this cannot see* section (lines 32–36) names "a link whose text is
     not the quoted word". It does not name visible text inside a non-link bracket or parenthesis, or a word glued to
     a URL.
   - **Proposed fix (a hypothesis; run it on the plant corpus first).** Search each output body under BOTH
     normalisations, the reduced form and the pre-fold form, and count a hit if either contains the fragment. No real
     quote changes under the reduction, so the quote side can stay as it is. The real build passes both forms: the
     round-1 code passed it, and so does this one. Add the three lines above as a case, and add a mutation that drops
     the unreduced half.

## Not findings (checked and refuted)

- **Can `_canon_sha` false-match a kept file?** No. The fresh build passes, and no excluded source is empty
  (`find docs/memory -size 0` lists nothing), so a blank output file cannot collide with one.
- **Is the round-2 "excluded side raw" mutation killed only by accident?** No. With the excluded side hashing raw
  bytes, `excluded b2.md\n` and the canonical `excluded b2.md` differ, so the case it names goes red. The harness
  attributes it to that case.
- **Is `recall.a = false` recorded on a CANNOT RUN probe?** No. It rests on the supplementary run, whose hook reached
  the matcher (`opened` 45 and 47 in the two hook records). The `dirname` addition to the allow-list is stated in the
  write-up as a deviation. Every recall row is `"later"`, none is `"1-if-feasible"`, and the corpus row keeps
  `C5: unanswered` until Human step H1. That meets the plan's FAILS-IF clauses.

VERDICT: NOT CONVERGED

<!-- codex-review: model=gpt-6.1-terra -->

**The branch satisfies backlog 697’s literal Fails-if at this HEAD**, but the round-1 content guard still has two fail-open paths. The review is **not converged**.

**MAJOR — closure-guard** · fix_induced: true · [check-shipping-sets.py:1066](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl697/scripts/check-shipping-sets.py:1066)

- **Input:** A group-D source with an added line, shipped as `notes/test.md` outside the two corpus directories.
- **Observed:** The content check returned no gaps. The added line defeats the whole-file canonical hash, and the directory filter excludes the file from quote checking. The same rule is applied to each package, so the escape is not confined to recall.
- **Expected:** A shipped file containing an unparaphrased group-D quote is reported regardless of its repository path.
- **Fix:** Run the content check over every shipped file, or enforce an equivalent content check for files outside the corpus directories.

**MAJOR — closure-guard** · fix_induced: true · [check-shipping-sets.py:1097](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/bl697/scripts/check-shipping-sets.py:1097)

- **Input:** A builder subprocess that exits 0, writes an error to stderr and ends stdout with a fabricated `PASS:` line; separately, one that writes garbage before that line.
- **Observed:** Both returned zero gaps. The guard accepts any final line beginning `PASS:` and ignores non-traceback stderr and preceding stdout.
- **Expected:** A builder failure or unreadable output is CANNOT RUN, rc 2.
- **Fix:** Validate the complete success output and reject unexpected stderr or stdout. Add cases for both malformed-success shapes.

The duplicate-basename input produced a gap, including when the quote-bearing file shared its basename with another file. A non-`.md` corpus file also produced a gap. A simulated timeout raised CANNOT RUN. The scratch directory was outside the repository and was removed after use.

For the current recall declaration, an independent comparison found zero excluded A–C basenames and zero byte-identical D sources. Backlog #707’s area is claimed in `features.md`; its Fails-if names observable publication and decision outcomes. The inventory row agrees with the component declaration’s 179 files and records the index, portability and content-review qualifications.

Verification in full clones outside the repository: shipping-set self-test **160/160**, builder self-test **31/31**, and three new mutations each failed their named case. The manifest contains **209** mutations and the recorded price is **13 seconds**. The non-self-test CI checks run locally passed except `check-inventory`’s documented owner-stop rc 3; the built-page check and self-test-count check timed out, and test-count verification lacked Jest results. PR-body-dependent checks and the CI mutation shard were not reproduced. No test process was left running.

## Loosening answers
LOOSENING-CHECK 54ff1a1efcdc: not a loosening
VERDICT: NOT CONVERGED

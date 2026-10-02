<!-- codex-review: model=gpt-5.5 -->

**Findings**

BLOCKING: R3 still has false negatives; it only catches `$OUT` at the end of the payload, not `$OUT` followed by punctuation or other text.

Evidence:
[scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:41) says:

```text
R3  No arm interpolates `$OUT` AFTER ANY OTHER TEXT without guarding on `[ -n "$OUT" ]`
```

But the implementation is:

```python
before = with_detail.partition(_PROBE)[0].rstrip()
without = observe(hook_src, rc, "").rstrip()
if without == before:
    bad.append(rc)
```

at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:352).

That detects `Detail: $OUT` because empty output leaves exactly the prefix. It misses `Detail: $OUT.`, `Detail: [$OUT]`, and `prefix $OUT suffix`, all of which interpolate `$OUT` after prior text without a guard.

Reproduction I ran, after checking the known positive first:

```text
5) PAYLOAD="unreadable. Detail: $OUT" ;;
with    = 'unreadable. Detail: PROBE-DETAIL-TEXT\n'
without = 'unreadable. Detail: \n'
result  = [5]

5) PAYLOAD="unreadable. Detail: $OUT." ;;
with    = 'unreadable. Detail: PROBE-DETAIL-TEXT.\n'
without = 'unreadable. Detail: .\n'
result  = []

5) PAYLOAD="unreadable. Detail: [$OUT]" ;;
with    = 'unreadable. Detail: [PROBE-DETAIL-TEXT]\n'
without = 'unreadable. Detail: []\n'
result  = []

5) PAYLOAD="prefix $OUT suffix" ;;
with    = 'prefix PROBE-DETAIL-TEXT suffix\n'
without = 'prefix  suffix\n'
result  = []
```

What would prove this wrong: `dangling_detail()` returning `[5]` for `PAYLOAD="unreadable. Detail: $OUT."` and `PAYLOAD="prefix $OUT suffix"`, or the stated R3 contract being narrowed to “only rejects arms whose no-detail payload is exactly the text before `$OUT`”.

This also refutes the stated strictness in the fold. The tests at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:777) cover labels and one unlabeled terminal `$OUT`, but not a suffix after `$OUT`.

**Central Claim**

The fold’s central claim is only half true. It no longer enumerates English labels, so the old label vocabulary cannot be incomplete in the same way. But it replaced that vocabulary with an unstated shape assumption: the empty-output payload must equal the prefix before `_PROBE`.

So R3 no longer has a label vocabulary left to be incomplete, but it still has an incomplete payload-shape vocabulary.

**Other Areas Checked**

R4 membership: I observed the shipped hook directly. rc 0/2/3/4 are silent with empty matcher output; rc 5 and 6 forward static sentences. `silent_codes(live,{0,2,3,4,5,6})` returned `[]`. The hook itself says rc 3 is guarded because the stale-cache nag dedupes while keeping rc 3 at [.claude/hooks/surface-recall.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/surface-recall.sh:60). I did not refute the R4 membership.

Wiring/global leakage: I imported the module, saved `ROOT`, `MATCHER`, `HOOK`, and `_self_test`, ran `_self_test()`, then `main([])`. The globals compared equal before and after. The restoration code is the `finally` at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:864) and the `_self_test` restore at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:901). No leak found.

M3/L4 raw counts: line-continuation tuples, parenthesized tuples, and a harmless separate annotation are accepted. Starred targets, chained assignments, and nonliteral tuple calls are refused. That is conservative but consistent with “readable without guessing” at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:222). No defect found.

`_read_or_refuse`: direct calls turn `FileNotFoundError`, `IsADirectoryError`, and other `OSError`s into `CannotRun`, as intended at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:496). The missing-file message says “exists but cannot be read”, but `main()` prechecks `is_file()` at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:505), so I did not classify that as a functional defect.

#206/#207 reachability: both remain real latent holes, and the backlog rows say that. #206 says “nothing mechanical” holds the line at [docs/backlog.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/backlog.md:234). #207 says the shipped catch-all is silent and therefore not triggerable today at [docs/backlog.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/backlog.md:235). I did not find the current rows denying reachability.

**Size / Design**

Measured numbers:
`wc -l` gives `904 scripts/check-rc-contract.py`, `95 .claude/hooks/surface-recall.sh`.
The suite marker starts at line 546, so production-before-suite is 545 lines and suite-including-marker is 359 lines.
A nonblank/noncomment shell count gives 23 hook code lines.

The guard still earns the cross-language contract check. But this finding supports moving some hook-message behavior into a hook-owned suite: R3 is fundamentally about rendered hook payloads, and the current guard’s observer is close to being that suite already. Keeping R1/R2 in the cross-file guard makes sense; R3/R4 could be clearer as hook fixtures plus one contract-level invocation.

**Could Not Establish**

I did not independently reproduce the prompt’s “382 production code lines” number. I reproduced the totals and the 23 hook code lines, but Python code-line counting depends on whether module/function docstrings and multiline strings count as code.

I did not run the 42-minute mutation sweep, per instruction.

NOT CONVERGED

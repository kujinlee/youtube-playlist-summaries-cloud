# ci-observer-log — round 1, Codex half

Subject: `6a8a2fbc` on `ci-observer-log`. Ran concurrently with the Claude half, which is the
measured-safe topology for round 1 only.

<!-- codex-review: model=gpt-5.5 -->

⚠ **FORMAT NOTE, recorded rather than normalised.** This capture did not emit the requested
`## Findings` table or a `**VERDICT:**` line. It found a real defect and showed its work, so it is
filed as a round — but the shape was asked for and not delivered, and this repo's own rule is that
*a report format is a CONTRACT*: a reader grepping for `VERDICT` finds nothing here and could read
that as a clean pass. Treated as **NOT CONVERGED, one Low**.

⭐ **Its one finding was found INDEPENDENTLY by the Claude half** (as that half's finding 7), from a
different direction — this half by driving payloads through `--decide`, the other by calling
`log_line` directly. The two halves otherwise shared nothing: this one returned 1 finding, the other
9, with exactly that one in common.

**Finding**
Low: [scripts/check-ci-watched.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-ci-watched.py:260) writes `session_id` from arbitrary Stop payload directly into the tab-separated log at [line 169](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-ci-watched.py:169). A tab or newline in `session_id` corrupts the “four columns, one record per warning” shape, which is the evidence base this commit adds.

Command run:

```sh
python3 - <<'PY'
# import script, redirect WARN_LOG/SENTINEL to temp, stub CI as pending,
# then run payloads with normal/tab/newline session_id
PY
```

Real output:

```text
session_repr= 'sess-ok'
rc= 1
raw_log_repr= '2026-09-22T18:12:50-07:00\tsess-ok\tunwatched\t1 unresolved on cafef00d\n'
physical_lines= 1
tab_counts= [3]
session_repr= 'sess\twith-tab'
rc= 1
raw_log_repr= '2026-09-22T18:12:51-07:00\tsess\twith-tab\tunwatched\t1 unresolved on cafef00d\n'
physical_lines= 1
tab_counts= [4]
session_repr= 'sess\nwith-newline'
rc= 1
raw_log_repr= '2026-09-22T18:12:51-07:00\tsess\nwith-newline\tunwatched\t1 unresolved on cafef00d\n'
physical_lines= 2
tab_counts= [1, 2]
```

A sanitizer for log fields, at least replacing `\t`, `\r`, and `\n`, would make the falsifier fail.

**Checks**
Control proved green:

```text
python3 scripts/check-ci-watched.py --self-test
42/42 self-test cases passed
```

Fresh `$HOME` self-test did not append to the real log:

```text
rc=0
before=absent
after=absent
summary=42/42 self-test cases passed
```

Unwritable log still warns and reports the lost evidence:

```text
rc= 1
has_warning= True
has_log_failure= True
```

Producer enumeration was mechanical for the new pure producers: AST walk over `_self_test` found `warn_reason` exercised at two distinct inputs for both classes, and `log_line` exercised at two distinct four-column inputs plus empty-session fallback.

Attacked, and found sound.


**VERDICT: NOT CONVERGED** — one Low (field injection), folded.

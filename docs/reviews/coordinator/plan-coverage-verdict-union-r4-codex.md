# Post-Plan Gate round 4 — CODEX half — backlog #91 coverage-verdict union

Subject: **round 3's own fixes**, in the working tree at the r3 fold (committed as `0a6f6319`).
Dispatched via `scripts/codex-review.py`; `gate_ran=true`, model `gpt-5.5` after
`gpt-5.6-sol/-terra/-luna` each returned HTTP 400. **First Codex half that has actually run in
this series** — rounds 1–3 were genuine CANNOT RUNs and are recorded as `REVIEW GAP:`.

⚠ Filed as **r4**, not r3, because it reviewed the POST-fold tree. Calling it r3 would
misdescribe its subject, which is the error class this branch keeps recording.

---

<!-- codex-review: model=gpt-5.5 -->

CONVERGED.

**Blocking**
None found.

Measured:
```bash
python3 scripts/check-plan-code.py --self-test
# 223/223 passed

python3 scripts/coverage_verdict.py --self-test
# 22/22 passed
```

What would prove me wrong: a concrete `extract()` input with a non-empty mutations declaration that returns `muts == []` and `mut_readable is True`, excluding the intentional empty `[]` declaration.

**High**
None found.

Measured representative routes:
```text
file_after_mut ... muts=[] mut_readable=False
mut_after_mut ... muts=[] mut_readable=False
empty_object ... muts=[] mut_readable=False
empty_string ... muts=[] mut_readable=False
bad_json_with_code ... muts=[] mut_readable=False
unterminated ... muts=[] mut_readable=False
empty_list ... muts=[] mut_readable=True problems=[]
```

`empty_list` is the only `muts == [] / mut_readable=True` route I measured, and it is an honest zero, not lost declared entries.

What would prove me wrong: a parser route that loses declared entry objects without hitting lines [214-217](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:214), [234-237](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:234), [283-295](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:283), or [327-329](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:327).

**Medium**
None found.

Measured census cases:
```text
dropped_only:
python fences: 1 (0 assembled, 1 tagged then DROPPED, 0 illustrative)
subject: --compare was given, but no block was assembled

dropped_plus_safe:
python fences: 2 (1 assembled, 1 tagged then DROPPED, 0 illustrative)
m.py 1 blocks assembled -> 1/1 passed
subject: the plan's blocks, DIFFED against the delivered files:
```

The census now follows the unsafe-tag drop at [324-325](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:324), and I did not find another evidence-line pair disagreeing.

The new self-tests are not vacuous for the four core reverted shapes:
```text
early_return_loses_mut_readable rc=1
  [FAIL] a plan whose mutations block does not PARSE is not an honest zero
  [FAIL] ...nor is a mutations tag with no JSON block after it

with_code_return_loses_mut_readable rc=1
  [FAIL] a plan WITH code and an unparseable mutations block is not a measured zero

census_stops_following_drop rc=1
  [FAIL] the census and the subject sentence cannot contradict each other

verify_mode_reads_result_again rc=1
  [FAIL] a --compare run with nothing assembled reports the mode it was GIVEN
```

What would prove me wrong: an in-memory revert of one of the eight new manifest mutations that still gets `223/223 passed`.

**Low**
Manifest-anchor fragility remains. New entries 32, 35, and 36 anchor on exact diagnostic text, e.g. [check-plan-code.json:350](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-plan-code.json:350), [383](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-plan-code.json:383), and [394](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-plan-code.json:394). The next plausible cleanup that centralizes or rewrites parser diagnostics would rewrite these anchors.

Measured:
```text
entries 41
all manifest old anchors resolve uniquely now:
done
```

So this is not a current break, but it is the same maintenance pressure that caused the two retargets.

What would prove me wrong: a project rule that these diagnostics are stable anchor surfaces, or retargeting these entries onto less prose-heavy structural statements while preserving unique resolution.

<!-- codex-review: model=gpt-5.5 -->

severity: Blocking  
component: top-level validation  
aim: deliverable  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:167), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:232)

`json.loads` does not remove the r3 Blocking class. A JSON object with no `findings` key is well-formed, and the rules the spec says are kept unchanged do not validate top-level `findings`. Current protection is in `parse_header`, which the spec deletes.

Command:
```text
python3 - <<'PY'
import json, importlib.util
spec=importlib.util.spec_from_file_location('crd','scripts/check-review-decision.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
rec=json.loads('{"round":1,"fixes_nontrivial":false}')
print('json keys', sorted(rec.keys()))
print('decide one-round tree-reviewed', mod.decide([rec], 'one-round', True))
PY
```

Output:
```text
json keys ['fixes_nontrivial', 'round']
decide one-round tree-reviewed ('STOP', 'converged — 1 round(s) with no Blocking/High and nothing in the deliverable — and a round saw the merging tree')
```

Walk of the six defects: r1 block-style and r2 marker-span are structural and JSON can remove them if conversion is correct; r2 `severity High` is syntax only in one spelling, but a wrong key remains a `_validate` failure; r3 absent `findings` is not stopped by JSON; r6 braces-in-prose is structural; r6 unreadable `fixes_nontrivial` is a value/top-level validation problem, not a JSON problem.

severity: Blocking  
component: conversion falsifiers  
aim: deliverable  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:118), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:241)

The round-trip measurement is of `parse_header` output, not document content. `parse_header` returns only `round`, `findings`, and `fixes_nontrivial`, so §2 can pass while dropping or misreading `subject` and `halves`. The two falsifiers also miss this: verdict unchanged, finding count unchanged.

Command output:
```text
parse_header keys: ['findings', 'fixes_nontrivial', 'round']
subject in output: None
halves in output: None
base decision STOP finding markers 1
mut decision STOP finding markers 1
parsed outputs equal: True
```

The constructed `mut` changed `subject` and changed `halves.claude` from `ran` to a `GAP`, but both proposed falsifiers still pass. A real converter must read the fenced document block itself, including `subject`, `halves`, comments, and any YAML features, not just `parse_header`’s decision projection.

severity: High  
component: corpus feature measurement  
aim: instrument  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:121), [docs/reviews/coordinator/seed-explainer-serve-manifest-r2-coordinator.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/coordinator/seed-explainer-serve-manifest-r2-coordinator.md:9)

The “0 headers with a YAML comment” measurement does not reproduce. Among the 30 parseable headers, one uses an inline YAML comment in `halves`.

Command output:
```text
parseable header comment lines 1 [('seed-explainer-serve-manifest-r2-coordinator.md', 6, "  codex: standin-by-claude   # round 1's Codex half timed out; see that round's REVIEW GAP")]
parseable header block scalar lines 0 []
```

That also falsifies “nothing in the corpus uses a YAML feature JSON lacks.” The block-scalar count is reproducible at 0.

severity: High  
component: no-fallback migration  
aim: deliverable  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:114), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:356)

The no-fallback rule is a slogan unless the migration covers branches in flight. `rounds_for()` reads coordinator docs from the current branch name. A branch that rebases/merges after this lands but still carries YAML round docs for its own branch will move from “decidable by the old reader” to `CANNOT_RUN` until those branch-local docs are manually converted. Refusing a fallback may be right eventually, but the spec needs a branch-coverage mechanism or a deliberate cutover failure mode.

severity: Medium  
component: size measurements  
aim: instrument  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:74)

The 121-line deletion number does not reproduce for the named deletion set.

Command output:
```text
span parse_header (198, 251, 54)
span _findings_span (287, 299, 13)
span _scalarise (302, 311, 10)
span _block_findings (314, 345, 32)
deleted four funcs sum 109
deleted incl FINDING_RE 110
decision funcs sum 93
```

The “93 decision rules kept” number does reproduce if counted as `scope_for`, `thrashing_component`, `converged`, `sequence_error`, `decide`, and `exit_code_for`.

severity: Medium  
component: self-test retirement  
aim: instrument  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:210), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:556)

“Many exist only to exercise malformed YAML” overstates the retirement case. The declared count is real:

```text
61/61 self-test cases passed
```

But the record-reading cases are 16 cases at lines 552-600. Strictly malformed-YAML-only cases are at most two: empty list item and `severity High` without colon. Several others are still required after JSON as schema/value tests: missing `round`, missing `findings`, out-of-set severity, missing component, non-trivial-fix behavior. Retiring them “with their subject” hides tests that should be rewritten against JSON/top-level validation.

severity: Medium  
component: defect taxonomy  
aim: instrument  
fix_induced: false  
evidence: [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:212), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:224), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:228), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:254), [scripts/check-review-decision.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-decision.py:260)

Six recorded defects is the right count, and the table mostly identifies each symptom. The umbrella claim “all absence reads as a pass” is not correct: r2 Medium and r6 Medium are false `CANNOT_RUN` cases, not pass-open cases. The spec itself says those rows read as false `CANNOT_RUN`.

severity: Low  
component: line-density claim  
aim: instrument  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:88)

“14 lines today, 13 as JSON” does not reproduce from the example shown in the spec.

Command output:
```text
yaml body lines 4 fenced lines 6
json body lines 7 fenced lines 9
```

severity: Low  
component: halves claim  
aim: instrument  
fix_induced: false  
evidence: [docs/superpowers/specs/2026-09-25-round-record-substrate-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:57), [scripts/check-review-rounds.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-review-rounds.py:81)

The claim true at the header layer is false as stated by name: `check-review-rounds.py` does contain `HALVES = ("codex", "claude")` and uses it at line 519. The intended point is narrower: it does not read `halves:` from the round header.

No finding on these measurements: `30 of 72` parse, `42` do not, `39` of those have no YAML header, `30/30` parsed outputs JSON round-trip, `61` self-test cases, and no `requirements.txt`, `pyproject.toml`, or `setup.py` at repo max depth 2.

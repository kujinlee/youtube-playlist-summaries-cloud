<!-- codex-review: model=gpt-5.5 -->

severity: Blocking  
component: conversion-falsifiers  
aim: instrument  
fix_induced: true  
evidence: §2 replaces the old falsifiers with “a FIELD-LEVEL TEXT DIFF,” but that diff cannot catch the stated comma-in-quoted-`component` misread without parsing YAML flow mappings correctly. A textual compare has to know that `component: "check-docs, check-backlog"` is one field, not two; that is exactly a second YAML-subset parser, reintroducing the class being deleted. The spec also still has stale text later: the concern table says conversion safety is “verdict invariance and per-document count parity,” and “How we would know it failed” still uses finding-count parity. So the fold both declares parity dropped and leaves it as the mechanism.

severity: High  
component: migration-cutover  
aim: deliverable  
fix_induced: true  
evidence: The new cutover section is a sentence, not a forcing mechanism. I ran `python3 scripts/check-review-decision.py` at HEAD `bef49007`; it reports `ROUND_OWED ... branch=backlog-117-parser-substrate ... rounds=0`. That verifies the recorded hazard: `rounds_for()` keys on the branch name at `scripts/check-review-decision.py:628`, but this branch’s own rounds are named `round-record-substrate-*`. The paragraph says “a branch carrying YAML converts its own,” but names no gate, command, template enforcement, or CI check that makes that happen before no-fallback deletion turns those branches into `CANNOT_RUN`.

severity: High  
component: roundtrip-evidence  
aim: instrument  
fix_induced: true  
evidence: The corrected measurements do not reproduce as stated. Command run: a Python probe over `docs/reviews/coordinator/*-r*-coordinator.md` using `parse_header` and raw fenced YAML scans. Results: `73` round-shaped coordinator files, `31` parseable, `42` unparseable; raw coordinator YAML blocks expose `9` top-level keys; exactly `1` inline YAML comment; block scalars `0`. Compact faithful JSON is longer in `31/31`, median `+1`, not `33/33`. The spec still says “All 30 currently-parseable round documents” and “JSON is LONGER in 33 of 33,” so its corpus is stale or mixed.

severity: High  
component: scope-entanglement  
aim: deliverable  
fix_induced: true  
evidence: The #187 factual claim checks out, but the fold stops at an unresolved fork. I widened `REQUIRED["disposition"]` with `refuted`, `redesigned`, `retreat`, and `moot`; all three `ship-src-root-alone-r1/r2/r3` coordinator docs then parse, with 10, 9, and 7 findings. So they fail on nothing but `disposition`. But the spec’s resolution is “settled first, or the schema deliberately carries the narrower set and says why.” That is not a decision for Phase 1; it leaves implementation order and migration corpus undefined.

severity: Medium  
component: selftest-retirement  
aim: instrument  
fix_induced: true  
evidence: The sizing numbers partially reproduce, but the split does not. `python3 scripts/check-review-decision.py --self-test` gives `61/61`; the record-reading section has 16 cases; mutating `_validate` to ignore missing decision fields still leaves `61/61` green. But the claimed “3 going red” names `fixes_nontrivial`, and there is no parser/schema self-test for missing `fixes_nontrivial`; the only direct non-trivial case constructs dicts in memory. Also the table says “the count may RISE,” then immediately below says “The --self-test count will FALL.” The fold preserved two incompatible sizing instructions.

severity: Medium  
component: header-schema  
aim: deliverable  
fix_induced: true  
evidence: Layer 2 now names only `round`, `fixes_nontrivial`, and `findings`. That covers the top-level checks `parse_header` enforces today: `round` present/int, `findings` present, `fixes_nontrivial` present/bool. But the same spec measures nine top-level keys and says conversion must carry them. The other six are left with no post-cutover owner: `subject`, `halves`, `architecture_review`, `deliverable_findings`, `deliverable_code_findings`, `stopping_rule`. Given r7 L1 was specifically a `halves` malformed-record defect, leaving these as “documentation” without even type/preservation rules moves the next defect out of schema and into silent evidence loss.

severity: Low  
component: defect-inventory  
aim: deliverable  
fix_induced: true  
evidence: The inventory was corrected to seven and the five-pass/two-false-refusal split is right, including r7 L1 from `docs/backlog.md:145`. But stale derived text remains: the evidence parenthetical still lists only six comment locations, and the concern table still says “6 recorded defects, all absence reads as a pass.” The fix repaired the headline while leaving downstream claims from the old premise in place.

# guard-fail-open-batch — round 3, Codex confirmation

Reviewed HEAD `66b1e026`, PR #404, `git diff origin/master...HEAD`. Mandate: REFUTE. Last confirmation round; no implementation folds.

## Receipt bet

No demonstrated protocol defect. The real hook creates a fresh, empty receipt with `mktemp`; it never accepts a caller-provided or persistent receipt path. Its second EXIT trap includes BOTH temporary files, preserving the earlier cleanup. Independent executions with TMPDIR redirected into an isolated directory left no `tmp.*` artifacts.

Executed copied-tree real-hook probes: empty receipt, garbage, whitespace-only, `0x`, and `1 2` each warn/exit 1 with “no verdict”. A checker forced to crash immediately AFTER writing its actual verdict still produces hook 0 for GOOD, 2 for REVERTED, and 2 for empty/CANNOT RUN. These are completed checker verdicts despite process failure, as designed. Whitespace surrounding a single digit is accepted by the intentional whitespace normalization; normalization alone does not invent a verdict from an empty fresh file.

Direct CLI probes: a pre-existing receipt containing 2 is overwritten with 0 on a compliant check; a nonexistent receipt parent raises FileNotFoundError/exit 1. Neither supplies a stale receipt to the hook, whose path is fresh on every invocation. `--self-test --receipt FILE` leaves FILE untouched and returns the suite status; the hook never invokes this combination. A wrapper maliciously writing a forged verdict is outside the distinction this channel provides: the same interpreter is trusted to execute the checker and detector.

All ten shipped real-hook cases pass. Their paired controls establish a working copied-tree checker (GOOD 0, UPSTREAM 2); the chatty case still blocks, a broken interpreter and failed payload copy warn, a truncated envelope warns, checker-only failure warns, prose-only rewording still blocks, and a wrapper that does not run the checker warns. The two intentional exit-0 cases are a compliant skill and another skill (outside the handoff gate). No ambient-pass defect demonstrated. The warning cases assert only return codes, so these tests do not independently prove diagnostic attribution; this is a test limitation, not an observed wrong result.

Applied the new no-receipt mutation to an isolated copied checker and executed its self-test. Exit 1; four named hook assertions fail, including the manifest target “hook: blocks /handoff when the skill names the wrong path”. The compliant, chatty, and reworded controls also fail. The mutation is killed by receipt-dependent behavior.

## Documentation and filed follow-up

The blind `--clear` now says “removed no arm record” and explicitly acknowledges legacy cleanup when it happened. PR #404’s live body narrows CANNOT RUN to “CANNOT RUN, or a warning for the handoff hook” and names the five outstanding malformed inputs.

Low, documentation only — backlog #357 preserves all five r2 findings and their qualifications, but “Each EXECUTED through the real entry point” overstates the evidence for findings 7 and 8. The r2 record says the permission probe called `arms_newest_first()` with a sentinel double, and the malformed-row probe called `run_decide` with `_pr_checks_raw` stubbed; neither was an actual CLI execution. Its universal falsifier “through --decide, exits 2” also cannot literally apply to check-handoff-path, which has no --decide option. FILED below as backlog #358; no implementation change requested in this round. This does not refute the receipt bet.

## Validation

All touched self-tests executed and passed: banner 239/239; CI watcher 86/86; closing table 155/155; handoff 20/20 (including ten real-hook cases); transcript references 19/19; mutation harness/check-plan-code 239/239. The hook has no standalone self-test switch. The full mutation sweep was not repeated; the new mutation was independently executed as described above.

VERDICT: CONVERGED

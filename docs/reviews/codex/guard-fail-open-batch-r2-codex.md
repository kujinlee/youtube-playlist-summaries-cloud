# guard-fail-open-batch — round 2, Codex confirmation

Subject: PR #404, HEAD `aa631d9f`, `git diff origin/master...HEAD`. Mandate: REFUTE.
Read both r1 halves, coordinator record, decision-log bet, and live PR body (`gh pr view 404`).

## Findings

1. **Medium — fold-induced: a presentation-only checker change bypasses the blocking verdict.** `.claude/hooks/enforce-handoff-path.sh:77`.

   Executed the real hook in a temporary copied tree with a reverted skill (`Save with mktemp`). Current checker, including the hook's `--quiet`: exit **2**, BLOCKED. Changed only the checker's finding text from `SKILL.md does not name` to `SKILL.md omits`; left its detection, REVERTED label, exit **1**, and CLI intact. The same hook now exits **1**, non-blocking, and incorrectly says the checker “did not run.” This is conditional on a wording change, not a bypass with today's unmodified checker. It demonstrates the requested wording-drift failure: an implementation detail of English prose has become an undocumented second verdict protocol. Preserve a machine-readable distinction between a completed checker verdict and interpreter failure. **Disposition: fold defect, requires correction.**

2. **Medium — pre-existing: undecodable transcripts still crash into the warning code before checking.** `scripts/check-banner-armed.py:1308`, `scripts/check-closing-table.py:907`, `scripts/check-transcript-references.py:135`.

   Executed all three actual `--decide` entry points against a temporary transcript containing bytes `b'{"type":"user","message":{"content":"hi"}}\n\xff\n'`, supplying its path in a valid envelope. Each exits **1**, with `UnicodeDecodeError`, rather than CANNOT RUN **2**. Their read handlers catch `OSError`, not decoding failures, and the new turn-rule handlers start after the read. No banner/table/reference assessment occurred. **Disposition: FILED here for follow-up; outside the fold, no implementation change in this confirmation round.**

3. **Medium — pre-existing: valid JSON with the wrong envelope shape still crashes into the warning code.** `scripts/check-banner-armed.py:1301`, `scripts/check-transcript-references.py:130`.

   Executed both actual `--decide` entry points with stdin `[]`: each exits **1**, `AttributeError: 'list' object has no attribute 'get'`, before inspecting a transcript. Control: closing-table receives the same input and correctly exits **2**, CANNOT RUN. These consumers need envelope-shape validation independently of record filtering. **Disposition: FILED here for follow-up; outside the fold.**

4. **Low — fold-induced: blind clear says it removed nothing after deleting the legacy file.** `scripts/check-ci-watched.py:1215`.

   Executed `main(['--clear'], None)` with SENTINEL redirected into a temporary directory, an existing sibling `ci-watching` legacy file, and `_run` returning `None`. Result: exit **2**, legacy file **deleted**, stdout `CANNOT RUN: could not read HEAD, so --clear removed NOTHING. TREAT THIS AS NOT CLEARED.` The cleanup and exit code are correct; the new ordering makes the absolute statement false. Say no HEAD-specific arm record was removed. **Disposition: fold defect.**

5. **Low — remaining blind success if the checker invocation exits zero before running.** `.claude/hooks/enforce-handoff-path.sh:72`.

   Executed the real hook in a temporary copied tree with a reverted skill (`Save with mktemp`). A `python3` shim delegated the envelope-detection call to real Python, then exited **0** without running `check-handoff-path.py` on the second call. The hook exited **0** with empty stdout and stderr, allowing the reverted skill. This requires a broken wrapper that falsely reports success; it is less likely than a checker wording change, but it is a direct remaining way the hook reports success without a check. The hook needs a positive checker receipt if it aims to distinguish that case. **Disposition: FILED; this is a residual of the original exit-code protocol, not caused by the r1 verdict gate.**

6. **Low — pre-existing: an undecodable handoff skill is treated as a non-blocking checker failure.** `scripts/check-handoff-path.py:97`, `.claude/hooks/enforce-handoff-path.sh:77`.

   Executed the real hook in a temporary copied tree with the skill containing byte `0xff`. `read_text(encoding="utf-8")` raises `UnicodeDecodeError`; the checker exits 1 with a traceback, and the hook exits 1 with “did not run”, so a real handoff is allowed. The checker contract says unreadable input is CANNOT RUN, but its `except OSError` omits decode failures. **Disposition: FILED, Low; malformed bytes are uncommon, but the hook's warning is non-blocking.**

7. **Low — pre-existing: CI sentinel permission failure escapes before the CI verdict.** `scripts/check-ci-watched.py:471`, `:474-478`, `:530`.

   Executed `arms_newest_first()` with a sentinel object whose `iterdir()` raises `PermissionError("denied")`; the exception escaped. `run_decide` calls this reader before `decide`, so a permission-denied sentinel produces a traceback/rc 1 rather than CANNOT RUN. **Disposition: FILED, Low; this is an environmental read failure, not a normal GitHub response.**

8. **Low — pre-existing: malformed external check rows crash the CI guard before checking.** `scripts/check-ci-watched.py:521-523`, `:532`.

   Executed `run_decide` with `_pr_checks_raw() -> ('[123]', False)`, a valid HEAD, and no skip reason. JSON parsing accepts the list, then `decide` raises `AttributeError: 'int' object has no attribute 'get'`; no CI verdict is produced. **Disposition: FILED, Low; the probe is a malformed external-row schema, not an observed `gh` payload.**

9. **Low — prose overstates the fold.** PR #404's opening says “Each now says CANNOT RUN”, but the handoff hook's checker-failure and broken-interpreter paths intentionally warn/exit 1, and the three malformed-input paths above still traceback/exit 1. The dashboard is narrower (“could not run”) and the four backlog rows accurately describe their fixes; the coordinator is a historical r1 record and is accurate about r1's dispositions. **Disposition: FILED as documentation correction.**

## Confirmation checks

- All touched Python self-tests passed: banner **239/239**, CI watcher **86/86**, closing table **155/155**, handoff **18/18**, transcript references **19/19**, mutation harness/check-plan-code **239/239**. Shell hook behavior is exercised by handoff's eight real-hook cases; it has no independent `--self-test` mode.
- Scanned **746** local `~/.claude/projects/**/*.jsonl` files for absent/null `message`. Many legitimate metadata records omit `message`; the new `obj.get('message', {})` default **keeps** them. Found **zero** explicit null-message records. The filter drops null, but the corpus does not establish a legitimate null-message regression; no such finding is asserted.
- Independently repeated that scan: **308,627** object records, **188,450** with no `message`, **0** with explicit `message: null`, and no unreadable files. The missing-field case is preserved by the `{}` default. Null is dropped; I found no transcript evidence that null is a legitimate message shape, so this is not filed as a defect.
- Confirmed the new `except Exception` spans only window/turn selection. A normal WARNING is determined afterward, so these handlers cannot swallow a real WARNING verdict; unexpected failures before that point become CANNOT RUN.
- The `--clear` reordering does run the legacy tidy before the missing-HEAD return and `head[:8]` occurs only after the falsy-HEAD return. The defect is only the inaccurate “removed NOTHING” text when the legacy file was just deleted.
- The new broad exception handlers surround turn selection, not warning generation. They cannot catch a normal warning return from the later decision/reporting paths.
- Current REVERTED output survives `--quiet` and blocks correctly. The wording-drift experiment in finding 1 is separate from that passing control.
- `head[:8]` follows the falsy-HEAD return; it introduces no None slicing failure. Legacy cleanup now runs on unreadable HEAD as intended, with the wording issue above.
- Additional executed probes: invalid UTF-8 through each actual `--decide` entry point produced rc **1** and a `UnicodeDecodeError`; `[]` as the payload produced rc **1** in banner and transcript-references, while closing-table returned CANNOT RUN **2**. The CI watcher probe `_pr_checks_raw() -> ('[123]', False)` produced `AttributeError: 'int' object has no attribute 'get'`; this is a malformed external-row schema probe, not an observed `gh` response. **Filed as low-priority defensive follow-ups**, not evidence of a normal CI response failing.
- PR/dashboard counts reconcile: +3 banner, +4 CI, +1 closing, +8 handoff, +1 references = **17** cases; manifest deltas **3+4+1+1 = 9**, total **2114**. The quoted historical scoped **195/195** mutation run was not independently repeated in this round. Backlog #253/#255/#152/#111 accurately describe their narrow fixes; the PR/dashboard blanket “each now says CANNOT RUN” remains too broad given findings 2–3. The coordinator truthfully records the r1 dispositions, but its “only the checker's own verdict” description omits the new dependence on exact prose.

The decision-log bet is refuted: Medium findings remain, including a fold-induced protocol fragility demonstrated under the explicitly requested wording-change scenario. Follow-ups are recorded above rather than folded into implementation. Existing-finding status changes this pass: **0**; newly surfaced follow-ups: **4** (findings 6–9).

VERDICT: NOT CONVERGED

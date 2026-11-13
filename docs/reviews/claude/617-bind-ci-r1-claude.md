Reviewed head: fb0c31f675993ef826265b43ef6581672e46b9e3

# 617-bind-ci — round 1, Claude half (adversarial)

Subject: backlog #617 part 1. `ci_flaky_contract` in `scripts/sweep-red-alert.py`, its call in `main`, 7 new self-test cases, 5 new mutants (pin 23 -> 28).

## Gates run by this reviewer

| Check | Result |
|---|---|
| `python3 scripts/sweep-red-alert.py --self-test` | 40/40 passed (4.5 s) |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/sweep-red-alert.py` | rc 0: 28 mutations, 28 killed, 28 attributed to the case each names, 0 survivors (a diagnostic slice, not the full gate) |
| Each of the 5 new mutants, traced by hand | Each one is killed by the case it names, for the reason it names. The `main` mutant is killed because the step fixture writes every shard file, so without the contract the step goes green and prints "no FLAKY mutation" |
| Adversarial `ci.yml` variants, run against the real function (scratch harness, repo untouched) | Results below |

No BLOCKER or MAJOR. I could not construct a `ci.yml` drift that silences the FLAKY scan. Every drift the contract misses still makes `read_flaky` report shard files as missing, so the step goes red (NOT RUN). The findings below are about what the contract claims to prove, false reds, ordering, and mutants nobody wrote.

## MINOR

**m1. The docstring claims more than the function proves.** `scripts/sweep-red-alert.py:106` says "RAISES unless `ci.yml` hands this script the files `read_flaky` reads". The function checks only 2 of the links in that chain. I measured these real drifts, and each one leaves the contract `ok`:
- download `path:` no longer equals the alert step's `FLAKY_DIR` (`.../flaky` vs `.../sweep-flaky`);
- download `pattern:` no longer matches the upload `name:` (`flaky-*` vs `sweep-flaky-<i>`);
- upload `path:` widened to `${{ runner.temp }}/`, so each file nests one directory deeper;
- `merge-multiple: true` placed under `env:` instead of `with:`.

Each of these is still loud: `read_flaky` reports every shard file missing and the step goes red. So this is an overclaim, not a silent hole. Fix: narrow the docstring to the two links it checks (the write's file name and index variable, and `merge-multiple`), or extend the check to the path, pattern and name joins.

**m2. Running the contract before `read_flaky` only loses FLAKY filings.** `scripts/sweep-red-alert.py:182`. When the contract is truly red, nothing would have been read anyway: with `$SHARD_TOTAL`, every shard writes `shard-N.txt`, which is outside `range(N)`; with `merge-multiple: false`, each file sits in a subdirectory. When the contract is falsely red, it aborts the filing of names that `read_flaky` could have read and filed (the r3 M1 rule: "names the PRESENT files hold are FILED first"). Harmless edits that I measured as false reds:
- `merge-multiple: true  # one dir` (a trailing comment, in a file that comments nearly every line);
- `merge-multiple: 'true'`;
- `shard-"$SHARD_INDEX".txt` or `${SHARD_INDEX:-0}`, both of which give 0 writes;
- the step written as `- if: ...` with `name:` on a later line.

Scenario: someone adds a trailing comment to line 1515. From then on, every master run is red at the contract, and the FLAKY names in the present shard files go unfiled. A red master check with no issue is exactly the unseen red that #330 exists to prevent. Two ways to fix it, either one enough:
- call the contract after the filing, at the point where `missing` is non-empty, so it explains a missing file instead of pre-empting the read;
- or strip a trailing `#` comment and the quotes before comparing.

The alert-first order (after `alert_red`) is correct and unchanged.

**m3. The index-variable check reads the whole workflow, not the step that writes the file.** `scripts/sweep-red-alert.py:116`. Any line anywhere in the file of the form `<VAR>: ${{ strategy.job-index }}` satisfies it. Measured: change the shard step to `SHARD_INDEX: ${{ matrix.shard }}` (1-based, which is the matrix's own values) and add another job whose `env:` has `SHARD_INDEX: ${{ strategy.job-index }}`. The contract says `ok`. Today `SHARD_INDEX` occurs once, so this is latent. No case pins the scoping. Fix: look the variable up in the env of the same step as the write.

**m4. Three mutants nobody wrote survive every self-test case.** Measured against the self-test's own fixtures:
- `<= ind` -> `< ind` (`:126`). The only "rescue" case puts its `merge-multiple: true` in a different JOB (`later:` at indent 2), so the walk stops there either way. A `merge-multiple: true` in the NEXT STEP of the same job (indent 6, the alert step) is rescued under this mutant: the contract says `ok`. The case "a SECOND `merge-multiple: true` elsewhere" therefore does not prove the step boundary that its mutant's name claims ("runs on past the step").
- `len(starts) != 1` -> `< 1` (`:121`). No case has two download steps.
- dropping the trailing `\s*$` anchor in the index regex (`:116`). No case has a value like `${{ strategy.job-index }}x`.

Fix: put the rescue fixture in the next step of the same job, and add a case with a duplicate download step and one with a suffixed index value. Each of the last two needs its own mutant and +1 on the pin.

**m5. A second copy of the step-block walk.** `ci_flaky_contract` (`:120-128`) reimplements the walk that `step_run_block` already does (`:268-273`): find the line `- name: X`, take its indent, collect lines until the indent is `<=` that. The two copies can drift independently (memory: one rule, one place). Fix: factor out `step_block(workflow_text, name) -> list[str]` and use it in both.

**m6. A self-test case pins a quirk as if it were a rule.** `scripts/sweep-red-alert.py:400` (the second half of "no shard-file write at all RAISES, and so does a second one"). It proves "a second write" by appending a COMMENT. So a YAML comment that mentions the file name counts as a write. That pins comment-sensitivity as correct behaviour. Measured consequence in the other direction: the real write is renamed to `s$SHARD_INDEX.txt`, and a nearby comment `# writes sweep-flaky/shard-$SHARD_INDEX.txt` stays behind. The contract says `ok`. That drift is still loud through `read_flaky`, but the contract is green over it. Fix: skip comment lines when counting writes, and use a real second `run:` write as the fixture.

## Verdict

FINDINGS: 6 MINOR, 0 MAJOR, 0 BLOCKER. All six are within this change's scope; none is a silent loss of the FLAKY scan. (This file's last line uses `NOT CONVERGED`, the form `record-review-verdict.py` parses, to mean FINDINGS.)

VERDICT: NOT CONVERGED

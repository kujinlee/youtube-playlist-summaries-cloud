<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

None established.

## Medium

- **M1 — `-RS` remains an implementation-specific prescription.** At `.agents/skills/handoff/SKILL.md:15`, `scripts/check-handoff-path.py:49`, `docs/process-rationale.md:372`, and the new memory lesson, the fold presents it as the reader-safe replacement. BSD grep and freshly built **ugrep 7.8.4** both passed the symlink and plugin-tree probes. However, their `-S` meanings differ: BSD follows symlinks; ugrep follows file symlinks under `-r`, with `-R` providing directory traversal. GNU grep 3.12’s source option table contains **no `S`**, and installed ripgrep rejects `-R`. Name the supported binary or provide implementation-specific commands. GNU’s documented recursive option is `-R`. [GNU grep documentation](https://www.gnu.org/s/grep/manual/html_node/File-and-Directory-Selection.html)  
  The withdrawal also remains incomplete: the skill’s same paragraph still says “`-R` does” follow the symlink, and `scripts/check-handoff-path.py:54–56` still affirmatively prescribes `grep -R`.

- **M2 — The refusal’s added in-project qualification is false.** `.claude/hooks/enforce-handoff-path.sh:76` says the degraded destination is “the path above when the store is in-project.” With user-global configuration `{"data_dir":"notes","handoff_mode":"per_session"}` and no usable session ID, the actual hook prints **`<project>/notes/remember.md`**, although the refusal’s path above is `.remember/remember.md`. Missing, empty, `..`, and slash-containing IDs all reproduce this. Keep “the shared file in the resolved store” and remove the incorrect qualification.

## Low

- **L1 — The claimed pasteable locator still lacks a usable destination.** The skill’s `grep -RSn 'REMEMBER_HANDOFF=' "$CLAUDE_PLUGIN_ROOT"` exits **2** from this project’s ordinary shell because that variable is unset. The refusal at `:68` still prints `grep -n 'REMEMBER_HANDOFF=' <the hook>`, which produces a shell syntax error when pasted. Supply an actual plugin-cache path or an explicit path-discovery step.

## Checked and found SOUND

- Reviewed **`755c35a6`**, its fold, the whole branch diff, and all three prior reviews. Repository remains clean; no review file written.
- **30 live-hook runs:** three stores × two modes × five session-ID states. The three Boolean hint conditions hold; printed-path precedence remains intact.
- Refusal render: **exit 2**, empty stdout, **30 stderr lines**, no sentinel expansion. Shell syntax passes.
- Withdrawal sweep, including code comments: superseded growth/drift figures survive only as explicitly withdrawn quotations or filed testimony. Absent `check-withdrawal` references disclose its absence.
- Cross-branch records support **rounds 11–13**, rather than 9–13. Replaying the round-13 subject’s extracted production functions reproduced both lost `bad-name` headings and fabricated message headings. The new caveat accurately reports those defects.
- Store: **104 entries**, exactly one matching `remember*`. Five original citation sites verified; three hint conditions verified.
- `plugins.md`: **260/260**, whole-branch **5 added / 5 removed**.
- Memory rows: **190 and 172 characters**. The commit body’s **178** is inaccurate.
- `doctor.sh` reports legacy storage from the **main checkout**; from this linked worktree it reports the shared main-checkout store as **external**. The dashboard quotation needs that execution-directory qualification.
- Documentation guard passes; handoff guard passes; self-test **10/10**; all five handoff mutation anchors bind.
- **Previously unexamined scope:** no additional changed mechanism found. The unrelated harness memory is already covered by prior reviews and the provenance checks above.

## CANNOT RUN

**These are validation failures, not passes.**

- `check-selftest-counts.py` exits **1**, naming the two known dependency-affected guards. Paid-caller independently returns **12/32**, exit **1**, with `ERR_MODULE_NOT_FOUND`; `node_modules` is absent. Pre-existing and outside this diff.
- GNU grep binary replay could not complete: its source build failed during configuration. The unsupported `-S` finding rests on its actual source option table, not a successful GNU runtime probe.
- Historical installation behavior and complete historical harness executions were not replayed. Review-record attribution and the two targeted parser replays do not validate those broader claims.

## Instruments

Commit-message-first inspection; fold and range diffs; filesystem withdrawal sweeps; BSD grep, source-built ugrep 7.8.4, ripgrep and GNU source inspection; isolated live-hook matrix; sentinel refusal rendering; main/worktree doctor comparison; store/config census; cross-branch review records and parser replay; guards, self-tests, counts and mutation-anchor checks.

**Result: 0 Blocking / 0 High / 2 Medium / 1 Low. This round is not clean.**

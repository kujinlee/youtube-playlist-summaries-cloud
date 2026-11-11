# Round 1 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (3 High, 4 Medium, 3 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: ran
findings:
  - {id: CH2, severity: High, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
  - {id: CH1, severity: High, aim: deliverable, fix_induced: false, component: window-distance, disposition: fixed}
  - {id: CH3, severity: High, aim: deliverable, fix_induced: false, component: fail-idioms, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: gate-callers, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: pin-removal, disposition: fixed}
  - {id: CM3, severity: Medium, aim: instrument, fix_induced: false, component: no-entry-case, disposition: fixed}
  - {id: CM4, severity: Medium, aim: deliverable, fix_induced: false, component: move-detection, disposition: declined}
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: false, component: dashboard-text, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: process-prose, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: app-attestation, disposition: fixed}
```

`C` = Claude half, `X` = Codex half. **Both halves independently found the two worst:** a gate deleted
outright printed READY (Codex High 1 = CH2: `+++ /dev/null` set the path to None), and added lines pushed an
adjacent removal out of the 5-line window (Codex Medium 2 = CH1, with six comment lines). Both executed the
probes. Both found `--app-tests-passed` is self-attested and that no executable caller misreads rc 3. Codex
applied all 14 manifest mutations in memory: each failed via its named case.

Dispositions:
- **CH2 FIXED:** `diff_lines` and `failure_path_removals` keep the `--- a/` path when the target is
  `/dev/null`. Cases: a deleted gate script, a deleted hook in a subdirectory, and a deleted non-gate (quiet).
- **CH1 FIXED:** distance is measured in OLD-FILE lines (`old_side` drops `+` lines), so nothing an author adds
  can move a removal away. Cases: six added comments, eight added code lines; the existing six-line `_far`
  negative still holds quiet.
- **CH3 FIXED:** `FAIL_PATH` gains `failures?`, `return|exit [12]`, `SystemExit(` and `\bdeny\b`; `GATE_CODE`
  now covers `scripts/check-*.sh`, `scripts/ci/**` and `.claude/hooks/**`.
- **CM1 FIXED:** new `GATE_CALLER` (`.github/workflows/*.yml`, `.claude/settings*.json`,
  `check-schema-gates.sh`, `scripts/ci/**`): a removed line naming a gate (`GATE_REF`) not re-added holds.
- **CM2 FIXED:** a pin present before and absent after (deleted or renamed away) holds.
- **CM3 FIXED:** the pure NO-ENTRY case passed `body` nowhere; removed, and replaced by a `main()` case with a
  NO-ENTRY body asserting rc 0. Mutation: main() reads NO-ENTRY instead of NO-REVIEW → it reddens.
- **CM4 DECLINED, stated as a bound:** an identical line re-added in dead code reads as a MOVE. Telling dead
  code from live is not decidable from a diff, and the rule targets an honest change, not an evasion (the
  owner's threat is an accidental loosening merged unseen). The bound is written in the script's comment and
  the dashboard entry, beside "a removal beyond the window" and Codex's renamed-key note (now covered by CM2).
- **XL1 FIXED:** the replay's NO-REVIEW count is 9, not 8; the union of 11 stood.
- **CL1 FIXED:** `process-checklists.md` no longer lists merge as always a human gate; `process-rationale.md`
  marks the merge half superseded. **CL2 FIXED:** the HOLD message and a comment call the flag an attestation.

**Base rate after the fold:** loosening holds 8 of the last 40 merged PRs (adds #386, #367, #366 — each
rewrites a failure path or a CI gate invocation), against 5 of 32 before. Mutations 30 -> 41 (eleven added,
one anchor rebound after the `old_side` edit; a per-mutation in-memory run over a GREEN control — 128/128 —
killed each via its named case). Cases 114 -> 128.

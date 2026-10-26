# Round 1 — `guard-fail-open-batch` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETED

```yaml
round: 1
fixes_nontrivial: true
subject: guard-fail-open-batch
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: handoff-hook, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: turn-rule-consumers, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: handoff-hook, disposition: fixed}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: true, component: ci-watched, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: turn-rule-consumers, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: true, component: ci-watched, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: handoff-hook, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on the first PR #404 commit. Both: every touched suite green; each of the four
manifest mutations red via its named case; the old hook fails the chatty and broken-interpreter cases (13/15).

- **XM2 = CM1 (fixed):** #152 was half fixed — an OBJECT whose `message` is not an object still crashed the turn
  rule in `check-banner-armed`'s and `check-transcript-references`' own decide paths (exit 1). `_parse_records` now
  drops such a record, and both decide paths map any exception from the turn rule to CANNOT RUN.
- **XM1 = CL3 (fixed):** the hook's `cat > "$TMP"` was unchecked, and an unreadable (truncated, empty) envelope read
  as "not mine". The copy is checked; an unreadable envelope warns and exits 1.
- **XM3 (fixed):** a checker that fails to RUN was reported as "BLOCKED — the skill would write where nothing reads".
  Only the checker's own verdict (rc 1 + its finding, rc 2 + its CANNOT RUN) blocks; anything else warns.
- **XL4 = CL2 (fixed):** `--clear`'s early return skipped the legacy-file tidy; it now runs before HEAD is needed.
  Also (Codex note): a sentinel directory removed after the `is_dir()` gate lists no arms instead of raising.
- **CL1 (fixed):** the prose said 10 cases; the counts are restated from the suites (17 now).

Route: ACCRETE (decision-log row written before this fold). Round 2 alternates to the Codex half.

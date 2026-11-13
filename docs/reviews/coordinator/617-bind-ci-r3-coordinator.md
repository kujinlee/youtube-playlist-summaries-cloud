# Round 3 — `617-bind-ci` (backlog #617 part 1) — coordinator — ⟳ NOT CONVERGED; M1, m2, m3 folded, m4 FILED; THRASHING ARMED

REVIEW GAP: codex — alternation (round 3 is Claude's half; the round cap closes the review here).

```yaml
round: 3
fixes_nontrivial: true
subject: 617-bind-ci
halves:
  codex: gap
  claude: ran
findings:
  - {id: CM1, severity: Major, aim: deliverable, fix_induced: false, component: contract-parser, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: deliverable, fix_induced: true, component: contract-parser, disposition: fixed}
  - {id: Cm3, severity: Minor, aim: deliverable, fix_induced: true, component: contract-parser, disposition: fixed}
  - {id: Cm4, severity: Minor, aim: deliverable, fix_induced: false, component: shard-count, disposition: filed}
```

Claude on `a2c28a43` (49/49, 37/37 re-run by the reviewer).

- **CM1** the reassignment check caught only `V=`. `((V++))`, `let V++`, `V+=1`, `read V` and `unset V` passed. Fixed by
  turning it into an ALLOW-list: in the writing step, the index name may appear only as `$V` or `${V`, or as its own `V:`
  key. Any other mention RAISES. The list of spellings stops growing.
- **Cm2** (caused by the r2 XM1 fix) `echo "SHARD_INDEX=$SHARD_INDEX"` was a false red. Under the allow-list it is still
  red, and that is deliberate: the case is named in the self-test, and the error message says to write the value as `$V`.
  Writing it that way, with `echo "${SHARD_INDEX}"`, passes.
- **Cm3** (caused by the r1 Cm3 fix) a `- ` line inside the script moved the step start. Fixed: the step's own `- ` line
  is the nearest one indented LESS than the write.
- **Cm4** `shard_count` ignores a second matrix axis or `include:`. This was there before the change, so it is FILED in
  backlog #617.

After: 52/52; mutation slice 39/39, each killed by its named case (pin 37 → 39).
THRASHING check: r2 had one fix-induced finding (Xm3) and r3 has two (Cm2, Cm3), all in contract-parser. Two consecutive
rounds → **armed**. Phase 6 is FILED as backlog #629, not run tonight (usage 97%). Its question is whether #619 R1
(structured per-shard records) retires this contract.

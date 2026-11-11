# Round 1 — `anchor-precheck` — coordinator — ✅ CONVERGED (both halves); three Lows

```yaml
round: 1
fixes_nontrivial: false
subject: anchor-precheck
halves:
  codex: ran
  claude: ran
findings:
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: anchor-precheck, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: false, component: anchor-precheck, disposition: declined}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

`X` = Codex: CONVERGED, no findings — differential probes of `anchor_problems` against `run_mutations` agreed on
sequential, overlapping, empty and CRLF edits; both shards and `--only` refused an orphan before staging; the
re-aimed shortfall world reaches the late path. `C` = Claude: CONVERGED with three Lows.

- **CL1 (fixed):** the whole-manifest `--only` claim had no case — narrowing the pre-check to the `--only` targets
  passed 244/244. Now a case and a manifest entry; the narrowing mutant reddens exactly that case.
- **CL2 (declined):** the `break` after a refusal survives deletion; the cost is a second message for an entry
  already refused, never a false pass.
- **CL3 (fixed):** backlog #252 read `✅` while its own falsifier — an `expect` naming no case — still holds. It is
  🟠 again, marked PARTLY (anchor half), the `expect` half pointed at backlog #208.

The fold adds one case and one mutation and touches no production line; a Codex confirmation round follows.

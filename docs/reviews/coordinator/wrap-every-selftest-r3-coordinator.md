# Round 3 — `wrap-every-selftest` — coordinator — ⟳ NOT CONVERGED (Codex); THRASHING → architecture review; SPLIT

REVIEW GAP: claude — the Claude half (spawned 01:31, time-boxed to 60 minutes with a draft due at 20) filed nothing by
its 01:51 draft deadline or a 02:10 hard cutoff, and was stopped — the second Claude half on this PR to run long without
filing (round 1's ran 2h32m). The Codex half is comprehensive and executed.

```yaml
round: 3
fixes_nontrivial: true
subject: wrap-every-selftest
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: rule-5, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: rule-5, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: rule-5, disposition: deferred}
  - {id: Xm4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Codex on `736e9b10`. **X1** a launch taken only when `--self-test` is in `sys.argv` (or `CI=true`, the real HOME, the real
module name) — the child samples one context, so the branch is live but untaken; **X2** `sitecustomize` via an inherited
`PYTHONPATH` vetoes the hook, and `.pth`/`sitecustomize` launch before it — fix measured: `-I -S`, 84/84 still pass;
**X3** native `system()` through `ctypes`/`dlsym` and CFFI emit no audit event; **Xm4** the published guarantees exceed
the measurement. **Held:** 130/130 and 88/88; 84 files observed with no launch; all 28 fixed probes refused; 48/48 and
42/42 mutations; 2,354 real; fork, multiprocessing, `_posixsubprocess`, atexit and non-daemon threads refused; early
exit and timeout → CANNOT CHECK; `check-ci-watched` runs identically at run time.

**THRASHING — YES** (round 2 fix-induced by round 1, round 3 by round 2, one component). Convened:
[`architecture-review-2026-10-28-import-time-launch.md`](../architecture-review-2026-10-28-import-time-launch.md).
**Route: SPLIT** — X1 closed by a static backstop for direct module-level launches (inside a module-level `if` too),
X2 by `-I -S`, Xm4 by bounding the claim; X3 (native calls) and enforcement outside the interpreter DEFERRED to #380.

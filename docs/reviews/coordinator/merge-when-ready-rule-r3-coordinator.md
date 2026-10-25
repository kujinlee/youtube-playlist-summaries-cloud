# Round 3 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (3 Medium, 1 Low) — BET LOST, SPLIT

```yaml
round: 3
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: path-identity, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: path-identity, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: true, component: path-identity, disposition: fixed}
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: true, component: path-identity, disposition: fixed}
```

REVIEW GAP: claude — round 3 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `8a1b6b9c`, run against REAL git diffs in a scratch repository. It re-applied all
45 mutations over a green control (each killed via its named case) and reproduced 8 of 40.

**The redesign bet LOST, and every finding is about how a file is NAMED, none about the detectors.** So the
route is SPLIT (decision log, written before round 4): the detector logic is held as is; `path-identity`
continues. 16 tracked files in this repo have a space or non-ASCII byte in their path, so XM1 is not hypothetical.

Dispositions:
- **XM1 FIXED:** `_unquote()` decodes git's C-quoting (octal UTF-8 bytes, `\"`, `\\`); `_side()` cuts the tab git
  appends after an unquoted path containing a space, then drops `a/`/`b/`. The `diff --git` header accepts quoted halves.
- **XM2 FIXED:** `deleted file mode` sets the new path to None and `new file mode` the old one, so a binary
  deletion (no `+++ /dev/null`) is a deletion.
- **XM3 FIXED:** a scope exit compares the gate's ROLE (code, caller, or both) across the rename, not "some
  gate" — a workflow renamed to `scripts/check-disabled.py` is an exit; a check renamed to a check is not.
- **XL1 FIXED:** `copy from`/`copy to` mark a copy, and a copy never exits (its source still runs).

Eight cases, each header copied from a real `git diff -M -C --find-copies-harder` run in a scratch repository;
two anchors rebound, five mutations added (45 -> 50), scoped sweep 50/50 each by its named case. Replay 8 of 40.

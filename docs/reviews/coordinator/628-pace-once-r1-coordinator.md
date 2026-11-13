# Round 1 — `628-pace-once` (backlog #628) — coordinator — ⟳ NOT CONVERGED; all folded or filed

```yaml
round: 1
fixes_nontrivial: true
subject: 628-pace-once
halves:
  codex: ran
  claude: ran
findings:
  - {id: XC1, severity: Major, aim: deliverable, fix_induced: false, component: prompt-dedup, disposition: fixed}
  - {id: XC2, severity: Minor, aim: deliverable, fix_induced: false, component: prompt-dedup, disposition: fixed}
  - {id: CM1, severity: Major, aim: deliverable, fix_induced: false, component: prompt-dedup, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: deliverable, fix_induced: false, component: prompt-dedup, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: prose, fix_induced: false, component: docstring, disposition: fixed}
  - {id: Cm3, severity: Minor, aim: prose, fix_induced: false, component: docstring, disposition: fixed}
```

Reviewed `ff8706eb` (both halves). Both ran the self-test (413/413) and applied the new mutations by hand.

- **XC1 / Cm1** (same defect) WARN → OK / REFUSE / stale → the same WARN was silenced: nothing in between rewrote the
  state line. Fixed in `28b71bb2`: every non-deduplicated prompt records `seen:<verdict>`. Case + mutation.
- **XC2** a crafted session id `"a warn:<hash>"` matched session `a`'s WARN record. Fixed: the separator is a tab, which
  `session_of` now refuses. Case + mutation.
- **CM1** a WARN carrying "treat it as NOT RUN" (unknown band, unreadable five-hour window) was deduplicated, against
  the PR's own claim. Fixed: the phrase is one constant `NOT_RUN_MARK`, used by both messages and by the dedup test,
  which skips any WARN containing it. Case + mutation; the earlier #628 cases now run WITH a meter, so their WARN is
  the deduplicated kind (without one, the REFUSE mutation survived — found by hand).
- **Cm2** a WARN given before `/compact` is not repeated after it (same session id). Stated as a bound in the docstring.
- **Cm3** "whole percent" was wrong (`pct()` is 0.1%, trend and days-left move too) and the ~160-token figure is not
  measured. Comments corrected; two sessions taking turns hear every notice — stated as a bound.

Seven existing mutation anchors were orphaned by the folds; each was re-bound and applied by hand (each red).
416/416 cases; mutations 202 (pin 196 → 202). The full slice (51 min locally) runs on CI.

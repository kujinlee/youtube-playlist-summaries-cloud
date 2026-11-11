# Round 1 — `fixture-git-isolation` — coordinator — ⟳ NOT CONVERGED (both halves); REDESIGN

```yaml
round: 1
fixes_nontrivial: true
subject: fixture-git-isolation
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: High, aim: deliverable, fix_induced: false, component: exemptions, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: exemptions, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Xm5, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: CB1, severity: High, aim: deliverable, fix_induced: false, component: exemptions, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: fixtures, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm1, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: helper, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `1003add0`. **Both: the 8 migrated fixtures leave a victim `GIT_DIR` byte-identical, the
guard refuses exactly those 8 on master's tree, and all 23 manifest mutations are real and attributed.**

Duplicates: XM1 = CB1 (codex-review's exemption is false: `unredirected()` keeps GIT_INDEX_FILE, GIT_OBJECT_DIRECTORY and
GIT_CONFIG_*, so the victim's index and objects change and the caller's hooks run in fixture repos). XM3 + XM4 = CM2 + Cm1
(the guard accepts an env that merely CONTAINS a helper call, and one isolated launch hides os.system, variable argv,
wrappers and non-test-named helpers). Xm5 = Cm2 (any positional "init" marks a builder).

**Route: REDESIGN, skipping ACCRETE.** Every guard finding has ONE cause: the guard asks whether the helper is MENTIONED,
not whether the environment that reaches git is isolated. Accreting a case per bypass shape invites round 2's next shape.
CM1 (the caller's fsmonitor runs 8/6/182 times under green suites, through production readers that inherit os.environ)
cannot be closed by per-call `env=` at all. The redesign makes isolation a property of the PROCESS for the self-test's
duration — a `fixture_git.isolated()` context that swaps os.environ — so every child, whatever its launch shape, inherits
it. The guard then checks one closed shape: the self-test entry runs inside it.

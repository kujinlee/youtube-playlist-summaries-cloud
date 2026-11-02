# Round 2 — `diff-coverage-zeros` — coordinator — ⟳ NOT CONVERGED; the ACCRETE bet LOST → REDESIGN

```yaml
round: 2
fixes_nontrivial: true
subject: diff-coverage-zeros
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: true, component: manifests, disposition: fixed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: true, component: environment, disposition: fixed}
  - {id: XP3, severity: Low, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: XP4, severity: Low, aim: deliverable, fix_induced: false, component: attributes, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `fc4a691c`, git 2.49. HELD: all five r1 working-tree attacks; the CR-forged header; a target present at
HEAD but not in the working tree (WARN) and the reverse (CANNOT RUN); a submodule; space/unicode/tab names; detached HEAD;
unborn HEAD (CANNOT RUN); non-UTF-8 stderr; 5,000 extra scripts in ~1.6 s; the whole suite under a victim `GIT_DIR` left
it byte-identical; 57/57; 34/34 mutations real.

- **XP3 (fixed) — the bet's named failure:** "main() over an unknown base exits 2" passed in a directory with no repository
  at all. It now runs in a real repository and asserts the base is the reason.
- **XP1 (fixed):** a HEAD symlink manifest whose LINK TEXT is valid JSON was read as a manifest — a clean zero. The snapshot
  now refuses any manifest entry that is not a regular blob (`100644`/`100755`): symlink and submodule are CANNOT RUN.
- **XP2 (fixed):** command-scope config (`GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n`) reached the fixtures — a failing hook crashed
  the suite. **REDESIGN:** the environment is CONSTRUCTED from an allow-list, never filtered; no `GIT_*` passes, in the tool
  or the fixtures, and the fixtures build theirs at call time.
- **XP4 (fixed):** an uncommitted `.gitattributes` changed what is measured; every call passes `--attr-source=HEAD`.
- ⚠ **Bound, stated:** the manifest LOADER is code read from the working tree (`_plan_code(root)`), like the checker itself.

The fold's own first attempt left a case passing ambiently — the fixture environment was computed BEFORE the case set
`GIT_CONFIG_COUNT`, so the case tested nothing; the sweep showed it (the mutation was caught by a different case), and
the environment is now built at call time with its own mutation. Route REDESIGN (decision-log row before round 3).
61 cases; 37 mutations, each killed by its named case.

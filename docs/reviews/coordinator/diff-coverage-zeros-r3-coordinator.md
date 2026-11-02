# Round 3 — `diff-coverage-zeros` — coordinator — ⟳ NOT CONVERGED; DEFER (SPLIT skipped, reason recorded): filed, merge on READY

```yaml
round: 3
fixes_nontrivial: false
subject: diff-coverage-zeros
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: true, component: attributes, disposition: filed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: true, component: manifests, disposition: filed}
  - {id: XP3, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 3 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `e3d23783`, git 2.49 (and 2.39.5 / 2.40.0 built for the version check). HELD: 61/61; 37/37 mutations
real and attributed; the suite outside any repository; under a victim `GIT_DIR` plus command-scope config (victim hashes
unchanged); every r1 and r2 attack; mode `100755` manifests accepted; deeper manifests ignored, matching the loader;
5,000 extra scripts in ~2.2 s; the allow-list environment drops nothing git needs for these reads.

- **XP1 (FILED, backlog #378):** `--attr-source=HEAD` replaces only the in-tree `.gitattributes`; `.git/info/attributes`
  and `core.attributesFile` (local or via HOME) still apply — each turned a WARN into NOT CHECKED, never into "every one
  is edited".
- **XP2 (FILED, backlog #378):** a DIRECTORY `scripts/mutations/h.json/` is omitted from the snapshot (`ls-tree -r`
  lists no tree entries), where the working-tree loader raises — a partial manifest set.
- **XP3 (fixed, prose):** git **2.41**, not 2.40 (Codex built both and both refuse the option); the attribute claim is
  narrowed to the in-tree `.gitattributes` in the docstring comment, backlog #371, the dashboard and the PR body.

**Route DEFER, skipping SPLIT, with the reason in the decision-log row:** the remaining holes are the unstable half, both
fail toward NOT CHECKED or an omission, and the tool is local and warn-only. PR #415 merges on READY after a
merge-confirmation round. 61 cases; 37 mutations.

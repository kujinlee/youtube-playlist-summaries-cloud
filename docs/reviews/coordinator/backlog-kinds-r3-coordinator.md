# Round 3 — `backlog-kinds` (PR #442, backlog #394, backlog #395) — coordinator — NOT CONVERGED (Claude); the route moves to SPLIT

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: backlog-kinds
halves:
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  claude: ran
findings:
  - {id: F1, severity: Medium, aim: deliverable, fix_induced: false, component: namespace-gate, disposition: filed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: namespace-exemption, disposition: fixed}
  - {id: F3, severity: Low, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: namespace-gate, disposition: filed}
```

The Claude half reviewed `e24da6df` with real-git worlds. **The redesign held** against:
- header impersonation and renames;
- a row moved within the file, edited or not;
- two markers, a tab inside a marker, and raw CRLF;
- a merge commit as head, and the base given as a sha, tag or branch name.

The real repo gives 0 violations, and the scratch leak scan works with the new API.

**The bet is refuted on two diff shapes:**
- **F1 (Medium, predates this PR, the GATE not the exemption):** a path git renders as BINARY (a NUL byte, `-diff`, or `*.md binary`) has no hunk, so the whole gate prints OK over a new bare `#N`.
- **F4 (Low, predates this PR):** a checked path replaced by a symlink to an out-of-scope file.
- **F2 (Low, fix-induced):** under `.gitattributes text eol=crlf`, the head is read as raw bytes but the diff is clean-filtered, so a kept row ends in `\r`, fails to cancel, and lets a marked duplicate through.
- **F3 (Low):** the `split("\n")` → `splitlines()` mutant survives.

**SPLIT.** F2 and F3 belong to this PR's exemption, so they are FOLDED:
- F2: count the head's unmarked copies through the same clean-filtered path;
- F3: a real-git case and a manifest entry.

F1 and F4 are gaps in the reference gate itself that predate this PR, so they are FILED as one backlog row: run diffs with `--text --no-textconv`, report "changed but no hunk" as CANNOT RUN, and treat a symlinked checked path as a violation.

# Round 6 — `retire-work-lines` (PR #434, backlog #389) — coordinator — CONVERGED (Codex), the Python 3.12 fix

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 6
fixes_nontrivial: false
subject: retire-work-lines
halves:
  codex: ran
  claude: gap
findings: []
```

After round 5 converged, CI (Python 3.12) went red: `Path.resolve()` raises RuntimeError on a symlink loop in 3.12 and
OSError in 3.13+, and the dev machine runs 3.14 — so the suite passed locally and failed in CI (reproduced in a
python:3.12-slim container from a `git archive`: 226/227). Fixed in `29db3aeb` with one helper. This round, scoped to that
diff: no findings — every serve/index `resolve()` goes through `resolve_or_none()`; a loop reaches the same
refused/403/unlisted state on 3.12 and 3.14; the patched-RuntimeError case is a real falsifier; 228/228 on 3.12;
62/62 mutations; leak scan 0. A wider 3.12 container run showed four further failures in gen-work-lines and
check-banner-armed that ALSO fail on origin/master in the same container: the container runs as root, which ignores
`chmod 000`, so the "unreadable directory" cases cannot pass there — an environment artefact, not a defect.

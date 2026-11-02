# Round 7 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (2 High, adversarial-only) — SPLIT + STOP RULE

```yaml
round: 7
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: false, component: hunk-ownership, disposition: fixed}
  - {id: XH2, severity: High, aim: deliverable, fix_induced: false, component: hunk-ownership, disposition: fixed}
```

REVIEW GAP: claude — round 7 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `5762d473`, real git. 180/180; 62/62 mutations via named cases; replay 8 of 40 (313
calls); the r6 rename-plus-directory shape HOLDs under all four diff algorithms, both indent-heuristic settings
and `core.autocrlf=true`; exit precedence 3/1/2 correct.

**XH1** two paths differing only by CR vs LF: text-mode reads translate CR, both tree entries took one key,
and the unchanged file's blob stood in for the changed gate's -> READY. **XH2** a gate that is a SYMLINK to
`../tools/gate.py`: the target changed alone, nothing tied it to the gate -> READY. Both need input an honest
change does not contain; neither is fix-induced.

The owner chose (card, A): fix both, and **pre-commit a stop rule** before round 8 — if round 8 finds only
shapes an honest change cannot contain, they are written into the script's threat-model bound and the loop
stops without a fold. Decision log: the hunk-ownership redesign is scored LOST; a SPLIT holds the blob
diffing and continues the two edges, with the stop rule in its prediction.

Dispositions — FIXED: `git_reader(run)` is the one way git is read, shared by `main()` and the real-git world:
BYTES (`text=False`) decoded by `as_text` (`surrogateescape`, no newline translation), and a failed command
raises (CANNOT RUN). A gate symlink (mode 120000, under the gate patterns) whose normalised target changed gets
the target's blob diff filed UNDER THE GATE'S NAME, so the detectors judge it as the gate; one level only,
stated. The world adds both shapes. 185 cases; mutations 62 -> 68 (six added), 68/68; replay 8 of 40.

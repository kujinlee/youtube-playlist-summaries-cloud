# Round 3 — `merge-ready-thrash-hold` — coordinator — NOT CONVERGED; C1–C5 fixed, C6 filed

Claude reviewed 7f2286d4 (the round-2 fold of backlog #680 part 2): `docs/reviews/claude/merge-ready-thrash-hold-r3-claude.md`
(C1, C2 MAJOR; C3–C6 MINOR; NOT CONVERGED). Rounds 2+ alternate, so the Codex half did not run this round.

REVIEW GAP: codex — alternation

Severity below uses the header grammar's words: MAJOR is `High`, MINOR is `Low`.

**Why this fold is structural.** r1 X1 (an inline value), r2 X1 (a second key) and r3 C1/C2 (an unindented
sequence, `[]` with items under it, a re-spelled key) are one class. The thrash gate inferred "clean" from the
ABSENCE of parsed items, so every shape the reader did not parse read as a clean round. Patching one spelling per
round does not close that class. This fold makes clean a POSITIVE form: one shape is clean, and every other shape
must prove that it was read. All of it lives in the thrash gate. `parse_round` exposes new fields
(`findings_rest`, `findings_dashes`, `findings_fields`, and `findings_keys` now normalised), and `parse_header`
strips them. Over every `docs/reviews/**/*.md` in the worktree (2997 files, 559 of which parse), `parse_header`'s
output is identical to master's: 0 differences.

- **C1. A clean round was inferred from zero parsed items.** `findings:` followed by an unindented `- {…}` (PyYAML's
  default dump style), an unindented block item, or `findings: []` with items under it, all read as clean.
  The fix: a round is clean only if its one findings key's value is literally `[]` (a `# comment` is allowed) AND no
  non-blank, non-comment line follows before the next column-0 key. Otherwise the parsed item count must equal the
  number of lines under the key that begin, after indentation, with `- `. A mismatch, or a bare key with no item,
  makes the round unreadable, which is a cannot-judge HOLD under the r1 C3 rule.
  **fix_induced: false.** Confirmed by the coordinator: at 3cc76714 (before the r2 fold), through `thrash_gate` over
  real git, J and A beside a fix-induced r1 return `[]` (no HOLD); the indented control arms.
- **C2. The key count read one spelling of the key.** `findings :`, `"findings":` and `'findings':` are the same
  YAML key. `parse_round` now finds the key by its normalised name (quotes stripped, whitespace before the colon
  removed) and counts every column-0 key that normalises to `findings`. A count other than 1 is unreadable.
  **fix_induced: false.** Confirmed by the coordinator at 3cc76714: P (a spaced second key) and Q (a quoted second
  key) return `[]`.
- **C3. A field-name variant was silently not the field.** `"fix_induced"`, `fix-induced` and a `<<` merge key were
  not read. Now a finding field that normalises (quotes stripped, `-`→`_`, lowercased) to `fix_induced` or
  `component` but is not spelled exactly so, or any key starting with `<<`, is unreadable. **fix_induced: false**
  (the reviewer reproduced it at 3cc76714).
- **C4. A trailing ` #` comment was part of the value.** `component: det4  # the detector` read as a different
  component from `det4`. In the thrash gate only, a `component` or `fix_induced` value containing ` #` is
  unreadable. `_scalarise` is unchanged. **fix_induced: false** (the reviewer reproduced it at 3cc76714).
- **C5. A rename, a copy or an empty file under the review path cleared the HOLD.** An architecture review now clears
  the HOLD only as a changed-file entry with status `A` or `M` whose blob at HEAD is non-empty (`git cat-file -s`).
  `R` and `C` entries clear nothing. `thrash_holds` now takes this `counted` set in place of `head_paths`.
  ⚠ **BOUND, stated in `thrash_holds`' docstring and in backlog row 680:** by this rule, a one-character edit to an
  OLD architecture review still clears the HOLD. **fix_induced: false** (the reviewer reproduced it at 3cc76714).
- **C6. False HOLD: editing an old coordinator doc of an already-reviewed subject HOLDs.** Filed as **backlog #695**:
  42 of 182 subjects at HEAD would HOLD on such an edit, and 1 of 174 first-parent master commits since 09-01 would
  have hit it. The fix candidates are in the row. **fix_induced: false** (this is the build's design).

**Corpus cost of each new clause**, over the 783 coordinator docs at HEAD: findings-key count ≠ 1: 1
(`hse-slice-d-r4`, already unreadable before this fold, because it has no `findings:` key). Normalised key count
differing from the exact count: 0. `[]` with lines under it: 0. Bare-key item-count mismatch: 0. Bare key with
zero items: 0. Near-miss or `<<` field: 0. ` #` in a judged value: 0. (63 docs raise in `parse_round` and 39 carry
an inline value other than `[]`; both predate this fold.) Per subject, `thrash_gate` before (69d8ecbf) and after:
140 none, 25 armed, 17 cannot-judge; 0 changed.

Replay over the 41 master commits that touched coordinator docs: 8 HOLDs (5 armed, 3 cannot-judge), 0 CANNOT RUN
before this fold, and the same after it. 11d0568d (PR #600) still HOLDs. Self-tests: check-merge-ready 448 → 467,
check-review-decision 123 → 130. Mutations: check-merge-ready 207 → 214 (8 added, 1 retired, 3 re-bound),
check-review-decision 32 → 33 (1 added, 1 re-bound). Each mutation was verified by hand in a full clone through
`parse_fail_names`, with an exact `expect` match.

```yaml
round: 3
fixes_nontrivial: true
subject: merge-ready-thrash-hold
halves:
  claude: ran
  codex: gap
findings:
  - id: C1
    severity: High
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: fixed
  - id: C2
    severity: High
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: fixed
  - id: C3
    severity: Low
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: fixed
  - id: C4
    severity: Low
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: fixed
  - id: C5
    severity: Low
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: fixed
  - id: C6
    severity: Low
    aim: deliverable
    fix_induced: false
    component: check-merge-ready-thrash-gate
    disposition: filed
```

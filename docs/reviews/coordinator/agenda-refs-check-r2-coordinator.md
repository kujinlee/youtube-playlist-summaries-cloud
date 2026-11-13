# Round 2 — `agenda-refs-check` (backlog #504) — coordinator — fold

REVIEW GAP: claude — alternation (round 1 ran both halves; round 2 is the Codex half). Codex: `docs/reviews/codex/agenda-refs-check-r2-codex.md`, on `8516de43`.

```yaml
round: 2
fixes_nontrivial: true
subject: agenda-refs-check
halves:
  codex: ran
  claude: gap
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: true, component: blank-repair, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: ref-kinds, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: blank-repair, disposition: fixed}
```

Codex: 0 BLOCKER, 1 MAJOR, 2 MINOR — NOT CONVERGED. All three fixed. Codex's inputs are used verbatim as the failing cases,
and each case was run red before the fix (406/409).

| Finding | Fix | Case that fails without it |
|---|---|---|
| F1 MAJOR — the r1 fold's repair read the log in TEXT mode (CRLF translated to LF) and truncated at that shorter length, cutting the tick's `}` | `_locked` reads BYTES. A new `_blank_tail_cut` cuts only what is provably not data: the blank lines AFTER the last record's own line ending (`\n` or `\r\n`, kept), or a log of nothing but blanks. Blanks on the last record's own line are never cut. A CRLF log is byte-identical except for the appended record | "⛔ a CRLF log is kept byte for byte ahead of the appended record…" (Codex's bytes verbatim), "…blank lines after a CRLF record are cut after its own CRLF, which is kept" |
| F2 MINOR — `REF_KINDS` comes from splitting the regex TEXT, so a group, an escaped `\|` or a flag drifts | The derivation stays as it is (making it exact would mean changing `page_markup.KEY_REF`'s anchored line). A second case checks from the other side: every `<word> #7` the grammar ACCEPTS, over each kind's case variants plus every word in the pattern text, must name a known kind | "⛔ no `<word> #7` the step grammar accepts names a kind outside the known ref kinds…". Measured on temp copies of `page_markup.KEY_REF`: `re.I` → this case red (406 self-tests had passed with it); `foo\|bar` → the r1 kinds case red; `(?:PR)` → the self-test aborts at an unrelated earlier case (IndexError, rc 1), so it fails closed but neither kinds case is reached |
| F3 MINOR — a refused, unfinished record lost its trailing spaces, because the repair cut before validation | The log is validated (`write(agendas(_agenda_records(…)))`) BEFORE any truncate. Both inputs are refused and the log is left unchanged: Codex's (no newline, so nothing is cut either way) and one with a blank tail the repair WOULD cut, which is what tests the order | "⛔ a log recording refuses as malformed is left unchanged — nothing is cut before it is validated" |

**Mutations** (`scripts/mutations/goal-tree.json`, each on a temp copy, anchors matched exactly once): 4 added — blanks on the last
record's own line are cut; a CR is taken for data when the tail is measured; the blank tail is cut before validation; the grammar is
read case-insensitively. 4 re-anchored onto the new code: lone-newline kept, whitespace-only not emptied, trailing blanks kept, and
backlog #499 r3 Codex M2's "no final newline is appended to on the same line", which the rewrite had orphaned. Manifest 312 = pin
(`check-plan-code.py`). The first new mutation's anchor was lengthened (it carries the line's comment), because
`check-plan-code.py` refuses an entry that repeats an earlier entry's anchor. All 15 #504 / M2 mutations KILLED by their named
case. Self-test 410/410 (declared 410).

`fix_induced`: F1 and F3 are both caused by the r1 fold's truncation (the same component, `blank-repair`). F2 is not. The drift it
describes existed when the kinds were a literal tuple; the r1 fold narrowed it but did not cause it.

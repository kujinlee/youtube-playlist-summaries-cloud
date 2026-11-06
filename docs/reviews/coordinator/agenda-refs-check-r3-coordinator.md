# Round 3 — `agenda-refs-check` (backlog #504) — coordinator — fold

REVIEW GAP: codex — alternation (round 1 ran both halves, round 2 the Codex half; round 3 is the Claude half). Claude: `docs/reviews/claude/agenda-refs-check-r3-claude.md`, on `7adf04ad`.

```yaml
round: 3
fixes_nontrivial: true
subject: agenda-refs-check
halves:
  codex: gap
  claude: ran
findings:
  - {id: N1, severity: Low, aim: deliverable, fix_induced: true, component: blank-repair, disposition: fixed}
  - {id: N2, severity: Low, aim: deliverable, fix_induced: true, component: blank-repair, disposition: fixed}
  - {id: N3, severity: Low, aim: deliverable, fix_induced: false, component: agenda-decode, disposition: filed}
```

Claude: 0 BLOCKER, 0 MAJOR, 3 MINOR — CONVERGED. N1 and N2 fixed, N3 filed as backlog #529. The reviewer's inputs are used
verbatim as the cases, and both cases were run red before the fix (410/412, every input red).

| Finding | Fix | Case that fails without it |
|---|---|---|
| N1 — the writers split on `\n` only while the reader's `read_text()` also ended a line at a lone `\r`: a lone-`\r` log read as 2 records and was refused on write | ONE line model, `_EOL` (`\r\n`, a lone `\r`, `\n` — what universal newlines read), used by `_agenda_records` for the reader and both writers, and by the blank repair over bytes (`_EOL_B`, derived from `_EOL.pattern`). The reader now decodes the bytes as the writers do. Chosen over "both refuse": it keeps every log the page reads today readable, and a valid JSON record cannot hold a raw `\r`, so splitting at one never splits a record | "⛔ a log whose lines end in a lone CR is read AND written: the writers' line model is the reader's" |
| N2 — the cut counted only space/tab/`\r`/`\n` as blank; the reader skips any line `str.strip()` empties | ONE predicate, `_blank(line) = not line.strip()`, used by the reader to skip and by `_blank_tail_cut` to decide what is cut; the cut walks lines in the reader's model and keeps through the last non-blank line's own ending. Round 2's byte preservation stands: the record's line and its ending are kept byte for byte, and both r2 CRLF cases are green | "⛔ a blank tail the reader skips is cut, whatever its whitespace or line ending…" (`\n\x0c`, `\n\x0b\n`, `\n`+NBSP, `\r\r\n`, `\r   `, and the whole log `\x0c\n`) |
| N3 — invalid UTF-8 raises `UnicodeDecodeError`, not `Malformed` (pre-existing, at `origin/master` too) | Not fixed: filed as backlog #529 | — |

**Mutations** (`scripts/mutations/goal-tree.json`, each on a temp copy, every anchor matched exactly once): 2 added — a lone CR
does not end a line (N1, killed by the N1 case); the cut's blank is narrower than the reader's (N2, killed by the N2 case). 4
re-anchored onto the rewritten `_blank_tail_cut`: lone-newline kept, trailing blanks kept, blanks on the record's own line cut, and
"a CR is taken for data" (now: the cut's line model sees only `\n`; its expected case moved to the N2 case). A first re-anchoring of
that last one — splitting a CRLF into two endings — SURVIVED and is equivalent: the cut then keeps `A\r`, and the newline repair
re-adds the `\n` it removed, so the bytes are identical. It was replaced, not kept. All 8 blank-repair / M2 mutations rc 1 and
killed by their named case. Manifest 314 = pin (`check-plan-code.py`). Self-test 412/412 (declared 412).

The reviewer's probe (`/Users/kujinlee/.claude-tmp/r3/probe.py`) re-run on the fold: every tail input leaves no blank line, the
lone-`\r` log records (its tick, correctly, is refused as "already ticked"); only the mid-file blank remains, by design (only the
tail is cut), and the invalid-UTF-8 input, filed.

`fix_induced`: N1 and N2 are both residue of round 2's F1 fix (`blank-repair`, which also carried r2's F1 and F3) — so this
component has fix-induced findings in two consecutive rounds. N3 is not fix-induced.

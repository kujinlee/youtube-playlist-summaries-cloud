# Round 1 — `idle-stop-750` (PR #652, backlog #750 step 1) — coordinator — both NOT CONVERGED; all folded

Both halves reviewed `593dd524`. They agree on the class: the decision log could change what the hook does. The log must never do that, because it is evidence about the guard, not a signal the guard reads.

| id | from | sev | finding | disposition |
|---|---|---|---|---|
| W1 | codex B + claude m3 | BLOCKER/MINOR | A FIFO at the log path makes `open(…, "a")` block, so the hook never returns its verdict. At the 10 s timeout, a block becomes an allow. | **Fixed:** open with `O_NONBLOCK` (a FIFO with no reader fails at once), and write only to a REGULAR file (`fstat`). Cases: the FIFO, and a link to /dev/null. |
| W2 | codex M + claude M1 | MAJOR | A lone surrogate in the payload raises `UnicodeEncodeError`, which is not an `OSError`. The BLOCK becomes exit 1 with a traceback. Reproduced by both halves. | **Fixed:** `ensure_ascii=True` makes the line ASCII, and the handler also catches `ValueError`. Case: the line is still written, and the hook exits 2. |
| W3 | codex M + claude M2 | MAJOR | `main` reused `why`, so the NOT CHECKED line printed `{'rule': 'unreadable'}` instead of the parser's reason. | **Fixed:** the parser's reason is kept in its own variable, `unread`. Case: the JSONDecodeError text is present and the rule is not. |
| W4 | codex M | MAJOR | A malformed `gh` answer could put an arbitrary object into the log as a PR number. Task descriptions can contain secrets. | **Fixed:** a PR number that is not an int is logged as a placeholder, at most 50 are kept, and the file is created 0600. **Bound, not fixed:** up to 80 characters of each live task's description are logged. That text already sits in full in the session transcript, under the same `~/.claude`. Stated in the docstring. |
| W5 | codex M + claude n5 | MAJOR/NIT | Two concurrent stops can race the size check against the rotation, and lose the rotated `.1` or a line. | **Fixed:** the rotation and the append run under one `flock`, and rotation happens only if the locked file is still the file at the path (`samestat`). **No case:** the race needs two processes interleaved at one instruction. The fix is argued, not shown. |
| W6 | claude m4 | MINOR | No case checks 5 of the 8 rule names. | **Fixed:** one case drives each of those five rules through `main` and reads back the logged names, plus a mutation that logs `usage` under the wrong name. |
| W7 | codex N | NIT | The docstring said 61 cases. | **Fixed:** it says 72. |

The two halves agree on everything else: the logged (a) entries come from the same `_live` function as the verdict, nothing reads the log, the round-0 mutants all die, and the `decide_why.*` exemption reasons are true.

Mutations: 65 → 72, one for each new guard.

```yaml
round: 1
fixes_nontrivial: true
subject: idle-stop-750
halves:
  codex: ran
  claude: ran
findings:
  - {id: W1, severity: BLOCKER, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
  - {id: W2, severity: MAJOR, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
  - {id: W3, severity: MAJOR, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
  - {id: W4, severity: MAJOR, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
  - {id: W5, severity: MAJOR, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
  - {id: W6, severity: MINOR, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
  - {id: W7, severity: NIT, aim: deliverable, fix_induced: false, component: check-idle-stop, disposition: fixed}
```

Reviews: `docs/reviews/codex/idle-stop-750-r1-codex.md`, `docs/reviews/claude/idle-stop-750-r1-claude.md`.

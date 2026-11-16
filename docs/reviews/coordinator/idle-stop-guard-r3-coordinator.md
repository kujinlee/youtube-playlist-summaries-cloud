# Round 3 — `idle-stop-guard` — coordinator — ⟳ NOT CONVERGED (Claude half) — Phase 6 ARMED

Claude (Opus, `docs/reviews/claude/idle-stop-guard-r3-claude.md`) reviewed `39c468cc`: 1 BLOCKER, 3 MINOR,
NOT CONVERGED. Self-test 93/93 quoted; 3,146 real stops replayed through `last_tool_asked` with no answered card
let through and no false "unreadable"; no wedge input found.

REVIEW GAP: codex — alternation (rounds 2+ run one half; Codex reviewed round 2).

```yaml
round: 3
fixes_nontrivial: true
subject: idle-stop-guard
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CB1, severity: Blocking, aim: deliverable, fix_induced: false, component: pause-exception, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: deliverable, fix_induced: true, component: ci-signal, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: deliverable, fix_induced: true, component: question-exception, disposition: fixed}
  - {id: Cm3, severity: Minor, aim: deliverable, fix_induced: false, component: question-exception, disposition: fixed}
```

## Arming condition — read by hand

`check-review-decision.py` answers CANNOT RUN on the Major/Minor vocabulary (backlog #661), so this is read by hand
from the r2 and r3 YAML:

| Component | r2 fix-induced | r3 fix-induced | Consecutive? |
|---|---|---|---|
| question-exception | XM1 (the r1 fold's AskUserQuestion exception kept an ANSWERED card) | Cm2 (the r2 fold's "last card wins" reset is unwitnessed) | **YES — armed** |
| ci-signal | none (XM4 was not fix-induced) | Cm1 | no |
| worktree-signal | XM5 | none | no |

**Phase 6 fires** on `question-exception`. CB1 (the pause marker excuses every idle stop for 24 h, and the block
message teaches the agent to create it) is in the sibling component — the guard's other ALLOW exception — so the
Phase 6 review takes BOTH exceptions in scope. Dispositions for all four findings wait for its verdict.

**Round cap:** the next round is round 4; from round 4 a non-BLOCKER is FILED (`docs/review-method.md` §0 Q4c).
CB1 is a BLOCKER and must be fixed before merge whatever Phase 6 says.

## Phase 6 verdict and dispositions

Phase 6 (Fable, `docs/reviews/architecture-review-2026-11-16-idle-stop-guard.md`, `6ce1e99a`) recommends **option D:
remove both ALLOW exceptions and the transcript reader**, so every ALLOW reads state the stopping agent did not
author. Each exception saved one refusal on its honest path (the continuation passes on `stop_hook_active` anyway),
fired on 4 of 3,147 replayed stops, and owned 26 of 99 mutations. The coordinator ADOPTS D.

| Finding | Disposition |
|---|---|
| CB1 (pause marker) | dissolved by removal — the marker is no longer read; a case pins it across a literal list of ages |
| Cm2 (last-card reset unwitnessed) | dissolved by removal — no card logic remains |
| Cm3 (unreadable transcript unexplained) | dissolved by removal — the transcript is never opened |
| Cm1 (`__typename` shape unwitnessed) | FIX — a case for a malformed `__typename` |

**Stop condition for round 4:** "an honest stop costs one refusal" and "a work signal can be forged" are FILED, not
folded. A BLOCKER in round 4 is only an announcement-only stop that exits 0 on its first attempt without forging a
work signal.

## Fold

Option D is folded on branch `idle-stop-guard`. Everything below was run in the worktree; the mutation sweep ran on
a copy of the tree, in three `--only` slices.

**What changed.** `scripts/check-idle-stop.py` no longer reads `.claude/paused` or the transcript: `_rejected`,
`last_tool_asked`, `read_tail`, `paused` and their constants are deleted, `decide()` lost its `tail` parameter, and
`main()` never opens `transcript_path`. The order is: payload not an object → NOT CHECKED; `stop_hook_active`;
`agent_id`; usage stop; signals (a), (b), (c); BLOCK. The block message names no file and no tool, only the two outs
(start the next job; or say in one line, quoting the owner, that the owner said stop or only the owner can act).
`.gitignore` lost its three `.claude/paused` lines. Backlog row 663 and the 2026-11-16 dashboard entry no longer
list the two exceptions.

**Cases, written first.** Nine statements for the review's eight cases (D5 is two). On the unchanged code the
self-test read 95/102: 7 red (D1, D2, D3, D4, both D5, D6) and 2 green by design (D7 is the Cm1 witness the old code
already satisfied; D8 pins an order the old code already had). After the change: 78/78.

| Case | What it holds | Before | After |
|---|---|---|---|
| D1 | a `.claude/paused` marker aged 0 s, 300 s, 20 h 53 m and 25 h changes nothing, through `main()` | red | green |
| D2 | a rejected question card plus a closing reply exits 2; its continuation exits 0 | red | green |
| D3 | a rejected card followed by an announcement exits 2 | red | green |
| D4 | the transcript is never opened: missing, a directory, a FIFO, unreadable, 200,000 deep, torn last line | red | green |
| D5 ×2 | the block names no `.claude/paused`, `touch`, `AskUserQuestion` or `paused`; it names both outs | red | green |
| D6 | marker, rejected card, unanswered card and hook-refused card each give the verdict of the bare payload | red | green |
| D7 | a malformed `__typename` (a list) reads as unreadable and BLOCKS naming (c); a well-formed one counts (Cm1) | green | green |
| D8 | `stop_hook_active`, `agent_id` and a usage stop each allow before `gh` is called | green | green |

**Retired: 24 cases** (all tested deleted code; 93 − 24 + 9 = 78). Names are shortened at `…`:
the rejected card → ALLOW; an ANSWERED AskUserQuestion is work to act on…; an AskUserQuestion with no result yet
keeps the exception; a card a HOOK refused…no exception; only a result for THIS card's id answers it…; a rejection
text WITHOUT is_error is an answer…; a rejection whose content is a list of text blocks…; an AskUserQuestion with no
id cannot be matched…; a human prompt as a LIST of text blocks ends the exception…; a human prompt holding a literal
U+2028…; a torn FIRST line…and a torn LAST line…are skipped; a torn line in the MIDDLE…; a record nested past the
parser's limit makes the transcript unreadable…; an AskUserQuestion BEFORE the latest human prompt does not count; a
later tool call after AskUserQuestion is the last one; a transcript record that is not an object…; the owner's pause
marker → ALLOW; a pause marker older than PAUSE_MAX_S is ignored, and said; main reads the transcript tail named by
the payload; main: a transcript record nested 200,000 deep (r2 XM3)…; read_tail keeps only the last `cap` bytes;
read_tail of a missing path is None; read_tail of a FIFO with no writer…; read_tail refuses a file that is not
regular….

**One surviving case edited, not weakened in intent:** "the block says what it saw and what to do" asserted the
tokens `start the work` and `PAUSE_FILE`; the constant is gone and the sentence changed, so it now asserts `start the
next job`. Two call sites dropped the removed `tail` argument. No other surviving case was touched.

**Mutations: 99 → 86, 0 survivors.** Retired 23 (their anchors were deleted): the pause marker is ignored; a stale
pause marker still pauses; a stale pause marker is not said; the AskUserQuestion exception is dropped; a human prompt
does not reset the last tool; the FIRST tool call is kept, not the last; a transcript record that is not an object is
read as one; main: the transcript is not read; read_tail reads from the start; read_tail opens blocking; read_tail
reads a file that is not regular; an ANSWERED card keeps the exception (r2 XM1); a result for ANY id answers the
card; a hook's refusal reads as the owner's rejection; a rejection needs no is_error; a list-form rejection is not
read; a card with no id keeps the exception; the transcript is split by splitlines again (r2 XM2); a torn MIDDLE line
is skipped; a torn FIRST or LAST line is unreadable; a RecursionError in the transcript is not caught (r2 XM3); an
unreadable transcript grants the exception; the unreadable transcript is not said. Re-bound 3 to new anchors with the
same intent (the two "a question in the prose is a question again" entries, "the block teaches ending on a
question"). Added 10: a marker read re-added to `decide()` (D1); `main()` opens the transcript, blocking and
non-blocking (D4, two entries); a rejected card excuses (D2); a rejected card plus an announcement excuses (D3); any
AskUserQuestion in the transcript excuses (D6); the old block message restored (D5); the message drops its second out
(D5); a malformed `__typename` is read past (D7, r3 Cm1); `gh` is called before the order's allows (D8). The review's
three binding mutations are the D1, D2 and D4 entries. Sweep on the copy: 22/22, 32/32, 32/32 killed and attributed;
76 s, 106 s, 115 s.

**Measurements.** Self-test wall time 2.5 s (2.53, 2.46, 2.54). Worst case through the launcher
`.claude/hooks/check-idle-stop.sh` — `gh` sleeping 30 s, a builder worktree of 400,000 old files, an empty HOME, a
FIFO as `transcript_path`, a fresh `.claude/paused` present: 4.22, 4.09, 4.09 s, exit 2 each time (round 2 measured
4.16, 4.11, 4.11 s). `scripts/sweep-costs.json` is unchanged: the priced 2.0 s control and 3.0 s per mutation were
measured here at 2.5 s and about 3.4 s on a loaded machine, a difference not attributed to this fold.

**Bounds.**
- D3 is killed only by its own mutant (the excuse gated on the word `starting` in the reply); no pre-existing mutant
  distinguishes it from D2.
- D4 witnesses "not opened" by spying on `builtins.open` and `os.open`; a read through another primitive is not seen.
- The latency figures are one machine, three runs each.
- A work signal can still be authored by the stopping agent: filed as backlog #664 (a `touch` in a builder worktree)
  and backlog #665 (the usage cache, an inference, not probed). Backlog #666 (an owner pause, a decision) and backlog
  #667 (what record a cron-fired wake leaves) are the review's other two proposed rows. None is folded.
- The roadmap was not edited for the four new rows.

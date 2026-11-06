Reviewed head: e4f812b02d048328fff5978cc7e0b5e8530aac0c

> **For the r4 fold of `agenda-refs-check` (PR #525, backlog #504).** Triggered by **THRASHING**, by the letter of
> `docs/dev-process.md` → *Phases*: `scripts/check-review-decision.py` prints `ARCHITECTURE_REVIEW — thrashing:
> 'blank-repair' carried fix-induced findings in r2 and r3`.
>
> **Verdict:** thrashing, design-caused, and **e4f812b0 already removes the class**. Keep it (option c). The r4 fold changes
> no code in `blank-repair`. **BLOCKERs: none.** Two items to FILE (§3).

# Phase 6 architecture review (narrow, triggered by thrashing): the blank repair of the agenda log in `scripts/goal-tree.py` (PR #525, backlog #504)

Scope: `_EOL`, `_EOL_B`, `_blank`, `_agenda_records`, `read_agenda_log`, `_locked`, `_blank_tail_cut`, and the two writers
`record_agenda` and `tick_agenda`. Read only. Read first: `CONTEXT.md` (*Agenda*), `docs/adr/` (no ADR covers the agenda log,
so none is re-litigated), backlog #504 and #529, the three coordinator documents, and the r1–r3 reviews. Nothing under
`.claude/plans/` was read. Measurement scripts are outside the repository, in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/arc6/`
(`probe.py`, `extra.py`, `conc.py`, `rename.py`, and `tree-*/`, which are `git archive` copies of `scripts/` at earlier heads).

## 1. Thrashing or prose floor?

**Thrashing, and design-caused. It is not a prose floor.** Each fix-induced finding is a real behavioural defect with an
input that was run. None is a wording point.

| Round | Finding | Fix-induced by | Evidence (quoted from the review) | Kind |
|---|---|---|---|---|
| r2 | F1 MAJOR | r1's whitespace strip | Codex r2: "`fh.read()` normalizes CRLF to LF, but `truncate(len(body.encode()))` uses that shortened length as an offset into the original file … truncates the tick's closing `}` before appending. Subsequent replay raises `Malformed` on line 2." | **data loss** |
| r2 | F3 MINOR | r1's whitespace strip | Codex r2: "truncation happens before validation … removes the three spaces belonging to the unfinished JSON string. The damaged input is modified despite refusal." | a refused log is modified |
| r3 | N1 MINOR | r2's byte rewrite (F1 fix) | Claude r3: "`_locked` now decodes the raw bytes and splits on `\n` only; `read_agenda_log` still uses `path.read_text()`, whose universal newlines turn a lone `\r` into a line break." A lone-`\r` log reads as 2 records and `record_agenda` raises Malformed | reader and writer disagree |
| r3 | N2 MINOR | r2's byte rewrite (F1 fix) | Claude r3: "`_blank_tail_cut` treats only `b" \t\r\n"` as blank and only `\n` as a line ending. The reader treats a line as blank when `ln.strip()` is empty." Six tails RUN, each leaves a blank line | reader and writer disagree |

r2 F2 (ref kinds) and r3 N3 (invalid UTF-8, backlog #529) are not fix-induced and not in this component.

**The cause, in one sentence: the PR gave the writer a second model of the file.** On `origin/master` the reader and the
writer used the SAME model, both by accident of the standard library. The reader did `read_text()` and then `split("\n")`. The
writer opened the log in text mode (`"a+"`) and read it. Both see universal newlines, and neither cut anything. The r1 fold
added a cut. A cut needs a byte offset, and a byte offset needs a byte model of lines and of "blank". Each fold then wrote
that model by hand, and each version was wrong in a different place:

- r1: a text-mode length used as a byte offset (F1), and the cut placed before validation (F3);
- r2: a byte model with `\n` as the only line ending and four bytes as the only blanks (N1, N2).

This is one class, "the writer and the reader each carry their own model of the file", exactly as suspected.

## 2. Can a redesign remove the class?

### The instrument

`probe.py` builds random logs from valid records (compact, and a hand-spaced one with an escaped `é`), with blank segments
drawn from **every** character for which `str.isspace()` is true (so `\x0b`, `\x0c`, `\x1c`–`\x1f`, NEL, NBSP, U+2028, U+2029,
and the others), random `\n` / `\r\n` / lone `\r` endings, stray spaces on a record's own line, and an optional missing final
newline. It runs each log through `read_agenda_log` and then `record_agenda`, and checks five properties. The measuring model
is written independently in the probe (`\r\n|\r|\n` and `str.strip()`, which is what universal newlines read). It does not
import the code under test's `_EOL` or `_blank`.

- **P1** the writer refuses exactly when the reader refuses;
- **P2** a refused log is byte-identical afterwards;
- **P3** the old records read back unchanged, and the log is still readable;
- **P4** no blank line (in the reader's model) sits between the last old record and the first new one;
- **P5** every byte up to the end of the last old record's text is preserved.

**Control: the probe finds every earlier round's defect at the head that had it** (RUN, seed 1, 3,000 logs each):

| Head | P1 disagree | P2 refused but changed | P3 unreadable after write | P4 blank left | P5 bytes lost |
|---|---:|---:|---:|---:|---:|
| `origin/master` | 0 | 0 | 0 | 1,667 | 0 |
| `8516de43` (r1 fold) | 313 | 183 | **1,062** | 0 | 255 |
| `7adf04ad` (r2 fold) | 1,056 | 0 | 0 | 746 | 0 |
| **`e4f812b0` (r3 fold, HEAD)** | **0** | **0** | **0** | **0** | **0** |

At HEAD: seed 1 × 3,000 plus seeds 2, 3 and 4 × 10,000 is **33,000 logs and 0 violations** (between 17% and 18% of them
are refused by both sides alike, for example a `\x0c` on a record's own line, which `json.loads` rejects).

Targeted inputs at HEAD (`extra.py`, RUN), each with 0 violations: an empty log; `A\r`; a NUL line (both sides refuse, file
unchanged); a BOM (both sides refuse); U+2028 and NEL inside a JSON string (not split, accepted); a whole log of `\x0c`
(emptied); Codex r2's CRLF + spaces input; `A\r\r\n`; and blank lines mid-file (kept, by design). `--self-test`: 412/412.

### (a) The writer re-serialises the whole log through the reader

**Removes:** every disagreement. The writer writes only what the reader parsed, so P1, P3 and P4 hold by construction (RUN as
a prototype in `probe.py`, mode `a`: 0 on P1–P4).

**Costs, MEASURED:**
- **Byte preservation:** P5 fails on **every one of 2,455** accepted logs. `json.dumps` rewrites every hand-spaced or compact
  record, and the CRLF bytes Codex r2 F1 protected are lost by design.
- **Concurrency, rewritten in place under `_locked`** (`conc.py`): readers do not lock. Two readers ran during 100 recordings
  over a 600-record log. **A reader saw an EMPTY log on 3,019 of 3,229 reads** (and 2,908 of 3,121 for the other reader), and
  `read_agenda_log` returned `[]` without raising. A snapshot taken at that moment would show "no agenda" and log it, which is a
  false state with no `Malformed` to flag it. HEAD and option (b) under the same load showed 0 empty reads, 0 shrinking reads
  and 0 Malformed.
- **Concurrency, made atomic by a temp file and `os.replace`** (`rename.py`): `flock` locks the old inode. A writer that opened
  the log before the rename waits on that lock, then reads the replaced (stale) file and replaces it again. **2 writers × 50
  recordings left 62 agendas, not 100: 38 recordings lost.** A fix needs a separate lock file, which is a new mechanism.

So (a) removes the class, but it trades a cosmetic blank line for byte loss on every write, plus either reader-visible empty
logs or lost writes. Rejected.

### (b) The writer never repairs, and appends a leading newline if the file does not end in one

**Removes:** the cut, and with it the only operation in this component that destroys bytes. That is the operation behind the
one data-loss finding (r2 F1). F1, F3 and N2 cannot arise. N1's agreement still needs the shared `_EOL` in
`_agenda_records`, which stays. The only line-model question left for the writer is one byte check:
`raw.endswith((b"\n", b"\r"))`.

**Costs, MEASURED** (`probe.py`, mode `b`, a prototype): P1, P2, P3 and P5 hold (0 violations). **P4 fails on 1,667 of
2,455** logs. That count is identical to `origin/master` across all four columns, because (b) **is** master's behaviour: a
text-mode `"a+"` read already saw a lone `\r` as `\n`. In other words, (b) reverts the blank-repair half of backlog #504 and
reopens the row's own Low item, "leaving a blank line replay ignores". Concurrency: 0 empty, shrinking or Malformed reads
(`conc.py`).

### (c) e4f812b0 as it stands

**Removes the class.** It gives ONE line model (`_EOL`, with `_EOL_B` derived from its pattern) and ONE blank predicate
(`_blank`). The reader now reads bytes and decodes them exactly as the writers do, so there is one decode path too. The cut
is computed in the reader's model and validated before any truncate. The table above is the evidence: 0 violations in
33,000 logs, by a probe that finds 313–1,062 violations at each earlier fold.

**Costs:** it keeps a byte-destroying `truncate` whose only purpose is cosmetic. That is about 15 lines (`_blank_tail_cut` and
the truncate branch in `_locked`) and 8 mutations to keep in step. Concurrency: the truncate runs under the same `LOCK_EX`
as the read and the append. An unlocked reader can see only a log missing some blank bytes, and that log is still valid (RUN:
0 anomalies in about 390 concurrent reads, `conc.py`).

**A remaining hole?** None found, and I claim none. The one thing I could not exclude by construction is a **future**
divergence: a third reader of `.claude/agenda-log.jsonl` that splits lines its own way. `grep` finds no other reader today
(`read_agenda_log` is the only one, in `scripts/goal-tree.py`). Invalid UTF-8 (backlog #529) is a separate, pre-existing hole.
Note that `_blank_tail_cut` decodes per line, so #529's fix must cover it as well as `read_agenda_log` and `_locked`. The row
already names `_blank_tail_cut`.

## 3. Recommendation

**Keep (c).** It removes the class, it is the only option that holds all five properties, and it is measured. (b) is the
simpler design, and it would have been the better r1 choice: it accepts the cosmetic blank line instead of building a cut.
But adopting (b) now means rewriting a converged, measured component at the round cap, and reopening backlog #504's stated
Low item, in exchange for removing about 15 lines that have no known defect. That trade is not worth it at r4.

| Item | r4 action | BLOCKER? | Why |
|---|---|---|---|
| The `blank-repair` design | **Adopt: no code change** | no | §2(c): 0 violations in 33,000 logs; the earlier folds' defects are each found by the same probe |
| A seeded property case in `--self-test`: P1–P5 over a generated corpus of whitespace and line-ending variants, with an independent line model. It guards the CLASS rather than the six inputs pinned so far | **FILE** (tooling, S) | no | Not a defect: HEAD passes it. It is the instrument that would have caught N1 and N2 before review (a review round sampled 6 tails, the corpus samples every `isspace` character) |
| If `blank-repair` ever reopens (for example in #529's decode fix), switch to (b): delete the cut, and append `\n` unless the raw bytes end in `\n` or `\r` | **FILE** as a note on backlog #504 / #529 | no | It removes the only byte-destroying operation. Its cost is the cosmetic blank line, measured above as master's behaviour |

**No BLOCKER.** Measured at HEAD: no false green and no data loss. P2, P3 and P5 hold on every log, and the self-test is 412/412.

## 4. Measured vs inferred

| Claim | Status | How |
|---|---|---|
| HEAD: 0 violations of P1–P5 in 33,000 random logs | **MEASURED** | `probe.py <HEAD goal-tree.py> head {1,2,3,4}` |
| The probe finds the r1 and r2 folds' defects (table in §2) and master's blank line | **MEASURED** | the same probe on `tree-8516de43`, `tree-7adf04ad`, `tree-origin_master` |
| 9 targeted inputs at HEAD, 0 violations | **MEASURED** | `extra.py` |
| `--self-test` 412/412 at HEAD | **MEASURED** | `python3 scripts/goal-tree.py --self-test` |
| (a) in place: P5 lost on 2,455/2,455; readers saw an empty log on about 93% of reads during writes | **MEASURED** (prototype, not PR code) | `probe.py … a`, `conc.py a` |
| (a) with `os.replace`: 38 of 100 recordings lost under 2 writers | **MEASURED** (prototype) | `rename.py` |
| (b) equals master on all five properties (P4 fails on 1,667/2,455) | **MEASURED** (prototype) | `probe.py … b` vs `tree-origin_master` |
| HEAD and (b) under concurrent readers: 0 empty, 0 shrinking, 0 Malformed | **MEASURED** (one run, about 390 reads each; a bound, not a proof) | `conc.py head`, `conc.py b` |
| Master's reader and writer shared a model only by the standard library's universal newlines | **READ** (`git show origin/master:scripts/goal-tree.py`: `read_text()` + `split("\n")`; `open("a+")`) | not run separately; the master row of the control table is consistent with it |
| No other reader of `.claude/agenda-log.jsonl` exists | **READ** (`grep` over `scripts/*.py`) | the grep covers only `scripts/` |
| (b) would have been the better r1 choice | **INFERRED** | judgement from the cost table |
| A future third reader is the only way the class returns | **INFERRED** | not exhaustive; it is the one route I could name |
| Invalid UTF-8 through `_blank_tail_cut` raises `UnicodeDecodeError` | **INFERRED** from the per-line `.decode("utf-8")`; the end-to-end path is backlog #529's, already filed | not run here |

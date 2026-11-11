# Architecture review — the shell-command parser of `scripts/check-agent-large-read.py` (backlog #465), armed by THRASHING on PR #471

**Armed by:** fix-induced findings in ONE component, the Bash parser (`simple_command` / `split_list` /
`list_spans`), in two consecutive rounds of `agent-large-read-lists`:
- round 2: all 8 findings (X1-X4, F1-F3, O1) were caused by the round-1 fold's per-part redirect and `cd` handling;
- round 3: X1 (`true; cd . '&&' cat big`, bash prints 0, denied as 500) was caused by the round-2 fold, which
  restored master's `simple_command` and then called it on each list part.

Per `docs/dev-process.md` → *Phases*, that is the arming condition. Rounds: `docs/reviews/{codex,claude,coordinator}/agent-large-read-lists-r{1,2,3}-*.md`.
Subject: `build-465` at `94d15f92`. Read first: `CONTEXT.md` (*Guard*, *Falsifier*, *Soundness check*) and
`docs/adr/`. ADR-0014 (a guard's `main` is drivable) is satisfied here (`main(argv, stdin_bytes, env)`) and not
re-opened. The mandate was to REFUTE the design. Every number below was produced by running the guard. It was
never inferred from reading the code.

## What kept failing, and why

**The parser reads one command string through SEVEN lexical views.** Each one decides part of the verdict:

| # | View | Where (symbol) | Quote-aware? |
|---|---|---|---|
| 1 | `READER_WORD` regex on the raw string | `simple_command` | no |
| 2 | `COMPOUND` regex on the raw string | `simple_command`, `list_spans` | no |
| 3 | `STDERR_REDIRECT` regex, applied BEFORE lexing | `simple_command` | no |
| 4 | `shlex(posix=True, punctuation_chars=True)` plus `OPERATOR.fullmatch` | `simple_command` | drops the quotes, so `';'` and `;` are the same token |
| 5 | a hand-written quote-tracking scanner | `split_list` | yes, but not `$'...'` |
| 6 | `LIST_STRICT` substring test on the raw string | `list_spans` | no (`echo '\'` counts as a backslash) |
| 7 | `shlex.split` (no punctuation) | `list_spans` | drops the quotes |

**Classifying the 19 findings of rounds 1-3** (from the coordinator documents):

| Class | Findings | Count |
|---|---|---|
| Two views disagree about the same characters | r1 X1, F1, X3, F3 · r2 X1, X2, X3, X4, F1, F2, F3 · r3 X1 | **12** |
| What a command DOES (its semantics) | r1 X2 (`printf -v`), X4 (failed `cd`), X5 (logical `cd ..`) · r2 O1 (`grep`) | 4 |
| Grammar (empty parts: `;;`, a trailing `&&`) | r1 X6, F2 | 2 |
| Policy | r1 F4 | 1 |

The thrashing is the first class. Every fold of rounds 1-3 either added a view or moved a string from one view to
another. Round 2 took redirects out of the list path and sent single commands to master's view 4. Round 3 is the
leak that move caused: view 4's quote loss reached list parts. **The semantics and grammar classes are already
closed** by a whitelist (`LIST_ZERO`, a leading `cd` only, one trailing `;`). No fold of them caused a later finding.

## Can a redesign remove it? — the four candidates, MEASURED

Harness (scratch, not committed): `.../scratchpad/arch465/` under this session's scratchpad. It holds `probe.py` (the
hook, the real `--hook` entry point, compared with what `bash -c` prints), `proto.py`, `fuzz.py`/`fuzz2.py` and
`replay*.py`. Fixture: `big` 500 lines, `a` and `b` 200, `small` 100, `sub/`.

**Prototype of (a)** (`proto.py`, about 90 lines, a lead and not an implementation). It has ONE quote-aware lexer
that emits tagged tokens: `op` (`;`/`&&`), `redir` (stderr) and `w` (value, globbable). Any other unquoted shell
character, a `$`, a backslash or a backtick throws Doubt, and the whole list is allowed. A closed grammar is checked
over those tokens, and the list path never calls `simple_command` and never runs a regex over the raw string.
Single commands and `cd W && reader` still go to master's `simple_spans`, unchanged.

| Corpus | HEAD `94d15f92` | Prototype (a) |
|---|---|---|
| The 22 reproducers of rounds 1-3 | — | **same verdict on all 22** |
| 27 hand probes | 2 false refusals, 11 silent allows over 300 | the same 2 false refusals; **5 silent allows become correct denials** (`cat a ';'; cat b` 400, `ca't' big; cat a` 700, `true; c'a't big` 500, `cat a '&&' cat b; true` 400, `echo '\'; cat big` 501) |
| Random fuzz, seed 7: 20,000 generated, 13,250 with `;`/`&&` | 18 false refusals: 16 are `&&` after a failure (a stated over-count), 2 are master's path; 1,049 silent allows; **150 tracebacks** (`IndexError`, a `#`-led command: row #464 F1, reproduced on `origin/master` with `#x cat a`) | 26 false refusals: 25 are `&&` after a failure, 1 is master's path; 1,001 silent allows; 0 tracebacks |
| REAL corpus: 410 subagent transcripts, 17,809 foreground Bash calls, replayed against today's files (worktree paths mapped to the main checkout) | 48 denials, 32,241 lines | **48 denials, 32,241 lines; 0 verdicts differ** |

How "false refusal" is classified: a denial is `&&`-after-failure when the same command with every `&&` replaced
by `;` makes bash print more than 300 lines. The remaining false refusals are `cd . '&&' cat big ...`. These are
master's single-command path. Its view 4 reads a quoted `'&&'` as the `cd DIR &&` prefix (bash prints 0 lines;
master and HEAD deny 500).

**Verdicts on the candidates:**

- **(a) one lexer + closed grammar: CAN remove the class**, measured in the sense that the list path has one view,
  so there is no second view to disagree with. The prototype keeps every round-1..3 verdict, fixes 5 fail-open
  cases, and has 0 list-path crashes. **It buys NOTHING measurable on the real corpus: 0 of 17,809 verdicts
  differ.** It is new code, a new surface for review, and a rebuild with at least one round. ⚠ The 25-vs-16
  `&&`-after-failure count shows that it denies more of the stated over-count. That is a consequence of counting
  parts HEAD gave up on, not a new class.
- **(b) the exact form `READER ARGS (; | &&) READER ARGS`, no zero-line commands: REFUTED.** It catches **0 of the
  4** list denials HEAD adds on the real corpus. All 4 contain `echo` (`echo "=== ci.yml ===" && cat -n
  .github/workflows/ci.yml` and three like it).
- **(c) drop the extension and keep master:** it loses those 4 denials, which are 5,693 lines, **17.7% of HEAD's
  denied lines** on the real corpus (`master` 44 denials / 26,548 lines; HEAD ⊇ master: 48 = 44 + 4). It removes no
  false refusal that was observed. The build cost is already spent, so (c) saves only future review cost.
- **(d) keep the current design: the parser has stopped producing FALSE REFUSALS outside two known, stated or
  pre-existing classes** (over 13,250 fuzzed lists and 17,809 real calls). Everything else it gets "wrong" fails
  toward allow and is inside the docstring's stated bound, with one exception: a QUOTED reader name (`ca't'`) is not
  listed. A round on a parser surface finds those fail-open strings forever. That is the review-is-the-wrong-
  instrument-for-a-surface shape, and no fold can end it.

## Value against cost

- **Value, ESTIMATED.** Row #457: Bash file reads over 8 KB are 4.1% of the 11-01 audit's 230M weighted (verified
  in `docs/backlog.md` row 457). Row #465's 21% has a different denominator: the over-300-line SUBAGENT file-read
  results, 5.84M = **2.54%** of 230M (`docs/reviews/coordinator/agent-large-read-guard-r2-coordinator.md`). So
  lists are about **0.21 × 2.54% ≈ 0.5% of usage**, not 0.9%: the 0.9% figure applied the 21% to the wrong
  denominator. The SAVING is lower still, because a refused agent still reads what it needs, in narrower calls.
  The real-corpus replay agrees on shape: 17.7% of denied lines.
- **What the real catches are.** All 4 are `echo LABEL && cat FILE` where ONE file alone is over 300 lines (424,
  1,411 and 1,763 lines, `wc -l` today). **The summing case that motivated the row (`sed -n 1,200p a; sed -n
  1,200p b`, every part under 300) has 0 occurrences in the real corpus.**
- **Cost so far:** 3 rounds, i.e. 5 review halves and 3 folds. Self-test 96 → 108 cases, mutations 95 → 107.
  Token cost not measured here.
- **Risk of false refusal** (it blocks an agent's call): 4 list denials in 17,809 real calls (0.02%). The 3rd has a
  recorded output of 425 lines against 424 counted, so it was a real large read. For the other 3 the recorded
  output was 90, 94 and 43 lines, which looks like a persisted-output preview. **UNVERIFIED: they may have been
  smaller files then.**

## Decision (recommended)

1. **(d) for PR #471: no redesign and no further parser fold on this PR.** At round 4 the round cap already files
   anything that is not a BLOCKER. This review adds the component-specific rule for what is foldable at all.
2. **Stop condition: the next round converges unless it reports a list-path FALSE REFUSAL** — a denial where
   bash prints at most 300 lines — that is NOT `&&` after a failure (stated) and does NOT reproduce on
   `origin/master` (master's path, filed as rows #464 and #469). A fail-open finding is checked against the stated
   bound. If it is outside the bound, the fix is a docstring line, never code. **Observation that would make it
   FAIL:** the differential run (fuzz seed 7 × 20,000, plus the real-corpus replay) shows a list-path false refusal
   of any other class, or HEAD denying fewer real calls than master.
3. **Docstring gap, a one-line fold this PR may carry:** list a quoted reader name (`ca't' big; cat a`, 700 lines,
   allowed) in the stated bound, beside the quoted operator.
4. **(a) is FILED as backlog #469, with a trigger and not as work now.** The NEXT change to this parser replaces
   views 1-7 on the list path with one tagged-token lexer, instead of patching a view. The differential harness
   becomes its soundness check. Doing it now buys 0 real-corpus verdicts.

## What did we decide that isn't written down?

1. **A list is SUMMED, but splitting it into separate calls puts the same lines into context.** The real catches
   are all a single part over 300. Whether summing is needed at all (rather than "any part over 300") was never
   decided: the row assumed it, and the corpus shows 0 sum-only cases. This review writes it down and does not
   change it.
2. **Master's single-command path is frozen WITH its defects** (round 2, decision A). The `#` traceback is row
   #464. The quoted-`'&&'` `cd` prefix false refusal (`cd . '&&' cat big`) was fixed inside lists in round 3, but it
   is neither in the docstring nor in any row. It is now in row #469.
3. **Every fail-toward-allow narrowing was accepted without measuring what coverage it gave up.** Measured here for
   the first time: on the real corpus HEAD ⊇ master, with no loss.
4. **A fail-open finding inside a stated bound is not foldable.** This was practised (round 1 X3 was declined),
   and it is the rule this component needs to converge, but it was never written. It is written in Decision 2.

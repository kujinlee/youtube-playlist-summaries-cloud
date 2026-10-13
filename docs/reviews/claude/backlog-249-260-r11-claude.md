<!-- claude-review: round 11, Claude half, PR #371 `backlog-249-260-fixes` at c7bf43df -->
<!-- subject: the r11 FOLD (c7bf43df) of the Codex half, plus 6b217be9 + ff5b10f7 -->

Second half of an alternating round, so the subject includes the FIXES. I did not re-find Codex's
H1/M1/L1/L2; H2 and M1 below are judgements of the fold for each.

## Blocking

None established.

## High

### H1 — `exception_heading` NAMES A NON-FATAL EXCEPTION AS THE KILLER, and in the flooded case the real killer appears nowhere in the report. Refutes claim 9.

Four shapes, each a **real Python 3.12 child** driven end-to-end through `run_mutations`, not a
hand-written fixture string:

| child | killed by | report says "the child DIED with …" |
|---|---|---|
| `__del__` raises at interpreter shutdown | `RuntimeError: THE_REAL_KILLER` | `ValueError: SHUTDOWN_NOISE_not_the_cause` |
| `atexit` callback raises | `RuntimeError: THE_REAL_KILLER` | `ValueError: ATEXIT_NOISE_not_the_cause` |
| `raise ExceptionGroup(...)` | `ExceptionGroup: the real group` | *(None)* → "stderr carries no traceback heading, so read the window" |
| child writes the literal heading line after its traceback | `RuntimeError: THE_REAL_KILLER` | `see the project README for help` |

⛔ **AND THE COMPOSITE IS THE ONE THAT MATTERS, because it reinstates exactly the harm Codex H1
measured and bolts a confident false attribution onto it.** Shutdown noise whose message floods the
window (`raise ValueError("NOISE\n" + "harmless shutdown chatter\n" * 40)` in `__del__`, over a
child that died of `RuntimeError: THE_REAL_KILLER_nobody_will_see`). Verbatim report:

```
... ⚠ WHAT THE CHILD ITSELF SAID — the child DIED with ValueError: NOISE:
    wn chatter
harmless shutdown chatter
harmless shutdown chatter
    ... (14 more)
```

`"THE_REAL_KILLER_nobody_will_see" in report` → **False**. The heading is wrong AND the window is
spent, so the report asserts a cause the child did not die of and carries no trace of the one it
did. Pre-r11 the message withheld the cause; this is worse than withholding — it is the
`message ASSERTED a cause that a local run refuted` shape row #270 exists to police, relocated into
the fix for it.

⚠ **THE DOCSTRING'S JUSTIFICATION IS FALSE AS A UNIVERSAL, and Python prints the discriminator
itself.** The docstring says *"the last one is the exception that actually killed the child, and the
earlier blocks are its causes"*. That holds for `raise … from …` and for
`During handling of the above exception` (I verified both). It is false for shutdown-time blocks,
where CPython writes `Exception ignored in: <function Leaky.__del__ …>` or
`Exception ignored in atexit callback: …` on the line **immediately above** the block — i.e. the
information needed to reject that block is already in the stream the rule is reading.

Two further defects in the same rule, both measured:

* **`ExceptionGroup` output never matches.** The opener is `  + Exception Group Traceback (most
  recent call last):` and the nested blocks are `  | Traceback …`, so `starts` is empty and the rule
  returns `None` — the caller then prints *"stderr carries no traceback heading"* over a stderr that
  carries one. That is world 3 claiming world 3 is impossible to leave.
* **An indented traceback block makes the rule return the next unindented line, whatever it is.**
  `l.strip() == "Traceback (most recent call last):"` matches an INDENTED opener, but the
  frame/heading skip then discards every indented line — including the heading. Measured:
  `exception_heading(indented_tb + "0/0 passed\n")` → `'0/0 passed'`, so the report reads
  *"the child DIED with 0/0 passed"*.

Root cause, one sentence: the rule validates **neither that the block it picks is fatal, nor that
the line it returns is an exception line.** Both are cheap — reject a block whose preceding
non-blank line starts `Exception ignored in`, and require the returned line to match
`^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Interrupt|Exit|Warning|:|$)` or similar — and either one
alone kills the composite.

⚠ **REACHABILITY, stated rather than implied.** My four witnesses are constructed children; I did
not catch this firing in a real sweep. The route into the delivered corpus is `TemporaryDirectory`'s
finalizer, which prints `Exception ignored in:` plus a traceback when cleanup fails — 34 scripts use
it, `check-plan-code.py` itself 45 times — and `threading` in three scripts (`Exception in thread …`
blocks; in my probe that noise preceded the killer, which is the harmless order). That is an
argument from the corpus, not a measurement of it. The constructed shapes are the measurement.

### H2 — TWO OF THE THREE WORLDS THE FOLD EXISTS TO DISTINGUISH HAVE NO FALSIFIER, and the four cases that look like they cover the disambiguation assert a phrase that is identical in all three. Answers claim 7; extends claim 10.

The commit body states the deliverable as *"The report now says which of THREE worlds it is in,
instead of two indistinguishable ones"*. Measured in a complete 248/248 mirror of the worktree built
**outside the repo** from `git ls-files` (plus `node_modules/typescript`, which `stage_tree`
requires), with a green control proved either side of every arm:

| mutation of the shipped code | suite |
|---|---|
| CONTROL | **248/248 passed** |
| world 1's sentence `"stderr is EMPTY, so the suite RAN and its PRINTER is the subject"` → `"XXXXXXXX"` | **248/248 passed** |
| world 3's sentence `"stderr carries no traceback heading, so read the window"` → `"YYYYYYYY"` | **248/248 passed** |
| `if not se.strip()` → `if False` — a printer defect now reported as *"read the window"* | **248/248 passed** |
| CONTROL (restored) | **248/248 passed** |

Only world 2 is covered, by entry 722. And the self-test **executes** world 1 — spying on
`exception_heading`, the sole production caller of this branch, shows the branch firing at four
self-test sites, two of them (`:3433` the mid-line fixture, `:3471` the `n.py` fixture) with
`stderr == 0 chars`, i.e. squarely in the world-1 arm. Executed, never asserted: this file's own
recorded shape, *"fixing a PREMISE is not covering the BRANCH"*.

⛔ **AND THIS IS THE ANSWER TO CLAIM 7: the substrings were preserved, and they do not discriminate.**
The four pre-existing cases assert `"report-format defect" in r.lower()` (`:3442`, `:3475`),
`"n.py" in r` (`:3477`), and the absence of `"caught by something else"` (`:3481`). Measured over the
`c.py` fixture — a suite that unambiguously **never reached its cases**:

```
'report-format defect' present?     True
'report-format defect in c.py'?     True
'caught by something else'?         False
said clause:  the child DIED with RuntimeError: DIED BEFORE CASE ONE
```

So the two "names it a REPORT-FORMAT defect" assertions hold **identically in the world the message
exists to separate**. The case named *"...and the report names it a REPORT-FORMAT defect, not a
coverage gap"* therefore cannot fail if the harness went back to calling a crash a printer defect,
and *"...names the file whose failure printer must change"* names a file that, in world 2, has no
printer to change. ⚠ This is not a style quibble: `:2796`'s comment was corrected **in this very
commit** (Codex L2) for making precisely that categorical claim, and the case names that make the
same claim were left standing — the brief's own question, answered by measurement rather than
reading. The property worth asserting is the `said` clause, which is the one thing with no case.

The two halves of H2 are one root cause: the deliverable is the `said` disambiguation, and nothing
in 248 cases asserts it except for world 2.

## Medium

### M1 — THE INCIDENT HAD **THREE** UNATTRIBUTED ENTRIES, NOT TWO. The third was never measured, and the corrected "5 and 2" covers two of them. Refutes claim 4 and claim 8.

Re-derived from the raw attempt-1 job logs (`115144461203`, `115144461240`), not from the round's
prose:

| attempt 1 | tally | unattributed entries |
|---|---|---|
| shard 4 | 191 mutations, 191 killed, **189** attributed | `#251 fold: hit_offset returns the first occurrence again…` **and** `⟳ r2 Codex HIGH — \| leaves the markdown-block class…` |
| shard 7 | 191 mutations, 191 killed, **190** attributed | `⟳ r3 Codex HIGH — the markdown HARD-break boundary goes` |

Row #270 writes a single parenthetical — *"(191 mutations, 191 killed, **189** attributed, 0
survivors)"* — over *"shards 4 and 7"*, and `check-plan-code.py:2712` says *"two entries 'killed,
unattributable'"*. Shard 7's figure is **190**, and the two shards together lost **three** entries.
Codex's M1 table had all three positions in hand (1091, 1099, 1102); the fold used two.

I measured all three myself, each edit applied to a `stage_tree` copy and run through
`run_suite_parts` with `child_env`:

| entry | rc | stdout | `[FAIL]` lines | `parse_fail_names` | stderr |
|---|---|---|---|---|---|
| `hit_offset` | 1 | 26,455 chars / 26,791 B | **5** | 5 | 0 |
| `\|` boundary | 1 | 26,474 chars / 26,810 B | **2** | 2 | 0 |
| HARD-break boundary | 1 | 26,446 chars / 26,782 B | **1** | 1 | 0 |

Scoped at HEAD: `--shard0 {1095,1103,1106}/1535` → **1 killed / 1 attributed each.** So the row's
*conclusion* survives and is now stronger — the printer is correct for all three, not two — but the
corrected figure set is **5, 2 and 1 over three entries**, and the comment's "two entries" is a
third wrong count on the same subject, written by the commit that corrected the second one.

## Low

### L1 — row #270 declares "8 cases" for a change that added 9.
`(\`exception_heading\`, 8 cases, 3 mutations)`. Measured: the docstring moved 239 → 248 and both
suites run at their declared counts, so the delta is **+9**. The commit body's own Verification
section says `239 -> 248`. One of the two is wrong and it is the row.

### L2 — the flood size is tied to `DIAGNOSTIC_WINDOW` only by a comment, and the comment credits the safety to the wrong mechanism. Claim 12.
The comment says *"60 continuation lines is ~840 characters against a 400-character window: the
flood has to be DERIVED from the budget, not guessed, or a later change to DIAGNOSTIC_WINDOW makes
this case quietly ambient again."* `* 60` is a literal; no derivation happens. But the stated harm
does **not** occur — measured, control green either side:

| `DIAGNOSTIC_WINDOW` | result |
|---|---|
| 400 (shipped) | 248/248 |
| 600 | 244/248 — four unrelated budget cases red, the H1 pair still green **and still correct** |
| 1000 | 243/248 — `...over a fixture where the 400-char window itself loses the heading` goes **red** |
| 2000 | 242/248 — `...and the 400-char tail DOES lose it` goes red too |

The partner case fires at the same threshold at which the first would become ambient, so the
failure is **loud**. The guarantee comes from the PAIRING, not from any derivation — which is the
better argument, and is not the one the comment makes. Fix the comment, not the code.

### L3 — the row's "stderr **1,259 B**" is not reproducible by construction.
Independently injecting `raise RuntimeError(...)` into `check-withdrawal.py`'s `signature_of`
reproduces the mechanism exactly (see SOUND, claim 3) but gives **1,251 B** run from a repo root and
**871 B** under `stage_tree`'s temp path: the figure is a function of the absolute path length baked
into every frame line. Qualify it ("~1.3 KB, path-dependent") or drop it; as a bare byte count it
reads as a reproducible measurement and is not one.

## Checked and found SOUND

* **Claim 1 — re-derived from the API, not cited.** Run `38351420487`, `headSha f599182d` on both
  attempts; attempt 1 `mutation-sweep (4)` and `(7)` `failure`, attempt 2 all eight `success`. Same
  run, same commit. The non-determinism is measured.
* **Claim 2's withdrawal.** Internally consistent and I re-derived the arithmetic: 1091 % 8 and
  1099 % 8 = 3 → shard 4; 1102 % 8 = 6 → shard 7. At HEAD the same three entries sit at 1095 / 1103
  / 1106 → shards 8 / 8 / 3, which is exactly the +4-entry insertion the fold describes. Withdrawing
  the reassignment story and resting on the rerun is correct.
* **Claim 3 — independently reproduced.** Raise injected into `signature_of`: `rc=1`, stdout
  **0 B**, **0** `[FAIL]` parsed. And the fold delivers here: `exception_heading` →
  `'RuntimeError: INJECTED CONSTRUCTION-TIME FAILURE'`. ⚠ **A scoping note the round should carry:**
  on this shape `diagnostic_tail` ALSO carried the cause (`True`), so for the mechanism row #270
  actually hypothesises, the window alone already sufficed. The fold closes the constructed
  multi-line hole Codex built, not this one. That is still worth shipping — it just means
  *"the next occurrence will name it"* was already true for the suspected occurrence.
* **Claim 4's sweep.** 32 `check-withdrawal.py` entries (= `EXPECTED_MUTATIONS`), run as one scoped
  sweep over a staged tree: **32 killed / 32 attributed / 0 survivors**, 55.0 s here.
* **Claim 5 — the fold does fix what Codex H1 measured.** The heading is read from `se` directly, so
  neither a 26,000-character stdout (stderr's budget collapsing to 200) nor a 40-line flooded stderr
  can evict it. Verified against the multi-line, `During handling of…` chain, CRLF, and big-stdout
  shapes. Claim 5 as originally written was false and the fold's replacement of it is right.
* **Claim 6 — a NEW differential corpus, 144 combinations, not the 25 that produced the claim.**
  `run_suite_parts` stubbed to constructed triples: `rc ∈ {0,1,2}` × 6 stdouts (empty,
  tally-only, 26,000 chars, a real `[FAIL]`, a mid-line marker, a `❌` line) × 8 stderrs (empty,
  blank-only, plain traceback, 40-line flood, `During handling of…` chain, `CANNOT RUN`, a
  self-printed heading, CRLF). Compared `ok`, the full `ev_muts` dicts, report line counts, the prose
  **before** the message line and the window text **after** it. **ff5b10f7 → c7bf43df: 0
  differences.** f599182d → c7bf43df: 40, every one inside the intended branch. The `rc == 2`
  branch, `parse_fail_names(out)` and the evidence payloads are unchanged.
* **Claim 8's replay, all of it.** `{603,604,605,609,619,719,720,721,722}/1535` → **1 killed / 1
  attributed each**. `--self-test` 248/248. `--binding` rc=0, **1,543 anchors / 1,535 entries**.
  `check-withdrawal --self-test` 179/179. Manifest total 1,535 = declared sum 1,535;
  `check-plan-code.py` 133 entries = declared 133; positions 719–722 are this branch's four new
  entries (719 from `6b217be9`, 720–722 from the fold). L1 above is the one figure that fails.
* **Claim 10's conclusion — right, by a different instrument than the one credited.** The commit
  credits "all five home-escape entries run individually", which is the wrong population: a case
  becomes ambient in the MUTATED world, and four of those five never reach the diagnostic branch at
  all. The complete measurement already existed — the CI sweep at `ff5b10f7`: shards 1,2,3,4,6,7,8
  `success`, shard 5 `failure` with the single survivor. **Bound for HEAD, established
  structurally:** new evidence enters a report only at `:2818`/`:2832`, and `:2818` is the sole
  production caller of `exception_heading` (grep + a spy over all 248 cases) — the branch fires at
  exactly four sites, two with empty stderr (no heading reachable) and two carrying tracebacks, both
  of which are this round's own cases. At HEAD, shard 5 is green and 604's scoped replay kills. See
  CANNOT RUN for what is still open.
* **Claim 11.** `REPLACEMENT text is scanned` has exactly one producer, the `repl` call site at
  `:2546`; the only other occurrences in the whole repo are the assertion and its own comment. And
  the fix is falsifiable *for the right reason*: delete `home_escapes(repl)` and `_ok5` is still
  `False` (the fixture's suite crashes), so it is the second tuple element that does the killing.
  The spy census confirms the fixed case no longer reaches the diagnostic branch at all, which is
  the structural version of the same statement.
* **Claim 12's substance.** `--shard0 722/1535` → 1 killed / 1 attributed, and with the heading
  dropped there is no other producer of `RuntimeError: FLOOD_MARKER`: stderr's last 400 characters
  over that fixture are entirely `uninformative`. The pair is falsifiable. See L2 for its comment.
* **Context, not a finding:** HEAD's `verify` job is RED solely because round 11 has one half —
  `check-review-rounds.py` reports *"backlog-249-260 round 11: only codex — claude neither ran nor
  recorded a `REVIEW GAP:` line"*. Committing this file clears it.

## CANNOT RUN

* **Full `--mutate .` at HEAD.** Not run locally — eight shards blow `SUITE_TIMEOUT` on a laptop,
  which this project has already measured; I scoped instead (13 single-entry sweeps plus the
  32-entry `check-withdrawal` sweep). CI run `38409915435` at `c7bf43df` has shards 2,3,4,5,7
  `success` and shards **1, 6 and 8 still in progress** at the time of writing. ⛔ **Treat full-HEAD
  mutation coverage as NOT RUN, not a pass** — it is the only complete instrument for the
  mutated-world population behind H2 and claim 10, and H2 predicts it will pass while two world-arms
  remain unfalsifiable, so a green sweep will not answer H2 either.
* **The exact historical `1,259 B` stderr.** Path-length-bound; see L3. **Treat that specific figure
  as NOT RUN**, not independently verified. The mechanism behind it IS verified (claim 3).
* **Why the shards are intermittent — which exception, and why only sometimes.** Out of scope per
  the brief, and I found nothing. Stated so the gap is not read as a clean search:
  **treat this as NOT RUN.**

## Instruments

* Worktree `wt-backlog` at `c7bf43df`, read-only apart from this file; `git status --short` empty
  before and after every background sweep (one census run wrote `hits.json` into the worktree root
  and it was moved out immediately — verified clean).
* The prepared Python 3.12.9 venv, its `bin` first on `PATH` for every `--mutate` call.
* **A complete mirror of the tree outside the repo**, built from `git ls-files` + `rsync` plus
  `node_modules/typescript`, proved at 248/248 before any mutation and re-proved after each revert.
  Every mutation of shipped code in H2 and L2 was applied there, never to the worktree — this
  repo's recorded rule that an instrument editing the repo corrupts its peers.
* A single-anchor mutator that **refuses** when its anchor does not bind exactly once, so a
  silently-unapplied mutation cannot read as a green result.
* A spy on `exception_heading` (its only production caller) with `traceback.extract_stack()`
  attribution, run over all 248 cases, to census the diagnostic branch's firings.
* A two-module differential driver loading `f599182d`, `ff5b10f7` and `c7bf43df` side by side with
  `run_suite_parts` stubbed, over 144 constructed stream triples.
* Real Python 3.12 children for every traceback shape in H1 — `ExceptionGroup`, `__del__` at
  shutdown, `atexit`, threads, `SyntaxError`, self-printed heading — plus the composite driven
  through `run_mutations`.
* GitHub API: run/attempt metadata and raw job logs for `38351420487` (both attempts),
  `38405547448` and `38409915435`.
* Scoped sweeps: `--shard0 {603,604,605,609,619,719,720,721,722,1095,1103,1106}/1535` and a
  32-entry in-process `check-withdrawal` sweep.

Repository otherwise unchanged. Nothing committed, nothing staged, no other file under
`docs/reviews/` touched.

# C5 recall matcher — round 1, Claude half

**Subject:** `c5-recall-matcher` at `a0bab2be` — `scripts/recall-match.py` (new, ~450 lines),
`.claude/hooks/surface-recall.sh` (new), `.claude/settings.json`, `scripts/mutations/recall-match.json`
(new), plus registrations in `check-plan-code.py`, `check-fixture-variation.py`,
`check-selftest-counts.py`. Seven guarded paths.

**Mandate:** refute, not confirm. **Verdict: 2 Blocking, 4 High, 4 Medium, 7 Low.**

REVIEW GAP: codex — not dispatched; the branch's own measurement refuted the approach before a second half was run

⚠ The line above is deliberately unadorned and line-initial. An earlier draft wrapped it in bold and
the gate refused it — the same defect as a backticked `NO-REVIEW:`, which cost a red CI run on this
very repository this morning. The findings below are the Claude half only.

---

## BLOCKING

**B1 — the repo's own mutation gate goes red on this commit: 7 of 10 entries attributed, not 10.**
Established by importing `check-plan-code.py` and calling `run_mutations()` on a staged tree, not by
re-implementing it. Three distinct causes:
- entry 3 removes the `if tt else 0.0` guard in `coverage`; the named case raises `ZeroDivisionError`
  **inside the argument expression**, so `check()` never runs and prints no `[FAIL]` line. The harness
  reports a report-format defect **for the whole file**.
- entry 4 pins the cutoff at `4.95`; the abort case does `rank(...)[0][0]` on an empty list →
  `IndexError` before `check()` can report. The only `[FAIL]` printed is a *different* case, and
  `expect` is matched by equality, so 0 matches.
- entry 9 **survives**. Its `"expect": "NO-CASE: exercised by the rc contract"` is an **invented
  grammar** — `grep -rn "NO-CASE" scripts/` returns exactly one hit, that file. The harness has no
  such branch. *"A hole with a label on it."*

**B2 — the "17%" fire rate is wrong by 3× on the population the hook actually sees.**
Harvested **1,062 unique real Bash commands** from 25 session transcripts. Shipped combiner at shipped
threshold: **560 fire = 52.7%**. The shipped 17% came from 30 commands the author chose.

Threshold sweep, five combiners, full population: `IDF only` is **98.2% flat from 0.1 to 0.5**;
`IDF × coverage` **plateaus at ~25% and never goes below it, even at 0.9**. The threshold does not
control what it is supposed to control.

Cause is dimensional: `relevance` multiplies a **bounded** factor (coverage ∈ [0,1]) by an
**unbounded** one (a *sum* of IDF up to `|trigger|·log N`), and the cutoff is `threshold·log(N)` — a
fraction of a **single** token's maximum weight. `DEFAULT_THRESHOLD`'s own comment describes a
quantity the code does not compute.

**No operating point exists.** Against a labelled set the must-silent commands are already clean at
0.30, so raising the threshold buys nothing and costs a true positive at every step: 0.3 → 0.4 drops
must-fire 3/5 → 2/5 while the population rate falls only 52.7% → 47.3%.

---

## HIGH

**H1 — the binding variable is the SITUATION's length, not the trigger's.** The summary line first
said "long triggers are unreachable"; **measured and reversed**: fires per entry by trigger length are
3-token 15.2, 6-token 46.3, **9-token 108.6**. Longer triggers fire *more*. Split by command size,
short commands (<60 ch) fire **0.00% at every trigger length** while long ones (>200 ch) fire at all
lengths. Median distinct tokens: short cmd 6, **long cmd 36**, trigger 6. `coverage` divides by the
trigger and deliberately not by the situation — reasoned for a `Doing:` line, deployed against a
36-token heredoc.
⭐ Compound (`;`) triggers dilute themselves, but that is **3 of 141** — a three-line edit, not a
corpus rewrite.

**H2 — when every matched token is corpus-unique (df=1), IDF cancels from both sides** and the
criterion collapses to `coverage ≥ threshold`, with no rarity in it. Verified identical at N = 3, 10,
141, 1000. *"This is the failure `× coverage` was added to fix; it was moved, not removed."*

**H3 — "fails closed" is false on two paths.** A 1-entry corpus can never fire (IDF over one doc is
all zeros) yet reports `nothing fires (1 triggers checked)` at rc=0 even when the situation is
byte-identical to the only trigger. And 1-parseable-of-141 reports the same string, because `seen` is
returned by `load_entries` and then discarded — `report()` receives `len(entries)`. 141 unparseable
*does* correctly reach rc=2.

**H4 — `tool_situation`, the only function the PreToolUse hook calls, has 0 self-test cases and 0
mutation entries.** So do `load_entries`, `memory_dir` and `report`. `EXAMINED_KEYS` lists only the
nine pure functions, so `check-fixture-variation` cannot see them either.

---

## MEDIUM

- **M1** — `json.loads(raw)` passed unchecked into `tool_situation`; non-object JSON (`"s"`, `[1]`,
  `null`, `42`) raises `AttributeError` and exits **rc=1**, undeclared in the docstring's rc contract.
  Masked by the hook's `2>/dev/null || true`.
- **M2** — the stemmer strips the inflectional suffix but not the **orthographic `e`** English elides
  before `-ing`/`-ed`, splitting every `-e` verb from its own forms, one-way and silently.
  **Nine pairs both live** in the vocabulary (`writ`/`write`, `chang`/`change`, `propos`/`propose`,
  `serv`/`serve`, `deriv`/`derive`, `valu`/`value`, `shar`/`share`, `slic`/`slice`, `stag`/`stage`),
  so IDF ran over a fragmented vocabulary: `write` scored as 8 of 141 when the concept appears in 22.
  ⭐ Load-bearing: it **silently voids trigger rewrites**, so it must be fixed before re-authoring.
- **M3** — `DEFAULT_TOP` was raised 3→5 because top-3 discarded a correct hit at rank six; the hook
  then passes `--top 2`. **98 of 300** real commands have more than two hits above the cutoff,
  truncated silently with no signal.
- **M4** — the docstring's *"No try/except that swallows and continues"* sits four lines above
  `except OSError: continue`. The intent (count in `seen` first) is sound, but `seen` never reaches
  the success-path output, so the swallow is real in effect (H3).

## LOW

- **L1** — section comment `# --- tokenise (6)` with 7 `check()` calls following.
- **L2** — a comment explains ordering against a `-in` suffix that does not exist in `_SUFFIXES`.
- **L3** — `report()`'s `situation` parameter is never used.
- **L4** — the docstring claims dotted/hyphenated identifiers *"survive whole"*; **false for 7 corpus
  identifiers** (`postgrest-js→postgrest-j`, `ask-choices→ask-choic`, `peer-sites→peer-sit`,
  `machine-parsed→machine-pars`, `writing-plans→writing-plan`, `well-tested→well-test`,
  `pre-committing→pre-committ`). ⭐ **The sole case pinning the claim uses `check-merge-ready.py`,
  which ends in `.py` and is immune by construction** — the one case found satisfied by a constant its
  own fixture supplies.
- **L5** — bare integers admitted; 43 sit in the vocabulary at near-maximum IDF, producing e.g.
  `sed -n '153,222p'` → `arch-review-153-workflow-readers`. Impact **6 of 560** fires.
- **L6** — the commit message carried a placeholder `NO-REVIEW: pending` line.
- **L7** — **125 ms per Bash call** (the hook's comment claimed ~109), unconditional and uncached: all
  141 files re-read, re-parsed, re-tokenised and the IDF table rebuilt **inside `rank`** every
  invocation. At 275 hook invocations per session ≈ **35 s added wall clock per session**.

---

## Areas the reviewer could NOT establish

1. Scoring / sample representativeness — **established** (B2, H1, H2).
2. `load_entries` failing open — **established** (H3). Sub-question answered: 141 unparseable *does*
   reach rc=2; **140-unparseable-plus-one-good does not**.
3. Hook hanging, blocking or corrupting a call — **established SAFE; could not make it fail.** Driven
   with a firing payload, `npm test`, `ls -la`, non-JSON garbage, non-dict JSON, empty stdin and a
   200 KB command: `exit 0` in every case.
4. Cases asserting implementation rather than property — **partial**: one genuine instance (L4); the
   other 39 hold up. The real weakness is **absent** cases (H4).
5. The 10 mutation entries — **fully established** (B1).
6. `plan_situation` / `tool_situation` mis-reading shapes — ⚠ **LARGELY NOT ESTABLISHED. The area with
   least to show for it.** Two hypotheses formed and **refuted**: the `tool_name` prefix is inert (no
   trigger contains `bash`), and `parse_trigger`'s em-dash split mis-reading other dashes — **0 of
   141** descriptions carry `FIRES-WHEN:` without an em-dash.

---

## Disposition

- **B1** — repaired but ⛔ **NOT VERIFIED, and not verifiable in this tree.** Cases were made lazy so
  a raising mutation is attributable; `corpus_verdict` was extracted at `fe618a54` so the surviving
  mutation has a case; the `NO-CASE:` label is removed and the anchor retargeted onto
  `if n_entries == 0: return CANNOT_RUN,` (`scripts/recall-match.py:105`).
  ⚠ **The same commit that fixed B1 turned the control red**, and a red control collapses the
  harness to `NotMeasured` — `mutate_delivered` returns no coverage verdict at all, for the whole
  run, which `check-plan-code.py:2908` asserts as a case. Measured 2026-09-29 on this tree:
  `--mutate .` reaches `[54/54] control scripts/recall-match.py`, prints *"did not prove the suite
  works (exit 1) BEFORE any mutation was applied"*, and ends `NOT MEASURED`. **All 54 scripts, not
  just this one.** So "B1 is fixed" is a reading of the diff, never of the gate.
  ⛔ Per `CLAUDE.md`, *cannot run is a FAILURE, never a pass* — B1's disposition is **unmeasured**,
  and the earlier line here said "fixed", which is the inference-stated-as-measured shape that this
  very review was convened to catch. `master` is unaffected: `scripts/recall-match.py` does not
  exist there, so the void verdict is branch-local.
- **B2 / H1 / H2 / M2** — repairs 1 and 2 landed and were **correct but insufficient**; see
  `fe618a54`'s message. The approach itself was then refuted.
- **H3** — confirmed, **not fixed**.
- **H4, M1, M3, M4, L1–L5, L7** — **not fixed**, deliberately: the scoring is being replaced.
- **L6** — fixed.

⛔ **Superseded by measurement after this review:** a labelled set (`8d1202f0`) scored **19/20** on
author-phrased situations and **2/20 paraphrased**; an LLM asked to match the same paraphrases by
meaning scored **19/20**. The trigger corpus is sound; lexical overlap is the wrong mechanism. Most
findings above concern code that should not survive.

# Round 6 — Claude adversarial half · `shard-mutation-sweep` (PR #366) at `68f6d7ea`

Subject: `git diff ece8d309..68f6d7ea` — the rewritten `SHARD_INDEX`/`SHARD_TOTAL` guard in
`.github/workflows/ci.yml`, plus the dashboard entry and round 5's Codex half and verdict.

Mandate: **REFUTE**.

**Headline.** The rewrite removes the overflow class it was written to remove — I confirmed every
one of the brief's ten already-measured inputs and could not reach a wrong spec through any of them.
But it **widened the accepted input class in the same property it defends**: the `case` guard it
replaced refused non-ASCII digits (bash `[!0-9]` is a byte class), and the Python parser accepts
**750** of them. `SHARD_INDEX='٠'` (U+0660) yields `1/8` — a job silently measuring shard 1, which
is the exact failure mode this guard exists to prevent, reached *through* the guard for the second
consecutive round. The same `\d`-is-Unicode defect sits one layer deeper in the deliverable script
(`SHARD_SPEC`), so this is a class, not an instance.

Not reachable from GitHub's `strategy.job-index` today — the same reachability status as round 5's
L2, which this fold nonetheless judged worth a rewrite.

---

## 1. Verification

`HEAD` = `68f6d7ea81b6da804c013a362fa2bf64cb1143d8`. **No tracked file was modified**: `git status
--porcelain` reads `M docs/explainers/questions.md` only, before and after, and the md5 of
`.github/workflows/ci.yml` is `ca7889a8e22af7c1f3b3d710a9377722` at the end of the review. The one
mutation (§Q5) was applied to a `git archive 68f6d7ea` copy under the scratchpad, never the tree.

### 1.1 The block was EXTRACTED, not retyped (brief item 4)

The brief's warning is the reason this is stated first. I did **not** use `textwrap.dedent` and did
not reason about the indentation. I loaded `.github/workflows/ci.yml` with a real YAML parser
(PyYAML 6.0.3 in a scratchpad venv — the repo's interpreter has no `yaml`), took
`jobs['mutation-sweep'].steps[*].run` verbatim, wrote it to `step.sh`, and ran *that* under `bash`.
The only edit was deleting the final `python3 scripts/check-plan-code.py --mutate .` line and
appending `echo "SPEC=[$SPEC]"`; the guard itself is byte-identical to what YAML hands bash.

After YAML's dedent the Python arrives at column 0 with its body at 4 spaces. It parses and runs.
**No `IndentationError`.** The file has no tabs in this region (`cat -t -e` over lines 655–725).

### 1.2 Legitimate matrix values — `0..N-1` → `1/N..N/N` (brief item 3)

```text
I=0 N=8  rc=0  SPEC=[1/8]      I=4 N=8  rc=0  SPEC=[5/8]
I=1 N=8  rc=0  SPEC=[2/8]      I=5 N=8  rc=0  SPEC=[6/8]
I=2 N=8  rc=0  SPEC=[3/8]      I=6 N=8  rc=0  SPEC=[7/8]
I=3 N=8  rc=0  SPEC=[4/8]      I=7 N=8  rc=0  SPEC=[8/8]
```

All eight distinct, complete, in order. Also `I=0 N=1 -> 1/1`, `I=0 N=256 -> 1/256`,
`I=0 N=4096 -> 1/4096`.

### 1.3 The brief's ten already-measured inputs — all reproduced, none refuted

```text
I=0  N=8                     rc=0  SPEC=[1/8]
I=7  N=8                     rc=0  SPEC=[8/8]
I=""                         rc=2  CANNOT RUN — SHARD_INDEX is ''
I=abc                        rc=2  CANNOT RUN — SHARD_INDEX is 'abc'
I=3x                         rc=2  CANNOT RUN — SHARD_INDEX is '3x'
I=08                         rc=2  CANNOT RUN — SHARD_INDEX is '08'
I=" 0"                       rc=2  CANNOT RUN — SHARD_INDEX is ' 0'
I=18446744073709551616       rc=2  CANNOT RUN  (was ACCEPTED and wrapped to 1 before)
I=8  N=8                     rc=2  CANNOT RUN — SHARD_INDEX=8 is not a valid 0-based index
I=0  N=0                     rc=2  CANNOT RUN — ... into SHARD_TOTAL=0
```

### 1.4 The brief's attack list (item 1)

```text
+0                      rc=2 CANNOT RUN
0x10                    rc=2 CANNOT RUN
'0\n' (really present)  rc=2 CANNOT RUN — repr shows '0\n'
'0\r'                   rc=2 CANNOT RUN
' 0' / '0 ' / '0.0'     rc=2 CANNOT RUN
'-1' / '00'             rc=2 CANNOT RUN
unset SHARD_INDEX       rc=2 CANNOT RUN (env -u, not merely empty)
unset BOTH              rc=2 CANNOT RUN
N=4097 / N=10^20        rc=2 CANNOT RUN
NUL in the value        IMPOSSIBLE — execve refuses: ValueError: embedded null byte
'٠' U+0660              rc=0 SPEC=[1/8]     <-- FINDING L1
'１' U+FF11             rc=0 SPEC=[2/8]     <-- FINDING L1
'𝟛' U+1D7DB            rc=0 SPEC=[4/8]     <-- FINDING L1
'٠٠٠٠٠٠'                rc=0 SPEC=[1/8]     <-- FINDING L1 (leading zeros, accepted)
'²' U+00B2              rc=2 Python traceback, NOT the CANNOT RUN sentence <-- L3
'½' / '௰'               rc=2 CANNOT RUN
```

Identical results under `bash -e` (GitHub's default `shell: bash -e {0}`).

### 1.5 The brief's figures

```text
python3 scripts/check-plan-code.py --self-test   -> 161/161 passed      rc=0  (rc read without a pipe)
manifest                                         -> 57 files, 1200 entries
EXPECTED_MUTATIONS                               -> 57 files, declared sum 1200
python3 scripts/check-python-pin.py              -> rc=0 (ADVISORY: this machine is 3.14, CI 3.12)
python3 scripts/check-docs.py                    -> rc=0  Documentation integrity OK
python3 scripts/check-selftest-counts.py         -> rc=0  50 scripts, every declared count verified
python3 scripts/check-review-rounds.py           -> rc=0
python3 scripts/check-features.py                -> rc=0  26 nodes
python3 scripts/check-dashboard-entry.py         -> rc=0  an entry block was added
python3 scripts/check-anchors.py                 -> rc=0  13 registered
```

All confirmed. Nothing in the brief's "already measured" list is false.

### 1.6 NOT MEASURED

- **Unsharded `--mutate .`** — forbidden by the brief, and not run. I confirmed by reading
  `check-plan-code.py:1740` (`shard_muts = shard_slice(...) if shard is not None else muts`) that an
  **absent** `--shard` still means the whole manifest. Read, not executed.
- **That a non-zero step exit fails the GitHub job.** Not observable locally; `exit 2` from the step
  script is standard GitHub Actions step failure. Reasoned, not measured.
- **GitHub's own YAML parser.** I used PyYAML. Both implement standard literal block scalars and the
  block has no tabs or ambiguous indentation, but a second parser is one I did not run.
- **CI on `68f6d7ea`.** I did not query the live checks.

---

## 2. Findings

Fixes are stated separately from findings and every fix below is **UNVERIFIED** — I wrote no code.

### L1 · Low · DELIVERABLE · caused by this fold — the rewrite ACCEPTS an input class the guard it replaced REFUSED

`str.isdigit()` is Unicode-wide. `int()` then accepts every code point for which `isdecimal()` is
also true — **750 non-ASCII code points**, measured by enumerating the full range.

Exhibiting input, through the shipped block as bash receives it:

```text
SHARD_INDEX='٠'  SHARD_TOTAL=8   ->  rc=0   SPEC=[1/8]        (U+0660 ARABIC-INDIC DIGIT ZERO)
SHARD_INDEX='１' SHARD_TOTAL=8   ->  rc=0   SPEC=[2/8]        (U+FF11 FULLWIDTH DIGIT ONE)
SHARD_INDEX='𝟛' SHARD_TOTAL=8   ->  rc=0   SPEC=[4/8]        (U+1D7DB MATH SANS-SERIF THREE)
```

Two things make this a finding rather than a curiosity.

**(a) It is a regression this fold introduced, in the property the guard defends.** The `case` guard
at `ece8d309` used `*[!0-9]*`, which bash evaluates as a byte class and which therefore refused all
of these. Measured side by side, old block vs new block, same inputs:

```text
INPUT                       OLD (ece8d309)     NEW (68f6d7ea)
I=٠  N=8                    rc2                SPEC=[1/8]      <<< DIFFERS
I=１ N=8                    rc2                SPEC=[2/8]      <<< DIFFERS
```

`٠` mapping to `1/8` is the all-jobs-alias-to-shard-1 shape — round 1's M2(a) and round 5's L2 —
reached through the third version of this guard.

**(b) The leading-zero rule is ASCII-only while the accept rule is Unicode-wide.** `startswith("0")`
tests U+0030. So:

```text
SHARD_INDEX='٠٠٠٠٠٠' SHARD_TOTAL=8  ->  rc=0  SPEC=[1/8]
```

Six leading zeros, accepted. The guard's own message asserts the value must be *"a canonical decimal
integer in 0..4096"*, and the dashboard entry says it *"rejects leading zeros"*. Both are false
about its actual accept set — which is the same defect round 5 charged against the previous
message ("its message says bash would read it as 0; actually bash errors loudly").

**Fix, UNVERIFIED:** replace `v.isdigit()` with an explicit ASCII test, e.g.
`v.isascii() and v.isdigit()`, or `re.fullmatch(r"0|[1-9][0-9]*", v)` which expresses the canonical
form, the leading-zero rule and the digit class as one predicate instead of three clauses that can
disagree about what a digit is.

### L2 · Low · DELIVERABLE · NOT caused by this fold — the same `\d`-is-Unicode hole one layer deeper, in `check-plan-code.py`

`scripts/check-plan-code.py:1546`:

```python
SHARD_SPEC = re.compile(r"^(\d+)/(\d+)$")
```

On `str` patterns Python's `\d` is Unicode-aware, so `parse_shard` has the same accept set:

```text
parse_shard('1/٨')  ->  ((1, 8), None)      accepted as shard 1 of 8
parse_shard('٠/8')  ->  refused, but the message renders it '0/8'
```

This predates the fold (it ships from `d74d1c2b`). It matters here because it means L1 is a **class,
not an instance**: "a decimal integer" is now spelled three different ways across two deliverable
files — bash `[!0-9]` (ASCII), `str.isdigit()` + `startswith("0")` (Unicode accept / ASCII reject),
and `\d` (Unicode) — and the three disagree. That is this repository's own *a second implementation
of one rule drifts* lesson, in the file that enforces it on everything else.

**Fix, UNVERIFIED:** `re.compile(r"^(\d+)/(\d+)$", re.ASCII)`, and then one named predicate shared
by `parse_shard` and the workflow guard rather than two spellings — though the workflow guard cannot
import from `scripts/`, which is the honest reason there are two, and may argue for the guard
delegating the whole decision to `check-plan-code.py` (see M1).

### L3 · Low / informational · DELIVERABLE · caused by this fold — 128 code points produce a traceback instead of the CANNOT RUN sentence

`isdigit()` is true and `isdecimal()` is false for 128 code points (`²`, `³`, `¹`, `፩`, `፪`, …).
`int()` then raises inside the guard, *after* the `isdigit()` arm has passed:

```text
SHARD_INDEX='²' SHARD_TOTAL=8  ->  rc=2
Traceback (most recent call last):
  File "<string>", line 9, in <module>
    i, n = one("SHARD_INDEX"), one("SHARD_TOTAL")
ValueError: invalid literal for int() with base 10: '²'
```

The exit direction is safe — `|| exit 2` still fires — so this is not a correctness hole. It is a
contract one: the reader gets a stack trace instead of *"NOTHING WAS MEASURED; treat this as NOT
CHECKED"*, and `parse_shard`'s own docstring eleven hundred lines away states the rule being broken:

> ⛔ A SENTENCE AND A CANNOT RUN, NEVER A TRACEBACK OR ARGPARSE'S "invalid value". Whoever typed
> `--shard` believed a subject was being measured; a stack trace tells them their invocation is
> broken without saying what was or was not checked.

**Fix, UNVERIFIED:** L1's single `re.fullmatch` predicate removes this too — there is no input it
admits that `int()` then rejects. Fixing L1 and L3 separately would be two clauses where one does.

### M1 · Medium · INSTRUMENT · pre-existing, but this fold is its second consecutive demonstration — the guard has NO falsifier anywhere in the repository

```text
$ grep -rln "SHARD_INDEX" --include=*.py --include=*.sh --include=*.json --include=*.ts \
      scripts/ tests/ .claude/
(no output)
```

Nothing outside `.github/workflows/ci.yml` mentions `SHARD_INDEX`. The guard has no `--self-test`,
no mutation-manifest entry, and no caller that exercises it. `scripts/check-plan-code.py --mutate .`
mutates `scripts/*.py`; the one manifest matching `ci.yml` is `check-python-pin.json`, which uses it
as a *fixture*, not a subject.

`scripts/check-ratchet-contract.py` is the guard that requires every guard to have a `--self-test`
and a caller, and it cannot see this one by construction — `:191-194` builds its population from
`scripts/*.sh`, `.claude/hooks/*` and `scripts/*.py`. `.github/workflows/` is not in it. So the
repository's rule *every guard has a falsifier* is true of every guard the ratchet can reach, and
this guard escaped by living in YAML.

The consequence is observable rather than theoretical: this guard has now shipped wrong **twice in
two consecutive rounds** — round 5's L2 and this round's L1 — and on both occasions it was a human
reviewer that found it, with every gate green. An untested guard whose job is to prevent a silent
false green is the shape the repository treats as most expensive.

**Fix, UNVERIFIED (two shapes, and I have not sized either):**
*(a)* move the parse into `check-plan-code.py` — have the step pass `SHARD_INDEX`/`SHARD_TOTAL`
straight through (`--shard-index "$SHARD_INDEX" --shard-total "$SHARD_TOTAL"`, 0-based, converted
inside) so the validation lands where `--self-test` and `--mutate .` already reach it, and the
workflow holds no logic at all; or *(b)* leave it in YAML and widen
`check-ratchet-contract.py`'s population to `.github/workflows/*.yml`, which is the larger change
and does not by itself give the guard a test.
*(a)* also dissolves L2's "there are two spellings because one cannot import the other".

### Informational — the `N=0` message names the wrong operand

`SHARD_INDEX=0 SHARD_TOTAL=0` refuses with *"SHARD_INDEX=0 is not a valid 0-based index into
SHARD_TOTAL=0"*. The failing clause is `n < 1`; the sentence leads with `SHARD_INDEX`. It is not
wrong — there is no valid index into zero shards — but a reader debugging a matrix with no jobs is
pointed at the wrong variable. Not filed as a finding.

---

## 3. Answers to the six questions

**1 · Can anything still reach a wrong-but-valid spec?** **Yes — L1.** 750 non-ASCII decimal code
points are accepted; `٠`→`1/8`, `１`→`2/8`, `𝟛`→`4/8`, and `٠٠٠٠٠٠`→`1/8` defeats the leading-zero
rule as well. Everything else on the brief's list refuses: `+0`, `0x10`, a real trailing `\n`, `\r`,
`' 0'`, `'0 '`, `-1`, `00`, `0.0`, both empty, genuinely unset (`env -u`, not merely empty),
`SHARD_TOTAL` > 4096 and `SHARD_TOTAL` = 10²⁰. A NUL cannot occur: `execve` refuses an environment
value containing one (`ValueError: embedded null byte`). `SHARD_TOTAL=1` with `SHARD_INDEX=0` →
`1/1`, correct. The brief's `isdigit()` warning was the right place to look, and it is true in both
directions — see L1 for accept and L3 for the traceback.

**2 · Is `|| exit 2` reachable in every refusal path, and is rc=2 what the job reports?** **Yes**, as
far as the step script goes. A standalone assignment's exit status is the command substitution's, so
`||` sees it; there is no `local`/`declare` prefix to swallow it, and `set -e` does not change it
(`bash -e` reproduces every rc above identically). Measured refusal routes, all rc=2 from the
script: `sys.exit(msg)` (python rc=1 → `exit 2`), an uncaught `ValueError` traceback (python rc=1 →
`exit 2`), and `python3` missing entirely (rc=127 → `exit 2`). I could not construct a path where
python exits 0 with a wrong spec other than L1. **That the job then fails is NOT MEASURED** — a
non-zero step exit failing a GitHub job is standard behaviour I did not observe on a runner.

**3 · Did the rewrite break the legitimate path?** **No.** `0..7` map to `1/8..8/8`, all eight
distinct and complete (§1.2). Against the prior shipped form the only behaviour changes are
improvements or unreachable, except L1: `08` goes rc=1→rc=2, `18446744073709551616` goes accepted→
refused, `I=8 N=8` goes `9/8`→refused, `N=0` goes `1/0`→refused, `N=''` goes `1/`→refused. The one
narrowing is `SHARD_TOTAL` > 4096, now refused where the old form passed it through — not a
reachable regression, since GitHub caps a matrix at 256 jobs. L1 is the one direction where the
rewrite is *wider* than what it replaced.

**4 · The embedded Python's indentation.** Extracted with a YAML parser and **run**, per the brief —
no `dedent`, no reasoning about it. §1.1. It executes correctly; the first line of the `-c` string is
empty, which Python accepts, the body lands at 4 spaces, and there are no tabs. I could not produce
an `IndentationError`. Caveat in §1.6: PyYAML, not GitHub's parser.

**5 · Does `check-python-pin.py` still read `ci.yml`, and is rc=0 earned?** **Yes, and yes — proved
by a falsifier, not by the rc.** The exact concern the brief raises (backlog #227, comments at job-key
indentation) is why I did not accept the green. Two measurements:

```text
job_names / declared_pins / unreadable_jobs / unpinned_jobs, same parser, both trees:
  ece8d309  jobs=3 ['verify','mutation-sweep','mutation-sweep-complete'] pins={'3.12'}x3 unreadable=0 unpinned=[]
  68f6d7ea  jobs=3 ['verify','mutation-sweep','mutation-sweep-complete'] pins={'3.12'}x3 unreadable=0 unpinned=[]
```

Identical — the eight new comment lines inside the `run:` changed nothing it sees. And the falsifier,
on a `git archive` clone, deleting the `setup-python` step from `mutation-sweep` **only**:

```text
control (clone, untouched)        rc=0
mutant (step removed)             rc=1
  FAILED — 1 job(s) pin no Python version:
      ci.yml:mutation-sweep
```

It names the job. It is not passing because it stopped seeing it.

**6 · Anything else in the delta.** The dashboard entry's measured table is **correct** — I
re-measured all ten of its rows independently through the extracted block and every result matches
(§1.3). Its lay paragraph is accurate about the mechanism. Its `⚠` admission about putting the PR
red is a record I did not verify against the live checks (NOT MEASURED). `check-dashboard-entry.py`
rc=0. The round-5 Codex verdict is well-formed: `gate_ran: true`, `refused: false`, `model gpt-5.5`,
`head ece8d309`, `dirty` only `docs/explainers/questions.md`. The Codex half's findings reproduce.

---

## 4. What I tried to refute and could not

- **That the two round-5 halves reviewed different trees is a defect.** They did —
  `git diff a5fcd951..ece8d309` touches `ci.yml` and `check-plan-code.py`, so the Claude half never
  saw the `case` guard its Codex partner refuted. I tried to make this a finding and **it is not**:
  `plugins.md` says rounds 2+ **alternate** precisely so a half reviews the *fixes*, and that is
  exactly what happened. The method worked.
- **Shell injection through the env values.** The Python source is a fixed single-quoted literal and
  both values are read via `os.environ`; nothing is interpolated into the shell. GitHub expands
  `${{ strategy.job-index }}` into the environment, not into the script. No route.
- **Stdout pollution yielding a wrong shard.** A chatty `sitecustomize.py` does pollute `SPEC`
  (`SPEC=[note: something chatty\n1/8]`), but `parse_shard` then refuses it — the embedded newline
  defeats `^(\d+)/(\d+)$` and `.strip()` only touches the ends. Fails in the safe direction.
- **`--shard` absent silently meaning "whole manifest" by accident.** It is deliberate and explicit
  at `:1740`. Read, not run.
- **An out-of-range spec slipping past the deliverable.** `parse_shard('9/8')`, `('1/0')`, `('1/')`
  all refuse with a sentence.
- **A dropped or duplicated shard for legitimate matrix values.** All eight indices distinct and
  complete; round 5 had already proved the round-robin union, and I found nothing to reopen.
- **Any error in the brief's "already measured" list.** All of it reproduced. Nothing is false.

---

## 5. Table

| Severity | Deliverable or instrument | Caused by this fold? |
|---|---|---|
| **M1** — the guard has no falsifier; `check-ratchet-contract`'s population cannot reach `.github/workflows/` | Instrument | No — but this fold is its second consecutive demonstration |
| **L1** — `isdigit()` accepts 750 non-ASCII digits; `٠`→`1/8`; the ASCII-only leading-zero rule is bypassed; the message is false about the accept set | Deliverable (`ci.yml`) | **Yes** — a regression; the `case` guard it replaced refused these |
| **L2** — `SHARD_SPEC`'s `\d` has the same Unicode accept set; `--shard 1/٨` → `(1, 8)` | Deliverable (`check-plan-code.py`) | No — ships from `d74d1c2b`; makes L1 a class |
| **L3** — 128 code points pass `isdigit()` and make `int()` raise: a traceback, not the CANNOT RUN sentence | Deliverable (`ci.yml`) | **Yes** |

---

## 6. Verdict

**NOT CONVERGED.**

Three of the four findings are aimed at the **deliverable**, and `review-method.md:108` makes *a
finding in the deliverable* a CONTINUE on its own, judged by aim rather than severity. **This is not
a clean round at all**, so it is neither quiet round 1 nor quiet round 2: round 4 was quiet round 1,
round 5 reset the streak, and this round resets it again. After the fix for L1/L3, the next round
starts the two-consecutive-clean count from zero.

The fold does what it set out to do — Bash performs no arithmetic and the overflow class is gone,
not narrowed. What it did not do is bound the value: it swapped an ASCII byte class for a Unicode
character property and widened the accept set in the one dimension that still produces a
valid-looking wrong shard. The guard has now been wrong three times in three shapes, and M1 is the
reason that keeps being discovered by a reviewer instead of a gate.

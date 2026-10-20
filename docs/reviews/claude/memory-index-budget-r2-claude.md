# memory-index-budget — round 2, CLAUDE half

Primary subject: `a18486f1` ("Round 2's Codex half found a LIVE under-count, and my round-1 fix had
repaired the instance rather than the class") on branch `baseline-surveys` — **the FOLD of the r2
Codex half**, not the original guard. Rounds 2+ alternate so each half reviews the other's fixes
(`docs/plugins.md`), so everything below is aimed at the six folded claims G1–G6 and at what the
fold itself introduced or left. r1 and r2-Codex findings are not re-filed.

⚠ **THE TREE MOVED UNDER THIS REVIEW, AND I CHECKED WHETHER IT MOVED ON MY SUBJECT.** Mid-review
`.claude/hooks/check-memory-index-budget.sh` changed on disk and `HEAD` advanced to `91b6bbf3` ("A
review finding number is indistinguishable from a backlog id, and `.claude/hooks/` is a
reader-facing surface"). Measured: `git diff --stat a18486f1 91b6bbf3 -- scripts/ .claude/hooks/`
is `.claude/hooks/check-memory-index-budget.sh | 4 ++--`, and the diff is `r2 CODEX #3` →
`r2 CODEX finding 3` in two comments. **No behaviour changed**, so every finding below stands at
both tips. All measurements were taken in a detached worktree at `a18486f1`
(`git rev-parse HEAD` = `a18486f19b32…`); nothing in the main working tree was touched except this
file.

Instrument, all of it run:

- the guard's live run (`rc 0`, 22,238 characters in the worktree checkout) and its suite —
  **51/51 green**, the declared count;
- the **22 shipped mutations** through the real harness over a staged `HARNESS_TREE`
  (`scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`,
  `.github/workflows`, `.agents/skills`), manifests pruned to this one file and
  `EXPECTED_MUTATIONS` pinned to it: **`OK — 22 mutation(s), 22 killed, 22 attributed to the case
  each names, 0 survivor(s)`**, green control and re-control, 3.9 s;
- a **per-mutation attribution sweep**: each of the 22 applied, every `[FAIL]` line collected, to
  ask whether the named case is the only witness or merely one of several;
- **27 mutations of my own** against a proved-green control, of which **17 survive all 51 cases**;
- the hook driven over **14 payload shapes** against a sentinel guard returning `OVER BUDGET`,
  plus a legitimate-symlink invocation, a circular symlink, and a **two-repo layout**;
- `check-selftest-counts.py` (54 declared counts, every one verified by running it, this guard's 51
  among them), `check-ratchet-contract.py` (48 guards, OK), `check-guard-coverage.py` (OK),
  `check-plan-code.py --self-test` (178/178), `check-paid-caller-arrival.py --self-test` (32/32);
- the historical index at `dff6a3f0^` and the `dff6a3f0` diff, for every number in G6;
- `recall-llm.py`'s own `memory_files` / `load_triggers` / `corpus_verdict` symbols for the corpus
  figures — not a re-implementation of their rules.

**NOT RUN, stated loudly:** the full repo sweep (`--mutate .` over all 64 manifests). My scoped run
is a claim about this manifest only. I also did **not** run a controlled producer-boundary
experiment against the harness, so G5's open question stays open — see L2, which is about the
*stated bound*, not about resolving it.

⚠ **ONE RETRACTION, recorded because the method is the point.** My first search for the guard's CI
caller was `grep -rn … | grep -v … | head -20`; the 20 lines were consumed by two very long
`docs/backlog.md` rows and showed **no** workflow hit, and I was one step from filing a Blocking
saying the lagging half the hook's header cites does not exist. It does:
`.github/workflows/ci.yml:269` (`Memory index injection budget`) and `:272` (its self-test). The
population my grep showed was not the population it searched —
`measure-the-population-the-code-actually-sees`, on a review of a fold whose own author made five
measurement errors this session.

> **The fold is real work and its live defect fix is correct — G1 survives every attack I could
> construct, G3's stub is sound, and every number in G6 reproduces to the character. But the
> repair that the commit message calls the class fix is itself an instance fix: eight of the ten
> numeric fields in the three verdict messages still carry no value assertion, I measured seven
> survivors among them, and the FILE LABEL that r1 CODEX #2a was entirely about is unwitnessed in
> all three measuring arms — a guard that measures the wrong index and prints the right name
> passes 51/51 today. The hook's root fix trades Codex's wrong root for the opposite one and makes
> the new failure SILENT.**

---

## Blocking

**None.** The guard is green, its 22 mutations all die via the case each names, the required
`verify` steps pass, and the live defect G1 fixed is genuinely fixed. Nothing here must be fixed
to merge; three Highs should be, because each one re-opens a class an earlier round closed.

---

## High

### H1 — High. The file label is unwitnessed in ALL THREE measuring arms. Hardcoding the
### correct-looking name survives 51/51, which is exactly r1 CODEX #2a's "worse than no guard"

`scripts/check-memory-index-budget.py:38-40` states the property the fold claims:

```
⛔ EVERY VERDICT NAMES THE FILE IT MEASURED (r1 CODEX #2a). Only the CANNOT RUN arms did, and
repointing `INDEX` at a different corpus file left all cases green — a guard that measures the
wrong file and reports "every row arrives" is worse than no guard, and the reader could not tell.
```

The three measuring arms interpolate `{label}`:

```python
            f"OVER BUDGET — {label} is {n_chars:,} CHARACTERS against the harness's "      # :148
            f"WARNING: {label} is {n_chars:,} characters, within "                          # :155
        f"ok — {label} is {n_chars:,} characters, {limit - n_chars:,} under the harness's "  # :160
```

Measured — each of these three applied singly to a proved-green control, `{label}` replaced by the
literal `docs/memory/MEMORY.md`:

```
SURVIVED  rc=0 self-test: 51/51 cases passed  <- the OK arm names a HARDCODED path
SURVIVED  rc=0 self-test: 51/51 cases passed  <- the WARNING arm names a HARDCODED path
SURVIVED  rc=0 self-test: 51/51 cases passed  <- the OVER arm names a HARDCODED path
```

The one case that looks like the witness cannot be one. `:449-450`:

```python
        check("an OK verdict names the file REPO-RELATIVE, with no absolute prefix",
              ("docs/memory/MEMORY.md" in printed_ok, str(ROOT) in printed_ok), (True, False))
```

It is driven over the real `INDEX`, so it asserts that the literal `docs/memory/MEMORY.md` appears
— which a hardcoded literal satisfies perfectly. Shipped mutation 10 (`shown = "WRONG"`) dies only
because `"WRONG"` is not that literal; `shown = INDEX_LABEL` dies only on the out-of-repo fixture
in the CANNOT RUN case. Neither reaches the message arms, and I measured the consequence directly:

```
SURVIVED  rc=0 self-test: 51/51 cases passed  <- index_chars silently measures the MODULE INDEX,
                                                 ignoring the path it is given, for any file
                                                 named MEMORY.md
```

So the composite the docstring forbids — **measure one file, name another** — is reachable with a
green suite. This is the same vacuity shape as r1 CLAUDE L3 (`"docs/memory/MEMORY.md" in …`
satisfied by an absolute path) one level in: the fix asserted the *absence of the absolute prefix*
and left the *presence of the right name* provable by writing the right name down.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** drive `main()` over a constructed index whose basename
is `MEMORY.md` but whose directory is a temp dir, capture stdout, and assert the printed label
contains that temp directory's name and NOT the string `docs/memory/MEMORY.md`. Today that case
does not exist for any of the three arms; if it existed and passed, H1 is wrong.

### H2 — High. The parsed-field repair covers the two fields Codex named and leaves EIGHT of ten.
### Seven survivors measured. Same class, third consecutive round, and the commit calls it the class fix

`:276-285` is explicit that the instance/class distinction is the lesson being learned:

```
    # ⛔ THE NUMBER IS PARSED AND COMPARED AS A VALUE. Two rounds of substring assertions failed
    #   r2 CODEX #1: my repair — ban the literal total `1,241` — blocked ONE VALUE, NOT THE CLASS.
    # No substring assertion can fix this, because any needle is a suffix of infinitely many
    # renderings. Parsing the field and comparing an int is the only form that cannot be fooled.
```

The three arms render **ten** numeric fields: OVER has `{n_chars}`, `{limit}`, `{n_chars - limit}`
(`:148-150`); WARNING has `{n_chars}`, `{limit - n_chars}`, `{limit}`, `{100 * n_chars // limit}`
(`:155-157`); OK has `{n_chars}`, `{limit - n_chars}`, `{limit}` (`:160-161`). **Two** carry a
value assertion: the OVER overage, at two inputs (`:291-294`), and the OK headroom (`:295-297`).
The other eight have none, and the fold added none. Measured, each applied singly:

```
SURVIVED  rc=0 51/51  <- WARNING-arm headroom gains 1000   ({limit - n_chars + 1000})
SURVIVED  rc=0 51/51  <- WARNING-arm percentage inverted   ({100 * limit // n_chars} -> 111%)
SURVIVED  rc=0 51/51  <- WARNING-arm states a limit 9,000 higher than the one it compared against
SURVIVED  rc=0 51/51  <- OVER-arm reported SIZE gains 1000
SURVIVED  rc=0 51/51  <- OVER-arm states a limit 9,000 higher than the one it compared against
SURVIVED  rc=0 51/51  <- OK-arm reported SIZE gains 1000 (parsed headroom stays right)
SURVIVED  rc=0 51/51  <- OK-arm states a limit 9,000 higher than the one it compared against
```

The first of those is the *same defect in the other arm*: r2 CODEX #1 found `"990 under"` matching
`"10,990 under"` in the OK arm, and the WARNING arm's headroom — a field with the identical role —
was never given the same treatment. `after-fixing-search-for-the-class`: the repair was applied to
the two call sites in the finding rather than to the function's rendered output.

Why it matters beyond cosmetics: this guard's entire product is a number a reader acts on. A
verdict reading *"within 1,990 characters of the harness's 33,985-character limit (111% of
budget)"* while the arithmetic that chose the arm is correct is a message that misdirects the one
decision the guard exists to inform — how much room is left, and therefore whether to move rows.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** a case parsing each of the eight fields and comparing an
int at two distinct inputs — the same form already used for the two covered fields. If such cases
exist and the seven mutations above redden, H2 is wrong.

### H3 — High. The hook's root is derived from the SCRIPT's location, so the fix for r2 CODEX #3b
### turns a LOUD wrong answer into a SILENT one. Measured inversion against the pre-fix code

`.claude/hooks/check-memory-index-budget.sh:39-48`:

```bash
src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
  target=$(readlink "$src")
  case "$target" in
    /*) src="$target" ;;
    *)  src="$(dirname "$src")/$target" ;;
  esac
done
root=$(cd -P "$(dirname "$src")/../.." && pwd)
out=$(cd "$root" && python3 scripts/check-memory-index-budget.py 2>&1)
```

Codex's configuration was a symlink pointing **into** the repo (a launcher elsewhere, the real hook
inside), and resolution fixes it — I reproduced that: invoked through
`$H/bin/hooklink.sh -> $H/.claude/hooks/check-memory-index-budget.sh`, the sentinel fires.

The opposite configuration inverts. Two throwaway repos, A holding the real hook with an index that
is **fine**, B sharing it by symlink with an index that is **over**:

```
B/.claude/hooks/check-memory-index-budget.sh -> A/.claude/hooks/check-memory-index-budget.sh
```

A write to **B's** index, payload `{"tool_input":{"file_path":"…/B/docs/memory/MEMORY.md"}}`:

```
post-fix hook (a18486f1):   hook rc=0   nothing on stderr   -> SILENT
pre-fix  hook (a18486f1^):  ⚠ memory index budget (advisory, rc=1):
                            OVER BUDGET — repo B index is OVER
```

The pre-fix code was **right** for this layout, because `dirname "${BASH_SOURCE[0]}"` is the
directory the hook was invoked from. Resolution sends it to where the file lives. Both versions
derive the root from the script; neither derives it from the subject — the path in the payload, the
only thing that says which index was written.

⛔ **The new failure is in the direction the fold itself names as the dangerous one.** The hook's
own comment at `:27-30` says *"a silent miss here is the whole failure this hook exists to
prevent"*, and the guard's docstring at `:56-58` says a guard that *"fails toward good news … is
the direction that gets believed"*. Pre-fix, the wrong root produced `CANNOT RUN` — loud. Post-fix
it produces nothing at all.

The same wrong-subject error is already reachable without any symlink, and I measured it on this
machine:

```
harness-served index  /Users/kujinlee/.claude/projects/…/memory/MEMORY.md
  -> resolves to      …/youtube-playlist-summaries-cloud/docs/memory/MEMORY.md   inode 192223183
worktree copy         …/scratchpad/wt-r2/docs/memory/MEMORY.md                   inode 192312554
```

A session working in a worktree — which `docs/dev-process.md` and this review's own brief mandate —
writes the worktree copy; the hook matches `*/docs/memory/MEMORY.md`, resolves root to that
worktree, and reports on a file nothing injects. The injected index could be over budget
throughout.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** derive the root from the matched `file_path` (strip the
`docs/memory/MEMORY.md` suffix) or from `git -C "$(dirname "$path")" rev-parse --show-toplevel`,
and the two-repo probe above fires on B. If it already did, H3 is wrong.

---

## Medium

### M1 — Medium. `_field` CAN be fooled. A float rendering survives 51/51, so "the only form that
### cannot be fooled" (`:285`) is an overclaim

```python
    def _field(msg: str, after: str) -> int | None:
        """PURE. -> the integer in `msg` immediately after `after`, or None. Commas stripped."""
        m = re.search(re.escape(after) + r"\s*([\d,]+)", msg)                      # :288
        return int(m.group(1).replace(",", "")) if m else None
```

`[\d,]+` stops at any character outside the class, so the parse reads a **prefix** of the rendered
field — the same structural weakness as the suffix matching it replaced, mirrored. Measured:

```
SURVIVED  rc=0 51/51  <- overage rendered as a FLOAT: f"{float(n_chars - limit):,}" -> "7.0" / "3,766.0"
SURVIVED  rc=0 51/51  <- _field anchors on the LAST match instead of the first
```

The honest version of the claim is narrower and still worth having: parsing a field defeats every
mutation that changes the field's VALUE, which is the class r2 CODEX #1 exhibited. It does not
defeat one that changes its RENDERING. Two attacks the brief asked for do fail, and I report that:
a negative field (`{limit - n_chars:,}` → `"-7"`) is **killed**, because `[\d,]+` cannot start at
`-` and `re.search` finds no second anchor, so `_field` returns `None`; a trailing period is read
correctly.

⚠ Note the asymmetry the measurement exposes: the OK arm keeps its old substring case at `:274`
(`"990 under" in …`) *beside* the parsed one, and that pair is what kills the float in the OK arm.
The OVER arm has only the parsed case, which is why the float survives there. The weaker assertion
is doing work the stronger one does not.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** anchor the field end — `([\d,]+)(?![\d.,])` or a parse
that rejects a trailing `.` — and re-run the float mutation; it should redden.

### M2 — Medium. Nothing witnesses that `--self-test` reaches the suite. Deleting the dispatch arm
### gives rc 0 with NO TALLY LINE, and the mutation harness would score it a survivor

```python
    if "--self-test" in argv:                   # :247
        return _self_test()                     # :248
```

Measured, that arm deleted:

```
SURVIVED  rc=0 NO TALLY LINE  <- the self-test DISPATCH arm is deleted
```

`--self-test` then falls through and measures the live index: rc 0, an `ok —` line, and no
`self-test: n/n cases passed`. No case drives `main(["--self-test"])` — the fold deliberately
avoids it (`:382-383`, the r1 recursion), and the new stub case (`:395-403`) asserts the suite is
**not** entered. So the suite's own entry point is the one behaviour it cannot see, and
`check-plan-code.py` decides a kill from the child's rc and its `[FAIL]` lines (`:2159-2190`), both
of which say "green" here.

⚠ **The repo does catch it, elsewhere, and that is the finding's real shape.**
`scripts/check-selftest-counts.py` runs each suite and reads its printed total — I confirmed it
covers this guard (`54 script(s) declare a count, every one verified by running it`), so a vanished
tally reddens there. The gap is that the guard's 51 cases and its 22-mutation manifest both report
full coverage of a file whose dispatch is guarded only by a sibling, and the manifest is what the
fold's "22 killed, 0 survivors" claim rests on.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** stub `_self_test` to return a sentinel and assert
`main(["--self-test"])` returns it — the mirror of the stub already written at `:395-403`, using
the mechanism the fold has already proved safe. If that case exists, M2 is wrong.

### M3 — Medium. The advisory is written to stderr at exit 0 — the channel this repo measured as
### not reaching the model, with the remedy sitting in the same directory

`.claude/hooks/check-memory-index-budget.sh:52-55`:

```bash
if [ "$rc" -ne 0 ] || printf '%s' "$out" | grep -q '^WARNING'; then
  printf '⚠ memory index budget (advisory, rc=%s):\n%s\n' "$rc" "$out" >&2
fi
exit 0
```

`.claude/hooks/surface-recall.sh:35-38` — a sibling hook, **same event (PostToolUse)**, same
advisory intent:

```
# ⛔ STRUCTURED JSON, NOT PLAIN STDOUT. Measured 2026-09-29: a hook's plain stdout at exit 0 reaches
# the USER'S TRANSCRIPT, not the model's context. The matcher's audience is the model, so plain
# stdout puts it in the one place it cannot work. This repo has a name for that defect — a gate's
# channel can be weaker than the gate.
```

and `:112` is the remedy, five lines of python emitting
`{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext": …}}`. The new hook uses
neither that nor plain stdout; it uses fd 2 at exit 0. ⚠ **Stated rather than overstated:** I did
not measure what Claude Code does with PostToolUse **stderr** at exit 0 — the repo's measurement is
about stdout, and I will not relay a neighbouring measurement as if it covered this one. What is
measured is that the two hooks make opposite choices for the same job, and that
`docs/memory/a-gates-channel-can-be-weaker-than-the-gate.md` exists because of this exact class.
It is also a `one-rule-one-place` divergence: two mechanisms for "advise at PostToolUse", and the
newer one did not read the older.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** register the hook, grow the index past budget, and
confirm the advisory appears in the model's context (not only in transcript mode). If it does, M3
is wrong and the comment in `surface-recall.sh` needs narrowing.

### M4 — Medium. `check("INDEX is the file the harness symlink actually serves", INDEX.is_file(), True)`
### proves existence, not identity — and I measured it passing while false

`:418`:

```python
    check("INDEX is the file the harness symlink actually serves", INDEX.is_file(), True)
```

The name claims identity with the harness-served file; the observation is that a file exists at
that path. In the worktree where I ran the suite, the case passed and the claim was false — the
inodes in H3 differ (192223183 vs 192312554). `a-case-can-pass-for-an-ambient-reason`: the tell is
NAME versus BODY, and here the body cannot see the subject the name is about.

This is not nit-picking a label. `ROOT` is `pathlib.Path(__file__).resolve().parent.parent`
(`:89`), so the guard measures *its own checkout's* copy by construction. Exactly one checkout on
the machine is the one the harness symlink resolves to; in every other, the guard reports on a file
no session loads, with all 51 cases green. CI's own comment acknowledges the committed/working-tree
half of this (`ci.yml:253-259`) but not the several-checkouts half.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** compare `INDEX.stat().st_ino` with the inode of the
resolved harness memory directory when that path exists, and report CANNOT RUN (never OK) when they
differ; or rename the case to what it proves. If the case asserted inode identity and passed, M4 is
wrong.

### M5 — Medium. The hook has no self-test and no mutation entries, and the precedent for covering
### exactly this kind of `.sh` seam already ships

The brief asks whether that is acceptable for an unregistered advisory hook. **It is a real gap,
and the repo has already decided this question against itself.** `ci.yml:277-281` says
`check-ratchet-contract`'s population is `scripts/check-*.py` so *"it cannot see a `.sh` file at
all"* — and the answer built for that was `scripts/check-surface-recall.py`, in the ratchet's own
48-guard list, described as *"THE ONLY GATE THAT READS BOTH SIDES OF THE MATCHER/HOOK SEAM, and it
exists because two LIVE defects lived there with 188 self-test cases and 91 mutations on the python
side alone"*. The same sentence is now true here: 51 cases and 22 mutations on the python side,
zero on the `.sh`.

Three hook behaviours are unwitnessed, and each was written *in response to a finding*:
the pattern list `*/docs/memory/MEMORY.md|docs/memory/MEMORY.md` (`:32`), the symlink loop
(`:39-47`), and `grep -q '^WARNING'` (`:52`) — which silently depends on the guard's warn message
starting with that exact token at `:155`. A rename of that prefix breaks the hook and reddens
nothing.

My 14-payload probe, for the record (sentinel guard returning OVER BUDGET, rc of the hook always 0):

| payload `tool_input.file_path` | advisory |
|---|---|
| absolute path | FIRED |
| `docs/memory/MEMORY.md` | FIRED (r2 CODEX #3 fixed) |
| `./docs/memory/MEMORY.md` | FIRED |
| `a/../docs/memory/MEMORY.md` | FIRED |
| trailing newline | FIRED (command substitution strips it) |
| `sub/docs/memory/MEMORY.md` | FIRED |
| **another repo's absolute path** | **FIRED — about THIS repo's index** (see L7) |
| `docs/memory/memory.md` | SILENT (see L7) |
| `docs/memory/MEMORY.md.bak` | SILENT (correct) |
| `file_path` a LIST | SILENT |
| `file_path` null | SILENT |
| no `tool_input` | SILENT |
| malformed JSON | SILENT |
| empty stdin | SILENT |

**The circular-symlink attack FAILS and I report it as such:** a→b→a cannot be executed at all
(`bash` refuses with ELOOP before line 1), so the `while [ -L "$src" ]` loop is never entered. The
loop terminates for every chain bash can load.

**OBSERVATION THAT WOULD MAKE M5 FAIL:** a `--self-test`-style harness for the hook (or a
`check-memory-index-hook.py` on the `check-surface-recall.py` model) that reddens when the pattern
list drops the relative form, when root resolution changes, or when the `^WARNING` token moves.

---

## Low

### L1 — Low. `OVERFLOW_TARGET in msg` is tautological, and the suite says so about itself 15 lines earlier

`:298-299`:

```python
    check("the OVER message names the remedy file",
          OVERFLOW_TARGET in budget_verdict(L + 1, L)[1], True)
```

Both sides read the same constant, so no value of `OVERFLOW_TARGET` can fail it. Measured:

```
SURVIVED  rc=0 51/51  <- OVERFLOW_TARGET repointed at docs/memory/nonexistent-target.md
SURVIVED  rc=0 51/51  <- the OVER arm's REMEDY sentence replaced by the bare constant
SURVIVED  rc=0 51/51  <- the WARNING arm stops naming the remedy file at all
```

The suite states the governing rule at `:311-314` for the exit codes — *"a case that reads the
constant it is testing is satisfied by whatever that constant happens to say"* — and then breaks it
for the remedy path. `docs/memory/slice-history.md` does exist today (7,541 bytes), so nothing is
live; the remedy is one rename away from pointing nowhere with a green suite.

**FAILS IF:** a case asserts the literal `docs/memory/slice-history.md` (as `:492` does for
`LIMIT_CHARS`) and that `(ROOT / OVERFLOW_TARGET).is_file()`.

### L2 — Low. G5's bound is INCOMPLETE: there is a third consistent candidate, and the fixture it
### names cannot separate it

`:181-189` states the bound as a two-way question — code points vs UTF-16 units, 26,930 vs 26,931,
both rounding to the reported 26.3KB — and names `24,984 × "x"` plus one astral character as the
fixture that would settle it. Measured over the historical index at `dff6a3f0^`:

| candidate | value | /1024 | prints |
|---|---|---|---|
| code points | 26,930 | 26.2988 | 26.3KB ✓ |
| UTF-16 units | 26,931 | 26.2998 | 26.3KB ✓ |
| NFC length | 26,930 | 26.2988 | 26.3KB ✓ |
| **NFD length** | **26,934** | 26.3027 | **26.3KB ✓** |
| grapheme approximation | 26,930 | 26.2988 | 26.3KB ✓ |
| UTF-8 bytes | 27,805 | 27.1533 | 27.2KB ✗ |

NFC and the grapheme approximation are degenerate on this corpus (0 combining marks, 0 variation
selectors, 0 ZWJ), but **NFD length is a genuinely different function of the content** — 26,934,
four more — and it is consistent with both observations the docstring relies on. ⛔ And the named
fixture cannot separate it: `24,984 × "x"` plus one astral character is NFD-invariant, so it
distinguishes code points from UTF-16 units and leaves NFD exactly where it was. A fixture
containing a decomposable character (`é` as U+00E9) is what would.

`a-bound-enumerates-what-is-witnessed` is the recorded class, including its sharper half — *a
caveat headed "stated rather than hidden" that is wrong is worse than none*. The margin is ~4
characters against 2,747 of headroom, which is why this is Low and not Medium.

**FAILS IF:** a normalisation-sensitive fixture is added and the stated bound names every candidate
consistent with the two measurements.

### L3 — Low. Six leftovers still say "byte(s)" about a character count, including the live
### verdict's own message. The unit fix was again applied to the instances in the finding

`:52-54` claims the opposite:

```
⟳ r1 CLAUDE L1: this exclusion was itself stated in BYTES (38 over 200) against a rule the
harness states in CHARACTERS — the same unit error as H1, which makes it a CLASS and not an
instance. Both are now characters.
```

Still in bytes at `a18486f1`:

- `:303` `check("one byte PAST the limit is over", …)`
- `:306` `check("one byte BELOW the warn threshold does not warn", …)`
- `:429` `check("main() fails a file ONE BYTE over, measured end to end", …)`
- `:495` `f"(it is {live if live is not None else 'UNREADABLE'} bytes)"` — **the message a reader
  sees**, reporting the character count in bytes; it printed `(it is UNREADABLE bytes)` during my
  attribution sweep
- `scripts/mutations/check-memory-index-budget.json`, entry 9 — `"main() under-reports the size
  by one byte, so an index one over the limit passes"`
- `:420-422` `"The coarse 2000-vs-1000 pair below let a `size - 1` mutation in main() survive: a
  real 24,986-**byte** index then passed"`

All are labels over ASCII fixtures, so no behaviour is wrong — but the fold's claim is that the
unit error was fixed as a class, and the class is "every place this file states the unit".

**FAILS IF:** `grep -in 'byte' scripts/check-memory-index-budget.py` (case-insensitive — `:429`
says `ONE BYTE`, which a case-sensitive grep misses) returns only the two places
genuinely about bytes (`:345-346`, the tautology check, and the `read_bytes` fixtures).

### L4 — Low. "Rows" is used without a definition, and ONE bullet accounts for all three ±1
### discrepancies this number has had

Measured over `dff6a3f0^`:

| quantity | bullets (`- `) | index-entry rows (`- [`) | shipped figure |
|---|---|---|---|
| index size | 146 | **145** | 145 (`:17`, `:49`) |
| moved to `slice-history.md` | 29 → 4,957 / 4,986 chars | **28 → 4,912 / 4,940** | 4,912 / 4,940 ✓ |
| lost to truncation past char 24,958 | 9 | **8** | 8 (`:7`, `:19`) |

The single non-entry bullet is `- **Older slices, all MERGED unless marked:**`, and it is the same
line in all three rows of that table — it is the 29th "row" that produced the retired 4,985, it is
the 146th bullet, and it is the 9th thing past the cut. Every shipped figure is correct under
"index-entry row" and every one is off by one under "bullet", and the file never says which it
means. Three numbers, one definitional gap, and the fold's commit message calls 4,912 the "third
version of this number".

**FAILS IF** the docstring says `- [` rows, or the guard counts them.

### L5 — Low. The suite's own comparator can be weakened to pass, and `_field`'s None path then
### becomes invisible

`:261-267`:

```python
    def check(label: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
```

Measured: `if got == want or got is None:` leaves **51/51 green**. Because `_field` returns `None`
on no match (`:289`), that one edit converts both parsed-field cases — the fold's headline repair —
into vacuous passes, and the mutation harness reads the suite's own tally, so it cannot see it. I
file this Low because mutating a suite's comparator is at the edge of what the manifest is for;
`a-test-that-cannot-fail` is the recorded class and the repo does already pin a FAIL-line format,
so it is inside the fence rather than outside it.

**FAILS IF** a case asserts `check`'s own discrimination (e.g. that a deliberately failing
comparison increments `fail`), which no case does today.

### L6 — Low. Two manifest entries claim more than they measure. One is redundant after its own
### repair; one's label is refuted by a sibling case

From my per-mutation attribution sweep (every entry goes red via the case it names — attribution is
sound, and I confirm the fold's 22/22):

- **Entries 14 and 17** redden **exactly the same two cases** (`the OVER message's overage is the
  DIFFERENCE…` and `the same field at a SECOND input…`). Entry 17 (`+ 1000`) was a distinct
  behaviour only against the *substring* assertion it was filed to refute; against the parsed
  assertion it adds no observation entry 14 does not already force. It documents the suffix class,
  which is worth something — but `EXPECTED_MUTATIONS` went 16 → 22 and one of those six is
  coverage-neutral.
- **Entry 19** is named *"WARN_FRACTION drifts by a near-miss a threshold fixture cannot see"*, and
  the case at `:406-407` repeats the claim (*"pinned so a near-miss like 0.9004 cannot slip"*).
  Measured, `WARN_FRACTION = 0.9004` reddens **two** cases, the second being the threshold fixture
  at `:408-409`: `int(1001 × 0.9004) = 901 ≠ 900`. The pin is fine; the justification written beside
  it is false at the inputs the suite actually uses.

**FAILS IF** entry 17 reddens a case entry 14 does not, or entry 19 reddens only its own case.

### L7 — Low. Two hook matcher edges: a case-insensitive filesystem, and another repo's index

Measured on this machine: the filesystem is **CASE-INSENSITIVE** (`CaseTest.txt` is found as
`casetest.txt`). The hook's `case` patterns are case-sensitive, so a write to
`docs/memory/memory.md` lands on `MEMORY.md` and the hook is **SILENT** — the same silent miss as
r2 CODEX #3, through a different door. Marginal in practice (tool writes echo the path they read),
and listed for completeness rather than as work.

In the other direction, `*/docs/memory/MEMORY.md` matches *any* repository's index, and the hook
then measures its own: a write to `/tmp/other-repo/docs/memory/MEMORY.md` **FIRED** an advisory
naming this repo's file. The owner has at least one sibling checkout
(`~/code/agentic-ai-docs/yps-sync-test/`), so this is reachable. It is a false advisory, not a false
green, which is why it is Low — but it is the same root cause as H3: the subject is in the payload
and the hook does not use it.

**FAILS IF** the hook derives its root from the matched path, which also fixes H3.

---

## Claims that SURVIVED attack, reported because a review that only accuses has not been run

- **G1 — `newline=""` is sufficient, and I tried to break it.** Universal-newline translation only
  changes a count for `\r\n` (two characters to one). Measured, guard vs default `read_text`:
  lone `CR ×9` 18/18, `U+2028 ×9` 18/18, `U+2029 ×9` 18/18, `CRLF ×9` **27/18**. Python's universal
  newlines handle only `\n`, `\r`, `\r\n`, so the Unicode separators were never at risk and a lone
  `\r` is 1→1. The fix closes the whole class for counting purposes. A UTF-8 BOM is counted as one
  character (`b"\xef\xbb\xbfabc"` → 4); whether the producer does is unknown and `encoding="utf-8-sig"`
  survives 51/51, but `MEMORY.md` carries no BOM, so this is latent and I do not file it.
- **G3 — the stub is sound.** The module global is restored in a `finally` (`:400-401`) and the
  restoration happens before the assertion at `:402`, so a raising case cannot leak the lambda into
  later cases. `(rc_both, _selftest_calls) == (2, [])` is satisfiable for the wrong reason in
  exactly one way — deleting the dispatch arm entirely — which is M2, a gap in a *different*
  behaviour, not a weakness in this case. Shipped mutation 18 is uniquely attributed.
- **G6 — every number reproduces.** Historical index at `dff6a3f0^`: **27,805 bytes, 26,930
  characters, 145 index rows, 35 over 200 characters, longest 602**, one non-BMP character (🔴) and
  therefore 26,931 UTF-16 units. Moved rows: **28 → 4,912 without line endings, 4,940 with one
  each**; the whole section 40 lines → 5,950 + 40 = **5,990**, exactly as claimed; and
  5,989 removed − 295 added = 5,694 = 26,930 − 21,236, so the arithmetic closes. Corpus via
  `recall-llm`'s own symbols: `memory_files` **163**, `load_triggers` **159**. The cut-point pair is
  internally consistent — `len(t[:24958].encode())` is **exactly 25,771** — and char 24,958 is a
  line boundary immediately before `- [Ask-choices — #186]`, with **8 index rows and 1 section
  bullet** after it. Everything in G6 is sound; L4 is about the word "rows", not the arithmetic.
- **The 22-mutation result is real.** `OK — 22 mutation(s), 22 killed, 22 attributed to the case
  each names, 0 survivor(s)`, green control and re-control. No entry is attributed to a case other
  than the one it names. Of the four pairs deliberately sharing a source line, **three are
  genuinely two behaviours** — (4 bytes / 16 CRLF), (3 literal / 20 round), (21 UnicodeDecodeError /
  22 OSError), each pair reddening a different case set — and the fourth (14 / 17) is L6.

---

## Verdict

**NOT CONVERGED** — on three Highs and five Mediums, none mechanical.

The fold's live fix is correct and its evidence is better than the round before it: G1 closes a 33%
under-count in the dangerous direction and survives every separator, BOM and normalisation attack I
could build; G3's stub is sound; and every one of G6's eleven numbers reproduces to the character,
including the cut-point pair whose byte and character halves agree exactly.

What has not converged is the shape the fold's own commit message names as its lesson. **H2 is
`a-filed-finding-s-proposed-fix-is-a-hypothesis` for the third consecutive round on the same
function:** r1 CLAUDE N1 found one vacuous field, r2 CODEX #1 found the repair blocked one value,
and the repair for *that* parsed the two fields Codex named while eight remain unasserted and seven
measurably survive. **H1 is worse, because it is not a cosmetic field:** r1 CODEX #2a's entire
subject was a guard that measures the wrong file and reports the right name, the docstring opens by
claiming every verdict names the file it measured, and hardcoding the correct-looking literal into
all three measuring arms passes 51/51. **H3 is the fold's own direction-of-failure rule turned on
itself** — the symlink repair is right for Codex's layout, wrong for the inverse, and the new wrong
answer is silent where the old one was loud.

The pattern across all three is one thing: **this guard's cases are strong about the arm chosen and
weak about everything the arm says.** The rc is witnessed at the boundary, at the warn threshold, at
two limits, end to end and over a constructed index. The message — which is the entire product, the
number a reader acts on and the filename that tells them what it is about — is witnessed in two
fields out of ten and in none of the three labels. That is not five more cases; it is one case
shape applied to every rendered field, and it would have caught r1 CLAUDE N1, r2 CODEX #1, H1 and
H2 in a single stroke.

The guard is worth having. The defect it found was real, the harness around it is honest, and the
author has now corrected their own numbers three times in public, which is the behaviour this
process is for. The remaining work is to stop fixing the fields the last reviewer happened to name.

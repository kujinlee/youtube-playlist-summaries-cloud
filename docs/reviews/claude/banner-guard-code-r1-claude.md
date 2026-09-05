# Claude adversarial code review — banner guard inverse, round 1

**Subject.** `scripts/check-banner-armed.py` and `.claude/hooks/block-idle-stop.sh` on branch
`backlog-95-banner-guard` (`git rev-parse --abbrev-ref HEAD`).

⚠ **THE SUBJECT MOVED DURING THIS REVIEW, AND EVERY MEASUREMENT BELOW IS RE-STATED AGAINST HEAD.**
I began against `c72140dc` (declared `# 55 cases`, suite 55/55). Mid-review, `e0b11c94`
*"An attempted edit is not an edit (code review round 1)"* — the fold of the Codex half — landed on
the branch and the file grew to `# 61 cases`. **All mutation sweeps and probes in this document were
re-run against `e0b11c94` and the numbers here are that build's**, except where a finding explicitly
concerns the earlier state. Two of my own round-1 observations were resolved by that fold before I
filed (the directory case, independently probed `True` at `c72140dc`); they are recorded under
*Claims I verified as CORRECT* rather than as findings.

**What I ran.** `python3 scripts/check-banner-armed.py --self-test` → **61/61**, exit 0.
`bash -n .claude/hooks/block-idle-stop.sh` → clean. 39 source mutations applied to temp copies of
the delivered files, each re-running the delivered suite. An 18-cell execution matrix of the hook
with stub children. Probes of `_edit_inside_repo` against a real symlinked fixture tree. A corpus
pass over **700 transcripts** under `~/.claude/projects/`.

**Method note on the mutation sweep.** Every "SURVIVED" below means: the named source line was
weakened on a temp copy, the *delivered* suite was executed against the weakened copy, and it
printed `N/N … passed` with exit 0. A control run of the unmutated copy passed first.

---

## Findings

### H1 — Blocking/High · The `total == 0 → CANNOT RUN` mapping, which two review rounds were spent establishing, is not tested. The case that claims to test it never parses a plan.

**Severity: High.**

**Claim.** Spec §4.3 exists because v1 "imported `count_steps()` then re-derived a *different*
meaning from its return value — the shared-function-holding-half-a-contract shape", and mandates
*"Map `total == 0` to `CANNOT_RUN`"*. That mapping lives at `scripts/check-banner-armed.py:357`:

```python
return None if total == 0 else (done, total)
```

Mutating `:357` to `return (done, total)` — i.e. reinstating exactly the defect §4.3 was written to
prevent — leaves the suite at **61/61, exit 0. SURVIVED.**

**Evidence.** The case that names this behaviour is `:564-565`:

```python
case("F3 armed + a plan parsing to zero checkboxes is CANNOT RUN, never quiet",
     decide([], armed=True, steps=None)[0] == CANNOT_RUN)
```

It passes `steps=None` **directly into the pure function**. No plan is parsed, `count_steps` is never
called, and `_plan_steps` is never entered. The case tests `decide`'s handling of a `None` it was
handed; the spec's F3 condition is *"armed · plan parses to **zero checkboxes** · edited"*. Those are
different propositions, and the delivered one cannot discriminate the fix. This is the project's own
recorded *fixing a PREMISE is not covering the BRANCH* shape.

The one case that does execute the real loader — F4 at `:636` — builds a fixture plan with four
checkboxes (`:620`), so it never reaches `total == 0` either.

**Smallest fix.** In the F4 fixture block, add a second run against a plan file containing prose and
no `- [ ]` checkboxes, asserting `run_decide(...) == CANNOT_RUN`. The fixture machinery (patched
`ROOT`/`SENTINEL`, copied `check-plan-progress.py`) already exists at `:611-640`; this is one extra
`write_text` and one extra `run_decide`.

---

### H2 — High · `BANNER_RC` can be deleted from the hook's exit arithmetic and the suite stays green. The guard would then print its warning to a stream the human is never shown — which is the exact failure backlog #95 exists to detect.

**Severity: High.**

**Claim.** `F6` (`:645`) proves the guard is *invoked* before the blocking check. Nothing proves its
**result** reaches the hook's exit code. Mutating `.claude/hooks/block-idle-stop.sh:71` from

```bash
if [[ "$BANNER_RC" != "0" || "$CI_RC" != "0" ]]; then
```

to `if [[ "$CI_RC" != "0" ]]; then` leaves the suite at **61/61, exit 0. SURVIVED.**

**Why that is not cosmetic.** By the hook's own contract (`block-idle-stop.sh:15`, and `:68-70`),
exit 0 allows the stop and exit 1 is *"Claude Code's non-blocking error, which shows stderr to the
human"*. With `BANNER_RC` dropped, an unblocked stop exits **0**, and the warning `check-banner-armed`
wrote to stderr is discarded. The guard would keep running, keep logging, and keep reporting success
while reaching nobody — *"the banner existed on every armed step and reached nobody"*
(`check-banner-armed.py:36-37`), one layer out. The slice's own premise is that a mechanism can work
and be unarmed; the delivered instrument cannot see that happen to itself.

**Corroborating evidence that the delivered code is correct today.** I executed all 18 combinations
of `(BANNER_RC, PLAN_RC, CI_RC) ∈ {0,1,2}×{0,1}×{0,1,2}` with stub children. Blocking precedence
holds in every cell: `PLAN_RC != 0 → hook exit 2`, unconditionally; the banner guard never produces
exit 2; `BANNER_RC != 0 → exit 1` whenever the stop is not blocked; and the banner stub's stderr is
emitted before the plan stub's in all 18. **The delivered behaviour is right. The guard on it is
absent.**

**Smallest fix.** Extend F6 with a third structural assertion — the hook text contains
`"$BANNER_RC" != "0"` — in the same style as F6b's `"$ROOT/scripts" not in _hook` at `:647`. This
stays inside the structural-only scope the spec fixed for F6 (§5) and costs one line.

---

### H3 — High · The `unarmed` class — the guard's only previously-shipped behaviour — has no execution coverage at all. Three separate mutations that silence or mislabel its log line all survive.

**Severity: High.**

**Claim.** §7's stated purpose for the log change is that *"`reason` discriminates the two warning
classes"*, and that dropping the `if banner:` gate is what lets the new class be recorded. Only the
**new** class is executed by any test. Three mutations, all in `run_decide` at `:411-418`:

| mutation | effect | result |
|---|---|---|
| `:418` `if True:` → `if not banner:` | reinstates a gate that suppresses **`unarmed`** logging | **SURVIVED 61/61** |
| `:414` `reason = "unarmed"` → `"unbannered"` | the two classes become indistinguishable in the log | **SURVIVED 61/61** |
| `:412` `banner = highest_banner(texts or [])` → `banner = None` | every warning logs as `unbannered` | **SURVIVED 61/61** |

**Evidence.** `log_line` is unit-tested at `:520-522`, but that case passes the reason in as an
argument and asserts it comes back out — it verifies the *format string*, not the state→reason
mapping. F4 (`:636-639`) is the only test that executes `run_decide`, and it asserts
`endswith("\tunbannered\t3 unticked")` — one class, one path. The `unarmed` branch at `:413-414` is
executed by nothing.

**Why this matters more than ordinary coverage.** §7's argument for warn-only mode is *"the rate is a
number"*. A silenced or mislabelled `unarmed` column makes that number wrong in the direction of
under-reporting, and the log is gitignored (`.gitignore:102`) — nobody diffs it, so the loss is
invisible. This is the same defect §7 was written to fix (a class the log cannot express reads as
never having fired), reintroduced on the other class.

**Smallest fix.** One more `run_decide` fixture run inside the existing `:611-640` block: unset the
sentinel (or point it at nothing), feed a transcript whose only assistant text is
`## ▶ STEP 2 of 5 — x`, and assert the appended line ends `\tunarmed\tSTEP 2 of 5`.

---

### M1 — Medium · `_armed()` fails OPEN on an unreadable sentinel. The module docstring says the opposite, in capitals.

**Severity: Medium.**

**Claim.** `check-banner-armed.py:60-62` states *"FAILS CLOSED ON ITS OWN BLINDNESS … A check that
cannot reach what it measures is never a pass"*. `:384-388` does not:

```python
def _armed() -> bool:
    try:
        return _armed_from_text(SENTINEL.read_text())
    except OSError:
        return False
```

**Measured.** With a real fixture — armed sentinel, plan with one unticked step, a transcript
containing an in-repo `Edit` and no banner — `chmod 000` on `.claude/executing-plan` produces
**exit 0 (QUIET)**, no message, no log line. With the sentinel readable, the same input produces
WARN. So the guard goes silent in precisely the state it exists to police, and the silence is
indistinguishable from "nothing was armed".

The blanket `except OSError` conflates `FileNotFoundError` — the overwhelmingly common and correct
QUIET case — with `PermissionError`, `IsADirectoryError` and `UnicodeDecodeError`, which are
blindness. §4.2 and §4.4 both reason carefully about what `armed` means; neither considers the
sentinel being unreadable.

Mutating `:387` to `return True` also survives (**61/61**), confirming nothing tests `_armed()`'s I/O
behaviour in either direction — only `_armed_from_text`, which is pure.

**Smallest fix.**

```python
    except FileNotFoundError:
        return False        # nothing armed — the normal case
```

and let other `OSError`/`UnicodeDecodeError` propagate into the existing `_plan_steps`/`decide`
blindness path, or return a third state that `decide` maps to `CANNOT_RUN`.

---

### M2 — Medium · `except Exception` discards the loader's own diagnostic, and the message that replaces it names three causes, none of which is the actual one.

**Severity: Medium.** *(This is item 4 of the brief, answered both ways.)*

**The good half, measured.** With `scripts/check-plan-progress.py` (a) truncated to a `SyntaxError`
and (b) deleted outright, the guard reports in its own vocabulary and exits 2 both times:

```
CANNOT RUN: .claude/executing-plan names a plan this check could not measure — missing,
unreadable, or containing zero `- [ ]` step checkboxes. TREAT THIS AS NOT RUN — …
```

So the spec §4.3 requirement — *"a rename would otherwise kill the working half with a traceback
instead of this file's own TREAT THIS AS NOT RUN vocabulary"* — is met. **`except Exception` at
`:358` does not fail open.**

**The defect.** The message is *false about the cause*. In both runs the plan file was present,
readable, and contained checkboxes; what broke was the borrowed module. `_load_plan_progress`
(`:326-339`) raises a deliberately-authored ImportError —

```python
f"scripts/check-plan-progress.py no longer defines {n} — this guard borrows the "
f"checkbox rule rather than copying it."
```

— and `:358` throws that string away, so **it can never reach any reader**. Confirming the point,
mutating `:335` (`if not hasattr(mod, n)`) to skip the contract check entirely leaves the suite at
**61/61 — SURVIVED**; so does narrowing `:358` to `except OSError`. The whole borrowed-import error
path is unexecuted by the suite and its one authored diagnostic is unreachable.

Because the message names only plan-file causes, the reader of a real failure would go and inspect a
plan file that is fine. That is the *"true about the name, silent about the layer"* shape.

**Smallest fix.** Capture the exception and widen the message by one clause:

```python
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
```

or, minimally, add *"— or `scripts/check-plan-progress.py` could not be imported"* to the CANNOT RUN
text at `:217-221`, so the sentence covers the cause it can actually have.

---

### M3 — Medium · Two thirds of the edit-tool table are untested; deleting `Write` from it silently narrows detection with a green suite.

**Severity: Medium.**

**Claim.** `:139` is `_EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")`. Mutating it to `("Edit",)`
leaves the suite at **61/61 — SURVIVED**. So does `("Edit", "Write")`. Every self-test case that
builds an edit record — `:533-535`, and the six new ones at `:651-676` — uses `"name": "Edit"`.

**Why `Write` is not hypothetical.** Spec §4.6 measured it: *"`Write` ×4 always `('content',
'file_path')`"*. My own corpus pass over 700 transcripts counted **4129 edit tool_uses** across the
three names. A turn that creates a new file with `Write` and emits no banner is a first-class instance
of the failure #95 describes, and dropping `Write` from `:139` under-fires **silently** — the
direction the module docstring itself calls dangerous (`:52-53`).

**Smallest fix.** One case: `edited_paths_of` over a `Write` tool_use returns its `file_path`. The
`edit_id` helper at `:651-653` already parameterises everything except the name.

---

### M4 — Medium · `isMeta` does not mean "not the human typing". Measured: 100 of the 405 boundaries this change removes carry a real human or agent message.

**Severity: Medium.**

**Claim.** `:98-101` justifies the new skip with *"Two kinds of `user` record are not the human
typing"*, and `:125` implements `rec.get("isMeta") is True` as one of them. Measured over the full
700-transcript corpus, that premise is false for a measurable slice of the population.

**Evidence.** Of 3175 non-tool-result `user` boundaries, the new rule removes **405**. Enumerating
the content of the removed ones:

| content prefix | count | is it the human? |
|---|---|---|
| `The user sent a new message while you were working:` | **30** | **yes — literally the human's text, relayed** |
| `<local-command-caveat>` (a slash command the human typed) | **67** | **yes** |
| `Another Claude session sent a message while you were working` | **3** | an agent, but a genuine new instruction |
| `<system-reminder>` / skill injections / this hook's own feedback | 305 | no — correctly skipped |

So ~100 of 405 removed boundaries begin a genuinely new instruction. The direction of the error is
**quieting** in both branches: a wider window makes a banner more likely to be found, which makes
`banner is None` false (new branch → QUIET) and makes the highest banner more likely to reach `i == N`
(old branch → QUIET).

**Bounded honestly.** I searched for the consequence and did not find it: across all 700 transcripts,
**0** cases where a banner sits between the previous real boundary and one of those relayed-human
records, i.e. **0 observed instances of a banner actually leaking forward**. The hazard is real in the
predicate and unobserved in the corpus. Spec §4.5 measured the *over-correction* of adding
`promptSource` and rejected it correctly; it did not measure what `isMeta` alone still swallows.

**Smallest fix.** Keep `isMeta`, and treat as a boundary any `isMeta` record whose content starts
with `The user sent a new message while you were working` or `Another Claude session sent a message`.
Two string tests, both measured above. If that is judged out of scope, the honest alternative is to
correct `:98-101` and add the class to *WHAT IT CANNOT SEE* (`:43-58`) — the guard's blind spots are
otherwise carefully enumerated and this one is missing.

---

### M5 — Medium · Spec R3 was delivered against the predicate, not the wiring; `edited` can be hardcoded `True` in `run_decide` with a green suite.

**Severity: Medium.**

**Claim.** Spec §5 R3 reads *"armed · unticked > 0 · edit **outside** the repo → QUIET, catches **a
missing path scope**"*. The delivered case (`:591-592`) is

```python
case("R3 an edit outside the repo does not count (the scratchpad case)",
     _edit_inside_repo(["/tmp/scratch/x.md"], _r) is False)
```

— an assertion about the pure helper. The scope is applied at `:408`:

```python
edited = _edit_inside_repo(edited_paths_of(records or []), ROOT)
```

Mutating `:408` to `edited = True` leaves the suite at **61/61 — SURVIVED.** That is exactly "a
missing path scope" at the only place it can go missing: the guard would then warn on every armed,
banner-less stop regardless of whether anything was edited, which is the cry-wolf outcome §6/§7 spend
their length avoiding.

Note that at the `decide` level R3 and R1 are the same call (`edited=False`), so the pure-function
case cannot distinguish them — the wiring is the only thing R3 could have been about.

**Smallest fix.** In the F4 fixture block, a second `run_decide` whose transcript's only edit has a
`file_path` under `/tmp/`, asserting `QUIET` and no new log line.

---

### L1 — Low · `if True:` at `:418` is dead syntax left by the removed `if banner:` gate.

`:418` reads `if True:` with a four-line body. It is the residue of the gate §7 asked to be dropped.
Harmless, but it reads as an unfinished edit, and it is the line H3's mutation targets — a reader
repairing "the odd `if True:`" is one keystroke from reinstating the suppression. **Fix:** dedent the
body and delete the line.

### L2 — Low · `_edit_inside_repo` still declares itself `PURE` after `e0b11c94` made it touch the filesystem.

`:363` says *"PURE. True iff any path is a FILE inside `root`"*; `:378` now calls `resolved.is_dir()`.
The function's result is a function of the filesystem at stop time, not of its arguments. Two of the
new self-test cases (`:673-676`) consequently assert against the live repo layout rather than a
fixture. The behaviour is right — the label is now false, and "PURE" is the word the rest of this file
uses to mark what is safe to test in isolation. **Fix:** replace `PURE.` with a sentence naming the
one filesystem read.

### L3 — Low · The hook's fail-closed comment was orphaned by the move and now reads as describing the observer.

`.claude/hooks/block-idle-stop.sh:36-38` — *"A hook that cannot run must not silently allow the stop
… **Blocking ONCE with a loud message is the middle ground**"* — described `check-plan-progress.py`,
which used to follow it immediately. The move inserted the observer block (`:39-52`) between them, so
the comment now sits directly above the one check in this file that is documented as never permitted
to block (`:68-70`). **Fix:** move `:36-38` down to immediately above `:54`.

### L4 — Low · `assistant_texts_since_last_user`'s "Existing callers unchanged" describes an empty set, and its behaviour did change.

`:189` says *"Back-compat wrapper: the text half of the window. Existing callers unchanged."*
`grep -rn 'assistant_texts_since_last_user'` over the whole repo returns **only**
`check-banner-armed.py` — its definition and eight self-test cases. `run_decide` now calls
`records_since_last_user` + `texts_of` directly (`:398-404`). There are no external callers to keep
compatible. Separately, the wrapper's *output* did change: the `isMeta` skip widens the final window
in **149 of 700** transcripts. **Fix:** either delete the wrapper and retarget the eight cases at
`records_since_last_user`/`texts_of`, or reword the docstring — it currently asserts a compatibility
property about a set of size zero.

### L5 — Low · One vacuous absence assertion, and one undocumented blind spot.

**(a)** `:577-578` asserts `"Nothing is blocked" not in decide([], armed=True, steps=S,
edited=True)[1]` — an absence assertion against a message string written in this same commit that has
never contained that phrase. It passes with or without any fix. Its sibling at `:442-443` is the
right shape (a *presence* assertion on `"does not block your stop by itself"`). **Fix:** make it a
presence assertion on the new message's own hedge, or drop it.

**(b)** A symlink **inside** the repo pointing outside it is not seen. Probed on a real fixture:
`_edit_inside_repo([<root>/link.py], root)` where `link.py → <outside>/g.py` returns **False**, because
`resolve()` follows the link before `is_relative_to`. The converse (an outside symlink into the repo)
returns True. This is the same silent-under-fire class as the worktree and macOS-case entries already
listed at `:50-53`, and it is the only one of the three not listed. **Fix:** one bullet in *WHAT IT
CANNOT SEE*.

---

## Claims I verified as CORRECT

* **Blocking precedence holds in every combination.** All 18 cells of
  `(BANNER_RC, PLAN_RC, CI_RC)` executed with stub children: `PLAN_RC != 0` → hook exit **2** in all
  6 such cells; the banner guard never yields exit 2; `BANNER_RC ∈ {1,2}` with an allowed stop → exit
  **1**; `0,0,0` → exit **0**. No dead code, no duplicated invocation.
* **The observer genuinely runs before the blocker, and this is load-bearing.** `:51-52` precedes
  `:54-56`. Mutating the hook to restore the old order, or to stop invoking the guard at all, is
  caught by F6 (both go red). The stated reason — `check-plan-progress.run_decide` unlinks the
  sentinel — is why order matters, not just reachability.
* **`check-ci-watched` runs exactly where it did before.** The diff is a pure move of the banner
  block; `:65-66` is untouched and still unreachable on a blocked stop, which §6 declares out of
  scope deliberately.
* **A broken or missing `check-plan-progress.py` reports CANNOT RUN, not silence.** Measured with a
  `SyntaxError` file and with the file deleted: exit 2 and `TREAT THIS AS NOT RUN` both times. The
  vocabulary requirement of §4.3 is met (the message's *content* is M2).
* **The borrowed import is safe to `exec_module`.** AST pass over `check-plan-progress.py`: the only
  module-scope statements are imports, defs, constants and the `if __name__ == "__main__"` guard at
  `:269`. No side effects, no I/O.
* **`e0b11c94`'s failed-edit pairing is sound, and the mechanism is real.** Independently measured
  over 700 transcripts: `tool_result` blocks carry `is_error` (17792 occurrences of the key); of
  **4129** unique edit `tool_use` ids, **4088** paired with a success, **41** with `is_error: true`,
  and **0 unpaired**. The error contents include permission denials (*"The user doesn't want to
  proceed with this tool use"*) and hook blocks, all correctly dropped. The "unpaired counts as
  in-flight" branch is unobserved at rest, consistent with its stated rationale.
* **The directory case is fixed.** At `c72140dc` I probed `_edit_inside_repo([<root>/sub], root)` →
  `True`, contradicting its docstring. `e0b11c94:378` resolves it; re-probed → `False`.
* **Gitignored paths inside `ROOT` count as work.** Probed: `.claude/executing-plan` and
  `.claude/banner-warnings.log` both return `True`. This is §4.7's explicit, measured decision
  (17 writes under `.claude/`, 0 to gitignored paths) — recorded here as verified, not re-litigated.
* **`..` traversal, sibling checkouts and the repo root behave as documented.** Probed on a real
  tree: `<root>/sub/../../outside/g.py` → False; `<root>/sub/../sub/f.py` → True; `/repo-old/x.md`
  against `/repo` → False; the root itself → False. The macOS case-insensitivity blind spot is real
  (`<ROOT.upper()>/sub/f.py` → False) and is already documented at `:51-53`.
* **The declared count is externally observed.** `:66` declares `# 61 cases`; the suite prints
  `61/61`; `check-banner-armed.py` is pinned in `check-selftest-counts.POPULATION:88`; CI runs the
  suite at `.github/workflows/ci.yml:195-196`.
* **Nine of the delivered regression cases are live, not vacuous.** Each of these mutations goes red
  via the case that names it: dropping `and edited` → R1; dropping `armed and` → R2; dropping
  `unticked > 0` → the finished-plan case; removing the CANNOT_RUN hoist → F2/F3; removing the
  `is_absolute` refusal → the relative-path case; removing the `.git` exclusion; removing the
  colon-less-line skip → the `parse_sentinel`-agreement case; ignoring `paused:` → R5; last-wins
  instead of highest → the HIGHEST case; dropping `re.M` → the mid-sentence case; dropping the
  `reason` column → the log-grammar case **and** F4.
* **§8 bookkeeping is complete.** Declared count moved (§8.1); the `:35-37` docstring rewritten
  (§8.2); the backlog falsifier reworded to *"a file inside the repo"* (§8.3, `docs/backlog.md`);
  both *"Nothing is blocked"* messages corrected — the remaining two hits are in
  `check-ci-watched.py:107` and its own test, which are out of scope (§8.4); a dashboard entry exists
  (§8.5, +38 lines).

---

## Note for the coordinator, not a finding

The backlog closure row added by `c72140dc` states *"55/55 self-tests, 11/11 mutations killed via the
case each names"*. That is a true statement about 11 mutations. This review applied **39** and found
**16 survivors**, of which the eight above are load-bearing. A count of killed mutations is not a
coverage claim, and the sentence reads as one.

---

VERDICT: NOT CONVERGED

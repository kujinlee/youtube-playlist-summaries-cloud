# Round 5, Claude half — `backlog-249-260-fixes` @ `6e829059`

Subject: `git diff 5f7bf286..6e829059 -- scripts/` — verified as **8 files, 598 insertions, 64
deletions** (`git diff --shortstat`). Mandate: refute. Hypothesis under test: *round 5's fold is
clean.*

**Verdict: the hypothesis breaks. Round 5's fold is the seventh consecutive instance** — High 1 is
a defect the fold itself introduced, in the lenient direction, measured against two independent
CommonMark parsers.

Everything below was run under `python3.12` (3.12.9). Every exit code was taken from a redirected
file, never after a pipe.

**The instrument.** I installed **`cmarkgfm`** (a real cmark binding) and **`markdown-it-py` 4.2.0**
(an independent CommonMark implementation) into a throwaway venv, so the central task the brief
names was done rather than declared. Harness:
`…/scratchpad/r5work/diffharness.py`.

I did **not** reimplement CommonMark. Span boundaries are read *out of the shipped function*: a
PROBE string keeps every character the function's decisions depend on (`` ` ``, `\`, `\n`, space,
tab) and replaces every other character with `\x0b`, which `.isspace()` is True for but which
`BLANK_LINE`'s `[ \t]*` does not match. The function's pairing decisions are therefore bit-identical
on probe and on text, while every in-span position becomes visible as a mask. Known positive first:
the harness independently reproduces the function's declared 3-backtick deferral
(`a ``` b c ``` d` → subject `[]`, cmark `['b c']`), so it is not reporting a clean sheet.

---

## Blocking

None. Both High findings make `check-withdrawal.py` **more lenient**, and the guard is warn-only
unless `--strict` (#56). The failure mode is a weaker warning, not a gate that refuses wrongly, so
neither blocks a merge on its own. I would not close #257 while High 1 stands.

---

## High

### H1 — `backtick_escaped` is applied where CommonMark escapes do not apply, so the r5 fix extends a span past its real closer and masks live prose. INTRODUCED BY THIS FOLD.

`scripts/check-withdrawal.py:322`, the filter added in `6e829059`:

```python
    runs = [m for m in BACKTICK_RUN.finditer(text)
            if len(m.group(0)) <= 2 and not backtick_escaped(text, m.start())]
```

and the rule it implements, from the same commit's docstring:

```
      · ⟳ r5 Codex H1 — AN ESCAPED BACKTICK IS NOT A DELIMITER
```

**That rule is true in prose and false inside a code span.** CommonMark backslash escapes do not
apply within a code span: once a span has opened, the scan for the closing delimiter run is purely
lexical, so a backslash immediately before a backtick is a *literal backslash* and the backtick
*closes the span*. The filter is unconditional — it is applied to every run, including runs that sit
inside an open span — so it discards real closers.

**Failure scenario, minimal:**

    input:   `a \` b` c
    cmark:   ['a \\']              ← code span is  `a \` ,  " b" and "c" are prose
    mdit:    ['a \\']              ← markdown-it-py agrees, independently
    shipped: ['a \\` b']           ← span extended past its real closer
    mask:    `ax\`xb` c            ← the space before "b" is PROSE and was masked

**Verdict-changing witness**, with a control:

| input | cmark / mdit span | `history_marker` | meaning |
|---|---|---|---|
| ``` `a \` the count was wrong:\n1,414 anchors` ``` | `['a \\']` | `'was '` | **SUPPRESSED — wrong** |
| ``` `a ` the count was wrong:\n1,414 anchors` ``` (control, escape removed) | `['a ']` | `''` | SURVIVOR — right |

Masking the `\n` after `wrong:` kills the `(?<=:)\n` alternative of `SENTENCE_SPLIT`, so the figure's
sentence absorbs the lead-in carrying `was`, and `is_history_context` returns `True`. A live stale
figure is reported as history. This is the lenient direction the function's own docstring calls
"the direction that hides a stale figure", and the direction the last two defects in this function
took.

**Live reach.** The new filter drops **64** backtick runs across **14** of the 393 files
`docs_files()` returns (`2026-06-09-deep-dive-html-export.md` 14, `2026-06-29-dig-section-subheadings.md`
12, `2026-06-18-summary-deepdive-quality.md` 10, …). These are real documents with shell/JS snippets
containing `` \` ``. Honest bound: across the **43** guard windows that contain an escaped backtick,
the marker is `''` in **43 of 43** today, so the class is **live but currently latent** — no verdict
in today's corpus flips. It flips as soon as a weak marker lands in a wrongly-extended sentence.

The document-level sweep surfaced this independently: 14 files show the subject's span running past
cmark's, every one at a `` \` `` (e.g. `2026-07-07-stage-1e-b-worker-summary-handler.md`, subject
`{ id: job.videoId, … summaryMd: \`${baseName}.md\`, playlistIndex: …`, cmark
`{ id: job.videoId, … summaryMd: \`). The inverse also occurs — cmark finds a span the subject
misses entirely (`2026-06-29-dig-section-subheadings.md`, cmark `['\\']` twice, subject none) —
same root cause, safe direction.

**The fix is a condition, not a new rule:** apply `backtick_escaped` only when deciding whether a
run may *open* a span, never when scanning for its closer. Stating it that way also removes the
need for the next hand-derived rule.

### H2 — `mask_inline_code` is applied to a 180-char window that cuts spans in half, and **all 205** of its live verdict changes are false suppressions.

`scripts/check-withdrawal.py:413`:

```python
    masked = mask_inline_code(window)
    bounds = [0] + [m.end() for m in SENTENCE_SPLIT.finditer(masked)] + [len(window)]
```

`window` is `window_around(text, start, end, span=CONTEXT_CHARS)` — a raw ±180-character slice. The
slice routinely begins *inside* a code span, so the first backtick in the window is a **closer whose
opener is outside it**. That inverts the parity of every backtick after it: the mask pairs the orphan
closer with the next genuine opener and masks the prose between them, and does so for the rest of
the window.

**Measured over the corpus.** Population: every window the guard would build for any numeric token
in the 393 files `docs_files()` returns — **75,076** windows. (This is a *superset* of any single
run's population, which is restricted to figures a diff removes; I state that rather than implying
it is the guard's own 49,240.)

| measurement | result |
|---|---|
| windows where `mask_inline_code` changes `history_marker` at all | **205** |
| of those, mask **creates a suppression** (marker non-empty, unmasked would be `''`) | **205** |
| of those, mask creates a **survivor** | **0** |
| same 205 under the **same masking rule decided on the whole document** instead of the fragment | **`''` — SURVIVOR — in all 205** |

So the function's entire live effect on verdicts is 205 false suppressions, and the cause is isolated:
fragment parity, not any CommonMark subtlety. Direction counts: `'was '`→`''` ×189, `'quoted'`→`''`
×8, `'earlier'`→`''` ×7, `'(was'`→`''` ×1. Concentrated in `backlog.md` (69), `dashboard-entries.md`
(44), `roadmap-to-launch.md` (19).

**Concrete witness** (`backlog.md`, figure `15`): the window opens mid-span at ``.test.ts` ``, and the
mask converts 53 characters of prose to `x`:

```
window : .test.ts` are all on `master`. The row was never ticked — it still said "IMPLEMENTED on `feat/dev-login-13`" …
masked : .test.ts`xarexallxonx`master`.xThexrowxwasxneverxtickedx—xitxstillxsaidx"IMPLEMENTEDxonx`feat/dev-login-13`"x…
```

`. The row was never ticked` is prose; masking its space kills the `(?<=[.!?])\s+` boundary and the
figure inherits `was`. Document-aware masking of the same text masks **0** characters, because the
document has no whitespace-bearing span there — marker `''`.

**I checked my instrument before trusting this**, per the brief's warning about a 100%. The
document-aware mask looked like an identity function on the first witness; it is not — on a known
positive (`backlog.md` span `render.ts .lead`, one of **879** document spans that contain
whitespace) it masks, and on a window containing one it masks the same 2 characters the fragment
mask does. The 205/205 is a result, not a dead probe.

**Why this is a round-5 finding even though the function predates it.** The docstring edited in this
fold reads:

```
    ⚠ THREE BOUNDS, STATED RATHER THAN HIDDEN — and the third was MISSING from this list until
    r4 Claude L1, which is the failure mode a caveat headed *stated rather than hidden* has:
```

The dominant live failure is not among the three, and three rounds of corrections have each refined
a CommonMark micro-rule while 100% of the function's live error went unexamined. By this repo's own
standard — *a caveat headed "stated rather than hidden" that is wrong is worse than none* — the list
has to name this one. The cheap repair is also the structural one: decide spans on the **document**
and pass the span set into `sentence_around`, which costs one call per blob and removes H1's
exposure at the same time.

---

## Medium

### M1 — the `(?!\.\d)` tail fix is instance-not-class: 14 tokens are accepted that `git rev-parse --verify` rejects as malformed.

`scripts/check-provenance.py:339`:

```python
    r"|`HEAD(?:[~^][0-9]*)?`|\bHEAD(?:[~^][0-9]*)+(?![\w~^])(?!\.\d)"
```

The fold's stated rule is "a run of `~`/`^` with optional digits, followed by neither a word
character nor another ref operator — so a real suffix is required and a word glued to it refuses",
and r5 added `(?!\.\d)` for one more tail. But `[0-9]*` still matches the **empty string**, and the
lookahead only excludes `[\w~^]` plus `.`+digit — so `HEAD~` followed by any *non-word* character
still matches. Measured against `git rev-parse --verify` in this repository:

| accepted here, rejected by git (rc=128) |
|---|
| `HEAD~-1` · `HEAD~+1` · `HEAD~1-2` · `HEAD~1,2` · `HEAD~=2` · `HEAD~!` · `HEAD~/x` · `HEAD~:2` · `HEAD~%1` · `HEAD~(1)` · `HEAD~1..3` · `HEAD~*` · `HEAD~#1` · `HEAD~1@2` |

The asymmetry has no stated reason: `HEAD~fiction` is refused and `HEAD~-1` accepted, and the only
difference is whether the glued garbage begins with a word character — which is exactly the
reasoning r4 recorded as overridden ("the question the guard asks is whether the token AS WRITTEN
names a source"). Direction is lenient: a row counts as sourced on a token nobody can resolve.

Low realistic exploitability, which is why this is Medium and not High — these read as typos, and
the negation class (`we cannot look at HEAD~1` → True) is already a declared limit. I also confirmed
the deliberate accepts are intact and correctly cased: `HEAD^2`, `HEAD~1^2`, `HEAD~1.` all match and
all give git rc=128 for the documented reason, and the four r5 refusals (`HEAD~١`, `HEAD~１`,
`HEAD~1.5`, plus `HEAD~fiction`/`HEAD~1x`/`HEAD^^zz`) each reproduce.

### M2 — `write_config` can discard every setting it does not own, and no case can see it. Measured: the mutation survives 50/50 with zero `[FAIL]`.

`scripts/codex-frontier-model.py:314`:

```python
        with open(CONFIG, "w", encoding="utf-8") as f:
            f.write(block + existing.lstrip("\n"))
```

The `existing` half is what preserves the user's `~/.codex/config.toml`. The r5 read guard added one
function above refuses specifically to protect it:

```
        cannot_run(f"error: cannot read {CONFIG}: {e} — the managed block cannot be refreshed "
                   f"without it, and overwriting would discard settings this script does not own. "
```

**That property has no case.** `_write_config_arm(readonly, pre)` takes `pre` ∈
`{"absent", "unreadable", "undecodable"}`, and the four call sites (`:677`, `:680`, `:683`, `:686`)
use `pre="absent"` for both arms that reach the write — so `existing` is `""` every time the write
executes. The two non-absent states refuse before reaching it.

Measured on a **copy** of the tree (`…/scratchpad/r5work/mut/`), never the repo:

| run | rc | cases | `[FAIL]` lines |
|---|---|---|---|
| control, unmutated copy | 0 | 50/50 | 0 |
| `f.write(block + existing.lstrip("\n"))` → `f.write(block)` | **0** | **50/50** | **0** |

The mutated file still compiles (`py_compile`, no exception), so this is a genuine survivor and not a
SyntaxError reading like a kill. A `--write-config` that silently truncates the reviewer's
`config.toml` to the managed block alone is indistinguishable from a correct one to this suite —
and `docs/plugins.md` publishes `--write-config` as the recommended invocation.

**The adjacent half IS covered, and I checked rather than assumed.** Removing the prior-block strip
(`existing = re.sub(…)` → `existing = existing`) gives rc=1, 49/50, **1** `[FAIL]`, attributed to the
propagation case by name. So the two-slug readback r5 built genuinely kills idempotence; it is
blind only to preservation. One `pre="present"` state and a fourth clause
(`"[existing]" in second`) closes it.

---

## Low

### L1 — inline backtick pairs inside fenced code blocks are masked, and the docstring's justification for deferring fences is the risk this already realises.

The docstring says fences are "left alone … widening the mask to fences risks pairing an unbalanced
fence and masking prose, which fails toward MORE suppression". But runs of 3+ are merely *dropped
from the run list*, which leaves the **single** backticks inside a fenced block free to pair with
each other. Measured document-level over the 393 files: **597** span-level disagreements of this
shape across **121** files — e.g. `anchors.md`, where `stable-blob-addressing` sits inside a
```` ```md ```` block and cmark reports no inline span while the subject masks it; likewise
`deploy.md` (`fly ips allocate-v4/-v6`, `--private`) and `m1.4-finishup-checklist.md`. Direction is
the same lenient one the comment warns about. The caveat is not wrong about the deferral, it is
wrong about which way the deferral currently fails.

### L2 — the PR body carries three stale figures, which is #257's own class in the artifact `docs_files()` cannot see.

PR #371's body states **`1,453 mutations`**, **`EXPECTED_MUTATIONS` 1408 → 1453 at both pinning
sites**, and **`--binding` — 1,461 anchors in 66 ms**. The tree at `6e829059` declares **1,524**
mutations over 62 manifests and `--binding` reports **1,532 anchors across 1,524 entries**. Three
superseded figures in the branch's most figure-dense artifact — and `docs_files()` globs
`docs/**` only, so the guard built to catch exactly this cannot reach a PR body. Worth noting
because the gap is structural, not an oversight of this fold.

### L3 — `HEAD@{1}` is a real ref form the provenance pattern refuses.

`git rev-parse --verify 'HEAD@{1}'` → rc=0; neither alternative matches it (both require `[~^]`
immediately after `HEAD`). Pre-existing, not fold-induced — the pre-r4 `\bHEAD[~^]\d*` did not match
it either. Flagged only so a future tightening does not record it as already handled.

---

## Checked and found SOUND

* **Every figure in the brief that I could reach reproduces.** Suite counts under `python3.12`:
  find-claim **86/86**, check-withdrawal **106/106**, check-provenance **144/144**, check-plan-code
  **237/237**, codex-frontier-model **50/50**, all rc=0. `EXPECTED_MUTATIONS`: **62** entries summing
  to **1,524**, against **62** manifest files holding **1,524** entries, with **zero** per-file
  mismatches (my first attempt keyed on the stem and reported 62 spurious mismatches — the keys are
  `scripts/<name>.py`; the error was mine). `--binding` rc=0, **1,532 anchors / 1,524 entries**.
  `git diff --shortstat` **8 files, 598 insertions, 64 deletions**. Live guard run at HEAD:
  `rc=0 — 5 figure(s) corrected, and none of them survives elsewhere`, no suppression line.
* **r4 L1 (equal-length pairing) is right, and cmark confirms it.** `a `b`` c `…` d` → cmark and
  markdown-it-py both give `['b`` c ']`, matching the shipped function exactly. The adjacent-only
  version really was wrong, and the fix matches a real parser rather than merely differing from it.
* **r5 M1 (skip the unmatched opener, do not `break`) is right.** `a `unclosed then ``x y``` →
  subject, cmark and mdit all give the later span.
* **The blank-line rule is right** — `the count was `wrong\n\nholds …`` → all three agree on no span.
  It is incomplete (a blank line is one of several block boundaries; H2 is the general case) but not
  wrong.
* **`_refusal_arm_in_dir` restores global state on every path.** `tempfile.tempdir = hostile` is
  assigned immediately before the `try`, so every exit including an exception inside
  `_refusal_arm` runs `finally: tempfile.tempdir = saved`; a failure in the preceding
  `os.makedirs` happens before the assignment and leaks nothing.
* **The needle-order question is answered by the strip, not by the order.** The classifier matches
  against `err.getvalue().replace(str(CACHE), "<CACHE>")`, and `CACHE` is the full path *inside* the
  hostile directory, so the directory name is removed with it. Both hostile-directory cases
  (`not found`, `cannot read`) return `(2, "malformed")`. `_write_config_arm` is protected the same
  way via `replace(str(CONFIG), "<CONFIG>")` even though it has no hostile-directory case.
* **The read guard's exception tuple is complete for this call.** `open().read()` on a path that
  exists can raise `OSError` (permission, `IsADirectoryError`, a vanished file) or
  `UnicodeDecodeError`; `LookupError` and `ValueError`-from-mode are unreachable with a literal
  mode and encoding. The `os.path.exists` + `open` window is a TOCTOU race, but it now lands in
  `except OSError` → `cannot_run` → rc=2, which is the safe direction for a race.
* **The duplicate-anchor entry is legitimate, and the harness already says why.** The two entries
  anchored on `EXPECT_OVERLAP_FLOOR = 12` (with and without `\n`) mutate the same constant to
  **different** values (`0` and `11`) under **different** `expect`s, so they are distinct coverage,
  not count-padding. `check-plan-code.py:2146-2168` already documents at length that the rule is
  evadable by changing the anchor literal and that "a duplicate-IN-SUBSTANCE entry is caught by
  NOTHING", with `EXPECTED_MUTATIONS` as the thing that keeps coverage from shrinking. I would not
  tighten it: the honest comment is already there, and `--binding` confirms both anchors resolve to
  exactly one site. My only note is that the `\n` form is now a worked example a future entry can
  copy, so the pin is doing the real work.
* **The brief's CI claim is true as stated.** At `9017b6c9` the sweep was green —
  `mutation-sweep (1)`–`(8)` all `success` plus `mutation-sweep-complete` `success`. See CANNOT RUN
  for what that does *not* cover.

---

## CANNOT RUN

* **Brief item 7 — "14 retargets still kill their named case" — is verified at `9017b6c9` and NOT at
  HEAD.** At `6e829059` the sweep is **5 of 8 shards green, 3 still `in_progress`**, and
  `mutation-sweep-complete` has not been scheduled. `6e829059` adds 78 manifest lines to
  `codex-frontier-model.json`, 56 to `check-withdrawal.json`, 26 to `check-plan-code.json` and
  changes 14 in `check-provenance.json`, so the shards that matter most to this fold are the ones
  still running. **Treat "every mutation kills via the case it names" as NOT MEASURED at HEAD.** I
  did not run `--mutate .` locally: per `scoped-mutation-run-in-four-seconds`, local shards time out
  and would have produced NOT MEASURED dressed as a result.
* **`verify` is RED at HEAD, and on all six CI runs of this branch.** The failing step is
  `check-review-recorded (PR only)`: *"FAILED — 4 round(s) ran and guarded code was committed after
  every one of them. The closest (`backlog-249-260-r2-codex.verdict.json`) never saw:
  scripts/check-plan-code.py, scripts/check-provenance.py, scripts/check-withdrawal.py,
  scripts/codex-frontier-model.py, scripts/find-claim.py, … (+4 more)"*. That is the expected
  mid-round state and this round's halves should satisfy it — but **"the sweep was green" must not
  be read as "CI was green"**, which is the reading the brief's row invites.
* **Document-level oracle alignment is content-sequence, not offsets.** `cmarkgfm` exposes
  `CMARK_OPT_SOURCEPOS` but no XML renderer, and cmark does not emit `data-sourcepos` on inline
  `<code>`, so I compared ordered span *contents* rather than character offsets. That is sound for
  detecting both directions of disagreement and is how H1 was found, but a handful of
  `backlog.md` rows (escaped table pipes, `` `` `path:line` `` ``) remain instrument-ambiguous: my
  boundary snapping mis-resolves a span whose own content starts or ends with a backtick run. I did
  not pursue those; they are ~25 `replace` ops and none showed the lenient direction. H1 and H2 do
  not rest on them — both are established by minimal witnesses and by the fragment-vs-document
  comparison, neither of which uses the oracle alignment.
* **I did not re-verify the coordinator's by-hand check of the 14 retargets individually.**
  `--binding` rc=0 proves all 1,532 anchors resolve to exactly one site, which is the *binding* half;
  the *killing* half is the sweep, which is incomplete at HEAD (above). So the brief's invitation to
  check that verification rather than trust it is answered only for binding.

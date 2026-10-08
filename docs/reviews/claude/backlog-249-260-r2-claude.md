# Round 2 adversarial review, CLAUDE half — backlog #249–#260

**Subject:** branch `backlog-249-260-fixes`, PR #371, commit `31e8768a`.
**Read from a pinned snapshot** — `git archive 31e8768a | tar -x -C /tmp/r2snap`. `git rev-parse HEAD`
returned `31e8768adbff5978101ba5b1afb371d789bac371` and `git status --porcelain` was empty, so the
worktree and the snapshot agreed for the whole review. Suites were run in the worktree; every
source claim below is quoted from `/tmp/r2snap`. Interpreter `python3.12` (3.12.9), which is what CI
pins; this machine's bare `python3` is 3.14.

**VERDICT: NOT CONVERGED**

One Blocking: a required CI step is red at this commit, and it is the round-2 fold's own damage —
the third consecutive round in which the fold reddens a check. Two High, six Medium, six Low.

The round-2 fold is substantively good: every one of Codex's seven findings has a real fix, each
fix has a case that fails when the fix is reverted, and I killed four of them by hand to prove it
(see *Checked and found SOUND*). The findings below are what the fixes themselves introduced or
left open — which is the pattern now three rounds deep in these same four files.

---

## Blocking

### B1 — `check-selftest-counts.py` is RED at `31e8768a`, and it is a required CI step

The fold added three cases to `codex-frontier-model.py` (`_GOLDEN_EMPTY`, `_GOLDEN_NONEAR`, and the
four-distinct-texts case) and did not update the count the file declares.

`scripts/codex-frontier-model.py:13`:

```
  python3 scripts/codex-frontier-model.py --self-test   # 31 cases, pure, no network
```

```bash
$ python3.12 scripts/codex-frontier-model.py --self-test 2>&1 | tail -2

34/34 self-test cases passed
```

The gate, run with **no pipe** so the exit code is its own:

```bash
$ python3.12 scripts/check-selftest-counts.py
declared self-test counts disagree with what the suites printed:

  ✗ codex-frontier-model.py: [DRIFT] the docstring declares 31 cases; the suite ran 34

$ echo $?
1
```

⚠ I first measured this through `| tail -4` and read `$?`, which reported 0 — tail's code, not the
guard's. That is the trap the brief names, and it inverts this finding, so the number above is from
an unpiped run. I re-ran it twice.

It is a CI step in the required `verify` job — `.github/workflows/ci.yml:390`:

```yaml
      - name: Declared self-test counts match the suites
        run: python3 scripts/check-selftest-counts.py
```

The other four declared counts in this fold WERE updated — `find-claim` 53→64, `check-provenance`
67→93, `check-withdrawal` 71→81, `check-plan-code` 220→226. `codex-frontier-model` is the one site
the fold missed, and it is the only one of the five whose docstring the fold did not otherwise touch.

**What would have to change:** `scripts/codex-frontier-model.py:13` → `# 34 cases, pure, no network`.
Then `python3.12 scripts/check-selftest-counts.py` unpiped, and confirm rc=0.

---

## High

### H1 — `collect_files` still loses a subject SILENTLY, one layer below the one the fold fixed

**`scripts/find-claim.py:267`**

```python
            for dirpath, dirnames, filenames in os.walk(p, followlinks=True):
```

`os.walk`'s `onerror` defaults to `None`, which means errors from `scandir` are **discarded**. The
fold rewrote this traversal to fix three real defects and left the error channel at the default, so
a directory the walk cannot read contributes nothing and is reported nowhere — not in `skipped`, not
in `pruned`, not in `err`, not in the verdict.

Harness: `scratchpad/atk/a1_unreadable.py`. World — a control in `root/ok.md`, the claim in
`root/locked/claim.md`, `chmod 000 root/locked`:

```
files   = ['ok.md']
skipped = []
pruned  = []
err     = ''
rc      = 0
stdout  = ok — absent in the searched files, and the control hit 1 time(s), so the search worked.  (1 file(s) searched)
```

The claim is live, in a file inside the searched root, and the tool returns **rc=0 and the sentence
"so the search worked"**. That is H1's own class — "a claim that is absent only because the search
never reached it" — and the fold's own commentary at `find-claim.py:253-266` is about exactly this
risk for symlinks and prunes.

The asymmetry makes it sharper: the *file* path already handles this correctly. Same harness,
`chmod 000` on the claim FILE instead of its directory (`scratchpad/atk/a2_more.py`, case F):

```
rc     : 2
out    : CANNOT RUN — 1 file(s) could not be read or decoded, so this search did not reach its whole
         subject. A control in a readable file cannot speak for one that is unreadable. Treat this
         as NOT RUN
```

So the guard has the right sentence, the right exit code, and the right principle for an unreadable
file, and none of it for an unreadable directory.

**What would have to change:** pass an `onerror` that appends to a returned list (the shape
`skipped` and `pruned` already have), and have `verdict` qualify on it or return 2 — `search_files`'
`unreadable` handling is the model. A case needs the `chmod 000` directory, and `followlinks=True`
makes a symlink to an unreadable directory the same hazard.

### H2 — `PROVENANCE_RE`'s new verb list has NO word boundary, and the fix's own comment claims it does

**`scripts/check-provenance.py:205-206`**

```python
    r"|(?:measured|re-?derived|derived|taken|counted|observed|verified|sampled)"
    r"(?:\s+\w+){0,2}\s+HEAD\b"
```

None of the eight alternatives is prefixed with `\b`. The comment three lines above
(`check-provenance.py:192-194`) presents inside-word matching as the hazard this rule had already
cleared:

```
    # ⟳⟳ r2 Codex MEDIUM — `\bat` WAS A SEMANTIC BYPASS, not just a word-boundary question.
    # It correctly refused `format HEAD` and `lookat HEAD`, and then accepted
    # **"we cannot look at HEAD"**
```

The replacement dropped the boundary that `\bat` had. Harness `scratchpad/atk/e3_wb.py`:

```
  provenance=True   'unverified at HEAD'
  provenance=True   'unmeasured at HEAD'
  provenance=True   'underived from HEAD'
  provenance=True   'mistaken at HEAD'
  provenance=True   'discounted at HEAD'
  provenance=True   'resampled at HEAD'
  provenance=False  'format HEAD'
  provenance=False  'lookat HEAD'
```

`unverified at HEAD` and `unmeasured at HEAD` are prose asserting that **no** measurement happened,
and they are accepted as provenance — M3's class, in the negation rather than the modal. The same
holds without the inside-word trick (`scratchpad/atk/e2_prov.py`):

```
  provenance=True   'the count cannot be measured at HEAD'
  provenance=True   'this was never counted at HEAD'
  provenance=True   'not verified against HEAD'
  provenance=True   'nothing was observed at HEAD'
  provenance=True   'we have not derived this from HEAD'
```

The literal witness Codex supplied IS fixed — `we cannot look at HEAD` → `False` — and row #255's
wording `cannot read HEAD` → `False`, deliberately. But the class was "prose about git accepted as
measurement provenance", and the fold closed one phrasing and opened six.

`format HEAD` and `lookat HEAD` still return `False`, so the boundary loss is not visible from the
two controls the comment cites — those two words simply do not END in one of the eight verbs. Any
word that does, matches: `unverified`, `unmeasured`, `underived`, `mistaken` (`taken`), `discounted`
(`counted`), `resampled` (`sampled`). The controls that would have caught this are words containing
a verb, and there are none.

**What would have to change:** `r"|\b(?:measured|re-?derived|…)"` for the boundary, which is
mechanical. The negation half is not mechanical and is the honest reason this rule cannot be a
word list; the alternative is to require the construction to carry a measured VALUE (`measured N …
at HEAD`) rather than any occurrence of a verb near `HEAD`.

---

## Medium

### M1 — `case_name_patterns` takes EVERY f-string in the file, so an unrelated format string forgives a stale expect

**`scripts/check-plan-code.py:1536-1547`**

```python
    for n in ast.walk(tree):
        if not isinstance(n, ast.JoinedStr):
            continue
```

Codex's M1 required change was *"restrict candidates to expressions that supply suite case names"*.
The fold added `min_static: int = 4` instead and left the candidate set as every `ast.JoinedStr`
anywhere in the module — print statements, error messages, paths, HTML.

`min_static=4` does not do the work claimed for it. The docstring says the floor keeps
`f"{a}{b}"` — "which would become `^.*?.*?$` and match everything" — out of the set, and it does;
but `^.*?:.*?\ —\ .*?$` is admitted and is nearly as broad.

Falsifier with a control, `scratchpad/atk/c2_falsify.py`, against the real
`scripts/check-plan-file-tags.py`:

```
expect 'a case that was deleted months ago: nothing — nothing at all'
   in literals?      False
   f-string pattern? True
   containment?      False
   -> warnings=["probe: expect 'a case that was deleted months ago: nothing — nothing at all'
                 matches no string literal in scripts/check-plan-file-tags.py"]

expect 'total nonsense with no colon or dash whatsoever'          <- the CONTROL
   f-string pattern? False
   -> errors=["probe: its expect names a case that is GONE from scripts/check-plan-file-tags.py —
               no literal there can produce it, so this mutation can no longer show WHICH case is
               the guard"]
```

The first expect names no case that has ever existed in that file. It is downgraded from the ERROR
arm to the WARNING arm solely because the file contains an f-string whose static parts are `":"`
and `" — "`. The control proves the instrument discriminates.

Reach, `scratchpad/atk/c4_bound.py` — build, per target file, a probe from one of its own derived
patterns with every `.*?` filled with invented prose:

```
target files where an INVENTED expect is downgraded ERROR -> WARNING: 62 of 62
   scripts/brief-compose.py   probe '<script>zz invented case that never existed</script>'
                              pattern ^<script>.*?</script>$
   scripts/check-banner-armed.py  probe '.zz invented case that never existed.tmp'
                              pattern ^\..*?\.tmp$
```

**Bounding this honestly, because the direction matters.** No live manifest entry depends on it
(`scratchpad/atk/c3_size.py`):

```
   forgiven ONLY by an f-string pattern : 0
   forgiven ONLY by containment         : 5
   forgiven by both                     : 62
```

So this changes no verdict today; it is a latent weakening of the refusal half, and the refusal half
is the half that exists to catch a renamed-away case. A stale title must coincidentally match one of
the file's own output templates, which is improbable per file and certain across 62 of them over time.

**What would have to change:** collect `JoinedStr` nodes only where they are a case-name argument —
the same positional rule `case_name_literals` serves — rather than from `ast.walk` over the module.

### M2 — `single_digit_figures` is still a denylist of words, 19× larger, and the 21st witness is easy

**`scripts/check-provenance.py:124-141`** — `LABEL_BEFORE` (24 words) and `SUBJECT_AFTER` (33 words).
The comment at `:101-109` argues the instrument changed:

```
# So the rule reads BOTH directions and lives in `single_digit_figures` where it can be read.
# MEASURED 2026-10-07: 20 of 20 witnesses correct — including all four the review supplied
```

Both directions, but both as word lists — the same instrument Codex called wrong ("Growing the
lookbehind list is the wrong instrument"), with 57 words where there were three.
`scratchpad/atk/d1_single.py`:

```
=== FALSE POSITIVES: an IDENTIFIER counted as a measurement ===
  COUNTED  **Stage 3 cloud-sync shipped**       -> ['3 cloud-sync']
  COUNTED  **item 2 blocked**                   -> ['2 blocked']
  COUNTED  **option 3 chosen**                  -> ['3 chosen']
  COUNTED  **tier 2 users only**                -> ['2 users']
  COUNTED  **attempt 2 failed the gate**        -> ['2 failed']
  COUNTED  **level 2 access**                   -> ['2 access']
  COUNTED  **Python 3 ships**                   -> ['3 ships']
  COUNTED  **table 3 lists them**               -> ['3 lists']
  COUNTED  **Sub-project 2 ships**              -> ['2 ships']
  COUNTED  **Day 2 metrics**                    -> ['2 metrics']
  refused  **figure 2 shows the split**         -> []
  refused  **M1 task 3 landed**                 -> []
```

`Stage 3 cloud-sync` and `Sub-project 2` are this repository's own vocabulary — `docs/dev-process.md`
§ *Project-Specific* and the slice history both use them. `item`, `option`, `level`, `tier`,
`attempt`, `table`, `Python` and `Stage` are the 25th through 32nd labels.

The other direction, at row level through `bolded_figures` (so these are not span-only artefacts):

```
=== FALSE NEGATIVES ===
  MISSED   **2 and 3 were red**             -> []
  MISSED   **4 from the sweep**             -> []
  MISSED   **6 that survived**              -> []
  MISSED   **2 in total**                   -> []
  MISSED   **3 or more rounds**             -> []
```

`SUBJECT_AFTER` holds `from of to in on at and or but that`, which are the words that most often
follow a genuine count. `**1 in 60**` — this repo's own phrasing for a false-fire bound — is missed
by the predicate, and survives at row level only because `60` is multi-digit.

That is 15 witnesses beyond the 20. "20 of 20 on witnesses I chose" is the shape the brief predicted.

**What would have to change:** nothing mechanical will separate `Stage 3` from `3 rounds` by word
lists. Either accept the rule as heuristic and say so where the comment now says "correct" — the
guard is warn-mode by default, so that is defensible — or require the counted noun to be a PLURAL
or a known unit, which is a different instrument rather than a longer list.

### M3 — the new `after` window reads across the markdown cell delimiter, and `|` is not in `TOKEN_STRIP`

**`scripts/check-provenance.py:142`**

```python
TOKEN_STRIP = "`*_([{)]}>,.:;!?\"'"
```

**`scripts/check-provenance.py:232-233`**

```python
        if figures_in_span(DATE_RE.sub("", b), row[m.end():m.end() + 40]):
```

`|` is absent from `TOKEN_STRIP`, so a pipe survives stripping and becomes the "counted noun".
`scratchpad/atk/e3_wb.py`:

```
  single_digit_figures('**7**', ' |')          -> ['7 |']
  single_digit_figures('**7**', ' | rounds |') -> ['7 |']
  single_digit_figures('**3**', '|')           -> ['3 |']
  '|' in TOKEN_STRIP? False
```

Two consequences, both measured at row level (`scratchpad/atk/e2_prov.py`):

```
  bolded_figures=['**7**']   findings=[('249', 1)]   | 249 | **7** |
  bolded_figures=['**3**']   findings=[('249', 1)]   | 249 | **3** | failures in the sweep |
```

The first: **any bold single digit ending a table cell is a measurement**, its counted noun being
`|`. The second: the 40-character window crosses into the NEXT CELL, so `failures` — a different
column — supplies the noun. `docs/backlog.md` is a markdown table, which is this guard's only corpus.

Nothing covers it. Applying the fix as a mutation — adding `|` to `TOKEN_STRIP` — leaves the suite
green (`scratchpad/atk/g1_mut.py`):

```
[SURVIVED] rc=0  check-provenance.py: add | to TOKEN_STRIP (the FIX for my M3)
```

A defect whose repair is indistinguishable from the defect, to every case in the file.

**What would have to change:** add `|` to `TOKEN_STRIP`, and clip `after` at the next `|` rather
than at 40 characters, so the noun comes from the figure's own cell. Both need a case at a
table-shaped row, which the `SINGLE_DIGIT_CASES` table currently has none of.

### M4 — `SENTENCE_SPLIT` fixed wrap-sensitivity by widening sentences past real statement boundaries

**`scripts/check-withdrawal.py:255-259`**

```python
SENTENCE_SPLIT = re.compile(
    r"(?<=[.!?])\s+"                               # ordinary end of sentence
    r"|\n\s*\n"                                    # a paragraph break
    r"|\n(?=\s*(?:[|#>]|[*+-]\s|\d+\.\s))"        # the start of a markdown block
)
```

A bare `\n` is no longer a boundary, so any two lines joined by a single newline are one sentence
unless the second starts a block. A WEAK marker on one line now reaches a figure on the next.
`scratchpad/atk/b1_sent.py`:

```
SUPPRESSED  marker='was '  colon lead-in, figure on next line
              sentence='Measured, and the earlier figure was wrong:\nthe sweep holds 1,414 anchors today'
SUPPRESSED  marker='was '  two plain prose lines, no terminal punctuation
              sentence='the old total was 1,414\nthe new total is 1,414 anchors'
SUPPRESSED  marker='was '  inside a fenced code block
              sentence='```\nwas 1,414 before\n1,414 now\n```'
SUPPRESSED  marker='was '  a markdown HARD break (two trailing spaces)
              sentence='the count was wrong  \nholds 1,414 here'
SUPPRESSED  marker='was '  numbered item written `1)` not `1.`
              sentence='the count was wrong\n1) holds 1,414 here'
survives    marker=''      marker line then a markdown TABLE row
survives    marker=''      marker line then a BULLET
survives    marker=''      marker line then a TAB-indented table row
```

Five shapes that are plainly separate statements now share a sentence. `\d+\.\s` catches `1.` and
not `1)`; nothing models a hard break or a code fence.

**The live magnitude, re-derived rather than taken** (`scratchpad/atk/b2_corpus.py`, 390 non-exempt
`docs/**/*.md`, both split rules over one corpus):

```
OLD \n-boundary    occurrences=47990  strong=4935  weak=2330  weak-across-a-line-break=0     median sentence=95
NEW r2 rule        occurrences=47990  strong=4935  weak=3688  weak-across-a-line-break=1418  median sentence=180
```

The fold's stated numbers reproduce exactly — 47,990 occurrences, 4,935 strong, 2,330 → 3,688 weak,
median 180. I get median **95** where the comment says 96; that is the only disagreement and it is a
sampling detail, not a defect. (Codex reported 49,184 occurrences for the same quantity; my 47,990
matches the fold. I used `NUMBER_RE` over non-exempt `docs/**/*.md`, which is what the guard does.)

**And then the part that makes this Medium rather than High.** I sampled the 1,335 suppressions the
new rule creates and the old one did not (`scratchpad/atk/b3_sample.py`, `b4_shapes.py`). The
majority are genuine wraps and the new rule is RIGHT on them, e.g.
`docs/adr/0007-artifacts-are-an-append-only-log.md`:

```
'Render addressing was SPLIT OUT (user decision) to\n  docs/.../2026-08-09-render-addressing-brief.md
 (backlog #25) after two designs were\n  refuted in two rounds.'
```

One wrapped sentence, correctly treated as one. I could not produce a live false negative — the
shapes above are constructed. So the trade is net positive and I am not asking for it to be
reverted.

**What would have to change:** the comment. `check-withdrawal.py:243-254` states the increase
(2,330 → 3,688) as evidence the prong was "narrowed, not deleted" and does not say that the
direction of the change is toward MORE suppression — which this file's own docstring at `:355-358`
calls "the expensive direction". Adding `\n` after a line ending in `:` or two spaces, and treating
fenced regions as block boundaries, would recover the five shapes; three more alternatives in a
regex that already has three.

### M5 — the cycle guard advertised in the fold's comment has no case and no mutation

**`scripts/find-claim.py:268-272`**

```python
                real = Path(dirpath).resolve()
                if real in seen_real:
                    dirnames[:] = []          # a cycle through a symlink; stop descending
                    continue
                seen_real.add(real)
```

`find-claim.py:261` presents this as a property: *"SYMLINKED DIRECTORIES ARE FOLLOWED, with cycle
protection by REAL path."* Severing it leaves the suite green (`scratchpad/atk/g1_mut.py`, AST-valid,
`if False and real in seen_real:`):

```
[SURVIVED] rc=0  find-claim.py: CYCLE GUARD severed
```

`_h1_witness` builds a symlink whose target is outside the root — deliberately, and the comment at
`:447` explains why — but no fixture contains a cycle, so nothing distinguishes protection from its
absence. The seven new `find-claim.json` entries name the symlink-following, the real prune, the
named directory, the tail message and the two verdict arms; none names this.

I did verify the behaviour is correct by hand (`scratchpad/atk/a2_more.py`, case C: `root/self ->
root` terminates and finds the claim once). So this is uncovered, not broken.

**What would have to change:** a case whose fixture contains `root/self -> root`, asserting
termination and the file count, plus a manifest entry bound to the `seen_real` test.

### M6 — two measured claims in the fold's comments do not reproduce

**`scripts/check-provenance.py:108-109`**

```
# MEASURED 2026-10-07: 20 of 20 witnesses correct — including all four the review supplied —
# with the live firing rate UNCHANGED at 48% (106/223) and not one row changing state.
```

Re-derived over `docs/backlog.md` at `31e8768a`, running the pre-fold module (`1efc6c51`) and the
folded one against one corpus (`scratchpad/atk/e3_wb.py`):

```
  pre-r2 1efc6c51    rows=247  fired=194  findings=90  findings/fired=46%
  r2 fold 31e8768a   rows=247  fired=195  findings=90  findings/fired=46%
  rows that GAINED a figure: 2   rows that LOST one: 1
     GAINED: | 13 | ✅ **Gated dev-login (local manual testing)** — the app login is **Google-OAuth only**
     GAINED: | 198 | 🟠 **`CONTEXT.md` has NO vocabulary for the recall subsystem - and this is the THIRD time
     LOST  : | 212 | 🟡 **A killed self-test leaves two untracked files in `.claude/hooks/`, and that path is
  FINDINGS gained: ['198']   lost: ['212']
```

"Not one row changing state" is false: three rows change figure-detection state and the finding set
changes membership — #198 arrives, #212 leaves. The finding COUNT is unchanged at 90, which is
presumably what was observed; the row-level claim is stronger than the measurement supports.

The `223` denominator is not this file at any revision in range — I checked four, because a stale
measurement against an older `docs/backlog.md` would be the charitable reading and it is not
available:

```bash
$ for rev in origin/master ecc1460f 1efc6c51 31e8768a; do git show $rev:docs/backlog.md …
origin/master   rows=247  fired=194  findings=95
ecc1460f        rows=247  fired=195  findings=90
1efc6c51        rows=247  fired=195  findings=90
31e8768a        rows=247  fired=195  findings=90
```

247 rows everywhere, never 223, and no figure of 106. The companion claim on the same change at
`check-provenance.py:201` — *"firing rate unchanged at 46% (90/195)"* — reproduces exactly, so the
`48% (106/223)` figure is the outlier and most likely came from an intermediate draft.

**What would have to change:** restate as "the finding count is unchanged at 90; two rows gain a
figure and one loses one, and the findings exchange #212 for #198", with the denominator that
matches the file. This repo's own rule is that a retrospective number needs provenance.

---

## Low

### L1 — the frontier "four reachable arms" bound cannot see two other reachable texts

**`scripts/codex-frontier-model.py:477-479`**

```python
    case("...and the four goldens are four DISTINCT texts, so no case can be satisfied by "
         "another arm's output — the bound is the enumeration, not the count",
         len({_GOLDEN, _GOLDEN_MIXED, _GOLDEN_EMPTY, _GOLDEN_NONEAR}), 4)
```

The comment at `:444-446` says the case "fails if a fifth shape is added without a golden". It
cannot: the four goldens pin the four arms of the `if near / if listed / elif models / else` chain,
and two reachable text shapes live outside that chain. `scratchpad/atk/e1_misc.py`:

```
  no client_version, empty models:
        the cache holds 0 model(s), fetched by client_version ?
  listed model with NO slug (near-miss arm):
      -> contains '<no slug>'
```

`codex-frontier-model.py:165` (`data.get('client_version') or '?'`) and `:189`
(`m.get('slug') or '<no slug>'`) are both reachable and neither appears in any golden; all four
golden inputs supply a `client_version`. Adding a sixth fallback to the shared prefix would not move
`len({...})` off 4. Low because both are fallbacks in text the goldens otherwise pin, not new arms.

### L2 — the find-claim tail can state a traversal property the traversal does not have, again

`scratchpad/atk/a2_more.py` case G — `root/node_modules/claim.md` plus `root/vendor -> node_modules`:

```
   files  : ['ok.md', 'vendor/claim.md']
   pruned : ['node_modules']
   rc     : 1
   out    : ... (2 file(s) searched, 1 dir(s) not walked (node_modules))
```

The run says `node_modules` was not walked and searched its contents through the alias. This is the
*safe* direction — more searched, not less — and literally true of the name, but it is the same
genus as the defect the fold rewrote this message to remove (`find-claim.py:729-731`: "REPORT WHAT
WAS ACTUALLY PRUNED, not the constant … which claimed a traversal property it did not have").

### L3 — the deny-list path lowercases the suffix and the allow-list path does not

**`scripts/find-claim.py:290-296`**

```python
                    if suffixes is not None:
                        (out if q.suffix in suffixes else skipped).append(q)
                    elif q.suffix.lower() in BINARY_SUFFIXES:
                        skipped.append(q)
```

`q.suffix.lower()` on the deny-list branch, bare `q.suffix` on the allow-list branch.
`scratchpad/atk/h1_case.py`, over a directory holding `a.PNG` and `b.MD`:

```
deny-list path  : files= ['b.MD', 'ok.md'] skipped= ['a.PNG']
allow-list path : files= ['ok.md']         skipped= ['a.PNG', 'b.MD']
```

A caller asking the narrow question `suffixes={".md"}` — which `find-claim.py:119-121` says is the
whole reason the allow-list was retained — silently drops `b.MD`. It lands in `skipped`, so it is
counted rather than invisible, and no CLI path reaches `suffixes` at all; that is why this is Low
rather than part of H1.

### L4 — `--diff-coverage` warns on the fold's own witness helper

```bash
$ python3.12 scripts/check-plan-code.py --diff-coverage
  scripts/find-claim.py
      _spy() changed, and no mutation anchor lands inside it
WARN — 1 function(s) this branch changed carry no mutation that reaches them.
```

Warn-only by #56, and `_spy` is a three-line test double, so this is noise rather than a gap. Noted
because it is the only output of that gate on this branch.

### L5 — `collect_files`' own CANNOT RUN message drops the counts the fold just threaded into `verdict`

**`scripts/find-claim.py:302-304`**

```python
    if not out:
        return [], skipped, pruned, "CANNOT RUN — the given paths contain no readable text files."
```

**`scripts/find-claim.py:702-705`** prints `err` and returns before any tail is built:

```python
    files, skipped, pruned, err = collect_files(args.paths)
    if err:
        print(err, file=sys.stderr)
        return 2
```

So `skipped` and `pruned` are returned and then discarded on exactly this path.
`scratchpad/atk/j1_err.py` — three different worlds, one message:

```
--- empty directory
    returns: files=0 skipped=0  pruned=0  rc=2
    stdout/err='CANNOT RUN — the given paths contain no readable text files.'
--- directory holding ONLY 20 binary files
    returns: files=0 skipped=20 pruned=0  rc=2
    stdout/err='CANNOT RUN — the given paths contain no readable text files.'
--- directory holding ONLY a pruned subdir
    returns: files=0 skipped=0  pruned=1  rc=2
    stdout/err='CANNOT RUN — the given paths contain no readable text files.'
```

"Contains no readable text files" is true of all three and useless in two: the caller who pointed
this at a directory of images, or at one whose only content is `node_modules`, is told nothing about
why. Low rather than part of Codex's Low because every arm is rc=2 — loud, and in the safe
direction — so this is diagnostics, not a wrong answer. It is the same class the fold just fixed
three arms of, and this is the fourth.

### L6 — the brief's own arithmetic, checked

`EXPECTED_MUTATIONS` is **1,493**, not the 1,476 the brief states (1,476 was the pre-`1efc6c51`
value; `check-plan-code.py:5420` asserts 1493). Suite counts are 64 / 93 / 81 / 34 / 226 for
find-claim / provenance / withdrawal / frontier / plan-code — all five match, and the 34 is the
Blocking.

---

## Checked and found SOUND

Everything here was checked by running something, and where a pass could have been ambient I made
the code change that should break it and watched.

**Codex's seven findings — each fix verified, four of them by reverting it.**
Hand-mutation harness `scratchpad/atk/g1_mut.py`: copy the snapshot, apply one AST-validated edit,
run that file's suite in a subprocess, report rc and the failing case names.

```
[KILLED  ] rc=1  find-claim.py: followlinks=True -> False
            [FAIL] ⭐ H1: the DIRECTORY form reaches a `.rst`, a suffixless file AND a symlinked one: got 2 want 3
[KILLED  ] rc=1  check-withdrawal.py: figure_offset_in_hit always 0 (= signature start)
            [FAIL] ⭐ figure_offset_in_hit locates the FIGURE, not the signature's start: got 0 want 13
            [FAIL] ...and a second hit text at a different figure gives its own offset: got 0 want 6
[KILLED  ] rc=1  check-withdrawal.py: paragraph-break alternative weakened
            [FAIL] ...and a PARAGRAPH break is still a boundary
[KILLED  ] rc=1  check-plan-code.py: min_static 4 -> 400
            [FAIL] ⭐ r2: an f-string that PRODUCES the name explains it exactly
[SURVIVED] rc=0  check-provenance.py: no-op control on LABEL_BEFORE        <- the CONTROL
```

The no-op control survived, so a red above is the edit and not the harness.

**Codex H1's three witnesses, re-run.** `scratchpad/atk/a2_more.py`. A symlinked directory outside
the root is reached; a pruned directory the caller NAMES is searched (`named_pruned` = 1 file); the
prune is real (0 `scandir` calls inside `node_modules` in `_h1_witness`, where the `rglob` version
made 4). Four further symlink shapes I built all find the claim and terminate: a symlink
alphabetically before its real target, a symlink to the walked root itself, two names for one
directory, and a dangling symlink. The cycle guard's behaviour is correct; M5 is only that nothing
tests it.

**Codex M4's live witness, re-run against the fold** (`scratchpad/atk/f1_sound.py`, a real git repo
per run, `main(["--strict","--base",base])`):

```
  rc=1  lead='The status was green.'          -> SURVIVOR docs/copy.md:1  (was rc=0, suppressed)
  rc=0  lead='The status is green. count was' -> suppressed as history: 1 hit(s) — 'was 'x1   (known positive)
  rc=1  lead='The status is green.'           -> SURVIVOR  (control, no marker anywhere)
```

Three outcomes from three leads, so the fixture discriminates rather than asserting rc=1 everywhere.
Codex's wrap witness is also fixed — `history_marker` returns `'was '` for both
`the sweep holds 1,414 anchors today (was wrong).` and the same text wrapped before the figure.

**Codex M1's docstring witness.** `case_name_literals` now excludes docstrings and bare string
statements and keeps real case names: `'the old case is gone forever' in literals -> False`,
`'replacement title' in literals -> True`.

**Codex's LOW is fully fixed and its arms are reachable from the CLI.** `scratchpad/atk/h1_case.py`
drives `main` at all three `--expect` values over a directory with one skipped file:

```
  --expect absent   rc=0  EXCLUDED-in-output=True
  --expect present  rc=1  EXCLUDED-in-output=True
  --expect report   rc=0  EXCLUDED-in-output=True
```

So the qualification is not merely present in `verdict`'s return value but reaches stdout on every
arm, including the `MISSING`/`present` arm the Low was filed about. An uppercase `.PNG` is skipped
(the deny-list branch lowercases) and an uppercase `.MD` is searched.

**Codex M3's literal witness.** `has_provenance('we cannot look at HEAD') -> False`; bare
`the tree at HEAD held 1,416 -> False`; `measured at HEAD, … -> True`; and row #255's own
`cannot read HEAD -> False`, with `read` deliberately absent from the verb list. H2 is a different
input, not this one.

**Codex H2's two new goldens.** `refusal_message` for the empty-cache and no-near-miss inputs equals
its golden byte for byte, and the four golden texts are four distinct strings.

**`figure_offset_in_hit` when the figure appears TWICE inside one signature.** `hit_text.find` takes
the FIRST occurrence, which is a real choice, and I tried to make it the wrong one
(`scratchpad/atk/i1_twice.py`):

```
  line      'it was 1,414 then. Now 1,414 holds.'
  signature 'it was 1,414 then. Now'            find-> 7   second occurrence at -1
  line      'was 1,414 then 1,414 now'
  signature 'was 1,414 then 1,414'              find-> 4   second occurrence at 15
```

It cannot be made wrong here, and the reason is `CONTEXT_WORDS = 2`: a signature is at most five
tokens, so the two occurrences either do not both fit inside it (case 1 — the second `1,414` is
outside the window and gets its own signature and its own hit) or they fit and share a sentence
(case 2, where `was ` is in the figure's own sentence either way). Making this wrong needs a
sentence boundary between two occurrences of one figure within five tokens, which I could not
construct. Sound as written, and sound *because* of the window bound rather than by accident — so
raising `CONTEXT_WORDS` would reopen it.

**`figure_offset_in_window` at both document edges.** `min(start, span)` is the hit's offset in
`window_around`'s slice for all `start`, because the slice begins at `max(0, start - span)`; the end
of the document cannot affect it. Checked at `start=12` and `start=4000` (the file's own case) and by
reading both functions together.

**`collect_files` went from a 3-tuple to a 4-tuple, and nothing outside the file unpacks it.**
This is the change most likely to break a caller silently, so I enumerated them rather than assuming:

```bash
$ grep -rn "collect_files" --include=*.py --include=*.sh --include=*.yml .
scripts/find-claim.py:430   files, _skipped, _pruned, _err = collect_files([str(d)])
scripts/find-claim.py:479   walked, skipped, pruned, _ = collect_files([str(d)])
scripts/find-claim.py:482   named, _, _, _ = collect_files(
scripts/find-claim.py:484   named_pruned, _, _, _ = collect_files([str(d / "node_modules")])
scripts/find-claim.py:538   len(collect_files([str(d)], {".md"})[0]) …          # index, arity-agnostic
scripts/find-claim.py:702   files, skipped, pruned, err = collect_files(args.paths)
scripts/check-fixture-variation.py:347  "collect_files.paths"               # a ratchet NAME, not a call
```

Every call site is inside `find-claim.py` and every one unpacks four. `check-withdrawal` imports
`find-claim` but uses only `build_pattern` and `find_in_text` (`:652`, `:852-854`), never
`collect_files`, so the arity change cannot reach it. And all three `err`-bearing returns go through
`main`'s single `if err: return 2`, so the two different empty returns the brief asks about cannot
confuse a caller — there is only one.

**`is_history_context` callers.** `grep -rn is_history_context scripts/ .claude/` — four call sites
(`:557`, `:559`, `:584`, `:741`, `:754`, `:867`), every one passing `figure_at=`. The parameter is
keyword-only with no default, so a missed caller is a `TypeError` at the call site rather than a
silent fall back to the window-wide rule.

**The L3 cross-check costs half a second and nothing else.** `check-withdrawal` loads
`check-provenance` by `importlib.util.spec_from_file_location` inside its suite, and also loads
`find-claim`; `check-provenance` imports neither, so there is no cycle and no doubled side effect
(each is one module exec, and `_check_provenance()` is called from two cases).

```bash
$ time python3.12 scripts/check-withdrawal.py --self-test > /dev/null   # 81 cases
real	0m0.608s
$ time python3.12 scripts/check-provenance.py --self-test > /dev/null   # 93 cases
real	0m0.082s
```

So the two imports account for roughly 0.5 s of a 0.6 s suite — measurable, and irrelevant beside
the 44-file control phase of a mutation run. The L3 case was correctly retargeted when
`check-provenance` stopped expressing the single-digit rule as a regex: asserting the old `NUM_RE`
equality would have silently stopped testing anything.

**The ratchets, by running them.**

```bash
$ python3.12 scripts/check-plan-code.py --binding          # rc=0
binding OK — 1501 anchor(s) across 1493 entries each resolve to exactly one site; 67 expect(s)
name no whole literal but ARE explained by one

$ python3.12 scripts/check-fixture-variation.py            # rc=0
fixture variation OK — 901 parameter(s) examined across 67 file(s); 117 known-unvaried ratcheted,
7 exempt with a written reason

$ python3.12 scripts/check-anchors.py          # rc=0
$ python3.12 scripts/check-docs.py             # rc=0
$ python3.12 scripts/check-ratchet-contract.py # rc=0
$ python3.12 scripts/check-dashboard-entry.py  # rc=0
```

**`EXPECTED_MUTATIONS` verified per target, not only as a sum** (`scratchpad/atk/e1_misc.py`, parsing
each `scripts/mutations/*.json` independently):

```
declared sum = 1493   actual sum = 1493   per-target mismatches = 0
```

So the case asserting `sum(EXPECTED_MUTATIONS.values()) == 1493` is not passing over a manifest that
drifted in two places that cancel.

**`check-review-rounds.py` returns rc=1 at this commit, and that is THIS DOCUMENT'S absence, not a
defect:**

```
  ✗ backlog-249-260 round 2: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
```

It goes green when this file lands. I am recording it so the next reader does not spend the time I
did establishing that it is not a second red.

---

## CANNOT RUN

Scored as neither pass nor fail.

**The full mutation sweep.** `--mutate .` has no per-file targeting — only `--shard I/N`, which is
round-robin over the whole manifest and so cannot isolate the five changed files. I started
`python3.12 scripts/check-plan-code.py --mutate . --shard 1/20` in the worktree; it completed its
44-file control phase green and was partway through its 75 mutations when I filed this. **0
survivors in what it reached**, but a fifth of a twentieth of 1,493 entries is not a measurement of
attribution across the manifest, and I am not reporting it as one. My eight hand-mutations above are
targeted, not a substitute: they cover the five new mechanisms and nothing else.

**Whether M4's five sentence shapes produce a live false negative.** I measured the corpus-wide
effect (+1,358 weak suppressions, 1,335 of them crossing a line break) and hand-sampled them, and
the sample is dominated by genuine wraps. Establishing a real survivor wrongly suppressed needs a
diff that corrects a figure near one of those five shapes, which this branch's diff does not contain.
The five witnesses are constructed; that is stated rather than hidden.

**`--mutate` under CI's own interpreter.** CI runs these steps as bare `python3` on its runner image;
I ran `python3.12` locally. The Blocking (a declared count vs a printed count) is
interpreter-independent, but I did not reproduce any gate under CI's actual Python.

**The three serialise-only hazards.** I ran no `git` write, touched nothing under `scripts/`, and
wrote exactly this one file under `docs/reviews/claude/`. Another worktree holding this branch exists
at `677677e1-…/scratchpad/wt-backlog`; I did not read or write it.

---

# ⟳ COORDINATOR'S FOLD AND CONVERGENCE ASSESSMENT — appended 2026-10-07 22:4x PDT

All thirteen findings are folded. This section is the coordinator's, not the reviewing half's,
and it exists because `docs/dev-process.md` requires one specific question to be answered in the
round document with per-finding evidence.

## 1 · THRASHING IS ARMED, AND THE ANSWER IS THRASHING — NOT A PROSE FLOOR

`dev-process.md`: *"It fires when **two consecutive rounds carry findings caused by the previous
round's own fix, in one component**."* The condition requires one component. It is met in five.

| | findings | caused by the previous round's fix |
|---|---|---|
| round 2, Codex half | 7 | **7 of 7** — every one was about round 1's fixes |
| round 2, Claude half | 13 | **11 of 13** — B1 H1 H2 M1 M2 M3 M4 M5 M6 L1 L2 |

Components carrying findings in BOTH consecutive rounds: `check-provenance` (M2,M3 → H2,M2,M3,M6),
`find-claim` (H1,L1 → H1,M5,L2,L3), `check-withdrawal` (M4 → M4), `check-plan-code` (M1 → M1),
`codex-frontier-model` (H2 → B1,L1).

**This is NOT the prose floor.** The distinguishing test in `review-method.md` is *can a redesign
remove it?* — and for the dominant class it provably can, because doing so is what fixed four of
this round's findings:

- **H2 was fixed by DELETING a mechanism, not extending one.** An eight-verb list with no `\b`
  accepted `unverified at HEAD` and `nothing was observed at HEAD` — prose asserting that no
  measurement happened. The fix requires `HEAD` to be backticked or suffixed, which is what every
  *other* alternative in the same regex already demands. 15/15 witnesses, 0 rows lose provenance,
  rate unchanged, **and the rule got shorter.**
- **M3 was fixed by IMPORTING the rule's existing owner.** `check-docs.CELL_SPLIT` owns markdown
  cell-splitting and `check-features`, `check-plan-code` and `gen-backlog-page` already import it.
  `check-provenance` read `row[at:at+40]` raw — a second implementation of one rule, this repo's
  most-measured defect — which is *why* the counted noun came from the next column.
- **M1 was fixed by a POSITIONAL rule**, not a floor: candidates now come only from a call's first
  argument where the call has ≥2 positional args. Patterns 1,585 → 96; the invented-expect
  downgrade falls from **62 of 62 files to 2**.
- **H1 was fixed by ROUTING INTO AN EXISTING CHANNEL.** An unreadable directory now joins the same
  `unreadable` list an unreadable file already used, and takes the same rc=2. The correct sentence
  was already written one function away.

**The one finding where no redesign helps is M2, and it is stated as a heuristic rather than
fixed.** Nothing lexical separates `Stage 3 cloud-sync` from `3 rounds`; the review's proposed
alternative (require a plural) was measured and is worse — it still admits five of ten false
positives and makes all five false negatives worse. Defensible only because `verdict` is
**warn-only unless `--strict`** (measured) over rows a branch ADDS, so a wrong answer costs a
dismissible warning. All fifteen witnesses are now pinned as `⚠ KNOWN WRONG` / `⚠ KNOWN MISSED`
cases, so the bound is data and a regression is visible.

## 2 · THE SECOND CLASS, WHICH NO REDESIGN TOUCHES

**Six findings across two rounds were a COMMENT asserting a property or measurement that was not
re-derived** — r2-Codex H1 (`"node_modules not walked"` while `scandir` ran 4× inside it), r2-Claude
H2 (a word-boundary claim three lines above the code that dropped it), M4 (stated a rise without
its direction), M6 (**two figures that do not reproduce at any revision**), L1 (a bound that cannot
see two reachable texts), L2.

⭐ **And `check-provenance` enforces exactly this rule — over backlog ROWS.** 59 scripts carry a
`MEASURED` claim in a comment and **no guard reads any of them.** That is the inverted-direction
shape backlog #98 was filed for, one corpus over. It is filed as follow-up work, not fixed here:
this branch is not the place to add a fifteenth guard.

## 3 · VERDICT

**NOT CONVERGED at `31e8768a`; the fold above is a candidate for round 3.** Convergence needs two
consecutive clean rounds and round 2 was not clean on either half. Phase 6 is **armed** and owed on
the two classes above — not on this branch's correctness, which is well measured, but on the
question neither per-round review can ask: whether a family of text-heuristic guards over prose
should exist in this shape at all.

⛔ **Not merged. Merging is the owner's gate.**

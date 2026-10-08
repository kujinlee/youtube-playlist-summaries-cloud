# Round 3 adversarial review, CLAUDE half — backlog #249–#260 at `1a976eff`

**VERDICT: NOT CONVERGED**

Subject pinned: `git rev-parse HEAD` → `1a976eff45718cb0a2fd015a8fcbdf9639560cdb`, `git status
--porcelain` empty. Read from `/tmp/r3snap` (`git archive 1a976eff | tar -x -C /tmp/r3snap`);
suites and the mutation harness driven in the worktree, which has `node_modules` (the snapshot
does not, and `stage_tree` correctly refuses it: *"CANNOT RUN — node_modules/typescript is
missing … TREAT THIS AS NOT CHECKED"*). Interpreter `python3.12` (3.12.9) throughout; this
machine's bare `python3` is 3.14.4.

---

## ⭐ THE CLAIM UNDER TEST, ANSWERED FIRST

> *"Round 3's fixes were deliberately a different KIND: four of five REMOVED a mechanism rather
> than extending one, on the theory that a fix which deletes cannot cause the next round's
> finding."*

**The theory is not refuted. The premise is.** Measured against `git diff e330ca80..1a976eff`,
**one** of the five fixes is a narrowing; the other four ADD a mechanism, and **both of my top
two findings sit in the added ones.**

| r3 Codex finding | What the fold actually did | Finding from me |
|---|---|---|
| M2 — `HEAD123` | **NARROWED**: `` `HEAD[~^]?\d*` `` → `` `HEAD(?:[~^]\d*)?` `` (one character class tightened) | none — attacked below, held |
| H2/H3 — withdrawal | **ADDED** 2 regex alternatives, 1 new function (`figure_offsets_in_hit`), widened the caller to `all(...)` | none in the code; M3 below is about its stated bound |
| H1/M1 — `case_name_patterns` | **ADDED** two candidate branches (keyword args; *any* single-target assign). Patterns 96 → 137 | **H1 — the stated bound is false** |
| M3 — metadata failure | **ADDED** a `try/except` at one of two call sites | **M1 — the other call site still crashes** |
| L1 — directory identity | **REPLACED** `resolve()` with `os.stat`, **ADDED** two probes | **B1 — the probe is inert on CI's filesystem and its mutation survives there** |

So the honest reading is the narrower one and it is still useful: **the single fix that only
removed produced nothing, and every finding below is in a fix that added.** The fold's framing
("four of five REMOVED") does not survive the diff — a 97-line addition to `check-plan-code.py`
that raises the candidate population by 43% is not a deletion, whatever the rule it replaced.

This is the fourth consecutive round in which the previous round's fix is the defect, and B1 is
the third consecutive round in which the fold reddens a required CI check.

---

## Blocking

### B1 — `_case_alias_probe` is inert on a case-sensitive filesystem, so the mutation that pins the directory-identity fix SURVIVES in CI and `--mutate .` exits 1

`scripts/find-claim.py:292-303` (the fix), `:646-664` (the probe), `:800-804` (the two cases),
`scripts/mutations/find-claim.json:290-302` (the mutation).

The fix and the probe:

```python
                try:
                    st = os.stat(dirpath)
                    real = (st.st_dev, st.st_ino)
```

```python
def _case_alias_probe() -> tuple:
    """(n_files, n_hits) over two symlinks to ONE directory spelled two ways. r3 Codex L1.

    macOS is case-insensitive and case-preserving, so `CaseDir` and `casedir` are the same
    directory with different `resolve()` strings. The walk counted its files twice.
    """
        target = d / "CaseDir"
        ...
        _os.symlink(target, d / "a")
        _os.symlink(d / "casedir", d / "outer" / "b")
```

**`d / "casedir"` only exists on a case-INSENSITIVE filesystem.** CI runs
`runs-on: ubuntu-latest` (`.github/workflows/ci.yml:630`), which is case-sensitive: there
`outer/b` is a dangling symlink, `q.is_file()` is False, it is dropped, and the probe returns
`(1, 1)` whether the fix is present or not.

Measured on a real case-sensitive volume (`hdiutil create -size 1g -fs "Case-sensitive APFS"`,
mounted at `/Volumes/CSTEST`, confirmed case-sensitive by `(d/"casedir").exists() == False`):

```bash
# the probe itself, shipped code, both filesystems
TMPDIR=/Volumes/CSTEST python3.12 -c "import runpy;print(runpy.run_path('scripts/find-claim.py')['_case_alias_probe']())"
python3.12            -c "import runpy;print(runpy.run_path('/tmp/csmut/fc_mut.py')['_case_alias_probe']())"
TMPDIR=/Volumes/CSTEST python3.12 -c "import runpy;print(runpy.run_path('/tmp/csmut/fc_mut.py')['_case_alias_probe']())"
```

where `fc_mut.py` is the shipped file with the manifest's own edit applied
(`real = (st.st_dev, st.st_ino)` → `real = str(Path(dirpath).resolve())`, `ast.parse` clean, text
changed):

```text
shipped, case-sensitive volume : (1, 1)
mutant, case-INsensitive /tmp  : (2, 2)     <- killed here
mutant, case-sensitive volume  : (1, 1)     <- survives here
```

Whole suite, control and mutant, on the case-sensitive volume:

```text
=== CONTROL (shipped) self-test, TMPDIR=case-sensitive ===   rc=0   76/76 passed   0 [FAIL] lines
=== MUTANT   self-test, TMPDIR=case-sensitive ===            rc=0   76/76 passed   0 [FAIL] lines
```

And through the shipped harness — `stage_tree` + `control_is_green` + `run_mutations`, green
control before and after, all 24 declared `find-claim` mutations:

```bash
TMPDIR=/Volumes/CSTEST python3.12 /tmp/csmut/sweep.py scripts/find-claim.py
```

```text
scripts/find-claim.py: mutations=24 control rc=0 green=True (0.1s)
  ok=False survivors=1 after-control rc=0 green=True
   REPORT: mutation SURVIVED — ⟳ r3 Codex LOW — directory identity goes back to a RESOLVED STRING,
   so on a case-insensitive filesystem two spellings of one directory are two directories and its
   files are counted twice: the suite stayed green, so no case can fail for what it names
TOTAL killed=23 survivors=1
```

The same command with the default (case-insensitive) `TMPDIR` reports `ok=True survivors=0`,
which is why the fold's own local run was green.

`main`'s `--mutate` arm ends `return 0 if ok else 1`, so this is **rc=1** in CI. The entry is at
1-based position **1236 of 1510** in the loaded manifest and `shard_of` is `muts[index-1::total]`,
so at N=8 it lands in **shard 4** (`--shard0 3/8`) → `mutation-sweep (4)` red →
`mutation-sweep-complete` red, which `ci.yml:764-772` names as *"the stable name to require"*.

**What would have to change.** The probe must build a world that is the same on both
filesystems. Two options, both cheap: create the second directory entry with an explicit
hardlink-free alias that exists on every platform (e.g. two symlinks `a -> CaseDir` and
`b -> ./a`, which differ in `resolve()` on no platform — so instead assert the property
directly), or make the case the *property* rather than the scenario — e.g. assert that two
distinct paths that `samefile` each other yield one entry in `seen_real`, skipping with an
explicit `CANNOT RUN` value when `samefile` is False because the filesystem is case-sensitive.
⛔ A skip must not return the asserted value — see M2 below for that failure mode already
present in the sibling probe.

---

## High

### H1 — `case_name_patterns`' third branch applies NO name test, so *"non-case templates entering the candidate set fall from 11 of 62 files to 0 — by construction"* is false: it is 34 of 62, and the reach probe got WORSE (12 → 17 files)

`scripts/check-plan-code.py:1605-1611`, claim at `:1588-1591`.

The shipped claim:

```python
        # non-case templates entering the candidate set fall from **11 of 62 files to 0 — by
        # construction, since a non-case producer cannot be named like one**.
```

The code that is supposed to make it true:

```python
        elif isinstance(n, ast.Assign):
            targets = [t.id for t in n.targets if isinstance(t, ast.Name)]
            if any("CASE" in t.upper() for t in targets):
                for el in ast.walk(n.value):
                    if isinstance(el, (ast.Tuple, ast.List)) and el.elts:
                        cands.append(el.elts[0])
            elif len(targets) == 1:
                cands = [n.value]
```

`elif len(targets) == 1: cands = [n.value]` tests **nothing** about the name. "By construction"
is asserted of a branch that has no construction to assert it with. Every shape the brief asked
about becomes a case-name pattern:

```bash
python3.12 -c "
import runpy; cnp = runpy.run_path('scripts/check-plan-code.py')['case_name_patterns']
for s in [...]: print(len(cnp(s)), '<-', s)"
```

```text
1 pattern(s)  <- CATALOG_SQL = f"select {col} from pg_constraint where conrelid = any (array{t})"
      ^select\ .*?\ from\ pg_constraint\ where\ conrelid\ =\ any\ \(array.*?\)$
1 pattern(s)  <- url = f"https://example.com/videos/{vid}/summary"
      ^https://example\.com/videos/.*?/summary$
1 pattern(s)  <- rel = f"docs/{sub}/{f.name}"
      ^docs/.*?/.*?$
1 pattern(s)  <- _pals = f':root[data-theme="light"]{{--bg:#fff}}'
1 pattern(s)  <- body = f"<h2>{heading}</h2><p>{text}</p>"
1 pattern(s)  <- msg = f"CANNOT RUN: {reason} so nothing was measured"
```

`^docs/.*?/.*?$` forgives **any** expect of the form `docs/X/Y` — the exact "nearly as broad as
`^.*?.*?$`" failure the comment at `:1545-1550` says attempt 1 suffered from.

Over the real population (all 62 target files from `load_manifests`, candidate branches labelled
by replicating the shipped selection):

```text
candidate rows by branch: {'call': 62, 'assign': 80}
total patterns (shipped fn): 137          # attempt 2 produced 96
files with >=1 NON-case-named single-target f-string assign: 34 of 62
top assign targets: msg(4) detail(3) authority(3) body(3) store_error(3) subject(2) extra(2)
                    where(2) chart(2) entries_html(2) CATALOG_SQL(1) rel(1) _pals(1) src(1) …
```

Live witnesses include `scripts/check-guard-coverage.py:336` `CATALOG_SQL = f"""select 'check:' ||
conname from pg_constraint …"""` (a SQL fragment), `scripts/check-anchors.py:122`
`rel = f'docs/{sub}/{f.name}'` (a repo path) and `scripts/brief-compose.py:1491`
`_pals = f':root[data-theme="light"]{{--bg:#fff}}'` (a CSS palette).

The review's own reach probe — replace each pattern's `.*?` with an invented title, un-escape,
and ask whether `binding_problems` downgrades it from ERROR to warning — **moves the wrong way**:

```text
attempt2 (e330ca80): patterns=96   files whose invented expect is FORGIVEN=12/62
SHIPPED (1a976eff):  patterns=137  files whose invented expect is FORGIVEN=17/62
```

**And the branch buys nothing.** Re-running the live binding pass with the branch removed:

```text
assign branch=ON (shipped): expect errors=0  warnings=67
assign branch=OFF:          expect errors=0  warnings=67
```

Zero live entries depend on it. It adds 41 patterns and 5 forgiving files for no live benefit.

**Its own case cannot see this.** `scripts/check-plan-code.py:5663-5664`:

```python
    case("⭐ r3: a case name ASSIGNED to a variable first is accepted too",
         len(case_name_patterns('title = f"{x} works"')), 1)
```

`title` is doing no work: `sql = f"{x} works"`, `url = …`, `msg = …` all return 1 as well. The
fixture *looks* like it tests a name rule; it tests only that the branch exists — which is also
all its mutation (`elif False:`) tests. This is *a case can pass for an ambient reason*, and the
ambient reason here is that the rule the comment describes was never written.

**What would have to change.** Constrain the assign branch the way the call branch is
constrained — accept `cands = [n.value]` only when the single target matches
`CASE_NAME_KEYWORDS` or `CASE_CALL_RE`-ish spelling — and re-derive the "non-case templates in
the candidate set" figure (currently 34 of 62) and the reach figure (currently 17 of 62) into the
comment, the backlog row and the roadmap. Then change the case fixture so a NON-case target name
is asserted to yield `[]`, which is the assertion that makes the mutation mean something.

---

## Medium

### M1 — the metadata-failure guard was applied to one of two `stat` call sites; an explicitly NAMED unreadable path still exits 1 with an unhandled `PermissionError`

`scripts/find-claim.py:275` (unguarded) vs `:327-333` (guarded, this fold).

The fold's own comment states the convention the crash violates:

```python
                    # ⛔ r3 Codex MEDIUM — A METADATA FAILURE IS NOT A REASON TO SKIP SILENTLY,
                    # … the run exited with an UNHANDLED PermissionError traceback — rc=1, which
                    # under this repo's convention means "violation found", not "cannot run".
```

Fifty-two lines above it, the caller-named arm is untouched:

```python
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
```

`Path.is_dir()` does **not** swallow `EACCES`. Measured:

```bash
python3.12 - <<'PY'
# root/ok.md (control), locked/claim.md (the claim), chmod 000 on `locked`,
# then NAME the unreadable file on the command line
r = subprocess.run(["python3.12","scripts/find-claim.py",
     "--pattern","the claim is still live","--control","control phrase",
     "--expect","absent", str(lock/"claim.md"), str(d/"ok.md")], ...)
PY
```

```text
explicitly NAMED unreadable file: rc=1  CANNOT RUN in output: False  Traceback: True
   File "/private/tmp/r3snap/scripts/find-claim.py", line 275, in collect_files
     if p.is_dir():
   PermissionError: [Errno 13] Permission denied: '.../locked/claim.md'

explicitly NAMED unreadable dir : rc=2  CANNOT RUN in output: True   Traceback: False
```

rc=1 on this tool means `FOUND — n occurrence(s) of a claim that was expected to be absent`
(`:207-209`). A crash and a real finding are the same exit code, which is precisely the sentence
the fold wrote about the other call site.

**What would have to change.** Guard `p.is_dir()` / `p.is_file()` in the caller-named arm with
the same `try/except OSError → unreadable_dirs` the discovered-entry arm now has, and add a case
that NAMES the unreadable path rather than discovering it.

### M2 — `_metadata_failure_probe`'s early return is a self-granted pass: under root (or any mount where `chmod 000` still reads) all three of its cases pass **and the mutation survives**

`scripts/find-claim.py:626-631`.

```python
            if _os.access(lock, _os.R_OK):          # the chmod did not take; do not pretend
                return (2, True, True)
```

The comment says *do not pretend*; the return pretends — `(2, True, True)` is exactly the triple
the three cases at `:798-804` assert. Measured, by making `os.access` answer as it does for root:

```bash
python3.12 - <<'PY'
import os, runpy
os.access = lambda *a, **k: True          # simulate root
print("SHIPPED:", runpy.run_path('scripts/find-claim.py')['_metadata_failure_probe']())
print("MUTANT :", runpy.run_path('/tmp/csmut/fc_mut2.py')['_metadata_failure_probe']())
PY
```

```text
SHIPPED: (2, True, True)   (cases assert (2, True, True))
MUTANT (guard removed): (2, True, True)   (cases assert (2, True, True))
```

`fc_mut2.py` is the shipped file with the manifest's own edit applied (the `try/except OSError`
around `q.is_file()` reverted). The mutation at `scripts/mutations/find-claim.json:276-289`
therefore survives in any environment where the `chmod` does not bite.

This is not live on `ubuntu-latest` (the runner is the non-root `runner` user), so it is a
Medium rather than a second Blocking — but it is the same defect class as B1 (a probe whose
world is not guaranteed), in the sibling probe added by the same commit, and this repo's own rule
is that a CANNOT RUN is a failure and never a pass.

**What would have to change.** Return a sentinel the cases do not assert — e.g. `(None, None,
None)` with the cases reading `got in ((2, True, True), SKIPPED)` is still wrong; the correct
shape is a fourth returned field `measured: bool` that a case asserts `True`, so an unmeasured
run goes RED rather than green.

### M3 — the `SENTENCE_SPLIT` bound was measured over 390 of the 393 files `docs_files()` actually returns

`scripts/check-withdrawal.py:279-281`:

```python
# MEASURED over 48,046 figure occurrences: weak suppressions 3,688 -> 3,630 (58 fewer false
# negatives), median sentence 180 -> 177, and a genuine wrap is still ONE sentence.
```

Re-derived with the shipped `docs_files`, `window_around`, `figure_offset_in_window`,
`STRONG_MARKERS`, `WEAK_MARKERS` and both `SENTENCE_SPLIT` revisions, over `1a976eff`:

```text
figure occurrences: 49240    (comment claims 48,046)
weak suppressions  old: 3688  new: 3630  delta: -58   (reproduces exactly)
median sentence    old: 184.0 new: 181.0  (comment claims 180 -> 177)
```

The comment's figures come from a `.md`-only corpus:

```text
docs_files() suffix breakdown: {'.md': 390, '.txt': 2, '.html': 1}
.md ONLY  occ= 48046  weak old= 3688 new= 3630  median old= 180.0 new= 177.0
```

```python
    return sorted(p for p in d.rglob("*")
                  if p.is_file() and p.suffix in {".md", ".html", ".txt"} …)
```

So 1,194 occurrences in the three non-`.md` files the guard reads were outside the measurement.
**The conclusion survives** — the −58 delta is identical in both corpora — but the denominator
and the median do not describe the population the code sees, which is the recurring defect class
this repository has filed eleven times.

I also classified all 58 lost suppressions: **58 of 58 are the colon lead-in**, and the sampled
ones are genuinely separate statements (`…Enumerated from the file:\n`[93, 102, …]` — **six**.`).
So "58 fewer false negatives" is justified. The other two new boundaries — the hard break and
`1)` — change **zero** live sites; their only evidence is their constructed unit cases.

**What would have to change.** Re-run the three figures over `docs_files()` and state 49,240 /
184 → 181, or state explicitly that the measurement is `.md`-only and why.

### M4 — the "0.7% honest bound" on `expect_explained` is an artefact of one rename generator; a TRUNCATION rename is forgiven 12× as often

`scripts/check-plan-code.py:1668-1675` — *"⚠ THE RESIDUAL IS STATED RATHER THAN HIDDEN: **0.7%,
10 of 1,421 synthesised renames, still slip through.** That is the honest bound."*

Re-derived with the shipped `expect_explained` and `case_name_literals`, following the comment's
own recipe at `:1677-1679`, over all 1,510 entries:

```text
prefix-swap (the comment's own generator): 11 of 1562 = 0.70%   (comment claims 10 of 1,422 = 0.7%)
  truncation    : 135 of 1562 = 8.64% wrongly forgiven
  tail-change   :  11 of 1562 = 0.70% wrongly forgiven
  word-reorder  :   4 of 1562 = 0.26% wrongly forgiven
```

The stated rate reproduces for the generator it was measured with. It does **not** hold for a
truncation — a case retitled by shortening it — because `EXPECT_OVERLAP_FRACTION` is 30% **of the
expect**, so the shorter the renamed-away expect, the easier it is to forgive. 8.64% is twelve
times the number the comment calls "the honest bound", and the note's own warning ("a note
claiming no false negatives would be worse than no note, because the next reader would stop
looking") applies to itself.

⚠ **This is NOT round 3's fold.** `expect_explained`, `EXPECT_OVERLAP_FLOOR` and
`EXPECT_OVERLAP_FRACTION` are unchanged in `git diff e330ca80..1a976eff`; this is round 2's rule.
I report it because the brief asked the question, and because it matters to the thrashing
verdict that this one is *not* another instance of the fold-causes-the-next-finding pattern.

**What would have to change.** Either state the bound per generator (prefix-swap 0.70%,
truncation 8.64%, tail-change 0.70%, reorder 0.26%), or make the fraction symmetric — require the
overlap to cover 30% of the *literal* as well as of the expect, which is what kills the
truncation shape.

---

## Low

### L1 — five real case-name forms the NAME rule refuses, one of which this repository already writes with static names

`scripts/check-plan-code.py:1593-1611`. Measured with the shipped function:

```text
0 pattern(s)  <- direct.append((f"{x} works", 1, 1))
0 pattern(s)  <- CASES = {f"{x} works": (1, 1)}
0 pattern(s)  <- rows += [(f"{x} works", 1, 1)]          # AugAssign is not ast.Assign
0 pattern(s)  <- nm, got = f"{x} works", 1               # a Tuple target yields targets == []
0 pattern(s)  <- for t in ts: case(t, 1, 1)
```

Zero live instances today (`--binding` reports 0 expect errors), so this is a Low. But
`direct.append((…, …, …))` is a form `check-withdrawal.py:810-815` writes **right now** with
static names — an f-string there is one edit away, and the direction of the miss is the half
that REFUSES, i.e. a legitimate case reddening a required check. That is exactly the shape of
r3 Codex H1.

### L2 — `firing rate unchanged at 46% (90/195)` is stated twice and is stale; round 3's Codex half already said so and the fold did not act

`scripts/check-provenance.py:283` and `:303`. Re-derived with the shipped `is_backlog_row`,
`bolded_figures` and `findings_for` over the live `docs/backlog.md`:

```text
backlog rows: 249   figure-bearing: 197   findings: 91
firing rate: 91/197 = 46.19%
```

The rate rounds the same; the pair does not. The r3 Codex review's SOUND section says *"The
current denominator is not 195"*, and the fold left both occurrences unchanged.

### L3 — `(?<=:)\n` requires the colon to be the LAST character of the line

`scripts/check-withdrawal.py:288`. 139 live weak suppressions have a lead-in ending `: ` (colon
plus one trailing space, which is neither `(?<=:)` nor `(?<=\s\s)`). **All 139 are YAML
frontmatter** (`metadata: `, `originSessionId: …`) in `docs/memory/*.md`, and a tightened search
for a *prose* colon-plus-emphasis lead-in (`…:**`, `…:` + backtick) found **0** live instances:

```text
LIVE prose instances (colon + EMPHASIS lead-in): 0
```

So the fold's "two shapes remain open … both constructed, not live" holds for what I could
search. Stated so the next round does not re-derive it. I also found **0** live instances of the
fenced-code-block shape where the marker precedes the fence.

### L4 — the only backlog row this branch adds trips the guard this branch tightened

`python3.12 scripts/check-provenance.py --base origin/master` → rc=0 (warn-only):

```text
  #262: 4 bolded figure(s), and the row names no commit, ref, path:line or run id. Where was it measured?
WARN — 1 new backlog row carry a bolded figure with no ref, commit or run id saying where it was measured.
```

`docs/backlog.md:277` cites "found 2026-10-07 on PR #371" — a date and a PR number, both
deliberately excluded from `PROVENANCE_RE` (`:259-261`). The guard is behaving as specified; the
row is the thing to fix, with a backticked ref.

### L5 — the `*CASES*` branch mis-classifies three non-table names, harmlessly today

`scripts/check-plan-code.py:1607`. `any("CASE" in t.upper() …)` captures `CASE_CALL_RE` and
`CASE_NAME_KEYWORDS` (`check-plan-code.py:1682, :1685` — the fold's own new constants) and
`CASECALL` (`check-fixture-variation.py:1458`). It yields no patterns only because their values
are a `re.compile` call and a `frozenset({…})` (an `ast.Set`, not a Tuple/List). No live effect.

### L6 — one figure, two denominators, in one comment block

`scripts/check-plan-code.py:1660` says `41 of 1422` / `10 of 1422`; `:1670` says `10 of 1,421`
for the same quantity.

### L7 — `codex-frontier-model.py` has a third reachable refusal state that crashes

The brief's item 5. `refusal_message` / `usable_models` assume `data["models"]` is a list. A
syntactically valid cache that is not:

```bash
# HOME redirected to a temp dir holding .codex/models_cache.json = {"client_version":"1.2.3","models":"oops"}
python3.12 scripts/codex-frontier-model.py
```

```text
rc= 1
AttributeError: 'str' object has no attribute 'get'
```

`resolve_candidates` (`:211-217`) catches `FileNotFoundError`, `OSError` and
`json.JSONDecodeError` but not a well-formed document of the wrong shape. The two goldens pin
`models: []` and the all-hidden arm; neither reaches this. ⚠ `codex-frontier-model.py` is
**unchanged** in `e330ca80..1a976eff` — this is round 2's subject, reported because the brief
asked for the third state.

---

## Checked and found SOUND

Named with how, because a clean verdict is worth only what the attempt behind it was.

**The five declared self-test counts, each by running its suite** (`python3.12 scripts/<g>.py
--self-test`, rc read directly, no pipe):

```text
find-claim               rc=0  76/76 passed
check-withdrawal         rc=0  90/90 passed
check-provenance         rc=0  128/128 passed
check-plan-code          rc=0  234/234 passed
codex-frontier-model     rc=0  36/36 self-test cases passed
```

All five match the brief's figures. `python3.12 scripts/check-selftest-counts.py` → rc=0,
*"55 script(s) declare a count, every one verified by running it"*.

**The arithmetic, not taken:**

```text
sum(EXPECTED_MUTATIONS) = 1510   declared in the case: 1510
loaded entries: 1510   load errors: none
per-file mismatches: NONE
```

`python3.12 scripts/check-plan-code.py --binding` → rc=0, *"1518 anchor(s) across 1510 entries
each resolve to exactly one site; 67 expect(s) name no whole literal but ARE explained by one"*.
`check-fixture-variation.py` → rc=0, 906 parameters / 67 files / 117 ratcheted / 7 exempt.
`--diff-coverage origin/master` → rc=0 with one WARN (`_spy()` in `find-claim.py`, changed
earlier on the branch, not by this fold).

**Mutation execution, through the shipped machinery** (`stage_tree` into a fresh temp tree per
file, `control_is_green` before AND after, `run_mutations` with the real manifests), from the
worktree so `HARNESS_TREE` is complete:

```text
scripts/find-claim.py          : 24 mutations, control green, 0 survivors
scripts/check-withdrawal.py    : 23 mutations, control green, 0 survivors
scripts/check-provenance.py    : 21 mutations, control green, 0 survivors
scripts/codex-frontier-model.py: 11 mutations, control green, 0 survivors
scripts/check-plan-code.py     : 128 mutations, control green, 0 survivors
TOTAL 207 killed, 0 survivors — on this machine's case-INSENSITIVE filesystem
```

**The same 207 re-run with `TMPDIR` on a real case-sensitive APFS volume** — this is the
measurement that separates B1 from everything else:

```text
scripts/find-claim.py          : 24 mutations, control green, 1 SURVIVOR   <- B1
scripts/check-withdrawal.py    : 23 mutations, control green, 0 survivors
scripts/check-provenance.py    : 21 mutations, control green, 0 survivors
scripts/codex-frontier-model.py: 11 mutations, control green, 0 survivors
scripts/check-plan-code.py     : 128 mutations, control green, 0 survivors
TOTAL 206 killed, 1 survivor — on a case-SENSITIVE filesystem
```

So **exactly one** of the 207 is platform-divergent, and it is the one this fold wrote. Every
other case in the five changed guards is filesystem-independent, which is what makes B1 a
specific defect rather than a general worry about the harness.

**The HEAD token (r3 Codex M2) — attacked and held.** With the shipped `has_provenance`:

| token | accepted | `git rev-parse --verify` |
|---|---|---|
| `` `HEAD` `` | yes | valid |
| `` `HEAD~1` ``, `` `HEAD^0` `` | yes | valid |
| `` `HEAD123` `` | **no** (was yes at `e330ca80`) | invalid |
| `` `HEADS` `` | no | invalid |

`` `HEAD~999999999` `` is accepted and is syntactically a valid ref that happens not to resolve;
`` `HEAD~1^2` `` is refused, and no live row uses that spelling. The stated semantic limit
(*"a backticked ref names a SOURCE; it does not establish that a measurement happened … `we
cannot measure at `HEAD`` passes"*) is **accurately stated** — I confirmed that sentence passes
and that `` `--clear` cannot read HEAD and it cost **47 s** `` (row #255's own wording, no
backticks on HEAD) is still refused. The verb list is gone, so `\bat` no longer exists to fire
inside other words.

**The single-digit heuristic — every idiom the brief named is refused.** `single_digit_figures`:

```text
'rc 1 is wrong'      -> []      'step 2 of 6'        -> []
'Phase 1 is the gate'-> []      'ADR 2 says so'      -> []
'r3 M2 was filed'    -> []      'shard 8 was red'    -> []
'round 2 found it'   -> []      'it took 3 rounds'   -> ['3 rounds']   (a genuine count)
'Chapter 3 findings' -> ['3 findings']  (the identifier false positive r3 Codex already pinned)
```

**`figure_offsets_in_hit` + `all(...)` — the claimed direction is not merely plausible, it is
monotone.** `ats` is always a superset of the single offset the old `find` produced (the first
occurrence is `out[0]`, and the not-found fallback `[0]` matches the old fallback), so `all()`
over it can only turn *exempt* into *survivor*, never the reverse. Overlapping occurrences are
reported (`find(figure, i+1)`, so `"11"` in `"111"` → `[0, 1]`). A `figure` that is a substring
of a longer number adds an offset, which again errs toward reporting. `figure_offset_in_window =
min(start, span)` is correct at both ends: `window_around` clips only the head, so the hit's
offset inside the window is `start - max(0, start - span)`. Every caller of `is_history_context`
passes the keyword-only `figure_at` (`:614, :616, :641, :846, :859, :973`).

**`find-claim`'s inverted filter (r1 H1) — all four of the brief's attacks hold.** Measured over
a built world:

```text
walk of parent:  files ['big.min.js', 'ok.md']  skipped ['a.PNG']  pruned ['node_modules']
NAMED node_modules explicitly -> files ['claim.md']  pruned []  err ''
verdict(expect='present', skipped=3) rc=0  skip note present: True
verdict(expect='report',  skipped=3) rc=0  skip note present: True
verdict(expect='absent',  skipped=3) rc=1  skip note present: True
```

An uppercase `.PNG` is lowercased and skipped; a 4 MB `.min.js` is searched (`.js` is not in
`BINARY_SUFFIXES`); a pruned directory the caller NAMES is walked; the skip count rides on every
verdict arm. `collect_files`'s two empty returns both carry `unreadable_dirs`, and `main` reaches
rc=2 on either path (`err` first at `:913`, `unreadable` at `:926`).

**The live warn-only runs, against `origin/master`:**

```text
check-withdrawal: rc=0  "ok — 5 figure(s) corrected, and none of them survives elsewhere in docs/."
check-provenance: rc=0  WARN, 1 row (#262 — see L4)
```

**The withdrawal cross-import (r1 L3)** costs nothing structural: `_check_provenance` loads the
sibling by `spec_from_file_location` from the suite only, there is no import at module scope in
either direction, and the withdrawal suite runs in 1.1 s.

**The `*CASES*` branch does not over-reach in practice**: `CASE_CALL_RE.fullmatch` rejects
`lowercase`, `uppercase`, `showcase`, `testcase`, `basecase`, `case_name`, `cases`, `Case` and
`CASE`, and the three incidental `"CASE" in name` assigns yield no patterns (L5).

---

## CANNOT RUN

Scored as neither pass nor fail.

- **The full 1,510-mutation sweep was not run**, in either filesystem mode. Only the 207
  mutations of the five changed guards are credited above. B1's CI consequence is derived from
  the shard arithmetic (`muts[index-1::total]`, entry 1236 of 1510, N=8 → shard 4), not from
  running shard 4.
- **`_metadata_failure_probe` under a real root process** was not run; M2's measurement
  substitutes `os.access` for root, which exercises the branch but not an actual privileged
  filesystem.
- **CI itself was not exercised.** B1's claim about `ubuntu-latest` rests on that runner being
  case-sensitive and on the reproduction above against a real case-sensitive APFS volume, not on
  a CI run.

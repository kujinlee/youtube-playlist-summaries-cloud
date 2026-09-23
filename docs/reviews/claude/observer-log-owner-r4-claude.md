# Round 4 — Claude half — `observer-log-owner` (PR #342)

## Subject

Exactly the two commits that landed after round 3 converged, plus everything on the branch they
could have broken:

| What | Value |
|---|---|
| Branch HEAD reviewed | `7840a3be` — *The harness REFUSED my fix's own cases: they passed for an ambient reason* |
| Previous unreviewed commit | `c3ad7727` — *The verdict path had no allocator, and it destroyed committed evidence a third time* |
| Last reviewed commit (r3 CONVERGED) | `26fc8f82` |
| Base | `origin/master` = `b493edcc` |
| Working tree | clean at `7840a3be` throughout; **not modified** by this review (`git status --porcelain` empty at start and end). All mutation work was done on copies under the session scratchpad |

Trees I built and measured in, all outside the checkout:

- `w2` — a faithful `HARNESS_TREE` staging produced by the repo's own `stage_tree()`, **no `.git`**
- `w1g` — a copy of `w2` with `git init` + `git add scripts` (an ambient repo where the file is tracked)
- `wc3` — `w1g` with `scripts/codex-review.py` replaced by its `c3ad7727` content
- `at-<sha>` — `git archive <sha> scripts` for the citation measurement

## Counts

**0 Blocking · 1 High · 5 Medium · 1 Low**

---

## What I verified GREEN, by running it

### 1. Every declared self-test, at HEAD

```
$ python3 scripts/codex-review.py --self-test 2>&1 | tail -3
  [PASS] the repo_root argument is load-bearing: two roots, two different answers: got False want False

103/103 passed
rc=0

$ for s in check-plan-code check-selftest-counts check-ratchet-contract check-review-rounds check-docs; do
    python3 scripts/$s.py --self-test | tail -1; done
130/130 passed
18/18 self-test cases passed
self-test: 41/41 passed
29/29 self-test cases passed
22/22 passed
```

`c3ad7727` claim 6 (pin 12 → 16) and `7840a3be` claim 5 (declared 101 → 103) both hold **at HEAD**.
The pin:

```
$ for ref in 26fc8f82 c3ad7727; do git show $ref:scripts/check-plan-code.py | grep -n '"scripts/codex-review.py":'; done
1047:    "scripts/codex-review.py": 12,
1063:    "scripts/codex-review.py": 16,
```

### 2. The manifest sum and `EXPECTED_MUTATIONS`, loaded rather than read

```
$ python3 - <<'EOF'   # sum every scripts/mutations/*.json
...
codex-review.json entries: 16
SUM of all manifests = 981

$ python3 -c "...import check-plan-code...; print(len(em), sum(em.values()), em['scripts/codex-review.py'])"
entries: 53 sum: 981
codex-review pin: 16
```

Sum 981 ✓, and it equals the declared table ✓. `7840a3be`'s "Sum stays 981 — cases changed,
entries did not" holds.

### 3. The anchor claims, by the harness's own rule (`src.count(find)`)

```
anchors total          = 989
not-exactly-once       = 0
duplicate anchor tuples= 0
```

`989 anchors, 0 not-exactly-once, 0 duplicate tuples` ✓ — independently re-derived against the
DELIVERED scripts using `check-plan-code.py`'s own binding rule, not a paraphrase of it.

### 4. `7840a3be` claim 4 — verified three ways, reproduced

```
$ cd <w2>          && python3 scripts/codex-review.py --self-test | tail -2   # staged, no .git
103/103 passed
$ cd /             && python3 <w2>/scripts/codex-review.py --self-test | tail -2   # outside any repo
103/103 passed
$ cd <w1g>         && python3 scripts/codex-review.py --self-test | tail -2   # a real git repo
103/103 passed
```

Plus the checkout itself (§1). Four worlds, 103/103 in all four. **The ambient-reason defect that
`7840a3be` fixes is genuinely fixed** — the three fetch cases now drive a repository the block
builds, and the answers no longer depend on where the suite stands.

### 5. All 16 `codex-review` mutations, re-measured in TWO worlds

I did **not** run the full `--mutate .` sweep (see *What I could not finish*). I applied every entry
of `scripts/mutations/codex-review.json` to a staged copy and ran the suite, in both the world that
broke last time (no `.git`) and a world where the ambient root *is* a repo:

```
===== WORLD w2 (no .git) =====          ===== WORLD w1g (git repo, file tracked) =====
16 × KILL+ATTR                          16 × KILL+ATTR
```

Every mutation goes red **and the failing case is the one its `expect` names**, in both worlds —
including the four added by `c3ad7727` and the one `expect` that `7840a3be` repointed
(`…and None for a path OUTSIDE that root — git's third answer, never read as False`). `c3ad7727`
claim 4 and `7840a3be`'s "all four re-measured, each red via the case it names" ✓.

### 6. `c3ad7727` claim 5 — the restored verdict is byte-identical

```
$ for ref in 26fc8f82 origin/master 7840a3be; do git show $ref:docs/reviews/verdicts/codex-r3.verdict.json | shasum; done
2be47bf883ff711a6e6db0738cbd7b874c0968e7
2be47bf883ff711a6e6db0738cbd7b874c0968e7
2be47bf883ff711a6e6db0738cbd7b874c0968e7
$ shasum docs/reviews/verdicts/codex-r3.verdict.json
2be47bf883ff711a6e6db0738cbd7b874c0968e7
```

✓. Byte-identical to `origin/master`, i.e. to the pre-clobber content.

### 7. Every live gate, at HEAD

```
check-docs                 Documentation integrity OK                                        rc=0
check-review-rounds        331 parsed, 18 exemptions, 0 silent gaps; 182 verdicts read       rc=0
check-selftest-counts      46 script(s) declare a count, every one verified by running it    rc=0
check-ratchet-contract     guards discovered (40) … ratchet contract OK                      rc=0
check-dashboard-entry      ok — an entry block was added                                     rc=0
check-anchors              13 registered, all claimed … floor 22 held                        rc=0
```

### 8. Backlog #175's own hazard — no NEW line citations were added

```
$ git diff 26fc8f82..7840a3be -- scripts/ | grep -E '^\+' | grep -oE '[^ ]+\.(py|sh|ts|json|md):[0-9]+' | sort -u
(no output)
```

Neither commit adds a line citation. (What they *broke* is M4 below — a different thing.)

---

## Findings

### H1 — The allocator still does not allocate, and the shape the repo's own documentation steers every caller into is the one it does not cover. **STRUCTURAL**

**Premise.** `c3ad7727` is titled *"The verdict path had no allocator"*, and `verdict_collision`'s
docstring states the defect as *"the namespace has no allocator: any two reviews that pick the same
output name write the same verdict."* The fix refuses exactly one collision shape: a **derived**
path that is **already tracked**.

**Measurement.** `verdict_path` reduces `--out` to its *basename*, so two runs in two different
temp directories derive one name:

```
$ python3 - <<'EOF'  (importing the shipped module)
--out 'codex-r3.md'                           -> vpath rel='docs/reviews/verdicts/codex-r3.verdict.json'
--out '/tmp/xyz/r.md'                         -> vpath rel='docs/reviews/verdicts/r.verdict.json'
--out '/Users/kujinlee/elsewhere/deep/nest/r.md' -> vpath rel='docs/reviews/verdicts/r.verdict.json'
```

`docs/plugins.md:158` is the repo's documented, preferred call shape:

```
python3 scripts/codex-review.py --prompt-file <path> --out "$(mktemp -d)/r.md"  # then promote
```

Every invocation of that shape derives `docs/reviews/verdicts/r.verdict.json`. That file is not
tracked, so the new guard passes it — and run B destroys run A's testimony exactly as before. Driven
against the shipped functions, with `REPO_ROOT` pointed at a throwaway git repo:

```
Documented call shape from docs/plugins.md:158 — --out "$(mktemp -d)/r.md"
  RUN A (Codex half, round 4): wrote docs/reviews/verdicts/r.verdict.json  (tracked=False)
  RUN B (Codex half, a different subject): wrote docs/reviews/verdicts/r.verdict.json  (tracked=False)

  verdict after run A: review A (Codex half, round 4) completed
  verdict after run B: review B (Codex half, a different subject) completed
  A's testimony still on disk? False
```

Two further measured facts sharpen it:

1. The *review artifact* is protected by **existence** — `codex-review.py:826` refuses when `--out`
   already exists, regardless of tracked-ness. Its *testimony* is protected only by **tracked-ness**.
   A fresh `mktemp -d` per run means the `--out` guard can never fire, and the verdict guard never
   fires either. The two artifacts of one run have two different, non-composable policies.
2. `git ls-files docs/reviews/verdicts/ | grep -cE '^(r[0-9]*|codex[0-9]*|plan-r[0-9]+|codex-r[0-9]+)…'`
   → **15** already-tracked verdicts with generic stems (`r1-codex`, `r3-codex`, `codex`,
   `codex2`, `plan-r1-codex`, …). The moment anyone commits an `r.verdict.json`, the *documented*
   call shape starts returning rc=2 for every review in the repo.

**Neither commit touches any documentation.** `git diff --stat 26fc8f82..7840a3be` lists
`docs/backlog.md`, two review artifacts, and three script/manifest files — `docs/plugins.md` is not
among them, and `grep -rn "verdict_collision\|already TRACKED" docs/ .claude/` returns nothing. A
caller following the documented shape is given no warning and no protection.

**Why High, not Blocking.** It does not regress anything: the committed-evidence destruction that
cost this branch a restore *is* now refused, and that was the stated scope. It is High because the
commit presents the allocator gap as closed and the gap remains open on the repo's own default path,
which is where the next instance will come from — the fourth, not the third.

**Proposed fix (pick one, not both):**
- *Allocate.* Derive the verdict name from something unique to the run — the dispatch HEAD plus a
  short digest of the prompt file, or a `-NN` suffix chosen by scanning the directory — so the
  namespace has one occupant per run and the refusal becomes a fallback rather than the mechanism.
- *Or make existence the rule, as `--out` already does*: refuse any existing derived verdict,
  tracked or not, with `--verdict` as the escape. That is one policy for both artifacts of a run
  and it covers the `mktemp` shape. Then fix `docs/plugins.md:158` in the same commit, because
  `r.md` stops working the first time two reviews run in one session.

---

### M1 — The stated reachability of git's rc=128 is false at the call site, and it is written in two places in the code. **STRUCTURAL**

**Premise.** `codex-review.py:1318` and `check-plan-code.py:1060` both justify the third
`path_is_tracked` outcome this way:

```
scripts/codex-review.py:1318
        # `--out` is documented to live OUTSIDE the repo, and `git ls-files --error-unmatch` exits
        # 128 with "is outside repository" for any such path.

scripts/check-plan-code.py:1060
    #     them; `--out` is documented to live OUTSIDE the repo, where rc=128 is what you get.
```

and `c3ad7727`'s message repeats it as the proof the input is *"REACHABLE … not contrived"*.

**Measurement.** `path_is_tracked` is never called on `--out`. `main()` calls it on `vpath`
(`codex-review.py:800`), and `verdict_path` — whose own docstring says *"Defaults into the repo —
not next to `--out`, which the documented safe call shape puts OUTSIDE the repo"* — takes
`os.path.basename(out_path)` and joins it under `REPO_ROOT`. So for every possible `--out`:

```
--out 'codex-r3.md'                    -> rel='docs/reviews/verdicts/codex-r3.verdict.json'   starts_with_..=False
--out '/tmp/xyz/r.md'                  -> rel='docs/reviews/verdicts/r.verdict.json'          starts_with_..=False
--out '/etc/passwd.md'                 -> rel='docs/reviews/verdicts/passwd.verdict.json'     starts_with_..=False
--out '../../../outside.md'            -> rel='docs/reviews/verdicts/outside.verdict.json'    starts_with_..=False
```

A derived `vpath` is never outside `REPO_ROOT`, so `relpath` never produces `../…` and git never
answers *"is outside repository"*. The only other route is `--verdict <path outside the repo>` — and
on that path `override_given=True`, so `verdict_collision` returns `None` before the fetched value
is read. **The reason given for the branch being reachable cannot produce it.**

The branch *is* reachable, by a different cause: `REPO_ROOT` not being a git repository at all. That
is precisely what `7840a3be` went on to measure — *"`--mutate .` stages a copytree with NO `.git`,
so git exits 128 there"*. So the correct justification was in hand one commit later and was not
back-fitted; the false one was copied forward verbatim into the rewritten comment block.

**Why Medium.** No behaviour is wrong — the case, the mutation and the kill are all real (verified
in §5 above, both worlds). What is wrong is the *recorded reason*, in two code sites that a future
reader will use to decide whether the branch still matters. This is the branch's own signature class:
`check-plan-code.py:1293-1296` says it in the file's own words — *"a comment asserting a property the
code lacks is this branch's signature defect."*

**Proposed fix.** Replace both sentences with the cause that actually reaches it: *"`REPO_ROOT` need
not be a git repository — the mutation harness stages a `copytree` with no `.git`, and a source
export has none either; `git ls-files` exits 128 there, and reading that as 'not tracked' is the
shrug this rule refuses."* One sentence, two sites, no code change.

---

### M2 — The case that is supposed to make a git-less environment fail loudly cannot run in a git-less environment. **STRUCTURAL**

**Premise.** `7840a3be` claim 3: *"Plus a case asserting the repository was really built, so an
environment without git fails loudly instead of reporting three passes."* The code says the same:

```
scripts/codex-review.py:1306-1308
        # ⛔ CANNOT RUN IS A FAILURE. If git is unavailable this must not quietly report three passes.
        chk("the throwaway repository was really built — otherwise the three cases below are void",
            _git_ok, True)
```

**Measurement.** `_git_ok` is computed from `subprocess.run(...).returncode`, and `subprocess.run`
does not return a code when the executable is missing — it raises.

```
$ cd <w2> && PATH=<empty-dir> /usr/local/bin/python3 scripts/codex-review.py --self-test
  File ".../scripts/codex-review.py", line 1299, in self_test
    if subprocess.run(["git", "-C", _repo] + cmd, capture_output=True).returncode != 0:
  ...
FileNotFoundError: [Errno 2] No such file or directory: 'git'
rc=1
```

(My first attempt at this used `PATH=<empty>:/usr/bin:/bin` and got `103/103 passed` — macOS ships
`/usr/bin/git`. That run measured nothing and is recorded here because it is the same
ambient-reason trap the commit is about.)

So in the named scenario the guard case is never reached; the loudness comes from an unhandled
exception in the harness. Conversely `_git_ok = False` requires git to be **present** and `init` or
`config` or `add` to fail — which no case, and no mutation in `codex-review.json`, drives. The case
is a passing assertion with no falsifier: deleting it leaves the suite green at 102, and nothing in
the manifest targets it.

**Why Medium.** The *property* the comment claims ("must not quietly report three passes") does
hold — a traceback is not quiet. The *mechanism* named in the commit message and in the comment is
not the one operating, and the case written to carry it is unfalsifiable. This is the
"fixing a PREMISE is not covering the BRANCH" shape the brief lists.

**Proposed fix.** Make the named mechanism real, and the case falsifiable, in one line — wrap the
three setup calls in `try: … except OSError: _git_ok = False`, so a missing git reaches
`chk("the throwaway repository was really built…")` and reports as a case rather than a stack trace.
Then a manifest entry that deletes the `chk` has something to go red on.

---

### M3 — `c3ad7727` shipped with `check-selftest-counts` LIVE red, and its message reported that gate in the one mode that cannot see it. **TRANSITIONAL**

**Premise.** `c3ad7727`'s message states *"declared self-test 91 -> 102"* and lists
*"Gates: codex-review 102/102, plan-code 130/130, selftest-counts 18/18, ratchet-contract 41/41 and
rc=0, review-rounds 29/29 and rc=0, docs rc=0."* Note the asymmetry: three gates are reported with a
live `rc=0`; `selftest-counts` is reported with its **self-test** count only.

**Measurement.** The file at that commit declares **101**, not the 102 the message states, and the
suite ran 102:

```
$ git show c3ad7727:scripts/codex-review.py | grep -n "self-test  #"
45:  scripts/codex-review.py --self-test  # 101 cases

$ cd <wc3> && python3 scripts/codex-review.py --self-test | tail -2
102/102 passed
```

And the gate whose job is exactly this disagreement fails at that commit:

```
$ cd <wc3> && python3 scripts/check-selftest-counts.py
declared self-test counts disagree with what the suites printed:

  ✗ codex-review.py: [DRIFT] the docstring declares 101 cases; the suite ran 102
rc=1
```

**Why Medium, and why transitional.** It is healed at HEAD (`103` declared, `103` run, live gate
green — §7), so nothing ships broken. It is Medium because the *reporting habit* is the defect, not
the drift: `18/18` is the counter proving its own rules work, which says nothing about the repo it
was pointed at. This repo has a name for that — *"a green check over the wrong subject is an
assertion in better packaging."* The drift the gate exists to catch was live in the same commit that
cited the gate.

**Proposed fix.** No code change. When a commit message lists gates, list the LIVE `rc` for every
gate that has a live mode, and never a `--self-test` tally in its place. `check-selftest-counts`,
`check-docs`, `check-review-rounds`, `check-ratchet-contract`, `check-anchors` and
`check-dashboard-entry` all have one.

---

### M4 — Backlog #175's headline measurement does not reproduce, and one of the breakages it counts was created by the commit that filed it. **STRUCTURAL**

**Premise.** `c3ad7727` filed backlog #175 and stated: *"MEASURED over scripts/\*.py: 88 citations,
76 resolve to a non-blank line, 10 land on a BLANK line, 2 point PAST EOF … three such exist in
check-plan-code.py which were already wrong on origin/master — **so they are not this branch's
regression**, which is why they are filed rather than fixed here."* The row repeats it as
*"57 in-file and 31 cross-file"* across *"6 files"*.

**Measurement, part A — the totals do not reproduce.** Extracting the row's own stated grammar
(`` `:NNN` `` in-file, `` `file.py:NNN` `` cross-file) over `scripts/*.py` at HEAD:

```
in-file `:NNN` = 56   cross-file `file.py:NNN` = 39   total = 95
backlog #175 claims: 57 in-file, 31 cross-file, 88 total
```

The broken *split* matches exactly (10 blank + 2 past-EOF at `c3ad7727`), but the denominator differs
by 7 and the cross-file class by 8. No extractor was committed, so neither number can be reconciled —
the row states a measurement that cannot be re-derived, which is the provenance failure the row is
itself about.

**Measurement, part B — the commit moved one citation into the bucket it then counted.** Running the
same extraction over `git archive` of three commits:

```
=== 26fc8f82 ===   total=95  non-blank=84  BLANK=9   past-EOF=2   broken=11
=== c3ad7727 ===   total=95  non-blank=83  BLANK=10  past-EOF=2   broken=12
=== 7840a3be ===   total=95  non-blank=83  BLANK=10  past-EOF=2   broken=12
```

The single new entry at `c3ad7727` is `check-plan-file-tags.py` → `` `check-plan-code.py:1668` ``.
Resolving that line at each commit:

```
origin/master  :1668 =     unattributable — §22's disease inside the machinery built to prevent it. Zero of the live
26fc8f82       :1668 =     ⛔ IT STATES THE AFFIRMATIVE NUMBERS, not only the negative one. It used to report
c3ad7727       :1668 = <<BLANK LINE>>
7840a3be       :1668 = <<BLANK LINE>>

$ git show c3ad7727 -- scripts/check-plan-code.py | grep -E "^@@"
@@ -1044,7 +1044,23 @@ EXPECTED_MUTATIONS = {      ← 16 lines inserted above 1668
```

The citing comment is `scripts/check-plan-file-tags.py:533`. The honest reading, stated in full: the
citation was already pointing at the *wrong content* on `origin/master`, so the message's
"already wrong" is true of its correctness — but it was **not** in the blank-line bucket until
`c3ad7727`'s own 16-line insertion put it there, and the 10 it reports was measured after that
insertion. The commit's blanket "not this branch's regression" is therefore false for this member.

**Why Medium.** Zero runtime impact — it is a comment. It is Medium because the branch's subject is
claims-versus-code, and this is a measured number inside a filed backlog row that a future guard will
be ratcheted against; a wrong denominator and a mis-attributed member both survive into that guard's
baseline. It is also a clean instance of *"a document inside the corpus it measures."*

**Proposed fix.** Commit the extractor the row's own Work item already calls for, restate the
numbers from its output, and amend the row to say that one of the 10 was created by the filing
commit. Fix `check-plan-file-tags.py:533` by citing the symbol rather than a line, per the
repo's own recorded rule.

---

### M5 — The collision refusal is the only exit with no durable record, on the channel this file says is unreliable. **STRUCTURAL**

**Premise.** `codex-review.py:797-804`:

```
    # ⛔ BEFORE ANY TESTIMONY IS WRITTEN, and before `emit` exists — because `emit` WRITES to `vpath`,
    # so a refusal discovered inside it would have to destroy the thing it is protecting in order to
    # report that it was protecting it. This is the one exit below that deliberately leaves no verdict.
    _collision = verdict_collision(vpath, tracked=path_is_tracked(vpath),
                                   override_given=bool(args.verdict))
    if _collision:
        print(f"[codex-review] {_collision}", file=sys.stderr)
        return 2
```

**Measurement / argument.** The same file's header states why the verdict mechanism exists at all:

> *"'Write a file the caller must read' only moves the problem if the CALLER is still the reader — a
> file ignored is an exit code ignored with extra steps. So the verdict lands INSIDE the repository,
> where `check-review-rounds.py` reads it in CI. **The consumer is deliberately NOT the caller.**"*

For this one exit the consumer *is* the caller again — an agent that this repo has recorded ignoring
a wrapper exit code four times (`docs/process-rationale.md:399`, `WRAPPER_RC=1` sat unread while the
round's Codex half never ran). A refused dispatch therefore leaves nothing on disk, and downstream a
refused run and a run that never happened are indistinguishable — which is the exact property the
verdict file was built to abolish.

The comment frames this as a forced binary (write to `vpath` and destroy, or write nothing). It is
not: the refusal could write its own testimony to a path that collides with nothing, e.g.
`<stem>.refused.<head>.verdict.json`, and `read_verdicts` in `check-review-rounds.py` would pick it
up with no grammar change (it globs `*.json` and requires only a `gate_ran` field).

**Why Medium.** Nothing destructive happens and the message on stderr is clear and actionable. It is
Medium because it re-opens, for one path, the failure mode the whole verdict mechanism exists to
close, and because the comment records a tradeoff that was not actually forced.

**Proposed fix.** On the refusal path, write a `gate_ran: false` verdict to a NON-colliding name
derived from the refusal (never `vpath`), and say in the comment why that name cannot be the one
being protected.

---

### L1 — `--allow-overwrite` does not compose with the new refusal, and the refusal never mentions it. **TRANSITIONAL**

**Premise / measurement.** `codex-review.py:748` defines `--allow-overwrite` as the deliberate
authorisation to replace an existing review artifact, consumed at `:826`. `verdict_collision` takes
`override_given=bool(args.verdict)` only, so a caller who passes `--allow-overwrite` — the flag whose
whole meaning is *"yes, replace it, I meant to"* — is still refused, and the refusal text names only
`--out` and `--verdict`:

```
  Fix: give --out a name unique to this review — the convention is
  <subject>-r<N>-codex.md, which yields <subject>-r<N>-codex.verdict.json — or
  pass --verdict <path> to replace that testimony deliberately.
```

`--verdict`'s own `--help` string (`:750`) says nothing about being a refusal escape:
`"write the run's verdict here (default: docs/reviews/verdicts/<review-stem>.verdict.json)"`.

**Why Low.** Recoverable in one re-run once the reader reads the message, which does name a working
escape. It is a vocabulary collision of the kind `check-vocabulary-collisions.py` exists for — two
flags authorising replacement of two artifacts of one run, neither implying the other.

**Proposed fix.** Either make `--allow-overwrite` satisfy `override_given` too (one mechanism, one
concern), or add one clause to the refusal saying that `--allow-overwrite` governs `--out` only and
the verdict needs `--verdict`. Mention the escape role in `--verdict`'s help string.

---

## What I could not finish / could not measure

- **The full `python3 scripts/check-plan-code.py --mutate .` sweep — NOT RUN by me.** The brief
  forbade it (~14 min) and states the coordinator got 53 files / 981 mutations / 981 killed / 981
  attributed / 0 survivors / rc=0 at `7840a3be`. **Treat that verdict as NOT INDEPENDENTLY
  VERIFIED by this half.** What I ran instead, and what it does and does not cover: I re-derived the
  981 sum from the manifests, re-derived all 989 anchors against the delivered scripts with the
  harness's own rule, and ran all 16 `codex-review` mutations end to end in two worlds (§3, §5). That
  covers the file the two commits changed and the arithmetic the sweep reports; it does **not** cover
  the other 52 files' kills, nor the sweep's own control-run logic. If I doubted the verdict I would
  run `--mutate .` at `7840a3be` with a clean `$HOME` redirect and compare the per-file table.
- **`c3ad7727`'s "three such exist in `check-plan-code.py` which were already wrong on
  origin/master"** — the non-blank-but-wrong subset. I did not enumerate it; by construction no
  mechanical test sees it and checking three citations by hand against `origin/master` was out of
  budget here. **Treat as NOT RUN.** It does not affect M4, which is about a different member.
- **Neither `codex exec` nor a real `codex-review.py` dispatch was run.** Every statement about
  `main()`'s behaviour in H1, M1 and M5 comes from importing the module and driving the shipped
  functions directly, or from reading the call site — not from a live review dispatch. The
  end-to-end pair `c3ad7727` reports (`--out codex-r3.md` → rc=2; `--out zzz-unique-r9-codex.md` →
  proceeds) is **NOT re-verified here**.
- **The full branch diff `origin/master...HEAD` beyond the two subject commits** was read only at
  `--stat` granularity plus the r3 review context. Round 3's findings were taken as folded on the
  strength of its CONVERGED verdict; I checked only that the two later commits did not regress the
  gates, which they did not (§7).

---

## Verdict

**NOT CONVERGED.**

`7840a3be` does what it claims about the ambient-reason defect — I reproduced 103/103 in four worlds
and 16/16 attributed kills in two, and that is the strongest part of this branch. But the fold
carried five claims that measurement falsifies (M1–M5), and H1 shows the headline defect —
*the namespace has no allocator* — is still open on the path `docs/plugins.md` tells every caller to
use. Round 4 repeated the branch's pattern: a defect inside the fix for the previous round's defect.

M1, M2, M3 and L1 are one-line or comment-only repairs. M4 needs an amended backlog row and one
symbol-instead-of-line citation. H1 and M5 are the two that need a decision rather than an edit.

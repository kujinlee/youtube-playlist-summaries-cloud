# Adversarial review r1 — `pin-python-interpreter` / PR #317 (Claude)

## PROOF OF SUBJECT

```
$ git log --oneline -3
a741549e Pin the interpreter every guard runs on — it was never declared (follow-up to #137)
72396668 Close backlog #137 — and this docs-only PR is its own falsifier (#316)
8832baea Fifteen schema gates reported red into a void, and the filter protecting them was buying nothing (backlog #137) (#315)

$ git rev-parse HEAD
a741549ee16d294baccc4eb17ea75ad69ec13157

$ git status --porcelain
(clean — no output)

$ git diff --stat 72396668..a741549e
 .github/workflows/ci.yml                |  31 ++++
 .github/workflows/schema-gates.yml      |  10 ++
 docs/dashboard-entries.md               |  37 ++++
 docs/dev-process.md                     |   4 +-
 scripts/check-fixture-variation.py      |   9 +
 scripts/check-plan-code.py              |  10 +-
 scripts/check-python-pin.py             | 308 ++++++++++++++++++++++++++++++++
 scripts/check-selftest-counts.py        |   1 +
 scripts/mutations/check-python-pin.json | 123 +++++++++++++
 9 files changed, 530 insertions(+), 3 deletions(-)

$ shasum -a 256 scripts/check-python-pin.py
61737b890cd37ea1f4bd30a0e09b38bf45c44a56c58ea14d24b94eddd0f6cd4a
```

**I read `a741549e`.** Line numbers are at that commit. All probing ran from `/tmp/pinrev/` against
copies; no tracked file was modified (`git status` clean above and after).

Reviewer's interpreter: **Python 3.14.4** — i.e. this review was written by the machine class the
branch exists because of, which is why every claim below says whether it was executed here, in CI, or
reasoned.

---

## ⭐ ATTACK 1 — "3.12 is what CI already ran": **VERIFIED, with one nuance the branch does not state**

The coordinator flagged this as inferred, not verified. It is now verified, from the runner image
manifest for the exact image the last pre-branch `master` run used.

```
$ gh run view 35197274199 --log | grep -iE "Image:|Image Release"
Image: ubuntu-24.04
Image Release: .../runner-images/releases/tag/ubuntu24%2F20260907.300

$ gh api "repos/actions/runner-images/contents/images/ubuntu/Ubuntu2404-Readme.md?ref=ubuntu24%2F20260907.300" \
    --jq .content | base64 -d | grep -nE "^- Python 3"
28:- Python 3.12.3          # <- the system python3 on PATH, i.e. what `python3` resolved to

  (Cached Tools → Python, same file, lines 200-205)
  3.10.21  3.11.16  3.12.14  3.13.15  3.14.7
```

So the pre-branch `python3` was **3.12.3**, and `3.12` is available in the tool cache. The claim
holds at the granularity the pin uses.

**Nuance, VERIFIED, currently unstated anywhere in the branch:** the pin does not keep the same
interpreter, it *swaps* it — from `/usr/bin/python3` 3.12.3 to the tool-cache build. From this
branch's own CI run:

```
$ gh run view 35213825227 --log | grep -nE "Successfully set up CPython|pythonLocation"
182: Successfully set up CPython (3.12.14)
725: pythonLocation: /opt/hostedtoolcache/Python/3.12.14/x64
732: python pin OK — every job pins 3.12, and this interpreter is 3.12
```

3.12.3 → 3.12.14 is a different build with a different `sys.prefix` and a different `site-packages`.
I checked the one way that could bite:

```
$ grep -hoE "^(import|from) [a-zA-Z_][a-zA-Z0-9_.]*" scripts/*.py | awk '{print $2}' | cut -d. -f1 | sort -u
__future__ argparse ast collections contextlib coverage_verdict dataclasses datetime hashlib html
http importlib inspect io json m4_base_db m4_catalog os page_chrome page_markup pathlib re shlex
shutil signal socket subject_status subprocess sys tempfile threading time tokenize typing urllib
   (plus docstring false hits: "a", "one", "real", "the", "this")

$ grep -rnE "/usr/bin/python3|/usr/local/bin/python" scripts/ .github/ | grep -v "env python3"
(no output)

$ head -1 scripts/*.py | grep "^#!" | sort | uniq -c
  57 #!/usr/bin/env python3
```

Stdlib + local modules only; no `pip install` step exists in either workflow; every shebang resolves
through `PATH`. So the site-packages swap is harmless and the `env python3` shebangs follow the pin.

Empirical confirmation that the swap changed nothing: the branch's own CI run is green everywhere
except the expected missing-review gate —

```
$ gh run view 35213825227 --log | grep -nE "##\[error\]|748 mutation|28/28"
773:  28/28 passed                                   (check-python-pin self-test)
7920: OK — delivered scripts mutated: 48 file(s), 748 mutation(s), 748 killed, 748 attributed …, 0 survivor(s)
8054: ##[error]Process completed with exit code 1.   (check-review-recorded — "no review round was recorded")

$ gh run view 35213825248 --log | grep -nE "Successfully set up CPython|15/15"
163:  Successfully set up CPython (3.12.14)          (job: schema-gates)
1266: ═══ 15/15 backlog 26's money trigger … ═══     (all fifteen gates green)
```

The only red is the gate this document closes.

**The two supporting numbers are exact, not approximate:**

```
$ git show 72396668:.github/workflows/ci.yml | grep -o 'python3 ' | wc -l
45
$ git grep -n "python-version" 72396668 -- .github
72396668:.github/workflows/schema-gates.yml:258:          python-version: '3.12'
```

45 bare `python3`, exactly one `python-version:` in the whole repository, in `prod-drift`. And the
root-cause behaviour, verified locally in both directions:

```
$ python3.12 -c "import pathlib; pathlib.Path('x'*5000).is_file()"   →  OSError errno 63 (ENAMETOOLONG)
$ python3.10 -c "…same…"                                            →  OSError errno 63
$ python3.14 -c "…same…"                                            →  False
```

**Attack 1 produced no finding. The claim is accurate.** Everything the branch says about *why* it
exists checks out.

---

## FINDINGS

### H1 — VERIFIED — the "the pin TOOK EFFECT" assertion cannot fail while the pin equals the image's system Python

**SEVERITY: High** (not Blocking — it does not red anything; it is a green that claims more than it
measures, which is the class this repository files findings about).

`scripts/check-python-pin.py:170`

```python
    if in_ci and running != pin:
        return 1, (f"FAILED — the pin did not take effect: …")
```

`running` is `running_version(sys.version_info[:2])` — major.minor of whatever `python3` resolved to.
`pin` is `3.12`. Attack 1 established that on `ubuntu-24.04` **the system `python3` is already
3.12.3**. So `running == pin` holds whether or not `setup-python` did anything: the comparison is
satisfied by the exact pre-branch world this guard exists to end.

**Concrete failure scenario.** `actions/setup-python@v5` takes `update-environment` (visible in this
branch's own run log, line 176: `update-environment: true`). Set it to `false` — a one-word edit, and
a plausible one if someone later wants the pin for a specific step only — and the action still
installs 3.12.14, still logs "Successfully set up CPython", and leaves `PATH` untouched. `python3`
stays the system 3.12.3, `running_version` returns `"3.12"`, and the guard prints

```
python pin OK — every job pins 3.12, and this interpreter is 3.12
```

while all 45 guards run on the unpinned interpreter. The step is present, ineffective, and green —
verbatim the shape the docstring at `:45-47` says it exists to catch.

Label: the two halves (system python is 3.12.3; the comparison is major.minor only) are **VERIFIED by
execution**; the composed scenario is **REASONED** — I did not push a workflow edit to prove it.

**The fix, and the observation that proves it fixed.** `setup-python` exports `pythonLocation`, and
the branch's own log proves it (line 725: `pythonLocation: /opt/hostedtoolcache/Python/3.12.14/x64`).
Assert provenance, not just the number:

```python
loc = os.environ.get("pythonLocation")            # exported ONLY by setup-python
# in CI: FAIL if loc is unset, or if sys.executable is not under loc
```

Falsifier: set `update-environment: false` (or delete the `uses:` line and leave the pin declared
elsewhere) → the step goes red. Today it stays green — that is the observation proving the gap.

**Three documents state the stronger claim and would need the same edit:**
`scripts/check-python-pin.py:45-47`, `.github/workflows/ci.yml:103-105` ("If the pin did not take
effect, their results are not evidence about anything"), and `docs/dashboard-entries.md` ("On the
build server it asserts the pin actually took effect"). Either strengthen the check or weaken the
three sentences — but the current pairing is a claim the code does not make.

---

### H2 — VERIFIED — the predicate fails **OPEN** for four legitimate YAML job shapes

**SEVERITY: High.** The docstring at `:37-39` says:

> A new job fails until someone states which case it is, **which is the direction that cannot fail
> silently.**

That property is measurably false. `job_names` (`:83-101`) requires the job key to be **exactly two
spaces indented with nothing after the colon**, and `jobs:` to be alone on its line
(`^jobs:\s*$`, `:92`). Anything else makes the job invisible, and an invisible job is a *passing* job.

Executed — real `.github/workflows/*.yml` corpus plus one added `deploy.yml` holding a genuinely
unpinned job, written five ways that are all valid YAML and all mean the same thing:

```
$ python3 /tmp/pinrev/failopen.py
rc  shape                           unpinned jobs detected
0   job key w/ trailing comment     []                       ← SILENT PASS
1   job key w/ trailing space       ['deploy.yml:deploy']
0   4-space indented jobs           []                       ← SILENT PASS
0   `jobs:` with trailing comment   []                       ← SILENT PASS
0   anchored job key (`deploy: &d`) []                       ← SILENT PASS
1   plain unpinned job (control)    ['deploy.yml:deploy']    ← the control works
```

**Concrete failure scenario.** Someone adds `release.yml` in this repository's house style —

```yaml
jobs:
  deploy:  # ships the worker
    steps:
      - run: python3 scripts/deploy.py
```

— and the guard reports `python pin OK`. The job runs an undeclared interpreter forever, and the
guard whose entire subject is "a job that pins nothing" says nothing. The trailing-comment shape is
the likely one: every other key in both workflow files in this repo carries commentary.

Note the asymmetry that makes this worse than a plain gap: the **only** shape the guard sees is the
one both current files happen to use. It is a guard calibrated on its own corpus — the
`a-measurement-is-only-as-good-as-its-corpus` shape.

**Fix, with the executed evidence for it.** I mutated the job-key regex to accept a trailing
value/comment and re-ran the suite:

```
$ python3 /tmp/pinrev/unguarded.py
SURVIVES :: job_names: allow a trailing value/comment on the job key
             (`^  ([A-Za-z_][\w-]*):.*$`  → 28/28 still passed)
killed   :: job_names: any indent counts as a job key
             (killed by 3 cases, incl. "…while a STEP key is not mistaken for a job")
```

So loosening the *tail* is free (no case depends on the strictness) and fixes three of the four
shapes, while the two-space *indent* is genuinely load-bearing and must stay. Remaining: 4-space job
indent. The durable repair for that one is not a regex — it is a **refusal**: if a workflow file
yields zero job names, exit 2 (CANNOT RUN), because a workflow with no jobs is not a thing that
exists. That converts every future unparseable shape from a silent pass into a loud "NOT CHECKED",
which is what `:8` already promises.

Falsifier for the fix: the six-row table above must read `1` on every row except the control's
sibling, and the `4-space indented jobs` row must become `2`.

---

### H3 — VERIFIED — the one line deciding whether the guard asserts in CI is untested *and* unmutated

**SEVERITY: High** (cheap to fix; it is the guard's own fail-open surface).

`scripts/check-python-pin.py:302`

```python
    rc, msg = verdict(_read_workflows(), running_version(sys.version_info[:2]),
                      bool(os.environ.get("GITHUB_ACTIONS")))
```

`self_test()` only ever calls `verdict` directly with an explicit `in_ci`. Nothing exercises `main`.
Executed:

```
$ python3 /tmp/pinrev/unguarded.py
SURVIVES :: main: in_ci hard-wired False (CI assertion never armed)
SURVIVES :: main: returns 0 always (guard can never fail the step)
SURVIVES :: main: pin argument swapped to a literal "3.12"
SURVIVES :: job_blocks: ignore the names filter
SURVIVES :: declared_pins: drop the ^ anchor (matches inside a comment)
SURVIVES :: _read_workflows: only read *.yml (drop the .yaml glob)
```

The first two are the ones that matter. `bool(os.environ.get("GITHUB_ACTIONS")) → False` silently
demotes the CI assertion to an advisory **on the runner**, and the suite stays 28/28 green. The
mutation manifest's `"the CI assertion goes"` entry guards `verdict`'s clause, not the wiring that
arms it — so the branch has a mutation for the lock and none for the door.

**There is precedent for closing this, in this repository:** `scripts/mutations/explainer-serve.json`
mutates `os.environ.get(SRC_ROOT_ENV, "")` directly, so environment reads are not treated as an
untestable boundary here.

Fix: extract `def in_ci(env: "dict[str,str]") -> bool` (PURE, takes the mapping), give it two cases
(set / unset), add a mutation entry for it and one for `main`'s `return rc`. Observation proving it
fixed: hard-wiring `in_ci` to `False` must produce a `[FAIL]` line naming that case.

Related and smaller, from the same run: `declared_pins` dropping its `^` anchor survives — meaning
no case distinguishes "anchored to line start" from "matches anywhere", so the protection against
Attack 4 (a `python-version:` inside a comment) is real in the code but **untested**. It is correct
today: a `#` is not `\s`, so comments genuinely cannot match. One case would pin it.

---

### M1 — VERIFIED — an inline comment on the pin line reds the REQUIRED check with a nonsense message

**SEVERITY: Medium.** `scripts/check-python-pin.py:79-80`

```python
    return [m.group(1).strip().strip("'\"")
            for m in re.finditer(r"^\s*python-version:\s*(.+?)\s*$", text, re.M)]
```

`(.+?)\s*$` takes everything to end of line, then strips quotes from the *outside*. A YAML inline
comment therefore becomes part of the version string. Executed against the real `ci.yml` with only
the pin line rewritten:

```
$ python3 /tmp/pinrev/fp.py
declared=["3.12'  # the version CI already ran"]
  rc=1  FAILED — workflows pin DIFFERENT Python versions: 3.12, 3.12'  # the version CI already ran.
declared=['3.12  # pinned']
  rc=1  FAILED — workflows pin DIFFERENT Python versions: 3.12, 3.12  # pinned.
declared=['3.12.14']
  rc=1  FAILED — workflows pin DIFFERENT Python versions: 3.12, 3.12.14.
declared=['3.12']   rc=0   (double-quoted)
declared=['3.12']   rc=0   (trailing whitespace)
```

**Failure scenario.** The house style of both workflow files is heavy commentary. Someone writes
`python-version: '3.12'  # what the runner already shipped`, pushes, and the required `verify` check
goes red **for that PR and every PR rebased on it**, with a message that says the workflows disagree
about the version when they do not. Time-to-diagnose is the cost here, and the message actively
misleads.

The patch-level row is the same defect wearing a different hat: pinning `'3.12.14'` — the natural
reaction to a patch-level behaviour difference — reds the check, and if it ever got past the
disagreement clause it would then hit `:170` and report "the pin did not take effect" about a pin
that took effect perfectly (`3.12` != `3.12.14`).

Fix: strip a trailing ` #…` before stripping quotes, and compare a declared pin to `running` on its
first two components so a patch-level pin is legal. Falsifier: the five rows above must read
`0 0 0 0 0`, and a genuinely disagreeing pair must still read `1`.

---

### M2 — VERIFIED — any newly added workflow reds the required check for the whole repository

**SEVERITY: Medium** (this is the designed direction, but the blast radius is undocumented).

The guard reads *every* file in `.github/workflows/`, and runs inside the one required check.
Executed (the control row of the H2 table): a plain unpinned job in a new `deploy.yml` → `rc=1`, so
`verify` fails.

**Failure scenario.** GitHub's CodeQL default setup, a Dependabot-authored workflow, or anything
added through the Actions UI lands a workflow nobody on the team wrote. Every open PR's required
check goes red at once, and the only fixes are a commit editing that workflow or a commit editing
`EXEMPT_JOBS`. Since backlog #137 made `schema-gates` required this is a repository-wide stop.

I am **not** filing this as "make it warn-only" — failing toward a decision is this repository's
stated preference and the failure message already says exactly what to do. The finding is that the
consequence is written down nowhere. One sentence in the docstring ("⚠ this fails the required check
for every open PR the moment a workflow arrives that nobody pinned — that is intended; the fix is two
lines of YAML or one line in `EXEMPT_JOBS`") converts a 2 a.m. surprise into a recognised one.

---

### M3 — VERIFIED — `EXEMPT_JOBS` is keyed by bare job name, so one exemption covers every file

**SEVERITY: Medium** (no live impact — the dict is empty; it is a trap laid for its first user).

`:69` declares `EXEMPT_JOBS: dict[str, str]`, `:132` tests `if job in exempt`, and `:135` reports
`f"{fname}:{job}"`. The report is file-qualified; the key is not. Executed:

```
$ python3 -c "…; m.unpinned_jobs({'a.yml': J, 'b.yml': J}, {'schema-gates': 'runs no python'})"
[]      # BOTH files' `schema-gates` jobs exempted by one entry
```

Both current workflow files already contain a job called `schema-gates`/`prod-drift` in one file and
`verify` in the other; a second `verify` in a future workflow is entirely likely. Exempting one
silently exempts the other, and the exemption's written reason then covers a job it was never about.

Fix: key on `f"{fname}:{job}"`, which is the string the failure message already prints — so the fix
also makes "copy the name out of the error" the correct action. Falsifier: the probe above must
return `['b.yml:schema-gates']`.

---

### L1 — VERIFIED — one self-test case computes its own expected value

`:282`

```python
    case("a matching interpreter is OK in CI", verdict({"w.yml": PINNED}, "3.12", True),
         (0, verdict({"w.yml": PINNED}, "3.12", True)[1]))
```

The second element of `want` is the same call. Executed: rewording the OK message killed **only** the
neighbouring case —

```
killed :: verdict: OK message reworded
          killed by: ['...and the OK message names the pin']     ← :284, not :282
```

So `:282` asserts the exit code and nothing else; its message half can never fail. Not a coverage
hole (`:284` covers the message), but it is one more instance of the ambient-pass class the branch
says it already found twice in this file. Fix: `case(…, verdict(…)[0], 0)` and let `:284` own the
message.

### L2 — VERIFIED — the `.yaml` half of the corpus is unguarded

`:190` reads `*.yml` + `*.yaml`. Dropping the `.yaml` glob survives the suite (see H3's run). There is
no `.yaml` file today, so this is a latent corpus hole rather than a defect: the first
`release.yaml` anyone adds becomes invisible, silently, in the same direction as H2. One case over
a two-key dict would pin it — or the H2 refusal (zero jobs seen → exit 2) covers it for free.

### L3 — VERIFIED — the `dev-process.md` compression lost a clause and hardened a hedge

```
-Verify progress from ground truth before acting — never from a context summary, which is a
-compressed snapshot and can be stale after `/compact`:
+Verify from ground truth, never a context summary — compressed, and stale after `/compact`:
```

Two changes, one harmless, one not: "before acting" was the operative instruction (*when* to verify)
and is gone; and "can be stale" became "stale", which asserts something false — a summary is often
current. `check-docs.py` is green and the file is at exactly 220/220, so the budget was genuinely
paid; the cheapest repair keeping the line count is roughly *"Verify from ground truth before acting,
never a context summary — compressed, and stale after `/compact`."* (one word longer, same line).

### L4 — REASONED — the took-effect question is asked only for `verify`

`check-python-pin.py` runs in `ci.yml` only. Its *declaration* checks are cross-file (it reads every
workflow), so a missing pin in `schema-gates.yml` is caught — verified: `verdict(real_corpus, "3.11",
True)` → `1`. But the in-CI "took effect" comparison is made against `verify`'s interpreter alone. If
`schema-gates`'s `setup-python` were present and ineffective, nothing observes it. Small, and H1's
`pythonLocation` fix plus one step in `schema-gates.yml` closes it if wanted.

---

## Mutation manifest — ATTACK 7: **clean, verified by applying all eleven**

```
$ python3 /tmp/pinrev/mutate.py
CONTROL rc=0 fails=[]
duplicate names: []
KILL ATTR anchors=ok :: declared_pins stops stripping quotes…
KILL ATTR anchors=ok :: job_names runs past the jobs block…
KILL ATTR anchors=ok :: job_blocks stops splitting…
KILL ATTR anchors=ok :: unpinned_jobs stops honouring the exemption list
KILL ATTR anchors=ok :: running_version drops the minor…
KILL ATTR anchors=ok :: the empty-corpus refusal goes…
KILL ATTR anchors=ok :: the no-pin-anywhere refusal goes…
KILL ATTR anchors=ok :: disagreeing pins stop failing…
KILL ATTR anchors=ok :: an unpinned job stops failing…
KILL ATTR anchors=ok :: the CI assertion goes…
KILL ATTR anchors=ok :: the local advisory becomes a FAILURE…
```

- **Control green first** (the `the-control-refuted-the-premise` precondition).
- **Every anchor occurs exactly once** in the delivered file — `anchors=ok` is a literal
  `text.count(frm) == 1` assertion, so the five-collision failure mode of the previous branch does
  not recur here.
- **All 11 killed, all 11 attributed** via the case each names.
- No duplicate mutation names; and the reverse direction is clean too — every `expect` string matches
  a real case name (`mutation 'expect' names with no matching case: set()`), so there are no orphaned
  anchors of the `a-refactor-orphans-the-mutation-guarding-it` kind.
- CI agrees: `748 mutation(s), 748 killed, 748 attributed, 0 survivor(s)` over 48 files
  (737 → 748 = +11, matching the `EXPECTED_MUTATIONS` edit).

11 of 28 cases are mutation-protected; every unprotected one I probed by hand is listed under H3/L1/L2.

---

## Attacks that produced nothing

Listed because a clean attack is evidence too.

| # | Attack | Result |
|---|---|---|
| 1 | "3.12 is what CI already ran" is unverified | **Refuted** — runner image `ubuntu24/20260907.300` ships system Python **3.12.3**; pin resolves to tool-cache **3.12.14**. Same major.minor. Nuance recorded above, no finding |
| 2 | The pin can fail or no-op | 3.12.14 is in the image's cached tools, so no download is even needed; if a future image drops it, `setup-python` fails the **step** — loud, not silent. Cost measured from the branch's log: `11:05:16.9577 → 11:05:17.0740` = **0.12 s** |
| 2b | The interpreter swap breaks an import | No `pip install` in either workflow; every import in `scripts/*.py` is stdlib or local; no hardcoded `/usr/bin/python3`; all 57 shebangs are `env python3`. Confirmed empirically — the full suite incl. the 748-mutation harness is green on 3.12.14 |
| 3 | A shape the line scan misreads **into a false POSITIVE** | Probed matrix jobs, reusable-workflow (`uses:` at job level), `if:` at job level, anchors, 4-space indent, `jobs:` in a run block. All failures are in the **fail-OPEN** direction (H2). The only false positives found are M1's and M2's, which are value-parsing and scope, not job scanning |
| 4 | `declared_pins` matches a comment or a run-block string | **Cannot** match a comment: `#` is not `\s`, so `^\s*python-version:` never reaches it. A `python-version: 3.11` line *inside* a `run: |` block does match — contrived enough that I am not filing it; the untested-ness of the `^` anchor is noted under H3 |
| 5 | `GITHUB_ACTIONS` can be set to silence the assertion | The advisory path only relaxes the took-effect question; the declaration questions still fail locally (verified: an unpinned job → `rc=1` on this 3.14 machine). Setting `GITHUB_ACTIONS` *on* only makes it stricter. The real exposure is H3's untested wiring, not the variable |
| 6 | Something earlier in `ci.yml` already uses Python | **No.** Steps before the check: `checkout` → `setup-node` → `setup-python` → `apt-get install ffmpeg`. First Python invocation in the job is the pin check itself (`ci.yml:107`), and it precedes all 45 others |
| 8 | More ambient cases | Found one (L1). The `group:`-with-no-value fixture at `:223-228` is genuinely load-bearing — loosening the job-key indent kills three cases including that one |
| 9 | Meaning lost in the `dev-process.md` compression | Yes, small — filed as L3 |
| — | Registration is complete and green | `check-ratchet-contract` ✅, `check-selftest-counts` ✅ (41 scripts, each verified by running it), `check-fixture-variation` ✅ (561 params, 53 files), `check-gate-falsifiability` ✅, `check-docs` ✅ (220/220 lines), `check-anchors` ✅ — all `rc=0` locally at `a741549e` |

Cleanup: `/tmp/pinrev/` and the `/tmp/*.log` captures are scratch only; `git status` is clean, no
tracked file was modified by this review other than this document.

---

## VERDICT

**NOT CONVERGED.** Three High and three Medium findings, all in the new guard rather than in the
workflow edits. The branch's *premises* are all true — I attacked the load-bearing one hardest and it
survived with evidence. What does not hold is the guard's account of its own strength: it claims a
direction that "cannot fail silently" while four legitimate YAML shapes pass silently (H2), and it
claims to assert the pin took effect while the comparison it makes is satisfied by the unpinned world
(H1). H3 is the same shape one layer down — the line that arms the assertion is the only line no case
and no mutation touches.

None of the six is expensive. H2 and H3 are a regex, a refusal, and one extracted function; M1 and M3
are a `split("#")` and a dict key.

## MERGE SAFETY

**Safe to merge as far as the repository is concerned — it does not and will not red the required
check for anyone else.** Verified, not assumed: the branch's own `verify` run fails on exactly one
step, `check-review-recorded` ("no review round was recorded"), which this document closes; the
`schema-gates` run on the same commit is **green**, with all fifteen gates passing on CPython
3.12.14. The workflow edits themselves are the safest part of the branch — `setup-python@v5` is a
0.12 s step resolving a version already present in the runner image's tool cache, and the pinned
interpreter is the same major.minor the repository has been running all along.

**My recommendation is to fix before merging, not after** — but the reason is quality of claim, not
risk of breakage. The three documents asserting "the pin took effect" (H1) are the kind of sentence
that gets believed and cited later, and H2's fail-open is cheapest to close now, while the file is
one commit old and nobody has added the workflow that would slip through it.

---

## ADDENDUM — the working tree moved WHILE this review was being written

**Read this before acting on anything above.** Everything above is about **`a741549e`**, the commit I
was asked to review, and it stays valid for that commit. But between my probes and this file being
saved, `scripts/check-python-pin.py` and `scripts/mutations/check-python-pin.json` were modified in
the working tree by a concurrent fold — evidently of the Codex half's r1 High, since the new
`declared_pins` docstring cites *"r1 High (codex)"*. My earlier sentence "no tracked file was
modified" describes **my own** actions and was true when written; the tree is no longer clean, and
not because of me.

```
$ git status --porcelain
 M scripts/check-python-pin.py
 M scripts/mutations/check-python-pin.json
?? docs/reviews/claude/pin-python-interpreter-r1-claude.md
?? docs/reviews/codex/pin-python-interpreter-r1-codex.md
?? docs/reviews/verdicts/pin-python-interpreter-r1-codex.verdict.json

$ git rev-parse HEAD
a741549e…                       # HEAD unmoved; the change is uncommitted

reviewed  scripts/check-python-pin.py  61737b89…   28 cases, 11 mutations
now       scripts/check-python-pin.py  de5fe3f7…   32 cases, 12 mutations
```

What changed: `declared_pins` no longer matches any pin-shaped line. It now walks from a
`- uses: actions/setup-python…` line to the start of the next step and counts only a
`python-version:` inside that span — closing the case where a `python-version:` in a heredoc or an
unrelated action's `with:` block made an entirely unpinned job read as pinned.

**I re-ran every probe against the modified tree. All six findings survive unchanged:**

```
$ python3 /tmp/pinrev/failopen.py            # H2
0  job key w/ trailing comment     []          ← still a SILENT PASS
1  job key w/ trailing space       ['deploy.yml:deploy']
0  4-space indented jobs           []          ← still a SILENT PASS
0  `jobs:` with trailing comment   []          ← still a SILENT PASS
0  anchored job key                []          ← still a SILENT PASS
1  plain unpinned job (control)    ['deploy.yml:deploy']

$ python3 /tmp/pinrev/fp.py                  # M1
rc=1  inline comment after the pin    declared=["3.12'  # the version CI already ran"]
rc=1  inline comment, unquoted        declared=['3.12  # pinned']
rc=1  patch-level pin                 declared=['3.12.14']

$ python3 /tmp/pinrev/unguarded.py           # H3, L2
SURVIVES :: main: in_ci hard-wired False (CI assertion never armed)
SURVIVES :: main: returns 0 always (guard can never fail the step)
SURVIVES :: _read_workflows: only read *.yml (drop the .yaml glob)
SURVIVES :: job_names: allow a trailing value/comment on the job key
killed   :: verdict: OK message reworded  → killed ONLY by '...and the OK message names the pin'   # L1 stands
```

H1 and M3 are untouched code (`verdict:170`, `EXEMPT_JOBS`) and stand by inspection. The fold
repaired the value's **provenance**; none of my findings are about provenance.

**One sub-note of mine is now stale, and it is stale in the good direction.** Under H3 I reported
that dropping the `^` anchor from the `python-version:` regex survived the suite. On the modified
file it is **killed by 16 cases** — the new step-boundary walk depends on that anchor, so it became
load-bearing as a side effect. Strike that paragraph; the two `main` mutations it was attached to are
unaffected and still survive.

**Honest note on the heredoc case.** My *Attacks that produced nothing* table records that a
`python-version:` inside a `run: |` block does match `declared_pins`, and I judged it "contrived
enough that I am not filing it". The Codex half filed it as a High and it has been fixed. That call
of mine was wrong: the shape is the same fail-open family as my own H2, and I should have filed it
rather than rated it unlikely. Recorded here rather than quietly edited out of the table.

**Consequence for the round.** The fold is in flight and its ratchet arithmetic was momentarily
inconsistent mid-write (manifest 12 entries vs `EXPECTED_MUTATIONS` 11, declared sum 748) and is now
consistent again (12 / 12 / 749). I re-replayed the manifest against the modified file after the fold
settled: **control green, 12/12 applied with every anchor occurring exactly once, 12/12 killed,
12/12 attributed via the case each names, no duplicate names.** So the fold is sound on its own
terms — it simply does not touch what H1, H2, H3, M1, M2 or M3 are about.

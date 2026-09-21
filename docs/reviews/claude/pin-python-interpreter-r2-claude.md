# Round 2 — Claude adversarial review — `pin-python-interpreter` (PR #317), NARROW / FINAL-TREE

## PROOF OF SUBJECT

```
$ git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
pin-python-interpreter
8c6e35e63c3ecfaf57ec3936c80530e40e029e36

$ git log --oneline -4
8c6e35e6 r2 codex High: the pin must be the input the ACTION reads, not merely nearby
c65e4f29 r1: the guard claimed to prove the pin took effect, and it could not (PR #317)
a741549e Pin the interpreter every guard runs on — it was never declared (follow-up to #137)
72396668 Close backlog #137 — and this docs-only PR is its own falsifier (#316)

$ git status --porcelain     # empty — the tree did not move while this was written
```

**Compared `a741549e..8c6e35e6` — two commits, `c65e4f29` and `8c6e35e6`.** Eleven files,
`+1134/-38`. The code half is `scripts/check-python-pin.py` (+251/-38 region),
`scripts/mutations/check-python-pin.json`, `scripts/check-plan-code.py` (counts),
`.github/workflows/schema-gates.yml` (two new steps), `docs/dev-process.md` (one line),
`docs/dashboard-entries.md` (one entry). The rest is the r1/r2 review record.

The tree was held still, as promised. Every probe below ran against `8c6e35e6` with a clean tree,
and every mutation ran on a copy in `/tmp` — no tracked file was modified.

---

## CONTROL FIRST

```
$ python3 scripts/check-python-pin.py --self-test   ; echo rc=$?
48/48 passed
rc=0
$ python3 scripts/check-plan-code.py --self-test    ; echo rc=$?
128/128 passed
rc=0
```

Repo gates, exit codes captured directly (not through a pipe — my first pass read `tail`'s status
and I re-ran them):

| gate | rc | last line |
|---|---|---|
| `check-selftest-counts` | 0 | 41 scripts declare a count, every one verified by running it |
| `check-docs` | 0 | Documentation integrity OK |
| `check-ratchet-contract` | 0 | ratchet contract OK |
| `check-dashboard-entry` | 0 | ok — an entry block was added |
| `check-anchors` | 0 | floor 22 held |
| `check-arch-findings` | 0 | 0 regressed past baseline |
| `check-test-counts` | 0 | 2,819 unit / 274 suites |
| `check-review-rounds` | **1** | `pin-python-interpreter round 2: only codex` — **this document is the missing half** |

---

## ⭐ ATTACK 5 FIRST — the 19 mutations: **CLEAN, all applied**

Each entry applied to a `/tmp` copy of the delivered script, over a control proved green.
Attribution parsed from the real `  [FAIL] <case>: got X want Y` line shape.

> ⚠ My first attribution parser was `FAIL\s+(.*)`, and it reported all 19 "correctly attributed"
> for the wrong reason: several case *names* contain the word `FAIL`, so the regex matched inside
> `ok` lines. I caught it when the same parser reported `[]` failures on a run that was red, and
> redid it. The numbers below are from the corrected parser. (`a-report-format-is-a-contract`.)

```
CONTROL rc=0 failed=[] tail='48/48 passed'

ok  killed_by=9  via its named case  declared_pins stops stripping quotes …
ok  killed_by=1  via its named case  job_names runs past the jobs block …
ok  killed_by=4  via its named case  job_blocks stops splitting …
ok  killed_by=2  via its named case  unpinned_jobs stops honouring the exemption list
ok  killed_by=2  via its named case  running_version drops the minor …
ok  killed_by=1  via its named case  the empty-corpus refusal goes …
ok  killed_by=1  via its named case  the no-pin-anywhere refusal goes …
ok  killed_by=1  via its named case  disagreeing pins stop failing …
ok  killed_by=1  via its named case  an unpinned job stops failing …
ok  killed_by=1  via its named case  the in-CI VERSION check goes …
ok  killed_by=1  via its named case  the local advisory becomes a FAILURE …
ok  killed_by=2  via its named case  the step's ACTION is no longer checked …
ok  killed_by=2  via its named case  pin_took_effect answers True with no evidence …
ok  killed_by=1  via its named case  the provenance test loses its separator …
ok  killed_by=1  via its named case  the no-provenance refusal goes …
ok  killed_by=1  via its named case  the wrong-interpreter refusal goes …
ok  killed_by=2  via its named case  asserts_here arms everywhere …
ok  killed_by=2  via its named case  the jobless refusal goes …
ok  killed_by=2  via its named case  the pin need not be under with: …

19 entries · 0 problems
```

Every anchor was asserted `count == 1` in the source before substitution (so uniqueness is proved,
not assumed), no edit was a no-op, no name repeats. `EXPECTED_MUTATIONS["scripts/check-python-pin.py"]`
is `19` and `sum(EXPECTED_MUTATIONS.values())` is `756`, matching `check-plan-code.py:3291`.
**Attack 5 found nothing.**

---

## FINDINGS

### ⭐ H1 — VERIFIED — naming the step hides the pin, and the error message then routes the author to `EXEMPT_JOBS`

**SEVERITY: High.** `scripts/check-python-pin.py:93`

```python
        m = re.match(r"^(\s*)-\s+uses:\s*actions/setup-python", line)
```

The scan starts **only** at a step whose list dash is immediately followed by `uses:`. Give the step
a `name:` — the ordinary way to label a step, and the way this repository writes 62 of its 70 steps —
and the dash is followed by `name:`, `uses:` carries no dash, the regex matches nothing, and the
whole `with:` block is never entered.

Executed:

```
$ python3 /tmp/pinattack/probe1.py
A: `- name:` BEFORE `uses:` (GitHub's own documented idiom)
   declared_pins -> []
   unpinned_jobs -> ['w.yml:verify']
   verdict(local) -> rc=2
```

fixture:

```yaml
jobs:
  verify:
    steps:
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
```

That job is pinned. The guard says it is not.

**Why this is High and not Medium, given r1 M1 was Medium for the same fail-closed direction.**
The direction is indeed closed — red, not green. But look at what the red *says* (`:259-263`):

```
FAILED — 1 job(s) pin no Python version:
    release.yml:release
  Add `uses: actions/setup-python@v5` with `python-version: '3.12'`, or
  add the job to EXEMPT_JOBS with the reason it runs no Python.
```

The first instruction is *do the thing you already did*. The second is an escape hatch. An author
staring at a `setup-python` step that is visibly present, told by a required check that it is absent,
takes the hatch — and `EXEMPT_JOBS` is permanent and silent. **The fail-closed message converts
itself into the fail-open outcome**, and the exemption's written reason ("runs no Python") is then
false about a job that does. That is the guard's own worst case, reached through its own advice.

Blast radius: `schema-gates` and `verify` are both required since backlog #137, so this reddens every
open PR the moment such a workflow lands.

There is also a genuine false-*green* tail. Two `setup-python` steps in one job, the effective one
written `- name:`-first and the other written bare, produce one visible pin and one invisible one — no
disagreement is detected and the guard certifies a version the job does not install. Contrived, but it
is the same regex.

**Measured house style, which is what makes this reachable:**

```
$ grep -c "^      - uses:" .github/workflows/*.yml
ci.yml:3   schema-gates.yml:5
$ grep -c "^      - name:" .github/workflows/*.yml
ci.yml:52  schema-gates.yml:10
```

Eight bare-`uses:` steps against 62 named ones — and this very diff adds two more named steps
(`- name: The Python pin took effect`) directly beneath the three bare ones. One contributor tidying
for consistency flips it.

**Fix.** Recognise the step, not the line: start a step at any `^(\s*)-\s` and, inside it, look for
both `uses: actions/setup-python` and the `with:` mapping in either order. **Falsifier:** shape A above
must return `['3.12']`, and the existing case *"...nor is one in an UNRELATED action's `with:` block"*
must still return `[]`.

---

### M1 — VERIFIED — the jobless refusal only fires when a file has **zero** readable jobs; one readable job restores the original false green

**SEVERITY: Medium** (real, and the code comment claims it is closed). `scripts/check-python-pin.py:244-256`

The new refusal reads:

```python
    jobless = sorted(f for f, text in workflows.items() if not job_names(text))
```

and its comment claims it turns *"any future unparseable shape from a silent pass into a loud NOT
CHECKED."* That holds only for all-or-nothing files. A file with one job the regex reads and one it
does not is not jobless, so nothing refuses — and `job_blocks` then slices the invisible job's text
into its visible neighbour, crediting the neighbour with a pin it does not have.

Executed:

```
$ python3 /tmp/pinattack/probe2.py
job_names          -> ['verify']
job_blocks keys    -> ['verify']
verify's block contains prod-drift's pin -> True
unpinned_jobs      -> []
verdict IN CI      -> rc=0  'python pin OK — every job pins 3.12, and this interpreter is 3.12'

control, both quoted -> job_names=[] verdict rc=2      # the refusal DOES fire here
```

fixture — `verify` has no `setup-python` at all; `"prod-drift"` uses a quoted key, which GitHub
accepts and `^  ([A-Za-z_][\w-]*):` does not:

```yaml
jobs:
  verify:
    steps:
      - run: echo "no python setup here at all"
  "prod-drift":
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
```

This is verbatim both r1 Highs at once — a job with no `setup-python` reading as pinned (codex r1),
and a pin credited to a sibling, which is the exact thing `job_blocks`' own docstring at `:148` says
the split exists to prevent.

**Reachability is low** — a quoted job key is the only spelling I found that GitHub accepts and the
regex rejects; unquoted job ids are constrained to `[A-Za-z_][\w-]*` and the regex covers all of them.
I am filing it because the *claim* in the comment is what is wrong, and a documented "this class is
now closed" is how the class stops being looked for.

**Fix.** Make the refusal count rather than test emptiness: inside the `jobs:` block, any 2-space
key-shaped line the job regex rejects is an unreadable job → exit 2. **Falsifier:** the fixture above
must return `rc=2`, and the real corpus must stay `rc=0`.

---

### M2 — VERIFIED — the dashboard entry states three counts, and all three are wrong

**SEVERITY: Medium** (human-facing, and no gate reads it). `docs/dashboard-entries.md:9895`

```
Current: 45 self-test cases, 18 mutation entries, manifest total 755, every entry proved to go red
through the case it names.
```

Measured on `8c6e35e6`:

```
$ python3 scripts/check-python-pin.py --self-test | tail -1
48/48 passed
$ python3 -c "import json;print(len(json.load(open('scripts/mutations/check-python-pin.json'))))"
19
$ # sum of EXPECTED_MUTATIONS, parsed with ast
manifest total (sum of EXPECTED_MUTATIONS): 756
entry for check-python-pin.py:              19
$ grep -n "the declared counts are the real ones" scripts/check-plan-code.py
3291:    case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 756)
```

48 / 19 / 756, not 45 / 18 / 755. The entry was written at `c65e4f29` and the second commit moved all
three under it. `check-dashboard-entry.py` is green because it owns the entry *header grammar*, not
the entry's arithmetic; `check-selftest-counts.py` reads `scripts/*.py` only.

This is the drift `docs/plugins.md` already records against itself — *"the pin stops the SCRIPT
drifting; it cannot see a second copy in prose"* — one file over, five days later, and the diff
carrying it also carries the sentence saying so.

**Fix.** Correct the three numbers, or drop the sentence. The durable version is to drop it: a count
with no owner drifts again, which is the resolution `docs/plugins.md` reached for the same problem.
**Falsifier:** the entry's numbers must equal the three commands above.

---

### M3 — VERIFIED — r1 M1's fix is real but **unfalsifiable**: deleting the inline-comment strip leaves 48/48 green

**SEVERITY: Medium.** `scripts/check-python-pin.py:115`

```python
                pins.append(got.group(1).split("#")[0].strip().strip("'\""))
```

The `.split("#")[0]` is r1 Medium 1's fix and the diff documents it as such at `:112-114`. Nothing
drives it. Executed — the fix removed, everything else intact:

```
$ python3 /tmp/pinattack/extra.py
SURVIVED ❌       declared_pins: inline-comment strip removed
```

The manifest's first entry mutates the *neighbouring* `.strip("'\"")` and is killed by the quotes
case; no case in the suite puts a comment on a pin line. So the fix works —

```
$ python3 /tmp/pinattack/r1check.py
M1 — an inline comment on the pin line:
  declared_pins -> ['3.12']
  verdict IN CI -> rc=0
```

— and nothing would notice if it stopped. The manifest count rose 12 → 18 citing M1 among the folds,
and M1 is the one fold in that list with neither a case nor an entry.

**Fix.** One case: `declared_pins("…python-version: '3.12'  # matches the Dockerfile\n") == ['3.12']`,
plus a manifest entry naming it. **Falsifier:** the mutation above must go red.

---

### L1 — VERIFIED — two r1 findings were neither folded nor declined in writing

`docs/reviews/claude/pin-python-interpreter-r1-claude.md:339` (M2) and `:404` (L2).

- **r1 M2** asked for one sentence in the docstring recording that the guard reddens the required
  check for every open PR the moment an unpinned workflow arrives (CodeQL default setup, a
  Dependabot-authored workflow). I explicitly did *not* ask for behaviour change. Measured:
  `grep -c "every open PR\|blast radius\|required check for every" scripts/check-python-pin.py` → `0`.
- **r1 L2**: the `*.yaml` half of the corpus is still unguarded.
  ```
  $ python3 /tmp/pinattack/extra.py
  SURVIVED ❌       L2: drop the .yaml glob from the corpus
  ```
  Note my r1 text speculated the jobless refusal would "cover it for free" — **that was wrong**, and
  I am correcting it here: a file that is never *read* cannot be jobless.

Both are Low-impact. The finding is that the fold list in the commit and the dashboard entry reads as
complete, and a silently-dropped finding is indistinguishable from a forgotten one.

---

### L2 — VERIFIED — three clauses inside the new `pin_took_effect` are undriven, one of them fail-open

`scripts/check-python-pin.py:218-221`

```python
    if not tool_location:
        return None
    root = tool_location.rstrip("/")
    return executable == root or executable.startswith(root + "/")
```

Executed, each deletion applied alone:

```
SURVIVED ❌   pin_took_effect: empty-string location is 'no evidence' -> 'is None'
SURVIVED ❌   pin_took_effect: drop the equality arm (location itself is the interpreter)
SURVIVED ❌   pin_took_effect: drop the rstrip, so a trailing slash breaks provenance
```

The first matters most, and it is **fail-open**: with `not tool_location` narrowed to
`tool_location is None`, an *empty* `pythonLocation` gives `root = ""` and
`executable.startswith("/")` → `True` for every absolute path on earth. A step doing
`echo "pythonLocation=" >> $GITHUB_ENV`, or a `setup-python` that exports the variable empty on a
partial failure, would then certify provenance for the ambient interpreter — the precise defect H1's
fix exists to stop, restored by a plausible tightening. Nothing in the suite would see it.

The other two are dead-weight clauses rather than hazards: an interpreter is never the directory
itself, and no case supplies a trailing slash (my probe shows it works — `pin_took_effect(EXE, LOC+"/")`
→ `True` — just that nothing holds it).

**Fix.** Three cases: `("", "")`-style empty location → `None`; a trailing-slash location → `True`;
drop the equality arm or give it a case. **Falsifier:** the three mutations above must go red.

---

### L3 — VERIFIED — `verdict`'s docstring says the order "is asserted by its own cases"; the new refusal's position is not

`scripts/check-python-pin.py:227` — *"PURE. `(exit code, message)`. Order matters and is asserted by
its own cases."* Executed, moving the whole `jobless` block below the `missing` block:

```
SURVIVED ❌   verdict: the jobless refusal is asked AFTER the unpinned-job question
```

I traced whether the order is load-bearing and concluded it mostly is not — a jobless file contributes
no jobs to `unpinned_jobs`, so both orders reach the same refusal unless a *second* file has a
genuinely unpinned job, in which case you get `1` instead of `2`. Both non-zero; no green is produced
either way. So this is a **documentation** defect: the docstring's claim is now false for one of the
five branches, and that sentence is the reason a later reader will not re-check.

I did search for a masking pair that produces a *wrong* answer and **found none** — see below.

---

### L4 — VERIFIED — the dashboard entry credits both reviewers with a finding only one made

`docs/dashboard-entries.md:9860` — *"**The new check claimed to prove something it could not**, and
both reviewers found it."*

Measured against the two codex halves in this same diff:

- `docs/reviews/codex/pin-python-interpreter-r1-codex.md:11` — codex's r1 High is that *`schema-gates`
  never runs the checker*, a different defect (it matches my r1 L4, not my H1). Its r1 `:19` High is
  `declared_pins` matching any line.
- `docs/reviews/codex/pin-python-interpreter-r2-codex.md:63` — codex r2 lists provenance under
  *"Attacks that failed"*. It reviewed the fix; it did not find the defect.

Neither codex half found that the version comparison cannot prove effect. That was the Claude half
alone — which is the standing evidence for why both halves run
(`dual-review-halves-are-not-redundant`), and merging a record that erases it weakens the argument
for the next round's cost.

---

### L5 — VERIFIED — a provenance check that passes prints no provenance

`scripts/check-python-pin.py:288`

```
python pin OK — every job pins 3.12, and this interpreter is 3.12
```

The whole point of this diff is that the version is no longer the evidence. The OK message still
reports only the version, so the CI log of a *passing* run contains nothing about `pythonLocation` or
`sys.executable` — the two values the pass was actually decided on. `docs/dev-process.md`'s own gate
rule is *"record which build a manual check was verified against"*; the same applies here. One
f-string: `… and this interpreter is 3.12, from {tool_location}`.

Related bounds, none of them defects today, all fail-closed, none stated anywhere:

```
$ python3 /tmp/pinattack/probe4.py
 False  venv made FROM the pinned interpreter        exe='/home/runner/work/x/.venv/bin/python'
 False  windows-style backslash layout               (separator is hard-coded "/")
  True  pythonLocation = a PARENT of the install     loc='/opt/hostedtoolcache/Python'
  True  location is '/' (degenerate)                 anything passes
```

A job that creates and activates a venv from the pinned interpreter reddens the required check; every
runner in this repo is `ubuntu-latest` so the separator does not bite today. Worth one docstring line,
not a change.

---

## Attacks that produced NOTHING — the ones that matter for merge

**Attack 1 — a fourth `declared_pins` shape.** Eight shapes probed (`/tmp/pinattack/probe1.py`). One
hit (H1). The rest:

| shape | result | verdict |
|---|---|---|
| `with: {python-version: '3.12'}` flow mapping | `[]` → job reads unpinned, `rc=2` | fail-closed, valid YAML, **noted not filed** — same root as H1 |
| `uses:` written after `with:` in one step | `[]` → `rc=2` | fail-closed; legal YAML, vanishingly rare |
| column-0 comment inside a step | `[]` → `rc=2` | fail-closed; illegible style |
| two `setup-python` steps, differing | `['3.12','3.11']` → `rc=1` disagreement | **correct** |
| `python-version: ${{ matrix.py }}` | pin is the expression → `rc=1` in CI | fail-closed; no matrix in this repo |
| block scalar `python-version: >-` | pin reads `'>-'` → `rc=1` in CI | fail-closed, nonsense message, not reachable here |
| tab-indented continuation | `[]` | YAML forbids tabs for indentation — **not a finding** |

The three flow/ordering shapes collapse into H1's fix (recognise a step, not a line), so I have not
filed them separately.

**Attack 2 — `pin_took_effect` from a different angle.** Symlinks, venvs, parent locations,
case-differing paths, relative `sys.executable`, empty executable, trailing slashes: eleven probes,
one finding (L2's empty-location mutation), and the live discrimination is **proved**, not argued —

```
$ python3 /tmp/pinattack/r1check.py
H1 — provenance discriminates update-environment: false:
  ambient python3, version MATCHES pin -> rc=1      # new code, correctly red
  (pre-diff code on the same world)    -> rc=0      # a741549e, green on the same world
```

That is the H1 fix working on the exact world that defeated the old one.

**Attack 3 — a masking pair among the five refusals.** None found that yields a wrong answer. The two
orderings I could construct that change the *message* (`len(pins) > 1` before `jobless`; `jobless`
before `missing`) both return non-zero either way, so no green is produced. The one pair that could
have masked — `effect is None` versus `not effect`, where `not None` is also truthy — is the pair the
diff already closed by asserting the message at `:439-442`, and the mutation for it is killed.

**Attack 4 — the jobless refusal on a legitimate workflow.** I could not make it false-fire.
Reusable (`workflow_call`) workflows have jobs. Anchored and merge-keyed job maps parse: `deploy: &d`
and `build:` + `<<: *defaults` both yield names (r1's falsifier table below). A workflow with no
`jobs:` is invalid and GitHub rejects it. The only files it refuses are ones whose jobs a *human*
would read and the line scan cannot — which is the intent. The residual is M1's mixed case, where it
does not fire at all.

**A collision I expected and did not get.** `job_blocks` finds a job's start by scanning the *whole*
file for `^  <name>:`, so a job named `push` should collide with `  push:` under `on:`. It does not
produce a false green — measured both pre- and post-diff:

```
$ python3 /tmp/pinattack/probe3.py
job_names   -> ['push', 'verify']
unpinned_jobs -> ['w.yml:push']
verdict IN CI -> rc=1   (correct)
```

**Attack 6 — an ambient pass.** 19 manifest mutations plus 19 of my own, on every clause the diff
adds. Four undriven clauses found (M3, L2×3, L3) — all reported. The two "absence" cases that worried
me (`declared_pins(env-block) == []`, `declared_pins(heredoc) == []`, which pass on any parse failure)
are each paired with a positive case over the *same* fixture, so they are not vacuous; the diff's own
comment at `:352-356` says out loud that the heredoc pair never reaches the step-boundary clause,
which is the honest version of this. `r1 L1`'s self-comparing case is gone — verified:
`case("a matching interpreter WITH provenance is OK in CI", verdict(...)[0], 0)` is a literal now.

---

## ATTACK 7 — are my ten r1 findings fixed, or reported fixed? **Eight fixed, two dropped**

Executed, `/tmp/pinattack/r1check.py`, against the real corpus:

```
H2 — r1's own falsifier table (r1 demanded 1 everywhere, 2 for the 4-space row):
  rc=1  job key w/ trailing comment      unpinned=['deploy.yml:deploy']
  rc=1  job key w/ trailing space        unpinned=['deploy.yml:deploy']
  rc=2  4-space indented jobs            unpinned=[]
  rc=1  `jobs:` with trailing comment    unpinned=['deploy.yml:deploy']
  rc=1  anchored job key (deploy: &d)    unpinned=['deploy.yml:deploy']
  rc=1  plain unpinned job (CONTROL)     unpinned=['deploy.yml:deploy']

M1 — inline comment on the pin line: declared_pins -> ['3.12'], rc=0
M3 — one entry, two files -> ['b.yml:schema-gates']            (file-qualified)
H3 — asserts_here drivable: True False False
H1 — ambient python3 + matching version: new rc=1, pre-diff rc=0
```

| r1 finding | status | evidence |
|---|---|---|
| **H1** took-effect cannot fail | ✅ fixed | provenance table above; old code green / new code red on the same world |
| **H2** four invisible job shapes | ✅ fixed | falsifier table matches r1's demand exactly, row for row |
| **H3** the arming line undrivable | ✅ fixed | `asserts_here` + 3 cases + 1 mutation, killed |
| **M1** inline comment reds the check | ⚠️ **fixed, unfalsifiable** | works; deleting the fix leaves 48/48 green → **M3 above** |
| **M2** blast radius undocumented | ❌ **not folded** | `grep -c` → 0 → **L1 above** |
| **M3** exemption keyed by bare name | ✅ fixed | `['b.yml:schema-gates']` |
| **L1** case computes its own `want` | ✅ fixed | now a literal `0` |
| **L2** `.yaml` glob unguarded | ❌ **not folded** | mutation survives → **L1 above** |
| **L3** `dev-process.md` lost a clause | ✅ fixed (partly) | *"before acting"* restored, *"stale"* → *"can go stale"*; the word *"compressed"* — the **reason** a summary is untrustworthy — is gone. `check-docs` green, budget paid. Not filing |
| **L4** took-effect asked only for `verify` | ✅ fixed | `schema-gates.yml:210` and `:280` both run the checker |

No finding was reported fixed and is not. The two gaps are omissions, stated as such.

---

## VERDICT

**NOT CONVERGED.** One High, three Medium, five Low.

The two commits do what they claim, and the central one is proved rather than asserted: the
provenance test discriminates on exactly the world that defeated the version test, measured
side-by-side against `a741549e`. Eight of my ten r1 findings are genuinely fixed and one — H2 —
matches its own falsifier table row for row, which is the strongest form of "actually fixed" this
process has.

What is left is one live defect and a pattern. **H1 is the pattern**: `declared_pins` has now been
wrong three times, and each repair narrowed the *span* it searches without ever naming the *thing* —
"any line" → "inside the step" → "inside the step's `with:`" — while the step itself is still
recognised by a regex that only matches when nothing is written before `uses:`. The fourth shape was
found in the first probe. The diff's own docstring at `:81` says *"the rule is not text that looks
like a pin"* and then identifies the step by text that looks like a step.

**On thrashing (`docs/dev-process.md` Phase 6 arming condition).** Two consecutive rounds have now
carried a `declared_pins` finding caused by the previous round's own fix, in one component: r2 codex's
High was introduced by r1's fix, and my H1 is introduced by r2's — the component has produced a
High in three consecutive rounds. **I read the arming condition as met for `declared_pins`
specifically**, and the answer to *"can a redesign remove it?"* is yes and it is small: parse a step
as a unit rather than anchoring on the dash. I am flagging this rather than deciding it — the
coordinator owns that call, and the rest of the file converged cleanly.

## MERGE SAFETY

**This diff is SAFE TO MERGE as an improvement over `a741549e`, and I would not merge it as-is.**

Both halves of that sentence are load-bearing, so to be unambiguous:

- Nothing in the diff makes the repository worse than `a741549e`. Every change is a strict
  improvement, the required checks are green on the real corpus, and H1 does not fire on any workflow
  that exists today — measured: `python3 scripts/check-python-pin.py` against the live tree returns
  `rc=0` with the local advisory.
- **H1 should be fixed first**, because it is cheap, because its failure mode routes an author into a
  permanent `EXEMPT_JOBS` hole, and because merging now ships a guard whose stated predicate — *"every
  job pins, or is exempt with a written reason"* — is false for the way most people write the step.
- M2 is a one-line correction to a human-facing page that is wrong today and gets read by the person
  who was away; it should ride in the same commit.
- M1, M3, L1–L5 are all fine to fold or to file; none of them blocks.

**The merge is blocked on a process fact independent of the above:** `check-review-rounds.py` exits 1
for round 2's missing Claude half. This document is that half; the gate should go green when it lands.

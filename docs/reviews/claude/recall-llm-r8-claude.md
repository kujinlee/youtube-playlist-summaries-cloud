# Round 8, Claude half — the fold of round 8's Codex half (#201/#202/#213/#214)

**Mandate: adversarial. The claim under attack is that this fold is correct.**

Subject: the **working tree**, uncommitted, on `semantic-recall-replication`.

## THE FREEZE HELD, AND I VERIFIED IT WITH THE PUBLISHED RECIPE

`scratchpad/r8-freeze-recipe.sh`, run at the start of this half:

```
06c46d1e96c7f2501b471987d53446ca84cc2e4cedb969fea32516914b276a76
```

That is the dispatch fingerprint, byte for byte. Run again at the end, **with this document's own
path excluded**, the same:

```
06c46d1e96c7f2501b471987d53446ca84cc2e4cedb969fea32516914b276a76   # subject only
8799535a9511c5cb4c40968491972bf1d078b1018a0f33c9c703db55bb9844e8   # recipe verbatim
```

**No drift in the subject.** This is the first round in this fold whose reviewer could answer the
question #214 is about, and the recipe is why. ⚠ **But the recipe has a defect worth folding into
#214:** it hashes `git status --porcelain` and every file in it, so the **Claude half's own output
file** — which lands at `docs/reviews/claude/<id>.md`, inside the working tree — changes the
fingerprint the moment the review is written. A reviewer therefore cannot verify the freeze at the
*end* without hand-excluding its own deliverable, which is exactly the kind of step that gets
skipped. The recipe should take the paths it covers as an argument, or exclude
`docs/reviews/**` by construction. (The Codex half is unaffected: its contract is *write no file*.)

Findings are additionally pinned to:

| file | sha256 (first 16) |
|---|---|
| `scripts/check-surface-recall.py` | `be030b09e88d55f7` |
| `scripts/check-rc-contract.py` | `a816722f9724a1ec` |
| `scripts/check-ratchet-contract.py` | `cb1977f5a71f10b8` |
| `.claude/hooks/surface-recall.sh` | `b371b3ad29114732` |
| `scripts/mutations/check-surface-recall.json` | `c2d66767e6c04932` |
| `scripts/mutations/check-rc-contract.json` | `7f1b2717526668fc` |
| `scripts/mutations/check-ratchet-contract.json` | `bc974a2a3dca2331` |
| `scripts/check-plan-code.py` | `45eac469313a4108` |
| `docs/backlog.md` | `b4fc6931f3cb70fb` |
| `.github/workflows/ci.yml` | `ead368408c353271` |

**Method.** Every measurement below was taken in a copy of the tree, never in the repo. Two copies:
`<scratchpad>/t1` (full `rsync -a`, excluding `.git`, `node_modules`, `.next`, `.screenshots`,
`coverage`) and `<scratchpad>/t2` (the four files `check-surface-recall.py` actually needs). No
tracked file in the repo was modified and no writing `git` command was run. One fixture was written
into `t1/.claude/hooks/` for the R3 probes and removed; `ls .claude/hooks | grep -c selftest` in the
**repo** is `0` and `git status --porcelain | wc -l` is `23`, unchanged from dispatch.

**Controls, in `t1`, before anything was severed:** `check-surface-recall.py` 47/47 rc=0, live rc=0;
`check-rc-contract.py` 55/55 rc=0, live rc=0; `check-ratchet-contract.py` 47/47 rc=0, live rc=0,
`guards discovered (43)`.

---

## Severity summary

| # | Severity | Title |
|---|---|---|
| B1 | **BLOCKING** | **The FIFTH wiring instance, and it voids the WHOLE ratchet contract**: `violations = evaluate(…)` severed at its call site → 47/47 green and `ratchet contract OK` over a *real* `R3_no_caller` violation |
| B2 | **BLOCKING** | **The SIXTH, and it is round 8 H1's own fix**: `caller_source_paths(ROOT, ci_path)` severed at its call site restores H1's exact false green — fixture satisfies R3, suite stays 47/47 |
| H1 | HIGH | Round 8 H2's fix has **no case and no mutation entry**: reverting the `_env` scrub in `observe` leaves 55/55 green, and the four-key allowlist is now hand-copied into two files with nothing reconciling them |
| H2 | HIGH | **The ENVIRONMENT is now the fabricated world round 7 B2 was about.** An arm branching on a variable the allowlist drops renders a dangling `Detail:` in production while the guard reports CLEAN — reproduced |
| H3 | HIGH | The equality covers **one polarity**. A hook that silently truncates the reader's detail to 16 characters ships at 47/47, 55/55 and both live rc=0 — #209's gap, present in the NEW rule, unfiled |
| H4 | HIGH | **Seventh and eighth instances**: `defined = _defined_codes()` and `defined = defined_codes(…)` are both severable to a literal dict — the matcher stops being read, `coverage` and R1 go vacuous, suites green |
| M1 | MEDIUM | `blob_for`'s own-text exclusion — the rule R3 depends on — has no case and no mutation; removing it makes `R3_no_caller` vacuous for all 43 guards. The H1 extraction took one line out of this block and left this one |
| M2 | MEDIUM | The `_selftest-` exclusion is a NAME convention duplicated across two files; renaming the fixture prefix silently restores H1 with every suite green. A derived rule (caller evidence must be git-TRACKED) exists |
| M3 | MEDIUM | The argument for the six-label vocabulary is refutable: **10 of 11** plausible dangling declarations escape it, and a derived "ends in `:`/`-`/`—`" rule catches all 10 while passing all six shipped declarations |
| M4 | MEDIUM | `DECLARED_RENDER` has ONE slot for TWO meanings — *approved* and *current but disputed* (rc 3 / #211). The table's header calls every entry approved |
| M5 | MEDIUM | **Five live citations name `RECALL_MATCHER`, which round 7 M1 deleted** — including #209's stated FIX and #196's amendment; and `check-surface-recall.py:10` cites a comment line for the seam |
| M6 | MEDIUM | #207's headline contradicts its own body and the measured behaviour: the guard does **not** report agreement — it goes red naming the catch-all |
| M7 | MEDIUM | #207's size ratio is stale, and the replacement figure (~9–10x) is not derivable from any pairing. Derived: 13.3x / 21.8x / 12.1x. The row's deferral rests on this number |
| L1 | LOW | `DECLARED_RENDER[0] = ""`'s justification omits the second producer: `recall-llm.py:1133-1134` returns `OK` for a **paused** thread. A conjunction, in the one table that is a human judgement |
| L2 | LOW | `if len(caller_sources) < 3:` is a CANNOT-RUN refusal with no case — severable, 47/47 green |
| L3 | LOW | The new `SOURCE_SCOPE_CASES` count is padded by appending tuples to the list to make `len()` agree, and one half of the last ad-hoc assertion is vacuous |
| L4 | LOW | #212's mechanism is SIGKILL-only; a concurrent `git add -A` stages the same two files by a different route |

**Counts: 2 BLOCKING, 4 HIGH, 7 MEDIUM, 4 LOW.**

---

## DIRECT ANSWER TO THE TWO QUESTIONS ASKED

### Is there a FIFTH wiring instance?

**Yes — there are four more, and two of them are BLOCKING.** I severed 26 call sites and rule
applications across the three files. Every sever was applied in `t1`, the suite and the live run
measured, and the file restored. A sever "dies" when a **named** `[FAIL]` line appears.

| # | sever | suite | live | verdict |
|---|---|---|---|---|
| S1 | `problems = coverage(defined, DECLARED_RENDER)` → `[]` | 45/47, 2 named | rc 0 | **dies** (r8 B1's fix works) |
| S2 | `bad = undeclared_render(…)` → `[]` | 46/47, 1 named | rc 0 | dies |
| S3 | `for code, label in declaration_dangles(…)` → empty | 45/47, 2 named | rc 0 | dies |
| S4 | `render`'s stderr refusal | 46/47, 1 named | rc 0 | dies |
| S5 | `render`'s returncode refusal | 46/47, 1 named | rc 0 | dies |
| S6 | `render`'s `_env` scrub → `dict(os.environ)` | 46/47, 1 named | rc 0 | dies |
| **S7** | `defined = _defined_codes()` → literal dict | **47/47** | **rc 0** | ⛔ **SURVIVES — H4** |
| R1 | `problems = verdict(…)` → `[]` | 52/55, 3 named | rc 0 | dies |
| R2 | `dead = dead_arms(…)` → `[]` | 54/55, 1 named | rc 0 | dies |
| R3 | `handled = handled_codes(…)` → `set(codes)` | 53/55, 2 named | rc 0 | dies |
| R4 | the inert-hook refusal | 54/55, 1 named | rc 0 | dies |
| R5 | `observe`'s stderr refusal | 54/55, 1 named | rc 0 | dies |
| **R6** | `observe`'s `_env` scrub → `dict(os.environ)` | **55/55** | **rc 0** | ⛔ **SURVIVES — H1** |
| R7 | `observe`'s returncode refusal | 54/55, 1 named | rc 0 | dies |
| **R8** | `defined = defined_codes(_read_or_refuse(MATCHER))` → literal dict | **55/55** | **rc 0** | ⛔ **SURVIVES — H4** |
| **T1** | `violations = evaluate(texts, blob_for, manifest_stems)` → `[]` | **47/47** | **rc 0** | ⛔ **SURVIVES — B1** |
| T2 | the `_selftest-` exclusion removed | 45/47, 2 named | rc 0 | dies (r8 H1's *rule* works) |
| **T3** | `caller_sources = caller_source_paths(ROOT, ci_path)` → the pre-fix inline block | **47/47** | **rc 0** | ⛔ **SURVIVES — B2** |
| T4 | `caller_source_paths` ignores its `root` argument | 43/47, 4 named | rc 0 | dies |
| T5 | the exclusion becomes a SUBSTRING test | 46/47, 1 named | rc 0 | dies |
| **T6** | `if len(caller_sources) < 3:` → never | **47/47** | **rc 0** | ⛔ **SURVIVES — L2** |
| T7 | `out.extend(check_contract(…))` → bare call | 46/47, 1 named | rc 0 | dies |
| T8 | `out.extend(check_caller(…))` → bare call | 46/47, 1 named | rc 0 | dies |
| T9 | `out.extend(check_manifest(…))` → bare call | 43/47, 4 named | rc 0 | dies |
| T10 | `out.extend(widened_debt_drift(…))` → bare call | 46/47, 1 named | rc 0 | dies |
| **T11** | `blob_for` stops excluding the guard's OWN text | **47/47** | **rc 0** | ⛔ **SURVIVES — M1** |

⭐ **The shape of the result is the finding.** Everything inside `evaluate` is wired and has a case —
its docstring says exactly why, and it is right. Everything inside `main` that is **not** a rule
function call is unwired: the result of `evaluate`, the source collection, the own-text exclusion,
the minimum-sources refusal. The fold extracted *one* of those four lines (`caller_source_paths`)
and gave it four cases, and then consumed it at a call site no case can see. The same holds in both
of the other two files for the ONE operand `coverage`/`verdict` take that r8 B1's new case does not
pin: `defined`.

### Does the `_selftest-` exclusion fail in either direction?

**The ESCAPE direction: no, within the repo as it stands.** The only writer into the real
`.claude/hooks/` is `check-surface-recall.py` (`grep -n "HOOK.parent" scripts/*.py` → 5 hits, all in
that file), both names it writes begin `_selftest-` (`:320`, `:334`), and no suite anywhere writes a
transient file into `scripts/*.sh` or `scripts/*.py`, the other two globs
(`grep "ROOT / \"scripts\"" scripts/*.py | grep write_text` → nothing). Four concurrent
`--self-test` runs in one tree: all four 47/47, zero `[FAIL]`, zero residue. That part of the fold
holds, measured.

**The FALSE-EXCLUSION direction: not reachable today, but the rule is a name convention held in two
files, and that is M2.** `startswith` is the right half of the pair and `check-fixture-variation`
forced an adjacent negative for it (T5 dies on `my_selftest-helper.sh`). What nothing reconciles is
that `check-surface-recall.py:320` *chooses* the prefix and `check-ratchet-contract.py:186`
*hardcodes* it. Rename the fixture prefix in a consistent, locally-green edit and H1 returns with
all three suites green — the exclusion matches nothing and nothing says so. The derived form exists:
caller evidence must be a file **git tracks**. Measured — `git ls-files .claude | wc -l` = 37 and all
13 real hooks are listed, so the tracked-only rule passes the real population and excludes any
transient fixture under *any* name, in *any* of the three globs.

---

## BLOCKING

### B1 · The fifth wiring instance is `main`'s consumption of `evaluate`, and it voids the entire ratchet contract — R1, R2, R3 and R4 over all 43 guards — with the suite at 47/47

**What is wrong.** `scripts/check-ratchet-contract.py:957`:

```python
    violations = evaluate(texts, blob_for, manifest_stems)
```

`evaluate` is the only place the four rules are applied, and this is the only place its answer is
read. Every case in `self_test()` calls `evaluate` (or a rule) **directly**; nothing drives `main`.
So the one assignment that turns four rules into a verdict is unguarded, which is precisely the
sentence #213 was filed on.

**The reproduction I ran.** In `t1`, over a tree carrying a *real* violation (the two
`check-surface-recall.py` CI steps replaced with `run: true`, so the guard genuinely has no caller):

```
# control, before the sever — the known positive
$ python3 scripts/check-ratchet-contract.py
  scripts/check-surface-recall.py  [R3_no_caller]
summary: 1 violation(s), baseline 0
RATCHET FAILED: a ratchet was added or changed without following the contract.
rc=1

# sever: `violations = evaluate(texts, blob_for, manifest_stems)` ->
#        `evaluate(texts, blob_for, manifest_stems)` + `violations = []`
$ python3 scripts/check-ratchet-contract.py
ratchet contract OK
rc=0
$ python3 scripts/check-ratchet-contract.py --self-test
self-test: 47/47 passed
```

`evaluate` still runs. Its answer is thrown away. `BASELINE`, `MANIFEST_BASELINE`, the debt-drift
arm and the whole violation report are bypassed by `if not violations: print("ratchet contract OK");
return 0` (`:960-962`). **This is a bigger blast radius than any of the four instances #213
enumerates**: those switched off one rule in one guard; this switches off the gate that asks every
other guard whether it has a self-test, a caller, a manifest and no fail-open.

**No manifest entry targets it.** I searched all three manifests for the anchor text
(`json.dumps(entry)` containing `violations = evaluate`): zero hits. So `--mutate .` cannot find it
either.

**What would prove this wrong.** A sever of exactly that assignment making a **named** self-test
case red, or a manifest entry whose edit replaces `violations` with a constant and is killed by the
case it names.

---

### B2 · The sixth instance is round 8 H1's OWN fix: `caller_source_paths` is extracted, tested four ways, and then consumed at a call site no case can see — severing it restores H1's exact false green

**What is wrong.** The fix moved the collection out of `main` into a function
(`scripts/check-ratchet-contract.py:168-188`) and added six cases, which is right. `main` then reads
it at `:939`:

```python
    caller_sources: list[Path] = caller_source_paths(ROOT, ci_path)
```

Nothing asserts that line. The four lines the diff **deleted** —

```python
    caller_sources: list[Path] = [ci_path]
    caller_sources += sorted((ROOT / "scripts").glob("*.sh"))
    caller_sources += sorted((ROOT / ".claude" / "hooks").glob("*"))
    caller_sources += sorted((ROOT / "scripts").glob("*.py"))
```

— can be put straight back, with the function left in place and still called, and the whole fix
evaporates in silence.

**The reproduction I ran** (three probes in `t1`, CI steps for the guard removed in all three so a
real caller-less guard exists; probe A is the known positive):

| probe | fixture in `.claude/hooks/` | `main` uses | result |
|---|---|---|---|
| A | none | `caller_source_paths` | `[R3_no_caller]`, `summary: 1 violation(s)`, rc **1** |
| B | `_selftest-999999.sh` containing `python3 scripts/check-surface-recall.py --self-test` | `caller_source_paths` | `[R3_no_caller]`, `summary: 1 violation(s)`, rc **1** — the fix works |
| C | the same fixture | the pre-fix inline block (function still called, result discarded) | **`ratchet contract OK`, rc 0** — and `--self-test: 47/47 passed` |

So round 8 H1's false green is one mechanical line-move away, and the six cases written to prevent
it all stay green through the move. ⚠ This is the instance the dispatch brief predicted: *"the two
fixes I just wrote are themselves candidates."* It is also the fourth time in this fold that the
author of #213's warning has written #213's defect — the count in that row should be **six**, not
four.

**What would prove this wrong.** A named case that drives `main` (or an `ast` assertion over it) and
goes red when `caller_sources` is reassigned from anything but `caller_source_paths`.

---

## HIGH

### H1 · Round 8 H2's fix has no case and no mutation entry — reverting the `_env` scrub in `observe` leaves the suite at 55/55, and the allowlist is now hand-copied into two files

**What is wrong.** The fix is `scripts/check-rc-contract.py:295-296`:

```python
            _env = {k: v for k, v in os.environ.items()
                    if k in ("PATH", "HOME", "TMPDIR", "LANG")}
```

Its sibling at `scripts/check-surface-recall.py:139` has **both** halves of a falsifier: the case
`"an ambient PYTHONVERBOSE does not turn the gate into a refusal — round 7 L1"` (`:491-492`) and
manifest entry 13 (*"the environment is inherited wholesale again…"*). This copy has neither.

**The reproduction I ran.**

```
# sever: `_env = {k: v for k, v in os.environ.items() if k in (…)}` -> `_env = dict(os.environ)`
$ python3 scripts/check-rc-contract.py --self-test
55/55 self-test cases passed      rc=0
$ python3 scripts/check-rc-contract.py
rc contract OK …                  rc=0
```

Derived: `grep -n "PYTHONVERBOSE\|environ" scripts/check-rc-contract.py` returns three hits, all
inside the comment and the dict comprehension itself — **no case touches it**. Manifest search for
`os.environ.items` across all three manifests: one hit, in `check-surface-recall.json`, none in
`check-rc-contract.json` (15 entries, unchanged from the pre-fold count of 15).

⭐ **The sharper half.** Round 8 H2 *is* the drift class — the stderr refusal was copied into one
file and not the other — and the fix for it copies the scrub into the second file by hand. That
leaves two hand-written copies of `("PATH", "HOME", "TMPDIR", "LANG")` with nothing reconciling
them, which is this repo's `a-second-implementation-of-one-rule-drifts` (17 recorded instances) being
paid a second time to settle the first. One shared `_scrubbed_env()` helper — or
`check-vocabulary-collisions.py` being taught this pair — removes the class rather than the
instance.

**What would prove this wrong.** A named case in `check-rc-contract.py`'s suite that goes red when
`_env` becomes `dict(os.environ)`, plus a manifest entry for it.

---

### H2 · The scrub makes the ENVIRONMENT a staged proxy, which is round 7 B2's class one dimension over — an arm branching on a dropped variable renders a dangling `Detail:` in production while the guard reports CLEAN

**What is wrong.** `check-surface-recall.py`'s whole claim is fidelity. Its docstring, `:9-14`:

> ⭐ IT RUNS THE REAL HOOK, IN THE REAL REPO … **There is no fabricated world here to be unfaithful.**

And the hook, `.claude/hooks/surface-recall.sh:51-59`, gives the argument:

> A staged tree is a PROXY FOR THE REPO, and the set of things a shell script can read — **files,
> env, $HOME, tools on PATH** — is open, so the proxy has a boundary like every other.

The round 7 L1 fix then replaced the environment with a four-key fabrication. The comment's own
enumeration of the open set includes `env`. So the world is fabricated again, in the dimension the
argument names.

**The reproduction I ran** (`t2`, `<scratchpad>/envprobe.py`). A corpus-style rc-5 arm that shows the
detail only when `$USER` is set — a variable every real session and every GitHub runner has, and one
the allowlist drops:

```bash
  5) PAYLOAD="<the approved sentence>"
     if [ -n "${USER:-}" ]; then PAYLOAD="$PAYLOAD Detail: $OUT"; fi ;;
```

```
USER in this process env: 'kujinlee'
GUARD verdict (undeclared_render)  : []                      <- CLEAN
REAL-ENV render, repr of tail      : "this is not 'nothing applies'. Detail: \n"
ends with a dangling label         : True
```

That is backlog #201's reader-visible defect, verbatim, invisible to the guard that exists for it.
⚠ Note what does **not** save you: `set -u` (hook `:39`) aborts on a bare `$FOO` and the stderr
refusal would then catch it — but `${FOO:-}`, `[ -n "${FOO:-}" ]` and `${FOO+x}` do not trip `-u`,
and those are how anyone actually writes it.

**Why the tension is real and the fix is not "stop scrubbing".** Round 7 L1 is also real: a gate
whose verdict depends on the caller's environment gets switched off (#56). Both can be had — run the
probe **twice**, once scrubbed (that run decides the verdict, preserving L1) and once under the full
ambient environment, and report a **disagreement between the two renders** as its own finding:
*"this arm's output depends on the environment."* That needs no vocabulary, no enumeration of
variables, and it is the same mechanism the corpus already uses.

**What would prove this wrong.** A mechanism that asserts the shipped hook reads no environment
variable other than the four (an `ast`/lexical check over the `case` block would do it), or a second
probe under the inherited environment whose render is compared.

---

### H3 · The equality covers ONE POLARITY, so a hook that silently truncates the reader's detail ships at 47/47, 55/55 and both live rc=0

**What is wrong.** `DECLARED_RENDER` is, by its own header (`:50`), *"WHAT THE READER MUST SEE WHEN
THERE IS NO DETAIL"*, and `undeclared_render` probes with `render(rc, "", …)` (`:178`). The
with-detail render — the one a reader actually receives most of the time — is asserted by exactly
two things in the whole suite:

- `scripts/check-surface-recall.py:378-379`: `render(5, "WIDGET").rstrip().endswith("Detail: WIDGET")`
- `scripts/check-surface-recall.py:381-382`: `render(6, "X").startswith("recall-llm: a plan IS")`

A 6-character payload under an `endswith`, and a 22-character `startswith`. That is a suffix proxy
and a prefix proxy — the exact kind of rule this file's own thesis (`:54-62`) spends ten lines
rejecting, surviving in the polarity the equality does not reach.

**The reproduction I ran** (`t2`). Both detail-bearing arms keep their `[ -n "$OUT" ]` guard — so the
no-detail render stays byte-identical to the approved sentence — and truncate the detail:

```bash
     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: ${OUT:0:16}" ;;
```

```
rc 5 tail: "hing applies'. Detail: A-DETAIL-THAT-IS\n"
rc 6 tail: 'us is\nmissing. Detail: A-DETAIL-THAT-IS\n'
equality verdict (no-detail polarity): []

check-surface-recall.py --self-test  ->  47/47      live rc=0
check-rc-contract.py     --self-test  ->  55/55     live rc=0
```

The reader gets a mangled promise and four green gates. ⚠ **And the corpus does not cover this, even
though it contains a truncation arm.** `r6 B1a TRUNCATED below the old probe's length` (`:430-431`)
is caught because it drops the `-n` guard and therefore dangles under the no-detail probe — not
because truncation is detected. Keep the guard and truncation is invisible.

This is #209's single-polarity finding (`dead_arms` probes with `_PROBE` only) present in the rule
that **replaced** the one #209 is filed against, and it is not filed anywhere.

**The fix is the same mechanism, second polarity.** A `DECLARED_RENDER_WITH_DETAIL` table, probed
with one payload long enough to expose truncation and distinctive enough to expose transformation,
compared by equality. Hand-typed like the first table, for the same reason.

**What would prove this wrong.** An equality (not a prefix or suffix test) over the with-detail
render for every declared code, going red on the truncating hook above.

---

### H4 · `defined`'s call site is severable in BOTH guards — the matcher stops being read, `coverage` and R1 go vacuous, and the suites stay at 47/47 and 55/55

**What is wrong.** Round 8 B1's new case pins **one** operand of `coverage`. The other is `defined`,
and its producer is the only thing in either file that reads the matcher at all.

`scripts/check-surface-recall.py:270` and `scripts/check-rc-contract.py:441`:

```python
        defined = _defined_codes()
        defined = defined_codes(_read_or_refuse(MATCHER))
```

**The reproduction I ran.** Replace each with a literal dict holding today's six codes
(`{"OK": 0, "CANNOT_RUN": 2, "STALE_CACHE": 3, "BAD_RESPONSE": 4, "UNREADABLE_PLAN": 5,
"UNANSWERABLE": 6}`), leaving the real call in place and discarding its result:

```
check-surface-recall.py --self-test  ->  47/47   live rc=0
check-rc-contract.py     --self-test  ->  55/55   live rc=0
```

Both guards then answer the cross-file question — *"this is the one cross-file question this file
asks"* (`check-surface-recall.py:246-249`) — about a constant. Add a seventh code to
`recall-llm.py:116` and neither notices; that is #206's shape with the detector switched off rather
than merely narrow.

The existing cases cannot see it. `case("the matcher's real tuple is READ, not re-derived",
_defined_codes(), D)` (`:472`) calls the **function**. The r8 B1 wiring case drives `main` with rc 4
removed from `DECLARED_RENDER`, which produces the identical one-problem verdict against a hardcoded
`defined`. And `check-rc-contract`'s R1 wiring case stages its own matcher (`_main_over`, `:730-746`)
whose codes equal the literal.

**What would prove this wrong.** A wiring case that drives `main` over a matcher with a **seventh**
code and asserts the verdict names it — which also closes #206's detector question from the other
side.

---

## MEDIUM

### M1 · `blob_for`'s own-text exclusion is a documented, measured rule with no case and no mutation; removing it makes `R3_no_caller` vacuous for all 43 guards

`scripts/check-ratchet-contract.py:946-953` carries the reason in full (*"measured on
check-producer-enumeration.py, whose only three mentions anywhere in the repo are its own docstring
and its own print()"*) and then states the rule in one clause:

```python
            if p.is_file() and str(p.relative_to(ROOT)) != rel)
```

**The reproduction I ran** (`t1`, CI steps for `check-surface-recall.py` removed so a real
caller-less guard exists):

```
# control, exclusion present          ->  [R3_no_caller], summary: 1 violation(s)
# exclusion removed (`if p.is_file())`) ->  ratchet contract OK        rc=0
#                                          --self-test: 47/47 passed
```

Every guard then satisfies R3 out of its own usage docstring. ⚠ **The reason this belongs in round
8's review and not in a general audit:** the H1 fix extracted the *globs* from this exact block into
`caller_source_paths` and left this rule inline in `main`, where no case can reach it — the same
`separate-the-rule-from-the-fetch` complaint the fix's own docstring makes, one line below the line
it fixed.

**What would prove this wrong.** A case over the per-guard blob construction that goes red when a
guard's own text is included.

---

### M2 · The `_selftest-` exclusion is one convention in two files with nothing reconciling them, so renaming the fixture prefix silently restores round 8 H1

The writer chooses the name — `scripts/check-surface-recall.py:320`,
`path = HOOK.parent / f"_selftest-{_os.getpid()}.sh"` — and the reader hardcodes it,
`scripts/check-ratchet-contract.py:186`, `if not q.name.startswith("_selftest-")`. A consistent
local rename in the writer (name, marker, and the two residue globs at `:569`/`:571`) keeps that
file at 47/47 and the ratchet exclusion then matches nothing. Nothing is red, and the hazard is
exactly H1's.

**The derived alternative, measured.** Caller evidence must be a file `git` tracks.
`git ls-files .claude | wc -l` = 37, and all 13 real hooks appear (`git ls-files .claude/hooks` lists
`block-default-branch-push.sh` … `surface-recall.sh`); `git check-ignore .claude/hooks/surface-recall.sh`
exits 1, so they are tracked, not merely unignored. A transient fixture is untracked by construction,
under any name, in any of the three globs — so the rule generalises to `scripts/*.sh` and
`scripts/*.py` too, which the name test does not cover at all.

**What would prove this wrong.** A real hook that `git` does not track (which would break the
tracked-only rule), or a reconciliation that makes the two files share one constant.

---

### M3 · The ARGUMENT for the six-label vocabulary is refutable: 10 of 11 plausible dangling declarations escape it, and a derived rule catches all 10 while passing all six shipped declarations

The argument above `_DANGLING_LABELS` (`:190-195`) is that a vocabulary is safe here because the
*subject* is closed — six hand-written literals. That is true of the subject and false of the thing
the net depends on: the set of **spellings** a dangling promise can take is open, and it is open in
exactly the way that defeated the same list four times when its subject was shell renders.

**Measured** (`t2`, `declaration_dangles` called directly on each candidate):

| declared sentence ends with | six-label vocabulary | `rstrip()[-1] in ":-—"` |
|---|---|---|
| `Diagnostic:` `Cause:` `Error:` `Message:` `Output:` `Why:` `namely:` `see:` | MISSED (8 of 8) | CAUGHT (8 of 8) |
| `DETAIL:` (case) | MISSED | CAUGHT |
| `Detail —` (em dash, no colon) | MISSED | CAUGHT |
| `Detail` (no punctuation) | MISSED | missed |
| `Detail:` (control, in the list) | CAUGHT | CAUGHT |

**10 of 11 escape the vocabulary; the punctuation rule catches those 10** and is clean over the
shipped table — rc 5 ends `'nothing applies'.`, rc 6 ends `missing.`, and rcs 0/2/3/4 are empty
(guard the empty case, as the vocabulary already does implicitly).

So the second line is strictly weaker than an equally closed-form, derived alternative that was
available. The file's stated price for the vocabulary (*"if it misses a spelling the cost is that one
careless declaration edit goes unflagged"*) is the right accounting; the error is paying it when a
cheaper rule exists.

**What would prove this wrong.** A declared sentence that the vocabulary catches and the punctuation
rule does not, or a legitimate declaration that must end in a colon.

---

### M4 · `DECLARED_RENDER` has one slot and two meanings — *approved* and *current but disputed*

The table's header (`:50`) is **"WHAT THE READER MUST SEE"**, and the docstring calls each entry
*"the sentence a human approved"* (`:64-66`). Five of the six entries mean that. `3: ""` does not:
its own comment (`:93-98`) says

> ⚠ THAT MAKES THIS DECLARATION A LIVE DESIGN QUESTION RATHER THAN A SETTLED ONE … Declared as the
> hook behaves TODAY, deliberately

so the guard now pins, as approved, a behaviour the author argues is probably wrong — and #211 is
the record that it is disputed. A reader of the table cannot tell the two apart, and a future
editor reconciling the table against a changed hook will treat `3: ""` as a decision.

This repo owns the rule: `scripts/check-sentinel-meanings.py` refuses a nullable column whose
meaning carries a conjunction. Its subject is database columns, and #196's own corrected verdict
says nothing applies it to rc codes. The cheap fix is a second field (or a `DISPUTED` marker keyed by
code, printed in the guard's output line) so the pin and the dispute are distinguishable in the
table rather than only in a comment.

**What would prove this wrong.** #211 being resolved — then the table has one meaning again.

---

### M5 · Five live citations name `RECALL_MATCHER`, which round 7 M1 deleted, and two of them are a backlog row's stated FIX

`grep -rn "RECALL_MATCHER" --include=*.py --include=*.sh --include=*.md --include=*.json --include=*.yml`,
excluding `docs/reviews/`:

| site | text | status |
|---|---|---|
| `scripts/check-rc-contract.py:140` | "through the `RECALL_MATCHER` seam, so there is no fabricated world left to be unfaithful" | **stale** |
| `scripts/check-plan-code.py:1368` | the same sentence | **stale** |
| `scripts/check-fixture-variation.py:335` | "REAL hook IN THE REAL REPO through one `RECALL_MATCHER` seam" | **stale** |
| `docs/backlog.md:224` (#196 amendment) | "through a single `RECALL_MATCHER` seam (`surface-recall.sh:42`)" | **stale** |
| `docs/backlog.md:237` (#209) | **the stated fix**: "observe the REAL hook in the REAL repo via the `RECALL_MATCHER` seam (`surface-recall.sh:42`)" | **stale** |
| `.claude/hooks/surface-recall.sh:44` | "The first version read `${RECALL_MATCHER:-…}`" | correct — history |

The seam is argv: `.claude/hooks/surface-recall.sh:60`, `MATCHER="${1:-$REPO_ROOT/scripts/recall-llm.py}"`.
Line 42 is a comment (`# ⭐ THE ONE SEAM, AND IT EXISTS SO THIS HOOK CAN BE TESTED WHERE IT SHIPS.`),
and `scripts/check-surface-recall.py:10` cites `surface-recall.sh:42` for the ARGV seam as well — it
is 18 lines off and names a comment.

Why this is MEDIUM rather than LOW: #209's row is a *work instruction*, and whoever picks it up is
sent looking for an environment variable that round 7 M1 removed **because** an env var was the wrong
mechanism. Two of the stale sites are in files whose own rule is *quote the code, don't characterise
it*; #196's amendment opens with "THE MECHANISM, quoted rather than characterised".

**What would prove this wrong.** `RECALL_MATCHER` existing anywhere in the hook as live code.

---

### M6 · #207's headline contradicts its own body, and the measured behaviour is the body

The row's title: *"A forwarding `*)` catch-all in the hook makes R1 vacuous — every defined code
reads as handled, **and the guard then reports agreement it never checked**."* Its body then says the
loud half is fixed by the dead-arm cap.

**Measured** (`t1`, the shipped hook with `*) : ;;` replaced by a forwarding arm, driven through
`handled_codes` / `dead_arms` / `verdict`):

```
handled: [0, 2, 3, 4, 5, 6]   (R1 vacuous: True)
dead count: 250
problems: 1
  * the hook ACTS on 250 different codes the matcher cannot emit (e.g. [1, 7, 8, 9] … [254, 255])
    — at this volume the cause is a catch-all that FORWARDS rather than one that is silent
```

R1 is vacuous, as the row says — but the guard does **not** report agreement: it fails, with one
problem naming the cause. The headline is the half a reader scans. Fix the title to the body's own
framing (*the loud half is fixed; R1's vacuity is the quiet half*).

**What would prove this wrong.** A forwarding catch-all under which the guard exits 0.

---

### M7 · #207's size ratio is stale and its replacement is not derivable; the row's deferral rests on the number

The row records 61x being "corrected" to 16.6x — `382/23`, production code over hook code. Derived at
the frozen tree (split at the `─── the suite` marker; "code" = non-blank, non-`#` lines):

| subject | total | production | production code | suite | suite code |
|---|---|---|---|---|---|
| `scripts/check-rc-contract.py` | 787 | 474 | **307** | 313 | 219 |
| `scripts/check-surface-recall.py` | 584 | 302 | **194** | 282 | 195 |
| `.claude/hooks/surface-recall.sh` | 113 | — | **23** | — | — |
| its `case` block | 41 | — | **14** | — | — |

So `382` is now `307` (R3 left the file), and the rc-contract-alone ratio **fell to 13.3x** — while a
*second* guard for the same hook arrived, so the ratio over the whole subject **rose to 21.8x**
(`(307+194)/23`), or 35.8x against the 14 code lines of the `case` block, or 12.1x on total lines
(`1371/113`). ⚠ I could not reproduce the brief's "~9–10x" from any pairing of these numbers; the
nearest is 7.0x (`787/113`), which pairs one guard's total lines against the hook's total lines and
is the same category error as the original 61x. Since the row's deferral is argued *from* the ratio,
the number should be stated with its pairing, and the pairing that matters is the whole subject's:
**21.8x, and rising.**

**What would prove this wrong.** A different line-classification rule that yields ~9–10x, stated.

---

## LOW

**L1 · `DECLARED_RENDER[0] = ""`'s justification names one producer and there are two.** The comment
(`:82`) reads *"the whole payload is `[ -n "$OUT" ]`-guarded, so no matches means no message.
Correct."* The hook itself says otherwise at `:65-66`: *"a paused thread and a NONE answer are both a
silent rc=0"*, and the matcher confirms it — `scripts/recall-llm.py:1133-1134`:

```python
    if paused(sentinel_text):
        return OK  # a paused thread has no current step. Silence here is an answer, not a failure.
```

So rc 0's declared meaning is a conjunction, in the one table the file calls a human judgement, and
the dispatch brief is right that rc 0's silence *"has never been questioned by anyone"*. My
judgement: the silence is defensible (a pause is a deliberate choice, unlike a stale cache) — but the
justification is incomplete in exactly the way round 7 H3 found rc 3's to be, and the comment should
name both producers.

**L2 · `if len(caller_sources) < 3:` (`check-ratchet-contract.py:940`) has no case.** Severing it
leaves 47/47 and `ratchet contract OK`. It is a CANNOT-RUN refusal, and a refusal with no falsifier
is this repo's `a-test-that-cannot-fail`. Pre-existing, adjacent to the H1 edit, cheap to cover now
that `caller_source_paths` is a function.

**L3 · The new `SOURCE_SCOPE_CASES` count is padded, and one assertion half is vacuous.** The loop at
`check-ratchet-contract.py:857-864` runs four cases; the two ad-hoc checks that follow are then
counted by *appending tuples to the list* (`:866-867`, `:874-875`) so `len(SOURCE_SCOPE_CASES)` comes
out at 6 for the `total` sum at `:897`. It works, and `check-selftest-counts.py` verifies 47 by
running it — but the count is now a side effect of a list the loop no longer reads. Separately, the
second ad-hoc check asserts `"real.sh" in _names2` is false (`:881`) over a `real.sh` the loop
already `unlink()`ed at `:860`, so that half can never fire; the `"peer.sh" not in _names2` half is
what binds `root`, and T4 confirms it does.

**L4 · #212's mechanism is SIGKILL-only.** The row names *"a killed self-test"*. The fixture is also
reachable by a concurrent `git add -A` during a live suite — `git check-ignore
.claude/hooks/_selftest-1.sh` exits 1, so the path is not ignored, and this session's own memory
records that hazard costing twice in one night. Same two files, same repo, different route; the row
should name both so the fix (a `.gitignore` line, which covers both) is not scoped to the crash case.

---

## WHAT I TRIED TO BREAK AND COULD NOT

These are negatives with a known positive checked, not silence.

- **Concurrent suites.** Four simultaneous `check-surface-recall.py --self-test` runs in one tree:
  4 × 47/47, zero `[FAIL]`, zero residue. Round 7 M4's false red is genuinely closed by pid scoping
  plus the `${BASH_SOURCE[0]%.sh}.marker` derivation.
- **Peer guards reading the fixture.** With `_selftest-424242.sh` + `.marker` present in
  `t1/.claude/hooks/`, eight peer guards all behaved: `check-docs` 0, `check-guard-coverage` 0,
  `check-gate-falsifiability` 0, `check-ratchet-contract` 0, `check-fixture-variation` 0
  (744 parameters / 62 files), `check-vocabulary-collisions` 0, `check-producer-enumeration` 0.
  `check-selftest-counts` exited 1 — and that is **my** artefact, not a finding: it reports
  `check-plan-code.py --self-test exited 1`, whose three red cases all name
  `node_modules/typescript`, which my `rsync` excluded. The guard refused correctly.
- **`evaluate`'s internals.** T7–T10 all die on named cases. `evaluate`'s docstring claims its
  extraction was "for the wiring, not for tidiness" and that claim holds, measured.
- **The `_selftest-` exclusion escaping.** No writer other than `check-surface-recall.py` touches the
  real `.claude/hooks/`, and both of its names carry the prefix.
- **A surviving ambient channel through the four allowlisted keys.** I probed `HOME`
  (a `usercustomize.py` writing to stderr under a fake `HOME`), `LANG=xx_YY.UTF-8`, and
  `TMPDIR=/definitely/not/here`; all three left both guards at rc 0 and 47/47 / 55/55. ⚠ Treat the
  `HOME` probe as **NOT ESTABLISHED** rather than negative: the known positive did not fire either
  (`HOME=<fake> python3 -c 'pass'` printed nothing on python3.14), so the probe never demonstrated it
  could find anything. `LANG` and `TMPDIR` are honest negatives — bash accepted the invalid locale
  and `tempfile` fell back.
- **`BASH_ENV`,** which the brief flagged: dropping it is a hardening, not a break — non-interactive
  bash sources it, so its absence under the scrub closes a poisoning channel. It is open in
  **production**, where the hook runs with the session's full environment, but that is outside this
  fold's subject and H2 is the general form of the same observation.

---

## COULD NOT ESTABLISH

- **The fingerprint MATCHED**, at start and at end:
  `06c46d1e96c7f2501b471987d53446ca84cc2e4cedb969fea32516914b276a76`, identical to dispatch. No drift.
  #214's convention worked, and the published recipe is what let me say so — which is itself the
  answer to the Codex half's own "Could Not Establish".
- **I did not run `--mutate .`**, as instructed. So I cannot say whether the full sweep is green at
  this tree; I can say that **no manifest entry targets any of the six surviving anchors**
  (searched all three manifests for `violations = evaluate`, `caller_source_paths`,
  `defined = _defined_codes`, `defined_codes(_read_or_refuse`, `relative_to(ROOT)) != rel`,
  and `os.environ.items` in `check-rc-contract.json`) — so the sweep cannot find them either, and a
  green sweep is not evidence against B1, B2, H1, H4, M1 or L2.
- **Declared counts, verified by running them:** `check-surface-recall.py` 47/47,
  `check-rc-contract.py` 55/55, `check-ratchet-contract.py` 47/47, matching the three docstrings.
  `EXPECTED_MUTATIONS` parsed by `ast`: 57 files, sum **1169**, with
  `scripts/check-surface-recall.py` = 15, `scripts/check-rc-contract.py` = 15,
  `scripts/check-ratchet-contract.py` = 11; manifest lengths on disk 15 / 15 / 11. All agree.
  `check-selftest-counts.py` in the repo: rc 0, *"50 script(s) declare a count, every one verified by
  running it"*. ⚠ The Codex half's `1167`, `14` and `15` are a stale tree, not a disagreement.
- **#213's and #214's mechanisms, both verified.** #214: `scripts/codex-review.py:714` writes
  `"dirty": None if dirty is None else dict(dirty)`, and `reviewed_state()` (`:803-835`) fills it
  with `<mode> <blob-sha>` per uncommitted path — `docs/reviews/verdicts/recall-llm-r8-codex.verdict.json`
  holds 20 such entries plus `head`. The data to enforce the freeze is captured, as the row claims.
  #213: the four instances it enumerates are accurate, and the count is now **six** (B1, B2) —
  eight if H4's two are counted separately.
- **#206, #209, #210 re-verified, all sound.** #206: `_RC_NAMES.issubset(set(names))` at
  `check-rc-contract.py:182` reads one tuple assignment only, and the matcher's is
  `recall-llm.py:116` — a seventh code assigned on its own line is invisible. #209: `dead_arms`
  observes with `_PROBE` only (`:372`) through `_stub_tree`; **and it now has a third shape**, the
  scrubbed environment (H2), which the row should absorb. #210: `rc, out = run_suite(d, fname)` at
  `check-plan-code.py:1693` with `fname = mut.get("file", "")` at `:1654` — the schema really does
  couple target and suite.
- **#207, #196 and #212 need amendment** (M6, M5, L4). #208 and #211 I did not attack; #211 I
  re-judged and agree it is a live question, with M4 as the additional structural point.

---

NOT CONVERGED

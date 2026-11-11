# memory-index-budget — round 3, CLAUDE half

Primary subject: `715e8ae3` ("The fix became the next finding four times running, so this is a
REDESIGN and a thrashing determination, not a fifth patch") on branch `baseline-surveys`, plus the
uncommitted corrections to `docs/reviews/architecture-review-2026-10-19-memory-index-budget-thrashing.md`
as they stand on disk.

Per this round's contract, findings are **FILED, NOT FIXED**. I changed no code. My only write is
this file.

⛔ **THE CODEX HALF RAN FIRST AND I READ IT BEFORE STARTING.** Its six findings — mutation 29
(facts swapped between message positions), `_shows` accepting `-414`/`414.5`, equal-valued facts
concealing each other, hook root discovery accepting a nearby guard, the four-way count ambiguity,
and the overstated causal table — are **not re-filed here**. Where I extend one I say so and name it.

---

## Instrument, all of it run

- The guard live: **rc 0, 22,238 characters**. Suite **59/59**. Hook self-test **12/12**.
- The **real harness** over a staged `HARNESS_TREE` (`scripts`, `supabase`, `docs`,
  `node_modules/typescript`, `.claude/hooks`, `.github/workflows`, `.agents/skills`), manifests
  pruned to this one file and `EXPECTED_MUTATIONS` pinned to it:
  `OK — 1 file(s), 28 mutation(s), 28 killed, 28 attributed to the case each names, 0 survivor(s)`,
  **green control and re-control**. This reproduces the Codex half's harness result independently.
- **Fourteen mutations of my own** against that proved-green control; **six survive all 59 cases**.
- The same staged tree re-run with the index pushed over budget, and again with the suite's oracle
  severed — two separate `--mutate .` runs, to measure what the harness does in each state.
- **Both interpreters**: the dev machine's 3.14.4 and **CI's pinned 3.12** (`/usr/local/bin/python3.12`,
  3.12.9), over all **69** scripts in `scripts/` that expose a `--self-test`.
- **The live CI run for PR #380** (`39375344140`), job logs read directly, not inferred.
- `check-selftest-counts.py` (54 declared counts, verified by running each), the 1,573-entry
  manifest corpus, `check-plan-code.py`'s control-failure path, `check-review-recorded.py`'s
  exemption rules, `check-ratchet-contract.py`'s guard population.

**NOT RUN, stated loudly.** I did not run `--mutate .` over all 63 manifested files (1,573 entries);
my scoped run is a claim about this manifest only. I did not run a controlled producer-boundary
experiment, so the counting question stays where r3 CODEX left it. I did not observe the hook's
advisory entering a consuming session — that measurement remains **NOT RUN**, not a pass, exactly as
the Codex half said.

⚠ **ONE NEAR-MISS, RECORDED BECAUSE THE METHOD IS THE POINT.** My first 3.12 sweep grepped stderr for
`TypeError|SyntaxError|AttributeError` and reported **three** broken guards. Two were false: the
strings matched *case names* in `check-ci-watched.py` and `check-review-rounds.py`
(`"...a NON-NUMERIC schema is a CANNOT RUN too, not a TypeError out of the era gate"`), not
tracebacks — `measure-the-population-the-code-actually-sees`. Re-run on **exit codes**, 2 of 69
diverge. The second, `scripts/page_chrome.py` (222/223 on my 3.12.9), is **also not a finding**:
`page_chrome self-test` is a CI step at `ci.yml:509`, the failing case exists on `master`, and
master's CI is **green** at `11c1d5db` on the runner's 3.12.15. My local red there is my machine.
**The class is 1 of 69, not 3 and not 2** — and the one is below.

---

> **The redesign is the right move and most of it holds: the facts/render split is sound, all 28
> manifest mutations kill and attribute over a green control, the exact-dict cases genuinely close
> the field-granularity class that four iterations could not, and the author's corrections to their
> own document are real corrections rather than rewording. But the commit does not run on the
> interpreter CI pins. `Path.read_text(newline="")` requires Python 3.13; `ci.yml` pins 3.12; the
> guard tracebacks on every CI invocation, `verify` dies 45 steps early, and all eight mutation
> shards report NOT MEASURED over the entire 1,573-entry manifest. That is live, it is in the run
> log for PR #380, and it was introduced by the round-2 fix for the CRLF under-count — which makes
> it a fifth instance of the shape this document was written to stop, and the first one that is an
> outage rather than a surviving mutant. Beneath it, the loop's invariant is one-directional: it
> proves every fact reaches the message and never that every number in the message is a fact, so
> `render` can add or recompute a number freely at 59/59.**

---

## BLOCKING — `index_chars` calls a Python 3.13+ API; CI pins 3.12, so the guard does not run in CI

`scripts/check-memory-index-budget.py:248`

```python
        return len(path.read_text(encoding="utf-8", newline=""))
```

The `newline` parameter was **added to `pathlib.Path.read_text` in Python 3.13**. Measured, both
signatures on this machine:

```
3.12: (self, encoding=None, errors=None)
3.14: (self, encoding=None, errors=None, newline=None)
```

`TypeError` is not in `except (OSError, UnicodeDecodeError)`, so it escapes as a traceback rather
than the CANNOT RUN this guard advertises.

**This is not a local artefact. It is in the live CI log**, run `39375344140`, job `118472120600`,
step *Memory index injection budget*, on `pythonLocation: /opt/hostedtoolcache/Python/3.12.15/x64`:

```
Traceback (most recent call last):
  File ".../scripts/check-memory-index-budget.py", line 617, in <module>
    sys.exit(main(sys.argv[1:]))
  File ".../scripts/check-memory-index-budget.py", line 290, in main
    rc, msg = budget_verdict(index_chars(index), limit, shown)
  File ".../scripts/check-memory-index-budget.py", line 248, in index_chars
    return len(path.read_text(encoding="utf-8", newline=""))
TypeError: Path.read_text() got an unexpected keyword argument 'newline'
```

**Blast radius, measured, not reasoned:**

| Consequence | Evidence |
|---|---|
| `verify` dies at the guard | `ci.yml:269` is in job `verify`, `python-version: '3.12'` at `:80`; the shell is `bash -e` |
| **45 of `verify`'s 69 steps never run** | counted from `ci.yml`: the guard is step 24; everything after it — the rc-contract gate, the ratchet contract, the reader-sentences guard, the explainer-delivery gate — is NOT RUN, presenting as one job failure |
| **All 8 mutation shards report NOT MEASURED** | job `118472120352`: `✗ CANNOT RUN — control run of scripts/check-memory-index-budget.py did not prove the suite works (exit 1) BEFORE any mutation was applied` → `NOT MEASURED — the mutation harness produced no coverage verdict` |
| The whole manifest, not just this file | `check-plan-code.py:1958` `targets = sorted({m["file"] for m in shard_muts})`, and `:1990` `if report: return False, report, NotMeasured...` — **one red control returns `NotMeasured` for the entire run**, all 1,573 entries |

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `/usr/local/bin/python3.12 scripts/check-memory-index-budget.py`
exits 0 or 1 with a verdict line instead of a traceback. Today it tracebacks at `RC=1`.

**It is a fifth instance of the thrashing shape, and the worst one.** The `newline=""` argument is
r2 CODEX #4's fix for the CRLF under-count — the round-2 repair became the round-3 finding, one
round later, as an outage. Manifest entry 16 pins the fix (`', newline=""' → ''`), so the manifest
now mandates the 3.13-only spelling.

**The repo already had the 3.12-compatible mechanism, mutation-pinned, under a name this fix did not
search.** `scripts/check-doc-citations.py:548`:

```python
        raw = target.read_bytes().decode("utf-8", errors="replace")
```

whose comment at `:536` reads *"⛔ `read_bytes().decode(...)`, NEVER `read_text(...)` — r4-codex H2,
AND THIS IS THE SECOND"*, and whose mutation anchor pins *"HOW THE BYTES ARE OBTAINED"*. Measured
on 3.12 against this guard's own CRLF fixture (`b"x\r\n" * 9`): `read_text()` → **18**,
`read_bytes().decode("utf-8")` → **27** — identical to what `newline=""` gives on 3.14, and
`UnicodeDecodeError` is already in the handler. This is `a-second-implementation-of-one-rule-drifts`
and `it-already-exists-under-a-name-i-didnt-search`, and the second implementation is the broken one.

⚠ **What caught it and what did not.** `check-python-pin.py` enforces that every job *pins* an
interpreter and that the pin *took effect* — both true here. Nothing asks whether the guards *run*
on the pin. The divergence is 1 of 69 scripts, so this is an instance, not a class, and the class
check is above.

---

## HIGH 1 — `path.is_file()` sits OUTSIDE the handler, and raises on CI's interpreter

`scripts/check-memory-index-budget.py:240`

```python
    if not path.is_file():
        return None
    try:
```

Measured, same path (`/tmp/` + 5,000 `x` + `.md`):

```
3.12 is_file() RAISED OSError 63        # ENAMETOOLONG
3.14 is_file() -> False
```

On 3.14 the guard returns CANNOT RUN at rc 2, correctly. On **3.12, the pinned interpreter**,
`index_chars` raises `OSError` from line 240 — before the `try` — and `main([], index=long, limit=1000)`
raises instead of returning 2. The case *"a present-but-unreadable index is CANNOT RUN, not a
traceback"* is therefore **interpreter-dependent**, and it passes on the only interpreter the author
ran.

This repo has already paid for this exact divergence and written it down.
`scripts/check-python-pin.py:18-19`:

> *"(ENAMETOOLONG) for an over-long path — **except on Python 3.13+, which widened the errno set it
> swallows**. The dev machine ran 3.14 and got `False`; the runner raised"*

**OBSERVATION THAT WOULD MAKE THIS FAIL:** on 3.12, `main([], index=<over-long path>, limit=1000)`
returns `2`. It raises.

Masked today only because BLOCKING kills the script two lines later. Severity is High rather than
Blocking because the input class is not reachable through `main`'s default `INDEX`.

---

## HIGH 2 — the live-index case couples the whole repo's mutation coverage to the length of a docs file

`scripts/check-memory-index-budget.py:607-610`

```python
    live = index_chars(INDEX)
    check("the LIVE index is measurable and within budget "
          f"(it is {live if live is not None else 'UNREADABLE'} bytes)",
          budget_verdict(live, LIMIT_CHARS)[0], OK)
```

This case's greenness is a function of a **mutable tracked file**, not of the guard's logic.
Measured on the staged tree, by appending filler rows to the staged copy of `MEMORY.md` until it
read 26,439 characters — i.e. the state this guard exists to detect:

```
GUARD        rc=1  OVER BUDGET — ... 26,439 CHARACTERS ...        (correct, by design)
SELF-TEST    rc=1  [FAIL] the LIVE index is measurable and within budget (it is 26439 bytes)
                   self-test: 58/59 cases passed
--mutate .   rc=1  ✗ CANNOT RUN — control run ... did not prove the suite works (exit 1)
                   NOT MEASURED — the mutation harness produced no coverage verdict.
```

So **the moment the guard fires, its own 28 mutations stop being measurable** — and by
`check-plan-code.py:1958` and `:1990` (quoted under BLOCKING), so do the other 1,545 entries in the
run. A docs file's length decides whether the repo has a mutation-coverage verdict.

**And the case buys nothing.** `ci.yml:269-270` runs `python3 scripts/check-memory-index-budget.py`
— which asserts exactly this, on the same tree, in the same job, **three lines above** the self-test
step at `:272`. The case is redundant with its own neighbour and is the sole source of the coupling.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** with `docs/memory/MEMORY.md` over `LIMIT_CHARS`,
`python3 scripts/check-plan-code.py --mutate .` still produces a coverage verdict. It produces
`NOT MEASURED`.

This is `separate-the-rule-from-the-fetch` — the rule (does `budget_verdict` classify correctly?) is
fully witnessed by the synthetic fixtures; only the fetch needs the live file, and the fetch already
has its own CI step.

---

## MEDIUM 1 — the loop is ONE-DIRECTIONAL: every fact reaches the message, but every number in the message need not be a fact

`scripts/check-memory-index-budget.py:387-392`

```python
    for _f in (OVER_F, WARN_F, OK_F, budget_facts(None, 8191, LBL), budget_facts(0, 8191, LBL)):
        _msg = render(_f)
        _vals = [_shown(v) for k, v in _f.items() if k not in ("rc", "state")]
        _vacuous += [f"{_f['state']}: {d}" for d in _vacuous_pairs(_vals)]
        _missing += [f"{_f['state']}.{k}={_shown(v)!r}" for k, v in _f.items()
                     if k not in ("rc", "state") and not _shows(_msg, _shown(v))]
```

The quantifier runs facts → message. Nothing runs message → facts. `render`'s docstring at `:161`
claims the opposite property:

> *"Every value comes FROM `f`, never recomputed. ⚠ Recomputing anything here would re-open the
> defect the split closes"*

That is a prose constraint with no witness. **Two survivor classes, measured over a proved-green
control:**

**(a) ADD — `render` gains a number that is not a fact.** Three independent variants, one per arm,
each **SURVIVED 59/59**. The OK-arm variant, run against the real index:

```
ok — docs/memory/MEMORY.md is 22,238 characters, 2,747 under (96% used) the harness's
24,985-character limit, so nothing is being dropped.
```

22,238 / 24,985 is **89%**, and the warn band starts at 90%. The reader is told the index is past
the warn threshold when it is below it, and no fact moved, so neither `_missing`, `_vacuous_pairs`
nor the exact-dict cases can object.

**(b) RECOMPUTE — `render` re-derives a fact instead of reading it.** At `:185`, replacing
`({f['percent']}% of budget)` with `({100 * f['chars'] // f['limit']}% of budget)` **SURVIVES 59/59**.
Output-identical today, so this is not a behaviour defect — it is the exact guarantee the docstring
asserts, unwitnessed. `a-sever-substitutes-todays-value` is the shape: a second expression of one
rule agrees until `budget_facts` changes how it computes, and then the cases pass while the reader
sees the other number.

**This GENERALISES r3 CODEX #1** rather than restating it. The position swap moves facts between
roles; (a) adds a non-fact; (b) duplicates the defining expression. All three are the same missing
invariant — **a bijection between the numbers in the message and the facts, each in its own role** —
and only the swap has been named.

⚠ **The mechanism that could have constrained this direction was deleted this round.** The suite's
comment at `:313-318` records removing the parsed-field helper because *"a superseded mechanism kept
'just in case' is one more thing to be wrong"*. That reasoning is sound for facts → message, where
the exact-dict cases superseded it. It is not sound for message → facts, where nothing replaced it.
The fix kind here is parsing in the **other direction**, which is not the mechanism that was retired.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** adding a numeric literal or a recomputed expression to
any arm of `render` turns a case red. Measured, four such edits, `59/59` each time.

---

## MEDIUM 2 — "covered by construction" is true of a FIELD and false of a STATE

`budget_facts`'s docstring (`:122`) and the architecture review's item 2 both claim:

> *"A new field is then covered by construction rather than by remembering to add a case."*

The loop's fixture tuple at `:387` is **hand-written and enumerates four states**. A fifth state is
covered by nothing. Measured: adding a `dire` band above `2 * limit` with a new `multiple` fact, and
rendering that fact **wrong (+40)**:

```
[SURVIVED] rc=0  self-test: 59/59 cases passed

FACTS : {'rc': 1, 'state': 'dire', 'label': 'docs/memory/MEMORY.md', 'chars': 75000,
         'limit': 24985, 'overage': 50015, 'multiple': 3}
READER: OVER BUDGET — docs/memory/MEMORY.md is 75,000 CHARACTERS, more than 43 times the
        24,985-character limit. REMEDY: move rows to docs/memory/slice-history.md.
```

75,000 / 24,985 is **3.0**. The message says 43. An entire arm and an entire new fact are
unwitnessed, at 59/59.

The claim should read *"a field added to a COVERED STATE is covered by construction; a new state is
not, and adding one requires adding it to the loop's tuple."* As written it is the kind of
coverage claim that stops the next person from checking.

⚠ **This is the thrashing shape one granularity out.** Four iterations ran at FIELD granularity; the
redesign closes field granularity and moves the open edge to STATE granularity. That is backlog
#154's recorded pattern — *"EIGHT rounds, each a NEW GRANULARITY (line→node→document→key-depth)"* —
and it is worth naming in the review document precisely because the document claims the class is
narrowed rather than relocated.

⚠ I checked the converse and it holds: adding a field to the three measured states via `common`
(`"warn_at": warn_at`) reddens **5** cases. r3 CODEX's conclusion that the `("rc", "state")`
exclusion yields no bypass reproduces.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** a fifth state with its own render arm turns a case red.
It does not.

---

## MEDIUM 3 — the hook's only mechanical cover has NO CALLER

`.claude/hooks/check-memory-index-budget.sh:40` declares `--self-test   # 12 cases`, and it passes
**12/12**. Nothing runs it.

- Zero invocations of any `.sh --self-test` in `.github/workflows/*.yml` (43 `--self-test` steps in
  `ci.yml`, all `.py`).
- `check-ratchet-contract.py:116` — `GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")` — so
  the rule *"every guard ON DISK has a `--self-test` … **and a caller** — or a written `NO-CALLER:`
  reason"* structurally cannot reach a `.sh`. `.claude/hooks/` is globbed by that script only as
  **caller evidence** for `.py` guards (`:192`), never as a population.

The architecture review's caveat section says the 12-case self-test *"is the only mechanical cover,
which is better than its sibling `surface-recall.sh` (no self-test, no mutations) and still a gap."*
Cover that nothing executes is not cover, and `a-declaration-is-not-the-act` is the entry for it. The
comparison to `surface-recall.sh` is also weaker than stated: against a suite nobody runs, *"has a
self-test"* and *"has no self-test"* differ only in what a reader believes.

⚠ The repo's own memory says a caveat headed *"stated rather than hidden"* that is wrong is worse
than none (`a-bound-enumerates-what-is-witnessed`). This is that shape: the gap is disclosed and the
disclosure overstates the cover.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `grep -rn -- "--self-test" .github/workflows/ | grep '\.sh'`
returns a line. It returns none.

---

## MEDIUM 4 — the CORRECTED thrashing determination is still overstated, on a different axis from r3 CODEX #6

I agree with r3 CODEX #6 and with the author's adoption of it. The question the brief asks is whether
the **replacement** claim holds. It does not, for a reason the correction did not address.

The arming condition, quoted in the document's own opening:

> *"It fires when **two consecutive rounds carry findings caused by the previous round's own fix, in
> one component**"*

The corrected text then rests the determination here:

> *"The causally strongest link is **r2 CODEX #1 → r2 CLAUDE H2's float-prefix finding**"*

⛔ **Both halves of that link are in round 2.** r2 CODEX #1 is a round-2 finding; its repair is a
within-round-2 fold; r2 CLAUDE H2 attacks that fold. That is *a finding caused by a fix made in the
same round*, not *by the previous round's fix*. The same is true of the second instance the document
adds — H3's symlink regression, caused by *"r2 CODEX finding 3's fix"*, also intra-round-2.

Read strictly against the table, the chain yields **exactly one** cross-round instance:
r1 CLAUDE N1's fix → r2 CODEX #1. One round carrying such a finding, not two consecutive.

**The asymmetry is the finding.** The document uses the STRICT reading of "round" to escape an
obligation — *"Four rounds were not reached: this is rounds 1 and 2, four halves"*, so the
oblige-asking clause does not fire — and the LOOSE reading of "round" (halves and internal folds as
links) to satisfy the arming clause. A term cannot mean halves in one paragraph and rounds in the
next, in the same document, in the direction that is convenient each time.

⚠ **And this is the second time this document has been corrected in the same direction.** r3 CODEX
#6 caught an inflated count; this is an inflated unit. `an-inference-stated-as-measured` names the
tell, and the document's own warning — *"the arming condition deserves the stricter reading, not the
one that makes the case easier"* — is the sentence this finding applies to the paragraph it sits in.

**⛔ BUT THE CONDITION IS NOW GENUINELY SATISFIED, BY EVIDENCE THE DOCUMENT COULD NOT HAVE HAD.** My
BLOCKING is a round-3 finding caused by the round-2 fix (r2 CODEX #4's `newline=""`). With it:

| link | rounds | cross-round? |
|---|---|---|
| r1 CLAUDE N1's fix → r2 CODEX #1 | 1 → 2 | ✅ |
| r2 CODEX #4's fix → r3 (BLOCKING, CI outage) | 2 → 3 | ✅ |

**Two consecutive rounds, each carrying a finding caused by the previous round's own fix, in one
component.** The determination is right; the evidence it cites is not what makes it right. The honest
repair is to say the arming condition fired on the r1→r2 link and was confirmed by the r2→r3 link,
and to demote the intra-round links to what they are: fixes that immediately needed fixing, which is
the same disease and not this clause.

**And it is not a prose floor.** I tested that directly rather than asserting it: every finding in
the chain, mine included, is a *runnable* observation over a proved-green control or a CI log. A
prose floor produces defensible wording changes; this produced a traceback in CI.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** a reading under which r2 CODEX #1 and r2 CLAUDE H2 are in
different rounds, that is also consistent with the document's own "four rounds were not reached".
I could not construct one.

---

## LOW 1 — the suite's oracle has no local witness; the harness is the witness, and I measured it working

`scripts/check-memory-index-budget.py:298-305`. One edit — `fail += 1` → `ok += 1` inside `check` —
and **all 28 manifest mutations survive while the suite prints `59/59 cases passed`**, measured
one by one.

The redesign applies the known-positive discipline one level down and says why
(`_vacuous_pairs` at `:354`, *"Without this the rule above is correct and UNEXERCISED"*). The same
sentence is true of `check`, and it was not applied there.

⚠ **I graded this down after measuring, and the measurement is the reason.** Running `--mutate .`
with the oracle severed:

```
FAILED — 1 file(s), 28 mutation(s), 0 killed, 0 attributed, 28 survivor(s)
```

So the harness catches it loudly, rc=1, and `--mutate .` runs in CI. It is **not** a silent hole, and
grading it High would have been inflation. The residual cost is diagnostic: a **single** broken
oracle presents as **28 separate findings**, and `a-harness-cannot-read-a-cause-from-a-childs-text`
is the entry for what that costs a reader. One case asserting `check` on a deliberately wrong pair
would make the cause local. No sibling guard does this either, so if it is worth fixing it belongs
with `check-ratchet-contract.py` as a new rule over the whole family, not here alone.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** severing `check`'s failure counter turns a case red
*within this suite*. It does not; only the harness sees it.

---

## LOW 2 — the unit the file exists to correct is still wrong in five reader-facing names, one of them pinned by the manifest

The central correction of this guard is bytes → characters, and the docstring calls it a class, not
an instance: *"the same unit error as H1, which makes it a CLASS and not an instance. Both are now
characters."* Five names say otherwise:

| site | text | measures |
|---|---|---|
| `:325` | `"one byte PAST the limit is over"` | characters |
| `:328` | `"one byte BELOW the warn threshold does not warn"` | characters |
| `:543` | `"main() fails a file ONE BYTE over, measured end to end"` | characters |
| `:608` | `f"(it is {live ...} bytes)"` | characters |
| manifest entry 9 | `"main() under-reports the size by one byte…"` | characters |

`:608` is the one a human actually reads: it is the only place the suite reports a live measurement,
and under HIGH 2 it is what a failing CI prints —
`[FAIL] the LIVE index is measurable and within budget (it is 26439 bytes)` — calling characters
bytes, unformatted, in the failure message of the guard whose subject is that distinction.

⚠ **Correcting this is coupled, which is why it is worth filing rather than leaving.** Manifest
entry 9's `expect` pins the case name at `:543` verbatim, so renaming it requires a lockstep manifest
edit or the mutation stops attributing — `a-guard-can-mandate-the-duplication-it-audits`, the shape
this file has already paid for once with the inverted bytes entry.

⚠ Related, and the reason the names are easy to misread as correct: the end-to-end boundary fixtures
are **ASCII** (`at_limit.write_bytes(b"x" * 1000)`, `over_by_one` 1001), so bytes and characters are
equal in them. Those cases are unit-blind by construction; the only unit witness in the suite is the
4-character glyph file at `:455`.

**OBSERVATION THAT WOULD MAKE THIS FAIL:** `grep -n "byte" scripts/check-memory-index-budget.py`
returns only sites genuinely about bytes. Five are about characters.

---

## The question the brief put to me directly: is FILE-DON'T-FIX a sound exit, or a loophole?

**The mechanism works as described, and I verified the premise rather than accepting it.**
`check-review-recorded.py` treats `docs/` as prose (`:141`, *"the default is GUARDED"* with `docs/`
exempted; `:284` names `docs/backlog.md` explicitly as prose a gate merely READS). So a round that
writes a review file and files backlog rows changes no guarded path, and the gate clears.

**It is sound process, for one specific reason.** Under fold-then-review, every round's fix is code
no round has seen, so the gate has no fixed point — the author's framing is right. Filing converts
*"findings → fix → unreviewed code"* into *"findings → a visible record over a tree a round actually
read"*, which is what the gate is asking for. The findings become work with an owner instead of
patches with no reviewer. For MEDIUM 1–4 and LOW 1–2 above, filing is the correct disposition and I
recommend it.

**It becomes a loophole at one identifiable boundary, and this tree is past it.** The test I would
write down is: **does the finding change what a green CI would say?**

- If CI would be green with the finding filed, filing defers real work and the branch is honest.
- If **CI is already red because of the finding**, filing is not a deferral — it is declining a gate
  that has already fired. `verify` fails and eight mutation shards report NOT MEASURED on PR #380
  right now. No amount of backlog filing turns that into a tree anyone can merge, and
  `check-review-recorded` going green says nothing about it, because it asks *"did a round see this
  tree"*, never *"is this tree good"* — `a-check-result-is-not-the-claim`.

So: **sound process, applied here to a tree where one finding is outside its scope.** The BLOCKING is
not work to carry; it is the branch not building, on the pinned interpreter, measured in the run log.
File the other eight. Fix that one, and let round 4 be the round that reviews the fix — which is the
normal cost of the fold-then-review shape, not an argument against the exit.

⚠ One precedent worth naming rather than leaving implicit: PR #378 took this path and merged NOT
CONVERGED with a Blocking filed. That is the owner's call to make and it was made. The risk is that
the second use establishes it as the default, and the difference between *"the owner chose to carry a
Blocking"* and *"the process absorbs Blockings"* is a sentence nobody writes down.

---

## What I attacked and did NOT find

Recorded so the next round does not re-spend it, and so the bound is the one I witnessed:

- **The `("rc", "state")` exclusion** — no bypass. Adding a fact to `common` reddens 5 cases.
  Reproduces r3 CODEX's null result.
- **`_shown` / `_shows` formatting divergence** — dropping the thousands separator from a rendered
  fact is caught (`EVERY fact reaches…` reddens).
- **Dropping the label from one arm** — caught.
- **Swapping `limit` and `headroom` in the OK arm** — caught by two cases. r3 CODEX's mutation 29
  works in the WARN arm because both operands there are facts of equal standing; the OK arm's
  `limit` is read into a local at `:176` (`limit = f["limit"]`) and the swap breaks an independent
  case.
- **`render`'s unguarded final arm** — an unknown state does render as the reassuring `ok` text, but
  every route I could construct to one reddens the exact-dict cases first.
- **`INDEX_LABEL` hardcoded back to the literal** — survives, as the comment at `:95-99` already
  says it does, and the stated reason (the paired INDEX mutation is what catches it) **reproduces**:
  with both edits applied, manifest entry 8 still reddens. Correctly documented, not a finding.
- **R5's bounds** — `1,573` manifest entries, **100% `.py`**, verified by counting. The docstring's
  statements that the unit is measured and the algorithm is not, and that the hook is outside the
  mutation population, are accurate as written.
- **The hook's JSON channel** — I did not duplicate r3 CODEX's serialisation work and have no
  independent finding there.

---

## NOT CONVERGED

One Blocking, two High, four Medium, two Low. The Blocking is a live CI failure on the pinned
interpreter, reproduced from the run log for PR #380 rather than inferred, and it was introduced by
the previous round's fix — which both confirms the thrashing determination the document makes and
refutes the part of it that treats the class as answered.

The redesign is the right response and should not be reverted. The facts/render split did what it was
built to do at field granularity, and the author's public corrections of their own numbers — three
times in this slice, including adopting a reviewer's refutation over defending their own table — are
the behaviour this process exists to produce. What remains is that the suite proves the message
*contains* the facts and never that the message *is* the facts, that the claim about what is covered
by construction is wider than what is covered, and that none of it ran on the interpreter that
matters.

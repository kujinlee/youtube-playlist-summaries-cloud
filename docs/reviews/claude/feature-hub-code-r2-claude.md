<!-- claude half of code round 2 -->

# Code review round 2 — Claude half

**Subject:** commit `8df15f6f` only (5 files, 166 insertions), the fix wave for
`docs/reviews/coordinator/feature-hub-code-r1-codex.md`. Branch `feature-hub-spec`, HEAD `c84374c8`.
Round 1 covered the rest of the branch.

**Verdict: safe to merge.** All three round-1 findings are ADDRESSED, every mechanical claim the
commit makes about itself is true, and the three defects I found are comment/message defects, not
behaviour defects. None of them changes what the gate accepts or refuses.

---

## Round-1 findings — verdicts

| r1 finding | Verdict | How I checked |
|---|---|---|
| **Blocking** — `>`/`<!--`/`#` exempted, so a status token rides into a node unread | **ADDRESSED** | `scripts/check-features.py:66` is now `if nodes and line.strip():`. The Codex half already re-tested the class; I did not repeat it. I confirmed the bypass is closed and, separately, that the *reason* given for the three new cases is wrong — finding 1 below |
| **High** — duplicate fields last-write-wins | **ADDRESSED, both halves** | `:84-91` refuses AND keeps the first value. Both halves are independently killed: mutation `if key in seen_fields:` → `if False:` reds 2 cases; mutation `continue` → `pass` reds exactly 1 (the first-value case). The commit's claim that the second entry was needed because the first cannot reach it is measured-true |
| **Low** — hook cannot distinguish no-stdin from unparseable stdin | **ADDRESSED** | `printf 'not json' \| bash .claude/hooks/regen-features-page.sh` → `rc=0` + one warning line; empty stdin → `rc=0` silent; unwatched path → `rc=0` silent |

Excluded by the brief and not re-reported: the residual that a valid-JSON payload with a renamed
path key is silently ignored (inherited by five hooks).

---

## Angle 1 — is the new strictness wrong anywhere?

**Conclusion: the strictness itself is right. Nothing a reasonable author writes is newly refused
except a trailing HTML comment, and that is a deliberate narrowing.** What is wrong is what the
refusals *say*.

I fed 17 author-plausible shapes through `parse_features` + `check_nodes`:

| Shape | Result |
|---|---|
| value containing a colon (`for: Note: turns …`) | accepted |
| value containing a URL with a `#` fragment | accepted |
| trailing whitespace after a value | accepted |
| CRLF line endings throughout | accepted (`raw.rstrip()` absorbs `\r`) |
| blank line inside a node | accepted |
| node with zero fields | parses; `check_nodes` reports 2 real problems |
| empty `anchors:` value | parses; correctly flagged |
| one leading space before a field | **refused** — pre-existing, but see finding 2 |
| tab-indented field | **refused** — pre-existing, see finding 2 |
| `State: built` (capitalised) | **refused** — pre-existing, see finding 2 |
| `state : built` (space before colon) | **refused** — pre-existing, see finding 2 |
| `---` after the last node | **refused** — pre-existing, see finding 3 |
| a footer paragraph after the last node | **refused** — pre-existing, see finding 3 |
| `<!-- generated -->` after the last node | **refused — NEW in this commit**, see finding 3 |
| two `areas:` lines (a wrapped long list) | **refused — NEW in this commit**, see finding 4 |

The two genuinely new refusals are both intended by the design. The document may no longer carry
any footer, separator or tool marker after its first `###`, and a comma list may no longer be
wrapped across two lines. Both are defensible; neither error message says so.

I also checked the drift risk: `scripts/gen-features-page.py:77-78` **imports** `parse_features`
from `check-features.py` rather than reimplementing it, so page and gate cannot disagree about the
new grammar.

---

## Findings

### 1. Important — a new comment makes a false claim about what its own cases prove

`scripts/check-features.py:274-277`:

> ⛔ THE THREE FIXTURES BELOW ARE CODEX'S, VERBATIM WHERE IT GAVE ONE. Each is a line that the
> old exemption tuple waved through, and each carries the two status tokens (`currently` and
> `#322`) the rule above exists to find — **so a case going green here means a status line has
> been read, not that a parser was tidy.**

The bolded clause is false, and it is false in the direction that matters. The three cases assert
only `any("neither a field nor a heading" in p for p in parse_features(…)[1])` — that the line was
*refused*. A refused line hits `continue` at `:72` and never reaches `purpose`, so `STATUS_TOKENS`
never runs on it.

Measured — the fixture's tokens are inert decoration:

```
Codex fixture (two status tokens)    case-green=True  status-token-rule-fired=False
SAME case, tokens REMOVED (`> hello.`)  case-green=True  status-token-rule-fired=False
SAME case, empty blockquote (`>`)       case-green=True  status-token-rule-fired=False
```

Green here means exactly *"the parser was tidy"* — the reading the comment explicitly denies. The
cost is the usual one: a future reader trusts these three cases as coverage of the status-token
rule on continuation lines, which they are not. **Fix: say what green means — the line was refused
before any rule could be asked about it, which is why refusing is the coverage.** (Confidence:
high — shown by experiment, not by reading.)

### 2. Important — the error message diagnoses a different mistake than the one an author made

`scripts/check-features.py:67-71` emits, for *every* unrecognised line inside a node:

> ``features.md:6: `summarise-a-video` has a line that is neither a field nor a heading:
> 'state: built'. Keep each field on ONE line — a wrapped `for:` would hide its own status tokens
> from the check. No prefix is exempt: a blockquote, an HTML comment and a stray `#` are text
> inside a node too``

That is the message for ` state: built`, `\tstate: built`, `State: built` and `state : built` —
four of the most likely things an author actually gets wrong. Read as prose at the moment someone
is blocked: it quotes back a string that visibly **is** a field while asserting it is not one, then
gives two pieces of advice (*keep it on one line*; *no prefix is exempt*) that describe neither
mistake. The commit **lengthened** this message and every added word is about the blockquote case.

The one sentence it never contains is the grammar: *a field starts at column 0, lowercase, as
`name:` with no space before the colon — one of `state`, `for`, `areas`, `anchors`,
`expected-because`.* Pre-existing behaviour, but this commit is the one that rewrote the message
and is the natural place to fix it.

### 3. Minor — document-level trailing content is blamed on the last node

`BASE + "\n---\n"` produces:

> ``features.md:10: `summarise-a-video` has a line that is neither a field nor a heading: '---'``

`---`, a footer paragraph and a trailing `<!-- … -->` are document-level, not node-level; the
message names a node four lines above and tells the author to keep *fields* on one line. Because
`nodes` is non-empty from the first `###` onward, everything after it — including the end of the
file — is attributed to whichever node happens to be last.

Attached to this: refusing a trailing HTML comment is **new** in this commit. The commit's
measurement (*"0 lines start with `>`, `<!--` …"*) establishes that nothing breaks today; it does
not establish that a tool marker or a generated-by comment will never be wanted at the foot of the
file. Worth knowing as a deliberate narrowing rather than discovering it later.

### 4. Minor — the duplicate-field message explains the rationale and omits the remedy

`scripts/check-features.py:85-88`:

> ``features.md:10: `summarise-a-video` repeats the field `areas` — a duplicate is refused, not
> merged. Under last-write-wins a later line silently replaces an earlier one, and what it replaces
> is never searched``

`areas:` and `anchors:` are comma lists, and splitting a long one across two lines is the natural
authoring shape now refused. The message says *why* last-write-wins is bad and never says *put
every value on one comma-separated line*. Same shape as finding 2: correct rationale, absent
instruction.

### 5. Minor — one mistake, two errors, and the second is misleading

A node with an empty `for:` followed by a real `for:` reports both:

```
P: features.md:8: `summarise-a-video` repeats the field `for` — a duplicate is refused …
N: features.md:5: `summarise-a-video` has no `for:` line — every node says what it is for
```

The node has two `for:` lines. "has no `for:` line" is an artefact of keeping the first value. It
is a consequence of the correct design choice, not an argument against it, but the second line
will send a reader looking for a missing field that is there twice.

### 6. Minor — a precedent claim is slightly wider than the precedent

`scripts/check-plan-code.py:3299` says the new coverage is *"three cases in `gen-features-page.py`
that RUN the hook, the shape `regen-backlog-page.sh` already set"*, and
`scripts/gen-features-page.py:604` calls those backlog cases the precedent. The backlog precedent
does **not** run its hook: `scripts/gen-backlog-page.py:2818` reads the awk program out of the
shell file and runs `awk`. The *placement* is the shared shape (coverage lives in the generator's
suite); *executing the shell script* is new here, and is strictly stronger. The comment claims
precedent for the part that has none.

---

## Angle 3 — the three subprocess cases, verified by experiment

| Claim | Result |
|---|---|
| (a) no case reaches the generator / writes a real `~/explainers` page | **Confirmed.** `~/explainers/features.html` mtime `1789883943` before and after a full `--self-test` run — unchanged. Separately, run inside a staged `scripts + docs + .claude/hooks` tree with `HOME` redirected: 12/12 green and **nothing written under the fake HOME** — so the mutation harness's control for `gen-features-page.json` is green for the right reason, not by luck |
| (b) with `.claude/hooks/` absent the suite reports CANNOT RUN rather than passing | **Confirmed.** Tree with `scripts` + `docs` only → `rc=1`, `8/12`, and three of the four failing lines print the full `CANNOT RUN: … stage scripts, docs AND .claude/hooks.` string. Nit: the `startswith("rc=0 ⚠")` case collapses the sentinel to `got False want True`, so that one line alone does not carry the cause — the presence case immediately above it does |
| (c) not slow enough to matter | **Confirmed.** Whole 12-case suite: **0.39s** wall clock, three `bash` + `python3` subprocesses included |

## Angle 4 — the mutation manifest, applied not read

Control proved green first (`30/30`), then all **20** entries of `scripts/mutations/check-features.json`
applied individually to the delivered source in a temp tree:

- every `edits` anchor occurs **exactly once** in `scripts/check-features.py` — 0 exceptions;
- every entry went red **via the case its `expect` names** — 20/20 `KILLED-BY-NAMED`, no
  unattributed kills, no survivors;
- the three new entries behave as the commit claims: `if key in seen_fields:` → `if False:` reds 2
  cases, `continue` → `pass` reds exactly 1, and the retargeted wrapped-continuation entry reds 4.

## Angle 5 — counts, recomputed from source

| Declared | Where | Recomputed | |
|---|---|---|---|
| 30 cases | `check-features.py:5` | `30/30 self-test cases passed` | ✅ |
| 12 cases | `gen-features-page.py:6` | `12/12 self-test cases passed` | ✅ |
| 20 entries | `scripts/mutations/check-features.json` | `len() == 20` | ✅ |
| 20 | `EXPECTED_MUTATIONS["scripts/check-features.py"]` | matches the manifest | ✅ |
| 767 | pinned sum, `check-plan-code.py:3303` | `sum(EXPECTED_MUTATIONS.values()) == 767`; independently, **on-disk entries across all 49 manifests total 767**, with **zero** per-file mismatches | ✅ |

## Angle 6 — comment audit, every claim in the diff

| Claim | Verdict |
|---|---|
| `check-features.py`: "Measured 2026-09-19 … 0 lines start with `>`, `<!--` or a non-heading `#` inside any node" | **True** — recomputed against `docs/features.md` today: 0 hits |
| `check-features.py:275-277`: "a case going green here means a status line has been read" | **FALSE** — finding 1 |
| `gen-features-page.py:600`: "`load_manifests` requires every entry's `file` to equal `scripts/<manifest stem>.py`" | **True** — `check-plan-code.py:1065`, `target = f"scripts/{man.stem}.py"` |
| `gen-features-page.py:601`: "`run_suite` runs the mutated file AS a Python suite, so a `.sh` target would red its own control" | **True** — `check-plan-code.py:500`, `[sys.executable, name, "--self-test"]` |
| `gen-features-page.py:604`: "`regen-backlog-page.sh`, whose four cases in `gen-backlog-page.py` set this precedent" | **Count true** (4 `_hook_awk` cases + 1 presence case), **mechanism overstated** — finding 6 |
| `gen-features-page.py:606`: "an unwatched path and two unreadable payloads" | True of the code (empty stdin does take the unparseable branch and is then suppressed), though the hook's own comment at `:35` insists empty stdin is *"nothing to have failed to parse"*. Terminology, not a defect |
| `check-plan-code.py:1006`: "The wrapped-continuation entry was RETARGETED … not an addition, so it is not in the +3" | **True** — visible in the diff; 17 + 3 = 20 and the retarget changes an anchor, not a count |
| `check-plan-code.py:1003-1005`: "the first cannot reach [the second half]: with the refusal gone BOTH cases red" | **True** — measured, redset 2 vs 1 |
| hook `:30-36`: the sentinel rationale, exit 0 on every path, empty stdin silent by design | **True** — all three behaviours reproduced |

## Gates run

| Command | rc | Result |
|---|---|---|
| `python3 scripts/check-features.py` | 0 | 26 nodes, 13 anchors + 21 areas each claimed once |
| `python3 scripts/check-features.py --self-test` | 0 | 30/30 |
| `python3 scripts/gen-features-page.py --self-test` | 0 | 12/12 |
| `python3 scripts/check-selftest-counts.py` | 0 | 42 scripts, every declared count verified by running it |
| `python3 scripts/check-fixture-variation.py scripts/check-features.py scripts/gen-features-page.py` | 0 | 13 parameters, 124 ratcheted, 7 exempt |
| `python3 scripts/check-plan-code.py --self-test` | 0 | 128/128 |
| `python3 scripts/check-ratchet-contract.py` | 0 | 37 guards, contract OK |
| `python3 scripts/check-docs.py` | 0 | documentation integrity OK |

`check-plan-code.py --mutate .` was **NOT RUN** (764+ mutations, excluded by the brief). CI runs it.
The `check-features.py` slice of it was run by hand above, over a proved-green control, 20/20.

## Out of scope

- **The warning channel.** The new warning is `echo`'d to stdout from a PostToolUse hook, which
  this repo has previously measured as reaching nobody outside transcript mode
  (`a-gates-channel-can-be-weaker-than-the-gate`). It is **not a defect of this commit** — all four
  sibling regen hooks (`regen-dashboard.sh:41`, `regen-goals-page.sh:45`,
  `regen-backlog-page.sh:49,95`) warn on the same channel, so it is a property of the hook family.
  Worth one backlog line for the family, not a change here.

# Round 8 — Claude half · `shard-mutation-sweep` · PR #366 · `df1ec075`

**Mandate: refute.** Immediate subject `git diff df9b5b47..df1ec075` (round 7's Codex fold);
whole-branch context `git diff 6416e212..df1ec075`.

**Verdict: NOT CONVERGED.** Two Medium findings aimed at the **deliverable**, so by
[`review-method.md`](../review-method.md):108 (*a finding in the deliverable → CONTINUE*) this is
**not a clean round**: the quiet counter returns to **0**, and this is neither the first nor the
second consecutive clean round.

`fixes_nontrivial: false` (this half changed no tracked file).

---

## Verification

Every command below was run at `df1ec075` on 2026-10-06. Python locally is **3.14.4**; CI pins 3.12,
so `check-python-pin` is advisory here.

### Counts and anchors — re-derived independently, not read back from the script

A second implementation of the counting rule, written against the manifests rather than asking the
script for its own answer:

```text
manifest files                      57
TOTAL manifest entries            1208      <- declared sum 1208   AGREE
check-plan-code.json entries       103      <- declared 103        AGREE
EXPECTED_MUTATIONS rows             57
edit anchors (sum of len(edits))  1216      AGREE
anchors unresolved in the delivered tree     0
anchors resolving AMBIGUOUSLY (count > 1)    0
duplicate (file, find-string) PAIRS          2   <- see note
duplicate (file, anchor-TUPLE) entries       0   AGREE
python3 scripts/check-plan-code.py --self-test   ->  175/175 passed, rc=0   AGREE
```

All four declared figures (175 / 103 / 1208 / 1216) are correct.

> **Note on the two duplicate find-strings, because the number disagrees with round 7's "0" and the
> disagreement is not a defect.** `check-plan-file-tags.json` and `check-python-pin.json` each hold a
> one-edit entry whose find-string also appears among a two-edit entry's anchors (at index 0 in
> `check-plan-file-tags`, index 1 in `check-python-pin`). The
> shipped refusal (`:1524`) keys on **exact tuple equality of an entry's find-strings**, so
> `(A,)` and `(A, B)` are not duplicates — correctly, they are different mutants of one line, and
> `:4514` records that this is deliberate. Reporting per-edit gives 2; reporting per-entry-tuple
> gives 0. Round 7's figure is the one the guard uses, and it is right.

Also checked, and also not a defect: **three mutation names are duplicated across manifests**
(`check-banner-armed`/`check-ci-watched`, and two names shared by `check-rc-contract`/
`check-surface-recall`). `seen_names` at `:1488` is reset **per manifest**, and the paired entries
target different files, so they are genuinely different mutations of parallel code.

### Gates

```text
check-docs                   rc=0  Documentation integrity OK
check-selftest-counts        rc=0  50 script(s) declare a count, every one verified by running it
check-anchors                rc=0  13 registered, all claimed
check-ratchet-contract       rc=0  ratchet contract OK
check-vocabulary-collisions  rc=0  no unjustified duplicate mechanism
check-backlog-closure        rc=0  WARN — 2 row(s) may be stale, 0 orphaned ids
check-python-pin             rc=0  advisory locally (3.14 vs CI 3.12)
check-review-rounds          rc=0
check-dashboard-entry        rc=0  ok — an entry block was added
```

⚠ **The full CI list was run, not a subset** (`docs/CLAUDE.md` rule 1) — the 31 `python3 scripts/check-*`
steps in `.github/workflows/ci.yml`. Every one returned **rc=0** except two, neither a defect:

- `check-banner-armed` rc=2 — it requires `--decide`/`--self-test`; CI passes them, a bare call does not.
- `check-review-rounds` rc=1 **after this file was written** (rc=0 before):
  `✗ shard-mutation-sweep round 8: only claude — codex neither ran nor recorded a REVIEW GAP: line`.
  That is the gate correctly observing a half-finished round; it clears when the Codex half is filed.

### A real sharded run, end to end — in an isolated clone, not the working tree

`--mutate .` mutates the delivered files in place, and this session has other agents in it, so the
sweep was run against a fresh clone at `df1ec075` with `node_modules/typescript` copied in.

⚠ **Two earlier attempts at this measured NOTHING and said so loudly, which is why they are
recorded rather than dropped:**

1. the first run wrapped the sweep in `timeout`, which **does not exist on macOS** → `rc=127`, and
   the `grep` I read the result through reported its own `rc=1`. Four "shards" finished in 5
   seconds. Had I read the pipe's exit code as the sweep's, this document would have claimed four
   shards it never ran.
2. the second run reached the harness, which **correctly refused the clone**:
   `CANNOT RUN — node_modules/typescript is missing under ., so the mutation tree would be
   incomplete and every verdict below it an artefact. TREAT THIS AS NOT CHECKED` → `NOT MEASURED`,
   rc=1. The `HARNESS_TREE` precondition does what it claims.

With the tree complete:

```text
=== SHARD 3 of 8 (12:40:20 -> 12:46:22) ===
rc=0
OK — delivered scripts mutated: 51 file(s), 151 mutation(s), 151 killed,
     151 attributed to the case each names, 0 survivor(s)
     — measured over shard 3 of 8 (round-robin)
git status --short after: clean

=== SHARD 1 of 8 (12:46:22 -> 12:53:05) ===
rc=0
OK — delivered scripts mutated: 51 file(s), 151 mutation(s), 151 killed,
     151 attributed to the case each names, 0 survivor(s)
     — measured over shard 1 of 8 (round-robin)
git status --short after: clean

=== SHARD 7 of 8 (12:53:05 -> 12:59:36) ===
rc=0
OK — delivered scripts mutated: 51 file(s), 151 mutation(s), 151 killed,
     151 attributed to the case each names, 0 survivor(s)
     — measured over shard 7 of 8 (round-robin)
git status --short after: clean

=== SHARD 2 of 8 (12:59:36 -> 13:05:41) ===
rc=0
OK — delivered scripts mutated: 48 file(s), 151 mutation(s), 151 killed,
     151 attributed to the case each names, 0 survivor(s)
     — measured over shard 2 of 8 (round-robin)
git status --short after: clean
```

⚠ **Shard 2 controls 48 files where the other three control 51** — correct and worth stating,
because a reader scanning the four lines would otherwise read it as a shortfall. Round-robin over a
manifest whose entries are grouped by file means a shard's *target* set depends on which entries its
stride lands on; the count that must not move is the **mutation** count, and all four are 151.
Derived independently from the manifest, and matching all four runs exactly:

```text
shard   1    2    3    4    5    6    7    8
muts   151  151  151  151  151  151  151  151
files   51   48   51   53   54   53   51   50
```

Shard 3 reproduces the coordinator's figure exactly. **And the strongest independent evidence is
CI's own**, at this exact SHA:

```text
gh pr checks 366
mutation-sweep (1..8)   ALL pass   2m53s .. 4m16s
mutation-sweep-complete pass
schema-gates            pass
verify                  FAIL  (see "the CI red" below)
```

### The partition, over the real manifest

Pure, exact, no suites:

```text
N=8 per-shard counts: {1:151, 2:151, 3:151, 4:151, 5:151, 6:151, 7:151, 8:151}
every mutation in exactly one shard: True
union size == manifest size (1208): True
--shard0 I/N selects the IDENTICAL slice as --shard (I+1)/N, for all 8 indices: True
--shard0 7/8 -> (8, 8)      --shard0 8/8 -> refused
```

### The whole shard surface — 28 invocations × both modes

`--self-test` × {`--shard`, `--shard0`} × {`''`, `' '`, `garbage`, `0/8`, `1/8`, `99/8`, `1/0`,
`x/5`, `3`, `1/٨`, `²/8`, `00/8`, `9999/9999`, `10000/10000`} → **all 28 rc=2**, each naming the
flag as typed. The coordinator's four spot checks are confirmed and extended; I could not find a
shard-shaped `--self-test` invocation that exits 0.

Same 14 values with `--mutate <nonexistent-dir>` (so the parser is exercised and no suite runs):

| value | `--shard` | `--shard0` |
|---|---|---|
| `''` `' '` `garbage` `3` `²/8` `00/8` `/` `0/` `/8` `10000/10000` | rc=2 *not of the form I/N* | rc=2 *not of the form I/N* |
| `0/8` | rc=2 *names a shard that does not exist* | rc=2 — **reached** the `--mutate` dir check |
| `1/8` `7/8` | rc=2 — **reached** the `--mutate` dir check | rc=2 — **reached** |
| `8/8` | rc=2 — **reached** | rc=2 *does not exist* (one past the last shard) |
| `99/8` `1/0` | rc=2 *does not exist* | rc=2 *does not exist* |
| `9999/9999` | rc=2 — **reached** | rc=2 *does not exist* |

"Reached the `--mutate` dir check" means the shard parsed and resolution continued — i.e. **no
over-refusal**. Both flags together (`--shard 1/8 --shard0 0/8`, and with either side garbage) →
rc=2 *"--shard and --shard0 are the same control with different bases; pass one"*.

### Merge artefacts — `check-merge-ready.py --pr 366`, relayed verbatim

```text
pull request           : #366
base                   : origin/master
pull-request-only steps: 2 derived from ci.yml — dashboard entry ratchet, check-review-recorded (PR only)

  ok  dashboard entry    rc=0  ok — an entry block was added
  NO  review recorded    rc=1  ok — review recorded in this range: docs/reviews/claude/shard-mutation-sweep-r1-claude.m
  ok  review rounds      rc=0  ⚠ verdict corpus: 222 read — 30 meaningfully checked below, 192 PRE-CUTOVER (schema < 3:
     ⛔ review recorded: the body contains 'NO-REVIEW', which is not `NO-REVIEW:`. The gate matches that literal exactly — case, hyphen and colon.
  NO  mergeability       rc=1  mergeStateStatus is BLOCKED
  NO  CI                 rc=1  failing: verify

NOT READY — CI, mergeability, review recorded
  ⚠ A local gate sweep cannot answer the pull-request-only checks above. That is why this script exists and why 'all my gates are green' is a different claim.
rc=1
```

**The CI red is `check-review-recorded`, and it is the expected mid-round state — not a finding:**

```text
FAILED — 7 round(s) ran and guarded code was committed after every one of them.
  The closest (shard-mutation-sweep-r6-codex.verdict.json) never saw:
    scripts/check-plan-code.py, scripts/mutations/check-plan-code.json
  Run one more round against the current tree, or put `NO-REVIEW: <reason>` in the pull-request body.
```

Verified mechanically: `shard-mutation-sweep-r7-codex.verdict.json` records
`"head": "df9b5b47e81f77fca838df4414956adb187e3702"`, and it was **added in `df1ec075`** — the same
commit that changed `scripts/check-plan-code.py`. So round 7's verdict provably predates the code it
is being asked to cover; the gate is right, and round 8's verdict at `df1ec075` is what clears it
**provided the fold for this round's findings does not itself touch guarded code**. If it does, the
gate reopens — review-method Q4(b) options 1–3 exist for exactly that.

The `⛔ NO-REVIEW` line is **advisory and accurate**: the body carries the heading
*"## ⟳ THE NO-REVIEW WAIVER IS WITHDRAWN"*, i.e. the bare token without a colon, which is correctly
not read as a waiver. It will keep printing on every run of the gate for this PR.

### Not measured / could not run

- **`--mutate .` unsharded** — forbidden by the brief (~29 min). Four shards plus CI's eight stand
  in its place.
- **The bytecode scrub** — excluded by the brief (rounds 4–6 found nothing).
- **Whether round 7's first draft's mutation really survived at `shard 8, 150/151`.** That tree no
  longer exists, so the historical number is **NOT MEASURED**. Its *mechanism* I did reproduce —
  see "could not refute" item 6.
- **`test:integration` / `test:e2e`** — need a live Supabase stack; not attempted.

---

## Findings

Severity order. Each finding states the observation; each fix is stated **separately** and is
**UNVERIFIED** — I changed no tracked file.

---

### M1 · Medium · DELIVERABLE · caused by THIS fold

> **"A third flag is one dict entry" is false in both directions. A hyphen-free third entry is
> silently inert and the whole suite stays green; a hyphenated one — the single spelling this fold's
> new function was written to support — turns the suite red.**

Three claims ship in the subject:

| site | claim |
|---|---|
| `scripts/check-plan-code.py:1658` | "A third flag is one dict entry, and disagreement is not DETECTED but **IMPOSSIBLE** — which is the stronger of the two" |
| `scripts/check-plan-code.py:1673` (**new in this fold**) | "**Both consumers** now route through here, so they agree **BY CONSTRUCTION**" |
| `scripts/check-plan-code.py:4646` | "The dict is the single declaration; this loop and the mode check in `main` are its **only two readers**" |

**There are five readers of these dests, not two.** Two derive from the dict; three name the flags
by hand:

```text
:4664   _mode_why = next(... shard_mode_refusal(getattr(a, shard_dest(_f)), ...)   DERIVED
:4650   ap.add_argument(f"--{_opt}", metavar="I/N", help=_help)                    DERIVED
:4720   if a.shard is not None and a.shard0 is not None:        <- mutual exclusion, HARD-CODED
:4724   if a.shard0 is not None:  parse_shard(..., zero_based=True, flag="--shard0")  HARD-CODED
:4729   if a.shard is not None:   parse_shard(a.shard)                               HARD-CODED
```

And the dict cannot express the one property that distinguishes the two shipped flags: `shard0`'s
zero-basedness lives at `:4724`, not in `SHARD_FLAGS`. The dict declares a flag's **name and help
text** — precisely the two things its two derived readers need — while everything that makes a
shard flag *do* something is written out by hand.

**Exhibit A — a hyphen-free third entry.** `SHARD_FLAGS` is read by `main` at call time, so this was
measured by monkeypatching the module global in-process; no tracked file was touched.

```text
SHARD_FLAGS["shard2"] = "a hypothetical third flag, ONE DICT ENTRY"

python3 --self-test                                       175/175 passed   rc=0
main(["--mutate", <fixture>, "--shard2", "1/2"])          rc=0
   OK — delivered scripts mutated: 2 file(s), 2 mutation(s), 2 killed, 2 attributed
        to the case each names, 0 survivor(s) — measured over the WHOLE manifest
main(["--mutate", <fixture>, "--shard2", "garbage"])      rc=0   ... the WHOLE manifest
main(["--mutate", <fixture>, "--shard2", "9/9"])          rc=0   ... the WHOLE manifest
main(["--mutate", <fixture>, "--shard", "1/2", "--shard2", "2/2"])   rc=0, honours --shard silently
```

So a third flag added exactly as the comment instructs: parses, passes the mode refusal, passes
**175/175**, and is then **ignored**. `garbage` is accepted at rc=0 — the same shape as round 7's H1
(`--self-test --shard0 garbage` printing `169/169 passed`) and round 1's Codex finding, reachable a
third time through the abstraction built to end it. An empty shard (`9/9`) is never refused, which
is the one outcome `shard_refusal`'s own docstring calls "a gate reporting success for work it never
did". And it is not mutually exclusive with `--shard`.

⚠ **It is not a false green, and the finding is smaller for it.** The verdict line honestly says
`the WHOLE manifest`, exactly as `:4713`'s note records for the `--shard ""` case. The realised harm
is N jobs each doing the whole sweep under a log line that admits it — wasteful, not lying. **The
defect is the claim**, and the claim is the thing that invites the next author to ship the flag.

**Exhibit B — a hyphenated third entry, i.e. the case `shard_dest` exists for.**

```text
SHARD_FLAGS["shard-x"] = "a hypothetical third flag — ONE DICT ENTRY"
_self_test()  ->  rc=1   174/175 passed
  [FAIL] ...and every shipped key survives the same normalisation:
         got ('shard', 'shard0', 'shard_x')  want ('shard', 'shard0', 'shard-x')
```

The fold added `shard_dest` so that a hyphenated flag *works*, and in the same fold added `:4047`,
which **refuses one**. The two new cases are in direct tension: `:4045` asserts hyphenated flags
round-trip correctly; `:4047` asserts no shipped key contains a hyphen. There is therefore **no
third flag that can be added as one dict entry** — a hyphen-free one is silently wrong, a
hyphenated one reds the suite.

Supporting observation: `:4047` has **no entry in `scripts/mutations/check-plan-code.json`** (grep
for its text returns 0), and its only live falsifier is adding a hyphenated shipped key. That is not
a contract violation — cases do not require mutations — but it means the case that blocks Exhibit B
is itself outside the sweep.

**Fix, UNVERIFIED — two coherent shapes; they are alternatives, not a sequence.**

- *(a) Make the claim true.* Give `SHARD_FLAGS` the fields a flag actually needs —
  `{"shard": {"zero_based": False, "help": …}, "shard0": {"zero_based": True, "help": …}}` — and
  derive `:4720`'s mutual exclusion (`[f for f in SHARD_FLAGS if getattr(a, shard_dest(f)) is not
  None]`, refuse when more than one) and `:4724`/`:4729`'s resolution from it. Then delete `:4047`,
  since hyphenated keys become genuinely supported.
- *(b) Withdraw the claim and refuse the third flag.* Say the dict covers **parsing and the mode
  question only**, keep the three hard-coded readers, and add a case asserting
  `set(SHARD_FLAGS) == {"shard", "shard0"}` with a message pointing at `:4720`–`:4731`. A third
  entry then fails loudly instead of being inert. **This is the shape backlog #154 settled on —
  refuse, don't widen** — and it is the cheaper of the two.

Either way, `:1658`, `:1673` and `:4646` must stop saying "impossible", "both consumers" and "only
two readers".

---

### M2 · Medium · DELIVERABLE · caused by ROUND 6's fold (`d95908c0`), outside the immediate fold diff

> **`.github/workflows/ci.yml:674-691` describes a `+1` and "the guard below" that round 6's M1
> deleted — two lines above the comment that says no logic lives there.**

The shipped invocation is:

```yaml
# ci.yml:710
python3 scripts/check-plan-code.py --mutate . \
  --shard0 "$SHARD_INDEX/$SHARD_TOTAL"
```

The comment block immediately above it says:

| line | claim | measured |
|---|---|---|
| `:675` | "`strategy.job-index` is 0-based, **hence the +1** — `--shard` is 1-based because that is what a human types" | there is no `+1`, and the step calls `--shard0`, not `--shard`. `git log -S 'SHARD_INDEX + 1'` shows `d74d1c2b` added `--shard "$((SHARD_INDEX + 1))/$SHARD_TOTAL"` and **`d95908c0` removed it** |
| `:679` | "An absent N makes the spec **`1/`**, which `parse_shard` refuses" | with `--shard0 "$SHARD_INDEX/$SHARD_TOTAL"` an absent N makes the spec **`0/`**. (It *is* refused — `--shard0 '0/'` → rc=2 *not of the form I/N* — so the protection holds; the spelling named does not) |
| `:689` | "the **guard below** costs two lines and removes the asymmetry rather than leaving a comment that is true about N and silent about I" | **there is no guard below.** `:696` opens with "⛔ **NO LOGIC LIVES HERE ANY MORE** — ROUND 6 M1" and the `run:` block asserts nothing |

So the file contains two comments, seven lines apart, that contradict each other about whether a
shell-side guard exists. The substantive protection *did* move correctly into `parse_shard` —
measured: `--shard0` with `''`, `' '`, `garbage`, `0/`, `/8`, `/` all exit 2 with a sentence — which
is why this is Medium and not High. But `ci.yml` is the one file an editor opens before changing the
shard invocation, and it currently tells them a two-line shell guard protects the I side.

**Fix, UNVERIFIED.** Rewrite `:674-691` to describe what ships: I and N arrive through `env:` as
`strategy.job-index`/`job-total`; the 0→1 conversion lives in `parse_shard` under `--shard0`; the
only guard is that parser, and an absent I or N yields `0/N` or `0/`, both rc=2. Keep the v1/v2/v3
history at `:699-706` — that is the part worth keeping. Delete "hence the +1" and "the guard below".

---

### L1 · Low · DELIVERABLE · caused by THIS fold

> **`shard_dest` is one of argparse's two normalisation steps, not "argparse's OWN normalisation".
> A key with a leading hyphen still produces the AttributeError traceback the fold set out to
> remove, and the new case probes exactly one input.**

argparse derives a dest as `long_option.lstrip(prefix_chars)` **then** `.replace("-", "_")`.
`shard_dest` (`:1675`) does only the second step. Measured across 13 keys:

```text
key            option          argparse dest   shard_dest
'shard-x'      --shard-x       'shard_x'       'shard_x'       AGREE
'a-b-c'        --a-b-c         'a_b_c'         'a_b_c'         AGREE
'2shard'       --2shard        '2shard'        '2shard'        AGREE
'x'            --x             'x'             'x'             AGREE
'shard__x'     --shard__x      'shard__x'      'shard__x'      AGREE
'shardé'       --shardé        'shardé'        'shardé'        AGREE
'shard.x'      --shard.x       'shard.x'       'shard.x'       AGREE
'-shard-x'     ---shard-x      'shard_x'       '_shard_x'      *** DISAGREE ***
'--shard'      ----shard       'shard'         '__shard'       *** DISAGREE ***
''             --              TypeError: dest= is required for options like '--'
'-'            ---             TypeError: dest= is required for options like '---'
```

For the two disagreeing keys, `main:4664`'s `getattr(a, shard_dest(_f))` raises
`AttributeError: 'Namespace' object has no attribute '_shard_x'` — **a traceback where a sentence is
owed**, which is verbatim the defect round 7's Codex half filed. The fix closed the instance
(a hyphen in the middle) and left the class (argparse strips leading prefix chars first).

The docstring's "**argparse's OWN normalisation, spelled once**" (`:1664`) therefore over-claims, and
`:1673`'s "they agree BY CONSTRUCTION" is false for these keys. The new case at `:4045` exercises
`shard_dest` at **one** input, which is the weaker form this repo has already paid for
(*exercise the producer at two distinct inputs*).

⚠ Leading-hyphen keys are exotic — `f"--{'-shard-x'}"` is `---shard-x`. This is Low because nothing
plausible reaches it, not because the claim is nearly true.

**Fix, UNVERIFIED.** `return opt.lstrip("-").replace("-", "_")`, and drive `:4045` from a tuple of
inputs — at minimum `("shard-x", "-shard-x", "a-b-c")` — so one case covers the rule rather than one
point of it. Alternatively, if hyphenated keys are not in fact wanted (see M1 Exhibit B), **refuse**
a key containing `-` at import and delete `shard_dest` entirely; that is the smaller surface.

---

### L2 · Low · INSTRUMENT · caused by THIS fold

> **`_roundtrip` catches only `AttributeError`, so the second failure mode its own docstring names
> — "the suite dies before printing `[FAIL] <case>`" — is still open.**

`:4040-4043` is:

```python
try:
    return getattr(_p.parse_args([f"--{_opt}", "2/5"]), shard_dest(_opt))
except AttributeError:
    return "MISSED — shard_dest disagrees with argparse"
```

Measured, with `shard_dest` replaced by a function that raises `TypeError`:

```text
shard_dest raises TypeError: RAISED TypeError: mutated shard_dest
   [FAIL] lines printed before death: 0   (tally line printed: False)
```

The suite dies with no `[FAIL]` line and no tally — "the same trap the length case fell into one
fold ago", which the docstring at `:4035-4036` cites as the reason for returning a value. The
returned-value technique closes exactly one exception type.

⚠ **No manifest entry reaches this today.** The shipped mutation is `return opt` → identity, which
raises `AttributeError` and is caught. So this is a latent gap in a case, with no live consequence.

**Fix, UNVERIFIED.** `except Exception:` (or `except (AttributeError, TypeError):`) and fold the
exception's type into the returned string, so a miss of any kind arrives as a named `[FAIL]`.

---

### L3 · Low · ARTEFACT · caused by ROUND 5's fold, carried through this one

> **The PR body's "## Review state" section says "Five rounds, both halves each." Seven rounds,
> both halves each, are on disk and inside this PR's own diff.**

```text
rounds with BOTH halves filed:  r1 CX  r2 CX  r3 CX  r4 CX  r5 CX  r6 CX  r7 CX
review documents added on this branch: 22
```

The section then narrates round 5's findings only, and closes "Round 5 broke none of it". Rounds 6
and 7 both produced findings that changed delivered code — round 6's M1 removed the `strategy.job-
index + 1` arithmetic from `ci.yml` (and left M2 above behind), round 7 produced H1 plus the Codex
Low this fold answers — and neither appears in the section a reader goes to for "what has been
reviewed".

⚠ **The sharpest part.** That section was *added* as round 5's M2 fix, under the heading
*"⟳ CORRECTIONS, 2026-10-06 — this body was one of four narration sites round 5 found stale"*. The
repair for stale narration is itself stale, by two rounds, in the same document. The figures table
in that section is **not** part of this finding: it names its vintage (`Actual at ece8d309`) and is
honest about it. "Five rounds" names no vintage.

Related, and the reason this is filed rather than waved through: the dashboard entry added by this
fold calls round 7's Codex Low **"Folded — twice"**, and the PR body's own narration will read to a
human as "that claim is now true". Per M1 it is not. Whatever is written for round 8 should not
repeat the pattern.

**Fix, UNVERIFIED.** In the PR body: "**Seven** rounds, both halves each"; add r6 and r7 with their
findings and dispositions; and when M1 is folded, record the claim's status rather than the fix's
existence.

---

## Answers to the six questions

**1 · `shard_dest` and the no-explicit-`dest` design — where do they disagree?**

Measured, not reasoned (13 keys, table in L1). They **agree** for: a hyphen anywhere but the start
(`shard-x`, `a-b-c`), leading digits (`2shard`), a single character (`x`), a double underscore
(`shard__x`), unicode (`shardé`), a dot (`shard.x`), a space (`shard x`). They **disagree** for any
key with a **leading hyphen** (`-shard-x` → argparse `shard_x`, `shard_dest` `_shard_x`; `--shard` →
argparse `shard`, `shard_dest` `__shard`), because argparse `lstrip`s prefix chars before replacing
and `shard_dest` does not. The consequence is a **traceback**, not a sentence — `AttributeError` out
of `:4664`. The **empty string** and a bare `"-"` never reach a dest at all: `add_argument("--")`
raises `TypeError: dest= is required for options like '--'` at parser construction, before any
value is read. That is L1.

Two further hazards the dict cannot see, neither a separate finding:

- **dest collision.** A key whose normalised dest equals an existing one — e.g. `self_test`, which
  argparse accepts as `--self_test` (no option-string conflict with `--self-test`) while landing on
  the **same dest** — would make `main:4664` read `--self-test`'s boolean as a shard value, and
  `:4670`'s `if a.self_test:` read a shard string as a mode switch. Nothing checks for it.
- **an empty `SHARD_FLAGS`.** Every new case is a tuple comprehension over the dict, so all of them
  are vacuously true over `{}`. It does not pass silently, though — measured, `_self_test()` then
  dies with `AttributeError: 'Namespace' object has no attribute 'shard'` from the case at `:4003`
  that calls `main(["--shard", "2/5"])`. It fails; it just fails by dying rather than by printing a
  `[FAIL]` line.

**2 · Is the new round-trip case genuinely falsifiable, and for the right reason?**

Mostly yes, with one real gap and one hazard.

- **It fails for the right reason when `shard_dest` is severed as shipped.** The manifest's single
  entry (`return opt.replace("-", "_")` → `return opt`) produces exactly
  `[FAIL] a hyphenated flag round-trips through 'shard_dest' exactly as argparse names it: got
  'MISSED — shard_dest disagrees with argparse' want '2/5'`, 174/175. Confirmed by applying the
  mutation in-process.
- **Could it pass while `shard_dest` is wrong? YES** — for the leading-hyphen class, because the
  case probes only `"shard-x"`. That is L1.
- **Could it fail while `shard_dest` is right?** I tried and could not construct one. A
  `shard_dest` that returns a *different but existing* dest (`"self_test"`) is correctly caught, as
  is one that mangles the shipped keys (caught by `:4047`). The only false-failure channel I found
  is argparse itself changing its rule — which is the case's purpose, not a flaw.
- **One hazard:** the `except AttributeError` is narrower than the docstring's own description of
  the trap. That is L2.
- **And `:4047`, the second new case, is a problem in the opposite direction:** its only live
  falsifier is a hyphenated shipped key, i.e. the configuration `shard_dest` was written to support.
  That is M1 Exhibit B.

**3 · `SHARD_FLAGS` as a dict — does anything depend on its order? Is a dict the right structure?**

**Order: yes, and it is deterministic.** `:4664` uses `next(... if _w)`, so the **first** flag in
insertion order wins. Dict insertion order is a language guarantee (3.7+), and `list(SHARD_FLAGS)`
is `['shard', 'shard0']` — fixed by source order. With both values invalid, the message is always
about `--shard`:

```text
shard_mode_refusal("bad1", None, flag="--shard") first ->
  CANNOT RUN — --shard 'bad1' only means something with --mutate ROOT, ...
```

That is stable, not non-deterministic, and reporting one of two is fine here because `:4720` refuses
both-at-once anyway. **No finding on order.**

**Is a dict the right structure? No — and that is M1's structural core.** `dict[str, str]` can carry
a flag's name and its help text and nothing else. The property that actually distinguishes the two
shipped flags — zero-basedness — is not in it; it is hard-coded at `:4724`. A structure that cannot
express the difference between its two members cannot make a third member "one dict entry". M1's
fix (a) is this, spelled out.

(The annotation itself is fine: `"dict[str, str]"` is a string literal, never evaluated, and the
values are implicit string concatenations inside parens, not tuples.)

**4 · The whole shard surface, end to end — and does a REAL sharded run still select the right
slice?**

Full matrices in Verification: 28 `--self-test` invocations all rc=2; 28 `--mutate` invocations
refusing every invalid value with a sentence and **accepting every valid one** (no over-refusal);
both flags together refused. The partition over the real 1,208-entry manifest is exact at N=8 — 151
per shard, every mutation in exactly one, union = manifest — and `--shard0 I/N` selects the
**identical** slice as `--shard (I+1)/N` for all eight indices, which is the property CI depends on.

End to end: **shards 1, 2, 3 and 7 each 151 mutations, 151 killed, 151 attributed, 0 survivors,
rc=0** in an isolated clone, with `git status` clean after each; and **all eight `mutation-sweep`
jobs pass in CI at `df1ec075`**. Over-refusal would have shown as a CANNOT RUN; under-refusal as a
shard reporting a count other than 151 or a verdict line naming the wrong slice. Neither appeared.

**5 · Counts and anchors — re-derived independently.**

175 / 103 / 1208 / 1216 are all correct; 0 unresolved, 0 ambiguous, 0 duplicate anchor tuples.
Details and the two explained near-misses (2 shared find-strings, 3 cross-manifest duplicate names,
neither a defect) are in Verification. **No count disagrees with the tree.**

**6 · The merge artefacts — is there any sentence a reader would be misled by?**

`check-merge-ready` relayed verbatim above: **NOT READY** on CI, mergeability and review-recorded,
all three traced to the one root cause — this round had not yet run — and none of them a finding.

Backlog rows read and consistent with the tree: **#217 ✅ (was 🟠)**; **#228, #229, #230, #231,
#232** all 🟡 and filed, with #230 correctly recorded as *deferred* and referenced from the PR body,
and #232 amended to five raising sites as the dashboard entry claims. Round 5's M1 (the body
claiming to close an open row) is genuinely fixed.

The dashboard entry added by this fold is accurate on its numbers (175 / 103 / 1208 / 1216, shards
3/5/8) and on its mechanism claims — I reproduced both of the ones that can still be reproduced (see
"could not refute" items 5 and 6).

**One sentence a reader would be misled by: "Five rounds, both halves each."** There are seven. That
is L3. And the entry's "Folded — twice" will read as *the claim is now sound*, which per M1 it is
not.

---

## What I tried to refute and could not

The round is not clean, so this is not the round's entire value — but these are the attacks that
failed, stated precisely enough to be re-run.

1. **Every one of the coordinator's six already-measured claims survived.** `--self-test` with
   `--shard ''`, `--shard0 ''`, `--shard0 garbage`, `--shard 0/8` → all rc=2 (and 24 further values
   besides). A hyphenated third key through `main` → rc=2 with a sentence, **not** AttributeError:
   `CANNOT RUN — --shard-x '2/5' only means something with --mutate ROOT`. Severing `shard_dest` →
   the named `[FAIL]`. `--self-test` 175/175. Shard 3 at 151/151/151/0. 1,216 anchors, 0 unresolved,
   0 duplicate tuples. `shard_mode_refusal(None, None)` and `(None, ".")` both `None` — the
   `is not None` fix does **not** over-refuse. I found nothing false in the brief.
2. **I tried to make a valid sharded run fail, and could not.** Every valid `I/N` for both flags
   reaches resolution; my four shards and CI's eight all land exactly 151. The `--shard0` →
   `--shard` mapping is slice-identical at all eight indices. I specifically looked for
   over-refusal, which nothing in CI would distinguish from a pass, and found none.
3. **I tried to find a *behavioural* defect in the fold and could not.** `main`'s
   `getattr(a, shard_dest(_f))` is correct for both shipped keys, which contain no hyphens; every
   finding above is about a claim, a hypothetical third flag, or a stale comment. The code that
   ships does what it says.
4. **I tried to break the partition at awkward N and could not.** N=1, 2, 3, 7, 8, 40 over the real
   1,208 entries: every mutation in exactly one shard, pairwise disjoint, union = manifest.
5. **I tried to show that `:4047` or `:4045` could pass over a wrong `shard_dest` in the ways that
   matter most, and got one hit and two misses.** The hit is the leading-hyphen class (L1). A
   `shard_dest` returning an existing-but-wrong dest, and one that mangles the shipped keys, are
   both caught.
6. **I tried to refute the fold's account of why its FIRST attempt was unfalsifiable, and
   reproduced it instead.** With `dest=shard_dest(_opt)` passed explicitly, the lookup succeeds for
   **both** the real and the severed `shard_dest` — `dest='shard_x'` → `'2/5'`, `dest='shard-x'` →
   `'2/5'` — so the case could not fail either way. The comment at `:4648-4654` is accurate, and so
   is its sibling claim that an explicit hyphenated dest "no ordinary attribute access can reach":
   `vars(ns)` is `{'shard-x': '2/5'}`, reachable by `getattr` and not by dot access.
7. **I tried to find a real duplicate-anchor or duplicate-name defect behind my two numeric
   disagreements with round 7, and both dissolved** into the guard's own (correct) definitions.
8. **I did not re-attack the bytecode scrub** (excluded), and I have no evidence for or against it.

---

## Findings table

| # | Severity | Aim | Caused by a previous fold? |
|---|---|---|---|
| M1 | Medium | **Deliverable** — `scripts/check-plan-code.py:1658, :1673, :4646, :4047` | **No — this fold.** `:1673` and `:4047` are new in `df1ec075`; `:1658`/`:4646` are round 7 H1's fold, which this one re-asserted |
| M2 | Medium | **Deliverable** — `.github/workflows/ci.yml:674-691` | **Yes** — round 6's M1 fold (`d95908c0`) removed the `+1` and the shell guard, kept the comment. Outside the immediate fold diff; missed by rounds 6 and 7, both halves |
| L1 | Low | **Deliverable** — `scripts/check-plan-code.py:1664, :1675, :4045` | **No — this fold.** The instance of round 7's Codex Low is fixed; its class is not |
| L2 | Low | Instrument — `scripts/check-plan-code.py:4040-4043` | **No — this fold** |
| L3 | Low | Artefact — PR #366 body, "## Review state" | **Yes** — round 5's M2 fold added the section; two rounds of drift since |

0 Blocking · 0 High · 2 Medium · 3 Low. **Three of the five are in the deliverable**, and all three
are the branch's signature defect: a sentence that claims more than the code keeps.

---

## Verdict

**NOT CONVERGED.**

Round 4 was quiet 1; rounds 5, 6 and 7 each reset the counter. **This round does not continue the
quiet run either** — M1 and M2 are findings in the deliverable, which `review-method.md:108` makes
an unconditional CONTINUE. The quiet counter stands at **0**, and this is **neither the first nor
the second consecutive clean round**.

⚠ **And the shape is worth naming before the next fold is written.** Eight rounds have produced one
recurring defect and this round did not break it: the fix for round 7's Codex Low repaired the
instance, re-asserted the claim that was wrong, and added a case that refuses the configuration the
fix was for. M1's fix (b) — *refuse the third flag rather than claim it works* — is the shape that
ends the sequence, because it replaces a promise about future flags with a gate on them. M1's fix
(a) keeps the promise and must then make it true at five sites; if that is the choice, the case
asserting `set(SHARD_FLAGS) == {"shard","shard0"}` should still be written first, so that the next
reviewer has a falsifier either way.

⚠ **Tree identity (Q4(b)).** The `verify` red is `check-review-recorded`, and it clears on a round-8
verdict at the tree that merges. **M1 and M2's fixes both touch guarded files** (`check-plan-code.py`
and `ci.yml`), so folding them re-opens the gate and round 9 becomes structurally necessary. Per
`review-method.md:116-122` that decision belongs to the human, cheapest option first — land the
editorial fix (L3, body-only) ahead of the final round, or keep the code fixes uncommitted for the
reviewer — **not** to a reviewer assuming another round.

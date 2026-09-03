# The mutation harness's final line must say whether it measured anything

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

⚠ **The header order is load-bearing, and `check-anchors` proved it.** `HEAD_LINES = 10`
(`scripts/check-anchors.py:61`) — the Anchor and Goal must sit in the first ten lines. Adding the v3
note *above* them pushed the declaration to line 16 and turned the gate red. **Version notes go
BELOW the declaration**, always.

> **v3 — 2026-09-03.** Rounds 1 **and 2** folded, both halves each
> ([r2 claude](../../reviews/spec-mutation-drift-report-contract-r2-claude.md),
> [r2 codex](../../reviews/spec-mutation-drift-report-contract-r2-codex.md)). Round 2 returned the
> **same Blocking from both halves for the second consecutive round**, and the user's decision was to
> **stop patching the landmark and write the state machine** — which §4 now is. Two positional
> proxies failed; v3 enumerates the five states and derives the flag from the enumeration.
>
> **v2 — 2026-09-03.** Round 1 folded, BOTH halves
> ([claude](../../reviews/spec-mutation-drift-report-contract-r1-claude.md),
> [codex](../../reviews/spec-mutation-drift-report-contract-r1-codex.md)). Both independently
> returned **NOT CONVERGED** on the same Blocking: **the recommended flip point was wrong and would
> have left the worst case unfixed.** v1's §1, §2, §4, §5, §6 and §7 all changed.

**Source:** `docs/reviews/architecture-review-2026-09-03.md`, finding **B**, candidate **2′**.
Replaces candidate 2, which was withdrawn after its premise was refuted by execution.

---

## 1. The defect, measured

`scripts/check-plan-code.py --mutate .` is what CI runs. On a manifest/`EXPECTED_MUTATIONS`
mismatch it prints, on one line:

```
FAILED — delivered scripts mutated: 0 file(s), 0 mutation(s), 0 survivor(s)
```

**Nothing was mutated.** `mutate_delivered` returns at `:625-626`, five lines before the
`shutil.copytree` at `:630`, with `ev` still the initializer built at `:584`
(`{"files": {}, "mutations": [], "survivors": [], …}`). The caller at `:2069-2074` formats a tally
out of that empty structure.

### The four returns — enumerated with `ast`, not by reading (r1 H1)

`mutate_delivered` spans `:576-663` and has **four** returns. Both review halves agreed this table is
the thing that makes the requirement checkable:

| line | vs `copytree` `:630` | cause | `ev` at that point |
|---|---|---|---|
| `:586` | before | `load_manifests` returned `problems` — no manifest dir, bad JSON, duplicate name/anchors, target mismatch | empty |
| `:626` | before | count/declaration drift, undeclared target, home-escape | empty |
| **`:646`** | **AFTER** | **control run red before any mutation** | **`files` POPULATED (`:639`), `mutations`/`survivors` still empty — set at `:648`** |
| `:663` | after | normal completion | full |

### Reproduced — three of the four returns exercised, on temp copies, never the repo

| trial | return | final line |
|---|---|---|
| clone an existing manifest entry (duplicate anchors, `:562`) | `:586` | `FAILED — … 0 file(s), 0 mutation(s), 0 survivor(s)` |
| add an entry with a distinct anchor, leave the count at 8 | `:626` | `FAILED — … 0 file(s), 0 mutation(s), 0 survivor(s)` |
| **force a target's control suite to exit 1** | **`:646`** | **`FAILED — … 7 file(s), 0 mutation(s), 0 survivor(s)`** |

⚠ **The third is the worst case and v1 did not cover it.** `7 file(s)` — not zero — beside
`0 survivor(s)` is the shape of a clean sweep, on a run whose own report says *"CANNOT RUN … Treat
this as NOT CHECKED."* `CLAUDE.md`'s first rule is that *"'Cannot run' is a FAILURE, never a pass"*.

`:663` is untested here and is covered by F3, which Codex ran: `OK — delivered scripts mutated:
7 file(s), 162 mutation(s), 0 survivor(s)`, exit 0.

## 2. Severity — 🟡, and the downgrade is deliberate

The review filed this 🟠. **That was too high, and the correction belongs here.**

- `:2072` already prints `FAILED —`, and `:2075` returns `1`. **There is no false-green path.**
  **Independently confirmed by the Codex half**, which searched for an early return yielding exit `0`
  or a line beginning `OK` and found none.

⚠ **v1 also argued "a careful reader sees `0 file(s)` and can infer nothing ran". That justification
is WITHDRAWN** — it is false for `:646`, which prints `7 file(s)`. The severity stays 🟡 on
exit-code semantics alone; the file count cannot carry any of the argument (r1 M2).

So this is a **report-contract** defect on an already-failing path, not a silent pass. What makes it
worth fixing anyway is that `0 survivor(s)` is *the project's success sentence* — the phrase every
green run ends with. Printing it on a run that never started makes "the harness aborted" and "the
harness measured and found nothing" **the same string**, which is this project's own recorded
failure mode: *"'Guard didn't fire' and 'nothing could see it fire' look identical."*

## 3. The precedent this follows

`:2100-2106` already solved the same class for the other mode, and says so:

> *"Name the MODE on the final line. All three modes used to end in an identical `OK — …`, so a CI
> log could not show which subject was measured, and dropping both flags looked exactly like passing
> them. Round 5, L1."*

The `--mutate` path never got that treatment. **This spec is that fix, applied to the one path that
was missed** — not a new idea.

## 4. What must become true

**R1 — RESTATED IN v3 AS A STATE MACHINE. Two landmark-based attempts failed; this one enumerates
what the final line may truthfully CLAIM, and derives the flag from that.**

⛔ **The history, kept because it is the reason for the shape.** v1 keyed on *"did we reach the
`copytree` at `:630`"* — Blocking, both halves: `:646` returns after it. v2 keyed on *"did
`run_mutations` return"* — Blocking, both halves: `:663` can return with the run declared NOT CHECKED.
**Both were positional proxies for one property — is this tally a trustworthy measurement — and each
was true while the property was false.** A third proxy would be the third instance.

### The five states, enumerated from the measured call taxonomy

| | state | return | `files` | `mutations` | the line may claim |
|---|---|---|---|---|---|
| **S0** | manifests unusable (`load_manifests` problems) | `:586` | 0 | 0 | **no tally at all** |
| **S1** | declared coverage disagrees with the manifests | `:626` | 0 | 0 | **no tally at all** |
| **S2** | control red **before** any mutation | `:646` | **N > 0** | 0 | **no tally at all — including the file count** |
| **S3** | measured, after-control green | `:663` | N | M | **the full tally; this is a verdict** |
| **S4** | measured, then **invalidated** by the after-control | `:663` | N | M | **the numbers exist but are NOT a verdict** |

Measured by wrapping `mutate_delivered` across the whole suite (158/158): S3 = call 1, S2 = call 2,
S0/S1 = calls 3-5 and 7, **S4 = call 6 `(ok=False, after_red=True, 1, 1, 0)`**.

### R1 — the requirement

**S0, S1, S2:** the final line contains **no** mutation count, **no** survivor count and **no** file
count, and says the harness did not run. *(R1a: S2's `N file(s)` counts control runs, which measure
nothing about mutations — suppressing only the mutation/survivor pair still leaves it asserting work.)*

**S3:** unchanged from today, byte for byte.

**S4:** the tally may be printed — the numbers are real — but the line must state that the run was
invalidated, so `0 survivor(s)` cannot be read as "everything was caught". `:659-662` already says
this in prose; the final line must not contradict it.

### R2 — the flag is three-valued, and each transition sits where the FACT becomes true

`ev["verdict"]`, not a boolean:

| value | set at | because that is where |
|---|---|---|
| `"not-run"` | `:584`, the initializer | nothing has been measured yet |
| `"measured"` | `:648`, where `ev["mutations"]` is assigned | `run_mutations` has returned real counts |
| `"invalidated"` | `:657`, beside `ok = False` | the after-control has just falsified them |

⚠ **A boolean cannot carry this.** S3-with-survivors and S4 are **both** `ok=False` — which is why
option (c) was refuted in round 1, and why v2's two-valued flag could not see S4. **Three states
require three values.**

**R3** (unchanged): the distinction is carried in the return value, never re-derived at the caller.
**R4** (unchanged): `--mutate`'s final line names what it measured, per `:2107`'s precedent.

**R2.** When the harness *does* run, the final line is unchanged. This spec changes no green output.

**R3.** The distinction must be **carried in the return value**, not re-derived at the caller by
testing whether `ev["files"]` is empty. A caller re-deriving state the callee already knew is the
shape the reviews keep finding.

**R4.** `--mutate`'s final line must name what it measured, matching `:2107`'s precedent.

## 5. Open question for the reader — one, and it is a real fork

**How should the "did not run" state be carried?** Three shapes, all satisfying R1–R4:

⟳ **v3 — the fork is NARROWER than it looks, because R2 settles the arity.** Three states need three
values; only the carrier is open.

| | shape | cost |
|---|---|---|
| **a** | `ev["verdict"]` ∈ `{"not-run","measured","invalidated"}`, transitions at `:584` / `:648` / `:657` | smallest diff; adds one key every reader of `ev` must know about |
| **b** | a fourth return value — `mutate_delivered` returns `(ok, report, ev, verdict)` | explicit; touches **8** call sites — 7 in `_self_test`, 1 in `main` |
| **c** | the caller branches on `ok` | ⛔ **REFUTED TWICE.** `ok=False` covers S2, S4 *and* S3-with-survivors (`:773`, `:779`). It cannot separate the three states, which is the whole requirement |

**Recommendation: (a).** `ev` is already the channel through which this function reports what it did,
and `ev.get(...)` is already used at `:843`, `:857` and `:917`, so an added key is structurally safe
(verified, r1 L1).

⛔ **Two superseded claims, kept rather than quietly dropped.** v1 said (a) flips *"after `copytree`"*
— wrong, S2. v2 said (a) flips at `:648` and is boolean — right about the point, wrong about the
**arity**, because it could not see S4. ⚠ v1 also said (b) touches "9 call sites"; it is **8** (r1 Low,
Codex): `:1866`, `:1875`, `:1883`, `:1897`, `:1909`, `:1930`, `:1943`, plus `:2069` in `main`.

## 6. Falsifiers

Each must be **run before being written into the plan** — F8 in the sibling plan was wrong in four
consecutive versions for four different reasons, every one of which a single execution would have
caught.

**F1 — the defect, without the fix. ✅ RUN 2026-09-03, on a temp copy, and it took two attempts.**

Add an entry with a **genuinely distinct edit anchor** to any `scripts/mutations/*.json`, leave
`EXPECTED_MUTATIONS` alone, run `--mutate <tmp>`. Measured:

```
✗ scripts/check-selftest-counts.py: manifest holds 9 mutation(s), expected 8. …
FAILED — delivered scripts mutated: 0 file(s), 0 mutation(s), 0 survivor(s)
exit=1
```

⚠ **The first attempt cloned `entry[0]` and tested a different return.** It tripped
`repeats the edit anchors of an earlier entry`, emitted at **`:562` inside `load_manifests`
(`:516-573`)**, so it returned at **`:586`** — not the drift return at `:626`. **The distinct anchor
is part of the falsifier, not an incidental detail.** That is the F8 failure from the sibling plan,
reproduced here in one attempt and caught in the next.

**The wrong run is retained as evidence, not discarded** (r1 M1): together with the corrected run and
the control-failure trial it means **three of the four returns are exercised**, which is what
establishes R1's scope.

**F2 — the fix. ONE RUN PER STATE, five in total.** v1 had one prose sentence; v2 had three shell
comments (r1/r2 Cx-Medium, twice). **v3 has one per row of R1's table, because the table is now the
thing being satisfied** — a falsifier set that does not cover every enumerated state is how S4 was
missed in the first place.

```bash
T=$(mktemp -d); cp -R scripts "$T/scripts"
# --- F2-S0 -> :586  clone entry[0] of any manifest (duplicate edit anchors)
python3 - "$T" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1])/"scripts/mutations/check-selftest-counts.json"
d=json.loads(p.read_text()); e=dict(d[0]); e["name"]="F2-S0 duplicate anchors"; d.append(e)
p.write_text(json.dumps(d,indent=2))
PY
# --- F2-S1 -> :626  add an entry with a DISTINCT anchor, leave EXPECTED_MUTATIONS at 8
# --- F2-S2 -> :646  prepend `raise SystemExit(1)` above `if __name__ ==` in a mutation target
# --- F2-S3 -> :663  unmodified tree
# --- F2-S4 -> :663  a target that passes the control and fails AFTER the sequence.
#                    Use the shipped fixture shape: check-plan-code.py:1918-1933 — `thing.py`
#                    counts its own runs in `runs.txt` and returns 1 on the THIRD, so the
#                    before-control (1) and the mutated run (2) are green and only the
#                    after-control (3) is red. DO NOT invent a new one; that fixture is
#                    already asserted by a named case.
python3 scripts/check-plan-code.py --mutate "$T"; echo "exit=$?"
```

**Pass conditions, per state:**

| | expected final line | exit |
|---|---|---|
| **S0 / S1 / S2** | the diagnostic message, and **none of** `mutation(s)`, `survivor(s)`, `file(s)` | 1 |
| **S3** | byte-identical to today's `OK — …` | 0 |
| **S4** | the tally **plus** an explicit statement that the run was invalidated | 1 |

⚠ **S4 is the one that must not be skipped for being awkward to build.** It is the only state where
the numbers are real *and* meaningless, and it is the state two rounds of reviewers had to find by
reading. The fixture already exists — there is no excuse for asserting it by argument.

**F3 — no green output moved.** `python3 scripts/check-plan-code.py --mutate .` prints a final line
byte-identical to today's. **Today's line, run by the Codex half:**
`OK — delivered scripts mutated: 7 file(s), 162 mutation(s), 0 survivor(s)`, exit 0.

**F4 — the mutation, written out.** v1 named no anchor, no target and no case, which by this spec's
own rule is a vacuous falsifier (r1 Cx-Medium). The entry appended to
`scripts/mutations/check-plan-code.json` is:

⟳ **v3: THREE transitions means the mutation must name WHICH one it deletes.** Deleting the `:657`
transition is the one that matters — it is the S4 guard, the state two rounds missed, and deleting it
silently collapses S4 into S3.

```json
{
  "name": "the invalidated transition is deleted, so an after-control failure reports a verdict",
  "file": "scripts/check-plan-code.py",
  "edits": [["<the ev['verdict'] = 'invalidated' assignment as delivered at :657>", ""]],
  "expect": ["<the named F2-S4 case asserting an invalidated run does not read as a verdict>"]
}
```

⚠ The `:648` transition is separately covered: deleting it collapses S3 into `"not-run"`, which F2-S3
catches by losing the `OK —` line. **The `:657` one has no such second reader**, which is exactly why
it needs the mutation.

The `expect` string **must name a case that exists** — `check-plan-code.py:723` parses only lines
beginning `[FAIL] `, so a case whose name does not match is reported as zero red cases, not as a
mismatch. **Write the case first, run it red, then write the manifest entry.**

`EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` rises **21 → 22** and the sum literal **162 → 163**,
in the same commit, with the reason in the message.

## 7. What this does NOT fix — stated, not glossed

**Round 4's Blocking on the guard-inventory plan is a PLAN defect and survives this spec.** T4
promises a sixth `read_population` mutation; T7 leaves `EXPECTED_MUTATIONS` at 5. The count must be
decided in one place, and this change only makes the resulting failure *legible*. The architecture
review's claim that candidate 2 would "dissolve" that Blocking was **withdrawn with candidate 2**.

⛔ **DO NOT COPY A GLOBAL TOTAL BETWEEN THESE TWO DOCUMENTS** (r1 Cx-Medium — a dependency v1 missed
entirely). v1 asserted the sibling plan's corrected sum is **168**. That is true **only if this spec
has not landed**. This spec raises the sum 162 → 163 (F4), so:

| order | sibling plan's `EXPECTED_MUTATIONS` sum |
|---|---|
| sibling plan lands first | **168** |
| **this spec lands first** | **169** |

**The stable part of that instruction is "six entries, `EXPECTED_MUTATIONS` 6"** — a per-file count,
which no other slice can move. The global total is not stable across slices and this spec should
never have quoted it. **The sibling plan must derive its sum from the file at the time it lands**, and
this section states the dependency instead of a number.

## 8. Limits

- Touches one script. No product code, no schema, no money path.
- The `<plan> --compare --verify-evidence` mode is untouched and remains out of CI.
- Does not address finding **A** (four inventories, nothing reconciles them). That is candidate 1's
  frame and is deliberately not in scope.

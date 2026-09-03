# The mutation harness's final line must say whether it measured anything

> **v2 — 2026-09-03.** Round 1 folded, BOTH halves
> ([claude](../../reviews/spec-mutation-drift-report-contract-r1-claude.md),
> [codex](../../reviews/spec-mutation-drift-report-contract-r1-codex.md)). Both independently
> returned **NOT CONVERGED** on the same Blocking: **the recommended flip point was wrong and would
> have left the worst case unfixed.** v1's §1, §2, §4, §5, §6 and §7 all changed.

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

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

**R1 — RESTATED IN v2. The predicate is "were mutations RUN", not "did we reach `copytree`".**

When `run_mutations` has not returned — i.e. any return at `:586`, `:626` or `:646` — the final line
**must contain neither a mutation count nor a survivor count, and must not report a file count that
implies work was measured.** It must say the harness did not run.

⛔ **v1 said "does not reach the `copytree` at `:630`". That was the Blocking, found by both review
halves.** `:646` returns *after* `:630`, so a flag flipped there would already be `True` on the one
path where the output is most misleading. **A line number is a proxy for a state; this one had
drifted from the state it stood for.**

**R1a.** The file count is part of the claim. `:646` prints `7 file(s)` because `ev["files"]` is
populated at `:639` for the *control* runs — which measure nothing about mutations. Suppressing only
the mutation/survivor pair still leaves `7 file(s)` asserting work.

**R2.** When the harness *does* run, the final line is unchanged. This spec changes no green output.

**R3.** The distinction must be **carried in the return value**, not re-derived at the caller by
testing whether `ev["files"]` is empty. A caller re-deriving state the callee already knew is the
shape the reviews keep finding.

**R4.** `--mutate`'s final line must name what it measured, matching `:2107`'s precedent.

## 5. Open question for the reader — one, and it is a real fork

**How should the "did not run" state be carried?** Three shapes, all satisfying R1–R4:

| | shape | cost |
|---|---|---|
| **a** | a sentinel key in `ev`, e.g. `ev["ran"] = False` set at `:584`, **flipped at `:648`, immediately after `run_mutations` returns** | smallest diff; adds a key every reader of `ev` must know about |
| **b** | a distinct return state — `mutate_delivered` returns `(ok, report, ev, ran)` | explicit; touches **8** call sites — 7 in `_self_test`, 1 in `main` |
| **c** | the caller branches on `ok` before formatting | zero new state, but **violates R3** — `ok=False` is also returned by `:646` *and* by a completed run with survivors (`:773`, `:779`), so the caller would print no tally for a real failure. **Rejected: it loses information on the path that most needs it** |

⛔ **v1 said (a) flips "after `copytree`". WRONG — see R1.** The flip is at **`:648`**. Flipping any
earlier marks a control-failure run as measured.

**Recommendation: (a), flipped at `:648`.** `ev` is already the channel through which this function
reports what it did, and `ev.get(...)` is already used at `:843`, `:857` and `:917`, so an added key
is structurally safe (verified, r1 L1).

⚠ **v1 said (b) touches "9 call sites". That was wrong — it is 8** (r1 Low, Codex): `:1866`, `:1875`,
`:1883`, `:1897`, `:1909`, `:1930`, `:1943` in `_self_test`, plus `:2069` in `main`. Corrected rather
than quietly dropped, because a count nobody checked is what this whole slice keeps finding.

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

**F2 — the fix. THREE runs, one per early return** (v1 had one, prose-only; r1 Cx-Medium).

```bash
T=$(mktemp -d); cp -R scripts "$T/scripts"
# F2a -> :586   clone an existing manifest entry (duplicate anchors)
# F2b -> :626   add an entry with a DISTINCT anchor, leave EXPECTED_MUTATIONS alone
# F2c -> :646   append `raise SystemExit(1)` above `if __name__ ==` in one mutation target
python3 scripts/check-plan-code.py --mutate "$T"; echo "exit=$?"
```

**Pass condition, all three:** the drift/CANNOT-RUN message is present, exit is `1`, and the final
line contains **none of** `mutation(s)`, `survivor(s)`, `file(s)`.

**F3 — no green output moved.** `python3 scripts/check-plan-code.py --mutate .` prints a final line
byte-identical to today's. **Today's line, run by the Codex half:**
`OK — delivered scripts mutated: 7 file(s), 162 mutation(s), 0 survivor(s)`, exit 0.

**F4 — the mutation, written out.** v1 named no anchor, no target and no case, which by this spec's
own rule is a vacuous falsifier (r1 Cx-Medium). The entry appended to
`scripts/mutations/check-plan-code.json` is:

```json
{
  "name": "the ran flip is deleted, so a control failure reports a tally",
  "file": "scripts/check-plan-code.py",
  "edits": [["<the ran-flip statement as delivered at :648>", ""]],
  "expect": ["<the named case asserting a control-failure run prints no tally>"]
}
```

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

# The mutation harness's final line must say whether it measured anything

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

Reproduced twice this session, on a temp copy of `scripts/`, never the repo:

| trial | first report line | `ev` |
|---|---|---|
| delete `scripts/mutations/page_chrome.json` | `scripts/page_chrome.py: manifest holds 0 mutation(s), expected 11` | `mutations=0, survivors=0` |
| add `scripts/mutations/zzz-undeclared.json` | `target scripts/zzz-undeclared.py does not exist` | `mutations=0, survivors=0` |

## 2. Severity — 🟡, and the downgrade is deliberate

The review filed this 🟠. **That was too high, and the correction belongs here.**

- `:2072` already prints `FAILED —`, and `:2075` returns `1`. **There is no false-green path.**
- A careful reader sees `0 file(s)` and can infer nothing ran.

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

**R1.** When `mutate_delivered` returns **by any path** that does not reach the `copytree` at `:630`,
the final line **must not contain a mutation count or a survivor count.** It must say the harness did
not run.

⚠ **"By any path" is load-bearing, and was learned by running the control wrongly.** The first F1
attempt cloned an existing manifest entry, so it tripped the **duplicate-anchor** check rather than
the count check — and produced *the same* `FAILED — … 0 mutation(s), 0 survivor(s)` line. The defect
is therefore a property of **every early return**, not of the drift branch. A fix scoped to the count
check would leave the other paths intact. See §6 F1.

**R2.** When the harness *does* run, the final line is unchanged. This spec changes no green output.

**R3.** The distinction must be **carried in the return value**, not re-derived at the caller by
testing whether `ev["files"]` is empty. A caller re-deriving state the callee already knew is the
shape the reviews keep finding.

**R4.** `--mutate`'s final line must name what it measured, matching `:2107`'s precedent.

## 5. Open question for the reader — one, and it is a real fork

**How should the "did not run" state be carried?** Three shapes, all satisfying R1–R4:

| | shape | cost |
|---|---|---|
| **a** | a sentinel key in `ev`, e.g. `ev["ran"] = False`, set at `:584` and flipped after `copytree` | smallest diff; adds a key every reader of `ev` must know about |
| **b** | a distinct return state — `mutate_delivered` returns `(ok, report, ev, ran)` | explicit; touches every call site, including 7 in `_self_test` |
| **c** | the caller branches on `ok` before formatting | zero new state, but **violates R3** — `ok=False` is also true for a run that completed with survivors, so the caller would print no tally for a real failure. **Rejected: it loses information on the path that most needs it** |

**Recommendation: (a).** (b) is more honest about the contract but rewrites 9 call sites for one bit,
and `ev` is already the channel through which this function reports what it did. **(c) is refuted
above and is recorded so it is not re-proposed.**

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

⚠ **The first attempt cloned `entry[0]` and tested the wrong branch** — it tripped
`repeats the edit anchors of an earlier entry` instead of the count check. **The distinct anchor is
part of the falsifier, not an incidental detail**, and writing F1 without running it would have
shipped a control that never reaches the branch it names. That is the F8 failure from the sibling
plan, reproduced here in one attempt and caught in the next.

**The wrong run is retained as evidence, not discarded:** it emitted the *same* final line, which is
what establishes R1's "by any path".

**F2 — the fix.** Same input, after the change: the drift message is present and the last line
contains **neither** `mutation(s)` nor `survivor(s)`.

**F3 — no green output moved.** A clean `--mutate .` prints a final line byte-identical to today's.

**F4 — the mutation.** A manifest entry that deletes the `ran` flip must redden a **named** case, per
`check-plan-code.py`'s own contract. `EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` rises from 21
to 22 and the sum literal from 162 to 163, **in the same commit**, with the reason in the message.

## 7. What this does NOT fix — stated, not glossed

**Round 4's Blocking on the guard-inventory plan is a PLAN defect and survives this spec.** T4
promises a sixth `read_population` mutation; T7 leaves `EXPECTED_MUTATIONS` at 5. The count must be
decided in one place — **six entries, `EXPECTED_MUTATIONS` 6, sum 168** — and this change only makes
the resulting failure *legible*. The architecture review's claim that candidate 2 would "dissolve"
that Blocking was **withdrawn with candidate 2**.

## 8. Limits

- Touches one script. No product code, no schema, no money path.
- The `<plan> --compare --verify-evidence` mode is untouched and remains out of CI.
- Does not address finding **A** (four inventories, nothing reconciles them). That is candidate 1's
  frame and is deliberately not in scope.

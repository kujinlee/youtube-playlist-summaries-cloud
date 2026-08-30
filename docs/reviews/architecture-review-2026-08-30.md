# Architecture Review #4 — 2026-08-30

> **Anchor:** `project-dashboard` — **ADRs consulted:** 0010 (documents declare their anchor). None
> re-litigated.
> **Trigger:** `docs/dev-process.md` Phase 6, second arming condition — four adversarial rounds
> without convergence, on PR #178. The user chose Phase 6 over a fifth round.
> **Subject:** the dashboard tooling and the guard stack around it — `scripts/gen-dashboard.py`,
> `scripts/check-plan-code.py`, `scripts/mutations/*.json`, and the 24 `scripts/check-*.py` guards.

**Method.** Coordinator-written. A subagent was dispatched for breadth and went idle without
delivering; rather than wait, every number below was measured in this session with a command I can
re-run. That is what `dev-process.md` requires of the coordinator anyway — *agent output is a lead,
not a finding*. **One suspected Blocking was refuted by that discipline** and is recorded in
§*Refuted* rather than filed.

---

## The one-paragraph answer

**Four review rounds on PR #178 found 31 findings, and the overwhelming majority were defects in the
GUARDS added by the previous round, not in the renderer they guard.** The dashboard now carries a
**seven-layer verification stack** where each layer exists to prove the layer below cannot go
vacuous — and every layer is itself code that can go vacuous. Meanwhile the renderer those layers
protect **has no seam**: four page generators re-implement inline markup independently, so the
behaviour that took four rounds to harden is hardened in exactly one of the four places it lives.
**The project has been paying for depth in the verification stack and shallowness in the thing
verified.**

---

## 1. What the four rounds were actually finding

Attribution was measured, not recalled — `git show <sha>:scripts/gen-dashboard.py | grep <symbol>`:

| symbol | first appears at | found defective by |
|---|---|---|
| `_write_sandbox`, `_inline_scan` | `df79f0c` (round 1's fix) | round 2 — 5 of its 6 findings |
| `_trim_url_tail`, `ENTITY_TAIL`, `_close_orphan_markup` | `dee62f2` (round 3's fix) | round 4 — all of its findings |
| manifest entry `UNSANDBOXED` | added `df79f0c`, removed `7bbabad` | round 2's H2 — it could destroy the live page |

Round 2's findings are in round 1's fixes. Round 4's are in round 3's. **The defect rate in
newly-added guard code did not decay across four rounds.** The renderer's own defects were largely
exhausted in round 1.

## 2. The seven-layer stack, read out of the code

| # | layer | file:line |
|---|---|---|
| 1 | the renderer | `gen-dashboard.py` product code (1,153 lines) |
| 2 | 185 `case()` assertions | `gen-dashboard.py:_self_test` (1,206 lines — **49% of the file**) |
| 3 | 61 mutations, each must redden a **named** case | `scripts/mutations/gen-dashboard.json` |
| 4 | `EXPECTED_MUTATIONS` — per-file entry count | `check-plan-code.py:302` |
| 5 | a literal `73` — pins the **sum** of layer 4 | `check-plan-code.py:1521` |
| 6 | 136 cases guarding the mutation runner | `check-plan-code.py:_self_test` (896 lines — **56%**) |
| 7 | `# 136 cases` in the docstring, checked by `count_drift` | `check-plan-code.py:694`, `:702` |

Layers 2–5 each acquired a defect during rounds 1–4. `check-plan-code.py:704-710` already records
the shape in its own words, from a different review: *"Extracting the function bought coverage of the
function; the wiring inherited the same blind spot."*

This is not an argument that the stack is wrong. It is an argument that **its cost is now the
dominant cost of changing the dashboard**, and that nobody has decided that deliberately.

---

# Findings

## A — 🟠 The guard inventory cannot see a guard that nothing calls

**REPRODUCED.** `scripts/check-ratchet-contract.py:67-81`, `:190`.

The repo has an inventory that enumerates every `check-*.py` and enforces a contract on it. Its
population comes from two sources (`discover_ratchets`), and its docstring is explicit that this is
deliberate — *"A registry list would be evadable by simply not registering."* The two sources are:

1. scripts named by a **CI step** in `.github/workflows/ci.yml`;
2. scripts whose **own docstring** self-declares as a ratchet.

Both presuppose the guard is already wired or already labels itself. Measured:

```
$ python3 scripts/check-ratchet-contract.py
ratchets discovered (14): …
ratchet contract OK
```

**14 discovered, of 24 on disk.** And the contract enforces R1 (`--self-test` exists) and R2 (no
fail-open handler) — honestly declaring that only 2 of its 6 rules are statically decidable. But
**"has a caller" is statically decidable and is not one of the six.**

Consequence — measured with `grep -rn <name> --include=*.sh --include=*.yml --include=*.py`,
excluding `docs/`:

| script | executed by |
|---|---|
| `scripts/check-plan-task-order.py` | **nothing** (0 hits in `ci.yml`, gates, hooks) |
| `scripts/check-producer-enumeration.py` | **nothing** (0 hits) |

**This class was named by Phase 6 #1.** `check-arch-findings.py`'s own docstring describes that
review's Finding #2 as *"a correct module exists and nobody calls it."* A ratchet was built for that
instance. `scripts/check-schema-gates.sh` records the same class three more times in comments —
`:52` (*"the live gate existed for a whole day and NOTHING CALLED IT"*), `:86`, `:109-110`
(*"named in the roadmap and the plan and invoked by NOTHING"*). **Four recorded instances, four
instance-fixes, and the check that would find the class was never built** — even though the
inventory to build it on already exists.

## B — 🟠 `dev-process.md` lists an unexecuted script under "What is mechanically enforced"

**REPRODUCED.** `docs/dev-process.md:144`.

> `| scripts/check-producer-enumeration.py | every guarded value's producer count matches its defining expression (--self-test: 11 cases) |`

It is in the table whose heading is *What is mechanically enforced*. Nothing executes it. This is
**the same row shape the document corrected for a different script at r12**, and that correction is
still visible two rows down — *"this row said 9 and, worse, listed the script as mechanically
enforced while nothing executed it."* The correction fixed the instance; the row above it is the
class, still live.

## C — 🟢 A docstring case-count drifts on a script nothing runs

**REPRODUCED.** `scripts/check-plan-task-order.py:26` says `# 12 cases`; the suite reports **16/16**.
`check-plan-code.py` has `count_drift` (`:694`) for exactly this, applied to its own docstring and
no other script's. Low because the script is unreachable anyway — but it is the *evidence* for A:
an unrun guard rots silently, and this one has.

## D — 🟠 The inline renderer has no seam; four generators re-implement it

**REPRODUCED.** Counts are `grep -c` over each file.

| generator | lines | inline-markup refs | escaping | contrast |
|---|---|---|---|---|
| `gen-dashboard.py` | 2,458 | 102 | 28 | 30 |
| `gen-backlog-page.py` | 1,898 | 62 | 14 | 17 |
| `gen-goals-page.py` | 508 | 46 | 0 | 0 |
| `explainer-serve.py` | 1,047 | 37 | 0 | 0 |

No generator imports another's renderer. **And the project already knows the pattern** — it uses
exactly the right seam for a different concern, with the arrow documented at
`gen-dashboard.py:402-408`:

> *"The dependency arrow points generator → gate, never the reverse… a page importing a gate is what
> keeps their readings identical by construction."*

`gen-backlog-page.py:74` does the same for `check-docs.py`'s split rule. So the mechanism, the
justification, and the idiom are all present — applied to **grammar** and to the **doc split rule**,
never to **rendering**. `gen-backlog-page.py:1432` and `:1715` are comments observing that
`gen-dashboard.py` had the same contrast holes, found separately, on a different day.

**Deletion test.** Delete `_inline` from `gen-dashboard.py`: complexity does not vanish, it
**reappears in three other generators** — where it already partly lives. That is the signature of a
module earning its keep with no seam to be reached through.

---

# Refuted — recorded because I nearly filed it

I suspected `check-paid-caller-arrival.py` was a fifth orphan: `grep` for its filename in
`check-schema-gates.sh` returned only comment lines, and `dev-process.md`'s r12 note claims it was
wired as gate 15. Reading the file rather than grepping it shows
`check-schema-gates.sh:254` — `run "15/15 backlog 26's money trigger (no non-test caller reaches
record_artifact)"`. **The gate is real and the doc's claim is true.** A grep for the *name* missed a
`run` line that describes the gate in *prose*. Filed nowhere; noted here because it is the same
"searched for the mechanism, not the property" shape this milestone kept producing.

---

# What we decided this milestone that isn't written down

The question `dev-process.md` says no tool can answer.

1. **That the dashboard's guard stack should be seven layers deep.** No ADR, no spec sentence, no
   decision record. It accreted one round at a time, each layer individually justified by a real
   defect. Nobody ever chose the aggregate — which is precisely the *"individually thoughtful, fail
   as a set"* verdict this project keeps reaching about its own documentation, now true of its
   verification.
2. **That `--mutate .` is allowed to execute the delivered scripts with the user's real `HOME`.**
   Rounds 2–4 spent significant effort making individual manifest entries safe under that decision.
   The decision itself — rather than running the whole harness under a redirected `HOME` — was never
   stated or examined.
3. **That a truncated headline may be silently altered to keep its markup balanced.** Round 3 chose
   to append closers rather than cut back; round 4 found that choice fabricating text. It is a real
   product decision about the reader's prose and it lives only in a code comment.

---

# Candidates (no interfaces proposed yet — see the covering message)

1. **Give the inline renderer a seam** (Finding D).
2. **Make the guard inventory's population the filesystem, and add "has a caller" to the contract**
   (Findings A + B + C in one).
3. **Decide the `HOME` question once**, instead of per manifest entry (undocumented decision 2).
4. **Flatten the verification stack** — retire layers whose defect-finding rate no longer justifies
   their own defect rate (§2).

**Nothing here has been filed to `docs/backlog.md` or the roadmap.** Filing is the user's step.

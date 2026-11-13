Reviewed head: 35f9fe70

> **For the r4 fold of `sweep-pin-select` (PR #526, backlog #533).** Triggered by **THRASHING** in the component
> `merge-ready-pins`: r2 F2 was caused by r1's fix, and r3 F1 by r2's fix (`docs/dev-process.md` → *Phases*).
>
> **Verdict: redesign.** Replace the STATIC proof ("the harness binds `PINS_FILE` once, to this literal") with a DYNAMIC
> comparison: **the pins the head harness HOLDS after import must equal the pins HEAD's `PINS_FILE` displays.** This is
> candidate (e) below. It removes `module_writes`, `harness_binding_problems`, `PINS_BINDING` and `harness_binds_pins`.
> On the routes measured, it closes every import-time route that any round found. The routes it leaves are runtime or
> context-sensitive harness code, which is backlog #535's class and which master also has. **BLOCKERs: none.** One item
> filed: backlog #536, the redesign itself.

# Phase 6 architecture review (narrow, triggered by thrashing): the pins binding check in `scripts/check-merge-ready.py`

Scope: `PINS_BINDING`, `_SCOPES`, `module_writes`, `harness_binding_problems`, `harness_binds_pins`, `pin_pair` and
`_pins_reader` in `scripts/check-merge-ready.py`, plus `PINS_FILE`, `own_pins_path`, `read_pins`, `EXPECTED_MUTATIONS` and
`own_pin_problems` in `scripts/check-plan-code.py`. Read only.

Read first:
- `CONTEXT.md` (*Soundness check*);
- `docs/adr/`: no ADR covers the mutation pins or the merge gate's pin reading, so none is re-litigated;
- backlog #533, #534 and #535;
- the r1 to r3 reviews and the r1 and r2 coordinator documents;
- `docs/review-method.md` → *Can a redesign remove it?*

Nothing under `.claude/plans/` was read. The measurement script is outside the repository, at
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/arch-sps/measure.py`.
Its output is `results.txt` in the same directory.

## 1. Thrashing or prose floor?

**Thrashing, and design-caused.** Each fix-induced finding is a behavioural defect with an input that was run:

| Round | Finding | Fix-induced by | What it does |
|---|---|---|---|
| r1 | Claude F1 | (the move itself) | A plain `PINS_FILE = "…/pins_v2.py"` rebinding plus a new pins file with a lowered pin read READY |
| r2 | Codex F1, Medium | not fix-induced: the class | `globals()['PINS_FILE']`, an imported `PINS_FILE`, or an `own_pins_path()` returning another file passed. Declined, filed as #535 |
| r2 | Codex F2, Low | r1's `ast.walk` count | A helper's LOCAL `PINS_FILE` made the real harness CANNOT RUN |
| r3 | Claude F1, Low | r2's `module_writes` | `global PINS_FILE` in a CLASS body rebinds the global and is not counted |

**The cause, in one sentence: the check proves a property of the harness's SPELLING, when the property wanted is about its
VALUE.** The claim is "the harness enforces the pins this script reads". The check approximates it with "the harness's
source writes `PINS_FILE` exactly once, at module level, as this literal". Python has many ways to bind a module global:
`=`, `global` in a function, `global` in a class, `globals()[…]`, `import … as`, `def`, `except … as`, `match` capture,
`exec`, and others. Each fold therefore taught the scope model one more of them:
- r1 counted too much, so it refused locals;
- r2 counted function scopes but not class scopes;
- the next fold would be `ast.ClassDef`, and the round after that would find the next spelling.

`CONTEXT.md`'s *Soundness check* entry names this shape: a hand-rolled reader cannot be made correct.

## 2. Can a redesign remove it?

**Yes.** `check-merge-ready` ALREADY imports the head harness: `_pins_reader(PINS_READER)` loads the working-tree
`check-plan-code.py` to borrow `pin_display`. That import runs every module-level statement, so after it the module's
`EXPECTED_MUTATIONS` is the dict the harness actually holds, however it was bound. Comparing that dict with the display
`pins_at(run, "HEAD")` already reads tests the claim itself, not one spelling of it. This is the repository's rule *assert
the property, not the mechanism*.

### The measurement

`measure.py` takes a `git archive HEAD scripts` copy for each variant and edits the copy's `check-plan-code.py`. It also
writes `scripts/mutations/pins_v2.py` with `check-anchors.py` lowered from 5 to 4, and leaves `expected_mutations.py` at 5.
`HOME` is redirected. It then:

1. calls the branch's `harness_binding_problems` on the edited source (the **static** column);
2. imports the edited harness the way `_load` does (`spec_from_file_location` and `exec_module`);
3. compares `EXPECTED_MUTATIONS["scripts/check-anchors.py"]` (the value the harness holds) with `pin_display` of the
   unchanged `PINS_FILE` (the value the display shows). The **dynamic** column refuses when they differ.

For a bypass route, refused is the right answer. For a legitimate shape, refused is a false refusal.

| Variant | Static (the branch today) | Held / display | Dynamic (e) |
|---|---|---|---|
| R1 plain `PINS_FILE = v2` (r1 F1) | refused | 4 / 5 | **refused** |
| R2 `globals()['PINS_FILE'] = v2` (r2 F1) | **passes** | 4 / 5 | **refused** |
| R3 `from _redir import PINS_FILE` (r2 F1) | **passes** | 4 / 5 | **refused** |
| R4 `class _Cfg: global PINS_FILE; PINS_FILE = v2` (r3 F1) | **passes** | 4 / 5 | **refused** |
| R5 `own_pins_path()` returns v2 (r2 F1) | **passes** | 4 / 5 | **refused** |
| R6 module `globals()['EXPECTED_MUTATIONS'] = {…4}` (master E1) | **passes** (`own_pin_problems` catches it) | 4 / 5 | **refused** |
| R7 `exec("PINS_FILE = v2")` | **passes** | 4 / 5 | **refused** |
| R8 a write inside a function called at run time (master E2) | passes | 5 / 5 at import, 4 after the call | **passes** |
| R9 `if __name__ == "__main__": PINS_FILE = v2` | refused | 5 / 5 under import | **passes** |
| R9b the same through `globals()` | **passes** | 5 / 5 under import | **passes** |
| L0 the unmodified harness | `[]` | 5 / 5 | `[]` |
| L1 a helper's local `PINS_FILE` (r2 F2) | `[]` | 5 / 5 | `[]` |
| L2 a class attribute `PINS_FILE` | `[]` | 5 / 5 | `[]` |
| L3 a module-level comprehension target (r3 F2) | **false refusal** | 5 / 5 | `[]` |
| L4 an outer local whose nested function says `global` (r3 F2) | **false refusal** | 5 / 5 | `[]` |

⚠ **What was measured, and what was not.** The table measures the PREDICATE, meaning the held dict against the display,
on real imports of edited copies. It does not measure the WIRING into `pin_pair`, because the redesign is not built. The
fold must show it end to end (§5).

### The remaining routes, R8 and R9, are master's class

Both need harness code whose effect differs between importing the module and running it. R8 writes at run time. R9 changes
behaviour on `__name__`, or on `sys.argv` and similar. Any check that observes the harness in a context other than CI's
has this hole. Master has the same hole at the same cost: its E2 (#535) is one line in `load_manifests`, and every gate is
green. Every such route edits `check-plan-code.py`, which is `SWEEP_HARNESS`. So the PR goes FULL and the edit is in the
reviewed diff. R9's plain spelling is the one route the static check closes and (e) does not. Its `globals()` spelling
(R9b) already passes the static check today, so the static check does not really close R9 either; it only makes R9 one
spelling harder.

## 3. The candidates

"Routes" counts the ten routes above, R1 to R9b. Master's baseline is R6 refused (its self-assertion reads `__file__`) and
the R8 class open. The routes that only the branch opened are the redirects R1 to R5 and R7.

| | Candidate | Routes still open | False refusals | Size of the check | Does the code that attracts findings shrink? |
|---|---|---|---|---|---|
| (a) | Hard-code the path in `own_pins_path`, with no module name; `check-merge-ready` only checks that the file exists | R5 becomes a plain one-line literal edit, as easy as r1 F1. R2 and R3 move to rebinding `own_pins_path` itself. R8 and R9 stay open | none | about −80 lines | yes, it is deleted, but r1's route comes back in a new spelling. A static check on the literal would recreate the treadmill |
| (b) | HOLD (owner-visible) any diff that touches the pin-loading code | **coarse** (any `check-plan-code.py` change): none, and it also closes R8 and R9, which is better than master. **fine** (by function name): any new function that writes `EXPECTED_MUTATIONS`, which is R8's shape | **coarse: about 32 of 145 master commits in the 30 days to 2026-11-06** changed harness lines that are neither pins nor comments. Each of those would be a HOLD for the owner. **fine:** low, but it needs a static map of "pin-loading code" | coarse: about 10 lines. fine: an AST scan of every write to `EXPECTED_MUTATIONS` | coarse: yes, at a large and permanent cost in owner attention. fine: no, it is the same static treadmill under another name |
| (c) | Accept the class: delete the binding check and document the bound (#535) | R1 to R5, R7, R8, R9 and R9b. R6 is still caught by `own_pin_problems` (measured) | none | about −110 lines (code, cases, 3 mutations) | yes, it is deleted. But it leaves a ONE-LINE plain redirect, more visible than E2 and as cheap |
| (d) | Keep the AST check and add `ast.ClassDef` (r3's one-token fix) | R2, R3, R5, R7, R8 and R9b; R4 is closed | L3 and L4 remain | +1 token, +1 case, +1 mutation, on top of about 81 lines and 3 mutations | **no**: it grows, and r2 has already listed the next spellings |
| **(e)** | **Compare the dict the head harness HOLDS after import with HEAD's `PINS_FILE` display (new)** | **R8, R9 and R9b only**, which is master's #535 class | none measured. A dirty working tree that changes the pins or the harness is CANNOT RUN, which fails closed and is wanted | about 81 lines and 3 mutations removed; about 10–15 lines, 2–3 cases and 1–2 mutations added | **yes**: the component that thrashed is deleted. What replaces it has no grammar to keep up with |

**Why not the others.** (d) continues the thrash by construction. (a) and (c) are honest and small, but they leave a
one-line plain edit that (e) closes at almost the same size. Coarse (b) is the only option stronger than master, but it
would HOLD about one PR in five. That buys protection against R8 and R9, which are the class master already accepts and
which the FULL sweep and review already cover. If that trade is wanted, it is backlog #535's to make on its own terms,
not this PR's.

## 4. Recommendation: (e), backlog #536

1. **Delete** `PINS_BINDING`, `_SCOPES`, `module_writes`, `harness_binding_problems` and `harness_binds_pins`. Delete their
   cases (the r1 F1 shape cases, the r2 F2 local case) and the three binding mutations named "sweep-pin-select r1 F1" and
   "r2 F2" in `scripts/mutations/check-merge-ready.json`.
2. **In `pin_pair`**, after `new = pins_at(run, "HEAD")`, read the head harness's held pins through the existing
   `_pins_reader(PINS_READER)`, inside `_cross` with `reduce=_exact_pins`. The working-tree sibling is the PR head, because
   `main()` already refuses a local HEAD that is not the PR head. When they differ, raise `PinsUnreadable` (CANNOT RUN),
   naming each target whose held value and displayed value differ. Apply this whether HEAD keeps its pins in `PINS_FILE`
   or `PINS_SCRIPT`, so there is no branch on `pins_home`.
3. **Keep the old r1 F1 case as an end-to-end case through `pin_pair`**, with `PINS_READER` pointed at a temp copy whose
   harness is redirected (R1). Add R2 and R4 as two more redirect spellings, plus L1 and L3 as accepted shapes. Each must
   go through the real import, not a synthetic string.
4. **The BOUND comment** names R8, R9 and R9b, meaning code that behaves differently when imported than when run, as
   backlog #535's class, with master's E2 as its equal-cost twin.
5. **Mutation:** "the held-versus-display comparison is skipped", killed by the R1 end-to-end case.

**FAILS IF:** after the fold, any of R1–R7 above (a module-level or import-time redirect, measured with
`check-anchors.py` lowered 5 → 4 in a new pins file) leaves `pin_pair` returning without `PinsUnreadable`; or the real
harness at the fold's head is refused.

## 5. What the fold must not take on trust

- **The wiring is unmeasured** (§2). Run R1, R2, R4 and R5 through `pin_pair`, and through `main()` with a stubbed `gh`,
  not only through the predicate.
- **`_pins_reader` is `lru_cache`d by path.** A case that edits the copy in place after the first import reads the stale
  module. Use one temp directory per variant.
- **The import is not new trust.** `pins_at` already imports the same file, so (e) adds one attribute read and no new
  execution. Do not let a reviewer re-open "executing the head harness" as new.
- ⚠ **Do not add R9 back as a static check.** It closes one spelling (R9b already passes it), and that is the treadmill
  this review exists to stop.

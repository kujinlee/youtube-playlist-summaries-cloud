# Round 2 — `hse-slice-c` — coordinator — ⟳ NOT CONVERGED (Codex half)

Codex (`gpt-6.1-sol`, `docs/reviews/codex/hse-slice-c-r2-codex.md`) reviewed `353bc475`, the round-1 fold
(de1bb2a2, 141d40b9, 353bc475) on PR #598: 4 MAJOR, 2 MINOR. It re-ran the round-1 inputs; none reopened.

REVIEW GAP: claude — alternation (rounds 2+ run ONE half; Claude takes round 3 if one is owed).

```yaml
round: 2
fixes_nontrivial: true
subject: hse-slice-c
halves:
  codex: ran
  claude: alternation
findings:
  - {id: XM1, severity: High, aim: deliverable, fix_induced: true, component: edge-reader, disposition: fixed}
  - {id: XM2, severity: High, aim: deliverable, fix_induced: true, component: edge-reader, disposition: fixed}
  - {id: XM3, severity: High, aim: deliverable, fix_induced: true, component: optional-edges, disposition: fixed}
  - {id: XM4, severity: High, aim: deliverable, fix_induced: true, component: optional-edges, disposition: fixed}
  - {id: Xm5, severity: Medium, aim: deliverable, fix_induced: true, component: closure-input, disposition: fixed}
  - {id: Xm6, severity: Medium, aim: deliverable, fix_induced: false, component: closure-arithmetic, disposition: fixed}
```

| Id | Finding |
|---|---|
| XM1 | `importlib.import_module(name='secret')` (keyword argument) escapes the AST reader, which claims import_module coverage |
| XM2 | an f-string with a conversion (`f'{NAME!s}.py'`) is dropped though the docstring says constant f-strings are followed |
| XM3 | `optional_edges` is taken on trust: a waived edge loaded UNCONDITIONALLY passes closure, and the materialised script crashes FileNotFoundError |
| XM4 | waiver validation matches the target globally: a waiver `a.py → secret.py` for an edge `a.py` lacks passes because `b.py` has it |
| Xm5 | `{}` inside `installed_files` → uncaught TypeError rc 1, not CANNOT RUN rc 2 |
| Xm6 | a reusable-workflow component's `expected_count` is never checked against its files |

**Thrashing watch.** XM1–XM5 come from the round-1 fold's own code (the new reader, the waiver). This is the FIRST
round with fix-induced findings; a round 3 with fix-induced findings in `edge-reader` or `optional-edges` arms
Phase 6 (two consecutive rounds). Round 3 is also the last before the cap: from round 4 findings are FILED unless
a BLOCKER.

## Fold

Folded in one commit on `hse-c`. Mechanism REMOVED rather than hardened where the finding allowed it: the map's
waiver is gone, and optionality is read from the file. Every case below was written from the reviewer's input
first, seen RED (114/125 before any code moved), then GREEN; no earlier case was weakened.

| Id | What changed | Witness (case in `check-shipping-sets.py --self-test`) |
|---|---|---|
| XM3 | `optional_edges` RETIRED: `load_map` refuses the key; `ComponentMap.optional_edges`, `closure(optional=)` and the waiver gap are deleted. A load is optional only in the BODY of an `if` whose test (or a conjunct of its `and`) is `P.is_file()` / `P.exists()` / `os.path.isfile(P)` / `os.path.exists(P)` with `P` reading to the load's own single path (`_Loads._tested`, `_guarded`). The closure follows an optional load the tree carries, and prints `optional: p` (not a gap) when it does not | "XM3 r2: a load is optional ONLY inside an existence guard on the same path — ..." (unconditional, another path, else branch, rebound name, lambda, function, no receiver → gap); "...run in the materialised tree without secret.py, the guarded script exits 0 and the unconditional one does not"; "a guarded load the package DOES carry is followed"; "the closure SAYS a guarded load the package omits" |
| XM4 | nothing left to key: there is no waiver. The reviewer's two inputs (an unconditional load waived, a waiver from a file without the edge) are now a REFUSED map | "XM3/XM4 r2: a map that still carries optional_edges ... is REFUSED" (both inputs and `[]`) |
| XM1 | every loader's argument is read by position OR keyword (`MODULE_LOADERS` now carries `(0, "name")`); a `**kwargs`/`*args` call whose argument cannot be placed is listed unresolved | "XM1 r2: import_module(name=...), __import__(name=...), run_path(path_name=...)" |
| XM2 | `!s` is read as the part; an unreadable part (`!r`/`!a`, a format spec, a subscript, an attribute, an unknown call, a name bound nowhere, an unbound wrapper parameter) is the sentinel `UNK`, carried in the form, and the load is LISTED (`python_loads(...)[2]`, `--closure` prints `<pkg>: unresolved: rel:line`, not a gap) — never dropped. The docstring's coverage claim now says exactly that. Real declaration: 28 such lines | "XM2 r2: `f'{NAME!s}.py'`"; "XM2 r2: a load whose path cannot be read is LISTED with its line" (11 forms + a second file/text); "XM2 r2: the closure SAYS each unresolved load" |
| Xm5 | `load_declaration` refuses, as CANNOT RUN, any file that is not a non-empty string (installed or a component's) and any non-integer `expected_count` | "Xm5 r2: a dict, an empty string or a list where a file belongs ... CANNOT RUN, rc 2" (6 shapes, each by its own refusal message) |
| Xm6 | `check_declaration` runs for every channel; its installed-files membership stays plugin-only | "Xm6 r2: a reusable-workflow component whose expected_count disagrees with its files is REFUSED, rc 1" |

No finding declined. Mutations: 159 → 184 (6 waiver mutations retired, 7 re-anchored, 31 added for the new
clauses); pin and `EXAMINED_KEYS` (`closure.optional` out, `python_loads.rel`/`.text` in) updated; the
declaration re-derived (`measured_at` only).

Sweep (on a copy, `claude` off PATH, `--only scripts/check-shipping-sets.py`, 8 slices): the first pass left 7
survivors and 1 misattribution. Three XM2 survivors (an unknown call, a subscript, and an unbound wrapper parameter
read as NOTHING instead of `UNK`) were invisible because an empty form set is listed too. The fix was a load whose
OTHER branch reads, and a wrapper called with no argument (lines 16–18 of the listing case). Four Xm5 survivors were
masked by a later refusal with the same `CANNOT RUN: ` prefix; the case now asserts each shape's own message. The
misattributed mutation (`a workflow's files must be installed files`) now names the one CM2 case it turns red.

# Spec review round 1 — Claude half — mutation drift report contract

**Subject:** `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md` (candidate
2′, from architecture review #5 finding B).
**Date:** 2026-09-03. **Verdict: NOT CONVERGED — 1 Blocking, 1 High, 2 Medium, 1 Low.**

> ⚠ **METHOD, stated because it is a deviation.** This half was written by the **coordinator**, not a
> fresh subagent, under a standing session instruction not to dispatch agents unless asked. It is
> **not** a `REVIEW GAP:` — the half was performed, and every finding below was produced by
> **executing** the code, not reading it. The Codex half ran independently
> (`spec-mutation-drift-report-contract-r1-codex.md`). Recorded so nobody later reads "coordinator"
> as "skipped".
>
> The author of the spec and the author of this review are the same. That is a real weakness, and the
> mitigation used was to enumerate the return paths **mechanically with `ast`** rather than by
> recollection — which is what found the Blocking.

---

## B1 — 🔴 BLOCKING. R1 is scoped by the wrong landmark, and the recommended option would not fix the worst case

**MEASURED.** The spec defines the bad state as *"`mutate_delivered` returns without reaching the
`copytree` at `:630`"* and recommends option (a), a sentinel *"set at `:584` and flipped after
`copytree`"*.

`mutate_delivered` has **four** returns, enumerated with `ast`, not by reading:

| line | relative to `copytree` (`:630`) | cause |
|---|---|---|
| `:586` | **before** | `load_manifests` returned `problems` |
| `:626` | **before** | count/declaration drift |
| **`:646`** | **AFTER** | **control run went red before any mutation** |
| `:663` | after | normal completion |

`:646` returns *after* `copytree`, so the proposed flag would already be `True`. And `ev["mutations"]`
/ `ev["survivors"]` are assigned at **`:648`** — two lines *after* that return — so they are still
empty while `ev["files"]` has been populated at `:639`.

**Reproduced.** A target's control suite forced to exit 1, on a temp copy:

```
✗ CANNOT RUN — control run of scripts/check-theme-token-coverage.py exited 1 BEFORE any
  mutation was applied. Every verdict below would be an artefact. Treat this as NOT CHECKED.
FAILED — delivered scripts mutated: 7 file(s), 0 mutation(s), 0 survivor(s)
exit=1
```

**This is worse than the drift case the spec was written for.** Drift prints `0 file(s)`, from which a
reader can infer nothing ran. This prints **`7 file(s)`** and `0 survivor(s)` — the shape of a clean
sweep — on a run whose own report says *treat this as NOT CHECKED*. `CLAUDE.md`'s first rule is that
*"'Cannot run' is a FAILURE, never a pass"*, and this is the line that gets believed.

**Required change.** The predicate is not *"did we reach `copytree`"* but **"were mutations actually
run"** — i.e. did control pass and `run_mutations` return. The flip belongs at **`:648`**, not after
`:630`. R1 must be restated in those terms, and §5's option (a) must name `:648` as the flip point.

**Falsifier for the fix:** force a control-run failure; the final line must contain neither
`mutation(s)` nor `survivor(s)`, **and must not report a file count** that implies work was measured.

## H1 — 🟠 The spec's evidence covers one return; its requirement covers all four

`§1` narrates only the drift path (`:625-626`). `R1` says "by any path". A requirement broader than
its evidence invites an implementer to scope the fix to the evidence — which is exactly how B1 would
have shipped.

**Required change:** §1 carries the four-row table above, with the `ast` enumeration as the method.
It is cheap and it is the thing that makes R1 checkable.

## M1 — 🟡 The spec mis-attributes which branch its own botched control exercised

§6 F1 says the first attempt *"tripped the duplicate-anchor check"* and treats it as an aside. That
message is emitted at **`:562`, inside `load_manifests` (516-573)**, so the run returned at **`:586`**
— a *different return* from the corrected run's `:626`.

That is better news than the spec claims, and should be stated as coverage rather than as a mistake:
**three of the four returns have now been exercised** — `:586` (botched F1), `:626` (corrected F1),
`:646` (B1's control-failure trial). Only `:663`, the green path, is untested, and F3 covers it.

## M2 — 🟡 The severity downgrade holds on exit codes, but understates the harm

§2 downgrades 🟠 → 🟡 because `:2072` prints `FAILED —` and `:2075` returns `1`. **Verified — every
one of the three trials exited 1, and none printed a line beginning `OK`.** No false green exists.

But the downgrade's *reasoning* — "a careful reader sees `0 file(s)` and can infer nothing ran" — is
**false for the `:646` path**, which prints `7 file(s)`. The severity can stay 🟡 on exit-code
semantics; the justification must stop relying on the file count being zero.

## L1 — 🟢 Adding a key to `ev` is safe — verified, not assumed

`ev` is already treated as a dict with optional keys: `ev.get("tally", …)` `:843`,
`ev.get("compared")` `:857`, `ev.get(…)` `:917`. Self-test readers at `:1024` and `:1080` index
existing keys only. A new `ran` key breaks nothing. Option (a) is structurally fine; only its flip
point is wrong (B1).

---

## Verified correct — recorded so the next round does not re-check

- **F4 arithmetic.** `EXPECTED_MUTATIONS["scripts/check-plan-code.py"] == 21` and
  `sum(...) == 162`, read by importing the module. The spec's 21→22 / 162→163 is right.
- **Option (c) is genuinely refuted.** `ok=False` is returned by `:646` *and* by `:663` on a real
  survivor, so branching on `ok` at the caller would suppress the tally for a completed run that
  found survivors — losing information on the path that most needs it. The spec's refutation stands.
- **§7's scope limit.** Round 4's Blocking on the guard-inventory plan (T4 vs T7) is a plan defect;
  nothing in this spec changes what that plan must say. Confirmed.

## Verdict

**NOT CONVERGED.** B1 must be folded before this spec is approved: as written, the recommended
implementation leaves the most misleading output in place. H1 and M1/M2 are corrections to the
evidence and framing, not to the design.

**The design itself survives** — a sentinel in `ev`, distinguishing "measured" from "did not
measure", carried in the return value rather than re-derived at the caller. Only the flip point and
the requirement's wording change.

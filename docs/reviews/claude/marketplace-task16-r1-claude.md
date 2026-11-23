Reviewed head: 07664d06afc825aef36df9e8a7dceb9522a8ded4

# Marketplace Task 16, round 1, the Claude half (adversarial)

Subject: plan `docs/superpowers/plans/2026-11-11-marketplace-inventory.md` Task 16 (FAILS IF: *a tier-A or tier-B
record lists an experiment failure on a scan-clean component with no corresponding scan case*). The step allows a
stated limit only for *"a finding that the scan cannot express"*. The spec is
`docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md` §5 (lines 926-935) and §9.

## What I ran, and what came back

- `python3 scripts/check-publishability.py --self-test` → `109/109 self-test cases passed`, rc 0 (42 s).
- `python3 scripts/check-publishability.py --out <scratch>/scan-now.json` → `46 component(s): 46 scanned, 0 CANNOT RUN`.
  `components` is **identical** to the committed `docs/marketplace/scan-2026-11-21.json` (dict equality), so item 5 holds.
  Only `measured_at` differs (see m1).
- Mutations, each run on a scratch copy of `scripts/` with `PLAN_CODE_MUTATION_RUN=1`: *one read target written twice
  on a line*, *a path in prose that is no read/follow instruction*, *install-root reports a path above or beside the
  root*. All three go red on the case each names (98/99, 98/99, 96/99). Manifest length 175 = the new pin. I found no
  new mutation whose named case stays green and no new case that cannot fail.
- A probe of `_install_root_uses` on nine small inputs (results in M3 and m2).

## Enumeration (item 1), from the raw sections and the sidecar `experiment-tier-a.json`

Tier A: `skill-brief` (S3, then S2; cond. 2 fail), `skill-explain-diff` (S2), `skill-explain-findings` (S3),
`skill-explain-topic` (S2), `skill-dashboard` (S3 + S4), `brief-compose` (`~/explainers` rc 1, S2, cond. 4 fail),
`explainer-serve` (cond. 1 fail, S2), the 6 S1 scripts (cond. 3 fail; `gen-dashboard` also S2 and cond. 4).
`ask-answerer` operation_ok `false` = NOT RUN, so it is no failure. The hooks were not exercised (S5 is predicted by
`needs-registration`). Tier B adds `explain-diff` not served (L4). It also adds `dashboard` refusing over **five**
files, not the three tier A named.

Every entry has a case or a limit **except the two in M2**. Some limits also fail the "cannot express" test (B1, M1).

## Item 2: the per-failure reading of "scan-clean"

The per-failure reading is **stricter** than the literal one. Every literally clean component is also clean for each
of its failures, so the reading cannot by itself let a failure escape. I accept it. Its cost is a discretionary
step: *does an existing finding "name the cause"?* That step is where M2 escapes. Note also that the literal reading
names exactly one component, `brief-compose`. The falsifier was written for that case, and B1 is about it.

---

## BLOCKER

### B1 — L3 records as a "limit" a failure the scan can express, on the one literally scan-clean component

- **Where:** `docs/marketplace/experiment-tier-a.md` L3 (*"The scan can see the path but cannot decide that its absence is
  fatal rather than a branch with a working default (spec rule M7)"*); tier-B row `brief-compose rc 1 (no ~/explainers)`.
- **Observation:** `scripts/brief-compose.py:76` is `ROOT = pathlib.Path.home() / "explainers"`.
  `scripts/brief-compose.py:789-790` is
  `if not root.is_dir(): raise SystemExit(f"brief-compose: no explainer directory at {root} — run /explain-diff once first")`.
  That is a statically visible error path, not a branch with a working default. The spec's own rule (§5, r2 CLAUDE M7)
  already says this is a prerequisite: *"counts as a prerequisite only when the component FAILS OR DEGRADES without
  it — i.e. there is no default, or the default leads to an error path"*. Detector 6 `config` already makes that exact
  judgement for environment variables.
- **Why it blocks:** `brief-compose` had zero findings in `scan-2026-11-17.json`, which makes it literally scan-clean.
  Every one of its failures is now closed by a limit (L1, L3) and none by a scan case. The plan's FAILS IF fires: *an
  experiment failure on a scan-clean component with no corresponding scan case*. A limit escapes it only when the
  scan genuinely cannot express the finding, and this one it can. `brief-compose` now carries two install-root
  findings (`brief-compose:2:1` at `:1556`, a provenance call; `brief-compose:2:2` at `:2621`, a self-test fixture
  read), but neither names the `~/explainers` refusal.
- **Fix:** add a detector-6 kind, for example `home-path`: a path built from `Path.home()` / `expanduser("~…")` that a
  `not <p>.is_dir()/exists()` guard turns into `SystemExit`/`sys.exit(≠0)`/`return <nonzero>`. Add a red→green case
  plus a mutation, re-scan, and drop L3. If it really cannot be done, L3 must say which part of that shape cannot be
  read. The current text is contradicted by `:789`.

## MAJOR

### M1 — L2 (S4) is a detector-4 judgement defect, not something the scan cannot express

- **Where:** tier-A L2; `.agents/skills/dashboard/SKILL.md:27-30` (`## The store` / `` `docs/dashboard-entries.md`. **Append-only,
  newest at the END.** `` / `> ⛔ **Append one block.**`).
- **Observation:** the scan reports `docs/dashboard-entries.md` (`:28`) and `docs/anchors.md` (`:14`) as detector-4
  `doc-path` **mentions**. Yet `skill-brief:4:1` (`.agents/skills/brief/SKILL.md:54`, a numbered list item naming
  `docs/roadmap-to-launch.md`) is a detector-4 **finding** of the same kind. The scan therefore already expresses
  "this skill depends on a host `docs/` file". The S4 miss comes from line locality: the instruction ("Append one
  block") sits two lines below the path, in the section the path heads. L2's reason (*"making every named docs/ path a
  dependency would be positional matching"*) argues against a fix nobody proposed. The fixable rule is narrower: a path
  that is the subject of a section whose body instructs an operation on it.
- **Fix:** either a section-scoped detector-4 rule with a case reproducing `:27-30` (red→green), or rewrite L2 to state
  the real bound ("detector 4 judges a line, not the section that introduces it"). The second leaves it a limit by
  choice, and the record should then say so.

### M2 — tier B's `dashboard` refusal names two package files that no case and no limit accounts for

- **Where:** `docs/marketplace/experiment-tier-b.md` skill-half table, `dashboard` row (*"Refused: `docs/dashboard-entries.md`,
  `scripts/regen-pages.py`, `check-dashboard-entry.py`, `.claude/hooks/regen-dashboard.sh`, `docs/anchors.md` absent"*).
  Also the Task-16 table row *"`dashboard` refused: host files absent … tier A S4 (and S3 for `scripts/regen-pages.py`)"*.
- **Observation:** `scripts/check-dashboard-entry.py` (`.agents/skills/dashboard/SKILL.md:21`) and
  `.claude/hooks/regen-dashboard.sh` (`:88`) are **shipped by the package** (`shipping-sets.json` →
  `comprehensibility` → `check-dashboard-entry`, `hook-regen-dashboard`). Both are named bare, and the session reported
  both absent, which is S3's cause. The scan has no finding at either line (`skill-dashboard` findings: `2:1` at
  `:76`, `2:2` at `:99`, `7:1`). They are neither invocations nor read/follow lines. The record files them under S4/L2
  and "the S3 half already predicted", but L2 covers host conventions, not package files.
- **Fix:** either a case (a shipped package path named bare in a skill's prose that the session treats as required is
  `cwd-relative`) or an explicit limit: "a package file named in descriptive prose rather than an INSTRUCTS line is not
  judged". In either case, list these two files in the tier-B table.

### M3 — `install-root` misses the `..` form, and L5 does not state it

- **Where:** `scripts/check-publishability.py` `_from_file` (the `ast.BinOp`/`os.path.join` branches keep `level`
  fixed and append `".."` as a part); tier-A L5.
- **Failing input (probe):** `R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")` followed by
  `open(os.path.join(R, "docs", "b.md"))` returns `[]`. `R = pathlib.Path(__file__).parent / ".."` followed by
  `(R / "docs" / "b.md").read_text()` also returns `[]`. A real instance of the form exists at
  `scripts/build-m4-schema.py:43`. Also, `ROOT: pathlib.Path = Path(__file__).resolve().parent.parent` (an `AnnAssign`)
  is not a binding to `_install_root_uses`. It is reported only as `.` at the binding line, and the `docs/b.md` read
  below it is lost.
- **Why MAJOR:** L5 claims to list what the rule does not see. It names "a call of the program's own function" and
  "a part held in anything but a literal". `..` **is** a literal, so a reader of L5 would take it as covered.
- **Fix:** make a `".."` part decrement `level` (normalise the parts and count leading `..`), treat `ast.AnnAssign`
  like `Assign` in `binds`, and add a case for each. Otherwise add both to L5.

## MINOR

- **m1 — the committed scan's provenance names a commit that does not produce it.** `scan-2026-11-21.json`
  `measured_at` = `75f2c58179b2…` (the base), and the record says *"measured at `75f2c581`"*. At `75f2c581` the
  script has no `install-root` and no read/follow clause, so re-running there gives a different scan. This
  scan is the one from the branch's detector over the base's tree. Fix: regenerate at the Task-16 commit, or record
  both (tree = base, scanner = branch).
- **m2 — `install-root` binds names file-wide, ignoring scope.** Probe: `def f(): x = 3; return x` next to
  `def g(): x = Path(__file__).resolve().parent.parent` reports `(4, '.')` at `f`'s `return x`. On the real tree this
  produces `check-plan-code:2:6` at `scripts/check-plan-code.py:3446` (`_sp.run = _real`, where `_real` is
  `_sp.run` from `:3419`). The only root binding of `_real` is at `:7822`, in a different function. That is
  check-plan-code's sole install-root finding, and it is a false positive with an id a verdict can cite. Fix: key
  `names` on (enclosing function, name), or state it in L5.
- **m3 — a `.` finding points at the first textual use, which can be an innocuous one.** `regen-pages:2:1` is at
  `scripts/regen-pages.py:421` (`os.path.realpath(repo) == os.path.realpath(ROOT)`, a comparison), while the git call
  that produced the experiment's rc 2 is `:423`. `gen-dashboard:2:1`/`2:2` sit at `:33`
  (`STORE_DEFAULT.relative_to(ROOT)`, a display string). `check-rc-contract:2:2` sits at `:449` (inside a `print`).
  The docstring says the root is "handed on (a `cwd=`, a `git -C`, an argument, a default)", but the code accepts any
  bare reference. Fix: restrict `.` to the handed-on positions it names, or say in the docstring that any reference
  counts.
- **m4 — the gen-dashboard row cites a cause its finding does not name.** Tier-A matrix: *"reads <install
  dir>/docs/backlog.md (absent)"*. The mapped finding `gen-dashboard:2:2` is `docs/dashboard-entries.md`, and no
  `gen-dashboard` finding names `docs/backlog.md`. One of the two is wrong. Reconcile it (if the read goes through
  another component, name that component's finding).
- **m5 — two tier-B degraded results are absent from the Task-16 table** (both are covered, so nothing escapes, but
  the table is the enumeration). `brief` *"written for a different repo (no roadmap/backlog/reviews)"* is predicted by
  `skill-brief:4:1`/`4:3`. `explain-diff`'s page had *no Ask tray* (S2/L1) as well as not being served (L4).
- **m6 — the S3 self-test case shares one `seen` set across both clauses of a line.** Not a defect today: the case
  passes and the duplicate mutation goes red. But no case puts an invocation and a read/follow of the **same** target on
  one line, so the cross-clause dedup is unpinned.

VERDICT: NOT CONVERGED

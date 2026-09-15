# Review Decision Procedure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

**Goal:** Consolidate every review decision into one procedure with observable inputs, so a session stops running rounds it does not owe and stops asking the human questions the rules already answer.

**Architecture:** A six-question decision card becomes section 0 of `docs/review-method.md`, with the existing deep sections kept beneath as the evidence for each rule — one source per rule. Each coordinator round document gains a machine-readable header so the counters the rules need are derived rather than remembered. `scripts/check-review-decision.py` reads those headers plus the branch diff and prints the next step. Separately, "Phase 6" is renamed to *architecture review* in the three instruction files, and the contradiction between the spine's count-based trigger and the method doc's cause-based one is resolved in favour of cause.

**Tech Stack:** Python 3 (stdlib only — `re`, `json`, `pathlib`, `subprocess`, `argparse`), Markdown, `git`.

**Spec:** `docs/superpowers/specs/2026-09-14-review-decision-procedure-design.md`

## Global Constraints

- **`docs/dev-process.md` is at 220/220 of its line budget** (`scripts/check-docs.py:191`). Any edit there must be **line-neutral or shorter**. A one-line addition fails CI.
- `docs/review-method.md` has **no** line budget — only `dev-process.md` (220) and `plugins.md` (260) are budgeted.
- **Rename scope is exactly 3 files, 12 occurrences:** `docs/dev-process.md` (5), `docs/review-method.md` (4), `docs/process-checklists.md` (3). `docs/plugins.md` contains the term **zero** times.
- **Never rename the record:** `docs/reviews/` (51 files), `docs/adr/` (4), `docs/superpowers/` (8), `docs/dashboard-entries.md` (1), `docs/roadmap-to-launch.md` (8), `docs/backlog.md` (9), and every comment in `scripts/`, `.claude/hooks/`, `.github/`. These are provenance.
- **Every new guard needs, per `scripts/check-ratchet-contract.py`:** a `--self-test`, no fail-open handler, and a caller **or** a written `NO-CALLER:` reason.
- **A declared self-test count** goes in the script's own docstring as `--self-test # N cases`, is verified by running it (`scripts/check-selftest-counts.py`), and the script name must be added to that checker's **pinned** population set.
- **Real exit codes only.** Never read `$?` after a pipe — it reports the last command in the pipeline. Redirect to a file, then echo `$?`.
- Run gates with `python3 scripts/<name>.py > /tmp/out 2>&1; echo "rc=$?"`.

---

### Task 1: Rename "Phase 6" to "architecture review" in the instruction files

**Files:**
- Modify: `docs/dev-process.md` (5 occurrences)
- Modify: `docs/review-method.md` (4 occurrences)
- Modify: `docs/process-checklists.md` (3 occurrences)

**Interfaces:**
- Consumes: nothing.
- Produces: the term *architecture review* as the name used by every later task. Task 2 and Task 3 both write prose that must use it.

**Why this is safe:** the machine-dependency grep was run 2026-09-14 and is clean — every occurrence in `scripts/`, `.claude/hooks/` and `.github/` is inside a **comment** (`check-docs.py:290`, `m4_catalog.py:173`, `check-schema-gates.sh:78,81`, `ci.yml:195,220`). No code keys on the string.

- [ ] **Step 1: Write the failing check**

```bash
cat > /tmp/check-rename.sh <<'EOF'
#!/usr/bin/env bash
# The instruction files must not call it "Phase 6". The record keeps its own words.
n=0
for f in docs/dev-process.md docs/review-method.md docs/process-checklists.md; do
  c=$(grep -o 'Phase 6' "$f" | wc -l | tr -d ' ')
  echo "  $f: $c"
  n=$((n + c))
done
echo "total in instructions: $n"
[ "$n" -eq 0 ] || { echo "FAIL — the instructions still name it by index"; exit 1; }
echo "ok"
EOF
chmod +x /tmp/check-rename.sh
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bash /tmp/check-rename.sh; echo "rc=$?"`
Expected: `total in instructions: 12` then `FAIL …` and `rc=1`.

- [ ] **Step 3: Rename, preserving the table index**

The phases table row keeps its number — an index belongs in the table it indexes. Everywhere else, the term becomes *architecture review*.

```bash
python3 - <<'PY'
import pathlib, re
for rel in ("docs/dev-process.md", "docs/review-method.md", "docs/process-checklists.md"):
    p = pathlib.Path(rel); t = p.read_text()
    before = t.count("Phase 6")
    # "Phase 6 (architecture review)" -> "architecture review"  (drop the gloss, keep the name)
    t = t.replace("Phase 6 (architecture review)", "the architecture review")
    # possessive and bare forms
    t = t.replace("Phase 6's", "the architecture review's")
    t = t.replace("Phase 6", "the architecture review")
    # tidy the double article that the bare replacement can create
    t = re.sub(r"\bthe the architecture review\b", "the architecture review", t)
    t = re.sub(r"\bThe the architecture review\b", "The architecture review", t)
    p.write_text(t)
    print(f"{rel}: {before} -> {t.count('Phase 6')}")
PY
```

- [ ] **Step 4: Read every changed line and fix the grammar by hand**

A blind substitution produces sentences like *"⟳ the architecture review also fires on FOUR NON-CONVERGING ROUNDS"*. Read each one:

Run: `git diff -U0 docs/dev-process.md docs/review-method.md docs/process-checklists.md | grep '^[+-]' | grep -v '^[+-][+-]'`

Fix any sentence that now reads wrongly. Keep the phases-table row as `| 6 | **Architecture Review** | …` — the index stays.

- [ ] **Step 5: Run the check and the doc gates**

```bash
bash /tmp/check-rename.sh; echo "rename rc=$?"
python3 scripts/check-docs.py > /tmp/d 2>&1; echo "check-docs rc=$?"; grep '^budget' /tmp/d
python3 scripts/check-anchors.py > /tmp/a 2>&1; echo "check-anchors rc=$?"
```
Expected: `ok`, `rename rc=0`, `check-docs rc=0`, `dev-process.md : 220 / 220 ok`, `check-anchors rc=0`.

⚠ If `dev-process.md` now reads OVER 220, the rename made a line wrap. Shorten the sentence; do not raise the budget.

- [ ] **Step 6: Confirm the record was NOT touched**

```bash
git status --short | grep -E 'docs/(reviews|adr|superpowers)/|dashboard-entries|roadmap-to-launch|backlog' && echo "FAIL — the record was modified" || echo "ok — record untouched"
```
Expected: `ok — record untouched`.

- [ ] **Step 7: Commit**

```bash
git add docs/dev-process.md docs/review-method.md docs/process-checklists.md
git commit -m "An index is not a name: 'Phase 6' becomes 'architecture review' in the instructions

Measured origin: the term first appears 2026-08-08 in 0b27094e, the same commit that
introduced the phases table. It is a row index in one table in one repo, used as a proper
noun. No vendored plugin or skill uses it in this sense, and superpowers:improve-codebase-
architecture — the skill it maps to — never uses it at all.

The usage proves it escaped the table: Phase 1 has 62 mentions across docs/, Phases 2-5
between 21 and 33, and Phase 6 has 184 — more than the other five combined. The others
acquired spoken names; 6 never did, though the table named it Architecture Review on the
day it was created.

Renames the INSTRUCTIONS only: dev-process.md (5), review-method.md (4),
process-checklists.md (3). The RECORD keeps its own words — 51 review documents, 4 ADRs,
8 specs/plans, the dashboard, roadmap and backlog all cite it as provenance, and
rewriting them would be editing evidence.

Safe by measurement: every occurrence in scripts/, .claude/hooks/ and .github/ is inside
a COMMENT, so no gate keys on the string and none can unhook."
```

---

### Task 2: Resolve the architecture-review trigger contradiction

**Files:**
- Modify: `docs/dev-process.md` — the phases table row 6 and the arming paragraph beneath it

**Interfaces:**
- Consumes: Task 1's renamed vocabulary.
- Produces: a single arming condition — *two consecutive fix-induced rounds in one component* — that Task 5's `thrashing_component()` implements.

**The contradiction:** `docs/dev-process.md` arms the review after **four non-converging rounds** (a count). `docs/review-method.md:324` says *"the distinction is the CAUSE of the non-convergence, not the count"*, and `:337` says **"RAW BLOCKING COUNT IS A BAD DISCRIMINATOR, AND THIS WAS MEASURED"** — the dashboard spec ran Blocking 4 → 5 → 4, flat, which reads as thrashing by count and was the prose floor.

- [ ] **Step 1: Record the line count before touching it**

```bash
wc -l docs/dev-process.md
```
Expected: `220`. **This must still be ≤ 220 at the end of the task.**

- [ ] **Step 2: Rewrite the trigger, line-neutral**

Change the table row's trigger clause from the count to the cause, and rewrite the arming paragraph to **point at** `review-method.md`'s thrashing/prose-floor table rather than restating it — a second copy of a rule is a copy that drifts.

The row becomes:

```markdown
| 6 | **Architecture Review** | `docs/reviews/architecture-review-<date>.md` | per **milestone** — **or on THRASHING: two consecutive rounds whose findings were caused by the previous round's fix** |
```

And the paragraph beneath it must state, within its existing line count:

- **cause arms it**, not the count: two consecutive fix-induced rounds in one component;
- **reaching four rounds obliges ASKING** *thrashing or prose floor?* and recording the answer with per-finding evidence — it does not fire;
- the shapes and the test *"can a redesign remove it?"* live in `review-method.md`, cited not copied.

- [ ] **Step 3: Verify line-neutrality and the gates**

```bash
wc -l docs/dev-process.md
python3 scripts/check-docs.py > /tmp/d 2>&1; echo "check-docs rc=$?"; grep 'dev-process' /tmp/d
```
Expected: `220` or fewer, `check-docs rc=0`, and the budget line reads `ok`.

- [ ] **Step 4: Verify the two documents no longer disagree**

```bash
grep -n "four\|4 review rounds\|non-converging" docs/dev-process.md | head
```
Expected: any surviving mention of four rounds is phrased as *obliges asking*, never as the arming condition.

- [ ] **Step 5: Commit**

```bash
git add docs/dev-process.md
git commit -m "The most expensive gate had the least clear condition: cause arms it, the count only asks

dev-process.md armed the architecture review on a COUNT of four non-converging rounds
while review-method.md:324 says the trigger is the CAUSE and :337 measures the count as a
bad discriminator — the dashboard spec ran Blocking 4->5->4, flat, which reads as
thrashing by count and was actually the prose floor.

One spine and one method document disagreed about when the most expensive gate fires.

Now: THRASHING arms it — two consecutive rounds whose findings were caused by the previous
round's fix, in one component. Reaching four rounds obliges ASKING 'thrashing or prose
floor?' and recording the answer with per-finding evidence; it does not fire.

The shapes and the test 'can a redesign remove it?' are CITED from review-method.md, not
restated — a second copy of a rule is a copy that drifts. Line-neutral: dev-process.md is
at 220/220 of its budget and a one-line addition would fail CI."
```

---

### Task 3: Add the decision card as section 0 of `review-method.md`

**Files:**
- Modify: `docs/review-method.md` — insert after the document title, before the current first section (`## Two rules for PREMISES, not findings`, line 15)

**Interfaces:**
- Consumes: Task 1's vocabulary, Task 2's arming condition.
- Produces: the six questions Q1–Q6 that Task 4's header schema and Task 5's `decide()` implement. **The field names `aim`, `fix_induced`, `disposition`, `severity`, `component` are introduced here and MUST match Task 4 and Task 5 exactly.**

- [ ] **Step 1: Write the card**

Insert a `## 0. The decision procedure — read this, do not recall it` section containing exactly the six questions from the spec's §1, each with its observable inputs, and each citing the section below it that carries the evidence. The content is specified in full in `docs/superpowers/specs/2026-09-14-review-decision-procedure-design.md` §1 — copy the six question blocks verbatim, including:

- Q1's two-row scope table (full loop vs one round) citing `:305` and `:309`;
- Q2's five-step round-1 protocol citing `:171`, `:243`, and the output contract;
- Q3's three-row disposition table, the note that it **replaces** `:298`, and `:246`'s proposed-fix warning;
- Q4's **two** sub-questions — (a) convergence with the four-row observation table and the AIM rule citing `:132`; (b) tree identity with the four cost-ordered answers citing `:266` and `:252`, and the ⛔ line forbidding a round for (b) before offering 1–3;
- Q5's three-shape table, the test `:67`, and Task 2's arming condition;
- Q6, citing `:350`.

- [ ] **Step 2: Verify every citation resolves**

```bash
python3 - <<'PY'
import re, pathlib
doc = pathlib.Path("docs/review-method.md").read_text()
lines = doc.split("\n")
card_end = doc.find("## Two rules for PREMISES")
card = doc[:card_end]
bad = []
for n in sorted({int(m) for m in re.findall(r"`:(\d+)`", card)}):
    if n - 1 >= len(lines):
        bad.append((n, "OUT OF RANGE")); continue
    print(f"  :{n:<4} {lines[n-1].strip()[:74]}")
print("\nout of range:", bad or "none")
PY
```
Expected: every cited line prints real content and `out of range: none`.

⚠ **Inserting the card SHIFTS every line below it.** The citations in the card must be re-derived **after** insertion, not copied from the spec, whose numbers were taken before the shift. This is the single most likely defect in this task.

- [ ] **Step 3: Run the doc gates**

```bash
python3 scripts/check-docs.py > /tmp/d 2>&1; echo "check-docs rc=$?"
python3 scripts/check-anchors.py > /tmp/a 2>&1; echo "check-anchors rc=$?"
wc -l docs/review-method.md
```
Expected: both rc=0. No budget applies to this file.

- [ ] **Step 4: Verify the card does not DUPLICATE the sections beneath it**

```bash
grep -c "Can a redesign remove it" docs/review-method.md
grep -c "Batch the editorial fixes" docs/review-method.md
```
Expected: `1` for each. The card **cites**; it must not restate. Two copies of a rule is the shape `scripts/check-vocabulary-collisions.py` exists to hunt.

- [ ] **Step 5: Commit**

```bash
git add docs/review-method.md
git commit -m "The rules were right and scattered: one decision card, six questions, at the top

PR #302 ran four review rounds on a contained single-file change. Two were owed. Rounds 3
and 4 each returned one Low in the coordinator's own test code — exactly the case :309
names when it says 'one round is fine, do not over-apply this'.

The cause was a CONFLATION, not a missing rule: convergence (has discovery dried up) and
tree identity (did a round see the code that MERGES) were merged and reported as one. The
cheaper answers to tree identity were already written down — :266 predicted the failure
verbatim, and :252 calls holding fixes uncommitted 'the documented way' — and neither was
offered to the human.

Q1 scope, Q2 round-1 topology, Q3 disposition, Q4 the TWO questions kept apart, Q5
thrashing, Q6 record the call. Each keyed on observable inputs and CITING the section
below it, never restating it."
```

---

### Task 4: The machine-readable round-document header

**Files:**
- Modify: `docs/review-method.md` — a `### The round-document header` subsection inside the card's Q6
- Create: `docs/reviews/ROUND-HEADER-TEMPLATE.md`

**Interfaces:**
- Consumes: Task 3's field names.
- Produces: the exact YAML schema that Task 5's `parse_header()` consumes. **Field names and value sets are frozen here.**

- [ ] **Step 1: Write the template**

```markdown
<!-- docs/reviews/ROUND-HEADER-TEMPLATE.md -->
# Round-document header

Every coordinator round document carries this block immediately after its title. It exists
because the counters the decision procedure needs — consecutive fix-induced rounds, rounds
since a finding in the deliverable — are mechanical, and `review-method.md` already refuses
the alternative: *"the evidence is derivable, not remembered. Do not maintain a hand-written
tally of it."*

```yaml
round: 3
subject: clickable-dashboard-asks
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, component: check-review-decision, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: check-review-decision, disposition: filed}
```

| Field | Values | Definition |
|---|---|---|
| `round` | integer | the round number |
| `subject` | string | the branch or artifact under review |
| `halves.<name>` | `ran` or a string starting `GAP:` | whether each half ran; a gap carries its reason |
| `severity` | `Blocking` `High` `Medium` `Low` | as filed by the reviewer |
| `aim` | `deliverable` `instrument` | does the finding sit in code the branch SHIPS, or in a test/guard/harness that MEASURES it? |
| `fix_induced` | `true` `false` | was the defect introduced by a fix written after a previous round? |
| `component` | string | the unit the finding is in; thrashing is per-component |
| `disposition` | `fixed` `filed` `declined` | what Q3 decided; the reason goes in prose below |

⚠ `aim` and `fix_induced` are **judgements the agent records**, not values the header derives.
A header filled in dishonestly produces confident wrong answers and nothing detects that.
```

- [ ] **Step 2: Document it in the card**

Add to `review-method.md`'s Q6 a short block pointing at the template — the schema lives in **one** place.

- [ ] **Step 3: Backfill the four PR #302 round documents**

```bash
ls docs/reviews/coordinator/clickable-dashboard-asks-r*-coordinator.md
```
Add the header to each, with the values already recorded in their prose: r1 `M1/Medium/deliverable/false/fixed`; r2 `M1/Medium/deliverable/true/fixed` and `L1/Low/instrument/false/fixed`; r3 `L1/Low/instrument/true/fixed`; r4 `L1/Low/instrument/true/filed`.

These four are the fixture Task 5 tests against — a real corpus beats a synthetic one.

- [ ] **Step 4: Verify the gates still pass**

```bash
python3 scripts/check-docs.py > /tmp/d 2>&1; echo "check-docs rc=$?"
python3 scripts/check-review-rounds.py > /tmp/r 2>&1; echo "check-review-rounds rc=$?"; tail -1 /tmp/r
```
Expected: both rc=0.

- [ ] **Step 5: Commit**

```bash
git add docs/reviews/ROUND-HEADER-TEMPLATE.md docs/review-method.md docs/reviews/coordinator/clickable-dashboard-asks-r*-coordinator.md
git commit -m "Counters nobody kept become counters nobody has to keep

The decision procedure needs two numbers — consecutive fix-induced rounds, and rounds
since a finding in the deliverable. On PR #302 nobody kept either, which is why four
rounds ran where two were owed. review-method.md:285 already refuses the alternative:
'the evidence is derivable, not remembered. Do not maintain a hand-written tally of it.'

Adds a YAML header to each coordinator round document, and backfills PR #302's four rounds
from what their prose already records — so the first consumer has a real corpus rather
than a synthetic one.

⚠ aim and fix_induced are JUDGEMENTS the agent records; the header does not pretend to
derive them. What becomes mechanical is the bookkeeping and the decision rule, which is
where recall failed."
```

---

### Task 5: The decision rules, as pure functions

**Files:**
- Create: `scripts/check-review-decision.py`

**Interfaces:**
- Consumes: Task 4's header schema.
- Produces:
  - `scope_for(paths: list[str]) -> str` → `"full-loop"` or `"one-round"`
  - `thrashing_component(rounds: list[dict]) -> str | None`
  - `converged(rounds: list[dict], scope: str) -> tuple[bool, str]`
  - `decide(rounds: list[dict], scope: str, tree_reviewed: bool) -> tuple[str, str]` → decision ∈ `{"STOP", "ROUND_OWED", "ARCHITECTURE_REVIEW", "TREE"}` and a reason string

  Task 6 wires these to the filesystem and the CLI. **All four are PURE** — they take data and return data, touching no file and no git — because a rule that needs a repository to answer cannot be cased cheaply.

- [ ] **Step 1: Write the failing cases**

Create `scripts/check-review-decision.py` with a `_self_test()` containing these cases and nothing else yet:

```python
def _self_test() -> int:
    cases = failures = 0
    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    # --- Q1 scope -------------------------------------------------------
    case("a migration needs the full loop",
         scope_for(["supabase/migrations/0028_x.sql"]), "full-loop")
    case("an RLS policy needs the full loop",
         scope_for(["supabase/policies/rls.sql"]), "full-loop")
    case("a page generator alone is one round",
         scope_for(["scripts/gen-dashboard.py"]), "one-round")
    case("docs alone are one round",
         scope_for(["docs/review-method.md"]), "one-round")
    case("one risky path in a mixed set still forces the full loop",
         scope_for(["docs/x.md", "lib/spend-ledger.ts"]), "full-loop")
    case("an empty diff is one round, not a crash",
         scope_for([]), "one-round")

    # --- Q5 thrashing ---------------------------------------------------
    r_fix_a = {"round": 1, "findings": [{"fix_induced": True, "component": "a"}]}
    r_fix_a2 = {"round": 2, "findings": [{"fix_induced": True, "component": "a"}]}
    r_fix_b = {"round": 2, "findings": [{"fix_induced": True, "component": "b"}]}
    r_clean = {"round": 2, "findings": [{"fix_induced": False, "component": "a"}]}
    case("two consecutive fix-induced rounds in ONE component is thrashing",
         thrashing_component([r_fix_a, r_fix_a2]), "a")
    case("two fix-induced rounds in DIFFERENT components is not thrashing",
         thrashing_component([r_fix_a, r_fix_b]), None)
    case("one fix-induced round is not thrashing",
         thrashing_component([r_fix_a, r_clean]), None)
    case("thrashing reads the LAST two rounds, not any two",
         thrashing_component([r_fix_a, r_fix_a2, r_clean]), None)

    # --- Q4a convergence ------------------------------------------------
    inst = {"severity": "Low", "aim": "instrument", "fix_induced": False, "component": "t"}
    deliv = {"severity": "Low", "aim": "deliverable", "fix_induced": False, "component": "d"}
    high = {"severity": "High", "aim": "deliverable", "fix_induced": False, "component": "d"}
    two_inst = [{"round": 1, "findings": [inst]}, {"round": 2, "findings": [inst]}]
    case("two consecutive instrument-only rounds converge",
         converged(two_inst, "full-loop")[0], True)
    case("a High blocks convergence",
         converged([{"round": 1, "findings": [inst]},
                    {"round": 2, "findings": [high]}], "full-loop")[0], False)
    case("a deliverable finding blocks convergence",
         converged([{"round": 1, "findings": [inst]},
                    {"round": 2, "findings": [deliv]}], "full-loop")[0], False)
    case("one clean round is NOT convergence on the full loop",
         converged([{"round": 1, "findings": []}], "full-loop")[0], False)
    case("one clean round IS convergence when the scope is one-round",
         converged([{"round": 1, "findings": []}], "one-round")[0], True)
    case("no rounds never converges",
         converged([], "one-round")[0], False)

    # --- decide ---------------------------------------------------------
    case("no round recorded owes a round",
         decide([], "one-round", False)[0], "ROUND_OWED")
    case("thrashing outranks convergence",
         decide([r_fix_a, r_fix_a2], "full-loop", True)[0], "ARCHITECTURE_REVIEW")
    case("converged but the merging tree is unreviewed asks for TREE, not a round",
         decide(two_inst, "full-loop", False)[0], "TREE")
    case("converged and the tree was reviewed is STOP",
         decide(two_inst, "full-loop", True)[0], "STOP")
    case("not converged owes a round",
         decide([{"round": 1, "findings": [high]}], "full-loop", True)[0], "ROUND_OWED")
    case("every decision carries a non-empty reason",
         all(decide(*a)[1] for a in [([], "one-round", False),
                                     ([r_fix_a, r_fix_a2], "full-loop", True),
                                     (two_inst, "full-loop", False),
                                     (two_inst, "full-loop", True)]), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/check-review-decision.py --self-test > /tmp/t 2>&1; echo "rc=$?"; head -5 /tmp/t`
Expected: rc≠0 with `NameError: name 'scope_for' is not defined`.

- [ ] **Step 3: Write the four pure functions**

```python
# Q1. The risk list is review-method.md's own (:305), as PATH PREFIXES so it is observable.
RISK_PREFIXES = (
    "supabase/",          # schema, migrations, RLS policies
    "lib/spend", "lib/quota", "lib/ledger",   # money and irreversible paths
    "lib/lease", "lib/queue", "lib/reservation",  # concurrency and leasing
    "middleware", "lib/auth",                 # auth / multi-tenant isolation
)


def scope_for(paths: list[str]) -> str:
    """PURE. `full-loop` if any path is risky, else `one-round` (:305, :309)."""
    for p in paths:
        if any(p.startswith(pre) for pre in RISK_PREFIXES):
            return "full-loop"
    return "one-round"


def thrashing_component(rounds: list[dict]) -> "str | None":
    """PURE. The component fix-induced in BOTH of the last two rounds, else None (:45)."""
    if len(rounds) < 2:
        return None
    last, prev = rounds[-1], rounds[-2]

    def induced(r):
        return {f.get("component") for f in r.get("findings", []) if f.get("fix_induced")}

    shared = induced(prev) & induced(last)
    return sorted(shared)[0] if shared else None


def converged(rounds: list[dict], scope: str) -> "tuple[bool, str]":
    """PURE. Q4(a). Judged by AIM, not severity (:132)."""
    if not rounds:
        return False, "no round recorded"
    need = 1 if scope == "one-round" else 2
    if len(rounds) < need:
        return False, f"{len(rounds)} round(s); {scope} needs {need}"
    for r in rounds[-need:]:
        for f in r.get("findings", []):
            if f.get("severity") in ("Blocking", "High"):
                return False, f"r{r.get('round')} produced a {f['severity']}"
            if f.get("aim") == "deliverable":
                return False, f"r{r.get('round')} found a defect in the deliverable"
    return True, f"{need} round(s) with no Blocking/High and nothing in the deliverable"


TREE_ANSWERS = (
    "batch the editorial fixes BEFORE the last round (:266)",
    "hold the final fixes uncommitted so the reviewer sees what ships (:252)",
    "declare NO-REVIEW: <reason> in the PR body",
    "run another round — LAST resort, never first",
)


def decide(rounds: list[dict], scope: str, tree_reviewed: bool) -> "tuple[str, str]":
    """PURE. One decision and its reason."""
    if not rounds:
        return "ROUND_OWED", f"no round recorded; scope is {scope}"
    th = thrashing_component(rounds)
    if th:
        return ("ARCHITECTURE_REVIEW",
                f"thrashing: '{th}' carried fix-induced findings in "
                f"r{rounds[-2].get('round')} and r{rounds[-1].get('round')}")
    ok, why = converged(rounds, scope)
    if not ok:
        return "ROUND_OWED", why
    if not tree_reviewed:
        return "TREE", "converged; cheapest answer first: " + "; ".join(TREE_ANSWERS)
    return "STOP", f"converged ({why}) and a round saw the merging tree"
```

- [ ] **Step 4: Run the cases to verify they pass**

Run: `python3 scripts/check-review-decision.py --self-test > /tmp/t 2>&1; echo "rc=$?"; tail -3 /tmp/t`
Expected: `rc=0` and `22/22 self-test cases passed`.

- [ ] **Step 5: Prove the cases are falsifiable, not decorative**

Each mutation must turn the suite red **via the case that names it**.

```bash
WORK=$(mktemp -d); cp scripts/check-review-decision.py "$WORK/g.py"
mut() { cp scripts/check-review-decision.py "$WORK/m.py"
  python3 - "$WORK/m.py" "$1" "$2" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
assert t.count(sys.argv[2]) == 1, f"anchor appears {t.count(sys.argv[2])}x"
p.write_text(t.replace(sys.argv[2], sys.argv[3], 1))
PY
  echo -n "  $2 -> "; python3 "$WORK/m.py" --self-test 2>&1 | grep -cE '^\s+\[FAIL\]' | tr -d '\n'; echo " case(s) red"; }
mut x "shared = induced(prev) & induced(last)" "shared = induced(prev) | induced(last)"
mut x 'if f.get("aim") == "deliverable":' 'if False:'
mut x 'need = 1 if scope == "one-round" else 2' 'need = 1'
mut x 'if not tree_reviewed:' 'if False:'
rm -rf "$WORK"
```
Expected: every line reports **at least 1 case red**. A mutation reporting `0` means that rule has no falsifier — fix the case, not the mutation.

- [ ] **Step 6: Commit**

```bash
git add scripts/check-review-decision.py
git commit -m "The decision rules as pure functions, so they can be cased cheaply

scope_for, thrashing_component, converged and decide take data and return data — no file,
no git. A rule that needs a repository to answer cannot be cased cheaply, and these are
the rules that were being recalled instead of read.

Q4(a) judges by AIM, not severity: :132 already says 'no new Blocking or High is a
statement about the REVIEWERS, not the design', and PR #302 measured it from the other
side — severity read converged from round 1 and was useless, while the aim column
separated the rounds cleanly.

decide() checks thrashing BEFORE convergence, and returns TREE — never ROUND_OWED — when
the only thing missing is that a round has not seen the merging tree. That ordering is the
whole fix: PR #302 ran two rounds because those two questions were merged.

22 cases; four mutations proved each rule falsifiable via the case that names it."
```

---

### Task 6: Wire the rules to the repository and satisfy the ratchet

**Files:**
- Modify: `scripts/check-review-decision.py` — add `parse_header()`, `rounds_for()`, `main()`, the docstring
- Modify: `scripts/check-selftest-counts.py` — add the new script to the pinned population
- Modify: `scripts/mutations/` — add a manifest file for the new script
- Modify: `scripts/check-plan-code.py` — `EXPECTED_MUTATIONS` and the declared sum

**Interfaces:**
- Consumes: Task 5's four pure functions, Task 4's header schema.
- Produces: `python3 scripts/check-review-decision.py` printing one decision line; exit 0 STOP, 1 a round or review is owed, 2 CANNOT RUN.

- [ ] **Step 1: Write the failing cases for the parser**

Add to `_self_test()`:

```python
    # --- header parsing -------------------------------------------------
    good = ('# r3\n\n```yaml\nround: 3\nsubject: s\nfindings:\n'
            '  - {id: L1, severity: Low, aim: instrument, fix_induced: true, '
            'component: c, disposition: filed}\n```\n')
    h = parse_header(good)
    case("a header parses its round number", h["round"], 3)
    case("a header parses its findings", len(h["findings"]), 1)
    case("a finding's booleans are real booleans",
         h["findings"][0]["fix_induced"], True)
    case("a finding's aim survives parsing", h["findings"][0]["aim"], "instrument")
    case("a document with NO header raises, never returns empty",
         _raises(lambda: parse_header("# r3\n\nprose only\n")), True)
    case("a header missing `round` raises rather than defaulting",
         _raises(lambda: parse_header("```yaml\nsubject: s\nfindings: []\n```")), True)
```

with a helper:

```python
def _raises(fn) -> bool:
    try:
        fn()
    except Exception:
        return True
    return False
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 scripts/check-review-decision.py --self-test > /tmp/t 2>&1; echo "rc=$?"; grep -c FAIL /tmp/t`
Expected: rc≠0, `NameError: name 'parse_header' is not defined`.

- [ ] **Step 3: Implement the parser and the CLI**

⚠ **No PyYAML** — stdlib only. The header is a fixed, flat shape, so parse exactly that shape and **raise** on anything else.

```python
FINDING_RE = re.compile(r"\{([^}]*)\}")


def parse_header(text: str) -> dict:
    """The `yaml` block after the title. RAISES if absent or malformed —
    a missing header is CANNOT RUN, never an empty round."""
    m = re.search(r"```yaml\n(.*?)```", text, re.S)
    if not m:
        raise ValueError("no ```yaml header block")
    body = m.group(1)
    rm = re.search(r"^round:\s*(\d+)\s*$", body, re.M)
    if not rm:
        raise ValueError("header has no `round:` line")
    findings = []
    for fm in FINDING_RE.finditer(body):
        f = {}
        for pair in fm.group(1).split(","):
            if ":" not in pair:
                continue
            k, v = pair.split(":", 1)
            v = v.strip().strip('"').strip("'")
            f[k.strip()] = {"true": True, "false": False}.get(v, v)
        findings.append(f)
    return {"round": int(rm.group(1)), "findings": findings}
```

`rounds_for(subject)` globs `docs/reviews/coordinator/<subject>-r*-coordinator.md`, parses each, and returns them sorted by `round`. `main()` derives the subject from the branch name, the changed paths from `git diff --name-only origin/master...HEAD`, and `tree_reviewed` by shelling out to `check-review-recorded.py` and reading **its exit code**. Any failure to read an input → print `CANNOT RUN — <what>` and `return 2`.

- [ ] **Step 4: Run the cases**

Run: `python3 scripts/check-review-decision.py --self-test > /tmp/t 2>&1; echo "rc=$?"; tail -2 /tmp/t`
Expected: `rc=0`, `28/28 self-test cases passed`.

- [ ] **Step 5: Run it live against PR #302's backfilled rounds**

```bash
git checkout clickable-dashboard-asks 2>/dev/null || echo "(branch merged; skip)"
python3 scripts/check-review-decision.py > /tmp/live 2>&1; echo "rc=$?"; cat /tmp/live
git checkout review-decision-procedure
```
Expected: it reports `STOP` or `TREE` for that branch — **not** `ROUND_OWED`. If it says a round is owed, the rules disagree with the conclusion we reached by hand, and **the rules are what changed** — investigate before proceeding.

- [ ] **Step 6: Satisfy the ratchet**

Declare the count in the docstring, pin the population, and add the manifest:

```bash
# 1. docstring line, matching scripts/check-anchors.py:5's shape:
#      python3 scripts/check-review-decision.py --self-test # 28 cases
# 2. NO-CALLER, because nothing in CI runs it — it is an agent's instrument:
#      NO-CALLER: an instrument the coordinator consults at a decision point; CI has no
#      decision to make. Its protection is that the decision card names it as the step.
python3 scripts/check-selftest-counts.py > /tmp/s 2>&1; echo "check-selftest-counts rc=$?"; tail -2 /tmp/s
python3 scripts/check-ratchet-contract.py > /tmp/r 2>&1; echo "check-ratchet-contract rc=$?"; tail -2 /tmp/r
```
⚠ If `check-selftest-counts` reports the script is unknown, add its name to the **pinned** set (`scripts/check-selftest-counts.py:75` — *"Pinned, not derived"*) and update the count in that docstring too.

- [ ] **Step 7: Add the mutation manifest and update the pins**

Create `scripts/mutations/check-review-decision.json` with the four mutations proved in Task 5 Step 5, each `expect`ing the **exact** case name (attribution is exact equality). Then:

```bash
python3 - <<'PY'
import json, pathlib, importlib.util, sys
n = len(json.loads(pathlib.Path("scripts/mutations/check-review-decision.json").read_text()))
p = pathlib.Path("scripts/check-plan-code.py"); t = p.read_text()
spec = importlib.util.spec_from_file_location("cpc", p)
m = importlib.util.module_from_spec(spec); sys.modules["cpc"] = m; spec.loader.exec_module(m)
old_sum = sum(m.EXPECTED_MUTATIONS.values())
print(f"add {n} entries; declared sum {old_sum} -> {old_sum + n}")
PY
```
Add `"scripts/check-review-decision.py": <n>` to `EXPECTED_MUTATIONS` and update the declared-sum case.

```bash
python3 scripts/check-plan-code.py --self-test > /tmp/c 2>&1; echo "check-plan-code rc=$?"; tail -2 /tmp/c
```
Expected: rc=0, 128/128 (or higher if the declared-sum case is the only change).

- [ ] **Step 8: Commit**

```bash
git add scripts/check-review-decision.py scripts/check-selftest-counts.py \
        scripts/mutations/check-review-decision.json scripts/check-plan-code.py
git commit -m "The decision becomes a command, so it is consulted rather than recalled

parse_header RAISES on a missing or malformed header and main() exits 2 — a round document
with no header is CANNOT RUN, never an empty round that silently reads as converged. That
is this repo's oldest rule about checks and the one a decision procedure can least afford
to break.

NO-CALLER is declared and argued rather than left implicit: nothing in CI runs this,
because CI has no decision to make. Its protection is that the decision card names it as
the step — which is exactly the protection that FAILED on PR #302 when the step was prose.
If it is skipped again, the answer is not better prose; it is making this a step nobody
can skip.

Verified live against PR #302's four backfilled rounds — the branch the rules were derived
from — so the first run measures a real corpus."
```

---

## Self-Review

**Spec coverage.** §1 → Task 3. §2 → Task 4. §3 → Tasks 5 and 6. §4 → Task 1. §5 → Task 2. The spec's *"what this does not do"* limits are carried into Task 4 Step 1 (`aim`/`fix_induced` are judgements) and Task 6 Step 6 (NO-CALLER argued, not assumed). No spec section is unimplemented.

**Placeholder scan.** No `TBD`/`TODO`; every code step carries real code; every verification step states the exact command and its expected output. Task 3 Step 1 deliberately says *"copy the six question blocks verbatim from the spec"* rather than duplicating 90 lines of prose here — the spec travels with the plan and is cited in the header, and copying it would create the second-copy-drifts defect the plan itself warns about.

**Type consistency.** `scope_for → str`, `thrashing_component → str | None`, `converged → tuple[bool, str]`, `decide → tuple[str, str]`, `parse_header → dict` with keys `round` and `findings`. The header field names — `round`, `subject`, `halves`, `severity`, `aim`, `fix_induced`, `component`, `disposition` — are identical in Task 4's template, Task 5's cases and Task 6's parser.

**Known risk, stated rather than discovered.** Task 3 inserts the card at the top of `review-method.md`, which **shifts every line number below it**. Every `:NNN` citation in the card must be re-derived after insertion. Task 3 Step 2 exists only to catch that, and it is the most likely defect in this plan.

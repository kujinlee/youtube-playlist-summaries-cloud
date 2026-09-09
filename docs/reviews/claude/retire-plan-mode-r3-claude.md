# retire-plan-mode — code review round 3, Claude half

**Subject:** r2's OWN FIXES — `git diff 6e5b2b78..f9d2c498 -- scripts/`, head `f9d2c498`.

**Verdict:** **NOT CONVERGED** — 3 Medium, 3 Low, all inside r2's fix region, all executed.
Nothing Blocking or High. The set-difference logic itself (Codex r2's fix) was attacked hard and
is **correct**.

⚠ **THIS HALF HAD TO BE RUN TWICE. The first attempt did not review anything** — see the process
section at the end. It is recorded here because the failure is more dangerous than any finding
below.

---

## F1 — Medium — `Finding.unreadable` is read by NO production code, and the comment justifying it states something false

The field's comment (`:111-115`) says `coverage_shortfall` *"must tell 'unread because the corpus
was narrowed' from 'unread because the file could not be opened' — and the only honest way to know
which is for the producer to SAY."*

`coverage_shortfall` cannot consult it. Its signature (`:122`) is
`def coverage_shortfall(docs_root: Path, seen: "set[Path]") -> str | None` — it never receives a
`Finding`. Every reference in the file:

    :116          definition
    :147,181,182  comments
    :195          the ONLY write
    :411,422      self-test assertions ONLY

`main()` never mentions `unreadable`. **Falsifier, run twice independently** (once by the reviewer,
once by the coordinator) — delete the field AND its kwarg so no reference survives, then compare
PRODUCTION output over a tree with a clean doc, a tagged doc and an undecodable doc:

    BASE    rc=1      NOFIELD rc=1
    SAME EXIT CODE             : True
    PRODUCTION OUTPUT IDENTICAL: True

The thing that actually fixed r2 H1 is `visited.add(md)` at `:188` — one line, sufficient alone.
`unreadable` is an inert addition now defended by one manifest entry and two self-test cases.

**Medium, not Low, because the comment sells it as load-bearing** by citing backlog #91's four-round
type work. A reader who trusts it will believe `main()` distinguishes the two causes. It does not.
This repo's rule is *assert the PROPERTY, not the mechanism*; here the property is not asserted at
all, and the recorded reason for the mechanism is untrue.

**Two honest fixes, pick one:** wire it (see F2), or delete field + kwarg + manifest entry + the two
cases and correct the comment. What must not remain is a type whose stated reason is false.

## F2 — Medium — the r2 fix moved "cannot read this document" from CANNOT RUN (rc=2) to FAIL (rc=1), and prints a remedy that cannot apply

Same tree (one clean doc + one undecodable doc, no tags), driven at both SHAs:

    ===== 6e5b2b78 =====  rc=2   stderr: CANNOT RUN — … The corpus was NARROWED … NOT CHECKED.
    ===== f9d2c498 =====  rc=1   stdout: ✗ …/undecodable.md:0 — could not be read …
                                         … put it in backticks, as 2 documents already do.

r2 was right that the old *cause* was a lie. The replacement asserts the opposite lie: rc=1 is this
script's *"a document embeds code through a retired tag"* verdict, and the closing sentence tells the
operator to put an undecodable byte sequence in backticks. `CLAUDE.md`: *"'Cannot run' is a FAILURE,
never a pass … it must fail loudly and say treat this as NOT RUN"* — and the exit code is the
machine-readable discriminator CI reads. Same shape for a directory named `*.md`.

**Stated against itself:** the docstring's FAILS-IF (`:57-61`) *does* list the undecodable case
under FAILS, so rc=1 may be deliberate. Filed anyway because (a) the remedy sentence is wrong for
the class either way, and (b) if rc=1 is intended then `unreadable` has no possible purpose and F1
hardens from *unwired* to *unwireable*. **The two cannot both be dismissed.**

## F3 — Medium — two manifest entries CRASH the suite, via a `sorted(n)[0]` this commit introduced at `:417` — the anti-pattern the same file bans 150 lines earlier

All 14 entries redden the case they name. Two of them kill the suite doing it:

    💥 CRASH [ 6] audit reports NOTHING visited …            summary=NONE — SUITE DIED  (IndexError)
    💥 CRASH [11] an unreadable doc is dropped from VISITED … summary=NONE — SUITE DIED  (IndexError)

    CONTROL              39/39 self-test cases passed
    both mutants         cases REPORTED=37, no summary line, case 39 never executed

The crash site is **new in this commit** — `:417`, `coverage_shortfall(r, n - {sorted(n)[0]})`. The
same file forbids exactly this at `:264-269` (*"⛔ NEVER INDEX `f[0]` IN A CASE … kills the SUITE"*),
and `check-plan-code.py:1668-1669` records it as measured on **2026-09-08, the day before this
commit**: *"a suite that cannot print a `[FAIL] <case>` line is a suite the mutation harness reads
as 'caught by something else'."*

Both entries attribute correctly **today** only because their named case prints *before* line 417.
That is ordering luck, not a property.

**And the r2-H1 entry does not model its own name.** Its edit deletes `visited.add(md)` outright, so
every document goes unvisited — behaviourally identical to the sibling entry `return findings,
set()`. The faithful, weakest mutation is the literal pre-fix code:

    FAITHFUL r2-H1 MUTATION — `visited.add(md)` moved to AFTER a successful read
    red cases: ['...so it is ACCOUNTED FOR and does not read as a narrowing']
    38/39 self-test cases passed     crashed=False

Exactly one red case, the named one, suite completes. *"Prefer the WEAKEST mutation that still fails
via the case it names."* The r2-H1 **coverage genuinely exists in the case**; it is the manifest
entry that is wrong.

⚠ **The coordinator's own earlier verification MISSED this and reported "14/14 OK".** That harness
checked only whether the named case appeared in the red list; it never checked for a completion
summary or a traceback, and an uncaught exception also exits 1. Same class as the memory
*"a report format is a CONTRACT"*, walked into while quoting it.

## F4 — Low — the presence twin at `:416-417` does not defend what its comment claims

Comment: *"without this, `unreadable` could absorb ANY gap."* Measured with the manifest's own
`unreadable: bool = False → True` mutation:

    [FAIL] a TAG finding is not marked unreadable: got [True] want [False]
    ✓ ...but a genuine narrowing ALONGSIDE an unreadable doc still refuses     <- twin PASSES

The twin passes under constant-`True`, and cannot do otherwise: it calls `coverage_shortfall`, which
never sees a `Finding`. It is set arithmetic over a strict subset — a strictly weaker duplicate of
`:383`. Not vacuous (deleting the `missing` branch reddens it) but mislabelled. F1 from the test side.

## F5 — Low — the remediation count (confirming both other halves, with a fresh number)

    docs rglob("*.md")                     = 1120
    documents with a BACKTICKED mention    = 19
    => the sentence overstates by 1101

Also found independently by Codex and the coordinator. See the coordinator's **C1** for the second
half of the defect (the advice is wrong on the unreadable path).

## F6 — Low — prose left stale by the count→set change

* `:71-72` still documents the retired mechanism: *"`scanned` disagrees with the number of documents
  under `ROOT/"docs"`."* `scanned` is now compared only against `0` (`:440`); the narrowing test is
  `want - seen`.
* `:351` `case("the scanned count is the number of documents READ", len(audit(r)[1]), 2)` and `:356`
  — the value is `len(visited)`, which **by this commit's own design** counts documents that were
  *not* read. The labels say READ where the code means VISITED, which is precisely the distinction
  the commit exists to draw.

---

## Codex's High — REFUTED, independently, by both this half and the coordinator

    $ sed -n '1295p' scripts/check-plan-code.py
        md = plan.read_text(encoding="utf-8")

    raw bytes          : b'x\r```\r<!-- file: m.py -->\r'
    read_text() result : 'x\n```\n<!-- file: m.py -->\n'
    contains a raw CR? : False

`audit` reads through the same `read_text(encoding="utf-8")` at `:190`. Universal-newline
translation happens in BOTH readers before either splitter runs. `\r`'s exclusion from the `:343`
loop is correct, not an oversight. Full adjudication in the Codex half.

## Checked and found SOUND

The set-difference shortfall (attack 1) — attacked and unbroken; add/delete races fail closed ·
all four `(findings, shortfall)` states plus the `stray` branch and a `*.md` directory drive
correctly, and **there is no state where the printed text and the exit code disagree** (attack 3) ·
`--self-test` 39/39 · manifest 14, 0 duplicate names · `EXPECTED_MUTATIONS` entry 14, sum 388, by
AST · `check-selftest-counts.py` rc=0 with this file pinned · `ci.yml:166,169` and `:310` present ·
the NINE-separator claim at `:200` is right (9 differ, 8 in the case loop, `\r` correctly excluded).

## CANNOT RUN, stated rather than hidden

* **The full `--mutate .` sweep** (~15 min). A targeted equivalent was substituted that applies each
  edit and reproduces the harness's documented attribution rule verbatim. It does **not** cover
  `HARNESS_TREE` staging, the `$HOME` redirect, or per-entry control runs inside the real runner.
* **Whether the two crashing entries pass under the real runner.** The named `[FAIL]` line *is*
  emitted before the crash, which is what the runner parses, so they are expected to pass today.
  F3's claim is about fragility and a mis-modelled entry, not a red CI.
* **A tree where the two `rglob` walks diverge** — none constructed, no evidence one exists. (Note
  this is a different question from the coordinator's **C4**, which is that *both* walks are blind
  to symlinked directories, so the shortfall check cannot see that hole by construction.)

---

## ⚠ PROCESS — the first attempt at this half REVIEWED NOTHING, and looked thorough doing it

The first subagent produced 27,489 bytes that were **byte-identical** (`diff` empty) to
`docs/reviews/plan-project-dashboard-r3-claude.md` — a review already committed in this repo, of a
different plan, on a different branch, with different findings and a different verdict. It then went
idle without ever sending a report.

**Why this is the dangerous shape.** Not empty, not a crash, not a timeout — each of which announces
itself. It was fluent, internally consistent, cited executed commands with plausible output, named
real repo paths, and closed with a confident NOT CONVERGED and six must-changes. Folded unread, it
would have sent the next session to fix defects in files this branch never touches.

**Nothing in the shape of a review distinguishes right-subject from wrong-subject work.** The only
falsifier is one the reviewer cannot satisfy by copying. The retry brief required live
`git rev-parse HEAD`, `git log --oneline -1` and `git diff --stat 6e5b2b78..f9d2c498` pasted as the
first content of the report — and this review opens with them. That requirement should be standing,
not incidental.

It was caught only because the brief had been amended mid-flight to demand a FILE, for an unrelated
reason (project memory records a fork that went idle without reporting). One hazard's mitigation
caught a different hazard entirely.

# retire-plan-mode — code review round 3, Codex half

**Subject:** r2's OWN FIXES — `git diff 6e5b2b78..f9d2c498 -- scripts/` (commit `f9d2c498`).
Round 1 reviewed `71f86f9a`; round 2 reviewed r1's fixes and found three more defects, all inside
them. This round reviews r2's fixes.

**Model:** gpt-5.5 (forced). **Verdict JSON:** `docs/reviews/verdicts/retire-plan-mode-r3-codex.verdict.json`
— `gate_ran: true`, `exit_code: 0`, 2635 chars, `intrusions: []`.

**Verdict:** 1 High (**REJECTED** — refuted by measurement, below), 1 Low (**CONFIRMED**, and found
independently by the coordinator at the same line). No Blocking, no Medium.

---

## Cx-H1 — REJECTED. "CR line endings hide a live tag" — refuted by running the real read path

**The claim.** `check-plan-file-tags.py:190` hides live tags in CR-line-ending documents: Codex
measured `check-plan-code.extract()` assembling `m.py` from `x\r```\n<!-- file: m.py -->…` while
`audit()` returned zero findings "on the same bytes", and called it a false green for the fence.

**Why it does not stand.** The two halves of that sentence did not use the same bytes. The decisive
fact is how the REAL consumer read a plan, and it is one line:

    check-plan-code.check():1295   md = plan.read_text(encoding="utf-8")

Text mode, `newline=None` — **universal-newline translation**. `extract` in production therefore
never received a raw `\r`; it received exactly the text `audit` receives. Measured end to end:

    bytes on disk    b'x\r```\n<!-- file: m.py -->\n```python\nV=1\n```\n'
    after read_text  'x\n```\n<!-- file: m.py -->\n```python\nV=1\n```\n'

    A) THE REAL PATH — both sides read the file as check() does
       extract(read_text(f)) -> []        audit(f) -> 0        AGREE
    B) Codex's construction — a RAW STRING handed straight to extract()
       extract(RAW)          -> ['m.py']  audit(f) -> 0        artefact

Panel B is not a path any caller can take. Plan mode is retired besides: `main()` refuses every
entry point that reached `extract` with rc=2, so there is no live consumer to disagree with.

⚠ **THIS IS THE SECOND TIME THIS EXACT ERROR HAS BEEN MADE ON THIS FILE, BY TWO DIFFERENT
REVIEWERS, INDEPENDENTLY.** The r1/r2 session made it, measured it, corrected it, and recorded the
correction. Codex re-derived it from the outside without seeing that record. When two reviewers
reach the same wrong conclusion by different routes, the invitation is in the code — see **C3**
in the coordinator's findings: the comment at `:200-205` lists `\r` among the separators
`splitlines()` honours and never says the thing that disarms it, namely that `\r` **cannot reach
either splitter** because `read_text` normalises it first. One clause prevents a third occurrence.

## Cx-L1 — CONFIRMED. The remediation message prints a number that means something else

`check-plan-file-tags.py:463`. On the finding path the closing sentence is

    "If you are writing ABOUT the tag, put it in backticks, as {len(list(DOCS.rglob('*.md')))}
     documents already do."

That count is the WHOLE markdown corpus, not the documents that already use backticks. Codex drove
it on a temp tree of one tagged file plus one unreadable file and got *"as 2 documents already
do"*, though neither document did. On the live tree it renders **"as 1119 documents already do"**;
Codex measured 16 backticked-mention documents by its probe, the coordinator 17 by a slightly
different one — both refute 1119.

**Found independently by the coordinator, same line, same two halves of the claim.** The
coordinator adds a second defect in the same sentence: on the unreadable-only path the advice
itself is wrong — "put it in backticks" cannot fix an undecodable file — and that path only became
reachable in `f9d2c498`, because before it the shortfall returned 2 first. Recorded as **C1**.

---

## Codex's non-findings, verified and worth keeping

Recorded so the next round does not re-spend the time. Each was independently reproduced by the
coordinator except where noted.

| Checked | Result |
|---|---|
| `coverage_shortfall`'s set difference | Right property for the intended `main()` path. Add/delete races between the two walks fail CLOSED as missing/stray |
| `Finding.unreadable` absorbing corpus gaps | It does not — a narrowing alongside an unreadable doc still refuses |
| A DIRECTORY named `*.md` | `rglob` yields it, `read_text` raises `IsADirectoryError`, reported as unreadable, included in `seen`, no false narrowing |
| Directory symlinks | Not descended into on this platform; symlinked `.md` FILES are included consistently. ⚠ The coordinator files the same observation as **C4** — a latent coverage hole, because both walks share the blind enumerator so the shortfall check structurally cannot see it |
| The retargeted + cardinality mutations | Filtered temp-root mutation pass over the six relevant/re-bound entries: all measured, all killed by their expected cases. The cardinality mutant is killed by its NAMED same-size/different-set case, not only by a sibling |
| Declared counts, by running | 39/39 self-test · 229/229 · manifest 14 · `EXPECTED_MUTATIONS` 14 · sum 388 · `check-selftest-counts.py` all 30 verified |
| CI wiring | `ci.yml` runs the live guard, its self-test, `check-selftest-counts.py`, and `check-plan-code.py --mutate .` |
| The nine separators | Re-run against `extract()`; all assembled `m.py`, matching the behavioural claim |

---

## ⚠ PROCESS — this round's Codex run OVERWROTE A COMMITTED VERDICT on its first attempt

The first invocation used `--out …/r3-codex.md`. `codex-review.verdict_path()` derives the verdict
filename from that basename **with no collision check**, so it wrote
`docs/reviews/verdicts/r3-codex.verdict.json` — a file committed under PR #214 for an unrelated
review. Caught by `git status` showing ` M`, diffed, restored with `git checkout --`, and the round
re-run under the unique stem `retire-plan-mode-r3-codex.md`, which produced the verdict this
document cites.

This is a verbatim recurrence of a defect already recorded in project memory
(*"a guard's evidence path is a namespace with no allocator"* — `--out r3-codex.md` overwrote a
committed verdict). It recurred because the only thing standing against it is a note telling a
human to be careful: `write_verdict` still clobbers silently, and a collision that overwrites can
never be seen by `ls | uniq -c`. Not filed to the backlog — that is the user's step.

---

# DISPOSITIONS — folded 2026-09-09

* **Cx-H1 (High) — REJECTED**, and the *cause* of the false positive fixed rather than only the
  claim. The comment at `audit`'s splitter now states that `\r` cannot reach either splitter,
  because both readers open with `read_text(encoding="utf-8")` and universal-newline translation
  precedes all splitting — and that the case loop drives EIGHT separators because the ninth is
  unreachable, not overlooked. Two independent reviewers reached this same wrong conclusion; the
  third should not have to.
* **Cx-L1 (Low) — FIXED.** The live corpus count is removed from the remediation message entirely.
  The remedy is now chosen by finding type, so an undecodable file is no longer told to use
  backticks. Same edit as the Claude half's F5 and the coordinator's C1.

Codex's non-findings table above was re-verified after the fold and still holds, with one
correction to the coordinator's own earlier work: the targeted mutation check reported "14/14 OK"
while **two entries crashed the suite**, because it parsed for the named `[FAIL]` line and never
checked for a completion summary. Both are fixed; the re-run shows 16/16 with zero crashes.

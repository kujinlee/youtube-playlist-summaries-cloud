# Round 4 — `velocity-177` — coordinator

```yaml
round: 4
fixes_nontrivial: true
subject: velocity-177
halves:
  codex: ran
  claude: "GAP: not dispatched — rounds 2+ alternate to the half that did not author the fix; Claude took r3, and r4's risk was verifying an architecture review's factual claims, which review-method.md routes to Codex"
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: number-populations, disposition: fixed}
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: architecture-review-claims, disposition: fixed}
```

REVIEW GAP: claude — alternation, same rule: Claude took r3, and r4's risk was verifying an architecture review's factual claims, which `review-method.md` routes to Codex. Not a failure to run.


## ⛔ LINK THREE. The architecture review's remedy did not terminate it either.

**B1 (Blocking).** Rule 4 still said a `ci.yml`-only derivation *"omits the **fifteen** schema
gates"*. That is a live repository count inside the governing rule — **spelled as a word**. The
check that had just removed `33/28/54/4` was `grep -nE '\*\*[0-9]+\*\*'`: bolded digits. It could
not see a number written in letters.

⭐ **This is the fifth consecutive fix that narrowed to the form just seen** — bolded digits, then
any digits, then number-words, then `file:line` locators, then doc-relative positions (*"twenty
lines below"*). Every fix correct; none terminating; each one a **pattern**, and the next instance
wearing a different spelling. That is this repo's recorded signature for a wrong seam, and backlog
#154 already named the terminating move for exactly this shape: *"the terminating move is not a
wider pattern but a soundness check — refuse what cannot be classified."*

### The terminating move, applied: a SHAPE, not a pattern

> **A governing rule's body may contain instructions and the name of a producer to run. It makes no
> claim about the repository's contents — no count in digits or in words, no `file:line` locator, no
> "N lines below".**

**Measured while writing it, which is why the pattern route is closed rather than merely doubted:** a
numeric sweep over this section flags **most of its lines** — dates, PR ids, backlog ids, rule
numbers, row references, and the word *one* used as a pronoun — while the genuinely repo-tracking
expressions were four. That reproduces, on this section, the result `process-checklists.md` →
*Qualify every number in prose* already recorded at three scopes and rejected. **There is now nothing
to parse: the rule does not make claims that can rot.**

Four expressions removed: the word-count of schema gates, a `file:line` locator (→ the symbol name),
a doc-relative position, and a count of required workflows.

**H1 (High, instrument).** The architecture review asserted *"no process document points at the
2026-09-21 decision."* **Refuted** — `docs/roadmap-to-launch.md`'s backlog #153 section records it
too, found by a grep I did not run. ⛔ **An asserted claim, inside a review about asserted claims.**
Corrected **in place**: the decision has two homes, both documents an author writing a number has no
reason to open, and **neither `process-checklists.md` nor `review-method.md` points at either** —
narrower, and it survives.

## What r4 verified rather than accepted

Codex checked the architecture review's four load-bearing claims individually. **Verified:** the
decision exists in `CONTEXT.md` and `git show 5ffe6017` dates it to 2026-09-21; it is in none of the
thirteen ADR files. **Refuted as written:** the "no process document" claim. **Refuted as
sufficient:** *"exactly one violator survived"* — true of digits, and the merge tree still carried a
word-count and locators. It also confirmed rule 4 remains **followable** after the counts left:
*"the problem is not loss of teeth; it is that the rule kept live numeric/locator teeth in prose."*

## ⚠ Thrashing status — still armed, and it should be

`check-review-decision.py` returned `ARCHITECTURE_REVIEW` before this round and the component has now
carried fix-induced findings in **three** consecutive rounds. The architecture review was already
convened and its root-cause finding stands — the decision existed and was unfindable. What r4
establishes is that the review's *remedy* was too narrow, not that its *diagnosis* was wrong: it
removed the instances it could see with a pattern, in a review whose own finding was that patterns
are the wrong instrument here.

⚠ **The de-escalation test is NOT met and is not claimed.** B1 was a checkable falsehood about the
repository, not a wording preference.

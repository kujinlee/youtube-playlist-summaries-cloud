# Round 3 — `velocity-177` — coordinator

```yaml
round: 3
fixes_nontrivial: true
subject: velocity-177
halves:
  claude: ran
  codex: "GAP: not dispatched — rounds 2+ alternate to the half that did not author the fix (review-method.md Round topology, step 4); Codex took r2, so r3 is the Claude half"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: number-populations, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: number-populations, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: number-populations, disposition: fixed}
```

REVIEW GAP: codex — alternation, same rule: Codex took r2, so r3 is the Claude half. Not a failure to run.


## ⛔ THE THRASHING TRIGGER FIRED. This is link two in `number-populations`.

`dev-process.md`: *"It fires when **two consecutive rounds carry findings caused by the previous
round's own fix, in one component**."* r2's M1 and all three of r3's findings are `fix_induced` in
`number-populations`. **The rule also says the firing is not to be litigated** — that correction was
itself bought by a case where arguing the trigger's wording cost three rounds of being technically
right. It is recorded here as fired.

The r3 half answered the mandated question *thrashing or prose floor?* explicitly and chose
thrashing, with per-finding evidence: H1 is a **checkable contradiction**, L1 a **countable
mismatch**, and only M1 is judgement-shaped — which it labelled as such rather than counting it
silently. It also applied `review-method.md:200`'s independent test, *"can a redesign remove it?"*,
and answered **yes**.

⚠ **It stated its own falsifier**, which is why the verdict is trustworthy: *if the coordinator
rejects M1 and reads H1's second site as predating the fix, the fix-induced link disappears.* It did
not hide the condition under which it would be wrong.

## The findings

**H1 (High).** The wrong `34` still stood in **three** places, one of them the line r2's half cited
by number and which `velocity-177-r2-coordinator.md:11` records as `disposition: fixed`. Half of it
was. Worst of the three, `:487-488` was the **prescriptive** clause — *Write "34 distinct scripts
invoked by `ci.yml`"* — so a reader following rule 1b as written **produces the defect rule 1b
exists to stop.**

⛔ **And the coordinator's own verification of the r2 fix missed it by measuring a narrower
population than it claimed** — the check was `grep -rn '\*\*34\*\*'`, which matches only the
**bolded** form, while two of the three survivors were unbolded. That is the rule's own defect,
committed while verifying the fix for the rule's own defect. Fourth instance.

**M1 (Medium).** The ⛔ paragraph added in r2 generalised *"the slip is in how measuring works"* from
all four table rows. Only rows 1 and 4 are that shape; row 3 is a **scope** error and row 2 has no
measurement at all — rule 1 already catches it. Claiming four was the same defect one level up.

**L1 (Low).** *"All four rules below"* over five headings, and the rationale document's outline
omitted 1b entirely — a count of the rules, inside the rules about counts.

## The redesign, applied

**Every one of these was a figure the text had to keep in sync with the repository.** Rule 3, twenty
lines below, had already solved this: *"the survivor COUNT is deliberately not quoted here."* Rule 1b
was written doing the opposite.

So rule 1b now **quotes no live figure at all** — its examples are SHAPES, and where a count would
go they say `N`. That removes the class rather than the instance: there is no longer anything in the
rule that can drift. The live counts stay in rule 4, where they are the subject, carrying their
method (*parsing `run:` blocks*) and their date.

M1's repair keeps the four-row table whole and states what each row actually demonstrates, because
the differences are the point — two rows support the clause, and two do not.

## The numbers survived a third, stronger method

r3 re-derived 33 / 28 / 54 / 4 with a hand-rolled indentation-aware block-scalar extractor using no
YAML library, which additionally **strips shell `#` comments inside `run:` blocks** — a step neither
earlier method had — and mutation-tested it three ways, all killed. Its mutation C is the
load-bearing one: a path added in a shell comment *inside* a `run:` block takes r2's method to 34 and
leaves r3's at 33. **The `33` is robust against a class r2's method could not see.**

## ⚠ What this round does NOT settle

The trigger fired; the redesign is applied. Whether a **Phase 6 architecture review is still
convened** is a scope decision with real cost, and it is the user's — `dev-process.md` routes
thrashing to an architecture review whose job is to *find* a redesign, and here the redesign was
named by the reviewer with in-repo precedent and is ~20 lines wide. ⛔ The coordinator is not
entitled to wave the firing away on that basis; the firing is recorded, and the decision is put to
the user rather than decided by the party whose fixes caused it.

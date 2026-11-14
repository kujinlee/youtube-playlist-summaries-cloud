---
name: a-test-that-cannot-fail
description: "FIRES-WHEN: about to add or tick a check, gate, checklist item or acceptance criterion, or to change a behaviour some assertion reads. Name the observation that would make it FAIL; removing a signal makes its falsifier vacuous, not red"
metadata:
  type: feedback
---

> Merged 2 memories. Former names (still referenced by other memories): `a-checklist-item-can-be-an-unfalsifiable-guard`, `removing-a-signal-hollows-out-its-falsifier`

**The rule: ask of any check — code, checklist item, gate description or acceptance criterion — *"What observation would make this FAIL? Name it concretely. If you cannot, the item is decoration."* And before changing a behaviour, ask *"which assertion reads the thing I am about to remove?"* — re-anchor it onto something that still varies, reading CONTENT, not presence or a count.**

**How to apply:**
- Run the question over any gate list before trusting it. An item phrased as a QUESTION ("check whether …") has no pass condition either.
- Prefer replacement over retirement: build the check that CAN fail, and verify it failing before trusting it.
- A scanner that flags a shape that legitimately ships ("a JWT") fires every build, gets muted, and detects nothing — judge the claim, not the shape.
- When re-anchoring a falsifier, a count is the cheap re-anchor and where it stops half-way; read the record itself.

**Why:** a missing check is visible; a false one produces a belief. This project's instruments (`check-guard-coverage.py`, SHAPE/SEQUENCE, `mutate-schema.py`, the ratchets) all inspect CODE — none inspects a checklist or gate sentence, which is where an unfalsifiable guard hides best. And a falsifier whose signal is removed goes vacuous, not red, so a mutation naming it reports "killed" or survives silently while the code it guards is rewritten.

## History (condensed)

- **2026-08-11:** `docs/m1.4-finishup-checklist.md` B5 — *"`npm run check:confinement` passes against the **real deployed environment**"*. `scripts/check-service-confinement.ts` walks the source import graph, no network; byte-identical against prod. Replaced (PR #70) by `npm run check:deployed-bundle`, which fetches what the live server serves and decodes JWT payloads to judge the claim. During review I also published a false "34 chunks, only 9 scanned" (occurrences vs distinct URLs; it was 9 either way) — [[quote-the-code-dont-characterise-it]].
- **2026-09-06, backlog #97 (PR #230):** F11 discriminated on exit code (`WARN` vs `QUIET`); the fix stopped warning, so both sides went QUIET and the pair asserted nothing — the mutation naming it would have survived green. Re-anchored onto "was a record appended" without reading the record: Codex rewrote `flush_line` to return a constant and it passed **94/94**. F11 had already been a tautology in two prior spec versions.

Related: [[dual-review-what-it-catches]] (a guard that passes in both worlds), [[gates-detect-defects-not-design]], [[assert-the-property-not-the-mechanism]], [[a-report-format-is-a-contract]], [[a-mutation-loses-its-binding]], [[fixing-a-premise-is-not-covering-the-branch]], [[the-control-refuted-the-premise]].

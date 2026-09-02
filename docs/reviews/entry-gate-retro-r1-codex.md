<!-- codex-review: model=gpt-5.5 -->

High — Entry-only branches can still ship dashboard entries the page marks unparseable
- WHERE: scripts/check-dashboard-entry.py:25, scripts/check-dashboard-entry.py:328, scripts/gen-dashboard.py:517
- WHAT: `FLAG = re.compile(r"\[(needs-you|heads-up|resolved:\s*[^\]]*)\]")` accepts `[resolved:]`, and `added_entry_problems()` only runs `err = header_error(line[1:])`. The page later rejects the same entry in `parse_entries()` with `if not r: e["error"] = "[resolved:] with no entry id after it"`.
- WHY IT MATTERS: this patch closes only malformed header syntax. An entry-only patch like `+## 2026-09-01 [resolved:]\n+Title\n` produces `added_entry_problems: []` and `verdict(...): (0, "no tracked files changed outside the exempt paths")`, but `gen-dashboard.parse_entries()` sets `"[resolved:] with no entry id after it"`, so the page renders a broken entry after the gate passed.
- FIX: either make `header_error()` reject an empty `resolved:` payload, or have `added_entry_problems()` validate the added block through the same entry parser path that produces page errors.

Low — Nested emphasized NO-ENTRY marker is still refused
- WHERE: scripts/check-dashboard-entry.py:93, scripts/check-dashboard-entry.py:112
- WHAT: `EMPH = re.compile(r"^(\*{1,3}|_{1,3})")` strips only one homogeneous opener before `if not rest.startswith(NO_ENTRY): return None`.
- WHY IT MATTERS: `exemption_reason("**_NO-ENTRY:_** x")` returns `None`, even though this is the same deliberate emphasized-marker shape as `**NO-ENTRY:** x`, just nested. The new matcher fixes the tested bold/italic instances but not the common bold+italic form.
- FIX: recognize balanced nested emphasis around the marker, for example by peeling leading `*`/`_` runs repeatedly only when the corresponding closer appears immediately after `NO_ENTRY`.

Checks run: `python3 scripts/check-dashboard-entry.py --self-test` passed `104/104` + `13/13`; `python3 scripts/check-plan-code.py --mutate .` passed `7 files / 150 mutations / 0 survivors`. I also checked current non-doc callers for the `collect()` four-tuple and found no stale three-value unpack.

VERDICT: NOT CONVERGED

---
## Coordinator adjudication (author, not an independent half)

**Codex High — CONFIRMED BY EXECUTION**, and the class is WIDER than reported. Measured:

| header | gate | page |
|---|---|---|
| `[resolved:]` | PASS | "with no entry id after it" |
| `[resolved:   ]` | PASS | same |
| `[resolved: nonsense]` | PASS | "names no entry in this file" |
| `[resolved: 2026-09-01/99]` | PASS | same |
| `[resolved: 2026-13-45/1]` | PASS | same |

FIVE shapes, splitting into TWO problems:
- **Syntactic** (first two) — `FLAG`'s `resolved:\s*[^\]]*` permits ZERO characters. `header_error`
  can reject these with no extra information.
- **Referential** (last three) — whether an id names a real entry is a property of the WHOLE STORE.
  `added_entry_problems` only ever sees a PATCH, so it is structurally incapable of answering.

⛔ `header_error`'s docstring claims parser and ratchet "CANNOT disagree about what a header is".
**That claim is false** and was false before this slice: `parse_entries` has a PASS 2 the ratchet
never had. The author's #78 fix said it validated "the SAME grammar the page's parser uses" — it
validates a SUBSET.

**Codex Low (nested `**_NO-ENTRY:_**` refused) — CONFIRMED**, independently reproduced by the
coordinator before reading the Codex review. Fails CLOSED. Low stands.

**Author-run checks, NOT an independent review half:**
- Vacuity: reverting the emphasis fix in a /tmp copy reddens 8 of the new cases. Non-vacuous.
- The four "still inert" cases pass in both worlds BY DESIGN — they are regression guards. The
  blockquote one IS mutation-covered (`line-leading rule removed`).
- Hypothesis RAISED AND REFUTED: widening `EMPH` to `^[>\s]*(...)` left 104/104 green. Not a
  coverage gap — that mutant is EQUIVALENT, because `rest = s[len(opener):]` slices by the captured
  group's length and a `> ` prefix leaves `rest` starting at `**NO-ENTRY:`.
- ⚠ NIT: `s[len(opener):]` should be `s[m.end():]`. Identical today only because the group starts at
  position 0 — correct by luck, not construction.
- `+++ b/docs/dashboard-entries.md` does NOT match `^\+##(?!#)`; no misfire on patch headers.

## The Claude half did not run

REVIEW GAP: claude — dispatched with the same brief, signalled idle TWICE and produced no review; a second narrowed request also produced nothing. Treated as a hang per docs/plugins.md's bounded-wait rule. Codex ran and found a real High. RE-RUN THE CLAUDE HALF before treating this round as converged.

⚠ Note how this line had to be written: it was first placed as a MARKDOWN HEADING (`## REVIEW GAP: …`) and `check-review-rounds.py` did not see it, because the marker must START the line. That is the SAME prefix-blindness class as `NO-ENTRY:` in bold, fixed in PR #203 hours earlier, and as `Decide:` counted with an anchored pattern. THIRD marker in the family, caught by the gate rather than by me.

Dispatched as a subagent with the same brief. It signalled idle TWICE without producing a review;
a second, narrowed request also produced nothing. Per `docs/plugins.md`'s bounded-wait rule this is
a hang, and the half is recorded as **NOT RUN** rather than as clean. The coordinator's own checks
above are AUTHOR-RUN and do not substitute for an independent half.

⚠ The Codex half found a real High that the author's gates, 150 mutations and 0 survivors all
passed over. A single-half round is exactly the shape this project has recorded as unsafe
(memory: dual review halves are not redundant). Re-run the Claude half before treating this
round as converged.

**ROUND VERDICT: NOT CONVERGED** — 1 High (confirmed, class widened to 5 shapes), 1 Low
(confirmed), 1 nit; one review half NOT RUN.

---
name: it-already-exists-under-a-name-i-didnt-search
description: "FIRES-WHEN: about to propose BUILDING something — ⭐ 3× in one day I proposed building something the repo already had — a roadmap, a page (filed 11 days earlier), a mechanism running in production. The tell is proposing from reasoning instead of from opening the file"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-25T02:28:30.803Z
---

**MEASURED 2026-08-24**, three times in one session, same shape each time.

| # | I proposed | It already existed as |
|---|---|---|
| 1 | re-derive the stable-id roadmap (~1 hour, **wrong conclusion**) | `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` |
| 2 | `scripts/gen-adr-map-page.py` (backlog #64(2)) | **backlog #59**, filed 11 days earlier — same page, different script name |
| 3 | an anchor column on `docs/backlog.md` | `ROOTS["adr-0006-addressing"]` in `gen-backlog-page.py:357`, with 6 rows already hanging off it |

**The error is not building the wrong thing — it is building a thing that exists under a name I did
not search for.** Each time the proposal came from *reasoning about what was needed*; each time the
existing version was found only by **opening a file** (`ls` the directory, `grep` the backlog, read
the generator). #3 was caught with seconds to spare, and would have tripped this repo's own
`check-vocabulary-collisions.py`.

**How to apply — before proposing to BUILD anything, do one grep and one directory read.** Not for
the name you have in mind (that is the name that failed); for the **concept** — the noun in the
user's sentence, and the file the thing would live next to. In this repo: `docs/backlog.md`,
`docs/adr/README.md`, `scripts/`, and `ls` the target directory **without `head`** (a truncated `ls`
over 82 files caused #1 — see [[anchor-name-and-stable-id-handoff]]).

⚠ **`ls … | head -20` is the specific instrument that failed.** Count first, or sort by date, or
don't pipe it at all.

This is the self-directed version of [[one-rule-one-place]] (duplicate vocabulary is the
shadow of a duplicate mechanism) and the same family as
[[quote-the-code-dont-characterise-it]] — a premise about what exists needs a **read**, not a
recollection. ADR-0010 exists because of #1 and #2; its own *Considered options* section is the
countermeasure for #2 specifically, since the ADR format predicts a rejected alternative gets
re-proposed in six months and here it took eleven days.

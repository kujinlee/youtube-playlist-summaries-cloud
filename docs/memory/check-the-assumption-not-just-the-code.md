---
name: check-the-assumption-not-just-the-code
description: "FIRES-WHEN: debugging when the code looks right — ⭐ User lesson (2026-08-14): verify the ASSUMPTION, not just the code — when in doubt, measure it. Three times in one design session the framing constraint was wrong, and each measurement was ~2 minutes; the design got simpler each time, never harder"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-14T16:56:45.415Z
---

Raised by the user during the backlog #36 design: **"check if your assumption is indeed correct. when
in doubt, check them."**

**Why:** an unchecked assumption is not neutral — it silently *becomes* a requirement, and then gets
paid for in design complexity or in the user's data. Measured three times in one session on #36, each
probe costing ~2 minutes:

1. *"Supabase rejects Korean."* → probed 13 keys: it rejects **every non-ASCII letter**, including
   `résumé` and `año`. A Korean-specific or transliteration-based fix would have been scoped wrong and
   shipped still-broken for French and Spanish titles.
2. *"Keys just need to be ASCII."* → bisected: there is also a **267-character** cap, and it fails
   with a **500** (looks transient, gets retried) rather than the charset's honest **400**. This
   invisible constraint ruled out every reversible encoding.
3. *"`list()` must invert the encoding."* → read the three callers: they pass a logical prefix they
   already hold and read back **ASCII** leaves (`{sectionId}.r{V}.md`). Inversion was never needed →
   reversibility not needed → a hash is legal → the length wall stops binding → the vault-filename cap
   I was about to charge the user 36 characters of Korean filename for **evaporated**.

Note the direction: **every check made the design simpler, none made it harder.** The assumption was
doing work — inventing a requirement — in all three cases.

**How to apply:** before building around a constraint, ask *"have I observed this, or inferred it?"*
and prefer a 2-minute probe over an inference. Especially when the constraint is what makes the design
hard — that is the one most worth falsifying, because a constraint that shapes the whole solution is
the most expensive thing to be wrong about. Probe scripts must refuse to run against prod (assert the
URL is local) and clean up after themselves.

Sibling of [[quote-the-code-dont-characterise-it]] (a premise about existing code must paste
file:line or be labelled unverified) — this extends it from *claims about our code* to *claims about
the system on the other side of a seam*, which no in-repo validator can check. See also
[[a-test-that-cannot-fail]] and
[[an-instrument-that-edits-the-repo-corrupts-its-peers]]. **Strong `docs/portable-practices.md`
candidate** — measured, and entirely project-independent. Not filed there; that index is the user's
call ([[feedback-agree-before-filing]]).

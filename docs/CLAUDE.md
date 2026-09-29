# You are touching `docs/` — three things that have actually gone wrong here

**Kept SHORT on purpose: this file is injected on every file access under `docs/`, so every line is a
permanent context tax.** It POINTS and never restates — a second copy of a rule is a copy that drifts,
which is this repository's most-measured failure (17 instances, `check-vocabulary-collisions.py`).

**Why this file exists at all.** Measured 2026-09-29: a nested `CLAUDE.md` loads *when a file in its
directory is read or edited*, mid-session — verified with a sentinel. That makes it a **path-keyed
matcher**, the one mechanism discussed under backlog #191 that already exists rather than needing to be
built. Audited against the six failures of 2026-09-27/28, it would have fired on **four**.

---

⛔ **1. Run ALL the document guards, never a subset.** Measured 2026-09-28: after editing `backlog.md`
I ran two of them, shipped an invented table value, and put a PR red. ⚠ **There is no single command
for them** — that absence is *why* the subset happened. The list CI runs is the `python3 scripts/check-*`
steps in `.github/workflows/ci.yml`; take it from there, not from memory. A local sweep still cannot
answer the PR-only gates: `python3 scripts/check-merge-ready.py --pr <N>`.

⛔ **2. A new value in a `backlog.md` column must already be claimed.** `check-features.py` refuses a
backlog area that no node in `docs/features.md` declares. Invent one and the row *cannot be displayed* —
the failure is silent in the file and loud in CI. Read the `areas:` lines in `features.md` first.

⛔ **3. `check-dashboard-entry.py` reads the COMMITTED diff.** Run it before committing and `rc=0` means
*"no tracked files changed"*, not *"your entry is fine"* — a vacuous pass that has now been believed
twice. Commit, then run it, and check the message says **"an entry block was added"**.

---

**Everything else lives elsewhere and is not repeated here:** the gate/checklist rules in
[`process-checklists.md`](process-checklists.md), the phase spine in
[`dev-process.md`](dev-process.md), the why in [`process-rationale.md`](process-rationale.md).

⚠ **Before adding a line here, ask whether it belongs in one of those instead.** This file earns its
place only for things that go wrong *at the moment a `docs/` file is touched* — that is the signal it
is keyed to, and anything else is better placed where its own trigger fires.

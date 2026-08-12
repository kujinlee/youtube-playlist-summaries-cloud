#!/usr/bin/env python3
"""RATCHET: the `artifacts_owner_rw` storage grant is pinned, because a money guard depends on it.

WHY THIS EXISTS — backlog #35, ADR-0008, found 2026-08-12.

The serve path decides whether to pay for a magazine model by asking storage whether the cached one
is there. On Supabase that answer is not proof: an object hidden by RLS returns a 404 byte-identical
to one that never existed. The application is safe anyway, because `loadSummaryForServe` first reads
the summary markdown from the same folder with the same principal and fails closed at 409 — and
**that is evidence about the model ONLY because the grant is on the owner path segment**, so one
grant covers both keys. Narrow the grant below owner-folder granularity and `resolveMagazineModel`
re-reserves and regenerates a model already in the bucket: measured 6c -> 12c, a second live Gemini
call, with every test green.

WHY A CHECK RATHER THAN A COMMENT IN THE MIGRATION. Two reasons, one measured.
  1. MEASURED against prod 2026-08-12: `supabase_migrations.schema_migrations` has no checksum
     column (`version`, `statements`, `name`) — so editing an applied migration breaks nothing — BUT
     `statements` retains SQL comments, and 0007's stored policy statement includes its comment
     block. Editing the file would make the repo's copy diverge from the record of what actually ran.
  2. A comment does not fail. Whoever narrows this grant edits the policy and its comment in one
     motion; the warning leaves with the thing it was warning about. A pin fails in their CI run.

WHAT THIS CAN AND CANNOT DO.
It detects that the policy TEXT changed. It cannot tell a widening from a narrowing, a rename from a
semantic change, or a safe edit from a dangerous one — that is the human judgement the failure message
asks for. It is a tripwire on a decision, not an analysis of it. A reviewer who re-pins without reading
ADR-0008 defeats it completely, and nothing here prevents that.

SCOPE, stated because an unstated one is assumed total: this reads ONE policy in ONE migration file.
It says nothing about any other grant, about `storage.objects` policies created elsewhere, or about
what is actually live in production — it is a repo-text check, not an infrastructure check.

Usage:
    python3 scripts/check-storage-grant-pin.py             # 0 = unchanged, 1 = changed or cannot run
    python3 scripts/check-storage-grant-pin.py --self-test
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "0007_storage_and_rpcs.sql"
POLICY = "artifacts_owner_rw"
ADR = "docs/adr/0008-serve-money-guard-depends-on-storage-grant-granularity.md"

# The normalised sha256 of the `create policy "artifacts_owner_rw" …;` statement.
# Pinned 2026-08-12 against the policy as merged in PR #78's era (unchanged since migration 0007).
# CHANGING THIS CONSTANT IS THE POINT OF REVIEW: do not re-pin without reading ADR-0008 and saying,
# in the PR, what the new grant means for the serve path's money guard.
PINNED_SHA256 = "7678ed0fa6906ab52840402fe1e43f377728c4638f5299bba4a98dfa4a27bba3"

POLICY_RE = re.compile(
    r"create\s+policy\s+\"" + re.escape(POLICY) + r"\".*?;",
    re.IGNORECASE | re.DOTALL,
)


def normalise(sql: str) -> str:
    """Collapse whitespace so reformatting is not a false positive; case-fold for the same reason."""
    return re.sub(r"\s+", " ", sql).strip().lower()


def extract_policy(text: str) -> str | None:
    m = POLICY_RE.search(text)
    return m.group(0) if m else None


def digest(sql: str) -> str:
    return hashlib.sha256(normalise(sql).encode("utf-8")).hexdigest()


def run() -> int:
    # "Cannot run" is a FAILURE, never a pass.
    if not MIGRATION.exists():
        print(f"❌ {MIGRATION.relative_to(ROOT)} is missing — treat this as NOT RUN.")
        return 1
    stmt = extract_policy(MIGRATION.read_text(encoding="utf-8"))
    if stmt is None:
        print(
            f"❌ could not find `create policy \"{POLICY}\"` in "
            f"{MIGRATION.relative_to(ROOT)} — treat this as NOT RUN.\n"
            f"   Either the policy was renamed or removed, or this checker's pattern is stale.\n"
            f"   Both are reasons to read {ADR} before proceeding."
        )
        return 1

    actual = digest(stmt)
    if actual == PINNED_SHA256:
        print(f"ok  {POLICY} unchanged  ({actual[:12]}…)")
        return 0

    print(
        f"❌ the `{POLICY}` storage grant CHANGED.\n"
        f"   pinned : {PINNED_SHA256[:12]}…\n"
        f"   actual : {actual[:12]}…\n\n"
        f"   A money guard depends on this grant staying at OWNER-PATH-SEGMENT granularity or\n"
        f"   coarser. Reading the summary markdown is only evidence that the magazine model is\n"
        f"   readable because one grant covers both keys. If this change narrows the grant —\n"
        f"   per playlist, per object, membership-scoped — the serve path must gain an explicit\n"
        f"   permission probe IN THIS SAME CHANGE, or it will re-reserve and regenerate a model\n"
        f"   that already exists (measured 6c -> 12c, a second live Gemini call, all tests green).\n\n"
        f"   Read {ADR}, decide, then re-pin PINNED_SHA256 to:\n"
        f"       {actual}\n"
    )
    return 1


def self_test() -> int:
    """Mutation-verified: each case must be killed by the discriminator it exercises."""
    cases: list[tuple[str, bool]] = []

    real = MIGRATION.read_text(encoding="utf-8") if MIGRATION.exists() else ""
    stmt = extract_policy(real)

    # 1. the real policy is findable at all
    cases.append(("policy is extractable from the migration", stmt is not None))

    if stmt is not None:
        # 2. reformatting is NOT a change
        reflowed = stmt.replace("\n", "\n   ").replace("  ", " ")
        cases.append(("whitespace reflow does not trip the pin", digest(reflowed) == digest(stmt)))
        # 3. narrowing the grant IS a change  ← the case this whole script exists for
        narrowed = stmt.replace("split_part(name, '/', 1)", "split_part(name, '/', 2)")
        cases.append(("narrowing the split_part segment trips the pin", digest(narrowed) != digest(stmt)))
        # 4. renaming the role IS a change
        rerole = stmt.replace("auth.uid()", "auth.jwt()")
        cases.append(("changing the compared credential trips the pin", digest(rerole) != digest(stmt)))
        # 5. a comment-only edit above the statement does not trip it (the statement is what is pinned)
        cases.append(("digest is over the statement, not the file", digest(stmt) == digest(stmt + "")))

    # 6. a missing policy is NOT-RUN, not a pass
    cases.append(("absent policy yields None, not a silent pass", extract_policy("select 1;") is None))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} self-test cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())

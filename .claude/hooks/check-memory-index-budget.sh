#!/usr/bin/env bash
# The LEADING half of the memory-index budget gate — the lagging half is the
# "Memory index injection budget" step in `.github/workflows/ci.yml`.
#
# ⛔ WHY A HOOK EXISTS AT ALL, and it is not belt-and-braces. Measured 2026-10-19 (r1 CLAUDE N2)
# over two worktrees at the same HEAD: a working tree grown past the limit with NOTHING COMMITTED
# gives rc=1 OVER BUDGET, while a fresh checkout of that same HEAD — what CI sees — gives rc=0 ok.
# A session loads the WORKING TREE, so the overflow that actually degrades a session is invisible
# to CI by construction. That is backlog #309's class: the matcher reads the working file, so no
# git-shaped guard can see it. The guard was never blind; it simply had no caller here.
#
# ⛔ THE ROOT COMES FROM THE FILE THAT WAS EDITED, NOT FROM THIS SCRIPT'S LOCATION, AND THAT IS A
# CORRECTION OF MY OWN REGRESSION (r2 CLAUDE H3). The first version read
# `dirname "${BASH_SOURCE[0]}"`; I then "fixed" it by resolving symlinks, and MEASURED that made it
# worse: with this hook shared by symlink into a second checkout, it reported SILENT on a
# 25,000-character over-budget index, where the unresolved version had correctly fired OVER BUDGET.
# A loud wrong answer became a quiet one. ⚠ Neither location is the subject — the subject is the
# index the tool just wrote, so the repository is the one CONTAINING THAT FILE. This is also what
# makes it correct across git worktrees, whose indexes are different inodes.
#
# ⚠ ADVISORY, DELIBERATELY. It warns and always exits 0. A blocking hook on a docs-only threshold is
# what backlog #56 measured getting switched off, and the remedy (move history rows to the triggered
# `slice-history.md` entry) is a judgement about which rows are history — not something to force
# mid-edit. The CI step stays the one that fails.
#
# ⚠ WHAT IT CANNOT DO: it fires on writes THROUGH THE TOOL. An edit by any other route — another
# agent, an editor, a script — is unobserved, which is exactly how the backlog #309 instance arrived.
#
# ⛔ STRUCTURED JSON, NOT STDERR, AND THE PROVENANCE MATTERS MORE THAN MY OPINION.
# `.claude/hooks/surface-recall.sh` in this directory records a MEASURED finding (2026-09-29): a
# hook's plain output at exit 0 reaches the USER'S TRANSCRIPT, not the model's context. This repo
# names that defect — a gate's channel can be weaker than the gate — and I had written this advisory
# to stderr (r2 CLAUDE medium). The ACTOR here is the model: the remedy is "move history-shaped rows
# to the triggered entry", which the model performs. So it goes to `additionalContext`, by the same
# reasoning and the same mechanism as its sibling.
# ⚠ I did NOT independently re-measure the channel; this adopts a sibling's measurement. If the
# advisory is ever observed reaching nobody, that observation refutes this choice.
#
#     echo '{"tool_input":{"file_path":"docs/memory/MEMORY.md"}}' | .claude/hooks/check-memory-index-budget.sh
#     .claude/hooks/check-memory-index-budget.sh --self-test   # 24 cases
# ⟳ PR #430 r3 (Codex), THRASHING on path handling: rounds 1–3 each found one more place where BASH
# mangled a pathname — a lexical match before resolution, `$(dirname …)` and `$(…)` stripping a
# trailing newline from a checkout name and then from a FILENAME, an `elif` that kept the lexical
# root. Each fix moved the edge. The class fix is structural: NO PATHNAME PASSES THROUGH BASH. Bash
# only launches Python with the payload on stdin untouched; parsing, resolution, index identification,
# the walk to the checkout and the checker call all happen in one Python program below.
# ⚠ STATED BOUND: an index path that resolves to a file which is NOT some checkout's
# docs/memory/MEMORY.md has no checker; the hook says NOT MEASURED and names the resolved target,
# rather than measuring a different file. The checker runs under a 20 s timeout (advisory: on expiry
# it reports NOT MEASURED, never a pass).
set -uo pipefail
PROG=$(cat <<'PY'
import json, os, subprocess, sys, tempfile

GUARD = os.path.join("scripts", "check-memory-index-budget.py")
SUFFIX = ("docs", "memory", "MEMORY.md")
TIMEOUT = 20
OUT_CAP = 4000


def is_index(p):
    """True when this path names the always-loaded index: its last three components are docs/memory/MEMORY.md."""
    return isinstance(p, str) and tuple(p.split("/")[-3:]) == SUFFIX


def absolute(p, pwd):
    return p if os.path.isabs(p) else os.path.join(pwd or os.getcwd(), p)


def root_for(p):
    """The checkout CONTAINING p: the nearest ancestor holding the guard, or None. Pure Python, so no name is mangled."""
    d = os.path.dirname(p)
    while True:
        if os.path.isfile(os.path.join(d, GUARD)):
            return d
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def candidates(*paths):
    """Each checkout that CONTAINS one of these paths (walking up from it), in order, without repeats."""
    seen = []
    for p in paths:
        r = root_for(p) if p else None
        if r and r not in seen:
            seen.append(r)
    return seen


def decide(file_path, pwd):
    """-> None (not an index edit: silent), ("measure", root), or ("unmeasured", reason).

    ⟳ PR #430 r4 (Codex), SPLIT: the index is identified by FILE IDENTITY, never by spelling. Names
    always miss an alias — a case alias on a case-insensitive filesystem, a hard link — so the edited
    file is compared with `samefile` against the index of each checkout CONTAINING it (walking up from
    its lexical and its resolved path). ⚠ STATED BOUND: a hard link to an index from OUTSIDE every
    checkout is not found by any walk, so such a write is unobserved.
    """
    if not isinstance(file_path, str) or not file_path:
        return None
    lexical = absolute(file_path, pwd)
    try:
        real = os.path.realpath(lexical)
    except (OSError, ValueError):
        real = None
    for root in candidates(lexical, real):
        index = os.path.join(root, *SUFFIX)
        try:
            if os.path.samefile(lexical, index):
                return ("measure", root)
        except (OSError, ValueError):
            continue
    if is_index(lexical) or (real and is_index(real)):
        target = real if real else lexical
        return ("unmeasured", f"{file_path!r} is named like an index but is not the index of any checkout containing "
                              f"it (it resolves to {target!r}), so no checker measures it")
    return None


def emit(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))


def main(stdin_text, pwd):
    try:
        v = json.loads(stdin_text).get("tool_input", {}).get("file_path", "")
    except Exception:
        return 0
    d = decide(v, pwd)
    if d is None:
        return 0
    if d[0] == "unmeasured":
        emit(f"⚠ memory index budget: NOT MEASURED — {d[1]}. Treat this as NOT RUN, never as a pass.")
        return 0
    root = d[1]
    try:
        r = subprocess.run([sys.executable, GUARD], cwd=root, capture_output=True, text=True, errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        emit(f"⚠ memory index budget: NOT MEASURED — the checker in {root!r} ran past {TIMEOUT} s. Treat this as NOT RUN.")
        return 0
    except OSError as e:
        emit(f"⚠ memory index budget: NOT MEASURED — the checker in {root!r} could not start ({e}). Treat this as NOT RUN.")
        return 0
    out = (r.stdout or "") + (r.stderr or "")
    if len(out) > OUT_CAP:  # PR #430 r4: a checker printing 10 MB forwarded 10 MB of context
        out = out[:OUT_CAP] + f"\n… TRUNCATED at {OUT_CAP} characters"
    if r.returncode != 0 or any(l.startswith("WARNING") for l in out.splitlines()):
        emit(f"⚠ memory index budget (advisory, rc={r.returncode}, root {root}):\n{out}")
    return 0


def self_test():
    ok = fail = 0
    def t(name, got, want):
        nonlocal ok, fail
        if got == want: ok += 1
        else:
            fail += 1; print(f"  [FAIL] {name}\n         got  {got!r}\n         want {want!r}")
    for p in ("/a/b/docs/memory/MEMORY.md", "docs/memory/MEMORY.md", "./docs/memory/MEMORY.md"):
        t(f"is_index accepts {p}", is_index(p), True)
    # ⛔ ADJACENT negatives, not absurd ones: each is one edit away from the real path.
    for p in ("docs/memory/MEMORY.md.bak", "docs/memory/OTHER.md", "memory/MEMORY.md", "", "docs/memory/MEMORY.mdx"):
        t(f"is_index REJECTS {p!r}", is_index(p), False)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = os.path.realpath(tmp)
        def mk(c):
            os.makedirs(os.path.join(c, "scripts"), exist_ok=True); os.makedirs(os.path.join(c, "docs", "memory"), exist_ok=True)
            open(os.path.join(c, GUARD), "w").close(); open(os.path.join(c, "docs", "memory", "MEMORY.md"), "w").close()
        A, B, NL, NLX = (os.path.join(tmp, n) for n in ("A", "B", "nl", "nl\n"))
        for c in (A, B, NL, NLX): mk(c)
        idx = lambda c: os.path.join(c, "docs", "memory", "MEMORY.md")
        t("a direct index measures its own checkout", decide(idx(B), tmp), ("measure", B))
        t("a RELATIVE index resolves against PWD", decide("docs/memory/MEMORY.md", A), ("measure", A))
        os.makedirs(os.path.join(tmp, "h", "projects", "slug")); os.symlink(os.path.join(B, "docs", "memory"), os.path.join(tmp, "h", "projects", "slug", "memory"))
        t("the HARNESS alias measures the checkout that holds the file (r1 P1)",
          decide(os.path.join(tmp, "h", "projects", "slug", "memory", "MEMORY.md"), tmp), ("measure", B))
        os.makedirs(os.path.join(tmp, "x", "docs")); os.symlink(os.path.join(B, "docs", "memory"), os.path.join(tmp, "x", "docs", "memory"))
        t("a LEXICALLY matching alias measures the RESOLVED checkout (r2 Q1)",
          decide(os.path.join(tmp, "x", "docs", "memory", "MEMORY.md"), tmp), ("measure", B))
        t("a checkout name ending in a NEWLINE measures itself, not its sibling (r2 Q2)", decide(idx(NLX), tmp), ("measure", NLX))
        os.symlink(idx(A), os.path.join(tmp, "tail")); os.symlink(idx(B), os.path.join(tmp, "tail\n"))
        # The alias names themselves are not index paths, so only resolution identifies them.
        t("an alias FILENAME ending in a NEWLINE resolves to ITS target, not its sibling's (r3 1)",
          decide(os.path.join(tmp, "tail\n"), tmp), ("measure", B))
        os.remove(idx(A)); open(os.path.join(B, "other.md"), "w").close(); os.symlink(os.path.join(B, "other.md"), idx(A))
        # ⟳ r4: under FILE IDENTITY, A's index path IS A's index even when it links to B/other.md — it is
        # the file a session in A loads — so A measures it. r3's NOT MEASURED came from the name rule.
        t("an index that links to another file is measured as ITS OWN checkout's index (r3 2, superseded in r4)",
          decide(idx(A), tmp), ("measure", A))
        os.makedirs(os.path.join(tmp, "lone", "docs", "memory")); open(os.path.join(tmp, "lone", "x.md"), "w").close()
        os.symlink(os.path.join(tmp, "lone", "x.md"), os.path.join(tmp, "lone", "docs", "memory", "MEMORY.md"))
        d = decide(os.path.join(tmp, "lone", "docs", "memory", "MEMORY.md"), tmp)
        t("an index-named file in NO checkout is NOT MEASURED", d[0] if d else None, "unmeasured")
        os.makedirs(os.path.join(tmp, "out", "docs", "memory")); open(os.path.join(tmp, "out", "docs", "memory", "MEMORY.md"), "w").close()
        d = decide(os.path.join(tmp, "out", "docs", "memory", "MEMORY.md"), tmp)
        t("an index with no checker above it is NOT MEASURED", d[0] if d else None, "unmeasured")
        t("an adjacent file through the alias stays silent",
          decide(os.path.join(tmp, "h", "projects", "slug", "memory", "OTHER.md"), tmp), None)
        os.link(idx(B), os.path.join(B, "hardlink"))
        t("a HARD LINK to an index inside its checkout is measured (r4 2)", decide(os.path.join(B, "hardlink"), tmp), ("measure", B))
        case_alias = os.path.join(B, "docs", "memory", "memory.md")
        if os.path.exists(case_alias):  # only on a case-insensitive filesystem
            t("a CASE alias of the index is measured (r4 1)", decide(case_alias, tmp), ("measure", B))
        else:
            t("a CASE alias of the index is measured (r4 1) — case-sensitive filesystem, so it is a different file", decide(case_alias, tmp), None)
        t("an ordinary file in a checkout is silent", decide(os.path.join(B, "other.md"), tmp), None)
        os.symlink(os.path.join(tmp, "loop"), os.path.join(tmp, "loop"))
        t("a symlink loop is silent and does not raise", decide(os.path.join(tmp, "loop"), tmp), None)
        t("malformed JSON returns 0", main("{not json", tmp), 0)
        t("a non-string file_path returns 0", main('{"tool_input":{"file_path":7}}', tmp), 0)
    print(f"self-test: {ok}/{ok + fail} cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    sys.exit(main(sys.stdin.read(), os.environ.get("PWD")))
PY
)
exec python3 -c "$PROG" "$@"

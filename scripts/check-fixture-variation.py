#!/usr/bin/env python3
"""Every parameter of a function under test must be VARIED by its cases, or be exempt in writing.

    python3 scripts/check-fixture-variation.py                 # the declared POPULATION
    python3 scripts/check-fixture-variation.py --self-test     # 38 cases

⛔ WHAT THIS EXISTS FOR, AND IT WAS BOUGHT WITH SIX ADVERSARIAL ROUNDS ON ONE FILE.
Six rounds of review on `check-plan-code.py` produced six Blocking findings, and five of them are
ONE defect: a case that cannot fail for the thing it names, because every case passes the SAME
value for the parameter that decides it. The reviews found them one axis at a time:

    r2  the WANT was derived from the subject          -> fixed the want
    r3  the want was a literal but the INPUT was far
        from the boundary                              -> fixed the input's magnitude
    r5  the input was at the boundary of magnitude
        but had no POSITION ("S" * 5000 reads the
        same from either end)                          -> fixed the input's position
    r6  the label was varied on every axis and the
        OTHER TWO ARGUMENTS never were: every case
        called `progress_line(164, 434, …)`, whose
        head is exactly ten characters, so
        `PROGRESS_WIDTH - len(head)` and
        `PROGRESS_WIDTH - 10` are indistinguishable    -> and here we are

Each round improved the fixture along the axis the PREVIOUS round had been bitten by. The
generator is not any one of those axes. It is that **the fixtures vary one argument and the
reviews have been improving that one argument**. The question that catches all four at once is not
"is this input at the edge?" but:

    FOR EACH PARAMETER OF EACH FUNCTION UNDER TEST, DO AT LEAST TWO CASES PASS DIFFERENT VALUES?

Under that rule `progress_line` fails on `done`, on `total` and on the head width — which is
exactly what r6 found by hand, after five rounds of not finding it. A guard, not a rule to
remember: this project's own standard is that a convention catches what you READ and a script
catches what is THERE.

⚠ AND ITS OWN `--self-test` FLAG IS NOT GUARDED FROM INSIDE — r7 L1, measured: mutating
`if a.self_test:` to `if False:` makes `--self-test` print the ordinary OK line and exit 0, so the
CI step that runs it would pass without executing one case. No case here can catch that, because
the suite it would have to run is the thing being skipped. The observer is EXTERNAL and already
exists: `check-selftest-counts.py` has this file in its POPULATION, runs it as a subprocess, and
exits 2 when no `N/M passed` line appears. Recorded here rather than left for the next reader to
re-derive — a guard that cannot check one of its own clauses should say which other guard does.

⚠ WHAT THIS CANNOT DO, SAID PLAINLY SO PASSING IT IS NOT MISTAKEN FOR SAFETY. It compares the
SOURCE TEXT of arguments. Two call sites passing `x` and `y` satisfy it even if both evaluate to
the same thing; two passing `"S" * 5000` and `"S" * 5000` do not. So it is a floor — it proves a
parameter was *thought about*, never that the values chosen are good ones. It cannot see that
`"S" * 5000` and `"E" * 5000` are both position-free (r5's Blocking), and it would NOT have caught
r5 B1. It catches r6's class, which is the one no human question caught for five rounds.
"""
from __future__ import annotations
import argparse
import ast
import contextlib
import io
import pathlib
import sys
import tempfile

# ── THE POPULATION, DECLARED ─────────────────────────────────────────────────────────────
# §21: a check has a RULE and a POPULATION and they fail separately. An empty population is
# CANNOT RUN, never a pass — a zero over nothing is not a finding.
# ⟳ r7 B1: this file JOINED its own population once `main`'s verdict path was cased.
# It could not before — its own rule reported `main(argv=…)` unvaried, which was the
# same fact as the four surviving verdict mutations.
# ⟳ r7 H3 — DERIVED FROM DISK, not listed. A hand-written list of two files let a green tick
# imply a coverage the rule could already have had: MEASURED, 48 scripts define a self-test the
# rule can read, 35 of them report findings, and the declared population covered 1 of 16 readable
# ones. Deriving removes the drift; `POPULATION_FLOOR` keeps the count from silently falling.
# ⚠ BOTH SUITE NAMES. The first version knew only `_self_test` and returned CANNOT RUN on the 32
# files that spell it `self_test` — a refusal, not a pass, so nothing was claimed falsely; but it
# read as "this guard cannot see those" when in fact it could not see their SPELLING.
SUITE_NAMES = ("_self_test", "self_test")
POPULATION_FLOOR = 48


def population_shortfall(found: int, floor: int) -> "str | None":
    """The CANNOT-RUN line when discovery returns fewer scripts than pinned, else None. PURE.

    ⚠ Extracted so a case can reach it — r7. Inline in `main`, the only way to exercise it was
    to shrink the real repository, so the clause had no case and its mutation survived. A
    shrunken subject is not a cleaner one, and this is the sentence that says so.
    """
    if found >= floor:
        return None
    return (f"CANNOT RUN — {found} script(s) define a readable self-test, below the pinned "
            f"floor of {floor}. The population shrank; a smaller subject is not a cleaner "
            f"one. NOT CHECKED.")


def population(root: pathlib.Path) -> "list[pathlib.Path]":
    """Every script under `scripts/` that defines a suite this rule can read. PURE-ish (reads
    the directory, nothing else)."""
    out = []
    for f in sorted((root / "scripts").glob("*.py")):
        try:
            tree = ast.parse(f.read_text())
        except (OSError, SyntaxError):
            continue
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        if names & set(SUITE_NAMES):
            out.append(f)
    return out


# ── THE RATCHET ─────────────────────────────────────────────────────────────────────────
# ⛔ 126 PARAMETERS ACROSS 35 FILES ARE ALREADY UNVARIED, and this branch is not the place to
# fix them — it is seven rounds deep on a progress line. They are frozen here BY NAME, not by
# count: a count alone is satisfied by fixing one and adding another. A new unvaried parameter
# fails; a fixed one is reported so the entry can be deleted, which is how the debt shrinks.
# This is the same shape as `EXPECTED_MUTATIONS` — visible, non-growing, and reducible — rather
# than a number nobody can act on.
KNOWN_UNVARIED: dict[str, tuple[str, ...]] = {
    'begin-plan.py': (
        'cmd_begin.slug_raw', 'cmd_begin.step_args', 'pp_count_drift.actual',
        'pp_count_drift.doc', 'render_banner.steps', 'render_plan.slug',
        'render_plan.steps', 'render_plan.today', 'render_sentinel.now',
        'render_sentinel.plan_rel', 'split_step.arg',),
    'check-anchors.py': (
        'audit.cutoff', 'audit.docs', 'audit.subdirs',),
    'check-anon-exposure.py': (
        'evaluate.baseline', 'evaluate_m4_reads.expect_roles',
        'm4_functions.manifest_text',),
    'check-arch-findings.py': (
        'line_counts.rx',),
    'check-banner-armed.py': (
        'asst_toolonly.path', 'edit.path', 'log_line.detail', 'log_line.reason',
        'log_line.session', 'log_line.when', 'meta.text', 'notif.text', 'use_nb.path',
        'use_nb.tid',),
    'check-catalog-coverage.py': (
        'classify.digested', 'digested_columns.sql',),
    'check-ci-watched.py': (
        'render_sentinel.sha', 'render_sentinel.when',),
    'check-dashboard-entry.py': (
        'fence_closes.open_run',),
    'check-explainer-delivery.py': (
        'audit.shared_rel', 'audit.skills_dir',),
    'check-gate-falsifiability.py': (
        'find_gate_defects.known_scripts', 'find_gate_defects.path',
        'find_gate_defects.text',),
    'check-handoff-path.py': (
        'check_text.text',),
    'check-live-schema.py': (
        'residue.manifest', 'split_residue.manifest', 'verdict.manifest',),
    'check-paid-caller-arrival.py': (
        'ck.got', 'report.migrations_dir', 'report.root', 'report.use_live',),
    'check-plan-code.py': (
        ),
    'check-plan-progress.py': (
        'next_pending_task.plan_text', 'strip_field.key',),
    'check-producer-enumeration.py': (
        'bare_alias.expr', 'branches_in.expr', 'defining_expression.line_no',
        'defining_expression.path', 'find_table.lines',),
    'check-ratchet-contract.py': (
        'check_caller.caller_blob', 'check_caller.path', 'check_caller.text',
        'check_contract.path', 'check_contract.text', 'discover_guards.script_paths',
        'discover_ratchets.ci_yaml', 'discover_ratchets.script_texts',
        'evaluate.caller_blob_for', 'evaluate.manifest_stems', 'evaluate.texts',),
    'check-review-recorded.py': (
        'review_added.paths', 'verdict.pr_body',),
    'check-review-rounds.py': (
        'audit.reviews',),
    'check-roadmap-consistency.py': (
        'find_inconsistencies.sources',),
    'check-selection-card.py': (
        'card.question',),
    'check-selftest-counts.py': (
        'declares.count_drift', 'population_errors.pinned',),
    'check-test-counts.py': (
        'compare.actual', 'load_results.path',),
    'check-theme-token-coverage.py': (
        'palette_tokens.name',),
    'codex-review.py': (
        'classify.exit_code', 'classify.message', 'classify.min_chars',
        'classify.out_path', 'classify.stdout', 'classify.timed_out',
        'dir_snapshot.directory', 'intrusions.after', 'intrusions.before',
        'intrusions.ours', 'quarantine.created', 'quarantine.dest',
        'unexpected_writes.before', 'verdict_record.attempts',
        'verdict_record.exit_code', 'verdict_record.gate_ran',
        'verdict_record.intrusions_seen', 'verdict_record.model',
        'verdict_record.out_path', 'verdict_record.reason', 'write_verdict.record',),
    'explainer-serve.py': (
        'format_question_entry.now', 'revision.p', 'safe_path.root',),
    'gen-backlog-page.py': (
        'build.edited', 'build.generated_at', 'build.sha', 'build.stamp',
        'link_contrast_errors.minimum', 'md.text', 'plain.text', 'report_run.rows',
        'report_run.unread', 'report_unread.unread', 'rows_of.text',),
    'gen-dashboard.py': (
        'commit_dates.window', 'contrast_failures.minimum',),
    'gen-goals-page.py': (
        'parse_header.head_lines', 'parse_roots.text',),
    'gen-m4-manifest.py': (
        'has_m4.catalog', 'has_m4.manifest', 'psql.db',),
    'page_chrome.py': (
        'assert_wired.page', 'assert_wired.where', 'raises.where',),
    'page_markup.py': (
        'escape.s', 'scan.s',),
    'prior-art.py': (
        'search.show_all',),
    'subject_status.py': (
        'subject_banner.script',),
    'verify-exclusion-reasons.py': (
        'md5_payloads.sql',),
}


# ── THE FLOOR, BECAUSE THE RULE IS NON-MONOTONIC WITHOUT IT ──────────────────────────────
# ⛔ r7 H1. A parameter with ONE call site is reported; a parameter with ZERO is not examined
# at all — so DELETING the last case that drives a function UPGRADES the file from FAILED to
# OK. Measured: removing both `stderr_progress(...)` call sites took the file from 29
# parameters to 26 and rc 1 to rc 0, and renaming `progress_line` to `_progress_line` — one
# token — made its whole signature invisible. Severity moving the wrong way with coverage is
# the same perverse shape as a ratchet that can be satisfied by deleting the subject.
# Reporting every never-called public function was considered and REJECTED: measured, that is
# four functions in `check-plan-code.py` (`child_env`, `control_is_green`, `merged_output`,
# `not_measured_line`), every one of them genuinely exercised through a caller. Four standing
# false positives is how a guard gets switched off.
# What is pinned instead is the COUNT, the way `EXPECTED_MUTATIONS` pins mutations: coverage
# may grow, and a drop is a finding that names its own number.
EXAMINED_FLOOR: dict[str, int] = {
    "scripts/check-plan-code.py": 29,
    "scripts/check-fixture-variation.py": 8,
}

# ── EXEMPTIONS, EACH WITH ITS REASON ─────────────────────────────────────────────────────
# `"<function>.<parameter>": "<why one value is right>"`. A parameter genuinely decided by one
# value is not a defect; an UNWRITTEN one is. Prose here is the artefact that says the question
# was asked and answered, which is what r4 L1 proved is needed.
EXEMPT: dict[str, str] = {
    "diagnostic_tail.window": "the budget is a module constant with its own boundary cases and "
                              "its own manifest entry; callers never pass it",
    "run_suite_parts.d": "the staging directory is the fixture's own temp dir; what varies "
                         "between its call sites is `name`, which is the parameter that "
                         "selects the suite. A second directory would test the tempfile "
                         "module, not this function",
}


def _is_case_arg(node: ast.AST) -> bool:
    """A `case(...)` call is the assertion, not a call under test."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "case"


def analyse(source: str, path: str, exempt: dict | None = None) -> tuple[list[str], int]:
    """(findings, parameters examined). PURE — no filesystem, no argv.

    A parameter is EXAMINED when its function is defined in this module and called at least
    twice from the suite. Called once is reported too: one call site cannot vary anything.
    """
    # ⚠ A SUBJECT THAT DOES NOT PARSE IS A POPULATION FAILURE, NOT A RULE FAILURE — r7 L2.
    # Unguarded, `ast.parse` raised and the traceback took rc 1, which is the code this guard
    # uses for "the rule found something". §21: the rule and the population fail separately.
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ([f"CANNOT RUN — {path} does not parse ({exc.msg} at line {exc.lineno}), so no "
                 f"case can be read from it. NOT CHECKED."], 0)
    defs: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            defs.setdefault(node.name, node)

    suite = next((n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name in SUITE_NAMES), None)
    if suite is None:
        return ([f"CANNOT RUN — {path} defines no self-test, so there are no cases to read. "
                 f"NOT CHECKED."], 0)

    # arg source text per (function, parameter), across every call site inside the suite
    seen: dict[tuple[str, str], list[str]] = {}
    for node in ast.walk(suite):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        fn = defs.get(node.func.id)
        if fn is None or _is_case_arg(node):
            continue
        # ⚠ KEYWORD-ONLY PARAMETERS TOO — r7 L1. Reading `fn.args.args` alone left them out of
        # `names`, so the omitted-default synthesis below could not cover them and a kwonly
        # parameter given at one site and omitted at another recorded ONE value and was reported
        # unvaried: the exact false positive that clause exists to prevent, on the other half of
        # the grammar. Latent when found (no public function here has one) — fixed before the
        # population widened into one.
        names = [a.arg for a in fn.args.args]
        kwonly = [a.arg for a in fn.args.kwonlyargs]
        given = set()
        for i, arg in enumerate(node.args):
            if i < len(names):
                seen.setdefault((fn.name, names[i]), []).append(ast.unparse(arg))
                given.add(names[i])
        for kw in node.keywords:
            if kw.arg:
                seen.setdefault((fn.name, kw.arg), []).append(ast.unparse(kw.value))
                given.add(kw.arg)
        # ⛔ OMITTING A DEFAULTED ARGUMENT IS A VALUE, and the first version of this did not
        # count it. `mutate_delivered(root)` and `mutate_delivered(root, progress=…)` are the
        # two sides of the reporter seam that cost this branch its first Blocking — read as
        # "one call site", they looked unvaried while being the best-covered parameter here.
        # A parameter with no default cannot be omitted, so this only ever ADDS a real value.
        defaulted = names[len(names) - len(fn.args.defaults):] if fn.args.defaults else []
        defaulted += [a for a, d in zip(kwonly, fn.args.kw_defaults) if d is not None]
        for d in defaulted:
            if d not in given:
                seen.setdefault((fn.name, d), []).append("<omitted, default>")

    findings = []
    for (fn, param), values in sorted(seen.items()):
        if f"{fn}.{param}" in (EXEMPT if exempt is None else exempt):
            continue
        if len(set(values)) < 2:
            only = values[0] if values else "?"
            findings.append(
                f"{path}: `{fn}({param}=…)` is passed the SAME value at every call site in the "
                f"suite ({len(values)}x `{only[:40]}`). No case can tell that parameter apart "
                f"from a constant, so any clause that reads it is unguarded. Vary it, or add "
                f"`{fn}.{param}` to EXEMPT with the reason one value is right.")
    return findings, len(seen)


def dead_exemptions(sources: "list[tuple[str, str]]") -> list[str]:
    """Exemptions not load-bearing ANYWHERE in the population: removing one changes nothing. PURE.

    ⛔ AN UNNEEDED EXEMPTION IS WORSE THAN NO EXEMPTION — r7 H1, found by a reviewer and not by
    this guard. `progress_line.label` was exempted on the reasoning that its axes matter more than
    its literal count, and MEASURED, the parameter passed the rule with no exemption at all. The
    entry changed nothing and would have masked that axis the moment it regressed to one value.
    An exemption is a standing promise that a parameter needs no variation; one doing no work
    today is a promise nobody will re-examine. The test is the one this project applies to any
    clause: REMOVE IT AND SEE.

    ⚠ DEADNESS IS A PROPERTY OF THE POPULATION, NOT OF ONE FILE, and the first version got that
    wrong. It judged each file alone, so an exemption written for `check-plan-code.py` read as
    dead the moment the population grew to a second file — two correct exemptions were reported
    as dead by the very commit that widened it. An exemption earns its place if it is needed
    SOMEWHERE; it is dead only if it is needed NOWHERE.
    """
    out = []
    for k in EXEMPT:
        trimmed = {kk: vv for kk, vv in EXEMPT.items() if kk != k}
        fn, _, param = k.partition(".")
        needed = any(any(f"`{fn}({param}=" in x for x in analyse(src, name, exempt=trimmed)[0])
                     for src, name in sources)
        if not needed:
            out.append(f"the exemption `{k}` is DEAD — the rule passes without it anywhere in the "
                       f"population, so it guards nothing today and will mask that parameter the "
                       f"moment it stops varying. Delete it; an exemption nobody needs is one "
                       f"nobody re-examines.")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("paths", nargs="*", help="override the declared POPULATION")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()

    root = pathlib.Path(__file__).resolve().parent.parent
    targets = [pathlib.Path(p) for p in a.paths] or population(root)
    missing = [str(p) for p in targets if not p.is_file()]
    if missing or not targets:
        print(f"CANNOT RUN — population is empty or unreadable: {missing or 'no targets'}. "
              f"A zero over nothing is not a pass. NOT CHECKED.", file=sys.stderr)
        return 2

    all_findings, examined, sources, paid = [], 0, [], []
    for t in targets:
        text = t.read_text()
        f, n = analyse(text, t.name)
        # ⛔ THE RATCHET, APPLIED BY NAME. A known entry is filtered out; anything else fails.
        known = set(KNOWN_UNVARIED.get(t.name, ()))
        fresh, seen_known = [], set()
        for x in f:
            if x.startswith("CANNOT RUN"):
                fresh.append(x)
                continue
            key = x.split("`")[1].replace("(", ".").replace("=…)", "")
            (seen_known.add(key) if key in known else fresh.append(x))
        all_findings += fresh
        # ...and a known entry that no longer fires is DEBT PAID: say so, so the list shrinks
        # instead of outliving its subject. Reported, not failed — tightening is a deliberate act.
        for gone in sorted(known - seen_known):
            paid.append(f"{t.name}: `{gone}` now varies — delete it from KNOWN_UNVARIED")
        examined += n
        sources.append((text, t.name))
        floor = EXAMINED_FLOOR.get(str(pathlib.Path("scripts") / t.name))
        if floor is not None and n < floor:
            all_findings.append(
                f"{t.name}: {n} parameter(s) examined, below the pinned floor of {floor}. A "
                f"parameter with no call site at all is not examined, so DELETING the last case "
                f"that drives a function makes this guard quieter. Restore the coverage, or "
                f"lower `EXAMINED_FLOOR` deliberately and say why in the commit.")
    # ⚠ AFTER the loop, and ONLY over a population that was actually read. Deadness is judged
    # across the whole set (see the docstring), so a member that could not be parsed makes every
    # verdict about it meaningless — reporting exemptions dead on the strength of a file nobody
    # could read is a zero over nothing, which is the shape §21 exists to refuse.
    cannot = [x for x in all_findings if x.startswith("CANNOT RUN")]
    if not cannot:
        all_findings += dead_exemptions(sources)
    if cannot:
        # ⚠ `all_findings`, NOT `cannot` — deliberately. Printing only the CANNOT-RUN lines
        # made the `if not cannot:` guard above invisible: deadness was still computed, just
        # never shown, so no case could tell the guard from its absence. Printing everything
        # that was collected makes the guard's effect observable, which is what lets a mutation
        # of it be attributed.
        for x in all_findings:
            print(f"  {x}", file=sys.stderr)
        return 2
    short = None if a.paths else population_shortfall(len(targets), POPULATION_FLOOR)
    if short:
        print(f"  {short}", file=sys.stderr)
        return 2
    for x in paid:
        print(f"  ⭐ {x}")
    if all_findings:
        print(f"FAILED — {len(all_findings)} parameter(s) never varied by any case:")
        for x in all_findings:
            print(f"  ✗ {x}")
        return 1
    print(f"fixture variation OK — {examined} parameter(s) examined across {len(targets)} "
          f"file(s); {sum(len(v) for v in KNOWN_UNVARIED.values())} known-unvaried ratcheted, "
          f"{len(EXEMPT)} exempt with a written reason")
    return 0


def _self_test() -> int:
    global EXEMPT          # two blocks below swap it; the declaration must precede every use
    ok = fail = 0

    def case(name: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    SRC = '''
def progress_line(done, total, label):
    return f"[{done}/{total}] {label}"

def _self_test():
    case("a", progress_line(164, 434, "x"), "…")
    case("b", progress_line(164, 434, "y"), "…")
'''
    f, n = analyse(SRC, "t.py")
    # ⛔ THE CENTRAL CASE: `done` and `total` are the same at both sites; `label` differs.
    case("a parameter passed one value at every site is reported",
         sorted(x.split("`")[1] for x in f), ["progress_line(done=…)", "progress_line(total=…)"])
    case("...and a parameter that DOES vary is not", any("label" in x for x in f), False)
    case("...and the count of examined parameters is reported, not just the failures", n, 3)

    VARIED = SRC.replace('progress_line(164, 434, "y")', 'progress_line(7, 38, "y")')
    f2, _ = analyse(VARIED, "t.py")
    case("varying both at one site clears both", f2, [])

    # One call site cannot vary anything, and that is the shape r6 B1 actually had for `head`.
    # ⚠ NOT named `progress_line`: the live EXEMPT covers `progress_line.label`, so reusing
    # that name would have this case measure the exemption instead of the rule. Measured — it
    # reported 2 findings where the rule gives 3.
    ONE = '''
def pline(done, total, label):
    return ""

def _self_test():
    case("a", pline(164, 434, "x"), "…")
'''
    f3, _ = analyse(ONE, "t.py")
    case("a single call site is reported for every parameter", len(f3), 3)
    case("...and the message says how many times the value appears",
         "1x" in f3[0], True)

    # Keyword arguments are call sites too — `mutate_delivered(root, progress=…)` is how this
    # file's own reporter seam is driven, and reading only positional args would miss it.
    KW = '''
def f(a, b):
    return None

def _self_test():
    case("x", f(1, b=2), None)
    case("y", f(1, b=3), None)
'''
    f4, _ = analyse(KW, "t.py")
    case("keyword arguments count as call sites", [x.split("`")[1] for x in f4], ["f(a=…)"])

    # ⛔ OMITTING A DEFAULTED ARGUMENT IS A VALUE. Without this, the reporter seam that cost
    # this branch its first Blocking — `f(1)` beside `f(2, b=3)` — reads as one call site and is
    # reported as unvaried, which is a false positive on the best-covered parameter in the file.
    DEFAULTED = '''
def g(a, b=None):
    return None

def _self_test():
    case("x", g(1), None)
    case("y", g(2, b=3), None)
'''
    fD, nD = analyse(DEFAULTED, "t.py")
    case("omitting a defaulted argument counts as a distinct value", (fD, nD), ([], 2))

    # An exemption is honoured, and ONLY for the named function+parameter.
    # ⚠ PASSED, NOT PATCHED — r7. These drove the rule by swapping the global `EXEMPT`, so the
    # `exempt=` parameter was omitted at all twelve call sites and the guard's own rule reported
    # it unvaried. Using the parameter is both what the rule asks for and less stateful.
    f5, _ = analyse(SRC, "t.py", exempt={"progress_line.done": "test"})
    case("an exemption removes exactly its own finding",
         [x.split("`")[1] for x in f5], ["progress_line(total=…)"])
    f6, _ = analyse(SRC, "t.py", exempt={"progress_line.nonexistent": "test"})
    case("...and an exemption for a parameter that does not exist changes nothing",
         len(f6), 2)

    # ⚠ A file with no suite is CANNOT RUN, not a pass — the rule and the population fail
    # separately (§21), and a zero over an unread population is the shape this project has
    # been burned by four times.
    f7, n7 = analyse("def f(a):\n    return a\n", "t.py")
    # ⚠ `any(...)` NOT `f7[0]` — indexing raises when the list is empty, which is exactly what
    # this case's own mutation produces, so the suite would DIE rather than report. A case that
    # dies from its defect attributes nothing; a case that reports it names the guard.
    case("a file with no _self_test is CANNOT RUN, not a clean bill",
         (any(x.startswith("CANNOT RUN") for x in f7), n7), (True, 0))

    # `case(...)` itself is the assertion, never a subject.
    CASECALL = '''
def case(name, got, want):
    return None

def _self_test():
    case("a", 1, 1)
    case("b", 1, 1)
'''
    f8, _ = analyse(CASECALL, "t.py")
    case("the case() helper is not treated as a function under test", f8, [])

    # A function defined but never driven by the suite has no call sites to compare, so it is
    # not examined — silence here is correct, and saying so is what stops a reader assuming
    # this guard covers every function in the file.
    UNCALLED = '''
def helper(a, b):
    return a

def _self_test():
    case("a", 1, 1)
'''
    f9, n9 = analyse(UNCALLED, "t.py")
    case("a function the suite never calls is not examined", (f9, n9), ([], 0))

    # Private helpers (leading underscore) are test plumbing, not the subject.
    PRIV = '''
def _mini(root, val):
    return None

def _self_test():
    _mini(1, 2)
    _mini(1, 2)
'''
    f10, n10 = analyse(PRIV, "t.py")
    case("a private helper is test plumbing, not a subject", (f10, n10), ([], 0))

    # ⛔ A DEAD EXEMPTION IS A FINDING — r7 H1, found by a reviewer and not by this guard.
    # `progress_line.label` was exempted here while the rule passed without it, so the entry did
    # nothing today and would have masked the label axis the moment it regressed.
    _sv = dict(EXEMPT)
    try:
        EXEMPT = {"g.b": "this parameter already varies, so the exemption guards nothing"}
        case("an exemption the rule does not need is reported as DEAD",
             len(dead_exemptions([(DEFAULTED, "t.py")])), 1)
        case("...and the message names the exemption so it can be deleted",
             "`g.b`" in dead_exemptions([(DEFAULTED, "t.py")])[0], True)
        # ...and one that IS load-bearing is silent: `a` is passed 1 and 2, `b` only 3.
        ONEVAL = DEFAULTED.replace("g(1)", "g(1, b=3)")
        EXEMPT = {"g.b": "needed — b is one value at every site"}
        case("...while a load-bearing exemption is not reported",
             dead_exemptions([(ONEVAL, "t.py")]), [])
        # ⛔ NEEDED SOMEWHERE IS NOT DEAD: the same exemption, with the file that needs it SECOND
        # in the population. The first version judged each file alone and reported this as dead.
        case("...and an exemption needed by only ONE file in the population survives",
             dead_exemptions([(DEFAULTED, "a.py"), (ONEVAL, "b.py")]), [])
        # ⛔ AND main() MUST SURFACE IT, not merely compute it. Without this case, deleting
        # `+ dead_exemptions(...)` from the findings leaves the check running and its result
        # unreachable — a guard that reaches a correct verdict and drops it on the floor.
        with tempfile.TemporaryDirectory() as _td:
            _f = pathlib.Path(_td) / "t.py"
            _f.write_text(DEFAULTED)
            EXEMPT = {"g.b": "dead — b already varies at its two call sites"}
            # ⚠ CALLED DIRECTLY, output captured inline. A `_quiet_main(...)` helper was tried
            # and this guard rejected it in one run: three varied call sites collapsed into one
            # passing `argv`, so `main.argv` read as unvaried. INDIRECTION HIDES VARIATION FROM
            # A RULE THAT READS CALL SITES — a true limit of the rule, recorded rather than
            # worked around, and the reason these three lines are shaped the way they are.
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_f = main([str(_f)])
            case("main() surfaces a dead exemption as a failure", _rc_f, 1)
            # ⛔ ...AND THE CLEAN PATH, which is the other half of the verdict — r7 B1. Four
            # mutations of `main`'s gate survived at 21/21 because NO case ever drove it to
            # rc 0 or rc 1: `if all_findings:` → `if False:` printed "OK", exited 0 and threw
            # the findings away, in a script wired into CI. ⭐ The guard's OWN RULE predicted
            # it — `main(argv=…)` had one call site and one value — so the unvaried parameter
            # and the four survivors were the same fact seen twice. That is why this file is
            # now in its own POPULATION: it could not have been, while this was true.
            EXEMPT = {}
            _clean = pathlib.Path(_td) / "clean.py"
            _clean.write_text(DEFAULTED.replace("g(1)", "g(1, b=9)"))
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_clean = main([str(_clean)])
            case("...and a subject with nothing to report exits 0", _rc_clean, 0)
    finally:
        EXEMPT = _sv

    # ⟳ r7 L2 — a subject that does not parse is a POPULATION failure with its own exit code.
    fS, nS = analyse("def f(\n", "broken.py")
    case("a subject that does not parse is CANNOT RUN, not a rule finding",
         (any(x.startswith("CANNOT RUN") for x in fS), nS), (True, 0))

    # ⟳ r7 L1 — keyword-only parameters are half the signature grammar. Given at one site and
    # omitted at another, they must read as TWO values, exactly like a positional default.
    KWONLY = '''
def h(a, *, b=None):
    return None

def _self_test():
    case("x", h(1), None)
    case("y", h(2, b=3), None)
'''
    fK, nK = analyse(KWONLY, "t.py")
    case("a keyword-only parameter omitted at one site counts as varied", (fK, nK), ([], 2))

    # ⟳ r7 H1 — the floor, driven through the real entry point. A file whose coverage has been
    # DELETED must fail, not go quiet.
    _sv2 = dict(EXEMPT)
    try:
        # ⚠ NO EXEMPTIONS while this runs. With the live list, every entry reads as dead over a
        # one-file population, so `main` returned 1 for that reason and the case passed with the
        # floor disabled — measured, both floor mutations survived. The floor must be the ONLY
        # thing that can fail here, or the case is not about the floor.
        EXEMPT = {}
        with tempfile.TemporaryDirectory() as _td:
            _fl = pathlib.Path(_td) / "check-plan-code.py"   # name matches a pinned floor entry
            _fl.write_text(DEFAULTED.replace("g(1)", "g(1, b=9)"))  # 2 parameters, floor is 29
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_fl = main([str(_fl)])
            case("a file below its pinned examined floor fails", _rc_fl, 1)
            # ...and the same subject with no floor pinned for it passes, so the case above is
            # about the FLOOR and not about the file being small.
            _nf = pathlib.Path(_td) / "unpinned.py"
            _nf.write_text(DEFAULTED.replace("g(1)", "g(1, b=9)"))
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_nf = main([str(_nf)])
            case("...while the same file with no pinned floor passes", _rc_nf, 0)
            # ⛔ AND A NEW UNVARIED PARAMETER STILL FAILS — the ratchet must filter only what is
            # named in KNOWN_UNVARIED. Its mutation (swallow everything) survived until this
            # case existed, because every other case reaches `analyse` and never the filter.
            _new = pathlib.Path(_td) / "brand-new.py"
            _new.write_text(SRC)
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_new = main([str(_new)])
            case("a NEW unvaried parameter is not swallowed by the ratchet", _rc_new, 1)
            # ⟳ r7 L2 + the ordering guard: an unreadable member reports CANNOT RUN and says
            # NOTHING about exemptions, because deadness over an unparsed population is a zero
            # over nothing.
            _bad = pathlib.Path(_td) / "broken.py"
            _bad.write_text("def f(\n")
            EXEMPT = {"g.b": "would read as dead over a population nobody could parse"}
            _e = io.StringIO()
            with contextlib.redirect_stderr(_e), contextlib.redirect_stdout(io.StringIO()):
                _rc_bad = main([str(_bad)])
            case("an unreadable member says CANNOT RUN and nothing about exemptions",
                 (_rc_bad, "is DEAD" in _e.getvalue()), (2, False))
    finally:
        EXEMPT = _sv2

    # ⟳ r7 H3: the population is DERIVED now, so what is asserted is that discovery finds a
    # real set and that every pinned floor names a file discovery actually returns.
    _root = pathlib.Path(__file__).resolve().parent.parent
    _pop = population(_root)
    case("a population below its pinned floor is CANNOT RUN",
         (population_shortfall(47, 48) or "").startswith("CANNOT RUN"), True)
    # ⚠ A SECOND FLOOR VALUE — the guard's own rule again: three call sites all passing 48 left
    # `floor` indistinguishable from a constant, so `found >= floor` could have been `found >= 48`.
    case("...and one at or above it is not reported",
         (population_shortfall(48, 48), population_shortfall(99, 7)), (None, None))

    case("discovery finds at least the pinned floor of scripts with a suite",
         len(_pop) >= POPULATION_FLOOR, True)
    case("...and every pinned examined-floor names a file discovery returns",
         all(any(str(pathlib.Path("scripts") / f.name) == k for f in _pop)
             for k in EXAMINED_FLOOR), True)
    case("...and every ratcheted file is one discovery returns",
         sorted(set(KNOWN_UNVARIED) - {f.name for f in _pop}), [])
    # ⚠ A SECOND ROOT, because this guard's own rule asked for one: `population(root=…)` had a
    # single call site until now. A tree with no `scripts/` yields nothing — which is also the
    # shape that must trip the population floor rather than read as a clean repo.
    with tempfile.TemporaryDirectory() as _er:
        case("discovery over a tree with no scripts/ finds nothing",
             population(pathlib.Path(_er)), [])
    case("...and every exemption carries a non-empty reason",
         all(isinstance(v, str) and v.strip() for v in EXEMPT.values()), True)
    case("...and every exemption names a function and a parameter",
         all(len(k.split(".")) == 2 and all(k.split(".")) for k in EXEMPT), True)

    # The real subject, read from disk — the guard must be able to run on what it ships for.
    root = pathlib.Path(__file__).resolve().parent.parent
    live = root / "scripts" / "check-plan-code.py"
    # ⚠ UNCONDITIONAL. These were guarded by `if live.is_file()`, so the case COUNT varied with
    # the state of the world — and a suite whose count moves cannot be ratcheted. The existence
    # of the file is its own case; the reads below assume it and fail loudly if wrong.
    case("the declared population exists on disk", live.is_file(), True)
    f11, n11 = analyse(live.read_text() if live.is_file() else "", live.name)
    case("...and reading it examines a non-zero number of parameters", n11 > 0, True)
    case("...and it reports no CANNOT RUN on the live file",
         any(x.startswith("CANNOT RUN") for x in f11), False)

    case("main() refuses an unreadable population with rc 2",
         main(["/nonexistent/nope.py"]), 2)

    print(f"\n{ok}/{ok + fail} passed")
    if ok + fail != 38:
        print(f"  [DRIFT] the docstring declares 38 cases; the suite ran {ok + fail}")
        return 1
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())

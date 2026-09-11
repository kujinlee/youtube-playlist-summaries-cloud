#!/usr/bin/env python3
"""Every parameter of a function under test must be VARIED by its cases, or be exempt in writing.

    python3 scripts/check-fixture-variation.py                 # the declared POPULATION
    python3 scripts/check-fixture-variation.py --self-test     # 48 cases

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


def population_drift(found: "list[str]", pinned: "list[str]") -> "str | None":
    """The CANNOT-RUN line when discovery returns a DIFFERENT SET than pinned, else None. PURE.

    ⛔ IDENTITY, NOT CARDINALITY — r8, Codex B1, measured. This pinned a COUNT, and a count is
    preserved by SUBSTITUTION: making `check-docs.py` unparseable while adding one new script
    kept the total at 48 and the guard reported OK **over a different set**. A departure and an
    arrival cancelled out. Comparing the names cannot be satisfied that way.
    ⚠ Both directions are reported. An arrival is not a failure of the subject, but it IS a file
    nobody pinned a floor for, so it would be examined with nothing ratcheting its coverage.
    """
    gone, new = sorted(set(pinned) - set(found)), sorted(set(found) - set(pinned))
    if not gone and not new:
        return None
    parts = []
    if gone:
        parts.append(f"no longer discovered: {', '.join(gone)}")
    if new:
        parts.append(f"newly discovered and unpinned: {', '.join(new)}")
    return (f"CANNOT RUN — the population is not the pinned set ({'; '.join(parts)}). A count "
            f"is preserved by substitution, so the SET is what is pinned. Update EXAMINED_KEYS "
            f"deliberately. NOT CHECKED.")


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
# ⛔ THE PARAMETERS LISTED BELOW ARE ALREADY UNVARIED, and this branch is not the place to
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
        'log_line.detail', 'log_line.reason', 'log_line.session', 'log_line.when',),
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
        'report.migrations_dir', 'report.root', 'report.use_live',),
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
        'assert_wired.page', 'assert_wired.where',),
    'page_markup.py': (
        'escape.s', 'scan.s',),
    'prior-art.py': (
        'search.show_all',),
    'subject_status.py': (
        'subject_banner.script',),
    'verify-exclusion-reasons.py': (
        'md5_payloads.sql',),
}


# ── WHAT WAS EXAMINED, PINNED BY NAME ───────────────────────────────────────────────────
# ⛔ r7 H1 pinned a per-file COUNT, because the rule is non-monotonic: a parameter with ONE call
# site is reported, one with ZERO is not examined at all, so deleting the last case that drives a
# function made this guard quieter. r8 then widened that count from 2 files to 48.
# ⟳ r9 B2 — AND A COUNT IS PRESERVED BY SUBSTITUTION, which r8's own commit message says in so
# many words about the population-level count it had just replaced with a name set. Within one
# file a departure and an arrival cancel out identically: measured, privatising a function and
# adding a decoy left the headline `402 parameter(s) examined` byte-identical to the control.
# 287 of the 402 keys — 71%, the healthy varied coverage this pin exists to protect — were held
# by nothing but that number.
# So the SET is pinned, as it already was at the population level. A key that stops being
# examined is a finding that names itself.
# ⚠ RESIDUAL, STATED RATHER THAN PAPERED OVER: identity here is `function.parameter`, a NAME. A
# replacement function with the same name AND the same signature is indistinguishable from the
# original by any means this guard has, and r9 B1 demonstrated exactly that construction. Name
# identity cannot be repaired by adding another name-shaped proxy — that is the move r8 made
# twice and r9 refuted twice. What is closed is every case where the signature differs, which
# includes plain privatisation, renaming, and parameter changes.
EXAMINED_KEYS: dict[str, tuple[str, ...]] = {
    'begin-plan.py': (
        'cmd_begin.slug_raw', 'cmd_begin.step_args', 'cmd_pause.why',
        'first_unticked.steps', 'normalise_slug.raw', 'parse_steps.plan_text',
        'pp_count_drift.actual', 'pp_count_drift.doc', 'render_banner.index',
        'render_banner.steps', 'render_plan.slug', 'render_plan.steps',
        'render_plan.today', 'render_sentinel.now', 'render_sentinel.plan_rel',
        'split_step.arg', 'tick.index', 'tick.plan_text',),
    'brief-compose.py': (),
    'build-m4-schema.py': (
        'apply_edits.s03', 'apply_edits.s04', 'assert_end_state.sql',
        'strip_comments.sql',),
    'check-anchors.py': (
        'audit.cutoff', 'audit.docs', 'audit.floor', 'audit.roots_text', 'audit.subdirs',),
    'check-anon-exposure.py': (
        'derive_no_session_access.relations', 'derive_no_session_access.spec_text',
        'evaluate.allow', 'evaluate.baseline', 'evaluate.funcs', 'evaluate.money',
        'evaluate_m4.expect_roles', 'evaluate_m4.m4rel', 'evaluate_m4.no_access',
        'evaluate_m4_functions.expect_roles', 'evaluate_m4_functions.m4fn',
        'evaluate_m4_reads.expect_roles', 'evaluate_m4_reads.m4rel',
        'evaluate_m4_reads.no_access', 'm4_functions.manifest_text',
        'm4_relations.manifest_text', 'parse_rows.stdout', 'pg_bool.s',
        'session_readable.spec_text',),
    'check-arch-findings.py': (
        'line_counts.line', 'line_counts.rx', 'line_counts.skip_comments',),
    'check-backlog-closure.py': (
        'closing_ids.subjects', 'findings.closes', 'findings.markers',
        'row_markers.text',),
    'check-banner-armed.py': (
        'assistant_texts_since_last_user.lines', 'decide.armed', 'decide.edited',
        'decide.steps', 'decide.texts', 'edited_paths_of.records',
        'highest_banner.texts', 'is_judgable.window', 'judged_window.wins',
        'log_line.detail', 'log_line.reason', 'log_line.session', 'log_line.when',
        'records_since_last_user.lines', 'run_decide.payload', 'texts_of.records',
        'windows.records',),
    'check-catalog-coverage.py': (
        'classify.column', 'classify.digested', 'digested_columns.sql',),
    'check-ci-watched.py': (
        'decide.head_sha', 'decide.rows', 'decide.watching_sha', 'parse_sentinel.text',
        'render_sentinel.sha', 'render_sentinel.when', 'unresolved_checks.rows',),
    'check-dashboard-entry.py': (
        'added_entry_problems.patch', 'added_reference_errors.base_text',
        'added_reference_errors.head_text', 'decision_errors.category',
        'decision_errors.plain', 'decisions.plain', 'exemption_reason.marker',
        'exemption_reason.pr_body', 'fence_closes.open_run', 'fence_closes.rest',
        'fence_closes.run', 'fenced_lines.text', 'header_error.line',
        'parse_entries.text', 'verdict.added_entry', 'verdict.changed',
        'verdict.entry_problems', 'verdict.pr_body', 'verdict.ref_problems',),
    'check-docs.py': (),
    'check-explainer-delivery.py': (
        'audit.page_skills', 'audit.shared_rel', 'audit.skills_dir',),
    'check-fixture-variation.py': (
        'analyse.exempt', 'analyse.path', 'analyse.source', 'dead_exemptions.sources',
        'main.argv', 'population.root', 'population_drift.found',
        'population_drift.pinned',),
    'check-function-revokes.py': (
        'audit.allow', 'audit.files', 'migrations.d',),
    'check-gate-falsifiability.py': (
        'find_gate_defects.current_release', 'find_gate_defects.known_scripts',
        'find_gate_defects.path', 'find_gate_defects.sections', 'find_gate_defects.text',),
    'check-guard-coverage.py': (
        'evaluate.covered_by', 'evaluate.exempt', 'evaluate.guards', 'evaluate.labels',
        'evaluate.live',),
    'check-handoff-path.py': (
        'check_file.path', 'check_text.text',),
    'check-live-schema.py': (
        'ambiguous.live', 'ambiguous.manifest', 'forbidden.live', 'load_accepted.path',
        'owned_relations.manifest', 'residue.live', 'residue.manifest', 'residue.mode',
        'split_residue.live', 'split_residue.manifest', 'unexpected.accepted',
        'unexpected.live', 'unexpected.manifest', 'verdict.accepted', 'verdict.live',
        'verdict.manifest', 'verdict.mode',),
    'check-paid-caller-arrival.py': (
        'report.migrations_dir', 'report.root', 'report.use_live',),
    'check-plan-code.py': (
        'count_drift.actual', 'count_drift.doc', 'diagnostic_tail.stderr',
        'diagnostic_tail.stdout', 'diagnostic_tail.window', 'home_escapes.src',
        'load_manifests.root', 'main.argv', 'mutate_delivered.progress',
        'mutate_delivered.root', 'parse_fail_names.out', 'progress_line.done',
        'progress_line.label', 'progress_line.total', 'run_mutations.d',
        'run_mutations.known', 'run_mutations.muts', 'run_mutations.progress',
        'run_suite.d', 'run_suite.name', 'run_suite_parts.d', 'run_suite_parts.name',
        'stage_tree.dest', 'stage_tree.root', 'stderr_progress.done',
        'stderr_progress.label', 'stderr_progress.total', 'tally_line.ok',
        'tally_line.verdict',),
    'check-plan-file-tags.py': (
        'audit.root', 'coverage_shortfall.docs_root', 'coverage_shortfall.seen',),
    'check-plan-progress.py': (
        'count_steps.plan_text', 'decide.plan_text', 'decide.prev_unticked',
        'decide.sentinel_text', 'decide.stop_hook_active',
        'next_pending_task.plan_text', 'parse_sentinel.text', 'strip_field.key',
        'strip_field.text',),
    'check-plan-task-order.py': (
        'forward_refs.consumes', 'forward_refs.preexisting', 'forward_refs.produces',
        'identifiers_in.line', 'parse_plan.text',),
    'check-producer-enumeration.py': (
        'bare_alias.expr', 'branches_in.expr', 'defining_expression.ident',
        'defining_expression.line_no', 'defining_expression.path', 'find_table.lines',),
    'check-ratchet-contract.py': (
        'check_caller.caller_blob', 'check_caller.path', 'check_caller.text',
        'check_contract.path', 'check_contract.text', 'discover_guards.script_paths',
        'discover_ratchets.ci_yaml', 'discover_ratchets.script_texts',
        'evaluate.caller_blob_for', 'evaluate.manifest_stems', 'evaluate.texts',),
    'check-review-recorded.py': (
        'guarded_changes.paths', 'review_added.paths', 'verdict.added',
        'verdict.changed', 'verdict.pr_body', 'verdict.reason_of',),
    'check-review-rounds.py': (
        'audit.known', 'audit.reviews', 'has_gap_line.text', 'parse.name',
        'read_verdicts.directory', 'verdict_problems.records',
        'verdict_problems.review_names',),
    'check-roadmap-consistency.py': (
        'find_inconsistencies.sources',),
    'check-selection-card.py': (
        'card_problems.questions', 'payload_of.raw',),
    'check-selftest-counts.py': (
        'borrow_errors.mod', 'declares.count_drift', 'declares.src',
        'population_errors.found', 'population_errors.pinned', 'printed_total.out',),
    'check-sentinel-meanings.py': (
        'evaluate.conjunction_ok', 'evaluate.live', 'evaluate.meanings',),
    'check-storage-grant-pin.py': (
        'digest.sql', 'extract_policy.text',),
    'check-test-counts.py': (
        'actual_counts.results', 'assert_describes_this_tree.config',
        'assert_describes_this_tree.results', 'compare.actual', 'compare.documented',
        'documented_counts.roadmap_text', 'load_results.path', 'test_sources.config',),
    'check-theme-token-coverage.py': (
        'audit.known_gap', 'audit.light', 'audit.shim', 'palette_tokens.name',
        'palette_tokens.text', 'shim_tokens.text',),
    'check-vocabulary-collisions.py': (
        'evaluate.allowed', 'evaluate.cols', 'evaluate.stems',),
    'codex-review.py': (
        'classify.exit_code', 'classify.message', 'classify.min_chars',
        'classify.out_path', 'classify.stdout', 'classify.timed_out',
        'dir_snapshot.directory', 'intrusions.after', 'intrusions.before',
        'intrusions.ours', 'prompt_demands_a_file.text', 'quarantine.created',
        'quarantine.dest', 'unexpected_writes.after', 'unexpected_writes.before',
        'unexpected_writes.written_by_us', 'verdict_path.out_path',
        'verdict_path.override', 'verdict_record.attempts', 'verdict_record.exit_code',
        'verdict_record.gate_ran', 'verdict_record.intrusions_seen',
        'verdict_record.model', 'verdict_record.out_path', 'verdict_record.reason',
        'watched_dirs.out_path', 'write_verdict.path', 'write_verdict.record',),
    'coverage_verdict.py': (
        'not_measured_reason.cause', 'not_measured_reason.declared',
        'not_measured_reason.entries',),
    'explainer-serve.py': (
        'explainers.root', 'format_question_entry.now', 'format_question_entry.payload',
        'index_html.root', 'is_fragment.p', 'is_standing.p', 'latest_target.root',
        'md_render.text', 'pid_alive.pid', 'question_text.payload', 'resolve_page.root',
        'resolve_page.url_path', 'revision.p', 'safe_path.root', 'safe_path.url_path',
        'stale_verdict.built_ns', 'stale_verdict.newest_source_ns',),
    'gen-backlog-page.py': (
        'build.edited', 'build.generated_at', 'build.rows', 'build.sha', 'build.stamp',
        'build.unread', 'bundle_options.rows', 'bundle_tags.raw',
        'changes_from_versions.versions', 'contradiction_errors.rows', 'dep_rank.num',
        'dependency_mermaid.by_num', 'dependency_svg.by_num', 'depends_errors.depends',
        'depends_errors.open_nums', 'depends_errors.roots', 'drift_notes_for.rows',
        'drift_notes_for.unread', 'is_delimiter.line', 'link_contrast_errors.minimum',
        'link_contrast_errors.page', 'link_rule_drift.page', 'md.text', 'parse.lines',
        'parse.unread', 'plain.text', 'report_run.rows', 'report_run.unread',
        'report_unread.unread', 'row_ish.line', 'rows_of.text',
        'sanitise_groups.groups', 'sanitise_groups.open_nums', 'undescribed.groups',
        'undescribed.open_nums', 'unread_note.unread', 'waiting_on.size',
        'word_diff.after', 'word_diff.before',),
    'gen-dashboard.py': (
        'badge_of.cleared', 'badge_of.entry', 'bucket_days.dates',
        'bucket_days.entries', 'bucket_days.today', 'bucket_days.window', 'build.days',
        'build.entries', 'build.exempt_error', 'build.exemptions', 'build.generated_at',
        'build.git_error', 'build.pr_error', 'build.prs', 'build.store',
        'build.store_error', 'build.window', 'cleared_ids.entries',
        'commit_dates.window', 'contrast_failures.html', 'contrast_failures.minimum',
        'contrast_ratio.bg', 'contrast_ratio.fg', 'main.argv', 'pr_state.budget',
        'pr_state.cache', 'pr_state.n', 'scheme_palettes.css', 'unresolved.entries',
        'unresolved_heads_up.entries',),
    'gen-goals-page.py': (
        'parse_adr.text', 'parse_header.head_lines', 'parse_header.text',
        'parse_milestones.text', 'parse_registry.text', 'parse_roots.text',),
    'gen-m4-manifest.py': (
        'derive.source', 'has_m4.catalog', 'has_m4.manifest', 'psql.db', 'psql.sql',),
    'page_chrome.py': (
        'assert_wired.page', 'assert_wired.where', 'chrome_bar.refresh',
        'chrome_bar.slug', 'chrome_bar.when', 'has_control.page',
        'missing_palettes.page', 'provenance.now', 'provenance.root', 'stamp.when',),
    'page_markup.py': (
        'escape.s', 'safe_href.url', 'scan.s', 'trim_url_tail.url',),
    'prior-art.py': (
        'search.show_all', 'search.terms',),
    'subject_status.py': (
        'last_commit.path', 'runtime_references.tables', 'subject_banner.script',
        'subject_banner.subject', 'subject_tables.subject',),
    'verify-exclusion-reasons.py': (
        'md5_payloads.sql',),
}

# ── EXEMPTIONS, EACH WITH ITS REASON ─────────────────────────────────────────────────────
# `"<function>.<parameter>": "<why one value is right>"`. A parameter genuinely decided by one
# value is not a defect; an UNWRITTEN one is. Prose here is the artefact that says the question
# was asked and answered, which is what r4 L1 proved is needed.
# ⛔ KEYED `file:function.parameter` — r8 H2. `KNOWN_UNVARIED` was keyed by file and this was
# not, so an exemption written for one script silenced the same `function.parameter` in EVERY
# script. r7 widened the population from 2 files to 48 and gave only one of the two ratchets a
# file dimension; a brand-new script defining a function called `run_suite_parts` would have
# inherited an excuse written about a different file entirely.
EXEMPT: dict[str, str] = {
    "check-plan-code.py:diagnostic_tail.window": "the budget is a module constant with its own boundary cases and "
                              "its own manifest entry; callers never pass it",
    "check-plan-code.py:run_suite_parts.d": "the staging directory is the fixture's own temp dir; what varies "
                         "between its call sites is `name`, which is the parameter that "
                         "selects the suite. A second directory would test the tempfile "
                         "module, not this function",
}


def _is_case_arg(node: ast.AST) -> bool:
    """A `case(...)` call is the assertion, not a call under test."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "case"


def analyse(source: str, path: str,
            exempt: dict | None = None) -> "tuple[list[str], set[str]]":
    """(findings, the set of `fn.param` keys EXAMINED). PURE — no filesystem, no argv.

    A parameter is EXAMINED when its function is defined at module level and called from
    the suite. Called once is reported too: one call site cannot vary anything.

    ⛔ THE SECOND RETURN VALUE IS A SET, NOT A COUNT — r8 B1, and the count was why the
    ratchet could be satisfied by deleting the subject. With only a number, "this entry
    did not fire" and "this parameter is no longer examined at all" are the same
    observation, and the caller reported both as DEBT PAID: renaming one public function
    to `_private` took three parameters out of the guard's field of view and earned three
    gold stars. The set makes the two distinguishable, which is the whole fix.
    """
    # ⚠ A SUBJECT THAT DOES NOT PARSE IS A POPULATION FAILURE, NOT A RULE FAILURE — r7 L2.
    # Unguarded, `ast.parse` raised and the traceback took rc 1, which is the code this guard
    # uses for "the rule found something". §21: the rule and the population fail separately.
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ([f"CANNOT RUN — {path} does not parse ({exc.msg} at line {exc.lineno}), so no "
                 f"case can be read from it. NOT CHECKED."], set())
    suite = next((n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name in SUITE_NAMES), None)
    # ⛔ PLUMBING IS DISTINGUISHED BY LOCATION, NOT BY A NAMING CONVENTION — r8 M1. The leading
    # underscore was a proxy: measured, 82 of the 484 "parameters examined" across 22 files
    # belonged to helpers DEFINED INSIDE the suite, and 9 of the 124 ratcheted findings were
    # about them. A fixture builder is plumbing whether or not someone remembered the underscore.
    inner = {n for s_ in ([suite] if suite else [])
             for n in ast.walk(s_) if isinstance(n, ast.FunctionDef)}
    defs: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
                and node not in inner):
            defs.setdefault(node.name, node)

    if suite is None:
        return ([f"CANNOT RUN — {path} defines no self-test, so there are no cases to read. "
                 f"NOT CHECKED."], set())

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
        # ⛔ POSITIONAL-ONLY FIRST — r8 L1, and this one fails WORSE than the kwonly gap above.
        # Positional arguments are matched to `names` BY INDEX, so a `/` in the signature shifted
        # every mapping: arguments were recorded against the WRONG parameter, not merely dropped.
        # r7 called kwonly "the other half of the signature grammar"; there is a third part.
        names = [a.arg for a in fn.args.posonlyargs] + [a.arg for a in fn.args.args]
        kwonly = [a.arg for a in fn.args.kwonlyargs]
        # ⛔ `*args` AND `**kwargs` ARE PARAMETERS — r9, Codex B1. Omitting them did not merely
        # lose coverage, it made a whole function INVISIBLE: `def target(*items)` examined ZERO
        # parameters and the gate passed. And `target(**options)` called as `target(mode=1)`
        # recorded `target.mode` — a key naming something that is not a formal parameter at all.
        # Extra positionals belong to the vararg; unrecognised keywords belong to the kwarg.
        vararg = fn.args.vararg.arg if fn.args.vararg else None
        kwarg = fn.args.kwarg.arg if fn.args.kwarg else None
        given, extra_pos, extra_kw = set(), [], []
        for i, arg in enumerate(node.args):
            if i < len(names):
                seen.setdefault((fn.name, names[i]), []).append(ast.unparse(arg))
                given.add(names[i])
            elif vararg:
                extra_pos.append(ast.unparse(arg))
        for kw in node.keywords:
            if kw.arg is None:                      # `**payload` at the call site
                if kwarg:
                    extra_kw.append("**" + ast.unparse(kw.value))
            elif kw.arg in names or kw.arg in kwonly:
                seen.setdefault((fn.name, kw.arg), []).append(ast.unparse(kw.value))
                given.add(kw.arg)
            elif kwarg:
                extra_kw.append(f"{kw.arg}={ast.unparse(kw.value)}")
        # ⚠ ONE VALUE PER CALL SITE, not one per element. A single `target(1, 2)` must not read as
        # two differing values — one call site cannot vary anything, which is this rule's premise.
        if vararg:
            seen.setdefault((fn.name, vararg), []).append("(" + ", ".join(extra_pos) + ")")
            given.add(vararg)
        if kwarg:
            seen.setdefault((fn.name, kwarg), []).append("{" + ", ".join(extra_kw) + "}")
            given.add(kwarg)
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
        if f"{path}:{fn}.{param}" in (EXEMPT if exempt is None else exempt):
            continue
        if len(set(values)) < 2:
            only = values[0] if values else "?"
            findings.append(
                f"{path}: `{fn}({param}=…)` is passed the SAME value at every call site in the "
                f"suite ({len(values)}x `{only[:40]}`). No case can tell that parameter apart "
                f"from a constant, so any clause that reads it is unguarded. Vary it, or add "
                f"`{fn}.{param}` to EXEMPT with the reason one value is right.")
    return findings, {f"{fn}.{param}" for fn, param in seen}


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
    # ⚠ AN EMPTY POPULATION IS CANNOT RUN, NOT "EVERY EXEMPTION IS DEAD" — r8 L2. `any(... for
    # ... in [])` is False, so with no sources every exemption read as needed-nowhere and was
    # reported dead. A zero over nothing is the shape §21 exists to refuse, and this function is
    # public and called from two places.
    if not sources:
        return ["CANNOT RUN — deadness was judged over an EMPTY population, so every exemption "
                "would read as needed nowhere. NOT CHECKED."]
    out = []
    for k in EXEMPT:
        trimmed = {kk: vv for kk, vv in EXEMPT.items() if kk != k}
        kfile, _, rest = k.partition(":")
        fn, _, param = rest.partition(".")
        needed = any(any(f"`{fn}({param}=" in x for x in analyse(src, name, exempt=trimmed)[0])
                     for src, name in sources if name == kfile)
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
        f, keys = analyse(text, t.name)
        n = len(keys)
        # ⛔ THE RATCHET, APPLIED BY NAME. A known entry is filtered out; anything else fails.
        known = set(KNOWN_UNVARIED.get(t.name, ()))
        # ⛔ THREE CAUSES, NOT TWO — r9 M1, and this is r8 B1's defect a third time. A ratcheted
        # key produces no finding because (a) it started varying — paid; (b) it is no longer
        # examined — lost; or (c) IT IS EXEMPT, suppressed before the finding is ever emitted.
        # r8 partitioned (a) and (b) and left (c) landing in the paid bucket, where an
        # exempt-and-ratcheted key would earn a permanent false gold star nobody can act on.
        exempted = {k.split(":", 1)[1] for k in EXEMPT if k.startswith(f"{t.name}:")}
        fresh, seen_known = [], set()
        for x in f:
            if x.startswith("CANNOT RUN"):
                fresh.append(x)
                continue
            key = x.split("`")[1].replace("(", ".").replace("=…)", "")
            (seen_known.add(key) if key in known else fresh.append(x))
        all_findings += fresh
        # ⛔ PAID versus LOST, and they are NOT the same observation — r8 B1. A ratcheted entry
        # stops firing either because the parameter started varying (paid) or because it left the
        # guard's field of view entirely (lost: renamed, privatised, its last call site deleted).
        # This reported both as paid, so a one-token `audit` -> `_audit` refactor across 17 call
        # sites earned THREE GOLD STARS while three parameters went unwatched. The key set from
        # `analyse` is what tells them apart.
        for gone in sorted(known & keys - seen_known - exempted):
            paid.append(f"{t.name}: `{gone}` now varies — delete it from KNOWN_UNVARIED")
        for lost in sorted(known - keys):
            all_findings.append(
                f"{t.name}: `{lost}` is ratcheted but NO LONGER EXAMINED — its function was "
                f"renamed, made private, or lost its last call site. That is coverage leaving, "
                f"not debt being paid. Restore it, or delete the entry deliberately and say why.")
        examined += n
        sources.append((text, t.name))
        pinned = set(EXAMINED_KEYS.get(t.name, ()))
        if t.name in EXAMINED_KEYS:
            for gone_key in sorted(pinned - keys):
                all_findings.append(
                    f"{t.name}: `{gone_key}` was examined and is NOT any more — its function was "
                    f"renamed, made private, or lost its last call site. Restore it, or update "
                    f"EXAMINED_KEYS deliberately and say why in the commit.")
    # ⚠ AFTER the loop, and ONLY over a population that was actually read. Deadness is judged
    # across the whole set (see the docstring), so a member that could not be parsed makes every
    # verdict about it meaningless — reporting exemptions dead on the strength of a file nobody
    # could read is a zero over nothing, which is the shape §21 exists to refuse.
    cannot = [x for x in all_findings if x.startswith("CANNOT RUN")]
    # ⚠ ONLY OVER THE FULL POPULATION — r8 H1. `--help` documents `paths` as an override, and
    # running the guard on ONE file made every exemption read as dead, so the documented
    # single-file invocation emitted two standing false positives. Deadness is a property of the
    # whole set; a subset cannot judge it.
    if not cannot and not a.paths:
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
    short = None if a.paths else population_drift(sorted(t.name for t in targets),
                                                   sorted(EXAMINED_KEYS))
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
    case("...and the examined keys are returned, not just the failures",
         sorted(n), ["progress_line.done", "progress_line.label", "progress_line.total"])

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
    case("omitting a defaulted argument counts as a distinct value",
         (fD, sorted(nD)), ([], ["g.a", "g.b"]))

    # An exemption is honoured, and ONLY for the named function+parameter.
    # ⚠ PASSED, NOT PATCHED — r7. These drove the rule by swapping the global `EXEMPT`, so the
    # `exempt=` parameter was omitted at all twelve call sites and the guard's own rule reported
    # it unvaried. Using the parameter is both what the rule asks for and less stateful.
    f5, _ = analyse(SRC, "t.py", exempt={"t.py:progress_line.done": "test"})
    case("an exemption removes exactly its own finding",
         [x.split("`")[1] for x in f5], ["progress_line(total=…)"])
    f6, _ = analyse(SRC, "t.py", exempt={"t.py:progress_line.nonexistent": "test"})
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
         (any(x.startswith("CANNOT RUN") for x in f7), n7), (True, set()))

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
    case("a function the suite never calls is not examined", (f9, n9), ([], set()))

    # Private helpers (leading underscore) are test plumbing, not the subject.
    PRIV = '''
def _mini(root, val):
    return None

def _self_test():
    _mini(1, 2)
    _mini(1, 2)
'''
    f10, n10 = analyse(PRIV, "t.py")
    case("a private helper is test plumbing, not a subject", (f10, n10), ([], set()))

    # ⛔ A DEAD EXEMPTION IS A FINDING — r7 H1, found by a reviewer and not by this guard.
    # `progress_line.label` was exempted here while the rule passed without it, so the entry did
    # nothing today and would have masked the label axis the moment it regressed.
    _sv = dict(EXEMPT)
    try:
        EXEMPT = {"t.py:g.b": "this parameter already varies, so the exemption guards nothing"}
        case("an exemption the rule does not need is reported as DEAD",
             len(dead_exemptions([(DEFAULTED, "t.py")])), 1)
        case("...and the message names the exemption so it can be deleted",
             "`t.py:g.b`" in dead_exemptions([(DEFAULTED, "t.py")])[0], True)
        # ...and one that IS load-bearing is silent: `a` is passed 1 and 2, `b` only 3.
        ONEVAL = DEFAULTED.replace("g(1)", "g(1, b=3)")
        EXEMPT = {"t.py:g.b": "needed — b is one value at every site"}
        case("...while a load-bearing exemption is not reported",
             dead_exemptions([(ONEVAL, "t.py")]), [])
        # ⛔ NEEDED SOMEWHERE IS NOT DEAD: the same exemption, with the file that needs it SECOND
        # in the population. The first version judged each file alone and reported this as dead.
        case("...and an exemption needed by only ONE file in the population survives",
             dead_exemptions([(DEFAULTED, "t.py"), (ONEVAL, "t.py")]), [])
        # ⛔ AND main() MUST SURFACE IT, not merely compute it. Without this case, deleting
        # `+ dead_exemptions(...)` from the findings leaves the check running and its result
        # unreachable — a guard that reaches a correct verdict and drops it on the floor.
        with tempfile.TemporaryDirectory() as _td:
            _f = pathlib.Path(_td) / "t.py"
            _f.write_text(DEFAULTED)
            EXEMPT = {"t.py:g.b": "dead — b already varies at its two call sites"}
            # ⚠ CALLED DIRECTLY, output captured inline. A `_quiet_main(...)` helper was tried
            # and this guard rejected it in one run: three varied call sites collapsed into one
            # passing `argv`, so `main.argv` read as unvaried. INDIRECTION HIDES VARIATION FROM
            # A RULE THAT READS CALL SITES — a true limit of the rule, recorded rather than
            # worked around, and the reason these three lines are shaped the way they are.
            # ⛔ A FULL-POPULATION RUN — r8 H1 made deadness a whole-set judgement, so a path
            # override deliberately does NOT judge it. Driving this with `[str(_f)]` would now
            # assert the opposite of what it is named for.
            # ⚠ THE REAL EXEMPTIONS STAY. Replacing them outright made their parameters fire as
            # ordinary findings, so `main` returned 1 for a reason that had nothing to do with
            # deadness and the case passed with the deadness aggregation deleted.
            EXEMPT = dict(_sv)
            EXEMPT["check-plan-code.py:nosuchfunction.nosuchparam"] = "cannot fire anywhere"
            # ⚠ ASSERT THE OUTPUT, NOT ONLY rc — r9 H1. `main` returns 1 whenever ANY file
            # reports ANYTHING, so `rc == 1` distinguished the deadness aggregation from its
            # absence only while every other script in the repo happened to be clean. r8 saw
            # this hazard, fixed its own fixture, and left the class.
            _dead_out = io.StringIO()
            with contextlib.redirect_stdout(_dead_out), contextlib.redirect_stderr(io.StringIO()):
                _rc_f = main([])
            case("main() surfaces a dead exemption as a failure",
                 (_rc_f, "nosuchfunction.nosuchparam` is DEAD" in _dead_out.getvalue()), (1, True))
            # ...and the documented single-file override does NOT, which is r8 H1 itself.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                _rc_one = main([str(_f)])
            case("...while a single-file override does not judge deadness at all", _rc_one, 0)
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
         (any(x.startswith("CANNOT RUN") for x in fS), nS), (True, set()))

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
    case("a keyword-only parameter omitted at one site counts as varied",
         (fK, sorted(nK)), ([], ["h.a", "h.b"]))

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
            # ⟳ r9 B2 — the pin is a SET now, so the falsifier is a key that stopped being
            # examined, not a number that fell. A count is preserved by substitution.
            _fl = pathlib.Path(_td) / "check-plan-code.py"   # name matches a pinned entry
            _fl.write_text(DEFAULTED.replace("g(1)", "g(1, b=9)"))
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_fl = main([str(_fl)])
            case("a file missing a pinned examined key fails", _rc_fl, 1)
            # ...and the same subject with no floor pinned for it passes, so the case above is
            # about the FLOOR and not about the file being small.
            _nf = pathlib.Path(_td) / "unpinned.py"
            _nf.write_text(DEFAULTED.replace("g(1)", "g(1, b=9)"))
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_nf = main([str(_nf)])
            case("...while the same file with nothing pinned for it passes", _rc_nf, 0)
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
    # ⛔ IDENTITY, NOT CARDINALITY — r8. The pair below is the measurement Codex made: a
    # DEPARTURE and an ARRIVAL cancel out under a count and cannot under a set.
    case("a population that swapped one file for another is CANNOT RUN",
         (population_drift(["a.py", "c.py"], ["a.py", "b.py"]) or "").startswith("CANNOT RUN"),
         True)
    case("...and the message names both directions",
         [w in (population_drift(["a.py", "c.py"], ["a.py", "b.py"]) or "")
          for w in ("no longer discovered: b.py", "newly discovered and unpinned: c.py")],
         [True, True])
    # ⚠ A THIRD PINNED SET, because the guard's own rule asked: the two cases above both passed
    # `["a.py", "b.py"]`, so `pinned` was indistinguishable from a constant and `set(pinned)`
    # could have been a literal.
    case("...while the same set in a different order is not drift",
         population_drift(["z.py", "y.py"], ["y.py", "z.py"]), None)

    # ⛔ LOST IS NOT PAID — r8 B1. The falsifier is a one-token privatisation: the parameter
    # stops being examined, the ratchet entry stops firing, and the old code called that success.
    _LOST = '''
def audit(cutoff):
    return cutoff

def _self_test():
    case("x", audit(1), 1)
    case("y", audit(1), 1)
'''
    # The falsifier drives `main` over a real file whose ratcheted parameter has been
    # privatised: `known - keys` must be a FINDING, and `known & keys - fired` the gold star.
    global KNOWN_UNVARIED, EXAMINED_KEYS
    _svK, _svF = dict(KNOWN_UNVARIED), dict(EXAMINED_KEYS)
    try:
        with tempfile.TemporaryDirectory() as _lt:
            _lf = pathlib.Path(_lt) / "lost.py"
            _lf.write_text(_LOST.replace("def audit(", "def _audit(").replace("audit(1)", "_audit(1)"))
            KNOWN_UNVARIED = {"lost.py": ("audit.cutoff",)}
            EXAMINED_KEYS = {"lost.py": ()}
            _eo = io.StringIO()
            with contextlib.redirect_stdout(_eo):
                _rc_lost = main([str(_lf)])
            # ⛔ AND NO GOLD STAR. Asserting only the finding let `known & keys` -> `known`
            # through: the entry is reported lost AND congratulated in the same run.
            case("a ratcheted entry whose parameter is no longer examined is a finding",
                 (_rc_lost, "NO LONGER EXAMINED" in _eo.getvalue(),
                  "now varies" in _eo.getvalue()), (1, True, False))
            # ...and one that IS still examined and now varies is a gold star, not a finding.
            _lf2 = pathlib.Path(_lt) / "paid.py"
            _lf2.write_text(_LOST.replace("audit(1), 1)\n    case(\"y\", audit(1)", "audit(1), 1)\n    case(\"y\", audit(2)"))
            KNOWN_UNVARIED = {"paid.py": ("audit.cutoff",)}
            EXAMINED_KEYS = {"paid.py": ("audit.cutoff",)}
            _po2 = io.StringIO()
            with contextlib.redirect_stdout(_po2):
                _rc_paid = main([str(_lf2)])
            case("...while one that started varying is debt paid, not a finding",
                 (_rc_paid, "now varies" in _po2.getvalue()), (0, True))
    finally:
        KNOWN_UNVARIED, EXAMINED_KEYS = _svK, _svF

    # ⟳ r8 L1 — a `/` shifts every positional mapping, so arguments land on the WRONG parameter.
    _PO = '''
def f(a, /, b):
    return a

def _self_test():
    case("x", f(1, 2), 1)
    case("y", f(1, 3), 1)
'''
    _f_p, _k_p = analyse(_PO, "t.py")
    case("a positional-only parameter is matched to its own name, not its neighbour's",
         (sorted(_k_p), [x.split("`")[1] for x in _f_p]), (["f.a", "f.b"], ["f(a=…)"]))

    # ⟳ r8 H2 — an exemption is an excuse about ONE file.
    _SH = '''
def run_suite_parts(d, name):
    return d

def _self_test():
    case("x", run_suite_parts(TMP, "a"), TMP)
    case("y", run_suite_parts(TMP, "b"), TMP)
'''
    case("an exemption is scoped to its file and does not silence another",
         [x.split("`")[1] for x in analyse(_SH, "other.py",
                                           exempt={"t.py:run_suite_parts.d": "elsewhere"})[0]],
         ["run_suite_parts(d=…)"])
    # ⛔ SCOPED DEADNESS: the exemption names a.py, where the parameter VARIES (so the exemption
    # is dead), while b.py has the same `function.parameter` unvaried. Judged against every file,
    # b.py's finding would keep a.py's exemption alive — an excuse kept by a different script's
    # debt. Only the scoped form can tell them apart.
    _A = DEFAULTED.replace("g(1)", "g(1, b=7)")          # b varies -> no finding here
    _B = DEFAULTED.replace("g(2, b=3)", "g(2, b=3)\n    case(\"z\", g(4, b=3), None)")
    _sv3 = dict(EXEMPT)
    try:
        EXEMPT = {"a.py:g.b": "claims b needs no variation in a.py"}
        # b.py must REPORT `g.b`, or both arms agree and the case sees nothing. DEFAULTED has
        # b varying; stripping the second call site makes it constant.
        _Bc = "def g(a, b=None):\n    return None\n\ndef _self_test():\n    case(\"x\", g(1, b=3), None)\n    case(\"y\", g(2, b=3), None)\n"
        case("an exemption is judged only against the file it names",
             len(dead_exemptions([(_A, "a.py"), (_Bc, "b.py")])), 1)
    finally:
        EXEMPT = _sv3

    # ⛔ `*args` AND `**kwargs` ARE PARAMETERS — r9, Codex B1. Omitting them made a whole
    # function INVISIBLE: `def target(*items)` examined zero parameters and the gate passed.
    _STAR = '''
def target(*items, **options):
    return items

def _self_test():
    case("a", target(1, mode="x"), None)
    case("b", target(1, mode="x"), None)
'''
    _fS2, _kS2 = analyse(_STAR, "t.py", exempt={})
    case("a *args parameter is examined, not invisible",
         (sorted(_kS2), sorted(x.split("`")[1] for x in _fS2)),
         (["target.items", "target.options"], ["target(items=…)", "target(options=…)"]))
    # ...and ONE call site cannot vary: `target(1, 2)` is one value, not two.
    _ONE_CALL = _STAR.replace('target(1, mode="x"), None)\n    case("b", target(1, mode="x")',
                              'target(1, 2, mode="x"), None)\n    case("b", target(1, 2, mode="x")')
    case("...and several values at ONE call site are one value, not several",
         sorted(x.split("`")[1] for x in analyse(_ONE_CALL, "t.py", exempt={})[0]),
         ["target(items=…)", "target(options=…)"])
    # ⛔ A KEY MUST NAME A FORMAL PARAMETER — r9 L1 / Codex's mis-key. `target(mode=1)` against
    # `def target(**options)` recorded `target.mode`, which is not a parameter of anything.
    _KWA = '''
def target(**options):
    return options

def _self_test():
    case("a", target(mode=1), None)
    case("b", target(mode=2), None)
'''
    case("an unrecognised keyword is attributed to the **kwargs parameter, not to itself",
         sorted(analyse(_KWA, "t.py", exempt={})[1]), ["target.options"])

    # ⛔ AN EXEMPT-AND-RATCHETED KEY IS NOT DEBT PAID — r9 M1, the third cause of "no finding".
    _svM = dict(EXEMPT); _svK2 = dict(KNOWN_UNVARIED); _svE2 = dict(EXAMINED_KEYS)
    try:
        with tempfile.TemporaryDirectory() as _mt:
            _mf = pathlib.Path(_mt) / "exempt-and-ratcheted.py"
            _mf.write_text(SRC)                       # progress_line.done/total are unvaried
            EXEMPT = {"exempt-and-ratcheted.py:progress_line.done": "excused here"}
            KNOWN_UNVARIED = {"exempt-and-ratcheted.py": ("progress_line.done",)}
            EXAMINED_KEYS = {"exempt-and-ratcheted.py": ("progress_line.done",
                                                         "progress_line.total",
                                                         "progress_line.label")}
            _mo = io.StringIO()
            with contextlib.redirect_stdout(_mo), contextlib.redirect_stderr(io.StringIO()):
                main([str(_mf)])
            case("an exempt key that is also ratcheted earns no false gold star",
                 "now varies" in _mo.getvalue(), False)
    finally:
        EXEMPT, KNOWN_UNVARIED, EXAMINED_KEYS = _svM, _svK2, _svE2

    case("every discovered file has a pinned key set, and vice versa",
         sorted(EXAMINED_KEYS) == sorted(f.name for f in _pop), True)
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
         all(len(k.split(":")) == 2 and len(k.split(":")[1].split(".")) == 2
             for k in EXEMPT), True)

    # The real subject, read from disk — the guard must be able to run on what it ships for.
    root = pathlib.Path(__file__).resolve().parent.parent
    live = root / "scripts" / "check-plan-code.py"
    # ⚠ UNCONDITIONAL. These were guarded by `if live.is_file()`, so the case COUNT varied with
    # the state of the world — and a suite whose count moves cannot be ratcheted. The existence
    # of the file is its own case; the reads below assume it and fail loudly if wrong.
    case("the declared population exists on disk", live.is_file(), True)
    f11, n11 = analyse(live.read_text() if live.is_file() else "", live.name)
    case("...and reading it examines a non-zero number of parameters", len(n11) > 0, True)
    case("...and it reports no CANNOT RUN on the live file",
         any(x.startswith("CANNOT RUN") for x in f11), False)

    case("main() refuses an unreadable population with rc 2",
         main(["/nonexistent/nope.py"]), 2)

    print(f"\n{ok}/{ok + fail} passed")
    if ok + fail != 48:
        print(f"  [DRIFT] the docstring declares 48 cases; the suite ran {ok + fail}")
        return 1
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())

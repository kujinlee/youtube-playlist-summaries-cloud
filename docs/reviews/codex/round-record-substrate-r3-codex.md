<!-- codex-review: model=gpt-5.5 -->

severity: Blocking  
component: conversion-falsifiers  
aim: instrument  
fix_induced: true  
evidence: The fourth falsifier fixes the comma-truncation case for changed values, but fails a new way: omissions have no guaranteed signal. The left column is whole raw header text, while the right column is “converted JSON, rendered field by field” (`docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:307-310`). Construct: a source header contains `deliverable_code_findings: true` or an inline comment-bearing `halves.codex` value; the converter drops that key/comment; the right side renders only fields it produced. There is no mismatch row for the missing thing unless the human already knows every expected source field and manually searches the whole raw header. That is no longer a field-level falsifier; it is unaided whole-header audit. The spec admits this at `:310`, but still calls the evidence “§2’s field-level table” at `:379`. This is a fourth falsifier design failing a fourth way, not the same comma-truncation class. Under the recorded pre-commitment, architecture review is convened.

severity: Blocking  
component: migration-cutover  
aim: deliverable  
fix_induced: true  
evidence: “Never in the decision path” is a promise, not an enforced property. The spec says the surviving converter is `scripts/migrate-round-headers.py` (`:340`) and “owes the full ratchet” because it is “exactly the population `check-ratchet-contract.py` exists to police” (`:285`). That is false today: `check-ratchet-contract.py` discovers guards by `GUARD_PATH_RE = re.compile(r"scripts/check-[\\w.-]+\\.py")` and filters with `fullmatch` (`scripts/check-ratchet-contract.py:113`, `:164`). `scripts/migrate-round-headers.py` is outside the population, so no `--self-test`, mutation manifest, caller, or `NO-CALLER:` obligation is enforced. Nothing in the spec prevents a later import into `check-review-decision.py`; the warrant depends on discipline.

severity: High  
component: header-schema  
aim: deliverable  
fix_induced: true  
evidence: The four layers are not exhaustive against what `parse_header` currently guarantees. Layer 2 says `round` is an int, but a naive `isinstance(v, int)` accepts `true` because `isinstance(True, int)` is true; this exact bool/int trap is already documented in `check-review-rounds.py:191-194`. Layer 2 says `findings` is a list, but not a list of objects; `json.loads` can hand `_validate` `1`, `[]`, or `null`, which today raise `TypeError`/`AttributeError` rather than the intended `ValueError`. The proposed layer-3 “type assertions” are also incomplete as stated: `_validate` currently accepts `component: []`, `{}`, and `null` because it only checks `str(f.get("component", "")).strip()`. So “type assertions of its own” must include `component` and finding-object shape, not only membership fields.

severity: High  
component: roundtrip-evidence  
aim: instrument  
fix_induced: true  
evidence: The new “derived values cannot live in the document” rule is not actually implemented and is still violated. The spec says every figure over `docs/reviews/coordinator/` is derived by `--calibrate` at read time (`:202-204`), but no `--calibrate` exists in `scripts/check-review-rounds.py` or `scripts/check-review-decision.py`. The stamped `bef49007` snapshot does reproduce for coordinator files only: 73 round-shaped, 34 yaml, 31 parseable, 39 headerless. At HEAD `54176525`, the same derivation is already 74/35/32/39. Yet fixed derived values remain: “31 of 31” at `:480`, “all 30” at `:249`, “4 of the 8 subjects” at `:330`, and “42 round-shaped documents” at `:356`.

severity: Medium  
component: migration-cutover  
aim: deliverable  
fix_induced: true  
evidence: The filename-vs-directory repair is underspecified and its rationale is stale against the actual `check-review-rounds.py` globbing. The checker reads flat files plus one-level subdirectories, then parses only the basename (`review_files` at `scripts/check-review-rounds.py:474-501`, `parse(p.name)` at `:510`). The spec says a directory-keyed refusal would catch “two misfiled `merge-ready-r*-codex.md` documents” that are “inert today” (`docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:346-349`). At HEAD there are three such files, and they are not inert to `check-review-rounds.py`: they parse as Codex halves and pair with `docs/reviews/claude/merge-ready-r1/r2/r3-claude.md`. The intended refusal must be stated as `who == "coordinator"` from the filename grammar, not parent directory, and the current evidence for why is wrong.

severity: Low  
component: defect-inventory  
aim: deliverable  
fix_induced: true  
evidence: The two corrected citations are good: `parse_header:209` is the `round:` check, and `parse_header:235-236` is the declared-vs-parsed parity check. But other citations are still broken or incomplete. The architecture review is cited as `architecture-review-2026-09-25-decision-family.md:180` and `:337` (`:138`, `:400`), but the file is actually `docs/reviews/architecture-review-2026-09-25-decision-family.md`. The seven-defect sentence cites only six comment locations in `check-review-decision.py` (`:38`), omitting the r7 `halves` case, which lives in the self-test around `scripts/check-review-decision.py:600-604`.

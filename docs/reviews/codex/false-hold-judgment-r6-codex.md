<!-- codex-review: model=gpt-6.1-sol -->

No findings in the scoped merge resolution.

Both features survive intact. The manifest is the exact 148-entry union, with no missing, extra, altered or duplicate entries. Pins are 148/91/23 with history comments preserved; `check-plan-code.py` equals master. All anchors bind once, with no pin drift. Docs retain both sides’ updates, with no unrelated resolution changes.

Self-tests passed: merge-ready 335/335; codex-review 232/232.

## Loosening answers
LOOSENING-CHECK 26a23836138b: not a loosening
LOOSENING-CHECK 795043e96b8f: not a loosening
LOOSENING-CHECK c7f21f95034a: not a loosening
LOOSENING-CHECK 6bd002a6d73a: not a loosening
LOOSENING-CHECK e8b3c3bfbf22: not a loosening
LOOSENING-CHECK f13e64d753fa: not a loosening
VERDICT: CONVERGED

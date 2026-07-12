# Task 10 — cloud VideoMenu "View PDF" item — dual review trail

**Files:** `components/VideoMenu.tsx` + `tests/components/video-menu-cloud-2c.test.tsx`. Base 16a94a0 → head (T10 + parity test).

## Both passes: Approved — 0 Blocking/High/Medium
Both verified the implementation is a clean, minimal mirror of the sibling "View summary":
- Inside the cloud-only block, immediately after View summary; reuses the same `ready` (video.summaryReady===true) + `pid` locals; `pdfHref(pid, video.id)` → exact `/api/pdf/{enc(id)}?playlist={pid}&type=summary`.
- Ready → `<a target="_blank" rel="noopener noreferrer" onClick={onClose} className={itemClass}>`; not-ready → disabled `<span aria-disabled title="Finalizing…" className={mutedItemClass}>`.
- `<a>` in `<li role="none">`, no `role="menuitem"` (convention). Local branch untouched by the diff.
- Tests non-vacuous (full href with both params; queryByRole for absence).

## Fix (Codex Low — test parity completeness)
The tests didn't fully lock parity: `rel` only asserted to *contain* `noopener` (would pass with bare `noopener`, dropping the `noreferrer` tabnabbing guard); no onClose-click; no class-parity. Strengthened the ready test → exact `rel="noopener noreferrer"`, `className === sibling's`, and `fireEvent.click → onClose called once`; disabled test → span `className === sibling's`. (Impl was already correct — these pin it against regression.)

**Final:** video-menu-cloud-2c 6/6; full suite 2076/2076; tsc clean. Both passes converged (0 Blocking/High); frontend surface now wired to the PDF route with parity pinned.

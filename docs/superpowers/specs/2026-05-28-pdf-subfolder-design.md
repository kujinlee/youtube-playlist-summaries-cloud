# PDF Subfolder Design

**Date:** 2026-05-28
**Status:** Approved

## Problem

MD and PDF files for each video share the same playlist folder. Obsidian indexes both file types, so every video title appears twice in the file explorer and full-text search — once for `slug.md` and once for `slug.pdf`.

## Solution

Move all PDF output files into a `pdfs/` subdirectory within each playlist folder. Obsidian only sees `.md` files at the root; PDFs are still served by the app's `/api/pdf` route, which reads the path from the index.

## Folder Layout

**Before:**
```
agentic-ai-claude-code/
  slug.md
  slug.pdf
  slug-deep-dive.md
  slug-deep-dive.pdf
  archived/
    slug.md
    slug.pdf
    …
```

**After:**
```
agentic-ai-claude-code/
  slug.md
  slug-deep-dive.md
  pdfs/
    slug.pdf
    slug-deep-dive.pdf
  archived/
    slug.md
    slug-deep-dive.md
    pdfs/
      slug.pdf
      slug-deep-dive.pdf
```

## Index Field Changes

`summaryPdf` and `deepDivePdf` in `playlist-index.json` change from a bare filename to a `pdfs/`-prefixed relative path:

| Field | Before | After |
|---|---|---|
| `summaryPdf` | `"slug.pdf"` | `"pdfs/slug.pdf"` |
| `deepDivePdf` | `"slug-deep-dive.pdf"` | `"pdfs/slug-deep-dive.pdf"` |

The `/api/pdf/[id]` route already uses `path.join(outputFolder, pdfFile)` where `pdfFile` comes from the index — so storing `pdfs/slug.pdf` there is sufficient. **No changes to the PDF API route.**

## Code Changes

### `lib/pipeline.ts`

Two locations:

**`readExistingVideoMeta`** (reads existing index on re-sync):
- Currently checks `path.join(mdDir, slug.pdf)` — change to check `path.join(outputFolder, 'pdfs', slug.pdf)`
- Store `summaryPdf` as `pdfs/${basename}.pdf`

**`processNewVideo`** (writes new video):
- `mkdir -p outputFolder/pdfs/` before writing
- Write PDF to `path.join(outputFolder, 'pdfs', baseName + '.pdf')`
- Set `summaryPdf: 'pdfs/' + baseName + '.pdf'`

### `lib/deep-dive.ts`

- `mkdir -p outputFolder/pdfs/` before writing
- Write PDF to `path.join(outputFolder, 'pdfs', base + '-deep-dive.pdf')`
- Set `deepDivePdf: 'pdfs/' + base + '-deep-dive.pdf'`

### `scripts/migrate-pdfs-to-subfolder.ts`

One-shot migration for existing data. For every `playlist-index.json` found under `baseOutputFolder`:

1. Collect videos where `summaryPdf` is set and does **not** start with `pdfs/`
2. `mkdir -p outputFolder/pdfs/`
3. For each such video:
   - Move `outputFolder/slug.pdf` → `outputFolder/pdfs/slug.pdf` (skip if already moved or file missing)
   - Update `summaryPdf` → `pdfs/slug.pdf` in the in-memory index
4. Repeat for `deepDivePdf`
5. Write updated index back to disk (atomic: write to `.tmp` then rename)

Script accepts `--base-folder <path>` argument; defaults to `settings.json` `baseOutputFolder` if not provided.

### `app/api/pdf/[id]/route.ts`

**No changes.** Already reads `pdfFile` from index and resolves with `path.join(outputFolder, pdfFile)`.

## Out of Scope

`lib/archive.ts` uses `videoId + suffix` patterns to locate files, which is a pre-existing naming mismatch (files use title slugs, not video IDs). The archive feature currently never moves PDF files. This is a separate bug and is not addressed here.

## Backward Compatibility

- Existing playlists that haven't run the migration script will continue to serve PDFs correctly — `summaryPdf` still holds the correct relative path for wherever the file lives.
- After migration, re-syncing any playlist writes new PDFs to `pdfs/` automatically.
- The migration script is idempotent: running it twice on the same folder is safe.

## Testing

### `tests/lib/pipeline.test.ts`

| Test | Change |
|---|---|
| New video: `summaryPdf` stored as `pdfs/slug.pdf` | Update assertion |
| New video: PDF file written to `outputFolder/pdfs/slug.pdf` | Update path assertion |
| Re-sync: `readExistingVideoMeta` detects PDF at `pdfs/` subfolder path | New test |
| Re-sync: `readExistingVideoMeta` returns `null` summaryPdf when PDF absent | Existing, no change |

### `tests/lib/deep-dive.test.ts`

| Test | Change |
|---|---|
| `deepDivePdf` stored as `pdfs/slug-deep-dive.pdf` | Update assertion |
| PDF written to `outputFolder/pdfs/slug-deep-dive.pdf` | Update path assertion |

### `scripts/migrate-pdfs-to-subfolder.test.ts` (new)

| Test | Covers |
|---|---|
| Moves `slug.pdf` → `pdfs/slug.pdf` and updates index | Happy path |
| Skips videos where `summaryPdf` already starts with `pdfs/` | Idempotency |
| Skips videos where PDF file doesn't exist on disk | Missing file |
| Handles `deepDivePdf` the same as `summaryPdf` | Deep-dive migration |

## Files Changed

| File | Change |
|---|---|
| `lib/pipeline.ts` | Write to `pdfs/` subfolder; store `pdfs/` prefix in `summaryPdf` |
| `lib/deep-dive.ts` | Write to `pdfs/` subfolder; store `pdfs/` prefix in `deepDivePdf` |
| `scripts/migrate-pdfs-to-subfolder.ts` | New migration script |
| `tests/lib/pipeline.test.ts` | Update PDF path assertions |
| `tests/lib/deep-dive.test.ts` | Update PDF path assertions |
| `tests/scripts/migrate-pdfs-to-subfolder.test.ts` | New test file |

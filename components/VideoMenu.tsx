'use client';

import type { Video } from '@/types';
import AskGeminiMenuItem from './AskGeminiMenuItem';
import { CURRENT_DOC_VERSION, isOlder } from '@/lib/doc-version';
import { useScope } from '@/lib/client/scope';
import { summaryHref } from '@/lib/client/api';

interface VideoMenuProps {
  video: Video;
  outputFolder: string;
  baseOutputFolder: string;
  onArchive: (videoId: string, action: 'archive' | 'unarchive') => void;
  onEditCorrections: () => void;
  onGenerateHtml: (videoId: string) => void;
  onResummarize?: (videoId: string) => void;
  onSavePdf?: (videoId: string, type: 'summary' | 'dig-deeper') => void;
  onShare?: () => void;
  onClose: () => void;
  busy?: boolean;
}

function obsidianHref(baseOutputFolder: string, outputFolder: string, file: string): string {
  // Vault = the playlist-level folder: the FIRST path segment of outputFolder below
  // baseOutputFolder (the data root). The note path is the remaining segments below it.
  // Each playlist folder under the data root is registered as its own Obsidian vault
  // (e.g. agentic-ai-claude-code, cs146s-the-modern-software-development); subfolders
  // like raw/ or wiki/ belong to the note path, not the vault name. When outputFolder
  // has no segment below the base (it IS the base, or sits outside it), fall back to the
  // output folder's own basename. Assumes POSIX paths and a non-empty outputFolder — the
  // row menu only renders once a folder is loaded, so both props are non-empty in practice.
  const base = (baseOutputFolder || outputFolder).replace(/\/+$/, '');
  const out = outputFolder.replace(/\/+$/, '');
  const rel = out !== base && out.startsWith(`${base}/`) ? out.slice(base.length + 1) : '';
  const segments = rel ? rel.split('/').filter(Boolean) : [];
  const vault = segments[0] ?? (out.split('/').filter(Boolean).at(-1) ?? out);
  const innerPath = segments.slice(1).join('/');
  const fullFile = innerPath ? `${innerPath}/${file}` : file;
  return `obsidian://open?vault=${encodeURIComponent(vault)}&file=${encodeURIComponent(fullFile)}`;
}

const itemClass = 'block w-full px-4 py-2 text-left text-sm text-zinc-200 hover:bg-zinc-700';
const disabledClass = 'block w-full px-4 py-2 text-left text-sm text-zinc-500 cursor-not-allowed';
const mutedItemClass = 'block w-full px-4 py-2 text-left text-sm text-[var(--text-muted)] cursor-not-allowed';

export default function VideoMenu({ video, outputFolder, baseOutputFolder, onArchive, onEditCorrections, onGenerateHtml, onResummarize = () => {}, onSavePdf = () => {}, onShare, onClose, busy = false }: VideoMenuProps) {
  const scope = useScope();
  // Stage 2a T15b: cloud mode allowlist. Doc generation, PDF export, Obsidian, Ask-Gemini and
  // corrections all depend on the local filesystem/output-folder pipeline (out of scope for
  // 2a/2b) — cloud only ever shows "Watch on YouTube" + Archive/Unarchive. Local mode is
  // unchanged (full menu).
  const cloudMode = scope.mode === 'cloud';
  const summaryFile = video.summaryMd?.replace(/\.md$/, '') ?? video.id;
  const hasSummary = !!video.summaryMd;
  const htmlViewHref = `/api/html/${encodeURIComponent(video.id)}?outputFolder=${encodeURIComponent(outputFolder)}&type=summary`;

  return (
    <ul
      role="menu"
      className="absolute left-0 top-full z-20 mt-1 w-52 rounded-md bg-zinc-800 border border-zinc-700 shadow-xl py-1"
    >
      <li role="none">
        <a href={video.youtubeUrl} onClick={onClose} target="_blank" rel="noopener noreferrer" className={itemClass}>
          Watch on YouTube
        </a>
      </li>
      {cloudMode && (() => {
        // Stage 2c T6: View/Download/Share, gated on summaryReady (the DB-computed readiness
        // flag — true once the summary artifact has finished writing). While not ready, render
        // each as a disabled <span> (no href, no click) rather than an inert anchor/button, so
        // getByRole('link'/'button') correctly finds nothing until the doc is actually servable.
        const ready = video.summaryReady === true;
        const pid = scope.mode === 'cloud' ? scope.playlistId : '';
        return (
          <>
            <li role="none">
              {ready ? (
                <a href={summaryHref(pid, video.id)} onClick={onClose} target="_blank" rel="noopener noreferrer" className={itemClass}>
                  View summary ↗
                </a>
              ) : (
                <span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>View summary ↗</span>
              )}
            </li>
            <li role="none">
              {ready ? (
                <a href={summaryHref(pid, video.id, { format: 'md', download: true })} onClick={onClose} download className={itemClass}>
                  Download Markdown
                </a>
              ) : (
                <span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>Download Markdown</span>
              )}
            </li>
            <li role="none">
              {ready ? (
                <a href={summaryHref(pid, video.id, { format: 'html', download: true })} onClick={onClose} download className={itemClass}>
                  Download HTML
                </a>
              ) : (
                <span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>Download HTML</span>
              )}
            </li>
            <li role="none">
              {ready ? (
                <button type="button" onClick={() => { onShare?.(); onClose(); }} className={itemClass}>
                  Share…
                </button>
              ) : (
                <span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>Share…</span>
              )}
            </li>
          </>
        );
      })()}
      {!cloudMode && (
        <li role="none">
          <AskGeminiMenuItem video={video} onClose={onClose} />
        </li>
      )}
      {!cloudMode && (
        <li role="none">
          <a href={obsidianHref(baseOutputFolder, outputFolder, summaryFile)} onClick={onClose} target="_blank" rel="noopener noreferrer" className={itemClass}>
            Open in Obsidian
          </a>
        </li>
      )}
      {!cloudMode && (
        <li role="none">
          {(() => {
            const current = !!video.summaryHtml && !isOlder(video.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION);
            if (!hasSummary) return <span aria-disabled="true" className={disabledClass}>HTML doc</span>;
            if (busy) return <span aria-disabled="true" className={disabledClass}>HTML doc <span aria-hidden="true">⏳</span></span>;
            return current
              ? <a href={htmlViewHref} onClick={onClose} target="_blank" rel="noopener noreferrer" className={itemClass}>HTML doc</a>
              : <button type="button" onClick={() => { onGenerateHtml(video.id); onClose(); }} className={itemClass}>HTML doc</button>;
          })()}
        </li>
      )}
      {!cloudMode && hasSummary && (
        <li role="none">
          {/* Always force-regenerates (never opens cached) — for a doc the audit flags or that looks off. */}
          {busy
            ? <span aria-disabled="true" className={disabledClass}>Re-summarize <span aria-hidden="true">⏳</span></span>
            : <button type="button" onClick={() => { onResummarize(video.id); onClose(); }} className={itemClass}>Re-summarize</button>}
        </li>
      )}
      {!cloudMode && video.summaryHtml && (
        <li role="none">
          {/* Save a self-contained PDF of the summary HTML doc into the pdfs/ folder. Requires the
              HTML doc to exist (summaryHtml) — same precondition as the "HTML doc" open-link. */}
          {busy
            ? <span aria-disabled="true" className={disabledClass}>Save summary PDF <span aria-hidden="true">⏳</span></span>
            : <button type="button" onClick={() => { onSavePdf(video.id, 'summary'); onClose(); }} className={itemClass}>Save summary PDF</button>}
        </li>
      )}
      {!cloudMode && video.digDeeperMd && (
        <li role="none">
          {busy
            ? <span aria-disabled="true" className={disabledClass}>Save dig-deeper PDF <span aria-hidden="true">⏳</span></span>
            : <button type="button" onClick={() => { onSavePdf(video.id, 'dig-deeper'); onClose(); }} className={itemClass}>Save dig-deeper PDF</button>}
        </li>
      )}
      {!cloudMode && video.summaryMd && (
        <li role="none">
          <button
            type="button"
            onClick={() => { onEditCorrections(); onClose(); }}
            className={itemClass}
          >
            Edit corrections
          </button>
        </li>
      )}
      <li role="none">
        <button
          type="button"
          onClick={() => { onArchive(video.id, video.archived ? 'unarchive' : 'archive'); onClose(); }}
          className={itemClass}
        >
          {video.archived ? 'Unarchive' : 'Archive'}
        </button>
      </li>
    </ul>
  );
}

'use client';

import { formatIngestSummary } from '@/lib/client/format-ingest-summary';
import type { IngestResult } from '@/lib/client/api';

export function IngestSummaryNotice({ result, onDismiss }: { result: IngestResult; onDismiss: () => void }) {
  const { line, challengeLine } = formatIngestSummary(result.counts, result.dailyCapReached, result.challengeRequired);
  return (
    <div role="status" className="flex items-start justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-[var(--text-primary)]">
      <div>
        <span aria-hidden="true">✓ </span>{line}
        {challengeLine && <span className="ml-1 text-[var(--warning)]">{challengeLine}</span>}
      </div>
      <button type="button" aria-label="Dismiss summary" onClick={onDismiss} className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)]">✕</button>
    </div>
  );
}

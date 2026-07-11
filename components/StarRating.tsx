'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useScope } from '@/lib/client/scope';
import { saveAnnotation, UnauthorizedError } from '@/lib/client/api';

interface StarRatingProps {
  videoId: string;
  value: number | undefined;
  onChange: (score: number | undefined) => void;
}

export default function StarRating({ videoId, value, onChange }: StarRatingProps) {
  const scope = useScope();
  const router = useRouter();
  const [hover, setHover]   = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  async function commit(newScore: number | undefined) {
    if (saving) return;
    const prev = value;
    onChange(newScore);
    setSaving(true);
    try {
      await saveAnnotation(scope, videoId, { personalScore: newScore ?? null });
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        router.replace('/login');
        return;
      }
      onChange(prev);
    } finally {
      setSaving(false);
    }
  }

  const displayFill = hover ?? value ?? 0;

  return (
    <div
      role="radiogroup"
      aria-label="My score"
      className={`flex gap-0.5 ${saving ? 'pointer-events-none' : ''}`}
    >
      {([1, 2, 3, 4, 5] as const).map((star) => {
        const checked = value === star;
        const filled  = star <= displayFill;
        return (
          <label key={star}>
            <input
              type="radio"
              name={`star-${videoId}`}
              value={String(star)}
              checked={checked}
              disabled={saving}
              aria-label={`${star} star${star !== 1 ? 's' : ''}`}
              className="sr-only"
              // onChange handles: new selection via keyboard (arrow keys) or mouse click on unselected
              onChange={() => !saving && commit(star)}
              // onClick handles: clicking the already-selected star to clear it
              onClick={() => { if (checked && !saving) commit(undefined); }}
            />
            <span
              aria-hidden="true"
              className={`text-base select-none cursor-pointer ${filled ? 'text-yellow-400' : 'text-zinc-600'}`}
              onMouseEnter={() => !saving && setHover(star)}
              onMouseLeave={() => !saving && setHover(null)}
            >
              {filled ? '★' : '☆'}
            </span>
          </label>
        );
      })}
    </div>
  );
}

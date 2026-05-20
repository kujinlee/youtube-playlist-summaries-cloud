'use client';

import type { Video } from '@/types';
import VideoRow from './VideoRow';

interface VideoListProps {
  videos: Video[];
  outputFolder: string;
  showArchive: boolean;
  onDeepDive: (videoId: string) => void;
  onArchive: (videoId: string, action: 'archive' | 'unarchive') => void;
}

export default function VideoList({
  videos,
  outputFolder,
  showArchive,
  onDeepDive,
  onArchive,
}: VideoListProps) {
  const visible = showArchive ? videos : videos.filter((v) => !v.archived);

  if (visible.length === 0) return null;

  return (
    <ul aria-label="Video list">
      {visible.map((video) => (
        <li key={video.id} className={video.archived ? 'opacity-50' : undefined}>
          {video.archived && <span className="sr-only">Archived</span>}
          <VideoRow
            video={video}
            outputFolder={outputFolder}
            onDeepDive={onDeepDive}
            onArchive={onArchive}
          />
        </li>
      ))}
    </ul>
  );
}

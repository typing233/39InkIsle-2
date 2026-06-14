import { readerApi } from '@/api/reader';
import { ReadingProgress } from '@/types/reader';

interface QueuedProgress {
  bookId: string;
  cfi: string;
  progress_percent: number;
  device_id: string;
  timestamp: number;
}

export async function syncQueuedProgress(): Promise<void> {
  const raw = localStorage.getItem('progress_queue');
  if (!raw) return;

  const queue: QueuedProgress[] = JSON.parse(raw);
  if (queue.length === 0) return;

  const remaining: QueuedProgress[] = [];

  for (const item of queue) {
    try {
      await readerApi.updateProgress(item.bookId, {
        cfi: item.cfi,
        progress_percent: item.progress_percent,
        device_id: item.device_id,
      });
    } catch {
      remaining.push(item);
    }
  }

  if (remaining.length > 0) {
    localStorage.setItem('progress_queue', JSON.stringify(remaining));
  } else {
    localStorage.removeItem('progress_queue');
  }
}

export function getDeviceId(): string {
  let id = localStorage.getItem('device_id');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('device_id', id);
  }
  return id;
}

/**
 * Resolve cross-device reading progress conflicts.
 * Strategy: last-write-wins by timestamp, with vector clock total as tiebreaker.
 * Returns the CFI string of the winning progress entry.
 */
export function resolveProgressConflict(
  progressList: ReadingProgress[]
): string | null {
  if (progressList.length === 0) return null;

  const withCfi = progressList.filter((p) => p.cfi != null);
  if (withCfi.length === 0) return null;

  const sorted = [...withCfi].sort((a, b) => {
    // Primary: most recently updated wins
    const timeDiff = new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    if (timeDiff !== 0) return timeDiff;

    // Tiebreaker: higher total vector clock count wins (more writes = more recent activity)
    const totalA = Object.values(a.vector_clock).reduce((s, v) => s + v, 0);
    const totalB = Object.values(b.vector_clock).reduce((s, v) => s + v, 0);
    if (totalB !== totalA) return totalB - totalA;

    // Final tiebreaker: higher progress percent wins
    const percentA = a.progress_percent ?? 0;
    const percentB = b.progress_percent ?? 0;
    return percentB - percentA;
  });

  return sorted[0].cfi;
}

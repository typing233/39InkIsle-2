import { readerApi } from '@/api/reader';

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

export function resolveProgressConflict(
  progressList: Array<{ updated_at: string; vector_clock: Record<string, number>; cfi: string | null }>
): string | null {
  if (progressList.length === 0) return null;

  const sorted = [...progressList].sort((a, b) => {
    const timeDiff = new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    if (timeDiff !== 0) return timeDiff;

    const totalA = Object.values(a.vector_clock).reduce((s, v) => s + v, 0);
    const totalB = Object.values(b.vector_clock).reduce((s, v) => s + v, 0);
    return totalB - totalA;
  });

  return sorted[0].cfi;
}

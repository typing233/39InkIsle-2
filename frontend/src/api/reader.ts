import client from './client';
import { ReadingProgress, TOCItem } from '@/types/reader';

export const readerApi = {
  getProgress: (bookId: string) =>
    client.get<ReadingProgress[]>(`/reader/${bookId}/progress`),

  updateProgress: (bookId: string, data: {
    cfi?: string;
    chapter_index?: number;
    progress_percent?: number;
    device_id: string;
  }) => client.put<ReadingProgress>(`/reader/${bookId}/progress`, data),

  getTOC: (bookId: string) =>
    client.get<TOCItem[]>(`/reader/${bookId}/toc`),

  getChapterContent: (bookId: string, chapter: number) =>
    client.get<string>(`/reader/${bookId}/content/${chapter}`, { responseType: 'text' as never }),
};

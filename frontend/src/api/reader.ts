import client from './client';
import { ReadingProgress, TOCItem, PdfInfo, CbzInfo } from '@/types/reader';

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

  // PDF
  getPdfInfo: (bookId: string) =>
    client.get<PdfInfo>(`/reader/${bookId}/pdf/info`),

  getPdfPageUrl: (bookId: string, page: number, dpi = 150) =>
    `/api/v1/reader/${bookId}/pdf/page/${page}?dpi=${dpi}`,

  getPdfStreamUrl: (bookId: string) =>
    `/api/v1/reader/${bookId}/pdf/stream`,

  // CBZ
  getCbzInfo: (bookId: string) =>
    client.get<CbzInfo>(`/reader/${bookId}/cbz/info`),

  getCbzPageUrl: (bookId: string, page: number) =>
    `/api/v1/reader/${bookId}/cbz/page/${page}`,
};

export interface ReadingProgress {
  id: string;
  book_id: string;
  cfi: string | null;
  chapter_index: number | null;
  progress_percent: number | null;
  device_id: string;
  vector_clock: Record<string, number>;
  updated_at: string;
}

export interface TOCItem {
  title: string;
  href: string;
  level: number;
}

export interface ReaderSettings {
  fontSize: number;
  fontFamily: string;
  lineHeight: number;
  theme: 'day' | 'night' | 'sepia';
  padding: number;
}

export interface PdfInfo {
  page_count: number;
  metadata: Record<string, string>;
}

export interface CbzInfo {
  page_count: number;
  pages: { name: string; index: number }[];
}

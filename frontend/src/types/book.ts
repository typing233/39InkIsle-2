export interface Book {
  id: string;
  title: string;
  author: string | null;
  description: string | null;
  cover_path: string | null;
  file_format: 'epub' | 'pdf' | 'cbz';
  file_size: number | null;
  language: string | null;
  publisher: string | null;
  publish_date: string | null;
  isbn: string | null;
  page_count: number | null;
  is_available: boolean;
  created_at: string;
  tags: Tag[];
}

export interface Tag {
  id: string;
  name: string;
}

export interface BookSearchParams {
  q?: string;
  author?: string;
  tag?: string;
  format?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

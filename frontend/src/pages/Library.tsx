import { useState, useEffect, useCallback } from 'react';
import { booksApi } from '@/api/books';
import { Book, Tag, BookSearchParams } from '@/types/book';
import { BookCard } from '@/components/books/BookCard';
import { SearchBar } from '@/components/books/SearchBar';
import { AdvancedSearch } from '@/components/books/AdvancedSearch';
import { Pagination } from '@/components/common/Pagination';

export default function Library() {
  const [books, setBooks] = useState<Book[]>([]);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [formatFilter, setFormatFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [advancedFilters, setAdvancedFilters] = useState<Partial<BookSearchParams>>({});
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);

  const pageSize = 24;

  useEffect(() => {
    booksApi.getTags().then(({ data }) => setAllTags(data)).catch(() => {});
  }, []);

  const fetchBooks = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await booksApi.search({
        q: query || undefined,
        format: formatFilter || undefined,
        tag: tagFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: pageSize,
        ...advancedFilters,
      });
      setBooks(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch {
      setBooks([]);
      setTotal(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [query, page, sortBy, sortOrder, formatFilter, tagFilter, advancedFilters]);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  useEffect(() => {
    setPage(1);
  }, [query, sortBy, sortOrder, formatFilter, tagFilter, advancedFilters]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <div className="flex-1 w-full">
          <SearchBar value={query} onChange={setQuery} />
        </div>
        <div className="flex gap-2 flex-wrap">
          <select
            value={formatFilter}
            onChange={(e) => setFormatFilter(e.target.value)}
            className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm"
          >
            <option value="">All Formats</option>
            <option value="epub">EPUB</option>
            <option value="pdf">PDF</option>
            <option value="cbz">CBZ</option>
          </select>
          <select
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [s, o] = e.target.value.split(':');
              setSortBy(s);
              setSortOrder(o as 'asc' | 'desc');
            }}
            className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm"
          >
            <option value="created_at:desc">Newest</option>
            <option value="created_at:asc">Oldest</option>
            <option value="title:asc">Title A-Z</option>
            <option value="title:desc">Title Z-A</option>
            <option value="author:asc">Author A-Z</option>
            <option value="avg_rating:desc">Top Rated</option>
          </select>
        </div>
      </div>

      <AdvancedSearch onSearch={setAdvancedFilters} tags={allTags} />

      {!loading && total > 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">{total} books found</p>
      )}

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="aspect-[2/3] bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : books.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-lg">No books found</p>
          <p className="text-sm mt-2">Your library is empty or no results match your search.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {books.map((book) => (
            <BookCard key={book.id} book={book} />
          ))}
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />
    </div>
  );
}

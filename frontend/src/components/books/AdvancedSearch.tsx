import { useState } from 'react';
import { BookSearchParams } from '@/types/book';
import { SlidersHorizontal, X } from 'lucide-react';

interface Props {
  onSearch: (params: Partial<BookSearchParams>) => void;
  tags: { id: string; name: string }[];
}

export function AdvancedSearch({ onSearch, tags }: Props) {
  const [open, setOpen] = useState(false);
  const [filters, setFilters] = useState<Partial<BookSearchParams>>({});

  const update = (key: keyof BookSearchParams, value: unknown) => {
    setFilters(prev => ({ ...prev, [key]: value || undefined }));
  };

  const apply = () => {
    onSearch(filters);
  };

  const reset = () => {
    setFilters({});
    onSearch({});
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700">
        <SlidersHorizontal size={14} /> Advanced
      </button>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Advanced Filters</h3>
        <button onClick={() => setOpen(false)} className="p-1 hover:bg-gray-100 rounded">
          <X size={16} />
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Language</label>
          <input
            value={filters.language || ''}
            onChange={(e) => update('language', e.target.value)}
            className="w-full px-2 py-1.5 border rounded text-sm"
            placeholder="en, zh..."
          />
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Series</label>
          <input
            value={filters.series || ''}
            onChange={(e) => update('series', e.target.value)}
            className="w-full px-2 py-1.5 border rounded text-sm"
            placeholder="Series name"
          />
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Min Rating</label>
          <select
            value={filters.rating_min ?? ''}
            onChange={(e) => update('rating_min', e.target.value ? Number(e.target.value) : undefined)}
            className="w-full px-2 py-1.5 border rounded text-sm"
          >
            <option value="">Any</option>
            <option value="1">1+</option>
            <option value="2">2+</option>
            <option value="3">3+</option>
            <option value="4">4+</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">Tag</label>
          <select
            value={filters.tag || ''}
            onChange={(e) => update('tag', e.target.value)}
            className="w-full px-2 py-1.5 border rounded text-sm"
          >
            <option value="">All tags</option>
            {tags.map(t => <option key={t.id} value={t.name}>{t.name}</option>)}
          </select>
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">From Date</label>
          <input
            type="date"
            value={filters.publish_date_from || ''}
            onChange={(e) => update('publish_date_from', e.target.value)}
            className="w-full px-2 py-1.5 border rounded text-sm"
          />
        </div>

        <div>
          <label className="text-xs text-gray-500 block mb-1">To Date</label>
          <input
            type="date"
            value={filters.publish_date_to || ''}
            onChange={(e) => update('publish_date_to', e.target.value)}
            className="w-full px-2 py-1.5 border rounded text-sm"
          />
        </div>

        <div className="flex items-end gap-1">
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="checkbox"
              checked={filters.q_fuzzy || false}
              onChange={(e) => update('q_fuzzy', e.target.checked)}
              className="rounded"
            />
            Fuzzy search
          </label>
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={apply} className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
          Apply Filters
        </button>
        <button onClick={reset} className="px-3 py-1.5 text-gray-600 text-sm border rounded hover:bg-gray-50">
          Reset
        </button>
      </div>
    </div>
  );
}

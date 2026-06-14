import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { collectionsApi, CollectionData, CollectionBookItem } from '@/api/collections';
import { booksApi } from '@/api/books';
import { Book } from '@/types/book';
import { Heart, BookMarked, FolderPlus, Trash2, RefreshCw, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';

interface CollectionWithBooks extends CollectionData {
  books: CollectionBookItem[];
  localBookIds: string[];
}

export default function Collections() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<CollectionWithBooks[]>([]);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [bookCache, setBookCache] = useState<Record<string, Book>>({});

  useEffect(() => { loadCollections(); }, []);

  const loadCollections = async () => {
    try {
      const { data } = await collectionsApi.list();
      const withBooks: CollectionWithBooks[] = await Promise.all(
        data.map(async (col) => {
          const booksRes = await collectionsApi.getBooks(col.id, 1, 100);
          const items = booksRes.data.items;
          // Sort by position for stable ordering
          items.sort((a, b) => a.position - b.position);
          return {
            ...col,
            books: items,
            localBookIds: items.map(i => i.book_id),
          };
        })
      );
      setCollections(withBooks);
    } catch {
      toast.error('Failed to load collections');
    }
    setLoading(false);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await collectionsApi.create(newName.trim());
      setNewName('');
      await loadCollections();
      toast.success('Collection created');
    } catch {
      toast.error('Failed to create collection');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await collectionsApi.delete(id);
      await loadCollections();
      toast.success('Collection deleted');
    } catch {
      toast.error('Cannot delete system collections');
    }
  };

  const handleSync = useCallback(async (col: CollectionWithBooks) => {
    setSyncing(col.id);
    try {
      const { data } = await collectionsApi.sync(
        col.id,
        col.localBookIds,
        col.vector_clock,
      );
      if (data.conflicts_resolved > 0) {
        toast.success(`Synced — ${data.conflicts_resolved} conflict(s) resolved`);
      } else {
        toast.success('Collection synced');
      }
      await loadCollections();
    } catch {
      toast.error('Sync failed');
    }
    setSyncing(null);
  }, []);

  const handleRemoveBook = async (collectionId: string, bookId: string) => {
    try {
      await collectionsApi.removeBook(collectionId, bookId);
      await loadCollections();
      toast.success('Book removed');
    } catch {
      toast.error('Failed to remove book');
    }
  };

  const loadBookDetails = async (bookId: string) => {
    if (bookCache[bookId]) return;
    try {
      const { data } = await booksApi.getById(bookId);
      setBookCache(prev => ({ ...prev, [bookId]: data }));
    } catch { /* ignore */ }
  };

  const handleExpand = (colId: string) => {
    const newId = expandedId === colId ? null : colId;
    setExpandedId(newId);
    if (newId) {
      const col = collections.find(c => c.id === newId);
      col?.books.forEach(b => loadBookDetails(b.book_id));
    }
  };

  const getIcon = (type: string) => {
    if (type === 'favorites') return <Heart size={18} className="text-red-500" />;
    if (type === 'to_read') return <BookMarked size={18} className="text-blue-500" />;
    return <FolderPlus size={18} className="text-gray-500" />;
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">My Collections</h1>

      {/* Create new */}
      <div className="flex gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New collection name..."
          className="flex-1 px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
        />
        <button onClick={handleCreate} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          Create
        </button>
      </div>

      {/* List */}
      <div className="space-y-2">
        {collections.map((col) => (
          <div key={col.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border overflow-hidden">
            <div className="flex items-center justify-between p-4">
              <div
                className="flex items-center gap-3 flex-1 cursor-pointer"
                onClick={() => handleExpand(col.id)}
              >
                {getIcon(col.collection_type)}
                <div>
                  <h3 className="font-medium text-sm">{col.name}</h3>
                  <p className="text-xs text-gray-500">{col.books.length} books</p>
                </div>
                <ChevronRight
                  size={16}
                  className={`text-gray-400 transition-transform ${expandedId === col.id ? 'rotate-90' : ''}`}
                />
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleSync(col)}
                  disabled={syncing === col.id}
                  className="p-2 text-blue-500 hover:bg-blue-50 rounded"
                  title="Sync across devices"
                >
                  <RefreshCw size={16} className={syncing === col.id ? 'animate-spin' : ''} />
                </button>
                {!col.is_system && (
                  <button onClick={() => handleDelete(col.id)} className="p-2 text-red-500 hover:bg-red-50 rounded">
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>

            {/* Expanded book list */}
            {expandedId === col.id && (
              <div className="border-t px-4 py-3 space-y-2 bg-gray-50 dark:bg-gray-900">
                {col.books.length === 0 ? (
                  <p className="text-xs text-gray-500">No books in this collection.</p>
                ) : (
                  col.books.map((item, idx) => {
                    const book = bookCache[item.book_id];
                    return (
                      <div
                        key={item.id}
                        className="flex items-center justify-between py-2 px-2 hover:bg-white dark:hover:bg-gray-800 rounded"
                      >
                        <div
                          className="flex items-center gap-2 flex-1 cursor-pointer min-w-0"
                          onClick={() => navigate(`/books/${item.book_id}`)}
                        >
                          <span className="text-xs text-gray-400 w-6 shrink-0">{idx + 1}</span>
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate">
                              {book?.title || item.book_id.slice(0, 8) + '...'}
                            </p>
                            {book?.author && <p className="text-xs text-gray-500 truncate">{book.author}</p>}
                          </div>
                        </div>
                        <button
                          onClick={() => handleRemoveBook(col.id, item.book_id)}
                          className="p-1 text-red-400 hover:text-red-600 shrink-0"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    );
                  })
                )}
                <p className="text-xs text-gray-400 pt-1">
                  Clock: {Object.entries(col.vector_clock).map(([k, v]) => `${k.slice(0, 6)}:${v}`).join(', ') || 'empty'}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

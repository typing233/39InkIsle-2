import { useEffect, useState } from 'react';
import { collectionsApi, CollectionData } from '@/api/collections';
import { Heart, BookMarked, FolderPlus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Collections() {
  const [collections, setCollections] = useState<CollectionData[]>([]);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadCollections(); }, []);

  const loadCollections = async () => {
    const { data } = await collectionsApi.list();
    setCollections(data);
    setLoading(false);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await collectionsApi.create(newName.trim());
      setNewName('');
      loadCollections();
      toast.success('Collection created');
    } catch {
      toast.error('Failed to create collection');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await collectionsApi.delete(id);
      loadCollections();
      toast.success('Collection deleted');
    } catch (e: unknown) {
      toast.error('Cannot delete system collections');
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
          <div key={col.id} className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm border">
            <div className="flex items-center gap-3">
              {getIcon(col.collection_type)}
              <div>
                <h3 className="font-medium text-sm">{col.name}</h3>
                <p className="text-xs text-gray-500">{col.item_count} books</p>
              </div>
            </div>
            {!col.is_system && (
              <button onClick={() => handleDelete(col.id)} className="p-2 text-red-500 hover:bg-red-50 rounded">
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

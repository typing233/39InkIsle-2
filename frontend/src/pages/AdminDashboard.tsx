import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store';
import toast from 'react-hot-toast';
import client from '@/api/client';
import { FolderPlus, RefreshCw, Play } from 'lucide-react';

interface ImportFolder {
  id: string;
  path: string;
  is_active: boolean;
  scan_interval_seconds: number;
  last_scanned_at: string | null;
}

interface ImportTask {
  id: string;
  file_name: string;
  status: string;
  error_message: string | null;
  retry_count: number;
  created_at: string;
}

interface ImportStats {
  total_tasks: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  skipped: number;
}

export default function AdminDashboard() {
  const { user } = useAuthStore();
  const [folders, setFolders] = useState<ImportFolder[]>([]);
  const [tasks, setTasks] = useState<ImportTask[]>([]);
  const [stats, setStats] = useState<ImportStats | null>(null);
  const [newPath, setNewPath] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const [fRes, tRes, sRes] = await Promise.all([
      client.get('/import/folders'),
      client.get('/import/tasks?page_size=50'),
      client.get('/import/stats'),
    ]);
    setFolders(fRes.data);
    setTasks(tRes.data);
    setStats(sRes.data);
  };

  const addFolder = async () => {
    if (!newPath.trim()) return;
    try {
      await client.post('/import/folders', { path: newPath.trim() });
      setNewPath('');
      toast.success('Folder added');
      loadData();
    } catch {
      toast.error('Failed to add folder');
    }
  };

  const triggerScan = async (folderId: string) => {
    await client.post(`/import/folders/${folderId}/scan`);
    toast.success('Scan triggered');
  };

  const retryTask = async (taskId: string) => {
    await client.post(`/import/tasks/${taskId}/retry`);
    toast.success('Task re-queued');
    loadData();
  };

  if (user?.role !== 'admin') return <p>Access denied</p>;

  const statusColor: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    skipped: 'bg-gray-100 text-gray-800',
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
          {Object.entries(stats).map(([key, val]) => (
            <div key={key} className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{val}</p>
              <p className="text-xs text-gray-500 capitalize">{key.replace('_', ' ')}</p>
            </div>
          ))}
        </div>
      )}

      <section>
        <h2 className="text-lg font-semibold mb-3">Watch Folders</h2>
        <div className="flex gap-2 mb-4">
          <input
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="/data/watch/mybooks"
            className="flex-1 px-3 py-2 rounded border"
          />
          <button onClick={addFolder} className="px-4 py-2 bg-blue-600 text-white rounded flex items-center gap-2">
            <FolderPlus size={16} /> Add
          </button>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg divide-y">
          {folders.map((f) => (
            <div key={f.id} className="p-4 flex items-center justify-between">
              <div>
                <p className="font-mono text-sm">{f.path}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Last scanned: {f.last_scanned_at ? new Date(f.last_scanned_at).toLocaleString() : 'Never'}
                </p>
              </div>
              <button onClick={() => triggerScan(f.id)} className="p-2 hover:bg-gray-100 rounded">
                <Play size={16} />
              </button>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Recent Import Tasks</h2>
        <div className="bg-white dark:bg-gray-800 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr className="text-left">
                <th className="p-3">File</th>
                <th className="p-3">Status</th>
                <th className="p-3">Error</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td className="p-3 truncate max-w-[200px]">{t.file_name}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${statusColor[t.status] || ''}`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="p-3 text-xs text-red-500 truncate max-w-[200px]">{t.error_message}</td>
                  <td className="p-3">
                    {t.status === 'failed' && (
                      <button onClick={() => retryTask(t.id)} className="p-1 hover:bg-gray-100 rounded">
                        <RefreshCw size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

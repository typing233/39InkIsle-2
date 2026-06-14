import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store';
import { authApi } from '@/api/auth';
import { Session } from '@/types/user';
import toast from 'react-hot-toast';
import { Smartphone, Trash2 } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    authApi.getSessions().then(({ data }) => setSessions(data));
  }, []);

  const handleRevoke = async (sessionId: string) => {
    try {
      await authApi.revokeSession(sessionId);
      setSessions((s) => s.filter((x) => x.id !== sessionId));
      toast.success('Session revoked');
    } catch {
      toast.error('Failed to revoke session');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <section>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Profile</h2>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-500">Username</span>
            <span className="text-gray-900 dark:text-white">{user?.username}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Email</span>
            <span className="text-gray-900 dark:text-white">{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Role</span>
            <span className="text-gray-900 dark:text-white capitalize">{user?.role}</span>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Active Sessions</h2>
        <div className="bg-white dark:bg-gray-800 rounded-lg divide-y divide-gray-200 dark:divide-gray-700">
          {sessions.map((session) => (
            <div key={session.id} className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Smartphone size={20} className="text-gray-400" />
                <div>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {session.device_name || 'Unknown Device'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {session.ip_address} &middot; {session.last_active_at ? new Date(session.last_active_at).toLocaleDateString() : 'N/A'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleRevoke(session.id)}
                className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <p className="p-4 text-gray-500 text-sm">No active sessions</p>
          )}
        </div>
      </section>
    </div>
  );
}

import { Link, useNavigate } from 'react-router-dom';
import { LogOut, BookOpen, Settings, Shield, Heart } from 'lucide-react';
import { useAuthStore } from '@/store';

export function Header() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-50 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
          <BookOpen size={24} />
          InkIsle
        </Link>

        <nav className="flex items-center gap-4">
          <Link to="/collections" className="text-gray-600 dark:text-gray-300 hover:text-gray-900" title="Collections">
            <Heart size={20} />
          </Link>
          {user?.role === 'admin' && (
            <Link to="/admin" className="text-gray-600 dark:text-gray-300 hover:text-gray-900">
              <Shield size={20} />
            </Link>
          )}
          <Link to="/settings" className="text-gray-600 dark:text-gray-300 hover:text-gray-900">
            <Settings size={20} />
          </Link>
          <button onClick={handleLogout} className="text-gray-600 dark:text-gray-300 hover:text-red-500">
            <LogOut size={20} />
          </button>
          {user && (
            <span className="text-sm text-gray-500">{user.username}</span>
          )}
        </nav>
      </div>
    </header>
  );
}

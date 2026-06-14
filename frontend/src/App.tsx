import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useEffect } from 'react';
import { useAuthStore } from '@/store';
import { authApi } from '@/api/auth';
import { AppShell } from '@/components/layout/AppShell';
import { ProtectedRoute, AdminRoute } from '@/components/common/ProtectedRoute';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Library from '@/pages/Library';
import Reader from '@/pages/Reader';
import SettingsPage from '@/pages/Settings';
import AdminDashboard from '@/pages/AdminDashboard';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30000 } },
});

function AuthLoader({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, setUser } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      authApi.getMe().then(({ data }) => setUser(data)).catch(() => {});
    }
  }, [isAuthenticated, setUser]);

  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthLoader>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/read/:bookId" element={
              <ProtectedRoute><Reader /></ProtectedRoute>
            } />
            <Route element={
              <ProtectedRoute><AppShell /></ProtectedRoute>
            }>
              <Route path="/" element={<Library />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/admin" element={
                <AdminRoute><AdminDashboard /></AdminRoute>
              } />
            </Route>
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </AuthLoader>
      </BrowserRouter>
      <Toaster position="top-right" />
    </QueryClientProvider>
  );
}

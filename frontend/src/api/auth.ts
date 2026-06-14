import client from './client';
import { TokenResponse, User } from '@/types/user';

export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    client.post<User>('/auth/register', data),

  login: (data: { username: string; password: string; device_name?: string }) =>
    client.post<TokenResponse>('/auth/login', data),

  refresh: (refresh_token: string) =>
    client.post<TokenResponse>('/auth/refresh', { refresh_token }),

  getMe: () => client.get<User>('/users/me'),

  getSessions: () => client.get('/auth/sessions'),

  revokeSession: (sessionId: string) => client.delete(`/auth/sessions/${sessionId}`),
};

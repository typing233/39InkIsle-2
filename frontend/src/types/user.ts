export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
  is_active: boolean;
  created_at: string;
}

export interface Session {
  id: string;
  device_name: string | null;
  ip_address: string | null;
  last_active_at: string | null;
  created_at: string;
  is_current: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

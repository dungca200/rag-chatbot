import type { AuthTokens } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  private getTokens(): AuthTokens | null {
    if (typeof window === 'undefined') return null;
    const tokens = localStorage.getItem('tokens');
    return tokens ? JSON.parse(tokens) : null;
  }

  private setTokens(tokens: AuthTokens): void {
    localStorage.setItem('tokens', JSON.stringify(tokens));
  }

  private clearTokens(): void {
    localStorage.removeItem('tokens');
  }

  private async refreshToken(): Promise<boolean> {
    const tokens = this.getTokens();
    if (!tokens?.refresh) return false;

    try {
      const response = await fetch(`${this.baseUrl}/api/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: tokens.refresh }),
      });

      if (!response.ok) {
        this.clearTokens();
        return false;
      }

      const data = await response.json();
      this.setTokens({ access: data.access, refresh: tokens.refresh });
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const tokens = this.getTokens();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (tokens?.access) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${tokens.access}`;
    }

    let response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    // Token expired, try refresh
    if (response.status === 401 && tokens?.refresh) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        const newTokens = this.getTokens();
        (headers as Record<string, string>)['Authorization'] = `Bearer ${newTokens?.access}`;
        response = await fetch(`${this.baseUrl}${endpoint}`, {
          ...options,
          headers,
        });
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    const tokens = this.getTokens();
    const headers: HeadersInit = {};

    if (tokens?.access) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${tokens.access}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Upload failed' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth methods
  async login(username: string, password: string): Promise<{ user: { id: string; username: string; email: string; is_staff: boolean }; tokens: AuthTokens }> {
    const response = await this.post<{
      success: boolean;
      tokens: AuthTokens;
      user: { id: string; username: string; email: string; is_staff: boolean };
    }>('/api/auth/login/', { username, password });

    if (response.tokens) {
      this.setTokens(response.tokens);
    }

    return { user: response.user, tokens: response.tokens };
  }

  async register(data: { username: string; email: string; password: string; password_confirm: string }): Promise<void> {
    await this.post('/api/auth/register/', data);
  }

  logout(): void {
    this.clearTokens();
  }

  isAuthenticated(): boolean {
    return !!this.getTokens()?.access;
  }

  // SSE streaming for chat
  createChatStream(
    message: string,
    conversationId?: string,
    documentKey?: string,
    persistEmbeddings?: boolean
  ): EventSource | null {
    const tokens = this.getTokens();
    if (!tokens?.access) return null;

    // For SSE, we need to use a different approach since EventSource doesn't support POST
    // We'll use fetch with ReadableStream instead
    return null; // Will be implemented in the chat hook
  }
}

export const apiClient = new ApiClient();
export default apiClient;

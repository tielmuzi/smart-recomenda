import type { AuthUser, Content, Metrics, PreferenceState } from '../types';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

const request = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    credentials: 'include',
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: 'Não foi possível concluir a operação.' }));
    throw new ApiError(detail.detail || 'Erro de comunicação com a API.', response.status);
  }
  return response.json();
};

const toQuery = (params: Record<string, string | number | undefined>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : '';
};

export const api = {
  loginUrl: `${apiBaseUrl}/api/v1/auth/login`,
  authConfig: () => request<{ enabled: boolean; demo_access: boolean }>('/auth/config'),
  authMe: () => request<AuthUser>('/auth/me'),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
  contents: (params = '') => request<{ items: Content[]; total: number }>(`/contents${params}`),
  recommendations: (params: Record<string, string | number | undefined> = {}) => request<{ items: Content[]; strategy: string }>('/recommendations' + toQuery(params)),
  preferences: () => request<PreferenceState>('/preferences'),
  savePreferences: (data: PreferenceState) => request<PreferenceState>('/preferences', { method: 'PUT', body: JSON.stringify(data) }),
  toggleFavorite: (contentId: number) => request<{ favorite: boolean }>(`/favorites/${contentId}`, { method: 'POST' }),
  favorites: () => request<Content[]>('/favorites'),
  rate: (contentId: number, rating: number) => request<{ ok: boolean }>(`/ratings/${contentId}`, { method: 'POST', body: JSON.stringify({ rating }) }),
  recordInteraction: (contentId: number, kind: 'view' | 'hide') => request<{ ok: boolean; kind: string }>(`/interactions/${contentId}`, { method: 'POST', body: JSON.stringify({ kind }) }),
  history: () => request<Content[]>('/interactions'),
  clearHistory: () => request<{ ok: boolean }>('/interactions', { method: 'DELETE' }),
  metrics: () => request<Metrics>('/admin/metrics'),
  adminCreate: (content: Partial<Content>) => request<Content>('/admin/contents', { method: 'POST', body: JSON.stringify(content) }),
};

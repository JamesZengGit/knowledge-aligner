import { User, Decision, PersonalizedDigest, Gap, SearchFilters } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(`API Error: ${errorText}`, response.status);
  }

  return response.json();
}

export const api = {
  // System endpoints
  getStatus: () => fetchApi<{
    users: number;
    messages: number;
    decisions: number;
    relationships: number;
    embeddings: Record<string, number>;
    ai_enabled: boolean;
  }>('/api/status'),

  setupSystem: () => fetchApi<{
    message: string;
    users: number;
    messages: number;
  }>('/api/setup', { method: 'POST' }),

  // User endpoints
  getUsers: () => fetchApi<User[]>('/api/users'),

  // Decision endpoints
  getDecisions: (params?: {
    limit?: number;
    user_id?: string;
    decision_type?: string;
    days?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.user_id) searchParams.append('user_id', params.user_id);
    if (params?.decision_type) searchParams.append('decision_type', params.decision_type);
    if (params?.days) searchParams.append('days', params.days.toString());

    return fetchApi<Decision[]>(`/api/decisions?${searchParams}`);
  },

  searchDecisions: (filters: SearchFilters & { query: string }) =>
    fetchApi<Decision[]>('/api/search', {
      method: 'POST',
      body: JSON.stringify(filters),
    }),

  // Digest endpoints
  getUserDigest: (userId: string, days: number = 7) =>
    fetchApi<PersonalizedDigest>(`/api/digest/${userId}?days=${days}`),

  // Gap detection endpoints
  getGaps: (days: number = 30) =>
    fetchApi<Gap[]>(`/api/gaps?days=${days}`),

  // Pipeline endpoints
  ingestMessages: (batchSize: number = 100) =>
    fetchApi<{
      message: string;
      processed: number;
      decisions_created: number;
    }>(`/api/ingest?batch_size=${batchSize}`, { method: 'POST' }),

  generateEmbeddings: () =>
    fetchApi<{
      message: string;
      results: Record<string, number>;
    }>('/api/embed', { method: 'POST' }),
};

export default api;
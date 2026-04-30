const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') + '/api/v1';

export async function fetchWithAuth(
  endpoint: string,
  token: string | null,
  options: RequestInit = {}
) {
  if (!token) {
    throw new Error('Authentication token is missing');
  }

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: 'Unknown error occurred' };
    }
    throw new Error(errorData.detail || 'API request failed');
  }

  return response.json();
}

export const api = {
  careRecipients: {
    create: async (token: string, data: any) => {
      return fetchWithAuth('/care-recipients', token, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    list: async (token: string) => {
      return fetchWithAuth('/care-recipients', token);
    },
    get: async (token: string, id: string) => {
      return fetchWithAuth(`/care-recipients/${id}`, token);
    },
    vitals: async (token: string, id: string, limit = 10) => {
      return fetchWithAuth(`/care-recipients/${id}/vitals?limit=${limit}`, token);
    },
    episodes: async (token: string, id: string, limit = 5) => {
      return fetchWithAuth(`/care-recipients/${id}/episodes?limit=${limit}`, token);
    },
    medications: async (token: string, id: string) => {
      return fetchWithAuth(`/care-recipients/${id}/medications`, token);
    },
  },
};

/**
 * ThreatLens API Client
 */

export const getAuthHeaders = () => {
  const token = localStorage.getItem('token') || '';
  const apiKey = localStorage.getItem('apiKey') || (token ? '' : 'test-api-key-12345');
  
  const headers = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  return headers;
};

export const apiFetch = async (endpoint, options = {}) => {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.detail || errorData.message || `API Error (${response.status})`;
    throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
  }

  return response.json();
};

export const fetchSystemHealth = async () => {
  try {
    return await apiFetch('/api/v1/health/detailed');
  } catch (err) {
    return {
      status: 'unhealthy',
      error: err.message,
      services: {
        postgres: { status: 'unhealthy' },
        qdrant: { status: 'unhealthy' },
      },
    };
  }
};

export const loginUser = async (email, password) => {
  const data = await apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    localStorage.setItem('token', data.access_token);
  }
  return data;
};

export const getCurrentUser = async () => {
  return await apiFetch('/api/v1/auth/me');
};

export const queryCopilotStream = async (queryPayload, onChunk, onError, onComplete) => {
  const headers = getAuthHeaders();
  
  try {
    const response = await fetch('/api/v1/query/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify(queryPayload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || `Query failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      // The last element is either empty (if ended with \n) or incomplete line
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith('data: ')) {
          const rawData = trimmed.slice(6).trim();
          if (rawData === '[DONE]') {
            if (onComplete) onComplete();
            return;
          }
          try {
            const parsed = JSON.parse(rawData);
            onChunk(parsed);
          } catch (e) {
            console.warn('Failed to parse SSE payload:', rawData, e);
          }
        }
      }
    }
    if (onComplete) onComplete();
  } catch (err) {
    if (onError) onError(err);
  }
};

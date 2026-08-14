const API_BASE = '/api';

function getAuthHeader(): HeadersInit {
  const token = localStorage.getItem('token');
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(r => handleResponse(r)),

  logout: () =>
    fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  getMe: () =>
    fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  // Essays
  getEssays: () =>
    fetch(`${API_BASE}/essays`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  getAllEssays: () =>
    fetch(`${API_BASE}/essays/all`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  getEssay: (id: number) =>
    fetch(`${API_BASE}/essays/${id}`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  deleteEssay: (id: number) =>
    fetch(`${API_BASE}/essays/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  uploadEssay: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/essays`, {
      method: 'POST',
      headers: getAuthHeader(),
      body: formData,
    }).then(r => handleResponse(r));
  },

  // Users (admin)
  getUsers: () =>
    fetch(`${API_BASE}/users`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  createUser: (data: { username: string; password: string; role: string }) =>
    fetch(`${API_BASE}/users`, {
      method: 'POST',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => handleResponse(r)),

  updateUser: (id: number, data: { username?: string; password?: string; role?: string }) =>
    fetch(`${API_BASE}/users/${id}`, {
      method: 'PUT',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => handleResponse(r)),

  deleteUser: (id: number) =>
    fetch(`${API_BASE}/users/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  // Cache (admin)
  getCacheStats: () =>
    fetch(`${API_BASE}/cache/stats`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  clearCache: () =>
    fetch(`${API_BASE}/cache`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  // Export (admin)
  getReport: () =>
    fetch(`${API_BASE}/export/report`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),
};

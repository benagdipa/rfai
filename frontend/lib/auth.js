import api from './api';

export async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await api.post('/auth/token', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  localStorage.setItem('token', response.data.access_token);
}

export async function signup(username, password) {
  const response = await api.post('/auth/signup', { username, password });
  localStorage.setItem('token', response.data.access_token);
}

export function logout() {
  localStorage.removeItem('token');
  window.location.href = '/login';
}
import api from './api';
import { useRouter } from 'next/router';
import { useState, useCallback, useEffect } from 'react';

// Core authentication functions
export async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  try {
    const response = await api.post('/auth/token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    const { access_token, refresh_token } = response.data;
    localStorage.setItem('token', access_token);
    if (refresh_token) localStorage.setItem('refresh_token', refresh_token);
    console.log('Login successful:', { username });
    return response.data;
  } catch (error) {
    const errorDetails = {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    };
    console.error('Login failed:', errorDetails);
    throw new Error(errorDetails.data?.detail || 'Login failed');
  }
}

export async function signup(username, password) {
  try {
    const response = await api.post('/auth/signup', { username, password });
    const { access_token, refresh_token } = response.data;
    localStorage.setItem('token', access_token);
    if (refresh_token) localStorage.setItem('refresh_token', refresh_token);
    console.log('Signup successful:', { username });
    return response.data;
  } catch (error) {
    const errorDetails = {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    };
    console.error('Signup failed:', errorDetails);
    throw new Error(errorDetails.data?.detail || 'Signup failed');
  }
}

export async function logout(navigate = null) {
  try {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    console.log('Logout successful');
    if (navigate) {
      navigate('/login');
    } else {
      window.location.href = '/login';
    }
  } catch (error) {
    console.error('Logout failed:', error);
  }
}

export async function getCurrentUser() {
  try {
    const response = await api.get('/auth/me');
    console.log('Fetched current user:', response.data);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch current user:', error);
    throw new Error('Unable to fetch user information');
  }
}

export async function refreshToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    console.log('Token refreshed successfully');
    return access_token;
  } catch (error) {
    console.error('Token refresh failed:', error);
    throw new Error('Failed to refresh token');
  }
}

// React Hook for authentication state management
export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchUser = useCallback(async () => {
    try {
      setLoading(true);
      const userData = await getCurrentUser();
      setUser(userData);
    } catch (error) {
      setUser(null);
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      router.push('/login');
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const handleLogin = async (username, password) => {
    try {
      setLoading(true);
      await login(username, password);
      await fetchUser();
      router.push('/');
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (username, password) => {
    try {
      setLoading(true);
      await signup(username, password);
      await fetchUser();
      router.push('/');
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = useCallback(async () => {
    try {
      setLoading(true);
      await logout(() => router.push('/login'));
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [router]);

  return {
    user,
    loading,
    login: handleLogin,
    signup: handleSignup,
    logout: handleLogout,
    refreshToken,
  };
}

export default api; // Export api for consistency

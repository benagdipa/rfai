import axios from 'axios';
import { logout } from './auth'; // Assuming auth utilities are in the same lib folder

// Base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000', // Adjusted for React (not Next.js)
  timeout: 10000, // 10-second timeout
  headers: {
    'Content-Type': 'application/json', // Default content type
  },
});

// Request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Preserve Content-Type set by specific requests (e.g., multipart/form-data)
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and token refresh
api.interceptors.response.use(
  (response) => response, // Pass successful responses unchanged
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized (e.g., token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark as retried to avoid infinite loops
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token available');

        const response = await axios.post(
          `${api.defaults.baseURL}/auth/refresh`,
          { refresh_token: refreshToken },
          { headers: { 'Content-Type': 'application/json' } }
        );

        const { access_token } = response.data;
        localStorage.setItem('token', access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest); // Retry original request with new token
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
        await logout(); // Logout user if refresh fails
        window.location.href = '/login'; // Redirect to login
        return Promise.reject(refreshError);
      }
    }

    // Handle other errors
    const errorMessage =
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred';
    console.error('API error:', errorMessage);
    return Promise.reject(new Error(errorMessage));
  }
);

// Utility functions for common HTTP methods
export const get = async (url, config = {}) => {
  try {
    const response = await api.get(url, config);
    return response.data;
  } catch (error) {
    throw error; // Let caller handle the error
  }
};

export const post = async (url, data, config = {}) => {
  try {
    const response = await api.post(url, data, config);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const put = async (url, data, config = {}) => {
  try {
    const response = await api.put(url, data, config);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const del = async (url, config = {}) => {
  try {
    const response = await api.delete(url, config);
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Export the axios instance for custom usage if needed
export default api;
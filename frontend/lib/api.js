import axios from 'axios';

// Base configuration
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000', // Configurable via env
  timeout: 10000, // Default timeout, overridable per request
  headers: {
    'Content-Type': 'application/json',
  },
});

// Variables to manage token refresh concurrency
let isRefreshing = false;
let refreshSubscribers = [];

// Helper to notify subscribers after token refresh
const onTokenRefreshed = (token) => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

// Request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') { // Browser-only logic
      const token = localStorage.getItem('token'); // TODO: Consider migrating to Cookies
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and token refresh
api.interceptors.response.use(
  (response) => response, // Pass through successful responses
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized with token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (typeof window !== 'undefined') { // Browser-only logic
        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const refreshToken = localStorage.getItem('refresh_token'); // TODO: Consider Cookies
            if (!refreshToken) throw new Error('No refresh token available');

            const response = await axios.post(
              `${api.defaults.baseURL}/auth/refresh`,
              { refresh_token: refreshToken },
              { headers: { 'Content-Type': 'application/json' } }
            );

            const { access_token } = response.data;
            localStorage.setItem('token', access_token); // Update token
            isRefreshing = false;
            onTokenRefreshed(access_token); // Notify subscribers
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return api(originalRequest); // Retry original request
          } catch (refreshError) {
            isRefreshing = false;
            refreshSubscribers = [];
            console.error('Token refresh failed:', refreshError);
            await import('./auth').then(({ logout }) => logout()); // Dynamic import
            if (typeof window !== 'undefined') { 
            window.location.href = '/login'; // Redirect to login
            }
            return Promise.reject(refreshError);
          }
        }

        // Queue requests during refresh
        return new Promise((resolve) => {
          refreshSubscribers.push((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }
    }

    // Generic error handling
    const errorMessage = error.response?.data?.detail || error.message || 'An unexpected error occurred';
    console.error('API error:', errorMessage);
    // TODO: Integrate with UI notification (e.g., react-hot-toast)
    // Example: toast.error(errorMessage);
    return Promise.reject(new Error(errorMessage));
  }
);

// HTTP method helpers with configurable options
export const get = async (url, config = {}) => {
  try {
    const response = await api.get(url, { ...config, timeout: config.timeout || 10000 });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const post = async (url, data, config = {}) => {
  try {
    const response = await api.post(url, data, { ...config, timeout: config.timeout || 10000 });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const put = async (url, data, config = {}) => {
  try {
    const response = await api.put(url, data, { ...config, timeout: config.timeout || 10000 });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const del = async (url, config = {}) => {
  try {
    const response = await api.delete(url, { ...config, timeout: config.timeout || 10000 });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Export the Axios instance for custom usage if needed
export default api;

/**
 * Notes for Future Improvements:
 * - Security: Replace localStorage with HTTP-only cookies (e.g., using js-cookie).
 *   Example: import Cookies from 'js-cookie'; const token = Cookies.get('token');
 * - UI Feedback: Integrate a notification library (e.g., react-hot-toast) for error messages.
 * - TypeScript: Add types for better type safety, e.g., export const get = async <T>(url: string) => Promise<T>;
 */
import apiClient from './api';
import { API_ENDPOINTS } from '../config/api';

export const authService = {
  login: async (username, password) => {
    try {
      const response = await apiClient.post(API_ENDPOINTS.LOGIN, {
        username,
        password,
      });
      
      if (response.data.key) {
        localStorage.setItem('authToken', response.data.key);
        return response.data;
      }
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  register: async (userData) => {
    try {
      const response = await apiClient.post(API_ENDPOINTS.REGISTER, userData);
      if (response.data.key) {
        localStorage.setItem('authToken', response.data.key);
      }
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  logout: async () => {
    try {
      await apiClient.post(API_ENDPOINTS.LOGOUT);
      localStorage.removeItem('authToken');
    } catch (error) {
      // Even if request fails, clear local token
      localStorage.removeItem('authToken');
    }
  },

  getCurrentUser: async () => {
    try {
      const response = await apiClient.get(API_ENDPOINTS.PROFILE);
      return response.data;
    } catch (error) {
      throw error.response?.data || error.message;
    }
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('authToken');
  },
};

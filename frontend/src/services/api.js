import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 90000,
});

const getErrorMessage = (error) => {
  if (error.response?.data?.detail) {
    return typeof error.response.data.detail === 'string'
      ? error.response.data.detail
      : JSON.stringify(error.response.data.detail);
  }
  if (error.message) return error.message;
  return 'Something went wrong. Please try again.';
};

export const uploadDocument = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return { success: true, data };
  } catch (error) {
    return { success: false, error: getErrorMessage(error) };
  }
};

export const askQuestion = async (question) => {
  try {
    const { data } = await api.post('/ask', { question });
    return { success: true, data };
  } catch (error) {
    return { success: false, error: getErrorMessage(error) };
  }
};

export const getDocumentInfo = async () => {
  try {
    const { data } = await api.get('/documents');
    return { success: true, data };
  } catch (error) {
    return { success: false, error: getErrorMessage(error) };
  }
};

export const clearKnowledgeBase = async () => {
  try {
    const { data } = await api.delete('/clear');
    return { success: true, data };
  } catch (error) {
    return { success: false, error: getErrorMessage(error) };
  }
};

export default api;

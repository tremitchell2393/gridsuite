/**
 * API client.
 *
 * Single axios instance, configured for the FastAPI backend (proxied
 * via Vite during dev — see vite.config.ts). Attaches the JWT from
 * localStorage to every request and redirects to /login on 401s.
 *
 * All typed request functions live in api/endpoints.ts — this file is
 * just the transport layer.
 */
import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/v1",
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("gridsuite_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("gridsuite_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

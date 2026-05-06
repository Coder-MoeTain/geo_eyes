import axios, { AxiosInstance } from "axios";

const instance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  withCredentials: true,
});

instance.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body && typeof body === "object" && "success" in body) {
      if (body.success) {
        response.data = body.data;
      } else {
        const err = new Error(body?.error?.message || "API request failed");
        throw err;
      }
    }
    return response;
  },
  (error) => {
    const detail = error?.response?.data?.error?.message || error?.message;
    if (detail) error.message = detail;
    return Promise.reject(error);
  }
);

export const apiClient = instance;

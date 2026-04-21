import axios from "axios";

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || "/";
const apiBaseUrl =
  rawApiBaseUrl !== "/" ? rawApiBaseUrl.replace(/\/+$/, "") : "/";

const resolveApiUrl = (path: string) =>
  apiBaseUrl === "/" ? path : `${apiBaseUrl}${path}`;

const api = axios.create({
  baseURL: apiBaseUrl,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — attach JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const { data } = await axios.post(resolveApiUrl("/api/auth/refresh"), {
            refresh_token: refreshToken,
          });
          localStorage.setItem("access_token", data.access_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user");
          window.location.href = "/login";
        }
      } else {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export default api;

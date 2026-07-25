import axios from "axios";

const api = axios.create({
  baseURL: "",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = token;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.startsWith("/login")) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export function login({ username, password, captcha_id, captcha_code }) {
  return api.post("/api/loyanui/auth/login", {
    username,
    password,
    captcha_id,
    captcha_code,
  });
}

export function verifyToken(token) {
  return api.get("/api/loyanui/auth/verify", { params: { token } });
}

export default api;

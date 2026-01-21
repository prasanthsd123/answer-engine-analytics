import axios from "axios";

// Use empty base URL to go through Next.js rewrites (avoids mixed content issues)
// The rewrites in next.config.js will proxy /api/* to the backend
export const api = axios.create({
  baseURL: "",
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    const response = await api.post("/api/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return response.data;
  },

  register: async (email: string, password: string, fullName?: string) => {
    const response = await api.post("/api/auth/register", {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  },

  getMe: async () => {
    const response = await api.get("/api/auth/me");
    return response.data;
  },

  googleAuth: async (credential: string) => {
    const response = await api.post("/api/auth/google", { credential });
    return response.data;
  },
};

// Brand APIs
export const brandApi = {
  list: async (page = 1, pageSize = 10, search?: string) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search) params.append("search", search);
    const response = await api.get(`/api/brands?${params}`);
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get(`/api/brands/${id}`);
    return response.data;
  },

  create: async (data: any) => {
    const response = await api.post("/api/brands", data);
    return response.data;
  },

  update: async (id: string, data: any) => {
    const response = await api.put(`/api/brands/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/api/brands/${id}`);
  },

  addCompetitor: async (brandId: string, data: any) => {
    const response = await api.post(`/api/brands/${brandId}/competitors`, data);
    return response.data;
  },

  removeCompetitor: async (brandId: string, competitorId: string) => {
    await api.delete(`/api/brands/${brandId}/competitors/${competitorId}`);
  },
};

// Question APIs
export const questionApi = {
  list: async (brandId: string, page = 1, pageSize = 20) => {
    const response = await api.get(
      `/api/questions/brand/${brandId}?page=${page}&page_size=${pageSize}`
    );
    return response.data;
  },

  create: async (brandId: string, data: any) => {
    const response = await api.post(`/api/questions/brand/${brandId}`, data);
    return response.data;
  },

  generate: async (brandId: string, options: any) => {
    const response = await api.post(
      `/api/questions/brand/${brandId}/generate`,
      options
    );
    return response.data;
  },

  delete: async (questionId: string) => {
    await api.delete(`/api/questions/${questionId}`);
  },
};

// Analysis APIs
export const analysisApi = {
  getOverview: async (brandId: string) => {
    const response = await api.get(`/api/analysis/brand/${brandId}/overview`);
    return response.data;
  },

  getTrends: async (brandId: string, metric: string, days = 30) => {
    const response = await api.get(
      `/api/analysis/brand/${brandId}/trends?metric=${metric}&days=${days}`
    );
    return response.data;
  },

  getPlatformMetrics: async (brandId: string, platform: string, days = 7) => {
    const response = await api.get(
      `/api/analysis/brand/${brandId}/platform/${platform}?days=${days}`
    );
    return response.data;
  },

  getCompetitorAnalysis: async (brandId: string, days = 30) => {
    const response = await api.get(
      `/api/analysis/brand/${brandId}/competitors?days=${days}`
    );
    return response.data;
  },

  triggerAnalysis: async (brandId: string, platforms?: string[]) => {
    // FastAPI expects multiple 'platforms' params, not comma-separated
    const params = platforms
      ? `?${platforms.map((p) => `platforms=${p}`).join("&")}`
      : "";
    const response = await api.post(
      `/api/analysis/brand/${brandId}/run${params}`
    );
    return response.data;
  },
};

// Report APIs
export const reportApi = {
  getSummary: async (brandId: string, days = 30) => {
    const response = await api.get(
      `/api/reports/brand/${brandId}/summary?days=${days}`
    );
    return response.data;
  },

  exportCsv: async (brandId: string, days = 30) => {
    const response = await api.get(
      `/api/reports/brand/${brandId}/export/csv?days=${days}`,
      { responseType: "blob" }
    );
    return response.data;
  },

  exportJson: async (brandId: string, days = 30) => {
    const response = await api.get(
      `/api/reports/brand/${brandId}/export/json?days=${days}`
    );
    return response.data;
  },
};

import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
    baseURL: API,
    withCredentials: true,
    headers: { "Content-Type": "application/json" },
});

let refreshing = null;

api.interceptors.response.use(
    (r) => r,
    async (error) => {
        const original = error.config;
        if (
            error.response &&
            error.response.status === 401 &&
            !original._retry &&
            !original.url.includes("/auth/login") &&
            !original.url.includes("/auth/refresh") &&
            !original.url.includes("/auth/register")
        ) {
            original._retry = true;
            try {
                if (!refreshing) {
                    refreshing = api.post("/auth/refresh").finally(() => {
                        refreshing = null;
                    });
                }
                await refreshing;
                return api(original);
            } catch (e) {
                return Promise.reject(error);
            }
        }
        return Promise.reject(error);
    },
);

export default api;

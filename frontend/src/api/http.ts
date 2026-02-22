import axios, {
  type AxiosResponse,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";

import { env } from "@/shared/config/env";
import { tokenStorage } from "@/shared/lib/token-storage";
import type { TokenPairResponse } from "@/shared/types/auth";

type RetriableConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

type AuthFailureHandler = () => void;

const apiBaseURL = env.apiBaseUrl;

export const http = axios.create({
  baseURL: apiBaseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

const refreshClient = axios.create({
  baseURL: apiBaseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

let refreshPromise: Promise<string> | null = null;
let authFailureHandler: AuthFailureHandler | null = null;

export function registerAuthFailureHandler(handler: AuthFailureHandler) {
  authFailureHandler = handler;
}

function notifyAuthFailure() {
  authFailureHandler?.();
}

function isAuthEndpoint(url: string | undefined) {
  if (!url) {
    return false;
  }

  return url.includes("/auth/login") || url.includes("/auth/refresh");
}

async function runRefreshFlow(): Promise<string> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) {
    throw new Error("Missing refresh token");
  }

  const response = await refreshClient.post<TokenPairResponse>("/auth/refresh", {
    refresh_token: refreshToken,
  });

  tokenStorage.setTokens({
    accessToken: response.data.access_token,
    refreshToken: response.data.refresh_token,
  });

  return response.data.access_token;
}

http.interceptors.request.use((config) => {
  const accessToken = tokenStorage.getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

http.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const statusCode = error.response?.status;
    const config = error.config as RetriableConfig | undefined;

    if (!config || statusCode !== 401 || config._retry || isAuthEndpoint(config.url)) {
      return Promise.reject(error);
    }

    config._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = runRefreshFlow().finally(() => {
          refreshPromise = null;
        });
      }

      const nextAccessToken = await refreshPromise;
      config.headers.Authorization = `Bearer ${nextAccessToken}`;
      return await http.request(config);
    } catch (refreshError) {
      tokenStorage.clear();
      notifyAuthFailure();
      return Promise.reject(refreshError);
    }
  },
);

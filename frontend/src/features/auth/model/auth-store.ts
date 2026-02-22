import { create } from "zustand";

import { getCurrentUser, login as loginRequest, logout as logoutRequest } from "@/api/auth";
import { registerAuthFailureHandler } from "@/api/http";
import { tokenStorage } from "@/shared/lib/token-storage";
import type { User } from "@/shared/types/auth";

type AuthStatus = "anonymous" | "authenticated";

type AuthStore = {
  user: User | null;
  authStatus: AuthStatus;
  isBootstrapping: boolean;
  isSubmitting: boolean;
  errorMessage: string | null;
  bootstrap: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearSession: () => void;
};

function normalizeApiError(error: unknown): string {
  if (typeof error === "object" && error !== null) {
    const candidate = error as {
      response?: { data?: { detail?: { message?: string } | string } };
      message?: string;
    };

    const detail = candidate.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = detail.message;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
    if (typeof candidate.message === "string" && candidate.message.trim()) {
      return candidate.message;
    }
  }

  return "Request failed.";
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  authStatus: "anonymous",
  isBootstrapping: true,
  isSubmitting: false,
  errorMessage: null,
  clearSession: () => {
    tokenStorage.clear();
    set({
      user: null,
      authStatus: "anonymous",
      isSubmitting: false,
      errorMessage: null,
    });
  },
  bootstrap: async () => {
    const hasAccess = Boolean(tokenStorage.getAccessToken());
    const hasRefresh = Boolean(tokenStorage.getRefreshToken());

    if (!hasAccess && !hasRefresh) {
      set({ isBootstrapping: false, authStatus: "anonymous", user: null });
      return;
    }

    set({ isBootstrapping: true, errorMessage: null });

    try {
      const { user } = await getCurrentUser();
      set({
        user,
        authStatus: "authenticated",
        isBootstrapping: false,
        errorMessage: null,
      });
    } catch {
      tokenStorage.clear();
      set({
        user: null,
        authStatus: "anonymous",
        isBootstrapping: false,
        errorMessage: null,
      });
    }
  },
  login: async (username, password) => {
    set({ isSubmitting: true, errorMessage: null });

    try {
      const payload = await loginRequest({ username, password });
      tokenStorage.setTokens({
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
      });
      set({
        user: payload.user,
        authStatus: "authenticated",
        isSubmitting: false,
        errorMessage: null,
      });
    } catch (error) {
      tokenStorage.clear();
      set({
        user: null,
        authStatus: "anonymous",
        isSubmitting: false,
        errorMessage: normalizeApiError(error),
      });
      throw error;
    }
  },
  logout: async () => {
    try {
      await logoutRequest();
    } catch {
      // Logout should still clear local session even if backend token is already invalid.
    } finally {
      tokenStorage.clear();
      set({
        user: null,
        authStatus: "anonymous",
        errorMessage: null,
        isSubmitting: false,
        isBootstrapping: false,
      });
    }
  },
}));

registerAuthFailureHandler(() => {
  useAuthStore.getState().clearSession();
});

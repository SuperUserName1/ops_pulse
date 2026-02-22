import { http } from "@/api/http";
import type { CurrentUserResponse, TokenPairResponse } from "@/shared/types/auth";

export type LoginPayload = {
  username: string;
  password: string;
};

export async function login(payload: LoginPayload): Promise<TokenPairResponse> {
  const response = await http.post<TokenPairResponse>("/auth/login", payload);
  return response.data;
}

export async function getCurrentUser(): Promise<CurrentUserResponse> {
  const response = await http.get<CurrentUserResponse>("/auth/me");
  return response.data;
}

export async function logout(): Promise<void> {
  await http.post("/auth/logout");
}

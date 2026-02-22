import { http } from "@/api/http";
import type {
  CurrentUserResponse,
  TokenPairResponse,
  UsersListResponse,
} from "@/shared/types/auth";

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

export type ListUsersParams = {
  limit?: number;
  offset?: number;
  search?: string;
  status?: "active" | "disabled";
  created_from?: string;
  created_to?: string;
};

export async function listUsers(params: ListUsersParams): Promise<UsersListResponse> {
  const response = await http.get<UsersListResponse>("/auth/users", { params });
  return response.data;
}

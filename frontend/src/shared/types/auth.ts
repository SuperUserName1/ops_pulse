export type UserRole = "admin" | "agent" | "viewer";
export type UserStatus = "active" | "disabled";

export type User = {
  id: string;
  org_id: string;
  username: string;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  created_at: string;
};

export type TokenPairResponse = {
  token_type: "bearer";
  access_token: string;
  refresh_token: string;
  access_expires_in: number;
  refresh_expires_in: number;
  user: User;
};

export type CurrentUserResponse = {
  user: User;
};

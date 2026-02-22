import { http } from "@/api/http";
import type { HealthResponse } from "@/shared/types/health";

export async function getHealth(): Promise<HealthResponse> {
  const response = await http.get<HealthResponse>("/health");
  return response.data;
}

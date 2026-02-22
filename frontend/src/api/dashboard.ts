import { http } from "@/api/http";
import type { DashboardSummaryResponse } from "@/shared/types/dashboard";

export async function getDashboardSummary(): Promise<DashboardSummaryResponse> {
  const response = await http.get<DashboardSummaryResponse>("/dashboard/summary");
  return response.data;
}

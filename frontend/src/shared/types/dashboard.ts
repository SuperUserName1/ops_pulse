import type { Task } from "@/shared/types/tasks";

export type DashboardTaskStatusCounts = {
  open: number;
  in_progress: number;
  blocked: number;
  done: number;
};

export type DashboardSummaryResponse = {
  org_id: string;
  total_tasks: number;
  counts: DashboardTaskStatusCounts;
  recent_tasks: Task[];
};

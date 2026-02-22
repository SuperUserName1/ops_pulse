export type TaskStatus = "open" | "in_progress" | "blocked" | "done";

export type Task = {
  id: string;
  org_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  assignee_user_id: string | null;
  created_at: string;
};

export type TaskResponse = {
  task: Task;
};

export type TasksListResponse = {
  items: Task[];
  total: number;
  limit: number;
  offset: number;
};

export type TaskCreatePayload = {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  assignee_user_id?: string | null;
};

export type TaskUpdatePayload = Partial<{
  title: string;
  description: string | null;
  status: TaskStatus;
  assignee_user_id: string | null;
}>;

import { http } from "@/api/http";
import type {
  TaskCreatePayload,
  TaskResponse,
  TasksListResponse,
  TaskUpdatePayload,
} from "@/shared/types/tasks";

export type ListTasksParams = {
  limit?: number;
  offset?: number;
  search?: string;
  status?: "open" | "in_progress" | "blocked" | "done";
  assignee_user_id?: string;
  created_from?: string;
  created_to?: string;
};

export async function listTasks(params: ListTasksParams): Promise<TasksListResponse> {
  const response = await http.get<TasksListResponse>("/tasks", { params });
  return response.data;
}

export async function createTask(payload: TaskCreatePayload): Promise<TaskResponse> {
  const response = await http.post<TaskResponse>("/tasks", payload);
  return response.data;
}

export async function updateTask(taskId: string, payload: TaskUpdatePayload): Promise<TaskResponse> {
  const response = await http.patch<TaskResponse>(`/tasks/${taskId}`, payload);
  return response.data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await http.delete(`/tasks/${taskId}`);
}

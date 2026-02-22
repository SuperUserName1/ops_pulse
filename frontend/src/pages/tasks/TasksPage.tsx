import { useEffect, useState } from "react";

import { listUsers } from "@/api/auth";
import { createTask, deleteTask, listTasks, updateTask } from "@/api/tasks";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { getApiErrorMessage } from "@/shared/lib/api-error";
import type { User } from "@/shared/types/auth";
import type { Task, TaskStatus } from "@/shared/types/tasks";

type TaskFilters = {
  search: string;
  status: "" | TaskStatus;
  assignee_user_id: string;
  limit: number;
  offset: number;
};

type TaskForm = {
  title: string;
  description: string;
  status: TaskStatus;
  assignee_user_id: string;
};

type TasksState = {
  items: Task[];
  total: number;
  isLoading: boolean;
  isSubmitting: boolean;
  errorMessage: string | null;
  successMessage: string | null;
};

const TASK_STATUS_OPTIONS: TaskStatus[] = ["open", "in_progress", "blocked", "done"];

const DEFAULT_FILTERS: TaskFilters = {
  search: "",
  status: "",
  assignee_user_id: "",
  limit: 20,
  offset: 0,
};

const DEFAULT_FORM: TaskForm = {
  title: "",
  description: "",
  status: "open",
  assignee_user_id: "",
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function statusClass(status: TaskStatus): string {
  switch (status) {
    case "done":
      return "is-done";
    case "blocked":
      return "is-blocked";
    case "in_progress":
      return "is-progress";
    default:
      return "is-open";
  }
}

export function TasksPage() {
  const user = useAuthStore((state) => state.user);
  const [filters, setFilters] = useState<TaskFilters>(DEFAULT_FILTERS);
  const [draftSearch, setDraftSearch] = useState("");
  const [form, setForm] = useState<TaskForm>(DEFAULT_FORM);
  const [assigneeOptions, setAssigneeOptions] = useState<User[]>([]);
  const [assigneeLoadError, setAssigneeLoadError] = useState<string | null>(null);
  const [state, setState] = useState<TasksState>({
    items: [],
    total: 0,
    isLoading: true,
    isSubmitting: false,
    errorMessage: null,
    successMessage: null,
  });

  const canCreateOrUpdate = user?.role === "admin" || user?.role === "agent";
  const canDelete = user?.role === "admin";
  const canLoadUsers = user?.role === "admin";

  const loadTasksData = async (nextFilters: TaskFilters) => {
    setState((current) => ({ ...current, isLoading: true, errorMessage: null }));
    try {
      const response = await listTasks({
        limit: nextFilters.limit,
        offset: nextFilters.offset,
        search: nextFilters.search || undefined,
        status: nextFilters.status || undefined,
        assignee_user_id: nextFilters.assignee_user_id || undefined,
      });
      setState((current) => ({
        ...current,
        items: response.items,
        total: response.total,
        isLoading: false,
        errorMessage: null,
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        isLoading: false,
        errorMessage: getApiErrorMessage(error, "Failed to load tasks."),
      }));
    }
  };

  useEffect(() => {
    void loadTasksData(filters);
  }, [filters]);

  useEffect(() => {
    if (!canLoadUsers) {
      setAssigneeOptions([]);
      setAssigneeLoadError(null);
      return;
    }

    let cancelled = false;

    const loadAssignees = async () => {
      try {
        const response = await listUsers({ limit: 100, offset: 0, status: "active" });
        if (!cancelled) {
          setAssigneeOptions(response.items);
          setAssigneeLoadError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setAssigneeLoadError(getApiErrorMessage(error, "Failed to load assignees."));
        }
      }
    };

    void loadAssignees();

    return () => {
      cancelled = true;
    };
  }, [canLoadUsers]);

  const onCreateTask = async () => {
    if (!canCreateOrUpdate) {
      return;
    }

    setState((current) => ({
      ...current,
      isSubmitting: true,
      errorMessage: null,
      successMessage: null,
    }));

    try {
      await createTask({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        status: form.status,
        assignee_user_id: form.assignee_user_id || undefined,
      });
      setForm(DEFAULT_FORM);
      setState((current) => ({
        ...current,
        isSubmitting: false,
        successMessage: "Task created.",
      }));
      await loadTasksData({ ...filters, offset: 0 });
      setFilters((current) => ({ ...current, offset: 0 }));
    } catch (error) {
      setState((current) => ({
        ...current,
        isSubmitting: false,
        errorMessage: getApiErrorMessage(error, "Failed to create task."),
      }));
    }
  };

  const onUpdateTaskStatus = async (taskId: string, status: TaskStatus) => {
    if (!canCreateOrUpdate) {
      return;
    }
    setState((current) => ({ ...current, isSubmitting: true, errorMessage: null, successMessage: null }));
    try {
      await updateTask(taskId, { status });
      setState((current) => ({
        ...current,
        isSubmitting: false,
        successMessage: "Task updated.",
      }));
      await loadTasksData(filters);
    } catch (error) {
      setState((current) => ({
        ...current,
        isSubmitting: false,
        errorMessage: getApiErrorMessage(error, "Failed to update task."),
      }));
    }
  };

  const onReassignTask = async (taskId: string, assigneeUserId: string) => {
    if (!canLoadUsers) {
      return;
    }
    setState((current) => ({ ...current, isSubmitting: true, errorMessage: null, successMessage: null }));
    try {
      await updateTask(taskId, { assignee_user_id: assigneeUserId || null });
      setState((current) => ({
        ...current,
        isSubmitting: false,
        successMessage: "Assignee updated.",
      }));
      await loadTasksData(filters);
    } catch (error) {
      setState((current) => ({
        ...current,
        isSubmitting: false,
        errorMessage: getApiErrorMessage(error, "Failed to reassign task."),
      }));
    }
  };

  const onDeleteTask = async (taskId: string) => {
    if (!canDelete) {
      return;
    }
    setState((current) => ({ ...current, isSubmitting: true, errorMessage: null, successMessage: null }));
    try {
      await deleteTask(taskId);
      setState((current) => ({
        ...current,
        isSubmitting: false,
        successMessage: "Task deleted.",
      }));
      await loadTasksData(filters);
    } catch (error) {
      setState((current) => ({
        ...current,
        isSubmitting: false,
        errorMessage: getApiErrorMessage(error, "Failed to delete task."),
      }));
    }
  };

  const canPrev = filters.offset > 0;
  const canNext = filters.offset + filters.limit < state.total;

  return (
    <section className="page-grid">
      {canCreateOrUpdate ? (
        <div className="card">
          <div className="section-header">
            <div>
              <h2 className="section-title">Create Task</h2>
              <p className="muted">Creates a task via <code>POST /v1/tasks</code>.</p>
            </div>
          </div>

          <div className="form-grid form-grid-wide">
            <div className="field">
              <label htmlFor="task-title">Title</label>
              <input
                id="task-title"
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="Short task title"
              />
            </div>

            <div className="field">
              <label htmlFor="task-status">Status</label>
              <select
                id="task-status"
                value={form.status}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    status: event.target.value as TaskStatus,
                  }))
                }
              >
                {TASK_STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>

            <div className="field field-full">
              <label htmlFor="task-description">Description</label>
              <textarea
                id="task-description"
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({ ...current, description: event.target.value }))
                }
                rows={3}
                placeholder="Optional details for operators"
              />
            </div>

            <div className="field">
              <label htmlFor="task-assignee">Assignee</label>
              <select
                id="task-assignee"
                value={form.assignee_user_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    assignee_user_id: event.target.value,
                  }))
                }
                disabled={!canLoadUsers}
                title={canLoadUsers ? undefined : "User list endpoint is admin-only"}
              >
                <option value="">Unassigned</option>
                {assigneeOptions.map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.full_name} ({candidate.username})
                  </option>
                ))}
              </select>
            </div>

            <div className="actions-inline">
              <button
                type="button"
                className="button button-primary"
                onClick={() => void onCreateTask()}
                disabled={!form.title.trim() || state.isSubmitting}
              >
                {state.isSubmitting ? "Saving..." : "Create Task"}
              </button>
              <button
                type="button"
                className="button button-secondary"
                onClick={() => setForm(DEFAULT_FORM)}
                disabled={state.isSubmitting}
              >
                Clear
              </button>
            </div>
          </div>

          {assigneeLoadError ? <p className="muted">{assigneeLoadError}</p> : null}
        </div>
      ) : (
        <div className="card">
          <p className="muted">
            Current role ({user?.role ?? "unknown"}) is read-only for tasks creation/update.
          </p>
        </div>
      )}

      <div className="card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Tasks</h2>
            <p className="muted">
              Tenant-scoped list from <code>GET /v1/tasks</code> with filters and pagination.
            </p>
          </div>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => void loadTasksData(filters)}
            disabled={state.isLoading || state.isSubmitting}
          >
            Refresh
          </button>
        </div>

        <form
          className="filters-grid"
          onSubmit={(event) => {
            event.preventDefault();
            setFilters((current) => ({
              ...current,
              search: draftSearch.trim(),
              offset: 0,
            }));
          }}
        >
          <div className="field">
            <label htmlFor="tasks-search">Search</label>
            <input
              id="tasks-search"
              value={draftSearch}
              onChange={(event) => setDraftSearch(event.target.value)}
              placeholder="title / description"
            />
          </div>

          <div className="field">
            <label htmlFor="tasks-status-filter">Status</label>
            <select
              id="tasks-status-filter"
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  status: event.target.value as TaskFilters["status"],
                  offset: 0,
                }))
              }
            >
              <option value="">All</option>
              {TASK_STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="tasks-assignee-filter">Assignee</label>
            <select
              id="tasks-assignee-filter"
              value={filters.assignee_user_id}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  assignee_user_id: event.target.value,
                  offset: 0,
                }))
              }
              disabled={!assigneeOptions.length}
            >
              <option value="">All</option>
              {assigneeOptions.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.username}
                </option>
              ))}
            </select>
          </div>

          <div className="actions-inline">
            <button type="submit" className="button button-primary" disabled={state.isLoading}>
              Apply Filters
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={() => {
                setDraftSearch("");
                setFilters(DEFAULT_FILTERS);
              }}
              disabled={state.isLoading}
            >
              Reset
            </button>
          </div>
        </form>

        {state.errorMessage ? <div className="error-box">{state.errorMessage}</div> : null}
        {state.successMessage ? <div className="success-box">{state.successMessage}</div> : null}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((task) => (
                <tr key={task.id}>
                  <td>
                    <div className="cell-stack">
                      <span className="cell-main">{task.title}</span>
                      <span className="cell-sub">{task.description || "No description"}</span>
                      <span className="cell-sub">
                        {task.id} · org: {task.org_id}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="cell-stack">
                      <span className={`status-pill ${statusClass(task.status)}`}>{task.status}</span>
                      {canCreateOrUpdate ? (
                        <select
                          className="table-select"
                          value={task.status}
                          onChange={(event) =>
                            void onUpdateTaskStatus(task.id, event.target.value as TaskStatus)
                          }
                          disabled={state.isSubmitting}
                        >
                          {TASK_STATUS_OPTIONS.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                      ) : null}
                    </div>
                  </td>
                  <td>
                    {canLoadUsers ? (
                      <select
                        className="table-select"
                        value={task.assignee_user_id ?? ""}
                        onChange={(event) => void onReassignTask(task.id, event.target.value)}
                        disabled={state.isSubmitting}
                      >
                        <option value="">Unassigned</option>
                        {assigneeOptions.map((candidate) => (
                          <option key={candidate.id} value={candidate.id}>
                            {candidate.username}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span>{task.assignee_user_id ?? "unassigned"}</span>
                    )}
                  </td>
                  <td>{formatDate(task.created_at)}</td>
                  <td>
                    <div className="row-actions">
                      {canDelete ? (
                        <button
                          type="button"
                          className="button button-danger"
                          onClick={() => void onDeleteTask(task.id)}
                          disabled={state.isSubmitting}
                        >
                          Delete
                        </button>
                      ) : (
                        <span className="muted">read-only</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {!state.items.length && !state.isLoading ? (
                <tr>
                  <td colSpan={5}>
                    <p className="muted table-empty">No tasks found.</p>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="pager-row">
          <p className="muted">
            Showing {state.items.length ? filters.offset + 1 : 0}-{filters.offset + state.items.length} of{" "}
            {state.total}
          </p>
          <div className="pager-actions">
            <button
              type="button"
              className="button button-secondary"
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  offset: Math.max(0, current.offset - current.limit),
                }))
              }
              disabled={!canPrev || state.isLoading || state.isSubmitting}
            >
              Previous
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  offset: current.offset + current.limit,
                }))
              }
              disabled={!canNext || state.isLoading || state.isSubmitting}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

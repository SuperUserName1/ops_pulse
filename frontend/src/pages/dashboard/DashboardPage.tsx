import { useEffect, useState } from "react";

import { getDashboardSummary } from "@/api/dashboard";
import { getHealth } from "@/api/health";
import { getApiErrorMessage } from "@/shared/lib/api-error";
import type { DashboardSummaryResponse } from "@/shared/types/dashboard";
import type { HealthResponse } from "@/shared/types/health";

type DashboardState = {
  summary: DashboardSummaryResponse | null;
  health: HealthResponse | null;
  isLoading: boolean;
  errorMessage: string | null;
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

export function DashboardPage() {
  const [state, setState] = useState<DashboardState>({
    summary: null,
    health: null,
    isLoading: true,
    errorMessage: null,
  });

  const loadDashboard = async () => {
    setState((current) => ({ ...current, isLoading: true, errorMessage: null }));

    try {
      const [summary, health] = await Promise.all([getDashboardSummary(), getHealth()]);
      setState({
        summary,
        health,
        isLoading: false,
        errorMessage: null,
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        isLoading: false,
        errorMessage: getApiErrorMessage(error, "Failed to load dashboard."),
      }));
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, []);

  const summary = state.summary;
  const health = state.health;

  return (
    <section className="page-grid">
      <div className="card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Dashboard</h2>
            <p className="muted">
              Aggregated tenant metrics from <code>GET /v1/dashboard/summary</code>
            </p>
          </div>
          <button type="button" className="button button-secondary" onClick={() => void loadDashboard()}>
            Refresh
          </button>
        </div>

        {state.errorMessage ? <div className="error-box">{state.errorMessage}</div> : null}

        <div className="stats-grid">
          <article className="stat-card">
            <p className="stat-label">Total tasks</p>
            <p className="stat-value">{summary?.total_tasks ?? "—"}</p>
          </article>
          <article className="stat-card">
            <p className="stat-label">Open</p>
            <p className="stat-value">{summary?.counts.open ?? "—"}</p>
          </article>
          <article className="stat-card">
            <p className="stat-label">In progress</p>
            <p className="stat-value">{summary?.counts.in_progress ?? "—"}</p>
          </article>
          <article className="stat-card">
            <p className="stat-label">Blocked</p>
            <p className="stat-value">{summary?.counts.blocked ?? "—"}</p>
          </article>
          <article className="stat-card">
            <p className="stat-label">Done</p>
            <p className="stat-value">{summary?.counts.done ?? "—"}</p>
          </article>
          <article className="stat-card">
            <p className="stat-label">Org</p>
            <p className="stat-value stat-value-small">{summary?.org_id ?? "—"}</p>
          </article>
        </div>

        {state.isLoading && !summary ? <p className="muted">Loading dashboard metrics...</p> : null}
      </div>

      <div className="card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Backend Health</h2>
            <p className="muted">
              Live check from <code>GET /v1/health</code>
            </p>
          </div>
        </div>

        {health ? (
          <dl className="info-grid compact">
            <div className="info-item">
              <dt>Status</dt>
              <dd>
                <span className={`status-pill ${health.status === "ok" ? "is-done" : "is-blocked"}`}>
                  {health.status}
                </span>
              </dd>
            </div>
            <div className="info-item">
              <dt>Service</dt>
              <dd>{health.service}</dd>
            </div>
            <div className="info-item">
              <dt>Version</dt>
              <dd>{health.version}</dd>
            </div>
            <div className="info-item">
              <dt>Environment</dt>
              <dd>{health.environment}</dd>
            </div>
            <div className="info-item">
              <dt>Request ID</dt>
              <dd>{health.request_id}</dd>
            </div>
            <div className="info-item">
              <dt>Timestamp</dt>
              <dd>{formatDate(health.timestamp)}</dd>
            </div>
          </dl>
        ) : (
          <p className="muted">Health data not loaded yet.</p>
        )}
      </div>

      <div className="card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Recent Tasks</h2>
            <p className="muted">Latest tenant tasks returned by dashboard summary.</p>
          </div>
        </div>
        {summary?.recent_tasks.length ? (
          <div className="list-stack">
            {summary.recent_tasks.map((task) => (
              <article key={task.id} className="list-row">
                <div>
                  <p className="row-title">{task.title}</p>
                  <p className="muted row-meta">
                    {task.id} · assignee: {task.assignee_user_id ?? "unassigned"} ·{" "}
                    {formatDate(task.created_at)}
                  </p>
                </div>
                <span className={`status-pill ${statusClass(task.status)}`}>{task.status}</span>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">No tasks yet. Create the first task on the Tasks page.</p>
        )}
      </div>
    </section>
  );
}

function statusClass(status: string): string {
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

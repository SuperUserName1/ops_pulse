import { useEffect, useState } from "react";

import { listUsers } from "@/api/auth";
import { getApiErrorMessage } from "@/shared/lib/api-error";
import type { User, UsersListResponse } from "@/shared/types/auth";

type UsersPageState = {
  data: UsersListResponse | null;
  isLoading: boolean;
  errorMessage: string | null;
};

type UserFilters = {
  search: string;
  status: "" | "active" | "disabled";
  limit: number;
  offset: number;
};

const DEFAULT_FILTERS: UserFilters = {
  search: "",
  status: "",
  limit: 20,
  offset: 0,
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

export function UsersPage() {
  const [filters, setFilters] = useState<UserFilters>(DEFAULT_FILTERS);
  const [draftSearch, setDraftSearch] = useState("");
  const [state, setState] = useState<UsersPageState>({
    data: null,
    isLoading: true,
    errorMessage: null,
  });

  const loadUsers = async (nextFilters: UserFilters) => {
    setState((current) => ({ ...current, isLoading: true, errorMessage: null }));
    try {
      const payload = await listUsers({
        limit: nextFilters.limit,
        offset: nextFilters.offset,
        search: nextFilters.search || undefined,
        status: nextFilters.status || undefined,
      });
      setState({ data: payload, isLoading: false, errorMessage: null });
    } catch (error) {
      setState((current) => ({
        ...current,
        isLoading: false,
        errorMessage: getApiErrorMessage(error, "Failed to load users."),
      }));
    }
  };

  useEffect(() => {
    void loadUsers(filters);
  }, [filters]);

  const rows = state.data?.items ?? [];
  const total = state.data?.total ?? 0;
  const canPrev = filters.offset > 0;
  const canNext = filters.offset + filters.limit < total;

  return (
    <section className="page-grid">
      <div className="card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Users</h2>
            <p className="muted">
              Admin user directory from <code>GET /v1/auth/users</code>
            </p>
          </div>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => void loadUsers(filters)}
            disabled={state.isLoading}
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
            <label htmlFor="users-search">Search</label>
            <input
              id="users-search"
              value={draftSearch}
              onChange={(event) => setDraftSearch(event.target.value)}
              placeholder="username / full name"
            />
          </div>

          <div className="field">
            <label htmlFor="users-status">Status</label>
            <select
              id="users-status"
              value={filters.status}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  status: event.target.value as UserFilters["status"],
                  offset: 0,
                }))
              }
            >
              <option value="">All</option>
              <option value="active">active</option>
              <option value="disabled">disabled</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="users-limit">Page size</label>
            <select
              id="users-limit"
              value={filters.limit}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  limit: Number(event.target.value),
                  offset: 0,
                }))
              }
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
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

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Org</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((user) => (
                <UserRow key={user.id} user={user} />
              ))}
              {!rows.length && !state.isLoading ? (
                <tr>
                  <td colSpan={5}>
                    <p className="muted table-empty">No users matched the current filters.</p>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="pager-row">
          <p className="muted">
            Showing {rows.length ? filters.offset + 1 : 0}-{filters.offset + rows.length} of {total}
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
              disabled={!canPrev || state.isLoading}
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
              disabled={!canNext || state.isLoading}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function UserRow({ user }: { user: User }) {
  return (
    <tr>
      <td>
        <div className="cell-stack">
          <span className="cell-main">{user.full_name}</span>
          <span className="cell-sub">
            {user.username} · {user.id}
          </span>
        </div>
      </td>
      <td>{user.role}</td>
      <td>
        <span className={`status-pill ${user.status === "active" ? "is-done" : "is-blocked"}`}>
          {user.status}
        </span>
      </td>
      <td>{user.org_id}</td>
      <td>{formatDate(user.created_at)}</td>
    </tr>
  );
}

import {
  Navigate,
  NavLink,
  Outlet,
  RouterProvider,
  createBrowserRouter,
  useLocation,
  useNavigate,
} from "react-router-dom";

import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import { LoginPage } from "@/pages/login/LoginPage";
import { ProfilePage } from "@/pages/profile/ProfilePage";
import { TasksPage } from "@/pages/tasks/TasksPage";
import { UsersPage } from "@/pages/users/UsersPage";
import { useAuthStore } from "@/features/auth/model/auth-store";

function ProtectedRoute() {
  const location = useLocation();
  const authStatus = useAuthStore((state) => state.authStatus);
  const isBootstrapping = useAuthStore((state) => state.isBootstrapping);

  if (isBootstrapping) {
    return (
      <div className="screen-shell">
        <div className="panel">
          <p className="muted">Loading session...</p>
        </div>
      </div>
    );
  }

  if (authStatus !== "authenticated") {
    return <Navigate replace to="/login" state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

function AppLayout() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-block">
          <span className="brand-kicker">Ops Pulse</span>
          <h1>Control Panel</h1>
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          <NavLink className={navLinkClassName} to="/app/dashboard">
            Dashboard
          </NavLink>
          <NavLink className={navLinkClassName} to="/app/tasks">
            Tasks
          </NavLink>
          {user?.role === "admin" ? (
            <NavLink className={navLinkClassName} to="/app/users">
              Users
            </NavLink>
          ) : null}
          <NavLink className={navLinkClassName} to="/app/profile">
            Profile
          </NavLink>
        </nav>
      </aside>
      <main className="app-main">
        <header className="app-header">
          <div>
            <p className="header-title">Workspace</p>
            <p className="muted">
              {user?.full_name} · {user?.role} · {user?.org_id}
            </p>
          </div>
          <button type="button" className="button button-secondary" onClick={onLogout}>
            Logout
          </button>
        </header>
        <Outlet />
      </main>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate replace to="/app/dashboard" />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/app",
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <Navigate replace to="dashboard" />,
          },
          {
            path: "dashboard",
            element: <DashboardPage />,
          },
          {
            path: "tasks",
            element: <TasksPage />,
          },
          {
            path: "users",
            element: <UsersPage />,
          },
          {
            path: "profile",
            element: <ProfilePage />,
          },
        ],
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

function navLinkClassName({ isActive }: { isActive: boolean }) {
  return isActive ? "nav-link is-active" : "nav-link";
}

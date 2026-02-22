import { useAuthStore } from "@/features/auth/model/auth-store";

export function ProfilePage() {
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return (
      <section className="card">
        <p className="muted">No user context.</p>
      </section>
    );
  }

  return (
    <section className="card" aria-label="Current user profile">
      <h2 style={{ marginTop: 0, marginBottom: "0.25rem" }}>Profile</h2>
      <p className="muted" style={{ marginBottom: "1rem" }}>
        Current authenticated user context from <code>GET /v1/auth/me</code>.
      </p>
      <dl className="profile-grid">
        <div className="profile-item">
          <dt>ID</dt>
          <dd>{user.id}</dd>
        </div>
        <div className="profile-item">
          <dt>Organization</dt>
          <dd>{user.org_id}</dd>
        </div>
        <div className="profile-item">
          <dt>Username</dt>
          <dd>{user.username}</dd>
        </div>
        <div className="profile-item">
          <dt>Full name</dt>
          <dd>{user.full_name}</dd>
        </div>
        <div className="profile-item">
          <dt>Role</dt>
          <dd>{user.role}</dd>
        </div>
        <div className="profile-item">
          <dt>Status</dt>
          <dd>{user.status}</dd>
        </div>
        <div className="profile-item">
          <dt>Created at</dt>
          <dd>{new Date(user.created_at).toLocaleString()}</dd>
        </div>
      </dl>
    </section>
  );
}

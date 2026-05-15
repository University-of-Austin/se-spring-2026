import { Link, useLocation } from 'react-router-dom';

export function NotFoundPage() {
  const { pathname } = useLocation();
  return (
    <>
      <div className="page-header"><h1>Not found</h1></div>
      <div className="empty-state">
        Nothing lives at <code>{pathname}</code>.
        <div style={{ marginTop: 'var(--space-3)' }}>
          <Link to="/" className="btn btn--ghost btn--sm">Back to feed</Link>
        </div>
      </div>
    </>
  );
}

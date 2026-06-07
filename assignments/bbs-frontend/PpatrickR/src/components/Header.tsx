import { Link, NavLink } from "react-router-dom";

const TABS = [
  { to: "/", label: "Feed", end: true },
  { to: "/compose", label: "Compose", end: false },
  { to: "/users", label: "Users", end: false },
];

export function Header({
  username,
  onSignOut,
}: {
  username: string | null;
  onSignOut: () => void;
}) {
  return (
    <header className="app-header">
      <Link to="/" className="brand" aria-label="BBS home">
        BBS
      </Link>
      <nav className="tabs" aria-label="Primary">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) => "tab" + (isActive ? " active" : "")}
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <div className="who">
        {username ? (
          <>
            <Link to={`/users/${encodeURIComponent(username)}`} className="link-btn">
              @{username}
            </Link>
            <button type="button" className="link-btn muted" onClick={onSignOut}>
              switch
            </button>
          </>
        ) : (
          <Link to="/signin" className="link-btn">
            sign in
          </Link>
        )}
      </div>
    </header>
  );
}

import { useEffect } from "react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { useCurrentUser } from "./hooks/useCurrentUser";
import { SignInView } from "./views/SignInView";
import { FeedView } from "./views/FeedView";
import { ComposeView } from "./views/ComposeView";
import { UserListView } from "./views/UserListView";
import { UserProfileView } from "./views/UserProfileView";
import { PostDetailView } from "./views/PostDetailView";
import "./App.css";

function RequireUser({
  username,
  children,
}: {
  username: string | null;
  children: React.ReactNode;
}) {
  const location = useLocation();
  if (!username) {
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

function UserProfileRoute() {
  const { username = "" } = useParams<{ username: string }>();
  return <UserProfileView username={username} />;
}

function PostDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const parsed = Number(id);
  if (!id || !Number.isFinite(parsed) || parsed <= 0) {
    return (
      <section className="view">
        <h1>Bad post URL</h1>
        <p className="muted">
          "{id}" isn't a valid post id.
        </p>
      </section>
    );
  }
  return <PostDetailView id={parsed} />;
}

function ComposeRoute({ username }: { username: string }) {
  return <ComposeView username={username} />;
}

function SignInRoute({
  username,
  onSignedIn,
}: {
  username: string | null;
  onSignedIn: (u: string) => void;
}) {
  if (username) return <Navigate to="/" replace />;
  return <SignInView onSignedIn={onSignedIn} />;
}

export default function App() {
  const { username, setUsername, clear } = useCurrentUser();
  const navigate = useNavigate();

  function handleSignOut() {
    clear();
    navigate("/signin");
  }

  useGlobalKeyboardShortcuts(navigate);

  return (
    <div className="app">
      <Header username={username} onSignOut={handleSignOut} />
      <main className="content">
        <Routes>
          <Route
            path="/"
            element={
              <RequireUser username={username}>
                <FeedView currentUser={username ?? ""} />
              </RequireUser>
            }
          />
          <Route
            path="/compose"
            element={
              <RequireUser username={username}>
                <ComposeRoute username={username ?? ""} />
              </RequireUser>
            }
          />
          <Route
            path="/users"
            element={
              <RequireUser username={username}>
                <UserListView />
              </RequireUser>
            }
          />
          <Route
            path="/users/:username"
            element={
              <RequireUser username={username}>
                <UserProfileRoute />
              </RequireUser>
            }
          />
          <Route
            path="/posts/:id"
            element={
              <RequireUser username={username}>
                <PostDetailRoute />
              </RequireUser>
            }
          />
          <Route
            path="/signin"
            element={
              <SignInRoute username={username} onSignedIn={setUsername} />
            }
          />
          <Route
            path="*"
            element={
              <section className="view">
                <h1>Not found</h1>
                <p className="muted">No page at this URL.</p>
              </section>
            }
          />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

function useGlobalKeyboardShortcuts(navigate: (to: string) => void) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      const isTyping =
        tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === "/" && !isTyping) {
        const search = document.getElementById("feed-search");
        if (search) {
          e.preventDefault();
          (search as HTMLInputElement).focus();
        }
        return;
      }
      if (e.key === "n" && !isTyping) {
        e.preventDefault();
        navigate("/compose");
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);
}

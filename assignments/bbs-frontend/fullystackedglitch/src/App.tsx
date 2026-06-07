import { Link, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { FeedView } from "./views/FeedView";
import { PostDetailView } from "./views/PostDetailView";
import { SignupView } from "./views/SignupView";
import { UserListView } from "./views/UserListView";
import { UserProfileView } from "./views/UserProfileView";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<FeedView />} />
        <Route path="users" element={<UserListView />} />
        <Route path="users/:username" element={<UserProfileView />} />
        <Route path="posts/:id" element={<PostDetailView />} />
        <Route path="signup" element={<SignupView />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

function NotFound() {
  return (
    <section style={{ textAlign: "center", padding: 32 }}>
      <h1>404</h1>
      <p>nothing here.</p>
      <Link to="/">back to feed</Link>
    </section>
  );
}

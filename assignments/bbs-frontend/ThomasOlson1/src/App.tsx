import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ToastProvider } from "./components/Toast";
import { Layout } from "./components/Layout";
import { FeedPage } from "./pages/FeedPage";
import { UserListPage } from "./pages/UserListPage";
import { UserProfilePage } from "./pages/UserProfilePage";
import { PostDetailPage } from "./pages/PostDetailPage";
import { SignUpPage } from "./pages/SignUpPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<FeedPage />} />
              <Route path="users" element={<UserListPage />} />
              <Route path="users/:username" element={<UserProfilePage />} />
              <Route path="posts/:id" element={<PostDetailPage />} />
              <Route path="signup" element={<SignUpPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

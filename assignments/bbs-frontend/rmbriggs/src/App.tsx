import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";
import NotFound from "@/pages/NotFound";
import LoginPage from "@/pages/LoginPage";
import FeedPage from "@/pages/FeedPage";
import { UserProvider } from "@/hooks/useCurrentUser";
import UsersPage from "@/pages/UsersPage";
import UserPage from "@/pages/UserPage";
import PostPage from "@/pages/PostPage";
import BoardsPage from "@/pages/BoardsPage";
import BoardPage from "@/pages/BoardPage";

export default function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<FeedPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/users/:username" element={<UserPage />} />
            <Route path="/posts/:id" element={<PostPage />} />
            <Route path="/boards" element={<BoardsPage />} />
            <Route path="/boards/:name" element={<BoardPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserProvider>
  );
}

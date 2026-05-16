import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./index.css";
import { AuthProvider } from "./auth";
import { Layout } from "./components/Layout";
import { Feed } from "./pages/Feed";
import { Users } from "./pages/Users";
import { Profile } from "./pages/Profile";
import { PostDetail } from "./pages/PostDetail";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { Boards } from "./pages/Boards";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Feed /> },
      { path: "users", element: <Users /> },
      { path: "users/:username", element: <Profile /> },
      { path: "boards", element: <Boards /> },
      { path: "posts/:id", element: <PostDetail /> },
      { path: "login", element: <Login /> },
      { path: "signup", element: <Signup /> },
      {
        path: "*",
        element: (
          <div className="page page-notfound">
            <h1>404</h1>
            <p>That page doesn't exist.</p>
          </div>
        ),
      },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);

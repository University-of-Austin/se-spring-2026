import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingDots } from "./components/LoadingDots";
import { ToastProvider } from "./hooks/useToast";

// Code-split each page — keeps the initial bundle small.
const FeedPage = lazy(() => import("./pages/FeedPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const UserProfilePage = lazy(() => import("./pages/UserProfilePage"));
const PostDetailPage = lazy(() => import("./pages/PostDetailPage"));
const SignInPage = lazy(() => import("./pages/SignInPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route
              path="/"
              element={
                <Suspense fallback={<LoadingDots />}>
                  <FeedPage />
                </Suspense>
              }
            />
            <Route
              path="/users"
              element={
                <Suspense fallback={<LoadingDots />}>
                  <UsersPage />
                </Suspense>
              }
            />
            <Route
              path="/users/:username"
              element={
                <Suspense fallback={<LoadingDots />}>
                  <UserProfilePage />
                </Suspense>
              }
            />
            <Route
              path="/posts/:id"
              element={
                <Suspense fallback={<LoadingDots />}>
                  <PostDetailPage />
                </Suspense>
              }
            />
            <Route
              path="/sign-in"
              element={
                <Suspense fallback={<LoadingDots />}>
                  <SignInPage />
                </Suspense>
              }
            />
            <Route
              path="*"
              element={
                <Suspense fallback={<LoadingDots />}>
                  <NotFoundPage />
                </Suspense>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}

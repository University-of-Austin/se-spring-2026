import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { UsernameProvider } from "./hooks/useUsername";
import { Compose } from "./pages/Compose/Compose";
import { Feed } from "./pages/Feed/Feed";
import { NotFound } from "./pages/NotFound/NotFound";
import { PostDetail } from "./pages/PostDetail/PostDetail";
import { SignIn } from "./pages/SignIn/SignIn";
import { UserList } from "./pages/UserList/UserList";
import { UserProfile } from "./pages/UserProfile/UserProfile";

// One QueryClient shared by the whole app. Defaults kept tame:
// retry once on network failure, don't refetch on every window focus.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <UsernameProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Feed />} />
              <Route path="/users" element={<UserList />} />
              <Route path="/users/:username" element={<UserProfile />} />
              <Route path="/posts/:id" element={<PostDetail />} />
              <Route path="/compose" element={<Compose />} />
              <Route path="/signin" element={<SignIn />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </UsernameProvider>
    </QueryClientProvider>
  );
}

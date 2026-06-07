import { Route, Routes } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { UserProvider } from './context/UserContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmProvider } from './context/ConfirmContext';
import { Layout } from './components/Layout';
import { FeedPage } from './pages/FeedPage';
import { UserListPage } from './pages/UserListPage';
import { UserProfilePage } from './pages/UserProfilePage';
import { PostDetailPage } from './pages/PostDetailPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';

export default function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <ToastProvider>
          <ConfirmProvider>
            <Routes>
              <Route element={<Layout />}>
                <Route path="/" element={<FeedPage />} />
                <Route path="/users" element={<UserListPage />} />
                <Route path="/users/:username" element={<UserProfilePage />} />
                <Route path="/posts/:id" element={<PostDetailPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </ConfirmProvider>
        </ToastProvider>
      </UserProvider>
    </ThemeProvider>
  );
}

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { IdentityProvider } from './identity/IdentityContext';
import { ThemeProvider } from './theme/ThemeContext';
import { ToastProvider } from './hooks/useToast';
import { AppShell } from './components/AppShell';
import FeedPage from './pages/FeedPage';
import ComposePage from './pages/ComposePage';
import UsersPage from './pages/UsersPage';
import UserProfilePage from './pages/UserProfilePage';
import PostDetailPage from './pages/PostDetailPage';
import SignupPage from './pages/SignupPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <ThemeProvider>
      <IdentityProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="/" element={<FeedPage />} />
                <Route path="/compose" element={<ComposePage />} />
                <Route path="/users" element={<UsersPage />} />
                <Route path="/users/:username" element={<UserProfilePage />} />
                <Route path="/posts/:id" element={<PostDetailPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/404" element={<NotFoundPage />} />
                <Route path="*" element={<Navigate to="/404" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </IdentityProvider>
    </ThemeProvider>
  );
}

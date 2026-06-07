import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/queryClient'
import { IdentityProvider } from './auth/IdentityContext'
import { AppShell } from './components/layout/AppShell'
import FeedPage from './pages/FeedPage'
import UsersPage from './pages/UsersPage'
import UserProfilePage from './pages/UserProfilePage'
import PostDetailPage from './pages/PostDetailPage'
import SignUpPage from './pages/SignUpPage'
import NotFoundPage from './pages/NotFoundPage'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider>
        <BrowserRouter>
          <AppShell>
            <Routes>
              <Route path="/" element={<FeedPage />} />
              <Route path="/users" element={<UsersPage />} />
              <Route path="/users/:username" element={<UserProfilePage />} />
              <Route path="/posts/:id" element={<PostDetailPage />} />
              <Route path="/signup" element={<SignUpPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AppShell>
        </BrowserRouter>
      </IdentityProvider>
    </QueryClientProvider>
  )
}

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { FeedOptimisticProvider } from './context/FeedOptimisticContext'
import { Layout } from './components/Layout'
import { AccountPage } from './pages/AccountPage'
import { ComposePage } from './pages/ComposePage'
import { FeedPage } from './pages/FeedPage'
import { PostDetailPage } from './pages/PostDetailPage'
import { UserProfilePage } from './pages/UserProfilePage'
import { UsersPage } from './pages/UsersPage'

export default function App() {
  return (
    <BrowserRouter>
      <FeedOptimisticProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<FeedPage />} />
            <Route path="compose" element={<ComposePage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="users/:username" element={<UserProfilePage />} />
            <Route path="posts/:id" element={<PostDetailPage />} />
            <Route path="account" element={<AccountPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </FeedOptimisticProvider>
    </BrowserRouter>
  )
}

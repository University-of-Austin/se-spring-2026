import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { Layout } from './components/Layout'
import { FeedPage } from './pages/FeedPage'
import { ComposePage } from './pages/ComposePage'
import { UsersPage } from './pages/UsersPage'
import { UserProfilePage } from './pages/UserProfilePage'
import { PostDetailPage } from './pages/PostDetailPage'
import { AuthPage } from './pages/AuthPage'
import { NotFoundPage } from './pages/NotFoundPage'

// Real client-side routing: bookmarkable URLs, refresh-safe, correct back button.
const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <FeedPage /> },
      { path: 'compose', element: <ComposePage /> },
      { path: 'users', element: <UsersPage /> },
      { path: 'users/:username', element: <UserProfilePage /> },
      { path: 'posts/:id', element: <PostDetailPage /> },
      { path: 'login', element: <AuthPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}

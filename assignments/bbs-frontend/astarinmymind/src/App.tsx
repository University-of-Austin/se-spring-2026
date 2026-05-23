// Top-level wiring: router → identity provider → routes → Layout shell → page.
// Order matters here: Layout reads username via useCurrentUser(), so UserProvider
// must wrap Layout. BrowserRouter has to be outermost so useNavigate/Link work.

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { UserProvider } from './context/UserContext'
import { ThemeProvider } from './context/ThemeContext'
import { Layout } from './components/Layout'

import FeedPage from './pages/FeedPage'
import UserListPage from './pages/UserListPage'
import UserProfilePage from './pages/UserProfilePage'
import PostDetailPage from './pages/PostDetailPage'
import SignInPage from './pages/SignInPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <UserProvider>
          <Routes>
          {/* Layout route: this <Route> has no `path`, just an `element`. It wraps
              all the child routes below, so every page renders inside <Layout>. */}
          <Route element={<Layout />}>
            <Route path="/" element={<FeedPage />} />
            <Route path="/users" element={<UserListPage />} />
            <Route path="/users/:username" element={<UserProfilePage />} />
            <Route path="/posts/:id" element={<PostDetailPage />} />
            <Route path="/signin" element={<SignInPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
          </Routes>
        </UserProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App

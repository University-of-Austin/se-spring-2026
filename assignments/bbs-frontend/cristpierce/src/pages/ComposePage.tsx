import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../lib/api'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import { Composer } from '../components/Composer'
import { BackLink, PageHeader } from '../components/PageBits'

export function ComposePage() {
  const { username, isLoggedIn } = useIdentity()
  const navigate = useNavigate()
  const toast = useToast()

  async function handlePost(message: string) {
    if (!username) throw new ApiError({ status: 0, message: 'Choose a username first.' })
    await api.createPost(username, message) // rejects -> Composer shows it inline
    toast.success('Posted.')
    navigate('/')
  }

  return (
    <div>
      <BackLink to="/">Back to feed</BackLink>
      <PageHeader
        title="Compose"
        subtitle={isLoggedIn ? `Posting as @${username}` : 'Choose a username to start posting'}
      />
      <Composer onPost={handlePost} autoFocus />
    </div>
  )
}

import { useAuth } from '../context/AuthContext'

export default function AdminGuard({ children, roles = ['admin'] }) {
  const { user } = useAuth()
  const allowed = roles.includes(user?.role)

  if (!allowed) {
    window.location.href = user?.role === 'cicli' ? '/cicli' : '/'
    return null
  }

  return children
}

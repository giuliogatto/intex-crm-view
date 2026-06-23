import { useAuth } from '../context/AuthContext'

export default function AdminGuard({ children }) {
  const { user } = useAuth()

  if (user?.role !== 'admin') {
    window.location.href = '/'
    return null
  }

  return children
}

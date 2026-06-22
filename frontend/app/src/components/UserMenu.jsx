import React from 'react'
import { useAuth } from '../context/AuthContext'

export default function UserMenu() {
  const { user, logout } = useAuth()

  if (!user?.username) return null

  return (
    <div className="user-menu">
      <button type="button" className="user-menu__trigger" aria-haspopup="true">
        {user.username}
      </button>
      <div className="user-menu__panel" role="menu">
        <button type="button" className="user-menu__logout" onClick={logout} role="menuitem">
          Esci
        </button>
      </div>
    </div>
  )
}

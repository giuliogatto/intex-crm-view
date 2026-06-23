const ADMIN_PAGES = [
  { href: '/chats', label: '💬 Chats' },
  { href: '/users', label: '👤 Utenti' },
]

export default function AdminNav() {
  const pathname = window.location.pathname

  return (
    <nav className="admin-nav" aria-label="Amministrazione">
      {ADMIN_PAGES.map((page) => (
        <a
          key={page.href}
          href={page.href}
          className={`btn${pathname === page.href ? ' is-active' : ''}`}
        >
          {page.label}
        </a>
      ))}
    </nav>
  )
}

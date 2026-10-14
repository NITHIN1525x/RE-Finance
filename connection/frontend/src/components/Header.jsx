export default function Header({ username, onSignOut, view = 'console' }) {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-title">
          <h1>QBO Connection Console</h1>
          <span className="badge badge-sandbox" title="All QuickBooks calls go to the sandbox API only">
            SANDBOX
          </span>
        </div>
        <nav className="header-nav" aria-label="Main">
          <a href="#" className="nav-link" aria-current={view === 'console' ? 'page' : undefined}>
            Connections
          </a>
          <a href="#results" className="nav-link" aria-current={view === 'results' ? 'page' : undefined}>
            Results
          </a>
        </nav>
        {onSignOut && (
          <div className="header-user">
            <span className="muted">
              Signed in as <strong>{username}</strong>
            </span>
            <button type="button" className="button button-quiet" onClick={onSignOut}>
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

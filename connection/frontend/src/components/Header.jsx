export default function Header({ username, onSignOut }) {
  return (
    <header className="header">
      <div className="header-title">
        <h1>QBO Connection Console</h1>
        <span className="badge badge-sandbox" title="All QuickBooks calls go to the sandbox API only">
          SANDBOX
        </span>
      </div>
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
    </header>
  )
}

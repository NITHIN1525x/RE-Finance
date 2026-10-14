import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import { callbackMessage } from './format.js'
import AuditLog from './components/AuditLog.jsx'
import ClientList from './components/ClientList.jsx'
import Header from './components/Header.jsx'
import Notice from './components/Notice.jsx'
import Results from './components/Results.jsx'
import SignIn from './components/SignIn.jsx'
import './App.css'
import './results/results.css'

// Read the ?qbo=…&reason=… result of the OAuth callback once, then remove it from the address bar.
function takeCallbackNotice() {
  const params = new URLSearchParams(window.location.search)
  const notice = callbackMessage(params)
  if (notice) window.history.replaceState(null, '', window.location.pathname)
  return notice
}

// "#results" or "#results/<item>" shows the saved results; anything else shows the console (no router needed).
function routeFromHash() {
  const match = /^#results(?:\/([\w-]+))?$/.exec(window.location.hash)
  return match ? { view: 'results', item: match[1] || null } : { view: 'console', item: null }
}

export default function App() {
  const [session, setSession] = useState({ state: 'loading' })
  const [notice, setNotice] = useState(takeCallbackNotice)
  const [auditVersion, setAuditVersion] = useState(0) // bump to reload the audit log after an action
  const [route, setRoute] = useState(routeFromHash)

  useEffect(() => {
    const onHashChange = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    api
      .me()
      .then((me) => setSession(me.authenticated ? { state: 'signed-in', ...me } : { state: 'signed-out' }))
      .catch((error) => setSession({ state: 'error', message: error.message }))
  }, [])

  const handleSignOut = useCallback(async () => {
    await api.logout().catch(() => {})
    setSession({ state: 'signed-out' })
  }, [])

  const handleActionDone = useCallback(() => setAuditVersion((v) => v + 1), [])

  return (
    <div className="app">
      <Header
        username={session.username}
        onSignOut={session.state === 'signed-in' ? handleSignOut : null}
        view={route.view}
      />
      {route.view === 'results' && (
        <main className="content content-wide">
          <Results selected={route.item} />
        </main>
      )}
      <main className="content" hidden={route.view !== 'console'}>
        {notice && <Notice tone={notice.tone} onDismiss={() => setNotice(null)}>{notice.text}</Notice>}

        {session.state === 'loading' && <p className="muted" role="status">Loading…</p>}
        {session.state === 'error' && <Notice tone="error">{session.message}</Notice>}
        {session.state === 'signed-out' && <SignIn />}
        {session.state === 'signed-in' && (
          <>
            {session.credentials_configured === false && (
              <Notice tone="warning">
                Intuit app credentials are not configured on the server, so connecting will fail. Add them to
                connection/.secrets/backend.env and restart Django.
              </Notice>
            )}
            <ClientList onActionDone={handleActionDone} />
            <AuditLog version={auditVersion} />
          </>
        )}
      </main>
      <footer className="footer muted">
        Sandbox only. Tokens are encrypted server-side and never sent to this page.
      </footer>
    </div>
  )
}

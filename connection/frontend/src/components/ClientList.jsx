import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import ClientCard from './ClientCard.jsx'
import Notice from './Notice.jsx'

export default function ClientList({ onActionDone }) {
  const [state, setState] = useState({ status: 'loading', clients: [] })

  const load = useCallback(() => {
    return api
      .clients()
      .then((data) => setState({ status: 'ready', clients: data.clients }))
      .catch((error) => setState({ status: 'error', clients: [], message: error.message }))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // After any action on a card: reload connection status and the audit log.
  const handleChanged = useCallback(() => {
    load()
    onActionDone()
  }, [load, onActionDone])

  return (
    <section className="panel" aria-labelledby="clients-heading" aria-busy={state.status === 'loading'}>
      <div className="panel-header">
        <h2 id="clients-heading">Client connections</h2>
        <button type="button" className="button button-quiet" onClick={load}>
          Refresh
        </button>
      </div>

      {state.status === 'loading' && <p className="muted" role="status">Loading clients…</p>}
      {state.status === 'error' && <Notice tone="error">{state.message}</Notice>}
      {state.status === 'ready' && state.clients.length === 0 && (
        <div className="empty">
          <p>No clients are assigned to you yet.</p>
          <p className="muted">
            Ask an administrator to run <code>python manage.py create_client --name … --member &lt;you&gt;</code>.
          </p>
        </div>
      )}
      {state.status === 'ready' && state.clients.length > 0 && (
        <ul className="client-list">
          {state.clients.map((client) => (
            <li key={client.slug}>
              <ClientCard client={client} onChanged={handleChanged} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

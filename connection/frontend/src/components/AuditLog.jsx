import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { formatDateTime } from '../format.js'
import Notice from './Notice.jsx'

const ACTION_LABELS = {
  oauth_start: 'OAuth started',
  oauth_callback: 'OAuth callback',
  refresh: 'Token refresh',
  test_connection: 'Test connection',
  disconnect: 'Disconnect',
  mcp_checkout: 'Checked out to MCP',
  mcp_checkout_refresh: 'Refresh for MCP checkout',
  mcp_checkin: 'Checked in from MCP',
  create_client: 'Client created',
  update_client_members: 'Members updated',
}

export default function AuditLog({ version }) {
  const [state, setState] = useState({ status: 'loading', entries: [] })
  const [reloads, setReloads] = useState(0)

  useEffect(() => {
    let cancelled = false
    api
      .audit(20)
      .then((data) => !cancelled && setState({ status: 'ready', entries: data.entries }))
      .catch((error) => !cancelled && setState({ status: 'error', entries: [], message: error.message }))
    return () => {
      cancelled = true
    }
  }, [version, reloads])

  return (
    <section className="panel" aria-labelledby="audit-heading" aria-busy={state.status === 'loading'}>
      <div className="panel-header">
        <h2 id="audit-heading">Recent activity</h2>
        <button type="button" className="button button-quiet" onClick={() => setReloads((n) => n + 1)}>
          Refresh
        </button>
      </div>
      {state.status === 'loading' && <p className="muted" role="status">Loading activity…</p>}
      {state.status === 'error' && <Notice tone="error">{state.message}</Notice>}
      {state.status === 'ready' && state.entries.length === 0 && <p className="muted">No activity yet.</p>}
      {state.status === 'ready' && state.entries.length > 0 && (
        <div className="table-scroll">
          <table className="audit">
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Client</th>
                <th scope="col">Action</th>
                <th scope="col">By</th>
                <th scope="col">Result</th>
                <th scope="col">Detail</th>
              </tr>
            </thead>
            <tbody>
              {state.entries.map((entry, i) => (
                <tr key={`${entry.timestamp}-${i}`}>
                  <td className="nowrap" data-label="When">{formatDateTime(entry.timestamp)}</td>
                  <td data-label="Client">{entry.client || '—'}</td>
                  <td data-label="Action">{ACTION_LABELS[entry.action] || entry.action}</td>
                  <td data-label="By">{entry.actor}</td>
                  <td data-label="Result">
                    <span className={`badge ${entry.success ? 'status-connected' : 'status-error'}`}>
                      {entry.success ? 'OK' : 'Failed'}
                    </span>
                  </td>
                  <td className="detail" data-label="Detail">{entry.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

import { useState } from 'react'
import { api, connectUrl } from '../api.js'
import { STATUS_LABELS, actionErrorMessage, formatDateTime, tokenExpiry } from '../format.js'
import ConfirmDialog from './ConfirmDialog.jsx'
import Notice from './Notice.jsx'
import TestResult from './TestResult.jsx'

export default function ClientCard({ client, onChanged }) {
  const [busy, setBusy] = useState(null) // 'test' | 'disconnect' | null
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)
  const [confirming, setConfirming] = useState(false)

  const expiry = tokenExpiry(client)
  const checkedOut = client.token_owner === 'mcp'
  const statusKey = client.status || 'not_connected'

  async function runTest() {
    setBusy('test')
    setError(null)
    setMessage(null)
    setResult(null)
    try {
      setResult(await api.testConnection(client.slug))
    } catch (e) {
      setError(actionErrorMessage(e))
    } finally {
      setBusy(null)
      onChanged()
    }
  }

  async function runDisconnect() {
    setConfirming(false)
    setBusy('disconnect')
    setError(null)
    setResult(null)
    try {
      const response = await api.disconnect(client.slug)
      setMessage(
        response.revoked_at_intuit
          ? 'Disconnected. Local tokens deleted and access revoked at Intuit.'
          : 'Local tokens deleted, but Intuit did not confirm the revoke. Revoke the app manually in the sandbox company.',
      )
    } catch (e) {
      setError(actionErrorMessage(e))
    } finally {
      setBusy(null)
      onChanged()
    }
  }

  return (
    <article className="card" aria-labelledby={`client-${client.slug}`}>
      <div className="card-header">
        <div>
          <h3 id={`client-${client.slug}`}>{client.name}</h3>
          <p className="muted small">
            {client.slug}
            {client.realm_hint && (
              <>
                {' · '}realm <span title="Only the first four characters are shown">{client.realm_hint}</span>
              </>
            )}
          </p>
        </div>
        <div className="badges">
          <span className="badge badge-sandbox">{(client.environment || 'sandbox').toUpperCase()}</span>
          <span className={`badge status-${statusKey}`}>{STATUS_LABELS[statusKey] || statusKey}</span>
          {checkedOut && (
            <span className="badge badge-mcp" title="The MCP server currently owns token refresh for this connection">
              Checked out to MCP
            </span>
          )}
        </div>
      </div>

      <dl className="facts">
        <div>
          <dt>Last refresh</dt>
          <dd>{formatDateTime(client.last_refreshed_at)}</dd>
        </div>
        <div>
          <dt>Token expiry</dt>
          <dd className={`tone-${expiry.tone}`}>{expiry.text}</dd>
        </div>
      </dl>

      <div className="actions">
        {!client.connected && !checkedOut && (
          <a className="button button-primary" href={connectUrl(client.slug)}>
            {statusKey === 'refresh_required' ? 'Reconnect QuickBooks' : 'Connect QuickBooks'}
          </a>
        )}
        {client.connected && (
          <>
            <button
              type="button"
              className="button button-primary"
              onClick={runTest}
              disabled={busy !== null}
              aria-label={`Test connection for ${client.name}`}
            >
              {busy === 'test' ? 'Testing…' : 'Test connection'}
            </button>
            <button
              type="button"
              className="button button-danger"
              onClick={() => setConfirming(true)}
              disabled={busy !== null}
              aria-label={`Disconnect ${client.name}`}
            >
              {busy === 'disconnect' ? 'Disconnecting…' : 'Disconnect'}
            </button>
          </>
        )}
      </div>

      {busy === 'test' && (
        <p className="muted small" role="status">
          Calling the QuickBooks sandbox API…
        </p>
      )}
      {error && <Notice tone="error" onDismiss={() => setError(null)}>{error}</Notice>}
      {message && <Notice tone="success" onDismiss={() => setMessage(null)}>{message}</Notice>}
      {result && <TestResult result={result} />}

      <ConfirmDialog
        open={confirming}
        title={`Disconnect ${client.name}?`}
        confirmLabel="Disconnect"
        onConfirm={runDisconnect}
        onCancel={() => setConfirming(false)}
      >
        This revokes the app&apos;s access at Intuit and deletes the stored tokens.
        {checkedOut && ' The MCP server is currently using this connection and will lose access too.'} You can
        reconnect later.
      </ConfirmDialog>
    </article>
  )
}

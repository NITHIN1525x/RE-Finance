// Display helpers. Pure functions, no React.

const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })
const timeOnly = new Intl.DateTimeFormat(undefined, { timeStyle: 'short' })

export function formatDateTime(value) {
  return value ? dateTime.format(new Date(value)) : '—'
}

export function formatMoney(amount, currency) {
  if (amount === undefined || amount === null) return '—'
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'USD' }).format(Number(amount))
  } catch {
    return `${amount} ${currency || ''}`.trim()
  }
}

export const STATUS_LABELS = {
  not_connected: 'Not connected',
  connected: 'Connected',
  refresh_required: 'Reconnect required',
  error: 'Error',
  disconnected: 'Disconnected',
}

// Token expiry text: { text, tone } where tone is one of ok | warn | bad | muted.
export function tokenExpiry(client) {
  if (!client.connected) {
    return client.status === 'refresh_required'
      ? { text: 'Refresh required: reconnect QuickBooks', tone: 'bad' }
      : { text: '—', tone: 'muted' }
  }
  const days = client.refresh_token_days_left
  let refreshText = 'Refresh token expiry unknown'
  let tone = 'ok'
  if (days !== null && days !== undefined) {
    if (days < 0) {
      refreshText = 'Refresh token expired: reconnect'
      tone = 'bad'
    } else {
      refreshText = `Refresh token expires in ${days} day${days === 1 ? '' : 's'}`
      tone = days < 14 ? 'warn' : 'ok'
    }
  }
  let accessText
  if (client.access_token_valid) {
    accessText = `access token valid until ${timeOnly.format(new Date(client.access_token_expires_at))}`
  } else if (client.token_owner === 'mcp') {
    accessText = 'access token expired (checked out to MCP)'
  } else {
    accessText = 'access token refreshes on next use'
  }
  return { text: `${refreshText}; ${accessText}`, tone }
}

// Fixed reason codes from the OAuth callback (backend never reflects free text).
const CALLBACK_REASONS = {
  invalid_state: 'The authorization link was invalid, reused or opened in a different session. Click Connect again.',
  state_expired: 'The authorization took longer than 10 minutes. Click Connect again.',
  unknown_client: 'That client does not exist or you do not have access to it.',
  denied: 'Authorization was cancelled at Intuit. Nothing was changed.',
  missing_params: 'Intuit returned an incomplete response. Try again.',
  not_configured: 'The Intuit app credentials are not configured on the server (connection/.secrets/backend.env).',
  checked_out: 'This connection is checked out to the MCP server. Check it in (sync_mcp_tokens) before reconnecting.',
  realm_in_use: 'That QuickBooks company is already connected to another client.',
  different_company: 'A different company is already connected to this client. Disconnect it first.',
  token_exchange_failed: 'Intuit rejected the authorization code. Check the redirect URI and app keys.',
  not_sandbox_company: 'That company is not reachable on the sandbox API, so the connection was refused and revoked.',
  verify_failed: 'Could not verify the company on the sandbox API. Nothing was saved.',
}

export function callbackMessage(params) {
  const status = params.get('qbo')
  if (!status) return null
  const client = params.get('client')
  if (status === 'connected') {
    return { tone: 'success', text: `QuickBooks sandbox connected${client ? ` for ${client}` : ''}.` }
  }
  return { tone: 'error', text: CALLBACK_REASONS[params.get('reason')] || 'Connecting to QuickBooks failed. Try again.' }
}

// Friendlier text for /test and /disconnect error codes.
export function actionErrorMessage(error) {
  const byCode = {
    checked_out: error.message, // backend message already explains the check-in step
    refresh_required: 'QuickBooks authorization expired or was revoked. Click Connect QuickBooks to re-authorize.',
    not_connected: 'This client is not connected yet.',
    invalid_client: 'Intuit rejected the app credentials. Check QUICKBOOKS_CLIENT_ID / SECRET.',
    transient: 'QuickBooks or Intuit is temporarily unavailable. Try again shortly.',
  }
  return byCode[error.code] || error.message
}

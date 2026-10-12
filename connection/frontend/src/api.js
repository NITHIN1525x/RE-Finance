// Small fetch wrapper for the Django API (same origin via the Vite proxy).
// Auth is the HttpOnly Django session cookie; nothing secret is ever stored in JS, localStorage or URLs.

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}

function csrfToken() {
  // Django's CSRF token cookie is deliberately readable by JS; it is not a credential on its own.
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

async function request(method, path, { query } = {}) {
  const url = query ? `${path}?${new URLSearchParams(query)}` : path
  const headers = { Accept: 'application/json' }
  if (method !== 'GET') headers['X-CSRFToken'] = csrfToken()

  let response
  try {
    response = await fetch(url, { method, headers, credentials: 'same-origin' })
  } catch {
    throw new ApiError(0, 'network', 'Cannot reach the backend. Is Django running on port 8000?')
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    // Non-JSON (e.g. proxy error page) is handled below.
  }
  if (!response.ok) {
    if (response.status === 403 && !body?.error) {
      throw new ApiError(403, 'forbidden', 'Your session has expired. Please sign in again.')
    }
    if (response.status === 404) {
      throw new ApiError(404, 'not_found', 'Client not found, or you do not have access to it.')
    }
    if (response.status >= 500 && !body) {
      throw new ApiError(response.status, 'backend_unavailable', 'The backend is not responding (is Django running?).')
    }
    throw new ApiError(response.status, body?.error || 'error', body?.message || `Request failed (HTTP ${response.status}).`)
  }
  return body
}

export const api = {
  me: () => request('GET', '/api/me/'),
  clients: () => request('GET', '/api/clients/'),
  audit: (limit = 20) => request('GET', '/api/audit/', { query: { limit } }),
  testConnection: (slug) => request('POST', `/api/qbo/${encodeURIComponent(slug)}/test`),
  disconnect: (slug) => request('POST', `/api/qbo/${encodeURIComponent(slug)}/disconnect`),
  logout: () =>
    fetch('/api/auth/logout/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken() },
      credentials: 'same-origin',
    }),
}

// Full-page navigations (not fetch): the browser must follow redirects to Intuit and back.
export const connectUrl = (slug) => `/api/qbo/connect?${new URLSearchParams({ client: slug })}`
export const loginUrl = '/api/auth/login/?next=/'

#!/usr/bin/env node
// Pre-flight launcher for the official QuickBooks Online MCP server (pinned submodule).
// Referenced by .mcp.json. It refuses to start unless the setup is safe, then runs the server
// in-process, so stdio passes straight through to Claude Code.
//
// Why a launcher instead of pointing .mcp.json at dist/index.js directly (DECISIONS_LOG D-09, D-24):
//  - QUICKBOOKS_TOKEN_STORE_PATH must be ABSOLUTE and machine-specific; .mcp.json stays portable.
//  - The server swallows a missing-credential error and lingers with zero tools; we exit non-zero instead.
//  - The server treats anything except exactly "sandbox" as production; we refuse it here.
//  - Its .env values override host env (dotenv override:true), so the read-only flags are checked IN THE FILE.
//  - The axios security patch (D-04) is silently reverted by `npm ci`; we refuse to run without it.
//
// Rules: never write to stdout (it is the MCP channel) and never print a credential value.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const connectionDir = path.resolve(here, '..')
const serverDir = path.join(connectionDir, 'quickbooks-online-mcp-server')
const entryPoint = path.join(serverDir, 'dist', 'index.js')
const storePath = process.env.QBO_MCP_TOKEN_STORE || path.join(connectionDir, '.secrets', 'mcp-server.env')
const READ_ONLY_FLAGS = ['QUICKBOOKS_DISABLE_WRITE', 'QUICKBOOKS_DISABLE_UPDATE', 'QUICKBOOKS_DISABLE_DELETE']
const MIN_AXIOS = [1, 20, 0]

function fail(message) {
  process.stderr.write(`[mcp_launch] REFUSING TO START: ${message}\n`)
  process.exit(1)
}

function parseEnvFile(file) {
  const values = {}
  for (const raw of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const line = raw.trim()
    if (!line || line.startsWith('#') || !line.includes('=')) continue
    const i = line.indexOf('=')
    values[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^(['"])(.*)\1$/, '$2')
  }
  return values
}

function versionAtLeast(version, min) {
  const parts = version.split('.').map((n) => parseInt(n, 10))
  for (let i = 0; i < min.length; i++) {
    if ((parts[i] || 0) !== min[i]) return (parts[i] || 0) > min[i]
  }
  return true
}

// 1. Server is built.
if (!fs.existsSync(entryPoint)) {
  fail(`${path.relative(process.cwd(), entryPoint)} not found. Build it: cd connection/quickbooks-online-mcp-server && npm ci && npm run build`)
}

// 2. Required axios patch is present (D-04). npm ci reinstalls 1.19.0 from the lockfile.
try {
  const axios = JSON.parse(fs.readFileSync(path.join(serverDir, 'node_modules', 'axios', 'package.json'), 'utf8'))
  if (!versionAtLeast(axios.version, MIN_AXIOS)) {
    fail(`axios ${axios.version} is installed; >= ${MIN_AXIOS.join('.')} is required (DECISIONS_LOG D-04). ` +
      'Run: npm install --no-save --ignore-scripts axios@1.20.0 (in connection/quickbooks-online-mcp-server)')
  }
} catch (e) {
  if (e.code === 'ENOENT') fail('server dependencies are not installed (npm ci)')
  throw e
}

// 3. Token store exists, is checked out, sandbox, read-only.
if (!fs.existsSync(storePath)) {
  fail('token store not found. Run: python manage.py export_mcp_env --client <slug> (in connection/backend)')
}
const store = parseEnvFile(storePath)
const missing = ['QUICKBOOKS_CLIENT_ID', 'QUICKBOOKS_CLIENT_SECRET', 'QUICKBOOKS_REFRESH_TOKEN', 'QUICKBOOKS_REALM_ID']
  .filter((k) => !store[k])
if (missing.length) {
  fail(`no connection is checked out to the MCP server (empty: ${missing.join(', ')}). ` +
    'Run: python manage.py export_mcp_env --client <slug> (in connection/backend)')
}
if (!/^\d+$/.test(store.QUICKBOOKS_REALM_ID)) fail('QUICKBOOKS_REALM_ID in the token store is malformed')
if (store.QUICKBOOKS_ENVIRONMENT !== 'sandbox') {
  fail('QUICKBOOKS_ENVIRONMENT in the token store is not exactly "sandbox"; production is refused by design')
}
const notReadOnly = READ_ONLY_FLAGS.filter((k) => store[k] !== 'true')
if (notReadOnly.length) fail(`read-only flags not exactly "true" in the token store: ${notReadOnly.join(', ')}`)

// 4. Hand over to the official server. Host-env values below are a fallback only; the server's
//    dotenv(override:true) applies the (already verified) token-store values on top.
process.env.QUICKBOOKS_TOKEN_STORE_PATH = path.resolve(storePath) // must be absolute (server rejects relative)
for (const flag of READ_ONLY_FLAGS) process.env[flag] = 'true'
process.env.QUICKBOOKS_ENVIRONMENT = 'sandbox'
delete process.env.QBO_PDF_OUTPUT_DIR // keep get_invoice_pdf from writing to local disk

process.stderr.write(`[mcp_launch] starting official QBO MCP server (sandbox, read-only, realm ${store.QUICKBOOKS_REALM_ID.slice(0, 4)}…)\n`)
await import(pathToFileURL(entryPoint).href)

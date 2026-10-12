# Official QuickBooks Online MCP server: pinned version

| Field | Value |
|---|---|
| Repository | https://github.com/intuit/quickbooks-online-mcp-server |
| Pinned commit | `31a1dd5c3e170e368dbff651abbaf61aabde6ed9` |
| Commit date | 2026-09-15 10:56:34 -0700 |
| Commit subject | `fix: make tests and CI cross-platform (#136)` |
| package.json version | `0.0.1` (not meaningful; the SHA is the pin) |
| Pin mechanism | Git submodule at `connection/quickbooks-online-mcp-server` (gitlink mode 160000) |
| Entry point (verified) | `dist/index.js` (`package.json` `main`/`bin`; built by `npm run build` = `tsc`) |
| Transport | stdio only (`StdioServerTransport` in `src/index.ts`) |
| Node used to verify | v22.17.0 / npm 11.6.2 on Windows 11 |

## Reproduce (required steps, in order)

```bash
git submodule update --init connection/quickbooks-online-mcp-server
cd connection/quickbooks-online-mcp-server
git rev-parse HEAD        # must print 31a1dd5c3e170e368dbff651abbaf61aabde6ed9
npm ci                    # exact versions from upstream package-lock.json
# REQUIRED security patch (DECISIONS_LOG D-04). npm ci reinstalls axios 1.19.0 from the lockfile,
# so this line must run after EVERY npm ci / fresh clone, not just once:
npm install --no-save --ignore-scripts axios@1.20.0
npm ls axios              # verify: every path shows axios@1.20.0 (do NOT use npm audit to verify)
npm run build             # tsc -> dist/
npm test                  # optional: upstream unit tests (639 expected)
```

`--no-save` changes only `node_modules`, so `package.json`, `package-lock.json` and the submodule's Git
tree stay exactly at the pin. The trade-off is that `npm audit` reads the lockfile and **keeps reporting
axios 1.19.0** even when 1.20.0 is installed. `npm ls axios` is the authoritative check.

Verify the pin from the parent repo without entering the submodule:

```bash
git ls-tree HEAD connection/quickbooks-online-mcp-server   # 160000 commit 31a1dd5c...
git submodule status                                       # no leading '+' means checkout == pin
```

## Verification results (2026-10-12)

| Check | Result |
|---|---|
| `npm ci` | OK, 628 packages. Install scripts only in `fsevents` (macOS-only, skipped) and `unrs-resolver` (dev, native binding selector) |
| `npm run build` | OK, no TypeScript errors |
| `npm test` | **639 passed / 35 suites** (README says 396, which is stale) |
| `npm audit --omit=dev` | 8 vulnerable runtime packages (1 critical, 2 high, 5 moderate) carrying 20 GHSA advisories. Reachability analysis in DECISIONS_LOG D-04 |
| axios patch (D-04) | **Applied**: `npm ls axios` shows 1.20.0 on both paths; only `node_modules/axios` differs from the lockfile (628 packages compared); build OK; `npm test` 639/639. `npm audit` still lists axios 1.19.0 because it reads the lockfile (expected). The other 7 packages are left unpatched by decision |

## Upgrading the pin

1. `cd connection/quickbooks-online-mcp-server && git fetch && git checkout <new-sha>`
2. Re-read `src/clients/quickbooks-client.ts` (token load/rotation) and `src/helpers/register-tool.ts`
   (restriction flags). Our token lease design depends on both.
3. `npm ci`, then the axios `--no-save` step above (re-check whether the new lockfile already has
   axios >= 1.20.0, in which case drop the step), then `npm run build && npm test` and
   `connection/scripts/smoke_test`. Re-run the D-04 reachability check.
4. Update this file and commit the new gitlink from the parent repo.

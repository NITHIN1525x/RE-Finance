#!/usr/bin/env python
"""Read the stretch company's P&L back through the UNCHANGED read-only MCP server (stretch goal, D-62).

    python stretch/read_live_pnl.py

Does NOT use the demo connection (abc-inc-sandbox): it gets its own short-lived READ grant for the stretch company,
writes it to a TEMPORARY token store (connection/.secrets/stretch-read-mcp.env, sandbox + all three read-only flags),
and starts the unchanged launcher (connection/scripts/mcp_launch.mjs) pointed at that store via its QBO_MCP_TOKEN_STORE
override, so every launcher check still applies. .mcp.json, the demo store and Django are not touched.

It confirms that no write tools are registered, finds the class with search_classes, lists the chart of accounts with
search_accounts (to tell Intuit sample-data accounts from ones the loader created), and calls get_profit_and_loss
filtered by that class, by month, in 6-month chunks to stay well under the ~21k-token output limit. Reports are saved
to demo-output/stretch/live/. Finally it stops the server, revokes the read grant (using the latest token in the store,
in case the server rotated it), confirms the revocation and deletes the temporary store, even after an error.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (COMPANY_RECORD, OUT, REPO, SECRETS, StretchError, app_credentials, check_company,  # noqa: E402
                    delete_secret_file, demo_realm_hash, interactive_grant, read_env, realm_hash, revoke,
                    write_secret_file)

READ_STORE = SECRETS / "stretch-read-mcp.env"
LAUNCHER = REPO / "connection" / "scripts" / "mcp_launch.mjs"
LIVE = OUT / "live"
WRITE_PREFIX = re.compile(r"^(create|update|delete)[_-]")


def smoke_client():
    """Reuse the smoke test's minimal MCP stdio client (imported, not modified)."""
    path = REPO / "connection" / "scripts" / "smoke_test"
    loader = importlib.machinery.SourceFileLoader("smoke_test", str(path))
    spec = importlib.util.spec_from_loader("smoke_test", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def six_month_chunks(months):
    """[('YYYY-MM-01', 'YYYY-MM-last'), ...] covering months in chunks of 6."""
    import calendar
    out = []
    for i in range(0, len(months), 6):
        first, last = months[i], months[min(i + 5, len(months) - 1)]
        y, m = int(last[:4]), int(last[5:7])
        out.append((f"{first}-01", f"{last}-{calendar.monthrange(y, m)[1]:02d}"))
    return out


def account_census(accounts, record, class_created):
    """Each account the stretch posts to: created by the loader (on/after the ABC-IMPORT class) or pre-existing."""
    by_fqn = {a["FullyQualifiedName"]: a for a in accounts}
    ours = record["accounts_reused"] + [r["created_as"] for r in record["accounts_renamed"]] + ["ABC import clearing"]
    rows = []
    for fqn in dict.fromkeys(ours):
        a = by_fqn.get(fqn)
        created = a["MetaData"]["CreateTime"] if a else None
        rows.append({"account": fqn, "type": a["AccountType"] if a else None, "created": created,
                     "origin": None if not a else
                     ("stretch loader" if created >= class_created else "pre-existing (Intuit sample data)")})
    clashes = [{"name": r["planned"], "type": by_fqn[r["planned"]]["AccountType"],
                "created": by_fqn[r["planned"]]["MetaData"]["CreateTime"]}
               for r in record["accounts_renamed"] if r["planned"] in by_fqn]
    return {"class_created": class_created, "accounts": rows, "renamed_because_of": clashes}


def read(record, months):
    st = smoke_client()
    os.environ["QBO_MCP_TOKEN_STORE"] = str(READ_STORE)          # this process and its children only
    client = st.McpStdioClient(["node", str(LAUNCHER)], cwd=REPO)
    try:
        init = client.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                             "clientInfo": {"name": "stretch_read", "version": "1"}})
        client.notify("notifications/initialized")
        launch = next((l for l in client.stderr_lines if "[mcp_launch]" in l), "")
        if "sandbox, read-only" not in launch:
            raise StretchError("the launcher did not report a sandbox, read-only start")
        tools = [t["name"] for t in client.request("tools/list")["result"]["tools"]]
        writes = [t for t in tools if WRITE_PREFIX.match(t)]
        if writes:
            raise StretchError(f"write tools are registered ({len(writes)}); refusing")
        print(f"[stretch] MCP server {init['result']['serverInfo']['name']}: {len(tools)} tools, 0 write tools "
              f"(launcher: sandbox, read-only)")

        text, err = st.tool_text(client.call_tool("search_classes", {"name": record["class_name"]}))
        # The tool answers "Found N classes:" followed by a JSON ARRAY of Class objects.
        classes = json.loads(text[text.index("["):]) if text and "[" in text else []
        class_id = next((c["Id"] for c in classes if c.get("Name") == record["class_name"]), None)
        if err or not class_id:
            raise StretchError(f"class {record['class_name']} not found via search_classes ({err or 'no match'})")
        print(f"[stretch] search_classes: {record['class_name']} has Id {class_id}"
              f"{' (same as the loader recorded)' if class_id == record['class_id'] else ' (DIFFERENT from the loader!)'}")
        if class_id != record["class_id"]:
            raise StretchError("class Id differs from the one the loader wrote")
        class_created = next(c for c in classes if c["Id"] == class_id)["MetaData"]["CreateTime"]

        text, err = st.tool_text(client.call_tool("search_accounts", {"criteria": {"fetchAll": True}}))
        # "Found N accounts:" then one JSON Account object per text item (joined by newlines).
        accounts = [json.loads(l) for l in (text or "").splitlines()[1:] if l.startswith("{")]
        if err or not accounts:
            raise StretchError(f"search_accounts failed ({err or 'no accounts'})")
        census = account_census(accounts, record, class_created)
        LIVE.mkdir(parents=True, exist_ok=True)
        (LIVE / "accounts-census.json").write_text(json.dumps(census, indent=2), encoding="utf-8")
        origins = [r["origin"] for r in census["accounts"]]
        print(f"[stretch] search_accounts: {len(accounts)} accounts in the company; of the {len(origins)} the stretch "
              f"posts to, {origins.count('stretch loader')} were created by the loader, "
              f"{origins.count('pre-existing (Intuit sample data)')} pre-existed, {origins.count(None)} not found "
              f"-> demo-output/stretch/live/accounts-census.json")

        for start, end in six_month_chunks(months):
            resp = client.call_tool("get_profit_and_loss", {"start_date": start, "end_date": end,
                                                             "summarize_column_by": "Month",
                                                             "accounting_method": "Accrual", "class": class_id})
            text, err = st.tool_text(resp)
            report = st.first_json(text) if text else None
            if err or not report:
                raise StretchError(f"get_profit_and_loss {start}..{end} failed ({err or 'unparseable'})")
            out = LIVE / f"pnl-{start[:7]}.json"
            out.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"[stretch] get_profit_and_loss {start}..{end}, class={class_id}: {len(text):,} characters "
                  f"(~{len(text) // 4:,} tokens) -> {out.relative_to(REPO).as_posix()}")
    finally:
        client.close()


def main():
    grant = None
    try:
        if not COMPANY_RECORD.is_file():
            raise StretchError("demo-output/stretch/stretch-company.json not found: run the loader (--apply) first")
        record = json.loads(COMPANY_RECORD.read_text(encoding="utf-8"))
        months = json.loads((OUT / "workbook-run" / "abc-inc-2026-06-trends.json").read_text(encoding="utf-8"))["meta"]["months"]
        grant = interactive_grant("READ")
        if realm_hash(grant["realm"]) != record["realm_sha256"]:
            raise StretchError("signed in to a different company than the one the loader wrote to")
        check_company(grant, record["company"])                 # also refuses the demo company
        cid, secret = app_credentials()
        write_secret_file(READ_STORE, {
            "QUICKBOOKS_CLIENT_ID": cid, "QUICKBOOKS_CLIENT_SECRET": secret,
            "QUICKBOOKS_REFRESH_TOKEN": grant["refresh_token"], "QUICKBOOKS_REALM_ID": grant["realm"],
            "QUICKBOOKS_ENVIRONMENT": "sandbox", "QUICKBOOKS_DISABLE_WRITE": "true",
            "QUICKBOOKS_DISABLE_UPDATE": "true", "QUICKBOOKS_DISABLE_DELETE": "true"},
            "TEMPORARY read-only MCP store for the stretch company. Revoked and deleted by stretch/read_live_pnl.py")
        print(f"[stretch] Temporary read-only store written for {record['company']} ({record['realm_hint']}); "
              f"demo store untouched: {demo_realm_hash() is not None}")
        read(record, months)
        return 0
    except StretchError as exc:
        print(f"[stretch] STOPPED: {exc}", file=sys.stderr)
        return 1
    finally:
        if grant:
            latest = read_env(READ_STORE).get("QUICKBOOKS_REFRESH_TOKEN") or grant["refresh_token"]
            revoke(latest)
            print(f"[stretch] READ grant revoked and confirmed (refresh now fails with invalid_grant); "
                  f"temporary store deleted: {delete_secret_file(READ_STORE)}")


if __name__ == "__main__":
    sys.exit(main())

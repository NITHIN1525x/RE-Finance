#!/usr/bin/env python
"""THROWAWAY loader (stretch goal, D-36 / D-62): put ABC Inc's monthly P&L into a NEW QuickBooks sandbox company.

    python stretch/load_abc_into_sandbox.py                       # DRY RUN (default): build + validate, no network
    python stretch/load_abc_into_sandbox.py --apply --expect-company "<new sandbox company name>"
    python stretch/load_abc_into_sandbox.py --revoke-only          # clean up a grant left by an interrupted run

Source: the skill's own JSON for the workbook run (every detail row; its subtotals reconcile 100%). Scope: the P&L only
(income, COGS and expense accounts + one journal entry per month). The balance sheet is NOT reproduced: each entry
balances against one equity account, "ABC import clearing". Accounts that are zero in every month are skipped.

Every imported line carries the class ABC-IMPORT, so the P&L can be read back filtered to exactly this data.
--apply uses its OWN short-lived OAuth grant (separate from the demo connection), refuses the demo company, writes,
self-checks, then revokes the grant, confirms the revocation and deletes its token file, even after an error.
"""
from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (COMPANY_RECORD, OUT, SECRETS, Sandbox, StretchError, check_company,  # noqa: E402
                    delete_secret_file, interactive_grant, read_env, realm_hash, realm_hint, revoke, write_secret_file)

DEFAULT_SOURCE = OUT / "workbook-run" / "abc-inc-2026-06-trends.json"
CLASS_NAME = "ABC-IMPORT"
CLEARING = "ABC import clearing"
RENAME_SUFFIX = " (ABC)"     # only when a sample-data account already uses the name with ANOTHER type
WRITE_TOKENS = SECRETS / "stretch-write.env"
TYPES = {"income": "Income", "cogs": "Cost of Goods Sold", "expense": "Expense", "clearing": "Other Current Liability"}
# The clearing account balances each entry; it is a balance-sheet account, so it never shows on the P&L. Its detail
# type is set explicitly: left blank, QuickBooks picks a default detail type that some companies allow only once.
DETAIL_TYPES = {"Other Current Liability": "OtherCurrentLiabilities"}


def cents(v):
    return Decimal(str(v)).quantize(Decimal("0.01"))


# ------------------------------------------------------------------------------------------------ plan (offline)
def account_path(row, kind):
    """Path of names from the top: group parents become parent accounts; 'A: B' (no ':' allowed in QBO) -> A > B."""
    parts = [p.strip() for p in row["name"].split(":")] if kind == "expense" else [row["name"]]
    group = row.get("group") if kind == "expense" else None
    return ([group] if group else []) + parts


def build_plan(analysis):
    meta = analysis["meta"]
    rows = ([("income", s) for s in analysis["revenue"]["streams"]] +
            [("cogs", c) for c in analysis["gross_margin"]["cogs_lines"]] +
            [("expense", a) for a in analysis["operating_expenses"]["accounts"]])
    skipped = [r["name"] for _, r in rows if not any(r["monthly"])]
    rows = [(k, r) for k, r in rows if any(r["monthly"])]

    accounts, seen = [], set()
    for kind, r in rows:
        path = account_path(r, kind)
        for depth in range(1, len(path) + 1):
            key = tuple(path[:depth])
            if key not in seen:
                seen.add(key)
                accounts.append({"path": list(key), "type": TYPES[kind]})
    accounts.append({"path": [CLEARING], "type": TYPES["clearing"]})

    entries = []
    for i, month in enumerate(meta["months"]):
        year, mon = int(month[:4]), int(month[5:7])
        lines, signed = [], {"income": Decimal(0), "cogs": Decimal(0), "expense": Decimal(0)}
        for kind, r in rows:
            v = cents(r["monthly"][i])
            if not v:
                continue
            signed[kind] += v
            credit = (v > 0) if kind == "income" else (v < 0)          # income is a credit; costs are debits
            lines.append({"path": account_path(r, kind), "posting": "Credit" if credit else "Debit", "amount": abs(v)})
        debits = sum(l["amount"] for l in lines if l["posting"] == "Debit")
        credits = sum(l["amount"] for l in lines if l["posting"] == "Credit")
        if credits != debits:
            lines.append({"path": [CLEARING], "posting": "Debit" if credits > debits else "Credit",
                          "amount": abs(credits - debits)})
        entries.append({"doc_number": f"{CLASS_NAME}-{month}",
                        "date": f"{month}-{calendar.monthrange(year, mon)[1]:02d}",
                        "month": month, "lines": lines, "signed": signed})
    return {"accounts": accounts, "entries": entries, "skipped": skipped, "months": meta["months"]}


def validate(plan, analysis):
    """Per month: debits == credits, and income / COGS / expenses / net income equal the JSON to the cent."""
    report, ok = [], True
    for i, e in enumerate(plan["entries"]):
        dr = sum(l["amount"] for l in e["lines"] if l["posting"] == "Debit")
        cr = sum(l["amount"] for l in e["lines"] if l["posting"] == "Credit")
        s = e["signed"]
        checks = {
            "balanced": dr == cr,
            "income": s["income"] == cents(analysis["revenue"]["total"]["monthly"][i]),
            "cogs": s["cogs"] == cents(analysis["gross_margin"]["monthly"][i]["cogs"]),
            "expenses": s["expense"] == cents(analysis["operating_expenses"]["total"]["monthly"][i]),
            "net_income": s["income"] - s["cogs"] - s["expense"] == cents(analysis["net_income"]["monthly"][i]),
        }
        ok &= all(checks.values())
        report.append({"month": e["month"], "lines": len(e["lines"]), "debits": dr, "credits": cr, **checks})
    return ok, report


def print_dry_run(plan, ok, report):
    by_type = {}
    for a in plan["accounts"]:
        by_type[a["type"]] = by_type.get(a["type"], 0) + 1
    print(f"Accounts to create: {len(plan['accounts'])} "
          f"({', '.join(f'{t} {n}' for t, n in by_type.items())}; parents included)")
    print(f"Journal entries: {len(plan['entries'])} (one per month, {plan['months'][0]} to {plan['months'][-1]}); "
          f"lines: {sum(len(e['lines']) for e in plan['entries'])} (incl. one clearing line per month)")
    print(f"Skipped (zero in every month): {', '.join(plan['skipped']) or 'none'}")
    print(f"\n{'Month':8} {'Lines':>5} {'Debits':>15} {'Credits':>15}  Dr=Cr  Income COGS Expenses NetIncome (vs JSON)")
    for r in report:
        flag = lambda k: "ok" if r[k] else "FAIL"  # noqa: E731
        print(f"{r['month']:8} {r['lines']:>5} {r['debits']:>15,.2f} {r['credits']:>15,.2f}  {flag('balanced'):5}  "
              f"{flag('income'):6} {flag('cogs'):4} {flag('expenses'):8} {flag('net_income')}")
    print(f"\nDRY RUN {'PASSED' if ok else 'FAILED'}: nothing was sent to QuickBooks.")


# ------------------------------------------------------------------------------------------------ apply (network)
def ensure_class_tracking(qb):
    prefs = qb.call("GET", "preferences")["Preferences"]
    info = prefs.get("AccountingInfoPrefs", {})
    if info.get("ClassTrackingPerTxnLine"):
        return "already on"
    qb.call("POST", "preferences", body={"sparse": True, "Id": prefs["Id"], "SyncToken": prefs["SyncToken"],
                                         "AccountingInfoPrefs": {"ClassTrackingPerTxn": False,
                                                                 "ClassTrackingPerTxnLine": True}})
    return "turned on"


def ensure_class(qb):
    found = qb.query(f"select * from Class where Name = '{CLASS_NAME}'").get("Class", [])
    if found:
        return found[0]["Id"], "existing"
    return qb.call("POST", "class", body={"Name": CLASS_NAME})["Class"]["Id"], "created"


def ensure_accounts(qb, plan):
    existing = {}
    start = 1
    while True:
        page = qb.query(f"select * from Account startposition {start} maxresults 1000").get("Account", [])
        for a in page:
            existing[a["FullyQualifiedName"]] = a
        if len(page) < 1000:
            break
        start += 1000
    # ids are keyed by the PLANNED path, so journal lines find their account whatever name it finally has.
    ids, created, reused, renamed = {}, 0, [], []
    actual_fqn = {}                                   # planned path -> the account's real FullyQualifiedName
    for acc in plan["accounts"]:
        fqn = ":".join(acc["path"])
        parent = actual_fqn.get(":".join(acc["path"][:-1])) if len(acc["path"]) > 1 else None
        name = acc["path"][-1]
        real = f"{parent}:{name}" if parent else name
        if real in existing and existing[real]["AccountType"] != acc["type"]:
            # A sample-data account with this name but another type (e.g. 'Depreciation' as Other Expense):
            # create our own, clearly marked, instead of posting ABC amounts to the wrong section of the P&L.
            clash_type = existing[real]["AccountType"]
            name = f"{name}{RENAME_SUFFIX}"
            real = f"{parent}:{name}" if parent else name
            if real in existing and existing[real]["AccountType"] != acc["type"]:
                raise StretchError(f"both {fqn!r} and {real!r} exist with another type; stopping before any entry")
            renamed.append({"planned": fqn, "created_as": real, "existing_type": clash_type})
        actual_fqn[fqn] = real
        if real in existing:
            ids[fqn] = existing[real]["Id"]
            reused.append(real)
            continue
        body = {"Name": name, "AccountType": acc["type"]}
        if acc["type"] in DETAIL_TYPES:
            body["AccountSubType"] = DETAIL_TYPES[acc["type"]]
        if parent:
            body.update({"SubAccount": True, "ParentRef": {"value": ids[":".join(acc["path"][:-1])]}})
        try:
            ids[fqn] = qb.call("POST", "account", body=body)["Account"]["Id"]
        except StretchError as exc:
            raise StretchError(f"creating account {real!r} ({acc['type']}) failed after {created} created and "
                               f"{len(reused)} reused, before any journal entry: {exc}") from exc
        created += 1
    return ids, created, reused, renamed


def post_entries(qb, plan, ids, class_id):
    posted, skipped = 0, 0
    for e in plan["entries"]:
        if qb.query(f"select Id from JournalEntry where DocNumber = '{e['doc_number']}'").get("JournalEntry"):
            skipped += 1
            continue
        lines = [{"DetailType": "JournalEntryLineDetail", "Amount": float(l["amount"]),
                  "JournalEntryLineDetail": {"PostingType": l["posting"],
                                             "AccountRef": {"value": ids[":".join(l["path"])]},
                                             "ClassRef": {"value": class_id}}} for l in e["lines"]]
        qb.call("POST", "journalentry", body={"DocNumber": e["doc_number"], "TxnDate": e["date"], "Line": lines,
                                              "PrivateNote": "ABC Inc P&L import, stretch goal (DECISIONS_LOG D-62)"})
        posted += 1
    return posted, skipped


def self_check(qb, plan, class_id):
    """The class-filtered P&L from QuickBooks itself must equal the plan per month (income, COGS, expenses, NI)."""
    rep = qb.call("GET", "reports/ProfitAndLoss", params={
        "start_date": plan["entries"][0]["date"][:8] + "01", "end_date": plan["entries"][-1]["date"],
        "summarize_column_by": "Month", "accounting_method": "Accrual", "class": class_id})
    totals = {}
    for row in rep["Rows"]["Row"]:
        summary = (row.get("Summary") or {}).get("ColData") or []
        if summary:
            totals[summary[0]["value"]] = [Decimal(c["value"] or "0") for c in summary[1:]]
    want = {"Total Income": "income", "Total Cost of Goods Sold": "cogs", "Total Expenses": "expense"}
    bad = []
    for i, e in enumerate(plan["entries"]):
        for label, key in want.items():
            if totals.get(label, [None] * 99)[i] != e["signed"][key]:
                bad.append(f"{e['month']} {label}")
    return bad


def apply(plan, expect_company):
    grant, record = None, {}
    try:
        grant = interactive_grant("WRITE")
        write_secret_file(WRITE_TOKENS, {"QUICKBOOKS_REFRESH_TOKEN": grant["refresh_token"],
                                         "QUICKBOOKS_REALM_ID": grant["realm"]},
                          "Stretch WRITE grant (throwaway). Revoked and deleted by load_abc_into_sandbox.py")
        name = check_company(grant, expect_company)
        print(f"[stretch] Company: {name} (realm {realm_hint(grant['realm'])}); NOT the demo company. Writing…")
        qb = Sandbox(grant["realm"], grant["access_token"])
        print(f"[stretch] Class tracking per line: {ensure_class_tracking(qb)}")
        class_id, how = ensure_class(qb)
        print(f"[stretch] Class {CLASS_NAME}: {how} (Id {class_id})")
        ids, created, reused, renamed = ensure_accounts(qb, plan)
        print(f"[stretch] Accounts: {created} created, {len(reused)} already there (reused), {len(renamed)} renamed")
        for r in renamed:
            print(f"[stretch]   renamed: {r['planned']!r} -> {r['created_as']!r} "
                  f"(the existing {r['planned']!r} is type {r['existing_type']!r})")
        print(f"[stretch]   reused: {', '.join(reused) or 'none'}")
        posted, skipped = post_entries(qb, plan, ids, class_id)
        print(f"[stretch] Journal entries: {posted} posted, {skipped} already there")
        bad = self_check(qb, plan, class_id)
        print(f"[stretch] Self-check (QuickBooks' class-filtered P&L vs plan): "
              f"{'all 18 months match' if not bad else 'MISMATCH: ' + ', '.join(bad)}")
        record = {"company": name, "realm_hint": realm_hint(grant["realm"]), "realm_sha256": realm_hash(grant["realm"]),
                  "class_name": CLASS_NAME, "class_id": class_id, "accounts_created": created,
                  "accounts_reused": reused, "accounts_renamed": renamed, "entries_posted": posted,
                  "entries_skipped": skipped,
                  "self_check_mismatches": bad, "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        OUT.mkdir(parents=True, exist_ok=True)
        COMPANY_RECORD.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return not bad
    finally:
        if grant:
            revoke(grant["refresh_token"])
            gone = delete_secret_file(WRITE_TOKENS)
            print(f"[stretch] WRITE grant revoked and confirmed (refresh now fails with invalid_grant); "
                  f"token file deleted: {gone}")


def revoke_only():
    env = read_env(WRITE_TOKENS)
    if not env.get("QUICKBOOKS_REFRESH_TOKEN"):
        print("[stretch] no write grant on file; nothing to revoke")
        return True
    revoke(env["QUICKBOOKS_REFRESH_TOKEN"])
    print(f"[stretch] write grant revoked and confirmed; token file deleted: {delete_secret_file(WRITE_TOKENS)}")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="the skill's *-trends.json for the ABC workbook")
    ap.add_argument("--apply", action="store_true", help="write to QuickBooks (needs --expect-company)")
    ap.add_argument("--expect-company", help="exact name of the NEW sandbox company (safety check)")
    ap.add_argument("--revoke-only", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.revoke_only:
            return 0 if revoke_only() else 1
        src = Path(args.source)
        if not src.is_file():
            raise StretchError(f"{src} not found. Create it (free): .claude/skills/monthly-trend-analysis/.venv/Scripts/"
                               "python .claude/skills/monthly-trend-analysis/scripts/run_trends.py --out-dir "
                               "demo-output/stretch/workbook-run")
        analysis = json.loads(src.read_text(encoding="utf-8"))
        plan = build_plan(analysis)
        ok, report = validate(plan, analysis)
        print_dry_run(plan, ok, report)
        if not ok:
            return 1
        if not args.apply:
            return 0
        if not args.expect_company:
            raise StretchError("--apply needs --expect-company \"<new sandbox company name>\"")
        return 0 if apply(plan, args.expect_company) else 1
    except StretchError as exc:
        print(f"[stretch] STOPPED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

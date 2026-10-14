"""Offline tests for the stretch-goal scripts (no network, no QuickBooks, no Claude).

Run:  .claude/skills/monthly-trend-analysis/.venv/Scripts/python stretch/test_stretch.py
"""
import copy
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "monthly-trend-analysis" / "scripts"))
import compare_live_vs_workbook as C  # noqa: E402
import common  # noqa: E402
import load_abc_into_sandbox as L  # noqa: E402
import pnl_to_workbook as A  # noqa: E402
import read_live_pnl as R  # noqa: E402
import run_trends  # noqa: E402

ABC_JSON = REPO / "trend-reports" / "abc-inc-2026-06-trends.json"


class LoaderPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = json.loads(ABC_JSON.read_text(encoding="utf-8"))
        cls.plan = L.build_plan(cls.analysis)

    def test_every_month_balances_and_matches_the_json(self):
        ok, report = L.validate(self.plan, self.analysis)
        self.assertTrue(ok, [r for r in report if not all(r[k] for k in ("balanced", "income", "cogs", "expenses"))])
        self.assertEqual(len(self.plan["entries"]), 18)

    def test_colon_names_become_sub_accounts_under_their_group(self):
        paths = [a["path"] for a in self.plan["accounts"]]
        self.assertIn(["Marketing", "Marketing/Advertising", "Ad Spend"], paths)
        self.assertNotIn(":", "".join(p[-1] for p in paths))          # QuickBooks forbids ':' in a name
        parents = [p[:-1] for p in paths if len(p) > 1]
        self.assertTrue(all(par in paths for par in parents))          # every parent is created, before use
        self.assertTrue(all(paths.index(par) < paths.index(p) for p in paths if len(p) > 1 for par in [p[:-1]]))

    def test_zero_accounts_skipped_and_signs_correct(self):
        self.assertEqual(len(self.plan["skipped"]), 4)
        jun = self.plan["entries"][-1]
        partnership = next(l for l in self.plan["entries"][14]["lines"] if l["path"] == ["Partnership Income"])
        source = next(s for s in self.analysis["revenue"]["streams"] if s["name"] == "Partnership Income")
        self.assertLess(source["monthly"][14], 0)                                   # Mar 2026 is a refund (negative)
        self.assertEqual((partnership["posting"], partnership["amount"]),           # so the income account is DEBITED
                         ("Debit", L.cents(abs(source["monthly"][14]))))
        self.assertTrue(all(l["amount"] > 0 for l in jun["lines"]))


class FakeQuickBooks:
    """Offline stand-in for common.Sandbox: a few sample-data accounts, records every account created."""

    def __init__(self, existing):
        self.accounts = {fqn: {"Id": str(i), "FullyQualifiedName": fqn, "AccountType": t}
                         for i, (fqn, t) in enumerate(existing.items(), 1)}
        self.created = []

    def query(self, sql):
        return {"Account": list(self.accounts.values())} if "from Account" in sql else {}

    def call(self, method, path, body=None, params=None):
        new_id = str(1000 + len(self.created))
        parent = next((a["FullyQualifiedName"] for a in self.accounts.values()
                       if body.get("ParentRef") and a["Id"] == body["ParentRef"]["value"]), None)
        fqn = f"{parent}:{body['Name']}" if parent else body["Name"]
        self.accounts[fqn] = {"Id": new_id, "FullyQualifiedName": fqn, "AccountType": body["AccountType"]}
        self.created.append((fqn, body["AccountType"]))
        return {"Account": {"Id": new_id}}


class AccountNameClashes(unittest.TestCase):
    def setUp(self):
        self.plan = L.build_plan(json.loads(ABC_JSON.read_text(encoding="utf-8")))

    def test_other_type_clash_is_renamed_same_type_is_reused(self):
        qb = FakeQuickBooks({"Depreciation": "Other Expense",       # sample data, different type -> rename
                             "Insurance": "Expense",                # sample data, same type -> reuse
                             "Platform Revenue": "Income"})          # created by an earlier, interrupted run
        ids, created, reused, renamed = L.ensure_accounts(qb, self.plan)
        self.assertEqual([r["created_as"] for r in renamed], ["Depreciation (ABC)"])
        self.assertEqual(renamed[0]["existing_type"], "Other Expense")
        self.assertIn(("Depreciation (ABC)", "Expense"), qb.created)
        self.assertNotIn(("Depreciation", "Expense"), qb.created)
        self.assertEqual(sorted(reused), ["Insurance", "Platform Revenue"])
        self.assertEqual(ids["Depreciation"], qb.accounts["Depreciation (ABC)"]["Id"])    # lines post to OUR account
        self.assertEqual(created, len(self.plan["accounts"]) - 2)
        self.assertIn(("Marketing:Marketing/Advertising:Ad Spend", "Expense"), qb.created)  # children keep parents

    def test_clearing_account_is_a_liability_with_an_explicit_detail_type(self):
        qb = FakeQuickBooks({})
        qb.bodies = []
        call = qb.call
        qb.call = lambda method, path, body=None, params=None: (qb.bodies.append(body), call(method, path, body))[1]
        L.ensure_accounts(qb, self.plan)
        clearing = next(b for b in qb.bodies if b["Name"] == L.CLEARING)
        self.assertEqual((clearing["AccountType"], clearing["AccountSubType"]),
                         ("Other Current Liability", "OtherCurrentLiabilities"))
        self.assertTrue(all("AccountSubType" not in b for b in qb.bodies if b["Name"] != L.CLEARING))

    def test_a_refused_account_is_named_in_the_error(self):
        qb = FakeQuickBooks({})
        def refuse(method, path, body=None, params=None):
            raise common.StretchError("HTTP 400: Business Validation Error")
        qb.call = refuse
        with self.assertRaisesRegex(common.StretchError, r"creating account 'Platform Revenue' \(Income\) failed"):
            L.ensure_accounts(qb, self.plan)

    def test_rename_target_with_wrong_type_stops(self):
        qb = FakeQuickBooks({"Depreciation": "Other Expense", "Depreciation (ABC)": "Other Expense"})
        with self.assertRaises(common.StretchError):
            L.ensure_accounts(qb, self.plan)


def section(label, rows, total_label, totals):
    return {"type": "Section", "Header": {"ColData": [{"value": label}, {"value": ""}, {"value": ""}]},
            "Rows": {"Row": rows}, "Summary": {"ColData": [{"value": total_label}] + [{"value": t} for t in totals]}}


def data(label, values):
    return {"type": "Data", "ColData": [{"value": label}] + [{"value": v} for v in values]}


def report(months, income, cogs, opex_parent, opex_child, net):
    cols = [{"ColTitle": "", "ColType": "Account"}] + [{"ColTitle": m, "ColType": "Money"} for m in months] + \
           [{"ColTitle": "Total", "ColType": "Money", "MetaData": [{"Name": "ColKey", "Value": "total"}]}]
    tot = lambda vals: [f"{sum(map(float, vals[i::len(months)])):.2f}" for i in range(len(months))]  # noqa: E731
    return {"Columns": {"Column": cols}, "Rows": {"Row": [
        section("Income", [data("Bread Sales", income + [""])], "Total Income", income + [""]),
        section("Cost of Goods Sold", [data("Flour", cogs + [""])], "Total Cost of Goods Sold", cogs + [""]),
        {"group": "GrossProfit", "Summary": {"ColData": [{"value": "Gross Profit"}] +
                                             [{"value": f"{float(i) - float(c):.2f}"} for i, c in zip(income, cogs)] + [{"value": ""}]}},
        section("Expenses", [section("Marketing", [data("Ad Spend", opex_child + [""])], "Total Marketing", opex_child + [""]),
                             data("Rent", opex_parent + [""])], "Total Expenses",
                [f"{float(a) + float(b):.2f}" for a, b in zip(opex_parent, opex_child)] + [""]),
        {"group": "NetIncome", "Summary": {"ColData": [{"value": "Net Income"}] + [{"value": n} for n in net] + [{"value": ""}]}},
    ]}}


class AccountCensus(unittest.TestCase):
    def test_accounts_created_after_the_class_are_the_loaders(self):
        acct = lambda fqn, t, created: {"FullyQualifiedName": fqn, "AccountType": t,  # noqa: E731
                                        "MetaData": {"CreateTime": created}}
        accounts = [acct("Insurance", "Expense", "2026-10-13T09:00:00-07:00"),          # sample data
                    acct("Depreciation", "Other Expense", "2026-10-13T09:00:00-07:00"),
                    acct("Rent", "Expense", "2026-10-13T22:05:00-07:00"),               # loader, run 1
                    acct("Depreciation (ABC)", "Expense", "2026-10-13T22:20:00-07:00"),
                    acct("ABC import clearing", "Other Current Liability", "2026-10-13T22:32:00-07:00")]
        record = {"accounts_reused": ["Insurance", "Rent", "Depreciation (ABC)", "Missing"],
                  "accounts_renamed": [{"planned": "Depreciation", "created_as": "Depreciation (ABC)"}]}
        census = R.account_census(accounts, record, "2026-10-13T22:00:00-07:00")
        origin = {r["account"]: r["origin"] for r in census["accounts"]}
        self.assertEqual(origin, {"Insurance": "pre-existing (Intuit sample data)", "Rent": "stretch loader",
                                  "Depreciation (ABC)": "stretch loader", "Missing": None,
                                  "ABC import clearing": "stretch loader"})
        self.assertEqual(census["renamed_because_of"][0]["type"], "Other Expense")


class Adapter(unittest.TestCase):
    def test_two_chunks_become_one_workbook_the_skill_reads_unchanged(self):
        r1 = report(["Jan 2026", "Feb 2026"], ["1000.00", "1100.00"], ["400.00", "420.00"], ["100.00", "100.00"],
                    ["50.00", "60.00"], ["450.00", "520.00"])
        r2 = report(["Mar 2026"], ["1200.00"], ["430.00"], ["100.00"], ["70.00"], ["600.00"])
        wb, months, rows = A.build([r1, r2], "Test Bakery (live)")
        self.assertEqual(months, ["Jan 2026", "Feb 2026", "Mar 2026"])
        self.assertIn(["Marketing", None, None, None], rows)                    # header row has no values
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "live.xlsx"
            wb.save(path)
            self.assertEqual(run_trends.main([str(path), "--out-dir", d]), 0)
            out = json.loads(next(Path(d).glob("*-trends.json")).read_text(encoding="utf-8"))
        self.assertEqual(out["revenue"]["total"]["monthly"], [1000.0, 1100.0, 1200.0])
        self.assertEqual(out["operating_expenses"]["total"]["monthly"], [150.0, 160.0, 170.0])
        self.assertEqual(out["net_income"]["monthly"], [450.0, 520.0, 600.0])
        self.assertTrue(all(c["status"] in ("pass", "skipped") for c in out["data_quality"]["checks"]))

    def test_a_parents_own_amounts_become_a_same_name_row_and_totals_still_tie(self):
        rep = report(["Jan 2026", "Feb 2026"], ["1000.00", "1000.00"], ["400.00", "400.00"], ["100.00", "100.00"],
                     ["50.00", "50.00"], ["445.00", "450.00"])
        marketing = rep["Rows"]["Row"][3]["Rows"]["Row"][0]
        marketing["Header"]["ColData"][1]["value"] = "5.00"                        # Jan postings to the parent itself
        marketing["Summary"]["ColData"][1]["value"] = "55.00"                      # QuickBooks' Total includes them
        rep["Rows"]["Row"][3]["Summary"]["ColData"][1]["value"] = "155.00"
        wb, months, rows = A.build([rep], "x")
        i = rows.index(["Marketing", None, None])
        self.assertEqual(rows[i + 1:i + 4], [["Marketing", 5.0, None], ["Ad Spend", 50.0, 50.0],
                                             ["Total Marketing", 55.0, 50.0]])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "live.xlsx"
            wb.save(path)
            self.assertEqual(run_trends.main([str(path), "--out-dir", d]), 0)
            out = json.loads(next(Path(d).glob("*-trends.json")).read_text(encoding="utf-8"))
        self.assertEqual(out["operating_expenses"]["total"]["monthly"], [155.0, 150.0])
        self.assertTrue(all(c["status"] in ("pass", "skipped") for c in out["data_quality"]["checks"]))


class Comparison(unittest.TestCase):
    def test_identical_runs_have_no_differences_and_a_change_is_caught(self):
        a = json.loads(ABC_JSON.read_text(encoding="utf-8"))
        self.assertEqual(C.compare(a, a)[2], [])
        b = copy.deepcopy(a)
        b["revenue"]["total"]["monthly"][3] += 0.05
        self.assertEqual(len(C.compare(a, b)[2]), 1)


class SafetyHelpers(unittest.TestCase):
    def test_realm_is_only_hinted_and_hashed(self):
        self.assertEqual(common.realm_hint("123456789012345"), "1234…")
        self.assertNotIn("123456789012345", common.realm_hash("123456789012345"))

    def test_api_calls_are_sandbox_only_and_token_files_stay_in_secrets(self):
        self.assertEqual(common.SANDBOX_API_HOST, "sandbox-quickbooks.api.intuit.com")
        with tempfile.TemporaryDirectory() as d, self.assertRaises(common.StretchError):
            common.write_secret_file(Path(d) / "x.env", {"A": "b"}, "test")


if __name__ == "__main__":
    unittest.main(verbosity=2)

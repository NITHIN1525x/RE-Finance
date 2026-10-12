"""Config loading and classification. Everything company-specific lives in references/category_map.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "references" / "category_map.json"


def load_config(path=None):
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


def _matches(patterns, text):
    return bool(text) and any(re.search(p, text, re.IGNORECASE) for p in patterns)


def section_role(section_name, config):
    """'revenue' | 'cogs' | 'operating_expenses' | 'other_income' | 'other_expense' | None (unknown)."""
    for role, patterns in config["statement_sections"].items():
        if role.startswith("_"):
            continue
        if _matches(patterns, section_name):
            return role
    return None


def summary_role(label, config):
    for role, patterns in config["summary_rows"].items():
        if _matches(patterns, label):
            return role
    return None


def opex_category(account_name, group_names, config):
    """Return (category, non_operating, matched_on). matched_on explains the decision for the reviewer."""
    rules = config["opex_categories"]["rules"]
    parent = account_name.split(":", 1)[0].strip() if ":" in account_name else None
    candidates = [("account", account_name)] + ([("parent account", parent)] if parent else []) + \
                 [("group", g) for g in reversed(group_names)]
    for rule in rules:
        for kind, text in candidates:
            if _matches(rule["patterns"], text):
                return rule["category"], bool(rule.get("non_operating")), f"{kind} '{text}'"
    return config["opex_categories"]["fallback_category"], False, "no rule matched"


def balance_role(section_name, config):
    for role, patterns in config["balance_sheet_sections"].items():
        if _matches(patterns, section_name):
            return role
    return None

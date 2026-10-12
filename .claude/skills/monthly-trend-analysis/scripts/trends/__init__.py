"""Monthly trend analysis for QuickBooks-Online-style Excel exports.

Modules:
    workbook  - parse a QBO-layout sheet into sections / detail accounts / stated subtotals (no account names hardcoded)
    mapping   - load category_map.json; assign statement roles and opex categories (unmapped -> fallback bucket)
    analysis  - monthly series, MoM %, TTM, gross margin, movers, rule-based flags, data-quality checks
    report    - render the analysis dict as a Markdown report for a human reviewer
"""

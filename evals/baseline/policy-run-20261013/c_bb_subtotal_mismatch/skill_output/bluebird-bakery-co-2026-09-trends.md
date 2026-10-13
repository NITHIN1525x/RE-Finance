# Monthly trend analysis: Bluebird Bakery Co, Sep 2026

> **DRAFT for reviewer.** Generated 2026-10-13T02:19:19+00:00 from `.claude\skills\monthly-trend-analysis\tests\test_data\bluebird-bakery.xlsx` (sheets: Profit and Loss, Balance Sheet). 9 months (Jan 2026 to Sep 2026). Figures are as exported (currency as exported (no conversion)); negatives in parentheses. Nothing here is a forecast or an accounting judgment.
>
> Data-quality checks: **1 MISMATCH(ES), see section 8**.

## 1. Commentary (draft)

- **Data quality, please resolve first:** In Mar 2026, 'Total for Professional Services' states 2,225.00, but its detail rows sum to 2,200.00 (diff 25.00). This analysis uses the detail rows. The reviewer should confirm which figure is right. The structure was also partly reconstructed. 'Total Delivery' had no header row, so it was grouped from Delivery Van Fuel and Courier: Same Day, which sum to it in every month. 'Charitable Donations' had no values and no total row, so the 4 rows after it were kept at the parent level.
- **Limited comparisons:** TTM and year-over-year figures aren't available because the export covers only 9 months (Jan–Sep 2026). Every comparison below is month-over-month or against the prior 6-month average.
- **Revenue 81,300, up 17.7%** from 69,050 in Aug 2026 and 17.3% above the prior 6-month average (69,292). Sep includes 12,000 from 'Wholesale Accounts', a new stream that was zero in the prior 6 months. Bread Sales rose 1.9% to 49,200 and Pastry Sales fell 2.2% to 15,700, continuing a steady monthly pattern in both. Catering Revenue was 3,800 (-5.0%), after 4,000 in Aug and 9,100 in Jul.
- **Gross margin 65.3%,** up from 59.6% in Aug 2026 (+5.7 pp) and above the prior 6-month average of 60.6%. It is the highest month in the period, which ranges from 56.8% (Mar 2026) to 65.3% (Sep 2026). COGS was 28,220 against 27,930 in Aug.
- **Operating expenses 31,570, up 21.0%.** Almost all of the increase is Payroll & Benefits: 22,600, up 5,000 or 28.4%, driven by Wages & Salaries (16,000 → 21,000, +31.2%). Payroll & Benefits had been 17,600 in each month from Apr to Aug 2026. The reviewer should confirm whether this is a single-month item or a new level. Mystery Shopper Program (400) shows as "from 0", but it is not new: it was 400 in Mar, Jun and Sep 2026.
- **Net income 21,553,** up from 15,077 in Aug 2026 (+6,476, +42.9%). It was positive in all 9 months, and the lowest month was Mar 2026 (8,387). The as-exported and excl.-non-operating figures are the same, because this export has no non-operating items inside opex.
- **Cash: Bank Accounts 37,600,** down 1,800 from Aug and down 10,800 from six months earlier (48,400). Over the same six months, equity went from 54,660 to 44,940 while net income was positive every month. The reviewer may want to check what accounts for this, such as owner draws or distributions, since the P&L doesn't show it.
- **Other items to review:** Gift Cards was negative in Mar 2026 (-300). This may be credits or refunds, which the reviewer should confirm. Three expense accounts matched no category rule and sit in 'Other Opex': Instagram Ads, Mystery Shopper Program and Supplier Rebates. Supplier Rebates is a credit (negative) line.

### Flags raised by the rules (evidence for the commentary)

- **[high] revenue**: Total revenue Sep 2026: 81,300, +17.7% vs Aug 2026 (69,050), +17.3% vs the prior 6-month average (69,292).
- **[high] cash**: 'Bank Accounts' Sep 2026: 37,600, -1,800 vs prior month and -10,800 vs six months earlier (48,400).
- **[high] data_quality**: 'Total for Professional Services' in Mar 2026 states 2,225.00 but its detail rows sum to 2,200.00 (diff 25.00). Analysis uses the detail rows; reviewer to confirm.
- **[medium] revenue_stream**: Revenue stream 'Gift Cards' is negative in Mar 2026 (-300): likely credits/refunds; reviewer to confirm.
- **[medium] revenue_stream**: New revenue stream 'Wholesale Accounts': 12,000 in Sep 2026, zero in the prior 6 months.
- **[medium] gross_margin**: Gross margin Sep 2026 65.3% vs 59.6% in Aug 2026 (+5.7 pp); prior 6-month average 60.6%.
- **[medium] opex_category**: Opex category 'Payroll & Benefits' Sep 2026: 22,600 (+28.4% / +5,000 vs Aug 2026).
- **[info] gross_margin**: Gross margin range over the period: 56.8% (Mar 2026) to 65.3% (Sep 2026).
- **[info] data_quality**: 'Total Delivery' has no header row; grouped the 2 row(s) above it (Delivery Van Fuel, Courier: Same Day) because they sum to it in every month
- **[info] data_quality**: 'Charitable Donations' has no values and no 'Total Charitable Donations' row; treated as an all-blank account (0). The 4 row(s) after it were kept at the parent level, not grouped under it.
- **[info] mapping**: 3 expense account(s) matched no category rule and are grouped as 'Other Opex': Instagram Ads, Mystery Shopper Program, Supplier Rebates.

## 2. Revenue by stream

| Stream | Apr 2026 | May 2026 | Jun 2026 | Jul 2026 | Aug 2026 | Sep 2026 | MoM % (Sep 2026) | YoY % (same month) | TTM (n/a: <12 months) | TTM share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Bread Sales | 44,700 | 45,600 | 46,500 | 47,400 | 48,300 | 49,200 | +1.9% | n/a | n/a | n/a |
| Pastry Sales | 17,450 | 17,100 | 16,750 | 16,400 | 16,050 | 15,700 | -2.2% | n/a | n/a | n/a |
| Catering Revenue | 7,200 | 6,100 | 8,800 | 9,100 | 4,000 | 3,800 | -5.0% | n/a | n/a | n/a |
| Gift Cards | 600 | 550 | 500 | 650 | 700 | 600 | -14.3% | n/a | n/a | n/a |
| Wholesale Accounts | 0 | 0 | 0 | 0 | 0 | 12,000 | from 0 | n/a | n/a | n/a |
| **Total revenue** | 69,950 | 69,350 | 72,550 | 73,550 | 69,050 | 81,300 | +17.7% | n/a | n/a | n/a |

Month-over-month % by stream:

| Stream | Apr 2026 | May 2026 | Jun 2026 | Jul 2026 | Aug 2026 | Sep 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bread Sales | +2.1% | +2.0% | +2.0% | +1.9% | +1.9% | +1.9% |
| Pastry Sales | -2.0% | -2.0% | -2.0% | -2.1% | -2.1% | -2.2% |
| Catering Revenue | n/a | -15.3% | +44.3% | +3.4% | -56.0% | -5.0% |
| Gift Cards | +300.0% | -8.3% | -9.1% | +30.0% | +7.7% | -14.3% |
| Wholesale Accounts | n/a | n/a | n/a | n/a | n/a | n/a |
| Total revenue | +14.1% | -0.9% | +4.6% | +1.4% | -6.1% | +17.7% |

## 3. Gross margin trend

| Month | Revenue | COGS | Gross profit | GM % | Δ vs prior | TTM GM % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-01 | 67,000 | 25,900 | 41,100 | 61.3% | n/a | n/a |
| 2026-02 | 67,000 | 26,190 | 40,810 | 60.9% | -0.4 pp | n/a |
| 2026-03 | 61,300 | 26,480 | 34,820 | 56.8% | -4.1 pp | n/a |
| 2026-04 | 69,950 | 26,770 | 43,180 | 61.7% | +4.9 pp | n/a |
| 2026-05 | 69,350 | 27,060 | 42,290 | 61.0% | -0.7 pp | n/a |
| 2026-06 | 72,550 | 27,350 | 45,200 | 62.3% | +1.3 pp | n/a |
| 2026-07 | 73,550 | 27,640 | 45,910 | 62.4% | +0.1 pp | n/a |
| 2026-08 | 69,050 | 27,930 | 41,120 | 59.6% | -2.9 pp | n/a |
| 2026-09 | 81,300 | 28,220 | 53,080 | 65.3% | +5.7 pp | n/a |

## 4. Operating expenses by category

| Category | Apr 2026 | May 2026 | Jun 2026 | Jul 2026 | Aug 2026 | Sep 2026 | MoM % (Sep 2026) | TTM (n/a: <12 months) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Payroll & Benefits | 17,600 | 17,600 | 17,600 | 17,600 | 17,600 | 22,600 | +28.4% | n/a |
| Facilities & Office | 6,335 | 6,250 | 6,615 | 6,660 | 6,735 | 6,770 | +0.5% | n/a |
| Other Opex | 850 | 900 | 1,200 | 1,000 | 1,050 | 1,500 | +42.9% | n/a |
| Professional Fees | 700 | 700 | 700 | 700 | 700 | 700 | +0.0% | n/a |
| Finance & Admin | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a |
| **Operating expenses excl. non-operating items** | 25,485 | 25,450 | 26,115 | 25,960 | 26,085 | 31,570 | +21.0% | n/a |
| **Total operating expenses (as exported)** | 25,485 | 25,450 | 26,115 | 25,960 | 26,085 | 31,570 | +21.0% | n/a |

¹ Non-operating items that this export places inside operating expenses (tax, interest). Shown separately so one-off credits do not distort underlying opex; whether to reclassify them is the reviewer's call.

% changes use the absolute prior value as the base. For credit (negative) lines a positive % means *less negative*: read the Change column in section 5 for those.

Accounts in **Other Opex** (no category rule matched; extend `category_map.json` to classify them): Instagram Ads, Mystery Shopper Program, Supplier Rebates.

## 5. Largest movers: Sep 2026 vs Aug 2026

| Category | Aug 2026 | Sep 2026 | Change | MoM % |
| --- | ---: | ---: | ---: | ---: |
| Payroll & Benefits | 17,600 | 22,600 | 5,000 | +28.4% |
| Other Opex | 1,050 | 1,500 | 450 | +42.9% |
| Facilities & Office | 6,735 | 6,770 | 35 | +0.5% |

| Account | Category | Aug 2026 | Sep 2026 | Change | MoM % |
| --- | --- | ---: | ---: | ---: | ---: |
| Wages & Salaries | Payroll & Benefits | 16,000 | 21,000 | 5,000 | +31.2% |
| Mystery Shopper Program | Other Opex | 0 | 400 | 400 | from 0 |
| Instagram Ads | Other Opex | 1,300 | 1,350 | 50 | +3.8% |
| Utilities | Facilities & Office | 925 | 940 | 15 | +1.6% |
| Delivery Van Fuel | Facilities & Office | 710 | 720 | 10 | +1.4% |

## 6. Net income

|  | Apr 2026 | May 2026 | Jun 2026 | Jul 2026 | Aug 2026 | Sep 2026 | TTM (n/a: <12 months) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Net income (as exported) | 17,733 | 16,879 | 19,125 | 19,991 | 15,077 | 21,553 | n/a |
| Net income excl. non-operating items | 17,733 | 16,879 | 19,125 | 19,991 | 15,077 | 21,553 | n/a |

Negative in 0 of 9 months; current negative streak: 0 month(s). Positive months: Jan 2026, Feb 2026, Mar 2026, Apr 2026, May 2026, Jun 2026, Jul 2026, Aug 2026, Sep 2026.

## 7. Balance sheet snapshot

| Line | 6 months earlier | Aug 2026 | Sep 2026 |
| --- | ---: | ---: | ---: |
| Assets | 58,000 | 50,500 | 49,000 |
| Bank Accounts | 48,400 | 39,400 | 37,600 |
| Liabilities and Equity | 58,000 | 50,500 | 49,000 |
| Liabilities | 3,340 | 3,940 | 4,060 |
| Equity | 54,660 | 46,560 | 44,940 |

## 8. Data quality

| Check | Status | Detail |
| --- | --- | --- |
| every stated subtotal vs sum of its detail rows (income statement) | MISMATCH | 7 subtotal rows x 9 months checked; 1 mismatches |
| gross_profit recomputed from detail rows vs workbook 'Gross Profit' | PASS | matches in every month |
| net_income recomputed from detail rows vs workbook 'Net Profit' | PASS | matches in every month |
| operating_income vs workbook | SKIPPED | no such summary row in the sheet |
| balance sheet: 'Assets' = 'Liabilities and Equity' | PASS | balances in every month |
| every stated subtotal vs sum of its detail rows (balance sheet) | PASS | 5 subtotal rows checked; 0 mismatches |

Extraction warnings:

- `inferred_group`: 'Total Delivery' has no header row; grouped the 2 row(s) above it (Delivery Van Fuel, Courier: Same Day) because they sum to it in every month
- `missing_total`: 'Charitable Donations' has no values and no 'Total Charitable Donations' row; treated as an all-blank account (0). The 4 row(s) after it were kept at the parent level, not grouped under it.
- `subtotal_mismatch`: 'Total for Professional Services' in Mar 2026 states 2,225.00 but its detail rows sum to 2,200.00 (diff 25.00). Analysis uses the detail rows; reviewer to confirm.

## 9. How each expense account was categorised

<details><summary>Account → category (click to expand)</summary>

| Account | Category | Matched on | Sep 2026 | TTM |
| --- | --- | --- | ---: | ---: |
| Wages & Salaries | Payroll & Benefits | account 'Wages & Salaries' | 21,000 | n/a |
| Payroll Taxes | Payroll & Benefits | account 'Payroll Taxes' | 1,600 | n/a |
| Rent - High Street | Facilities & Office | account 'Rent - High Street' | 4,500 | n/a |
| Utilities | Facilities & Office | account 'Utilities' | 940 | n/a |
| Equipment Repairs | Facilities & Office | account 'Equipment Repairs' | 300 | n/a |
| Delivery Van Fuel | Facilities & Office | account 'Delivery Van Fuel' | 720 | n/a |
| Courier: Same Day | Facilities & Office | account 'Courier: Same Day' | 310 | n/a |
| Charitable Donations | Finance & Admin | account 'Charitable Donations' | 0 | n/a |
| Instagram Ads | Other Opex | no rule matched | 1,350 | n/a |
| Mystery Shopper Program | Other Opex | no rule matched | 400 | n/a |
| Bookkeeping | Professional Fees | account 'Bookkeeping' | 700 | n/a |
| Legal | Professional Fees | account 'Legal' | 0 | n/a |
| Supplier Rebates | Other Opex | no rule matched | (250) | n/a |

</details>

## 10. For the reviewer

This report does **not**: forecasting; accounting judgments (accruals, reclassifications, one-off treatment); currency conversion; causal explanations beyond what the numbers show.

- [ ] Confirm the data-quality section (any mismatch: which number is right?)
- [ ] Decide how to treat flagged one-off / non-operating items
- [ ] Check the 'Other' category assignments and the account mapping appendix
- [ ] Add business context the numbers cannot show (pricing changes, churn, hires, timing)
- [ ] Edit the commentary and remove the DRAFT banner when final

import { formatMoney } from '../format.js'

const PNL_ROWS = [
  ['total_income', 'Total income'],
  ['cost_of_goods_sold', 'Cost of goods sold'],
  ['gross_profit', 'Gross profit'],
  ['total_expenses', 'Total expenses'],
  ['net_operating_income', 'Net operating income'],
  ['other_income', 'Other income'],
  ['other_expenses', 'Other expenses'],
  ['net_income', 'Net income'],
]

// Shows only figures QuickBooks returned; absent sections are omitted, not shown as zero.
export default function TestResult({ result }) {
  const pnl = result.profit_and_loss
  const rows = PNL_ROWS.filter(([key]) => pnl.totals[key] !== undefined)

  return (
    <div className="result" role="status">
      <p className="result-company">
        <span className="ok-mark" aria-hidden="true">✓</span> Connected to <strong>{result.company.name || 'Unnamed company'}</strong>
        {result.company.country && <span className="muted"> ({result.company.country})</span>}
        <span className="muted small"> via {result.api_host}</span>
      </p>

      {pnl.has_data ? (
        <table className="pnl">
          <caption>
            Profit &amp; Loss, {pnl.start_date} to {pnl.end_date}
            {pnl.basis && ` (${pnl.basis.toLowerCase()} basis)`}
          </caption>
          <tbody>
            {rows.map(([key, label]) => (
              <tr key={key} className={key === 'net_income' ? 'pnl-total' : undefined}>
                <th scope="row">{label}</th>
                <td>{formatMoney(pnl.totals[key], pnl.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">
          No Profit &amp; Loss activity between {pnl.start_date} and {pnl.end_date} in this sandbox company.
        </p>
      )}
    </div>
  )
}

import { lex } from './lex.js'

// Markdown -> React elements. marked is used ONLY as a lexer (tokens); this file builds the elements, so no HTML
// string is ever produced and nothing goes through dangerouslySetInnerHTML. Raw HTML in the source is never
// rendered: comments are dropped, <details><summary> blocks become a real <details> element, anything else is
// shown as plain text. Links go only to https:// URLs or to other saved results; everything else is plain text.

const STATUS_WORD = /\b(PASS|FAIL|BLOCKED|UNSTABLE|SKIP|AGREES|DISAGREES)\b/
const NUMERIC_CELL = /^[\s(+\-−$≈~]*\d[\d,]*(\.\d+)?\s*(%|pp)?\)?\s*$/
const DETAILS_OPEN = /^\s*<details>\s*<summary>([\s\S]*?)<\/summary>\s*$/i
const DETAILS_CLOSE = /^\s*<\/details>\s*$/i
const COMMENT = /^\s*<!--[\s\S]*-->\s*$/

export function StatusBadge({ status }) {
  const tone = { PASS: 'pass', AGREES: 'pass', FAIL: 'fail', DISAGREES: 'fail', BLOCKED: 'fail', UNSTABLE: 'warn', SKIP: 'skip' }
  return <span className={`status-badge status-badge-${tone[status] || 'skip'}`}>{status}</span>
}

const plainText = (tokens) => (tokens || []).map((t) => (t.tokens ? plainText(t.tokens) : t.text || '')).join('')

// Status words become badges (text + colour) only where they state a result: a table cell that is just the word,
// or a short bold label such as **PASS** or **Result: PASS.** Running prose ("FAIL if the claim is missing")
// stays plain text, so rules and explanations never look like failed results.
function withBadges(text, key) {
  const parts = String(text).split(STATUS_WORD)
  if (parts.length === 1) return text
  return parts.map((part, i) => (i % 2 ? <StatusBadge key={`${key}-${i}`} status={part} /> : part))
}

function linkTarget(href, resolveLink) {
  if (/^https:\/\//i.test(href)) return { external: href }
  const internal = resolveLink?.(href)
  return internal ? { internal } : null
}

export function Inline({ tokens, resolveLink }) {
  return (tokens || []).map((t, i) => {
    switch (t.type) {
      case 'strong': {
        const label = plainText(t.tokens)
        if (label.length <= 24 && STATUS_WORD.test(label)) return <strong key={i}>{withBadges(label, i)}</strong>
        return <strong key={i}><Inline tokens={t.tokens} resolveLink={resolveLink} /></strong>
      }
      case 'em':
        return <em key={i}><Inline tokens={t.tokens} resolveLink={resolveLink} /></em>
      case 'del':
        return <del key={i}><Inline tokens={t.tokens} resolveLink={resolveLink} /></del>
      case 'codespan':
        return <code key={i}>{t.text}</code>
      case 'br':
        return <br key={i} />
      case 'link': {
        const target = linkTarget(t.href, resolveLink)
        const label = <Inline tokens={t.tokens} resolveLink={resolveLink} />
        if (target?.external)
          return <a key={i} href={target.external} target="_blank" rel="noopener noreferrer">{label}</a>
        if (target?.internal) return <a key={i} href={target.internal}>{label}</a>
        return <span key={i} className="md-path" title={t.href}>{label}</span>   // repo file: not navigable here
      }
      case 'image':
        return <span key={i} className="muted">[{t.text}]</span>             // never load remote images
      case 'html':
        return COMMENT.test(t.raw) ? null : <span key={i}>{t.raw}</span>     // shown as text, never as HTML
      case 'text':
        return t.tokens ? <Inline key={i} tokens={t.tokens} resolveLink={resolveLink} /> : t.text
      case 'escape':
        return t.text
      default:
        return t.raw || null
    }
  })
}

function Cell({ cell, resolveLink }) {
  const text = plainText(cell.tokens).trim()
  if (new RegExp(`^${STATUS_WORD.source}$`).test(text)) return <StatusBadge status={text} />
  return <Inline tokens={cell.tokens} resolveLink={resolveLink} />
}

const cellText = (cell) => (cell.text || '').trim()

function Table({ token, resolveLink }) {
  const alignOf = (i, cell) => token.align[i] || (NUMERIC_CELL.test(cellText(cell)) ? 'right' : null)
  return (
    <div className="table-wrap">
      <table className="md-table">
        <thead>
          <tr>
            {token.header.map((cell, i) => (
              <th key={i} scope="col" className={token.align[i] ? `align-${token.align[i]}` : undefined}>
                <Inline tokens={cell.tokens} resolveLink={resolveLink} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {token.rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, i) => {
                const align = alignOf(i, cell)
                return (
                  <td key={i} className={align ? `align-${align}` : undefined}>
                    <Cell cell={cell} resolveLink={resolveLink} />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Group <details><summary>…</summary> … </details> html tokens into nested blocks.
function groupDetails(tokens) {
  const out = []
  for (let i = 0; i < tokens.length; i++) {
    const open = tokens[i].type === 'html' && DETAILS_OPEN.exec(tokens[i].raw)
    if (!open) {
      out.push(tokens[i])
      continue
    }
    const inner = []
    let depth = 1
    for (i += 1; i < tokens.length; i++) {
      const t = tokens[i]
      if (t.type === 'html' && DETAILS_OPEN.test(t.raw)) depth += 1
      if (t.type === 'html' && DETAILS_CLOSE.test(t.raw) && --depth === 0) break
      inner.push(t)
    }
    out.push({ type: 'details', summary: open[1].replace(/<[^>]*>/g, '').trim(), tokens: inner })
  }
  return out
}

export function Blocks({ tokens, resolveLink, headingOffset = 1 }) {
  return groupDetails(tokens || []).map((t, i) => {
    switch (t.type) {
      case 'heading': {
        const Tag = `h${Math.min(6, t.depth + headingOffset)}`
        return <Tag key={i} className="md-heading"><Inline tokens={t.tokens} resolveLink={resolveLink} /></Tag>
      }
      case 'paragraph':
        return <p key={i}><Inline tokens={t.tokens} resolveLink={resolveLink} /></p>
      case 'text':
        return <p key={i}><Inline tokens={t.tokens || [t]} resolveLink={resolveLink} /></p>
      case 'list': {
        const Tag = t.ordered ? 'ol' : 'ul'
        return (
          <Tag key={i} start={t.ordered && t.start !== 1 ? t.start : undefined}>
            {t.items.map((item, j) => (
              <li key={j}>
                {item.tokens.length === 1 && item.tokens[0].type === 'text' ? (
                  <Inline tokens={item.tokens[0].tokens || [item.tokens[0]]} resolveLink={resolveLink} />
                ) : (
                  <Blocks tokens={item.tokens} resolveLink={resolveLink} headingOffset={headingOffset} />
                )}
              </li>
            ))}
          </Tag>
        )
      }
      case 'table':
        return <Table key={i} token={t} resolveLink={resolveLink} />
      case 'blockquote':
        return (
          <blockquote key={i}>
            <Blocks tokens={t.tokens} resolveLink={resolveLink} headingOffset={headingOffset} />
          </blockquote>
        )
      case 'code':
        return <pre key={i} className="md-code"><code>{t.text}</code></pre>
      case 'hr':
        return <hr key={i} />
      case 'details':
        return (
          <details key={i} className="md-details">
            <summary>{t.summary}</summary>
            <Blocks tokens={t.tokens} resolveLink={resolveLink} headingOffset={headingOffset} />
          </details>
        )
      case 'html':
        return COMMENT.test(t.raw) || DETAILS_CLOSE.test(t.raw) ? null : <pre key={i} className="md-code">{t.raw}</pre>
      case 'space':
        return null
      default:
        return t.raw ? <p key={i}>{t.raw}</p> : null
    }
  })
}

export default function Markdown({ text, tokens, resolveLink, headingOffset }) {
  return (
    <div className="md">
      <Blocks tokens={tokens || lex(text)} resolveLink={resolveLink} headingOffset={headingOffset} />
    </div>
  )
}

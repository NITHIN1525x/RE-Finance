// Splits each saved submission file into "request" and "response" parts for the Results page.
// Pure functions over the Markdown tokens. They only use the structure scripts/build_submission.py emits
// (headings, table columns, the --- separator), never copies of its content.
import { lex } from './lex.js'
import { SUBMISSION } from './sources.js'

const FILES = {
  task1: 'Task 1 response.md',
  task2: 'Task 2 response.md',
  task3: 'Task 3 response.md',
  qa: 'Q&A log.md',
}
const CASE_FILE = /^Task 3\.(\d+)\.md$/

const plain = (tokens) =>
  (tokens || []).map((t) => (t.tokens ? plain(t.tokens) : t.type === 'codespan' ? t.text : t.text || '')).join('')

// { title, preamble, sections: [{ title, tokens }] } split at level-2 headings.
function outline(tokens) {
  const doc = { title: null, preamble: [], sections: [] }
  for (const t of tokens) {
    if (t.type === 'heading' && t.depth === 1 && doc.title === null) doc.title = plain(t.tokens)
    else if (t.type === 'heading' && t.depth === 2) doc.sections.push({ title: plain(t.tokens), tokens: [] })
    else (doc.sections.at(-1)?.tokens || doc.preamble).push(t)
  }
  return doc
}

const section = (doc, prefix) => doc.sections.find((s) => s.title.startsWith(prefix))
const firstTable = (tokens) => (tokens || []).find((t) => t.type === 'table')
const tableRow = (table, label) => table?.rows.find((row) => plain(row[0].tokens).trim() === label)
const withoutTitle = (tokens) => tokens.filter((t) => !(t.type === 'heading' && t.depth === 1))

function load(name) {
  const raw = SUBMISSION[name]
  if (!raw) return null
  const tokens = lex(raw)
  return { name, raw, tokens, doc: outline(tokens) }
}

const caseNames = () =>
  Object.keys(SUBMISSION)
    .filter((n) => CASE_FILE.test(n))
    .sort((a, b) => Number(CASE_FILE.exec(a)[1]) - Number(CASE_FILE.exec(b)[1]))

export const itemId = (name) =>
  name === FILES.task1 ? 'task-1' : name === FILES.task2 ? 'task-2' : name === FILES.task3 ? 'task-3'
    : name === FILES.qa ? 'qa' : CASE_FILE.test(name) ? `task-3-${CASE_FILE.exec(name)[1]}` : null

// Links between saved files (e.g. "Task 3.1.md" in the summary table) become in-page navigation.
export function resolveLink(href) {
  let name
  try {
    name = decodeURIComponent(href).split('/').pop()
  } catch {
    return null
  }
  const id = SUBMISSION[name] ? itemId(name) : null
  return id ? `#results/${id}` : null
}

// ---------------------------------------------------------------------------------------- Task 1
function task1() {
  const f = load(FILES.task1)
  if (!f) return null
  const qa = firstTable(section(f.doc, 'Questions and answers')?.tokens)
  return {
    id: 'task-1',
    label: 'Task 1',
    title: f.doc.title,
    file: f.name,
    generated: /Run at (\S+?) \(UTC\)/.exec(f.raw)?.[1] || null,
    requestNote: 'Asked of the QuickBooks sandbox through the official MCP server (no Claude model involved).',
    questions: qa ? qa.rows.map((row) => row[1].tokens) : [],
    response: withoutTitle(f.tokens),
  }
}

// ---------------------------------------------------------------------------------------- Task 2
function task2() {
  const f = load(FILES.task2)
  if (!f) return null
  const header = firstTable(f.doc.preamble)
  const pick = (labels) => labels.map((l) => [l, tableRow(header, l)]).filter(([, row]) => row)
  const hr = f.tokens.findIndex((t) => t.type === 'hr')
  return {
    id: 'task-2',
    label: 'Task 2',
    title: f.doc.title,
    file: f.name,
    generated: /task2-generated-at: (\S+)/.exec(f.raw)?.[1] || null,
    request: pick(['Workbook', 'Company', 'Period']),
    provenance: pick(['Report generated', 'Source report', 'Commentary written by']),
    note: f.doc.preamble.filter((t) => t.type === 'blockquote'),
    response: hr >= 0 ? f.tokens.slice(hr + 1) : withoutTitle(f.tokens),
  }
}

// ---------------------------------------------------------------------------------------- Task 3 summary
function task3(cases) {
  const f = load(FILES.task3)
  if (!f) return null
  const fields = firstTable(f.doc.preamble)
  return {
    id: 'task-3',
    label: 'Summary',
    title: f.doc.title,
    file: f.name,
    // "start to finish" in the file; the run's results were saved when it finished
    generated: /\S+\s+to\s+(\S+)/.exec(plain(tableRow(fields, 'Date (UTC)')?.[1]?.tokens))?.[1] || null,
    cases: cases.map((c) => ({ id: c.id, label: c.label, title: c.title, tests: c.testsTokens, status: c.status })),
    response: withoutTitle(f.tokens),
    doc: f.doc,
  }
}

// ---------------------------------------------------------------------------------------- Task 3.x cases
// The case's own results, cut out of Task 3 response.md: its per-case row, its rows in each check table, and
// its commentary verdicts. Rows are matched by the case letter / "Task 3.N" label the generator writes.
function caseResults(summaryDoc, n, letter) {
  if (!summaryDoc) return { status: null, tokens: [] }
  const out = []
  let status = null
  const perCase = firstTable(section(summaryDoc, 'Per case')?.tokens)
  const row = perCase?.rows.find((r) => plain(r[0].tokens).includes(`Task 3.${n}`))
  if (row) {
    status = plain(row[2].tokens).trim()
    out.push({ type: 'table', header: perCase.header.slice(2), align: perCase.align.slice(2), rows: [row.slice(2)] })
  }
  for (const s of summaryDoc.sections) {
    const table = firstTable(s.tokens)
    if (table && plain(table.header[0].tokens).trim() === 'Case') {
      const rows = table.rows.filter((r) => plain(r[0].tokens).trim() === letter)
      if (rows.length) {
        out.push({ type: 'heading', depth: 3, tokens: [{ type: 'text', text: s.title }] })
        out.push({ type: 'table', header: table.header.slice(1), align: table.align.slice(1), rows: rows.map((r) => r.slice(1)) })
      }
    } else if (s.title.startsWith('Commentary')) {
      const start = s.tokens.findIndex((t) => t.type === 'paragraph' && t.raw.startsWith(`**Task 3.${n} (`))
      if (start >= 0) {
        const rest = s.tokens.slice(start + 1)
        const end = rest.findIndex((t) => t.type === 'paragraph' && t.raw.startsWith('**Task 3.'))
        out.push({ type: 'heading', depth: 3, tokens: [{ type: 'text', text: s.title }] })
        out.push(...(end >= 0 ? rest.slice(0, end) : rest))
      }
    }
  }
  return { status, tokens: out }
}

function caseItem(name, summaryDoc) {
  const f = load(name)
  const n = CASE_FILE.exec(name)[1]
  const letter = /Case id:\*\* `([a-z])_/.exec(f.raw)?.[1] || null
  const tests = section(f.doc, 'What it tests')
  const results = caseResults(summaryDoc, n, letter)
  return {
    id: `task-3-${n}`,
    label: `Case 3.${n}`,
    letter,
    title: f.doc.title,
    file: name,
    generated: null, // case files are generated from evals/goldens/cases.json and carry no timestamp
    testsTokens: tests ? tests.tokens.filter((t) => t.type === 'paragraph').slice(0, 1) : [],
    request: [...f.doc.preamble, ...(tests?.tokens || []), ...(section(f.doc, 'Input')?.tokens || [])],
    expected: f.doc.sections
      .filter((s) => /^(Expected results|Required claims|Forbidden content)/.test(s.title))
      .flatMap((s) => [{ type: 'heading', depth: 3, tokens: [{ type: 'text', text: s.title }] }, ...s.tokens]),
    grading: [...(section(f.doc, 'How it is graded')?.tokens || []), ...(section(f.doc, 'Change log')?.tokens || [])],
    status: results.status,
    results: results.tokens,
  }
}

// ---------------------------------------------------------------------------------------- Q&A log
// One level-2 section per entry (newest first, as scripts/log_answer.py writes it). The question and data source
// are the request; the answer and the figures it cites are the response.
const REQUEST_FIELDS = /^\*\*(Question|Data source):\*\*/

function qa() {
  const f = load(FILES.qa)
  if (!f) return null
  const entries = f.doc.sections.map((s) => ({
    title: s.title,
    answered: /\*\*Answered:\*\*[ \t]*([^\r\n]+)/.exec(s.tokens.map((t) => t.raw).join(''))?.[1].trim() || null,
    request: s.tokens.filter((t) => t.type === 'paragraph' && REQUEST_FIELDS.test(t.raw)),
    response: s.tokens.filter(
      (t) => !(t.type === 'paragraph' && (REQUEST_FIELDS.test(t.raw) || t.raw.startsWith('**Answered:**'))),
    ),
  }))
  return {
    id: 'qa',
    label: 'Q&A',
    title: f.doc.title,
    file: f.name,
    generated: entries[0]?.answered || null,
    intro: f.doc.preamble,
    entries,
  }
}

export function buildResults() {
  const summary = load(FILES.task3)
  const cases = caseNames().map((name) => caseItem(name, summary?.doc))
  const t3 = task3(cases)
  return {
    qa: qa(),
    task1: task1(),
    task2: task2(),
    task3: t3,
    cases,
    runGenerated: t3?.generated || null,
    runLabel: summary ? summary.doc.preamble.find((t) => t.type === 'paragraph') : null,
  }
}

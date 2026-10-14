import { useMemo } from 'react'
import { formatDateTime } from '../format.js'
import Markdown, { Blocks, Inline, StatusBadge } from '../results/Markdown.jsx'
import { buildResults, resolveLink } from '../results/content.js'

// A timestamp that can't be parsed is shown as written rather than breaking the page.
function when(value) {
  return Number.isNaN(new Date(value).getTime()) ? value : formatDateTime(value)
}

// Read-only view of the SAVED results in <repo>/submission/ (bundled at build time). It calls no API and
// never asks Claude anything: what it shows is exactly what scripts/build_submission.py last generated.

function Saved({ when: stamp, children }) {
  return (
    <p className="saved" title={stamp || undefined}>
      <span className="saved-label">Saved result</span>{' '}
      {stamp ? <>generated {when(stamp)} <span className="muted">({stamp})</span></> : children}
    </p>
  )
}

function Panel({ kind, title, children }) {
  return (
    <section className={`qa-panel qa-${kind}`} aria-label={title}>
      <h3 className="qa-title">{title}</h3>
      {children}
    </section>
  )
}

function Missing({ file }) {
  return (
    <div className="notice notice-warning" role="status">
      <span>
        <code>submission/{file}</code> has not been generated yet. Run <code>python scripts/build_submission.py</code>
        {file.startsWith('Task 1') && <> with <code>--live-task1</code></>} and rebuild the console.
      </span>
    </div>
  )
}

function Task1View({ item }) {
  return (
    <>
      <Saved when={item.generated} />
      <Panel kind="request" title="Question / request">
        <p className="muted">{item.requestNote}</p>
        <ol className="question-list">
          {item.questions.map((tokens, i) => (
            <li key={i}><Inline tokens={tokens} resolveLink={resolveLink} /></li>
          ))}
        </ol>
      </Panel>
      <Panel kind="response" title="Response / result">
        <Markdown tokens={item.response} resolveLink={resolveLink} />
      </Panel>
    </>
  )
}

function FieldList({ rows }) {
  return (
    <dl className="field-list">
      {rows.map(([label, row]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd><Inline tokens={row[1].tokens} resolveLink={resolveLink} /></dd>
        </div>
      ))}
    </dl>
  )
}

function Task2View({ item }) {
  return (
    <>
      <Saved when={item.generated} />
      <Panel kind="request" title="Question / request">
        <p className="muted">Monthly trend analysis requested for:</p>
        <FieldList rows={item.request} />
      </Panel>
      <Panel kind="response" title="Response / result">
        <FieldList rows={item.provenance} />
        <Blocks tokens={item.note} resolveLink={resolveLink} />
        <Markdown tokens={item.response} resolveLink={resolveLink} />
      </Panel>
    </>
  )
}

function Task3View({ item }) {
  return (
    <>
      <Saved when={item.generated} />
      <Panel kind="request" title="Question / request">
        <p className="muted">Grade the skill against the golden cases:</p>
        <ul className="case-index">
          {item.cases.map((c) => (
            <li key={c.id}>
              <a href={`#results/${c.id}`}>{c.label}</a>
              {c.status && <StatusBadge status={c.status} />}
              <span className="muted"> <Inline tokens={c.tests[0]?.tokens} /></span>
            </li>
          ))}
        </ul>
      </Panel>
      <Panel kind="response" title="Response / result">
        <Markdown tokens={item.response} resolveLink={resolveLink} />
      </Panel>
    </>
  )
}

function QaView({ item }) {
  return (
    <>
      <Saved when={null}>
        {item.entries.length ? <>newest entry answered {item.entries[0].answered || 'at an unrecorded time'}</> : 'no entries yet'}
        {' · '}appended with <code>/log-answer</code>
      </Saved>
      <Blocks tokens={item.intro} resolveLink={resolveLink} />
      {item.entries.map((entry, i) => (
        <section key={i} className="qa-entry" aria-label={entry.title}>
          <h3 className="qa-entry-title">
            {entry.title}
            {i === 0 && <span className="badge status-connected">Newest</span>}
          </h3>
          <Panel kind="request" title="Question / request">
            <Markdown tokens={entry.request} resolveLink={resolveLink} />
          </Panel>
          <Panel kind="response" title="Response / result">
            <Markdown tokens={entry.response} resolveLink={resolveLink} />
          </Panel>
        </section>
      ))}
    </>
  )
}

function CaseView({ item, runGenerated, runLabel }) {
  return (
    <>
      <Saved when={null}>
        expectations generated from <code>evals/goldens/cases.json</code> (no timestamp in the file); results from
        the eval run {runGenerated ? <>finished {when(runGenerated)} <span className="muted">({runGenerated})</span></> : 'summary'}
      </Saved>
      <Panel kind="request" title="Question / request">
        <Markdown tokens={item.request} resolveLink={resolveLink} />
      </Panel>
      <Panel kind="expected" title="Expected (golden case)">
        <Markdown tokens={item.expected} resolveLink={resolveLink} />
        <details className="md-details">
          <summary>How it is graded</summary>
          <Markdown tokens={item.grading} resolveLink={resolveLink} />
        </details>
      </Panel>
      <Panel kind="response" title="Response / result">
        <p className="case-status">
          Case result: {item.status ? <StatusBadge status={item.status} /> : <span className="muted">not in the run summary</span>}
        </p>
        {runLabel && <Blocks tokens={[runLabel]} resolveLink={resolveLink} />}
        <Markdown tokens={item.results} resolveLink={resolveLink} />
      </Panel>
    </>
  )
}

export default function Results({ selected }) {
  const data = useMemo(() => buildResults(), [])
  const items = [data.task1 && { ...data.task1, group: 'Task 1' }, data.task2 && { ...data.task2, group: 'Task 2' }]
  const task3Items = [data.task3, ...data.cases].filter(Boolean)
  const all = [...items.filter(Boolean), ...task3Items, data.qa && { ...data.qa, group: 'Q&A' }].filter(Boolean)
  const missing = { 'task-1': !data.task1 && 'Task 1 response.md', 'task-2': !data.task2 && 'Task 2 response.md',
    'task-3': !data.task3 && 'Task 3 response.md', qa: !data.qa && 'Q&A log.md' }[selected]
  const current = missing ? null : all.find((x) => x.id === selected) || all[0]

  return (
    <div className="results">
      <nav className="results-nav" aria-label="Saved results">
        <ul>
          {[['task-1', 'Task 1', data.task1], ['task-2', 'Task 2', data.task2]].map(([id, label, item]) => (
            <li key={id}>
              <a href={`#results/${id}`} aria-current={current?.id === id ? 'page' : undefined}>
                {label}
                {!item && <span className="muted small"> (missing)</span>}
              </a>
            </li>
          ))}
          <li className="results-nav-group">
            <span className="results-nav-heading">Task 3</span>
            <ul>
              {task3Items.map((item) => (
                <li key={item.id}>
                  <a href={`#results/${item.id}`} aria-current={current?.id === item.id ? 'page' : undefined}>
                    <span>{item.label}</span>
                    {item.status && <StatusBadge status={item.status} />}
                  </a>
                </li>
              ))}
            </ul>
          </li>
          <li className="results-nav-group">
            <a href="#results/qa" aria-current={current?.id === 'qa' ? 'page' : undefined}>
              <span>Q&amp;A</span>
              {data.qa ? <span className="muted small">{data.qa.entries.length}</span> : <span className="muted small">(missing)</span>}
            </a>
          </li>
        </ul>
      </nav>

      <article className="results-body panel" aria-labelledby="results-title">
        {missing && <Missing file={missing} />}
        {!missing && !current && <Missing file="Task 3 response.md" />}
        {current && (
          <>
            <header className="results-header">
              <p className="results-kicker">{current.group || 'Task 3'} · read-only</p>
              <h2 id="results-title">{current.title}</h2>
              <p className="muted small">
                Source: <code>submission/{current.file}</code>
              </p>
            </header>
            {current.id === 'task-1' && <Task1View item={current} />}
            {current.id === 'task-2' && <Task2View item={current} />}
            {current.id === 'task-3' && <Task3View item={current} />}
            {current.id === 'qa' && <QaView item={current} />}
            {current.id.startsWith('task-3-') && (
              <CaseView item={current} runGenerated={data.runGenerated} runLabel={data.runLabel} />
            )}
          </>
        )}
      </article>
    </div>
  )
}

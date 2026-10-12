// Inline message. Errors use role="alert" (announced immediately); the rest are polite status updates.
export default function Notice({ tone = 'info', children, onDismiss }) {
  const isAlert = tone === 'error' || tone === 'warning'
  return (
    <div className={`notice notice-${tone}`} role={isAlert ? 'alert' : 'status'}>
      <span>{children}</span>
      {onDismiss && (
        <button type="button" className="notice-dismiss" onClick={onDismiss} aria-label="Dismiss message">
          ×
        </button>
      )}
    </div>
  )
}

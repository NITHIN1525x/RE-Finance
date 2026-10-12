import { useEffect, useRef } from 'react'

// Native <dialog>: modal focus handling and Esc-to-close come from the browser.
export default function ConfirmDialog({ open, title, children, confirmLabel, onConfirm, onCancel }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog ref={ref} className="dialog" aria-labelledby="dialog-title" onCancel={onCancel}>
      <h2 id="dialog-title">{title}</h2>
      <p>{children}</p>
      <div className="actions actions-end">
        <button type="button" className="button button-quiet" onClick={onCancel} autoFocus>
          Cancel
        </button>
        <button type="button" className="button button-danger" onClick={onConfirm}>
          {confirmLabel}
        </button>
      </div>
    </dialog>
  )
}

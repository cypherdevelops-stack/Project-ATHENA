import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';

type ConfirmModalProps = {
  title: string;
  message: string;
  confirmLabel?: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmModal({
  title,
  message,
  confirmLabel = 'Confirm',
  busy = false,
  onCancel,
  onConfirm,
}: ConfirmModalProps) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !busy) onCancel();
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [busy, onCancel]);

  return (
    <div className="confirm-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && !busy && onCancel()}>
      <section className="confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="confirm-modal-title" aria-describedby="confirm-modal-message">
        <div className="confirm-modal-icon" aria-hidden="true"><AlertTriangle size={24} /></div>
        <div className="confirm-modal-copy">
          <h2 id="confirm-modal-title">{title}</h2>
          <p id="confirm-modal-message">{message}</p>
        </div>
        <div className="confirm-modal-actions">
          <button type="button" className="form-cancel" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="button" className="confirm-delete-button" onClick={onConfirm} disabled={busy}>{busy ? 'Deleting...' : confirmLabel}</button>
        </div>
      </section>
    </div>
  );
}

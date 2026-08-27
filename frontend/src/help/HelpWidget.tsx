import { useEffect, useRef, useState, type FormEvent } from 'react';
import { HelpCircle, Paperclip, Send, X } from 'lucide-react';
import { submitHelpRequest } from './helpService';

type HelpMessage = { id: string; author: 'user' | 'support'; text: string; attachments?: string[] };

export function HelpWidget() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [messages, setMessages] = useState<HelpMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  function handleFiles(event: React.ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []).slice(0, 5));
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if ((!message.trim() && files.length === 0) || sending) return;
    const sentMessage = message.trim();
    const sentFiles = files;
    setSending(true);
    setError(null);
    try {
      const result = await submitHelpRequest(sentMessage, sentFiles);
      setMessages((current) => [
        ...current,
        { id: `${result.id}-user`, author: 'user', text: sentMessage || 'Attached files', attachments: sentFiles.map((file) => file.name) },
        { id: `${result.id}-support`, author: 'support', text: result.message },
      ]);
      setMessage('');
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to send your request.');
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {open && <section className="help-panel" role="dialog" aria-modal="false" aria-labelledby="help-panel-title">
        <header className="help-panel-header">
          <h2 id="help-panel-title">Help</h2>
          <button type="button" className="help-close" aria-label="Close help" onClick={() => setOpen(false)}><X size={18} /></button>
        </header>
        <div className="help-messages" aria-live="polite">
          {messages.length === 0 && <p className="help-empty">How can we help with your ATHENA workspace?</p>}
          {messages.map((item) => <div className={`help-message help-message-${item.author}`} key={item.id}>
            <p>{item.text}</p>
            {item.attachments && item.attachments.length > 0 && <small>{item.attachments.join(', ')}</small>}
          </div>)}
        </div>
        {error && <p className="help-error" role="alert">{error}</p>}
        {files.length > 0 && <p className="help-attachments">{files.map((file) => file.name).join(', ')}</p>}
        <form className="help-composer" onSubmit={(event) => void handleSubmit(event)}>
          <button type="button" className="help-composer-button" aria-label="Attach files" title="Attach files" onClick={() => fileInputRef.current?.click()} disabled={sending}><Paperclip size={17} /></button>
          <input ref={fileInputRef} className="help-file-input" type="file" multiple onChange={handleFiles} />
          <input className="help-input" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ask for help..." aria-label="Help message" disabled={sending} />
          <button type="submit" className="help-send-button" aria-label="Send help request" title="Send" disabled={sending || (!message.trim() && files.length === 0)}><Send size={17} /></button>
        </form>
      </section>}
      <button type="button" className="help-floating-button" aria-label="Open help" title="Help" onClick={() => setOpen(true)}><HelpCircle size={22} /></button>
    </>
  );
}

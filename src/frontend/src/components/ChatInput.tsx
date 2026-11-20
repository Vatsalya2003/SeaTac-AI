import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { ArrowUp, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  /** true while an answer is coming: the box and the send button are disabled */
  disabled?: boolean;
}

const MAX_LINES = 6;

export function ChatInput({ onSendMessage, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = message.trim().length > 0 && !disabled;

  // grow with the text, up to 6 lines, then scroll
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    const style = getComputedStyle(el);
    const line = parseFloat(style.lineHeight) || 24;
    const max = line * MAX_LINES + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, max)}px`;
    el.style.overflowY = el.scrollHeight > max ? 'auto' : 'hidden';
  }, [message]);

  // focus on load and when an answer has arrived (not on small screens, where it would open the keyboard)
  useEffect(() => {
    if (!disabled && window.matchMedia('(min-width: 768px)').matches) textareaRef.current?.focus();
  }, [disabled]);

  const send = () => {
    if (!canSend) return;
    onSendMessage(message.trim());
    setMessage('');
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    send();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends, Shift+Enter adds a line (and Enter while composing text, e.g. an IME, does nothing)
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="sea-composer">
      <form className="sea-composer-box" onSubmit={handleSubmit} aria-busy={disabled}>
        <label htmlFor="chat-input" className="sea-sr-only">Ask a question about SeaTac airfield operations</label>
        <textarea
          ref={textareaRef}
          id="chat-input"
          rows={1}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Waiting for the answer…' : 'Ask about taxi times, runway use, delays…'}
          disabled={disabled}
          aria-describedby="chat-input-hint"
        />
        <button type="submit" className="sea-send" disabled={!canSend}
                aria-label={disabled ? 'Waiting for the answer' : 'Send question'}>
          {disabled ? <Loader2 className="sea-spin" aria-hidden="true" /> : <ArrowUp aria-hidden="true" />}
        </button>
      </form>
      <p id="chat-input-hint" className="sea-composer-hint">Enter to send · Shift+Enter for a new line</p>
    </div>
  );
}

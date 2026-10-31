import { useState, useRef, type KeyboardEvent, type ChangeEvent } from 'react';
import { ArrowUp, Square } from 'lucide-react';

interface Props {
  onSend: (text: string) => void;
  isLoading: boolean;
}

export function Composer({ onSend, isLoading }: Props) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const composingRef = useRef(false);

  const autoGrow = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 140) + 'px';
  };

  const handleInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    autoGrow();
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setText('');
    // Reset height after clearing
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.focus();
      }
    });
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !composingRef.current) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = text.trim().length > 0 && !isLoading;

  return (
    <div
      className="shrink-0 border-t border-border bg-surface px-4 py-3 sm:px-6"
      style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
    >
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-xl border border-border bg-bg px-3 py-2 transition-all focus-within:border-primary focus-within:shadow-[0_0_0_3px_var(--primary-light)]">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => {
              composingRef.current = true;
            }}
            onCompositionEnd={() => {
              composingRef.current = false;
            }}
            placeholder="Ask anything about MITS..."
            className="max-h-[140px] min-h-[24px] flex-1 resize-none border-0 bg-transparent text-[15px] leading-relaxed text-text outline-none placeholder:text-text-muted"
            style={{ fontSize: 'max(15px, 1rem)' }}
            autoComplete="off"
            spellCheck
            aria-label="Ask a question"
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-white transition-all hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-40"
            aria-label={isLoading ? 'Generating response' : 'Send message'}
          >
            {isLoading ? (
              <Square className="h-3.5 w-3.5 fill-current" />
            ) : (
              <ArrowUp className="h-4 w-4" />
            )}
          </button>
        </div>
        <div className="mt-1.5 text-center text-[0.7rem] text-text-muted">
          Press Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}

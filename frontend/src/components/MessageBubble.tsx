import { useState } from 'react';
import { Copy, Check, RotateCcw } from 'lucide-react';
import type { ChatMessage } from '../types/chat';
import { MarkdownRenderer } from './MarkdownRenderer';
import { Sources } from './Sources';

interface Props {
  message: ChatMessage;
  onRetry?: () => void;
}

export function MessageBubble({ message, onRetry }: Props) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard may be blocked — silently ignore */
    }
  };

  return (
    <div className={`flex gap-3 animate-fade-up ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          isUser
            ? 'bg-primary text-white'
            : 'bg-surface-hover text-primary'
        }`}
        aria-hidden="true"
      >
        {isUser ? 'U' : 'M'}
      </div>

      {/* Content column */}
      <div className={`flex min-w-0 flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Sender label */}
        <div className="text-[0.65rem] font-semibold uppercase tracking-wider text-text-muted">
          {isUser ? 'You' : 'MITS AI'}
        </div>

        {/* Bubble */}
        <div
          className={`max-w-[calc(100%-2.75rem)] rounded-lg px-4 py-2.5 ${
            isUser
              ? 'rounded-tr-sm bg-primary text-white'
              : message.isError
                ? 'rounded-tl-sm border border-danger/30 bg-danger-bg text-danger'
                : 'rounded-tl-sm border border-border bg-surface text-text'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.text}</p>
          ) : (
            <MarkdownRenderer content={message.text} />
          )}
        </div>

        {/* Typing indicator placeholder is handled by ChatView, not here */}

        {/* Action row for AI messages */}
        {!isUser && (
          <div className="flex items-center gap-3">
            {/* Copy */}
            {!message.isError && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-[0.7rem] text-text-muted transition-colors hover:text-text"
                aria-label="Copy response"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-success" />
                    <span className="text-success">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}

            {/* Retry */}
            {message.isError && onRetry && (
              <button
                onClick={onRetry}
                className="flex items-center gap-1 text-[0.7rem] font-medium text-primary transition-colors hover:text-primary-hover"
                aria-label="Retry last question"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Retry</span>
              </button>
            )}
          </div>
        )}

        {/* Sources */}
        {!isUser && !message.isError && <Sources sources={message.sources} />}
      </div>
    </div>
  );
}

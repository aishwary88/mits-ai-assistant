import { useEffect, useRef, useState } from 'react';
import { ArrowDown } from 'lucide-react';
import type { ChatMessage } from '../types/chat';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
  onRetry?: () => void;
}

export function ChatView({ messages, isLoading, onRetry }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  // Auto-scroll to bottom when new messages arrive (only if user was at bottom)
  useEffect(() => {
    if (atBottom) {
      const el = scrollRef.current;
      if (el) {
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      }
    }
  }, [messages, isLoading, atBottom]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const threshold = 100;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setAtBottom(isAtBottom);
  };

  const scrollToBottom = () => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      setAtBottom(true);
    }
  };

  return (
    <div className="relative flex-1 overflow-hidden">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto px-4 py-6 sm:px-6"
        aria-live="polite"
        aria-label="Conversation"
      >
        <div className="mx-auto flex max-w-3xl flex-col gap-5">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} onRetry={onRetry} />
          ))}

          {/* Typing indicator */}
          {isLoading && (
            <div className="flex animate-fade-up gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-hover text-xs font-bold text-primary">
                M
              </div>
              <div className="flex flex-col gap-1">
                <div className="text-[0.65rem] font-semibold uppercase tracking-wider text-text-muted">
                  MITS AI
                </div>
                <div className="rounded-lg rounded-tl-sm border border-border bg-surface px-4 py-3">
                  <TypingIndicator />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Scroll to latest button */}
      {!atBottom && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-muted shadow-md transition-colors hover:text-text"
          aria-label="Scroll to latest message"
        >
          <ArrowDown className="h-3.5 w-3.5" />
          Scroll to latest
        </button>
      )}
    </div>
  );
}

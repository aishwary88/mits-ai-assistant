import { useCallback, useRef, useState } from 'react';
import type { ChatMessage } from '../types/chat';
import { askQuestion, ApiError } from '../api/chat';

function makeId(): string {
  return crypto.randomUUID();
}

/**
 * Manages the chat conversation state, API calls, loading state,
 * and error/retry handling. Preserves the exact API contract from
 * the original static/app.js via the api/chat module.
 */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const loadingRef = useRef(false);
  const lastUserQuestionRef = useRef('');

  /** Call the API and append the AI response or an error message. */
  const fetchAnswer = useCallback(async (question: string) => {
    try {
      const data = await askQuestion(question);
      const aiMsg: ChatMessage = {
        id: makeId(),
        role: 'assistant',
        text: data.answer,
        sources: data.sources,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      let text: string;
      if (err instanceof ApiError) {
        if (err.kind === 'empty') {
          text = 'I received an empty response. Please try rephrasing your question.';
        } else if (err.kind === 'network') {
          text = 'Network error — could not reach the server. Please check your connection and try again.';
        } else {
          text = "I couldn't retrieve an answer right now. Please try again.";
        }
      } else {
        text = 'An unexpected error occurred. Please try again.';
      }

      const errMsg: ChatMessage = {
        id: makeId(),
        role: 'assistant',
        text,
        isError: true,
      };
      setMessages((prev) => [...prev, errMsg]);
    }
  }, []);

  /** Send a new question: adds a user message, then calls the API. */
  const sendMessage = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || loadingRef.current) return;

      lastUserQuestionRef.current = trimmed;
      loadingRef.current = true;
      setIsLoading(true);

      const userMsg: ChatMessage = { id: makeId(), role: 'user', text: trimmed };
      setMessages((prev) => [...prev, userMsg]);

      try {
        await fetchAnswer(trimmed);
      } finally {
        loadingRef.current = false;
        setIsLoading(false);
      }
    },
    [fetchAnswer],
  );

  /** Remove the last error message and re-send the previous user question. */
  const retryLast = useCallback(async () => {
    if (loadingRef.current || !lastUserQuestionRef.current) return;

    // Remove the trailing error message
    setMessages((prev) =>
      prev[prev.length - 1]?.isError ? prev.slice(0, -1) : prev,
    );

    loadingRef.current = true;
    setIsLoading(true);

    try {
      await fetchAnswer(lastUserQuestionRef.current);
    } finally {
      loadingRef.current = false;
      setIsLoading(false);
    }
  }, [fetchAnswer]);

  const clearChat = useCallback(() => {
    setMessages([]);
    lastUserQuestionRef.current = '';
  }, []);

  return { messages, isLoading, sendMessage, retryLast, clearChat };
}

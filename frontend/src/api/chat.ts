/**
 * MITS AI Assistant — API module
 * --------------------------------
 * Preserves the EXACT request logic from the original static/app.js:
 *   - URL: POST /ask  (FastAPI route in app/main.py)
 *   - Headers: Content-Type: application/json
 *   - Body: { question: string }
 *   - Response: { answer, sources[], retrieval{} }
 *
 * No changes to URL, method, headers, or body shape.
 */

import type { ChatResponse } from '../types/chat';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public kind: 'http' | 'network' | 'empty',
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

/**
 * Send a question to the RAG backend and return the structured response.
 * Throws ApiError on any failure (HTTP error, network failure, empty answer).
 */
export async function askQuestion(question: string): Promise<ChatResponse> {
  let response: Response;

  try {
    response = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
  } catch (networkErr) {
    throw new ApiError(0, 'Network error — could not reach the server.', 'network');
  }

  if (!response.ok) {
    let detail = `Server error (${response.status})`;
    try {
      const errBody = await response.json();
      detail = errBody.detail || detail;
    } catch {
      /* non-JSON error body — keep generic message */
    }
    throw new ApiError(response.status, detail, 'http');
  }

  const data = await response.json();
  const answer = (data.answer || '').trim();
  const sources = Array.isArray(data.sources) ? data.sources : [];

  if (!answer) {
    throw new ApiError(200, 'Empty response', 'empty');
  }

  return {
    answer,
    sources,
    retrieval: data.retrieval,
  };
}

/** Extract just the filename from a source title that may be a full path. */
export function sourceFilename(title: string): string {
  return title.split(/[\\/]/).pop() || title;
}

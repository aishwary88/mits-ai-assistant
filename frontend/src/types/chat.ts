/**
 * Type definitions for the MITS AI chat API.
 * Derived from the existing backend (app/main.py) and frontend (static/app.js).
 */

export interface Source {
  title: string;
  type: string;
  page: number;
  excerpt: string;
}

export interface RetrievalDocument {
  title: string;
  page: number;
}

export interface RetrievalInfo {
  originalQuery: string;
  chunksRetrieved: number;
  steps: string[];
  documents: RetrievalDocument[];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  retrieval: RetrievalInfo;
}

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  sources?: Source[];
  isError?: boolean;
}

export interface RecentChat {
  id: string;
  title: string;
  ts: number;
}

export type ThemeMode = 'light' | 'dark';

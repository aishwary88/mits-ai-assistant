import { useCallback, useState } from 'react';
import type { RecentChat } from '../types/chat';

const STORAGE_KEY = 'mits_recent_chats';
const MAX_ITEMS = 12;

function loadRecent(): RecentChat[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveRecent(items: RecentChat[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_ITEMS)));
  } catch {
    /* storage quota — ignore */
  }
}

export function useRecentChats() {
  const [recentChats, setRecentChats] = useState<RecentChat[]>(loadRecent);

  const addRecentChat = useCallback((title: string) => {
    const trimmed = title.length > 48 ? title.slice(0, 45) + '…' : title;
    setRecentChats((prev) => {
      // deduplicate by title
      const filtered = prev.filter((i) => i.title !== trimmed);
      const next = [{ id: crypto.randomUUID(), title: trimmed, ts: Date.now() }, ...filtered];
      saveRecent(next);
      return next;
    });
  }, []);

  const removeRecentChat = useCallback((id: string) => {
    setRecentChats((prev) => {
      const next = prev.filter((i) => i.id !== id);
      saveRecent(next);
      return next;
    });
  }, []);

  return { recentChats, addRecentChat, removeRecentChat };
}

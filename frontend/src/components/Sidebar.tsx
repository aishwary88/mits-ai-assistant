import { useEffect, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, MessageSquare, X, Trash2 } from 'lucide-react';
import type { RecentChat } from '../types/chat';

const LOGO_URL = '/static/assets/mits-logo.png';

interface Props {
  recentChats: RecentChat[];
  onNewChat: () => void;
  onRecentClick: (title: string) => void;
  onRemoveRecent: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({
  recentChats,
  onNewChat,
  onRecentClick,
  onRemoveRecent,
  isOpen,
  onClose,
}: Props) {
  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  const content: ReactNode = (
    <>
      {/* Brand */}
      <div
        className="flex items-center gap-2.5 border-b px-4 py-4"
        style={{ borderColor: 'var(--sidebar-border)' }}
      >
        <img
          src={LOGO_URL}
          alt="MITS Logo"
          className="h-10 w-10 shrink-0 rounded bg-white p-0.5 object-contain"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
        <div className="flex flex-col overflow-hidden">
          <strong className="text-sm font-bold text-slate-100">MITS AI</strong>
          <span
            className="text-[0.62rem] font-semibold uppercase tracking-wider"
            style={{ color: 'var(--sidebar-text)' }}
          >
            Campus Intelligence
          </span>
        </div>
      </div>

      {/* New Chat */}
      <button
        onClick={() => {
          onNewChat();
          onClose();
        }}
        className="mx-3 mt-3 flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors"
        style={{
          color: '#CBD5E1',
          borderColor: 'var(--sidebar-border)',
        }}
      >
        <Plus className="h-4 w-4" />
        New Chat
      </button>

      {/* Recent label */}
      <div
        className="px-4 pb-1 pt-4 text-[0.62rem] font-semibold uppercase tracking-wider"
        style={{ color: 'var(--sidebar-text)' }}
      >
        Recent Conversations
      </div>

      {/* Recent list */}
      <div className="sidebar-scroll flex-1 overflow-y-auto px-2 pb-3">
        {recentChats.length === 0 ? (
          <div
            className="px-2.5 py-4 text-xs"
            style={{ color: 'var(--sidebar-text)' }}
          >
            No conversations yet
          </div>
        ) : (
          recentChats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => {
                onRecentClick(chat.title);
                onClose();
              }}
              className="group flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 transition-colors"
              style={{ color: 'var(--sidebar-text)' }}
            >
              <MessageSquare className="h-3.5 w-3.5 shrink-0" />
              <span className="flex-1 truncate text-xs">{chat.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveRecent(chat.id);
                }}
                className="opacity-0 transition-opacity hover:opacity-100 group-hover:opacity-60"
                aria-label="Delete conversation"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))
        )}
      </div>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className="hidden w-[260px] shrink-0 flex-col lg:flex"
        style={{ background: 'var(--sidebar-bg)' }}
      >
        {content}
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
              className="fixed left-0 top-0 z-50 flex h-[100dvh] w-[260px] flex-col lg:hidden"
              style={{ background: 'var(--sidebar-bg)' }}
            >
              <button
                onClick={onClose}
                className="absolute right-3 top-4 flex h-8 w-8 items-center justify-center rounded-md lg:hidden"
                style={{ color: 'var(--sidebar-text)' }}
                aria-label="Close menu"
              >
                <X className="h-4 w-4" />
              </button>
              {content}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

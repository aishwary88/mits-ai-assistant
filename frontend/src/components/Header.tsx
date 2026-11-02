import { Menu, Sun, Moon } from 'lucide-react';
import type { ThemeMode } from '../types/chat';

interface Props {
  theme: ThemeMode;
  onToggleTheme: () => void;
  onMenuClick: () => void;
}

export function Header({ theme, onToggleTheme, onMenuClick }: Props) {
  return (
    <header
      className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4 sm:px-6"
      role="banner"
    >
      {/* Left: menu (mobile) + title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="flex h-9 w-9 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-surface-hover hover:text-text lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex flex-col gap-0.5">
          <div className="hidden text-[0.6rem] font-semibold uppercase tracking-wider text-text-muted sm:block">
            Madhav Institute of Technology &amp; Science, Gwalior
          </div>
          <div className="text-sm font-bold text-text">MITS AI Assistant</div>
        </div>
      </div>

      {/* Right: status + theme toggle */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface-hover px-2.5 py-1 text-xs font-medium text-text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          <span className="hidden sm:inline">RAG System Online</span>
          <span className="sm:hidden">Online</span>
        </div>
        <button
          onClick={onToggleTheme}
          className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface-hover text-text-muted transition-colors hover:bg-surface-hover hover:text-text"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>
      </div>
    </header>
  );
}

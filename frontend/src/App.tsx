import { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from './hooks/useTheme';
import { useChat } from './hooks/useChat';
import { useRecentChats } from './hooks/useRecentChats';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { ChatView } from './components/ChatView';
import { Composer } from './components/Composer';

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { messages, isLoading, sendMessage, retryLast, clearChat } = useChat();
  const { recentChats, addRecentChat, removeRecentChat } = useRecentChats();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isHome = messages.length === 0;

  const handleSend = useCallback(
    (question: string) => {
      sendMessage(question);
      addRecentChat(question);
    },
    [sendMessage, addRecentChat],
  );

  const handleNewChat = useCallback(() => {
    clearChat();
    setSidebarOpen(false);
  }, [clearChat]);

  const handleRecentClick = useCallback(
    (title: string) => {
      handleSend(title);
      setSidebarOpen(false);
    },
    [handleSend],
  );

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-bg text-text">
      <Sidebar
        recentChats={recentChats}
        onNewChat={handleNewChat}
        onRecentClick={handleRecentClick}
        onRemoveRecent={removeRecentChat}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex h-[100dvh] min-w-0 flex-1 flex-col">
        <Header
          theme={theme}
          onToggleTheme={toggleTheme}
          onMenuClick={() => setSidebarOpen(true)}
        />

        {/* Content area — flex-1 + min-h-0 enables scrolling inside */}
        <main className="flex min-h-0 flex-1 flex-col">
          <AnimatePresence mode="wait">
            {isHome ? (
              <motion.div
                key="home"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex min-h-0 flex-1 flex-col"
              >
                <Hero onCardClick={handleSend} />
              </motion.div>
            ) : (
              <motion.div
                key="chat"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex min-h-0 flex-1 flex-col"
              >
                <ChatView
                  messages={messages}
                  isLoading={isLoading}
                  onRetry={retryLast}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        <Composer onSend={handleSend} isLoading={isLoading} />
      </div>
    </div>
  );
}

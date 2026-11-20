import { queryAPI } from "./api/query";
import { useState, useEffect, useRef, useCallback } from 'react';
import { ChatSidebar, SIDEBAR_DEFAULT, clampSidebarWidth, isMobileLayout } from './components/ChatSidebar';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { ChatWelcome } from './components/ChatWelcome';
import { LoginPage } from './components/LoginPage';
import { ThemeToggle, useTheme } from './theme';
import { AnswerDetails, type AnswerMetadata } from './components/AnswerDetails';
import { LogOut, PanelLeftOpen } from 'lucide-react';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string | Date;
  chart?: any;
  data?: any[];
  metadata?: AnswerMetadata;
}

interface ChatThread {
  id: string;
  title: string;
  messages: Message[];
  lastUpdated: string | Date;
}

const STORAGE_KEY = 'aiport_chat_threads_v7_0_fixed';
const SIDEBAR_WIDTH_KEY = 'seatac_sidebar_width';
const SIDEBAR_COLLAPSED_KEY = 'seatac_sidebar_collapsed';

// localStorage can be unavailable (private mode, blocked storage): the app still works without it
const readSetting = (key: string): string | null => {
  try { return localStorage.getItem(key); } catch { return null; }
};
const writeSetting = (key: string, value: string) => {
  try { localStorage.setItem(key, value); } catch { /* not saved */ }
};

// Sidebar title: the chat's first question as plain text (no markdown), or "New chat"
const chatTitle = (thread: ChatThread): string => {
  const first = thread.messages.find(m => m.role === 'user')?.content ?? '';
  const text = (first || (thread.title === 'New Chat' ? '' : thread.title))
    .replace(/[*_`#>|~]/g, '').replace(/\s+/g, ' ').trim();
  return text ? (text.length > 80 ? `${text.slice(0, 79)}…` : text) : 'New chat';
};

export default function App() {
  // Login state
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState('');

  const { theme, toggleTheme } = useTheme();

  // Chat state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => readSetting(SIDEBAR_COLLAPSED_KEY) === '1');
  const [sidebarWidth, setSidebarWidth] = useState(() =>
    clampSidebarWidth(Number(readSetting(SIDEBAR_WIDTH_KEY) ?? SIDEBAR_DEFAULT)));
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [detailsFor, setDetailsFor] = useState<string | null>(null);  // answer whose details panel is open
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeChat, setActiveChat] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const closeDetails = useCallback(() => setDetailsFor(null), []);
  useEffect(() => { setDetailsFor(null); }, [activeChat]);  // a different chat closes the panel

  // Remember the sidebar width and collapsed state
  useEffect(() => { writeSetting(SIDEBAR_WIDTH_KEY, String(sidebarWidth)); }, [sidebarWidth]);
  useEffect(() => { writeSetting(SIDEBAR_COLLAPSED_KEY, isSidebarCollapsed ? '1' : '0'); }, [isSidebarCollapsed]);

  // Check if already logged in
  useEffect(() => {
    const savedUser = localStorage.getItem('aiport_user');
    if (savedUser) {
      setCurrentUser(savedUser);
      setIsLoggedIn(true);
    }
  }, []);

  // Load threads (only after login)
  useEffect(() => {
    if (!isLoggedIn) return;

    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        console.log('💾 Loaded threads:', parsed.length);
        setThreads(parsed);
        if (parsed.length > 0) {
          setActiveChat(parsed[0].id);
        }
      } catch (e) {
        console.error('Error loading threads:', e);
      }
    } else {
      const initialThread: ChatThread = {
        id: Date.now().toString(),
        title: 'New Chat',
        messages: [],
        lastUpdated: new Date().toString()
      };
      console.log('🆕 Creating initial thread:', initialThread.id);
      setThreads([initialThread]);
      setActiveChat(initialThread.id);
    }
  }, [isLoggedIn]);

  // Save threads
  useEffect(() => {
    if (threads.length > 0 && isLoggedIn) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(threads));
      console.log('💾 Saved threads:', threads.length);
    }
  }, [threads, isLoggedIn]);

  // Scrolling: a new question or the loading indicator scrolls to the bottom; a new answer scrolls to the
  // top of that answer, so the one-sentence answer and its badge are in view (long tables follow below).
  const activeMessages = threads.find(t => t.id === activeChat)?.messages ?? [];
  const lastMessage = activeMessages[activeMessages.length - 1];
  useEffect(() => {
    if (!lastMessage) return;
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (lastMessage.role === 'assistant') {
      document.getElementById(`msg-${lastMessage.id}`)?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
    } else {
      bottomRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' });
    }
  }, [lastMessage?.id, isTyping]);

  // Login check (demo accounts, no real auth). Returns true when the login worked.
  const handleLogin = (username: string, password: string): boolean => {
    if ((username === 'admin' && password === 'admin123') || 
        (username === 'guest' && password === 'guest123')) {
      setCurrentUser(username);
      setIsLoggedIn(true);
      localStorage.setItem('aiport_user', username);
      return true;
    }
    return false;
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setCurrentUser('');
    localStorage.removeItem('aiport_user');
  };

  // Show login page
  if (!isLoggedIn) {
    return <LoginPage onLogin={handleLogin} themeToggle={<ThemeToggle theme={theme} onToggle={toggleTheme} />} />;
  }

  // Get current messages
  const currentThread = threads.find(t => t.id === activeChat);
  const messages = currentThread?.messages || [];

  console.log('🎨 Render - Active chat:', activeChat, 'Messages:', messages.length);

  const handleSendMessage = async (userMessage: string) => {
    console.log('\n=== HANDLE SEND MESSAGE ===');
    console.log('📤 Input:', userMessage);
    console.log('📍 Active chat:', activeChat);

    if (!activeChat) {
      console.error('❌ No active chat!');
      return;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      content: userMessage,
      role: 'user',
      timestamp: new Date().toString()
    };

    console.log('👤 User message:', userMsg.id);

    setThreads(prevThreads => {
      const updated = prevThreads.map(t => 
        t.id === activeChat 
          ? { ...t, messages: [...t.messages, userMsg], lastUpdated: new Date().toString() }
          : t
      );
      console.log('✅ User message added');
      return updated;
    });

    const currentThread = threads.find(t => t.id === activeChat);
    if (currentThread && currentThread.messages.length === 0) {
      const title = userMessage.slice(0, 50);
      setThreads(prev => prev.map(t => 
        t.id === activeChat ? { ...t, title } : t
      ));
    }

    setIsTyping(true);

    try {
      console.log('🌐 Calling API...');
      const response = await queryAPI(userMessage);

      console.log('✅ API Response:', {
        hasMessage: !!response.message,
        hasTableData: !!response.tableData,
        hasChart: !!response.chart,
        tableDataLength: response.tableData?.length
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.message || 'No response',
        role: 'assistant',
        timestamp: new Date().toString(),
        chart: response.chart,
        data: response.tableData, // ✅ Using tableData from query.ts
        metadata: {
          outputFormat: response.output_format,
          outputConfidence: response.output_confidence,
          queryType: response.use_case,
          rowCount: response.row_count || 0,
          sqlSource: response.sql_source,
          metric: response.metric,
          sqlQueries: response.sql_queries,
          definition: response.definition,
          includedCount: response.included_count,
          excluded: response.excluded
        }
      };

      console.log('🤖 Assistant message created:', {
        hasChart: !!assistantMessage.chart,
        hasData: !!assistantMessage.data,
        dataLength: assistantMessage.data?.length
      });

      setThreads(prevThreads => {
        const updated = prevThreads.map(t => {
          if (t.id === activeChat) {
            const newMessages = [...t.messages, assistantMessage];
            console.log('✅ Assistant message added. Total messages:', newMessages.length);
            return {
              ...t,
              messages: newMessages,
              lastUpdated: new Date().toString()
            };
          }
          return t;
        });
        return updated;
      });

    } catch (error) {
      console.error('❌ Error:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        role: 'assistant',
        timestamp: new Date().toString()
      };

      setThreads(prev => prev.map(t => 
        t.id === activeChat 
          ? { ...t, messages: [...t.messages, errorMessage] }
          : t
      ));
    } finally {
      setIsTyping(false);
      console.log('=== SEND MESSAGE END ===\n');
    }
  };

  const createThread = (): ChatThread => ({
    id: Date.now().toString(),
    title: 'New Chat',
    messages: [],
    lastUpdated: new Date().toString()
  });

  const handleNewChat = () => {
    if (currentThread && currentThread.messages.length === 0) return;  // already on an empty chat
    const newThread = createThread();
    setThreads(prev => [newThread, ...prev]);
    setActiveChat(newThread.id);
  };

  const handleSelectChat = (chatId: string) => {
    setActiveChat(chatId);
  };

  const handleDeleteChat = (chatId: string) => {
    const remaining = threads.filter(t => t.id !== chatId);
    if (remaining.length === 0) {  // always keep one chat
      const newThread = createThread();
      setThreads([newThread]);
      setActiveChat(newThread.id);
      return;
    }
    setThreads(remaining);
    if (activeChat === chatId) setActiveChat(remaining[0].id);
  };

  // the clicked button disappears when the sidebar hides or shows, so focus moves to the matching one
  const focusSoon = (selector: string) =>
    requestAnimationFrame(() => document.querySelector<HTMLElement>(selector)?.focus());
  const openSidebar = () => {
    if (isMobileLayout()) return setMobileSidebarOpen(true);
    setIsSidebarCollapsed(false);
    focusSoon('[data-testid="sidebar-collapse"]');
  };
  const collapseSidebar = () => {
    setIsSidebarCollapsed(true);
    focusSoon('[data-testid="sidebar-open"]');
  };
  const sidebarVisible = mobileSidebarOpen || !isSidebarCollapsed;

  const isWelcomeView = messages.length === 0;

  return (
    <div className="sea-app">
      <ChatSidebar
        chats={threads.map(t => ({ id: t.id, title: chatTitle(t) }))}
        activeChat={activeChat}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        width={sidebarWidth}
        onWidthChange={setSidebarWidth}
        collapsed={isSidebarCollapsed}
        onCollapse={collapseSidebar}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      <div className="sea-main">
        <header className="sea-topbar">
          <button
            type="button"
            className={`sea-icon-btn sea-menu-btn${isSidebarCollapsed ? '' : ' sea-mobile-only'}`}
            onClick={openSidebar}
            aria-label="Show sidebar"
            aria-controls="chat-sidebar"
            aria-expanded={sidebarVisible}
            title="Show sidebar"
            data-testid="sidebar-open"
          >
            <PanelLeftOpen aria-hidden="true" />
          </button>
          <h1 className="sea-topbar-title">SeaTac AI</h1>
          <div className="sea-topbar-user">
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
            <span className="sea-topbar-name">Signed in as {currentUser}</span>
            <button type="button" className="sea-btn sea-btn-ghost sea-logout" onClick={handleLogout}>
              <LogOut aria-hidden="true" /> Log out
            </button>
          </div>
        </header>

        <div className="sea-scroll" ref={scrollRef}>
          {isWelcomeView ? (
            <ChatWelcome onAsk={handleSendMessage} disabled={isTyping} />
          ) : (
            <div className="sea-thread">
              {messages.map((message, i) => (
                <ChatMessage key={message.id} message={message}
                             question={messages[i - 1]?.role === 'user' ? messages[i - 1].content : undefined}
                             onShowDetails={message.role === 'assistant' ? () => setDetailsFor(message.id) : undefined} />
              ))}
              {isTyping && (
                <div className="sea-loading" role="status">
                  <span className="sea-dots" aria-hidden="true"><i /><i /><i /></span>
                  Looking up the data…
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <ChatInput onSendMessage={handleSendMessage} disabled={isTyping} />

        {(() => {
          const shown = detailsFor ? messages.find(m => m.id === detailsFor) : undefined;
          return shown ? (
            <AnswerDetails content={shown.content} metadata={shown.metadata} onClose={closeDetails} />
          ) : null;
        })()}
      </div>
    </div>
  );
}

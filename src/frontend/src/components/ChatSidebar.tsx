import { useEffect, type CSSProperties, type KeyboardEvent, type PointerEvent } from 'react';
import { PanelLeftClose, Plus, Trash2 } from 'lucide-react';
import { cn } from './ui/utils';

export const SIDEBAR_MIN = 200;
export const SIDEBAR_MAX = 420;
export const SIDEBAR_DEFAULT = 260;
const KEY_STEP = 16;

export const clampSidebarWidth = (w: number) =>
  Math.round(Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, Number.isFinite(w) ? w : SIDEBAR_DEFAULT)));

/** Below this width the sidebar is a slide-over panel (same breakpoint as seatac.css). */
export const isMobileLayout = () => window.matchMedia('(max-width: 767px)').matches;

export interface ChatSummary {
  id: string;
  title: string;
}

interface ChatSidebarProps {
  chats: ChatSummary[];
  activeChat: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat: (id: string) => void;
  width: number;
  onWidthChange: (width: number) => void;
  collapsed: boolean;
  onCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function ChatSidebar({
  chats, activeChat, onSelectChat, onNewChat, onDeleteChat,
  width, onWidthChange, collapsed, onCollapse, mobileOpen, onCloseMobile,
}: ChatSidebarProps) {
  // Esc closes the slide-over panel on small screens
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === 'Escape') onCloseMobile(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mobileOpen, onCloseMobile]);

  const hide = () => (isMobileLayout() ? onCloseMobile() : onCollapse());
  const afterPick = () => { if (isMobileLayout()) onCloseMobile(); };

  const startResize = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = width;
    const move = (ev: globalThis.PointerEvent) => onWidthChange(clampSidebarWidth(startWidth + ev.clientX - startX));
    const stop = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', stop);
      document.body.classList.remove('sea-resizing');
    };
    document.body.classList.add('sea-resizing');
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop);
  };

  const resizeWithKeys = (e: KeyboardEvent<HTMLDivElement>) => {
    const next = { ArrowLeft: width - KEY_STEP, ArrowRight: width + KEY_STEP, Home: SIDEBAR_MIN, End: SIDEBAR_MAX }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    onWidthChange(clampSidebarWidth(next));
  };

  return (
    <>
      {mobileOpen && <div className="sea-backdrop" onClick={onCloseMobile} aria-hidden="true" />}
      <aside
        id="chat-sidebar"
        className={cn('sea-sidebar', collapsed && 'is-collapsed', mobileOpen && 'is-open')}
        style={{ '--sea-sidebar-width': `${width}px` } as CSSProperties}
        aria-label="Chats"
      >
        <div className="sea-sidebar-head">
          <button type="button" className="sea-btn sea-btn-secondary sea-new-chat"
                  onClick={() => { onNewChat(); afterPick(); }}>
            <Plus aria-hidden="true" /> New chat
          </button>
          <button type="button" className="sea-icon-btn" onClick={hide} aria-label="Hide sidebar"
                  title="Hide sidebar" data-testid="sidebar-collapse">
            <PanelLeftClose aria-hidden="true" />
          </button>
        </div>

        <h2 className="sea-sidebar-label">Recent chats</h2>
        <ul className="sea-chat-list">
          {chats.map((chat) => {
            const active = chat.id === activeChat;
            return (
              <li key={chat.id} className={cn('sea-chat', active && 'is-active')}>
                <button type="button" className="sea-chat-item" title={chat.title}
                        aria-current={active ? 'true' : undefined}
                        onClick={() => { onSelectChat(chat.id); afterPick(); }}>
                  {chat.title}
                </button>
                <button type="button" className="sea-icon-btn sea-chat-delete"
                        onClick={() => onDeleteChat(chat.id)}
                        aria-label={`Delete chat: ${chat.title}`} title="Delete chat">
                  <Trash2 aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>

        <div
          className="sea-resize"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize sidebar"
          aria-controls="chat-sidebar"
          aria-valuemin={SIDEBAR_MIN}
          aria-valuemax={SIDEBAR_MAX}
          aria-valuenow={width}
          tabIndex={0}
          onPointerDown={startResize}
          onKeyDown={resizeWithKeys}
          onDoubleClick={() => onWidthChange(SIDEBAR_DEFAULT)}
          title="Drag to resize (double-click to reset)"
          data-testid="sidebar-resize"
        />
      </aside>
    </>
  );
}

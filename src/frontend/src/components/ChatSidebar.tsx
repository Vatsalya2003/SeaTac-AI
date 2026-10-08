import React from 'react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Plus, MessageSquare, Trash2, Menu, X } from 'lucide-react';
import { cn } from './ui/utils';

interface ChatHistory {
  id: string;
  title: string;
  timestamp: string | Date;
  preview: string;
}

interface ChatSidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  activeChat: string | null;
  onSelectChat: (id: string) => void;
  // now the history is controlled by parent (App.tsx)
  chatHistory: ChatHistory[];
  onDeleteChat: (id: string) => void;
}

// used for debug
console.log('🔥 ChatSidebar loaded');

export function ChatSidebar({
  isCollapsed,
  onToggle,
  onNewChat,
  activeChat,
  onSelectChat,
  chatHistory,
  onDeleteChat,
}: ChatSidebarProps) {
  const deleteChat = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onDeleteChat(id);
    if (activeChat === id) {
      onNewChat();
    }
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <div
      className={cn(
        'bg-gray-50/80 border-r border-gray-200 transition-all duration-300 ease-in-out flex flex-col  h-full',
        isCollapsed ? 'w-16' : 'w-80'
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={onToggle} className="h-8 w-8 p-0">
            {isCollapsed ? <Menu className="h-4 w-4" /> : <X className="h-4 w-4" />}
          </Button>

          {!isCollapsed && (
            <Button
              onClick={onNewChat}
              size="sm"
              className="flex items-center gap-2 bg-white hover:bg-gray-50 text-gray-700 border border-gray-200"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          )}
        </div>
      </div>

      {/* Chat History */}
      {!isCollapsed && (
        <>
          <div className="px-4 py-3">
            <h3 className="text-sm font-medium text-gray-600">Recent Chats</h3>
          </div>
          
          <ScrollArea className="flex-1 px-2">
            <div className="space-y-1">
              {chatHistory.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => onSelectChat(chat.id)}
                  className={cn(
                    'group relative flex flex-col p-3 pr-6 rounded-lg cursor-pointer transition-all duration-200',
                    'hover:bg-white hover:shadow-sm',
                    activeChat === chat.id && 'bg-white shadow-sm border border-gray-200'
                  )}
                >
                  {/* Title */}
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-gray-900 truncate min-w-0 flex-1">
                      {chat.title}
                    </p>
                  </div>

                  {/* Preview */}
                  <p className="text-xs text-gray-500 truncate mt-0.5 min-w-0">{chat.preview}</p>

                  {/* Time and delete button */}
                  <div className="mt-2 relative">
                    <span className="text-xs text-gray-400">{formatTime(new Date(chat.timestamp))}</span>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e: React.MouseEvent) => deleteChat(e, chat.id)}
                      aria-label={`Delete chat ${chat.title}`}
                      title="Delete chat"
                      className="absolute right-0 top-0 h-6 w-6 p-0 text-gray-700 hover:text-red-600 transition-colors bg-white rounded-md z-[999]"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>

                </div>
              ))}
            </div>
          </ScrollArea>

        </>
      )}

      {/* Collapsed State */}
      {isCollapsed && (
        <div className="flex-1 flex flex-col items-center pt-4 space-y-2">
          <Button onClick={onNewChat} variant="ghost" size="sm" className="h-10 w-10 p-0">
            <Plus className="h-4 w-4" />
          </Button>

          <Separator className="w-8" />

          <div className="space-y-1">
            {chatHistory.slice(0, 3).map((chat) => (
              <Button
                key={chat.id}
                variant="ghost"
                size="sm"
                onClick={() => onSelectChat(chat.id)}
                className={cn('h-10 w-10 p-0', activeChat === chat.id && 'bg-white shadow-sm')}
              >
                <MessageSquare className="h-4 w-4" />
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Send, Square } from 'lucide-react';
import { cn } from './ui/utils';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  isTyping?: boolean;
}

export function ChatInput({ onSendMessage, disabled = false, isTyping = false }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  // Focus on mount
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isTyping) {
      onSendMessage(message.trim());
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleStop = () => {
    // Placeholder for stop generation functionality
    console.log('Stop generation requested');
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-2">
          {/* Textarea */}
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isTyping 
                  ? "Waiting for response..." 
                  : "Ask about flight operations, taxi times, delays..."
              }
              disabled={disabled || isTyping}
              className={cn(
                "min-h-[60px] max-h-[200px] resize-none pr-12",
                "focus:ring-2 focus:ring-green-500 focus:border-transparent",
                (disabled || isTyping) && "bg-gray-50 cursor-not-allowed"
              )}
              rows={1}
            />
            
            {/* Character count (optional) */}
            {message.length > 0 && (
              <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                {message.length}
              </div>
            )}
          </div>

          {/* Submit/Stop Button */}
          {isTyping ? (
            <Button
              type="button"
              onClick={handleStop}
              size="lg"
              variant="outline"
              className="h-[60px] px-4 border-red-300 hover:bg-red-50"
            >
              <Square className="h-5 w-5 text-red-600" />
            </Button>
          ) : (
            <Button
              type="submit"
              disabled={!message.trim() || disabled}
              size="lg"
              className={cn(
                "h-[60px] px-6",
                "bg-green-600 hover:bg-green-700",
                "disabled:bg-gray-300 disabled:cursor-not-allowed"
              )}
            >
              <Send className="h-5 w-5" />
            </Button>
          )}
        </div>

        {/* Helper text */}
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
          <span>
            Press <kbd className="px-1.5 py-0.5 bg-gray-100 rounded border">Enter</kbd> to send,{' '}
            <kbd className="px-1.5 py-0.5 bg-gray-100 rounded border">Shift+Enter</kbd> for new line
          </span>
          {isTyping && (
            <span className="text-green-600 font-medium">
              AI is thinking...
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
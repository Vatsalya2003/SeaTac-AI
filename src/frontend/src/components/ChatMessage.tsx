import { useState } from 'react';
import { Button } from './ui/button';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Copy, Check, BarChart3, Table as TableIcon, BadgeCheck, Sparkles } from 'lucide-react';
import { cn } from './ui/utils';
import ChartVisualization from './ChartVisualization';
import { DataTableWithExport } from './DataTableWithExport';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './query-results.css';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date | string;
  chart?: any;
  data?: any[];
  metadata?: { sqlSource?: string };
}

interface ChatMessageProps {
  message: Message;
}

// Badge above each answer, from the backend's sql_source. Greetings ('system') and answers that
// couldn't be given ('none', or no sql_source) get no badge.
const SOURCE_BADGES: Record<string, { label: string; className: string; Icon: typeof BadgeCheck }> = {
  template: { label: 'Verified answer', Icon: BadgeCheck,
              className: 'border-green-200 bg-green-50 text-green-700' },
  ai_sql: { label: 'AI-generated, not yet verified', Icon: Sparkles,
            className: 'border-amber-300 bg-amber-50 text-amber-800' },
};

function SourceBadge({ source }: { source?: string }) {
  const badge = source ? SOURCE_BADGES[source] : undefined;
  if (!badge) return null;
  const { label, className, Icon } = badge;
  return (
    <div className={cn('mb-2 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium', className)}
         data-testid="answer-source-badge">
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {label}
    </div>
  );
}

// "**Answer** (N rows):" label lines (templates and views modes). The "**Answer:**" sentence is kept.
const ROW_COUNT_LABEL = /^\*\*Answer\*\* \([\d,]+ rows?\)[^\n]*:[ \t]*\n?/gm;
const isTableLine = (line: string) => line.trimStart().startsWith('|');

// Removes the row-count labels. When the reply has data rows, also removes the last markdown table:
// it holds the same rows as message.data, which is shown below as the sortable, exportable data table.
// Every other table (e.g. Q4's arrivals/departures summary, Q7's by-taxiway table) stays in the text.
function answerMarkdown(markdown: string, hasData: boolean): string {
  const text = markdown.replace(ROW_COUNT_LABEL, '');
  if (!hasData) return text;
  const lines = text.split('\n');
  let end = lines.length - 1;
  while (end >= 0 && !isTableLine(lines[end])) end--;
  if (end < 0) return text;
  let start = end;
  while (start > 0 && isTableLine(lines[start - 1])) start--;
  lines.splice(start, end - start + 1);
  return lines.join('\n');
}

const textOf = (node: any): string =>
  typeof node === 'string' || typeof node === 'number' ? String(node)
    : Array.isArray(node) ? node.map(textOf).join('')
    : node?.props?.children !== undefined ? textOf(node.props.children) : '';

// Markdown tables use the same style as the data table (query-results.css); numbers are right-aligned.
const markdownTables = {
  table: ({ node, ...props }: any) => (
    <div className="not-prose my-3 rounded-lg border border-gray-200 bg-white overflow-x-auto">
      <table className="query-data-table" {...props} />
    </div>
  ),
  td: ({ node, children, ...props }: any) => (
    <td className={/^-?[\d,]+(\.\d+)?$/.test(textOf(children).trim()) ? 'query-number' : undefined} {...props}>
      {children}
    </td>
  ),
};

export function ChatMessage({ message }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('table');
  const hasData = message.role === 'assistant' && !!message.data?.length;
  const detailStart = message.role === 'assistant'
    ? message.content.search(/\*\*(?:Sample|Definition)[^\n]*?:\*\*/)
    : -1;
  const details = detailStart >= 0 ? message.content.slice(detailStart) : '';
  const answer = detailStart >= 0 ? message.content.slice(0, detailStart) : message.content;

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (timestamp: Date | string) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  console.log('🎨 ChatMessage rendering:', message);

  return (
    <div className={cn(
      "group flex gap-4 p-6 hover:bg-gray-50/50 transition-colors",
      message.role === 'assistant' && "bg-gray-50/30"
    )}>
      {/* Avatar */}
      <div className="flex-shrink-0">
        <Avatar className="h-8 w-8">
          <AvatarFallback className={cn(
            "text-sm font-medium",
            message.role === 'user' 
              ? "bg-blue-100 text-blue-700" 
              : "bg-green-100 text-green-700"
          )}>
            {message.role === 'user' ? 'U' : 'AI'}
          </AvatarFallback>
        </Avatar>
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-gray-900">
            {message.role === 'user' ? 'You' : 'Gate Assistant'}
          </span>
          <span className="text-xs text-gray-500">
            {formatTime(message.timestamp)}
          </span>
        </div>
        
        {message.role === 'assistant' && <SourceBadge source={message.metadata?.sqlSource} />}

        {/* Markdown content */}
        <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed query-answer">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownTables}>
            {message.role === 'assistant' ? answerMarkdown(answer, hasData) : answer}
          </ReactMarkdown>
        </div>

        {/* Chart/Table Toggle for responses with both */}
        {message.role === 'assistant' && message.chart && message.data && message.data.length > 0 && (
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-3">
              <Button
                variant={viewMode === 'chart' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('chart')}
                className="h-8 px-3 text-xs"
              >
                <BarChart3 className="h-3 w-3 mr-1.5" />
                Chart View
              </Button>
              <Button
                variant={viewMode === 'table' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('table')}
                className="h-8 px-3 text-xs"
              >
                <TableIcon className="h-3 w-3 mr-1.5" />
                Table View
              </Button>
            </div>

            {viewMode === 'chart' ? (
              <ChartVisualization chartConfig={message.chart} insightsText={message.content} />
            ) : (
              <DataTableWithExport 
                data={message.data} 
                title="SeaTac Operations Analysis"
                pageSize={5}
              />
            )}
          </div>
        )}

        {/* Chart Only (no table data) */}
        {message.role === 'assistant' && message.chart && (!message.data || message.data.length === 0) && (
          <div className="mt-4">
            <ChartVisualization chartConfig={message.chart} insightsText={message.content} />
          </div>
        )}

        {/* Table Only (no chart) */}
        {message.role === 'assistant' && !message.chart && message.data && message.data.length > 0 && (
          <div className="mt-4">
            <DataTableWithExport 
              data={message.data} 
              title="Query Results"
              pageSize={5}
            />
          </div>
        )}

        {details && (
          <div className="query-calculation-details">
            <div className="query-details-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{details}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {message.role === 'assistant' && (
          <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              onClick={copyToClipboard}
              className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 mr-1" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 mr-1" />
                  Copy
                </>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

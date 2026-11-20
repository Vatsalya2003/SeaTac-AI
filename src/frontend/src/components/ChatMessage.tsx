import { useState } from 'react';
import { Button } from './ui/button';
import { Copy, Check, BarChart3, Table as TableIcon, BadgeCheck, FlaskConical, Sparkles } from 'lucide-react';
import { cn } from './ui/utils';
import ChartVisualization from './ChartVisualization';
import { DataTableWithExport } from './DataTableWithExport';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './query-results.css';
import { headlineRow } from '../format';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date | string;
  chart?: any;
  data?: any[];
  metadata?: { sqlSource?: string; queryType?: string };
}

interface ChatMessageProps {
  message: Message;
}

// Badge above each answer, from the backend's sql_source. Greetings ('system') and answers that
// couldn't be given ('none', or no sql_source) get no badge.
const SOURCE_BADGES: Record<string, { label: string; className: string; Icon: typeof BadgeCheck }> = {
  template: { label: 'Verified answer', Icon: BadgeCheck,
              className: 'answer-badge--verified' },
  provisional: { label: 'Tested, provisional rule', Icon: FlaskConical,
                 className: 'answer-badge--provisional' },
  ai_sql: { label: 'AI-generated, not yet verified', Icon: Sparkles,
            className: 'answer-badge--ai' },
};

// A tested answer whose rule the Port hasn't confirmed yet: its notes say PROVISIONAL (Q7) or
// PENDING PORT CONFIRMATION (Q3). The backend sends no separate flag, so the text decides.
const PROVISIONAL_NOTE = /\bPROVISIONAL\b|PENDING PORT CONFIRMATION/;
const badgeSource = (source: string | undefined, content: string) =>
  source === 'template' && PROVISIONAL_NOTE.test(content) ? 'provisional' : source;

function SourceBadge({ source }: { source?: string }) {
  const badge = source ? SOURCE_BADGES[source] : undefined;
  if (!badge) return null;
  const { label, className, Icon } = badge;
  return (
    <div className={cn('answer-badge', className)} data-testid="answer-source-badge">
      <Icon className="answer-badge-icon" aria-hidden="true" />
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
const HOURLY_ANSWERS = new Set(['Q2', 'Q3', 'Q10']);

const NUMBER_CELL = /^-?[\d,]+(\.\d+)?$/;
const cellsOf = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());

// Marks number columns right-aligned in each markdown table (|---:|), labels left (|:---|).
function alignTableColumns(text: string): string {
  const lines = text.split('\n');
  for (let i = 1; i < lines.length; i++) {
    if (!/^\s*\|(\s*:?-+:?\s*\|)+\s*$/.test(lines[i]) || !isTableLine(lines[i - 1])) continue;
    let end = i + 1;
    while (end < lines.length && isTableLine(lines[end])) end++;
    const body = lines.slice(i + 1, end).map(cellsOf);
    const numeric = cellsOf(lines[i]).map((_, c) => body.length > 0
      && body.every(r => NUMBER_CELL.test(r[c] ?? '') || r[c] === 'No data') && body.some(r => NUMBER_CELL.test(r[c] ?? '')));
    lines[i] = '|' + numeric.map(n => (n ? '---:' : ':---')).join('|') + '|';
  }
  return lines.join('\n');
}

function answerMarkdown(markdown: string, hasData: boolean): string {
  const text = alignTableColumns(markdown.replace(ROW_COUNT_LABEL, ''));
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
    <div className="query-md-table">
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
  // hourly answers (Q2 taxi-out by hour, Q3 movement area by hour, Q10 peak hours) open on the chart
  const [viewMode, setViewMode] = useState<'chart' | 'table'>(
    () => (HOURLY_ANSWERS.has(message.metadata?.queryType ?? '') && message.chart ? 'chart' : 'table'));
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

  if (message.role === 'user') {
    return (
      <div className="sea-msg sea-msg-user" id={`msg-${message.id}`}>
        <div className="sea-bubble">{message.content}</div>
      </div>
    );
  }

  return (
    <article className="sea-msg sea-msg-assistant" id={`msg-${message.id}`} aria-label="Answer from SeaTac AI">
        <div className="sea-msg-meta">
          <span className="sea-msg-author">SeaTac AI</span>
          <time dateTime={new Date(message.timestamp).toISOString()}>{formatTime(message.timestamp)}</time>
        </div>

        <SourceBadge source={badgeSource(message.metadata?.sqlSource, message.content)} />

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
                highlightRow={headlineRow(message.metadata?.queryType, message.data)}
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
              highlightRow={headlineRow(message.metadata?.queryType, message.data)}
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

        <div className="sea-msg-actions">
          <button type="button" className="sea-btn sea-btn-ghost sea-copy" onClick={copyToClipboard}>
            {copied ? <><Check aria-hidden="true" /> Copied</> : <><Copy aria-hidden="true" /> Copy</>}
          </button>
        </div>
    </article>
  );
}
